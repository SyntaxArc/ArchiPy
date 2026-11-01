"""Map redis-py failures to ``CacheError`` while keeping the original exception type catchable."""

from __future__ import annotations

import inspect
from functools import wraps
from typing import TYPE_CHECKING, Any

from redis.exceptions import RedisError

from archipy.models.errors import CacheError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

_MAPPED_TYPES: dict[type[RedisError], type[CacheError]] = {}


def to_cache_error(error: RedisError) -> CacheError:
    """Build a CacheError that is also an instance of the original redis-py exception type.

    Existing ``except redis.exceptions.RedisError`` (or any subclass) handlers keep working, and new code can
    catch ``CacheError``.

    Args:
        error (RedisError): The exception raised by redis-py.

    Returns:
        CacheError: A mapped error; the original is available as ``__cause__`` once raised ``from`` it.
    """
    error_type = type(error)
    mapped_type = _MAPPED_TYPES.get(error_type)
    if mapped_type is None:
        original_base: Any = error_type
        mapped_type = type(f"Cache{error_type.__name__}", (CacheError, original_base), {"__module__": __name__})
        _MAPPED_TYPES[error_type] = mapped_type
    mapped = mapped_type.__new__(mapped_type)
    mapped.__dict__.update(vars(error))
    CacheError.__init__(mapped, cache_type="redis", additional_data={"error": str(error)})
    return mapped


def _wrap_sync(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        try:
            return func(*args, **kwargs)
        except CacheError:
            raise
        except RedisError as error:
            raise to_cache_error(error) from error

    return wrapper


def _wrap_async(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        try:
            return await func(*args, **kwargs)
        except CacheError:
            raise
        except RedisError as error:
            raise to_cache_error(error) from error

    return wrapper


def map_redis_errors(cls: type, *, is_async: bool) -> None:
    """Wrap the public methods of a class so redis-py errors surface as ``CacheError``.

    Sync classes wrap every public function; async classes wrap public coroutine functions only. Methods that
    return lazy objects (iterators, pipelines, pub/sub) are not wrapped for sync classes beyond the call itself.

    Args:
        cls (type): The adapter or handle class to patch in place.
        is_async (bool): Whether to wrap coroutine functions instead of plain functions.
    """
    for name in dir(cls):
        if name.startswith("_"):
            continue
        member = inspect.getattr_static(cls, name)
        if not inspect.isfunction(member):
            continue
        if is_async:
            if inspect.iscoroutinefunction(member):
                setattr(cls, name, _wrap_async(member))
        elif not inspect.isgeneratorfunction(member):
            setattr(cls, name, _wrap_sync(member))
