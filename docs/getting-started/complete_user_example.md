---
title: Complete User Example
description: End-to-end ArchiPy application — entities, DTOs, adapters, repository, logic, DI container, FastAPI service, and entry point for a User domain.
---

# Complete User Example

This page walks through every layer of a real ArchiPy application for a **User** domain, from the database
entity all the way to the FastAPI endpoint and `main.py`. Each section corresponds to one layer in the
[four-layer architecture](../getting-started/concepts.md).

---

## Project Layout

```
my_app/
├── configs/
│   ├── app_config.py
│   └── containers.py
├── models/
│   ├── dtos/
│   │   └── user/
│   │       ├── domain/v1/user_dtos.py      # versioned — cross service boundary
│   │       └── repository/user_dtos.py     # internal — never versioned
│   ├── entities/user.py
│   └── errors/user_errors.py
├── repositories/
│   └── user/
│       ├── adapters/
│       │   ├── user_db_adapter.py
│       │   └── user_cache_adapter.py
│       └── user_repository.py
├── logics/
│   └── user/
│       ├── user_registration_logic.py
│       └── user_query_logic.py
├── services/
│   └── user/v1/user_service.py
└── main.py
```

---

## Configuration

```python
# configs/app_config.py
from archipy.configs.base_config import BaseConfig


class AppConfig(BaseConfig):
    """Application-specific configuration.

    All ArchiPy sections (REDIS, POSTGRES, FASTAPI, …) are inherited from BaseConfig.
    Add custom fields below.
    """

    APP_NAME: str = "my-service"
    DEBUG: bool = False


config = AppConfig()
BaseConfig.set_global(config)
```

---

## Entity

```python
# models/entities/user.py
import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Synonym, mapped_column

from archipy.models.entities.sqlalchemy.base_entities import BaseEntity


class User(BaseEntity):
    """User domain entity."""

    __tablename__ = "users"

    user_uuid = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pk_uuid = Synonym("user_uuid")

    username = mapped_column(String(100), unique=True, nullable=False)
    email = mapped_column(String(255), unique=True, nullable=False)
```

---

## DTOs

DTOs are split into two groups:

| Group          | Purpose                                       | Location                     | Versioned? |
|----------------|-----------------------------------------------|------------------------------|------------|
| **Domain**     | Cross the service boundary (client ↔ service) | `dtos/{domain}/domain/v{n}/` | Yes        |
| **Repository** | Internal (logic ↔ repository ↔ adapter)       | `dtos/{domain}/repository/`  | No         |

```python
# models/dtos/user/domain/v1/user_dtos.py
from uuid import UUID

from pydantic import EmailStr

from archipy.models.dtos.base_dtos import BaseDTO


class UserRegistrationInputDTO(BaseDTO):
    """Incoming registration request from the client."""

    username: str
    email: EmailStr


class UserRegistrationOutputDTO(BaseDTO):
    """Response returned to the client after registration."""

    id: str
    username: str
    email: EmailStr


class UserGetInputDTO(BaseDTO):
    """Request to retrieve a single user by ID."""

    user_id: UUID


class UserGetOutputDTO(BaseDTO):
    """Response for a single user lookup."""

    id: str
    username: str
    email: EmailStr


class UserSearchInputDTO(BaseDTO):
    """Search filters from the client."""

    username: str | None = None
    limit: int = 20


class UserSearchOutputDTO(BaseDTO):
    """Paginated search results returned to the client."""

    users: list["UserSummaryOutputDTO"]


class UserSummaryOutputDTO(BaseDTO):
    """Compact user representation used inside search results."""

    id: str
    username: str
    email: EmailStr
```

```python
# models/dtos/user/repository/user_dtos.py
from uuid import UUID

from pydantic import EmailStr

from archipy.models.dtos.base_dtos import BaseDTO


class CreateUserCommandDTO(BaseDTO):
    """Command DTO for creating a new user record."""

    username: str
    email: EmailStr


class GetUserByIdQueryDTO(BaseDTO):
    """Query DTO for retrieving a single user by UUID."""

    user_id: UUID


class SearchUsersQueryDTO(BaseDTO):
    """Query DTO for searching users by optional username filter."""

    username: str | None = None
    limit: int = 20


class UserResponseDTO(BaseDTO):
    """Internal result DTO returned from the repository layer."""

    id: str
    username: str
    email: EmailStr
```

---

## Custom Error

```python
# models/errors/user_errors.py
from archipy.models.errors import AlreadyExistsError


class UserAlreadyExistsError(AlreadyExistsError):
    """Raised when a registration attempt uses a username that already exists."""
```

