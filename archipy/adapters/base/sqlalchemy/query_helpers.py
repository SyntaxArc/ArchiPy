"""Count-cache and entity-validation helpers shared by the sync and async base SQLAlchemy adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NoReturn

from archipy.models.entities import BaseEntity
from archipy.models.errors import ConfigurationError, InvalidEntityTypeError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from sqlalchemy import Result

    from archipy.configs.config_template import SQLAlchemyConfig


def _released_compute() -> NoReturn:
    raise RuntimeError("The count request was already run")  # noqa: TRY003


class _CountRequest:
    """A count to compute, hashed and compared by its cache key only.

    The cache decorators key on every argument. The session and the query are not part of the identity of a count,
    so they travel inside ``compute`` and stay out of the key. The runner releases ``compute`` after the count, so a
    cached key never keeps the session or the query alive.
    """

    __slots__ = ("compute", "key")

    def __init__(self, key: tuple[str, str, int | None], compute: Callable[[], Any]) -> None:
        self.key = key
        self.compute = compute

    def __hash__(self) -> int:
        return hash(self.key)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _CountRequest) and self.key == other.key


def _run_count_request(request: _CountRequest) -> int:
    try:
        return request.compute()
    finally:
        request.compute = _released_compute


async def _run_async_count_request(request: _CountRequest) -> int:
    try:
        return await request.compute()
    finally:
        request.compute = _released_compute


def _build_count_cache(config: SQLAlchemyConfig) -> Callable[[_CountRequest], int] | None:
    """Create the cached count runner when the config enables it (needs the ``cache`` extra)."""
    if not config.COUNT_CACHE_ENABLED:
        return None
    from archipy.helpers.decorators.ttl_caching import ttl_cache  # noqa: PLC0415  # optional "cache" extra

    return ttl_cache(ttl_seconds=config.COUNT_CACHE_TTL_SECONDS, maxsize=config.COUNT_CACHE_MAX_SIZE)(
        _run_count_request,
    )


def _build_async_count_cache(config: SQLAlchemyConfig) -> Callable[[_CountRequest], Awaitable[int]] | None:
    """Create the cached async count runner when the config enables it (needs the ``cache`` extra).

    Raises:
        ConfigurationError: If the count cache is enabled but ``async-lru`` is not installed.
    """
    if not config.COUNT_CACHE_ENABLED:
        return None
    try:
        from async_lru import alru_cache  # noqa: PLC0415  # optional "cache" extra
    except ImportError as exception:
        raise ConfigurationError(
            operation="count_cache",
            reason="async-lru is not installed; install it with archipy[cache]",
        ) from exception

    return alru_cache(ttl=config.COUNT_CACHE_TTL_SECONDS, maxsize=config.COUNT_CACHE_MAX_SIZE)(
        _run_async_count_request,
    )


def _ensure_entity(entity: object) -> None:
    """Raise if the object is not a BaseEntity instance.

    Raises:
        InvalidEntityTypeError: If the object is not a BaseEntity instance.
    """
    if not isinstance(entity, BaseEntity):
        raise InvalidEntityTypeError(
            message=f"Expected BaseEntity subclass, got {type(entity).__name__}",
            expected_type="BaseEntity",
            actual_type=type(entity).__name__,
        )


def _ensure_entities(entities: list[Any]) -> None:
    """Raise if any item is not a BaseEntity instance.

    Raises:
        InvalidEntityTypeError: If any item is not a BaseEntity instance.
    """
    if not all(isinstance(entity, BaseEntity) for entity in entities):
        raise InvalidEntityTypeError(
            message="All entities must be BaseEntity subclasses",
            expected_type="BaseEntity",
            actual_type="mixed",
        )


def _ensure_entity_type(entity_type: type) -> None:
    """Raise if the class is not a BaseEntity subclass.

    Raises:
        InvalidEntityTypeError: If the class is not a BaseEntity subclass.
    """
    if not issubclass(entity_type, BaseEntity):
        raise InvalidEntityTypeError(
            message=f"Expected BaseEntity subclass, got {entity_type.__name__}",
            expected_type="BaseEntity",
            actual_type=entity_type.__name__,
        )


def _extract_entities[E: BaseEntity](result_set: Result[Any], entity: type[E], has_multiple_entities: bool) -> list[E]:
    """Extract entities of the requested type from a search result.

    Args:
        result_set: The executed search result.
        entity: The entity class the query selects.
        has_multiple_entities: True when the query selects several entities (for example through joins).
            Only the first column of each row is returned, and values that are not instances of ``entity`` are dropped.

    Returns:
        The extracted entities.
    """
    entities = result_set.scalars().all()
    if has_multiple_entities:
        return [item for item in entities if isinstance(item, entity)]
    return list(entities)
