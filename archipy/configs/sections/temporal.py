"""Temporal configuration."""

from typing import Self

from pydantic import BaseModel, Field, model_validator

from archipy.models.errors import InvalidArgumentError

TLS_CERT_PARTS_REQUIRED = 3


class TemporalConfig(BaseModel):
    """Configuration settings for Temporal workflow engine integration.

    Controls connection parameters, security settings, and timeout configurations
    for Temporal workflow orchestration services.
    """

    HOST: str = Field(default="localhost", description="Temporal server host address")
    PORT: int = Field(default=7233, ge=1, le=65535, description="Temporal server port number")
    NAMESPACE: str = Field(default="default", description="Temporal namespace for workflow isolation")
    TASK_QUEUE: str = Field(default="task-queue", description="Default task queue name")

    # Metrics Configuration (OTLP via global OTEL config)
    ENABLE_METRICS: bool = Field(
        default=False,
        description=(
            "Enable OTLP metrics export for Temporal workflows and activities "
            "(requires BaseConfig.OTEL.IS_ENABLED and METRICS_ENABLED; uses OTEL endpoint). "
            "With OTEL.METRICS_EXPORTER=pull the Temporal SDK serves its own /metrics scrape endpoint instead."
        ),
    )
    METRICS_PULL_PORT: int = Field(
        default=8201,
        ge=1,
        le=65535,
        description=(
            "Port of the Temporal SDK /metrics scrape endpoint when OTEL.METRICS_EXPORTER=pull "
            "(bound on OTEL.METRICS_PULL_HOST; must differ from OTEL.METRICS_PULL_PORT)"
        ),
    )

    PYDANTIC_DATA_CONVERTER: bool = Field(
        default=True,
        description=(
            "Serialize workflow and activity payloads with temporalio's Pydantic data converter "
            "(Pydantic models, datetimes and decimals round trip); ignored when a data_converter is passed explicitly"
        ),
    )

    # Client Connection Configuration
    CLIENT_IDENTITY: str | None = Field(
        default=None,
        description="Client identity string for Temporal server visibility",
    )
    API_KEY: str | None = Field(
        default=None,
        description="API key for Temporal Cloud authentication (ignored by local dev server)",
    )
    LAZY_CONNECT: bool = Field(
        default=False,
        description="Defer establishing the Temporal client connection until first use",
    )
    KEEP_ALIVE_INTERVAL_MS: int = Field(
        default=30000,
        ge=1,
        description="gRPC keep-alive ping interval in milliseconds",
    )
    KEEP_ALIVE_TIMEOUT_MS: int = Field(
        default=15000,
        ge=1,
        description="gRPC keep-alive timeout in milliseconds",
    )
    RPC_METADATA: dict[str, str] | None = Field(
        default=None,
        description="Custom RPC metadata headers sent with every client request",
    )
    CLIENT_RPC_RETRY_MAX_RETRIES: int = Field(
        default=10,
        ge=0,
        description="Maximum client-side RPC retry attempts",
    )
    CLIENT_RPC_RETRY_INITIAL_INTERVAL_MS: int = Field(
        default=100,
        ge=1,
        description="Initial backoff interval for client-side RPC retries in milliseconds",
    )
    CLIENT_RPC_RETRY_MAX_INTERVAL_MS: int = Field(
        default=5000,
        ge=1,
        description="Maximum backoff interval for client-side RPC retries in milliseconds",
    )

    # Worker Configuration
    WORKER_GRACEFUL_SHUTDOWN_SECONDS: int = Field(
        default=30,
        ge=0,
        description="Maximum time in seconds to wait for graceful worker shutdown",
    )
    WORKER_MAX_CACHED_WORKFLOWS: int = Field(
        default=1000,
        ge=0,
        description="Maximum number of workflow instances cached in worker memory",
    )
    WORKER_DEBUG_MODE: bool = Field(
        default=False,
        description="Enable worker debug mode (e.g. breakpoint support in workflow sandbox)",
    )
    WORKER_MAX_CONCURRENT_LOCAL_ACTIVITIES: int | None = Field(
        default=None,
        ge=1,
        description="Maximum concurrent local activities (None uses server default)",
    )
    WORKER_DISABLE_EAGER_ACTIVITY_EXECUTION: bool = Field(
        default=False,
        description="Disable eager activity execution on the worker",
    )

    # TLS Configuration
    TLS_CA_CERT: str | None = Field(default=None, description="Path to TLS CA certificate")
    TLS_CLIENT_CERT: str | None = Field(default=None, description="Path to TLS client certificate")
    TLS_CLIENT_KEY: str | None = Field(default=None, description="Path to TLS client private key")

    # Workflow Timeout Settings
    WORKFLOW_EXECUTION_TIMEOUT: int | None = Field(
        default=None,
        ge=1,
        description="Maximum workflow execution time in seconds, retries included (None: unbounded)",
    )
    WORKFLOW_RUN_TIMEOUT: int | None = Field(
        default=None,
        ge=1,
        description="Maximum single workflow run time in seconds (None: unbounded)",
    )
    WORKFLOW_TASK_TIMEOUT: int = Field(
        default=30,
        ge=1,
        description="Maximum workflow task processing time in seconds",
    )

    WORKFLOW_RETRY_ENABLED: bool = Field(
        default=False,
        description=(
            "Apply the RETRY_* policy to whole workflow executions started by the adapter "
            "(a workflow retry reruns the workflow from the start)"
        ),
    )

    # Activity Timeout Settings
    ACTIVITY_START_TO_CLOSE_TIMEOUT: int = Field(
        default=30,
        ge=1,
        description="Maximum activity execution time in seconds",
    )
    ACTIVITY_HEARTBEAT_TIMEOUT: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Activity heartbeat timeout in seconds (None disables it; set only for activities that heartbeat, "
            "otherwise they fail with a heartbeat timeout)"
        ),
    )

    # Retry Configuration
    RETRY_MAXIMUM_ATTEMPTS: int = Field(
        default=3,
        ge=1,
        description="Maximum retry attempts for failed activities",
    )
    RETRY_BACKOFF_COEFFICIENT: float = Field(
        default=2.0,
        ge=1.0,
        description="Backoff multiplier for retry delays",
    )
    RETRY_MAXIMUM_INTERVAL: int = Field(
        default=60,
        ge=1,
        description="Maximum retry interval in seconds",
    )
    RETRY_INITIAL_INTERVAL: int = Field(
        default=1,
        ge=1,
        description="Initial retry interval in seconds for workflow and activity retry policies",
    )
    RETRY_NON_RETRYABLE_ERROR_TYPES: list[str] | None = Field(
        default=None,
        description="Error type names that should not be retried by workflow/activity retry policies",
    )

    @model_validator(mode="after")
    def validate_tls_configuration(self) -> Self:
        """Validate TLS configuration consistency."""
        tls_fields = [self.TLS_CA_CERT, self.TLS_CLIENT_CERT, self.TLS_CLIENT_KEY]
        tls_provided = [field for field in tls_fields if field is not None]

        if len(tls_provided) > 0 and len(tls_provided) != TLS_CERT_PARTS_REQUIRED:
            raise InvalidArgumentError()

        return self

    @model_validator(mode="after")
    def validate_timeout_hierarchy(self) -> Self:
        """Validate timeout configuration hierarchy."""
        # The task timeout bounds a single workflow task, so it is independent of the run timeout.
        if (
            self.WORKFLOW_RUN_TIMEOUT is not None
            and self.WORKFLOW_EXECUTION_TIMEOUT is not None
            and self.WORKFLOW_RUN_TIMEOUT > self.WORKFLOW_EXECUTION_TIMEOUT
        ):
            raise InvalidArgumentError()

        return self

    @model_validator(mode="after")
    def validate_keep_alive_configuration(self) -> Self:
        """Validate keep-alive timeout is less than the keep-alive interval."""
        if self.KEEP_ALIVE_TIMEOUT_MS >= self.KEEP_ALIVE_INTERVAL_MS:
            raise InvalidArgumentError()

        return self

    @model_validator(mode="after")
    def validate_rpc_metadata(self) -> Self:
        """Validate RPC metadata keys and values are non-empty strings."""
        if self.RPC_METADATA is None:
            return self

        for key, value in self.RPC_METADATA.items():
            if not key or not value:
                raise InvalidArgumentError()

        return self
