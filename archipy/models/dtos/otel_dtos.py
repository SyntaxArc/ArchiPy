"""DTOs for the OpenTelemetry helpers."""

from typing import Any

from archipy.models.dtos.base_dtos import BaseDTO


class RpcInstrumentsDTO(BaseDTO):
    """The gRPC server metric instruments of one meter provider.

    Attributes:
        duration: The ``rpc.server.call.duration`` histogram.
        active: The ``rpc.server.active_requests`` up-down counter.
        provider_id: ``id()`` of the meter provider that created them, so a provider reset recreates them.
    """

    duration: Any
    active: Any
    provider_id: int
