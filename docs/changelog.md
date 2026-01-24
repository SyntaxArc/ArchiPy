# Changelog

All notable changes to ArchiPy are documented in this changelog, organized by version.

## [v4.0.3] - 2026-01-24

### Added

#### Tests

- Add PostgreSQL and SQLite support for atomic transaction tests
- Add Starrocks TestContainer support

### Changed

- Replace Black with Ruff formatter

### Fixed

#### Configs

- Resolve type errors in base_config and keycloak_utils

- Remove reference to non-existent error_message_types module

### Chore

#### Configs

- Configure Ruff to respect pyproject.toml in CI lint workflow

- Apply Ruff formatting fixes
- Merge branch 'master' of github.com:SyntaxArc/ArchiPy
- Merge pull request #102 from SyntaxArc/dependabot/github_actions/actions/cache-5
- Update dependencies

### CI

- Bump actions/cache from 4 to 5
- Refactor ty workflow
- Separate ruff and ty linting into dedicated workflows

## [v4.0.2] - 2025-12-11

### Changed

#### Development Tools

- Broadened Ruff configuration (additional ignores, per-file overrides, relaxed limits) and expanded type-checking/lint
  sections for optional dependency handling (lazy imports, optional extras).
- Raised Pylint branch/statement limits to accommodate complex decorator and interceptor flows; added explicit flake8
  config blocks for comprehensions, errmsg, type-checking, and unused-arguments.

#### Adapters

- SQLAlchemy base adapters: tightened filtering/exception handling helpers and optional dependency guards in session
  managers.
- Email/Kafka/ScyllaDB/Temporal adapters: improved lazy import behavior, tracing hooks, and error handling consistency
  to match optional extras.

#### Helpers

- Decorators (cache/retry/timing/tracing/sqlalchemy_atomic): clarified lazy-import paths, kept TYPE_CHECKING stubs, and
  aligned __getattr__ caching.
- gRPC interceptors (trace/metric, client/server): better Sentry span management, traceparent propagation, and guard
  rails when APM extras are disabled.
- Utility helpers (app/error/file/keycloak): safer optional imports for HTTP/gRPC/Keycloak, clearer exception logging,
  and minor robustness fixes.

#### Testing

- BDD updates for cache decorator (TTL, clearing, bound method identity), Elastic adapter, Keycloak adapter, ScyllaDB
  adapter, and error utils to match revised behaviors and lazy-import handling.

#### Dependencies

- **Optional Dependencies**
    - Updated `starrocks` extra from `>=1.3.1` to `>=1.3.2` (includes `starrocks-async`)

## [v4.0.1] - 2025-12-10

### Added

#### Helpers - Decorators

- **Comprehensive Cache Decorator BDD Tests** - Added extensive BDD test suite for cache decorators
    - Test scenarios for function caching with TTL expiration
    - Test scenarios for async function caching
    - Test scenarios for method caching (both sync and async)
    - Test scenarios for bound method caching with instance isolation
    - Test scenarios for cache key generation with different argument types
    - Test scenarios for cache invalidation and clearing
    - Test scenarios for cache statistics and monitoring
    - Test scenarios for error handling and edge cases

### Fixed

#### Helpers - Decorators

- **Bound Method Caching** - Fixed cache decorator to properly handle bound methods
    - Fixed cache key generation for bound methods to include instance identity
    - Ensures each instance has its own cache namespace
    - Prevents cache collisions between different instances of the same class
    - Improved cache statistics tracking for bound methods

- **Type Checker Errors** - Resolved all Ty type checker errors (22 fixes)
    - Refactored decorators with `ParamSpec` for proper type preservation
    - Implemented descriptor protocol for cache decorator
    - Updated port interfaces with correct type annotations
    - Added `TYPE_CHECKING` imports for better type checking
    - No `cast()` usage - all types properly inferred

### Changed

#### Development Tools

- **Type Checker Migration** - Migrated from MyPy to Ty type checker
    - Replaced MyPy with Ty for Python 3.14 type checking
    - Updated all type hints to use Python 3.14 syntax (`|` for unions, lowercase built-ins)
    - Updated Makefile to use `ty check` instead of `mypy`
    - Changed cache directory from `.mypy_cache/` to `.ty_cache/`
    - Updated pre-commit hooks to use Ty
    - Updated documentation and contributing guides

#### Dependencies

- **Optional Dependencies**
    - Updated `fastapi` from `>=0.124.0` to `>=0.124.2`
    - Updated `sqlalchemy` from `>=2.0.44` to `>=2.0.45`

- **Development Dependencies**
    - Removed `mypy>=1.19.0`
    - Added `ty` (Ty type checker)
    - Updated `types-protobuf` from `>=6.32.1.20251105` to `>=6.32.1.20251210`

## [v4.0.0] - 2025-12-08

### Changed

#### Models - Errors

- **Error System Migration to T-Strings** - Refactored error system to use t-string template formatting with inline
  context variables
    - Removed `ErrorDetailDTO` and `ErrorMessageType` dependencies
    - Added class attributes (`code`, `message_en`, `message_fa`, `http_status`, `grpc_status`) to `BaseError`
    - Implemented t-string template formatting with context variables in error messages
    - Override `get_message()` in error classes with explicit variable passing
    - Applied Persian number conversion for FA language messages
    - Removed deprecated `http_status_code_value` and `grpc_status_code_value` properties
    - Removed `_get_grpc_status_code` method, use `_convert_int_to_grpc_status` directly
    - Updated all error classes (validation, auth, resource, database, business, network, system, keycloak, temporal)
    - Updated FastAPI integration, adapters, and utilities
    - Fixed MyPy type errors in `BaseError.to_dict()` and gRPC metadata handling

### Tests

- **Comprehensive Error Handling Tests** - Added comprehensive error handling tests for FastAPI and gRPC
    - Added BDD test scenarios for FastAPI error handling (`fastapi_error_handling.feature`)
    - Added BDD test scenarios for gRPC error handling (`grpc_error_handling.feature`)
    - Implemented test step definitions for error handling scenarios
    - Added test servers and utilities for FastAPI and gRPC error testing
    - Renamed "exception" to "error" in behave test files and features for consistency

### Chore

- **Python Version References** - Updated all Python version references to 3.14
    - Updated documentation and configuration files to reflect Python 3.14 requirement
    - Aligned version references across the codebase

## [v3.15.3] - 2025-12-02

### Changed

#### Helpers - Decorators

- **Lazy Import for SQLAlchemy Decorators** - Changed SQLAlchemy decorators to use lazy imports via `__getattr__` in
  `archipy.helpers.decorators`
    - SQLAlchemy decorators are now only imported when actually accessed, not at module import time
    - Prevents SQLAlchemy from being required when using archipy without the `sqlalchemy` extra (e.g.,
      `archipy[scylladb]`)
    - Provides better error messages when SQLAlchemy decorators are accessed without the sqlalchemy extra installed
    - Maintains full IDE support through type stubs using `TYPE_CHECKING`

#### Adapters - Temporal

- **Lazy Import for SQLAlchemy Decorators** - Updated `AtomicActivity` class to use lazy imports for SQLAlchemy atomic
  decorators
    - Moved SQLAlchemy decorator imports from module level to method level in `_get_atomic_decorator()`
    - Prevents SQLAlchemy from being required when using Temporal adapters without the sqlalchemy extra
    - Improves modularity and allows using Temporal features independently of SQLAlchemy

## [v3.15.2] - 2025-12-02

### Added

#### Database Adapters - ScyllaDB

- **Conditional Insert Support** - Added `if_not_exists` parameter to `insert()` method in ScyllaDB adapter
    - Prevents errors on duplicate primary keys using CQL's `IF NOT EXISTS` clause
    - Available in both synchronous (`ScyllaDBAdapter`) and asynchronous (`AsyncScyllaDBAdapter`) adapters
    - Uses lightweight transactions to ensure idempotent insert operations
    - Note: This feature is slower than regular inserts due to the lightweight transaction overhead

#### Testing

- **Enhanced BDD Test Suite** - Added test scenarios for ScyllaDB conditional insert functionality
    - Test scenarios for `if_not_exists` parameter in insert operations
    - Validation of duplicate key handling behavior

### Changed

#### Dependencies

- **Core Dependencies**
    - Updated `pydantic` from `>=2.12.4` to `>=2.12.5`

- **Optional Dependencies**
    - Updated `elastic-apm` from `>=6.24.0` to `>=6.24.1`
    - Updated `fastapi` from `>=0.122.0` to `>=0.123.3`
    - Updated `minio` from `>=7.2.18` to `>=7.2.20`
    - Updated `postgres` (psycopg) from `>=3.2.13` to `>=3.3.0`
    - Updated `starrocks` from `>=1.2.3` to `>=1.3.1`
    - Updated `scylladb` optional dependencies to include `cachetools>=6.2.2` and `async-lru>=2.0.5`

- **Development Dependencies**
    - Updated `mypy` from `>=1.18.2` to `>=1.19.0`
    - Updated `pre-commit` from `>=4.4.0` to `>=4.5.0`

- **Documentation Dependencies**
    - Updated `mkdocstrings-python` from `>=1.18.2` to `>=2.0.0`
    - Updated `mkdocstrings` from `>=0.30.1` to `>=1.0.0`

### CI

- **GitHub Actions** - Updated `actions/checkout` from v5 to v6

## [v3.15.1] - 2025-11-30

### Added

#### Database Adapters - ScyllaDB Enhancements

- **Retry Policies** - Added configurable retry policies for handling transient failures in ScyllaDB adapter
    - Exponential backoff retry policy with configurable min/max intervals and max retries
    - Fallthrough retry policy for no-retry scenarios
    - Downgrading consistency retry policy for automatic consistency level adjustment
    - Configuration options: `RETRY_POLICY`, `RETRY_MAX_NUM_RETRIES`, `RETRY_MIN_INTERVAL`, `RETRY_MAX_INTERVAL`

- **Health Checks** - Added comprehensive health check functionality
    - Connection status verification with `is_connected()` method for both sync and async adapters
    - Detailed health metrics including cluster state, host availability, and latency
    - `health_check()` method returning comprehensive cluster health information
    - Configurable health check timeout via `HEALTH_CHECK_TIMEOUT` configuration

- **Exception Handling** - Improved error handling with centralized exception management
    - Centralized `_handle_scylladb_exception()` method for consistent error handling
    - Specific error messages for connection, query execution, and configuration issues
    - Proper exception chaining for better debugging and error tracing

- **Helper Methods** - Added convenience methods for common database operations
    - `insert()` method with TTL support for time-based data expiration
    - `update()` method with conditional updates and TTL support
    - `count()` method for counting rows with optional WHERE clause filtering
    - `exists()` method for checking record existence based on conditions
    - `close()` method for explicit connection cleanup and resource management

- **Connection Pool Monitoring** - Added connection pool statistics and monitoring capabilities
    - `get_pool_stats()` method providing detailed metrics on pool utilization
    - Metrics include connections per host, in-flight requests, and pool health
    - Configurable pool parameters: `MAX_CONNECTIONS_PER_HOST`, `MIN_CONNECTIONS_PER_HOST`, `CORE_CONNECTIONS_PER_HOST`
    - `MAX_REQUESTS_PER_CONNECTION` configuration for request throttling
    - Optional pool monitoring via `ENABLE_CONNECTION_POOL_MONITORING` flag

- **Prepared Statement Caching** - Implemented caching mechanism for prepared statements
    - LRU cache with configurable size via `PREPARED_STATEMENT_CACHE_SIZE`
    - Configurable TTL via `PREPARED_STATEMENT_CACHE_TTL_SECONDS`
    - Automatic cache invalidation after TTL expiration
    - Enable/disable via `ENABLE_PREPARED_STATEMENT_CACHE` configuration
    - Improved performance for frequently executed queries

- **Data Center Awareness** - Added support for multi-datacenter deployments
    - Local datacenter configuration via `LOCAL_DC` for optimized query routing
    - Replication strategy configuration: `REPLICATION_STRATEGY` (SimpleStrategy, NetworkTopologyStrategy)
    - Per-datacenter replication factor configuration via `REPLICATION_CONFIG`
    - Improved latency for geographically distributed deployments

#### Documentation

- **ScyllaDB Adapter Documentation** - Added comprehensive documentation for ScyllaDB adapter
    - Complete usage examples for all adapter methods
    - Configuration guide with all available options
    - Best practices for connection pooling and performance tuning
    - Examples for retry policies, health checks, and TTL usage
    - Multi-datacenter deployment configuration examples

#### Testing

- **Enhanced BDD Test Suite** - Expanded Behave test scenarios for ScyllaDB adapter
    - Added test scenarios for TTL functionality
    - Added test scenarios for helper methods (count, exists, insert, update)
    - Added test scenarios for health checks and connection status
    - Added test scenarios for connection pool monitoring
    - Improved test coverage for error handling and edge cases

