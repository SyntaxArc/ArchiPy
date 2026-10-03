"""DTOs for Redis Search results."""

from pydantic import Field, NonNegativeFloat, NonNegativeInt

from archipy.models.dtos.base_dtos import BaseDTO


class SearchHitDTO(BaseDTO):
    """Single RediSearch document hit."""

    doc_id: str
    score: float | None = None
    fields: dict[str, str | int | float | list[float] | bytes] = Field(default_factory=dict)


class SearchResultDTO(BaseDTO):
    """Normalized RediSearch query result."""

    total: NonNegativeInt
    hits: list[SearchHitDTO]
    duration_ms: NonNegativeFloat | None = None
    warnings: list[str] = Field(default_factory=list)
