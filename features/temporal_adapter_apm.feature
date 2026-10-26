@needs-temporal @needs-otel-collector @needs-apm-server @needs-apm-collector
Feature: Temporal Adapter Operations with Elastic APM
  As a developer
  I want to test Temporal adapter operations
  So that I can ensure reliable workflow orchestration functionality

  Background:
    Given a Temporal test container is running
    And a Temporal adapter is configured
    And a Temporal worker manager is configured

  Scenario Outline: Elastic APM Server shows Temporal activities as messaging transactions <route>
    Given Temporal traces are exported to Elastic APM Server <route>
    And a worker is started for task queue "otel-apm-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "apm"
    Then Elastic APM Server should store a "messaging" transaction named "RunActivity:greeting_activity"
    And Elastic APM Server should store a "messaging" transaction named "RunWorkflow:GreetingWorkflow"
    And Elastic APM Server should store a "messaging" transaction named "StartWorkflow:GreetingWorkflow"
    And Elastic APM Server should store a "messaging" span named "StartActivity:greeting_activity"

    Examples:
      | route                 |
      | directly              |
      | through the collector |

  Scenario Outline: Elastic APM Server shows the saga as linked messaging transactions <route>
    Given Temporal traces are exported to Elastic APM Server <route>
    And a worker is started for task queue "otel-apm-queue" with OrderSagaWorkflow
    When I start the order saga "apm-saga-1" with payment succeeding on attempt 3 and shipping failure false requiring approval
    And I wait for 1 seconds
    And I add the note "apm" to the order saga "apm-saga-1"
    And I query workflow "apm-saga-1" with query "get_state"
    And I send signal "approve" to workflow "apm-saga-1"
    Then the order saga "apm-saga-1" should end completed after steps reserve_inventory,charge_payment,ship_order,notify_customer with compensations none
    And Elastic APM Server should store a "messaging" transaction named "RunWorkflow:OrderSagaWorkflow"
    And Elastic APM Server should store a "messaging" transaction named "HandleUpdate:add_note"
    And Elastic APM Server should store a "messaging" transaction named "HandleSignal:approve"
    And Elastic APM Server should store a "messaging" transaction named "HandleQuery:get_state"
    And Elastic APM Server should store a "messaging" transaction named "ValidateUpdate:add_note"
    And Elastic APM Server should store a "messaging" transaction named "SignalWorkflow:approve"
    And Elastic APM Server should store a "messaging" transaction named "QueryWorkflow:get_state"
    And Elastic APM Server should store a "messaging" transaction named "StartWorkflowUpdate:add_note"
    And Elastic APM Server should store 3 "messaging" transactions named "RunActivity:charge_payment"
    And Elastic APM Server should store a "messaging" transaction named "RunWorkflow:NotificationWorkflow"
    And Elastic APM Server should store a "messaging" span named "StartChildWorkflow:NotificationWorkflow"

    Examples:
      | route                 |
      | directly              |
      | through the collector |

  Scenario Outline: Elastic APM Server stores Temporal SDK metrics <route>
    Given Temporal metrics and traces are exported to Elastic APM Server <route>
    And a worker is started for task queue "<task_queue>" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "metrics"
    Then Elastic APM Server should store the Temporal metric "temporal_workflow_completed" for task queue "<task_queue>"

    Examples:
      | route                 | task_queue              |
      | directly              | otel-apm-metrics-direct |
      | through the collector | otel-apm-metrics-via    |
