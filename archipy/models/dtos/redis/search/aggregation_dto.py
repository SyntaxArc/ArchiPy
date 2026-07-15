from archipy.models.dtos.base_dtos import BaseDTO


class AggregationDTO(BaseDTO):
    """RediSearch aggregation request parameters."""

    query: str = "*"
    group_by: list[str] | None = None
    reduce_field: str | None = None
    reduce_function: str | None = None
    sort_by: str | None = None
    sort_direction: str = "ASC"
    limit: int | None = None
