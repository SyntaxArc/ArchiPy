"""Helpers for keeping deprecated names working while warning callers."""

from __future__ import annotations

import warnings
from functools import wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def warn_deprecated_name(old_name: str, new_name: str, *, stacklevel: int = 3) -> None:
    """Emit a ``DeprecationWarning`` that points at the caller of the deprecated name.

    Args:
        old_name: The deprecated name.
        new_name: The replacement name.
        stacklevel: Frames to skip. The default targets the caller of the function that called this helper.
    """
    warnings.warn(f"{old_name} is deprecated; use {new_name} instead.", DeprecationWarning, stacklevel=stacklevel)


def deprecated_alias[**P, R](old_name: str, replacement: Callable[P, R]) -> Callable[P, R]:
    """Return a callable that behaves like ``replacement`` but warns that ``old_name`` is deprecated.

    The warning is raised when the alias is called (for decorator factories that is when the
    decorator is applied), and points at the calling code.

    Args:
        old_name: The deprecated public name.
        replacement: The function that supersedes it.

    Returns:
        A wrapper with the signature and docstring of ``replacement`` and the name ``old_name``.
    """
    new_name = getattr(replacement, "__name__", "the replacement")

    @wraps(replacement)
    def alias(*args: P.args, **kwargs: P.kwargs) -> R:
        warn_deprecated_name(old_name, new_name)
        return replacement(*args, **kwargs)

    alias.__name__ = old_name
    alias.__qualname__ = old_name
    return alias
