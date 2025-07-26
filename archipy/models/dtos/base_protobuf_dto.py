from typing import Any, ClassVar, Self

from archipy.models.dtos.base_dtos import BaseDTO
from archipy.models.errors import InvalidEntityTypeError

try:
    from google.protobuf.json_format import MessageToDict, ParseDict
    from google.protobuf.message import Message

    PROTOBUF_AVAILABLE = True
except ImportError:
    Message = object  # Define Message as a placeholder
    PROTOBUF_AVAILABLE = False


class BaseProtobufDTO(BaseDTO):
    """A base DTO that can be converted to and from a Protobuf message.

    Requires 'google-protobuf' to be installed.
    """

    _proto_class: ClassVar[type[Message] | None] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Add a check at runtime when someone tries to use the class
        if not PROTOBUF_AVAILABLE:
            raise RuntimeError("The 'protobuf' extra is not installed. ")
        super().__init__(*args, **kwargs)

    @classmethod
    def from_proto(cls, request: Message) -> Self:
        """Converts a Protobuf message into a Pydantic DTO instance."""
        if cls._proto_class is None:
            raise NotImplementedError(f"{cls.__name__} is not mapped to a proto class.")

        if not isinstance(request, cls._proto_class):
            raise InvalidEntityTypeError(
                message=f"{cls.__name__}.from_proto expected a different type of request.",
                expected_type=cls._proto_class.__name__,
                actual_type=type(request).__name__,
            )

        input_data = MessageToDict(
            message=request,
            always_print_fields_with_no_presence=True,
            preserving_proto_field_name=True,
        )
        return cls.model_validate(input_data)

    def to_proto(self) -> Message:
        """Converts the Pydantic DTO instance into a Protobuf message."""
        if self._proto_class is None:
            raise NotImplementedError(f"{self.__class__.__name__} is not mapped to a proto class.")

        return ParseDict(self.model_dump(mode="json"), self._proto_class())
