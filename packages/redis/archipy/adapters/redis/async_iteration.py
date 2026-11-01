"""Async iteration helpers for the Redis adapters."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Generator
from typing import Self


class AwaitableAsyncIterator[T](AsyncIterator[T], Awaitable[AsyncIterator[T]]):
    """Async iterator that can also be awaited, resolving to the wrapped iterator.

    ``async for key in adapter.scan_iter()`` works directly. The older
    ``async for key in await adapter.scan_iter()`` form keeps working because awaiting this object
    returns the underlying async iterator.
    """

    def __init__(self, iterator: AsyncIterator[T]) -> None:
        """Wrap an async iterator.

        Args:
            iterator (AsyncIterator[T]): The iterator to expose.
        """
        self._iterator = iterator

    def __aiter__(self) -> Self:
        """Return the iterator itself so ``async for`` works without awaiting first."""
        return self

    async def __anext__(self) -> T:
        """Return the next item of the wrapped iterator."""
        return await self._iterator.__anext__()

    def __await__(self) -> Generator[None, None, AsyncIterator[T]]:
        """Resolve to the wrapped async iterator, keeping the old ``await`` call style valid."""
        return self._resolve().__await__()

    async def _resolve(self) -> AsyncIterator[T]:
        """Return the wrapped iterator."""
        return self._iterator
