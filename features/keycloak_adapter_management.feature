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
