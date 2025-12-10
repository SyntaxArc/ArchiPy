import signal
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

from archipy.models.errors import DeadlineExceededError

# Define a type variable for the return type of the decorated function
F = TypeVar("F", bound=Callable[..., Any])


def timeout_decorator(seconds: int) -> Callable[[F], F]:
    """A decorator that adds a timeout to a function.

    If the function takes longer than the specified number of seconds to execute,
    a DeadlineExceededException is raised.

    Args:
        seconds (int): The maximum number of seconds the function is allowed to run.

    Returns:
        Callable: The decorated function with a timeout.

    Example:
        To use this decorator, apply it to any function and specify the timeout in seconds:

        ```python
        @timeout_decorator(3)  # Set a timeout of 3 seconds
        def long_running_function():
            time.sleep(5)  # This will take longer than the timeout
            return "Finished"

        try:
            result = long_running_function()
        except DeadlineExceededException as e:
            print(e)  # Output: "Function long_running_function timed out after 3 seconds."
        ```

        Output:
        ```
        DeadlineExceededException: Function long_running_function timed out after 3 seconds.
        ```
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            def handle_timeout(_signum: int, _frame: Any) -> None:
                raise DeadlineExceededError(operation=func.__name__)

            # Set the signal handler and alarm
            signal.signal(signal.SIGALRM, handle_timeout)
            signal.alarm(seconds)

            try:
                result = func(*args, **kwargs)
            finally:
                # Disable the alarm
                signal.alarm(0)
            return result

        return wrapper

    return decorator
