# features/elasticsearch.feature
@needs-otel-collector @needs-elasticsearch @needs-apm-server @needs-apm-collector
Feature: Elasticsearch Operations Testing with Elastic APM
  As a developer
  I want to test Elasticsearch operations using the adapter pattern
  So that I can ensure proper interaction with the Elasticsearch cluster through our standardized interface

  Background:
    Given an Elasticsearch cluster is running
    And document type "test-doc" is configured for index "test-index"

  Scenario Outline: Elasticsearch adapter spans reach Elastic APM Server <route>
    Given adapter spans are exported to Elastic APM Server <route>
    When I index and search a document through the Elasticsearch adapter
    Then Elastic APM Server should store a span of type "external" with subtype "http"

    Examples:
      | route                 |
      | directly              |
      | through the collector |
