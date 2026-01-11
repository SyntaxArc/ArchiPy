"""Environment configuration for behave tests.

This file configures the environment for running BDD tests with behave,
particularly focusing on setup/teardown of resources like databases
and handling async operations.
"""

import logging
import uuid

from behave.model import Feature, Scenario
from behave.runner import Context
from features.scenario_context_pool_manager import ScenarioContextPoolManager
from features.test_containers import ContainerManager
from pydantic_settings import SettingsConfigDict
from testcontainers.core.config import testcontainers_config

from archipy.adapters.base.sqlalchemy.session_manager_registry import SessionManagerRegistry
from archipy.configs.base_config import BaseConfig


class TestConfig(BaseConfig):
    """Configuration for test environment with container images."""

    model_config = SettingsConfigDict(
        env_file=".env.test",
    )

    # Test container images
    REDIS__IMAGE: str
    POSTGRES__IMAGE: str
    ELASTIC__IMAGE: str
    KAFKA__IMAGE: str
    MINIO__IMAGE: str
    KEYCLOAK__IMAGE: str
    SCYLLADB__IMAGE: str
    STARROCKS__IMAGE: str
    TESTCONTAINERS_RYUK_CONTAINER_IMAGE: str | None = None

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        # Configure testcontainers to use custom ryuk image
        if self.TESTCONTAINERS_RYUK_CONTAINER_IMAGE:
            testcontainers_config.ryuk_image = self.TESTCONTAINERS_RYUK_CONTAINER_IMAGE


# Initialize global config
config = TestConfig()
BaseConfig.set_global(config)


def before_all(context: Context) -> None:
    """Setup performed before all tests run.

    Args:
        context: The behave context object
    """
    # Configure logging for tests
    logging.basicConfig(level=logging.INFO)
    context.logger = logging.getLogger("behave.tests")
    context.logger.info("Starting test suite")

    # Create the scenario context pool manager
    context.scenario_context_pool = ScenarioContextPoolManager()

    # Initialize container manager
    context.test_containers = ContainerManager


def before_feature(context: Context, feature: Feature) -> None:
    """Setup performed before each feature runs.

    Starts containers required by the feature based on its tags.
    Also starts gRPC servers for gRPC error handling tests.
    """
    # Extract feature-level tags - convert Tag objects to strings
    if hasattr(feature, "tags") and feature.tags:
        feature_tags = [str(tag) for tag in feature.tags]

        if feature_tags:
            # Extract required containers from tags
            required_containers = ContainerManager.extract_containers_from_tags(feature_tags)

            if required_containers:
                # Start containers if not already started (start_containers handles this)
                ContainerManager.start_containers(list(required_containers))

    # Start gRPC servers for gRPC error handling feature
    # Check feature filename or name
    feature_filename = ""
    if hasattr(feature, "filename"):
        feature_filename = str(feature.filename) if feature.filename else ""
    feature_name = getattr(feature, "name", "") or ""

    if "grpc_error_handling" in feature_filename or "grpc_error" in feature_name.lower():
        try:
            from features.test_servers import (
                create_test_async_grpc_server,
                create_test_async_grpc_servicer,
                create_test_grpc_server,
                create_test_grpc_servicer,
                start_async_grpc_server_sync,
                start_grpc_server,
            )

            # Create default servicers (will be replaced per scenario)
            default_sync_servicer = create_test_grpc_servicer()
            default_async_servicer = create_test_async_grpc_servicer()

            # Create and start sync server
            sync_server = create_test_grpc_server()
            sync_server, sync_port = start_grpc_server(sync_server, default_sync_servicer)

            # Store sync server first (even if async fails)
            context.grpc_sync_server = sync_server
            context.grpc_sync_port = sync_port
            context.grpc_sync_servicer = default_sync_servicer

            # Try to start async server (may fail due to event loop issues)
            try:
                async_server = create_test_async_grpc_server()
                async_server, async_port, async_thread, async_loop = start_async_grpc_server_sync(
                    async_server, default_async_servicer,
                )
                context.grpc_async_server = async_server
                context.grpc_async_port = async_port
                context.grpc_async_servicer = default_async_servicer
                context.grpc_async_thread = async_thread
                context.grpc_async_loop = async_loop
                context.logger.info(f"Started gRPC servers - sync on port {sync_port}, async on port {async_port}")
            except Exception as async_error:
                context.logger.warning(f"Failed to start async gRPC server: {async_error}. Async tests may fail.")
                # Create a placeholder so tests don't fail on attribute access
                context.grpc_async_server = None
                context.grpc_async_port = None
                context.grpc_async_servicer = None
                context.grpc_async_thread = None
                context.grpc_async_loop = None
                context.logger.info(f"Started gRPC sync server on port {sync_port} (async server failed to start)")

        except Exception as e:
            context.logger.warning(f"Failed to start gRPC servers: {e}. gRPC tests may fail.")


