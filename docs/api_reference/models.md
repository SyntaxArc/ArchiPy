# Models

The `models` module provides core data structures and types used throughout the application, following clean
architecture principles.

## Quick Start

```python
from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.entities.sqlalchemy.base_entities import BaseEntity

# Create a DTO
class UserDTO(BaseDTO):
    id: str
    username: str
    email: str

# Create an entity
class User(BaseEntity):
    __tablename__ = "users"
    username: str
    email: str
```

## Core Components

### DTOs (Data Transfer Objects)

**Base DTOs** - Base classes for all DTOs with common functionality
**Protobuf DTOs** - DTOs that can be converted to/from Google Protocol Buffer messages
**Email DTOs** - DTOs for email-related operations
**Error DTOs** - Standardized error response format
**Pagination DTO** - Handles pagination parameters for queries
**Range DTOs** - Handles range-based queries (integer, date, datetime)
**Search Input DTO** - Standardized search input format
**Sort DTO** - Handles sorting parameters

### Entities

**Base Entities** - Base classes for SQLAlchemy entities with common functionality
**Update Tracking** - Entities with automatic update timestamp tracking
**Soft Deletion** - Entities with soft deletion support
**Admin Tracking** - Entities with admin user tracking
**Manager Tracking** - Entities with manager user tracking

### Errors

**Base Error** - Base class for all custom exceptions
**Auth Errors** - Authentication and authorization errors
**Business Errors** - Business logic violation errors
**Database Errors** - Database operation errors
**Network Errors** - Network communication errors
**Resource Errors** - Resource not found or access errors
**System Errors** - System-level errors
**Validation Errors** - Data validation errors

### Types

**Base Types** - Common type definitions
**Email Types** - Email-related type definitions
**Error Message Types** - Error message type definitions
**Language Type** - Language enumeration
**Sort Order Type** - Sort order enumeration
**Time Interval Unit Type** - Time interval unit enumeration

## Examples

For detailed examples, see:
- [Protobuf DTOs](../examples/models/protobuf_dtos.md)
- [Error Handling](../examples/error_handling.md)
    page_size=10,
    total_items=100
)
```

::: archipy.models.dtos.pagination_dto
options:
show_root_heading: true
show_source: true

### Range DTOs

Handles range-based queries and filters.

```python
from archipy.models.dtos.range_dtos import (
    RangeDTO,
    IntegerRangeDTO,
    DateRangeDTO,
    DatetimeRangeDTO
)

# Integer range
int_range = IntegerRangeDTO(start=1, end=100)

# Date range
date_range = DateRangeDTO(
    start=date(2023, 1, 1),
    end=date(2023, 12, 31)
)

# Datetime range
dt_range = DatetimeRangeDTO(
    start=datetime(2023, 1, 1),
    end=datetime(2023, 12, 31)
)
```

::: archipy.models.dtos.range_dtos
options:
show_root_heading: true
show_source: true

### Search Input DTO

Standardized search parameters.

```python
from archipy.models.dtos.search_input_dto import SearchInputDTO

search = SearchInputDTO[str](
    query="john",
    filters={"active": True},
    pagination=pagination
)
```

::: archipy.models.dtos.search_input_dto
options:
show_root_heading: true
show_source: true

### Sort DTO

Handles sorting parameters for queries.

```python
from archipy.models.dtos.sort_dto import SortDTO

sort = SortDTO[str](
    field="created_at",
    order="desc"
)
```

::: archipy.models.dtos.sort_dto
options:
show_root_heading: true
show_source: true

## Entities

### SQLAlchemy Base Entities

Base classes for SQLAlchemy entities with various mixins for different capabilities.

```python
from archipy.models.entities.sqlalchemy.base_entities import (
    BaseEntity,
    UpdatableEntity,
    DeletableEntity,
    AdminEntity,
    ManagerEntity,
    UpdatableDeletableEntity,
    ArchivableEntity,
    UpdatableAdminEntity,
    UpdatableManagerEntity,
    ArchivableDeletableEntity,
    UpdatableDeletableAdminEntity,
    UpdatableDeletableManagerEntity,
    ArchivableAdminEntity,
    ArchivableManagerEntity,
    UpdatableManagerAdminEntity,
    ArchivableManagerAdminEntity,
    ArchivableDeletableAdminEntity,
    ArchivableDeletableManagerEntity,
    UpdatableDeletableManagerAdminEntity,
    ArchivableDeletableManagerAdminEntity
)
from sqlalchemy import Column, String

# Basic entity
class User(BaseEntity):
    __tablename__ = "users"
    username = Column(String(100), unique=True)
    email = Column(String(255), unique=True)

# Entity with update tracking
class Post(UpdatableEntity):
    __tablename__ = "posts"
    title = Column(String(200))
    content = Column(String)

# Entity with soft deletion
class Comment(DeletableEntity):
    __tablename__ = "comments"
    text = Column(String)

# Entity with admin tracking
class AdminLog(AdminEntity):
    __tablename__ = "admin_logs"
    action = Column(String)

# Entity with manager tracking
class ManagerLog(ManagerEntity):
    __tablename__ = "manager_logs"
    action = Column(String)
