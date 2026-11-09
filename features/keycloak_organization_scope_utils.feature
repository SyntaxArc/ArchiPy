Feature: Keycloak Organization Scope Utilities

  Scenario Outline: Resolve the selected organization of <count> organizations with scope "<scope>"
    Given token claims with <count> organizations and scope "<scope>"
    When the selected organization is resolved
    Then the resolution outcome should be "<outcome>"

    Examples:
      | count | scope                 | outcome  |
      | 0     | openid                | none     |
      | 1     | openid profile        | selected |
      | 1     | openid organization:* | none     |
      | 3     | openid organization:* | none     |

  Scenario Outline: Resolve the selected organization of <kind> token claims
    Given token claims of kind "<kind>"
    When the selected organization is resolved
    Then the resolution outcome should be "none"

    Examples:
      | kind            |
      | none            |
      | no organization |

  Scenario Outline: Several organizations with scope "<scope>" are denied
    Given token claims with 3 organizations and scope "<scope>"
    When the selected organization is resolved
    Then a permission denied error should be raised with reason "multiple organizations selected"
    And the error should report an organization count of 3

    Examples:
      | scope          |
      | openid profile |
      | organization:1 |

  Scenario Outline: Malformed organization claim "<case>" with scope "<scope>" is denied
    Given token claims with a malformed organization claim "<case>" and scope "<scope>"
    When the selected organization is resolved
    Then a permission denied error should be raised with reason "invalid organization claim"

    Examples:
      | case             | scope                 |
      | non-mapping      | openid                |
      | non-mapping      | openid organization:* |
      | entry without id | openid                |
      | entry without id | openid organization:* |
      | invalid uuid     | openid                |
      | invalid uuid     | openid organization:* |

  Scenario Outline: Malformed organization claim "<case>" yields no parsed ids
    Given token claims with a malformed organization claim "<case>" and scope "openid"
    When the organization uuids are parsed
    Then no organization uuids should be parsed

    Examples:
      | case             |
      | non-mapping      |
      | entry without id |
      | invalid uuid     |

  Scenario Outline: Scope claim that is <scope_kind> is treated as no scopes for <count> organizations
    Given token claims with <count> organizations and a scope claim that is <scope_kind>
    When the selected organization is resolved
    Then the resolution outcome should be "<outcome>"

    Examples:
      | count | scope_kind | outcome  |
      | 2     | a list     | denied   |
      | 2     | None       | denied   |
      | 2     | missing    | denied   |
      | 1     | a list     | selected |

  Scenario Outline: Requiring an organization fails for <kind> token claims
    Given token claims of kind "<kind>"
    When the selected organization is required
    Then a permission denied error should be raised with reason "organization not selected"

    Examples:
      | kind                           |
      | none                           |
      | no organization                |
      | one organization with wildcard |

  Scenario Outline: Requiring an organization returns the selected one for <kind> token claims
    Given token claims of kind "<kind>"
    When the selected organization is required
    Then the resolution outcome should be "selected"

    Examples:
      | kind             |
      | one organization |
