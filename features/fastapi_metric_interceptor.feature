Feature: FastAPI Metric Interceptor

  Scenario: Interceptor is added when Prometheus is enabled
    Given a FastAPI app with Prometheus enabled
    When the metric interceptor is setup
    Then the FastAPI app should have the metric interceptor

  Scenario: Interceptor is skipped when Prometheus is disabled
    Given a FastAPI app with Prometheus disabled
    When the metric interceptor is setup
    Then the FastAPI app should not have the metric interceptor

  Scenario: Response time is recorded for successful requests
    Given a FastAPI app with Prometheus enabled and metric interceptor
    When a GET request is made to "/test" endpoint
    Then the response time metric should be recorded
    And the metric should have method label "GET"
    And the metric should have status_code label "200"
    And the metric should have path_template label "/test"

  Scenario: Response time is recorded for failed requests
    Given a FastAPI app with Prometheus enabled and metric interceptor
    When a GET request is made to an endpoint that raises an error
    Then the response time metric should be recorded with status code 500

  Scenario: Active requests gauge increments and decrements correctly
    Given a FastAPI app with Prometheus enabled and metric interceptor
    When a GET request is made to "/test" endpoint
    Then the active requests gauge should increment before processing
    And the active requests gauge should decrement after processing

  Scenario: Prometheus server starts only once
    Given Prometheus is enabled
    When multiple FastAPI apps are created
    Then the Prometheus server should only start once

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
