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
      | origin                        |
      | https://malicious.com         |
      | https://subdomain.example.com |
      | https://example.com:8080      |
      | http://example.com            |
      | null                          |
      | https://attacker.org          |

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
      | header           |
      | X-Custom-Token   |
      | X-Api-Key        |
      | X-Debug          |
      | Cookie           |
      | X-Requested-With |

  Scenario Outline: CORS preflight should reject disallowed methods
    Given a FastAPI app with CORS configuration
    When I make an OPTIONS preflight requesting method "<method>"
    Then the response should NOT have access-control-allow-methods header

    Examples:
      | method |
      | PUT    |
      | DELETE |
      | PATCH  |
      | TRACE  |

  Scenario Outline: CORS preflight should reject disallowed headers
    Given a FastAPI app with CORS configuration
    When I make an OPTIONS preflight requesting header "<header>"
    Then the response should NOT have access-control-allow-headers header

    Examples:
      | header         |
      | X-Custom-Token |
      | X-Api-Key      |
      | X-Debug        |
      | Cookie         |

  Scenario Outline: CORS should reject wrong Content-Type
    Given a FastAPI app with CORS configuration
    When I send a POST request to test endpoint with origin "https://example.com" and custom content-type "<content_type>"
    Then the response should return status code 405

    Examples:
      | content_type    |
      | application/xml |
      | text/plain      |
      | multipart/form  |

  Scenario Outline: CORS preflight should reject incomplete requests
    Given a FastAPI app with CORS configuration
    When I make an OPTIONS preflight <preflight_type>
    Then the response should NOT have access-control-allow-methods header

    Examples:
      | preflight_type                               |
      | without Origin header                        |
      | without Access-Control-Request-Method header |
      | with invalid Origin                          |

  Scenario: Default app should not register optional middleware
    When a FastAPI app is created
    Then the app should not have GZip middleware
    And the app should not have TrustedHost middleware
    And the app should not have HTTPS redirect middleware

  Scenario: GZip middleware compresses large responses
    Given a FastAPI app with GZip middleware enabled
    When I request the large payload endpoint with gzip accepted
    Then the response should have content-encoding gzip

  Scenario: GZip middleware skips small responses
    Given a FastAPI app with GZip middleware enabled
    When I request the small payload endpoint with gzip accepted
    Then the response should not have content-encoding gzip

  Scenario: TrustedHost middleware allows configured host
    Given a FastAPI app with TrustedHost middleware enabled for "testserver"
    When I request the test endpoint
    Then the response should return status code 200

  Scenario Outline: TrustedHost middleware rejects invalid host
    Given a FastAPI app with TrustedHost middleware enabled for "testserver"
    When I request the test endpoint with host "<host>"
    Then the response should return status code 400

    Examples:
      | host         |
      | evil.com     |
      | attacker.org |

  Scenario: TrustedHost middleware skips when allowed hosts is empty
    Given a FastAPI app with TrustedHost enabled and no allowed hosts
    Then the app should not have TrustedHost middleware

  Scenario: HTTPS redirect middleware redirects HTTP requests
    Given a FastAPI app with HTTPS redirect middleware enabled
    When I request the test endpoint without following redirects
    Then the response should return status code 307
    And the response location should use https scheme

  Scenario: HTTPS redirect middleware is not registered when disabled
    Given a FastAPI app with HTTPS redirect middleware disabled
    When I request the test endpoint
    Then the response should return status code 200
    And the app should not have HTTPS redirect middleware

  Scenario: Server-sent events are delivered as an event stream
    Given a FastAPI app with a server-sent events endpoint
    When the client reads 3 server-sent events
    Then the response should be an event stream
    And the client should have received the events "event-0,event-1,event-2"

  Scenario: Server-sent events are flushed incrementally
    Given a FastAPI app with a server-sent events endpoint
    When the client reads 3 server-sent events
    Then the first event should have arrived before the stream finished

  Scenario: GZip middleware does not compress or buffer server-sent events
    Given a FastAPI app with GZip middleware enabled and a server-sent events endpoint
    When the client reads 3 server-sent events
    Then the client should have received the events "event-0,event-1,event-2"
    And the response should not be compressed
    And the first event should have arrived before the stream finished

  Scenario: A failure mid-stream keeps events already delivered
    Given a FastAPI app with a server-sent events endpoint
    When the client reads a server-sent events stream that fails after the first event
    Then the client should have received the events "event-0"

  Scenario: Server-sent events stop when the client disconnects
    Given a FastAPI app with a server-sent events endpoint
    When the client reads 2 of an endless server-sent events stream and disconnects
    Then the server should stop producing events

  Scenario: Concurrent clients each receive the full event stream
    Given a FastAPI app with a server-sent events endpoint
    When 5 clients read 3 server-sent events concurrently
    Then every client should have received the events "event-0,event-1,event-2"

  Scenario: Server-sent events carry CORS headers for allowed origins
    Given a FastAPI app with a server-sent events endpoint
    When the client reads 2 server-sent events from origin "https://example.com"
    Then the client should have received the events "event-0,event-1"
    And the response should allow origin "https://example.com"

  Scenario: Server-sent events omit CORS headers for disallowed origins
    Given a FastAPI app with a server-sent events endpoint
    When the client reads 2 server-sent events from origin "https://evil.example"
    Then the response should not allow any origin

  Scenario: TrustedHost middleware allows server-sent events for a configured host
    Given a FastAPI app with TrustedHost middleware enabled for "127.0.0.1" and a server-sent events endpoint
    When the client reads 2 server-sent events with host "127.0.0.1"
    Then the client should have received the events "event-0,event-1"

  Scenario: TrustedHost middleware rejects server-sent events for an invalid host
    Given a FastAPI app with TrustedHost middleware enabled for "127.0.0.1" and a server-sent events endpoint
    When the client reads 2 server-sent events with host "evil.com"
    Then the event stream request should return status code 400
    And the client should have received no events

  Scenario: An error raised before the stream starts is mapped to an HTTP status
    Given a FastAPI app with a server-sent events endpoint
    When the client reads a server-sent events stream that is rejected before it starts
    Then the event stream request should return status code 400
    And the client should have received no events

  Scenario Outline: A gRPC app runs custom interceptors in the order they were given
    Given custom <kind> gRPC interceptors "first,second,third"
    When a <mode> gRPC app is created with the custom interceptors
    Then the gRPC app should run the custom interceptors in the order "first,second,third"

    Examples:
      | mode  | kind  |
      | sync  | list  |
      | sync  | tuple |
      | async | list  |
      | async | tuple |

  Scenario Outline: A gRPC app still accepts a set of custom interceptors
    Given custom set gRPC interceptors "first,second,third"
    When a <mode> gRPC app is created with the custom interceptors
    Then the gRPC app should run all the custom interceptors

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario Outline: A rate limiter that fails to start stops a fail-closed gRPC server
    Given gRPC rate limiting is enabled with fail closed set to <fail_closed> and a Redis client that cannot be created
    When the <mode> gRPC rate limit interceptor is set up
    Then the gRPC rate limit setup should <outcome>

    Examples:
      | mode  | fail_closed | outcome                          |
      | sync  | true        | raise the initialization error   |
      | async | true        | raise the initialization error   |
      | sync  | false       | continue without the interceptor |
      | async | false       | continue without the interceptor |

  Scenario Outline: TrustedHost middleware checks the host of a WebSocket handshake
    Given a FastAPI app with TrustedHost middleware enabled for "testserver" and an echo WebSocket
    When a WebSocket client connects with the host "<host>"
    Then the WebSocket handshake should be <outcome>

    Examples: Hosts
      | host         | outcome  |
      | testserver   | accepted |
      | evil.com     | refused  |
      | attacker.org | refused  |

  Scenario Outline: HTTPS redirect middleware <effect> a plain WebSocket handshake
    Given a FastAPI app with HTTPS redirect middleware <state> and an echo WebSocket
    When a WebSocket client connects with the host "testserver"
    Then the WebSocket handshake should be <outcome>

    Examples: Redirect settings
      | effect       | state    | outcome  |
      | redirects    | enabled  | refused  |
      | leaves alone | disabled | accepted |

  Scenario: Uvicorn arguments come from the defaults of the UVICORN section
    Given a configuration built from:
      """
      {}
      """
    When the uvicorn arguments are built
    Then the uvicorn argument "timeout_keep_alive" is 5
    And the uvicorn argument "workers" is 4
    And the uvicorn argument "port" is 8100
    And the uvicorn arguments leave out "ssl_keyfile"
    And the uvicorn arguments leave out "forwarded_allow_ips"
    And no deprecation warning is raised

  Scenario: A UVICORN setting wins over the deprecated FASTAPI setting without a warning
    Given a configuration built from:
      """
      {
        "UVICORN": {
          "TIMEOUT_KEEP_ALIVE": 30
        }
      }
      """
    When the uvicorn arguments are built
    Then the uvicorn argument "timeout_keep_alive" is 30
    And no deprecation warning is raised

  Scenario: A deprecated FASTAPI uvicorn setting still applies and warns
    Given a configuration built from:
      """
      {
        "FASTAPI": {
          "TIMEOUT_KEEP_ALIVE": 9,
          "FORWARDED_ALLOW_IPS": [
            "10.0.0.1"
          ]
        }
      }
      """
    When the uvicorn arguments are built
    Then the uvicorn argument "timeout_keep_alive" is 9
    And the uvicorn argument "forwarded_allow_ips" is ["10.0.0.1"]
    And a deprecation warning mentions "UVICORN.TIMEOUT_KEEP_ALIVE"

  Scenario: Reload leaves the worker count out
    Given a configuration built from:
      """
      {
        "UVICORN": {
          "RELOAD": true
        }
      }
      """
    When the uvicorn arguments are built
    Then the uvicorn argument "reload" is true
    And the uvicorn arguments leave out "workers"

  Scenario: TLS settings reach the uvicorn arguments
    Given a configuration built from:
      """
      {
        "UVICORN": {
          "SSL_KEYFILE": "/tls/key.pem",
          "SSL_CERTFILE": "/tls/cert.pem",
          "SSL_CA_CERTS": "/tls/ca.pem"
        }
      }
      """
    When the uvicorn arguments are built
    Then the uvicorn argument "ssl_keyfile" is "/tls/key.pem"
    And the uvicorn argument "ssl_certfile" is "/tls/cert.pem"
    And the uvicorn argument "ssl_ca_certs" is "/tls/ca.pem"

  Scenario: A TLS key without a certificate is rejected
    Then building a configuration from the following fails with "ssl_keyfile_and_certfile_required_together":
      """
      {
        "UVICORN": {
          "SSL_KEYFILE": "/tls/key.pem"
        }
      }
      """

  Scenario: Building a FASTAPI section with a deprecated uvicorn field warns
    When the FASTAPI section is built with a deprecated uvicorn field
    Then a deprecation warning mentions "UVICORN"

  Scenario Outline: Reading a deprecated FASTAPI uvicorn field warns and names its replacement
    Given a configuration built from:
      """
      {}
      """
    When the FASTAPI field "<field>" is read
    Then a deprecation warning mentions "UVICORN.<field>"

    Examples:
      | field                     |
      | TIMEOUT_KEEP_ALIVE        |
      | FORWARDED_ALLOW_IPS       |
      | RELOAD                    |
      | TIMEOUT_GRACEFUL_SHUTDOWN |

  Scenario: Reading the UVICORN field and dumping the FASTAPI section do not warn
    Given a configuration built from:
      """
      {
        "FASTAPI": {
          "TIMEOUT_KEEP_ALIVE": 9
        }
      }
      """
    When the UVICORN field "TIMEOUT_KEEP_ALIVE" is read and the FASTAPI section is dumped
    Then no deprecation warning is raised

  Scenario: The deprecated FASTAPI fields are marked deprecated in the JSON schema
    Then the JSON schema of the FASTAPI section marks "TIMEOUT_KEEP_ALIVE" as deprecated

  Scenario Outline: Reading a deprecated ScyllaDB pool field warns, loading the config does not
    Given a configuration built from:
      """
      {
        "SCYLLADB": {
          "MAX_CONNECTIONS_PER_HOST": 4
        }
      }
      """
    When the SCYLLADB field "<field>" is read
    Then a deprecation warning mentions "no per-host connection pool sizing"

    Examples:
      | field                       |
      | MAX_CONNECTIONS_PER_HOST    |
      | MIN_CONNECTIONS_PER_HOST    |
      | CORE_CONNECTIONS_PER_HOST   |
      | MAX_REQUESTS_PER_CONNECTION |