def before_scenario(context: Context, scenario: Scenario) -> None:
    """Setup performed before each scenario runs."""
    # Set up logger
    logger = logging.getLogger("behave.tests")
    context.logger = logger

    # Generate a unique scenario ID if not present
    if not hasattr(scenario, "id"):
        scenario.id = str(uuid.uuid4())

    # Get the scenario-specific context from the pool
    scenario_context = context.scenario_context_pool.get_context(scenario.id)

    logger.info(f"Starting scenario: {scenario.name} (ID: {scenario.id})")

    # Assign test containers to scenario context
    try:
        scenario_context.store("test_containers", context.test_containers)
    except Exception:
        logger.exception("Error setting test containers")


def after_scenario(context: Context, scenario: Scenario) -> None:
    """Cleanup performed after each scenario runs."""
    logger = getattr(context, "logger", logging.getLogger("behave.environment"))

    # Get the scenario ID
    scenario_id = getattr(scenario, "id", "unknown")
    logger.info(f"Cleaning up scenario: {scenario.name} (ID: {scenario_id})")

    # Clean up the scenario context and remove from pool
    if hasattr(context, "scenario_context_pool"):
        context.scenario_context_pool.cleanup_context(scenario_id)

    # Reset the registry
    SessionManagerRegistry.reset()


def after_feature(context: Context, feature: Feature) -> None:
    """Cleanup performed after each feature runs."""
    # Stop gRPC servers if they were started
    if hasattr(context, "grpc_sync_server"):
        try:
            context.grpc_sync_server.stop(grace=None)
            context.logger.info("Stopped sync gRPC server")
        except Exception as e:
            context.logger.warning(f"Error stopping sync gRPC server: {e}")

    if hasattr(context, "grpc_async_server") and context.grpc_async_server is not None:
        try:
            from features.test_servers import stop_async_grpc_server_gracefully

            if hasattr(context, "grpc_async_thread") and hasattr(context, "grpc_async_loop"):
                stop_async_grpc_server_gracefully(
                    context.grpc_async_server,
                    context.grpc_async_thread,
                    context.grpc_async_loop,
                    timeout=5.0,
                )
                context.logger.info("Stopped async gRPC server gracefully")
            else:
                # Fallback: try to stop without thread/loop info
                import asyncio

                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                loop.run_until_complete(context.grpc_async_server.stop(grace=2.0))
                context.logger.info("Stopped async gRPC server (fallback method)")
        except Exception as e:
            context.logger.warning(f"Error stopping async gRPC server: {e}")

    # Stop all test containers to free up memory
    if hasattr(context, "test_containers"):
        context.test_containers.stop_all()
        context.logger.info("Stopped all test containers after feature")


def after_all(context: Context) -> None:
    """Cleanup performed after all tests run."""
    # Stop all test containers
    if hasattr(context, "test_containers"):
        context.test_containers.stop_all()

    # Clean up any remaining resources
    if hasattr(context, "scenario_context_pool"):
        context.scenario_context_pool.cleanup_all()

    context.logger.info("Test suite completed")