---

## Domain Adapters

Domain adapters wrap an ArchiPy base adapter and own all entity construction and query logic for a
single aggregate.

```python
# repositories/user/adapters/user_db_adapter.py
import logging
from uuid import UUID, uuid4

from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter

from models.dtos.user.repository.user_dtos import CreateUserCommandDTO, SearchUsersQueryDTO, UserResponseDTO
from models.entities.user import User

logger = logging.getLogger(__name__)


class UserDBAdapter:
    """Wraps PostgresSQLAlchemyAdapter for the User aggregate."""

    def __init__(self, db: PostgresSQLAlchemyAdapter) -> None:
        self._adapter = db

    def create_user(self, command: CreateUserCommandDTO) -> UserResponseDTO:
        """Persist a new User entity and return a response DTO.

        Args:
            command: Create command with username and email.

        Returns:
            Response DTO for the newly created user.
        """
        user = User(user_uuid=uuid4(), username=command.username, email=command.email)
        created = self._adapter.create(user)
        logger.debug("Created user %s", created.user_uuid)
        return UserResponseDTO(id=str(created.user_uuid), username=created.username, email=created.email)

    def get_user_by_id(self, query: "GetUserByIdQueryDTO") -> UserResponseDTO | None:
        """Retrieve a User by UUID.

        Args:
            query: Query with the target user UUID.

        Returns:
            Response DTO, or None if not found.
        """
        from models.dtos.user.repository.user_dtos import GetUserByIdQueryDTO  # noqa: PLC0415

        user = self._adapter.get_by_uuid(User, query.user_id)
        if not user:
            return None
        return UserResponseDTO(id=str(user.user_uuid), username=user.username, email=user.email)

    def search_users(self, query: SearchUsersQueryDTO) -> list[UserResponseDTO]:
        """Search users by optional username filter.

        Args:
            query: Search filters.

        Returns:
            List of matching response DTOs.
        """
        users = self._adapter.filter_by(User, username=query.username, limit=query.limit)
        return [UserResponseDTO(id=str(u.user_uuid), username=u.username, email=u.email) for u in users]
```

```python
# repositories/user/adapters/user_cache_adapter.py
import logging

from archipy.adapters.redis.ports import RedisPort

from models.dtos.user.repository.user_dtos import UserResponseDTO

logger = logging.getLogger(__name__)

_USER_TTL = 3600  # seconds


class UserCacheAdapter:
    """Cache adapter for the User aggregate — wraps a RedisPort implementation."""

    def __init__(self, cache: RedisPort) -> None:
        self._cache = cache

    def get_user(self, user_id: str) -> UserResponseDTO | None:
        """Read a cached user response DTO.

        Args:
            user_id: String UUID of the user.

        Returns:
            Cached UserResponseDTO, or None on cache miss.
        """
        import json  # noqa: PLC0415

        raw = self._cache.get(f"user:{user_id}")
        if raw is None:
            return None
        logger.debug("Cache hit for user %s", user_id)
        return UserResponseDTO.model_validate(json.loads(raw))

    def set_user(self, user_id: str, response: UserResponseDTO) -> None:
        """Write a user response DTO to the cache.

        Args:
            user_id: String UUID used as cache key suffix.
            response: DTO to serialise and store.
        """
        self._cache.set(f"user:{user_id}", response.model_dump_json(), ex=_USER_TTL)
        logger.debug("Cached user %s for %ds", user_id, _USER_TTL)
```

---

## Repository

```python
# repositories/user/user_repository.py
import logging

from models.dtos.user.repository.user_dtos import (
    CreateUserCommandDTO,
    GetUserByIdQueryDTO,
    SearchUsersQueryDTO,
    UserResponseDTO,
)
from repositories.user.adapters.user_cache_adapter import UserCacheAdapter
from repositories.user.adapters.user_db_adapter import UserDBAdapter

logger = logging.getLogger(__name__)


class UserRepository:
    """Orchestrates DB and cache adapters for the User aggregate."""

    def __init__(self, db_adapter: UserDBAdapter, cache_adapter: UserCacheAdapter) -> None:
        self._db = db_adapter
        self._cache = cache_adapter

    def create_user(self, command: CreateUserCommandDTO) -> UserResponseDTO:
        """Create a new user and prime the cache.

        Args:
            command: Create command with username and email.

        Returns:
            Response DTO for the new user.
        """
        response = self._db.create_user(command)
        self._cache.set_user(response.id, response)
        return response

    def get_user_by_id(self, query: GetUserByIdQueryDTO) -> UserResponseDTO | None:
        """Return a user by ID, reading from cache first.

        Args:
            query: Query with the target user UUID.

        Returns:
            Response DTO, or None if the user does not exist.
        """
        cached = self._cache.get_user(str(query.user_id))
        if cached:
            return cached
        response = self._db.get_user_by_id(query)
        if response:
            self._cache.set_user(response.id, response)
        return response

    def search_users(self, query: SearchUsersQueryDTO) -> list[UserResponseDTO]:
        """Search users by optional username filter (always hits the DB).

        Args:
            query: Search filters.

        Returns:
            List of matching response DTOs.
        """
        return self._db.search_users(query)
```

