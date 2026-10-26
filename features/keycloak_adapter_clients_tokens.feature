# features/keycloak_adapter_clients_tokens.feature
@needs-keycloak @needs-envoy @needs-otel-collector
Feature: Keycloak Clients, Keys and Tokens Testing
  As a developer
  I want to test Keycloak authentication operations
  So that I can ensure secure authentication and management operations

  @realms
  Scenario Outline: Realm administration with events, policies, localization, import and deletion
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    Then the realm "<realm_name>" is listed and its event settings, client policies, profiles and types round-trip using <adapter_type> adapter
    And the realm "<realm_name>" records and clears events and admin events using <adapter_type> adapter
    And the realm "<realm_name>" manages default groups and localization texts using <adapter_type> adapter
    And the realm "<realm_name>" exports, imports, logs everyone out and pushes revocation using <adapter_type> adapter
    And the realm "<realm_name>" deletes a session, reports SMTP and permission settings and can be deleted using <adapter_type> adapter

    Examples:
      | adapter_type | realm_name              | realm_display_name | client_name         | via    |
      | sync         | realm-admin-sync        | Realm Admin Sync   | realm-admin-client  | direct |
      | async        | realm-admin-async       | Realm Admin Async  | realm-admin-aclient | direct |
      | sync         | realm-admin-sync-envoy  | Realm Admin Sync   | realm-admin-client  | envoy  |
      | async        | realm-admin-async-envoy | Realm Admin Async  | realm-admin-aclient | envoy  |

  @realms
  Scenario Outline: Realm keys, attack detection, initial access tokens and client certificates
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    Then the realm keys and the client registration policy providers are listed using <adapter_type> adapter
    And the brute force status of user "<username>" is read and cleared using <adapter_type> adapter
    And a client initial access token is created, listed and deleted using <adapter_type> adapter
    And the client "<client_name>" generates and downloads a certificate using <adapter_type> adapter

    Examples:
      | adapter_type | username      | password | realm_name       | realm_display_name | client_name  | via    |
      | sync         | miscuser      | pass123  | test-realm       | Test Realm         | misc-client  | direct |
      | async        | asyncmiscuser | async123 | test-realm       | Async Test Realm   | amisc-client | direct |
      | sync         | miscuser      | pass123  | test-realm-envoy | Test Realm         | misc-client  | envoy  |
      | async        | asyncmiscuser | async123 | test-realm-envoy | Async Test Realm   | amisc-client | envoy  |

  @realms
  Scenario Outline: Identity providers with mappers
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I create the identity provider "<idp_alias>" with a mapper "<mapper>" using <adapter_type> adapter
    Then the identity provider "<idp_alias>" and its mapper "<mapper>" are listed, read, updated and deleted using <adapter_type> adapter

    Examples:
      | adapter_type | idp_alias | mapper     | realm_name       | realm_display_name | client_name | via    |
      | sync         | idp-main  | role-sync  | test-realm       | Test Realm         | idp-client  | direct |
      | async        | aidp-main | arole-sync | test-realm       | Async Test Realm   | aidp-client | direct |
      | sync         | idp-main  | role-sync  | test-realm-envoy | Test Realm         | idp-client  | envoy  |
      | async        | aidp-main | arole-sync | test-realm-envoy | Async Test Realm   | aidp-client | envoy  |

  @tokens
  Scenario Outline: Token exchange and the JWT authorization grant
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I enable standard token exchange on the client "<client_name>" using <adapter_type> adapter
    Then the access token of "<username>" with password "<password>" is exchanged for another access token and an ID token using <adapter_type> adapter
    When I trust an external issuer for the client "<client_name>" and link user "<username>" as "<external>" using <adapter_type> adapter
    Then a JWT signed by the external issuer is traded for an access token using <adapter_type> adapter

    Examples:
      | adapter_type | username      | password | external | realm_name       | realm_display_name | client_name      | via    |
      | sync         | exchuser      | pass123  | exchext  | test-realm       | Test Realm         | exchange-client  | direct |
      | async        | asyncexchuser | async123 | aexchext | test-realm       | Async Test Realm   | aexchange-client | direct |
      | sync         | exchuser      | pass123  | exchext  | test-realm-envoy | Test Realm         | exchange-client  | envoy  |
      | async        | asyncexchuser | async123 | aexchext | test-realm-envoy | Async Test Realm   | aexchange-client | envoy  |

  @authz
  Scenario Outline: Requesting party tokens and AuthZEN decisions
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I enable authorization services for client "<client_name>" using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I protect the resource "<resource>" with scope "<scope>" for the realm role "offline_access" on client "<client_name>" using <adapter_type> adapter
    Then the user "<username>" with password "<password>" gets a requesting party token for "<resource>#<scope>" using <adapter_type> adapter
    And AuthZEN decides access to "<resource>" for "<username>" as granted for "<scope>" and denied for "write" using <adapter_type> adapter

    Examples:
      | adapter_type | username     | password | resource | scope | realm_name       | realm_display_name | client_name | via    |
      | sync         | rptuser      | pass123  | rpt-doc  | read  | test-realm       | Test Realm         | rpt-client  | direct |
      | async        | asyncrptuser | async123 | arpt-doc | read  | test-realm       | Async Test Realm   | arpt-client | direct |
      | sync         | rptuser      | pass123  | rpt-doc  | read  | test-realm-envoy | Test Realm         | rpt-client  | envoy  |
      | async        | asyncrptuser | async123 | arpt-doc | read  | test-realm-envoy | Async Test Realm   | arpt-client | envoy  |

  @roles
  Scenario Outline: Required actions, authentication providers and roles by name
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    Then the authenticator, form and client authenticator providers are listed using <adapter_type> adapter
    And the required actions are listed, updated and reordered, and their settings are described using <adapter_type> adapter
    When I manage the realm role "<role>" and the client role "<client_role>" of client "<client_name>" by name using <adapter_type> adapter
    Then the roles "<role>" and "<client_role>" are listed with composites, users and groups using <adapter_type> adapter

    Examples:
      | adapter_type | role        | client_role  | realm_name       | realm_display_name | client_name   | via    |
      | sync         | named-role  | named-crole  | test-realm       | Test Realm         | named-client  | direct |
      | async        | anamed-role | anamed-crole | test-realm       | Async Test Realm   | anamed-client | direct |
      | sync         | named-role  | named-crole  | test-realm-envoy | Test Realm         | named-client  | envoy  |
      | async        | anamed-role | anamed-crole | test-realm-envoy | Async Test Realm   | anamed-client | envoy  |

  @authz
  Scenario Outline: Authorization queries, evaluation, protocol mapper bulk calls and group and component settings
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I enable authorization services for client "<client_name>" using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I protect the resource "<resource>" with scope "read" for the realm role "offline_access" on client "<client_name>" using <adapter_type> adapter
    Then the resource "<resource>" and scope "read" of client "<client_name>" are found, filtered, searched and described using <adapter_type> adapter
    And the policies and permissions of client "<client_name>" are found, searched, listed by provider and evaluated for user "<username>" using <adapter_type> adapter
    And the client scope "<scope>" lists, bulk-adds and reads protocol mappers by id and protocol, and the group "<group>" and a component report their settings using <adapter_type> adapter

    Examples:
      | adapter_type | username     | password | resource | scope     | group     | realm_name       | realm_display_name | client_name | via    |
      | sync         | azxuser      | pass123  | az-doc   | az-scope  | az-group  | test-realm       | Test Realm         | az-client   | direct |
      | async        | asyncazxuser | async123 | aaz-doc  | aaz-scope | aaz-group | test-realm       | Async Test Realm   | aaz-client  | direct |
      | sync         | azxuser      | pass123  | az-doc   | az-scope  | az-group  | test-realm-envoy | Test Realm         | az-client   | envoy  |
      | async        | asyncazxuser | async123 | aaz-doc  | aaz-scope | aaz-group | test-realm-envoy | Async Test Realm   | aaz-client  | envoy  |

  @clientscopes
  Scenario Outline: Typed protocol mapper configs change the tokens
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a client named "<audience_client>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I add a typed hardcoded claim mapper "typed-claim-mapper" with claim "<claim>" and value "gold" to the client scope "<scope>" assigned to client "<client_name>" using <adapter_type> adapter
    Then the typed mapper config is read back and the example token of client "<client_name>" carries claim "<claim>" as "gold" using <adapter_type> adapter
    When I change the typed mapper to value "platinum" using <adapter_type> adapter
    Then the typed mapper config is read back and the example token of client "<client_name>" carries claim "<claim>" as "platinum" using <adapter_type> adapter
    When I add a typed audience mapper for client "<audience_client>" and a typed claim mapper "typed-client-claim" with claim "<client_claim>" and value "direct" to client "<client_name>" using <adapter_type> adapter
    Then the typed client mappers are read back, updated and the example token of client "<client_name>" shows claim "<client_claim>" as "direct" and audience "<audience_client>" using <adapter_type> adapter

    Examples:
      | adapter_type | scope        | claim | client_claim | realm_name       | realm_display_name | client_name   | audience_client | via    |
      | sync         | typed-scope  | tier  | origin       | test-realm       | Test Realm         | typed-client  | typed-audience  | direct |
      | async        | atyped-scope | atier | aorigin      | test-realm       | Async Test Realm   | atyped-client | atyped-audience | direct |
      | sync         | typed-scope  | tier  | origin       | test-realm-envoy | Test Realm         | typed-client  | typed-audience  | envoy  |
      | async        | atyped-scope | atier | aorigin      | test-realm-envoy | Async Test Realm   | atyped-client | atyped-audience | envoy  |

  @tokens
  Scenario Outline: Chaining identity across two realms with token exchange and the JWT authorization grant
    Given a configured <adapter_type> Keycloak adapter via <via>
    When I set up domain A "<realm_a>" with client "<client_a>", user "<username>" and domain B "<realm_b>" as an audience using <adapter_type> adapter
    And I set up domain B "<realm_b>" with client "<client_b>" trusting domain A through the identity provider "<alias>" using <adapter_type> adapter
    Then a token from domain A is exchanged for a JWT assertion and redeemed in domain B using <adapter_type> adapter

    Examples:
      | adapter_type | realm_a             | realm_b             | client_a | client_b | username   | alias    | via    |
      | sync         | chain-a-sync        | chain-b-sync        | clienta  | clientb  | chainuser  | domaina  | direct |
      | async        | chain-a-async       | chain-b-async       | aclienta | aclientb | achainuser | adomaina | direct |
      | sync         | chain-a-sync-envoy  | chain-b-sync-envoy  | clienta  | clientb  | chainuser  | domaina  | envoy  |
      | async        | chain-a-async-envoy | chain-b-async-envoy | aclienta | aclientb | achainuser | adomaina | envoy  |

  @authz
  Scenario Outline: UMA permission checks with several permissions and creating an existing realm
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I enable authorization services for client "<client_name>" using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I protect the resource "<resource>" with scope "read" for the realm role "offline_access" on client "<client_name>" using <adapter_type> adapter
    And I protect the resource "<resource2>" with scope "write" for the realm role "offline_access" on client "<client_name>" using <adapter_type> adapter
    And I remember the user "<username>" with password "<password>" for the UMA checks using <adapter_type> adapter
    Then UMA permissions_check answers true for "<resource>#read" and "<resource2>#write" together and false when "<resource>#write" is added using <adapter_type> adapter
    And creating the realm "<realm_name>" again with skip_exists reports it as existing and without skip_exists fails using <adapter_type> adapter

    Examples:
      | adapter_type | username     | password | resource | resource2 | realm_name       | realm_display_name | client_name       | via    |
      | sync         | umauser      | pass123  | uma-doc  | uma-doc2  | test-realm       | Test Realm         | uma-check-client  | direct |
      | async        | asyncumauser | async123 | auma-doc | auma-doc2 | test-realm       | Async Test Realm   | auma-check-client | direct |
      | sync         | umauser      | pass123  | uma-doc  | uma-doc2  | test-realm-envoy | Test Realm         | uma-check-client  | envoy  |
      | async        | asyncumauser | async123 | auma-doc | auma-doc2 | test-realm-envoy | Async Test Realm   | auma-check-client | envoy  |

  @components
  Scenario Outline: Component listing
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I get all components using <adapter_type> adapter
    Then the <adapter_type> components request should succeed

    Examples:
      | adapter_type | realm_name             | realm_display_name | client_name       | via    |
      | sync         | test-realm             | Test Realm         | test-client       | direct |
      | async        | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @impersonation
  Scenario: Token without act claim is not impersonated
    Given a decoded token without an act claim
    When the auth context is built
    Then the auth context is not impersonated

  @impersonation
  Scenario: Token with nested act claim exposes the actor chain
    Given a decoded token with act sub "admin-1" nested under act client "agent-app"
    When the auth context is built
    Then the auth context is impersonated by "admin-1"
    And the actor chain has 2 entries
    And the propagation headers carry the bearer token
