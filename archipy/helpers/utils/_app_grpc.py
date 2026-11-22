"""Optional gRPC imports for the application bootstrap helpers."""

from typing import TYPE_CHECKING

try:
    import grpc
    from grpc import aio as grpc_aio
except ImportError:
    # Static types describe the interface with the extra installed.
    if TYPE_CHECKING:
        raise
    GRPC_APP = False
    grpc = None
    grpc_aio = None
    create_grpc_server = None
else:
    GRPC_APP = True
    create_grpc_server = grpc_aio.server

__all__ = ["GRPC_APP", "create_grpc_server", "grpc", "grpc_aio"]
