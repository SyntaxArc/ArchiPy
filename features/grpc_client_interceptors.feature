@unit
Feature: gRPC client interceptor bases

  Scenario: Client call details expose their fields
    When sync client call details are built for method "/pkg.Svc/Call" with timeout 2.5 and metadata "x-a=1"
    Then the client call details report method "/pkg.Svc/Call" and timeout 2.5 and metadata "x-a=1"
    And the client call details are a gRPC client call details instance

  Scenario: Async client call details expose their fields
    When async client call details are built for method "/pkg.Svc/Call" with timeout 1.0 and metadata "x-b=2"
    Then the client call details report method "/pkg.Svc/Call" and timeout 1.0 and metadata "x-b=2"
    And the client call details are an async gRPC client call details instance

  Scenario: Base client interceptors cannot be instantiated directly
    Then the base sync client interceptor cannot be instantiated
    And the base async client interceptor cannot be instantiated

  Scenario Outline: Sync interceptor passes call details and request through unchanged
    Given a sync pass-through client interceptor
    When a sync "<kind>" call with request "req-1" is intercepted
    Then the sync continuation received request "req-1" with method "/pkg.Svc/Call"
    And the sync continuation received no extra client metadata
    And the intercepted sync call returned the continuation result

    Examples:
      | kind          |
      | unary_unary   |
      | unary_stream  |
      | stream_unary  |
      | stream_stream |

  Scenario Outline: Sync interceptor adds metadata before calling the continuation
    Given a sync metadata-adding client interceptor adding "x-token" with "secret"
    When a sync "<kind>" call with request "req-2" is intercepted
    Then the sync continuation received request "req-2" with method "/pkg.Svc/Call"
    And the sync continuation received client metadata "x-token" with "secret"
    And the sync continuation kept the original client metadata "x-orig" with "keep"

    Examples:
      | kind          |
      | unary_unary   |
      | unary_stream  |
      | stream_unary  |
      | stream_stream |

  Scenario: Sync streaming response is consumable through the interceptor
    Given a sync pass-through client interceptor
    When a sync "stream_stream" call with request "a,b,c" is intercepted
    Then the intercepted sync streaming response yields "a,b,c"

  Scenario: Sync interceptor propagates continuation errors
    Given a sync pass-through client interceptor with a failing continuation
    When a sync "unary_unary" call with request "boom" is intercepted expecting failure
    Then the intercepted sync call raised "continuation failed"

  @async
  Scenario Outline: Async interceptor passes call details and request through unchanged
    Given an async pass-through client interceptor
    When an async "<kind>" call with request "req-3" is intercepted
    Then the async continuation received request "req-3" with method "/pkg.Svc/Call"
    And the async continuation received no extra client metadata
    And the intercepted async call returned the continuation result

    Examples:
      | kind          |
      | unary_unary   |
      | unary_stream  |
      | stream_unary  |
      | stream_stream |

  @async
  Scenario Outline: Async interceptor adds metadata before calling the continuation
    Given an async metadata-adding client interceptor adding "x-token" with "secret"
    When an async "<kind>" call with request "req-4" is intercepted
    Then the async continuation received request "req-4" with method "/pkg.Svc/Call"
    And the async continuation received client metadata "x-token" with "secret"
    And the async continuation kept the original client metadata "x-orig" with "keep"

    Examples:
      | kind          |
      | unary_unary   |
      | unary_stream  |
      | stream_unary  |
      | stream_stream |

  @async
  Scenario: Async interceptor propagates continuation errors
    Given an async pass-through client interceptor with a failing continuation
    When an async "unary_unary" call with request "boom" is intercepted expecting failure
    Then the intercepted async call raised "continuation failed"
