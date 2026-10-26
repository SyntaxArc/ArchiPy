# features/keycloak_adapter_management.feature
@needs-keycloak @needs-envoy @needs-otel-collector
Feature: Keycloak Management Testing
  As a developer
  I want to test Keycloak authentication operations
  So that I can ensure secure authentication and management operations

  @groups
  Scenario Outline: Group CRUD hierarchy membership and roles
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I create coverage roles for group "<group_name>" and client "<client_name>" using <adapter_type> adapter
    When I create a group named "<group_name>" using <adapter_type> adapter
    Then group creation with the <adapter_type> adapter should succeed
    When I get all groups using <adapter_type> adapter
    Then the groups list should contain group "<group_name>"
    When I get the group count using <adapter_type> adapter
    Then the <adapter_type> groups count request should succeed
    When I get group "<group_name>" by id using <adapter_type> adapter
    Then the <adapter_type> group get by id should succeed
    When I get group "<group_name>" by path using <adapter_type> adapter
    Then the <adapter_type> group get by path should succeed
    When I update group "<group_name>" using <adapter_type> adapter
    Then the <adapter_type> group update should succeed
    When I create a child group under "<group_name>" using <adapter_type> adapter
    Then child group creation with the <adapter_type> adapter should succeed
    When I list child groups of "<group_name>" using <adapter_type> adapter
    Then the <adapter_type> group children list should succeed
    When I get subgroups under "<group_name>" using <adapter_type> adapter
    Then the <adapter_type> subgroups get should succeed
    When I add user "<username>" to group "<group_name>" using <adapter_type> adapter
    Then the <adapter_type> group user add should succeed
    When I list members of group "<group_name>" using <adapter_type> adapter
    Then the <adapter_type> group members list should succeed
    When I assign coverage realm roles to group "<group_name>" using <adapter_type> adapter
    Then assigning realm roles to the group with the <adapter_type> adapter should succeed
    When I list realm roles for group "<group_name>" using <adapter_type> adapter
    Then the <adapter_type> group realm roles list should succeed
    When I assign coverage client roles to group "<group_name>" for client "<client_name>" using <adapter_type> adapter
    Then assigning client roles to the group with the <adapter_type> adapter should succeed
    When I list client roles for group "<group_name>" and client "<client_name>" using <adapter_type> adapter
    Then the <adapter_type> group client roles list should succeed
    When I get composite client roles for group "<group_name>" and client "<client_name>" using <adapter_type> adapter
    Then the <adapter_type> composite client roles get should succeed
    When I list groups that have the coverage realm role using <adapter_type> adapter
    Then the <adapter_type> realm role groups list should succeed
    When I list groups that have the coverage client role for client "<client_name>" using <adapter_type> adapter
    Then the <adapter_type> client role groups list should succeed
    When I enable permissions on group "<group_name>" using <adapter_type> adapter
    Then the <adapter_type> group permissions step should succeed or be skipped
    When I remove coverage realm roles from group "<group_name>" using <adapter_type> adapter
    Then removing realm roles from the group with the <adapter_type> adapter should succeed
    When I remove coverage client roles from group "<group_name>" for client "<client_name>" using <adapter_type> adapter
    Then removing client roles from the group with the <adapter_type> adapter should succeed
    When I remove user "<username>" from group "<group_name>" using <adapter_type> adapter
    Then the <adapter_type> group user remove should succeed
    When I delete the child group under "<group_name>" using <adapter_type> adapter
    Then deleting the child group with the <adapter_type> adapter should succeed
    When I delete group "<group_name>" using <adapter_type> adapter
    Then deleting the parent group with the <adapter_type> adapter should succeed

    Examples:
      | adapter_type | username  | password | group_name  | realm_name             | realm_display_name | client_name       | via    |
      | sync         | groupuser | pass123  | test-group  | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncgrp  | async123 | async-group | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | groupuser | pass123  | test-group  | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncgrp  | async123 | async-group | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @authflows
  Scenario Outline: Create and manage authentication flows
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I create a coverage authentication flow using <adapter_type> adapter
    Then the <adapter_type> authentication flow creation should succeed
    And the coverage flow creation result has the id of the new resource
    When I list all authentication flows using <adapter_type> adapter
    Then the authentication flows list should include the coverage flow
    When I get the coverage authentication flow by id using <adapter_type> adapter
    Then the <adapter_type> authentication flow get by id should succeed
    When I update the coverage authentication flow description using <adapter_type> adapter
    Then the <adapter_type> authentication flow update should succeed
    When I copy the coverage authentication flow using <adapter_type> adapter
    Then the <adapter_type> authentication flow copy should succeed
    And the coverage copy creation result has the id of the new resource
    When I add a subflow to the coverage authentication flow using <adapter_type> adapter
    Then the <adapter_type> authentication subflow creation should succeed
    And the coverage subflow creation result has the id of the new resource
    When I add a username-password execution to the coverage flow using <adapter_type> adapter
    Then the <adapter_type> authentication execution creation should succeed
    And the coverage execution creation result has the id of the new resource
    When I list executions for the coverage authentication flow using <adapter_type> adapter
    Then the <adapter_type> authentication executions list should succeed
    When I get the coverage flow execution details using <adapter_type> adapter
    Then the <adapter_type> authentication execution get should succeed
    When I update the coverage flow execution using <adapter_type> adapter
    Then the <adapter_type> authentication execution update should succeed
    When I change the coverage flow execution priority using <adapter_type> adapter
    Then the <adapter_type> execution priority change should succeed
    When I list authenticator providers using <adapter_type> adapter
    Then the <adapter_type> authenticator providers list should succeed
    When I get the username-password authenticator config description using <adapter_type> adapter
    Then the <adapter_type> authenticator config description get should succeed
    When I create execution config for the coverage flow execution using <adapter_type> adapter
    Then the <adapter_type> execution config step should succeed or be skipped
    And the coverage config creation result has the id of the new resource
    When I delete the coverage flow execution using <adapter_type> adapter
    Then the <adapter_type> authentication execution deletion should succeed
    When I delete the copied coverage authentication flow using <adapter_type> adapter
    Then the <adapter_type> copied authentication flow deletion should succeed
    When I delete the coverage authentication flow using <adapter_type> adapter
    Then the <adapter_type> authentication flow deletion should succeed

    Examples:
      | adapter_type | realm_name             | realm_display_name | client_name       | via    |
      | sync         | test-realm             | Test Realm         | test-client       | direct |
      | async        | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @clientscopes
  Scenario Outline: Client scope CRUD mappers and assignments
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I create a coverage client scope using <adapter_type> adapter
    Then client scope creation with the <adapter_type> adapter should succeed
    When I list all client scopes using <adapter_type> adapter
    Then the <adapter_type> client scopes list should succeed
    When I get the coverage client scope by id using <adapter_type> adapter
    Then getting the coverage client scope by id with the <adapter_type> adapter should succeed
    When I get the coverage client scope by name using <adapter_type> adapter
    Then getting the coverage client scope by name with the <adapter_type> adapter should succeed
    When I update the coverage client scope description using <adapter_type> adapter
    Then updating the coverage client scope with the <adapter_type> adapter should succeed
    When I add a mapper to the coverage client scope for client "<client_name>" using <adapter_type> adapter
    Then adding a mapper to the coverage client scope with the <adapter_type> adapter should succeed
    And the coverage scope mapper creation result has the id of the new resource
    When I list mappers on the coverage client scope using <adapter_type> adapter
    Then listing client scope mappers with the <adapter_type> adapter should succeed
    When I update the coverage client scope mapper using <adapter_type> adapter
    Then updating the coverage client scope mapper with the <adapter_type> adapter should succeed
    When I delete the coverage client scope mapper using <adapter_type> adapter
    Then deleting the coverage client scope mapper with the <adapter_type> adapter should succeed
    When I add a mapper to client "<client_name>" using <adapter_type> adapter
    Then adding a client mapper with the <adapter_type> adapter should succeed
    And the coverage client mapper creation result has the id of the new resource
    When I list mappers on client "<client_name>" using <adapter_type> adapter
    Then listing client mappers with the <adapter_type> adapter should succeed
    When I update the coverage client mapper using <adapter_type> adapter
    Then updating the coverage client mapper with the <adapter_type> adapter should succeed
    When I remove the coverage client mapper using <adapter_type> adapter
    Then removing the coverage client mapper with the <adapter_type> adapter should succeed
    When I list default client scopes for client "<client_name>" using <adapter_type> adapter
    Then listing default client scopes with the <adapter_type> adapter should succeed
    When I add the coverage scope as default for client "<client_name>" using <adapter_type> adapter
    Then adding default client scope with the <adapter_type> adapter should succeed
    When I remove the coverage scope from default scopes for client "<client_name>" using <adapter_type> adapter
    Then removing default client scope with the <adapter_type> adapter should succeed
    When I list optional client scopes for client "<client_name>" using <adapter_type> adapter
    Then listing optional client scopes with the <adapter_type> adapter should succeed
    When I add the coverage scope as optional for client "<client_name>" using <adapter_type> adapter
    Then adding optional client scope with the <adapter_type> adapter should succeed
    When I remove the coverage scope from optional scopes for client "<client_name>" using <adapter_type> adapter
    Then removing optional client scope with the <adapter_type> adapter should succeed
    When I list realm default client scopes using <adapter_type> adapter
    Then listing realm default client scopes with the <adapter_type> adapter should succeed
    When I add the coverage scope to realm default scopes using <adapter_type> adapter
    Then adding realm default client scope with the <adapter_type> adapter should succeed
    When I remove the coverage scope from realm default scopes using <adapter_type> adapter
    Then removing realm default client scope with the <adapter_type> adapter should succeed
    When I list realm optional client scopes using <adapter_type> adapter
    Then listing realm optional client scopes with the <adapter_type> adapter should succeed
    When I add the coverage scope to realm optional scopes using <adapter_type> adapter
    Then adding realm optional client scope with the <adapter_type> adapter should succeed
    When I remove the coverage scope from realm optional scopes using <adapter_type> adapter
    Then removing realm optional client scope with the <adapter_type> adapter should succeed
    When I delete the coverage client scope using <adapter_type> adapter
    Then deleting the coverage client scope with the <adapter_type> adapter should succeed

    Examples:
      | adapter_type | realm_name             | realm_display_name | client_name       | via    |
      | sync         | test-realm             | Test Realm         | test-client       | direct |
      | async        | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @authz
  Scenario Outline: Authorization settings retrieval
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I enable authorization services for client "<client_name>" using <adapter_type> adapter
    When I get authorization settings for client "<client_name>" using <adapter_type> adapter
    Then the <adapter_type> authorization settings request should succeed

    Examples:
      | adapter_type | realm_name             | realm_display_name | client_name       | via    |
      | sync         | test-realm             | Test Realm         | test-client       | direct |
      | async        | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @authz
  Scenario Outline: Authorization resources scopes policies and permissions
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I enable authorization services for client "<client_name>" using <adapter_type> adapter
    When I create the authorization scope "read" for client "<client_name>" using <adapter_type> adapter
    And I create the authorization resource "report" with scope "read" for client "<client_name>" using <adapter_type> adapter
    And I create the role policy "readers" for realm role "offline_access" on client "<client_name>" using <adapter_type> adapter
    And I create the client policy "self" for client "<client_name>" using <adapter_type> adapter
    And I create the scope permission "read-report" on resource "report" scope "read" policy "readers" for client "<client_name>" using <adapter_type> adapter
    Then the authorization objects of client "<client_name>" are listed as scope "read", resource "report", policies "readers,self" and permission "read-report" using <adapter_type> adapter
    When I set the description of scope permission "read-report" to "updated" for client "<client_name>" using <adapter_type> adapter
    Then the scope permission "read-report" of client "<client_name>" has description "updated" and its policies and scopes are readable using <adapter_type> adapter
    When I delete the authorization policy "self" and resource "report" of client "<client_name>" using <adapter_type> adapter
    Then the policy "self" and resource "report" of client "<client_name>" no longer exist using <adapter_type> adapter

    Examples:
      | adapter_type | realm_name             | realm_display_name | client_name       | via    |
      | sync         | test-realm             | Test Realm         | test-client       | direct |
      | async        | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @uma
  Scenario Outline: UMA resource sets policies and permission tickets
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I enable authorization services for client "<client_name>" using <adapter_type> adapter
    When I create the UMA resource set "docs" with scope "view" using <adapter_type> adapter
    Then the UMA resource set "docs" is typed, owned by the client and listed using <adapter_type> adapter
    When I create the UMA policy "viewers" for realm role "offline_access" on resource set "docs" using <adapter_type> adapter
    And I set the description of UMA policy "viewers" on resource set "docs" to "updated" using <adapter_type> adapter
    Then querying UMA policies of resource set "docs" returns "viewers" with description "updated" using <adapter_type> adapter
    And a UMA permission ticket for resource "docs" scope "view" is issued using <adapter_type> adapter
    When I delete the UMA policy "viewers" and resource set "docs" using <adapter_type> adapter
    Then the UMA resource set "docs" no longer exists using <adapter_type> adapter

    Examples:
      | adapter_type | realm_name             | realm_display_name | client_name       | via    |
      | sync         | test-realm             | Test Realm         | test-client       | direct |
      | async        | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @realms
  Scenario Outline: Keycloak rejects unknown fields in <kind> payloads
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "test-realm" with display name "Test Realm" using <adapter_type> adapter
    When I send a <kind> payload with the unknown field "typoField" to Keycloak using <adapter_type> adapter
    Then Keycloak rejects the payload as invalid and names the field "typoField"

    Examples:
      | adapter_type | kind  | via    |
      | sync         | group | direct |
      | sync         | user  | direct |
      | sync         | realm | direct |
      | async        | group | direct |
      | sync         | group | envoy  |
      | sync         | user  | envoy  |
      | sync         | realm | envoy  |
      | async        | group | envoy  |

  @users
  Scenario Outline: User counts, credentials, groups, federated identities, sessions and profile
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    Then the users are counted and filtered, and the user "<username>" has credentials, no consents and no unmanaged attributes using <adapter_type> adapter
    When I add user "<username>" to a new group "<group>" using <adapter_type> adapter
    Then the user "<username>" lists and counts the group "<group>" using <adapter_type> adapter
    When I link user "<username>" to the identity provider "<idp_alias>" as "<external>" using <adapter_type> adapter
    Then the user "<username>" lists the link to "<idp_alias>" and removes it using <adapter_type> adapter
    And the user "<username>" with password "<password>" has a session, can be impersonated and the user profile is readable using <adapter_type> adapter
    And the email actions for user "<username>" reach Keycloak and report the missing SMTP setup using <adapter_type> adapter

    Examples:
      | adapter_type | username      | password | group      | idp_alias | external | realm_name       | realm_display_name | client_name       | via    |
      | sync         | usrextra      | pass123  | extra-grp  | usr-idp   | usrext   | test-realm       | Test Realm         | test-client       | direct |
      | async        | asyncusrextra | async123 | aextra-grp | ausr-idp  | ausrext  | test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | usrextra      | pass123  | extra-grp  | usr-idp   | usrext   | test-realm-envoy | Test Realm         | test-client       | envoy  |
      | async        | asyncusrextra | async123 | aextra-grp | ausr-idp  | ausrext  | test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @clients
  Scenario Outline: Clients by UUID with secrets, evaluation, sessions and nodes
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I list, read and update the client "<client_name>" by its UUID using <adapter_type> adapter
    Then the client "<client_name>" is found by client id and carries the new description using <adapter_type> adapter
    And the client "<client_name>" has a secret that can be regenerated and rotated using <adapter_type> adapter
    And the client "<client_name>" evaluates example tokens, mappers, scope roles and installation config using <adapter_type> adapter
    And the client "<client_name>" counts sessions, registers a node and reports management permissions using <adapter_type> adapter
    When I delete the client "<client_name>" by its UUID using <adapter_type> adapter
    Then the deleted client is no longer found using <adapter_type> adapter

    Examples:
      | adapter_type | realm_name       | realm_display_name | client_name        | via    |
      | sync         | test-realm       | Test Realm         | extra-client       | direct |
      | async        | test-realm       | Async Test Realm   | async-extra-client | direct |
      | sync         | test-realm-envoy | Test Realm         | extra-client       | envoy  |
      | async        | test-realm-envoy | Async Test Realm   | async-extra-client | envoy  |

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
