# ArchiPy Architecture

## Overview

ArchiPy is organized into four main modules, each serving a specific purpose in creating structured, maintainable Python
applications:

1. **Adapters**: External service integrations
2. **Configs**: Configuration management
3. **Helpers**: Utility functions and support classes
4. **Models**: Core data structures

This architecture follows clean architecture principles, separating concerns and ensuring that dependencies point inward
toward the domain core.

## Modules

### Adapters

The `adapters` module provides implementations for external service integrations, following the Ports and Adapters
pattern (Hexagonal Architecture). This module includes:

- **Base Adapters**: Core implementations and interfaces
    - SQLAlchemy base components
    - Common adapter patterns
    - Base session management

- **Database Adapters**: Database-specific implementations
    - PostgreSQL
    - SQLite
    - StarRocks
    - Each with their own SQLAlchemy integration

- **Service Adapters**: External service integrations
    - Email service adapters
    - External API clients
    - File storage adapters (MinIO)
    - Message brokers (Kafka)
    - Caching systems (Redis)

Each adapter includes both concrete implementations and corresponding mocks for testing.

### Configs

The `configs` module manages configuration loading, validation, and injection. It provides:

- Environment-based configuration
- Type-safe configuration through Pydantic models
- Centralized access to configuration values
- Support for various configuration sources (environment variables, files, etc.)

### Helpers

The `helpers` module contains utility functions and classes to simplify common development tasks. It includes several
subgroups:

- **Utils**: General utility functions for dates, strings, errors, files, JWTs, passwords, TOTP, etc.
- **Decorators**: Function and class decorators for atomic transactions, caching, logging, and more
- **Interceptors**: Classes for cross-cutting concerns like logging, tracing, and validation
- **Metaclasses**: Meta-programming utilities for advanced patterns

### Models

The `models` module defines the core data structures used throughout the application:

- **Entities**: Domain model objects
- **DTOs**: Data Transfer Objects for API input/output
- **Errors**: Custom exception classes
- **Types**: Type definitions and enumerations

## Architectural Flow

ArchiPy applications follow a clean architecture approach where:

1. The Models module forms the core domain layer
2. The Helpers module provides supporting functionality
3. The Configs module manages application configuration
4. The Adapters module interfaces with external systems

This modular organization promotes separation of concerns, making ArchiPy applications easier to test, maintain, and
extend over time.

## Design Philosophy

ArchiPy is designed to standardize and simplify Python application development by providing a flexible set of building
blocks that work across different architectural approaches. Rather than enforcing a single architectural pattern,
ArchiPy offers components that can be applied to:

* Layered Architecture
* Hexagonal Architecture (Ports & Adapters)
* Clean Architecture
* Domain-Driven Design
* Service-Oriented Architecture
* And more...

These building blocks help maintain consistency, testability, and maintainability regardless of the specific
architectural style chosen for your project.

## Core Building Blocks

### Configuration Management

ArchiPy provides a standardized way to manage configuration across your application using Pydantic models:

```python
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import PostgresSQLAlchemyConfig
from archipy.configs.environment_type import EnvironmentType

class AppConfig(BaseConfig):
    # Override default configurations as needed
    ENVIRONMENT: EnvironmentType = EnvironmentType.PRODUCTION
    DEBUG: bool = False

    # BaseConfig provides pre-configured templates for:
    # POSTGRES_SQLALCHEMY, REDIS, KAFKA, KEYCLOAK, MINIO, etc.

# Set global configuration (accessible throughout your application)
config = AppConfig()
BaseConfig.set_global(config)

# Access from anywhere
from archipy.configs.base_config import BaseConfig
current_config = BaseConfig.global_config()
```

**📖 Learn more:** [Configuration Management Examples](examples/config_management.md)

### Adapters & Ports

ArchiPy implements the ports and adapters pattern to isolate the application core from external dependencies:

