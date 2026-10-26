# features/keycloak_auth_guards.feature
@needs-keycloak @needs-envoy @needs-otel-collector
Feature: Keycloak Auth Guards Testing
  As a developer
  I want to test Keycloak authentication operations
  So that I can ensure secure authentication and management operations

  # --- Keycloak auth dependencies and decorators ---
  # Real tokens issued by the Keycloak container drive keycloak.auth fastapi_auth, grpc_auth and
  # AuthContextManager. gRPC uses a ServicerContext fake only to record aborts.
  Scenario Outline: Auth FastAPI dependency populates request state for a valid token
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth dependency returns the user info of user "authuser"
    And the keycloak auth request state user roles include "auth-reader"
    And the keycloak auth request state has an empty actor chain
    And the keycloak auth context holds user "authuser" while the dependency is active
    And the keycloak auth context is cleared after the dependency ends

    Examples:
      | via    |
      | direct |
      | envoy  |

  @auth-guards
  Scenario Outline: Reading <field> from the request state warns and points to the auth context
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then reading "<field>" from the request state warns and names "<replacement>"
    And the value the keycloak auth dependency returned does not warn when it is read
    And the request state keeps the same content as the auth context

    Examples:
      | field       | replacement                                         | via    |
      | user_info   | AuthContextManager.get_auth_context().raw_user_info | direct |
      | token_info  | AuthContextManager.get_auth_context().token_info    | direct |
      | actor_chain | AuthContextManager.get_auth_context().actor_chain   | direct |
      | user_roles  | AuthContextManager.get_auth_context().roles         | direct |
      | user_info   | AuthContextManager.get_auth_context().raw_user_info | envoy  |
      | token_info  | AuthContextManager.get_auth_context().token_info    | envoy  |
      | actor_chain | AuthContextManager.get_auth_context().actor_chain   | envoy  |
      | user_roles  | AuthContextManager.get_auth_context().roles         | envoy  |

  Scenario Outline: Auth FastAPI dependency accepts a client role from resource access
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And I create a client role named "auth-operator" for client "auth-client" with description "Operator" using sync adapter
    And I assign client role "auth-operator" of client "auth-client" to user "authuser" using sync adapter
    And the keycloak fastapi auth requires all roles "auth-reader,auth-operator"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth request state user roles include "auth-reader,auth-operator"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth FastAPI dependency rejects missing credentials
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    When the keycloak auth fastapi dependency is called without credentials
    Then the keycloak auth call fails with error code "UNAUTHENTICATED"
    And the keycloak auth context is cleared after the dependency ends

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth FastAPI dependency rejects a garbage token
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    When the keycloak auth fastapi dependency is called with token "not-a-real-jwt"
    Then the keycloak auth call fails with error code "TOKEN_EXPIRED"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth FastAPI dependency rejects an expired token
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-expiry-realm" with display name "Auth Expiry Realm" using sync adapter
    And the keycloak auth realm "auth-expiry-realm" has an access token lifespan of 1 seconds
    And I create a client named "auth-expiry-client" in realm "auth-expiry-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authexpiring" and password "pass123" using sync adapter
    And the keycloak auth access token of user "authexpiring" is obtained with password "pass123"
    When the keycloak auth access token lifespan has elapsed
    And the keycloak auth fastapi dependency is called with the access token of user "authexpiring"
    Then the keycloak auth call fails with error code "TOKEN_EXPIRED"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth FastAPI dependency rejects a caller without the required role
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak fastapi auth requires any of roles "auth-admin"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "PERMISSION_DENIED"
    And the keycloak auth error lists required roles "auth-admin"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth FastAPI dependency requires every role when all roles are required
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak fastapi auth requires all roles "auth-reader,auth-writer"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "PERMISSION_DENIED"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth FastAPI dependency allows a granted UMA permission
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak auth client "auth-client" guards resource "auth-doc" with scopes "read,write" and grants scope "read" to realm role "auth-reader"
    And the keycloak fastapi auth requires permissions "auth-doc#read"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth dependency returns the user info of user "authuser"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth FastAPI dependency denies an ungranted UMA permission
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak auth client "auth-client" guards resource "auth-doc" with scopes "read,write" and grants scope "read" to realm role "auth-reader"
    And the keycloak fastapi auth requires permissions "auth-doc#read,auth-doc#write"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "PERMISSION_DENIED"
    And the keycloak auth error lists missing permission "auth-doc#write"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth FastAPI dependency denies a request when every UMA permission is ungranted
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak auth client "auth-client" guards resource "auth-doc" with scopes "read,write" and grants scope "read" to realm role "auth-reader"
    And the keycloak fastapi auth requires permissions "auth-doc#write"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "PERMISSION_DENIED"
    And the keycloak auth error lists missing permission "auth-doc#write"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth FastAPI dependency allows the owner of a resource
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And I create a user with username "authother" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authother" using sync adapter
    And the keycloak auth access token of user "authother" is obtained with password "pass123"
    And the keycloak fastapi auth guards resource type "users" by path parameter "user_uuid"
    And the keycloak auth request path parameter "user_uuid" is the id of user "authuser"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth dependency returns the user info of user "authuser"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth FastAPI dependency denies a non owner of a resource
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And I create a user with username "authother" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authother" using sync adapter
    And the keycloak auth access token of user "authother" is obtained with password "pass123"
    And the keycloak fastapi auth guards resource type "users" by path parameter "user_uuid"
    And the keycloak auth request path parameter "user_uuid" is the id of user "authother"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "PERMISSION_DENIED"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth FastAPI dependency lets an admin role bypass resource ownership
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And I create a user with username "authother" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authother" using sync adapter
    And the keycloak auth access token of user "authother" is obtained with password "pass123"
    And the keycloak fastapi auth guards resource type "users" by path parameter "user_uuid"
    And the keycloak fastapi auth treats roles "auth-reader" as admin roles
    And the keycloak auth request path parameter "user_uuid" is the id of user "authother"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth dependency returns the user info of user "authuser"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth FastAPI dependency rejects a request missing the resource path parameter
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak fastapi auth guards resource type "users" by path parameter "user_uuid"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "INVALID_ARGUMENT"

    Examples:
      | via    |
      | direct |
      | envoy  |

  @auth-guards
  Scenario Outline: Auth gRPC handler runs with the auth context for a valid token
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak grpc auth requires any of roles "auth-reader"
    When the keycloak auth <mode> grpc handler is invoked with the bearer access token of user "authuser"
    Then the keycloak auth grpc handler ran as user "authuser" with roles including "auth-reader"
    And the keycloak auth grpc handler returned "handled"
    And the keycloak auth context is cleared

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  @auth-guards
  Scenario Outline: Auth gRPC handler accepts a raw token without the bearer prefix
    Given a configured sync Keycloak adapter via <via>
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    When the keycloak auth <mode> grpc handler is invoked with the raw access token of user "authuser"
    Then the keycloak auth grpc handler ran as user "authuser" with roles including "auth-reader"

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

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
    When the keycloak auth context is set for user "user-9"
    Then the keycloak auth context belongs to user "user-9"

  Scenario: Auth context manager clears the context
    Given the keycloak auth context is set for user "user-9"
    When the keycloak auth context is cleared by the manager
    Then the keycloak auth context is cleared

  Scenario: Auth context manager restores the outer context when cleared with the token of a nested one
    Given the keycloak auth context is set for user "outer-user"
    When the keycloak auth context of user "inner-user" is set and then cleared with its token
    Then the keycloak auth context belongs to user "outer-user"

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

  Scenario Outline: Auth userinfo lookups are cached for the configured TTL
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And the keycloak auth adapter caches remote lookups for 60 seconds
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    And the keycloak auth sessions of user "authuser" are cleared
    And the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth dependency returns the user info of user "authuser"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth cached lookups are looked up again after the TTL
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And the keycloak auth adapter caches remote lookups for 60 seconds
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    And the keycloak auth sessions of user "authuser" are cleared
    And the keycloak auth cached lookups expire
    And the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "INVALID_CREDENTIALS"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth cached lookups are kept apart per token
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And I create a user with username "authother" and password "pass123" using sync adapter
    And I assign realm role "auth-reader" to user "authother" using sync adapter
    And the keycloak auth access token of user "authother" is obtained with password "pass123"
    And the keycloak auth adapter caches remote lookups for 60 seconds
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    And the keycloak auth fastapi dependency is called with the access token of user "authother"
    Then the keycloak auth dependency returns the user info of user "authother"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth permission lookups are cached for the configured TTL
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And the keycloak auth client "auth-client" guards resource "auth-doc-cached" with scopes "read,write" and grants scope "read" to realm role "auth-reader"
    And the keycloak auth client "auth-client" guards resource "auth-doc-cached" with scopes "read,write" and grants scope "write" to realm role "auth-reader"
    And the keycloak auth adapter caches remote lookups for 60 seconds
    And the keycloak fastapi auth requires permissions "auth-doc-cached#read,auth-doc-cached#write"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    And the keycloak auth permission granting scope "read" on resource "auth-doc-cached" of client "auth-client" is deleted
    And the keycloak adapter's own permission cache is cleared
    And the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth dependency returns the user info of user "authuser"

    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth permission lookups are not cached unless a TTL is configured
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And the keycloak auth client "auth-client" guards resource "auth-doc-uncached" with scopes "read,write" and grants scope "read" to realm role "auth-reader"
    And the keycloak auth client "auth-client" guards resource "auth-doc-uncached" with scopes "read,write" and grants scope "write" to realm role "auth-reader"
    And the keycloak fastapi auth requires permissions "auth-doc-uncached#read,auth-doc-uncached#write"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    And the keycloak auth permission granting scope "read" on resource "auth-doc-uncached" of client "auth-client" is deleted
    And the keycloak adapter's own permission cache is cleared
    And the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "PERMISSION_DENIED"

    Examples:
      | via    |
      | direct |
      | envoy  |

  @auth-guards
  Scenario Outline: Auth gRPC handler reads the bearer scheme case-insensitively
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And the keycloak grpc auth requires any of roles "auth-reader"
    When the keycloak auth <mode> grpc handler is invoked with the access token of user "authuser" under authorization scheme "BEARER"
    Then the keycloak auth grpc handler ran as user "authuser" with roles including "auth-reader"

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  @auth-guards
  Scenario Outline: Auth gRPC handler rejects an empty bearer credential
    Given a keycloak auth realm with a client via <via>
    And the keycloak grpc auth requires any of roles "auth-reader"
    When the keycloak auth <mode> grpc handler is invoked with metadata key "authorization" value "Bearer "
    Then the keycloak auth servicer context was aborted with status "UNAUTHENTICATED"
    And the keycloak auth grpc handler did not run

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  @auth-guards
  Scenario Outline: Auth gRPC handler rejects conflicting authorization headers
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And the keycloak grpc auth requires any of roles "auth-reader"
    When the keycloak auth <mode> grpc handler is invoked with a conflicting bearer token "other-token" next to the access token of user "authuser"
    Then the keycloak auth servicer context was aborted with status "UNAUTHENTICATED"
    And the keycloak auth grpc handler did not run

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  Scenario Outline: Auth FastAPI dependency rejects a token without userinfo
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth sessions of user "authuser" are cleared
    And the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "INVALID_CREDENTIALS"

    # A real Keycloak cannot be made to return empty claims for a token that it just issued and that passed
    # validation, so this one defensive branch injects an empty claims result into the real adapter.
    Examples:
      | via    |
      | direct |
      | envoy  |

  Scenario Outline: Auth FastAPI dependency rejects a token whose claims cannot be read
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token via <via>
    And the keycloak auth adapter cannot read the claims of issued tokens
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "TOKEN_EXPIRED"

    Examples:
      | via    |
      | direct |
      | envoy  |

  @tracing
  Scenario Outline: Keycloak <mode> adapter requests emit HTTP spans
    Given adapter spans are exported to the collector
    And a configured <mode> Keycloak adapter via <via>
    When I create a realm named "span-realm" with display name "Span Realm" using <mode> adapter
    Then the collector should have a span with attribute "http.url" containing "/admin/realms"

    Examples:
      | mode  | via    |
      | sync  | direct |
      | async | direct |
      | sync  | envoy  |
      | async | envoy  |

  @gateway
  Scenario Outline: Envoy routes <host> host requests for <path>
    Given the Keycloak realms "app" and "master2" exist
    When I request "<path>" on the "<host>" host
    Then the response status is <status>

    Examples:
      | host   | path                                             | status |
      | public | /realms/app/.well-known/openid-configuration     | 200    |
      | public | /realms/master2/.well-known/openid-configuration | 200    |
      | public | /realms/master                                   | 404    |
      | public | /realms/master/                                  | 404    |
      | public | /realms/master/.well-known/openid-configuration  | 404    |
      | public | /realms/master/protocol/openid-connect/token     | 404    |
      | public | /admin/master/console/                           | 404    |
      | public | /admin/realms/app                                | 404    |
      | admin  | /admin/master/console/                           | 200    |
      | admin  | /realms/master/.well-known/openid-configuration  | 200    |
      | admin  | /realms/app/.well-known/openid-configuration     | 404    |
      | admin  | /realms/master2/.well-known/openid-configuration | 404    |
      | admin  | /                                                | 404    |

  @gateway
  Scenario Outline: The admin console loads every URL from the <present> host
    Given the Keycloak realms "app" and "master2" exist
    When I request "/admin/master/console/" on the "<present>" host
    Then the response body contains the <present> host
    And the response body does not contain the <absent> host

    Examples:
      | present | absent |
      | admin   | public |

  @gateway
  Scenario Outline: A resource linked from the admin console is served on the <host> host
    Given the Keycloak realms "app" and "master2" exist
    When I request "/admin/master/console/" on the "<host>" host
    And I request the first resource linked from the response on the "<host>" host
    Then the response status is <status>

    Examples:
      | host  | status |
      | admin | 200    |

  @gateway
  Scenario Outline: The master realm token endpoint through the <host> host answers <status>
    Given the Keycloak realms "app" and "master2" exist
    When I request an admin token for the "master" realm on the "<host>" host
    Then the response status is <status>
    And the response access token is <token>

    Examples:
      | host   | status | token   |
      | admin  | 200    | present |
      | public | 404    | absent  |

  @gateway
  Scenario Outline: The <realm> realm issuer on the <host> host is the <expected> host
    Given the Keycloak realms "app" and "master2" exist
    Then the "<realm>" realm issuer on the "<host>" host is the <expected> host

    Examples:
      | realm  | host   | expected |
      | master | admin  | admin    |
      | app    | public | public   |
