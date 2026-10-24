"""Deprecated module aliases for the Keycloak mixin packages that moved into ``resources``."""

from __future__ import annotations

import sys
from importlib import import_module
from types import ModuleType
from typing import Any

from archipy.helpers._deprecation import warn_deprecated_name


class _DeprecatedModule(ModuleType):
    """A module that forwards attribute reads to its replacement and warns about the old path."""

    def __init__(self, name: str, target: str) -> None:
        super().__init__(name)
        self._target = target

    def __getattr__(self, name: str) -> Any:  # noqa: ANN401 - forwards any attribute of the target module
        if name.startswith("__"):
            raise AttributeError(name)
        warn_deprecated_name(self.__name__, self._target)
        return getattr(import_module(self._target), name)


def install_module_aliases(package: str, mapping: dict[str, str]) -> None:
    """Register ``{package}.{old}`` as a deprecated alias of the module ``mapping[old]``."""
    for old, target in mapping.items():
        sys.modules.setdefault(f"{package}.{old}", _DeprecatedModule(f"{package}.{old}", target))
