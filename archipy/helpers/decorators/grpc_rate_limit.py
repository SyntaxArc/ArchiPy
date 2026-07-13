"""Decorator for declaring per-RPC gRPC rate-limit windows on servicer methods."""

from __future__ import annotations

from collections.abc import Callable
from typing import ParamSpec, TypeVar

from archipy.helpers.utils.rate_limit_utils import RateLimitUtils

P = ParamSpec("P")
R = TypeVar("R")


def grpc_rate_limit_decorator(
    calls_count: int = 1,
    milliseconds: int = 0,
    seconds: int = 0,
    minutes: int = 0,
    hours: int = 0,
    days: int = 0,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Attach a rate-limit window to a gRPC servicer method without wrapping it.

    Stack multiple decorators on one method to enforce burst and sustained limits.
    The ``GrpcServerRateLimitInterceptor`` reads ``__archipy_rate_limit_windows__``
    and enforces each window in declaration order.

    Args:
        calls_count: Maximum allowed requests within the window.
        milliseconds: Milliseconds component of the window.
        seconds: Seconds component of the window.
        minutes: Minutes component of the window.
        hours: Hours component of the window.
        days: Days component of the window.

    Returns:
        A decorator that records the window on the target function.

    Raises:
        InvalidArgumentError: If ``calls_count`` or the computed window is invalid.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        window = RateLimitUtils.compute_rate_limit_window(
            calls_count=calls_count,
            milliseconds=milliseconds,
            seconds=seconds,
            minutes=minutes,
            hours=hours,
            days=days,
        )
        existing = getattr(func, RateLimitUtils.ARCHIPY_RATE_LIMIT_WINDOWS_ATTR, ())
        setattr(func, RateLimitUtils.ARCHIPY_RATE_LIMIT_WINDOWS_ATTR, (*existing, window))
        return func

    return decorator
