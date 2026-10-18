"""gRPC configuration."""

import os
from typing import Self

from pydantic import BaseModel, Field, model_validator


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

    SERVER_OPTIONS_CONFIG_LIST: list[tuple[str, int]] = Field(
        default=[
            # ── Message limits ──────────────────────────────────────────────
            ("grpc.max_metadata_size", 16 * 1024),  # 16KB  (default is 8KB)
            ("grpc.max_message_length", 128 * 1024 * 1024),  # 128MB
            ("grpc.max_receive_message_length", 128 * 1024 * 1024),
            ("grpc.max_send_message_length", 128 * 1024 * 1024),
            # ── Keepalive ───────────────────────────────────────────────────
            # Server rarely initiates pings; 2h is the standard default.
            ("grpc.keepalive_time_ms", 7_200_000),  # 2h
            ("grpc.keepalive_timeout_ms", 20_000),  # 20s
            ("grpc.keepalive_permit_without_calls", 1),  # allow pings on idle connections
            # ── Ping enforcement (server-side) ──────────────────────────────
            # Must be <= client keepalive_time_ms to avoid ENHANCE_YOUR_CALM.
            ("grpc.http2.min_recv_ping_interval_without_data_ms", 300_000),  # 5min
            ("grpc.http2.min_ping_interval_without_data_ms", 300_000),  # 5min
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.http2.max_ping_strikes", 2),
            # ── Connection lifetime ─────────────────────────────────────────
            ("grpc.max_connection_idle_ms", 600_000),  # 10min
            ("grpc.max_connection_age_ms", 1_800_000),  # 30min
            ("grpc.max_connection_age_grace_ms", 5_000),  # 5s graceful drain
        ],
        description="Server channel options",
    )

    STUB_OPTIONS_CONFIG_LIST: list[tuple[str, int | str]] = Field(
        default=[
            # ── Message limits ──────────────────────────────────────────────
            ("grpc.max_metadata_size", 16 * 1024),  # 16KB
            ("grpc.max_message_length", 128 * 1024 * 1024),  # 128MB
            ("grpc.max_receive_message_length", 128 * 1024 * 1024),
            ("grpc.max_send_message_length", 128 * 1024 * 1024),
            # ── Keepalive ───────────────────────────────────────────────────
            # 5min is the recommended minimum to avoid ENHANCE_YOUR_CALM / GOAWAY.
            # Also activates TCP_USER_TIMEOUT for fast dead-connection detection.
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
        description="Client stub channel options",
    )

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