## [v3.15.0] - 2025-11-29

### Added

#### Database Adapters

- **ScyllaDB/Cassandra Adapter** - Implemented comprehensive adapter for ScyllaDB and Apache Cassandra databases
  following the Ports & Adapters pattern
    - Added `ScyllaDBPort` and `AsyncScyllaDBPort` interfaces defining contracts for database operations
    - Implemented `ScyllaDBAdapter` for synchronous operations with connection pooling and session management
    - Implemented `AsyncScyllaDBAdapter` for asynchronous operations with async/await support
    - Supports CQL query execution, prepared statements, batch operations, and CRUD operations
    - Provides keyspace and table management (create, drop, use keyspace)
    - Includes connection management with automatic reconnection and session lifecycle handling
    - Supports configurable consistency levels (ONE, QUORUM, ALL, LOCAL_QUORUM, etc.)
    - Implements shard awareness for optimal performance (can be disabled for Docker/Testcontainer environments)
    - Includes LZ4 compression support for network traffic optimization

#### Configuration

- **ScyllaDB Configuration** - Added `ScyllaDBConfig` class for managing ScyllaDB connection settings
    - Configurable contact points (cluster node addresses)
    - Port configuration for CQL native transport (default: 9042)
    - Authentication support (username/password)
    - Protocol version selection (3-5)
    - Connection and request timeout settings
    - Consistency level configuration
    - Compression enable/disable option
    - Shard awareness control for containerized environments
    - Integrated into `BaseConfig` as `SCYLLADB` attribute
    - Added to configuration template with validation rules

#### Testing Infrastructure

- **ScyllaDB Test Container** - Added `ScyllaDBTestContainer` class for integration testing
    - Single-node ScyllaDB container configuration optimized for testing
    - Dynamic port allocation to prevent conflicts
    - Automatic configuration injection into global config
    - Resource-efficient setup (1 CPU, 750MB memory)
    - Integrated with `ContainerManager` for tag-based container startup
    - Added `@needs-scylladb` tag support for selective test execution

- **BDD Test Suite** - Comprehensive Behave test suite for ScyllaDB adapter
    - Feature file covering keyspace operations, table management, CRUD operations
    - Test scenarios for insert, select, update, delete operations
    - Batch execution and prepared statement testing
    - WHERE clause condition testing
    - Error handling and edge case validation
    - Step definitions implementing all adapter operations

#### Dependencies

- **New Optional Dependency Group** - Added `scylladb` optional dependency group
    - Added `scylla-driver>=3.29.0` for ScyllaDB/Cassandra driver support
    - Added `lz4>=4.3.0` for compression support in network communication
    - Enables ScyllaDB adapter functionality when installed via `uv sync --extra scylladb`

## [v3.14.4] - 2025-11-20

### Changed

#### Dependency Updates

- **Comprehensive Dependency Synchronization** - Updated multiple core dependencies to latest versions for improved
  security, performance, and bug fixes
    - Updated fastapi from 0.121.1 to 0.121.3 for enhanced API framework capabilities and bug fixes
    - Updated cachetools from 6.2.1 to 6.2.2 for improved caching utilities and bug fixes
    - Updated protobuf from 6.33.0 to 6.33.1 for enhanced protocol buffer support and bug fixes
    - Updated redis from 7.0.1 to 7.1.0 for improved Redis client capabilities and performance
    - Updated sentry-sdk from 2.43.0 to 2.45.0 for enhanced error tracking and monitoring
    - Updated temporalio from 1.18.2 to 1.19.0 for improved workflow orchestration capabilities
    - Updated testcontainers from 4.13.2 to 4.13.3 for enhanced testing infrastructure
    - Updated bandit from 1.8.6 to 1.9.1 for improved security scanning capabilities
    - Updated ruff from 0.14.4 to 0.14.5 for enhanced linting capabilities and bug fixes
    - Updated mkdocs-material from 9.6.23 to 9.7.0 for improved documentation rendering
    - Updated pymdown-extensions from 10.16.1 to 10.17.1 for enhanced markdown extensions

#### Test Infrastructure

- **Test Container Image Updates** - Updated test container images to latest versions for improved testing
  reliability and compatibility
    - Updated Redis test container image from 8.2.3-alpine to 8.4.0-alpine
    - Updated PostgreSQL test container image from 18.0-alpine to 18.1-alpine
    - Updated Keycloak test container image from 26.4.2 to 26.4.5
    - Updated Elasticsearch test container image from 9.2.0 to 9.2.1

## [v3.14.3] - 2025-11-11

### Fixed

#### Redis Configuration

- **Removed Invalid Retry on Timeout Configuration** - Fixed Redis adapter configuration by removing unsupported
  parameter
    - Removed `RETRY_ON_TIMEOUT` field from `RedisConfig` class as it does not exist in Redis cluster configuration
    - Removed `retry_on_timeout` parameter from both synchronous and asynchronous Redis adapter initialization
    - Resolves configuration errors when using Redis cluster mode with invalid parameters
    - Ensures compatibility with redis-py library's actual parameter set
    - Prevents potential runtime errors from passing unsupported configuration options

### Changed

#### Dependency Updates

- **Comprehensive Dependency Synchronization** - Updated multiple core dependencies to latest versions for improved
  security, performance, and bug fixes
    - Updated fastapi from 0.120.2 to 0.121.1 for enhanced API framework capabilities and bug fixes
    - Updated confluent-kafka from 2.12.1 to 2.12.2 for improved Kafka messaging reliability and performance
    - Updated psycopg from 3.2.11 to 3.2.12 for enhanced PostgreSQL driver stability and bug fixes
    - Updated pydantic-settings from 2.11.0 to 2.12.0 for improved settings management and validation
    - Updated pre-commit from 4.3.0 to 4.4.0 for improved git hook management
    - Updated ruff from 0.14.3 to 0.14.4 for enhanced linting capabilities and bug fixes

## [v3.14.2] - 2025-11-06

### Added

#### Testing Infrastructure

- **Tag-Based Selective Container Startup** - Implemented intelligent container startup based on feature tags for behave
  tests
    - Added `TAG_CONTAINER_MAP` mapping feature tags to container names (e.g., `@needs-postgres`, `@needs-kafka`,
      `@needs-elasticsearch`)
    - Implemented `extract_containers_from_tags()` method in `ContainerManager` to automatically detect required
      containers from feature/scenario tags
    - Enhanced `before_all()` and `before_feature()` hooks in `environment.py` to start only required containers based
      on tags
    - Added container tags to feature files (`atomic_transactions.feature`, `elastic_adapter.feature`,
      `kafka_adapters.feature`, `keycloak_adapter.feature`, `minio_adapter.feature`)
    - Optimizes test execution by starting only necessary containers, reducing resource usage and test startup time
    - Improves test isolation and parallel test execution capabilities

### Changed

#### Testing Infrastructure

- **Dynamic Port Allocation for Testcontainers** - Refactored test container initialization to use dynamic ports instead
  of fixed ports
    - Updated all test container classes (`RedisTestContainer`, `PostgresTestContainer`, `KeycloakTestContainer`,
      `ElasticsearchTestContainer`, `KafkaTestContainer`, `MinioTestContainer`) to use dynamic port allocation
    - Containers now automatically assign available ports using `get_exposed_port()` method from testcontainers
    - Enhanced container startup to update global configuration with actual dynamic host and port values
    - Eliminates port conflicts when running multiple test suites in parallel or on shared CI/CD infrastructure
    - Improved test reliability and compatibility across different environments

- **Simplified Configuration Access** - Streamlined configuration access patterns in test step definitions
    - Refactored step definitions to use `BaseConfig.global_config()` directly instead of complex configuration access
      patterns
    - Updated step definitions across multiple modules (`app_utils_steps.py`, `base_config_steps.py`,
      `datetime_utils_steps.py`, `elastic_adapter_steps.py`, `jwt_utils_steps.py`, `keycloak_adapter_steps.py`,
      `minio_adapter_steps.py`, `password_utils_steps.py`, `totp_utils_steps.py`)
    - Simplified `.env.test` configuration file structure
    - Enhanced code maintainability and reduced configuration complexity in test infrastructure
    - Improved developer experience with clearer configuration access patterns

#### Dependency Updates

- **Comprehensive Dependency Synchronization** - Updated multiple core dependencies to latest versions for improved
  security, performance, and bug fixes
    - Updated pydantic from 2.12.3 to 2.12.4 for enhanced data validation and performance improvements
    - Updated fakeredis from 2.32.0 to 2.32.1 for improved Redis mocking capabilities and bug fixes
    - Updated grpcio from 1.75.1 to 1.76.0 for enhanced gRPC framework capabilities and performance improvements
    - Updated grpcio-health-checking from 1.75.1 to 1.76.0 for improved health checking functionality
    - Updated confluent-kafka from 2.12.0 to 2.12.1 for enhanced Kafka messaging capabilities and bug fixes
    - Updated apscheduler from 3.11.0 to 3.11.1 for improved task scheduling capabilities and bug fixes
    - Updated aiomysql from 0.2.0 to 0.3.2 for enhanced async MySQL connectivity and performance improvements
    - Updated add-trailing-comma from 3.2.0 to 4.0.0 for improved code formatting capabilities
    - Updated ruff from 0.14.0 to 0.14.3 for enhanced linting capabilities and bug fixes
    - Updated types-cachetools from 6.2.0.20250827 to 6.2.0.20251022 for improved type stubs
    - Updated types-protobuf from 6.32.1.20250918 to 6.32.1.20251105 for enhanced Protocol Buffers type support
    - Updated types-regex from 2025.9.18.20250921 to 2025.11.3.20251106 for improved regex type hints
    - Updated mkdocs-material from 9.6.21 to 9.6.23 for enhanced documentation rendering and Material theme features

## [v3.14.1] - 2025-10-30

### Fixed

#### FastAPI Configuration Naming

- **ReDoc Configuration Field Name Correction** - Fixed typo in FastAPI configuration field name
    - Corrected `RE_DOCS_URL` to `RE_DOC_URL` in `FastAPIConfig` class to match FastAPI's actual parameter name
    - Updated `AppUtils.create_fastapi_app()` to use correct `redoc_url` parameter instead of `redocs_url`
    - Ensures proper ReDoc documentation endpoint configuration in FastAPI applications
    - Resolves potential configuration errors when setting up ReDoc documentation

### Security

#### OpenAPI Schema Exposure

- **OpenAPI Endpoint Disabled by Default** - Enhanced security by disabling OpenAPI schema endpoint by default
    - Changed `OPENAPI_URL` default value from `/openapi.json` to `None` in `FastAPIConfig` class
    - Prevents automatic exposure of API schema documentation in production environments
    - Applications must explicitly enable OpenAPI schema by setting `OPENAPI_URL` configuration value
    - Improves security posture by requiring opt-in for API documentation endpoints
    - Aligns with security best practices for production deployments

### Changed

#### Dependency Updates

- **Comprehensive Dependency Synchronization** - Updated multiple core dependencies to latest versions for improved
  security, performance, and bug fixes
    - Updated aiohttp from 3.13.1 to 3.13.2 for enhanced async HTTP client capabilities and bug fixes
    - Updated alembic from 1.17.0 to 1.17.1 for improved database migration tool capabilities
    - Updated elasticsearch from 9.1.1 to 9.2.0 for enhanced Elasticsearch connectivity and reliability
    - Updated fastapi from 0.120.0 to 0.120.2 for improved API framework stability and bug fixes
    - Updated python-dotenv from 1.1.1 to 1.2.1 for enhanced environment variable loading capabilities
    - Updated redis from 7.0.0 to 7.0.1 for improved Redis client reliability and performance
    - Updated rignore from 0.7.1 to 0.7.2 for enhanced ignore file handling
    - Updated sentry-sdk from 2.42.1 to 2.43.0 for improved error tracking and monitoring capabilities
    - Updated starlette from 0.48.0 to 0.49.1 for enhanced ASGI framework features and bug fixes
    - Updated temporalio from 1.18.1 to 1.18.2 for improved workflow orchestration capabilities
    - Updated virtualenv from 20.35.3 to 20.35.4 for enhanced virtual environment management

## [3.14.0] - 2025-10-26

### Added

#### gRPC Application Creation Utilities

