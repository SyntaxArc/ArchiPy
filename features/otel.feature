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

  Scenario: BaseError with client http status leaves span OK
    Given a sync function decorated with trace_span that raises NotFoundError
    When I call the traced sync function and it fails with NotFoundError
    Then the recorded span status should be OK
    And the recorded span should include an exception event
