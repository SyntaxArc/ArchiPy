@needs-otel-collector
Feature: Pydantic AI OpenTelemetry instrumentation
  As a developer
  I want Pydantic AI agents to export their traces and metrics through ArchiPy
  So that agent runs, model requests and tool calls show up next to the rest of my telemetry

  Scenario: An agent run exports the run, model request and tool call spans
    Given Pydantic AI telemetry is exported to the collector
    When I run a Pydantic AI agent named "span-bot" that calls a tool named "ping"
    Then the collector should have the Pydantic AI span "invoke_agent span-bot"
    And the collector should have the Pydantic AI span "chat test"
    And the collector should have the Pydantic AI span "execute_tool ping"
    And the Pydantic AI model request span should be a child of the agent run span

  Scenario: A delegated agent run is traced inside the calling tool
    Given Pydantic AI telemetry is exported to the collector
    When I run a Pydantic AI agent named "parent-bot" whose tool "delegate" runs the agent "child-bot"
    Then the collector should have the Pydantic AI span "invoke_agent parent-bot"
    And the collector should have the Pydantic AI span "invoke_agent child-bot"
    And the Pydantic AI agent run "child-bot" should be a child of the tool call "delegate"
    And the Pydantic AI agent runs "parent-bot" and "child-bot" should share one trace

  Scenario: A delegated agent run is not counted in the parent run's token usage
    Given Pydantic AI telemetry is exported to the collector
    When I run a Pydantic AI agent named "parent-bot" whose tool "delegate" runs the agent "child-bot"
    Then the Pydantic AI agent run "parent-bot" should count only the input tokens of its own model requests
    And the Pydantic AI agent run "child-bot" should count its own input tokens

  Scenario: Agents running at the same time keep separate traces
    Given Pydantic AI telemetry is exported to the collector
    When I run 3 Pydantic AI agents at the same time
    Then the collector should have 3 Pydantic AI agent run spans in 3 different traces
    And each Pydantic AI model request span should be a child of its own agent run

  Scenario: Agents run one after another in one request share the request trace
    Given Pydantic AI telemetry is exported to the collector
    When I run two Pydantic AI agents one after another inside a span named "request"
    Then every Pydantic AI agent run span should be a child of the span "request"

  Scenario Outline: An agent run inside a <transport> request joins the request trace
    Given Pydantic AI telemetry is exported to the collector
    When I run a Pydantic AI agent named "request-bot" inside a <transport> request
    Then the Pydantic AI agent run "request-bot" should descend from the span "<span>"
    And the Pydantic AI model request span should be a child of the agent run span

    Examples:
      | transport  | span                         |
      | FastAPI    | GET /agent                   |
      | gRPC       | /test.TestService/TestMethod |
      | async gRPC | /test.TestService/TestMethod |

  Scenario: The agent run exports token usage metrics
    Given Pydantic AI telemetry is exported to the collector
    When I run a Pydantic AI agent named "metric-bot" that calls a tool named "ping"
    Then the collector should have the Pydantic AI metric "gen_ai.client.token.usage"

  Scenario: A failing tool marks its span as an error
    Given Pydantic AI telemetry is exported to the collector
    When I run a Pydantic AI agent named "fail-bot" whose tool "boom" raises an error
    Then the collector should have the Pydantic AI span "execute_tool boom" with error status

  Scenario: A streamed agent response exports the time to first chunk
    Given Pydantic AI telemetry is exported to the collector
    When I stream the response of a Pydantic AI agent named "stream-bot"
    Then the collector should have the Pydantic AI metric "gen_ai.client.operation.time_to_first_chunk"

  Scenario: Spans carry no prompt or tool content when the config turns it off
    Given the Pydantic AI config does not include Pydantic AI content
    And Pydantic AI telemetry is exported to the collector
    When I run a Pydantic AI agent named "private-bot" that calls a tool named "ping"
    Then no exported Pydantic AI span should carry the prompt or tool content

  Scenario: Spans carry the prompt and tool content by default
    Given Pydantic AI telemetry is exported to the collector
    When I run a Pydantic AI agent named "open-bot" that calls a tool named "ping"
    Then an exported Pydantic AI span should carry the prompt and tool content

  Scenario: The config can turn Pydantic AI instrumentation off
    Given the Pydantic AI config turns Pydantic AI instrumentation off
    When Pydantic AI telemetry is exported to the collector
    Then the library "pydantic_ai" should not be auto-instrumented

  Scenario: Instrumentation an application installed itself is left alone
    Given the application instruments all Pydantic AI agents itself
    When Pydantic AI telemetry is exported to the collector
    Then the application's Pydantic AI instrumentation should still be installed

  Scenario: Pydantic AI is not instrumented while OpenTelemetry is disabled
    Given OpenTelemetry has not been initialized
    When I run a Pydantic AI agent named "quiet-bot" that calls a tool named "ping"
    Then the library "pydantic_ai" should not be auto-instrumented

  @needs-apm-server @needs-apm-collector
  Scenario Outline: Pydantic AI spans reach Elastic APM Server <route>
    Given Pydantic AI telemetry is exported to Elastic APM Server <route>
    When I run a Pydantic AI agent named "apm-bot" that calls a tool named "ping"
    Then Elastic APM Server should store a "unknown" transaction named "invoke_agent apm-bot"
    And Elastic APM Server should store a "genai" span named "chat test"
    And Elastic APM Server should store a "app" span named "execute_tool ping"

    Examples:
      | route                 |
      | directly              |
      | through the collector |

  @needs-apm-server @needs-apm-collector
  Scenario Outline: An agent run inside a <transport> request is a span of the request transaction in Elastic APM Server <route>
    Given Pydantic AI telemetry is exported to Elastic APM Server <route>
    When I run a Pydantic AI agent named "request-bot" inside a <transport> request
    Then Elastic APM Server should store <transactions> "request" transactions named "<transaction>"
    And Elastic APM Server should store a "app" span named "invoke_agent request-bot"
    And Elastic APM Server should store a "genai" span named "chat test"

    Examples:
      | route                 | transport | transaction                  | transactions |
      | directly              | FastAPI   | GET /agent                   | 1            |
      | through the collector | FastAPI   | GET /agent                   | 1            |
      | directly              | gRPC      | /test.TestService/TestMethod | 2            |
      | through the collector | gRPC      | /test.TestService/TestMethod | 2            |
