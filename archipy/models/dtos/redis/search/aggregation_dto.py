"""DTOs for Redis Search aggregations."""

from typing import Annotated, Literal

from pydantic import Field, field_validator

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.dtos.redis.search.escaping import SearchIdentifier


class AggregationDTO(BaseDTO):
    """RediSearch aggregation request parameters.

    ``query`` is raw RediSearch syntax and is not escaped; escape untrusted input with ``escape_text``,
    ``escape_tag`` or ``quote_phrase``. Field names are validated identifiers.
    """

    query: str = "*"
    group_by: list[SearchIdentifier] | None = None
    reduce_field: SearchIdentifier | None = None
    reduce_function: Literal["COUNT", "COLLECT"] | None = None
    collect_fields: list[SearchIdentifier] = Field(default_factory=list)
    collect_sort_by: SearchIdentifier | None = None
    collect_sort_direction: Literal["ASC", "DESC"] = "ASC"
    collect_limit: tuple[Annotated[int, Field(ge=0)], Annotated[int, Field(ge=0)]] | None = None
    sort_by: SearchIdentifier | None = None
    sort_direction: Literal["ASC", "DESC"] = "ASC"
    limit: int | None = None

    @field_validator("sort_direction", "collect_sort_direction", mode="before")
    @classmethod
    def _normalize_sort_direction(cls, value: object) -> object:
        """Accept any casing of ASC/DESC, as before."""
        return value.upper() if isinstance(value, str) else value
