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

  Scenario Outline: A PostgreSQL DSN fills the connection parts it carries
    When a PostgreSQL configuration is built from the DSN "<dsn>"
    Then the PostgreSQL connection parts should be user "<user>", password "<password>", host "<host>", port <port> and database "<database>"

    Examples: DSN forms
      | dsn                                                    | user  | password | host        | port | database |
      | postgresql+psycopg://alice:s3cret@db.internal:5433/app | alice | s3cret   | db.internal | 5433 | app      |
      | postgresql+psycopg://bob@db.internal:5432/app          | bob   | (none)   | db.internal | 5432 | app      |

  Scenario: PostgreSQL connection parts build the DSN
    When a PostgreSQL configuration is built from the parts user "alice", password "s3cret", host "db.internal", port 5433 and database "app"
    Then the PostgreSQL DSN should be "postgresql+psycopg://alice:s3cret@db.internal:5433/app"

  Scenario: Connection parts that are set win over the DSN
    When a PostgreSQL configuration is built with the host "override.internal" and the DSN "postgresql+psycopg://alice:s3cret@db.internal:5433/app"
    Then the PostgreSQL connection parts should be user "alice", password "s3cret", host "override.internal", port 5433 and database "app"

  Scenario Outline: A StarRocks isolation level of <level> is <outcome>
    When a StarRocks configuration is built with the isolation level "<level>"
    Then the StarRocks configuration should be <outcome>

    Examples: Isolation levels
      | level           | outcome  |
      | READ COMMITTED  | accepted |
      | read_committed  | accepted |
      | SERIALIZABLE    | rejected |
      | REPEATABLE READ | rejected |

  Scenario Outline: A Vault client is refused when <problem>
    When a Vault client is built for <auth_method> auth when <problem>
    Then a ConfigurationError should be raised
    And the error should mention "<fragment>"

    Examples: Incomplete Vault settings
      | auth_method | problem                          | fragment              |
      | token       | no token is set                  | TOKEN or TOKEN_FILE   |
      | token       | the token file cannot be read    | Failed to read secret |
      | approle     | no role id is set                | APPROLE_ROLE_ID       |
      | approle     | no secret id is set              | APPROLE_SECRET_ID     |
      | userpass    | no username is set               | USERNAME              |
      | userpass    | no password is set               | PASSWORD              |
      | kubernetes  | no role is set                   | KUBERNETES_ROLE       |
      | jwt         | no role is set                   | JWT_ROLE              |
      | jwt         | no jwt is set                    | JWT or JWT_FILE       |
      | aws         | no access key is set             | AWS_ACCESS_KEY        |
      | azure       | no role is set                   | AZURE_ROLE            |
      | azure       | no jwt is set                    | AZURE_JWT             |
      | gcp         | no role is set                   | GCP_ROLE              |
      | gcp         | no jwt is set                    | GCP_JWT               |
      | github      | no github token is set           | GITHUB_TOKEN          |
      | token       | no address is set                | VAULT.ADDR            |
      | token       | only a client certificate is set | CLIENT_KEY_PATH       |

  Scenario Outline: A Vault client logs in with <method>
    Given Vault accepts <method> logins for a test identity
    When a Vault client is built for the test identity
    Then the Vault client should be authenticated

    Examples: Login methods
      | method     |
      | token file |
      | approle    |
      | userpass   |

  Scenario Outline: A <section> configuration with <problem> is <outcome>
    When a <section> configuration is built with <problem>
    Then the configuration should be <outcome>

    Examples: Configuration checks
      | section  | problem                                 | outcome  |
      | Kafka    | SASL_SSL without credentials            | rejected |
      | Kafka    | SASL_SSL with credentials               | accepted |
      | Kafka    | auto commit and no offset reset         | rejected |
      | Kafka    | a heartbeat longer than the session     | rejected |
      | Redis    | cluster mode without nodes              | rejected |
      | Redis    | cluster mode with nodes                 | accepted |
      | Redis    | sentinel mode without a service name    | rejected |
      | Redis    | standalone mode without a host          | rejected |
      | ScyllaDB | no contact points                       | rejected |
      | ScyllaDB | a username without a password           | rejected |
      | ScyllaDB | a minimum pool above the maximum        | rejected |
      | Temporal | only a client certificate               | rejected |
      | Temporal | a run timeout above the execution one   | rejected |
      | Temporal | a keep alive timeout above the interval | rejected |

  Scenario Outline: The Temporal <field> default is <expected>
    When a default Temporal configuration is built
    Then the default Temporal setting <field> should be <expected>

    Examples: Temporal defaults
      | field                      | expected |
      | ACTIVITY_HEARTBEAT_TIMEOUT | None     |
      | PYDANTIC_DATA_CONVERTER    | True     |

  Scenario Outline: The <environment> environment reports its kind and log level
    When the environment type <environment> is inspected
    Then it should be production <production>, test <test>, dev <dev>, local <local> and log at <level>

    Examples: Environment kinds
      | environment | production | test  | dev   | local | level   |
      | PRODUCTION  | True       | False | False | False | WARNING |
      | BETA        | False      | True  | False | False | INFO    |
      | ALPHA       | False      | True  | False | False | INFO    |
      | TEST        | False      | True  | False | False | INFO    |
      | DEV         | False      | False | True  | False | DEBUG   |
      | LOCAL       | False      | False | False | True  | DEBUG   |
