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

  Scenario: Exporters compress with gzip by default
    Given an OpenTelemetry config built from:
      """
      {}
      """
    When the OTLP exporters are created from the config
    Then every OTLP exporter compresses with gzip

  Scenario: Exporters do not compress when asked not to
    Given an OpenTelemetry config built from:
      """
      {
        "OTLP_COMPRESSION": "none"
      }
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

  Scenario Outline: B3 context sent as <header> continues the trace on a FastAPI route
    Given the global propagator is set to "<propagator>"
    And a tracer provider that keeps its spans in memory
    When a FastAPI route with native telemetry receives the header <header> "<value>"
    Then the server span continues trace "0af7651916cd43dd8448eb211c80319c" from parent span "b7ad6b7169203331"

    Examples:
      | propagator   | header      | value                                                   |
      | b3           | b3          | 0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-1     |
      | tracecontext | traceparent | 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01 |

  Scenario Outline: A sync gRPC call carries the trace in <header> headers
    Given the global propagator is set to "<propagator>"
    And a tracer provider that keeps its spans in memory
    When a gRPC client with the OpenTelemetry interceptor calls a server with the OpenTelemetry interceptor
    Then the gRPC server received the header "<header>" and not "<other>"
    And the gRPC server span belongs to the trace of the client span

    Examples:
      | propagator   | header      | other       |
      | b3           | b3          | traceparent |
      | tracecontext | traceparent | b3          |

  Scenario Outline: An async gRPC call carries the trace in <header> headers
    Given the global propagator is set to "<propagator>"
    And a tracer provider that keeps its spans in memory
    When an async gRPC client with the OpenTelemetry interceptor calls an async server with the OpenTelemetry interceptor
    Then the gRPC server received the header "<header>" and not "<other>"
    And the gRPC server span belongs to the trace of the client span

    Examples:
      | propagator   | header      | other       |
      | b3           | b3          | traceparent |
      | tracecontext | traceparent | b3          |

  Scenario Outline: A trace sent to FastAPI as <header> continues through the <route> gRPC call
    Given the global propagator is set to "<propagator>"
    And a tracer provider that keeps its spans in memory
    When the FastAPI app that calls gRPC servers and an HTTP service is requested at "<route>" with the header <header> "<value>"
    Then every recorded span belongs to trace "0af7651916cd43dd8448eb211c80319c"
    And a gRPC server span was recorded

    Examples:
      | propagator   | header      | value                                                   | route              |
      | b3           | b3          | 0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-1     | /def-sync-client   |
      | b3           | b3          | 0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-1     | /async-aio-client  |
      | b3           | b3          | 0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-1     | /async-sync-client |
      | b3           | b3          | 0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-1     | /def-aio-client    |
      | tracecontext | traceparent | 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01 | /def-sync-client   |
      | tracecontext | traceparent | 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01 | /async-aio-client  |
      | tracecontext | traceparent | 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01 | /async-sync-client |
      | tracecontext | traceparent | 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01 | /def-aio-client    |

  Scenario Outline: A trace sent to FastAPI as <header> reaches an outbound <route> request in the same format
    Given the global propagator is set to "<propagator>"
    And a tracer provider that keeps its spans in memory
    When the FastAPI app that calls gRPC servers and an HTTP service is requested at "<route>" with the header <header> "<value>"
    Then every recorded span belongs to trace "0af7651916cd43dd8448eb211c80319c"
    And the outbound HTTP request carried the header "<header>" and not "<other>"

    Examples:
      | propagator   | header      | other       | value                                                   | route   |
      | b3           | b3          | traceparent | 0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-1     | /httpx  |
      | b3           | b3          | traceparent | 0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-1     | /httpx2 |
      | tracecontext | traceparent | b3          | 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01 | /httpx  |
      | tracecontext | traceparent | b3          | 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01 | /httpx2 |

  Scenario: b3 propagation without its package names the install hint
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
      | OTEL_EXPORTER_OTLP_COMPRESSION | none                  |
      | OTEL_TRACES_SAMPLER            | traceidratio          |
      | OTEL_TRACES_SAMPLER_ARG        | 0.5                   |
      | OTEL_PROPAGATORS               | tracecontext          |
      | OTEL_BSP_MAX_QUEUE_SIZE        | 2000                  |
      | OTEL_BLRP_SCHEDULE_DELAY       | 250                   |
      | OTEL_METRIC_EXPORT_INTERVAL    | 15000                 |
      | OTEL_SERVICE_NAME              | env-service           |
    When the standard environment is applied
    Then the effective setting "OTLP_ENDPOINT" is "http://collector:4318/"
    And the effective setting "PROTOCOL" is "http/protobuf"
    And the effective setting "OTLP_HEADERS" is {"a": "b", "c": "d"}
    And the effective setting "TIMEOUT" is 3.0
    And the effective setting "OTLP_COMPRESSION" is "none"
    And the effective setting "TRACES_SAMPLER" is "traceidratio"
    And the effective setting "TRACES_SAMPLE_RATIO" is 0.5
    And the effective setting "PROPAGATORS" is ["tracecontext"]
    And the effective setting "SPAN_BATCH_MAX_QUEUE_SIZE" is 2000
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
    Then the effective setting "OTLP_COMPRESSION" is "gzip"
    And the effective setting "TRACES_SAMPLER" is "parentbased_traceidratio"
    And the effective setting "SPAN_BATCH_MAX_QUEUE_SIZE" is 4096
    And the effective setting "SPAN_BATCH_SCHEDULE_DELAY_MS" is 750

  Scenario: Values that are valid alone but invalid together are all ignored
    Given an OpenTelemetry config built from:
      """
      {
        "USE_STANDARD_ENV": true,
        "SPAN_BATCH_MAX_EXPORT_BATCH_SIZE": 500
      }
      """
    And the standard OTEL environment:
      | name                    | value |
      | OTEL_BSP_MAX_QUEUE_SIZE | 10    |
      | OTEL_BSP_SCHEDULE_DELAY | 750   |
    When the standard environment is applied
    Then the effective setting "SPAN_BATCH_MAX_QUEUE_SIZE" is 4096
    And the effective setting "SPAN_BATCH_SCHEDULE_DELAY_MS" is 5000

  Scenario Outline: Lowering only the <signal> queue size shrinks the unset batch size with it
    Given an OpenTelemetry config built from:
      """
      {
        "<queue_field>": 100
      }
      """
    Then the config setting "<batch_field>" is 100
    And the config setting "<other_batch_field>" is 512

    Examples:
      | signal | queue_field               | batch_field                      | other_batch_field                |
      | span   | SPAN_BATCH_MAX_QUEUE_SIZE | SPAN_BATCH_MAX_EXPORT_BATCH_SIZE | LOG_BATCH_MAX_EXPORT_BATCH_SIZE  |
      | log    | LOG_BATCH_MAX_QUEUE_SIZE  | LOG_BATCH_MAX_EXPORT_BATCH_SIZE  | SPAN_BATCH_MAX_EXPORT_BATCH_SIZE |

  Scenario: A queue size from the standard environment shrinks the unset batch size too
    Given an OpenTelemetry config built from:
      """
      {
        "USE_STANDARD_ENV": true
      }
      """
    And the standard OTEL environment:
      | name                    | value |
      | OTEL_BSP_MAX_QUEUE_SIZE | 100   |
    When the standard environment is applied
    Then the effective setting "SPAN_BATCH_MAX_QUEUE_SIZE" is 100
    And the effective setting "SPAN_BATCH_MAX_EXPORT_BATCH_SIZE" is 100

  Scenario Outline: The <setting> OTLP export is <state> on the wire
    Given an OpenTelemetry config built from:
      """
      {
        "PROTOCOL": "http/protobuf",
        "OTLP_COMPRESSION": "<setting>"
      }
      """
    When the HTTP span exporter of the config sends one span to a local collector
    Then the collector received a valid trace request <state>

    Examples:
      | setting | state        |
      | gzip    | gzip-encoded |
      | none    | unencoded    |

  Scenario: gRPC gzip compression shrinks what crosses the wire
    Given an OpenTelemetry config built from:
      """
      {}
      """
    And a gRPC trace collector behind a byte-counting proxy
    When the gRPC span exporter of the config sends 200 spans through the proxy with compression "none"
    And the gRPC span exporter of the config sends 200 spans through the proxy with compression "gzip"
    Then the gzip export sent less than 0.7 of the bytes of the uncompressed export

  Scenario: A full default batch of error spans stays under the gRPC message limit
    Given an OpenTelemetry config built from:
      """
      {}
      """
    Then a full default batch of spans with 25 attributes and a 4000 character stack trace each encodes to under 4 MiB
    And gzip makes that batch at least 1.5 times smaller

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
