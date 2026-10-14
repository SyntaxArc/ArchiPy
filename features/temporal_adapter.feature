@needs-temporal @needs-otel-collector
Feature: Temporal Adapter Operations
  As a developer
  I want to test Temporal adapter operations
  So that I can ensure reliable workflow orchestration functionality

  Background:
    Given a Temporal test container is running
    And a Temporal adapter is configured
    And a Temporal worker manager is configured

  # Basic Workflow Operations
  Scenario: Start and get workflow handle
    Given a worker is started for task queue "test-queue" with GreetingWorkflow
    When I start workflow "GreetingWorkflow" with argument "Alice" and workflow id "test-greeting-1"
    Then I should be able to get workflow handle for "test-greeting-1"
    And the workflow handle should have workflow id "test-greeting-1"

  Scenario: Execute workflow and wait for result
    Given a worker is started for task queue "test-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "Bob"
    Then the workflow result should be "Hello, Bob!"

  Scenario: Cancel running workflow
    Given a worker is started for task queue "test-queue" with SignalQueryWorkflow
    When I start workflow "SignalQueryWorkflow" with workflow id "test-cancel-1"
    And I wait for 1 seconds
    And I cancel workflow "test-cancel-1"
    Then the workflow "test-cancel-1" should be cancelled

  Scenario: Terminate running workflow
    Given a worker is started for task queue "test-queue" with SignalQueryWorkflow
    When I start workflow "SignalQueryWorkflow" with workflow id "test-terminate-1"
    And I wait for 1 seconds
    And I terminate workflow "test-terminate-1" with reason "Test termination"
    Then the workflow "test-terminate-1" should be terminated

  Scenario: List workflows with query filter
    Given a worker is started for task queue "test-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "Charlie"
    And I list workflows with query "WorkflowType='GreetingWorkflow'"
    Then the workflow list should contain at least 1 workflow

  Scenario: Describe workflow execution
    Given a worker is started for task queue "test-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "Diana" and workflow id "test-describe-1"
    And I describe workflow "test-describe-1"
    Then the workflow description should have workflow id "test-describe-1"
    And the workflow description should have type "GreetingWorkflow"

  Scenario: Start workflow with custom timeouts
    Given a worker is started for task queue "test-queue" with TimeoutWorkflow
    When I start workflow "TimeoutWorkflow" with argument 2 and custom timeouts:
      | key               | value |
      | execution_timeout | 30    |
      | run_timeout       | 20    |
      | task_timeout      | 10    |
    Then the workflow should start successfully

  Scenario: Start workflow with memo and search attributes
    Given a worker is started for task queue "test-queue" with GreetingWorkflow
    When I start workflow "GreetingWorkflow" with argument "Eve" and metadata:
      | type              | value          |
      | memo              | test_memo      |
      | search_attributes | test_attribute |
    Then the workflow should start successfully

  # Signal and Query Operations
  Scenario: Send signal to running workflow
    Given a worker is started for task queue "test-queue" with SignalQueryWorkflow
    When I start workflow "SignalQueryWorkflow" with workflow id "test-signal-1"
    And I wait for 1 seconds
    And I send signal "update_counter" with value 5 to workflow "test-signal-1"
    And I send signal "complete" to workflow "test-signal-1"
    Then the workflow "test-signal-1" should complete successfully

  Scenario: Query workflow state during execution
    Given a worker is started for task queue "test-queue" with SignalQueryWorkflow
    When I start workflow "SignalQueryWorkflow" with workflow id "test-query-1"
    And I wait for 1 seconds
    And I query workflow "test-query-1" with query "get_counter"
    Then the query result should be 0

  Scenario: Multiple signals in sequence
    Given a worker is started for task queue "test-queue" with SignalQueryWorkflow
    When I start workflow "SignalQueryWorkflow" with workflow id "test-multi-signal-1"
    And I wait for 1 seconds
    And I send signals to workflow "test-multi-signal-1":
      | signal_name    | value  |
      | update_counter | 5      |
      | update_counter | 10     |
      | set_status     | active |
    And I send signal "complete" to workflow "test-multi-signal-1"
    Then the workflow "test-multi-signal-1" should complete successfully

  Scenario: Signal with complex data
    Given a worker is started for task queue "test-queue" with SignalQueryWorkflow
    When I start workflow "SignalQueryWorkflow" with workflow id "test-complex-signal-1"
    And I wait for 1 seconds
    And I send signal "set_status" with value "processing" to workflow "test-complex-signal-1"
    And I query workflow "test-complex-signal-1" with query "get_status"
    Then the query result should be "processing"

  Scenario: Query before and after signal
    Given a worker is started for task queue "test-queue" with SignalQueryWorkflow
    When I start workflow "SignalQueryWorkflow" with workflow id "test-query-signal-1"
    And I wait for 1 seconds
    And I query workflow "test-query-signal-1" with query "get_counter"
    Then the query result should be 0
    When I send signal "update_counter" with value 15 to workflow "test-query-signal-1"
    And I wait for 1 seconds
    And I query workflow "test-query-signal-1" with query "get_counter"
    Then the query result should be 15

  # Worker Management
  Scenario: Start worker with workflows and activities
    When I start a worker for task queue "worker-test-queue" with workflows and activities
    Then the worker should be running
    And the worker should have 1 or more registered workflows
    And the worker should have 1 or more registered activities

  Scenario: Multiple workers on different task queues
    When I start a worker for task queue "queue-1" with workflows and activities
    And I start a worker for task queue "queue-2" with workflows and activities
    Then the worker manager should have 2 workers
    And each worker should be on a different task queue

  Scenario: Worker with build_id for versioning
    When I start a worker for task queue "versioned-queue" with build_id "v1.0.0"
    Then the worker should be running
    And the worker should have build_id "v1.0.0"

  Scenario: Stop worker gracefully
    When I start a worker for task queue "stop-test-queue" with workflows and activities
    Then the worker should be running
    When I stop the worker
    Then the worker should be stopped

  Scenario: Get worker statistics
    When I start a worker for task queue "stats-queue" with workflows and activities
    And I get worker statistics
    Then the worker stats should show worker is running
    And the worker stats should show task queue "stats-queue"

  Scenario: Shutdown all workers
    When I start a worker for task queue "shutdown-queue-1" with workflows and activities
    And I start a worker for task queue "shutdown-queue-2" with workflows and activities
    Then the worker manager should have 2 workers
    When I shutdown all workers
    Then the worker manager should have 0 workers

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

  Scenario: Temporal runtime manager reuses one runtime until it is reset
    Given Temporal metrics and traces are exported to the collector
    Then the Temporal runtime manager should reuse one runtime until it is reset
