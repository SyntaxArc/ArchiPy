import logging
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from archipy.models.errors import ResourceExhaustedError

# Define type variables for decorators
P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def retry_decorator(
    max_retries: int = 3,
    delay: float = 1,
    retry_on: tuple[type[Exception], ...] | None = None,
    ignore: tuple[type[Exception], ...] | None = None,
    resource_type: str | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """A decorator that retries a function when it raises an exception.

    Args:
        max_retries (int): The maximum number of retry attempts. Defaults to 3.
        delay (float): The delay (in seconds) between retries. Defaults to 1.
        retry_on (Optional[Tuple[Type[Exception], ...]]): A tuple of errors to retry on.
            If None, retries on all errors. Defaults to None.
        ignore (Optional[Tuple[Type[Exception], ...]]): A tuple of errors to ignore (not retry on).
            If None, no errors are ignored. Defaults to None.
        resource_type (Optional[str]): The type of resource being exhausted. Defaults to None.

    Returns:
        Callable: The decorated function with retry logic.

    Example:
        To use this decorator, apply it to a function:

        ```python
        @retry_decorator(max_retries=3, delay=1, retry_on=(ValueError,), ignore=(TypeError,), resource_type="API")
        def unreliable_function():
            if random.random() < 0.5:
                raise ValueError("Temporary failure")
            return "Success"


        result = unreliable_function()
        ```

        Output:
        ```
        2023-10-10 12:00:00,000 - WARNING - Attempt 1 failed: Temporary failure
        2023-10-10 12:00:01,000 - INFO - Attempt 2 succeeded.
        Success
        ```
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        from functools import wraps

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            retries = 0
            while retries < max_retries:
                try:
                    result = func(*args, **kwargs)
                    if retries > 0:
                        logger.info("Attempt %d succeeded.", retries + 1)
                except Exception as e:
                    retries += 1
                    # Check if the exception should be ignored
                    if ignore and isinstance(e, ignore):
                        raise
                    # Check if the exception should be retried
                    if retry_on and not isinstance(e, retry_on):
                        raise
                    logger.warning("Attempt %d failed: %s", retries, e)
                    if retries < max_retries:
                        time.sleep(delay)
                    continue
                return result
            raise ResourceExhaustedError(resource_type=resource_type)

        return wrapper

    return decorator
