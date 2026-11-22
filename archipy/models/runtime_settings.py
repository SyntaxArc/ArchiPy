"""Hook through which models read the application settings without importing the configs layer."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

DEFAULT_PAGINATION_MAX_ITEMS = 10000
"""Largest ``page * page_size`` a pagination request may reach when no settings are registered."""

_settings_provider: Callable[[], object] | None = None


def register_settings_provider(provider: Callable[[], object], *, replace: bool = True) -> None:
    """Register the callable that returns the application settings.

    The configs layer registers ``BaseConfig.global_config`` as the default on import. Models can then read settings
    without importing configs. Tests can register a provider to supply settings from another source.
    The default provider raises ``AssertionError`` while no settings are set.

    Args:
        provider: Callable returning the settings object.
        replace: Whether to replace an existing provider.
    """
    global _settings_provider  # noqa: PLW0603
    if replace or _settings_provider is None:
        _settings_provider = provider


def get_settings() -> object | None:
    """Return the registered application settings.

    Returns:
        The settings object, or ``None`` when no provider is registered or no settings are set yet.
    """
    if _settings_provider is None:
        return None
    try:
        return _settings_provider()
    except AssertionError:
        return None