```python
# Port: defines an interface (contract)
from typing import Protocol
from uuid import UUID
from archipy.models.entities.sqlalchemy.base_entities import BaseEntity

class UserRepositoryPort(Protocol):
    def get_by_id(self, user_id: UUID) -> User | None: ...
    def create(self, user: User) -> User: ...

# Adapter: implements the interface for a specific technology
from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter

class SqlAlchemyUserRepository:
    def __init__(self, db_adapter: PostgresSQLAlchemyAdapter):
        self.db_adapter = db_adapter

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.db_adapter.get_by_uuid(User, user_id)

    def create(self, user: User) -> User:
        return self.db_adapter.create(user)

# Application core uses the port, not the adapter
class UserService:
    def __init__(self, repository: UserRepositoryPort):
        self.repository = repository

    def get_user(self, user_id: UUID) -> User | None:
        return self.repository.get_by_id(user_id)
```

**📖 Learn more:** [PostgreSQL Adapter Examples](examples/adapters/postgres.md)

### Entity Models

Standardized entity models provide a consistent approach to domain modeling:

```python
from sqlalchemy import Column, String
from archipy.models.entities.sqlalchemy.base_entities import BaseEntity

class User(BaseEntity):
    __tablename__ = "users"

    name = Column(String(100))
    email = Column(String(255), unique=True)
```

### Data Transfer Objects (DTOs)

Define consistent data structures for transferring data between layers:

```python
from datetime import datetime
from pydantic import EmailStr
from archipy.models.dtos.base_dtos import BaseDTO

class UserCreateDTO(BaseDTO):
    name: str
    email: EmailStr

class UserResponseDTO(BaseDTO):
    id: str
    name: str
    email: EmailStr
    created_at: datetime
```

**📖 Learn more:** [Error Handling Examples](examples/error_handling.md)

## Example Architectures

### Layered Architecture

ArchiPy can be used with a traditional layered architecture approach:

```
┌───────────────────────┐
│     Presentation      │  API, UI, CLI
├───────────────────────┤
│     Application       │  Services, Workflows
├───────────────────────┤
│       Domain          │  Business Logic, Entities
├───────────────────────┤
│    Infrastructure     │  Adapters, Repositories, External Services
└───────────────────────┘
```

### Clean Architecture

ArchiPy supports Clean Architecture principles:

```
┌─────────────────────────────────────────────┐
│                  Entities                    │
│     Domain models, business rules            │
├─────────────────────────────────────────────┤
│                  Use Cases                   │
│     Application services, business workflows │
├─────────────────────────────────────────────┤
│                 Interfaces                   │
│     Controllers, presenters, gateways        │
├─────────────────────────────────────────────┤
│                Frameworks                    │
│     External libraries, UI, DB, devices      │
└─────────────────────────────────────────────┘
```

### Hexagonal Architecture

For projects using a Hexagonal (Ports & Adapters) approach:

```
┌───────────────────────────────────────────────────┐
│                                                   │
│                 Application Core                  │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │                                             │  │
│  │           Domain Logic / Models             │  │
│  │                                             │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
│  ┌─────────────┐         ┌─────────────────────┐  │
│  │             │         │                     │  │
│  │  Input      │         │  Output Ports       │  │
│  │  Ports      │         │                     │  │
│  │             │         │                     │  │
│  └─────────────┘         └─────────────────────┘  │
│                                                   │
└───────────────────────────────────────────────────┘
        ▲                           ▲
        │                           │
        │                           │
┌───────┴──────────┐      ┌────────┴────────────┐
│                  │      │                     │
│  Input Adapters  │      │  Output Adapters    │
│  (Controllers)   │      │  (Repositories,     │
│                  │      │   Clients, etc.)    │
│                  │      │                     │
└──────────────────┘      └─────────────────────┘
```

## Practical Implementation

Let's see how a complete application might be structured using ArchiPy with domain-specific organization:

