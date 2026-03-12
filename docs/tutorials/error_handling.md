---
title: Error Handling
description: Practical tutorials for error handling patterns in ArchiPy.
---

# Error Handling

This document provides examples of how to use the error handling system in different scenarios.

!!! note "Always use specific exception types"
ArchiPy errors extend `BaseError` and map to standard HTTP status codes automatically when used
with the FastAPI integration. Never catch or raise bare `Exception` — use the most specific type available.

!!! danger "Never swallow exceptions silently"
Always either re-raise (with `raise ... from e`) or log and raise. Swallowing exceptions hides
bugs and makes debugging nearly impossible in production.

## Basic Error Handling

```python
import logging

from archipy.models.errors import (
    InvalidArgumentError,
    NotFoundError,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)

# Simulated dependencies (replace with actual implementations in your app)
user_repository: "UserRepository"  # type: ignore[name-defined]


def has_admin_access() -> bool:
    """Return True if the current user has admin access."""
    return False  # Placeholder


def get_user(user_id: str) -> dict[str, str]:
    """Fetch a user by ID.

    Args:
        user_id: The user's unique identifier.

    Returns:
        The user data dictionary.

    Raises:
        NotFoundError: If the user does not exist.
    """
    try:
        user = user_repository.find_by_id(user_id)  # type: ignore[name-defined]
        if not user:
            raise NotFoundError(
                resource_type="user",
                additional_data={"user_id": user_id},
            )
        return user
    except NotFoundError as e:
        logger.error(f"User not found: {e.to_dict()}")
        raise


def update_user_permissions(user_id: str, permissions: list[str]) -> None:
    """Update a user's permissions.

    Args:
        user_id: The user's unique identifier.
        permissions: List of permission strings to assign.

    Raises:
        InvalidArgumentError: If permissions is not a list.
        PermissionDeniedError: If the caller lacks admin access.
    """
    try:
        if not isinstance(permissions, list):
            raise InvalidArgumentError(
                argument="permissions",
                additional_data={"detail": "Permissions must be a list"},
            )

        if not has_admin_access():
            raise PermissionDeniedError(
                operation="update_permissions",
                additional_data={"detail": "Admin access required"},
            )

        user_repository.update_permissions(user_id, permissions)  # type: ignore[name-defined]
    except (InvalidArgumentError, PermissionDeniedError) as e:
        logger.error(f"Failed to update permissions: {e.to_dict()}")
        raise
```

## Business Logic Error Handling

```python
import logging

from archipy.models.errors import (
    BusinessRuleViolationError,
    InsufficientFundsError,
    InvalidStateError,
)

logger = logging.getLogger(__name__)


def process_transaction(account_id: str, amount: float) -> None:
    """Process a financial transaction.

    Args:
        account_id: The account's unique identifier.
        amount: The transaction amount.

    Raises:
        InvalidStateError: If the account is not active.
        InsufficientFundsError: If the account lacks sufficient funds.
        BusinessRuleViolationError: If the amount exceeds the transaction limit.
    """
    try:
        account = account_repository.find_by_id(account_id)  # type: ignore[name-defined]
        if not account.is_active:
            raise InvalidStateError(
                current_state="inactive",
                expected_state="active",
            )

        if account.balance < amount:
            raise InsufficientFundsError(
                additional_data={"required": amount, "available": account.balance},
            )

        if amount > account.transaction_limit:
            raise BusinessRuleViolationError(
                rule="transaction_limit",
                additional_data={"limit": account.transaction_limit},
            )

        account_repository.process_transaction(account_id, amount)  # type: ignore[name-defined]
    except (InsufficientFundsError, BusinessRuleViolationError, InvalidStateError) as e:
        logger.error(f"Transaction failed: {e.to_dict()}")
        raise
```

## System Error Handling

