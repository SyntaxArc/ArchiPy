"""Worker management for Temporal workflow execution.

This module provides worker management functionality for Temporal workflow
orchestration, including worker lifecycle management, task queue assignment,
and integration with ArchiPy service adapters.
"""

import asyncio
import logging
from collections.abc import Callable
from typing import Any, override
from uuid import uuid4

from temporalio.client import Client
from temporalio.worker import Worker

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import TemporalConfig
from archipy.models.errors.temporal_errors import WorkerConnectionError, WorkerShutdownError

from .adapters import TemporalAdapter
from .ports import WorkerHandle as PortWorkerHandle, WorkerPort


class WorkerHandle(PortWorkerHandle):
    """Handle for managing a Temporal worker instance.

    Provides methods to control and monitor a running Temporal worker,
    including starting, stopping, and querying worker status.

    Attributes:
        worker_id (str): Unique identifier for this worker instance.
        task_queue (str): The task queue this worker polls from.
        workflows (list[type]): List of workflow types registered with this worker.
        activities (list[Callable]): List of activity callables registered with this worker.
        build_id (str | None): Build identifier for worker versioning.
        identity (str | None): Worker identity for debugging and monitoring.
        max_concurrent_workflow_tasks (int): Maximum concurrent workflow tasks.
        max_concurrent_activities (int): Maximum concurrent activity tasks.
    """

    def __init__(
        self,
        worker: Worker,
        worker_id: str,
        task_queue: str,
        workflows: list[type] | None = None,
        activities: list[Callable[..., Any]] | None = None,
        build_id: str | None = None,
        identity: str | None = None,
        max_concurrent_workflow_tasks: int | None = None,
        max_concurrent_activities: int | None = None,
    ) -> None:
        """Initialize the worker handle.

        Args:
            worker (Worker): The Temporal worker instance.
            worker_id (str): Unique identifier for this worker instance.
            task_queue (str): The task queue this worker polls from.
            workflows (list[type], optional): List of workflow types. Defaults to None.
            activities (list[Callable], optional): List of activity callables. Defaults to None.
            build_id (str, optional): Build identifier for worker versioning. Defaults to None.
            identity (str, optional): Worker identity. Defaults to None.
            max_concurrent_workflow_tasks (int, optional): Maximum concurrent workflow tasks.
                Defaults to None.
            max_concurrent_activities (int, optional): Maximum concurrent activity tasks.
                Defaults to None.
        """
        self._worker = worker
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.workflows = workflows or []
        self.activities = activities or []
        self.build_id = build_id
        self.identity = identity
        self.max_concurrent_workflow_tasks = max_concurrent_workflow_tasks
        self.max_concurrent_activities = max_concurrent_activities
        self._running = False
        self._logger = logging.getLogger(__name__)

    async def start(self) -> None:
        """Start the worker to begin polling for tasks.

        Raises:
            WorkerConnectionError: If the worker fails to start.
        """
        try:
            self._logger.info(
                "Starting worker",
                extra={
                    "worker_id": self.worker_id,
                    "task_queue": self.task_queue,
                    "identity": self.identity,
                },
            )

            # Start the worker in the background
            task = asyncio.create_task(self._worker.run())
            # Store task reference to avoid it being garbage collected
            self._background_task = task
            self._running = True

            self._logger.info(
                "Worker started successfully",
                extra={
                    "worker_id": self.worker_id,
                    "task_queue": self.task_queue,
                },
            )

        except Exception as error:
            raise WorkerConnectionError(
                additional_data={
                    "message": f"Failed to start worker for task queue '{self.task_queue}'",
                    "task_queue": self.task_queue,
                    "worker_id": self.worker_id,
                    "error": str(error),
                },
            ) from error

    async def stop(self, grace_period: int = 30) -> None:
        """Stop the worker gracefully.

        Args:
            grace_period (int): Maximum time to wait for graceful shutdown in seconds.
                Defaults to 30.

        Raises:
            WorkerShutdownError: If the worker fails to stop gracefully.
        """
        if not self._running:
            return

        try:
            self._logger.info(
                "Stopping worker",
                extra={
                    "worker_id": self.worker_id,
                    "task_queue": self.task_queue,
                    "grace_period": grace_period,
                },
            )

            # Signal shutdown and wait for graceful completion
            await asyncio.wait_for(self._worker.shutdown(), timeout=grace_period)
            self._running = False

            self._logger.info(
                "Worker stopped successfully",
                extra={
                    "worker_id": self.worker_id,
                    "task_queue": self.task_queue,
                },
            )

        except TimeoutError as error:
            raise WorkerShutdownError(
                additional_data={
                    "message": f"Worker shutdown timeout after {grace_period} seconds",
                    "worker_identity": self.identity,
                    "task_queue": self.task_queue,
                    "worker_id": self.worker_id,
                    "grace_period": grace_period,
                },
            ) from error
        except Exception as error:
            raise WorkerShutdownError(
                additional_data={
                    "message": f"Failed to stop worker for task queue '{self.task_queue}'",
                    "worker_identity": self.identity,
                    "task_queue": self.task_queue,
                    "worker_id": self.worker_id,
                    "error": str(error),
                },
            ) from error

    async def wait_until_stopped(self) -> None:
        """Wait until the worker is stopped."""
        await self._background_task

    @property
    def is_running(self) -> bool:
        """Check if the worker is currently running.

        Returns:
            bool: True if the worker is running, False otherwise.
        """
        return self._running

    def get_stats(self) -> dict[str, Any]:
        """Get worker statistics and status information.

        Returns:
            dict[str, Any]: Worker statistics and status.
        """
        return {
            "worker_id": self.worker_id,
            "task_queue": self.task_queue,
            "identity": self.identity,
            "build_id": self.build_id,
            "is_running": self.is_running,
            "workflow_count": len(self.workflows),
            "activity_count": len(self.activities),
            "max_concurrent_workflow_tasks": self.max_concurrent_workflow_tasks,
            "max_concurrent_activities": self.max_concurrent_activities,
        }


