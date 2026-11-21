Feature: Optional dependencies
  Modules that are imported without an extra must not fail when the optional dependency is missing.

  Scenario: Email adapter works without jinja2 unless a template is used
    Given jinja2 is not installed
    When I build an email message without and with a template
    Then the plain message should be built
    And the template message should fail with a message mentioning "jinja2"

  Scenario: The PostgreSQL adapter requires the Psycopg binary distribution
    When I read the "base" extra of the "postgres" package
    Then it should require "psycopg[binary]>=3.3.9"

  Scenario Outline: The <package> async extra installs greenlet through sqlalchemy[asyncio]
    When I read the "<extra>" extra of the "<package>" package
    Then it should require "sqlalchemy[asyncio]"
    And it should not require "asyncmy2"

    Examples: Async SQL extras
      | package   | extra |
      | mysql     | async |
      | starrocks | async |
      | sqlite    | base  |

  Scenario Outline: A caller imports <name> before using <implementation>
    Given a fresh Python process importing "<name>" from "<package>"
    Then loading "<implementation>" honors the interpreter's import timing for "<definition>" and "<dependency>"

    Examples:
      | name              | package                                               | implementation                  | definition                              | dependency          |
      | BaseError         | archipy.models.errors                                 | KeycloakInvalidCredentialsError | keycloak_errors.InvalidCredentialsError | keycloak.exceptions |
      | TemporalPort      | archipy.adapters.temporal                             | TemporalWorkerManager           | worker.TemporalWorkerManager            | temporalio.worker   |
      | TemporalPort      | archipy.adapters.temporal                             | TemporalAdapter                 | adapters.TemporalAdapter                | temporalio.client   |
      | WorkerPort        | archipy.adapters.temporal                             | BaseWorkflow                    | base.BaseWorkflow                       | temporalio.workflow |
      | ScyllaDBPort      | archipy.adapters.scylladb                             | ScyllaDBAdapter                 | adapters.ScyllaDBAdapter                | cassandra           |
      | PaymentRequestDTO | archipy.adapters.internet_payment_gateways.ir.parsian | ParsianShaparakPaymentAdapter   | adapters.ParsianShaparakPaymentAdapter  | zeep                |
      | PaymentRequestDTO | archipy.adapters.internet_payment_gateways.ir.saman   | SamanShaparakPaymentAdapter     | adapters.SamanShaparakPaymentAdapter    | httpx2              |

  Scenario: The Keycloak ports defer the SDK on Python 3.15
    Then importing the public Keycloak ports honors the interpreter's import timing

  Scenario Outline: Construct a <package> client with explicit settings
    Then the "<package>" adapter can defer global configuration when given explicit settings

    Examples:
      | package       |
      | redis         |
      | elasticsearch |
      | kafka         |
