"""Data transfer objects for rate-limit window tiers."""

from __future__ import annotations

from pydantic import Field, PositiveInt

from archipy.models.dtos.base_dtos import BaseDTO


class RateLimitWindowDTO(BaseDTO):
    """Data transfer object for a single rate-limit tier.

    Attributes:
        calls_count: Maximum allowed requests within the window.
        window_ms: Window duration in milliseconds.
    """

    calls_count: PositiveInt = Field(description="Maximum allowed requests within the window.")
    window_ms: PositiveInt = Field(description="Window duration in milliseconds.")

    @property
    def key_suffix(self) -> str:
        """Return a stable Redis key segment for this window tier."""
        return f"{self.calls_count}x{self.window_ms}ms"
