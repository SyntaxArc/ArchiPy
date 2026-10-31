"""Temporal adapter implementation for workflow orchestration.

This module provides concrete implementations of the Temporal port interfaces,
integrating with the Temporal workflow engine while following ArchiPy patterns
and conventions.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import warnings
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, override
from uuid import uuid4

from temporalio.client import (
    Client,
    KeepAliveConfig,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleOverlapPolicy,
    SchedulePolicy,
    ScheduleSpec,
    ScheduleUpdate,
    TLSConfig,
    WorkflowExecution,
    WorkflowExecutionAsyncIterator,
    WorkflowExecutionDescription,
    WorkflowHandle,
)
from temporalio.common import RetryPolicy
from temporalio.contrib.opentelemetry import ReplaySafeTracerProvider
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.service import RetryConfig, RPCError, RPCStatusCode

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import OtelMetricsExporter
from archipy.models.errors import (
    AlreadyExistsError,
    DeadlineExceededError,
    InvalidArgumentError,
    NotFoundError,
    UnavailableError,
)
from archipy.models.errors.temporal_errors import TemporalError, WorkerConnectionError

from .ports import TemporalPort
from .runtime import TemporalRuntimeManager

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Sequence

    from temporalio.client import (
        Interceptor,
        ScheduleDescription,
        ScheduleHandle,
        ScheduleListDescription,
        ScheduleUpdateInput,
    )
    from temporalio.common import WorkflowIDConflictPolicy, WorkflowIDReusePolicy
    from temporalio.converter import DataConverter
    from temporalio.runtime import Runtime

    from archipy.configs.config_template import OpentelemetryConfig, TemporalConfig
    from archipy.models.errors.base_error import BaseError

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

    def __init__(
        self,
        temporal_config: TemporalConfig | None = None,
        data_converter: DataConverter | None = None,
        interceptors: Sequence[Interceptor] | None = None,
    ) -> None:
        """Initialize the TemporalAdapter with configuration settings.

        Args:
            temporal_config (TemporalConfig, optional): Configuration settings for Temporal.
                If None, retrieves from global config. Defaults to None.
            data_converter (DataConverter, optional): Data converter for payloads, e.g.
                ``dataclasses.replace(pydantic_data_converter, payload_codec=MyCodec())`` to encrypt or compress them.
                If None, the Pydantic converter is used when ``PYDANTIC_DATA_CONVERTER`` is enabled. Defaults to None.
            interceptors (Sequence[Interceptor], optional): Client interceptors. Those that also implement
                ``temporalio.worker.Interceptor`` apply to workers created from this client. Defaults to None.
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
        self._data_converter = data_converter
        self._interceptors = list(interceptors or [])
        self._client: Client | None = None
        self._client_lock = asyncio.Lock()

    async def get_client(self) -> Client:
        """Get or create the Temporal client connection.

        Returns:
            Client: The Temporal client instance.

        Raises:
            ConnectionError: If unable to connect to Temporal server.
        """
        if self._client is not None:
            return self._client
        # Concurrent first calls must share one connection.
        async with self._client_lock:
            if self._client is None:
                self._client = await self._connect()
        return self._client

    async def _connect(self) -> Client:
        """Connect a new Temporal client from the configuration.

        Returns:
            Client: The connected client.

        Raises:
            BaseError: If unable to connect to the Temporal server.
        """
        try:
            return await Client.connect(f"{self.config.HOST}:{self.config.PORT}", **self._build_connect_kwargs())
        except Exception as error:
            raise WorkerConnectionError(
                additional_data={
                    "server": f"{self.config.HOST}:{self.config.PORT}",
                    "namespace": self.config.NAMESPACE,
                    "original_error": str(error),
                },
            ) from error

    def _optional_connect_kwargs(self) -> dict[str, Any]:
        """Build the ``Client.connect`` keyword arguments that are only passed when configured.

        Returns:
            dict[str, Any]: The configured optional connection keyword arguments.
        """
        optional: dict[str, Any] = {}
        data_converter = self._data_converter
        if data_converter is None and self.config.PYDANTIC_DATA_CONVERTER:
            data_converter = pydantic_data_converter
        if data_converter is not None:
            optional["data_converter"] = data_converter
        if self._interceptors:
            optional["interceptors"] = self._interceptors
        if self.config.CLIENT_IDENTITY is not None:
            optional["identity"] = self.config.CLIENT_IDENTITY
        if self.config.API_KEY is not None:
            optional["api_key"] = self.config.API_KEY
        if self.config.RPC_METADATA:
            optional["rpc_metadata"] = self.config.RPC_METADATA
        tls = self._tls_option()
        if tls is not None:
            optional["tls"] = tls
        return optional

    def _build_connect_kwargs(self) -> dict[str, Any]:
        """Build the ``Client.connect`` keyword arguments, only including optional settings when configured.

        Returns:
            dict[str, Any]: The connection keyword arguments.
        """
        connect_kwargs: dict[str, Any] = {
            "namespace": self.config.NAMESPACE,
            "lazy": self.config.LAZY_CONNECT,
            "keep_alive_config": KeepAliveConfig(
                interval_millis=self.config.KEEP_ALIVE_INTERVAL_MS,
                timeout_millis=self.config.KEEP_ALIVE_TIMEOUT_MS,
            ),
            "retry_config": RetryConfig(
                initial_interval_millis=self.config.CLIENT_RPC_RETRY_INITIAL_INTERVAL_MS,
                max_interval_millis=self.config.CLIENT_RPC_RETRY_MAX_INTERVAL_MS,
                max_retries=self.config.CLIENT_RPC_RETRY_MAX_RETRIES,
            ),
        }
        connect_kwargs.update(self._optional_connect_kwargs())

        # Configure Runtime with OTLP metrics if Temporal + OTel metrics are enabled
        global_config = BaseConfig.global_config()
        otel = global_config.OTEL
        if self.config.ENABLE_METRICS and otel.IS_ENABLED and otel.METRICS_ENABLED:
            runtime = self._build_metrics_runtime(otel)
            if runtime is not None:
                connect_kwargs["runtime"] = runtime

        # Attach OTel tracing plugin when traces are enabled
        if otel.IS_ENABLED and otel.TRACES_ENABLED:
            from archipy.helpers.utils.otel_utils import OtelUtils

            OtelUtils.init_otel_if_needed(global_config)
            self._append_tracing_plugin(connect_kwargs)
        return connect_kwargs

    def _build_metrics_runtime(self, otel: OpentelemetryConfig) -> Runtime | None:
        """Build the Temporal Runtime that exports SDK metrics according to the OTel exporter mode.

        The Temporal SDK core can only export over OTLP or serve its own Prometheus scrape endpoint, so
        ``METRICS_EXPORTER=pull`` selects the scrape endpoint and every other mode uses OTLP.

        Args:
            otel: The global OpenTelemetry configuration.

        Returns:
            Runtime | None: The configured Runtime, or None when it could not be created.
        """
        from archipy.helpers.utils.otel_utils import OtelUtils

        otlp_endpoint = OtelUtils.resolve_metrics_endpoint(otel)
        prometheus_bind_address: str | None = None
        if otel.METRICS_EXPORTER == OtelMetricsExporter.PULL:
            prometheus_bind_address = f"{otel.METRICS_PULL_HOST}:{self.config.METRICS_PULL_PORT}"
        elif otel.METRICS_EXPORTER == OtelMetricsExporter.PUSHGATEWAY:
            logger.warning(
                "Temporal SDK metrics cannot be pushed to a Pushgateway; they are exported over OTLP to %s instead",
                otlp_endpoint,
            )

        return TemporalRuntimeManager().get_runtime(
            otel_metrics_enabled=True,
            otlp_endpoint=otlp_endpoint,
            headers=dict(otel.OTLP_HEADERS),
            use_http=(otel.PROTOCOL == "http/protobuf"),
            prometheus_bind_address=prometheus_bind_address,
            global_tags=self.config.METRICS_GLOBAL_TAGS,
            core_log_level=self.config.SDK_CORE_LOG_LEVEL,
        )

    @staticmethod
    def _append_tracing_plugin(connect_kwargs: dict[str, Any]) -> None:
        """Append ArchiPy's Temporal OpenTelemetry plugin without discarding existing plugins.

        Skipped with a warning when the global tracer provider is not replay-safe.

        Args:
            connect_kwargs: Keyword arguments passed to ``Client.connect``.
        """
        from archipy.adapters.temporal.tracing import MessagingOpenTelemetryPlugin
        from archipy.helpers.utils.otel_utils import OtelUtils

        # The plugin needs a replay-safe provider; ArchiPy builds one itself, but a provider another library
        # registered first is adopted as is, and workers with workflows would then fail to start.
        if not isinstance(OtelUtils.tracer_provider(), ReplaySafeTracerProvider):
            logger.warning(
                "Temporal tracing is disabled: the global TracerProvider is not a temporalio ReplaySafeTracerProvider",
            )
            return
        connect_kwargs.setdefault("plugins", []).append(MessagingOpenTelemetryPlugin())

    def _has_tls_config(self) -> bool:
        """Check if any TLS file or server name is configured.

        Returns:
            bool: True if a CA certificate, a client certificate pair or a server name is set.
        """
        return any(
            [
                self.config.TLS_CA_CERT,
                self.config.TLS_CLIENT_CERT,
                self.config.TLS_SERVER_NAME,
            ],
        )

    def _tls_option(self) -> TLSConfig | bool | None:
        """Resolve the ``tls`` argument of ``Client.connect``.

        Returns:
            TLSConfig | bool | None: A TLS configuration when TLS settings are present (unless TLS is forced off),
                the ``TLS_ENABLED`` flag otherwise, or None to let the SDK enable TLS when an API key is set.
        """
        if self.config.TLS_ENABLED is False:
            return False
        if self._has_tls_config():
            return self._build_tls_config()
        return self.config.TLS_ENABLED

    def _build_tls_config(self) -> TLSConfig:
        """Build TLS configuration for secure connections from the configured files.

        Server-only TLS needs just the CA certificate (or none, to use the system CA bundle); mutual TLS adds the
        client certificate and key.

        Returns:
            TLSConfig: The TLS configuration object.

        Raises:
            InvalidArgumentError: If a configured TLS file cannot be read.
        """
        try:
            return TLSConfig(
                server_root_ca_cert=self._read_tls_file(self.config.TLS_CA_CERT),
                client_cert=self._read_tls_file(self.config.TLS_CLIENT_CERT),
                client_private_key=self._read_tls_file(self.config.TLS_CLIENT_KEY),
                domain=self.config.TLS_SERVER_NAME,
            )
        except OSError as error:
            raise InvalidArgumentError(additional_data={"original_error": str(error)}) from error

    @staticmethod
    def _read_tls_file(path: str | None) -> bytes | None:
        """Read a TLS file when a path is configured.

        Args:
            path (str | None): The file path.

        Returns:
            bytes | None: The file contents, or None when no path is set.
        """
        return Path(path).read_bytes() if path else None

    @staticmethod
    def _timeout(override: int | None, default: int | None) -> timedelta | None:
        """Resolve a timeout in seconds from a call override and its configured default.

        Args:
            override (int | None): The timeout passed to the call.
            default (int | None): The configured timeout.

        Returns:
            timedelta | None: The timeout, or None when neither is set (unbounded).
        """
        seconds = override or default
        return timedelta(seconds=seconds) if seconds else None

    @contextlib.asynccontextmanager
    async def _mapped_errors(self, operation: str, resource_id: str | None) -> AsyncGenerator[None]:
        """Map Temporal client errors raised in the block to ArchiPy domain errors.

        Workflow failures (``WorkflowFailureError``) are left as is: they carry the workflow's own error.

        Args:
            operation (str): The adapter operation, for error context.
            resource_id (str | None): The workflow or schedule ID the operation targets.

        Yields:
            None: Control to the wrapped block.

        Raises:
            AlreadyExistsError: If the workflow or schedule ID is already in use.
            NotFoundError: If the workflow or schedule does not exist.
            UnavailableError: If the Temporal server is unreachable.
            DeadlineExceededError: If the call timed out.
            TemporalError: For any other Temporal RPC error.
        """
        try:
            yield
        except (WorkflowAlreadyStartedError, ScheduleAlreadyRunningError) as error:
            raise AlreadyExistsError(resource_type=operation, additional_data={"id": resource_id}) from error
        except RPCError as error:
            raise self._map_rpc_error(error, operation, resource_id) from error

    @staticmethod
    def _map_rpc_error(error: RPCError, operation: str, resource_id: str | None) -> BaseError:
        """Translate a Temporal RPC error into the matching ArchiPy error, without leaking the server message.

        Args:
            error (RPCError): The Temporal RPC error.
            operation (str): The adapter operation.
            resource_id (str | None): The workflow or schedule ID the operation targets.

        Returns:
            BaseError: The domain error to raise.
        """
        context = {"operation": operation, "id": resource_id, "status": error.status.name}
        match error.status:
            case RPCStatusCode.NOT_FOUND:
                return NotFoundError(resource_type=operation, additional_data=context)
            case RPCStatusCode.ALREADY_EXISTS:
                return AlreadyExistsError(resource_type=operation, additional_data=context)
            case RPCStatusCode.UNAVAILABLE:
                return UnavailableError(resource_type="temporal", additional_data=context)
            case RPCStatusCode.DEADLINE_EXCEEDED:
                return DeadlineExceededError(operation=operation, additional_data=context)
            case _:
                return TemporalError(additional_data=context)

    def _build_retry_policy(self) -> RetryPolicy:
        """Build default retry policy from configuration.

        Returns:
            RetryPolicy: The configured retry policy.
        """
        return RetryPolicy(
            initial_interval=timedelta(seconds=self.config.RETRY_INITIAL_INTERVAL),
            maximum_attempts=self.config.RETRY_MAXIMUM_ATTEMPTS,
            backoff_coefficient=self.config.RETRY_BACKOFF_COEFFICIENT,
            maximum_interval=timedelta(seconds=self.config.RETRY_MAXIMUM_INTERVAL),
            non_retryable_error_types=self.config.RETRY_NON_RETRYABLE_ERROR_TYPES,
        )

    def _build_workflow_retry_policy(self) -> RetryPolicy | None:
        """Build the workflow-level retry policy, only when enabled in configuration.

        A workflow retry reruns the whole workflow from the start, so it is opt-in.

        Returns:
            RetryPolicy | None: The configured retry policy, or None when workflow retries are disabled.
        """
        if not self.config.WORKFLOW_RETRY_ENABLED:
            return None
        return self._build_retry_policy()

    @staticmethod
    def _id_policies(
        id_reuse_policy: WorkflowIDReusePolicy | None,
        id_conflict_policy: WorkflowIDConflictPolicy | None,
    ) -> dict[str, Any]:
        """Build the workflow ID policy keyword arguments, leaving out unset ones so the SDK defaults apply.

        Args:
            id_reuse_policy (WorkflowIDReusePolicy | None): The ID reuse policy.
            id_conflict_policy (WorkflowIDConflictPolicy | None): The ID conflict policy.

        Returns:
            dict[str, Any]: The keyword arguments for ``start_workflow`` / ``execute_workflow``.
        """
        policies: dict[str, Any] = {}
        if id_reuse_policy is not None:
            policies["id_reuse_policy"] = id_reuse_policy
        if id_conflict_policy is not None:
            policies["id_conflict_policy"] = id_conflict_policy
        return policies

    @override
    async def start_workflow(
        self,
        workflow: str | Callable[..., Any],
        arg: Any = None,
        workflow_id: str | None = None,
        task_queue: str | None = None,
        execution_timeout: int | None = None,
        run_timeout: int | None = None,
        task_timeout: int | None = None,
        memo: dict[str, Any] | None = None,
        search_attributes: dict[str, Any] | None = None,
        id_reuse_policy: WorkflowIDReusePolicy | None = None,
        id_conflict_policy: WorkflowIDConflictPolicy | None = None,
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
            id_reuse_policy (WorkflowIDReusePolicy, optional): Whether a closed workflow's ID may be reused.
                Defaults to None (server default: allow duplicate).
            id_conflict_policy (WorkflowIDConflictPolicy, optional): What to do when a workflow with the same ID
                is still running, e.g. ``USE_EXISTING`` for idempotent starts. Defaults to None (server default: fail).

        Returns:
            WorkflowHandle[T, Any]: Handle to the started workflow execution.
        """
        async with self._mapped_errors("start_workflow", workflow_id):
            client = await self.get_client()

            workflow_id = workflow_id or str(uuid4())
            task_queue = task_queue or self.config.TASK_QUEUE

            # Build positional args: only include arg if it's not None,
            # so workflows that take no parameters aren't given an extra argument.
            positional_args: list[Any] = [] if arg is None else [arg]

            return await client.start_workflow(
                workflow,
                *positional_args,
                id=workflow_id,
                task_queue=task_queue,
                execution_timeout=self._timeout(execution_timeout, self.config.WORKFLOW_EXECUTION_TIMEOUT),
                run_timeout=self._timeout(run_timeout, self.config.WORKFLOW_RUN_TIMEOUT),
                task_timeout=self._timeout(task_timeout, self.config.WORKFLOW_TASK_TIMEOUT),
                retry_policy=self._build_workflow_retry_policy(),
                memo=memo,
                search_attributes=search_attributes,
                **self._id_policies(id_reuse_policy, id_conflict_policy),
            )

    @override
    async def execute_workflow(
        self,
        workflow: str | Callable[..., Any],
        arg: Any = None,
        workflow_id: str | None = None,
        task_queue: str | None = None,
        execution_timeout: int | None = None,
        run_timeout: int | None = None,
        task_timeout: int | None = None,
        id_reuse_policy: WorkflowIDReusePolicy | None = None,
        id_conflict_policy: WorkflowIDConflictPolicy | None = None,
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
            id_reuse_policy (WorkflowIDReusePolicy, optional): Whether a closed workflow's ID may be reused.
                Defaults to None (server default: allow duplicate).
            id_conflict_policy (WorkflowIDConflictPolicy, optional): What to do when a workflow with the same ID
                is still running, e.g. ``USE_EXISTING`` for idempotent starts. Defaults to None (server default: fail).

        Returns:
            T: The workflow execution result.
        """
        async with self._mapped_errors("execute_workflow", workflow_id):
            client = await self.get_client()

            workflow_id = workflow_id or str(uuid4())
            task_queue = task_queue or self.config.TASK_QUEUE

            # Build positional args: only include arg if it's not None,
            # so workflows that take no parameters aren't given an extra argument.
            positional_args: list[Any] = [] if arg is None else [arg]

            return await client.execute_workflow(
                workflow,
                *positional_args,
                id=workflow_id,
                task_queue=task_queue,
                execution_timeout=self._timeout(execution_timeout, self.config.WORKFLOW_EXECUTION_TIMEOUT),
                run_timeout=self._timeout(run_timeout, self.config.WORKFLOW_RUN_TIMEOUT),
                task_timeout=self._timeout(task_timeout, self.config.WORKFLOW_TASK_TIMEOUT),
                retry_policy=self._build_workflow_retry_policy(),
                **self._id_policies(id_reuse_policy, id_conflict_policy),
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
        async with self._mapped_errors("get_workflow_handle", workflow_id):
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
        async with self._mapped_errors("cancel_workflow", workflow_id):
            handle = await self.get_workflow_handle(workflow_id, run_id)
            await handle.cancel(reason=reason or "")

    @override
    async def terminate_workflow(self, workflow_id: str, run_id: str | None = None, reason: str | None = None) -> None:
        """Terminate a running workflow execution immediately.

        Args:
            workflow_id (str): The unique identifier of the workflow execution.
            run_id (str, optional): The specific run identifier within the workflow.
                If None, terminates the latest run. Defaults to None.
            reason (str, optional): Reason for termination. Defaults to None.
        """
        async with self._mapped_errors("terminate_workflow", workflow_id):
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
        async with self._mapped_errors("signal_workflow", workflow_id):
            handle = await self.get_workflow_handle(workflow_id, run_id)
            # Only pass arg if it's not None, so signal handlers with no parameters work correctly.
            positional_args: list[Any] = [] if arg is None else [arg]
            await handle.signal(signal_name, *positional_args)

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
        async with self._mapped_errors("query_workflow", workflow_id):
            handle = await self.get_workflow_handle(workflow_id, run_id)
            # Only pass arg if it's not None, so query handlers with no parameters work correctly.
            positional_args: list[Any] = [] if arg is None else [arg]
            return await handle.query(query_name, *positional_args)

    @override
    async def list_workflows(
        self,
        query: str | None = None,
        page_size: int | None = None,
        next_page_token: bytes | None = None,
        limit: int | None = None,
    ) -> list[WorkflowExecution]:
        """List workflow executions matching the given criteria.

        Args:
            query (str, optional): List filter query in Temporal SQL syntax.
                Defaults to None (no filter).
            page_size (int, optional): Maximum number of results per page.
                Defaults to None (server default).
            next_page_token (bytes, optional): Token for pagination.
                Defaults to None (first page).
            limit (int, optional): Maximum number of executions to return. Defaults to None, which loads every
                matching execution into memory; set it, or use ``iter_workflows``, for large namespaces.

        Returns:
            list[WorkflowExecution]: The workflow executions matching the query.
        """
        workflows_iter = await self.iter_workflows(
            query=query,
            page_size=page_size,
            next_page_token=next_page_token,
            limit=limit,
        )
        return [workflow async for workflow in workflows_iter]

    async def iter_workflows(
        self,
        query: str | None = None,
        page_size: int | None = None,
        next_page_token: bytes | None = None,
        limit: int | None = None,
    ) -> WorkflowExecutionAsyncIterator:
        """Iterate workflow executions page by page without loading them all into memory.

        Args:
            query (str, optional): List filter query in Temporal SQL syntax. Defaults to None (no filter).
            page_size (int, optional): Number of results fetched per page. Defaults to None (100).
            next_page_token (bytes, optional): Token to resume from. Defaults to None (first page).
            limit (int, optional): Maximum number of executions to yield. Defaults to None (no limit).

        Returns:
            WorkflowExecutionAsyncIterator: Async iterator of executions; its ``next_page_token`` resumes the listing.
        """
        async with self._mapped_errors("iter_workflows", None):
            client = await self.get_client()
            return client.list_workflows(
                query=query,
                limit=limit,
                page_size=page_size or 100,
                next_page_token=next_page_token,
            )

    @override
    async def describe_workflow(self, workflow_id: str, run_id: str | None = None) -> WorkflowExecutionDescription:
        """Get detailed information about a workflow execution.

        Args:
            workflow_id (str): The unique identifier of the workflow execution.
            run_id (str, optional): The specific run identifier within the workflow.
                If None, describes the latest run. Defaults to None.

        Returns:
            WorkflowExecutionDescription: Detailed workflow execution information.
        """
        async with self._mapped_errors("describe_workflow", workflow_id):
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
    async def create_schedule(
        self,
        schedule_id: str,
        workflow_class: Any,
        spec: ScheduleSpec,
        task_queue: str,
        workflow_id: str | None = None,
        schedule_policy: SchedulePolicy | None = None,
        args: Sequence[Any] | None = None,
        memo: dict[str, Any] | None = None,
    ) -> None:
        """Create a schedule for a workflow.

        Args:
            schedule_id (str): Unique schedule ID.
            workflow_class (Any): The workflow class or workflow type name to start.
            spec (ScheduleSpec): When the schedule fires (intervals, calendars, cron).
            task_queue (str): Task queue of the started workflows.
            workflow_id (str, optional): Base ID of the started workflows; the server appends the fire time.
                Defaults to the schedule ID.
            schedule_policy (SchedulePolicy, optional): Overlap, catchup window and pause-on-failure policy.
                Defaults to skipping overlapping runs.
            args (Sequence[Any], optional): Arguments of the started workflows. Defaults to None.
            memo (dict[str, Any], optional): Memo of the started workflows. Defaults to None.
        """
        async with self._mapped_errors("create_schedule", schedule_id):
            client = await self.get_client()

            workflow_execution_id = workflow_id or schedule_id
            sched = Schedule(
                action=ScheduleActionStartWorkflow(
                    workflow=workflow_class,
                    args=list(args or []),
                    id=workflow_execution_id,
                    task_queue=task_queue,
                    memo=memo,
                ),
                spec=spec,
                policy=schedule_policy
                or SchedulePolicy(
                    overlap=ScheduleOverlapPolicy.SKIP,
                ),
            )

            await client.create_schedule(schedule_id, sched)

    @override
    async def stop_schedule(self, schedule_id: str) -> None:
        """Delete a schedule.

        Deprecated: the name hides that the schedule is deleted; use ``delete_schedule``, or ``pause_schedule`` to
        stop it while keeping it.

        Args:
            schedule_id (str): The schedule ID.
        """
        warnings.warn(
            "stop_schedule() deletes the schedule and is deprecated; use delete_schedule() or pause_schedule()",
            DeprecationWarning,
            stacklevel=2,
        )
        await self.delete_schedule(schedule_id)

    @override
    async def delete_schedule(self, schedule_id: str) -> None:
        """Delete a schedule permanently; ``pause_schedule`` stops it while keeping it.

        Args:
            schedule_id (str): The schedule ID.
        """
        async with self._mapped_errors("delete_schedule", schedule_id):
            await (await self._schedule_handle(schedule_id)).delete()

    async def _schedule_handle(self, schedule_id: str) -> ScheduleHandle:
        """Get a handle to an existing schedule.

        Args:
            schedule_id (str): The schedule ID.

        Returns:
            ScheduleHandle: Handle to the schedule.
        """
        client = await self.get_client()
        return client.get_schedule_handle(schedule_id)

    async def pause_schedule(self, schedule_id: str, note: str | None = None) -> None:
        """Pause a schedule so it stops firing.

        Args:
            schedule_id (str): The schedule ID.
            note (str, optional): Why the schedule is paused. Defaults to None.
        """
        async with self._mapped_errors("pause_schedule", schedule_id):
            await (await self._schedule_handle(schedule_id)).pause(note=note)

    async def unpause_schedule(self, schedule_id: str, note: str | None = None) -> None:
        """Resume a paused schedule.

        Args:
            schedule_id (str): The schedule ID.
            note (str, optional): Why the schedule is resumed. Defaults to None.
        """
        async with self._mapped_errors("unpause_schedule", schedule_id):
            await (await self._schedule_handle(schedule_id)).unpause(note=note)

    async def trigger_schedule(self, schedule_id: str, overlap: ScheduleOverlapPolicy | None = None) -> None:
        """Start the schedule's action now, outside its spec.

        Args:
            schedule_id (str): The schedule ID.
            overlap (ScheduleOverlapPolicy, optional): Overlap policy for this run. Defaults to the schedule's.
        """
        async with self._mapped_errors("trigger_schedule", schedule_id):
            await (await self._schedule_handle(schedule_id)).trigger(overlap=overlap)

    async def describe_schedule(self, schedule_id: str) -> ScheduleDescription:
        """Get a schedule's definition, state and recent actions.

        Args:
            schedule_id (str): The schedule ID.

        Returns:
            ScheduleDescription: The schedule description.
        """
        async with self._mapped_errors("describe_schedule", schedule_id):
            return await (await self._schedule_handle(schedule_id)).describe()

    async def update_schedule(
        self,
        schedule_id: str,
        spec: ScheduleSpec | None = None,
        schedule_policy: SchedulePolicy | None = None,
    ) -> None:
        """Replace a schedule's spec and/or policy, keeping its action and state.

        Args:
            schedule_id (str): The schedule ID.
            spec (ScheduleSpec, optional): New spec. Defaults to None (unchanged).
            schedule_policy (SchedulePolicy, optional): New policy. Defaults to None (unchanged).
        """

        def _update(update_input: ScheduleUpdateInput) -> ScheduleUpdate:
            schedule = update_input.description.schedule
            if spec is not None:
                schedule.spec = spec
            if schedule_policy is not None:
                schedule.policy = schedule_policy
            return ScheduleUpdate(schedule=schedule)

        async with self._mapped_errors("update_schedule", schedule_id):
            await (await self._schedule_handle(schedule_id)).update(_update)

    async def list_schedules(self, query: str | None = None, limit: int | None = None) -> list[ScheduleListDescription]:
        """List schedules, optionally filtered by a visibility query.

        Args:
            query (str, optional): Visibility list filter. Defaults to None (all schedules).
            limit (int, optional): Maximum number of schedules to return. Defaults to None (all).

        Returns:
            list[ScheduleListDescription]: The matching schedules.
        """
        async with self._mapped_errors("list_schedules", None):
            client = await self.get_client()
            schedules: list[ScheduleListDescription] = []
            async for schedule in await client.list_schedules(query):
                if limit is not None and len(schedules) >= limit:
                    break
                schedules.append(schedule)
            return schedules
