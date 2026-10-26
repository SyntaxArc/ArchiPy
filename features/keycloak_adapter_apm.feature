# features/keycloak_auth.feature
@needs-keycloak @needs-envoy @needs-otel-collector @needs-apm-server @needs-apm-collector
Feature: Keycloak Authentication Testing with Elastic APM
  As a developer
  I want to test Keycloak authentication operations
  So that I can ensure secure authentication and management operations

  @tracing
  Scenario Outline: Keycloak <mode> adapter spans reach Elastic APM Server <route>
    Given adapter spans are exported to Elastic APM Server <route>
    And a configured <mode> Keycloak adapter via <via>
    When I create a realm named "span-realm" with display name "Span Realm" using <mode> adapter
    Then Elastic APM Server should store a span of type "external" with subtype "http"

    Examples:
      | route                 | mode  | via    |
      | directly              | sync  | direct |
      | directly              | async | direct |
      | through the collector | sync  | direct |
      | through the collector | async | direct |
      | directly              | sync  | envoy  |
      | directly              | async | envoy  |
      | through the collector | sync  | envoy  |
      | through the collector | async | envoy  |
