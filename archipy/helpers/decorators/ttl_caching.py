"""Caching decorator helpers."""

from __future__ import annotations

import inspect
import threading
from functools import wraps
from typing import TYPE_CHECKING, Any, cast

from cachetools.keys import typedkey

from archipy.helpers.decorators._deprecation_alias import deprecated_alias

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


_MISSING: Any = object()


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
        cache: Any,
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
        self._cache: Any = cache
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

    def _make_key(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any | None:
        """Build a hashable key from the call arguments, or None if they cannot be hashed."""
        key = typedkey(*args, **kwargs)
        try:
            hash(key)
        except TypeError:
            return None
        return key

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
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
            return self._call_async(key, call_args, kwargs)

        if key is None:
            return self._func(*call_args, **kwargs)
        with self._lock:
            cached = self._cache.get(key, _MISSING)
        if cached is not _MISSING:
            return cached

        result: R = self._func(*call_args, **kwargs)
        with self._lock:
            self._cache[key] = result
        return result

    async def _call_async(self, key: Any | None, call_args: tuple[Any, ...], kwargs: dict[str, Any]) -> Any:
        """Await the wrapped coroutine function and cache its awaited value."""
        if key is None:
            return await cast("Awaitable[Any]", self._func(*call_args, **kwargs))
        with self._lock:
            cached = self._cache.get(key, _MISSING)
        if cached is not _MISSING:
            return cached

        result = await cast("Awaitable[Any]", self._func(*call_args, **kwargs))
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
    from cachetools import TTLCache

    resolved_ttl = int(ttl_seconds) if isinstance(ttl_seconds, int) else int(ttl_seconds())
    cache: TTLCache = TTLCache(maxsize=maxsize, ttl=resolved_ttl)
    lock = threading.RLock()

    def decorator(func: Callable[P, R]) -> CachedFunction[P, R]:
        return CachedFunction(func, cache, instance=None, lock=lock)

    return decorator


ttl_cache_decorator = deprecated_alias("ttl_cache_decorator", ttl_cache)
