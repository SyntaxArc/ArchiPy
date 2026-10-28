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

  Scenario: Starting a running workflow ID again with USE_EXISTING returns the same run
    Given a worker is started for task queue "test-queue" with SignalQueryWorkflow
    When I start workflow "SignalQueryWorkflow" with workflow id "test-id-policy-1" twice using conflict policy USE_EXISTING
    Then both starts should return the same run id

  Scenario: Execute workflow and wait for result
    Given a worker is started for task queue "test-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "Bob"
    Then the workflow result should be "Hello, Bob!"

  Scenario: BaseWorkflow runs activities with config defaults inside the sandbox
    Given a worker is started for task queue "test-queue" with BaseGreetingWorkflow
    When I execute workflow "BaseGreetingWorkflow" with argument "Zed"
    Then the workflow result should be "Hello, Zed!"

  Scenario: Cancel running workflow
    Given a worker is started for task queue "test-queue" with SignalQueryWorkflow
    When I start workflow "SignalQueryWorkflow" with workflow id "test-cancel-1"
    And I wait for 1 seconds
    And I cancel workflow "test-cancel-1"
    Then the workflow "test-cancel-1" should be cancelled

  Scenario: Cancel running workflow with a reason
    Given a worker is started for task queue "test-queue" with SignalQueryWorkflow
    When I start workflow "SignalQueryWorkflow" with workflow id "test-cancel-reason-1"
    And I request cancellation of workflow "test-cancel-reason-1" with reason "user abort"
    Then the cancel request of workflow "test-cancel-reason-1" should carry reason "user abort"

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

  Scenario: Pydantic payloads round trip through a workflow
    Given a worker is started for task queue "test-queue" with EchoOrderWorkflow
    When I execute workflow "EchoOrderWorkflow" with order "order-7" totalling 12.50
    Then the echoed order should equal the sent order

  Scenario: List workflows stops at the limit
    Given a worker is started for task queue "test-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "Limit-1"
    And I execute workflow "GreetingWorkflow" with argument "Limit-2"
    And I list workflows with query "WorkflowType='GreetingWorkflow'" and limit 1
    Then the workflow list should contain exactly 1 workflow

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

  # Saga: several activities with retries, compensation, a child workflow, signal, query and update
  Scenario: Order saga retries the payment and completes
    Given a worker is started for task queue "test-queue" with OrderSagaWorkflow
    When I execute the order saga with payment succeeding on attempt 3 and shipping failure false
    Then the order saga should end completed after steps reserve_inventory,charge_payment,ship_order,notify_customer with compensations none

  Scenario: Order saga reverts the completed activities when shipping fails
    Given a worker is started for task queue "test-queue" with OrderSagaWorkflow
    When I execute the order saga with payment succeeding on attempt 2 and shipping failure true
    Then the order saga should end compensated after steps reserve_inventory,charge_payment with compensations refund_payment,release_inventory

  Scenario Outline: Order saga is driven by an update, a query and the <signal> signal
    Given a worker is started for task queue "test-queue" with OrderSagaWorkflow
    When I start the order saga "test-saga-<signal>" with payment succeeding on attempt 2 and shipping failure false requiring approval
    And I wait for 1 seconds
    And I add the note "gift wrap" to the order saga "test-saga-<signal>"
    And I query workflow "test-saga-<signal>" with query "get_state"
    And I send signal "<signal>" to workflow "test-saga-<signal>"
    Then the update result should be 1
    And the order saga "test-saga-<signal>" should end <status> after steps <steps> with compensations <compensations>

    Examples:
      | signal  | status      | steps                                                       | compensations                    |
      | approve | completed   | reserve_inventory,charge_payment,ship_order,notify_customer | none                             |
      | cancel  | compensated | reserve_inventory,charge_payment                            | refund_payment,release_inventory |

  Scenario: Order saga update validator rejects a blank note
    Given a worker is started for task queue "test-queue" with OrderSagaWorkflow
    When I start the order saga "test-saga-blank" with payment succeeding on attempt 1 and shipping failure false requiring approval
    And I wait for 1 seconds
    And I try to add a blank note to the order saga "test-saga-blank"
    And I send signal "approve" to workflow "test-saga-blank"
    Then the blank note should be rejected by the update validator
    And the order saga "test-saga-blank" should end completed after steps reserve_inventory,charge_payment,ship_order,notify_customer with compensations none

  Scenario: Order saga starts and updates in one update-with-start request
    Given a worker is started for task queue "test-queue" with OrderSagaWorkflow
    When I add the note "rush" to a new order saga "test-saga-uws" with update-with-start
    Then the update result should be 1
    And the order saga should end completed after steps reserve_inventory,charge_payment,ship_order,notify_customer with compensations none

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

  Scenario: Worker with poller autoscaling and an activity rate limit runs workflows
    Given a Temporal worker manager is configured with poller autoscaling and 50 activities per second
    And a worker is started for task queue "test-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "Tuned"
    Then the workflow result should be "Hello, Tuned!"

  Scenario: Worker joins a Worker Deployment version
    When I start a worker for task queue "deployment-queue" in deployment "orders" with build id "v2.0.0"
    Then the worker should be running
    And the worker should have build_id "v2.0.0"

  Scenario: Stop worker gracefully
    When I start a worker for task queue "stop-test-queue" with workflows and activities
    Then the worker should be running
    When I stop the worker
    Then the worker should be stopped

  Scenario: Worker handle reports a run that ended outside the handle
    When I start a worker for task queue "run-ended-queue" with workflows and activities
    Then the worker should be running
    When the worker run ends without the handle
    Then the worker should be stopped
    And the worker should have no run error

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

  Scenario: Concurrent first calls share one Temporal client
    When 5 callers get the client of a new Temporal adapter at once
    Then they should all receive the same client

  Scenario Outline: Activity cache key is a stable content digest
    When I build the activity cache key for input "<input>"
    Then the activity cache key should be "CacheKeyActivity:<digest>"

    Examples: Cache keys
      | input    | digest                                                           |
      | order-42 | 90140eb1a898639024d3752994bf84b1d40cfe639f70bcbdf7d047bf72274a1d |
      | alice    | 0a50500b2a3435fe7472877eb22d48d47a228e946b0b991ab7402a8d00f6b32d |
