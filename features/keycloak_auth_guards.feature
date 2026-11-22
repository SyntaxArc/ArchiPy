# features/keycloak_auth_guards.feature
@needs-keycloak @needs-envoy @needs-otel-collector
Feature: Keycloak Auth Guards Testing
  As a developer
  I want to test Keycloak authentication operations
  So that I can ensure secure authentication and management operations

  # --- Keycloak auth dependencies and decorators ---
  # Real tokens issued by the Keycloak container drive keycloak.auth fastapi_auth, grpc_auth and
  # AuthContextManager. gRPC uses a ServicerContext fake only to record aborts.
  Scenario Outline: Auth FastAPI dependency sets the auth context for a valid token
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
    And the keycloak auth context user roles include "auth-reader"
    And the keycloak auth context has an empty actor chain
    And the keycloak auth context holds user "authuser" while the dependency is active
    And the request state has no Keycloak auth fields
    And the keycloak auth context is cleared after the dependency ends

    Examples:
      | via    |
      | direct |
      | envoy  |

  @auth-guards
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
    Then the keycloak auth context user roles include "auth-reader,auth-operator"

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

  @organization-scope
  Scenario Outline: Auth guards read UserInfo organizations while access tokens stay minimal
    Given a keycloak auth realm with a client via <via>
    And I enable organization of realm named "auth-realm"
    And I create a user with username "orguser" and password "pass123" using sync adapter
    And user "orguser" belongs to <count> organizations with organization IDs enabled in UserInfo
    And the default organization requirement is <configured>
    And the organization requirement of the guard is "<override>"
    When user "orguser" obtains a token with organization scope "<scope>"
    And the organization <transport> guard is called for user "orguser"
    Then the organization guard outcome is "<outcome>"
    And the keycloak auth context is cleared

    Examples:
      | via    | count | scope    | configured | override | transport  | outcome  |
      | direct | 0     | personal | false      | default  | fastapi    | accepted |
      | direct | 1     | selected | false      | true     | fastapi    | accepted |
      | direct | 2     | all      | false      | default  | fastapi    | accepted |
      | direct | 1     | all      | false      | true     | fastapi    | denied   |
      | direct | 0     | personal | true       | default  | fastapi    | denied   |
      | direct | 0     | personal | true       | false    | fastapi    | accepted |
      | direct | 0     | personal | false      | true     | fastapi    | denied   |
      | direct | 0     | personal | false      | default  | grpc sync  | accepted |
      | direct | 1     | selected | false      | true     | grpc sync  | accepted |
      | direct | 2     | all      | false      | default  | grpc sync  | accepted |
      | direct | 1     | all      | false      | true     | grpc sync  | denied   |
      | direct | 0     | personal | true       | default  | grpc sync  | denied   |
      | direct | 0     | personal | true       | false    | grpc sync  | accepted |
      | direct | 0     | personal | false      | true     | grpc sync  | denied   |
      | direct | 0     | personal | false      | default  | grpc async | accepted |
      | direct | 1     | selected | false      | true     | grpc async | accepted |
      | direct | 2     | all      | false      | default  | grpc async | accepted |
      | direct | 1     | all      | false      | true     | grpc async | denied   |
      | direct | 0     | personal | true       | default  | grpc async | denied   |
      | direct | 0     | personal | true       | false    | grpc async | accepted |
      | direct | 0     | personal | false      | true     | grpc async | denied   |
      | envoy  | 1     | selected | false      | true     | fastapi    | accepted |
      | direct | 1     | aliases  | false      | default  | fastapi    | accepted |
      | direct | 2     | multiple | false      | default  | fastapi    | denied   |
      | direct | 1     | aliases  | false      | default  | grpc sync  | accepted |
      | direct | 2     | multiple | false      | default  | grpc sync  | denied   |
      | direct | 1     | aliases  | false      | default  | grpc async | accepted |
      | direct | 2     | multiple | false      | default  | grpc async | denied   |

  @organization-attributes
  Scenario Outline: Auth guards preserve organization attributes returned by UserInfo
    Given a keycloak auth realm with a client
    And I enable organization of realm named "auth-realm"
    And I create a user with username "orguser" and password "pass123" using sync adapter
    And user "orguser" belongs to <count> organizations with organization IDs enabled in UserInfo
    And the organizations have these attributes
      | attribute   | values                     |
      | plan        | ["enterprise"]             |
      | country     | ["DE"]                     |
      | website     | ["https://acme.example"]   |
      | departments | ["engineering", "support"] |
      | locale      | ["de-DE"]                  |
      | custom_code | ["customer-42"]            |
    When user "orguser" obtains a token with organization scope "<scope>"
    And the organization <transport> guard is called for user "orguser"
    Then organization DTOs expose the configured attributes and preserve them when serialized
    And the keycloak auth context is cleared

    Examples:
      | count | scope    | transport  |
      | 1     | selected | fastapi    |
      | 2     | all      | fastapi    |
      | 1     | selected | grpc sync  |
      | 2     | all      | grpc sync  |
      | 1     | selected | grpc async |
      | 2     | all      | grpc async |

  @ownership-integration
  Scenario Outline: FastAPI resolves resource ownership from real Keycloak authentication
    Given a keycloak auth realm with a client
    And I enable organization of realm named "auth-realm"
    And I create a user with username "orguser" and password "pass123" using sync adapter
    And user "orguser" belongs to <count> organizations with organization IDs enabled in UserInfo
    And the default organization requirement is false
    When user "orguser" obtains a token with organization scope "<scope>"
    And the fastapi endpoint resolves ownership using "<resolver>" for user "orguser"
    Then the authenticated ownership outcome is "<outcome>" for user "orguser"
    And the keycloak auth context is cleared

    Examples:
      | count | scope            | resolver | outcome      |
      | 0     | personal         | explicit | USER         |
      | 2     | personal         | request  | USER         |
      | 1     | selected         | explicit | ORGANIZATION |
      | 2     | selected         | request  | ORGANIZATION |
      | 1     | all              | request  | denied       |
      | 2     | all              | explicit | denied       |
      | 1     | aliases-selected | explicit | denied       |
      | 1     | aliases-selected | request  | denied       |

  @malformed-user-uuid
  Scenario: FastAPI rejects a malformed UserInfo subject as unauthenticated
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And Keycloak UserInfo reports subject "not-a-uuid" for user "authuser"
    When the protected identity endpoint is called with the access token of user "authuser"
    Then the protected identity endpoint rejects the caller as unauthenticated
    And the keycloak auth context is cleared

  @unit @keycloak-ownership
  Scenario: Resolve personal ownership
    Given an ownership context with scope "openid" and organizations "none" and selection "none"
    When I resolve the authenticated owner explicitly
    Then the resolved owner is "USER" with UUID "11111111-1111-4111-8111-111111111111"
    And the authenticated user ID is a UUID and serializes as a string
    And the resolved owner is immutable
    And the public owner DTO has documented fields and no legacy alias

  @unit @keycloak-ownership
  Scenario Outline: Actor and owner helpers identify both parties consistently
    Given an ownership context with scope "openid" and organizations "none" and selection "none"
    And the acting chain is "<chain>"
    When I resolve the authenticated actor
    Then the actor is "<type>" with identifier "<identifier>"
    When I resolve the authenticated actor and owner together
    Then the actor is "<type>" with identifier "<identifier>"
    And the resolved owner is "USER" with UUID "11111111-1111-4111-8111-111111111111"
    And the keycloak auth context is cleared

    Examples:
      | chain  | type   | identifier                           |
      | direct | USER   | 11111111-1111-4111-8111-111111111111 |
      | user   | USER   | 44444444-4444-4444-8444-444444444444 |
      | client | CLIENT | service-client                       |
      | nested | CLIENT | service-client                       |

  @unit @keycloak-ownership
  Scenario: The actor helper rejects unauthenticated access
    Given no keycloak auth context is set
    When I resolve the authenticated actor
    Then ownership resolution fails with "UNAUTHENTICATED"

  @unit @keycloak-ownership
  Scenario: Combined actor and owner helper rejects unauthenticated access
    Given no keycloak auth context is set
    When I resolve the authenticated actor and owner together
    Then ownership resolution fails with "UNAUTHENTICATED"

  @unit @keycloak-ownership
  Scenario: Combined helper does not return a partial result for ambiguous ownership
    Given an ownership context with scope "openid organization:*" and organizations "selected" and selection "none"
    When I resolve the authenticated actor and owner together
    Then ownership resolution fails with "PERMISSION_DENIED"

  @unit @keycloak-ownership
  Scenario Outline: Owner claim details must match the ownership identity
    When I construct a "<type>" owner with "<claims>" claim details
    Then the owner rejects inconsistent claim details

    Examples:
      | type         | claims                 |
      | USER         | different user         |
      | USER         | organization           |
      | ORGANIZATION | user                   |
      | ORGANIZATION | different organization |
      | USER         | malformed user subject |

  @unit @keycloak-ownership
  Scenario: Resolve a selected organization
    Given an ownership context with scope "openid organization:acme" and organizations "selected" and selection "selected"
    When I resolve the authenticated owner explicitly
    Then the resolved owner is "ORGANIZATION" with UUID "22222222-2222-4222-8222-222222222222"

  @unit @keycloak-ownership
  Scenario Outline: Reject ambiguous and inconsistent organization ownership
    Given an ownership context with scope "<scope>" and organizations "<organizations>" and selection "<selection>"
    When I resolve the authenticated owner explicitly
    Then ownership resolution fails with "PERMISSION_DENIED"

    Examples:
      | scope                    | organizations | selection  |
      | openid organization:*    | none          | none       |
      | openid organization:*    | selected      | none       |
      | openid organization:*    | selected      | selected   |
      | openid organization:*    | multiple      | none       |
      | openid organization      | none          | none       |
      | openid organization:acme | none          | none       |
      | openid                   | aliases       | none       |
      | openid                   | selected      | none       |
      | openid                   | multiple      | none       |
      | openid                   | none          | selected   |
      | openid                   | selected      | other      |
      | openid                   | selected      | missing-id |
      | openid                   | multiple      | selected   |
      | openid                   | mixed         | selected   |

  @unit @keycloak-ownership
  Scenario: Never fall back to personal ownership when only raw claims contain an organization
    Given an ownership context with scope "openid" and organizations "none" and selection "none"
    And only raw UserInfo contains an organization claim
    When I resolve the authenticated owner explicitly
    Then ownership resolution fails with "PERMISSION_DENIED"

  @unit @keycloak-ownership
  Scenario: Personal ownership belongs to the subject during impersonation
    Given an ownership context with scope "openid" and organizations "none" and selection "none"
    And the ownership context has an impersonating actor
    When I resolve the owner through the request context
    Then the resolved owner is "USER" with UUID "11111111-1111-4111-8111-111111111111"

  @unit @keycloak-ownership
  Scenario: The request helper resolves organization ownership
    Given an ownership context with scope "openid organization:acme" and organizations "selected" and selection "selected"
    When I resolve the owner through the request context
    Then the resolved owner is "ORGANIZATION" with UUID "22222222-2222-4222-8222-222222222222"

  @unit @keycloak-ownership
  Scenario: The request helper rejects wildcard ownership
    Given an ownership context with scope "openid organization:*" and organizations "selected" and selection "none"
    When I resolve the owner through the request context
    Then ownership resolution fails with "PERMISSION_DENIED"

  @unit @keycloak-ownership
  Scenario: The request helper rejects unauthenticated access
    Given no keycloak auth context is set
    When I resolve the owner through the request context
    Then ownership resolution fails with "UNAUTHENTICATED"

  @unit @keycloak-ownership
  Scenario Outline: Malformed UUIDs cannot enter the authenticated context
    When I construct an ownership context with malformed "<field>"
    Then the ownership context fails UUID validation

    Examples:
      | field                      |
      | user UUID                  |
      | organization UUID          |
      | selected organization UUID |
