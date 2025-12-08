"""Test server utilities for FastAPI and gRPC error handling tests."""

import json
import socket
from typing import Any

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.app_utils import AppUtils
from archipy.models.errors import BaseError

try:
    import grpc
    from grpc import aio as grpc_aio
    from grpc.aio import server as async_server

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    grpc = None
    grpc_aio = None
    async_server = None

try:
    import sys
    from pathlib import Path

    # Add proto directory to path so generated files can import each other
    proto_dir = Path(__file__).parent / "proto"
    if str(proto_dir) not in sys.path:
        sys.path.insert(0, str(proto_dir))

    import test_service_pb2
    import test_service_pb2_grpc

    PROTOBUF_AVAILABLE = True
except ImportError:
    PROTOBUF_AVAILABLE = False
    test_service_pb2 = None
    test_service_pb2_grpc = None

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from starlette.testclient import TestClient as StarletteTestClient

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    TestClient = None
    StarletteTestClient = None


def create_test_fastapi_app() -> FastAPI:
    """Create a FastAPI test application with error handling configured.

    Returns:
        FastAPI: Configured FastAPI application instance.
    """
    if not FASTAPI_AVAILABLE:
        raise RuntimeError("FastAPI is not available")

    config = BaseConfig.global_config()
    return AppUtils.create_fastapi_app(config)


def create_test_grpc_server() -> grpc.Server:
    """Create a sync gRPC test server with error handling interceptors.

    Returns:
        grpc.Server: Configured sync gRPC server instance.
    """
    if not GRPC_AVAILABLE:
        raise RuntimeError("gRPC is not available")

    config = BaseConfig.global_config()
    return AppUtils.create_grpc_app(config)


def stop_async_grpc_server_gracefully(
    server: async_server, thread: threading.Thread, loop: asyncio.AbstractEventLoop, timeout: float = 5.0,
) -> None:
    """Stop an async gRPC server gracefully.

    Args:
        server: The async gRPC server to stop.
        thread: The thread running the server's event loop.
        loop: The event loop running the server.
        timeout: Maximum time to wait for graceful shutdown in seconds.
    """
    import asyncio
    import threading
    import logging

    if not loop.is_running():
        # Loop already stopped
        return

    # Suppress BlockingIOError warnings during shutdown
    logger = logging.getLogger("asyncio")
    original_level = logger.level

    def stop_in_loop():
        """Stop the server in its own event loop."""
        try:
            # Schedule server stop in the event loop
            async def stop():
                try:
                    # Stop the server with grace period
                    await server.stop(grace=2.0)  # Give 2 seconds for graceful shutdown
                except Exception:
                    pass  # Ignore errors during shutdown
                finally:
                    # Wait a bit for completion queue to settle
                    await asyncio.sleep(0.1)
                    # Always stop the loop
                    loop.call_soon_threadsafe(loop.stop)

            # Schedule the stop coroutine
            future = asyncio.run_coroutine_threadsafe(stop(), loop)
            # Wait for it to complete (with timeout)
            try:
                future.result(timeout=3.0)
            except Exception:
                # If stop fails, just stop the loop
                loop.call_soon_threadsafe(loop.stop)
        except Exception:
            # If we can't schedule, just stop the loop
            try:
                loop.call_soon_threadsafe(loop.stop)
            except Exception:
                pass

    # Temporarily suppress asyncio error logging
    try:
        logger.setLevel(logging.CRITICAL)
        # Stop the server from the main thread
        stop_in_loop()

        # Wait for thread to finish (with timeout)
        thread.join(timeout=timeout)

        if thread.is_alive():
            # Force stop if still alive - stop the loop and close it
            try:
                if loop.is_running():
                    loop.call_soon_threadsafe(loop.stop)
                else:
                    loop.close()
            except Exception:
                pass
            thread.join(timeout=1.0)
    finally:
        # Restore original logging level
        logger.setLevel(original_level)


def create_test_async_grpc_server() -> async_server:
    """Create an async gRPC test server with error handling interceptors.

    Returns:
        grpc.aio.Server: Configured async gRPC server instance.
    """
    if not GRPC_AVAILABLE:
        raise RuntimeError("gRPC is not available")

    config = BaseConfig.global_config()
    return AppUtils.create_async_grpc_app(config)


