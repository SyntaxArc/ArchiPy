"""gRPC test utilities for error handling tests."""

import logging
from typing import Any

try:
    import grpc
    from grpc import aio as grpc_aio

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    grpc = None
    grpc_aio = None

logger = logging.getLogger(__name__)


def create_grpc_channel(host: str, port: int) -> grpc.Channel:
    """Create an insecure gRPC channel to the test server.

    Args:
        host: Server host address.
        port: Server port number.

    Returns:
        grpc.Channel: Insecure channel to the server.

    Raises:
        RuntimeError: If gRPC is not available.
    """
    if not GRPC_AVAILABLE:
        raise RuntimeError("gRPC is not available")

    address = f"{host}:{port}"
    logger.debug(f"Creating gRPC channel to {address}")
    return grpc.insecure_channel(address)


def create_async_grpc_channel(host: str, port: int) -> grpc.aio.Channel:
    """Create an insecure async gRPC channel to the test server.

    Args:
        host: Server host address.
        port: Server port number.

    Returns:
        grpc.aio.Channel: Insecure async channel to the server.

    Raises:
        RuntimeError: If gRPC is not available.
    """
    if not GRPC_AVAILABLE:
        raise RuntimeError("gRPC is not available")

    address = f"{host}:{port}"
    logger.debug(f"Creating async gRPC channel to {address}")
    return grpc.aio.insecure_channel(address)


def get_test_stub(channel: grpc.Channel) -> Any:
    """Get the TestService stub for making gRPC calls.

    Args:
        channel: gRPC channel to use.

    Returns:
        TestServiceStub: The gRPC stub for TestService.
    """
    try:
        import sys
        from pathlib import Path

        # Add proto directory to path so generated files can import each other
        proto_dir = Path(__file__).parent.parent / "proto"
        if str(proto_dir) not in sys.path:
            sys.path.insert(0, str(proto_dir))

        import test_service_pb2_grpc

        return test_service_pb2_grpc.TestServiceStub(channel)
    except ImportError as e:
        raise RuntimeError("Failed to import test_service_pb2_grpc. Make sure protobuf files are compiled.") from e


def get_test_async_stub(channel: grpc.aio.Channel) -> Any:
    """Get the async TestService stub for making gRPC calls.

    Args:
        channel: Async gRPC channel to use.

    Returns:
        TestServiceStub: The async gRPC stub for TestService.
    """
    try:
        import sys
        from pathlib import Path

        # Add proto directory to path so generated files can import each other
        proto_dir = Path(__file__).parent.parent / "proto"
        if str(proto_dir) not in sys.path:
            sys.path.insert(0, str(proto_dir))

        import test_service_pb2_grpc

        return test_service_pb2_grpc.TestServiceStub(channel)
    except ImportError as e:
        raise RuntimeError("Failed to import test_service_pb2_grpc. Make sure protobuf files are compiled.") from e


def get_test_request(data: str = "") -> Any:
    """Create a TestRequest message.

    Args:
        data: Request data string.

    Returns:
        TestRequest: The protobuf request message.
    """
    try:
        import sys
        from pathlib import Path

        # Add proto directory to path so generated files can import each other
        proto_dir = Path(__file__).parent.parent / "proto"
        if str(proto_dir) not in sys.path:
            sys.path.insert(0, str(proto_dir))

        import test_service_pb2

        return test_service_pb2.TestRequest(data=data)
    except ImportError as e:
        raise RuntimeError("Failed to import test_service_pb2. Make sure protobuf files are compiled.") from e


def extract_grpc_error_info(error: grpc.RpcError) -> dict[str, Any]:
    """Extract error information from a gRPC RpcError.

    Args:
        error: The gRPC RpcError exception.

    Returns:
        Dictionary containing error information:
        - code: gRPC status code (int)
        - details: Error message/details (str)
        - trailing_metadata: Trailing metadata tuple
    """
    return {
        "code": error.code().value[0] if isinstance(error.code().value, tuple) else error.code().value,
        "details": error.details() or "",
        "trailing_metadata": error.trailing_metadata() or (),
    }
