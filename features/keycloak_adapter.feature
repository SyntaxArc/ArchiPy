# features/keycloak_adapter.feature
@needs-keycloak @needs-envoy @needs-otel-collector
Feature: Keycloak Authentication Testing
  As a developer
  I want to test Keycloak authentication operations
  So that I can ensure secure authentication and management operations

  @realms
  Scenario Outline: Basic realm and client operations
    Given a configured <adapter_type> Keycloak adapter via <via>
    When I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    Then the <adapter_type> realm creation should succeed
    And the realm "<realm_name>" should exist
    And the realm should have display name "<realm_display_name>"

    Examples:
      | adapter_type | realm_name             | realm_display_name | client_name       | via    |
      | sync         | test-realm             | Test Realm         | test-client       | direct |
      | async        | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @realms
  Scenario Outline: Realm update
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And the <adapter_type> realm creation should succeed
    When I update the realm "<realm_name>" display name to "<new_display_name>" using <adapter_type> adapter
    Then the realm "<realm_name>" should have display name "<new_display_name>"

    Examples:
      | adapter_type | realm_name               | realm_display_name | new_display_name   | via    |
      | sync         | update-realm             | Original           | Updated Display    | direct |
      | async        | async-update-realm       | Async Original     | Async Updated Name | direct |
      | sync         | update-realm-envoy       | Original           | Updated Display    | envoy  |
      | async        | async-update-realm-envoy | Async Original     | Async Updated Name | envoy  |

  @tokens
  Scenario Outline: User authentication flow
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I request a token with username "<username>" and password "<password>" using <adapter_type> adapter
    Then the <adapter_type> user creation should succeed
    And the <adapter_type> user token request should succeed
    And the <adapter_type> token response should contain "access_token" and "refresh_token"

    Examples:
      | adapter_type | username  | password | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @tokens
  Scenario Outline: Token operations
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I refresh the token using <adapter_type> adapter
    Then the <adapter_type> token refresh should succeed
    And the <adapter_type> token response should contain "access_token" and "refresh_token"

    Examples:
      | adapter_type | username  | password | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @users
  Scenario Outline: User information operations
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I request user info with the token using <adapter_type> adapter
    Then the <adapter_type> user info request should succeed
    And the <adapter_type> user info should contain "sub" and "preferred_username"

    Examples:
      | adapter_type | username  | password | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @tokens
  Scenario Outline: Token validation
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I validate the token using <adapter_type> adapter
    Then the <adapter_type> token validation should succeed

    Examples:
      | adapter_type | username  | password | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @tokens
  Scenario: Async token validation after the realm signing key rotates
    Given a configured sync Keycloak adapter via direct
    And I create a realm named "async-rotated-key-realm" with display name "Rotated Key Realm" using sync adapter
    And I create a client named "async-rotated-key-client" in realm "async-rotated-key-realm" with service accounts and update adapter using sync adapter
    And I create a user with username "rotateuser" and password "pass123" using sync adapter
    And I have a valid token for "rotateuser" with password "pass123" using sync adapter
    And the realm "async-rotated-key-realm" rotates its signing key
    Then an async adapter for realm "async-rotated-key-realm" and client "async-rotated-key-client" should validate the token of "rotateuser"
    And the same async adapter should read the claims of the token of "rotateuser"

  @tokens
  Scenario Outline: Clearing all caches works without admin mode
    Given a configured sync Keycloak adapter via direct
    Then a <kind> adapter without admin mode clears all its caches without logging in

    Examples:
      | kind  |
      | sync  |
      | async |

  @tokens
  Scenario Outline: Async adapter refreshes an expired admin token once and off the event loop
    Given a configured sync Keycloak adapter via direct
    When <calls> concurrent admin calls run on an async adapter whose admin token expired
    Then the admin client was refreshed once outside the event loop thread

    Examples:
      | calls |
      | 1     |
      | 5     |

  @users
  Scenario Outline: User retrieval operations
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I get user by username "<username>" using <adapter_type> adapter
    Then the <adapter_type> user retrieval should succeed
    And the user should have username "<username>"

    Examples:
      | adapter_type | username  | password | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @users
  Scenario Outline: Email-based user retrieval
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user including username "<username>" email "<email>" and password "<password>" using <adapter_type> adapter
    When I get user by email "<email>" using <adapter_type> adapter
    Then the <adapter_type> user retrieval should succeed
    And the user should have email "<email>"

    Examples:
      | adapter_type | username  | email             | password | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | test@example.com  | pass123  | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async@example.com | async123 | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | test@example.com  | pass123  | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async@example.com | async123 | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @roles
  Scenario Outline: Realm role management
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I create a realm role named "<role_name>" with description "<role_description>" using <adapter_type> adapter
    And I assign realm role "<role_name>" to user "<username>" using <adapter_type> adapter
    Then the <adapter_type> realm role creation should succeed
    And the <adapter_type> realm role assignment should succeed
    And the user "<username>" should have realm role "<role_name>"

    Examples:
      | adapter_type | username  | password | role_name       | role_description | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | test-role       | Test Role        | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | async-test-role | Async Test Role  | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | test-role       | Test Role        | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | async-test-role | Async Test Role  | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @roles
  Scenario Outline: Client role management
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I create a client role named "<client_role_name>" for client "<client_name>" with description "<client_role_description>" using <adapter_type> adapter
    And I assign client role "<client_role_name>" of client "<client_name>" to user "<username>" using <adapter_type> adapter
    Then the <adapter_type> client role creation should succeed
    And the <adapter_type> client role assignment should succeed
    And the user "<username>" should have client role "<client_role_name>" for client "<client_name>"

    Examples:
      | adapter_type | username  | password | client_role_name  | client_role_description | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | client-role       | Client Role             | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | async-client-role | Async Client Role       | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | client-role       | Client Role             | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | async-client-role | Async Client Role       | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @users
  Scenario Outline: User search operations
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<search_user1>" and password "<password>" using <adapter_type> adapter
    And I create a user with username "<search_user2>" and password "<password>" using <adapter_type> adapter
    When I search for users with query "<search_query>" using <adapter_type> adapter
    Then the <adapter_type> user search should succeed
    And the search results should contain 2 users

    Examples:
      | adapter_type | search_user1   | search_user2   | search_query  | password | realm_name             | realm_display_name | client_name       | via    |
      | sync         | searchuser1    | searchuser2    | searchuser    | pass123  | test-realm             | Test Realm         | test-client       | direct |
      | async        | asynctestuser4 | asynctestuser5 | asynctestuser | async123 | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | searchuser1    | searchuser2    | searchuser    | pass123  | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asynctestuser4 | asynctestuser5 | asynctestuser | async123 | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @users
  Scenario Outline: User update operations
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I update user "<username>" with first name "<first_name>" and last name "<last_name>" using <adapter_type> adapter
    Then the <adapter_type> user update should succeed
    And the user "<username>" should have first name "<first_name>" and last name "<last_name>"

    Examples:
      | adapter_type | username  | password | first_name | last_name | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | John       | Doe       | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | Async      | User      | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | John       | Doe       | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | Async      | User      | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @users
  Scenario Outline: Password reset operations
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    When I reset password for user "<username>" to "<new_password>" using <adapter_type> adapter
    Then the <adapter_type> password reset should succeed
    And I should be able to get token with username "<username>" and password "<new_password>" using <adapter_type> adapter

    Examples:
      | adapter_type | username  | password | new_password | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | newpass456   | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | newasync456  | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | newpass456   | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | newasync456  | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @users
  Scenario Outline: Session management
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I clear sessions for user "<username>" using <adapter_type> adapter
    Then the <adapter_type> session clearing should succeed

    Examples:
      | adapter_type | username  | password | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @tokens
  Scenario Outline: Logout operations
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    And I create a user with username "<username>" and password "<password>" using <adapter_type> adapter
    And I have a valid token for "<username>" with password "<password>" using <adapter_type> adapter
    When I logout the user using <adapter_type> adapter
    Then the <adapter_type> logout operation should succeed

    Examples:
      | adapter_type | username  | password | realm_name             | realm_display_name | client_name       | via    |
      | sync         | testuser  | pass123  | test-realm             | Test Realm         | test-client       | direct |
      | async        | asyncuser | async123 | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | testuser  | pass123  | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | asyncuser | async123 | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |

  @tokens
  Scenario Outline: Client credentials token
    Given a configured <adapter_type> Keycloak adapter via <via>
    And I create a realm named "<realm_name>" with display name "<realm_display_name>" using <adapter_type> adapter
    And I create a client named "<client_name>" in realm "<realm_name>" with service accounts and update adapter using <adapter_type> adapter
    When I request client credentials token using <adapter_type> adapter
    Then the <adapter_type> client credentials token request should succeed
    And the <adapter_type> token response should contain "access_token"

    Examples:
      | adapter_type | realm_name             | realm_display_name | client_name       | via    |
      | sync         | test-realm             | Test Realm         | test-client       | direct |
      | async        | async-test-realm       | Async Test Realm   | async-test-client | direct |
      | sync         | test-realm-envoy       | Test Realm         | test-client       | envoy  |
      | async        | async-test-realm-envoy | Async Test Realm   | async-test-client | envoy  |
