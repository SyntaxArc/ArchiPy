"""Base classes for Temporal workflows and activities.

This module provides base classes and utilities for implementing Temporal workflows
and activities within the ArchiPy architecture, including integration with existing
adapters and standardized patterns.
"""

from abc import abstractmethod
from collections.abc import Callable
from datetime import timedelta
from typing import Any, TypeVar

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

# Type imports for generic base classes

T = TypeVar("T")
R = TypeVar("R")


class BaseWorkflow[T, R]:
    """Base class for all Temporal workflows in ArchiPy.

    Provides common functionality and patterns for workflow implementations,
    including standardized logging, error handling, and integration with
    ArchiPy services through activities.

    Type Parameters:
        T: Type of the workflow input parameter.
        R: Type of the workflow return value.
    """

    @workflow.run
    async def run(self, workflow_input: T) -> R:
        """Main workflow execution method.

        This method must be implemented by concrete workflow classes to define
        the workflow logic. It should orchestrate activities and child workflows
        to accomplish the business process.

        Args:
            workflow_input (T): The input data for the workflow.

        Returns:
            R: The result of the workflow execution.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError("Workflow must implement run method")

    async def _execute_activity_with_retry(
        self,
        activity_func: Any,
        arg: Any,
        start_to_close_timeout: timedelta | None = None,
        heartbeat_timeout: timedelta | None = None,
        retry_policy: RetryPolicy | None = None,
        task_queue: str | None = None,
    ) -> Any:
        """Execute an activity with standardized retry configuration.

        Args:
            activity_func (Any): The activity function to execute.
            arg (Any): Argument to pass to the activity.
            start_to_close_timeout (timedelta): Maximum execution time for the activity.
                Defaults to 30 seconds.
            heartbeat_timeout (timedelta, optional): Heartbeat timeout for long-running activities.
                Defaults to None.
            retry_policy (RetryPolicy, optional): Custom retry policy.
                If None, uses default retry policy. Defaults to None.
            task_queue (str, optional): Task queue for activity execution.
                If None, uses workflow's task queue. Defaults to None.

        Returns:
            Any: The result of the activity execution.
        """
        # Get temporal config for default values
        from archipy.configs.base_config import BaseConfig

        temporal_config = BaseConfig.global_config().TEMPORAL

        # Use config defaults if not provided
        if start_to_close_timeout is None:
            start_to_close_timeout = timedelta(seconds=temporal_config.ACTIVITY_START_TO_CLOSE_TIMEOUT)
        if heartbeat_timeout is None:
            heartbeat_timeout = timedelta(seconds=temporal_config.ACTIVITY_HEARTBEAT_TIMEOUT)
        if retry_policy is None:
            retry_policy = RetryPolicy(
                maximum_attempts=temporal_config.RETRY_MAXIMUM_ATTEMPTS,
                backoff_coefficient=temporal_config.RETRY_BACKOFF_COEFFICIENT,
                maximum_interval=timedelta(seconds=temporal_config.RETRY_MAXIMUM_INTERVAL),
            )

        return await workflow.execute_activity(
            activity_func,
            arg,
            start_to_close_timeout=start_to_close_timeout,
            heartbeat_timeout=heartbeat_timeout,
            retry_policy=retry_policy,
            task_queue=task_queue or temporal_config.TASK_QUEUE,
        )

    async def _execute_child_workflow(
        self,
        child_workflow: Any,
        arg: Any,
        workflow_id: str | None = None,
        task_queue: str | None = None,
        execution_timeout: timedelta | None = None,
    ) -> Any:
        """Execute a child workflow with standardized configuration.

        Args:
            child_workflow (Any): The child workflow function to execute.
            arg (Any): Argument to pass to the child workflow.
            workflow_id (str, optional): Unique ID for the child workflow.
                If None, auto-generated. Defaults to None.
            task_queue (str, optional): Task queue for child workflow execution.
                If None, uses parent workflow's task queue. Defaults to None.
            execution_timeout (timedelta, optional): Maximum execution time for the child workflow.
                If None, uses default timeout. Defaults to None.

        Returns:
            Any: The result of the child workflow execution.
        """
        # Get temporal config for default values
        from archipy.configs.base_config import BaseConfig

        temporal_config = BaseConfig.global_config().TEMPORAL

        # Use config defaults if not provided
        if execution_timeout is None:
            execution_timeout = timedelta(seconds=temporal_config.WORKFLOW_EXECUTION_TIMEOUT)

        return await workflow.execute_child_workflow(
            child_workflow,
            arg,
            id=workflow_id,
            task_queue=task_queue or temporal_config.TASK_QUEUE,
            execution_timeout=execution_timeout,
        )

    def _log_workflow_event(self, event: str, details: dict[str, Any] | None = None) -> None:
        """Log workflow events with consistent formatting.

        Args:
            event (str): The event description.
            details (dict[str, Any], optional): Additional event details.
                Defaults to None.
        """
        log_data = {
            "workflow_id": workflow.info().workflow_id,
            "workflow_type": workflow.info().workflow_type,
            "event": event,
        }

        if details:
            log_data.update(details)

        workflow.logger.info("Workflow event", extra=log_data)


class BaseActivity[T, R]:
    """Base class for all Temporal activities in ArchiPy.

    Provides common functionality for activity implementations, including
    integration with your logic layer, standardized error handling, and
    execution hooks for cross-cutting concerns.

    Type Parameters:
        T: Type of the activity input parameter.
        R: Type of the activity return value.
    """

    def __init__(self, logic: Any | None = None) -> None:
        """Initialize the activity with a logic instance.

        Args:
            logic (Any, optional): Your business logic instance (object) that contains
                a repository with access to adapters. If None, subclass should override _get_logic().
                Defaults to None.
        """
        self._logic = logic

    def _get_logic(self) -> Any:
        """Get the logic instance for this activity.

        Override this method in subclasses to provide your specific logic instance,
        or pass it via constructor using dependency injection. Your logic instance
        should have a repository that manages adapter access.

        Returns:
            Any: Your business logic instance.

        Raises:
            NotImplementedError: If not implemented by the subclass and no logic provided.
        """
        if self._logic is not None:
            return self._logic
        raise NotImplementedError("Activity must provide a logic instance via constructor or override _get_logic()")

    @activity.defn
    async def execute(self, activity_input: T) -> R:
        """Main activity execution method with hooks.

        This method provides a template for activity execution with pre/post hooks
        for common concerns like caching, validation, and monitoring.

        Args:
            activity_input (T): The input data for the activity.

        Returns:
            R: The result of the activity execution.

        Raises:
            Exception: Any exception that occurs during activity execution.
        """
        try:
            # Pre-execution hook
            await self._before_execute(activity_input)

            # Check cache if enabled
            if self._is_cacheable():
                cache_key = self._get_cache_key(activity_input)
                cached_result = await self._get_from_cache(cache_key)
                if cached_result is not None:
                    activity.logger.info("Using cached result", extra={"cache_key": cache_key})
                    return cached_result

            # Main business logic execution
            result = await self._do_execute(activity_input)

            # Cache result if enabled
            if self._is_cacheable() and result is not None:
                cache_key = self._get_cache_key(activity_input)
                await self._store_in_cache(cache_key, result)

            # Post-execution hook
            await self._after_execute(activity_input, result)

            return result

        except Exception as error:
            await self._handle_error(activity_input, error)
            raise

    @abstractmethod
    async def _do_execute(self, activity_input: T) -> R:
        """Execute the main activity business logic.

        This method must be implemented by concrete activity classes to define
        the specific business logic for the activity.

        Args:
            activity_input (T): The input data for the activity.

        Returns:
            R: The result of the activity execution.

        Raises:
            NotImplementedError: If not implemented by the subclass.
        """
        raise NotImplementedError("Activity must implement _do_execute method")

    async def _before_execute(self, activity_input: T) -> None:
        """Pre-execution hook for common setup tasks.

        Override this method to perform tasks before the main activity logic,
        such as validation, setup, or preparation.

        Args:
            activity_input (T): The input data for the activity.
        """
        self._log_activity_event("execution_started", {"input_type": type(activity_input).__name__})

    async def _after_execute(self, activity_input: T, result: R) -> None:
        """Post-execution hook for cleanup and monitoring.

        Override this method to perform tasks after successful activity execution,
        such as cleanup, metrics emission, or notifications.

        Args:
            activity_input (T): The input data that was processed.
            result (R): The result of the activity execution.
        """
        self._log_activity_event(
            "execution_completed",
            {
                "input_type": type(activity_input).__name__,
                "result_type": type(result).__name__,
            },
        )

    async def _handle_error(self, activity_input: T, error: Exception) -> None:
        """Handle activity execution errors.

        Override this method to implement custom error handling logic,
        such as error reporting, cleanup, or compensation actions.

        Args:
            activity_input (T): The input data that was being processed.
            error (Exception): The exception that occurred.
        """
        self._log_activity_event(
            "execution_failed",
            {
                "input_type": type(activity_input).__name__,
                "error_type": type(error).__name__,
                "error_message": str(error),
            },
        )

    def _is_cacheable(self) -> bool:
        """Determine if this activity's results should be cached.

        Override this method to enable caching for specific activities.

        Returns:
            bool: True if results should be cached, False otherwise.
        """
        return False

    def _get_cache_key(self, activity_input: T) -> str:
        """Generate a cache key for the given input.

        Override this method to customize cache key generation for activities
        that support caching.

        Args:
            activity_input (T): The activity input data.

        Returns:
            str: The cache key for storing/retrieving results.
        """
        return f"{self.__class__.__name__}:{hash(str(activity_input))}"

    async def _get_from_cache(self, cache_key: str) -> R | None:
        """Retrieve a result from cache using your logic instance.

        Override this method to implement caching using your repository pattern.
        By default, this returns None (no caching).

        Args:
            cache_key (str): The cache key to look up.

        Returns:
            R | None: The cached result if found, None otherwise.
        """
        # Override this method to use your logic instance's repository
        return None

    async def _store_in_cache(self, cache_key: str, result: R, ttl: int = 3600) -> None:
        """Store a result in cache using your logic instance.

        Override this method to implement caching using your repository pattern.
        By default, this does nothing.

        Args:
            cache_key (str): The cache key for storage.
            result (R): The result to cache.
            ttl (int): Time-to-live in seconds. Defaults to 3600 (1 hour).
        """
        # Override this method to use your logic instance's repository
        pass

    def _log_activity_event(self, event: str, details: dict[str, Any] | None = None) -> None:
        """Log activity events with consistent formatting.

        Args:
            event (str): The event description.
            details (dict[str, Any], optional): Additional event details.
                Defaults to None.
        """
        log_data = {
            "activity_type": self.__class__.__name__,
            "event": event,
        }

        if details:
            log_data.update(details)

        activity.logger.info("Activity event", extra=log_data)


class LogicIntegratedActivity(BaseActivity[T, R]):
    """Activity base class that enforces the logic layer pattern.

    This class provides helper methods that delegate to your logic instance,
    ensuring all business operations go through your established architecture
    with a single repository managing adapter access.
    """

    async def _execute_with_logic(self, operation_func: str, *args: Any, **kwargs: Any) -> Any:
        """Execute an operation using your logic instance.

        This is a convenience method to call methods on your logic instance.

        Args:
            operation_func (str): The name of the method to call on your logic instance.
            *args (Any): Arguments to pass to the logic method.
            **kwargs (Any): Keyword arguments to pass to the logic method.

        Returns:
            Any: Result of the logic operation.

        Example:
            # Call logic.get_user_by_id(user_id)
            user = await self._execute_with_logic("get_user_by_id", user_id)
        """
        logic = self._get_logic()
        method = getattr(logic, operation_func)
        return await method(*args, **kwargs)

    async def _execute_with_atomic(self, operation_func: str, *args: Any, **kwargs: Any) -> Any:
        """Execute an operation using your logic instance method decorated with @atomic.

        This method assumes your logic methods are decorated with atomic decorators
        for transaction management.

        Args:
            operation_func (str): The name of the method to call on your logic instance.
                This method should be decorated with @atomic for transaction support.
            *args (Any): Arguments to pass to the logic method.
            **kwargs (Any): Keyword arguments to pass to the logic method.

        Returns:
            Any: Result of the atomic operation.

        Example:
            # Call logic.process_order(order_data) - method decorated with @atomic
            result = await self._execute_with_atomic("process_order", order_data)
        """
        logic = self._get_logic()
        method = getattr(logic, operation_func)
        # Method should be decorated with @atomic, so transaction is handled automatically
        return await method(*args, **kwargs)

    async def _call_atomic_method(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """Call an atomic method directly on your logic instance.

        This is an alias for _execute_with_atomic for clearer semantic meaning.

        Args:
            method_name (str): The name of the atomic method to call.
            *args (Any): Arguments to pass to the method.
            **kwargs (Any): Keyword arguments to pass to the method.

        Returns:
            Any: Result of the atomic method call.

        Example:
            # Direct call to @atomic decorated method
            result = await self._call_atomic_method("create_order_with_payment", order_data)
        """
        return await self._execute_with_atomic(method_name, *args, **kwargs)


class AtomicActivity(BaseActivity[T, R]):
    """Activity base class with built-in atomic transaction support.

    This class extends BaseActivity to provide direct atomic transaction support
    within activity execution, ensuring database consistency during activity operations.

    Args:
        logic (Any, optional): Business logic instance with repository access. Defaults to None.
        db_type (str, optional): Database type for atomic operations. Defaults to "postgres".
    """

    def __init__(self, logic: Any | None = None, db_type: str = "postgres") -> None:
        """Initialize the atomic activity.

        Args:
            logic (Any, optional): Business logic instance. Defaults to None.
            db_type (str): Database type ("postgres", "sqlite", "starrocks"). Defaults to "postgres".

        Raises:
            ValueError: If an invalid db_type is provided.
        """
        super().__init__(logic)
        if db_type not in ("postgres", "sqlite", "starrocks"):
            raise ValueError(f"Invalid db_type: {db_type}. Must be one of: postgres, sqlite, starrocks")
        self.db_type = db_type

    def _get_atomic_decorator(self) -> Callable[..., Any]:
        """Get the appropriate async atomic decorator for the configured database type.

        Returns:
            Callable: The async atomic decorator function for the configured database.

        Raises:
            ImportError: If SQLAlchemy is not installed and atomic decorators are needed.
        """
        # Lazy import to avoid requiring SQLAlchemy when using temporalio without sqlalchemy extra
        from archipy.helpers.decorators import (
            async_postgres_sqlalchemy_atomic_decorator,
            async_sqlite_sqlalchemy_atomic_decorator,
            async_starrocks_sqlalchemy_atomic_decorator,
        )

        decorators_map = {
            "postgres": async_postgres_sqlalchemy_atomic_decorator,
            "sqlite": async_sqlite_sqlalchemy_atomic_decorator,
            "starrocks": async_starrocks_sqlalchemy_atomic_decorator,
        }
        return decorators_map[self.db_type]

    @activity.defn
    async def execute_atomic(self, activity_input: T) -> R:
        """Execute the activity within a database transaction.

        This method wraps the entire activity execution (including pre/post hooks)
        within a database transaction, ensuring atomicity of all database operations.

        Args:
            activity_input (T): The input data for the activity.

        Returns:
            R: The result of the activity execution.

        Raises:
            Exception: Any exception that occurs during activity execution.
        """
        atomic_decorator = self._get_atomic_decorator()

        @atomic_decorator
        async def _atomic_execute() -> R:
            return await super(AtomicActivity, self).execute(activity_input)

        return await _atomic_execute()

    async def _do_execute_atomic(self, activity_input: T) -> R:
        """Execute main business logic within a database transaction.

        This method provides atomic transaction support for the core business logic only,
        excluding pre/post hooks from the transaction scope.

        Args:
            activity_input (T): The input data for the activity.

        Returns:
            R: The result of the business logic execution.
        """
        atomic_decorator = self._get_atomic_decorator()

        @atomic_decorator
        async def _atomic_do_execute() -> R:
            return await self._do_execute(activity_input)

        return await _atomic_do_execute()

    async def execute_custom_atomic_operation(self, operation: Callable[[], Any]) -> Any:
        """Execute a custom operation within a database transaction.

        This utility method allows executing custom logic within the activity's
        configured atomic transaction context.

        Args:
            operation (Callable[[], T]): The operation to execute atomically.

        Returns:
            Any: The result of the operation.

        Example:
            ```python
            async def custom_logic():
                # Custom database operations
                return await some_database_work()

            result = await self.execute_custom_atomic_operation(custom_logic)
            ```
        """
        atomic_decorator = self._get_atomic_decorator()

        @atomic_decorator
        async def _execute_operation() -> Any:
            return await operation()

        return await _execute_operation()

    def with_db_type(self, db_type: str) -> "AtomicActivity[T, R]":
        """Create a new instance with a different database type.

        Args:
            db_type (str): The new database type ("postgres", "sqlite", or "starrocks").

        Returns:
            AtomicActivity[T, R]: New activity instance with the specified database type.

        Raises:
            ValueError: If an invalid db_type is provided.
        """
        # Cannot return concrete type due to abstract method
        raise NotImplementedError("AtomicActivity cannot be instantiated directly")
