"""Shared rate-limit window helpers."""

from __future__ import annotations

from archipy.models.dtos.rate_limit_window_dto import RateLimitWindowDTO
from archipy.models.errors import InvalidArgumentError


class RateLimitUtils:
    """Utility class for building and reading rate-limit window metadata."""

    ARCHIPY_RATE_LIMIT_WINDOWS_ATTR = "__archipy_rate_limit_windows__"

    @classmethod
    def compute_rate_limit_window(
        cls,
        calls_count: int = 1,
        milliseconds: int = 0,
        seconds: int = 0,
        minutes: int = 0,
        hours: int = 0,
        days: int = 0,
    ) -> RateLimitWindowDTO:
        """Build a validated rate-limit window from time unit parameters.

        Args:
            calls_count: Maximum allowed requests within the window.
            milliseconds: Milliseconds component of the window.
            seconds: Seconds component of the window.
            minutes: Minutes component of the window.
            hours: Hours component of the window.
            days: Days component of the window.

        Returns:
            A ``RateLimitWindowDTO`` with the combined window in milliseconds.

        Raises:
            InvalidArgumentError: If ``calls_count`` is below 1 or the window is zero.
        """
        if calls_count < 1:
            raise InvalidArgumentError(additional_data={"detail": "calls_count must be at least 1"})

        window_ms = (
            milliseconds + 1000 * seconds + 60 * 1000 * minutes + 60 * 60 * 1000 * hours + 24 * 60 * 60 * 1000 * days
        )
        if window_ms <= 0:
            raise InvalidArgumentError(
                additional_data={"detail": "Rate limit window must be greater than 0 milliseconds"},
            )

        return RateLimitWindowDTO(calls_count=calls_count, window_ms=window_ms)

    @classmethod
    def get_rate_limit_windows_from_callable(cls, method: object) -> tuple[RateLimitWindowDTO, ...]:
        """Return stacked rate-limit windows attached to a callable or bound method.

        Args:
            method: A function, bound method, or other callable inspected for decorator metadata.

        Returns:
            Tuple of ``RateLimitWindowDTO`` instances in declaration order.
        """
        target = getattr(method, "__func__", method)
        windows = getattr(target, cls.ARCHIPY_RATE_LIMIT_WINDOWS_ATTR, ())
        if not windows:
            return ()
        return tuple(RateLimitWindowDTO.model_validate(window) for window in windows)
