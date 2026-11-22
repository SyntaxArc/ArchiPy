"""Temporal configuration."""

__lazy_modules__ = ["archipy.models.errors"]

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from archipy.configs.sections._common import deprecated_flat_message, fold_flat_fields
from archipy.models.errors import InvalidArgumentError

# Kept for backward compatibility; the TLS files no longer have to be set all together.
TLS_CERT_PARTS_REQUIRED = 3


class TemporalTlsConfig(BaseModel):
    """TLS settings of the Temporal connection."""

    model_config = ConfigDict(extra="forbid")

    IS_ENABLED: bool | None = Field(
        default=None,
        description=(
            "Force TLS on (system CA bundle) or off; None enables it when API_KEY or any TLS_* file is set "
            "(server-only TLS needs just TLS_CA_CERT or nothing)"
        ),
    )
    CA_CERT: str | None = Field(default=None, description="Path to TLS CA certificate")
    CLIENT_CERT: str | None = Field(default=None, description="Path to TLS client certificate")
    CLIENT_KEY: str | None = Field(default=None, description="Path to TLS client private key")
    SERVER_NAME: str | None = Field(
        default=None,
        description="Server name to verify the TLS certificate against, when it differs from HOST",
    )
    VERIFICATION_SERVER_NAME: str | None = Field(
        default=None,
        description=(
            "Name checked against the server certificate without changing the SNI sent, e.g. behind an "
            "SNI-inspecting proxy (requires TLS_CA_CERT)"
        ),
    )

    @model_validator(mode="after")
    def validate_tls_configuration(self) -> Self:
        """Validate the mutual TLS client certificate and key are set together; the CA certificate is optional.

        A certificate verification server name needs ``CA_CERT``, the root it verifies against.
        """
        if (self.CLIENT_CERT is None) != (self.CLIENT_KEY is None):
            raise InvalidArgumentError()
        if self.VERIFICATION_SERVER_NAME is not None and self.CA_CERT is None:
            raise InvalidArgumentError()

        return self


class TemporalWorkerConfig(BaseModel):
    """Worker settings."""

    model_config = ConfigDict(extra="forbid")

    GRACEFUL_SHUTDOWN_SECONDS: int = Field(
        default=30,
        ge=0,
        description="Maximum time in seconds to wait for graceful worker shutdown",
    )
    MAX_CACHED_WORKFLOWS: int = Field(
        default=1000,
        ge=0,
        description="Maximum number of workflow instances cached in worker memory",
    )
    DEBUG_MODE: bool = Field(
        default=False,
        description="Enable worker debug mode (e.g. breakpoint support in workflow sandbox)",
    )
    MAX_CONCURRENT_LOCAL_ACTIVITIES: int | None = Field(
        default=None,
        ge=1,
        description="Maximum concurrent local activities (None uses server default)",
    )
    DISABLE_EAGER_ACTIVITY_EXECUTION: bool = Field(
        default=False,
        description="Disable eager activity execution on the worker",
    )
    MAX_EAGER_ACTIVITY_RESERVATIONS: int | None = Field(
        default=None,
        ge=1,
        description="Maximum eager activities one workflow task may reserve (None: SDK default of 3)",
    )
    POLLER_AUTOSCALING: bool = Field(
        default=False,
        description=(
            "Let the worker scale its workflow and activity task pollers to the backlog "
            "(requires Temporal Server 1.28+)"
        ),
    )
    MAX_ACTIVITIES_PER_SECOND: float | None = Field(
        default=None,
        gt=0,
        description="Rate limit for activities this worker starts per second (None: unlimited)",
    )
    MAX_TASK_QUEUE_ACTIVITIES_PER_SECOND: float | None = Field(
        default=None,
        gt=0,
        description="Server-enforced rate limit for activities across the whole task queue (None: unlimited)",
    )


class TemporalClientRetryConfig(BaseModel):
    """Client RPC retry settings."""

    model_config = ConfigDict(extra="forbid")

    MAX_RETRIES: int = Field(
        default=10,
        ge=0,
        description="Maximum client-side RPC retry attempts",
    )
    INITIAL_INTERVAL_MS: int = Field(
        default=100,
        ge=1,
        description="Initial backoff interval for client-side RPC retries in milliseconds",
    )
    MAX_INTERVAL_MS: int = Field(
        default=5000,
        ge=1,
        description="Maximum backoff interval for client-side RPC retries in milliseconds",
    )


