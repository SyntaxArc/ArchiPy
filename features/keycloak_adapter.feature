# features/keycloak_auth.feature
Feature: Keycloak Authentication Testing
  As a developer
  I want to test Keycloak authentication operations
  So that I can ensure secure authentication and management operations

  Scenario: Create realm and verify creation using sync adapter
    Given a configured sync Keycloak adapter
    When I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    Then the sync realm creation should succeed
    And the realm "test-realm" should exist
    And the realm should have display name "Test Realm"

  Scenario: Create client with service accounts and verify creation using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    When I create a client named "test-client" in realm "test-realm" with service accounts enabled using sync adapter
    Then the sync client creation should succeed
    And the client "test-client" should exist in realm "test-realm"
    And the client "test-client" should have service accounts enabled

  Scenario: Create user and obtain token using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    When I create a user with username "testuser" and password "pass123" using sync adapter
    And I request a token with username "testuser" and password "pass123" using sync adapter
    Then the sync user creation should succeed
    And the sync user token request should succeed
    And the sync token response should contain "access_token" and "refresh_token"

  Scenario: Refresh token using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    And I have a valid token for "testuser" with password "pass123" using sync adapter
    When I refresh the token using sync adapter
    Then the sync token refresh should succeed
    And the sync token response should contain "access_token" and "refresh_token"

  Scenario: Get user info with sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    And I have a valid token for "testuser" with password "pass123" using sync adapter
    When I request user info with the token using sync adapter
    Then the sync user info request should succeed
    And the sync user info should contain "sub" and "preferred_username"

  Scenario: Validate token with sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    And I have a valid token for "testuser" with password "pass123" using sync adapter
    When I validate the token using sync adapter
    Then the sync token validation should succeed

  Scenario: Get user by username using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    When I get user by username "testuser" using sync adapter
    Then the sync user retrieval should succeed
    And the user should have username "testuser"

  Scenario: Get user by email using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user including username "testuser" email "test@example.com" and password "pass123" using sync adapter
    When I get user by email "test@example.com" using sync adapter
    Then the sync user retrieval should succeed
    And the user should have email "test@example.com"

  Scenario: Create and assign realm role using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    When I create a realm role named "test-role" with description "Test Role" using sync adapter
    And I assign realm role "test-role" to user "testuser" using sync adapter
    Then the sync realm role creation should succeed
    And the sync realm role assignment should succeed
    And the user "testuser" should have realm role "test-role"

  Scenario: Create and assign client role using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    When I create a client role named "client-role" for client "test-client" with description "Client Role" using sync adapter
    And I assign client role "client-role" of client "test-client" to user "testuser" using sync adapter
    Then the sync client role creation should succeed
    And the sync client role assignment should succeed
    And the user "testuser" should have client role "client-role" for client "test-client"

  Scenario: Search users using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "searchuser1" and password "pass123" using sync adapter
    And I create a user with username "searchuser2" and password "pass123" using sync adapter
    When I search for users with query "searchuser" using sync adapter
    Then the sync user search should succeed
    And the search results should contain 2 users

  Scenario: Update user using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    When I update user "testuser" with first name "John" and last name "Doe" using sync adapter
    Then the sync user update should succeed
    And the user "testuser" should have first name "John" and last name "Doe"

  Scenario: Reset user password using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    When I reset password for user "testuser" to "newpass456" using sync adapter
    Then the sync password reset should succeed
    And I should be able to get token with username "testuser" and password "newpass456" using sync adapter

  Scenario: Clear user sessions using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    And I have a valid token for "testuser" with password "pass123" using sync adapter
    When I clear sessions for user "testuser" using sync adapter
    Then the sync session clearing should succeed

  Scenario: Logout user using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    And I have a valid token for "testuser" with password "pass123" using sync adapter
    When I logout the user using sync adapter
    Then the sync logout operation should succeed

  Scenario: Get client credentials token using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    When I request client credentials token using sync adapter
    Then the sync client credentials token request should succeed
    And the sync token response should contain "access_token"

  Scenario: Introspect token using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    And I have a valid token for "testuser" with password "pass123" using sync adapter
    When I introspect the token using sync adapter
    Then the sync token introspection should succeed
    And the introspection result should indicate active token

  Scenario: Get token info using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    And I have a valid token for "testuser" with password "pass123" using sync adapter
    When I get token info using sync adapter
    Then the sync token info request should succeed
    And the token info should contain user claims

  Scenario: Check user role permissions using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    And I create a realm role named "test-role" with description "Test Role" using sync adapter
    And I assign realm role "test-role" to user "testuser" using sync adapter
    And I have a valid token for "testuser" with password "pass123" using sync adapter
    When I check if user has role "test-role" using sync adapter
    Then the sync role check should succeed
    And the user should have the role "test-role"

  Scenario: Remove realm role from user using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    And I create a realm role named "test-role" with description "Test Role" using sync adapter
    And I assign realm role "test-role" to user "testuser" using sync adapter
    When I remove realm role "test-role" from user "testuser" using sync adapter
    Then the sync role removal should succeed
    And the user "testuser" should not have realm role "test-role"

  Scenario: Delete user using sync adapter
    Given a configured sync Keycloak adapter
    And I create a realm named "test-realm" with display name "Test Realm" using sync adapter
    And I create a client named "test-client" in realm "test-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "testuser" and password "pass123" using sync adapter
    When I delete user "testuser" using sync adapter
    Then the sync user deletion should succeed
    And the user "testuser" should not exist

  @async
  Scenario: Create realm and verify creation using async adapter
    Given a configured async Keycloak adapter
    When I create a realm named "async-test-realm" with display name "Async Test Realm" using async adapter
    Then the async realm creation should succeed
    And the realm "async-test-realm" should exist
    And the realm should have display name "Async Test Realm"

  @async
  Scenario: Create client with service accounts and verify creation using async adapter
    Given a configured async Keycloak adapter
    And I create a realm named "async-test-realm" with display name "Async Test Realm" using async adapter
    When I create a client named "async-test-client" in realm "async-test-realm" with service accounts enabled using async adapter
    Then the async client creation should succeed
    And the client "async-test-client" should exist in realm "async-test-realm"
    And the client "async-test-client" should have service accounts enabled

  @async
  Scenario: Create user and obtain token using async adapter
    Given a configured async Keycloak adapter
    And I create a realm named "async-test-realm" with display name "Async Test Realm" using async adapter
    And I create a client named "async-test-client" in realm "async-test-realm" with service accounts enabled using async adapter
    When I create a user with username "asyncuser" and password "async123" using async adapter
    And I request a token with username "asyncuser" and password "async123" using async adapter
    Then the async user creation should succeed
    And the async user token request should succeed
    And the async token response should contain "access_token" and "refresh_token"

  @async
  Scenario: Refresh token using async adapter
    Given a configured async Keycloak adapter
    And I create a realm named "async-test-realm" with display name "Async Test Realm" using async adapter
    And I create a client named "async-test-client" in realm "async-test-realm" with service accounts enabled using async adapter
    And I create a user with username "asyncuser" and password "async123" using async adapter
    And I have a valid token for "asyncuser" with password "async123" using async adapter
    When I refresh the token using async adapter
    Then the async token refresh should succeed
    And the async token response should contain "access_token" and "refresh_token"

  @async
  Scenario: Get user info using async adapter
    Given a configured async Keycloak adapter
    And I create a realm named "async-test-realm" with display name "Async Test Realm" using async adapter
    And I create a client named "async-test-client" in realm "async-test-realm" with service accounts enabled using async adapter
    And I create a user with username "asyncuser" and password "async123" using async adapter
    And I have a valid token for "asyncuser" with password "async123" using async adapter
    When I request user info with the token using async adapter
    Then the async user info request should succeed
    And the async user info should contain "sub" and "preferred_username"

  @async
  Scenario: Validate token using async adapter
    Given a configured async Keycloak adapter
    And I create a realm named "async-test-realm" with display name "Async Test Realm" using async adapter
    And I create a client named "async-test-client" in realm "async-test-realm" with service accounts enabled using async adapter
    And I create a user with username "asyncuser" and password "async123" using async adapter
    And I have a valid token for "asyncuser" with password "async123" using async adapter
    When I validate the token using async adapter
    Then the async token validation should succeed

  @async
  Scenario: Create and assign realm role using async adapter
    Given a configured async Keycloak adapter
    And I create a realm named "async-test-realm" with display name "Async Test Realm" using async adapter
    And I create a client named "async-test-client" in realm "async-test-realm" with service accounts enabled using async adapter
    And I create a user with username "asyncuser" and password "async123" using async adapter
    When I create a realm role named "async-test-role" with description "Async Test Role" using async adapter
    And I assign realm role "async-test-role" to user "asyncuser" using async adapter
    Then the async realm role creation should succeed
    And the async realm role assignment should succeed
    And the user "asyncuser" should have realm role "async-test-role"

  @async
  Scenario: Search users using async adapter
    Given a configured async Keycloak adapter
    And I create a realm named "async-test-realm" with display name "Async Test Realm" using async adapter
    And I create a client named "async-test-client" in realm "async-test-realm" with service accounts enabled using async adapter
    And I create a user with username "asynctestuser4" and password "async123" using async adapter
    And I create a user with username "asynctestuser5" and password "async123" using async adapter
    When I search for users with query "asynctestuser" using async adapter
    Then the async user search should succeed
    And the search results should contain 2 users

  @async
  Scenario: Delete user using async adapter
    Given a configured async Keycloak adapter
    And I create a realm named "async-test-realm" with display name "Async Test Realm" using async adapter
    And I create a client named "async-test-client" in realm "async-test-realm" with service accounts enabled using async adapter
    And I create a user with username "asyncuser6" and password "async123" using async adapter
    When I delete user "asyncuser6" using async adapter
    Then the async user deletion should succeed
    And the user "asyncuser6" should not exist
