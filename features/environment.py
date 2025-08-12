"""Environment configuration for behave tests.

This file configures the environment for running BDD tests with behave,
particularly focusing on setup/teardown of resources like databases
and handling async operations.
"""

import os
import logging
import uuid

from behave.model import Scenario
from behave.runner import Context
from features.scenario_context_pool_manager import ScenarioContextPoolManager
from pydantic_settings import SettingsConfigDict

from archipy.adapters.base.sqlalchemy.session_manager_registry import SessionManagerRegistry
from archipy.configs.base_config import BaseConfig

from features.test_containers import ContainerManager

from testcontainers.core.config import testcontainers_config

class TestConfig(BaseConfig):
    model_config = SettingsConfigDict(
        env_file=".env.test",
    )

    # Test container images
    REDIS__IMAGE: str = "redis:7-alpine"
    POSTGRES__IMAGE: str = "postgres:17"
    ELASTIC__IMAGE: str = "elasticsearch:9.1.0"
    KAFKA__IMAGE: str = "confluentinc/cp-kafka:7.4.0"
    MINIO__IMAGE: str = "minio/minio:latest"
    KEYCLOAK__IMAGE: str = "quay.io/keycloak/keycloak:23.0"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Configure testcontainers to use custom ryuk image
        ryuk_image = os.getenv("TESTCONTAINERS_RYUK_CONTAINER_IMAGE")
        if ryuk_image:
            testcontainers_config.ryuk_image = ryuk_image



# Initialize global config
config = TestConfig()
BaseConfig.set_global(config)


def before_all(context: Context):
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

    # Initialize and start all test containers
    context.test_containers = ContainerManager
    context.test_containers.start_all()


def before_scenario(context: Context, scenario: Scenario):
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

    # Assign test config to scenario context
    try:
        scenario_context.store("test_config", config)
        scenario_context.store("test_containers", context.test_containers)
    except Exception as e:
        logger.exception(f"Error setting test config: {e}")



def after_scenario(context: Context, scenario: Scenario):
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


def after_all(context: Context):
    """Cleanup performed after all tests run."""
    # Stop all test containers
    if hasattr(context, "test_containers"):
        context.test_containers.stop_all()

    # Clean up any remaining resources
    if hasattr(context, "scenario_context_pool"):
        context.scenario_context_pool.cleanup_all()

    context.logger.info("Test suite completed")
