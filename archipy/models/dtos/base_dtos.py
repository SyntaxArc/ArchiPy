from enum import Enum
from typing import Any, Self, TypeVar

from pydantic import BaseModel, ConfigDict
from pydantic._internal._model_construction import ModelMetaclass

# Generic types
T = TypeVar("T", bound=Enum)


class FieldStr(str):
    """Type-safe field name reference string.

    Allows referencing Pydantic model field names as class attributes
    instead of hardcoded strings, enabling IDE autocompletion and
    refactoring support.

    Examples:
        >>> class UserDTO(BaseDTO):
        ...     name: str
        ...     email: str
        >>> UserDTO.name  # returns FieldStr("name")
        'name'
        >>> UserDTO.name == "name"
        True
    """

    __slots__ = ("name",)

    def __new__(cls, value: str) -> Self:
        """Create a new FieldStr instance.

        Args:
            value: The field name string.

        Returns:
            FieldStr: A string subclass carrying the field name.
        """
        obj = super().__new__(cls, value)
        obj.name = value
        return obj


class BaseMeta(ModelMetaclass):
    """Metaclass that adds FieldStr class attributes for each Pydantic model field.

    After Pydantic's ModelMetaclass constructs the class and populates
    ``model_fields``, this metaclass overwrites the corresponding class
    attributes with :class:`FieldStr` instances so that
    ``MyDTO.field_name`` returns a type-safe string equal to ``"field_name"``.

    Instance attribute access is unaffected because Python resolves
    instance ``__dict__`` entries before class attributes.
    """

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> type:  # noqa: ANN401
        """Create a new class with FieldStr attributes for each model field.

        Args:
            name: The class name.
            bases: The base classes.
            namespace: The class namespace.
            **kwargs: Additional keyword arguments forwarded to ModelMetaclass.

        Returns:
            The newly created class with FieldStr attributes.
        """
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        for field_name in cls.model_fields:  # ty:ignore[unresolved-attribute]
            setattr(cls, field_name, FieldStr(field_name))
        return cls


class BaseDTO(BaseModel, metaclass=BaseMeta):
    """Base Data Transfer Object class.

    This class extends Pydantic's BaseModel with a custom metaclass that
    provides type-safe field name references. After class construction,
    each field name is accessible as a :class:`FieldStr` class attribute.

    Examples:
        >>> class ProductDTO(BaseDTO):
        ...     title: str
        ...     price: float
        >>> ProductDTO.title  # FieldStr("title")
        'title'
        >>> product = ProductDTO(title="Widget", price=9.99)
        >>> product.title  # actual value
        'Widget'
    """

    model_config = ConfigDict(
        extra="ignore",
        validate_default=True,
        from_attributes=True,
        frozen=True,
        str_strip_whitespace=True,
        arbitrary_types_allowed=True,
    )
