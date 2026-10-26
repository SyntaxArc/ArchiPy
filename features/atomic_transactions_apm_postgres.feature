@needs-postgres @needs-apm-server @needs-apm-collector
Feature: SQLAlchemy Atomic Transactions with Elastic APM on PostgreSQL

  Scenario Outline: SQLAlchemy adapter spans reach Elastic APM Server <route>
    Given adapter spans are exported to Elastic APM Server <route>
    When I run a query through the <db_type> SQLAlchemy adapter
    Then Elastic APM Server should store a span of type "db" with subtype "<system>"

    Examples:
      | route                 | db_type  | system     |
      | directly              | postgres | postgresql |
      | through the collector | postgres | postgresql |
