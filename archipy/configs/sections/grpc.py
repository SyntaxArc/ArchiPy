"""gRPC configuration."""

# Error classes are used only by validators, which run when a config is built, not when it is imported.
__lazy_modules__ = ["archipy.models.errors"]

import os
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from archipy.configs.sections._common import deprecated_flat_message, fold_flat_fields
from archipy.models.errors import InvalidArgumentError


class GrpcRateLimitConfig(BaseModel):
    """Configuration for gRPC server rate limiting.

    Controls Redis key layout, failure modes, and identity resolution for
    ``GrpcServerRateLimitInterceptor`` / ``AsyncGrpcServerRateLimitInterceptor``.
    Per-RPC limits are declared via ``grpc_rate_limit`` on servicer methods.
    When ``IS_ENABLED`` is True, ``AppUtils.create_grpc_app`` and ``AppUtils.create_async_grpc_app``
    register the matching interceptor automatically.
    """

    IS_ENABLED: bool = Field(
        default=False,
        description=(
            "When True, register the gRPC rate-limit interceptor in "
            "``AppUtils.create_grpc_app`` / ``AppUtils.create_async_grpc_app``."
        ),
    )
    KEY_PREFIX: str | None = Field(
        default=None,
        description="Redis key prefix. When None, ``{GRPC.SERVE_HOST}:RateLimit`` is used.",
    )
    FAIL_CLOSED: bool = Field(
        default=True,
        description="When True, Redis or identity-resolution failures abort with UNAVAILABLE instead of allowing RPCs.",
    )
    SKIP_METHODS: list[str] = Field(
        default=["/grpc.health.v1.Health/Check", "/grpc.health.v1.Health/Watch"],
        description="Full gRPC method names excluded from rate limiting.",
    )
    IDENTITY_FROM_ACCESS_TOKEN: bool = Field(
        default=True,
        description=(
            "When True, verify Bearer access tokens from invocation metadata via JWTUtils and bucket by sub; "
            "fall back to peer IP when the token is missing or invalid."
        ),
    )


class GrpcTlsConfig(BaseModel):
    """Server TLS and mTLS settings."""

    model_config = ConfigDict(extra="forbid")

    IS_ENABLED: bool = Field(
        default=False,
        description=(
            "When True, ``AppUtils.add_grpc_port`` binds a TLS port with ``grpc.ssl_server_credentials`` instead of "
            "an insecure port. Requires ``TLS_CERT_FILE`` and ``TLS_KEY_FILE``."
        ),
    )
    CERT_FILE: str | None = Field(default=None, description="Path to the PEM server certificate chain")
    KEY_FILE: str | None = Field(default=None, description="Path to the PEM server private key")
    CA_FILE: str | None = Field(
        default=None,
        description="Path to the PEM CA bundle used to verify client certificates (mTLS)",
    )
    REQUIRE_CLIENT_AUTH: bool = Field(
        default=False,
        description="When True, reject clients without a valid certificate. Requires ``TLS_CA_FILE``.",
    )

    @model_validator(mode="after")
    def validate_tls_settings(self) -> Self:
        """Check that TLS has a certificate and key, and mTLS has a CA."""
        if self.IS_ENABLED and not (self.CERT_FILE and self.KEY_FILE):
            raise InvalidArgumentError(argument_name="GRPC.TLS.CERT_FILE")
        if self.REQUIRE_CLIENT_AUTH and not self.CA_FILE:
            raise InvalidArgumentError(argument_name="GRPC.TLS.CA_FILE")
        return self


class GrpcStubTlsConfig(BaseModel):
    """Client channel TLS and mTLS settings."""

    model_config = ConfigDict(extra="forbid")

    IS_ENABLED: bool = Field(
        default=False,
        description="When True, ``AppUtils.create_grpc_channel`` opens a TLS channel instead of a plaintext one.",
    )
    CA_FILE: str | None = Field(
        default=None,
        description="Path to the PEM CA bundle that verifies the server. None uses the gRPC default roots.",
    )
    CERT_FILE: str | None = Field(
        default=None,
        description="Path to the PEM client certificate chain for mTLS. Requires ``STUB_TLS_KEY_FILE``.",
    )
    KEY_FILE: str | None = Field(
        default=None,
        description="Path to the PEM client private key for mTLS. Requires ``STUB_TLS_CERT_FILE``.",
    )

    @model_validator(mode="after")
    def validate_stub_tls_settings(self) -> Self:
        """Check that the client certificate and key come as a pair."""
        if bool(self.CERT_FILE) != bool(self.KEY_FILE):
            raise InvalidArgumentError(argument_name="GRPC.STUB_TLS.KEY_FILE")
        return self


