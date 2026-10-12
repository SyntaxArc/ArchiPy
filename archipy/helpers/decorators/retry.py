"""Retry decorator helpers."""

from __future__ import annotations

import asyncio
import inspect
import logging
import random
import time
from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any, cast

from archipy.models.errors import InvalidArgumentError, ResourceExhaustedError

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


def retry_decorator[**P, R](
    max_retries: int = 3,
    delay: float = 1,
    retry_on: tuple[type[Exception], ...] | None = None,
    ignore: tuple[type[Exception], ...] | None = None,
    resource_type: str | None = None,
    backoff: float = 1.0,
    jitter: float = 0.0,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """A decorator that retries a function when it raises an exception.

    Works for both regular and ``async def`` functions. Async functions are awaited and
    wait with ``asyncio.sleep`` between attempts, so the event loop is never blocked.

    Args:
        max_retries (int): The maximum number of attempts, including the first call
            (``3`` means one call plus two retries). Must be at least 1. Defaults to 3.
        delay (float): The delay (in seconds) before the first retry. Defaults to 1.
        retry_on (Optional[Tuple[Type[Exception], ...]]): A tuple of errors to retry on.
            If None, retries on all errors. Defaults to None.
        ignore (Optional[Tuple[Type[Exception], ...]]): A tuple of errors to ignore (not retry on).
            If None, no errors are ignored. Takes precedence over ``retry_on``. Defaults to None.
        resource_type (Optional[str]): The type of resource being exhausted. Defaults to None.
        backoff (float): Multiplier applied to the delay after every failed attempt.
            ``1.0`` keeps a fixed delay, ``2.0`` doubles it each time. Defaults to 1.0.
        jitter (float): Fraction of the delay added randomly (``0.1`` adds up to 10%) to avoid
            synchronized retries from many callers. Defaults to 0.0.

    Returns:
        Callable: The decorated function with retry logic.

    Raises:
        InvalidArgumentError: If ``max_retries`` is below 1, ``delay`` or ``jitter`` is negative,
            or ``backoff`` is below 1.

    Example:
        To use this decorator, apply it to a function:

        ```python
        @retry_decorator(max_retries=3, delay=1, backoff=2, retry_on=(ValueError,), resource_type="API")
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
    if max_retries < 1:
        raise InvalidArgumentError(argument_name="max_retries", additional_data={"minimum": 1})
    if delay < 0:
        raise InvalidArgumentError(argument_name="delay", additional_data={"minimum": 0})
    if backoff < 1:
        raise InvalidArgumentError(argument_name="backoff", additional_data={"minimum": 1})
    if jitter < 0:
        raise InvalidArgumentError(argument_name="jitter", additional_data={"minimum": 0})

    policy = _RetryPolicy(max_retries, delay, backoff, jitter, retry_on, ignore, resource_type)

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(func):
            return cast("Callable[P, R]", _wrap_async(func, policy))
        return _wrap_sync(func, policy)

    return decorator


@dataclass(frozen=True)
class _RetryPolicy:
    """Validated retry settings shared by the sync and async wrappers."""

    max_attempts: int
    delay: float
    backoff: float
    jitter: float
    retry_on: tuple[type[Exception], ...] | None
    ignore: tuple[type[Exception], ...] | None
    resource_type: str | None

    def should_retry(self, error: Exception) -> bool:
        if self.ignore and isinstance(error, self.ignore):
            return False
        return not (self.retry_on and not isinstance(error, self.retry_on))

    def next_delay(self, attempt: int) -> float:
        base = self.delay * (self.backoff ** (attempt - 1))
        return base + random.uniform(0, base * self.jitter) if self.jitter else base  # noqa: S311  # not security

    def exhausted(self, last_exception: Exception | None) -> ResourceExhaustedError:
        error = ResourceExhaustedError(resource_type=self.resource_type)
        error.__cause__ = last_exception
        return error


def _wrap_async(func: Callable[..., Any], policy: _RetryPolicy) -> Callable[..., Any]:
    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        last_exception: Exception | None = None
        for attempt in range(1, policy.max_attempts + 1):
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                if not policy.should_retry(e):
                    raise
                last_exception = e
                logger.warning("Attempt %d failed: %s", attempt, e)
                if attempt < policy.max_attempts:
                    await asyncio.sleep(policy.next_delay(attempt))
            else:
                if attempt > 1:
                    logger.info("Attempt %d succeeded.", attempt)
                return result
        raise policy.exhausted(last_exception)

    return async_wrapper


def _wrap_sync[**P, R](func: Callable[P, R], policy: _RetryPolicy) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        last_exception: Exception | None = None
        for attempt in range(1, policy.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                if not policy.should_retry(e):
                    raise
                last_exception = e
                logger.warning("Attempt %d failed: %s", attempt, e)
                if attempt < policy.max_attempts:
                    time.sleep(policy.next_delay(attempt))
            else:
                if attempt > 1:
                    logger.info("Attempt %d succeeded.", attempt)
                return result
        raise policy.exhausted(last_exception)

    return wrapper