class TestServiceServicer(test_service_pb2_grpc.TestServiceServicer):
    """Real gRPC servicer implementation for error handling tests.

    This servicer implements the TestService from the protobuf definition
    and can raise various errors for testing purposes.
    The servicer is mutable - you can change its configuration at runtime.
    """

    def __init__(
        self,
        error_to_raise: BaseError | None = None,
        unexpected_error: bool = False,
        validation_error: bool = False,
    ) -> None:
        """Initialize the test servicer.

        Args:
            error_to_raise: The error to raise when methods are called.
            unexpected_error: If True, raise a generic Exception instead of BaseError.
            validation_error: If True, raise a Pydantic ValidationError.
        """
        if not PROTOBUF_AVAILABLE:
            raise RuntimeError("Protobuf files are not available. Make sure they are compiled.")
        self.error_to_raise = error_to_raise
        self.unexpected_error = unexpected_error
        self.validation_error = validation_error

    def configure(
        self,
        error_to_raise: BaseError | None = None,
        unexpected_error: bool = False,
        validation_error: bool = False,
    ) -> None:
        """Update the servicer configuration at runtime.

        Args:
            error_to_raise: The error to raise when methods are called.
            unexpected_error: If True, raise a generic Exception instead of BaseError.
            validation_error: If True, raise a Pydantic ValidationError.
        """
        self.error_to_raise = error_to_raise
        self.unexpected_error = unexpected_error
        self.validation_error = validation_error

    def TestMethod(self, request: test_service_pb2.TestRequest, context: grpc.ServicerContext) -> test_service_pb2.TestResponse:
        """Test method that can raise errors (sync implementation).

        Args:
            request: The gRPC TestRequest.
            context: The gRPC servicer context.

        Returns:
            TestResponse: The response message (never reached if error is raised).
        """
        if self.validation_error:
            from pydantic import ValidationError

            raise ValidationError.from_exception_data(
                "TestRequest",
                [{"type": "missing", "loc": ("data",), "msg": "Field required", "input": {}}],
            )
        if self.unexpected_error:
            raise ValueError("Unexpected error for testing")
        if self.error_to_raise:
            raise self.error_to_raise
        return test_service_pb2.TestResponse(result="success")


class TestServiceAsyncServicer(test_service_pb2_grpc.TestServiceServicer):
    """Real async gRPC servicer implementation for error handling tests.

    This servicer implements the TestService from the protobuf definition
    with async methods and can raise various errors for testing purposes.
    Note: Uses the same base class as sync, but methods are async.
    The servicer is mutable - you can change its configuration at runtime.
    """

    def __init__(
        self,
        error_to_raise: BaseError | None = None,
        unexpected_error: bool = False,
        validation_error: bool = False,
    ) -> None:
        """Initialize the test servicer.

        Args:
            error_to_raise: The error to raise when methods are called.
            unexpected_error: If True, raise a generic Exception instead of BaseError.
            validation_error: If True, raise a Pydantic ValidationError.
        """
        if not PROTOBUF_AVAILABLE:
            raise RuntimeError("Protobuf files are not available. Make sure they are compiled.")
        self.error_to_raise = error_to_raise
        self.unexpected_error = unexpected_error
        self.validation_error = validation_error

    def configure(
        self,
        error_to_raise: BaseError | None = None,
        unexpected_error: bool = False,
        validation_error: bool = False,
    ) -> None:
        """Update the servicer configuration at runtime.

        Args:
            error_to_raise: The error to raise when methods are called.
            unexpected_error: If True, raise a generic Exception instead of BaseError.
            validation_error: If True, raise a Pydantic ValidationError.
        """
        self.error_to_raise = error_to_raise
        self.unexpected_error = unexpected_error
        self.validation_error = validation_error

    async def TestMethod(
        self, request: test_service_pb2.TestRequest, context: grpc.aio.ServicerContext,
    ) -> test_service_pb2.TestResponse:
        """Test method that can raise errors (async implementation).

        Args:
            request: The gRPC TestRequest.
            context: The gRPC async servicer context.

        Returns:
            TestResponse: The response message (never reached if error is raised).
        """
        if self.validation_error:
            from pydantic import ValidationError

            raise ValidationError.from_exception_data(
                "TestRequest",
                [{"type": "missing", "loc": ("data",), "msg": "Field required", "input": {}}],
            )
        if self.unexpected_error:
            raise ValueError("Unexpected error for testing")
        if self.error_to_raise:
            raise self.error_to_raise
        return test_service_pb2.TestResponse(result="success")


def create_test_grpc_servicer(
    error_to_raise: BaseError | None = None,
    unexpected_error: bool = False,
    validation_error: bool = False,
) -> TestServiceServicer:
    """Create a sync test gRPC servicer instance.

    Args:
        error_to_raise: The error to raise when methods are called.
        unexpected_error: If True, raise a generic Exception instead of BaseError.
        validation_error: If True, raise a Pydantic ValidationError.

    Returns:
        TestServiceServicer: Test servicer instance.
    """
    return TestServiceServicer(
        error_to_raise=error_to_raise,
        unexpected_error=unexpected_error,
        validation_error=validation_error,
    )


