# features/kafka_operations.feature
@needs-kafka @needs-apm-server @needs-apm-collector
Feature: Kafka Adapter Operations Testing with Elastic APM
  As a developer
  I want to test Kafka adapter operations
  So that I can ensure reliable messaging functionality

  Background:
    Given a configured Kafka admin adapter

  Scenario Outline: Kafka adapter spans reach Elastic APM Server <route>
    Given adapter spans are exported to Elastic APM Server <route>
    When I produce and consume a message on topic "apm-topic" through the Kafka adapters
    Then Elastic APM Server should store a transaction of type "messaging"

    Examples:
      | route                 |
      | directly              |
      | through the collector |

  @async
  Scenario Outline: Async Kafka adapter spans reach Elastic APM Server <route>
    Given adapter spans are exported to Elastic APM Server <route>
    When I produce and consume a message on topic "apm-topic-async" through the async Kafka adapters
    Then Elastic APM Server should store a transaction of type "messaging"

    Examples:
      | route                 |
      | directly              |
      | through the collector |
