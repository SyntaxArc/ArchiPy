"""Caching decorator helpers."""

from __future__ import annotations

import inspect
import threading
from functools import wraps
from typing import TYPE_CHECKING, Final, cast

from archipy.helpers._deprecation import deprecated_alias
from archipy.models.errors import ConfigurationError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Hashable, Mapping, MutableMapping


_MISSING: Final = object()


def _require_cachetools() -> None:
    """Fail with an install hint when the optional ``cachetools`` dependency is missing.

    Raises:
        ConfigurationError: If ``cachetools`` is not installed (``archipy[cache]`` extra).
    """
    try:
        import cachetools  # noqa: F401
    except ImportError as exception:
        raise ConfigurationError(
            operation="ttl_cache",
            reason="cachetools is not installed; install it with archipy[cache]",
        ) from exception


class CachedFunction[**P, R]:
    """Wrapper class for a cached function with a clear_cache method.

    This class wraps a function to provide TTL-based caching. The cache is shared
    across all instances when used as an instance method decorator.

    Example:
        ```python
        @ttl_cache(ttl_seconds=60, maxsize=100)
        def expensive_function(x: int) -> int:
            return x * 2


        # First call executes the function
        result = expensive_function(5)  # Returns 10

        # Second call returns cached result
        result = expensive_function(5)  # Returns 10 (from cache)

        # Clear cache manually
        expensive_function.clear_cache()
        ```
    """

    def __init__(
        self,
        func: Callable[..., R],
        cache: MutableMapping[Hashable, object],
        instance: object | None = None,
        lock: threading.RLock | None = None,
    ) -> None:
        """Initialize the cached function wrapper.

        Args:
            func: The function to wrap.
            cache: The cache instance to use.
            instance: The instance this method is bound to (for bound methods).
            lock: Lock guarding the cache; shared between bound copies of the same decorated function.
        """
        self._func: Callable[..., R] = func
        self._cache: MutableMapping[Hashable, object] = cache
        self._instance: object | None = instance
        # Calls on the same cache from several threads must not race on the (non thread-safe) TTLCache
        self._lock = lock if lock is not None else threading.RLock()
        # Preserve function metadata
        wraps(func)(self)
        if inspect.iscoroutinefunction(func):
            inspect.markcoroutinefunction(self)

    def __get__(self, obj: object, objtype: type | None = None) -> CachedFunction[P, R]:
        """Support instance methods by implementing descriptor protocol.

        This method caches the bound method in the instance's __dict__ to ensure
        identity consistency (obj.method is obj.method returns True).
        """
        if obj is None:
            return self

        # Cache the bound method in the instance's __dict__ for identity consistency
        func_name = getattr(self._func, "__name__", "cached_method")
        # id(self) keeps same-named cached methods of different classes in one MRO apart
        bound_method_name = f"_cached_{func_name}_{id(self)}"
        if not hasattr(obj, bound_method_name):
            # Create a bound CachedFunction that shares the same cache
            bound_cached: CachedFunction[P, R] = CachedFunction(self._func, self._cache, instance=obj, lock=self._lock)
            # Store in instance __dict__ to maintain identity
            try:
                object.__setattr__(obj, bound_method_name, bound_cached)
            except AttributeError, TypeError:
                # If we can't set the attribute (frozen dataclass, etc.), return a new instance
                return CachedFunction(self._func, self._cache, instance=obj, lock=self._lock)

        return getattr(obj, bound_method_name)

    def _make_key(self, args: tuple[object, ...], kwargs: Mapping[str, object]) -> Hashable | None:
        """Build a hashable key from the call arguments, or None if they cannot be hashed."""
        from cachetools.keys import typedkey

        key = typedkey(*args, **kwargs)
        try:
            hash(key)
        except TypeError:
            return None
        return key

    def __call__(self, *args: object, **kwargs: object) -> R:
        """Call the cached function.

        Calls whose arguments are not hashable bypass the cache instead of failing.

        Args:
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The result of the function call (from cache or fresh). For ``async def`` functions
            the result is an awaitable and the awaited value is what gets cached.
        """
        key = self._make_key(args, kwargs)
        call_args = args if self._instance is None else (self._instance, *args)

        if inspect.iscoroutinefunction(self._func):
            # R is the coroutine type here; the cached coroutine wrapper stands in for it
            return cast("R", self._call_async(key, call_args, kwargs))

        if key is None:
            return self._func(*call_args, **kwargs)
        with self._lock:
            cached = self._cache.get(key, _MISSING)
        if cached is not _MISSING:
            return cast("R", cached)

        result: R = self._func(*call_args, **kwargs)
        with self._lock:
            self._cache[key] = result
        return result

    async def _call_async(
        self,
        key: Hashable | None,
        call_args: tuple[object, ...],
        kwargs: Mapping[str, object],
    ) -> object:
        """Await the wrapped coroutine function and cache its awaited value."""
        if key is None:
            return await cast("Awaitable[object]", self._func(*call_args, **kwargs))
        with self._lock:
            cached = self._cache.get(key, _MISSING)
        if cached is not _MISSING:
            return cached

        result = await cast("Awaitable[object]", self._func(*call_args, **kwargs))
        with self._lock:
            self._cache[key] = result
        return result

    def clear_cache(self) -> None:
        """Clear the cache.

        This clears all cached values for this function. When used with instance methods,
        this clears the shared cache for all instances.
        """
        with self._lock:
            self._cache.clear()


