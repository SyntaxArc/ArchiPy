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

  Scenario: Error models are usable without transport SDKs
    Then importing and using public error types does not load gRPC or Keycloak

  Scenario: Resolving domain errors can defer application settings
    Then resolving an error honors the interpreter's import timing for global configuration

  Scenario: Reading a Redis config can defer other settings sections
    Then loading a Redis config honors the interpreter's import timing for SQLAlchemy settings

  Scenario Outline: Creating a <framework> app loads its framework on demand
    Then the "<framework>" app loads with the interpreter's import timing

    Examples:
      | framework |
      | fastapi   |
      | grpc      |

  Scenario: Application utilities can be imported without framework extras
    Then application utilities report missing FastAPI and gRPC extras on request

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
      | name                   | package                                               | implementation                 | definition                                                 | dependency                       |
      | TemporalPort           | archipy.adapters.temporal                             | TemporalWorkerManager          | worker.TemporalWorkerManager                               | temporalio.worker                |
      | TemporalPort           | archipy.adapters.temporal                             | TemporalAdapter                | adapters.TemporalAdapter                                   | temporalio.client                |
      | WorkerPort             | archipy.adapters.temporal                             | BaseWorkflow                   | base.BaseWorkflow                                          | temporalio.workflow              |
      | ScyllaDBPort           | archipy.adapters.scylladb                             | ScyllaDBAdapter                | adapters.ScyllaDBAdapter                                   | cassandra                        |
      | PaymentRequestDTO      | archipy.adapters.internet_payment_gateways.ir.parsian | ParsianShaparakPaymentAdapter  | adapters.ParsianShaparakPaymentAdapter                     | zeep                             |
      | PaymentRequestDTO      | archipy.adapters.internet_payment_gateways.ir.saman   | SamanShaparakPaymentAdapter    | adapters.SamanShaparakPaymentAdapter                       | httpx2                           |
      | InMemoryRateLimitStore | archipy.helpers.interceptors.grpc.rate_limit          | GrpcServerRateLimitInterceptor | grpc_rate_limit_interceptor.GrpcServerRateLimitInterceptor | grpc                             |
      | timing                 | archipy.helpers.decorators                            | trace_span                     | tracing.trace_span                                         | archipy.helpers.utils.otel_utils |
      | timing                 | archipy.helpers.decorators                            | measure_duration               | metrics.measure_duration                                   | archipy.helpers.utils.otel_utils |
      | timing                 | archipy.helpers.decorators                            | grpc_rate_limit                | grpc_rate_limit_window.grpc_rate_limit                     | pydantic                         |

  Scenario: The Keycloak ports defer the SDK on Python 3.15
    Then importing the public Keycloak ports honors the interpreter's import timing

  Scenario: The base configuration keeps error modules lazy on Python 3.15
    Then importing the base configuration honors the interpreter's import timing

  Scenario: Error classes work without the gRPC extra
    Then the error package works when gRPC is not installed

  Scenario: Core helpers defer config and error imports on Python 3.15
    Then importing core helpers honors the interpreter's import timing

  Scenario: Loading global configuration preserves a custom settings provider
    Then the custom settings provider still controls error localization

  Scenario Outline: Construct a <package> client with explicit settings
    Then the "<package>" adapter can defer global configuration when given explicit settings

    Examples:
      | package       |
      | redis         |
      | elasticsearch |
      | kafka         |
      | mysql         |
      | postgres      |
      | sqlite        |
      | starrocks     |
      | minio         |