```
my_app/
├── configs/
│   └── app_config.py              # Application configuration
├── models/
│   ├── dtos/                      # Data Transfer Objects
│   │   ├── user_dtos.py
│   │   └── order_dtos.py
│   ├── entities/                  # Domain entities
│   │   ├── user.py
│   │   └── order.py
│   └── errors/                    # Custom exceptions
│       ├── user_errors.py
│       └── order_errors.py
├── repositories/
│   ├── user/                      # User domain
│   │   ├── adapters/              # User-specific adapters
│   │   │   ├── user_db_adapter.py
│   │   │   └── user_cache_adapter.py
│   │   └── user_repository.py
│   └── order/                     # Order domain
│       ├── adapters/              # Order-specific adapters
│       │   ├── order_db_adapter.py
│       │   └── order_payment_adapter.py
│       └── order_repository.py
├── logic/
│   ├── user/                      # User domain business logic
│   │   ├── user_registration_logic.py
│   │   └── user_authentication_logic.py
│   └── order/                     # Order domain business logic
│       ├── order_creation_logic.py
│       └── order_payment_logic.py
├── services/
│   ├── user/                      # User domain services (FastAPI endpoints)
│   │   ├── v1/                    # API version 1
│   │   │   └── user_service.py
│   │   └── v2/                    # API version 2 (future)
│   │       └── user_service.py
│   └── order/                     # Order domain services (FastAPI endpoints)
│       └── v1/                    # API version 1
│           └── order_service.py
└── main.py                        # Application entry point (run app)
```

## Code Example

Here's how you might structure a FastAPI application using ArchiPy with domain-specific organization:

```python
# models/entities/user.py
from sqlalchemy import Column, String
from archipy.models.entities.sqlalchemy.base_entities import BaseEntity


class User(BaseEntity):
    __tablename__ = "users"

    username = Column(String(100), unique=True)
    email = Column(String(255), unique=True)


# models/dtos/user_dtos.py
from uuid import UUID
from pydantic import EmailStr
from archipy.models.dtos.base_dtos import BaseDTO


# Input DTOs (from service layer)
class UserRegistrationInputDTO(BaseDTO):
    username: str
    email: EmailStr


# Command DTOs (for logic → repository: create, update, delete)
class CreateUserCommandDTO(BaseDTO):
    username: str
    email: EmailStr


class UpdateUserCommandDTO(BaseDTO):
    user_id: UUID
    username: str | None = None
    email: EmailStr | None = None


class DeleteUserCommandDTO(BaseDTO):
    user_id: UUID


# Query DTOs (for logic → repository: get, search)
class GetUserByIdQueryDTO(BaseDTO):
    user_id: UUID


class SearchUsersQueryDTO(BaseDTO):
    username: str | None = None
    email: str | None = None
    limit: int = 10
    offset: int = 0


# Response DTOs (from logic/repository)
class UserResponseDTO(BaseDTO):
    id: str
    username: str
    email: EmailStr


# Output DTOs (to client)
class UserRegistrationOutputDTO(BaseDTO):
    id: str
    username: str
    email: EmailStr


class UserGetOutputDTO(BaseDTO):
    id: str
    username: str
    email: EmailStr


# models/errors/user_errors.py
from archipy.models.errors import AlreadyExistsError


class UserAlreadyExistsError(AlreadyExistsError):
    """Raised when attempting to create a user that already exists."""
    pass


# repositories/user/adapters/user_db_adapter.py
from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter


class UserDBAdapter(PostgresSQLAlchemyAdapter):
    """Database adapter for User domain operations."""
    pass


# repositories/user/adapters/user_cache_adapter.py
from archipy.adapters.redis.adapters import RedisAdapter


class UserCacheAdapter(RedisAdapter):
    """Cache adapter for User domain operations."""

    def get_cache_key(self, user_id: str) -> str:
        return f"user:{user_id}"


# repositories/user/user_repository.py
from uuid import uuid4
from sqlalchemy import select
from repositories.user.adapters.user_db_adapter import UserDBAdapter
from repositories.user.adapters.user_cache_adapter import UserCacheAdapter
from models.entities.user import User
from models.dtos.user_dtos import (
    CreateUserCommandDTO,
    GetUserByIdQueryDTO,
    SearchUsersQueryDTO,
    UserResponseDTO
)
import json


class UserRepository:
    def __init__(
        self,
        db_adapter: UserDBAdapter,
        cache_adapter: UserCacheAdapter | None = None
    ):
        self.db_adapter = db_adapter
        self.cache_adapter = cache_adapter

    def create_user(self, command: CreateUserCommandDTO) -> UserResponseDTO:
        """Create user using Command DTO and return Response DTO."""
        # Convert Command DTO to Entity
        user = User(
            test_uuid=uuid4(),
            username=command.username,
            email=command.email
        )

        # Persist entity
        created_user = self.db_adapter.create(user)

        # Invalidate cache after creation
        if self.cache_adapter and created_user:
            self.cache_adapter.delete(
                self.cache_adapter.get_cache_key(str(created_user.test_uuid))
            )

        # Convert Entity to Response DTO
        return UserResponseDTO(
            id=str(created_user.test_uuid),
            username=created_user.username,
            email=created_user.email
        )

    def get_user_by_id(self, query: GetUserByIdQueryDTO) -> UserResponseDTO | None:
        """Get user using Query DTO and return Response DTO."""
        # Try cache first if available
        if self.cache_adapter:
            cached = self.cache_adapter.get(
                self.cache_adapter.get_cache_key(str(query.user_id))
            )
            if cached:
                data = json.loads(cached)
                return UserResponseDTO(**data)

        # Fetch from database
        user = self.db_adapter.get_by_uuid(User, query.user_id)

        if not user:
            return None

        # Cache the result
        if self.cache_adapter:
            response_data = {
                "id": str(user.test_uuid),
                "username": user.username,
                "email": user.email
            }
            self.cache_adapter.set(
                self.cache_adapter.get_cache_key(str(query.user_id)),
                json.dumps(response_data),
                ex=3600  # 1 hour expiration
            )

        # Convert Entity to Response DTO
        return UserResponseDTO(
            id=str(user.test_uuid),
            username=user.username,
            email=user.email
        )

    def search_users(self, query: SearchUsersQueryDTO) -> list[UserResponseDTO]:
        """Search users using Query DTO and return list of Response DTOs."""
        db_query = select(User)

        if query.username:
            db_query = db_query.where(User.username.ilike(f"%{query.username}%"))
        if query.email:
            db_query = db_query.where(User.email.ilike(f"%{query.email}%"))

        db_query = db_query.limit(query.limit).offset(query.offset)

        users, _ = self.db_adapter.execute_search_query(User, db_query)

        # Convert list of Entities to list of Response DTOs
        return [
            UserResponseDTO(
                id=str(user.test_uuid),
                username=user.username,
                email=user.email
            )
            for user in users
        ]


# logic/user/user_registration_logic.py
from uuid import UUID
from models.dtos.user_dtos import CreateUserCommandDTO, SearchUsersQueryDTO, UserResponseDTO
from models.errors.user_errors import UserAlreadyExistsError
from repositories.user.user_repository import UserRepository


class UserRegistrationLogic:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def register_user(self, username: str, email: str) -> UserResponseDTO:
        """Business logic for user registration.

        This method contains the core business rules:
        - Check if user already exists
        - Create new user via Command DTO
        - Return Response DTO
        """
        # Business rule: Check if user already exists using Query DTO
        search_query = SearchUsersQueryDTO(username=username, limit=1)
        existing_users = self.user_repository.search_users(search_query)

        if existing_users:
            raise UserAlreadyExistsError(
                resource_type="user",
                additional_data={"username": username}
            )

        # Create new user using Command DTO
        command = CreateUserCommandDTO(username=username, email=email)
        return self.user_repository.create_user(command)


# logic/user/user_query_logic.py
from uuid import UUID
from models.dtos.user_dtos import GetUserByIdQueryDTO, SearchUsersQueryDTO, UserResponseDTO
from repositories.user.user_repository import UserRepository
from archipy.models.errors import NotFoundError


class UserQueryLogic:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def get_user_by_id(self, user_id: UUID) -> UserResponseDTO:
        """Get user by ID with business validation using Query DTO."""
        query = GetUserByIdQueryDTO(user_id=user_id)
        user = self.user_repository.get_user_by_id(query)

        if not user:
            raise NotFoundError(
                resource_type="user",
                additional_data={"user_id": str(user_id)}
            )

        return user

    def search_users(self, username: str | None = None) -> list[UserResponseDTO]:
        """Search users using Query DTO - can call other logic if needed."""
        query = SearchUsersQueryDTO(username=username, limit=10)
        return self.user_repository.search_users(query)


# services/user/v1/user_service.py
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from models.dtos.user_dtos import (
    UserRegistrationInputDTO,
    UserRegistrationOutputDTO,
    UserGetOutputDTO
)
from models.errors.user_errors import UserAlreadyExistsError
from archipy.models.errors import NotFoundError
from logic.user.user_registration_logic import UserRegistrationLogic
from logic.user.user_query_logic import UserQueryLogic
from repositories.user.user_repository import UserRepository
from repositories.user.adapters.user_db_adapter import UserDBAdapter
from repositories.user.adapters.user_cache_adapter import UserCacheAdapter

# Create router for user endpoints v1
router = APIRouter(prefix="/api/v1/users", tags=["users-v1"])

# Initialize domain-specific adapters (could be moved to dependency injection)
user_db_adapter = UserDBAdapter()
user_cache_adapter = UserCacheAdapter()


# Dependency injection
def get_user_repository() -> UserRepository:
    """Factory for user repository."""
    return UserRepository(
        db_adapter=user_db_adapter,
        cache_adapter=user_cache_adapter
    )


def get_registration_logic(
    user_repository: UserRepository = Depends(get_user_repository)
) -> UserRegistrationLogic:
    """Factory for user registration logic."""
    return UserRegistrationLogic(user_repository)


def get_query_logic(
    user_repository: UserRepository = Depends(get_user_repository)
) -> UserQueryLogic:
    """Factory for user query logic."""
    return UserQueryLogic(user_repository)


# Service layer endpoints - handle I/O and call logic
@router.post("/", response_model=UserRegistrationOutputDTO, status_code=201)
def register_user(
    input_dto: UserRegistrationInputDTO,
    registration_logic: UserRegistrationLogic = Depends(get_registration_logic)
) -> UserRegistrationOutputDTO:
    """Register a new user.

    Flow: service (Input DTO) → logic (Response DTO) → repository (Command/Query DTO → Response DTO)
    """
    try:
        # Service receives Input DTO, calls logic, gets Response DTO
        response_dto = registration_logic.register_user(
            input_dto.username,
            input_dto.email
        )

        # Convert Response DTO to Output DTO
        return UserRegistrationOutputDTO(
            id=response_dto.id,
            username=response_dto.username,
            email=response_dto.email
        )
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{user_id}", response_model=UserGetOutputDTO)
def get_user(
    user_id: str,
    query_logic: UserQueryLogic = Depends(get_query_logic)
) -> UserGetOutputDTO:
    """Get user by ID.

    Flow: service (Input) → logic (Response DTO) → repository (Query DTO → Response DTO)
    """
    try:
        # Service calls logic with user_id, gets Response DTO
        response_dto = query_logic.get_user_by_id(UUID(user_id))

        # Convert Response DTO to Output DTO
        return UserGetOutputDTO(
            id=response_dto.id,
            username=response_dto.username,
            email=response_dto.email
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")


# main.py
from archipy.helpers.utils.app_utils import AppUtils
from archipy.configs.base_config import BaseConfig
from services.user.v1.user_service import router as user_v1_router
# from services.user.v2.user_service import router as user_v2_router
# from services.order.v1.order_service import router as order_v1_router

# Initialize configuration
config = BaseConfig()
BaseConfig.set_global(config)

# Create FastAPI app
app = AppUtils.create_fastapi_app()

# Include versioned routers from service layers
app.include_router(user_v1_router)
# app.include_router(user_v2_router)  # Future API version
# app.include_router(order_v1_router)

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**📖 Complete guide:** [Getting Started](usage.md)

This structure provides:

- **Clear layer separation**:
  - `main.py` → Initializes app and includes routers (runs the project)
  - `services/{domain}/v1/` → Contains versioned FastAPI endpoints (handles I/O, DTOs) and calls logic
  - `logic/` → Contains pure business rules (can call other logic or repositories)
  - `repositories/` → Data access and persistence

- **API Versioning**:
  - URL path includes version: `/api/v1/users`, `/api/v2/users`
  - Service folders organized by version: `services/user/v1/`, `services/user/v2/`
  - Easy to maintain multiple API versions simultaneously
  - Smooth migration path for API changes

- **Clear DTO Naming Conventions (CQRS-inspired)**:
  - **Input DTOs**: `{Operation}InputDTO` - From client to service (e.g., `UserRegistrationInputDTO`)
  - **Command DTOs**: `{Action}CommandDTO` - For write operations: create, update, delete (e.g., `CreateUserCommandDTO`)
  - **Query DTOs**: `{Action}QueryDTO` - For read operations: get, search, list (e.g., `GetUserByIdQueryDTO`, `SearchUsersQueryDTO`)
  - **Response DTOs**: `{Domain}ResponseDTO` - From repository/logic (e.g., `UserResponseDTO`)
  - **Output DTOs**: `{Operation}OutputDTO` - From service to client (e.g., `UserRegistrationOutputDTO`, `UserGetOutputDTO`)
  - Clear separation of concerns at each layer
  - Self-documenting API interfaces with explicit operation context

- **Service layer (FastAPI endpoints)**:
  - Each service module has its own versioned APIRouter
  - Handles HTTP I/O (request/response)
  - Converts InputDTO → calls logic → receives ResponseDTO → converts to OutputDTO
  - Calls logic layer for business operations
  - Handles HTTP exceptions

- **Logic layer (Business rules)**:
  - Pure business logic isolated from HTTP/I/O
  - Creates Command/Query DTOs to call repositories
  - Receives ResponseDTO from repositories
  - Can call other logic classes or repositories
  - Returns ResponseDTO to service layer
  - Framework-agnostic (no FastAPI, no HTTP)
  - Easy to unit test without mocking HTTP
  - Reusable across different interfaces (REST, GraphQL, CLI, gRPC, etc.)

- **Repository layer (Data access)**:
  - Accepts CommandDTO (create, update, delete) or QueryDTO (get, search)
  - Converts DTO → Entity for database operations
  - Converts Entity → ResponseDTO before returning
  - Always returns ResponseDTO (never raw entities)
  - Clean separation between data layer and business layer

- **Main.py (Application runner)**:
  - Initializes configuration
  - Creates FastAPI app
  - Includes all versioned service routers
  - Runs the application

- **Domain-driven organization**: User and Order domains have their own adapters, repositories, logic, and versioned service endpoints
- **Domain-specific adapters**: Each domain has its own adapter layer (e.g., `UserDBAdapter`, `UserCacheAdapter`)
- **Scalability**: Easy to add new domains, endpoints, API versions, or logic without affecting existing ones
- **Testability**: Each layer can be tested independently (logic without HTTP, services with HTTP mocking)
- **Maintainability**: Related code (adapters, logic, versioned endpoints) is grouped together by domain
- **Flexibility**: Different domains can use different storage strategies, business rules, and API patterns

By providing standardized building blocks rather than enforcing a specific architecture, ArchiPy helps teams maintain
consistent development practices while allowing flexibility to choose the architectural pattern that best fits their
needs.