class TemporalKeepAliveConfig(BaseModel):
    """Connection keep-alive settings."""

    model_config = ConfigDict(extra="forbid")

    INTERVAL_MS: int = Field(
        default=30000,
        ge=1,
        description="gRPC keep-alive ping interval in milliseconds",
    )
    TIMEOUT_MS: int = Field(
        default=15000,
        ge=1,
        description="gRPC keep-alive timeout in milliseconds",
    )

    @model_validator(mode="after")
    def validate_keep_alive_configuration(self) -> Self:
        """Validate keep-alive timeout is less than the keep-alive interval."""
        if self.TIMEOUT_MS >= self.INTERVAL_MS:
            raise InvalidArgumentError()

        return self


class TemporalWorkflowConfig(BaseModel):
    """Default workflow timeouts and retry."""

    model_config = ConfigDict(extra="forbid")

    EXECUTION_TIMEOUT: int | None = Field(
        default=None,
        ge=1,
        description="Maximum workflow execution time in seconds, retries included (None: unbounded)",
    )
    RUN_TIMEOUT: int | None = Field(
        default=None,
        ge=1,
        description="Maximum single workflow run time in seconds (None: unbounded)",
    )
    TASK_TIMEOUT: int = Field(
        default=30,
        ge=1,
        description="Maximum workflow task processing time in seconds",
    )
    RETRY_ENABLED: bool = Field(
        default=False,
        description=(
            "Apply the RETRY_* policy to whole workflow executions started by the adapter "
            "(a workflow retry reruns the workflow from the start)"
        ),
    )

    @model_validator(mode="after")
    def validate_timeout_hierarchy(self) -> Self:
        """Validate timeout configuration hierarchy."""
        # The task timeout bounds a single workflow task, so it is independent of the run timeout.
        if (
            self.RUN_TIMEOUT is not None
            and self.EXECUTION_TIMEOUT is not None
            and self.RUN_TIMEOUT > self.EXECUTION_TIMEOUT
        ):
            raise InvalidArgumentError()

        return self


class TemporalActivityConfig(BaseModel):
    """Default activity timeouts."""

    model_config = ConfigDict(extra="forbid")

    START_TO_CLOSE_TIMEOUT: int = Field(
        default=30,
        ge=1,
        description="Maximum activity execution time in seconds",
    )
    HEARTBEAT_TIMEOUT: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Activity heartbeat timeout in seconds (None disables it; set only for activities that heartbeat, "
            "otherwise they fail with a heartbeat timeout)"
        ),
    )


class TemporalRetryConfig(BaseModel):
    """Default workflow and activity retry policy."""

    model_config = ConfigDict(extra="forbid")

    MAXIMUM_ATTEMPTS: int = Field(
        default=3,
        ge=1,
        description="Maximum retry attempts for failed activities",
    )
    BACKOFF_COEFFICIENT: float = Field(
        default=2.0,
        ge=1.0,
        description="Backoff multiplier for retry delays",
    )
    MAXIMUM_INTERVAL: int = Field(
        default=60,
        ge=1,
        description="Maximum retry interval in seconds",
    )
    INITIAL_INTERVAL: int = Field(
        default=1,
        ge=1,
        description="Initial retry interval in seconds for workflow and activity retry policies",
    )
    NON_RETRYABLE_ERROR_TYPES: list[str] | None = Field(
        default=None,
        description="Error type names that should not be retried by workflow/activity retry policies",
    )


