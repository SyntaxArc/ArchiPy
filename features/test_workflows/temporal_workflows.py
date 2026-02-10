"""Test workflows for Temporal adapter testing.

This module provides workflow definitions used in Temporal adapter tests,
including simple workflows, signal/query workflows, timeout scenarios,
retry workflows, and scheduled workflows.
"""

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activities - using with_start_activity to reference them
with workflow.unsafe.imports_passed_through():
    from features.test_workflows.temporal_activities import (
        calculation_activity,
        counter_activity,
        data_processing_activity,
        failing_activity,
        greeting_activity,
        long_running_activity,
        status_activity,
    )


@workflow.defn(name="GreetingWorkflow")
class GreetingWorkflow:
    """Simple workflow that calls a greeting activity.

    Used for basic workflow execution testing.
    """

    @workflow.run
    async def run(self, name: str) -> str:
        """Execute the greeting workflow.

        Args:
            name (str): Name to greet.

        Returns:
            str: Greeting message from activity.
        """
        result = await workflow.execute_activity(
            greeting_activity,
            name,
            start_to_close_timeout=timedelta(seconds=10),
        )
        return result


@workflow.defn(name="CalculatorWorkflow")
class CalculatorWorkflow:
    """Workflow that performs multiple calculations.

    Used for testing workflows with multiple activity calls.
    """

    @workflow.run
    async def run(self, operations: list[dict[str, Any]]) -> list[int]:
        """Execute multiple calculation activities.

        Args:
            operations (list[dict[str, Any]]): List of operation dicts with keys: a, b, operation.

        Returns:
            list[int]: List of calculation results.
        """
        results = []
        for op in operations:
            result = await workflow.execute_activity(
                calculation_activity,
                args=[op["a"], op["b"], op["operation"]],
                start_to_close_timeout=timedelta(seconds=10),
            )
            results.append(result)
        return results


@workflow.defn(name="SignalQueryWorkflow")
class SignalQueryWorkflow:
    """Workflow with signal and query handlers.

    Used for testing workflow signals and queries.
    """

    def __init__(self) -> None:
        """Initialize workflow state."""
        self._counter = 0
        self._status = "initialized"
        self._completed = False

    @workflow.run
    async def run(self) -> dict[str, Any]:
        """Execute the signal/query workflow.

        Waits for signals to update state and can be queried for current state.

        Returns:
            dict[str, Any]: Final workflow state.
        """
        # Wait for completion signal or timeout
        await workflow.wait_condition(lambda: self._completed, timeout=timedelta(seconds=30))

        return {
            "counter": self._counter,
            "status": self._status,
            "completed": self._completed,
        }

    @workflow.signal
    async def update_counter(self, value: int) -> None:
        """Signal handler to update counter.

        Args:
            value (int): Value to add to counter.
        """
        self._counter += value

    @workflow.signal
    async def set_status(self, status: str) -> None:
        """Signal handler to set status.

        Args:
            status (str): New status value.
        """
        self._status = status

    @workflow.signal
    async def complete(self) -> None:
        """Signal handler to mark workflow as completed."""
        self._completed = True

    @workflow.query
    def get_counter(self) -> int:
        """Query handler to get current counter value.

        Returns:
            int: Current counter value.
        """
        return self._counter

    @workflow.query
    def get_status(self) -> str:
        """Query handler to get current status.

        Returns:
            str: Current status.
        """
        return self._status


@workflow.defn(name="TimeoutWorkflow")
class TimeoutWorkflow:
    """Workflow for testing timeout scenarios.

    Used for testing workflow execution and run timeouts.
    """

    @workflow.run
    async def run(self, sleep_duration: int) -> str:
        """Execute workflow that sleeps for specified duration.

        Args:
            sleep_duration (int): Duration to sleep in seconds.

        Returns:
            str: Completion message.
        """
        await workflow.sleep(sleep_duration)
        return f"Completed after {sleep_duration} seconds"


@workflow.defn(name="RetryWorkflow")
class RetryWorkflow:
    """Workflow that calls a failing activity with retry policy.

    Used for testing activity retry behavior.
    """

    @workflow.run
    async def run(self, should_fail: bool, max_attempts: int = 3) -> str:
        """Execute workflow with failing activity.

        Args:
            should_fail (bool): Whether the activity should fail.
            max_attempts (int): Maximum retry attempts. Defaults to 3.

        Returns:
            str: Result from activity or error message.
        """
        try:
            result = await workflow.execute_activity(
                failing_activity,
                should_fail,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(
                    maximum_attempts=max_attempts,
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(seconds=5),
                    backoff_coefficient=2.0,
                ),
            )
            return result
        except Exception as e:
            return f"Activity failed after retries: {e!s}"


@workflow.defn(name="ScheduledWorkflow")
class ScheduledWorkflow:
    """Simple workflow for schedule testing.

    Used for testing scheduled workflow execution.
    """

    @workflow.run
    async def run(self, message: str = "scheduled") -> str:
        """Execute scheduled workflow.

        Args:
            message (str): Message to include in result. Defaults to "scheduled".

        Returns:
            str: Completion message with workflow info.
        """
        workflow_id = workflow.info().workflow_id
        return f"Scheduled workflow {workflow_id} executed: {message}"


@workflow.defn(name="DataProcessingWorkflow")
class DataProcessingWorkflow:
    """Workflow that processes data through an activity.

    Used for testing workflows with complex data types.
    """

    @workflow.run
    async def run(self, data: dict[str, Any]) -> dict[str, Any]:
        """Execute data processing workflow.

        Args:
            data (dict[str, Any]): Data to process.

        Returns:
            dict[str, Any]: Processed data from activity.
        """
        result = await workflow.execute_activity(
            data_processing_activity,
            data,
            start_to_close_timeout=timedelta(seconds=10),
        )
        return result


@workflow.defn(name="LongRunningWorkflow")
class LongRunningWorkflow:
    """Workflow with long-running activity that sends heartbeats.

    Used for testing activity heartbeat behavior.
    """

    @workflow.run
    async def run(self, duration: int) -> str:
        """Execute long-running workflow.

        Args:
            duration (int): Duration for activity to run in seconds.

        Returns:
            str: Completion message from activity.
        """
        result = await workflow.execute_activity(
            long_running_activity,
            duration,
            start_to_close_timeout=timedelta(seconds=duration + 10),
            heartbeat_timeout=timedelta(seconds=5),
        )
        return result


@workflow.defn(name="ConcurrentActivitiesWorkflow")
class ConcurrentActivitiesWorkflow:
    """Workflow that executes multiple activities concurrently.

    Used for testing concurrent activity execution.
    """

    @workflow.run
    async def run(self, names: list[str]) -> list[str]:
        """Execute multiple greeting activities concurrently.

        Args:
            names (list[str]): List of names to greet.

        Returns:
            list[str]: List of greeting messages.
        """
        # Execute activities concurrently using asyncio.gather
        tasks = [
            workflow.execute_activity(
                greeting_activity,
                name,
                start_to_close_timeout=timedelta(seconds=10),
            )
            for name in names
        ]

        results = await asyncio.gather(*tasks)
        return list(results)