- **gRPC App Creation** - Added comprehensive gRPC application creation utilities for both sync and async servers
    - Added `AppUtils.create_async_grpc_app()` method for async gRPC server creation with interceptor support
    - Added `AppUtils.create_grpc_app()` method for synchronous gRPC server creation
    - Implemented automatic setup of exception, tracing, and metric interceptors
    - Added `GrpcAPIUtils` class with setup methods for trace and metric interceptors for sync gRPC servers
    - Added `AsyncGrpcAPIUtils` class with setup methods for trace and metric interceptors for async gRPC servers
    - Integrated Prometheus metric collection with configurable HTTP server port
    - Enhanced optional import handling for gRPC dependencies with proper graceful degradation
    - Configured ThreadPoolExecutor with configurable worker count and server options
    - Support for custom interceptors and compression settings

#### Prometheus Metrics Support

- **Metric Collection** - Added Prometheus metrics integration for gRPC servers
    - Automatic metric interceptor setup when Prometheus is enabled in configuration
    - Configurable HTTP server for metrics endpoint exposure
    - Integrated metric collection for both sync and async gRPC servers
    - Enhanced observability with automatic Prometheus client initialization

### Changed

#### Kafka Producer Enhancements

- **Key Parameter Support** - Enhanced Kafka producer with proper key encoding support
    - Added optional `key` parameter to `KafkaProducerPort.produce()` method signature
    - Implemented proper UTF-8 encoding for message keys using `_pre_process_message()` helper
    - Ensures consistent handling of both string and bytes keys in message production
    - Improved key/value consistency in Kafka message production workflow

#### Cache Decorator Optimization

- **Lazy Import Optimization** - Optimized TTL cache decorator import strategy
    - Moved `cachetools.TTLCache` import inside the decorator function to prevent global import issues
    - Improved module initialization performance by avoiding heavy dependencies at import time
    - Maintained backward compatibility while improving startup time
    - Enhanced import cleanliness and reduced initialization overhead

### Fixed

#### Kafka Producer Key Processing

- **Key Encoding Fix** - Fixed issue where message keys were not being properly processed
    - Applied `_pre_process_message()` to key parameter in `produce()` method for proper encoding
    - Corrected key handling to match message value processing behavior
    - Resolved potential encoding errors when using string keys in Kafka message production
    - Enhanced BDD test coverage with proper key verification scenarios

#### Import Cleanup

- **Module Organization** - Improved import structure across multiple modules
    - Fixed unnecessary imports in Keycloak and MinIO adapters
    - Enhanced import cleanup in decorators module
    - Improved code organization and reduced import overhead

## [3.13.10] - 2025-10-20

### Changed

#### Dependency Updates

- **Comprehensive Dependency Synchronization** - Updated multiple core dependencies to latest versions for improved
  security and performance
    - Updated aiohttp from 3.13.0 to 3.13.1 for enhanced async HTTP client capabilities and bug fixes
    - Updated cryptography from 46.0.2 to 46.0.3 for improved cryptographic security and performance
    - Updated elastic-transport from 9.1.0 to 9.2.0 for enhanced Elasticsearch connectivity and reliability
    - Updated mkdocs-material from 9.6.21 to 9.6.22 for improved documentation rendering and Material theme features
    - Updated mkdocs-material from 9.6.21 to 9.6.22 for improved documentation rendering and Material theme features
    - Updated protobuf from 6.32.1 to 6.33.0 for enhanced Protocol Buffers support and performance
    - Updated pydantic from 2.12.2 to 2.12.3 for improved data validation and type safety
    - Updated pytokens from 0.1.10 to 0.2.0 for enhanced token processing capabilities
    - Updated ruff from 0.14.0 to 0.14.1 for improved linting capabilities and bug fixes
    - Updated wrapt from 1.17.3 to 2.0.0 for enhanced function wrapping capabilities

## [3.13.9] - 2025-10-15

### Improved

#### Elastic APM Client Initialization

- **Enhanced Client Reuse** - Improved Elastic APM client initialization to prevent duplicate client creation
    - Updated tracing decorators to use `elasticapm.get_client()` before creating new clients
    - Applied same pattern to gRPC server interceptors (both sync and async)
    - Prevents potential memory leaks and improves performance by reusing existing clients
    - Maintains backward compatibility while optimizing resource usage

## [3.13.8] - 2025-10-15

### Changed

#### Redis Configuration Refinements

- **Redis Cluster Parameter Standardization** - Aligned Redis cluster configuration with redis-py library standards
    - Replaced deprecated `skip_full_coverage_check` parameter with standard `require_full_coverage` parameter
    - Updated both synchronous and asynchronous Redis cluster adapters for compatibility with latest redis-py
    - Removed redundant `CLUSTER_SKIP_FULL_COVERAGE_CHECK` configuration field
    - Enhanced Redis cluster reliability with proper full coverage validation
    - Improved code maintainability by following redis-py best practices

#### Dependency Updates

- **Pydantic Version Update** - Updated Pydantic to version 2.12.2 for enhanced data validation
    - Improved validation performance and bug fixes

## [3.13.7] - 2025-10-13

### Changed

#### Dependency Updates

- **Core Dependencies** - Updated key dependencies to latest versions for improved security and performance
    - Updated cachetools from 6.2.0 to 6.2.1 for enhanced caching capabilities and performance improvements
    - Updated idna from 3.10 to 3.11 for improved internationalized domain name handling and security fixes

#### Configuration Improvements

- **Redis Mode Constants** - Standardized Redis mode constants to uppercase format for better consistency
    - Updated RedisMode enum values from lowercase to uppercase (`standalone` → `STANDALONE`, `sentinel` → `SENTINEL`,
      `cluster` → `CLUSTER`)
    - Enhanced configuration consistency across Redis deployment modes
    - Improved code readability and standardization

#### Development Workflow

- **Makefile Enhancement** - Updated dependency installation command for better package management
    - Changed `uv sync --extra dev --upgrade` to `uv sync --all-extras --group dev --upgrade`
    - Enhanced dependency resolution with comprehensive extra package installation
    - Improved development environment setup with better group-based dependency management

### Performance

- **Optimized Dependency Resolution** - Improved dependency installation and resolution performance
    - Enhanced UV package manager integration with latest dependency versions
    - Improved lock file generation and dependency resolution speed
    - Better memory usage during dependency installation and updates

## [3.13.6] - 2025-01-15

### Changed

#### Dependency Updates

- **Core Framework Updates** - Updated key dependencies to latest compatible versions for improved performance and
  security
    - Updated SQLAlchemy from >=2.0.43 to >=2.0.44 for enhanced ORM functionality and performance improvements
    - Updated FastAPI from >=0.118.2 to >=0.119.0 for improved web framework capabilities and bug fixes
    - Updated Confluent Kafka from >=2.12.0 to latest stable version for enhanced messaging capabilities and improved
      reliability

### Performance

- **Optimized Dependency Resolution** - Improved dependency resolution and installation performance
    - Enhanced UV package manager integration with latest dependency versions
    - Improved lock file generation and dependency resolution speed
    - Better memory usage during dependency installation and updates

## [3.13.5] - 2025-10-08

### Changed

#### Dependency Updates

- **Comprehensive Dependency Synchronization** - Updated all dependencies to latest compatible versions for improved
  security and performance
    - Updated Pydantic from 2.11.10 to 2.12.0 for enhanced data validation and performance improvements
    - Updated Pydantic Core from 2.33.2 to 2.41.1 for improved core functionality and performance
    - Updated FastAPI from 0.118.0 to 0.118.1 for enhanced web framework capabilities and bug fixes
    - Updated Fakeredis from 2.31.3 to 2.32.0 for improved Redis mocking capabilities
    - Updated Ruff from 0.13.3 to 0.14.0 for enhanced linting capabilities and Python 3.13 support
    - Updated Testcontainers from 4.13.1 to 4.13.2 for improved container testing support

#### Test Environment Updates

- **Docker Image Updates** - Updated test container images for improved test reliability and compatibility
    - Updated Redis test image from 8.2.1-alpine to 8.2.2-alpine for enhanced stability
    - Updated Elasticsearch test image from 9.1.4 to 9.1.5 for improved search functionality

#### Type Safety Improvements

- **SQLAlchemy Adapter Typing** - Enhanced type safety in SQLAlchemy adapter base model
    - Improved generic type handling in SQLAlchemy adapter base classes
    - Enhanced type inference and IDE support for database operations
    - Better type safety for entity operations and query results

#### Temporal Workflow Enhancements

- **Custom Workflow ID Support** - Added support for custom workflow IDs in Temporal scheduled workflows
    - Enhanced Temporal workflow scheduling with configurable workflow IDs
    - Improved workflow identification and management capabilities
    - Better integration with existing workflow orchestration patterns

#### CI/CD Infrastructure

- **GitHub Actions Updates** - Updated UV setup action for improved CI/CD reliability
    - Updated astral-sh/setup-uv from version 6 to 7 across all workflows
    - Enhanced dependency management and build performance
    - Improved compatibility with latest UV features

### Performance

- **Optimized Dependency Resolution** - Improved dependency resolution and installation performance
    - Enhanced UV package manager integration with latest features
    - Improved lock file generation and dependency resolution speed
    - Better memory usage during dependency installation and updates

### Security

- **Enhanced Security Posture** - Multiple security updates across dependencies
    - Updated dependencies include latest security patches and vulnerability fixes
    - Improved overall application security through latest package versions
    - Enhanced cryptographic libraries and security-related packages

## [3.13.4] - 2025-10-07

### Changed

#### Dependency Updates

- **Comprehensive Dependency Synchronization** - Updated all dependencies to latest compatible versions for improved
  security and performance
    - Updated Pydantic from 2.11.9 to 2.11.10 for enhanced data validation and performance improvements
    - Updated Requests from 2.32.4 to 2.32.5 for improved HTTP client capabilities and security fixes
    - Updated Elastic APM from 6.23.0 to 6.24.0 for enhanced application performance monitoring
    - Updated Redis client from 6.2.0 to 6.4.0 with hiredis extension for improved performance
    - Updated Sentry SDK from 2.39.0 to 2.40.0 for better error tracking and monitoring capabilities
    - Updated SQLAlchemy from 2.0.41 to 2.0.43 for enhanced ORM functionality and performance
    - Updated StarRocks driver from 1.2.2 to 1.2.3 for improved database connectivity
    - Updated Temporalio from 1.18.0 to 1.18.1 for enhanced workflow orchestration capabilities

- **Development Tools Enhancement** - Updated development and build infrastructure for improved developer experience
    - Updated Bandit from 1.7.8 to 1.8.6 for enhanced security vulnerability scanning
    - Updated Pre-commit hooks from 4.6.0 to 6.0.0 for improved code quality enforcement
    - Updated Pre-commit from 3.8.0 to 4.3.0 for better hook management and performance
    - Updated Ruff from 0.13.2 to 0.13.3 for enhanced linting capabilities and Python 3.13 support
    - Updated Validate-pyproject from 0.18 to 0.24.1 for improved project configuration validation
    - Updated PyMdown Extensions from 10.14.3 to 10.16.1 for enhanced Markdown processing

#### Testing Infrastructure

- **Kafka Test Environment Update** - Updated Kafka test container image for improved test reliability
    - Updated Kafka test image from confluentinc/cp-kafka:7.4.10 to 7.9.3
    - Enhanced test environment compatibility with latest Kafka features
    - Improved test stability and performance in CI/CD environments

#### Development Workflow Improvements

- **Enhanced Dependency Management** - Improved Makefile targets for better dependency management
    - Added `--upgrade` flag to `install` and `install-dev` targets for automatic dependency updates
    - Added new `update-all` target for aggressive dependency updates with comprehensive upgrade process
    - Enhanced dependency synchronization between pyproject.toml and uv.lock files
    - Improved developer experience with streamlined dependency update workflows

#### Development Environment

- **Cursor IDE Rules Enhancement** - Updated Cursor IDE rules for improved development experience
    - Enhanced code generation guidelines and architectural patterns
    - Improved development workflow documentation and best practices
    - Updated coding standards and quality enforcement rules

#### Configuration Management

- **Comprehensive .env.example Update** - Synchronized environment configuration template with all available config
  options
    - Added Language configuration support with Persian (FA) language setting
    - Enhanced Elasticsearch configuration with complete API key, SSL, and sniffing options
    - Expanded Kafka configuration with SSL settings, compression, batch processing, and transaction support
    - Added Redis cluster and sentinel mode configurations with connection pooling settings
    - Included Temporal workflow orchestration configuration (completely new section)
    - Added Parsian Shaparak payment gateway configuration (completely new section)
    - Enhanced authentication configuration with comprehensive TOTP, password policies, and token security features
    - Added separate SQLite and StarRocks SQLAlchemy configurations for different database types
    - Improved existing configurations with missing fields and proper default values
    - Organized configuration sections with clear headers and proper data type formatting
    - Provided comprehensive reference for all available ArchiPy configuration options

### Performance

