import logging
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)


def timing_decorator[**P, R](func: Callable[P, R]) -> Callable[P, R]:
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

    # Capture function name before wrapping - use getattr for type safety
    func_name = getattr(func, "__name__", "unknown")

    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if logging.getLogger().level == logging.DEBUG:
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            logger.debug("%s took %.4f seconds to execute.", func_name, end_time - start_time)
        else:
            result = func(*args, **kwargs)
        return result

    return wrapper
