@needs-mailpit @needs-mailpit-plain @needs-otel-collector @needs-apm-server @needs-apm-collector
Feature: Email adapter with Elastic APM

  Background:
    Given an empty Mailpit mailbox

  Scenario Outline: httpx2 client spans reach Elastic APM Server <route>
    Given adapter spans are exported to Elastic APM Server <route>
    When I call the Mailpit API with httpx2
    Then Elastic APM Server should store a span of type "external" with subtype "http"

    Examples:
      | route                 |
      | directly              |
      | through the collector |