```python
import logging
import time
from collections.abc import Callable
from typing import Any

from archipy.models.errors import (
    DatabaseConnectionError,
    DeadlockDetectedError,
    ResourceExhaustedError,
)

logger = logging.getLogger(__name__)


def execute_with_retry(operation: Callable[[], Any], max_retries: int = 3) -> Any:
    """Execute an operation with automatic retry on deadlock.

    Args:
        operation: A callable to execute.
        max_retries: Maximum number of retry attempts.

    Returns:
        The return value of the operation.

    Raises:
        DeadlockDetectedError: If max retries are exceeded.
        DatabaseConnectionError: On connection failure (not retried).
        ResourceExhaustedError: On resource exhaustion (not retried).
    """
    retries = 0
    while retries < max_retries:
        try:
            return operation()
        except DeadlockDetectedError as e:
            retries += 1
            if retries == max_retries:
                logger.error(f"Max retries exceeded: {e.to_dict()}")
                raise
            logger.warning(f"Deadlock detected, retrying ({retries}/{max_retries})")
            time.sleep(1)
        except DatabaseConnectionError as e:
            logger.error(f"Database connection failed: {e.to_dict()}")
            raise
        except ResourceExhaustedError as e:
            logger.error(f"Resource exhausted: {e.to_dict()}")
            raise
    return None


def process_batch(items: list[dict[str, Any]]) -> dict[str, Any]:
    """Process a batch of items with retry logic.

    Args:
        items: List of item dictionaries to process.

    Returns:
        A result dict or an error dict on final failure.
    """

    def batch_operation() -> Any:
        return database.batch_insert(items)  # type: ignore[name-defined]

    try:
        return execute_with_retry(batch_operation)
    except (DeadlockDetectedError, DatabaseConnectionError, ResourceExhaustedError) as e:
        return {"error": e.to_dict()}
```

## Error Response Formatting

```python
import logging
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from archipy.models.errors import BaseError, NotFoundError
from archipy.models.types.language_type import LanguageType

logger = logging.getLogger(__name__)

app = FastAPI()


def handle_error(error: BaseError) -> dict[str, Any]:  # type: ignore[name-defined]
    """Convert error to API response format.

    Args:
        error: The ArchiPy BaseError instance.

    Returns:
        A dictionary with status, error details, and timestamp.
    """
    error_dict = error.to_dict()
    return {
        "status": "error",
        "error": error_dict,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.exception_handler(BaseError)
async def error_handler(request: Request, exc: BaseError) -> JSONResponse:
    """Handle all ArchiPy domain errors uniformly.

    Args:
        request: The incoming HTTP request.
        exc: The raised BaseError instance.

    Returns:
        A JSON response with error details.
    """
    return JSONResponse(
        status_code=exc.http_status_code or 500,
        content=handle_error(exc),
    )


@app.get("/users/{user_id}")
async def get_user_endpoint(user_id: str) -> dict[str, Any]:  # type: ignore[name-defined]
    """Get user by ID.

    Args:
        user_id: The user's unique identifier.

    Returns:
        A success response containing the user data.

    Raises:
        NotFoundError: If the user does not exist.
    """
    try:
        user = user_service.get_user(user_id)  # type: ignore[name-defined]
        return {"status": "success", "data": user}
    except NotFoundError:
        raise
```

## Error Logging and Monitoring

```python
import logging

import sentry_sdk

from archipy.models.errors import (
    BaseError,
    ConfigurationError,
    InternalError,
    UnknownError,
)

logger = logging.getLogger(__name__)


def log_error(error: BaseError, context: dict[str, Any] | None = None) -> None:  # type: ignore[name-defined]
    """Log error with context and send to monitoring service.

    Args:
        error: The ArchiPy BaseError instance.
        context: Optional additional context for the error.
    """
    error_dict = error.to_dict()

    if context:
        error_dict["context"] = context

    logger.error(
        f"Error occurred: {error_dict['error']}",
        extra={"error": error_dict},
    )

    if isinstance(error, (InternalError, UnknownError, ConfigurationError)):
        sentry_sdk.capture_exception(error)


def process_request(request_data: dict[str, Any]) -> Any:  # type: ignore[name-defined]
    """Process an incoming request.

    Args:
        request_data: The request payload dictionary.

    Returns:
        The processing result.

    Raises:
        BaseError: On any domain error during processing.
    """
    try:
        result = service.process(request_data)  # type: ignore[name-defined]
        return result
    except BaseError as e:
        log_error(e, context={"request_data": request_data})
        raise
```

## Exception Chaining

