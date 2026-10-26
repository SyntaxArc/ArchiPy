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
