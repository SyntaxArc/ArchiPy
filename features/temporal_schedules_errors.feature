@needs-temporal @needs-otel-collector
Feature: Temporal Schedules, Timeouts and Errors
  As a developer
  I want to test Temporal adapter operations
  So that I can ensure reliable workflow orchestration functionality

  Background:
    Given a Temporal test container is running
    And a Temporal adapter is configured
    And a Temporal worker manager is configured

  # Schedule Operations
  Scenario: Create and verify schedule
    Given a worker is started for task queue "test-queue" with ScheduledWorkflow
    When I create a schedule "test-schedule-1" for workflow "ScheduledWorkflow" with interval 2 seconds
    And I wait for 5 seconds
    Then the schedule "test-schedule-1" should have executed at least 1 time

  Scenario: Schedule with interval spec
    Given a worker is started for task queue "test-queue" with ScheduledWorkflow
    When I create a schedule "interval-schedule-1" with interval spec:
      | key      | value |
      | interval | 3     |
      | phase    | 0     |
    Then the schedule should be created successfully

  Scenario: Schedule with cron spec
    Given a worker is started for task queue "test-queue" with ScheduledWorkflow
    When I create a schedule "cron-schedule-1" with cron spec "* * * * *"
    Then the schedule should be created successfully

  Scenario: Schedule with overlap policy SKIP
    Given a worker is started for task queue "test-queue" with ScheduledWorkflow
    When I create a schedule "overlap-schedule-1" with overlap policy "SKIP"
    Then the schedule should be created successfully

  Scenario: Stop and delete schedule
    Given a worker is started for task queue "test-queue" with ScheduledWorkflow
    When I create a schedule "delete-schedule-1" for workflow "ScheduledWorkflow" with interval 10 seconds
    And I wait for 2 seconds
    And I stop schedule "delete-schedule-1"
    Then the schedule "delete-schedule-1" should be stopped

  # Timeout and Retry
  Scenario: Workflow execution timeout
    Given a worker is started for task queue "test-queue" with TimeoutWorkflow
    When I execute workflow "TimeoutWorkflow" with argument 20 and execution timeout 2 seconds
    Then the workflow should timeout with execution timeout error

  Scenario: Workflow run timeout
    Given a worker is started for task queue "test-queue" with TimeoutWorkflow
    When I execute workflow "TimeoutWorkflow" with argument 15 and run timeout 2 seconds
    Then the workflow should timeout with run timeout error

  Scenario: Activity retry on failure
    Given a worker is started for task queue "test-queue" with RetryWorkflow
    When I execute workflow "RetryWorkflow" with argument true and max attempts 3
    Then the workflow result should contain "failed after retries"

  Scenario: Activity heartbeat timeout
    Given a worker is started for task queue "test-queue" with LongRunningWorkflow
    When I execute workflow "LongRunningWorkflow" with argument 3
    Then the workflow should complete successfully

  # Error Handling
  Scenario: Connection failure to Temporal server
    Given a Temporal adapter with invalid server configuration
    When I try to execute workflow "GreetingWorkflow" with argument "Test"
    Then I should receive a connection error

  Scenario: Start workflow with invalid workflow type
    Given a worker is started for task queue "test-queue" with GreetingWorkflow
    When I try to start workflow "NonExistentWorkflow" with argument "Test"
    Then I should receive a workflow not found error

  Scenario: Get handle for non-existent workflow
    When I try to get workflow handle for "non-existent-workflow-id"
    Then I should receive a workflow not found error

  Scenario: Signal non-existent workflow
    When I try to send signal "update_counter" with value 5 to workflow "non-existent-signal-workflow"
    Then I should receive a workflow not found error

  Scenario: Worker start failure with invalid task queue
    When I try to start a worker with empty task queue
    Then I should receive a worker configuration error

  # Advanced Operations
  Scenario: Workflow with concurrent activity execution
    Given a worker is started for task queue "test-queue" with ConcurrentActivitiesWorkflow
    When I execute workflow "ConcurrentActivitiesWorkflow" with names:
      | name    |
      | Alice   |
      | Bob     |
      | Charlie |
    Then the workflow result should contain 3 greetings

  Scenario: Long-running workflow with heartbeat
    Given a worker is started for task queue "test-queue" with LongRunningWorkflow
    When I execute workflow "LongRunningWorkflow" with argument 5
    Then the workflow should complete successfully
    And the workflow result should contain "Completed after 5 seconds"

  Scenario: Data processing workflow
    Given a worker is started for task queue "test-queue" with DataProcessingWorkflow
    When I execute workflow "DataProcessingWorkflow" with data:
      | key  | value |
      | name | Alice |
      | age  | 30    |
      | city | NYC   |
    Then the workflow result should contain processed data
    And the processed data should have item count 3

  Scenario: Connect with extended SDK client configuration
    Given Temporal adapter is configured with client identity "archipy-bdd-client"
    And a Temporal worker manager is configured with worker debug mode enabled
    And a worker is started for task queue "test-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "ConfigTest"
    Then the workflow result should be "Hello, ConfigTest!"
    And the temporal adapter config should have client identity "archipy-bdd-client"
    And the temporal worker manager config should have debug mode enabled

  # OpenTelemetry export (real Temporal server, workers and OpenTelemetry Collector)
  Scenario: Worker exports activity slot gauges
    Given Temporal metrics and traces are exported to the collector
    And a worker limited to 3 concurrent activities is started for task queue "otel-slots-queue"
    When I execute workflow "GreetingWorkflow" with argument "slots"
    Then the Temporal gauge "temporal_worker_task_slots_available" for task queue "otel-slots-queue" and worker type "ActivityWorker" should settle at 3
    And the Temporal gauge "temporal_worker_task_slots_used" for task queue "otel-slots-queue" and worker type "ActivityWorker" should settle at 0

  Scenario: Worker exports poller and sticky cache metrics
    Given Temporal metrics and traces are exported to the collector
    And a worker is started for task queue "otel-pollers-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "pollers"
    Then the collector should expose Temporal metric "temporal_num_pollers" for task queue "otel-pollers-queue" where poller_type is "activity_task"
    And the collector should expose Temporal metric "temporal_num_pollers" for task queue "otel-pollers-queue" where poller_type is "sticky_workflow_task"
    And the collector should expose Temporal metric "temporal_sticky_cache_size" for the task queue "otel-pollers-queue"
    And the collector should expose Temporal metric "temporal_worker_start" for the task queue "otel-pollers-queue"

  Scenario: Worker exports workflow completion and latency metrics
    Given Temporal metrics and traces are exported to the collector
    And a worker is started for task queue "otel-workflow-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "workflow"
    Then the Temporal "temporal_workflow_completed" count for task queue "otel-workflow-queue" and workflow_type "GreetingWorkflow" should be at least 1
    And the collector should expose Temporal metric "temporal_workflow_task_execution_latency" for task queue "otel-workflow-queue" where workflow_type is "GreetingWorkflow"
    And the collector should expose Temporal metric "temporal_workflow_endtoend_latency" for task queue "otel-workflow-queue" where workflow_type is "GreetingWorkflow"
    And the collector should expose Temporal metric "temporal_workflow_task_schedule_to_start_latency" for the task queue "otel-workflow-queue"

  Scenario: Worker exports activity execution metrics
    Given Temporal metrics and traces are exported to the collector
    And a worker is started for task queue "otel-activity-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "activity"
    Then the collector should expose Temporal metric "temporal_activity_execution_latency" for task queue "otel-activity-queue" where activity_type is "greeting_activity"
    And the Temporal "temporal_activity_task_received" count for task queue "otel-activity-queue" and activity_type "greeting_activity" should be at least 1
    And the collector should expose Temporal metric "temporal_activity_succeed_endtoend_latency" for task queue "otel-activity-queue" where activity_type is "greeting_activity"

  Scenario: Worker exports failed activity metrics
    Given Temporal metrics and traces are exported to the collector
    And a worker is started for task queue "otel-failing-queue" with RetryWorkflow
    When I execute the failing retry workflow with 2 attempts on task queue "otel-failing-queue"
    Then the Temporal "temporal_activity_execution_failed" count for task queue "otel-failing-queue" and activity_type "failing_activity" should be at least 1
    And the collector should expose Temporal metric "temporal_activity_execution_failed" for task queue "otel-failing-queue" where failure_reason is "ActivityError"

  Scenario: Client exports request metrics
    Given Temporal metrics and traces are exported to the collector
    And a worker is started for task queue "otel-client-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "client"
    Then the collector should expose client Temporal metric "temporal_request" where operation is "StartWorkflowExecution"
    And the collector should expose client Temporal metric "temporal_long_request" where operation is "GetWorkflowExecutionHistory"
    And the collector should expose client Temporal metric "temporal_request_latency" where operation is "RespondActivityTaskCompleted"

  Scenario: Temporal metrics stay off when ENABLE_METRICS is false
    Given Temporal traces are exported to the collector while Temporal metrics are disabled
    And a worker is started for task queue "otel-disabled-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "disabled"
    Then the collector should not expose any Temporal metric for task queue "otel-disabled-queue"

  Scenario: Temporal tracing interceptor exports one trace for client and worker
    Given Temporal metrics and traces are exported to the collector
    And a worker is started for task queue "otel-trace-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "trace"
    Then the collector should have exported Temporal workflow and activity spans:
      | name                            |
      | StartWorkflow:GreetingWorkflow  |
      | RunWorkflow:GreetingWorkflow    |
      | StartActivity:greeting_activity |
      | RunActivity:greeting_activity   |
    And the exported Temporal spans should share one trace id
    And the exported RunActivity span should carry messaging attributes for task queue "otel-trace-queue"
    And the exported RunWorkflow span should carry messaging attributes for task queue "otel-trace-queue"
    And the exported StartWorkflow span should carry messaging "send" attributes for task queue "otel-trace-queue"
    And the exported StartActivity span should carry messaging "send" attributes for task queue "otel-trace-queue"

  Scenario Outline: Temporal tracing exports a saga with retries, an update, a query and the <signal> signal
    Given Temporal metrics and traces are exported to the collector
    And a worker is started for task queue "otel-saga-queue" with OrderSagaWorkflow
    When I start the order saga "otel-saga-<signal>" with payment succeeding on attempt 3 and shipping failure false requiring approval
    And I wait for 1 seconds
    And I add the note "trace" to the order saga "otel-saga-<signal>"
    And I query workflow "otel-saga-<signal>" with query "get_state"
    And I send signal "<signal>" to workflow "otel-saga-<signal>"
    Then the order saga "otel-saga-<signal>" should end <status> after steps <steps> with compensations <compensations>
    And the collector should have exported Temporal workflow and activity spans:
      | name                            |
      | StartWorkflow:OrderSagaWorkflow |
      | RunWorkflow:OrderSagaWorkflow   |
      | StartActivity:reserve_inventory |
      | RunActivity:charge_payment      |
      | <last_span>                     |
    And the exported Temporal spans should share one trace id
    And the exported StartActivity span should carry messaging "send" attributes for task queue "otel-saga-queue"
    And the collector should have exported Temporal workflow and activity spans:
      | name                    |
      | HandleSignal:<signal>   |
      | HandleUpdate:add_note   |
      | HandleQuery:get_state   |
      | ValidateUpdate:add_note |
    And the exported HandleSignal span should carry messaging attributes for task queue "otel-saga-queue"
    And the exported ValidateUpdate span should carry messaging attributes for task queue "otel-saga-queue"
    And the collector should have exported Temporal workflow and activity spans:
      | name                         |
      | SignalWorkflow:<signal>      |
      | QueryWorkflow:get_state      |
      | StartWorkflowUpdate:add_note |
    And the exported SignalWorkflow span should carry messaging "send" attributes without a destination
    And the exported QueryWorkflow span should carry messaging "send" attributes without a destination
    And the exported StartWorkflowUpdate span should carry messaging "send" attributes without a destination

    Examples:
      | signal  | status      | steps                                                       | compensations                    | last_span                        |
      | approve | completed   | reserve_inventory,charge_payment,ship_order,notify_customer | none                             | RunWorkflow:NotificationWorkflow |
      | cancel  | compensated | reserve_inventory,charge_payment                            | refund_payment,release_inventory | RunActivity:release_inventory    |

  Scenario: Temporal tracing marks update-with-start and a standalone activity as sends
    Given Temporal metrics and traces are exported to the collector
    And a worker is started for task queue "otel-send-queue" with OrderSagaWorkflow
    When I add the note "rush" to a new order saga "otel-saga-uws" with update-with-start
    And I run a standalone greeting activity for "solo" on the last worker queue
    Then the collector should have exported Temporal workflow and activity spans:
      | name                                           |
      | StartUpdateWithStartWorkflow:OrderSagaWorkflow |
      | StartActivity:greeting_activity                |
      | RunActivity:greeting_activity                  |
    And the exported StartUpdateWithStartWorkflow span should carry messaging "send" attributes for task queue "otel-send-queue"
    And the exported StartActivity span should carry messaging "send" attributes for task queue "otel-send-queue"
    And the standalone activity should return "Hello, solo!"

  Scenario: Temporal tracing is disabled when another library registered a plain tracer provider first
    Given a Temporal test container is running
    And a Temporal adapter is configured
    And a Temporal worker manager is configured
    Given Temporal traces are exported to the collector after another library registered a plain tracer provider
    And a worker is started for task queue "otel-plain-provider-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "plain"
    Then the Temporal client should not carry a tracing interceptor

  Scenario: Temporal runtime manager reuses one runtime until it is reset
    Given Temporal metrics and traces are exported to the collector
    Then the Temporal runtime manager should reuse one runtime until it is reset

  Scenario: Worker metrics are served on a scrape endpoint when the exporter is pull
    Given Temporal metrics are served on a scrape endpoint
    And a worker is started for task queue "otel-scrape-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "scrape"
    Then the Temporal scrape endpoint should expose "temporal_workflow_completed" for task queue "otel-scrape-queue"

  Scenario: Worker metrics fall back to OTLP when the exporter is the Pushgateway
    Given Temporal metrics are exported over OTLP while the app exporter is the Pushgateway
    And a worker is started for task queue "otel-fallback-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "fallback"
    Then the Temporal "temporal_workflow_completed" count for task queue "otel-fallback-queue" and workflow_type "GreetingWorkflow" should be at least 1

  Scenario: Temporal telemetry is exported over HTTP/protobuf
    Given Temporal metrics and traces are exported to the collector over HTTP/protobuf
    And a worker is started for task queue "otel-http-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "http"
    Then the Temporal client should carry a tracing interceptor
    And the Temporal "temporal_workflow_completed" count for task queue "otel-http-queue" and workflow_type "GreetingWorkflow" should be at least 1
