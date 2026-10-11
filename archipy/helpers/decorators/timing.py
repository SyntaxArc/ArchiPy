"""Timing and performance decorator helpers."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


def timing_decorator[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """A decorator that measures the execution time of a function and logs it when DEBUG logging is enabled.

    The duration is also logged when the function raises an exception.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable: The wrapped function which logs the execution time when DEBUG logging is enabled.

    Example:
        To use this decorator, simply apply it to any function. For example:

        ```python
        @timing_decorator
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
    from functools import wraps

    # Capture function name before wrapping - use getattr for type safety
    func_name = getattr(func, "__name__", "unknown")

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
