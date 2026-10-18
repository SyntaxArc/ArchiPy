"""Storage ports for the gRPC rate-limit interceptors."""

from __future__ import annotations

import sqlite3
import threading
import time
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


class InMemoryRateLimitStore:
    """Counter store kept in an in-memory SQLite database; it satisfies :class:`RateLimitStore`.

    Counts live in the process, so every server process counts on its own. Use it for tests, single-process servers
    and local development; use ``RedisAdapter`` when several processes must share one limit. Expired counters are
    removed on each call.
    """

    def __init__(self) -> None:
        """Create an empty in-memory counter database."""
        self._lock = threading.Lock()
        self._db = sqlite3.connect(":memory:", check_same_thread=False, isolation_level=None)
        self._db.execute("CREATE TABLE counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL, expires_at INTEGER)")
        self._db.execute("CREATE INDEX counters_expires_at ON counters (expires_at)")

    @staticmethod
    def _now_ms() -> int:
        return time.monotonic_ns() // 1_000_000

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

        ``applied`` is the amount actually added. A result beyond a bound is clamped to it when ``saturate`` is true
        and rejected otherwise; a rejected call returns ``applied`` 0. ``px`` is the time to live in milliseconds,
        set only when the counter has none if ``enx`` is true.
        """
        now = self._now_ms()
        with self._lock:
            self._db.execute("DELETE FROM counters WHERE expires_at IS NOT NULL AND expires_at <= ?", (now,))
            row = self._db.execute("SELECT value, expires_at FROM counters WHERE name = ?", (name,)).fetchone()
            value, expires_at = row or (0, None)
            new_value = value + (byint or 0)
            if ubound is not None and new_value > ubound:
                new_value = int(ubound) if saturate else value
            if lbound is not None and new_value < lbound:
                new_value = int(lbound) if saturate else value
            applied = new_value - value
            if row is None and applied == 0:
                return [value, 0]
            if enx and px is not None and expires_at is None:
                expires_at = now + px
            self._db.execute(
                "INSERT INTO counters (name, value, expires_at) VALUES (?, ?, ?) "
                "ON CONFLICT (name) DO UPDATE SET value = excluded.value, expires_at = excluded.expires_at",
                (name, new_value, expires_at),
            )
            return [new_value, applied]

    def pttl(self, name: str) -> int:
        """Return the milliseconds left before ``name`` expires, -1 if it never expires and -2 if it does not exist."""
        now = self._now_ms()
        with self._lock:
            row = self._db.execute("SELECT expires_at FROM counters WHERE name = ?", (name,)).fetchone()
        if row is None or (row[0] is not None and row[0] <= now):
            return -2
        return -1 if row[0] is None else row[0] - now


class AsyncInMemoryRateLimitStore:
    """Awaitable counterpart of :class:`InMemoryRateLimitStore`; it satisfies :class:`AsyncRateLimitStore`.

    The calls never wait on I/O, so they run on the event loop.
    """

    def __init__(self) -> None:
        """Create an empty in-memory counter database."""
        self._store = InMemoryRateLimitStore()

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
        return self._store.increx(name, byint=byint, lbound=lbound, ubound=ubound, saturate=saturate, px=px, enx=enx)

    async def pttl(self, name: str) -> int:
        """Return the milliseconds left before the counter ``name`` expires."""
        return self._store.pttl(name)
