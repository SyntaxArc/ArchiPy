"""Values that warn when read, for the auth data ``fastapi_auth`` still puts on ``request.state``.

``request.state`` gives no hook on attribute reads, and Starlette stays untouched, so the stored value warns instead:
each common read method of the dict, list or set emits a ``DeprecationWarning`` that names the replacement. The value
is a real ``dict``, ``list`` or ``set`` subclass with the same content, so existing code keeps working.
"""

from __future__ import annotations

import functools
from typing import TYPE_CHECKING

from archipy.helpers._deprecation import warn_deprecated_name

if TYPE_CHECKING:
    from collections.abc import Callable

_DICT_READS = ("__getitem__", "__iter__", "__contains__", "__len__", "get", "keys", "values", "items", "copy")
_LIST_READS = ("__getitem__", "__iter__", "__len__", "__contains__", "index", "count", "copy")
_SET_READS = (
    "__iter__",
    "__contains__",
    "__len__",
    "copy",
    "isdisjoint",
    "issubset",
    "issuperset",
    "union",
    "intersection",
    "difference",
)


def _guard(base: type, name: str) -> Callable[..., object]:
    """Wrap the ``name`` method of ``base`` so it warns before it reads."""
    original = getattr(base, name)

    @functools.wraps(original)
    def method(self: _Warning, *args: object, **kwargs: object) -> object:
        warn_deprecated_name(f"request.state.{self.field}", self.replacement)
        return original(self, *args, **kwargs)

    return method


class _Warning:
    """Mixin that remembers which ``request.state`` field a value stands for and what replaces it."""

    field: str
    replacement: str


class _WarningDict(_Warning, dict):
    """A dict that warns on reads."""


class _WarningList(_Warning, list):
    """A list that warns on reads."""


class _WarningSet(_Warning, set):
    """A set that warns on reads."""


for _name in _DICT_READS:
    setattr(_WarningDict, _name, _guard(dict, _name))
for _name in _LIST_READS:
    setattr(_WarningList, _name, _guard(list, _name))
for _name in _SET_READS:
    setattr(_WarningSet, _name, _guard(set, _name))


def deprecated_dict(value: dict, field: str, replacement: str) -> dict:
    """Return a copy of ``value`` that warns on reads."""
    result = _WarningDict(value)
    result.field, result.replacement = field, replacement
    return result


def deprecated_list(value: list, field: str, replacement: str) -> list:
    """Return a copy of ``value`` that warns on reads."""
    result = _WarningList(value)
    result.field, result.replacement = field, replacement
    return result


def deprecated_set(value: set, field: str, replacement: str) -> set:
    """Return a copy of ``value`` that warns on reads."""
    result = _WarningSet(value)
    result.field, result.replacement = field, replacement
    return result
