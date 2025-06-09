from enum import StrEnum

class SchemaTypes(StrEnum):
    """Enumeration of supported schema types for data serialization.

    Attributes:
        PROTOBUF: Represents the Protocol Buffers serialization format.
        AVRO: Represents the Avro serialization format.
    """
    PROTOBUF = "PROTOBUF"
    AVRO = "AVRO"
