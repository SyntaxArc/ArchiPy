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
      | attribute  |
      | AUTH       |
      | ELASTIC    |
      | REDIS      |
      | FASTAPI    |

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
