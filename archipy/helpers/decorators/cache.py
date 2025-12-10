from collections.abc import Callable
from functools import wraps
from typing import Any, Protocol, TypeVar

T = TypeVar("T")
R = TypeVar("R")
P_co = TypeVar("P_co", bound=Callable[..., Any], covariant=True)


class ClearableFunction(Protocol[P_co]):
    """Protocol for a function with a clear_cache method."""

    def __call__(self, *args: object, **kwargs: object) -> object:
        """Call the function."""
        ...

    def clear_cache(self) -> None:
        """Clear the cache."""
        ...


def ttl_cache_decorator(
    ttl_seconds: int = 300,
    maxsize: int = 100,
) -> Callable[[Callable[..., Any]], ClearableFunction[Callable[..., Any]]]:
    """Decorator that provides a TTL cache for methods.

    Args:
        ttl_seconds: Time to live in seconds (default: 5 minutes)
        maxsize: Maximum size of the cache (default: 100)

    Returns:
        Decorated function with TTL caching
    """
    from cachetools import TTLCache

    cache: TTLCache = TTLCache(maxsize=maxsize, ttl=ttl_seconds)

    def decorator(func: Callable[..., Any]) -> ClearableFunction[Callable[..., Any]]:
        @wraps(func)
        def wrapper(*args: object, **kwargs: object) -> object:
            # Create a key based on function name, args, and kwargs
            func_name = getattr(func, "__name__", "unknown")
            key_parts = [func_name]
            key_parts.extend(str(arg) for arg in args[1:])  # Skip self
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            key = ":".join(key_parts)

            # Check if result is in cache
            if key in cache:
                return cache[key]

            # Call the function and cache the result
            result = func(*args, **kwargs)
            cache[key] = result
            return result

        # Add a method to clear the cache
        def clear_cache() -> None:
            cache.clear()

        # Add clear_cache method to wrapper using setattr for dynamic attribute
        wrapper.clear_cache = clear_cache
        return wrapper

    return decorator
