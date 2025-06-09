# Changelog

All notable changes to ArchiPy are documented in this changelog, organized by version.


## [v3.3.0] - 2025-01-06

### New Features

#### Elasticsearch Integration
- **New Elasticsearch adapter** - Added comprehensive Elasticsearch integration with full search and indexing capabilities, enabling powerful full-text search and analytics functionality for your applications
- **Enhanced search capabilities** - Integrated advanced search features with Elasticsearch 9.0.2 support for improved performance and modern search functionality

### Improvements

#### Configuration & Testing
- **Improved Elasticsearch configuration** - Enhanced configuration management with better validation and streamlined setup process
- **Comprehensive test coverage** - Added extensive test suite for Elasticsearch functionality to ensure reliability and stability

### Bug Fixes
- **Configuration validation** - Removed unnecessary authentication validation in Elasticsearch configuration for improved flexibility
- **Adapter initialization** - Fixed Elasticsearch adapter initialization issues for smoother integration

### Collaboration
- **Community contributions** - Merged contributions from @alireza-shirmohammadi improving Elasticsearch functionality and resolving upstream conflicts

## [v3.2.7] - 2025-01-06

### Improvements

#### Database Query Flexibility

- **Enhanced query result handling** - Added `has_multiple_entities` parameter to search query methods in both
  synchronous and asynchronous SQLAlchemy adapters and ports. This new parameter provides flexible control over query
  result processing, allowing developers to choose between `fetchall()` for multiple entities or `scalars().all()` for
  single entity queries, optimizing performance based on query requirements.

## [v3.2.7] - 2025-01-06

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

- Updated ElasticSearch Config Template
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
- Updated ElasticSearch Config Template

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
