@needs-redis @needs-redis-cluster @needs-apm-server @needs-apm-collector
Feature: Redis Testing with Elastic APM
  As a developer
  I want to test Redis operations with both mocks and real containers
  So that I can ensure compatibility and reliability across different environments

  Background:
    Given test entities are defined

  Scenario Outline: Redis adapter spans reach Elastic APM Server <route>
    Given adapter spans are exported to Elastic APM Server <route>
    When I set and get a key through the Redis adapter
    Then Elastic APM Server should store a span of type "db" with subtype "redis"

    Examples:
      | route                 |
      | directly              |
      | through the collector |

  @async
  Scenario Outline: Async Redis adapter spans reach Elastic APM Server <route>
    Given adapter spans are exported to Elastic APM Server <route>
    When I set and get a key through the async Redis adapter
    Then Elastic APM Server should store a span of type "db" with subtype "redis"

    Examples:
      | route                 |
      | directly              |
      | through the collector |
