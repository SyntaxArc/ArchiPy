Feature: Keycloak Organization Scope FastAPI Dependency

  Scenario Outline: Dependency with an auth context of kind "<kind>"
    Given an auth context of kind "<kind>"
    When the organization dependency is called
    Then the dependency outcome should be "<outcome>"

    Examples:
      | kind                  | outcome           |
      | one organization      | selected          |
      | no organization claim | permission denied |
      | none                  | unauthenticated   |
