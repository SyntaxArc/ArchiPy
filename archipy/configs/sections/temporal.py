"""Temporal configuration."""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from archipy.models.errors import InvalidArgumentError

# Kept for backward compatibility; the TLS files no longer have to be set all together.
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

    METRICS_GLOBAL_TAGS: dict[str, str] | None = Field(
        default=None,
        description="Tags added to every Temporal SDK metric, e.g. service and environment",
    )
    SDK_CORE_LOG_LEVEL: Literal["ERROR", "WARN", "INFO", "DEBUG", "TRACE"] | None = Field(
        default=None,
        description="Log level of the Temporal SDK core (None keeps the SDK default of WARN)",
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
    CONNECT_TIMEOUT: float | None = Field(
        default=None,
        gt=0,
        description="Seconds to wait for the TCP connection, separate from RPC timeouts (None: SDK default)",
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

    WORKER_POLLER_AUTOSCALING: bool = Field(
        default=False,
        description=(
            "Let the worker scale its workflow and activity task pollers to the backlog "
            "(requires Temporal Server 1.28+)"
        ),
    )
    WORKER_MAX_ACTIVITIES_PER_SECOND: float | None = Field(
        default=None,
        gt=0,
        description="Rate limit for activities this worker starts per second (None: unlimited)",
    )
    WORKER_MAX_TASK_QUEUE_ACTIVITIES_PER_SECOND: float | None = Field(
        default=None,
        gt=0,
        description="Server-enforced rate limit for activities across the whole task queue (None: unlimited)",
    )

    # TLS Configuration
    TLS_CA_CERT: str | None = Field(default=None, description="Path to TLS CA certificate")
    TLS_CLIENT_CERT: str | None = Field(default=None, description="Path to TLS client certificate")
    TLS_CLIENT_KEY: str | None = Field(default=None, description="Path to TLS client private key")
    TLS_SERVER_NAME: str | None = Field(
        default=None,
        description="Server name to verify the TLS certificate against, when it differs from HOST",
    )
    TLS_VERIFICATION_SERVER_NAME: str | None = Field(
        default=None,
        description=(
            "Name checked against the server certificate without changing the SNI sent, e.g. behind an "
            "SNI-inspecting proxy (requires TLS_CA_CERT)"
        ),
    )
    TLS_ENABLED: bool | None = Field(
        default=None,
        description=(
            "Force TLS on (system CA bundle) or off; None enables it when API_KEY or any TLS_* file is set "
            "(server-only TLS needs just TLS_CA_CERT or nothing)"
        ),
    )

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
        """Validate the mutual TLS client certificate and key are set together; the CA certificate is optional.

        A certificate verification server name needs ``TLS_CA_CERT``, the root it verifies against.
        """
        if (self.TLS_CLIENT_CERT is None) != (self.TLS_CLIENT_KEY is None):
            raise InvalidArgumentError()
        if self.TLS_VERIFICATION_SERVER_NAME is not None and self.TLS_CA_CERT is None:
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
