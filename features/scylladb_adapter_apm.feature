@needs-apm-server @needs-apm-collector
Feature: ScyllaDB Adapter with Elastic APM
  As a developer
  I want to interact with ScyllaDB using the adapter
  So that I can perform database operations in a consistent manner

  Background:
    Given a ScyllaDB test container is running

  @needs-scylladb
  Scenario Outline: ScyllaDB adapter spans reach Elastic APM Server <route>
    Given adapter spans are exported to Elastic APM Server <route>
    When I run a query through the ScyllaDB adapter
    Then Elastic APM Server should store a span of type "db" with subtype "cassandra"

    Examples:
      | route                 |
      | directly              |
      | through the collector |
