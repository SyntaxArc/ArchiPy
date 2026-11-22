"""Hook through which models read the application settings without importing the configs layer."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_PAGINATION_MAX_ITEMS = 10000
"""Largest ``page * page_size`` a pagination request may reach when no settings are registered."""

_settings_provider: Callable[[], object] | None = None
_default_settings_provider: Callable[[], object] | None = None


def register_settings_provider(provider: Callable[[], object]) -> None:
    """Set or replace the callable that returns the application settings.

    Args:
        provider: Callable returning the settings object.
    """
    global _settings_provider  # noqa: PLW0603
    _settings_provider = provider


def register_default_settings_provider(provider: Callable[[], object]) -> None:
    """Set the provider used when no explicit provider is registered.

    Args:
        provider: Callable returning the settings object.
    """
    global _default_settings_provider  # noqa: PLW0603
    _default_settings_provider = provider


def get_settings() -> object | None:
    """Return the registered application settings.

    Returns:
        The settings object, or ``None`` when no provider is registered or no settings are set yet.
    """
    provider = _settings_provider if _settings_provider is not None else _default_settings_provider
    if provider is None:
        return None
    try:
        return provider()
    except AssertionError:
        return None