- **Optimized Dependency Resolution** - Improved dependency resolution and installation performance
    - Enhanced UV package manager integration with latest features
    - Improved lock file generation and dependency resolution speed
    - Better memory usage during dependency installation and updates

### Security

- **Enhanced Security Posture** - Multiple security updates across dependencies
    - Updated dependencies include latest security patches and vulnerability fixes
    - Improved overall application security through latest package versions
    - Enhanced cryptographic libraries and security-related packages

## [3.13.3]

### Changed

#### Documentation Examples - Complete Python 3.13 & Best Practices Update

- **Comprehensive Example Documentation Refactor** - Updated all 17 example files to follow modern Python 3.13 standards
  and ArchiPy best practices
    - Updated all type hints to Python 3.13 syntax (`|` for unions, lowercase built-ins, `type` instead of `Type`)
    - Replaced `Union[X, Y]` with `X | Y` throughout all examples
    - Replaced `Optional[X]` with `X | None` throughout all examples
    - Changed `List`, `Dict` to lowercase `list`, `dict` consistently
    - Removed `from typing import Union, Optional` in favor of native syntax

- **Exception Handling Standardization** - Implemented proper exception handling patterns across all examples
    - Added `try-except-else` pattern with explicit `return` statements in `else` blocks
    - Ensured all exceptions use `raise ... from e` for proper error chaining
    - Removed operation/query messages from exception constructors (per workspace rules)
    - Replaced generic `Exception`, `ValueError` with specific ArchiPy error types
    - Added comprehensive error handling examples in all adapter documentation

- **Logging Standardization** - Replaced all print statements with proper logging
    - Added `logger = logging.getLogger(__name__)` to all example files
    - Replaced all `print()` statements with appropriate `logger.info()`, `logger.error()`, etc.
    - Implemented consistent logging levels and informative messages
    - Added logging configuration examples in code snippets

- **Documentation Structure Improvements** - Enhanced navigation and cross-referencing
    - Added "See Also" sections to all adapter examples
    - Linked adapter examples to corresponding BDD test `.feature` files
    - Added cross-references to error handling, configuration, and API documentation
    - Improved code explanations with detailed docstrings
    - Added warnings for common pitfalls and best practices

- **New Complete Examples Added**
    - Email adapter with FastAPI integration and comprehensive error handling
    - SQLite adapter with async operations and context managers
    - StarRocks adapter with analytical query patterns and batch operations
    - Metaclasses with singleton pattern, thread safety, and best practices
    - Parsian payment gateway with complete payment flow and error recovery
    - Temporal workflow orchestration with atomic activities and worker management

- **Code Quality Improvements**
    - All examples now syntactically correct with proper indentation
    - Fixed indentation errors in `error_handling.md`
    - Added security warnings for sensitive data (passwords in `.env` files)
    - Improved FastAPI integration examples with proper dependency injection
    - Enhanced async/await patterns with proper error handling

## [3.13.2]

### Changed

#### Documentation Infrastructure

- **MkDocs Configuration Reorganization** - Restructured MkDocs configuration for improved build performance and
  flexibility
    - Moved `mkdocs.yml` from project root to `docs/` directory for better organization
    - Added `docs_dir: .` and `site_dir: ../site` configuration for proper directory mapping
    - Created `docs/mkdocs-fast.yml` for fast local development builds (10-20s)
    - Created `docs/mkdocs-full.yml` for complete production builds (2-5min)
    - Implemented configuration inheritance using `INHERIT` directive to reduce duplication
    - Enhanced main `mkdocs.yml` with performance optimizations and balanced settings

#### Documentation Performance

- **MkDocs Build Optimization** - Significantly improved documentation build performance
    - Disabled source code display by default for faster rendering (`show_source: false`)
    - Simplified object paths for reduced processing time (`show_object_full_path: false`)
    - Disabled submodule auto-expansion for improved performance (`show_submodules: false`)
    - Disabled base class display to reduce content size (`show_bases: false`)
    - Enabled summary mode for faster documentation generation (`summary: true`)
    - Excluded undocumented items from generation (`show_if_no_docstring: false`)
    - Disabled inherited member display for major performance gain (`inherited_members: false`)
    - Added environment variable control for mkdocstrings (`ENABLE_MKDOCSTRINGS`)

#### Documentation Features

- **Enhanced Navigation** - Improved user experience with modern Material theme features
    - Added instant prefetch for faster page navigation (`navigation.instant.prefetch`)
    - Added loading progress indicator (`navigation.instant.progress`)
    - Maintained existing features: instant loading, tracking, tabs, sections, ToC, code copy

#### CI/CD Pipeline

- **GitHub Actions Workflow Update** - Enhanced documentation deployment workflow
    - Updated deploy workflow to use `docs/mkdocs-full.yml` for production builds
    - Maintained full feature set for GitHub Pages deployment
    - Improved build reliability with explicit configuration file reference

#### ReadTheDocs Configuration

- **Configuration Update** - Updated ReadTheDocs configuration for new structure
    - Updated `mkdocs.configuration` path to `docs/mkdocs.yml`
    - Maintained compatibility with ReadTheDocs build system
    - Ensured proper documentation generation on ReadTheDocs platform

#### Makefile Enhancements

- **Documentation Build Commands** - Added comprehensive make targets for all build modes
    - Added `docs-serve` for balanced mode development (default)
    - Added `docs-serve-fast` for quick iterations with fast builds
    - Added `docs-serve-no-api` for fastest builds without API generation
    - Added `docs-build` for balanced builds
    - Added `docs-build-fast` for fast configuration builds
    - Added `docs-build-full` for production builds with all features
    - Updated `docs-deploy` to use full configuration for production deployment

#### Documentation Content

- **Usage Guide Restructuring** - Completely rewrote usage documentation for better onboarding
    - Restructured as quick-start guide focusing on 5-minute setup
    - Added minimal working FastAPI example for rapid prototyping
    - Added clear next steps directing users to Architecture Guide for production patterns
    - Reorganized content into Quick Start, Next Steps, Key Concepts, and Production-Ready Structure sections
    - Enhanced best practices section with clear, actionable guidelines
    - Improved navigation with links to detailed guides and examples
    - Emphasized domain-driven organization and API versioning
    - Added Command/Query/Response DTO pattern references
    - Streamlined content to focus on getting started quickly while pointing to comprehensive resources

- **Architecture Guide Expansion** - Enhanced architecture documentation with comprehensive real-world example
    - Added complete end-to-end user management system example
    - Demonstrated domain-driven design with clear layer separation
    - Included API versioning patterns (`/api/v1/`, `/api/v2/`)
    - Showcased CQRS-inspired DTO naming conventions (InputDTO, CommandDTO, QueryDTO, ResponseDTO, OutputDTO)
    - Illustrated service, logic, and repository layer interactions
    - Provided complete working code for models, DTOs, errors, repositories, logic, and services
    - Demonstrated domain-specific adapters (`UserDBAdapter`, `UserCacheAdapter`)
    - Highlighted scalability, testability, and maintainability benefits
    - Emphasized framework-agnostic business logic design
    - Showed clear separation of concerns at each architectural layer

### Performance

- **Optimized Documentation Build Times** - Achieved significant performance improvements across all build modes
    - Fast mode: 10-20s builds for rapid local development iteration
    - Balanced mode: 30-60s builds for regular development work
    - Full mode: 2-5min builds with all features for production deployment
    - Reduced memory usage through content filtering and summary modes
    - Improved developer experience with faster feedback loops

### Developer Experience

- **Improved Documentation Workflow** - Enhanced documentation development and deployment experience
    - Clear separation of development and production configurations
    - Multiple build modes for different use cases and performance requirements
    - Better local development experience with fast rebuild times
    - Streamlined deployment process with optimized production builds
    - Consistent configuration management through inheritance

## [3.13.1] - 2025-09-30

### Changed

#### Dependency Updates

- **Core Dependencies** - Updated multiple core dependencies for improved security and performance
    - Updated Pydantic from 2.11.7 to 2.11.9 for enhanced data validation and performance improvements
    - Updated Pydantic Settings from 2.10.1 to 2.11.0 for better configuration management capabilities
    - Updated PyYAML from 6.0.2 to 6.0.3 for enhanced YAML processing and security fixes
    - Updated Sentry SDK from 2.36.0 to 2.39.0 for improved error tracking and monitoring
    - Updated Ruff from 0.13.1 to 0.13.2 for enhanced code linting and formatting capabilities

- **Parser and Processing Libraries** - Enhanced parsing and processing capabilities
    - Updated pycparser from 2.22 to 2.23 for improved C code parsing
    - Updated ruamel.yaml.clib from 0.2.12 to 0.2.14 for better YAML processing performance
    - Added pytokens 0.1.10 for enhanced token processing capabilities

- **Build and Development Tools** - Updated development and build infrastructure
    - Updated Starlette from 0.47.3 to 0.48.0 for improved ASGI framework support
    - Updated StarRocks driver from 1.2.2 to 1.2.3 for enhanced database connectivity
    - Updated Temporalio from 1.12.0 to 1.18.0 for improved workflow orchestration capabilities
    - Updated Testcontainers from 4.12.0 to 4.13.1 for better container testing support
    - Updated Typer from 0.17.3 to 0.19.2 for enhanced CLI development features
    - Updated Uvicorn from 0.35.0 to 0.37.0 for improved ASGI server performance
    - Updated Zeep from 4.3.1 to 4.3.2 for better SOAP/WSDL client functionality

- **Type Checking and Development** - Enhanced type checking and development experience
    - Updated types-grpcio from 1.0.0.20250703 to 1.0.0.20250914 for better gRPC type support
    - Updated types-protobuf from 6.30.2.20250822 to 6.32.1.20250918 for improved Protocol Buffers typing
    - Updated types-pymysql from 1.1.0.20250822 to 1.1.0.20250916 for enhanced MySQL type hints
    - Updated types-regex from 2025.9.1.20250903 to 2025.9.18.20250921 for better regex type support
    - Updated types-requests from 2.32.4.20250809 to 2.32.4.20250913 for improved HTTP client typing

- **Infrastructure and Utility Libraries** - Updated supporting infrastructure
    - Updated rich-toolkit from 0.15.0 to 0.15.1 for enhanced terminal output formatting
    - Updated numerous additional dependencies for security patches and performance improvements

### Security

- **Enhanced Security Posture** - Multiple security updates across dependencies
    - Updated dependencies include security patches and vulnerability fixes
    - Improved overall application security through latest package versions
    - Enhanced cryptographic libraries and security-related packages

### Performance

- **Optimized Dependencies** - Performance improvements through dependency updates
    - Enhanced parsing and processing performance with updated libraries
    - Improved build and development tool performance
    - Better memory usage and execution speed through optimized package versions

## [3.13.0] - 2025-09-21

### Added

#### Redis Cluster and Sentinel Support

- **Redis Cluster Integration** - Added comprehensive Redis Cluster support for distributed caching and high
  availability
    - Added `CLUSTER` mode to RedisMode enum for cluster deployment configuration
    - Implemented cluster-specific methods: `cluster_info()`, `cluster_nodes()`, `cluster_slots()`, and
      `cluster_keyslot()`
    - Added cluster configuration options: `CLUSTER_NODES`, `CLUSTER_REQUIRE_FULL_COVERAGE`,
      `CLUSTER_READ_FROM_REPLICAS`
    - Enhanced connection pooling with `MAX_CONNECTIONS` and retry mechanisms for cluster nodes
    - Improved error handling for cluster-specific operations and node failover scenarios

- **Redis Sentinel Integration** - Added Redis Sentinel support for automatic failover and high availability
    - Added `SENTINEL` mode to RedisMode enum for sentinel deployment configuration
    - Implemented sentinel-specific configuration: `SENTINEL_NODES`, `SENTINEL_SERVICE_NAME`, `SENTINEL_SOCKET_TIMEOUT`
    - Enhanced master/slave discovery and automatic failover through Sentinel coordination
    - Added robust connection management for Sentinel-monitored Redis deployments

#### Enhanced Redis Configuration

- **Flexible Deployment Modes** - Unified configuration system supporting standalone, sentinel, and cluster modes
    - Added `RedisMode` enum with `STANDALONE`, `SENTINEL`, and `CLUSTER` options
    - Enhanced configuration validation with mode-specific parameter validation
    - Improved connection timeout settings: `SOCKET_CONNECT_TIMEOUT` and `SOCKET_TIMEOUT`
    - Added comprehensive error handling for mismatched configuration parameters

#### Testing and Mocking Improvements

- **Enhanced Mock Support** - Extended Redis mocking capabilities for all deployment modes
    - Updated mock implementations to support cluster and sentinel operation simulation
    - Enhanced test coverage for cluster-specific methods and sentinel failover scenarios
    - Improved test configuration with mode-specific environment variables

### Changed