---

## Logic Layer

```python
# logics/user/user_registration_logic.py
import logging

from archipy.helpers.decorators.sqlalchemy_atomic import postgres_sqlalchemy_atomic_decorator

from models.dtos.user.domain.v1.user_dtos import UserRegistrationInputDTO, UserRegistrationOutputDTO
from models.dtos.user.repository.user_dtos import CreateUserCommandDTO, SearchUsersQueryDTO
from models.errors.user_errors import UserAlreadyExistsError
from repositories.user.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserRegistrationLogic:
    """Business logic for registering new users."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._repo = user_repository

    @postgres_sqlalchemy_atomic_decorator
    def register_user(self, input_dto: UserRegistrationInputDTO) -> UserRegistrationOutputDTO:
        """Validate uniqueness and persist a new user.

        Args:
            input_dto: Registration data from the service layer.

        Returns:
            Output DTO for the newly created user.

        Raises:
            UserAlreadyExistsError: If the username is already taken.
        """
        existing = self._repo.search_users(SearchUsersQueryDTO(username=input_dto.username, limit=1))
        if existing:
            raise UserAlreadyExistsError(
                resource_type="user",
                additional_data={"username": input_dto.username},
            )
        created = self._repo.create_user(
            CreateUserCommandDTO(username=input_dto.username, email=input_dto.email),
        )
        return UserRegistrationOutputDTO(id=created.id, username=created.username, email=created.email)
```

```python
# logics/user/user_query_logic.py
import logging

from archipy.helpers.decorators.sqlalchemy_atomic import postgres_sqlalchemy_atomic_decorator
from archipy.models.errors import NotFoundError

from models.dtos.user.domain.v1.user_dtos import (
    UserGetInputDTO,
    UserGetOutputDTO,
    UserSearchInputDTO,
    UserSearchOutputDTO,
    UserSummaryOutputDTO,
)
from models.dtos.user.repository.user_dtos import GetUserByIdQueryDTO, SearchUsersQueryDTO
from repositories.user.user_repository import UserRepository

logger = logging.getLogger(__name__)


class UserQueryLogic:
    """Business logic for querying user data."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._repo = user_repository

    @postgres_sqlalchemy_atomic_decorator
    def get_user_by_id(self, input_dto: UserGetInputDTO) -> UserGetOutputDTO:
        """Retrieve a user by ID.

        Args:
            input_dto: Contains the UUID of the user.

        Returns:
            Output DTO for the matched user.

        Raises:
            NotFoundError: If no user with the given ID exists.
        """
        user = self._repo.get_user_by_id(GetUserByIdQueryDTO(user_id=input_dto.user_id))
        if not user:
            raise NotFoundError(resource_type="user", additional_data={"user_id": str(input_dto.user_id)})
        return UserGetOutputDTO(id=user.id, username=user.username, email=user.email)

    @postgres_sqlalchemy_atomic_decorator
    def search_users(self, input_dto: UserSearchInputDTO) -> UserSearchOutputDTO:
        """Search users by optional username filter.

        Args:
            input_dto: Search filters from the service layer.

        Returns:
            Output DTO wrapping the list of matched users.
        """
        results = self._repo.search_users(SearchUsersQueryDTO(username=input_dto.username, limit=input_dto.limit))
        return UserSearchOutputDTO(
            users=[UserSummaryOutputDTO(id=u.id, username=u.username, email=u.email) for u in results],
        )
```

---

## DI Container

