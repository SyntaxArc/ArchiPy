Feature: App Utilities

  Scenario: Create a FastAPI app with default settings
    When a FastAPI app is created
    Then the app should have the correct title
    And exception handlers should be registered

  Scenario: Handle a common custom exception
    Given a FastAPI app
    When an endpoint raises a "BaseError"
    Then the response should have status code 500

  Scenario: Handle validation errors in FastAPI
    Given a FastAPI app
    When an endpoint raises a validation error
    Then the response should have status code 422

  Scenario: Generate unique route ID
    Given a FastAPI route with tag "user" and name "get_user_info"
    When a unique ID is generated
    Then the unique ID should be "user-get_user_info"

  Scenario: Setup CORS middleware
    Given a FastAPI app with CORS configuration
    Then the app should allow origins "https://example.com"
    And the app should have expose headers "X-Total-Count, X-Request-ID"
    And the app should have max age 600

  Scenario Outline: CORS should reject requests from disallowed origins
    Given a FastAPI app with CORS configuration
    When I make a request with origin "<origin>"
    Then the response should NOT have access-control-allow-origin header

    Examples:
      | origin                           |
      | https://malicious.com            |
      | https://subdomain.example.com    |
      | https://example.com:8080        |
      | http://example.com               |
      | null                             |
      | https://attacker.org             |

  Scenario Outline: CORS should reject requests with disallowed HTTP methods
    Given a FastAPI app with CORS configuration
    When I make a <method> request with origin "https://example.com"
    Then the response should return status code 405

    Examples:
      | method  |
      | PUT     |
      | DELETE  |
      | PATCH   |
      | TRACE   |
      | CONNECT |

  Scenario Outline: CORS should reject requests with disallowed headers
    Given a FastAPI app with CORS configuration
    When I send a request to test endpoint with origin "https://example.com" and custom header "<header>"
    Then the custom header should NOT be in access-control-expose-headers

    Examples:
      | header          |
      | X-Custom-Token  |
      | X-Api-Key       |
      | X-Debug         |
      | Cookie          |
      | X-Requested-With|

  Scenario Outline: CORS preflight should reject disallowed methods
    Given a FastAPI app with CORS configuration
    When I make an OPTIONS preflight requesting method "<method>"
    Then the response should NOT have access-control-allow-methods header

    Examples:
      | method  |
      | PUT     |
      | DELETE  |
      | PATCH   |
      | TRACE   |

  Scenario Outline: CORS preflight should reject disallowed headers
    Given a FastAPI app with CORS configuration
    When I make an OPTIONS preflight requesting header "<header>"
    Then the response should NOT have access-control-allow-headers header

    Examples:
      | header          |
      | X-Custom-Token  |
      | X-Api-Key       |
      | X-Debug         |
      | Cookie          |

  Scenario Outline: CORS should reject wrong Content-Type
    Given a FastAPI app with CORS configuration
    When I send a POST request to test endpoint with origin "https://example.com" and custom content-type "<content_type>"
    Then the response should return status code 405

    Examples:
      | content_type    |
      | application/xml  |
      | text/plain      |
      | multipart/form  |

  Scenario Outline: CORS preflight should reject incomplete requests
    Given a FastAPI app with CORS configuration
    When I make an OPTIONS preflight <preflight_type>
    Then the response should NOT have access-control-allow-methods header

    Examples:
      | preflight_type                                  |
      | without Origin header                           |
      | without Access-Control-Request-Method header   |
      | with invalid Origin                            |