class TemporalConfig(BaseModel):
    """Configuration settings for Temporal workflow engine integration.

    Controls connection parameters, security settings, and timeout configurations
    for Temporal workflow orchestration services.
    """

    HOST: str = Field(default="localhost", description="Temporal server host address")
    PORT: int = Field(default=7233, ge=1, le=65535, description="Temporal server port number")
    NAMESPACE: str = Field(default="default", description="Temporal namespace for workflow isolation")
    TASK_QUEUE: str = Field(default="task-queue", description="Default task queue name")
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
    RUNTIME_DISABLE_ENVIRONMENT_INFO: bool = Field(
        default=False,
        description="Keep runtime, hosting and platform information out of worker heartbeats sent to the server",
    )
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
    RPC_METADATA: dict[str, str] | None = Field(
        default=None,
        description="Custom RPC metadata headers sent with every client request",
    )
    CONNECT_TIMEOUT: float | None = Field(
        default=None,
        gt=0,
        description="Seconds to wait for the TCP connection, separate from RPC timeouts (None: SDK default)",
    )
    GRPC_COMPRESSION: Literal["gzip", "none"] | None = Field(
        default=None,
        description=(
            "gRPC compression of client requests; 'none' for proxies without gRPC compression support "
            "(None: SDK default, gzip)"
        ),
    )
    PAYLOADS_WARN_SIZE: int | None = Field(
        default=None,
        ge=1,
        description="Payload size in bytes above which the SDK logs a warning (None: SDK default, 512 KiB)",
    )
    MEMO_WARN_SIZE: int | None = Field(
        default=None,
        ge=1,
        description="Memo size in bytes above which the SDK logs a warning (None: SDK default, 2 KiB)",
    )

    TLS: TemporalTlsConfig = Field(
        default_factory=TemporalTlsConfig,
        description="TLS settings of the Temporal connection",
    )
    WORKER: TemporalWorkerConfig = Field(default_factory=TemporalWorkerConfig, description="Worker settings")
    CLIENT_RETRY: TemporalClientRetryConfig = Field(
        default_factory=TemporalClientRetryConfig,
        description="Client RPC retry settings",
    )
    KEEP_ALIVE: TemporalKeepAliveConfig = Field(
        default_factory=TemporalKeepAliveConfig,
        description="Connection keep-alive settings",
    )
    WORKFLOW: TemporalWorkflowConfig = Field(
        default_factory=TemporalWorkflowConfig,
        description="Default workflow timeouts and retry",
    )
    ACTIVITY: TemporalActivityConfig = Field(
        default_factory=TemporalActivityConfig,
        description="Default activity timeouts",
    )
    RETRY: TemporalRetryConfig = Field(
        default_factory=TemporalRetryConfig,
        description="Default workflow and activity retry policy",
    )

    TLS_ENABLED: bool | None = Field(
        default=None,
        description=(
            "Force TLS on (system CA bundle) or off; None enables it when API_KEY or any TLS_* file is set "
            "(server-only TLS needs just TLS_CA_CERT or nothing)"
        ),
        deprecated=deprecated_flat_message("TEMPORAL", "TLS_ENABLED", "TLS", "IS_ENABLED"),
    )
    TLS_CA_CERT: str | None = Field(
        default=None,
        description="Path to TLS CA certificate",
        deprecated=deprecated_flat_message("TEMPORAL", "TLS_CA_CERT", "TLS", "CA_CERT"),
    )
    TLS_CLIENT_CERT: str | None = Field(
        default=None,
        description="Path to TLS client certificate",
        deprecated=deprecated_flat_message("TEMPORAL", "TLS_CLIENT_CERT", "TLS", "CLIENT_CERT"),
    )
    TLS_CLIENT_KEY: str | None = Field(
        default=None,
        description="Path to TLS client private key",
        deprecated=deprecated_flat_message("TEMPORAL", "TLS_CLIENT_KEY", "TLS", "CLIENT_KEY"),
    )
    TLS_SERVER_NAME: str | None = Field(
        default=None,
        description="Server name to verify the TLS certificate against, when it differs from HOST",
        deprecated=deprecated_flat_message("TEMPORAL", "TLS_SERVER_NAME", "TLS", "SERVER_NAME"),
    )
    TLS_VERIFICATION_SERVER_NAME: str | None = Field(
        default=None,
        description=(
            "Name checked against the server certificate without changing the SNI sent, e.g. behind an "
            "SNI-inspecting proxy (requires TLS_CA_CERT)"
        ),
        deprecated=deprecated_flat_message(
            "TEMPORAL",
            "TLS_VERIFICATION_SERVER_NAME",
            "TLS",
            "VERIFICATION_SERVER_NAME",
        ),
    )
    WORKER_GRACEFUL_SHUTDOWN_SECONDS: int = Field(
        default=30,
        ge=0,
        description="Maximum time in seconds to wait for graceful worker shutdown",
        deprecated=deprecated_flat_message(
            "TEMPORAL",
            "WORKER_GRACEFUL_SHUTDOWN_SECONDS",
            "WORKER",
            "GRACEFUL_SHUTDOWN_SECONDS",
        ),
    )
    WORKER_MAX_CACHED_WORKFLOWS: int = Field(
        default=1000,
        ge=0,
        description="Maximum number of workflow instances cached in worker memory",
        deprecated=deprecated_flat_message("TEMPORAL", "WORKER_MAX_CACHED_WORKFLOWS", "WORKER", "MAX_CACHED_WORKFLOWS"),
    )
    WORKER_DEBUG_MODE: bool = Field(
        default=False,
        description="Enable worker debug mode (e.g. breakpoint support in workflow sandbox)",
        deprecated=deprecated_flat_message("TEMPORAL", "WORKER_DEBUG_MODE", "WORKER", "DEBUG_MODE"),
    )
    WORKER_MAX_CONCURRENT_LOCAL_ACTIVITIES: int | None = Field(
        default=None,
        ge=1,
        description="Maximum concurrent local activities (None uses server default)",
        deprecated=deprecated_flat_message(
            "TEMPORAL",
            "WORKER_MAX_CONCURRENT_LOCAL_ACTIVITIES",
            "WORKER",
            "MAX_CONCURRENT_LOCAL_ACTIVITIES",
        ),
    )
    WORKER_DISABLE_EAGER_ACTIVITY_EXECUTION: bool = Field(
        default=False,
        description="Disable eager activity execution on the worker",
        deprecated=deprecated_flat_message(
            "TEMPORAL",
            "WORKER_DISABLE_EAGER_ACTIVITY_EXECUTION",
            "WORKER",
            "DISABLE_EAGER_ACTIVITY_EXECUTION",
        ),
    )
    WORKER_MAX_EAGER_ACTIVITY_RESERVATIONS: int | None = Field(
        default=None,
        ge=1,
        description="Maximum eager activities one workflow task may reserve (None: SDK default of 3)",
        deprecated=deprecated_flat_message(
            "TEMPORAL",
            "WORKER_MAX_EAGER_ACTIVITY_RESERVATIONS",
            "WORKER",
            "MAX_EAGER_ACTIVITY_RESERVATIONS",
        ),
    )
    WORKER_POLLER_AUTOSCALING: bool = Field(
        default=False,
        description=(
            "Let the worker scale its workflow and activity task pollers to the backlog "
            "(requires Temporal Server 1.28+)"
        ),
        deprecated=deprecated_flat_message("TEMPORAL", "WORKER_POLLER_AUTOSCALING", "WORKER", "POLLER_AUTOSCALING"),
    )
    WORKER_MAX_ACTIVITIES_PER_SECOND: float | None = Field(
        default=None,
        gt=0,
        description="Rate limit for activities this worker starts per second (None: unlimited)",
        deprecated=deprecated_flat_message(
            "TEMPORAL",
            "WORKER_MAX_ACTIVITIES_PER_SECOND",
            "WORKER",
            "MAX_ACTIVITIES_PER_SECOND",
        ),
    )
    WORKER_MAX_TASK_QUEUE_ACTIVITIES_PER_SECOND: float | None = Field(
        default=None,
        gt=0,
        description="Server-enforced rate limit for activities across the whole task queue (None: unlimited)",
        deprecated=deprecated_flat_message(
            "TEMPORAL",
            "WORKER_MAX_TASK_QUEUE_ACTIVITIES_PER_SECOND",
            "WORKER",
            "MAX_TASK_QUEUE_ACTIVITIES_PER_SECOND",
        ),
    )
    CLIENT_RPC_RETRY_MAX_RETRIES: int = Field(
        default=10,
        ge=0,
        description="Maximum client-side RPC retry attempts",
        deprecated=deprecated_flat_message("TEMPORAL", "CLIENT_RPC_RETRY_MAX_RETRIES", "CLIENT_RETRY", "MAX_RETRIES"),
    )
    CLIENT_RPC_RETRY_INITIAL_INTERVAL_MS: int = Field(
        default=100,
        ge=1,
        description="Initial backoff interval for client-side RPC retries in milliseconds",
        deprecated=deprecated_flat_message(
            "TEMPORAL",
            "CLIENT_RPC_RETRY_INITIAL_INTERVAL_MS",
            "CLIENT_RETRY",
            "INITIAL_INTERVAL_MS",
        ),
    )
    CLIENT_RPC_RETRY_MAX_INTERVAL_MS: int = Field(
        default=5000,
        ge=1,
        description="Maximum backoff interval for client-side RPC retries in milliseconds",
        deprecated=deprecated_flat_message(
            "TEMPORAL",
            "CLIENT_RPC_RETRY_MAX_INTERVAL_MS",
            "CLIENT_RETRY",
            "MAX_INTERVAL_MS",
        ),
    )
    KEEP_ALIVE_INTERVAL_MS: int = Field(
        default=30000,
        ge=1,
        description="gRPC keep-alive ping interval in milliseconds",
        deprecated=deprecated_flat_message("TEMPORAL", "KEEP_ALIVE_INTERVAL_MS", "KEEP_ALIVE", "INTERVAL_MS"),
    )
    KEEP_ALIVE_TIMEOUT_MS: int = Field(
        default=15000,
        ge=1,
        description="gRPC keep-alive timeout in milliseconds",
        deprecated=deprecated_flat_message("TEMPORAL", "KEEP_ALIVE_TIMEOUT_MS", "KEEP_ALIVE", "TIMEOUT_MS"),
    )
    WORKFLOW_EXECUTION_TIMEOUT: int | None = Field(
        default=None,
        ge=1,
        description="Maximum workflow execution time in seconds, retries included (None: unbounded)",
        deprecated=deprecated_flat_message("TEMPORAL", "WORKFLOW_EXECUTION_TIMEOUT", "WORKFLOW", "EXECUTION_TIMEOUT"),
    )
    WORKFLOW_RUN_TIMEOUT: int | None = Field(
        default=None,
        ge=1,
        description="Maximum single workflow run time in seconds (None: unbounded)",
        deprecated=deprecated_flat_message("TEMPORAL", "WORKFLOW_RUN_TIMEOUT", "WORKFLOW", "RUN_TIMEOUT"),
    )
    WORKFLOW_TASK_TIMEOUT: int = Field(
        default=30,
        ge=1,
        description="Maximum workflow task processing time in seconds",
        deprecated=deprecated_flat_message("TEMPORAL", "WORKFLOW_TASK_TIMEOUT", "WORKFLOW", "TASK_TIMEOUT"),
    )
    WORKFLOW_RETRY_ENABLED: bool = Field(
        default=False,
        description=(
            "Apply the RETRY_* policy to whole workflow executions started by the adapter "
            "(a workflow retry reruns the workflow from the start)"
        ),
        deprecated=deprecated_flat_message("TEMPORAL", "WORKFLOW_RETRY_ENABLED", "WORKFLOW", "RETRY_ENABLED"),
    )
    ACTIVITY_START_TO_CLOSE_TIMEOUT: int = Field(
        default=30,
        ge=1,
        description="Maximum activity execution time in seconds",
        deprecated=deprecated_flat_message(
            "TEMPORAL",
            "ACTIVITY_START_TO_CLOSE_TIMEOUT",
            "ACTIVITY",
            "START_TO_CLOSE_TIMEOUT",
        ),
    )
    ACTIVITY_HEARTBEAT_TIMEOUT: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Activity heartbeat timeout in seconds (None disables it; set only for activities that heartbeat, "
            "otherwise they fail with a heartbeat timeout)"
        ),
        deprecated=deprecated_flat_message("TEMPORAL", "ACTIVITY_HEARTBEAT_TIMEOUT", "ACTIVITY", "HEARTBEAT_TIMEOUT"),
    )
    RETRY_MAXIMUM_ATTEMPTS: int = Field(
        default=3,
        ge=1,
        description="Maximum retry attempts for failed activities",
        deprecated=deprecated_flat_message("TEMPORAL", "RETRY_MAXIMUM_ATTEMPTS", "RETRY", "MAXIMUM_ATTEMPTS"),
    )
    RETRY_BACKOFF_COEFFICIENT: float = Field(
        default=2.0,
        ge=1.0,
        description="Backoff multiplier for retry delays",
        deprecated=deprecated_flat_message("TEMPORAL", "RETRY_BACKOFF_COEFFICIENT", "RETRY", "BACKOFF_COEFFICIENT"),
    )
    RETRY_MAXIMUM_INTERVAL: int = Field(
        default=60,
        ge=1,
        description="Maximum retry interval in seconds",
        deprecated=deprecated_flat_message("TEMPORAL", "RETRY_MAXIMUM_INTERVAL", "RETRY", "MAXIMUM_INTERVAL"),
    )
    RETRY_INITIAL_INTERVAL: int = Field(
        default=1,
        ge=1,
        description="Initial retry interval in seconds for workflow and activity retry policies",
        deprecated=deprecated_flat_message("TEMPORAL", "RETRY_INITIAL_INTERVAL", "RETRY", "INITIAL_INTERVAL"),
    )
    RETRY_NON_RETRYABLE_ERROR_TYPES: list[str] | None = Field(
        default=None,
        description="Error type names that should not be retried by workflow/activity retry policies",
        deprecated=deprecated_flat_message(
            "TEMPORAL",
            "RETRY_NON_RETRYABLE_ERROR_TYPES",
            "RETRY",
            "NON_RETRYABLE_ERROR_TYPES",
        ),
    )

    @model_validator(mode="after")
    def validate_rpc_metadata(self) -> Self:
        """Validate RPC metadata keys and values are non-empty strings."""
        if self.RPC_METADATA is None:
            return self

        for key, value in self.RPC_METADATA.items():
            if not key or not value:
                raise InvalidArgumentError()

        return self

    @model_validator(mode="after")
    def fold_deprecated_flat_fields(self) -> Self:
        """Copy deprecated flat settings into their groups."""
        fold_flat_fields(
            self,
            "TLS",
            TemporalTlsConfig,
            {
                "TLS_ENABLED": "IS_ENABLED",
                "TLS_CA_CERT": "CA_CERT",
                "TLS_CLIENT_CERT": "CLIENT_CERT",
                "TLS_CLIENT_KEY": "CLIENT_KEY",
                "TLS_SERVER_NAME": "SERVER_NAME",
                "TLS_VERIFICATION_SERVER_NAME": "VERIFICATION_SERVER_NAME",
            },
        )
        fold_flat_fields(
            self,
            "WORKER",
            TemporalWorkerConfig,
            {
                "WORKER_GRACEFUL_SHUTDOWN_SECONDS": "GRACEFUL_SHUTDOWN_SECONDS",
                "WORKER_MAX_CACHED_WORKFLOWS": "MAX_CACHED_WORKFLOWS",
                "WORKER_DEBUG_MODE": "DEBUG_MODE",
                "WORKER_MAX_CONCURRENT_LOCAL_ACTIVITIES": "MAX_CONCURRENT_LOCAL_ACTIVITIES",
                "WORKER_DISABLE_EAGER_ACTIVITY_EXECUTION": "DISABLE_EAGER_ACTIVITY_EXECUTION",
                "WORKER_MAX_EAGER_ACTIVITY_RESERVATIONS": "MAX_EAGER_ACTIVITY_RESERVATIONS",
                "WORKER_POLLER_AUTOSCALING": "POLLER_AUTOSCALING",
                "WORKER_MAX_ACTIVITIES_PER_SECOND": "MAX_ACTIVITIES_PER_SECOND",
                "WORKER_MAX_TASK_QUEUE_ACTIVITIES_PER_SECOND": "MAX_TASK_QUEUE_ACTIVITIES_PER_SECOND",
            },
        )
        fold_flat_fields(
            self,
            "CLIENT_RETRY",
            TemporalClientRetryConfig,
            {
                "CLIENT_RPC_RETRY_MAX_RETRIES": "MAX_RETRIES",
                "CLIENT_RPC_RETRY_INITIAL_INTERVAL_MS": "INITIAL_INTERVAL_MS",
                "CLIENT_RPC_RETRY_MAX_INTERVAL_MS": "MAX_INTERVAL_MS",
            },
        )
        fold_flat_fields(
            self,
            "KEEP_ALIVE",
            TemporalKeepAliveConfig,
            {"KEEP_ALIVE_INTERVAL_MS": "INTERVAL_MS", "KEEP_ALIVE_TIMEOUT_MS": "TIMEOUT_MS"},
        )
        fold_flat_fields(
            self,
            "WORKFLOW",
            TemporalWorkflowConfig,
            {
                "WORKFLOW_EXECUTION_TIMEOUT": "EXECUTION_TIMEOUT",
                "WORKFLOW_RUN_TIMEOUT": "RUN_TIMEOUT",
                "WORKFLOW_TASK_TIMEOUT": "TASK_TIMEOUT",
                "WORKFLOW_RETRY_ENABLED": "RETRY_ENABLED",
            },
        )
        fold_flat_fields(
            self,
            "ACTIVITY",
            TemporalActivityConfig,
            {
                "ACTIVITY_START_TO_CLOSE_TIMEOUT": "START_TO_CLOSE_TIMEOUT",
                "ACTIVITY_HEARTBEAT_TIMEOUT": "HEARTBEAT_TIMEOUT",
            },
        )
        fold_flat_fields(
            self,
            "RETRY",
            TemporalRetryConfig,
            {
                "RETRY_MAXIMUM_ATTEMPTS": "MAXIMUM_ATTEMPTS",
                "RETRY_BACKOFF_COEFFICIENT": "BACKOFF_COEFFICIENT",
                "RETRY_MAXIMUM_INTERVAL": "MAXIMUM_INTERVAL",
                "RETRY_INITIAL_INTERVAL": "INITIAL_INTERVAL",
                "RETRY_NON_RETRYABLE_ERROR_TYPES": "NON_RETRYABLE_ERROR_TYPES",
            },
        )
        return self
