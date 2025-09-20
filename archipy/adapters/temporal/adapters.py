"""Temporal adapter implementation for workflow orchestration.

This module provides concrete implementations of the Temporal port interfaces,
integrating with the Temporal workflow engine while following ArchiPy patterns
and conventions.
"""

from collections.abc import Callable
from datetime import timedelta
from typing import Any, TypeVar, override
from uuid import uuid4

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleSpec,
    TLSConfig,
    WorkflowHandle,
)
from temporalio.common import RetryPolicy

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import TemporalConfig
from archipy.models.errors import InvalidArgumentError
from archipy.models.errors.base_error import BaseError

from .ports import TemporalPort

T = TypeVar("T")


class TemporalAdapter(TemporalPort):
    """Temporal workflow adapter implementing the TemporalPort interface.

    This adapter provides a standardized interface for interacting with Temporal
    workflow orchestration services, following ArchiPy architecture patterns.
    It handles client connections, TLS configuration, and workflow lifecycle
    management.

    Args:
        temporal_config (TemporalConfig, optional): Configuration settings for Temporal.
            If None, retrieves from global config. Defaults to None.
    """

    def __init__(self, temporal_config: TemporalConfig | None = None) -> None:
        """Initialize the TemporalAdapter with configuration settings.

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
        self._client: Client | None = None

    async def get_client(self) -> Client:
        """Get or create the Temporal client connection.

        Returns:
            Client: The Temporal client instance.

        Raises:
            ConnectionError: If unable to connect to Temporal server.
        """
        if self._client is None:
            try:
                tls_config = self._build_tls_config() if self._has_tls_config() else None

                self._client = await Client.connect(
                    f"{self.config.HOST}:{self.config.PORT}",
                    namespace=self.config.NAMESPACE,
                    tls=tls_config,
                )
            except Exception as error:
                raise BaseError(
                    additional_data={
                        "server": f"{self.config.HOST}:{self.config.PORT}",
                        "namespace": self.config.NAMESPACE,
                        "original_error": str(error),
                    },
                ) from error

        return self._client

    def _has_tls_config(self) -> bool:
        """Check if TLS configuration is provided.

        Returns:
            bool: True if TLS configuration is complete, False otherwise.
        """
        return all(
            [
                self.config.TLS_CA_CERT,
                self.config.TLS_CLIENT_CERT,
                self.config.TLS_CLIENT_KEY,
            ],
        )

    def _build_tls_config(self) -> TLSConfig:
        """Build TLS configuration for secure connections.

        Returns:
            TLSConfig: The TLS configuration object.

        Raises:
            InvalidArgumentError: If TLS configuration is incomplete.
        """
        if not self._has_tls_config():
            raise InvalidArgumentError(
                additional_data={
                    "ca_cert": bool(self.config.TLS_CA_CERT),
                    "client_cert": bool(self.config.TLS_CLIENT_CERT),
                    "client_key": bool(self.config.TLS_CLIENT_KEY),
                },
            )

        try:
            with open(self.config.TLS_CA_CERT, "rb") as f:
                ca_cert_data = f.read()

            client_cert_data = None
            client_key_data = None

            if self.config.TLS_CLIENT_CERT:
                with open(self.config.TLS_CLIENT_CERT, "rb") as f:
                    client_cert_data = f.read()

            if self.config.TLS_CLIENT_KEY:
                with open(self.config.TLS_CLIENT_KEY, "rb") as f:
                    client_key_data = f.read()

            return TLSConfig(
                server_root_ca_cert=ca_cert_data,
                client_cert=client_cert_data,
                client_private_key=client_key_data,
            )
        except OSError as error:
            raise InvalidArgumentError(additional_data={"original_error": str(error)}) from error

    def _build_retry_policy(self) -> RetryPolicy:
        """Build default retry policy from configuration.

        Returns:
            RetryPolicy: The configured retry policy.
        """
        return RetryPolicy(
            maximum_attempts=self.config.RETRY_MAXIMUM_ATTEMPTS,
            backoff_coefficient=self.config.RETRY_BACKOFF_COEFFICIENT,
            maximum_interval=timedelta(seconds=self.config.RETRY_MAXIMUM_INTERVAL),
        )

    @override
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
    ) -> WorkflowHandle[T, Any]:
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
        """
        client = await self.get_client()

        workflow_id = workflow_id or str(uuid4())
        task_queue = task_queue or self.config.TASK_QUEUE

        return await client.start_workflow(
            workflow,
            arg,
            id=workflow_id,
            task_queue=task_queue,
            execution_timeout=timedelta(seconds=execution_timeout or self.config.WORKFLOW_EXECUTION_TIMEOUT),
            run_timeout=timedelta(seconds=run_timeout or self.config.WORKFLOW_RUN_TIMEOUT),
            task_timeout=timedelta(seconds=task_timeout or self.config.WORKFLOW_TASK_TIMEOUT),
            retry_policy=self._build_retry_policy(),
            memo=memo,
            search_attributes=search_attributes,
        )

    @override
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
        """
        client = await self.get_client()

        workflow_id = workflow_id or str(uuid4())
        task_queue = task_queue or self.config.TASK_QUEUE

        return await client.execute_workflow(
            workflow,
            arg,
            id=workflow_id,
            task_queue=task_queue,
            execution_timeout=timedelta(seconds=execution_timeout or self.config.WORKFLOW_EXECUTION_TIMEOUT),
            run_timeout=timedelta(seconds=run_timeout or self.config.WORKFLOW_RUN_TIMEOUT),
            task_timeout=timedelta(seconds=task_timeout or self.config.WORKFLOW_TASK_TIMEOUT),
            retry_policy=self._build_retry_policy(),
        )

    @override
    async def get_workflow_handle(self, workflow_id: str, run_id: str | None = None) -> WorkflowHandle[T, Any]:
        """Get a handle to an existing workflow execution.

        Args:
            workflow_id (str): The unique identifier of the workflow execution.
            run_id (str, optional): The specific run identifier within the workflow.
                If None, gets the latest run. Defaults to None.

        Returns:
            WorkflowHandle[T, Any]: Handle to the workflow execution.
        """
        client = await self.get_client()
        return client.get_workflow_handle(workflow_id, run_id=run_id)

    @override
    async def cancel_workflow(self, workflow_id: str, run_id: str | None = None, reason: str | None = None) -> None:
        """Cancel a running workflow execution.

        Args:
            workflow_id (str): The unique identifier of the workflow execution.
            run_id (str, optional): The specific run identifier within the workflow.
                If None, cancels the latest run. Defaults to None.
            reason (str, optional): Reason for cancellation. Defaults to None.
        """
        handle = await self.get_workflow_handle(workflow_id, run_id)
        await handle.cancel()

    @override
    async def terminate_workflow(self, workflow_id: str, run_id: str | None = None, reason: str | None = None) -> None:
        """Terminate a running workflow execution immediately.

        Args:
            workflow_id (str): The unique identifier of the workflow execution.
            run_id (str, optional): The specific run identifier within the workflow.
                If None, terminates the latest run. Defaults to None.
            reason (str, optional): Reason for termination. Defaults to None.
        """
        handle = await self.get_workflow_handle(workflow_id, run_id)
        await handle.terminate(reason=reason)

    @override
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
        """
        handle = await self.get_workflow_handle(workflow_id, run_id)
        await handle.signal(signal_name, arg)

    @override
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
        """
        handle = await self.get_workflow_handle(workflow_id, run_id)
        return await handle.query(query_name, arg)

    @override
    async def list_workflows(
        self,
        query: str | None = None,
        page_size: int | None = None,
        next_page_token: bytes | None = None,
    ) -> Any:
        """List workflow executions matching the given criteria.

        Args:
            query (str, optional): List filter query in Temporal SQL syntax.
                Defaults to None (no filter).
            page_size (int, optional): Maximum number of results per page.
                Defaults to None (server default).
            next_page_token (bytes, optional): Token for pagination.
                Defaults to None (first page).

        Returns:
            Any: List of workflow executions with pagination info.
        """
        client = await self.get_client()
        # list_workflows returns an async iterator, not awaitable
        workflows_iter = client.list_workflows(
            query=query,
            page_size=page_size or 100,
            next_page_token=next_page_token,
        )
        # Convert to list for compatibility
        workflows = []
        async for workflow in workflows_iter:
            workflows.append(workflow)
        return workflows

    @override
    async def describe_workflow(self, workflow_id: str, run_id: str | None = None) -> Any:
        """Get detailed information about a workflow execution.

        Args:
            workflow_id (str): The unique identifier of the workflow execution.
            run_id (str, optional): The specific run identifier within the workflow.
                If None, describes the latest run. Defaults to None.

        Returns:
            Any: Detailed workflow execution information.
        """
        handle = await self.get_workflow_handle(workflow_id, run_id)
        return await handle.describe()

    @override
    async def close(self) -> None:
        """Close the Temporal client connection.

        Performs cleanup of resources and closes the connection to the Temporal server.
        Should be called when the adapter is no longer needed.
        """
        if self._client:
            # Temporal client doesn't have a close method, just clear the reference
            self._client = None

    @override
    async def create_schedule(self, schedule_id: str, workflow_class: Any, spec: ScheduleSpec, task_queue: str) -> None:
        """Create a schedule for a workflow."""
        client = await self.get_client()

        sched = Schedule(
            action=ScheduleActionStartWorkflow(
                workflow_class,
                id=schedule_id,
                task_queue=task_queue,
            ),
            spec=spec,
        )

        await client.create_schedule(schedule_id, sched)

    @override
    async def stop_schedule(self, schedule_id: str) -> None:
        """Stop a schedule."""
        client = await self.get_client()
        handle = client.get_schedule_handle(schedule_id)
        await handle.delete()