#### Error Handling Enhancements

- **Improved Error Utilities** - Enhanced error handling for Redis connection and operation failures
    - Updated error utilities to handle cluster and sentinel specific errors
    - Improved error messaging for connection failures across different Redis modes

### Dependencies

- **Redis Client Updates** - Updated Redis client dependencies to support cluster and sentinel operations
    - Enhanced Redis protocol support for cluster and sentinel deployments
    - Improved connection handling for distributed Redis architectures

## [3.12.0] - 2025-09-21

### Added

#### Temporal Workflow Scheduling Enhancement

- **Schedule Management Methods** - Added comprehensive schedule management capabilities to Temporal adapter
    - Added `create_schedule()` method for creating workflow schedules with configurable specifications
    - Added `stop_schedule()` method for deleting and stopping existing schedules
    - Enhanced Temporal integration with ScheduleActionStartWorkflow support
    - Improved workflow scheduling capabilities with ScheduleSpec configuration
    - Enhanced temporal workflow orchestration with automated scheduling support

#### Performance Optimization

- **Redis Hiredis Extension** - Enhanced Redis performance with native C extension support
    - Updated Redis dependency to include hiredis extension for improved performance
    - Added high-performance Redis protocol parsing with native C implementation
    - Enhanced Redis connection speed and throughput for better scalability
    - Improved Redis adapter performance with reduced memory usage and faster operations

### Changed

#### CI/CD Infrastructure

- **GitHub Actions Updates** - Updated workflow dependencies for improved reliability
    - Updated tj-actions/changed-files from version 46 to 47 for enhanced file change detection
    - Improved CI/CD pipeline reliability with latest action features
    - Enhanced workflow performance with optimized file change tracking

## [3.11.1] - 2025-09-06

### Added

#### Temporal Worker Management Enhancement

- **Wait Until Stopped Method** - Added `wait_until_stopped()` method to Temporal WorkerHandle class
    - Enhanced worker lifecycle management with ability to wait for worker completion
    - Improved synchronization capabilities for worker shutdown scenarios
    - Better control over worker background task lifecycle in long-running applications
    - Enhanced debugging and monitoring capabilities for Temporal worker operations

### Changed

#### CI/CD Infrastructure

- **GitHub Actions Updates** - Updated Python setup action across all workflows for improved CI/CD reliability
    - Updated actions/setup-python from version 5 to 6 in all GitHub Actions workflows
    - Enhanced Python environment setup with latest action features and security improvements
    - Improved workflow performance and compatibility with latest GitHub Actions infrastructure
    - Updated workflows: deploy-docs.yml, lint.yml, publish.yml, and tests.yml

#### Documentation

- **Documentation Build Fixes** - Resolved documentation generation and deployment issues
    - Fixed documentation builds for improved reliability and consistency
    - Enhanced documentation index organization and navigation
    - Improved documentation deployment pipeline stability

## [3.11.0] - 2025-09-04

### Added

#### Temporal Workflow Orchestration

- **Comprehensive Temporal Integration** - Added complete Temporal workflow orchestration support
    - Full Temporal integration with atomic transaction support for activities
    - Comprehensive configuration management for Temporal workflow execution
    - Clean architecture separation between workflow orchestration and activity execution
    - Support for distributed workflow patterns with reliable activity execution
    - Enhanced error handling and transaction management for Temporal workflows

### Changed

#### Documentation Assets

- **Logo Path Update** - Updated logo path reference for improved asset management
    - Enhanced documentation asset organization
    - Improved logo accessibility and display consistency

## [3.10.0] - 2025-09-04

### Added

#### gRPC Interceptor Enhancements

- **Sentry Support in gRPC Trace Interceptors** - Enhanced gRPC trace interceptors with dual APM support
    - Added Sentry span creation for both sync and async gRPC client interceptors
    - Added Sentry transaction creation for both sync and async gRPC server interceptors
    - Maintained backward compatibility with existing Elastic APM functionality
    - Support for simultaneous Elastic APM and Sentry tracing in gRPC services
    - Proper error handling and span status management for both APM systems
    - Configuration-driven tracing with graceful degradation when APM systems are unavailable

## [3.9.0] - 2025-09-04

### Added

#### Tracing Decorators

- **Pure Python APM Tracing** - Added `@capture_transaction` and `@capture_span` decorators for pure Python applications
    - `@capture_transaction` decorator for top-level transaction tracing without FastAPI/gRPC dependencies
    - `@capture_span` decorator for nested span tracking within existing transactions
    - Seamless integration with existing Sentry and Elastic APM configuration system
    - Conditional tracing based on `config.SENTRY.IS_ENABLED` and `config.ELASTIC_APM.IS_ENABLED` settings
    - Proper error handling and graceful fallbacks when APM libraries are unavailable
    - Automatic initialization of Sentry with full config parameters for transactions
    - Uses existing APM clients for spans to work within transaction context

#### Developer Experience

- **Comprehensive Decorator Exports** - Enhanced `archipy.helpers.decorators` module accessibility
    - Exported all 17 decorators in `__init__.py` for easy discovery and import
    - Includes tracing, caching, retry, database atomic operations, deprecation, and utility decorators
    - Simplified import syntax for all decorator functionality

## [3.8.1] - 2025-09-04

### Changed

#### Dependency Updates

- **Elasticsearch Version Bump** - Updated Elasticsearch Docker image from 9.1.2 to 9.1.3 in test configuration
    - Enhanced test reliability with latest Elasticsearch stable version
    - Improved test container compatibility and performance

#### Code Quality Improvements

- **Enhanced Keycloak Utils Type Safety** - Improved type handling in Keycloak utilities for gRPC metadata
    - Fixed handling of both bytes and string metadata values in gRPC authentication
    - Enhanced type conversion safety with proper string/bytes compatibility
    - Improved authentication reliability across different gRPC implementations
- **MyPy Configuration Enhancements** - Expanded MyPy overrides for better type checking coverage
    - Added comprehensive overrides for Keycloak utilities, MinIO, Kafka, and payment gateway adapters
    - Enhanced type checking for optional imports with proper type placeholders
    - Improved development experience with more accurate type checking

#### Library Updates

- **Development Tools** - Updated multiple development dependencies for improved tooling
    - Updated Ruff from 0.7.4 to 0.12.11 for enhanced linting capabilities
    - Updated various type stubs packages for better IDE support and type checking
    - Enhanced MkDocs Material theme from 9.6.7 to 9.6.18 for improved documentation
- **Core Dependencies** - Updated runtime dependencies for better performance and security
    - Updated fakeredis from 2.30.1 to 2.31.1 for improved Redis mocking
    - Updated sentry-sdk from 2.33.0 to 2.36.0 for better error tracking
    - Updated pymysql from 1.1.1 to 1.1.2 for enhanced MySQL compatibility
    - Updated behave from 1.3.1 to 1.3.2 for improved BDD testing

#### Documentation and Code Structure

- **Enhanced CLAUDE.md** - Comprehensive documentation improvements for Claude Code integration
    - Added detailed architecture overview with module descriptions
    - Enhanced code style guidelines with Python 3.13+ requirements
    - Improved command reference with complete development workflow
    - Added comprehensive MyPy configuration documentation

### Bug Fixes

#### Type Safety

- **Optional Import Handling** - Fixed type assignments for optional gRPC imports
    - Resolved type compatibility issues when gRPC dependencies are not available
    - Enhanced graceful degradation with proper type placeholders
    - Improved development experience with better error messages

#### Configuration

- **Workflow Permissions** - Fixed potential security issues in GitHub Actions workflows
    - Added proper permissions configuration to prevent unauthorized access
    - Enhanced CI/CD security with explicit permission declarations
    - Resolved code scanning alerts for workflow security best practices

## [3.8.0] - 2025-08-21

### Changed

#### Build System Migration

- **Poetry to UV Migration** - Migrated from Poetry to UV for improved performance and modern toolchain
    - Replaced Poetry with UV for dependency management and virtual environment handling
    - Updated all GitHub Actions workflows to use `astral-sh/setup-uv@v4`
    - Converted `pyproject.toml` to use standard `[project]` format with UV-compatible optional dependencies
    - Updated Makefile commands to use UV equivalents (`uv sync`, `uv run`, `uv build`)
    - Updated pre-commit hooks to use UV for tool execution
    - Migrated from Poetry build backend to Hatchling for better flexibility
    - Updated all documentation to reflect UV usage instead of Poetry
    - Significant performance improvements in dependency resolution and installation

#### Python 3.13 Compatibility

- **Modern Type Hints** - Updated codebase to use Python 3.13 generic syntax and modern type annotations
    - Migrated from `Union[T, None]` to `T | None` syntax throughout the codebase
    - Updated Generic syntax to use modern Python 3.13 patterns (UP046, UP047)
    - Enhanced type safety with improved generic type operations and Comparable protocol
    - Fixed type assignment issues in error classes and DTO implementations
    - Added comprehensive mypy overrides for flexible data dictionary assignments

#### Code Quality Improvements

- **Linting and Type Checking** - Resolved all ruff and mypy issues across the codebase
    - Fixed type annotations and imports across configs, models, and decorators
    - Added missing error classes (DeadlineExceededError, DeprecationError)
    - Enhanced SQLAlchemy column type compatibility with mapped_column
    - Resolved import conflicts and improved code organization
    - Added missing docstrings and type hints for better code documentation
- **Test Infrastructure Cleanup** - Streamlined test helper functions for better maintainability
    - Removed unused imports and dependencies from test_helpers.py
    - Cleaned up test infrastructure to reduce code duplication
    - Improved test execution efficiency and maintainability

#### CI/CD Enhancements

- **GitHub Actions Updates** - Updated all GitHub Actions workflows to latest versions
    - Bumped actions/setup-python from 4 to 5 for improved Python support
    - Bumped actions/cache from 3 to 4 for enhanced caching capabilities
    - Bumped actions/checkout from 4 to 5 for better repository access
    - Improved workflow reliability and performance across all CI/CD pipelines

#### Testing Framework Updates

- **Behave Version Upgrade** - Updated Behave testing framework to version 1.3.1
    - Enhanced test execution capabilities with latest Behave features
    - Improved test reliability and performance across all test suites
    - Better compatibility with modern Python development practices
- **MyPy Version Upgrade** - Updated MyPy type checker to version 1.17.1
    - Enhanced type checking capabilities with latest MyPy features
    - Improved type safety and error detection across the codebase
    - Better support for Python 3.13 type annotations and modern type patterns

### Bug Fixes

#### Type System

- **Generic Type Operations** - Fixed generic type operations with Comparable protocol in DTO classes
- **SQLAlchemy Compatibility** - Resolved SQLAlchemy column type compatibility issues with mapped_column
- **Error Class Initialization** - Fixed type assignment issues in error classes for better type safety

#### Configuration

- **Type Annotations** - Resolved type annotation and inheritance issues in configuration classes
- **Validator Documentation** - Added missing docstrings to validators for better code documentation

### Known Issues

- **Remaining Linting Issues** - Some minor linting issues remain that are planned for future releases
    - 13 ANN401 (any-type) violations for flexible data handling
    - 11 ANN201 (missing return type annotations) for public functions
    - 8 D415 (missing terminal punctuation) for docstrings
    - These issues are intentionally allowed for specific use cases and will be addressed incrementally

## [3.7.0] - 2025-08-16

### New Features

#### Elasticsearch Index Management

- **Index Existence Check** - Added `index_exists` method to Elasticsearch adapters for improved index management
    - New `index_exists()` method in both synchronous and asynchronous Elasticsearch ports
    - Enhanced index lifecycle management with proper existence validation
    - Improved error handling and index operation safety
    - Better support for index-dependent operations and workflows

#### CI/CD Pipeline Enhancement

- **Dedicated Test Workflow** - Implemented comprehensive CI/CD pipeline for automated testing
    - Added dedicated GitHub Actions workflow for Behave BDD tests
    - Automated test execution on push to main branch and pull requests
    - Python 3.13 matrix testing with Poetry dependency management
    - Enhanced test reliability and continuous integration capabilities

### Improvements

#### Testing Framework

- **Kafka Test Reliability** - Enhanced Kafka adapter tests with retry mechanism for improved stability
    - Implemented retry logic for Kafka connection tests to handle transient network issues
    - Improved test reliability in CI/CD environments with better error handling
    - Enhanced test coverage for Kafka adapter functionality

#### Configuration Management

- **PostgreSQL DSN Type Safety** - Fixed PostgresDsn type instantiation for improved configuration validation
    - Corrected PostgresDsn type handling in configuration templates
    - Enhanced type safety for database connection string validation
    - Improved configuration error handling and validation

#### Development Tools

