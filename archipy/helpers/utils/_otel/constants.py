"""Constants shared by the OpenTelemetry helpers."""

_DEFAULT_PROPAGATORS = ["tracecontext", "baggage"]

_DEFAULT_FLUSH_TIMEOUT_MS = 30_000
_INIT_RETRY_BACKOFF_SECONDS = 30.0
DURATION_HISTOGRAM_BUCKETS_S: tuple[float, ...] = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
    7.5,
    10.0,
)

_OTEL_INSTALL_HINT = 'OpenTelemetry requires the optional dependency. Install with: uv add "archipy[otel]"'
_OTEL_FASTAPI_HINT = 'FastAPI OTel instrumentation requires: uv add "archipy[otel,fastapi]"'
_OTEL_GRPC_HINT = 'gRPC OTel instrumentation requires: uv add "archipy[otel-grpc]"'
