from enum import Enum
from typing import TypeVar

from pydantic import BaseModel, ConfigDict

# Generic types
T = TypeVar("T", bound=Enum)


class BaseDTO(BaseModel):
    """Base Data Transfer Object class.

    This class extends Pydantic's BaseModel to provide common configuration
    for all DTOs in the application.
    """

    model_config = ConfigDict(
        extra="ignore",
        validate_default=True,
        from_attributes=True,
        frozen=True,
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
    )
