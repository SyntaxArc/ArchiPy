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
    And a histogram metric named "otel.grpc.testmethod.duration" should have datapoints

  Scenario: gRPC OTel interceptor is prepended without dropping existing interceptors
    When I setup the gRPC OTel interceptor on a list with a sentinel interceptor
    Then the OTel interceptor should be first and the sentinel should remain

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

  Scenario: distributed gRPC calls gRPC share one trace
    When gRPC upstream calls gRPC downstream TestMethod
    Then all finished spans should share one trace id
    And at least 2 spans named "/test.TestService/TestMethod" should be recorded

  Scenario: distributed gRPC calls FastAPI share one trace
    When gRPC upstream calls FastAPI downstream over HTTP
    Then all finished spans should share one trace id
    And a span named "/test.TestService/TestMethod" should be recorded
    And a span named "GET /from-grpc" should be recorded
