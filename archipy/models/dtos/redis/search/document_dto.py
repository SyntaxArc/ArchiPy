"""DTOs for Redis Search documents."""

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.types import JsonValue


class HashDocumentUpsertDTO(BaseDTO):
    """Payload for upserting a HASH-backed RediSearch document."""

    doc_id: str
    fields: dict[str, str | int | float]
    vector_field: str | None = None
    vector: list[float] | None = None


class JsonDocumentUpsertDTO(BaseDTO):
    """Payload for upserting a JSON-backed RediSearch document."""

    doc_id: str
    payload: dict[str, JsonValue]
    json_path: str = "$"