```

::: archipy.models.entities.sqlalchemy.base_entities
options:
show_root_heading: true
show_source: true

## Errors

The error handling system is organized into several categories, each handling specific types of errors:

### Authentication Errors
Handles authentication and authorization related errors.

```python
from archipy.models.errors import (
    UnauthenticatedError,
    InvalidCredentialsError,
    TokenExpiredError,
    InvalidTokenError,
    SessionExpiredError,
    PermissionDeniedError,
    AccountLockedError,
    AccountDisabledError,
    InvalidVerificationCodeError
)

# Example: Handle invalid credentials
try:
    authenticate_user(username, password)
except InvalidCredentialsError as e:
    logger.warning(f"Failed login attempt: {e}")
```

### Validation Errors
Handles input validation and format errors.

```python
from archipy.models.errors import (
    InvalidArgumentError,
    InvalidFormatError,
    InvalidEmailError,
    InvalidPhoneNumberError,
    InvalidLandlineNumberError,
    InvalidNationalCodeError,
    InvalidPasswordError,
    InvalidDateError,
    InvalidUrlError,
    InvalidIpError,
    InvalidJsonError,
    InvalidTimestampError,
    OutOfRangeError
)

# Example: Validate user input
try:
    validate_user_input(email, phone)
except InvalidEmailError as e:
    return {"error": e.to_dict()}
```

### Resource Errors
Handles resource and data management errors.

```python
from archipy.models.errors import (
    NotFoundError,
    AlreadyExistsError,
    ConflictError,
    ResourceLockedError,
    ResourceBusyError,
    DataLossError,
    InvalidEntityTypeError,
    FileTooLargeError,
    InvalidFileTypeError,
    QuotaExceededError
)

# Example: Handle resource not found
try:
    user = get_user(user_id)
except NotFoundError as e:
    return {"error": e.to_dict()}
```

### Network Errors
Handles network and communication errors.

```python
from archipy.models.errors import (
    NetworkError,
    ConnectionTimeoutError,
    ServiceUnavailableError,
    GatewayTimeoutError,
    BadGatewayError,
    RateLimitExceededError
)

# Example: Handle network issues
try:
    response = make_api_request()
except ConnectionTimeoutError as e:
    logger.error(f"Connection timeout: {e}")
```

### Business Errors
Handles business logic and operation errors.

```python
from archipy.models.errors import (
    InvalidStateError,
    BusinessRuleViolationError,
    InvalidOperationError,
    InsufficientFundsError,
    InsufficientBalanceError,
    MaintenanceModeError,
    FailedPreconditionError
)

# Example: Handle business rule violation
try:
    process_transaction(amount)
except InsufficientFundsError as e:
    return {"error": e.to_dict()}
```

### Database Errors
Handles database and storage related errors.

```python
from archipy.models.errors import (
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseTransactionError,
    StorageError,
    CacheError,
    CacheMissError
)

# Example: Handle database errors
try:
    save_to_database(data)
except DatabaseConnectionError as e:
    logger.error(f"Database connection failed: {e}")
```

### System Errors
Handles system and internal errors.

```python
from archipy.models.errors import (
    InternalError,
    ConfigurationError,
    ResourceExhaustedError,
    UnavailableError,
    UnknownError,
    AbortedError,
    DeadlockDetectedError
)

# Example: Handle system errors
try:
    process_request()
except DeadlockDetectedError as e:
    logger.error(f"Deadlock detected: {e}")
    # Implement retry logic
```

::: archipy.models.errors
options:
show_root_heading: true
show_source: true

## Types

### Base Types

Basic type definitions used throughout the application.

::: archipy.models.types.base_types
options:
show_root_heading: true
show_source: true

### Email Types

Type definitions for email-related operations.

::: archipy.models.types.email_types
options:
show_root_heading: true
show_source: true

### Error Message Types

Standardized error message types for consistent error handling.

::: archipy.models.types.error_message_types
options:
show_root_heading: true
show_source: true

### Language Type

Language code type definition.

::: archipy.models.types.language_type
options:
show_root_heading: true
show_source: true

### Sort Order Type

Sort order type definition for queries.

::: archipy.models.types.sort_order_type
options:
show_root_heading: true
show_source: true

## Key Classes

### BaseDTO

Class: `archipy.models.dtos.base_dtos.BaseDTO`

Base class for all DTOs with features:

- Pydantic model inheritance
- JSON serialization
- Validation
- Type hints
- Common utility methods

### BaseEntity

Class: `archipy.models.entities.sqlalchemy.base_entities.BaseEntity`

Base class for SQLAlchemy entities with features:

- UUID primary key
- Timestamp fields (created_at, updated_at)
- Common query methods
- Relationship support
- Type-safe column definitions
- Mixin support for:
    - Update tracking
    - Soft deletion
    - Admin tracking
    - Manager tracking
    - Archiving
    - Combined capabilities

### BaseError

Class: `archipy.models.errors.BaseError`

Base class for custom errors with features:

- Standardized error format
- Error code system
- Detailed error messages
- Stack trace support
- Error context
- Additional data support
- Language localization
- HTTP and gRPC status code mapping
