Feature: OpenTelemetry decorators
  As a developer
  I want tracing and metrics decorators backed by OpenTelemetry
  So that spans and instruments are recorded for observability

  Background:
    Given OpenTelemetry is configured for testing

  Scenario: trace_span creates a span with the expected name
    Given a sync function decorated with trace_span named "load_user"
    When I call the traced sync function
    Then a span named "load_user" should be recorded

  @async
  Scenario: async_trace_span creates a span
    Given an async function decorated with async_trace_span named "load_user_async"
    When I call the traced async function
    Then a span named "load_user_async" should be recorded

  Scenario: capture_args records named arguments as span attributes
    Given a sync function decorated with trace_span that captures arg "user_id"
    When I call the traced sync function with user_id 42
    Then the recorded span should have attribute "user_id" equal to 42

  Scenario: on exception the span status is ERROR
    Given a sync function decorated with trace_span that raises an error
    When I call the traced sync function and it fails
    Then the recorded span status should be ERROR
    And the recorded span should include an exception event

  Scenario: trace_root starts a new root trace
    Given an ambient parent span is active
    And a sync function decorated with trace_root named "root_work"
    When I call the traced root function under the ambient parent
    Then the root span trace id should differ from the ambient parent trace id

  Scenario: trace_class wraps public methods only
    Given a class decorated with trace_class
    When I call the public method and the private method on the traced class
    Then a span named "TracedService.public_method" should be recorded
    And no span named "TracedService._private_method" should be recorded

  Scenario: measure_duration records histogram datapoints
    Given a sync function decorated with measure_duration named "test.work.duration"
    When I call the measured sync function
    Then a histogram metric named "test.work.duration" should have datapoints

  Scenario: count_calls records counter datapoints
    Given a sync function decorated with count_calls named "test.work.calls"
    When I call the counted sync function
    Then a counter metric named "test.work.calls" should have datapoints

  Scenario: capture_exception records exception on current span
    Given an active recording span named "manual_span"
    When I capture an exception on the current span
    Then the recorded span should include an exception event
    And the recorded span status should be ERROR

  Scenario: when OTel is disabled trace_span is a no-op
    Given OpenTelemetry is disabled for testing
    And a sync function decorated with trace_span named "noop_span"
    When I call the traced sync function
    Then no span named "noop_span" should be recorded

  Scenario: BaseError with client http status leaves span UNSET
    Given a sync function decorated with trace_span that raises NotFoundError
    When I call the traced sync function and it fails with NotFoundError
    Then the recorded span status should be UNSET
    And the recorded span should include an exception event
    And the recorded span should have exactly 1 exception event

  Scenario: failing span records exactly one exception event
    Given a sync function decorated with trace_span that raises an error
    When I call the traced sync function and it fails
    Then the recorded span should have exactly 1 exception event

  Scenario: metrics survive provider reset and reconfigure
    Given a sync function decorated with measure_duration named "test.reset.duration"
    When I call the measured sync function
    And I reset and reconfigure OpenTelemetry for testing
    And I call the measured sync function again
    Then a histogram metric named "test.reset.duration" should have datapoints

  Scenario: capture_args redacts password arguments
    Given a sync function decorated with trace_span that captures arg "password"
    When I call the traced sync function with password "s3cret"
    Then the recorded span should have attribute "password" equal to "***"

  Scenario: sync measure_duration rejects coroutine functions
    When I apply measure_duration to an async function
    Then an InvalidArgumentError should be raised for decorator "measure_duration"

  Scenario: http protobuf resolves signal paths on OTLP endpoint
    When I resolve OTLP endpoints for protocol "http/protobuf" with base "http://localhost:4318"
    Then the traces endpoint should be "http://localhost:4318/v1/traces"
    And the metrics endpoint should be "http://localhost:4318/v1/metrics"
    And the logs endpoint should be "http://localhost:4318/v1/logs"

  Scenario: per-signal endpoint override wins over base
    When I resolve OTLP metrics endpoint for protocol "http/protobuf" with base "http://localhost:4318" overridden to "http://collector:4318/v1/metrics"
    Then the metrics endpoint should be "http://collector:4318/v1/metrics"

  Scenario: grpc keeps base endpoint without signal path
    When I resolve OTLP endpoints for protocol "grpc" with base "http://localhost:4317"
    Then the traces endpoint should be "http://localhost:4317"
    And the metrics endpoint should be "http://localhost:4317"

  Scenario: resource attributes include service name and environment
    Given OpenTelemetry providers are built with service name "archipy-bdd" and environment "test"
    Then the tracer provider resource should include "service.name" equal to "archipy-bdd"
    And the tracer provider resource should include "deployment.environment.name" equal to "test"

  Scenario: sample ratio zero drops all spans
    Given OpenTelemetry is configured for testing with sample ratio 0.0
    And a sync function decorated with trace_span named "unsampled_span"
    When I call the traced sync function
    Then no span named "unsampled_span" should be recorded

  Scenario: threading instrumentor propagates span context
    When I run a traced function inside a worker thread under an ambient parent
    Then the worker span should share the ambient parent trace id

  Scenario: FastAPI request records HTTP span and server metrics
    When I create an instrumented FastAPI app and GET "/otel-ping"
    Then a span named "GET /otel-ping" should be recorded
    And an HTTP server duration metric should have datapoints

  Scenario: gRPC request records RPC span and handler metrics
    When I call an instrumented gRPC TestMethod
    Then a span named "/test.TestService/TestMethod" should be recorded
    And a histogram metric named "rpc.server.duration" should have datapoints

  @async
  Scenario: async gRPC request records RPC span and handler metrics
    When I call an instrumented async gRPC TestMethod
    Then a span named "/test.TestService/TestMethod" should be recorded
    And a histogram metric named "rpc.server.duration" should have datapoints

  Scenario: gRPC OTel interceptor is prepended without dropping existing interceptors
    When I setup the gRPC OTel interceptor on a list with a sentinel interceptor
    Then the OTel interceptor should be first and the sentinel should remain

  @async
  Scenario: async gRPC OTel interceptor is prepended without dropping existing interceptors
    When I setup the async gRPC OTel interceptor on a list with a sentinel interceptor
    Then the OTel interceptor should be first and the sentinel should remain

  Scenario: metrics-only gRPC records RPC duration without span
    Given OpenTelemetry metrics-only mode for testing
    When I call an instrumented gRPC TestMethod
    Then no span named "/test.TestService/TestMethod" should be recorded
    And a histogram metric named "rpc.server.duration" should have datapoints

  @async
  Scenario: metrics-only async gRPC records RPC duration without span
    Given OpenTelemetry metrics-only mode for testing
    When I call an instrumented async gRPC TestMethod
    Then no span named "/test.TestService/TestMethod" should be recorded
    And a histogram metric named "rpc.server.duration" should have datapoints

  Scenario: measure_duration records ok status for client BaseError
    Given a sync function decorated with measure_duration named "test.notfound.duration" that raises NotFoundError
    When I call the measured sync function and it fails with NotFoundError
    Then a histogram metric named "test.notfound.duration" should have status "ok"

  Scenario: system metrics stay off when SYSTEM_METRICS_ENABLED is false
    Given OpenTelemetry is configured for production init with system metrics disabled
    When I initialize OpenTelemetry providers from config
    Then system CPU metric instruments should be absent

  Scenario: metrics pull scrape exposes recorded histogram
    Given OpenTelemetry is configured for pull-only metrics on an ephemeral port
    When I initialize OpenTelemetry providers from config
    And I call a measured sync function named "test.pull.duration"
    Then the metrics pull scrape endpoint should return 200 containing "test_pull_duration"

  Scenario: metrics pull disabled leaves scrape port closed
    Given OpenTelemetry is configured for OTLP-only metrics with pull port reserved
    When I initialize OpenTelemetry providers from config
    Then the metrics pull scrape port should refuse connections

  Scenario: invalid METRICS_EXPORTER is rejected
    When I build OpentelemetryConfig with METRICS_EXPORTER "both"
    Then a ValidationError should be raised for field "METRICS_EXPORTER"

  Scenario: metrics pull init is idempotent
    Given OpenTelemetry is configured for pull-only metrics on an ephemeral port
    When I initialize OpenTelemetry providers from config twice
    Then the metrics pull scrape endpoint should return 200

  Scenario: metrics pull shutdown stops scrape
    Given OpenTelemetry is configured for pull-only metrics on an ephemeral port
    When I initialize OpenTelemetry providers from config
    And I shut down OpenTelemetry providers
    Then the metrics pull scrape port should refuse connections

  Scenario: metrics pull scrape bind failure keeps providers
    Given OpenTelemetry is configured for pull metrics on a busy port with traces enabled
    When I initialize OpenTelemetry providers from config
    Then the OpenTelemetry meter provider should be available
    And the OpenTelemetry tracer provider should be available
    And the metrics registry should be available
    And the metrics pull scrape port should refuse connections

  Scenario: metrics pushgateway pushes and deletes on shutdown
    Given OpenTelemetry is configured for pushgateway metrics with a stub gateway
    When I initialize OpenTelemetry providers from config
    And I wait for a Pushgateway push
    Then the Pushgateway should have received a push for job "archipy-pushgateway-bdd"
    And the metrics pull scrape port should refuse connections
    When I shut down OpenTelemetry providers
    Then the Pushgateway should have received a delete for job "archipy-pushgateway-bdd"

  Scenario: metrics pushgateway push failure keeps providers
    Given OpenTelemetry is configured for pushgateway metrics with a failing stub gateway
    When I initialize OpenTelemetry providers from config
    And I wait for a Pushgateway push attempt
    Then the OpenTelemetry meter provider should be available
    And the metrics registry should be available

  Scenario: Temporal connect attaches TracingInterceptor and resolved metrics endpoint
    When I connect a Temporal adapter with OTel enabled using a mocked Client
    Then the Temporal connect kwargs should include a TracingInterceptor
    And the Temporal runtime should receive metrics endpoint "http://localhost:4318/v1/metrics"

  Scenario: Temporal TracingInterceptor append preserves caller interceptors
    When I append a Temporal TracingInterceptor to connect kwargs that already have a sentinel
    Then the Temporal connect kwargs should keep the sentinel and include a TracingInterceptor

  Scenario: distributed FastAPI calls FastAPI share one trace
    When FastAPI upstream calls FastAPI downstream over HTTP
    Then all finished spans should share one trace id
    And a span named "GET /call-fa" should be recorded
    And a span named "GET /downstream" should be recorded

  Scenario: distributed FastAPI calls gRPC share one trace
    When FastAPI upstream calls gRPC TestMethod
    Then all finished spans should share one trace id
    And a span named "GET /call-grpc" should be recorded
    And a span named "/test.TestService/TestMethod" should be recorded
    And the span named "/test.TestService/TestMethod" should descend from span "GET /call-grpc"

  Scenario: distributed gRPC calls gRPC share one trace
    When gRPC upstream calls gRPC downstream TestMethod
    Then all finished spans should share one trace id
    And at least 2 spans named "/test.TestService/TestMethod" should be recorded

  Scenario: distributed gRPC calls FastAPI share one trace
    When gRPC upstream calls FastAPI downstream over HTTP
    Then all finished spans should share one trace id
    And a span named "/test.TestService/TestMethod" should be recorded
    And a span named "GET /from-grpc" should be recorded

  Scenario: traces disabled leaves decorator as no-op
    Given OpenTelemetry metrics-only mode for testing
    And a sync function decorated with trace_span named "metrics_only_span"
    When I call the traced sync function
    Then no span named "metrics_only_span" should be recorded

  Scenario: capture_args survives failing repr
    Given a sync function decorated with trace_span that captures a broken repr arg
    When I call the traced sync function with a broken repr object
    Then the recorded span should have attribute "payload" equal to "<unreprable>"

  Scenario: static password attribute is redacted
    Given a sync function decorated with trace_span and static attribute password "s3cret"
    When I call the traced sync function
    Then the recorded span should have attribute "password" equal to "***"

  @async
  Scenario: async cancellation records cancelled metric status
    Given an async function decorated with async_measure_duration named "test.cancel.duration"
    When I cancel the measured async function
    Then a histogram metric named "test.cancel.duration" should have status "cancelled"

  @async
  Scenario: async cancellation sets span ERROR status
    Given an async function decorated with async_trace_span named "cancel_span"
    When I cancel the traced async function
    Then the recorded span status should be ERROR

  Scenario: force_flush succeeds for in-memory providers
    When I force flush OpenTelemetry providers
    Then OpenTelemetry force flush should succeed

  Scenario: shutdown is idempotent and clears owned providers
    When I shut down OpenTelemetry providers twice
    Then OpenTelemetry tracer provider should be absent

  Scenario: adopted global tracer is preserved on shutdown
    Given OpenTelemetry is configured for testing with a borrowed tracer provider
    When I shut down OpenTelemetry providers
    Then the borrowed TracerProvider should still be usable

  Scenario: partial exporter failure does not publish providers
    When OpenTelemetry initialization fails while creating the metric exporter
    Then OpenTelemetry should not be marked initialized
    And OpenTelemetry meter provider should be absent

  Scenario: missing dependency is a decorator no-op
    Given OpenTelemetry import failure is simulated
    And a sync function decorated with trace_span named "missing_dep_span"
    When I call the traced sync function
    Then no span named "missing_dep_span" should be recorded
    And the traced sync function result should be "ok"

  Scenario: logs are exported through the logging handler
    Given OpenTelemetry is configured for testing with log export
    When I emit an INFO log message "otel-log-probe"
    Then a log record containing "otel-log-probe" should be exported

  Scenario: log record carries active span context
    Given OpenTelemetry is configured for testing with log export
    And an ambient parent span is active
    When I emit an INFO log message "otel-log-with-trace"
    Then a log record containing "otel-log-with-trace" should carry the ambient parent trace id and span id

  Scenario: invalid LOGS_EXPORTER is rejected
    When I build OpentelemetryConfig with LOGS_EXPORTER "both"
    Then a ValidationError should be raised for field "LOGS_EXPORTER"

  Scenario: console log exporter writes INFO to stdout
    Given OpenTelemetry is configured for console log export with captured streams
    When I emit an INFO log message "otel-console-info"
    Then the captured stdout should contain "otel-console-info"
    And the captured stderr should not contain "otel-console-info"

  Scenario: console log exporter writes WARNING to stderr
    Given OpenTelemetry is configured for console log export with captured streams
    When I emit a WARNING log message "otel-console-warn"
    Then the captured stderr should contain "otel-console-warn"
    And the captured stdout should not contain "otel-console-warn"

  Scenario: post-fork state rebuilds owned providers
    Given OpenTelemetry is configured for testing
    When I simulate a process fork after OpenTelemetry init
    And I re-initialize OpenTelemetry after the simulated fork
    Then OpenTelemetry should be marked initialized

  Scenario: invalid OTEL config with no signals is rejected
    When I build OpentelemetryConfig with IS_ENABLED true and all signals false
    Then a ConfigurationError should be raised for operation "otel"

  Scenario: invalid LOGS_LEVEL is rejected
    When I build OpentelemetryConfig with LOGS_LEVEL "VERBOSE"
    Then a ConfigurationError should be raised for operation "otel"

  Scenario: concurrent histogram creation is thread-safe
    Given a sync function decorated with measure_duration named "test.concurrent.duration"
    When I call the measured sync function from 8 threads concurrently
    Then a histogram metric named "test.concurrent.duration" should have datapoints

  Scenario: traces disabled FastAPI request records no HTTP span
    Given OpenTelemetry metrics-only mode for testing
    When I create an instrumented FastAPI app and GET "/otel-ping"
    Then no span named "GET /otel-ping" should be recorded

  Scenario: missing tracer provider skips gRPC OTel interceptor
    Given OpenTelemetry import failure is simulated
    When I setup the gRPC OTel interceptor on a list with a sentinel interceptor
    Then the interceptor list should contain only the sentinel

  Scenario: FastAPI lifespan shutdown clears OTel providers
    When I run FastAPI lifespan startup and shutdown
    Then OpenTelemetry force flush should have been invoked during lifespan exit

  Scenario: auto-instrumentation covers httpx2 clients
    When I run auto-instrumentation of installed libraries
    Then the library "httpx2" should be auto-instrumented
    And httpx2 transports should be wrapped by OpenTelemetry
    And no OpenTelemetry instrumentor error should be logged

  Scenario: missing instrumented library is skipped without error log
    Given the httpx instrumentor reports its target library as missing
    When I run auto-instrumentation of installed libraries
    Then the library "httpx" should not be auto-instrumented
    And the library "httpx2" should be auto-instrumented
    And no OpenTelemetry instrumentor error should be logged
