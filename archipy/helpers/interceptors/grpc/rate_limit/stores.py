"""Storage ports for the gRPC rate-limit interceptors."""

from __future__ import annotations

from typing import Protocol


class RateLimitStore(Protocol):
    """Counter store a sync rate-limit interceptor needs: Redis ``INCREX`` and ``PTTL`` semantics.

    ``RedisAdapter`` satisfies it. Any object with the same two methods can replace it, for example an in-memory store
    in a test or another backend.
    """

    def increx(
        self,
        name: str,
        *,
        byint: int | None = None,
        lbound: float | None = None,
        ubound: float | None = None,
        saturate: bool = False,
        px: int | None = None,
        enx: bool = False,
    ) -> list[int]:
        """Add ``byint`` to the counter ``name`` within the bounds and return ``[new_value, applied]``.

        ``px`` is the time to live in milliseconds, set only when the counter is created if ``enx`` is true.
        """
        ...

    def pttl(self, name: str) -> int:
        """Return the milliseconds left before the counter ``name`` expires."""
        ...


class AsyncRateLimitStore(Protocol):
    """Counter store an async rate-limit interceptor needs; the awaitable counterpart of :class:`RateLimitStore`."""

    async def increx(
        self,
        name: str,
        *,
        byint: int | None = None,
        lbound: float | None = None,
        ubound: float | None = None,
        saturate: bool = False,
        px: int | None = None,
        enx: bool = False,
    ) -> list[int]:
        """Add ``byint`` to the counter ``name`` within the bounds and return ``[new_value, applied]``."""
        ...

    async def pttl(self, name: str) -> int:
        """Return the milliseconds left before the counter ``name`` expires."""
        ...
