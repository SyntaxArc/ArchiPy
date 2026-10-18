"""Timeout decorator helpers."""

from __future__ import annotations

import asyncio
import inspect
import signal
import threading
import time
from functools import wraps
from typing import TYPE_CHECKING, cast

from archipy.helpers._deprecation import deprecated_alias
from archipy.models.errors import DeadlineExceededError, FailedPreconditionError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from types import FrameType


def timeout[**P, R](seconds: float) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """A decorator that adds a timeout to a function.

    If the function takes longer than the specified number of seconds to execute,
    a `DeadlineExceededError` is raised. The timeout is implemented with
    `signal.setitimer(signal.ITIMER_REAL, ...)`, so fractional seconds are supported.
    After the call, the previous SIGALRM handler is restored and any timer that was
    pending before the call is re-armed with its remaining time.

    ``async def`` functions are supported too: they are bounded with `asyncio.timeout`, which
    works in any thread and needs no signals.

    Limitations:
        Synchronous functions rely on `SIGALRM`, so they work only on Unix and only when the
        decorated function is called from the main thread of the main interpreter. Calling one
        from another thread raises `FailedPreconditionError` instead of running without a timeout.
        It cannot interrupt blocking C calls that do not return to the interpreter.

    Args:
        seconds (float): The maximum number of seconds the function is allowed to run.

    Returns:
        Callable: The decorated function with a timeout.

    Example:
        To use this decorator, apply it to any function and specify the timeout in seconds:

        ```python
        @timeout(3)  # Set a timeout of 3 seconds
        def long_running_function():
            time.sleep(5)  # This will take longer than the timeout
            return "Finished"


        try:
            result = long_running_function()
        except DeadlineExceededError as e:
            print(e.additional_data)  # {"timeout": 3, "operation": "long_running_function"}
        ```
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        # Capture function name before wrapping - use getattr for type safety
        func_name = getattr(func, "__name__", "unknown")

        if inspect.iscoroutinefunction(func):
            # R is the coroutine type here; the wrapper awaits it and returns the awaited value
            async_func = cast("Callable[P, Awaitable[object]]", func)

            @wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> object:
                try:
                    async with asyncio.timeout(seconds):
                        return await async_func(*args, **kwargs)
                except TimeoutError as e:
                    raise DeadlineExceededError(timeout=seconds, operation=func_name) from e

            return cast("Callable[P, R]", async_wrapper)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if threading.current_thread() is not threading.main_thread():
                raise FailedPreconditionError(
                    precondition="timeout requires the main thread",
                    additional_data={"operation": func_name},
                )

            def handle_timeout(_signum: int, _frame: FrameType | None) -> None:
                raise DeadlineExceededError(timeout=seconds, operation=func_name)

            previous_handler = signal.signal(signal.SIGALRM, handle_timeout)
            started = time.monotonic()
            previous_remaining, previous_interval = signal.setitimer(signal.ITIMER_REAL, seconds)

            try:
                return func(*args, **kwargs)
            finally:
                # Disable our timer, restore the previous handler and any timer that was pending
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous_handler)
                if previous_remaining > 0:
                    remaining = max(previous_remaining - (time.monotonic() - started), 1e-6)
                    signal.setitimer(signal.ITIMER_REAL, remaining, previous_interval)

        return wrapper

    return decorator


timeout_decorator = deprecated_alias("timeout_decorator", timeout)
