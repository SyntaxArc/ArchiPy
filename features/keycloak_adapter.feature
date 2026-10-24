# features/keycloak_auth.feature
@needs-keycloak @needs-otel-collector @needs-apm-server @needs-apm-collector
Feature: Keycloak Authentication Testing
  As a developer
  I want to test Keycloak authentication operations
  So that I can ensure secure authentication and management operations

  @realms
  Scenario Outline: Basic realm and client operations
    Given a configured <adapter_type> Keycloak adapter
    When I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    Then the <adapter_type> realm creation should succeed
    And the realm "<realm_name>" should exist
    And the realm should have display name "<realm_display_name>"

    Examples:
      | adapter_type | realm_name       | realm_display_name | client_name       |
      | sync         | test-realm       | Test Realm         | test-client       |
      | async        | async-test-realm | Async Test Realm   | async-test-client |

  @realms
  Scenario Outline: Realm update
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And the <adapter_type> realm creation should succeed
    When I update the realm "<realm_name>" display name to "<new_display_name>" using <adapter_type> adapter
    Then the realm "<realm_name>" should have display name "<new_display_name>"

    Examples:
      | adapter_type | realm_name         | realm_display_name | new_display_name   |
      | sync         | update-realm       | Original           | Updated Display    |
      | async        | async-update-realm | Async Original     | Async Updated Name |

  @tokens
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
      | adapter_type | username  | password | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | async-test-realm | Async Test Realm   | async-test-client |

  @tokens
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
      | adapter_type | username  | password | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | async-test-realm | Async Test Realm   | async-test-client |

  @users
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
      | adapter_type | username  | password | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | async-test-realm | Async Test Realm   | async-test-client |

  @tokens
  Scenario Outline: Token validation
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I validate the token using <adapter_type> adapter
    Then the <adapter_type> token validation should succeed

    Examples:
      | adapter_type | username  | password | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | async-test-realm | Async Test Realm   | async-test-client |

  @users
  Scenario Outline: User retrieval operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I get user by username "<username>" using <adapter_type> adapter
    Then the <adapter_type> user retrieval should succeed
    And the user should have username "<username>"

    Examples:
      | adapter_type | username  | password | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | async-test-realm | Async Test Realm   | async-test-client |

  @users
  Scenario Outline: Email-based user retrieval
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user including username "<username>" email "<email>" and password "<password>" using <adapter_type> adapter
    When I get user by email "<email>" using <adapter_type> adapter
    Then the <adapter_type> user retrieval should succeed
    And the user should have email "<email>"

    Examples:
      | adapter_type | username  | email             | password | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | test@example.com  | pass123  | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async@example.com | async123 | async-test-realm | Async Test Realm   | async-test-client |

  @roles
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
      | adapter_type | username  | password | role_name       | role_description | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | test-role       | Test Role        | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | async-test-role | Async Test Role  | async-test-realm | Async Test Realm   | async-test-client |

  @roles
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
      | adapter_type | username  | password | client_role_name  | client_role_description | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | client-role       | Client Role             | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | async-client-role | Async Client Role       | async-test-realm | Async Test Realm   | async-test-client |

  @users
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
      | adapter_type | search_user1   | search_user2   | search_query  | password | realm_name       | realm_display_name | client_name       |
      | sync         | searchuser1    | searchuser2    | searchuser    | pass123  | test-realm       | Test Realm         | test-client       |
      | async        | asynctestuser4 | asynctestuser5 | asynctestuser | async123 | async-test-realm | Async Test Realm   | async-test-client |

  @users
  Scenario Outline: User update operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I update user "<username>" with first name "<first_name>" and last name "<last_name>" using <adapter_type> adapter
    Then the <adapter_type> user update should succeed
    And the user "<username>" should have first name "<first_name>" and last name "<last_name>"

    Examples:
      | adapter_type | username  | password | first_name | last_name | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | John       | Doe       | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | Async      | User      | async-test-realm | Async Test Realm   | async-test-client |

  @users
  Scenario Outline: Password reset operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I reset password for user "<username>" to "<new_password>" using <adapter_type> adapter
    Then the <adapter_type> password reset should succeed
    And I should be able to get token with username "<username>" and password "<new_password>" using <adapter_type> adapter

    Examples:
      | adapter_type | username  | password | new_password | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | newpass456   | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | newasync456  | async-test-realm | Async Test Realm   | async-test-client |

  @users
  Scenario Outline: Session management
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I clear sessions for user "<username>" using <adapter_type> adapter
    Then the <adapter_type> session clearing should succeed

    Examples:
      | adapter_type | username  | password | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | async-test-realm | Async Test Realm   | async-test-client |

  @tokens
  Scenario Outline: Logout operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I logout the user using <adapter_type> adapter
    Then the <adapter_type> logout operation should succeed

    Examples:
      | adapter_type | username  | password | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | async-test-realm | Async Test Realm   | async-test-client |

  @tokens
  Scenario Outline: Client credentials token
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I request client credentials token using <adapter_type> adapter
    Then the <adapter_type> client credentials token request should succeed
    And the <adapter_type> token response should contain "access_token"

    Examples:
      | adapter_type | realm_name       | realm_display_name | client_name       |
      | sync         | test-realm       | Test Realm         | test-client       |
      | async        | async-test-realm | Async Test Realm   | async-test-client |

  @tokens
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
      | adapter_type | username  | password | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | async-test-realm | Async Test Realm   | async-test-client |

  @tokens
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
      | adapter_type | username  | password | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | async-test-realm | Async Test Realm   | async-test-client |

  @roles
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
      | adapter_type | username  | password | role_name       | role_description | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | test-role       | Test Role        | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | async-test-role | Async Test Role  | async-test-realm | Async Test Realm   | async-test-client |

  @roles
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
      | adapter_type | username  | password | role_name       | role_description | realm_name       | realm_display_name | client_name       |
      | sync         | testuser  | pass123  | test-role       | Test Role        | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser | async123 | async-test-role | Async Test Role  | async-test-realm | Async Test Realm   | async-test-client |

  @users
  Scenario Outline: User deletion operations
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I delete user "<username>" using <adapter_type> adapter
    Then the <adapter_type> user deletion should succeed
    And the user "<username>" should not exist

    Examples:
      | adapter_type | username   | password | realm_name       | realm_display_name | client_name       |
      | sync         | testuser   | pass123  | test-realm       | Test Realm         | test-client       |
      | async        | asyncuser6 | async123 | async-test-realm | Async Test Realm   | async-test-client |

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
      | adapter_type | org_name       | org_alias       | org_display_name  | realm_name | realm_display_name | client_name       |
      | sync         | test-org       | test-org-alias  | Test Org Display  | test-realm | Test Realm         | test-client       |
      | async        | async-test-org | async-org-alias | Async Org Display | test-realm | Async Test Realm   | async-test-client |

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
      | adapter_type | username     | password | org_name   | org_alias    | realm_name | realm_display_name | client_name       |
      | sync         | orguser      | pass123  | test-org1  | test-alias1  | test-realm | Test Realm         | test-client       |
      | async        | asyncorguser | async123 | async-org1 | async-alias1 | test-realm | Async Test Realm   | async-test-client |

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
      | adapter_type | username  | password | group_name  | realm_name       | realm_display_name | client_name       |
      | sync         | groupuser | pass123  | test-group  | test-realm       | Test Realm         | test-client       |
      | async        | asyncgrp  | async123 | async-group | async-test-realm | Async Test Realm   | async-test-client |

  @authflows
  Scenario Outline: Create and manage authentication flows
    Given a configured <adapter_type> Keycloak adapter
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
      | adapter_type | realm_name       | realm_display_name | client_name       |
      | sync         | test-realm       | Test Realm         | test-client       |
      | async        | async-test-realm | Async Test Realm   | async-test-client |

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
      | adapter_type | realm_name       | realm_display_name | client_name       |
      | sync         | test-realm       | Test Realm         | test-client       |
      | async        | async-test-realm | Async Test Realm   | async-test-client |

  @authz
  Scenario Outline: Authorization settings retrieval
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I enable authorization services for client "<client_name>" using <adapter_type> adapter
    When I get authorization settings for client "<client_name>" using <adapter_type> adapter
    Then the <adapter_type> authorization settings request should succeed

    Examples:
      | adapter_type | realm_name       | realm_display_name | client_name       |
      | sync         | test-realm       | Test Realm         | test-client       |
      | async        | async-test-realm | Async Test Realm   | async-test-client |

  @authz
  Scenario Outline: Authorization resources scopes policies and permissions
    Given a configured <adapter_type> Keycloak adapter
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
      | adapter_type | realm_name       | realm_display_name | client_name       |
      | sync         | test-realm       | Test Realm         | test-client       |
      | async        | async-test-realm | Async Test Realm   | async-test-client |

  @uma
  Scenario Outline: UMA resource sets policies and permission tickets
    Given a configured <adapter_type> Keycloak adapter
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
      | adapter_type | realm_name       | realm_display_name | client_name       |
      | sync         | test-realm       | Test Realm         | test-client       |
      | async        | async-test-realm | Async Test Realm   | async-test-client |

  @realms
  Scenario Outline: Keycloak rejects unknown fields in <kind> payloads
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using <adapter_type> adapter
    When I send a <kind> payload with the unknown field "typoField" to Keycloak using <adapter_type> adapter
    Then Keycloak rejects the payload as invalid and names the field "typoField"

    Examples:
      | adapter_type | kind  |
      | sync         | group |
      | sync         | user  |
      | sync         | realm |
      | async        | group |

  @components
  Scenario Outline: Component listing
    Given a configured <adapter_type> Keycloak adapter
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I get all components using <adapter_type> adapter
    Then the <adapter_type> components request should succeed

    Examples:
      | adapter_type | realm_name       | realm_display_name | client_name       |
      | sync         | test-realm       | Test Realm         | test-client       |
      | async        | async-test-realm | Async Test Realm   | async-test-client |

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

  # --- Keycloak auth dependencies and decorators ---
  # Real tokens issued by the Keycloak container drive keycloak.auth fastapi_auth, grpc_auth and
  # AuthContextManager. gRPC uses a ServicerContext fake only to record aborts.
  Scenario: Auth FastAPI dependency populates request state for a valid token
    Given a configured sync Keycloak adapter
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

  @auth-guards
  Scenario Outline: Reading <field> from the request state warns and points to the auth context
    Given a configured sync Keycloak adapter
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
      | field       | replacement                                         |
      | user_info   | AuthContextManager.get_auth_context().raw_user_info |
      | token_info  | AuthContextManager.get_auth_context().token_info    |
      | actor_chain | AuthContextManager.get_auth_context().actor_chain   |
      | user_roles  | AuthContextManager.get_auth_context().roles         |

  Scenario: Auth FastAPI dependency accepts a client role from resource access
    Given a configured sync Keycloak adapter
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

  Scenario: Auth FastAPI dependency rejects missing credentials
    Given a configured sync Keycloak adapter
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    When the keycloak auth fastapi dependency is called without credentials
    Then the keycloak auth call fails with error code "UNAUTHENTICATED"
    And the keycloak auth context is cleared after the dependency ends

  Scenario: Auth FastAPI dependency rejects a garbage token
    Given a configured sync Keycloak adapter
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    When the keycloak auth fastapi dependency is called with token "not-a-real-jwt"
    Then the keycloak auth call fails with error code "TOKEN_EXPIRED"

  Scenario: Auth FastAPI dependency rejects an expired token
    Given a configured sync Keycloak adapter
    And I create a realm named "auth-expiry-realm" with display name "Auth Expiry Realm" using sync adapter
    And the keycloak auth realm "auth-expiry-realm" has an access token lifespan of 1 seconds
    And I create a client named "auth-expiry-client" in realm "auth-expiry-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authexpiring" and password "pass123" using sync adapter
    And the keycloak auth access token of user "authexpiring" is obtained with password "pass123"
    When the keycloak auth access token lifespan has elapsed
    And the keycloak auth fastapi dependency is called with the access token of user "authexpiring"
    Then the keycloak auth call fails with error code "TOKEN_EXPIRED"

  Scenario: Auth FastAPI dependency rejects a caller without the required role
    Given a configured sync Keycloak adapter
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

  Scenario: Auth FastAPI dependency requires every role when all roles are required
    Given a configured sync Keycloak adapter
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak fastapi auth requires all roles "auth-reader,auth-writer"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "PERMISSION_DENIED"

  Scenario: Auth FastAPI dependency allows a granted UMA permission
    Given a configured sync Keycloak adapter
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

  Scenario: Auth FastAPI dependency denies an ungranted UMA permission
    Given a configured sync Keycloak adapter
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

  Scenario: Auth FastAPI dependency denies a request when every UMA permission is ungranted
    Given a configured sync Keycloak adapter
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

  Scenario: Auth FastAPI dependency allows the owner of a resource
    Given a configured sync Keycloak adapter
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

  Scenario: Auth FastAPI dependency denies a non owner of a resource
    Given a configured sync Keycloak adapter
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

  Scenario: Auth FastAPI dependency lets an admin role bypass resource ownership
    Given a configured sync Keycloak adapter
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

  Scenario: Auth FastAPI dependency rejects a request missing the resource path parameter
    Given a configured sync Keycloak adapter
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    And the keycloak fastapi auth guards resource type "users" by path parameter "user_uuid"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "INVALID_ARGUMENT"

  @auth-guards
  Scenario Outline: Auth gRPC handler runs with the auth context for a valid token
    Given a configured sync Keycloak adapter
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
      | mode  |
      | sync  |
      | async |

  @auth-guards
  Scenario Outline: Auth gRPC handler accepts a raw token without the bearer prefix
    Given a configured sync Keycloak adapter
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "authuser" and password "pass123" using sync adapter
    And I create a realm role named "auth-reader" with description "Reader" using sync adapter
    And I assign realm role "auth-reader" to user "authuser" using sync adapter
    And the keycloak auth access token of user "authuser" is obtained with password "pass123"
    When the keycloak auth <mode> grpc handler is invoked with the raw access token of user "authuser"
    Then the keycloak auth grpc handler ran as user "authuser" with roles including "auth-reader"

    Examples:
      | mode  |
      | sync  |
      | async |

  @auth-guards
  Scenario Outline: Auth gRPC handler allows the owner of a resource
    Given a configured sync Keycloak adapter
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
      | mode  |
      | sync  |
      | async |

  @auth-guards
  Scenario Outline: Auth gRPC handler aborts the servicer context when the token is missing
    Given a configured sync Keycloak adapter
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    When the keycloak auth <mode> grpc handler is invoked without metadata
    Then the keycloak auth servicer context was aborted with status "UNAUTHENTICATED"
    And the keycloak auth grpc handler did not run
    And the keycloak auth context is cleared

    Examples:
      | mode  |
      | sync  |
      | async |

  @auth-guards
  Scenario Outline: Auth gRPC handler aborts the servicer context when the token is invalid
    Given a configured sync Keycloak adapter
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    When the keycloak auth <mode> grpc handler is invoked with bearer token "not-a-real-jwt"
    Then the keycloak auth servicer context was aborted with status "UNAUTHENTICATED"
    And the keycloak auth grpc handler did not run

    Examples:
      | mode  |
      | sync  |
      | async |

  @auth-guards
  Scenario Outline: Auth gRPC handler aborts the servicer context when the role is insufficient
    Given a configured sync Keycloak adapter
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
      | mode  |
      | sync  |
      | async |

  @auth-guards
  Scenario Outline: Auth gRPC handler aborts when the request lacks the resource attribute
    Given a configured sync Keycloak adapter
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
      | mode  |
      | sync  |
      | async |

  @auth-guards
  Scenario Outline: Auth gRPC handler raises the typed error when the context is not a servicer context
    Given a configured sync Keycloak adapter
    And I create a realm named "auth-realm" with display name "Auth Realm" using sync adapter
    And I create a client named "auth-client" in realm "auth-realm" with service accounts and update adapter using sync adapter
    When the keycloak auth <mode> grpc handler is invoked without metadata on a plain context
    Then the keycloak auth call fails with error code "UNAUTHENTICATED"
    And the keycloak auth grpc handler did not run

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario: Auth sync gRPC handler wraps unexpected failures in an internal error
    Given a configured sync Keycloak adapter
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

  Scenario: Auth async gRPC handler aborts with an internal status on unexpected failures
    Given a configured sync Keycloak adapter
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
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And a FastAPI app whose routes are guarded by the keycloak fastapi auth
    When the guarded app is requested at "<path>" with the access token of user "authuser"
    Then the app response reports the caller "authuser" every time it reads the auth context

    Examples:
      | path    |
      | /async  |
      | /sync   |
      | /stream |

  Scenario: A FastAPI background task still sees the caller after the response
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And a FastAPI app whose routes are guarded by the keycloak fastapi auth
    When the guarded app is requested at "/background" with the access token of user "authuser"
    Then the app response reports the caller "authuser" every time it reads the auth context
    And the background task saw the caller "authuser"

  Scenario: The auth context does not leak into a later unguarded request
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And a FastAPI app whose routes are guarded by the keycloak fastapi auth
    When the guarded app is requested at "/async" with the access token of user "authuser"
    And the guarded app is requested at "/open" without credentials
    Then the app response reports no caller

  # --- Keycloak auth gRPC decorators and caching against the real Keycloak container ---
  @auth-guards
  Scenario Outline: Auth gRPC response-stream handler keeps the auth context while streaming
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And the keycloak grpc auth requires any of roles "auth-reader"
    And the keycloak auth grpc handler is a response stream
    When the keycloak auth <mode> grpc handler is invoked with the bearer access token of user "authuser"
    Then the keycloak auth grpc handler ran as user "authuser" with roles including "auth-reader"
    And the keycloak auth grpc handler returned "a,b"
    And the keycloak auth context is cleared

    Examples:
      | mode  |
      | sync  |
      | async |

  @auth-guards
  Scenario Outline: Auth gRPC response-stream handler rejects a missing token
    Given a keycloak auth realm with a client
    And the keycloak auth grpc handler is a response stream
    When the keycloak auth <mode> grpc handler is invoked without metadata on a plain context
    Then the keycloak auth call fails with error code "UNAUTHENTICATED"
    And the keycloak auth grpc handler did not run

    Examples:
      | mode  |
      | sync  |
      | async |

  @auth-guards
  Scenario Outline: Auth gRPC handler abort is not rewritten as an internal error
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And the keycloak grpc auth requires any of roles "auth-reader"
    And the keycloak auth grpc handler aborts the servicer context itself
    When the keycloak auth <mode> grpc handler is invoked with the bearer access token of user "authuser"
    Then the keycloak auth servicer context was aborted exactly once with status "RESOURCE_EXHAUSTED"
    And the keycloak auth context is cleared

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario: Auth sync gRPC handler hides the cause of unexpected failures
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And the keycloak grpc auth requires any of roles "auth-reader"
    And the keycloak auth grpc handler crashes with a runtime failure
    When the keycloak auth sync grpc handler is invoked with the bearer access token of user "authuser" on a plain context
    Then the keycloak auth call fails with error code "INTERNAL_ERROR"
    And the keycloak auth error should not expose "boom"

  Scenario: Auth lookups are not cached unless a TTL is configured
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    And the keycloak auth sessions of user "authuser" are cleared
    And the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "INVALID_CREDENTIALS"

  Scenario: Auth userinfo lookups are cached for the configured TTL
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And the keycloak auth adapter caches remote lookups for 60 seconds
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    And the keycloak auth sessions of user "authuser" are cleared
    And the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth dependency returns the user info of user "authuser"

  Scenario: Auth cached lookups are looked up again after the TTL
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And the keycloak auth adapter caches remote lookups for 60 seconds
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    And the keycloak auth sessions of user "authuser" are cleared
    And the keycloak auth cached lookups expire
    And the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "INVALID_CREDENTIALS"

  Scenario: Auth cached lookups are kept apart per token
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And I create a user with username "authother" and password "pass123" using sync adapter
    And I assign realm role "auth-reader" to user "authother" using sync adapter
    And the keycloak auth access token of user "authother" is obtained with password "pass123"
    And the keycloak auth adapter caches remote lookups for 60 seconds
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    And the keycloak auth fastapi dependency is called with the access token of user "authother"
    Then the keycloak auth dependency returns the user info of user "authother"

  Scenario: Auth permission lookups are cached for the configured TTL
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And the keycloak auth client "auth-client" guards resource "auth-doc-cached" with scopes "read,write" and grants scope "read" to realm role "auth-reader"
    And the keycloak auth client "auth-client" guards resource "auth-doc-cached" with scopes "read,write" and grants scope "write" to realm role "auth-reader"
    And the keycloak auth adapter caches remote lookups for 60 seconds
    And the keycloak fastapi auth requires permissions "auth-doc-cached#read,auth-doc-cached#write"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    And the keycloak auth permission granting scope "read" on resource "auth-doc-cached" of client "auth-client" is deleted
    And the keycloak adapter's own permission cache is cleared
    And the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth dependency returns the user info of user "authuser"

  Scenario: Auth permission lookups are not cached unless a TTL is configured
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And the keycloak auth client "auth-client" guards resource "auth-doc-uncached" with scopes "read,write" and grants scope "read" to realm role "auth-reader"
    And the keycloak auth client "auth-client" guards resource "auth-doc-uncached" with scopes "read,write" and grants scope "write" to realm role "auth-reader"
    And the keycloak fastapi auth requires permissions "auth-doc-uncached#read,auth-doc-uncached#write"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    And the keycloak auth permission granting scope "read" on resource "auth-doc-uncached" of client "auth-client" is deleted
    And the keycloak adapter's own permission cache is cleared
    And the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "PERMISSION_DENIED"

  @auth-guards
  Scenario Outline: Auth gRPC handler reads the bearer scheme case-insensitively
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And the keycloak grpc auth requires any of roles "auth-reader"
    When the keycloak auth <mode> grpc handler is invoked with the access token of user "authuser" under authorization scheme "BEARER"
    Then the keycloak auth grpc handler ran as user "authuser" with roles including "auth-reader"

    Examples:
      | mode  |
      | sync  |
      | async |

  @auth-guards
  Scenario Outline: Auth gRPC handler rejects an empty bearer credential
    Given a keycloak auth realm with a client
    And the keycloak grpc auth requires any of roles "auth-reader"
    When the keycloak auth <mode> grpc handler is invoked with metadata key "authorization" value "Bearer "
    Then the keycloak auth servicer context was aborted with status "UNAUTHENTICATED"
    And the keycloak auth grpc handler did not run

    Examples:
      | mode  |
      | sync  |
      | async |

  @auth-guards
  Scenario Outline: Auth gRPC handler rejects conflicting authorization headers
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And the keycloak grpc auth requires any of roles "auth-reader"
    When the keycloak auth <mode> grpc handler is invoked with a conflicting bearer token "other-token" next to the access token of user "authuser"
    Then the keycloak auth servicer context was aborted with status "UNAUTHENTICATED"
    And the keycloak auth grpc handler did not run

    Examples:
      | mode  |
      | sync  |
      | async |

  Scenario: Auth FastAPI dependency rejects a token without userinfo
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth sessions of user "authuser" are cleared
    And the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "INVALID_CREDENTIALS"

  # A real Keycloak cannot be made to return empty claims for a token that it just issued and that passed
  # validation, so this one defensive branch injects an empty claims result into the real adapter.
  Scenario: Auth FastAPI dependency rejects a token whose claims cannot be read
    Given a keycloak auth realm with user "authuser" holding realm role "auth-reader" and an access token
    And the keycloak auth adapter cannot read the claims of issued tokens
    And the keycloak fastapi auth requires any of roles "auth-reader"
    When the keycloak auth fastapi dependency is called with the access token of user "authuser"
    Then the keycloak auth call fails with error code "TOKEN_EXPIRED"

  @tracing
  Scenario Outline: Keycloak <mode> adapter requests emit HTTP spans
    Given adapter spans are exported to the collector
    And a configured <mode> Keycloak adapter
    When I create a realm named "span-realm" with display name "Span Realm" using <mode> adapter
    Then the collector should have a span with attribute "http.url" containing "/admin/realms"

    Examples:
      | mode  |
      | sync  |
      | async |

  @tracing
  Scenario Outline: Keycloak <mode> adapter spans reach Elastic APM Server <route>
    Given adapter spans are exported to Elastic APM Server <route>
    And a configured <mode> Keycloak adapter
    When I create a realm named "span-realm" with display name "Span Realm" using <mode> adapter
    Then Elastic APM Server should store a span of type "external" with subtype "http"

    Examples:
      | route                 | mode  |
      | directly              | sync  |
      | directly              | async |
      | through the collector | sync  |
      | through the collector | async |
