from collections.abc import Callable
from functools import wraps
from typing import Any


class CachedFunction[**P, R]:
    """Wrapper class for a cached function with a clear_cache method.

    This class wraps a function to provide TTL-based caching. The cache is shared
    across all instances when used as an instance method decorator.

    Example:
        ```python
        @ttl_cache_decorator(ttl_seconds=60, maxsize=100)
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

    def __init__(self, func: Callable[..., R], cache: Any, instance: object | None = None) -> None:
        """Initialize the cached function wrapper.

        Args:
            func: The function to wrap.
            cache: The cache instance to use.
            instance: The instance this method is bound to (for bound methods).
        """
        self._func: Callable[..., R] = func
        self._cache: Any = cache
        self._instance: object | None = instance
        # Preserve function metadata
        wraps(func)(self)

    def __get__(self, obj: object, objtype: type | None = None) -> CachedFunction[P, R]:
        """Support instance methods by implementing descriptor protocol.

        This method caches the bound method in the instance's __dict__ to ensure
        identity consistency (obj.method is obj.method returns True).
        """
        if obj is None:
            return self

        # Cache the bound method in the instance's __dict__ for identity consistency
        func_name = getattr(self._func, "__name__", "cached_method")
        bound_method_name = f"_cached_{func_name}"
        if not hasattr(obj, bound_method_name):
            # Create a bound CachedFunction that shares the same cache
            bound_cached: CachedFunction[P, R] = CachedFunction(self._func, self._cache, instance=obj)
            # Store in instance __dict__ to maintain identity
            try:
                object.__setattr__(obj, bound_method_name, bound_cached)
            except (AttributeError, TypeError):
                # If we can't set the attribute (frozen dataclass, etc.), return a new instance
                return CachedFunction(self._func, self._cache, instance=obj)

        return getattr(obj, bound_method_name)

    def __call__(self, *args: Any, **kwargs: Any) -> R:
        """Call the cached function.

        Args:
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            The result of the function call (from cache or fresh).
        """
        # Create a key based on function name, args, and kwargs
        func_name = getattr(self._func, "__name__", "unknown")
        key_parts = [func_name]

        # Use repr() with type information for robust key generation
        key_parts.extend(f"{type(arg).__name__}:{arg!r}" for arg in args)

        # Add keyword arguments
        key_parts.extend(f"{k}={type(v).__name__}:{v!r}" for k, v in sorted(kwargs.items()))

        key = ":".join(key_parts)

        # Check if result is in cache
        if key in self._cache:
            return self._cache[key]

        # Call the function with the instance if this is a bound method
        if self._instance is not None:
            result: R = self._func(self._instance, *args, **kwargs)
        else:
            result = self._func(*args, **kwargs)

        self._cache[key] = result
        return result

    def clear_cache(self) -> None:
        """Clear the cache.

        This clears all cached values for this function. When used with instance methods,
        this clears the shared cache for all instances.
        """
        self._cache.clear()


def ttl_cache_decorator[**P, R](
    ttl_seconds: int = 300,
    maxsize: int = 100,
) -> Callable[[Callable[P, R]], CachedFunction[P, R]]:
    """Decorator that provides a TTL cache for functions and methods.

    The cache is shared across all instances when decorating instance methods.
    This is by design to allow efficient caching of expensive operations that
    depend only on the method arguments, not the instance state.

    Args:
        ttl_seconds: Time to live in seconds (default: 5 minutes).
            After this time, cached entries expire and the function is re-executed.
        maxsize: Maximum size of the cache (default: 100).
            When the cache is full, the least recently used entry is evicted.

    Returns:
        Decorated function with TTL caching and a clear_cache() method.

    Example:
        ```python
        class DataService:
            @ttl_cache_decorator(ttl_seconds=60, maxsize=50)
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
        - Cache is shared across all instances of a class (not per-instance)
    """
    from cachetools import TTLCache

    cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)

    def decorator(func: Callable[P, R]) -> CachedFunction[P, R]:
        return CachedFunction(func, cache, instance=None)

    return decorator
