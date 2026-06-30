# features/keycloak_auth.feature
@needs-keycloak
Feature: Keycloak Authentication Testing
  As a developer
  I want to test Keycloak authentication operations
  So that I can ensure secure authentication and management operations

  Scenario Outline: Basic realm and client operations
    Given a configured <adapter_type> Keycloak adapter
    When I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    Then the <adapter_type> realm creation should succeed
    And the realm "<realm_name>" should exist
    And the realm should have display name "<realm_display_name>"

    Examples:
      | adapter_type | realm_name      | realm_display_name | client_name      |
      | sync         | test-realm      | Test Realm         | test-client      |
      | async        | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Realm update
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And the <adapter_type> realm creation should succeed
    When I update the realm "<realm_name>" display name to "<new_display_name>" using <adapter_type> adapter
    Then the realm "<realm_name>" should have display name "<new_display_name>"

    Examples:
      | adapter_type | realm_name        | realm_display_name | new_display_name   |
      | sync         | update-realm      | Original           | Updated Display    |
      | async        | async-update-realm| Async Original     | Async Updated Name |

  Scenario Outline: User authentication flow
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I request a token with username "<username>" and password "<password>" using <adapter_type> adapter
    Then the <adapter_type> user creation should succeed
    And the <adapter_type> user token request should succeed
    And the <adapter_type> token response should contain "access_token" and "refresh_token"

    Examples:
      | adapter_type | username | password | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Token operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I refresh the token using <adapter_type> adapter
    Then the <adapter_type> token refresh should succeed
    And the <adapter_type> token response should contain "access_token" and "refresh_token"

    Examples:
      | adapter_type | username | password | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: User information operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I request user info with the token using <adapter_type> adapter
    Then the <adapter_type> user info request should succeed
    And the <adapter_type> user info should contain "sub" and "preferred_username"

    Examples:
      | adapter_type | username | password | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Token validation
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I validate the token using <adapter_type> adapter
    Then the <adapter_type> token validation should succeed

    Examples:
      | adapter_type | username | password | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: User retrieval operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I get user by username "<username>" using <adapter_type> adapter
    Then the <adapter_type> user retrieval should succeed
    And the user should have username "<username>"

    Examples:
      | adapter_type | username | password | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Email-based user retrieval
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user including username "<username>" email "<email>" and password "<password>" using <adapter_type> adapter
    When I get user by email "<email>" using <adapter_type> adapter
    Then the <adapter_type> user retrieval should succeed
    And the user should have email "<email>"

    Examples:
      | adapter_type | username | email              | password | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | test@example.com   | pass123  | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async@example.com  | async123 | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Realm role management
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I create a realm role named "<role_name>" with description "<role_description>" using <adapter_type> adapter
    And I assign realm role "<role_name>" to user "<username>" using <adapter_type> adapter
    Then the <adapter_type> realm role creation should succeed
    And the <adapter_type> realm role assignment should succeed
    And the user "<username>" should have realm role "<role_name>"

    Examples:
      | adapter_type | username | password | role_name    | role_description | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | test-role    | Test Role        | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | async-test-role| Async Test Role | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Client role management
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I create a client role named "<client_role_name>" for client "<client_name>" with description "<client_role_description>" using <adapter_type> adapter
    And I assign client role "<client_role_name>" of client "<client_name>" to user "<username>" using <adapter_type> adapter
    Then the <adapter_type> client role creation should succeed
    And the <adapter_type> client role assignment should succeed
    And the user "<username>" should have client role "<client_role_name>" for client "<client_name>"

    Examples:
      | adapter_type | username | password | client_role_name | client_role_description | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | client-role      | Client Role             | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | async-client-role| Async Client Role       | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: User search operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<search_user1>" and password "<password>" using <adapter_type> adapter
    And I create a user with username "<search_user2>" and password "<password>" using <adapter_type> adapter
    When I search for users with query "<search_query>" using <adapter_type> adapter
    Then the <adapter_type> user search should succeed
    And the search results should contain 2 users

    Examples:
      | adapter_type | search_user1   | search_user2   | search_query | password | realm_name      | realm_display_name | client_name      |
      | sync         | searchuser1    | searchuser2    | searchuser   | pass123  | test-realm      | Test Realm         | test-client      |
      | async        | asynctestuser4 | asynctestuser5 | asynctestuser| async123 | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: User update operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I update user "<username>" with first name "<first_name>" and last name "<last_name>" using <adapter_type> adapter
    Then the <adapter_type> user update should succeed
    And the user "<username>" should have first name "<first_name>" and last name "<last_name>"

    Examples:
      | adapter_type | username | password | first_name | last_name | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | John       | Doe       | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | Async      | User      | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Password reset operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I reset password for user "<username>" to "<new_password>" using <adapter_type> adapter
    Then the <adapter_type> password reset should succeed
    And I should be able to get token with username "<username>" and password "<new_password>" using <adapter_type> adapter

    Examples:
      | adapter_type | username | password | new_password | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | newpass456   | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | newasync456  | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Session management
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I clear sessions for user "<username>" using <adapter_type> adapter
    Then the <adapter_type> session clearing should succeed

    Examples:
      | adapter_type | username | password | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Logout operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I logout the user using <adapter_type> adapter
    Then the <adapter_type> logout operation should succeed

    Examples:
      | adapter_type | username | password | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Client credentials token
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I request client credentials token using <adapter_type> adapter
    Then the <adapter_type> client credentials token request should succeed
    And the <adapter_type> token response should contain "access_token"

    Examples:
      | adapter_type | realm_name      | realm_display_name | client_name      |
      | sync         | test-realm      | Test Realm         | test-client      |
      | async        | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Token introspection
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I introspect the token using <adapter_type> adapter
    Then the <adapter_type> token introspection should succeed
    And the introspection result should indicate active token

    Examples:
      | adapter_type | username | password | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Token info retrieval
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I get token info using <adapter_type> adapter
    Then the <adapter_type> token info request should succeed
    And the token info should contain user claims

    Examples:
      | adapter_type | username | password | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Role permission checking
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I create a realm role named "<role_name>" with description "<role_description>" using <adapter_type> adapter
    And I assign realm role "<role_name>" to user "<username>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I check if user has role "<role_name>" using <adapter_type> adapter
    Then the <adapter_type> role check should succeed
    And the user should have the role "<role_name>"

    Examples:
      | adapter_type | username | password | role_name    | role_description | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | test-role    | Test Role        | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | async-test-role| Async Test Role | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: Role removal operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I create a realm role named "<role_name>" with description "<role_description>" using <adapter_type> adapter
    And I assign realm role "<role_name>" to user "<username>" using <adapter_type> adapter
    When I remove realm role "<role_name>" from user "<username>" using <adapter_type> adapter
    Then the <adapter_type> role removal should succeed
    And the user "<username>" should not have realm role "<role_name>"

    Examples:
      | adapter_type | username | password | role_name    | role_description | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | test-role    | Test Role        | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser| async123 | async-test-role| Async Test Role | async-test-realm| Async Test Realm   | async-test-client|

  Scenario Outline: User deletion operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I delete user "<username>" using <adapter_type> adapter
    Then the <adapter_type> user deletion should succeed
    And the user "<username>" should not exist
    Examples:
      | adapter_type | username | password | realm_name      | realm_display_name | client_name      |
      | sync         | testuser | pass123  | test-realm      | Test Realm         | test-client      |
      | async        | asyncuser6| async123| async-test-realm| Async Test Realm   | async-test-client|

  @organizations
  Scenario Outline: Organization create get update and delete
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I enable organization of realm named "<realm_name>"
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I create an organization with name "<org_name>" and alias "<org_alias>" using <adapter_type> adapter
    Then the <adapter_type> organization creation should succeed
    And the organization "<org_name>" should exist
    And the organization should have alias "<org_alias>"
    When I get all organizations using <adapter_type> adapter
    Then the organizations list should contain organization "<org_name>"
    When I get organizations with search "<org_name>" using <adapter_type> adapter
    Then the organizations list should contain organization "<org_name>"
    When I update the organization name to "<org_display_name>" using <adapter_type> adapter
    Then the <adapter_type> organization update should succeed
    And the organization should have name "<org_display_name>"
    When I delete the organization using <adapter_type> adapter
    Then the <adapter_type> organization deletion should succeed

    Examples:
      | adapter_type | org_name      | org_alias     | org_display_name | realm_name      | realm_display_name | client_name      |
      | sync         | test-org      | test-org-alias| Test Org Display | test-realm  | Test Realm         | test-client      |
      | async        | async-test-org| async-org-alias| Async Org Display| test-realm  | Async Test Realm   | async-test-client|

  @organizations
  Scenario Outline: Organization members add and remove
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I enable organization of realm named "<realm_name>"
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I create an organization with name "<org_name>" and alias "<org_alias>" using <adapter_type> adapter
    When I add user "<username>" to the organization using <adapter_type> adapter
    Then the <adapter_type> organization add member should succeed
    When I get organization members using <adapter_type> adapter
    Then the organization should have 1 member
    When I get organizations for user "<username>" using <adapter_type> adapter
    Then the user organizations list should contain organization "<org_name>"
    When I remove user "<username>" from the organization using <adapter_type> adapter
    Then the <adapter_type> organization remove member should succeed
    When I get organization members count using <adapter_type> adapter
    Then the organization members count should be 0
    When I get organizations for user "<username>" using <adapter_type> adapter
    Then the user organizations list should not contain organization "<org_name>"

    Examples:
      | adapter_type | username | password | org_name | org_alias | realm_name     | realm_display_name | client_name      |
      | sync         | orguser  | pass123  | test-org1 | test-alias1| test-realm | Test Realm         | test-client      |
      | async        | asyncorguser| async123| async-org1| async-alias1| test-realm | Async Test Realm   | async-test-client|

  @groups
  Scenario Outline: Group CRUD hierarchy membership and roles
    Given a configured <adapter_type> Keycloak adapter
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
      | adapter_type | username | password | group_name | realm_name      | realm_display_name | client_name      |
      | sync         | groupuser| pass123  | test-group | test-realm      | Test Realm         | test-client      |
      | async        | asyncgrp | async123 | async-group| async-test-realm| Async Test Realm   | async-test-client|

  @authflows
  Scenario Outline: Create and manage authentication flows
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I create a coverage authentication flow using <adapter_type> adapter
    Then the <adapter_type> authentication flow creation should succeed
    When I list all authentication flows using <adapter_type> adapter
    Then the authentication flows list should include the coverage flow
    When I get the coverage authentication flow by id using <adapter_type> adapter
    Then the <adapter_type> authentication flow get by id should succeed
    When I update the coverage authentication flow description using <adapter_type> adapter
    Then the <adapter_type> authentication flow update should succeed
    When I copy the coverage authentication flow using <adapter_type> adapter
    Then the <adapter_type> authentication flow copy should succeed
    When I add a subflow to the coverage authentication flow using <adapter_type> adapter
    Then the <adapter_type> authentication subflow creation should succeed
    When I add a username-password execution to the coverage flow using <adapter_type> adapter
    Then the <adapter_type> authentication execution creation should succeed
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
    When I delete the coverage flow execution using <adapter_type> adapter
    Then the <adapter_type> authentication execution deletion should succeed
    When I delete the copied coverage authentication flow using <adapter_type> adapter
    Then the <adapter_type> copied authentication flow deletion should succeed
    When I delete the coverage authentication flow using <adapter_type> adapter
    Then the <adapter_type> authentication flow deletion should succeed

    Examples:
      | adapter_type | realm_name      | realm_display_name | client_name      |
      | sync         | test-realm      | Test Realm         | test-client      |
      | async        | async-test-realm| Async Test Realm   | async-test-client|

  @clientscopes
  Scenario Outline: Client scope CRUD mappers and assignments
    Given a configured <adapter_type> Keycloak adapter
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
    When I list mappers on the coverage client scope using <adapter_type> adapter
    Then listing client scope mappers with the <adapter_type> adapter should succeed
    When I update the coverage client scope mapper using <adapter_type> adapter
    Then updating the coverage client scope mapper with the <adapter_type> adapter should succeed
    When I delete the coverage client scope mapper using <adapter_type> adapter
    Then deleting the coverage client scope mapper with the <adapter_type> adapter should succeed
    When I add a mapper to client "<client_name>" using <adapter_type> adapter
    Then adding a client mapper with the <adapter_type> adapter should succeed
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
      | adapter_type | realm_name      | realm_display_name | client_name      |
      | sync         | test-realm      | Test Realm         | test-client      |
      | async        | async-test-realm| Async Test Realm   | async-test-client|

  @authz
  Scenario Outline: Authorization settings retrieval
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I enable authorization services for client "<client_name>" using <adapter_type> adapter
    When I get authorization settings for client "<client_name>" using <adapter_type> adapter
    Then the <adapter_type> authorization settings request should succeed

    Examples:
      | adapter_type | realm_name      | realm_display_name | client_name      |
      | sync         | test-realm      | Test Realm         | test-client      |
      | async        | async-test-realm| Async Test Realm   | async-test-client|

  @components
  Scenario Outline: Component listing
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I get all components using <adapter_type> adapter
    Then the <adapter_type> components request should succeed

    Examples:
      | adapter_type | realm_name      | realm_display_name | client_name      |
      | sync         | test-realm      | Test Realm         | test-client      |
      | async        | async-test-realm| Async Test Realm   | async-test-client|
