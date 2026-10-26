@needs-vault @needs-apm-server @needs-apm-collector
Feature: Vault Adapter with Elastic APM
  As a developer
  I want to use the Vault adapter for secret and transit operations
  So that applications can manage secrets and encryption at runtime

  Background:
    Given a configured Vault adapter

  Scenario Outline: Vault client spans reach Elastic APM Server <route>
    Given adapter spans are exported to Elastic APM Server <route>
    When I call the Vault API with requests
    Then Elastic APM Server should store a span of type "external" with subtype "http"

    Examples:
      | route                 |
      | directly              |
      | through the collector |