```python
import logging
from uuid import UUID

from archipy.models.entities.sqlalchemy.base_entities import BaseEntity
from archipy.models.errors import (
    DatabaseQueryError,
    InvalidEntityTypeError,
    NotFoundError,
)

logger = logging.getLogger(__name__)


def fetch_entity(entity_type: type[BaseEntity], entity_uuid: UUID) -> BaseEntity:
    """Fetch an entity by type and UUID, chaining exceptions.

    Args:
        entity_type: The SQLAlchemy entity class to query.
        entity_uuid: The UUID of the entity to fetch.

    Returns:
        The fetched entity.

    Raises:
        NotFoundError: If no entity with the given UUID exists.
        DatabaseQueryError: On any underlying database error.
    """
    try:
        result = session.get(entity_type, entity_uuid)  # type: ignore[name-defined]
        if not result:
            raise NotFoundError(
                resource_type=entity_type.__name__,
                additional_data={"uuid": str(entity_uuid)},
            )
        return result
    except (NotFoundError, DatabaseQueryError):
        raise
    except Exception as e:
        raise DatabaseQueryError() from e


def validate_entity(entity: object) -> None:
    """Validate that an entity is a BaseEntity subclass.

    Args:
        entity: The object to validate.

    Raises:
        InvalidEntityTypeError: If the entity is not a BaseEntity subclass.
    """
    if not isinstance(entity, BaseEntity):
        raise InvalidEntityTypeError(
            expected_type="BaseEntity",
            actual_type=type(entity).__name__,
        )
```

## Error Recovery Strategies

```python
import gc
import logging
from collections.abc import Callable
from typing import Any

from archipy.models.errors import (
    CacheMissError,
    ResourceExhaustedError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


class ErrorRecovery:
    """Provides recovery strategies for common domain errors."""

    @staticmethod
    def handle_cache_miss(error: CacheMissError) -> Any:
        """Handle cache miss by fetching from primary source.

        Args:
            error: The CacheMissError instance.

        Returns:
            The data fetched from the primary source.

        Raises:
            CacheMissError: If recovery from the primary source also fails.
        """
        try:
            data = database.get(error.key)  # type: ignore[name-defined]
            cache.set(error.key, data)  # type: ignore[name-defined]
            return data
        except Exception as e:
            logger.error(f"Failed to recover from cache miss: {e}")
            raise

    @staticmethod
    def handle_service_unavailable(error: ServiceUnavailableError) -> Any:
        """Handle service unavailability with fallback.

        Args:
            error: The ServiceUnavailableError instance.

        Returns:
            Data from the fallback service.

        Raises:
            ServiceUnavailableError: If the fallback service is also unavailable.
        """
        if error.service == "primary":  # type: ignore[attr-defined]
            try:
                return fallback_service.get_data()  # type: ignore[name-defined]
            except Exception as e:
                raise ServiceUnavailableError(
                    additional_data={"detail": "Both primary and fallback services unavailable"},
                ) from e
        raise error

    @staticmethod
    def handle_resource_exhaustion(error: ResourceExhaustedError) -> Any:
        """Handle resource exhaustion with cleanup.

        Args:
            error: The ResourceExhaustedError instance.

        Returns:
            Result of the retried operation after cleanup.

        Raises:
            ResourceExhaustedError: If exhaustion persists after cleanup.
        """
        if error.resource_type == "memory":  # type: ignore[attr-defined]
            gc.collect()
            try:
                return retry_operation()  # type: ignore[name-defined]
            except Exception as e:
                raise ResourceExhaustedError(
                    additional_data={"detail": "Resource exhaustion persisted after cleanup"},
                ) from e
        raise error


def get_data(key: str) -> Any:
    """Get data by key, with automatic error recovery.

    Args:
        key: The cache or storage key.

    Returns:
        The retrieved data.
    """
    try:
        return cache.get(key)  # type: ignore[name-defined]
    except CacheMissError as e:
        return ErrorRecovery.handle_cache_miss(e)
    except ServiceUnavailableError as e:
        return ErrorRecovery.handle_service_unavailable(e)
    except ResourceExhaustedError as e:
        return ErrorRecovery.handle_resource_exhaustion(e)
```

## See Also

- [API Reference - Errors](../api_reference/models/errors.md) - Full error model API documentation
- [Tutorials Overview](index.md) - Overview of all tutorials
