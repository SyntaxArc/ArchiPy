"""Timing and performance decorator helpers."""

from __future__ import annotations

import inspect
import logging
import time
from functools import wraps
from typing import TYPE_CHECKING, Any, cast

from archipy.helpers.decorators._deprecation_alias import deprecated_alias

if TYPE_CHECKING:
    from collections.abc import Callable

# Logger name kept from the former ``timing`` module so existing logging configuration still applies
logger = logging.getLogger("archipy.helpers.decorators.timing")


def timing[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """A decorator that measures the execution time of a function and logs it when DEBUG logging is enabled.

    The duration is also logged when the function raises an exception. Works for both regular
    and ``async def`` functions; for async functions the time spent awaiting is included.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable: The wrapped function which logs the execution time when DEBUG logging is enabled.

    Example:
        To use this decorator, simply apply it to any function. For example:

        ```python
        @timing
        def example_function(n: int) -> str:
            time.sleep(n)
            return f"Slept for {n} seconds"


        result = example_function(2)
        ```

        Output (if DEBUG logging is enabled):
        ```
        2023-10-10 12:00:00,000 - DEBUG - example_function took 2.0001 seconds to execute.
        Slept for 2 seconds
        ```
    """
    # Capture function name before wrapping - use getattr for type safety
    func_name = getattr(func, "__name__", "unknown")

    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            if not logger.isEnabledFor(logging.DEBUG):
                return await func(*args, **kwargs)
            start_time = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                logger.debug("%s took %.4f seconds to execute.", func_name, time.perf_counter() - start_time)

        return cast("Callable[P, R]", async_wrapper)

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if not logger.isEnabledFor(logging.DEBUG):
            return func(*args, **kwargs)
        start_time = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            logger.debug("%s took %.4f seconds to execute.", func_name, time.perf_counter() - start_time)

    return wrapper


timing_decorator = deprecated_alias("timing_decorator", timing)
