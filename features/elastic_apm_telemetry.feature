@needs-apm-server @needs-apm-collector
Feature: Elastic APM telemetry
  As a developer
  I want metrics and logs to reach Elastic APM Server
  So that Elasticsearch holds every signal the application exports, directly or through a collector

  Scenario Outline: A counter metric reaches Elastic APM Server <route>
    Given OpenTelemetry traces, metrics and logs are exported to Elastic APM Server <route>
    And a sync function decorated with count_calls named "apm.work.calls"
    When I call the counted sync function
    Then Elastic APM Server should store the metric "apm.work.calls"

    Examples:
      | route                 |
      | directly              |
      | through the collector |

  Scenario Outline: A duration metric reaches Elastic APM Server <route>
    Given OpenTelemetry traces, metrics and logs are exported to Elastic APM Server <route>
    And a sync function decorated with measure_duration named "apm.work.duration"
    When I call the measured sync function
    Then Elastic APM Server should store the metric "apm.work.duration"

    Examples:
      | route                 |
      | directly              |
      | through the collector |

  Scenario Outline: A log record reaches Elastic APM Server with its trace id <route>
    Given OpenTelemetry traces, metrics and logs are exported to Elastic APM Server <route>
    When I log "apm-log-probe" inside a traced function
    Then Elastic APM Server should store the log "apm-log-probe" correlated with that trace

    Examples:
      | route                 |
      | directly              |
      | through the collector |

  Scenario Outline: gRPC server metrics reach Elastic APM Server <route>
    Given OpenTelemetry traces, metrics and logs are exported to Elastic APM Server <route>
    When I call an instrumented gRPC TestMethod
    Then Elastic APM Server should store the metric "rpc.server.call.duration"

    Examples:
      | route                 |
      | directly              |
      | through the collector |

  Scenario Outline: FastAPI server metrics reach Elastic APM Server <route>
    Given OpenTelemetry traces, metrics and logs are exported to Elastic APM Server <route>
    When I create an instrumented FastAPI app and GET "/otel-ping"
    Then Elastic APM Server should store the metric "http.server.request.duration"

    Examples:
      | route                 |
      | directly              |
      | through the collector |
