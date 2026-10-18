@unit
Feature: OpenTelemetry configuration
  As an operator
  I want the OpenTelemetry settings to reach the SDK
  So that sampling, batching, resources and propagation follow my configuration

  Scenario Outline: The configured sampler is the one the tracer provider uses
    Given an OpenTelemetry config built from:
      """
      {
        "TRACES_SAMPLER": "<sampler>",
        "TRACES_SAMPLE_RATIO": 0.25
      }
      """
    When the tracer provider is built from the config
    Then the sampler description contains "<description>"

    Examples:
      | sampler                  | description                              |
      | always_on                | AlwaysOnSampler                          |
      | always_off               | AlwaysOffSampler                         |
      | traceidratio             | TraceIdRatioBased{0.25}                  |
      | parentbased_always_on    | ParentBased{root:AlwaysOnSampler         |
      | parentbased_always_off   | ParentBased{root:AlwaysOffSampler        |
      | parentbased_traceidratio | ParentBased{root:TraceIdRatioBased{0.25} |

  Scenario: The default sampler keeps the parent decision and samples a tenth of new traces
    Given an OpenTelemetry config built from:
      """
      {}
      """
    When the tracer provider is built from the config
    Then the sampler description contains "ParentBased{root:TraceIdRatioBased{0.1}"

  Scenario: The span batch settings reach the batch processor
    Given an OpenTelemetry config built from:
      """
      {
        "SPAN_BATCH_MAX_QUEUE_SIZE": 100,
        "SPAN_BATCH_MAX_EXPORT_BATCH_SIZE": 20,
        "SPAN_BATCH_SCHEDULE_DELAY_MS": 250,
        "SPAN_BATCH_EXPORT_TIMEOUT_MS": 900
      }
      """
    When the tracer provider is built from the config
    Then the span batch processor holds queue 100, batch 20, delay 250 and timeout 900

  Scenario: A batch larger than its queue is rejected
    Then building an OpenTelemetry config from the following fails with "batch_size_exceeds_queue_size":
      """
      {
        "SPAN_BATCH_MAX_QUEUE_SIZE": 10,
        "SPAN_BATCH_MAX_EXPORT_BATCH_SIZE": 20
      }
      """

  Scenario Outline: OTLP compression reaches the <protocol> exporters
    Given an OpenTelemetry config built from:
      """
      {
        "PROTOCOL": "<protocol>",
        "OTLP_COMPRESSION": "gzip"
      }
      """
    When the OTLP exporters are created from the config
    Then every OTLP exporter compresses with gzip

    Examples:
      | protocol      |
      | grpc          |
      | http/protobuf |

  Scenario: Exporters do not compress by default
    Given an OpenTelemetry config built from:
      """
      {}
      """
    When the OTLP exporters are created from the config
    Then no OTLP exporter compresses

  Scenario: The resource carries the service identity and the detected attributes
    Given an OpenTelemetry config built from:
      """
      {
        "SERVICE_NAME": "orders",
        "SERVICE_VERSION": "1.4.2",
        "SERVICE_INSTANCE_ID": "pod-7",
        "RESOURCE_ATTRIBUTES": {
          "team": "payments"
        }
      }
      """
    When the resource is created from the config
    Then the resource attribute "service.name" is "orders"
    And the resource attribute "service.version" is "1.4.2"
    And the resource attribute "service.instance.id" is "pod-7"
    And the resource attribute "team" is "payments"
    And the resource has the attributes "host.name, host.arch, os.type"
    And the resource has no attribute "process.pid"

  Scenario: The service instance id is generated when it is not configured
    Given an OpenTelemetry config built from:
      """
      {
        "SERVICE_NAME": "orders"
      }
      """
    When the resource is created from the config
    Then the resource has the attributes "service.instance.id"

  Scenario: The process detector is opt-in
    Given an OpenTelemetry config built from:
      """
      {
        "RESOURCE_DETECTORS": [
          "process"
        ]
      }
      """
    When the resource is created from the config
    Then the resource has the attributes "process.pid"
    And the resource has no attribute "host.name"

  Scenario: Explicit settings win over detected attributes
    Given an OpenTelemetry config built from:
      """
      {
        "RESOURCE_ATTRIBUTES": {
          "host.name": "pinned-host"
        }
      }
      """
    When the resource is created from the config
    Then the resource attribute "host.name" is "pinned-host"

  Scenario Outline: The propagators follow the configuration
    When the propagator is created for "<names>"
    Then the propagator carries the fields "<fields>"

    Examples:
      | names                | fields                                |
      | tracecontext,baggage | traceparent,tracestate,baggage        |
      | tracecontext         | traceparent,tracestate                |
      | b3                   | b3                                    |
      | b3multi              | x-b3-traceid,x-b3-spanid,x-b3-sampled |
      | none                 | (none)                                |

  Scenario: b3 propagation without its package names the extra
    Given the b3 propagator package is not installed
    Then creating the propagator for "b3" fails with "b3_propagator_missing"

  Scenario: The standard environment variables fill in unset settings
    Given an OpenTelemetry config built from:
      """
      {
        "USE_STANDARD_ENV": true
      }
      """
    And the standard OTEL environment:
      | name                           | value                 |
      | OTEL_EXPORTER_OTLP_ENDPOINT    | http://collector:4318 |
      | OTEL_EXPORTER_OTLP_PROTOCOL    | http/protobuf         |
      | OTEL_EXPORTER_OTLP_HEADERS     | a=b,c=d               |
      | OTEL_EXPORTER_OTLP_TIMEOUT     | 3                     |
      | OTEL_EXPORTER_OTLP_COMPRESSION | gzip                  |
      | OTEL_TRACES_SAMPLER            | traceidratio          |
      | OTEL_TRACES_SAMPLER_ARG        | 0.5                   |
      | OTEL_PROPAGATORS               | tracecontext          |
      | OTEL_BSP_MAX_QUEUE_SIZE        | 1000                  |
      | OTEL_BLRP_SCHEDULE_DELAY       | 250                   |
      | OTEL_METRIC_EXPORT_INTERVAL    | 15000                 |
      | OTEL_SERVICE_NAME              | env-service           |
    When the standard environment is applied
    Then the effective setting "OTLP_ENDPOINT" is "http://collector:4318/"
    And the effective setting "PROTOCOL" is "http/protobuf"
    And the effective setting "OTLP_HEADERS" is {"a": "b", "c": "d"}
    And the effective setting "TIMEOUT" is 3.0
    And the effective setting "OTLP_COMPRESSION" is "gzip"
    And the effective setting "TRACES_SAMPLER" is "traceidratio"
    And the effective setting "TRACES_SAMPLE_RATIO" is 0.5
    And the effective setting "PROPAGATORS" is ["tracecontext"]
    And the effective setting "SPAN_BATCH_MAX_QUEUE_SIZE" is 1000
    And the effective setting "LOG_BATCH_SCHEDULE_DELAY_MS" is 250
    And the effective setting "METRIC_EXPORT_INTERVAL_MS" is 15000
    And the effective setting "SERVICE_NAME" is "env-service"

  Scenario: An explicitly set field wins over the standard variable
    Given an OpenTelemetry config built from:
      """
      {
        "USE_STANDARD_ENV": true,
        "SERVICE_NAME": "explicit",
        "TRACES_SAMPLE_RATIO": 0.3
      }
      """
    And the standard OTEL environment:
      | name                    | value        |
      | OTEL_SERVICE_NAME       | env-service  |
      | OTEL_TRACES_SAMPLER     | traceidratio |
      | OTEL_TRACES_SAMPLER_ARG | 0.9          |
    When the standard environment is applied
    Then the effective setting "SERVICE_NAME" is "explicit"
    And the effective setting "TRACES_SAMPLE_RATIO" is 0.3
    And the effective setting "TRACES_SAMPLER" is "traceidratio"

  Scenario: The standard variables are ignored unless the config asks for them
    Given an OpenTelemetry config built from:
      """
      {}
      """
    And the standard OTEL environment:
      | name                        | value                 |
      | OTEL_EXPORTER_OTLP_ENDPOINT | http://collector:4318 |
    When the standard environment is applied
    Then the effective setting "OTLP_ENDPOINT" is "http://localhost:4317/"

  Scenario: Invalid standard values are ignored and the rest still apply
    Given an OpenTelemetry config built from:
      """
      {
        "USE_STANDARD_ENV": true
      }
      """
    And the standard OTEL environment:
      | name                           | value         |
      | OTEL_EXPORTER_OTLP_COMPRESSION | zstd          |
      | OTEL_TRACES_SAMPLER            | jaeger_remote |
      | OTEL_BSP_MAX_QUEUE_SIZE        | many          |
      | OTEL_BSP_SCHEDULE_DELAY        | 750           |
    When the standard environment is applied
    Then the effective setting "OTLP_COMPRESSION" is "none"
    And the effective setting "TRACES_SAMPLER" is "parentbased_traceidratio"
    And the effective setting "SPAN_BATCH_MAX_QUEUE_SIZE" is 2048
    And the effective setting "SPAN_BATCH_SCHEDULE_DELAY_MS" is 750

  Scenario: Values that are valid alone but invalid together are all ignored
    Given an OpenTelemetry config built from:
      """
      {
        "USE_STANDARD_ENV": true
      }
      """
    And the standard OTEL environment:
      | name                    | value |
      | OTEL_BSP_MAX_QUEUE_SIZE | 10    |
      | OTEL_BSP_SCHEDULE_DELAY | 750   |
    When the standard environment is applied
    Then the effective setting "SPAN_BATCH_MAX_QUEUE_SIZE" is 2048
    And the effective setting "SPAN_BATCH_SCHEDULE_DELAY_MS" is 5000

  Scenario Outline: OTEL_SDK_DISABLED switches OpenTelemetry off only for a config that reads the standard variables
    Given an OpenTelemetry config built from:
      """
      {"IS_ENABLED": true, "USE_STANDARD_ENV": <reads>}
      """
    And the standard OTEL environment:
      | name              | value   |
      | OTEL_SDK_DISABLED | <value> |
    Then the OpenTelemetry SDK is <state>

    Examples:
      | reads | value | state    |
      | true  | true  | disabled |
      | true  | True  | disabled |
      | true  | false | enabled  |
      | false | true  | enabled  |

  Scenario: The duration histogram buckets come from the configuration
    Given an OpenTelemetry config built from:
      """
      {
        "METRICS_DURATION_BUCKETS_S": [
          0.1,
          1.0,
          10.0
        ]
      }
      """
    Then the duration histogram buckets of the global config are 0.1, 1.0, 10.0

  Scenario Outline: Unsorted or non-positive duration buckets are rejected
    Then building an OpenTelemetry config from the following fails with "invalid_duration_buckets":
      """
      {"METRICS_DURATION_BUCKETS_S": <buckets>}
      """

    Examples:
      | buckets    |
      | [1.0, 0.5] |
      | [0, 1.0]   |
      | [1.0, 1.0] |