- **Dependency Updates** - Updated development dependencies for improved tooling and security
    - Enhanced Poetry dependency management with latest package versions
    - Improved development environment setup and tooling
    - Better compatibility with Python 3.13 and modern development practices

### Bug Fixes

#### Test Infrastructure

- **Image Version Compatibility** - Fixed test container image versions for improved test reliability
    - Updated Elasticsearch, Keycloak, and Kafka test container images
    - Resolved test environment compatibility issues
    - Enhanced test stability across different environments

#### Error Handling

- **Exception Utility Assertions** - Fixed error assertion logic in exception utilities
    - Corrected error handling in test scenarios for better validation
    - Improved error message consistency and debugging capabilities

### Dependencies

- **Development Tools** - Updated development dependencies for improved tooling and security
- **Test Containers** - Enhanced test container configurations for better test reliability
- **CI/CD Tools** - Improved GitHub Actions workflow for automated testing

### Community Contributions

- **@heysaeid** - Fixed PostgresDsn type instantiation for improved configuration validation
- **@negatic** - Enhanced Kafka adapter tests with retry mechanism and improved test infrastructure
- **@s.kazemi** - Added index_exists method to Elasticsearch adapters and implemented CI/CD test workflow

## [3.6.1] - 2025-08-11

### New Features

#### Security Scanning Integration

- **Bandit Security Tool** - Added comprehensive security vulnerability scanning to the development workflow
    - Integrated Bandit 1.7.8 for automated security analysis of Python code
    - Added security scanning to CI/CD pipeline with configurable rules and exclusions
    - Enhanced security posture with automated detection of common security issues
    - Improved code quality through proactive security vulnerability identification

#### Enhanced Testing Framework

- **Behave 1.3.0 Upgrade** - Updated BDD testing framework to latest version with improved async support
    - Enhanced async test handling capabilities for better performance and reliability
    - Improved test execution efficiency with optimized async context management
    - Streamlined test infrastructure with cleaner step definitions and scenario management
    - Enhanced test coverage and reliability across all adapter test suites

### Improvements

#### SQLAlchemy Type Safety

- **Generic TypeVar Support** - Enhanced SQLAlchemy adapters with improved generic type preservation
    - Added TypeVar support to preserve concrete entity types in adapter operations
    - Improved type safety for database operations with better generic type handling
    - Enhanced IDE support and type checking for database adapter usage
    - Maintained backward compatibility while improving type inference capabilities

#### Test Infrastructure

- **Streamlined Test Helpers** - Refactored and optimized test infrastructure for better maintainability
    - Removed redundant test helper functions to reduce code duplication
    - Enhanced step definitions with cleaner, more focused implementations
    - Improved test scenario context management for better test isolation
    - Optimized test execution with reduced overhead and improved performance

### Code Quality

#### Security Enhancements

- **Automated Security Checks** - Integrated security scanning into development workflow
    - Added Bandit configuration with customizable security rules and exclusions
    - Enhanced CI/CD pipeline with automated security vulnerability detection
    - Improved security posture through proactive code analysis
    - Standardized security practices across development team

#### Testing Improvements

- **Enhanced Test Coverage** - Improved test reliability and maintainability
    - Updated all adapter test suites to work with Behave 1.3.0
    - Streamlined test step definitions for better readability and maintenance
    - Enhanced test context management for improved test isolation
    - Optimized test execution performance and reliability

### Dependencies

- **Security Tools** - Added Bandit 1.7.8 for automated security scanning
- **Testing Framework** - Updated Behave to version 1.3.0 for improved async support
- **Development Tools** - Enhanced development workflow with security and testing improvements

### Community Contributions

- **@younesious** - Enhanced SQLAlchemy adapters with generic TypeVar support for improved type safety
- **@itsnegaar** - Upgraded Behave testing framework to version 1.3.0 with enhanced async support

## [3.6.0] - 2025-07-29

### New Features

#### gRPC Exception Interceptor System

- **Centralized Exception Handling** - Implemented comprehensive gRPC server exception interceptors for both synchronous
  and asynchronous operations
    - Added `GrpcServerExceptionInterceptor` for synchronous gRPC services with automatic exception conversion
    - Added `AsyncGrpcServerExceptionInterceptor` for asynchronous gRPC services with async exception handling
    - Eliminated the need for repetitive try-catch blocks in individual gRPC service methods
    - Automatic conversion of exceptions to appropriate gRPC error responses with proper status codes

#### Enhanced Error Handling

- **Pydantic Validation Error Handling** - Integrated automatic Pydantic validation error processing in gRPC
  interceptors
    - Automatic conversion of ValidationError to InvalidArgumentError with detailed error information
    - Structured validation error formatting with field-level error details
    - Enhanced debugging capabilities with comprehensive validation error reporting

#### Language Configuration System

- **Global Language Configuration** - Added LANGUAGE configuration to BaseConfig for consistent language handling
    - Introduced LANGUAGE attribute in BaseConfig with default Persian (FA) language support
    - Standardized language type constants to uppercase for ISO compliance
    - Improved language handling across error messages and user interfaces

### Improvements

#### gRPC Status Code Management

- **Enhanced Status Code Handling** - Improved gRPC status code conversion and management in BaseError
    - Added static method for converting integer status codes to gRPC StatusCode enums
    - Enhanced metadata handling in gRPC abort methods with conditional additional data inclusion
    - Refined type hints for context parameters in abort methods for better clarity
    - Improved error context preservation and debugging capabilities

#### Error System Refactoring

- **Optional Language Parameters** - Refactored error handling classes to use optional language parameters
    - Removed mandatory language parameter requirements for improved flexibility
    - Enhanced error initialization with automatic language detection from global configuration
    - Improved error message consistency and localization support
    - Maintained backward compatibility while improving developer experience

### Bug Fixes

#### Error Initialization

- **Language Configuration Fix** - Fixed language initialization in BaseError to use global configuration
    - Ensured language is set correctly from global configuration when not provided during initialization
    - Improved error message consistency across different initialization scenarios
    - Enhanced code readability and maintainability

#### Type Safety Improvements

- **Enhanced Type Hints** - Improved type hints for gRPC status codes and error handling
    - Refined type annotations for better IDE support and code reliability
    - Enhanced type safety across error handling components
    - Improved developer experience with better autocomplete and error detection

### Code Quality

- **Comprehensive Error Coverage** - Updated all error classes to support the new language and gRPC handling system
    - Enhanced auth_errors, business_errors, database_errors, network_errors, resource_errors, system_errors, and
      validation_errors
    - Improved error categorization and handling consistency
    - Enhanced error reporting and debugging capabilities across all error types

## [3.5.2] - 2025-07-28

### Bug Fixes

#### Elasticsearch Authentication

- **Password Secret Value Extraction** - Fixed critical authentication issue in Elasticsearch adapters where password
  secret values were not being properly extracted
    - Updated both synchronous and asynchronous Elasticsearch adapters to use `get_secret_value()` method for
      HTTP_PASSWORD
    - Resolved authentication failures when using SecretStr password configuration
    - Improved security by properly handling encrypted password fields in Elasticsearch configuration

### Dependencies

- **Poetry Lock Update** - Updated poetry.lock file to Poetry 2.1.2 for improved dependency management
    - Enhanced dependency resolution with latest Poetry version
    - Updated platform-specific package markers for better cross-platform compatibility
    - Improved package hash verification and security

### Code Quality

- **Authentication Consistency** - Standardized password handling across Elasticsearch adapters
    - Ensured consistent secret value extraction in both sync and async adapters
    - Maintained backward compatibility while improving security practices
    - Enhanced error handling for authentication configuration

## [3.5.1] - 2025-07-28

### Bug Fixes

#### HTTP Status Code Handling

- **Status Code Name Mismatch** - Fixed critical issue in FastAPIExceptionHandler where `http_status_code` was
  incorrectly referenced
    - Changed from `exception.http_status_code` to `exception.http_status_code_value` for proper status code retrieval
    - Resolved HTTP status code name mismatch that was causing incorrect error responses
    - Improved error handling consistency in FastAPI exception processing

### Improvements

#### Protobuf DTO Runtime Type Safety

- **Runtime Type Checking** - Enhanced BaseProtobufDTO with comprehensive runtime type validation
    - Added runtime type checking in `from_proto()` method to validate input parameter types
    - Implemented proper type validation before protobuf message processing
    - Enhanced error messages with clear type mismatch information

#### Custom Exception Integration

- **Custom Exception Handling** - Replaced generic TypeError with domain-specific InvalidEntityTypeError
    - Updated protobuf DTO type validation to use `InvalidEntityTypeError` for better error categorization
    - Improved error context with expected and actual type information
    - Enhanced error handling consistency across the protobuf DTO system

### Code Quality Enhancements

- **Error Handling Consistency** - Standardized error handling patterns across protobuf DTO operations
    - Improved error message clarity and debugging capabilities
    - Enhanced type safety with proper exception chaining
    - Maintained backward compatibility while improving error reporting

## [3.5.0] - 2025-07-26

### New Features

#### Protobuf DTO Support

- **BaseProtobufDTO** - Added new base class for Data Transfer Objects that can be converted to and from Protobuf
  messages
    - Provides seamless integration between Pydantic DTOs and Google Protocol Buffers
    - Supports bidirectional conversion with `from_proto()` and `to_proto()` methods
    - Includes runtime dependency checking for protobuf availability
    - Maintains type safety with proper error handling for missing protobuf dependencies

### Bug Fixes

#### Type Safety Improvements

- **ClassVar Type Variable Issue** - Fixed critical type annotation issue in BaseProtobufDTO where ClassVar contained
  type variables
    - Resolved `ClassVar` parameter cannot include type variables error
    - Updated type annotations to use concrete `Message` type instead of type variables
    - Improved type safety by using proper concrete types for class variables
    - Added comprehensive type annotations for all methods and parameters

#### Code Quality Enhancements

- **Import Cleanup** - Removed invalid Unicode characters and simplified import structure
    - Fixed invisible Unicode character `\uab` that was causing linter errors
    - Streamlined protobuf import logic by removing unnecessary type variables
    - Enhanced code readability and maintainability
    - Added proper docstring formatting with Google-style documentation

#### Linting Configuration

- **Ruff Configuration** - Updated linting rules to accommodate protobuf DTO patterns
    - Added `ANN401` exception for `base_protobuf_dto.py` to allow `Any` types in `*args` and `**kwargs`
    - Maintained strict type checking while allowing necessary flexibility for DTO inheritance patterns
    - Ensured all pre-commit hooks pass without compromising code quality standards

## [3.4.5] - 2025-07-24

### Improvements

#### Configuration Template Enhancements

- **Improved Readability** - Enhanced ElasticsearchAPMConfig size fields to use human-readable string values instead of
  raw bytes
    - Changed `API_REQUEST_SIZE` from `768 * 1024` to `"768kb"` for better configuration clarity
    - Changed `LOG_FILE_SIZE` from `50 * 1024 * 1024` to `"50mb"` for improved readability
- **Configuration Clarity** - Updated size-related configuration fields to use standard size notation (kb, mb) making
  configuration files more intuitive and easier to understand

### Bug Fixes

- **Code Cleanup** - Removed redundant files to improve project structure and reduce maintenance overhead

## [3.4.4] - 2025-07-17

### Improvements

#### gRPC Integration Improvements

- **Import Safety** - Added robust gRPC import handling with try/except blocks to prevent import errors when gRPC is not
  available
- **Type Safety** - Enhanced type annotations for gRPC context handling with improved error type definitions
- **Error Handling** - Improved gRPC error handling with better type safety and context management

#### Dependency Updates

- **Kafka** - Updated confluent-kafka to version 2.11.0+ for improved stability and performance
- **Keycloak** - Updated python-keycloak to version 5.7.0+ for enhanced security and features
- **Sentry** - Updated sentry-sdk to version 2.33.0+ for better error tracking capabilities
- **MyPy** - Updated MyPy to version 1.17.0+ for improved type checking and Python 3.13 support

## [3.4.3] - 2025-07-17

### Improvements

#### Keycloak Security Enhancements

- **Admin Mode Control** - Implemented `IS_ADMIN_MODE_ENABLED` configuration flag to control Keycloak admin operations
- **Enhanced Security** - Added granular control over admin capabilities allowing authentication-only mode without admin
  privileges
- **Principle of Least Privilege** - Updated both synchronous and asynchronous Keycloak adapters to respect admin mode
  configuration
- **Test Coverage** - Updated BDD test steps to properly handle admin mode configuration for comprehensive testing

### Security

- **Reduced Attack Surface** - Admin operations can now be disabled while maintaining authentication capabilities
- **Environment Isolation** - Different environments can have different admin capabilities based on configuration
- **Audit Trail** - Clear separation between authentication and administrative operations for better security monitoring

## [3.4.2] - 2025-07-17

