# Features

ArchiPy provides a robust framework for structured Python development, focusing on standardization, testability, and
productivity.

## Database Integration

- **Multi-Database Support**: Dedicated adapters for PostgreSQL, SQLite, StarRocks, and ScyllaDB
- **SQLAlchemy Integration**: Standardized ORM implementation with:
    - Base SQLAlchemy components for common functionality
    - Database-specific session management
    - Enhanced transaction handling with atomic decorators
    - Connection pooling and lifecycle management
- **NoSQL Support**: Native ScyllaDB/Cassandra adapter with CQL support, prepared statements, and TTL

## Configuration Management

- **Standardized Configs**: Use `base_config` and `config_template` for consistent setup
- **Injection**: Seamlessly inject configurations into components
- **Environment Management**: Flexible environment variable handling with validation
- **Type Safety**: Configuration validation with Pydantic models

## Adapters & Mocks

- **Database Adapters**: Dedicated implementations for PostgreSQL, SQLite, StarRocks, and ScyllaDB
- **Service Adapters**: Pre-built for Redis, Email, Keycloak, MinIO, and Kafka
- **Mocks**: Testable mocks for isolated testing
- **Async Support**: Synchronous and asynchronous implementations
- **Ports & Adapters Pattern**: Clean architecture with dependency inversion

## Data Standardization

- **Base Entities**: Standardized SQLAlchemy entities with timestamp handling
- **DTOs**: Pydantic-based DTOs for data transfer:
    - Pagination and sorting
    - Error handling
    - Search and range operations
    - Email and attachment handling
- **Type Safety**: Enforced via Pydantic and modern Python type hints

## Helper Utilities

- **Decorators**:
    - Retry mechanism for resilient operations
    - Singleton pattern implementation
    - SQLAlchemy atomic transactions
    - TTL caching for performance optimization
- **Interceptors**:
    - FastAPI rate limiting
    - gRPC tracing and monitoring
- **Security**:
    - Keycloak integration for authentication
    - TOTP implementation
    - Password utilities with secure hashing
    - JWT handling
- **Type Safety**: Consistent type checking and casting

## Testing & Quality

- **BDD Testing**:
    - Behave integration for sync/async scenarios
    - Comprehensive feature files
    - Step definitions for common operations
- **Code Quality**:
    - Automated linting with ruff
    - Type checking with mypy
    - Code formatting with black
    - Pre-commit hooks for quality assurance

## Best Practices & Tooling

- **UV**: Fast Python package installer and resolver
- **Pre-commit**: Automated code quality checks
- **Clean Architecture**: Hexagonal design pattern
- **Modular Design**: Optional dependencies for flexibility
- **Comprehensive Documentation**: API reference and usage examples

## Performance & Scalability

- **Connection Pooling**: Optimized database connections
- **Caching**: Redis integration for performance
- **Async Support**: Non-blocking operations
- **Resource Management**: Proper cleanup and lifecycle handling
- **Error Recovery**: Robust error handling and retry mechanisms