class GrpcConfig(BaseModel):
    """Configuration settings for gRPC services.

    Controls gRPC server behavior, including connection parameters,
    performance tuning, and timeout settings.
    """

    SERVE_PORT: int = Field(default=8100, description="Port to serve gRPC on")
    SERVE_HOST: str = Field(default="[::]", description="Host to serve gRPC on")  # IPv6 equivalent of 0.0.0.0
    THREAD_WORKER_COUNT: int | None = Field(
        default=None,
        description=(
            "Number of worker threads. If omitted (None), set at model validation to "
            "THREAD_PER_CPU_CORE * (os.cpu_count() or 1)."
        ),
    )
    MAX_CONCURRENT_RPCS: int | None = Field(default=None, description="Maximum number of concurrent requests")
    THREAD_PER_CPU_CORE: int = Field(
        default=40,
        description="Threads per CPU core. Adjust based on thread block to CPU time ratio.",
    )
    SERVER_OPTIONS_CONFIG_LIST: list[tuple[str, int | str]] = Field(
        default=[
            ("grpc.max_metadata_size", 16 * 1024),  # 16KB  (default is 8KB)
            ("grpc.max_message_length", 128 * 1024 * 1024),  # 128MB
            ("grpc.max_receive_message_length", 128 * 1024 * 1024),
            ("grpc.max_send_message_length", 128 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 7_200_000),  # 2h
            ("grpc.keepalive_timeout_ms", 20_000),  # 20s
            ("grpc.keepalive_permit_without_calls", 1),  # allow pings on idle connections
            ("grpc.http2.min_recv_ping_interval_without_data_ms", 300_000),  # 5min
            ("grpc.http2.min_ping_interval_without_data_ms", 300_000),  # 5min
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.http2.max_ping_strikes", 2),
            ("grpc.max_connection_idle_ms", 600_000),  # 10min
            ("grpc.max_connection_age_ms", 1_800_000),  # 30min
            ("grpc.max_connection_age_grace_ms", 5_000),  # 5s graceful drain
        ],
        description="Server channel options. Values may be integers or strings.",
    )
    STUB_OPTIONS_CONFIG_LIST: list[tuple[str, int | str]] = Field(
        default=[
            ("grpc.max_metadata_size", 16 * 1024),  # 16KB
            ("grpc.max_message_length", 128 * 1024 * 1024),  # 128MB
            ("grpc.max_receive_message_length", 128 * 1024 * 1024),
            ("grpc.max_send_message_length", 128 * 1024 * 1024),
            ("grpc.keepalive_time_ms", 300_000),  # 5min
            ("grpc.keepalive_timeout_ms", 20_000),  # 20s
            ("grpc.keepalive_permit_without_calls", 1),
            ("grpc.http2.max_pings_without_data", 0),
            (
                "grpc.service_config",
                "{"
                '  "methodConfig": [{'
                '    "name": [],'
                '    "timeout": "10s",'
                '    "waitForReady": true,'
                '    "retryPolicy": {'
                '      "maxAttempts": 5,'
                '      "initialBackoff": "0.1s",'
                '      "maxBackoff": "1s",'
                '      "backoffMultiplier": 2,'
                '      "retryableStatusCodes": ["UNAVAILABLE", "ABORTED", "RESOURCE_EXHAUSTED"]'
                "    }"
                "  }],"
                '  "retryThrottling": {'
                '    "maxTokens": 10,'
                '    "tokenRatio": 0.1'
                "  }"
                "}",
            ),
        ],
        description=(
            "Client stub channel options, applied by ``AppUtils.create_grpc_channel``. Values may be integers or "
            "strings."
        ),
    )
    SERVER_COMPRESSION: Literal["none", "deflate", "gzip"] | None = Field(
        default=None,
        description=(
            "Default server compression, used by ``AppUtils.create_grpc_app`` / ``AppUtils.create_async_grpc_app`` "
            "when no ``compression`` argument is passed. None leaves the gRPC default."
        ),
    )
    STUB_COMPRESSION: Literal["none", "deflate", "gzip"] | None = Field(
        default=None,
        description=(
            "Default channel compression, used by ``AppUtils.create_grpc_channel``. None leaves the gRPC default."
        ),
    )
    SHUTDOWN_GRACE_SECONDS: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Seconds ``AppUtils.stop_grpc_app`` lets in-flight RPCs finish before it aborts them. "
            "None aborts them at once."
        ),
    )

    TLS: GrpcTlsConfig = Field(default_factory=GrpcTlsConfig, description="Server TLS and mTLS settings")
    STUB_TLS: GrpcStubTlsConfig = Field(
        default_factory=GrpcStubTlsConfig,
        description="Client channel TLS and mTLS settings",
    )

    TLS_ENABLED: bool = Field(
        default=False,
        description=(
            "When True, ``AppUtils.add_grpc_port`` binds a TLS port with ``grpc.ssl_server_credentials`` instead of "
            "an insecure port. Requires ``TLS_CERT_FILE`` and ``TLS_KEY_FILE``."
        ),
        deprecated=deprecated_flat_message("GRPC", "TLS_ENABLED", "TLS", "IS_ENABLED"),
    )
    TLS_CERT_FILE: str | None = Field(
        default=None,
        description="Path to the PEM server certificate chain",
        deprecated=deprecated_flat_message("GRPC", "TLS_CERT_FILE", "TLS", "CERT_FILE"),
    )
    TLS_KEY_FILE: str | None = Field(
        default=None,
        description="Path to the PEM server private key",
        deprecated=deprecated_flat_message("GRPC", "TLS_KEY_FILE", "TLS", "KEY_FILE"),
    )
    TLS_CA_FILE: str | None = Field(
        default=None,
        description="Path to the PEM CA bundle used to verify client certificates (mTLS)",
        deprecated=deprecated_flat_message("GRPC", "TLS_CA_FILE", "TLS", "CA_FILE"),
    )
    TLS_REQUIRE_CLIENT_AUTH: bool = Field(
        default=False,
        description="When True, reject clients without a valid certificate. Requires ``TLS_CA_FILE``.",
        deprecated=deprecated_flat_message("GRPC", "TLS_REQUIRE_CLIENT_AUTH", "TLS", "REQUIRE_CLIENT_AUTH"),
    )
    STUB_TLS_ENABLED: bool = Field(
        default=False,
        description="When True, ``AppUtils.create_grpc_channel`` opens a TLS channel instead of a plaintext one.",
        deprecated=deprecated_flat_message("GRPC", "STUB_TLS_ENABLED", "STUB_TLS", "IS_ENABLED"),
    )
    STUB_TLS_CA_FILE: str | None = Field(
        default=None,
        description="Path to the PEM CA bundle that verifies the server. None uses the gRPC default roots.",
        deprecated=deprecated_flat_message("GRPC", "STUB_TLS_CA_FILE", "STUB_TLS", "CA_FILE"),
    )
    STUB_TLS_CERT_FILE: str | None = Field(
        default=None,
        description="Path to the PEM client certificate chain for mTLS. Requires ``STUB_TLS_KEY_FILE``.",
        deprecated=deprecated_flat_message("GRPC", "STUB_TLS_CERT_FILE", "STUB_TLS", "CERT_FILE"),
    )
    STUB_TLS_KEY_FILE: str | None = Field(
        default=None,
        description="Path to the PEM client private key for mTLS. Requires ``STUB_TLS_CERT_FILE``.",
        deprecated=deprecated_flat_message("GRPC", "STUB_TLS_KEY_FILE", "STUB_TLS", "KEY_FILE"),
    )

    @model_validator(mode="after")
    def fold_deprecated_flat_fields(self) -> Self:
        """Copy deprecated flat settings into their groups."""
        fold_flat_fields(
            self,
            "TLS",
            GrpcTlsConfig,
            {
                "TLS_ENABLED": "IS_ENABLED",
                "TLS_CERT_FILE": "CERT_FILE",
                "TLS_KEY_FILE": "KEY_FILE",
                "TLS_CA_FILE": "CA_FILE",
                "TLS_REQUIRE_CLIENT_AUTH": "REQUIRE_CLIENT_AUTH",
            },
        )
        fold_flat_fields(
            self,
            "STUB_TLS",
            GrpcStubTlsConfig,
            {
                "STUB_TLS_ENABLED": "IS_ENABLED",
                "STUB_TLS_CA_FILE": "CA_FILE",
                "STUB_TLS_CERT_FILE": "CERT_FILE",
                "STUB_TLS_KEY_FILE": "KEY_FILE",
            },
        )
        return self

    @model_validator(mode="after")
    def resolve_thread_worker_count(self) -> Self:
        """Resolve worker thread count from CPU cores when not explicitly set.

        Returns:
            This model with ``THREAD_WORKER_COUNT`` set when it was ``None``.
        """
        if self.THREAD_WORKER_COUNT is not None:
            return self
        cores = os.cpu_count() or 1
        resolved = self.THREAD_PER_CPU_CORE * cores
        self.THREAD_WORKER_COUNT = resolved
        return self