class TemporalWorkerManager(WorkerPort):
    """Manager for Temporal worker lifecycle and operations.

    This class provides a high-level interface for managing Temporal workers,
    including creation, configuration, and lifecycle management. It integrates
    with ArchiPy configuration and service patterns.

    Args:
        temporal_config (TemporalConfig, optional): Configuration settings for Temporal.
            If None, retrieves from global config. Defaults to None.
    """

    def __init__(self, temporal_config: TemporalConfig | None = None) -> None:
        """Initialize the worker manager.

        Args:
            temporal_config (TemporalConfig, optional): Configuration settings for Temporal.
                If None, retrieves from global config. Defaults to None.
        """
        # Get temporal config from the global config or use provided one
        if temporal_config is None:
            global_config = BaseConfig.global_config()
            if hasattr(global_config, "TEMPORAL"):
                self.config = global_config.TEMPORAL
            else:
                # Create a default config if none exists
                from archipy.configs.config_template import TemporalConfig

                self.config = TemporalConfig()
        else:
            self.config = temporal_config
        self._temporal_adapter = TemporalAdapter(temporal_config)
        self._workers: dict[str, WorkerHandle] = {}
        self._logger = logging.getLogger(__name__)

    async def _get_client(self) -> Client:
        """Get the Temporal client from the adapter.

        Returns:
            Client: The Temporal client instance.
        """
        return await self._temporal_adapter.get_client()

    @override
    async def start_worker(
        self,
        task_queue: str,
        workflows: list[type] | None = None,
        activities: list[Callable[..., Any]] | None = None,
        build_id: str | None = None,
        identity: str | None = None,
        max_concurrent_workflow_tasks: int | None = None,
        max_concurrent_activities: int | None = None,
    ) -> WorkerHandle:
        """Start a Temporal worker for the specified task queue.

        Args:
            task_queue (str): The task queue this worker will poll from.
            workflows (list[type], optional): List of workflow classes to register.
                Defaults to None.
            activities (list[Callable], optional): List of activity callables to register.
                Defaults to None.
            build_id (str, optional): Build identifier for worker versioning.
                Defaults to None.
            identity (str, optional): Unique worker identity. If None, auto-generated.
                Defaults to None.
            max_concurrent_workflow_tasks (int, optional): Maximum concurrent workflow tasks.
                Defaults to None (server default).
            max_concurrent_activities (int, optional): Maximum concurrent activity tasks.
                Defaults to None (server default).

        Returns:
            WorkerHandle: Handle to the started worker.

        Raises:
            WorkerConnectionError: If the worker fails to start.
        """
        client = await self._get_client()
        worker_id = str(uuid4())
        worker_identity = identity or f"worker-{worker_id[:8]}"

        try:
            # Create the Temporal worker
            worker = Worker(
                client,
                task_queue=task_queue,
                workflows=workflows or [],
                activities=activities or [],
                build_id=build_id,
                identity=worker_identity,
                max_concurrent_workflow_tasks=max_concurrent_workflow_tasks,
                max_concurrent_activities=max_concurrent_activities,
            )

            # Create worker handle
            worker_handle = WorkerHandle(
                worker=worker,
                worker_id=worker_id,
                task_queue=task_queue,
                workflows=workflows,
                activities=activities,
                build_id=build_id,
                identity=worker_identity,
                max_concurrent_workflow_tasks=max_concurrent_workflow_tasks,
                max_concurrent_activities=max_concurrent_activities,
            )

            # Start the worker
            await worker_handle.start()

            # Register the worker
            self._workers[worker_id] = worker_handle

            self._logger.info(
                "Worker created and started",
                extra={
                    "worker_id": worker_id,
                    "task_queue": task_queue,
                    "identity": worker_identity,
                    "workflow_count": len(workflows) if workflows else 0,
                    "activity_count": len(activities) if activities else 0,
                },
            )

            return worker_handle

        except Exception as error:
            raise WorkerConnectionError(
                additional_data={
                    "message": f"Failed to start worker for task queue '{task_queue}'",
                    "task_queue": task_queue,
                    "worker_id": worker_id,
                    "identity": worker_identity,
                    "error": str(error),
                },
            ) from error

    @override
    async def stop_worker(self, worker_handle: PortWorkerHandle) -> None:
        """Stop a running Temporal worker.

        Args:
            worker_handle (PortWorkerHandle): Handle to the worker to stop.

        Raises:
            WorkerShutdownError: If the worker fails to stop gracefully.
        """
        if worker_handle.worker_id not in self._workers:
            return  # Worker already stopped or not managed by this manager

        try:
            await worker_handle.stop()
            del self._workers[worker_handle.worker_id]

            self._logger.info(
                "Worker stopped and removed",
                extra={
                    "worker_id": worker_handle.worker_id,
                    "task_queue": worker_handle.task_queue,
                },
            )

        except Exception:
            # Remove from tracking even if shutdown failed
            if worker_handle.worker_id in self._workers:
                del self._workers[worker_handle.worker_id]
            raise

    @override
    async def shutdown_all_workers(self) -> None:
        """Shutdown all workers managed by this port.

        Performs graceful shutdown of all active workers, waiting for current
        tasks to complete before terminating.

        Raises:
            WorkerShutdownError: If any worker fails to shutdown gracefully.
        """
        if not self._workers:
            return

        self._logger.info(
            "Shutting down all workers",
            extra={
                "worker_count": len(self._workers),
            },
        )

        shutdown_errors = []
        workers_to_stop = list(self._workers.values())

        # Stop all workers concurrently
        for worker_handle in workers_to_stop:
            try:
                await self.stop_worker(worker_handle)
            except Exception as error:
                shutdown_errors.append(
                    {
                        "worker_id": worker_handle.worker_id,
                        "task_queue": worker_handle.task_queue,
                        "error": str(error),
                    },
                )

        if shutdown_errors:
            raise WorkerShutdownError(
                additional_data={
                    "message": f"Failed to shutdown {len(shutdown_errors)} workers",
                    "worker_count": len(self._workers),
                    "failed_count": len(shutdown_errors),
                    "shutdown_errors": shutdown_errors,
                },
            )

        self._logger.info("All workers shut down successfully")

    def get_worker_stats(self) -> list[dict[str, Any]]:
        """Get statistics for all managed workers.

        Returns:
            list[dict[str, Any]]: List of worker statistics.
        """
        return [worker.get_stats() for worker in self._workers.values()]

    def get_worker_by_task_queue(self, task_queue: str) -> WorkerHandle | None:
        """Get a worker handle by task queue.

        Args:
            task_queue (str): The task queue to search for.

        Returns:
            WorkerHandle | None: Worker handle if found, None otherwise.
        """
        for worker in self._workers.values():
            if worker.task_queue == task_queue:
                return worker
        return None

    def list_workers(self) -> list[WorkerHandle]:
        """Get a list of all managed workers.

        Returns:
            list[WorkerHandle]: List of worker handles.
        """
        return list(self._workers.values())

    @property
    def worker_count(self) -> int:
        """Get the number of managed workers.

        Returns:
            int: Number of managed workers.
        """
        return len(self._workers)

    async def close(self) -> None:
        """Close the worker manager and all managed workers.

        Performs cleanup of all resources, including stopping all workers
        and closing the Temporal client connection.
        """
        await self.shutdown_all_workers()
        await self._temporal_adapter.close()
        self._logger.info("Worker manager closed")