def create_test_async_grpc_servicer(
    error_to_raise: BaseError | None = None,
    unexpected_error: bool = False,
    validation_error: bool = False,
) -> TestServiceAsyncServicer:
    """Create an async test gRPC servicer instance.

    Args:
        error_to_raise: The error to raise when methods are called.
        unexpected_error: If True, raise a generic Exception instead of BaseError.
        validation_error: If True, raise a Pydantic ValidationError.

    Returns:
        TestServiceAsyncServicer: Test async servicer instance.
    """
    return TestServiceAsyncServicer(
        error_to_raise=error_to_raise,
        unexpected_error=unexpected_error,
        validation_error=validation_error,
    )


def find_free_port() -> int:
    """Find a free port on the system.

    Returns:
        int: An available port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def start_grpc_server(server: grpc.Server, servicer: TestServiceServicer) -> tuple[grpc.Server, int]:
    """Start a gRPC server on a dynamic port with the given servicer.

    Args:
        server: The gRPC server instance.
        servicer: The servicer implementation to register.

    Returns:
        Tuple of (server, actual_port): The server and the port it's listening on.
    """
    if not GRPC_AVAILABLE:
        raise RuntimeError("gRPC is not available")
    if not PROTOBUF_AVAILABLE:
        raise RuntimeError("Protobuf files are not available")

    # Register the servicer
    test_service_pb2_grpc.add_TestServiceServicer_to_server(servicer, server)

    # Find a free port and bind
    port = find_free_port()
    address = f"[::]:{port}"
    server.add_insecure_port(address)
    server.start()

    return server, port


def start_async_grpc_server_sync(server: async_server, servicer: TestServiceAsyncServicer) -> tuple[async_server, int, threading.Thread, asyncio.AbstractEventLoop]:
    """Start an async gRPC server on a dynamic port with the given servicer (synchronous wrapper).

    Args:
        server: The async gRPC server instance (not used, created in thread).
        servicer: The async servicer implementation to register.

    Returns:
        Tuple of (server, port, thread, loop): The server, port, thread, and event loop.
    """
    import asyncio
    import threading
    import time

    if not GRPC_AVAILABLE:
        raise RuntimeError("gRPC is not available")
    if not PROTOBUF_AVAILABLE:
        raise RuntimeError("Protobuf files are not available")

    # Find a free port first
    port = find_free_port()
    address = f"[::]:{port}"

    # Start server in a new thread with its own event loop
    # We need to create the server in the thread to avoid event loop conflicts
    exception_result: list[Exception] = []
    started_event = threading.Event()
    server_ref: list[async_server] = []
    loop_ref: list[asyncio.AbstractEventLoop] = []

    def run_server():
        """Run the async server in a new event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop_ref.append(loop)

        # Suppress BlockingIOError from gRPC completion queue during shutdown
        def exception_handler(loop, context):
            """Handle exceptions in the event loop, suppressing expected BlockingIOError."""
            exception = context.get("exception")
            if isinstance(exception, OSError) and exception.errno == 11:  # EAGAIN/EWOULDBLOCK
                # Expected during gRPC server shutdown - suppress it
                return
            # For other exceptions, use default handler
            loop.default_exception_handler(context)

        loop.set_exception_handler(exception_handler)

        try:
            # Create a fresh server in this thread's event loop
            from archipy.configs.base_config import BaseConfig
            from archipy.helpers.utils.app_utils import AppUtils

            config = BaseConfig.global_config()
            new_server = AppUtils.create_async_grpc_app(config)

            # Register the servicer
            test_service_pb2_grpc.add_TestServiceServicer_to_server(servicer, new_server)

            # Bind to port and start
            new_server.add_insecure_port(address)
            loop.run_until_complete(new_server.start())
            server_ref.append(new_server)
            started_event.set()

            # Keep the loop running to serve requests
            try:
                loop.run_forever()
            except Exception:
                # Expected when loop is stopped
                pass
        except Exception as e:
            exception_result.append(e)
            started_event.set()

    thread = threading.Thread(target=run_server, daemon=True)  # Daemon so it doesn't block test exit
    thread.start()

    # Wait for server to start (with timeout)
    if not started_event.wait(timeout=3.0):
        raise RuntimeError("Async gRPC server failed to start within timeout")

    if exception_result:
        raise exception_result[0]

    if not server_ref or not loop_ref:
        raise RuntimeError("Async gRPC server was not created")

    # Give it a moment to fully initialize
    time.sleep(0.2)

    return server_ref[0], port, thread, loop_ref[0]


def parse_grpc_metadata(metadata: tuple[tuple[str, str | bytes], ...] | None) -> dict[str, Any]:
    """Parse gRPC trailing metadata into a dictionary.

    Args:
        metadata: gRPC trailing metadata tuple.

    Returns:
        Dictionary containing parsed metadata.
    """
    if not metadata:
        return {}

    result: dict[str, Any] = {}
    for key, value in metadata:
        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8")
            except UnicodeDecodeError:
                continue

        if key == "additional_data":
            try:
                result[key] = json.loads(str(value))
            except (json.JSONDecodeError, TypeError):
                result[key] = str(value)
        else:
            result[key] = value

    return result
