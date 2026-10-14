@needs-vault
Feature: Base Configuration System

  Scenario: Setting and retrieving global configuration
    Given a custom BaseConfig instance
    When the global configuration is set
    Then retrieving global configuration should return the same instance

  Scenario: Retrieving global configuration without setting it
    Given BaseConfig is not initialized globally
    When retrieving global configuration
    Then an error should be raised with message "You should set global configs with BaseConfig.set_global(MyConfig())"

  Scenario Outline: Ensure configuration contains specific attributes
    Given a custom BaseConfig instance
    When the configuration is initialized
    Then the attribute "<attribute>" should exist

    Examples:
      | attribute |
      | APP_NAME  |
      | AUTH      |
      | ELASTIC   |
      | REDIS     |
      | FASTAPI   |

  Scenario: Ensure .env settings override BaseConfig's defaults
    Given an env file with key "ENVIRONMENT" and value "PRODUCTION"
    When BaseConfig is initialized
    Then the ENVIRONMENT should be "PRODUCTION"

  Scenario: Vault secrets are injected into nested config fields
    Given a running Vault instance with a KV v2 secret at "myapp/config" containing "REDIS__PASSWORD=vault-secret"
    When BaseConfig is initialized with Vault enabled
    Then the REDIS.PASSWORD should be "vault-secret"

  Scenario: Vault secrets override environment variables
    Given a running Vault instance with a KV v2 secret at "myapp/config" containing "REDIS__PASSWORD=vault-secret"
    And the environment variable "REDIS__PASSWORD" is set to "env-secret"
    When BaseConfig is initialized with Vault enabled
    Then the REDIS.PASSWORD should be "vault-secret"

  Scenario: Vault settings source is a no-op when disabled
    Given Vault is not enabled
    When BaseConfig is initialized
    Then no Vault connection should be attempted

  Scenario: Vault authentication failure surfaces a configuration error
    Given a running Vault instance with an invalid token
    When BaseConfig is initialized with Vault enabled
    Then a ConfigurationError should be raised

  Scenario: APP_NAME syncs into nested identity fields on set_global
    Given a BaseConfig with APP_NAME "my-service" and nested identity defaults
    When the global configuration is set
    Then OTEL.SERVICE_NAME should be "my-service"
    And FASTAPI.PROJECT_NAME should be "my-service"
    And AUTH.JWT_ISSUER should be "my-service"
    And TEMPORAL.CLIENT_IDENTITY should be "my-service"

  Scenario: Explicit nested identity overrides win over APP_NAME
    Given a BaseConfig with APP_NAME "my-service" and OTEL.SERVICE_NAME "other"
    When the global configuration is set
    Then OTEL.SERVICE_NAME should be "other"

  Scenario: An unset COUNT_THRESHOLD defaults to PAGINATION.MAX_ITEMS on set_global
    Given a BaseConfig with PAGINATION.MAX_ITEMS 500 and no COUNT_THRESHOLD
    When the global configuration is set
    Then every SQLAlchemy COUNT_THRESHOLD should be 500

  Scenario: An explicit COUNT_THRESHOLD wins over PAGINATION.MAX_ITEMS
    Given a BaseConfig with PAGINATION.MAX_ITEMS 500 and POSTGRES_SQLALCHEMY.COUNT_THRESHOLD 20
    When the global configuration is set
    Then POSTGRES_SQLALCHEMY.COUNT_THRESHOLD should be 20
    And SQLITE_SQLALCHEMY.COUNT_THRESHOLD should be 500

  Scenario: The pagination limit follows PAGINATION.MAX_ITEMS
    Given a BaseConfig with PAGINATION.MAX_ITEMS 50 and no COUNT_THRESHOLD
    When the global configuration is set
    Then pagination of page 5 with size 10 should be accepted
    And pagination of page 6 with size 10 should be rejected as out of range
