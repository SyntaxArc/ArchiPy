Feature: Optional dependencies
  Modules that are imported without an extra must not fail when the optional dependency is missing.

  Scenario: Email adapter works without jinja2 unless a template is used
    Given jinja2 is not installed
    When I build an email message without and with a template
    Then the plain message should be built
    And the template message should fail with a message mentioning "jinja2"
