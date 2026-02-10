"""Test activities for Temporal adapter testing.

This module provides async activity definitions used in Temporal workflow tests,
including simple operations, calculations, data processing, long-running tasks,
and failure scenarios for retry testing.
"""

import asyncio
from typing import Any

from temporalio import activity


@activity.defn(name="greeting_activity")
async def greeting_activity(name: str) -> str:
    """Simple async activity that returns a greeting message.

    Args:
        name (str): Name to include in the greeting.

    Returns:
        str: Greeting message.
    """
    await asyncio.sleep(0.1)  # Simulate async work
    return f"Hello, {name}!"


@activity.defn(name="calculation_activity")
async def calculation_activity(a: int, b: int, operation: str) -> int:
    """Async activity that performs mathematical operations.

    Args:
        a (int): First operand.
        b (int): Second operand.
        operation (str): Operation to perform (add, subtract, multiply, divide).

    Returns:
        int: Result of the calculation.

    Raises:
        ValueError: If operation is not supported or division by zero.
    """
    await asyncio.sleep(0.1)  # Simulate async work

    if operation == "add":
        return a + b
    if operation == "subtract":
        return a - b
    if operation == "multiply":
        return a * b
    if operation == "divide":
        if b == 0:
            raise ValueError("Division by zero")
        return a // b
    raise ValueError(f"Unsupported operation: {operation}")


@activity.defn(name="data_processing_activity")
async def data_processing_activity(data: dict[str, Any]) -> dict[str, Any]:
    """Async activity that processes and transforms data.

    Args:
        data (dict[str, Any]): Input data dictionary.

    Returns:
        dict[str, Any]: Processed data with additional fields.
    """
    await asyncio.sleep(0.2)  # Simulate async processing

    processed = {
        "original": data,
        "processed": True,
        "item_count": len(data),
        "keys": list(data.keys()),
    }

    return processed


@activity.defn(name="long_running_activity")
async def long_running_activity(duration: int) -> str:
    """Async activity that runs for a specified duration with heartbeat support.

    Args:
        duration (int): Duration to run in seconds.

    Returns:
        str: Completion message.
    """
    # Send heartbeats during execution
    for i in range(duration):
        activity.heartbeat(f"Progress: {i + 1}/{duration}")
        await asyncio.sleep(1)

    return f"Completed after {duration} seconds"


@activity.defn(name="failing_activity")
async def failing_activity(should_fail: bool) -> str:
    """Async activity that can fail for retry testing.

    Args:
        should_fail (bool): Whether the activity should fail.

    Returns:
        str: Success message if should_fail is False.

    Raises:
        RuntimeError: If should_fail is True.
    """
    await asyncio.sleep(0.1)  # Simulate async work

    if should_fail:
        raise RuntimeError("Activity intentionally failed for testing")

    return "Activity completed successfully"


@activity.defn(name="counter_activity")
async def counter_activity(value: int) -> int:
    """Simple activity that returns the input value.

    Used for testing signal/query workflows.

    Args:
        value (int): Input value.

    Returns:
        int: The same value.
    """
    await asyncio.sleep(0.05)
    return value


@activity.defn(name="status_activity")
async def status_activity(status: str) -> str:
    """Simple activity that returns the input status.

    Used for testing signal/query workflows.

    Args:
        status (str): Input status.

    Returns:
        str: The same status.
    """
    await asyncio.sleep(0.05)
    return status
