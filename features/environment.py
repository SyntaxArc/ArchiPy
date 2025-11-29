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
    TESTCONTAINERS_RYUK_CONTAINER_IMAGE: str | None = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Configure testcontainers to use custom ryuk image
        if self.TESTCONTAINERS_RYUK_CONTAINER_IMAGE:
            testcontainers_config.ryuk_image = self.TESTCONTAINERS_RYUK_CONTAINER_IMAGE


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

    # Initialize container manager
    context.test_containers = ContainerManager

    # Collect feature-level tags from all features being executed
    all_tags: set[str] = set()
    if hasattr(context, "features") and context.features:
        for feature in context.features:
            # Get feature-level tags - convert Tag objects to strings
            if hasattr(feature, "tags") and feature.tags:
                feature_tags = [str(tag) for tag in feature.tags]
                all_tags.update(feature_tags)
                context.logger.debug(f"Feature '{feature.name}' has tags: {feature_tags}")

    # Extract required containers from tags
    required_containers = ContainerManager.extract_containers_from_tags(list(all_tags))

    if required_containers:
        context.logger.info(f"Detected required containers from tags: {sorted(required_containers)}")
        ContainerManager.start_containers(list(required_containers))
    else:
        context.logger.info("No container tags detected, no containers will be started")


def before_feature(context: Context, feature: Feature):
    """Setup performed before each feature runs.

    This is a fallback to ensure containers are started if they weren't started in before_all().
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

    # Assign test containers to scenario context
    try:
        scenario_context.store("test_containers", context.test_containers)
    except Exception as e:
        logger.exception(f"Error setting test containers: {e}")


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
