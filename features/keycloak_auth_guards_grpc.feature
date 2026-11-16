# features/keycloak_auth_guards_grpc.feature
@needs-keycloak @needs-envoy @needs-otel-collector
Feature: Keycloak Auth Guards for gRPC, Envoy and Caching Testing
  As a developer
  I want to test Keycloak authentication operations
  So that I can ensure secure authentication and management operations

  @ownership-integration
  Scenario Outline: gRPC resolves resource ownership from real Keycloak authentication
    Given a keycloak auth realm with a client
    And I enable organization of realm named "auth-realm"
    And I create a user with username "orguser" and password "pass123" using sync adapter
    And user "orguser" belongs to <count> organizations with organization IDs enabled in UserInfo
    And the default organization requirement is false
    When user "orguser" obtains a token with organization scope "<scope>"
    And the grpc <mode> endpoint resolves ownership using "<resolver>" for user "orguser"
    Then the authenticated ownership outcome is "<outcome>" for user "orguser"
    And the keycloak auth context is cleared

    Examples:
      | mode  | count | scope            | resolver | outcome      |
      | sync  | 0     | personal         | explicit | USER         |
      | async | 0     | personal         | explicit | USER         |
      | sync  | 2     | personal         | request  | USER         |
      | async | 2     | personal         | request  | USER         |
      | sync  | 1     | selected         | explicit | ORGANIZATION |
      | async | 1     | selected         | explicit | ORGANIZATION |
      | sync  | 2     | selected         | request  | ORGANIZATION |
      | async | 2     | selected         | request  | ORGANIZATION |
      | sync  | 1     | all              | request  | denied       |
      | async | 1     | all              | request  | denied       |
      | sync  | 2     | all              | explicit | denied       |
      | async | 2     | all              | explicit | denied       |
      | sync  | 1     | aliases-selected | explicit | denied       |
      | async | 1     | aliases-selected | explicit | denied       |
      | sync  | 1     | aliases-selected | request  | denied       |
      | async | 1     | aliases-selected | request  | denied       |

  @malformed-user-uuid
  Scenario Outline: gRPC rejects a malformed UserInfo subject as unauthenticated
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And Keycloak UserInfo reports subject "not-a-uuid" for user "authuser"
    When the keycloak auth <mode> grpc handler is invoked with the bearer access token of user "authuser"
    Then the keycloak auth servicer context was aborted with status "UNAUTHENTICATED"
    And the keycloak auth grpc handler did not run
    And the keycloak auth context is cleared

    Examples:
      | mode  |
      | sync  |
      | async |

  @auth-guards
  Scenario Outline: Auth gRPC handler allows the owner of a resource
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak grpc auth reads the resource from request attribute "user_id"
    And the keycloak auth grpc request attribute "user_id" is the id of user "authuser"
    When the keycloak auth <mode> grpc handler is invoked with the bearer access token of user "authuser"
    Then the keycloak auth grpc handler ran as user "authuser" with roles including "auth-reader"

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  @auth-guards
  Scenario Outline: Auth gRPC handler aborts the servicer context when the token is missing
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    When the keycloak auth <mode> grpc handler is invoked without metadata
    Then the keycloak auth servicer context was aborted with status "UNAUTHENTICATED"
    And the keycloak auth grpc handler did not run
    And the keycloak auth context is cleared

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  @auth-guards
  Scenario Outline: Auth gRPC handler aborts the servicer context when the token is invalid
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    When the keycloak auth <mode> grpc handler is invoked with bearer token "not-a-real-jwt"
    Then the keycloak auth servicer context was aborted with status "UNAUTHENTICATED"
    And the keycloak auth grpc handler did not run

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  @auth-guards
  Scenario Outline: Auth gRPC handler aborts the servicer context when the role is insufficient
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak grpc auth requires any of roles "auth-admin"
    When the keycloak auth <mode> grpc handler is invoked with the bearer access token of user "authuser"
    Then the keycloak auth servicer context was aborted with status "PERMISSION_DENIED"
    And the keycloak auth grpc handler did not run
    And the keycloak auth context is cleared

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  @auth-guards
  Scenario Outline: Auth gRPC handler aborts when the request lacks the resource attribute
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak grpc auth reads the resource from request attribute "user_id"
    When the keycloak auth <mode> grpc handler is invoked with the bearer access token of user "authuser"
    Then the keycloak auth servicer context was aborted with status "INVALID_ARGUMENT"

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  @auth-guards
  Scenario Outline: Auth gRPC handler raises the typed error when the context is not a servicer context
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    When the keycloak auth <mode> grpc handler is invoked without metadata on a plain context
    Then the keycloak auth call fails with error code "UNAUTHENTICATED"
    And the keycloak auth grpc handler did not run

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  Scenario Outline: Auth sync gRPC handler wraps unexpected failures in an internal error
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak auth grpc handler crashes with a runtime failure
    When the keycloak auth sync grpc handler is invoked with the bearer access token of user "authuser" on a plain context
    Then the keycloak auth call fails with error code "INTERNAL_ERROR"
    And the keycloak auth context is cleared

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth async gRPC handler aborts with an internal status on unexpected failures
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak auth grpc handler crashes with a runtime failure
    When the keycloak auth async grpc handler is invoked with the bearer access token of user "authuser"
    Then the keycloak auth servicer context was aborted with status "INTERNAL"
    And the keycloak auth context is cleared

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario: Auth context manager stores and returns the context
    Given no keycloak auth context is set
    When the keycloak auth context is set for user "11111111-1111-4111-8111-111111111111"
    Then the keycloak auth context belongs to user "11111111-1111-4111-8111-111111111111"

  Scenario: Auth context manager clears the context
    Given the keycloak auth context is set for user "11111111-1111-4111-8111-111111111111"
    When the keycloak auth context is cleared by the manager
    Then the keycloak auth context is cleared

  Scenario: Auth context manager restores the outer context when cleared with the token of a nested one
    Given the keycloak auth context is set for user "22222222-2222-4222-8222-222222222222"
    When the keycloak auth context of user "33333333-3333-4333-8333-333333333333" is set and then cleared with its token
    Then the keycloak auth context belongs to user "22222222-2222-4222-8222-222222222222"

  Scenario: Auth context manager returns nothing when no context was set
    Given no keycloak auth context is set
    Then the keycloak auth context is cleared

  @auth-guards
  Scenario Outline: A guarded FastAPI route keeps the auth context on the <path> route
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And a FastAPI app whose routes are guarded by the keycloak fastapi auth
    When the guarded app is requested at "<path>" with the access token of user "authuser"
    Then the app response reports the caller "authuser" every time it reads the auth context

    Examples:
      | path    | via    |
      | /async  | direct |
      | /sync   | direct |
      | /stream | direct |
      | /async  | envoy  |
      | /sync   | envoy  |
      | /stream | envoy  |

  Scenario Outline: A FastAPI background task still sees the caller after the response
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And a FastAPI app whose routes are guarded by the keycloak fastapi auth
    When the guarded app is requested at "/background" with the access token of user "authuser"
    Then the app response reports the caller "authuser" every time it reads the auth context
    And the background task saw the caller "authuser"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: The auth context does not leak into a later unguarded request
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And a FastAPI app whose routes are guarded by the keycloak fastapi auth
    When the guarded app is requested at "/async" with the access token of user "authuser"
    And the guarded app is requested at "/open" without credentials
    Then the app response reports no caller

    # --- Keycloak auth gRPC decorators and caching against the real Keycloak container ---
    Examples:
      | via    |
      | direct |
      | envoy  |

  @auth-guards
  Scenario Outline: Auth gRPC response-stream handler keeps the auth context while streaming
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And the keycloak grpc auth requires any of roles "auth-reader"
    And the keycloak auth grpc handler is a response stream
    When the keycloak auth <mode> grpc handler is invoked with the bearer access token of user "authuser"
    Then the keycloak auth grpc handler ran as user "authuser" with roles including "auth-reader"
    And the keycloak auth grpc handler returned "a,b"
    And the keycloak auth context is cleared

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  @auth-guards
  Scenario Outline: Auth gRPC response-stream handler rejects a missing token
    Given a keycloak auth realm with a client via <via>
    And the keycloak auth grpc handler is a response stream
    When the keycloak auth <mode> grpc handler is invoked without metadata on a plain context
    Then the keycloak auth call fails with error code "UNAUTHENTICATED"
    And the keycloak auth grpc handler did not run

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  @auth-guards
  Scenario Outline: Auth gRPC handler abort is not rewritten as an internal error
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And the keycloak grpc auth requires any of roles "auth-reader"
    And the keycloak auth grpc handler aborts the servicer context itself
    When the keycloak auth <mode> grpc handler is invoked with the bearer access token of user "authuser"
    Then the keycloak auth servicer context was aborted exactly once with status "RESOURCE_EXHAUSTED"
    And the keycloak auth context is cleared

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  Scenario Outline: Auth sync gRPC handler hides the cause of unexpected failures
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And the keycloak grpc auth requires any of roles "auth-reader"
    And the keycloak auth grpc handler crashes with a runtime failure
    When the keycloak auth sync grpc handler is invoked with the bearer access token of user "authuser" on a plain context
    Then the keycloak auth call fails with error code "INTERNAL_ERROR"
    And the keycloak auth error should not expose "boom"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth lookups are not cached unless a TTL is configured
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    And the keycloak auth sessions of user "authuser" are cleared
    And the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "INVALID_CREDENTIALS"

    Examples:
      | via    |
      | direct |
      | envoy  |
