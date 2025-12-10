from collections.abc import Callable
from functools import wraps
from typing import Any


class CachedFunction[**P, R]:
    """Wrapper class for a cached function with a clear_cache method."""

    def __init__(self, func: Callable[P, R], cache: Any) -> None:
        """Initialize the cached function wrapper.

        Args:
            func: The function to wrap.
            cache: The cache instance to use.
        """
        self._func = func
        self._cache = cache
        # Preserve function metadata
        wraps(func)(self)

    def __get__(self, obj: object, objtype: type | None = None) -> CachedFunction[P, R]:
        """Support instance methods by implementing descriptor protocol."""
        if obj is None:
            return self
        # Return a bound method-like callable
        from functools import partial

        bound_call = partial(self.__call__, obj)
        # Create a new CachedFunction instance that wraps the bound method
        # This ensures clear_cache is available on the bound method
        bound_cached = CachedFunction(bound_call, self._cache)
        return bound_cached

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> R:
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
        # Skip first arg if it looks like 'self' (for instance methods)
        # We check if args[0] has __dict__ which indicates it's likely an instance
        if args and hasattr(args[0], "__dict__"):
            key_parts.extend(str(arg) for arg in args[1:])
        else:
            key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        key = ":".join(key_parts)

        # Check if result is in cache
        if key in self._cache:
            return self._cache[key]

        # Call the function and cache the result
        result = self._func(*args, **kwargs)
        self._cache[key] = result
        return result

    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()


def ttl_cache_decorator[**P, R](
    ttl_seconds: int = 300,
    maxsize: int = 100,
) -> Callable[[Callable[P, R]], CachedFunction[P, R]]:
    """Decorator that provides a TTL cache for methods.

    Args:
        ttl_seconds: Time to live in seconds (default: 5 minutes)
        maxsize: Maximum size of the cache (default: 100)

    Returns:
        Decorated function with TTL caching
    """
    from cachetools import TTLCache

    cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)

    def decorator(func: Callable[P, R]) -> CachedFunction[P, R]:
        return CachedFunction(func, cache)

    return decorator
