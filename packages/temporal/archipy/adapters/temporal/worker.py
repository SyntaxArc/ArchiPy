"""Worker management for Temporal workflow execution.

This module provides worker management functionality for Temporal workflow
orchestration, including worker lifecycle management, task queue assignment,
and integration with ArchiPy service adapters.
"""

from __future__ import annotations

import asyncio
import logging
import warnings
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override
from uuid import uuid7

from temporalio.worker import (
    PollerBehavior,
    PollerBehaviorAutoscaling,
    PollerBehaviorSimpleMaximum,
    Worker,
)
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import TemporalConfig
from archipy.models.errors import InvalidArgumentError
from archipy.models.errors.temporal_errors import (
    WorkerConnectionError,
    WorkerShutdownError,
)

from .adapters import TemporalAdapter
from .ports import WorkerHandle as PortWorkerHandle, WorkerPort

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from concurrent.futures import Executor

    from temporalio.client import Client, Interceptor
    from temporalio.converter import DataConverter
    from temporalio.worker import WorkerDeploymentConfig, WorkerTuner, WorkflowRunner


# Extra time past the graceful shutdown timeout for the SDK to cancel and drain activities.
SHUTDOWN_MARGIN_SECONDS = 10

# temporalio's own default for Worker(max_eager_activity_reservations_per_workflow_task=...).
_SDK_EAGER_ACTIVITY_RESERVATIONS = 3


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
        graceful_shutdown_seconds: int = 30,
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
            graceful_shutdown_seconds (int): Default graceful shutdown timeout in seconds.
                Defaults to 30.
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
        self._graceful_shutdown_seconds = graceful_shutdown_seconds
        self._running = False
        self._run_error: BaseException | None = None
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
            task.add_done_callback(self._on_worker_done)

            self._logger.info(
                "Worker started successfully",
                extra={
                    "worker_id": self.worker_id,
                    "task_queue": self.task_queue,
                },
            )

        except Exception as error:  # worker lifecycle; temporal/runtime may raise broadly
            raise WorkerConnectionError(
                additional_data={
                    "message": f"Failed to start worker for task queue '{self.task_queue}'",
                    "task_queue": self.task_queue,
                    "worker_id": self.worker_id,
                    "error": str(error),
                },
            ) from error

    def _on_worker_done(self, task: asyncio.Task[None]) -> None:
        """Mark the worker stopped when ``Worker.run`` returns, and log the error that ended it.

        Args:
            task (asyncio.Task[None]): The finished ``Worker.run`` task.
        """
        self._running = False
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            self._run_error = error
            self._logger.error(
                "Worker stopped unexpectedly",
                exc_info=error,
                extra={"worker_id": self.worker_id, "task_queue": self.task_queue},
            )

    @property
    def run_error(self) -> BaseException | None:
        """The error that ended ``Worker.run``, if it crashed.

        Returns:
            BaseException | None: The error, or None while running or after a clean stop.
        """
        return self._run_error

    async def stop(self, grace_period: int | None = None) -> None:
        """Stop the worker gracefully.

        Args:
            grace_period (int, optional): Seconds to let running activities finish before the SDK cancels them,
                as set by ``graceful_shutdown_timeout``. If None, uses the configured graceful shutdown timeout.
                The call gives up ``SHUTDOWN_MARGIN_SECONDS`` after that, so the SDK's own cancellation completes.

        Raises:
            WorkerShutdownError: If the worker fails to stop gracefully.
        """
        if grace_period is None:
            grace_period = self._graceful_shutdown_seconds

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

            # The SDK enforces the grace period itself (cancelling activities when it elapses); the outer timeout only
            # guards against activities that ignore cancellation, so it must not cut the SDK's shutdown short.
            await asyncio.wait_for(self._worker.shutdown(), timeout=grace_period + SHUTDOWN_MARGIN_SECONDS)
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
        except Exception as error:  # worker lifecycle; temporal/runtime may raise broadly
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

    def __init__(
        self,
        temporal_config: TemporalConfig | None = None,
        data_converter: DataConverter | None = None,
        interceptors: Sequence[Interceptor] | None = None,
    ) -> None:
        """Initialize the worker manager.

        Args:
            temporal_config (TemporalConfig, optional): Configuration settings for Temporal.
                If None, retrieves from global config. Defaults to None.
            data_converter (DataConverter, optional): Data converter passed to the client the workers use.
                Defaults to None (see ``TemporalAdapter``).
            interceptors (Sequence[Interceptor], optional): Client interceptors; those that also implement
                ``temporalio.worker.Interceptor`` apply to every worker this manager starts. Defaults to None.
        """
        # Get temporal config from the global config or use provided one
        if temporal_config is None:
            global_config = BaseConfig.global_config()
            if hasattr(global_config, "TEMPORAL"):
                self.config = global_config.TEMPORAL
            else:
                # Create a default config if none exists

                self.config = TemporalConfig()
        else:
            self.config = temporal_config
        self._temporal_adapter = TemporalAdapter(temporal_config, data_converter, interceptors)
        self._workers: dict[str, WorkerHandle] = {}
        self._logger = logging.getLogger(__name__)

    async def _get_client(self) -> Client:
        """Get the Temporal client from the adapter.

        Returns:
            Client: The Temporal client instance.
        """
        return await self._temporal_adapter.get_client()

    def _poller_behavior(self) -> PollerBehavior:
        """Build the task poller behaviour, autoscaling when enabled in configuration.

        Returns:
            PollerBehavior: Autoscaling pollers, or the SDK default of at most 5 pollers.
        """
        if self.config.WORKER_POLLER_AUTOSCALING:
            return PollerBehaviorAutoscaling()
        return PollerBehaviorSimpleMaximum(maximum=5)

    def _eager_activity_reservations(self) -> int:
        """Resolve how many eager activities one workflow task may reserve.

        Returns:
            int: ``WORKER_MAX_EAGER_ACTIVITY_RESERVATIONS``, or the SDK default when it is unset.
        """
        reservations = self.config.WORKER_MAX_EAGER_ACTIVITY_RESERVATIONS
        return _SDK_EAGER_ACTIVITY_RESERVATIONS if reservations is None else reservations

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
        tuner: WorkerTuner | None = None,
        activity_executor: Executor | None = None,
        deployment_config: WorkerDeploymentConfig | None = None,
        workflow_failure_exception_types: Sequence[type[BaseException]] = (),
        workflow_runner: WorkflowRunner | None = None,
    ) -> WorkerHandle:
        """Start a Temporal worker for the specified task queue.

        Args:
            task_queue (str): The task queue this worker will poll from.
            workflows (list[type], optional): List of workflow classes to register.
                Defaults to None.
            activities (list[Callable], optional): List of activity callables to register.
                Defaults to None.
            build_id (str, optional): Deprecated, use ``deployment_config``. Build identifier for worker
                versioning. Defaults to None.
            identity (str, optional): Unique worker identity. If None, auto-generated.
                Defaults to None.
            max_concurrent_workflow_tasks (int, optional): Maximum concurrent workflow tasks.
                Defaults to None (server default).
            max_concurrent_activities (int, optional): Maximum concurrent activity tasks.
                Defaults to None (server default).
            tuner (WorkerTuner, optional): Slot supplier tuner, e.g. ``WorkerTuner.create_resource_based(...)``.
                Cannot be combined with the ``max_concurrent_*`` limits. Defaults to None.
            activity_executor (Executor, optional): Executor that runs synchronous (non-async) activities.
                Required when registering sync activities. Defaults to None.
            deployment_config (WorkerDeploymentConfig, optional): Worker Deployment version this worker belongs
                to, replacing ``build_id``. Defaults to None.
            workflow_failure_exception_types (Sequence[type[BaseException]], optional): Exception types that fail
                the workflow instead of retrying the workflow task (e.g. ``[Exception]`` to fail on any error).
                Defaults to () (only ``FailureError`` subclasses fail it).
            workflow_runner (WorkflowRunner, optional): Workflow runner, e.g. a ``SandboxedWorkflowRunner`` with
                ``restrictions.with_passthrough_modules(...)``. Defaults to None (the SDK sandbox).

        Returns:
            WorkerHandle: Handle to the started worker.

        Raises:
            WorkerConnectionError: If the worker fails to start.
        """
        if not task_queue or not task_queue.strip():
            raise WorkerConnectionError(
                additional_data={
                    "message": "Task queue name cannot be empty",
                    "task_queue": task_queue,
                },
            )

        if build_id is not None:
            if deployment_config is not None:
                raise InvalidArgumentError(
                    argument_name="build_id",
                    additional_data={"reason": "build_id and deployment_config are mutually exclusive"},
                )
            warnings.warn(
                "start_worker(build_id=...) is deprecated; pass deployment_config=WorkerDeploymentConfig(...) instead",
                DeprecationWarning,
                stacklevel=2,
            )

        client = await self._get_client()
        worker_id = str(uuid7())
        # uuid7 starts with the timestamp, so the random tail keeps identities of workers started together apart.
        worker_identity = identity or f"worker-{worker_id[-12:]}"

        try:
            # Create the Temporal worker
            # Note: Worker inherits Runtime (including OTLP metrics config) from the Client
            worker = Worker(
                client,
                task_queue=task_queue,
                workflows=workflows or [],
                activities=activities or [],
                build_id=build_id,
                deployment_config=deployment_config,
                workflow_failure_exception_types=workflow_failure_exception_types,
                workflow_runner=workflow_runner or SandboxedWorkflowRunner(),
                identity=worker_identity,
                max_concurrent_workflow_tasks=max_concurrent_workflow_tasks,
                max_concurrent_activities=max_concurrent_activities,
                max_cached_workflows=self.config.WORKER_MAX_CACHED_WORKFLOWS,
                graceful_shutdown_timeout=timedelta(seconds=self.config.WORKER_GRACEFUL_SHUTDOWN_SECONDS),
                debug_mode=self.config.WORKER_DEBUG_MODE,
                disable_eager_activity_execution=self.config.WORKER_DISABLE_EAGER_ACTIVITY_EXECUTION,
                max_eager_activity_reservations_per_workflow_task=self._eager_activity_reservations(),
                max_concurrent_local_activities=self.config.WORKER_MAX_CONCURRENT_LOCAL_ACTIVITIES,
                tuner=tuner,
                activity_executor=activity_executor,
                max_activities_per_second=self.config.WORKER_MAX_ACTIVITIES_PER_SECOND,
                max_task_queue_activities_per_second=self.config.WORKER_MAX_TASK_QUEUE_ACTIVITIES_PER_SECOND,
                workflow_task_poller_behavior=self._poller_behavior(),
                activity_task_poller_behavior=self._poller_behavior(),
            )

            # Create worker handle
            worker_handle = WorkerHandle(
                worker=worker,
                worker_id=worker_id,
                task_queue=task_queue,
                workflows=workflows,
                activities=activities,
                build_id=build_id or (deployment_config.version.build_id if deployment_config else None),
                identity=worker_identity,
                max_concurrent_workflow_tasks=max_concurrent_workflow_tasks,
                max_concurrent_activities=max_concurrent_activities,
                graceful_shutdown_seconds=self.config.WORKER_GRACEFUL_SHUTDOWN_SECONDS,
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

        except Exception as error:  # worker lifecycle; temporal/runtime may raise broadly
            raise WorkerConnectionError(
                additional_data={
                    "message": f"Failed to start worker for task queue '{task_queue}'",
                    "task_queue": task_queue,
                    "worker_id": worker_id,
                    "identity": worker_identity,
                    "error": str(error),
                },
            ) from error
        else:
            return worker_handle

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

        except Exception:  # worker lifecycle; temporal/runtime may raise broadly
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
        results = await asyncio.gather(
            *(self.stop_worker(worker_handle) for worker_handle in workers_to_stop),
            return_exceptions=True,
        )
        for worker_handle, result in zip(workers_to_stop, results, strict=True):
            if isinstance(result, BaseException):
                shutdown_errors.append(
                    {
                        "worker_id": worker_handle.worker_id,
                        "task_queue": worker_handle.task_queue,
                        "error": str(result),
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