### Bug Fixes

- **Import Error Resolution** - Fixed critical import errors that were preventing proper module initialization and
  functionality

## [3.4.1] - 2025-07-07

### Bug Fixes

- **Import Error Fix** - Resolved import error issues that were affecting module loading and dependency resolution

## [3.4.0] - 2025-06-29

### New Features

#### gRPC Integration Enhancements

- **Async gRPC Server Interceptors** - Added comprehensive async gRPC server interceptors with enhanced tracing
  capabilities and metric collection for better observability
- **Enhanced Authentication Context** - Implemented advanced authentication context management with gRPC decorators for
  seamless integration
- **Improved Error Handling** - Enhanced gRPC error handling and context management with better type annotations and
  error propagation

#### Keycloak gRPC Authentication

- **gRPC Authentication Enhancement** - Added token extraction and role validation capabilities for gRPC services with
  Keycloak integration
- **Composite Role Management** - Implemented composite role management methods in both KeycloakAdapter and
  AsyncKeycloakAdapter for advanced authorization scenarios
- **Streamlined Role Checks** - Enhanced role checking and error handling in KeycloakAdapter for better performance and
  reliability

### Improvements

#### Error Handling & Type Safety

- **Enhanced Type Annotations** - Updated type annotations in BaseError class for improved gRPC context handling and
  better type safety
- **Refined Interceptors** - Improved gRPC server interceptors with better error handling and method name context
  support

#### Code Quality & Performance

- **DateTime Optimization** - Refactored BaseUtils and UpdatableMixin to use naive local datetime for improved
  performance and consistency
- **Library Updates** - Updated dependencies and libraries for better compatibility and security

### Community Contributions

- **Collaborative Development** - Merged contributions from @Mohammadreza-kh94 for Keycloak gRPC authentication
  enhancements
- **Code Refactoring** - Integrated improvements from @heysaeid for datetime handling optimizations

## [v3.3.1] - 2025-06-12

### Improvements

#### Keycloak Integration Enhancements

- **Enhanced error handling** - Added comprehensive custom error classes and centralized exception handling for better
  Keycloak error management and debugging
- **Improved error messaging** - Introduced `KeycloakErrorMessageType` enum for standardized error handling and clearer
  error messages
- **Extended functionality** - Added `get_realm` method to both synchronous and asynchronous Keycloak ports for better
  realm management
- **Optimized caching** - Updated cache clearing methods in Keycloak adapters for improved performance and reliability

#### Datetime Utilities Enhancement

- **Enhanced datetime handling** - Significantly improved datetime utility functions with better timezone support, date
  parsing capabilities, and comprehensive validation for more robust date and time operations
- **Extended functionality** - Added new datetime manipulation methods and improved existing functions for better
  developer experience

#### Elasticsearch Adapter Refinements

- **Improved adapter implementation** - Enhanced Elasticsearch adapter with better error handling, improved connection
  management, and optimized query performance
- **Configuration enhancements** - Refined Elasticsearch configuration options for more flexible deployment scenarios
  and better SSL/TLS support

#### Configuration Management

- **Enhanced configuration templates** - Updated configuration templates with improved validation, better default
  values, and comprehensive documentation
- **Streamlined setup process** - Simplified configuration management for various adapters and services with clearer
  parameter definitions

#### Testing & Quality Assurance

- **Enhanced test coverage** - Significantly improved Keycloak adapter feature tests and datetime utilities with
  comprehensive feature tests and better validation scenarios
- **Development environment** - Updated Keycloak and development configuration in test environment for improved local
  development experience
- **Documentation updates** - Enhanced API reference documentation and configuration guides for better developer
  onboarding

#### Code Quality & Maintenance

- **Code organization** - Improved code structure and organization across multiple modules for better maintainability
- **Enhanced validation** - Added better input validation and error handling throughout the codebase

### Bug Fixes

- **Configuration cleanup** - Removed invalid imports and unused Elasticsearch configuration references to prevent
  import errors
- **Code optimization** - Removed redundant error handling code for cleaner and more maintainable codebase

### Community Contributions

- **Collaborative improvements** - Merged contributions from @Mohammadreza-kh94 for Keycloak enhancements and @heysaeid
  for configuration fixes

## [v3.3.0] - 2025-06-09

### New Features

#### Elasticsearch Integration

- **New Elasticsearch adapter** - Added comprehensive Elasticsearch integration with full search and indexing
  capabilities, enabling powerful full-text search and analytics functionality for your applications
- **Enhanced search capabilities** - Integrated advanced search features with Elasticsearch 9.0.2 support for improved
  performance and modern search functionality

### Improvements

#### Configuration & Testing

- **Improved Elasticsearch configuration** - Enhanced configuration management with better validation and streamlined
  setup process
- **Comprehensive test coverage** - Added extensive test suite for Elasticsearch functionality to ensure reliability and
  stability

### Bug Fixes

- **Configuration validation** - Removed unnecessary authentication validation in Elasticsearch configuration for
  improved flexibility
- **Adapter initialization** - Fixed Elasticsearch adapter initialization issues for smoother integration

### Collaboration

- **Community contributions** - Merged contributions from @alireza-shirmohammadi improving Elasticsearch functionality
  and resolving upstream conflicts

## [v3.2.7] - 2025-01-06

### Improvements

#### Database Query Flexibility

- **Enhanced query result handling** - Added `has_multiple_entities` parameter to search query methods in both
  synchronous and asynchronous SQLAlchemy adapters and ports. This new parameter provides flexible control over query
  result processing, allowing developers to choose between `fetchall()` for multiple entities or `scalars().all()` for
  single entity queries, optimizing performance based on query requirements.

#### Database Performance

- **Optimized search query execution** - Refactored SQLAlchemy query execution method to use `fetchall()` instead of
  `scalars().all()` for improved performance and memory efficiency in both synchronous and asynchronous adapters

## [v3.2.6] - 2025-01-06

### Improvements

#### Database Performance

- **Optimized search query execution** - Refactored SQLAlchemy query execution method to use `fetchall()` instead of
  `scalars().all()` for improved performance and memory efficiency in both synchronous and asynchronous adapters

## [v3.2.5] - 2025-01-06

### Improvements

#### Developer Experience

- **Enhanced changelog generation script** - Significantly improved the changelog generation process with comprehensive
  type hints, better error handling, and enhanced Conventional Commits support for more accurate categorization of
  changes
- **Updated development guidelines** - Added new coding standards and architectural rules to improve code quality and
  maintainability

### Technical Enhancements

- **Type Safety** - Added Python 3.13 type hints throughout the changelog generation script for better IDE support and
  code reliability
- **Error Handling** - Implemented proper exception chaining and more robust error reporting
- **Code Organization** - Refactored script structure for better modularity and maintainability

## [3.2.4] - 2025-01-27

### Fixed

#### Testing

- Fixed atomic transactions feature test error handling expectations:
- Corrected test to expect `InternalError` instead of `DatabaseError` for normal exceptions
- Aligned test expectations with the correct exception wrapping behavior in atomic decorators
- Normal exceptions (like `ValueError`) are now correctly expected to be wrapped as `InternalError`
- Database-specific exceptions continue to be wrapped as appropriate `DatabaseError` subclasses

## [3.2.3] - 2025-01-24

### Fixed

- Fix using "IS_ENABLED" instead wrong variable "ENABLED" in elastic ap… by @majasemzadeh in #45

## [3.2.2] - 2025-05-24

### Changed

#### Database Entities

- Enhanced timestamp handling in SQLAlchemy base entities:
- Improved timezone-aware datetime handling in UpdatableMixin
- Updated `updated_at` field to use server-side default timestamp
- Added helper method `_make_naive()` for timezone conversion
- Optimized update timestamp behavior for better database compatibility

## [3.2.1] - 2025-05-20

### Changed

#### Elastic APM Configuration

- Enhanced Elastic APM configuration and integration:
- Refactored configuration logic for improved maintainability
- Updated configuration templates for greater flexibility
- Improved gRPC tracing interceptor for better observability
- Refined application utility functions related to APM

## [3.2.0] - 2025-05-20

### Added

#### Keycloak Integration

- Added and refactored methods for creating realms, clients, and client roles in Keycloak adapters (sync and async)
- Improved admin credential support and configuration for Keycloak
- Enhanced type hints and readability in Keycloak step definitions

#### Utilities

- Introduced string utility functions for case conversion (snake_case ↔ camelCase)

#### Configuration

- Expanded .env.example with more detailed configuration options for services
- Improved KeycloakConfig with admin fields for easier testing and setup

#### Documentation & Code Quality

- Improved and clarified usage examples and step definitions
- Reformatted Python files to comply with Ruff checks
- Minor refactoring for better code clarity and maintainability

## [3.1.1] - 2025-05-17

### Documentation

- Enhanced project documentation
- Improved usage examples

### Changed

#### Configuration

- Updated configuration templates
- Enhanced Kafka configuration template with improved settings
- Optimized template structure for better usability

### Fixed

- Resolved merge conflicts
- Streamlined codebase integration

## [3.1.0] - 2025-05-15

### Added

#### Payment Gateway

- Implemented Parsian Internet Payment Gateway adapter
- Added comprehensive IPG integration support
- Enhanced payment processing capabilities

### Changed

#### Documentation

- Updated adapter documentation
- Improved IPG integration examples
- Refactored Parsian adapter code structure

### Removed

- Eliminated redundant error messages
- Streamlined error handling

## [3.0.1] - 2025-04-27

### Fixed

#### Code Quality

- Fixed import error in module dependencies

## [3.0.0] - 2025-04-27

### Changed

#### Database Adapters

- Refactor StarRocks driver integration
- Refactor SQLite driver integration
- Enhanced database adapter support
- Updated dependencies for StarRocks compatibility

#### Configuration

- Updated Elasticsearch Config Template
- Enhanced configuration management
- Improved dependency handling

### Code Quality

- Improved type safety across adapters
- Enhanced error handling
- Optimized connection management

## [2.0.1] - 2025-04-27

### Added

#### StarRocks

- Added StarRocks driver integration
- Enhanced database adapter support
- Updated dependencies for StarRocks compatibility

### Changed

#### Dependencies

- Updated poetry.lock with new dependencies
- Enhanced package compatibility
- Updated Elasticsearch Config Template

## [2.0.0] - 2025-04-27

### Changed

#### Models

- Refactored range DTOs for better type safety and validation
- Enhanced pagination DTO implementation
- Added time interval unit type support

### Code Quality

- Improved type hints in DTO implementations
- Enhanced validation in range operations
- Optimized DTO serialization

## [1.0.3] - 2025-04-20

### Documentation

#### Features

- Updated atomic transaction documentation with detailed examples
- Enhanced feature documentation with clear scenarios
- Added comprehensive step definitions for BDD tests

#### Code Quality

- Improved SQLAlchemy atomic decorator implementation
- Enhanced test coverage for atomic transactions
- Updated BDD test scenarios for better clarity

## [1.0.2] - 2025-04-20

### Documentation

#### API Reference

- Updated adapter documentation with new architecture details
- Enhanced API reference structure and organization
- Added comprehensive usage examples

#### General Documentation

- Improved installation guide with detailed setup instructions
- Enhanced feature documentation with clear examples
- Updated usage guide with new architecture patterns

#### Code Quality

- Updated dependencies in poetry.lock and pyproject.toml
- Enhanced documentation consistency and clarity

## [1.0.1] - 2025-04-20

### Fixed

#### Error Handling

- Enhanced exception capture in all scenarios
- Improved error handling robustness across components
- Added comprehensive error logging

#### Code Quality

- Strengthened error recovery mechanisms
- Enhanced error reporting and debugging capabilities

## [1.0.0] - 2025-04-20

### Architecture

#### Database Adapters

- Refactored database adapter architecture for better modularity
- Separated base SQLAlchemy functionality from specific database implementations
- Introduced dedicated adapters for PostgreSQL, SQLite, and StarRocks
- Enhanced session management with improved registry system

### Added

#### PostgreSQL Support

- Implemented dedicated PostgreSQL adapter with optimized connection handling
- Added PostgreSQL-specific session management
- Enhanced configuration options for PostgreSQL connections

#### SQLite Support

- Added dedicated SQLite adapter with improved transaction handling
- Implemented SQLite-specific session management
- Enhanced mock testing capabilities for SQLite

#### StarRocks Support

- Introduced StarRocks database adapter
- Implemented StarRocks-specific session management
- Added configuration support for StarRocks connections

### Changed

#### Core Architecture

- Moved base SQLAlchemy functionality to `adapters/base/sqlalchemy`
- Refactored session management system for better extensibility
- Improved atomic transaction decorator implementation

#### Documentation

- Updated API reference for new adapter structure
- Enhanced configuration documentation
- Added examples for new database adapters

