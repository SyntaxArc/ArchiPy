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

  Scenario Outline: A PostgreSQL DSN carries percent-encoded credentials and libpq options
    When a PostgreSQL configuration is built from the DSN "<dsn>"
    Then the PostgreSQL connection parts should be user "<user>", password "<password>", host "db.internal", port 5432 and database "app"
    And the PostgreSQL options should be SSL_MODE "<ssl_mode>", SSL_ROOT_CERT "<root_cert>", APPLICATION_NAME "<app>" and CONNECT_TIMEOUT "<timeout>"

    Examples: DSN forms
      | dsn                                                                                                                                   | user   | password | ssl_mode    | root_cert   | app    | timeout |
      | postgresql+psycopg://al%40ice:p%40ss%2Fw@db.internal:5432/app                                                                         | al@ice | p@ss/w   | (none)      | (none)      | (none) | (none)  |
      | postgresql+psycopg://alice:s3@db.internal:5432/app?sslmode=verify-full&sslrootcert=/etc/ca.pem&application_name=svc&connect_timeout=7 | alice  | s3       | verify-full | /etc/ca.pem | svc    | 7       |

  Scenario: PostgreSQL connection parts build the DSN
    When a PostgreSQL configuration is built from the parts user "alice", password "s3cret", host "db.internal", port 5433 and database "app"
    Then the PostgreSQL DSN should be "postgresql+psycopg://alice:s3cret@db.internal:5433/app"

  Scenario Outline: A password with reserved characters builds a valid DSN and never appears in an error
    When a PostgreSQL configuration is built from the parts user "alice", password "<password>", host "db.internal", port 5433 and database "app"
    Then the PostgreSQL DSN should be "<dsn>"
    And the PostgreSQL connection parts should be user "alice", password "<password>", host "db.internal", port 5433 and database "app"
    And an invalid PostgreSQL configuration with password "<password>" should not echo it in its error

    Examples: Reserved characters
      | password  | dsn                                                           |
      | S3cret/x  | postgresql+psycopg://alice:S3cret%2Fx@db.internal:5433/app    |
      | p#ss?word | postgresql+psycopg://alice:p%23ss%3Fword@db.internal:5433/app |

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

  Scenario Outline: A Vault client applies <tls> and its timeouts to every request
    Given Vault accepts token file logins for a test identity
    And the test identity uses <tls> with a 3s connect and 9s read timeout
    When a Vault client is built for the test identity
    Then the Vault client should be authenticated
    And the Vault client should send requests with verify <verify> and a 3s, 9s timeout

    Examples: TLS settings
      | tls                       | verify                    |
      | no TLS overrides          | True                      |
      | TLS verification disabled | False                     |
      | a custom CA bundle        | /etc/archipy/vault-ca.pem |

  Scenario Outline: A <section> configuration with <problem> is <outcome>
    When a <section> configuration is built with <problem>
    Then the configuration should be <outcome>

    Examples: Configuration checks
      | section  | problem                                            | outcome  |
      | Kafka    | SASL_SSL without credentials                       | rejected |
      | Kafka    | SASL_SSL with credentials                          | accepted |
      | Kafka    | auto commit and no offset reset                    | rejected |
      | Kafka    | a heartbeat longer than the session                | rejected |
      | Redis    | cluster mode without nodes                         | rejected |
      | Redis    | cluster mode with nodes                            | accepted |
      | Redis    | sentinel mode without a service name               | rejected |
      | Redis    | standalone mode without a host                     | rejected |
      | ScyllaDB | no contact points                                  | rejected |
      | ScyllaDB | a username without a password                      | rejected |
      | ScyllaDB | a minimum pool above the maximum                   | rejected |
      | ScyllaDB | a client certificate without a key                 | rejected |
      | ScyllaDB | a CA file with TLS disabled                        | rejected |
      | ScyllaDB | TLS enabled with a CA file                         | accepted |
      | ScyllaDB | an exponential reconnection base above the maximum | rejected |
      | ScyllaDB | an exponential reconnection within bounds          | accepted |
      | Temporal | only a client certificate                          | rejected |
      | Temporal | only a CA certificate                              | accepted |
      | Temporal | a client key without a certificate                 | rejected |
      | Temporal | a run timeout above the execution one              | rejected |
      | Temporal | a keep alive timeout above the interval            | rejected |
      | Temporal | a task timeout above the run timeout               | accepted |
      | Temporal | a verification name without a CA                   | rejected |
      | Temporal | a verification name with a CA                      | accepted |

  Scenario Outline: A ScyllaDB configuration with <tls> builds <context>
    When a ScyllaDB TLS context is built with <tls>
    Then the ScyllaDB TLS context should be <context>

    Examples: TLS contexts
      | tls                                | context                             |
      | TLS disabled                       | absent                              |
      | a CA file                          | verifying with host name check      |
      | a CA file and no host name check   | verifying without host name check   |
      | verification disabled              | not verifying                       |
      | a CA file and a client certificate | verifying with a client certificate |

  Scenario Outline: The Temporal <field> default is <expected>
    When a default Temporal configuration is built
    Then the default Temporal setting <field> should be <expected>

    Examples: Temporal defaults
      | field                                  | expected |
      | ACTIVITY_HEARTBEAT_TIMEOUT             | None     |
      | WORKER_POLLER_AUTOSCALING              | False    |
      | WORKFLOW_RETRY_ENABLED                 | False    |
      | PYDANTIC_DATA_CONVERTER                | True     |
      | WORKFLOW_EXECUTION_TIMEOUT             | None     |
      | WORKFLOW_RUN_TIMEOUT                   | None     |
      | CONNECT_TIMEOUT                        | None     |
      | TLS_VERIFICATION_SERVER_NAME           | None     |
      | GRPC_COMPRESSION                       | None     |
      | PAYLOADS_WARN_SIZE                     | None     |
      | MEMO_WARN_SIZE                         | None     |
      | RUNTIME_DISABLE_ENVIRONMENT_INFO       | False    |
      | WORKER_MAX_EAGER_ACTIVITY_RESERVATIONS | None     |

  Scenario Outline: The Elasticsearch client carries retry backoff only when configured
    When I build an Elasticsearch client with RETRY_BACKOFF_BASE <base> and RETRY_BACKOFF_CAP <cap>
    Then the client retry backoff should be <expected>

    Examples: Retry backoff
      | base | cap  | expected  |
      | none | none | default   |
      | 0.5  | 8    | 0.5 and 8 |

  Scenario Outline: The Elasticsearch config rejects bearer auth combined with <other> auth
    When I validate an Elasticsearch config with BEARER_AUTH and <other> auth
    Then the Elasticsearch config should be rejected as invalid

    Examples: Conflicting auth
      | other   |
      | API key |
      | basic   |

  Scenario: The Elasticsearch client sends no extra headers or cloud settings when unset
    When I build an Elasticsearch client with RETRY_BACKOFF_BASE none and RETRY_BACKOFF_CAP none
    Then the client should carry no bearer, opaque ID or custom headers

  Scenario Outline: The Postgres session managers pass connect_timeout to psycopg only when configured
    When I read the connect arguments of the <kind> Postgres session manager with CONNECT_TIMEOUT <value>
    Then the connect arguments should be <expected>

    Examples: Connect arguments
      | kind  | value | expected          |
      | sync  | none  | empty             |
      | sync  | 7     | connect_timeout 7 |
      | async | none  | empty             |
      | async | 7     | connect_timeout 7 |

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

  Scenario Outline: The <db_type> session managers pass the <field> option to the <kind> driver only when configured
    When I build the <kind> <db_type> driver options with <field> set to <value>
    Then the driver options should be <expected>

    Examples: PostgreSQL
      | kind  | db_type  | field                       | value | expected                                 |
      | sync  | postgres | STATEMENT_TIMEOUT_MS        | null  | {}                                       |
      | sync  | postgres | STATEMENT_TIMEOUT_MS        | 5000  | {"options": "-c statement_timeout=5000"} |
      | async | postgres | LOCK_TIMEOUT_MS             | 1500  | {"options": "-c lock_timeout=1500"}      |
      | sync  | postgres | APPLICATION_NAME            | "api" | {"application_name": "api"}              |
      | async | postgres | PREPARE_THRESHOLD           | 0     | {"prepare_threshold": 0}                 |
      | sync  | postgres | DISABLE_PREPARED_STATEMENTS | true  | {"prepare_threshold": null}              |

    Examples: MySQL
      | kind  | db_type | field                     | value | expected                                                   |
      | sync  | mysql   | CONNECT_TIMEOUT           | null  | {}                                                         |
      | sync  | mysql   | CONNECT_TIMEOUT           | 7     | {"connect_timeout": 7}                                     |
      | async | mysql   | READ_TIMEOUT              | 9     | {"read_timeout": 9}                                        |
      | sync  | mysql   | WRITE_TIMEOUT             | 11    | {"write_timeout": 11}                                      |
      | async | mysql   | WRITE_TIMEOUT             | 11    | {}                                                         |
      | sync  | mysql   | STATEMENT_TIMEOUT_MS      | 3000  | {"init_command": "SET SESSION max_execution_time=3000"}    |
      | async | mysql   | LOCK_WAIT_TIMEOUT_SECONDS | 4     | {"init_command": "SET SESSION innodb_lock_wait_timeout=4"} |

    Examples: SQLite
      | kind  | db_type | field             | value | expected                     |
      | sync  | sqlite  | TIMEOUT           | null  | {}                           |
      | sync  | sqlite  | TIMEOUT           | 2.5   | {"timeout": 2.5}             |
      | async | sqlite  | TIMEOUT           | 2.5   | {"timeout": 2.5}             |
      | sync  | sqlite  | CHECK_SAME_THREAD | false | {"check_same_thread": false} |
      | async | sqlite  | CHECK_SAME_THREAD | false | {}                           |
