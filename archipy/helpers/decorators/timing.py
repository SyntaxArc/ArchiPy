import logging
import time
from collections.abc import Callable
from typing import Any


def timing_decorator[F: Callable[..., Any]](func: F) -> F:
    """A decorator that measures the execution time of a function and logs it if the logging level is DEBUG.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable: The wrapped function which logs the execution time if the logging level is DEBUG.

    Example:
        To use this decorator, simply apply it to any function. For example:

        ```python
        @timing_decorator
        def example_function(n: int) -> str:
            time.sleep(n)
            return f"Slept for {n} seconds"

        result = example_function(2)
        ```

        Output (if logging level is DEBUG):
        ```
        2023-10-10 12:00:00,000 - DEBUG - example_function took 2.0001 seconds to execute.
        Slept for 2 seconds
        ```
    """
    from functools import wraps

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if logging.getLogger().level == logging.DEBUG:
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            logging.debug("%s took %.4f seconds to execute.", func.__name__, end_time - start_time)
        else:
            result = func(*args, **kwargs)
        return result

    return wrapper
