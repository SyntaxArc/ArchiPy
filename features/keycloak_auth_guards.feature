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

  Scenario Outline: Auth FastAPI dependency refuses a resource guard with only one of its two arguments
    Given a configured sync Keycloak adapter via <via>
    And the keycloak fastapi auth sets only its <argument> to "<value>"
    When the keycloak auth fastapi dependency is called without credentials
    Then the keycloak auth call fails with error code "CONFIGURATION_ERROR"

    Examples:
      | via    | argument       | value     |
      | direct | resource type  | users     |
      | direct | path parameter | user_uuid |

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
