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