def ttl_cache[**P, R](
    ttl_seconds: int | Callable[[], int] = 300,
    maxsize: int = 100,
) -> Callable[[Callable[P, R]], CachedFunction[P, R]]:
    """Decorator that provides a TTL cache for functions and methods.

    The cache is shared across all instances when decorating instance methods.
    This is by design to allow efficient caching of expensive operations that
    depend only on the method arguments, not the instance state.

    Args:
        ttl_seconds: Time to live in seconds (default: 5 minutes), or a zero-argument
            callable that returns the TTL (evaluated once when the decorator is applied).
            After this time, cached entries expire and the function is re-executed.
        maxsize: Maximum size of the cache (default: 100).
            When the cache is full, the least recently used entry is evicted.

    Returns:
        Decorated function with TTL caching and a clear_cache() method.

    Raises:
        ConfigurationError: If ``cachetools`` is not installed (``archipy[cache]`` extra).

    Example:
        ```python
        class DataService:
            @ttl_cache(ttl_seconds=60, maxsize=50)
            def fetch_data(self, key: str) -> dict:
                # Expensive operation
                return {"data": key}


        service1 = DataService()
        service2 = DataService()

        # First call executes the function
        result1 = service1.fetch_data("key1")

        # Second call from different instance returns cached result
        result2 = service2.fetch_data("key1")  # From cache

        # Clear cache manually
        service1.fetch_data.clear_cache()
        ```

    Note:
        - Exceptions are not cached; the function will be re-executed on the next call
        - None values are cached like any other value
        - Argument types are part of the key (``f(1)`` and ``f(1.0)`` are cached separately) and
          arguments must be hashable; calls with unhashable arguments run uncached
        - ``async def`` functions are supported; the awaited result is cached
        - Access to the cache is guarded by a lock, so it is safe to call from several threads
        - Cache is shared across all instances of a class (not per-instance)
    """
    _require_cachetools()
    from cachetools import TTLCache

    resolved_ttl = int(ttl_seconds) if isinstance(ttl_seconds, int) else int(ttl_seconds())
    cache: TTLCache[Hashable, object, float] = TTLCache(maxsize=maxsize, ttl=resolved_ttl)
    lock = threading.RLock()

    def decorator(func: Callable[P, R]) -> CachedFunction[P, R]:
        return CachedFunction(func, cache, instance=None, lock=lock)

    return decorator


ttl_cache_decorator = deprecated_alias("ttl_cache_decorator", ttl_cache)
