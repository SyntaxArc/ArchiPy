@needs-temporal
Feature: Metric Interceptor

  Scenario Outline: Interceptor is added when Prometheus is enabled
    Given a <framework> app with Prometheus enabled
    When the <framework> metric interceptor is setup
    Then the <framework> app should have the metric interceptor

    Examples:
      | framework |
      | FastAPI   |
      | gRPC      |
      | AsyncgRPC |

  Scenario Outline: Interceptor is skipped when Prometheus is disabled
    Given a <framework> app with Prometheus disabled
    When the <framework> metric interceptor is setup
    Then the <framework> app should not have the metric interceptor

    Examples:
      | framework |
      | FastAPI   |
      | gRPC      |
      | AsyncgRPC |

  Scenario Outline: Response time is recorded for successful requests
    Given a <framework> app with Prometheus enabled and metric interceptor
    When a <framework> request is made
    Then the <framework> response time metric should be recorded
    And the <framework> metric should have correct labels

    Examples:
      | framework |
      | FastAPI   |
      | gRPC      |
      | AsyncgRPC |

  Scenario Outline: Active requests gauge increments and decrements correctly
    Given a <framework> app with Prometheus enabled and metric interceptor
    When a <framework> request is made
    Then the <framework> active requests gauge should increment before processing
    And the <framework> active requests gauge should decrement after processing

    Examples:
      | framework |
      | FastAPI   |
      | gRPC      |
      | AsyncgRPC |

  Scenario Outline: Prometheus server starts only once
    Given Prometheus is enabled for <framework>
    When multiple <framework> apps are created
    Then the Prometheus server should only start once

    Examples:
      | framework |
      | FastAPI   |
      | gRPC      |
      | AsyncgRPC |

  Scenario: Response time is recorded for failed requests
    Given a FastAPI app with Prometheus enabled and metric interceptor
    When a GET request is made to an endpoint that raises an error
    Then the response time metric should be recorded with status code 500

  Scenario Outline: Metrics include correct labels for parameterized routes
    Given a FastAPI app with Prometheus enabled and metric interceptor with routes
    When a <method> request is made to "<actual_path>" with route pattern "<route_pattern>"
    Then the metric should have path_template label "<route_pattern>"
    And the metric should not have path_template label "<actual_path>"
    And the metric should have method label "<method>"

    Examples:
      | method | actual_path           | route_pattern                      |
      | GET    | /users/123            | /users/{id}                        |
      | POST   | /users/456/posts      | /users/{user_id}/posts             |
      | GET    | /api/v1/items/789     | /api/v1/items/{item_id}            |
      | PUT    | /orders/abc/items/xyz | /orders/{order_id}/items/{item_id} |
      | DELETE | /resources/test-123   | /resources/{resource_id}           |

  Scenario: Path template extraction works for routes without parameters
    Given a FastAPI app with Prometheus enabled and metric interceptor
    When a GET request is made to "/health" endpoint
    Then the metric should have path_template label "/health"

  Scenario: Path template cache improves performance
    Given a FastAPI app with Prometheus enabled and metric interceptor with routes
    When multiple GET requests are made to "/users/123"
    Then all metrics should have the same path_template label "/users/{id}"
    And the cache should have stored the path template

  Scenario: Temporal metrics are not collected when disabled
    Given a Temporal test container is running
    And a Temporal worker manager is configured
    And a Temporal adapter with metrics disabled
    And a worker is started for task queue "no-metrics-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "TestUser"
    Then Temporal metrics should not be present in Prometheus registry

  Scenario: Temporal metrics are collected when enabled
    Given a Temporal test container is running
    And a Temporal worker manager is configured
    And a Temporal adapter with metrics enabled
    And a worker is started for task queue "metrics-test-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "TestUser"
    Then Temporal metrics should be present in Prometheus registry
    And Temporal client metrics should include workflow operations
    And Temporal worker metrics should include task execution

  Scenario: Temporal worker metrics track task queue operations
    Given a Temporal test container is running
    And a Temporal worker manager is configured
    And a Temporal adapter with metrics enabled
    And a worker is started for task queue "worker-metrics-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "TestUser"
    Then Temporal worker task execution metrics should be recorded
    And worker metrics should include task queue labels

  Scenario: Temporal activity execution metrics are recorded
    Given a Temporal test container is running
    And a Temporal worker manager is configured
    And a Temporal adapter with metrics enabled
    And a worker is started for task queue "activity-metrics-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "TestData"
    Then Temporal activity execution metrics should be recorded
    And activity metrics should include activity type information

  Scenario: Temporal workflow execution count increments correctly
    Given a Temporal test container is running
    And a Temporal worker manager is configured
    And a Temporal adapter with metrics enabled
    And a worker is started for task queue "count-metrics-queue" with GreetingWorkflow
    When I execute workflow "GreetingWorkflow" with argument "User1"
    And I execute workflow "GreetingWorkflow" with argument "User2"
    And I execute workflow "GreetingWorkflow" with argument "User3"
    Then Temporal workflow execution count metrics should show at least 3 executions
