"""Port interfaces for Temporal workflow orchestration.

This module defines the abstract interfaces for Temporal workflow and activity
operations, providing a standardized contract for workflow orchestration within
the ArchiPy architecture.
"""

from abc import abstractmethod
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from temporalio.client import ScheduleSpec

T = TypeVar("T")


class TemporalPort:
    """Interface for Temporal workflow operations providing a standardized access pattern.

    This interface defines the contract for Temporal adapters, ensuring consistent
    implementation of workflow operations across different adapters. It covers
    workflow lifecycle management, execution control, and query operations.

    Implementing classes should provide concrete implementations for all
    methods, typically by wrapping a Temporal client library.
    """

    @abstractmethod
    async def start_workflow(
        self,
        workflow: str | Callable,
        arg: Any = None,
        workflow_id: str | None = None,
        task_queue: str | None = None,
        execution_timeout: int | None = None,
        run_timeout: int | None = None,
        task_timeout: int | None = None,
        memo: dict[str, Any] | None = None,
        search_attributes: dict[str, Any] | None = None,
    ) -> Any:  # WorkflowHandle
        """Start a workflow execution asynchronously.

        Args:
            workflow (str | Callable): The workflow function or workflow type name.
            arg (Any, optional): Input argument for the workflow. Defaults to None.
            workflow_id (str, optional): Unique identifier for the workflow execution.
                If None, a UUID will be generated. Defaults to None.
            task_queue (str, optional): Task queue name for workflow execution.
                If None, uses the default task queue. Defaults to None.
            execution_timeout (int, optional): Maximum workflow execution time in seconds.
                Overrides config default. Defaults to None.
            run_timeout (int, optional): Maximum single workflow run time in seconds.
                Overrides config default. Defaults to None.
            task_timeout (int, optional): Maximum workflow task processing time in seconds.
                Overrides config default. Defaults to None.
            memo (dict[str, Any], optional): Non-indexed metadata for the workflow.
                Defaults to None.
            search_attributes (dict[str, Any], optional): Indexed metadata for workflow search.
                Defaults to None.

        Returns:
            WorkflowHandle[T, Any]: Handle to the started workflow execution.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def execute_workflow(
        self,
        workflow: str | Callable,
        arg: Any = None,
        workflow_id: str | None = None,
        task_queue: str | None = None,
        execution_timeout: int | None = None,
        run_timeout: int | None = None,
        task_timeout: int | None = None,
    ) -> T:
        """Execute a workflow and wait for its completion.

        Args:
            workflow (str | Callable): The workflow function or workflow type name.
            arg (Any, optional): Input argument for the workflow. Defaults to None.
            workflow_id (str, optional): Unique identifier for the workflow execution.
                If None, a UUID will be generated. Defaults to None.
            task_queue (str, optional): Task queue name for workflow execution.
                If None, uses the default task queue. Defaults to None.
            execution_timeout (int, optional): Maximum workflow execution time in seconds.
                Overrides config default. Defaults to None.
            run_timeout (int, optional): Maximum single workflow run time in seconds.
                Overrides config default. Defaults to None.
            task_timeout (int, optional): Maximum workflow task processing time in seconds.
                Overrides config default. Defaults to None.

        Returns:
            T: The workflow execution result.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_workflow_handle(self, workflow_id: str, run_id: str | None = None) -> Any:  # WorkflowHandle
        """Get a handle to an existing workflow execution.

        Args:
            workflow_id (str): The unique identifier of the workflow execution.
            run_id (str, optional): The specific run identifier within the workflow.
                If None, gets the latest run. Defaults to None.

        Returns:
            WorkflowHandle[T, Any]: Handle to the workflow execution.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def cancel_workflow(self, workflow_id: str, run_id: str | None = None, reason: str | None = None) -> None:
        """Cancel a running workflow execution.

        Args:
            workflow_id (str): The unique identifier of the workflow execution.
            run_id (str, optional): The specific run identifier within the workflow.
                If None, cancels the latest run. Defaults to None.
            reason (str, optional): Reason for cancellation. Defaults to None.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def terminate_workflow(self, workflow_id: str, run_id: str | None = None, reason: str | None = None) -> None:
        """Terminate a running workflow execution immediately.

        Args:
            workflow_id (str): The unique identifier of the workflow execution.
            run_id (str, optional): The specific run identifier within the workflow.
                If None, terminates the latest run. Defaults to None.
            reason (str, optional): Reason for termination. Defaults to None.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def signal_workflow(
        self,
        workflow_id: str,
        signal_name: str,
        arg: Any = None,
        run_id: str | None = None,
    ) -> None:
        """Send a signal to a running workflow execution.

        Args:
            workflow_id (str): The unique identifier of the workflow execution.
            signal_name (str): The name of the signal to send.
            arg (Any, optional): Argument to pass with the signal. Defaults to None.
            run_id (str, optional): The specific run identifier within the workflow.
                If None, signals the latest run. Defaults to None.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def query_workflow(
        self,
        workflow_id: str,
        query_name: str,
        arg: Any = None,
        run_id: str | None = None,
    ) -> Any:
        """Query a running workflow execution for information.

        Args:
            workflow_id (str): The unique identifier of the workflow execution.
            query_name (str): The name of the query to execute.
            arg (Any, optional): Argument to pass with the query. Defaults to None.
            run_id (str, optional): The specific run identifier within the workflow.
                If None, queries the latest run. Defaults to None.

        Returns:
            Any: The query result from the workflow.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_workflows(
        self,
        query: str | None = None,
        page_size: int | None = None,
        next_page_token: bytes | None = None,
    ) -> "WorkflowListResponse":
        """List workflow executions matching the given criteria.

        Args:
            query (str, optional): List filter query in Temporal SQL syntax.
                Defaults to None (no filter).
            page_size (int, optional): Maximum number of results per page.
                Defaults to None (server default).
            next_page_token (bytes, optional): Token for pagination.
                Defaults to None (first page).

        Returns:
            WorkflowListResponse: List of workflow executions with pagination info.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def describe_workflow(self, workflow_id: str, run_id: str | None = None) -> "WorkflowDescription":
        """Get detailed information about a workflow execution.

        Args:
            workflow_id (str): The unique identifier of the workflow execution.
            run_id (str, optional): The specific run identifier within the workflow.
                If None, describes the latest run. Defaults to None.

        Returns:
            WorkflowDescription: Detailed workflow execution information.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Close the Temporal client connection.

        Performs cleanup of resources and closes the connection to the Temporal server.
        Should be called when the adapter is no longer needed.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def create_schedule(
        self,
        schedule_id: str,
        workflow_class: Any,
        spec: "ScheduleSpec",
        task_queue: str,
    ) -> None:
        """Create a new schedule."""
        raise NotImplementedError

    @abstractmethod
    async def stop_schedule(self, schedule_id: str) -> None:
        """Stop a schedule."""
        raise NotImplementedError


class WorkerPort:
    """Interface for Temporal worker operations providing a standardized access pattern.

    This interface defines the contract for Temporal worker management, ensuring consistent
    implementation of worker lifecycle operations. Workers are responsible for executing
    workflows and activities.

    Implementing classes should provide concrete implementations for all
    methods, typically by wrapping a Temporal worker.
    """

    @abstractmethod
    async def start_worker(
        self,
        task_queue: str,
        workflows: list[type] | None = None,
        activities: list[object] | None = None,
        build_id: str | None = None,
        identity: str | None = None,
        max_concurrent_workflow_tasks: int | None = None,
        max_concurrent_activities: int | None = None,
    ) -> "WorkerHandle":
        """Start a Temporal worker for the specified task queue.

        Args:
            task_queue (str): The task queue this worker will poll from.
            workflows (list[type], optional): List of workflow classes to register.
                Defaults to None.
            activities (list[object], optional): List of activity instances to register.
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
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def stop_worker(self, worker_handle: "WorkerHandle") -> None:
        """Stop a running Temporal worker.

        Args:
            worker_handle (WorkerHandle): Handle to the worker to stop.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError

    @abstractmethod
    async def shutdown_all_workers(self) -> None:
        """Shutdown all workers managed by this port.

        Performs graceful shutdown of all active workers, waiting for current
        tasks to complete before terminating.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError


# Type stubs for forward references
class WorkflowHandle:
    """Type stub for workflow handle."""

    pass


class WorkflowListResponse:
    """Type stub for workflow list response."""

    pass


class WorkflowDescription:
    """Type stub for workflow description."""

    pass


class WorkerHandle:
    """Type stub for worker handle."""

    pass