```python
# configs/containers.py
import configs.app_config  # noqa: F401 — importing triggers BaseConfig.set_global

from dependency_injector import containers, providers

from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.adapters.redis.adapters import RedisAdapter

from logics.user.user_query_logic import UserQueryLogic
from logics.user.user_registration_logic import UserRegistrationLogic
from repositories.user.adapters.user_cache_adapter import UserCacheAdapter
from repositories.user.adapters.user_db_adapter import UserDBAdapter
from repositories.user.user_repository import UserRepository


class UserContainer(containers.DeclarativeContainer):
    """Wires the User domain dependency graph as thread-safe singletons."""

    _postgres: providers.Provider[PostgresSQLAlchemyAdapter] = providers.ThreadSafeSingleton(
        PostgresSQLAlchemyAdapter,
    )

    _redis: providers.Provider[RedisAdapter] = providers.ThreadSafeSingleton(
        RedisAdapter,
    )

    _db_adapter: providers.Provider[UserDBAdapter] = providers.ThreadSafeSingleton(
        UserDBAdapter,
        db=_postgres,
    )

    _cache_adapter: providers.Provider[UserCacheAdapter] = providers.ThreadSafeSingleton(
        UserCacheAdapter,
        cache=_redis,
    )

    _repository: providers.Provider[UserRepository] = providers.ThreadSafeSingleton(
        UserRepository,
        db_adapter=_db_adapter,
        cache_adapter=_cache_adapter,
    )

    registration_logic: providers.Provider[UserRegistrationLogic] = providers.ThreadSafeSingleton(
        UserRegistrationLogic,
        user_repository=_repository,
    )

    query_logic: providers.Provider[UserQueryLogic] = providers.ThreadSafeSingleton(
        UserQueryLogic,
        user_repository=_repository,
    )
```

---

## FastAPI Service

```python
# services/user/v1/user_service.py
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from archipy.models.errors import NotFoundError

from configs.containers import UserContainer
from logics.user.user_query_logic import UserQueryLogic
from logics.user.user_registration_logic import UserRegistrationLogic
from models.dtos.user.domain.v1.user_dtos import (
    UserGetInputDTO,
    UserGetOutputDTO,
    UserRegistrationInputDTO,
    UserRegistrationOutputDTO,
)
from models.errors.user_errors import UserAlreadyExistsError

logger = logging.getLogger(__name__)


def create_router(container: UserContainer) -> APIRouter:
    """Build the versioned user router wired to the given DI container.

    Args:
        container: The DI container providing logic instances.

    Returns:
        A configured APIRouter for the User domain.
    """
    router = APIRouter(prefix="/api/v1/users", tags=["users-v1"])

    @router.post("/", response_model=UserRegistrationOutputDTO, status_code=201)
    def register_user(
        input_dto: UserRegistrationInputDTO,
        registration_logic: UserRegistrationLogic = Depends(container.registration_logic),
    ) -> UserRegistrationOutputDTO:
        """Register a new user.

        Args:
            input_dto: Registration payload from the client.
            registration_logic: Injected by the DI container.

        Returns:
            Output DTO for the newly created user.

        Raises:
            HTTPException: 409 if the username is already taken.
        """
        try:
            return registration_logic.register_user(input_dto)
        except UserAlreadyExistsError as e:
            raise HTTPException(status_code=409, detail=str(e)) from e

    @router.get("/{user_id}", response_model=UserGetOutputDTO)
    def get_user(
        user_id: str,
        query_logic: UserQueryLogic = Depends(container.query_logic),
    ) -> UserGetOutputDTO:
        """Retrieve a user by ID.

        Args:
            user_id: String representation of the user's UUID.
            query_logic: Injected by the DI container.

        Returns:
            Output DTO for the matched user.

        Raises:
            HTTPException: 404 if no user with the given ID exists.
            HTTPException: 400 if the user_id is not a valid UUID.
        """
        try:
            return query_logic.get_user_by_id(UserGetInputDTO(user_id=UUID(user_id)))
        except NotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid user ID format") from e

    return router
```

---

## Entry Point

```python
# main.py
from archipy.helpers.utils.app_utils import AppUtils

import configs.app_config  # noqa: F401 — importing triggers BaseConfig.set_global
from configs.containers import UserContainer
from services.user.v1.user_service import create_router as create_user_v1_router

user_container = UserContainer()

app = AppUtils.create_fastapi_app()
app.include_router(create_user_v1_router(user_container))

if __name__ == "__main__":
    import uvicorn
    from archipy.configs.base_config import BaseConfig

    config = BaseConfig.global_config()
    uvicorn.run(app, host="0.0.0.0", port=8000)  # noqa: S104
```

---

## See Also

- [Concepts](concepts.md) — four-layer architecture and import rules
- [Project Structure](project_structure.md) — reference folder layout
- [Dependency Injection](../examples/dependency_injection.md) — DI container patterns in depth
- [Configuration Management](../examples/config_management.md) — environment variables and `.env` files
- [Error Handling](../examples/error_handling.md) — custom errors and HTTP mapping
- [Testing Strategy](../examples/testing_strategy.md) — BDD testing with mock adapters