### Code Quality

- Improved type safety across database adapters
- Enhanced error handling in session management
- Optimized connection pooling implementation

## [0.14.3] - 2025-04-26

### Added

#### Adapters

- Major database adapter refactoring

### Changed

- Update dependencies

### Fixed

- Fix capture exeptrioin in all senario

## [0.14.2] - 2025-04-20

### Fixed

#### Keycloak

- Resolved linter errors in Keycloak integration
- Enhanced code quality in authentication components

#### Code Quality

- Improved type safety in Keycloak adapters
- Enhanced error handling in authentication flows

## [0.14.1] - 2025-04-20

### Fixed

#### Database

- Resolved "DEFAULT" server_default value issue in BaseEntity timestamps
- Enhanced timestamp handling in database entities

#### Code Quality

- Improved database entity configuration
- Enhanced type safety in entity definitions

## [0.14.0] - 2025-04-16

### Added

#### Kafka Integration

- Implemented comprehensive Kafka adapter system with ports and adapters
- Added test suite for Kafka adapters
- Enhanced Kafka documentation with detailed usage examples

#### Documentation

- Refactored and improved documentation structure
- Added comprehensive Kafka integration guides
- Enhanced docstrings for better code understanding

### Fixed

#### Code Quality

- Resolved linting issues in configuration templates
- Fixed lint errors in Keycloak adapters and ports

## [0.13.5] - 2025-04-16

### Fixed

#### SQLAlchemy

- Resolved sorting functionality in SQLAlchemy mixin
- Enhanced query sorting capabilities with improved error handling

#### Code Quality

- Applied ruff formatter to config_template.py for consistent code style
- Updated AsyncContextManager to AbstractAsyncContextManager to resolve UP035 lint error

## [0.13.4] - 2025-04-15

### Added

#### FastAPI Integration

- Implemented lifespan support for FastAPI applications
- Enhanced application lifecycle management with proper startup and shutdown handlers

#### Database Configuration

- Added automatic database URL generation with validation in SqlAlchemyConfig
- Improved database connection configuration with enhanced error handling

### Code Quality

- Integrated new features with comprehensive test coverage
- Enhanced configuration validation and error reporting

### Changed

- Update changelogs

### Fixed

#### Configs

- Run ruff format on config_template.py to resolve formatting issues
- Replace AsyncContextManager with AbstractAsyncContextManager to fix UP035 lint error

## [0.13.3] - 2025-04-15

### Added

#### CI/CD

- Implemented comprehensive linting workflow for improved code quality
- Enhanced GitHub Actions with updated tj-actions/changed-files for better change tracking

#### Documentation

- Added detailed documentation for range DTOs and their usage patterns
- Improved API reference documentation with new examples

### Changed

#### Models

- Enhanced range DTOs with improved type safety and validation
- Updated range DTOs to support more flexible boundary conditions

### Code Quality

- Integrated automated linting for consistent code style
- Improved code formatting and documentation standards

## [0.13.2] - 2025-04-10

### Documentation

- Enhanced Redis adapter documentation with comprehensive docstrings
- Added MinIO adapter to API reference documentation

### Code Quality

- Improved code quality with linter fixes across Redis adapter and ORM components
- Fixed file utilities test suite
- Cleaned up redundant changelog files

## [0.13.1] - 2025-04-08

### Security

- Enhanced cryptographic security by replacing `random` with `secrets` module
- Strengthened TOTP implementation with improved security practices
- Upgraded password utilities with robust validation and generation

### Code Quality

- Improved type safety with explicit typing and modern type hints
- Enhanced error handling with domain-specific exception types
- Standardized parameter naming and module consistency

### Documentation

- Added comprehensive docstrings to configuration classes
- Expanded utility function documentation
- Improved error handling documentation

## [0.13.0] - 2025-04-08

### Features

- **MinIO Integration**: Full S3-compatible object storage adapter with:
    - Comprehensive S3 operation support (12 standardized methods)
    - Built-in TTL caching for performance optimization
    - Flexible configuration with endpoint and credential management
    - Clear cache management through `clear_all_caches`

### Testing

- Added complete BDD test suite for MinIO adapter:
    - Bucket and object operation validation
    - Presigned URL generation testing
    - Bucket policy management verification

### Documentation

- Added extensive MinIO adapter examples and usage guides
- Improved error handling documentation
- Updated configuration documentation with new MinIO settings

### Usage Example

```python
# Initialize the MinIO adapter
from archipy.adapters.minio.adapters import MinioAdapter

minio = MinioAdapter()

# Create a bucket and upload a file
minio.make_bucket("my-bucket")
minio.put_object("my-bucket", "document.pdf", "/path/to/document.pdf")

# Generate a presigned URL for temporary access
download_url = minio.presigned_get_object("my-bucket", "document.pdf", expires=3600)
```

## [0.12.0] - 2025-03-29

### Features

- **Keycloak Integration**: Comprehensive authentication and authorization for FastAPI:
    - Role-based access control with customizable requirements
    - Resource-based authorization for fine-grained access control
    - Both synchronous and asynchronous authentication flows
    - Token validation and introspection
    - User info extraction capabilities

### Code Quality

- Improved error handling clarity by renaming `ExceptionMessageType` to `ErrorMessageType`
- Enhanced error documentation with detailed descriptions
- Updated error handling implementation with new message types

### Usage Example

```python
from fastapi import FastAPI, Depends
from archipy.helpers.utils.keycloak_utils import KeycloakUtils

app = FastAPI()


@app.get("/api/profile")
def get_profile(user: dict = Depends(KeycloakUtils.fastapi_auth(
    required_roles={"user"},
    admin_roles={"admin"}
))):
    return {
        "user_id": user.get("sub"),
        "username": user.get("preferred_username")
    }
```

## [0.11.2] - 2025-03-21

### Error Handling

- Enhanced exception management with improved error reporting
- Streamlined error messaging for better debugging
- Fixed various error handling edge cases

## [0.11.1] - 2025-03-15

### Performance

- Optimized resource usage across core components
- Enhanced caching mechanisms for improved performance
- Improved memory utilization in key operations

## [0.11.0] - 2025-03-10

### Features

- **Keycloak Adapter**: New authentication and authorization system:
    - Asynchronous operations support
    - Token management and validation
    - User information retrieval
    - Comprehensive security features

### Performance

- Added TTL cache decorator for optimized performance
- Improved Keycloak adapter efficiency

### Documentation

- Added detailed Keycloak integration guides
- Included comprehensive usage examples

### Usage Example

```python
from archipy.adapters.keycloak.adapters import KeycloakAdapter

# Initialize adapter with configuration from global config
keycloak = KeycloakAdapter()

# Authenticate and get access token
token = keycloak.get_token("username", "password")

# Get user information
user_info = keycloak.get_userinfo(token)

# Verify token validity
is_valid = keycloak.validate_token(token)
```

## [0.10.2] - 2025-03-05

### Stability

- Improved Redis connection pool stability and management
- Enhanced error recovery mechanisms
- Fixed various edge cases in Redis operations

## [0.10.1] - 2025-03-01

### Documentation

- Enhanced Redis and email adapter documentation
- Added comprehensive API reference
- Improved usage examples for common operations

## [0.10.0] - 2025-02-25

### Features

- **Redis Integration**: New caching and key-value storage system:
    - Flexible key-value operations
    - Built-in TTL support
    - Connection pooling
    - Comprehensive error handling

- **Email Service**: New email integration system:
    - Multiple email provider support
    - Template-based email sending
    - Attachment handling
    - Async operation support

### Configuration

- Enhanced configuration management system
- Added support for Redis and email settings
- Improved environment variable handling

### Usage Example

```python
# Initialize the Redis adapter
from archipy.adapters.redis.adapters import RedisAdapter

redis = RedisAdapter()

# Basic operations
redis.set("user:1:name", "John Doe")
name = redis.get("user:1:name")

# Using with TTL
redis.set("session:token", "abc123", ttl=3600)  # Expires in 1 hour
```

## [0.9.0] - 2025-02-20

### Security

- **TOTP System**: Comprehensive Time-based One-Time Password implementation:
    - Secure token generation and validation
    - Configurable time windows
    - Built-in expiration handling
    - RFC compliance

- **Multi-Factor Authentication**: Enhanced security framework:
    - Multiple authentication factor support
    - Flexible factor configuration
    - Integration with existing auth systems

### Usage Example

```python
from archipy.helpers.utils.totp_utils import TOTPUtils
from uuid import uuid4

# Generate a TOTP code
user_id = uuid4()
totp_code, expires_at = TOTPUtils.generate_totp(user_id)

# Verify a TOTP code
is_valid = TOTPUtils.verify_totp(user_id, totp_code)

# Generate a secure key for TOTP initialization
secret_key = TOTPUtils.generate_secret_key_for_totp()
```

## [0.8.0] - 2025-02-15

### Features

- **Redis Integration**: Comprehensive key-value store and caching system:
    - Full Redis API implementation
    - Built-in caching functionality
    - Performance-optimized operations
    - Connection pooling support

### Testing

- **Mock Redis Implementation**:
    - Complete test coverage for Redis operations
    - Simulated Redis environment for testing
    - Configurable mock behaviors

### Documentation

- Added Redis integration guides
- Included mock testing examples
- Updated configuration documentation

## [0.7.2] - 2025-02-10

### Database

- Enhanced connection pool stability and management
- Improved transaction isolation and handling
- Optimized error reporting for database operations
- Added connection lifecycle management

## [0.7.1] - 2025-02-05

### Performance

- Optimized query execution and planning
- Reduced memory footprint for ORM operations
- Enhanced connection pool efficiency
- Improved cache utilization

## [0.7.0] - 2025-02-01

### Features

- **SQLAlchemy Integration**: Complete ORM implementation:
    - Robust entity model system
    - Transaction management with ACID compliance
    - Connection pooling with configurable settings
    - Comprehensive database operations support

### Usage Example

```python
from archipy.adapters.postgres.sqlalchemy.adapters import SQLAlchemyAdapter
from archipy.models.entities.sqlalchemy.base_entities import BaseEntity
from sqlalchemy import Column, String


# Define a model
class User(BaseEntity):
    __tablename__ = "users"
    name = Column(String(100))
    email = Column(String(100), unique=True)


# Use the ORM
orm = SQLAlchemyAdapter()
with orm.session() as session:
    # Create and read operations
    new_user = User(name="John Doe", email="john@example.com")
    session.add(new_user)
    session.commit()

    user = session.query(User).filter_by(email="john@example.com").first()
```

## [0.6.1] - 2025-01-25

### Stability

- Fixed memory leaks in gRPC interceptors
- Improved interceptor performance and efficiency
- Enhanced request/response handling reliability
- Optimized resource cleanup

## [0.6.0] - 2025-01-20

### Features

- **gRPC Integration**: Comprehensive interceptor system:
    - Client and server-side interceptors
    - Request/response monitoring
    - Performance tracing capabilities
    - Enhanced error management

### Documentation

- Added gRPC integration guides
- Included interceptor configuration examples
- Updated troubleshooting documentation

## [0.5.1] - 2025-01-15

### Stability

- Enhanced FastAPI middleware reliability
- Improved response processing efficiency
- Optimized request handling performance
- Fixed edge cases in error management

## [0.5.0] - 2025-01-10

### Features

- **FastAPI Integration**: Complete web framework support:
    - Custom middleware components
    - Request/response processors
    - Standardized error handling
    - Response formatting utilities

### Documentation

- Added FastAPI integration guides
- Included middleware configuration examples
- Updated API documentation

## [0.4.0] - 2025-01-05

### Features

- **Configuration System**: Flexible environment management:
    - Environment variable support
    - Type-safe configuration validation
    - Default value management
    - Override capabilities

### Documentation

- Added configuration system guides
- Included environment setup examples
- Updated validation documentation

## [0.3.0] - 2024-12-25

### Features

- **Core Utilities**: Comprehensive helper functions:
    - Date/time manipulation with timezone support
    - String processing and formatting
    - Common development utilities
    - Type conversion helpers

### Documentation

- Added utility function reference
- Included usage examples
- Updated API documentation

## [0.2.0] - 2024-12-20

### Architecture

- **Hexagonal Architecture**: Core implementation:
    - Ports and adapters pattern
    - Clean architecture principles
    - Domain-driven design
    - Base entity models

### Documentation

- Added architecture overview
- Included design pattern guides
- Updated component documentation

## [0.1.0] - 2025-02-21

### Features

- **Initial Release**: Project foundation:
    - Core project structure
    - Basic framework components
    - Configuration system
    - CI/CD pipeline with GitHub Actions

### Documentation

- Added initial documentation
- Included getting started guide
- Created contribution guidelines
