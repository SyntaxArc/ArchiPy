"""This module provides utilities to help with async testing in behave.

It focuses on solving the problem of SQLAlchemy async scoped sessions
using current_task() for scoping, which can cause issues in behave tests.
"""

from archipy.models.entities import BaseEntity


def get_current_scenario_context(context):
    """Get the current scenario context from the pool.

    Args:
        context: The behave context object

    Returns:
        The scenario-specific context for the current scenario

    Raises:
        AttributeError: If no scenario context pool or current scenario is available
    """
    if not hasattr(context, "scenario_context_pool"):
        raise AttributeError("No scenario context pool available")

    # Get the current scenario
    current_scenario = context.scenario_context_pool.get_context(context.scenario.id)
    if not current_scenario:
        raise AttributeError("No current scenario available")

    # Get the scenario ID
    scenario_id = getattr(current_scenario, "scenario_id", None)
    if not scenario_id:
        raise AttributeError("No scenario ID available")

    # Get the scenario context from the pool
    return current_scenario


def get_adapter(context):
    """Get the adapter for the current scenario."""
    scenario_context = get_current_scenario_context(context)

    adapter = scenario_context.adapter
    if not adapter:
        raise AttributeError("No adapter found in scenario context. Make sure the database is initialized.")

    return adapter


def get_async_adapter(context):
    """Get the async adapter for the current scenario."""
    scenario_context = get_current_scenario_context(context)

    async_adapter = scenario_context.async_adapter
    if not async_adapter:
        raise AttributeError("No async adapter found in scenario context. Make sure the database is initialized.")

    return async_adapter


def safe_has_attr(obj, attr):
    """A truly safe way to check if an attribute exists on an object.

    This uses the __dict__ directly rather than hasattr() which can
    trigger __getattr__ and raise exceptions.

    Args:
        obj: The object to check
        attr: The attribute name to check for

    Returns:
        bool: True if the attribute exists, False otherwise
    """
    # For Context objects in behave, check the dictionary directly
    if hasattr(obj, "__dict__"):
        return attr in obj.__dict__

    # Fallback to normal hasattr for other objects
    try:
        return hasattr(obj, attr)
    except:
        return False


def safe_get_attr(obj, attr, default=None):
    """A truly safe way to get an attribute from an object.

    This uses the __dict__ directly rather than getattr() which can
    trigger __getattr__ and raise exceptions.

    Args:
        obj: The object to get the attribute from
        attr: The attribute name to get
        default: The default value to return if the attribute doesn't exist

    Returns:
        The attribute value, or the default if it doesn't exist
    """
    # For Context objects in behave, check the dictionary directly
    if hasattr(obj, "__dict__"):
        return obj.__dict__.get(attr, default)

    # Fallback to normal getattr for other objects
    try:
        return getattr(obj, attr, default)
    except:
        return default


def safe_set_attr(obj, attr, value):
    """A truly safe way to set an attribute on an object.

    This uses the __dict__ directly rather than setattr() which can
    trigger __getattr__ and raise exceptions.

    Args:
        obj: The object to set the attribute on
        attr: The attribute name to set
        value: The value to set
    """
    # For Context objects in behave, set the dictionary directly
    if hasattr(obj, "__dict__"):
        obj.__dict__[attr] = value
    else:
        # Fallback to normal setattr for other objects
        setattr(obj, attr, value)


async def async_schema_setup(async_adapter):
    """Set up database schema for async adapter."""
    # Use AsyncEngine.begin() for proper transaction handling
    async with async_adapter.session_manager.engine.begin() as conn:
        # Drop all tables (but only if they exist)
        await conn.run_sync(BaseEntity.metadata.drop_all)
        # Create all tables
        await conn.run_sync(BaseEntity.metadata.create_all)


# Temporal-specific helper functions
def wait_for_temporal_condition(condition_func, max_retries: int = 10, delay: float = 0.5) -> bool:
    """Wait for a Temporal condition to be met with retries.

    Args:
        condition_func: Function that returns True when condition is met.
        max_retries (int): Maximum number of retry attempts. Defaults to 10.
        delay (float): Delay between retries in seconds. Defaults to 0.5.

    Returns:
        bool: True if condition was met, False if max retries exceeded.
    """
    import time

    for attempt in range(max_retries):
        try:
            if condition_func():
                return True
        except Exception:
            pass
        if attempt < max_retries - 1:
            time.sleep(delay)
    return False


def create_test_workflow_id(prefix: str = "test") -> str:
    """Generate a unique workflow ID for testing.

    Args:
        prefix (str): Prefix for the workflow ID. Defaults to "test".

    Returns:
        str: Unique workflow ID with timestamp and UUID.
    """
    import time
    from uuid import uuid4

    timestamp = int(time.time() * 1000)
    unique_id = str(uuid4())[:8]
    return f"{prefix}-{timestamp}-{unique_id}"
