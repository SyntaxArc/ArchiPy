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
from temporalio.exceptions import ActivityError, ApplicationError

# Import activities - using with_start_activity to reference them
with workflow.unsafe.imports_passed_through():
    from features.test_workflows.temporal_activities import (
        calculation_activity,
        charge_payment,
        data_processing_activity,
        failing_activity,
        greeting_activity,
        long_running_activity,
        notify_customer,
        refund_payment,
        release_inventory,
        reserve_inventory,
        ship_order,
    )
    from features.test_workflows.temporal_activities import OrderPayload

    from archipy.adapters.temporal.base import BaseWorkflow


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


@workflow.defn(name="NotificationWorkflow")
class NotificationWorkflow:
    """Child workflow that notifies the customer once an order shipped."""

    @workflow.run
    async def run(self, order_id: str) -> str:
        """Run the notification activity.

        Args:
            order_id (str): Order identifier.

        Returns:
            str: Notification message.
        """
        return await workflow.execute_activity(
            notify_customer,
            order_id,
            start_to_close_timeout=timedelta(seconds=10),
        )


@workflow.defn(name="OrderSagaWorkflow")
class OrderSagaWorkflow:
    """Order saga: reserve, charge (with retries), optionally wait for approval, ship, notify via a child workflow.

    When a step fails, the compensations of the completed steps run in reverse order. It also exposes a signal
    (``approve`` / ``cancel``), a query (``get_state``) and an update (``add_note``) so one workflow covers the Temporal features.
    """

    def __init__(self) -> None:
        self._steps: list[str] = []
        self._compensations: list[str] = []
        self._notes: list[str] = []
        self._approved = False
        self._cancelled = False
        self._status = "running"

    @workflow.signal
    async def approve(self) -> None:
        """Approve the order so a saga waiting for approval continues."""
        self._approved = True

    @workflow.signal
    async def cancel(self) -> None:
        """Cancel the order while it waits for approval, which reverts the completed steps."""
        self._cancelled = True

    @workflow.query
    def get_state(self) -> dict[str, Any]:
        """Return the saga progress.

        Returns:
            dict[str, Any]: Status, completed steps, run compensations and notes.
        """
        return {
            "status": self._status,
            "steps": self._steps,
            "compensations": self._compensations,
            "notes": self._notes,
        }

    @workflow.update
    async def add_note(self, note: str) -> int:
        """Attach a note to the order.

        Args:
            note (str): The note text.

        Returns:
            int: The number of notes now attached.
        """
        self._notes.append(note)
        return len(self._notes)

    @add_note.validator
    def validate_note(self, note: str) -> None:
        """Reject blank notes before they reach the history.

        Args:
            note (str): The note text.

        Raises:
            ValueError: If the note is blank.
        """
        if not note.strip():
            raise ValueError("note must not be blank")

    @workflow.run
    async def run(self, order: dict[str, Any]) -> dict[str, Any]:
        """Run the saga.

        Args:
            order (dict[str, Any]): ``order_id``, ``payment_succeeds_on_attempt``, ``fail_shipping`` and
                ``require_approval``.

        Returns:
            dict[str, Any]: The final state, with status ``completed`` or ``compensated``.
        """
        order_id = order["order_id"]
        timeout = timedelta(seconds=10)
        payment_retry = RetryPolicy(
            maximum_attempts=4,
            initial_interval=timedelta(milliseconds=100),
            backoff_coefficient=1.0,
        )
        try:
            await workflow.execute_activity(reserve_inventory, order_id, start_to_close_timeout=timeout)
            self._steps.append("reserve_inventory")
            await workflow.execute_activity(
                charge_payment,
                args=[order_id, order.get("payment_succeeds_on_attempt", 1)],
                start_to_close_timeout=timeout,
                retry_policy=payment_retry,
            )
            self._steps.append("charge_payment")
            if order.get("require_approval"):
                await workflow.wait_condition(lambda: self._approved or self._cancelled, timeout=timedelta(seconds=30))
                if self._cancelled:
                    raise ApplicationError("order cancelled", non_retryable=True)
            await workflow.execute_activity(
                ship_order,
                args=[order_id, order.get("fail_shipping", False)],
                start_to_close_timeout=timeout,
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
            self._steps.append("ship_order")
            await workflow.execute_child_workflow(
                NotificationWorkflow.run,
                order_id,
                id=f"{workflow.info().workflow_id}-notify",
            )
            self._steps.append("notify_customer")
            self._status = "completed"
        except (ActivityError, ApplicationError):
            # Undo the completed steps, last first.
            for step, name, compensation in (
                ("charge_payment", "refund_payment", refund_payment),
                ("reserve_inventory", "release_inventory", release_inventory),
            ):
                if step in self._steps:
                    await workflow.execute_activity(compensation, order_id, start_to_close_timeout=timeout)
                    self._compensations.append(name)
            self._status = "compensated"
        return self.get_state()


@workflow.defn(name="BaseGreetingWorkflow")
class BaseGreetingWorkflow(BaseWorkflow[str, str]):
    """Greeting workflow built on ``BaseWorkflow`` to check its config-driven activity defaults in the sandbox."""

    @workflow.run
    async def run(self, workflow_input: str) -> str:
        """Greet through the base class activity helper.

        Args:
            workflow_input (str): Name to greet.

        Returns:
            str: Greeting message from the activity.
        """
        return await self._execute_activity_with_retry(greeting_activity, workflow_input)
@workflow.defn(name="EchoOrderWorkflow")
class EchoOrderWorkflow:
    """Workflow that returns its Pydantic input, to check the data converter round trip."""

    @workflow.run
    async def run(self, order: OrderPayload) -> OrderPayload:
        """Return the order unchanged.

        Args:
            order (OrderPayload): The order payload.

        Returns:
            OrderPayload: The same order.
        """
        return order


@workflow.defn(name="ValueErrorWorkflow")
class ValueErrorWorkflow:
    """Workflow that raises a plain ``ValueError``, to check ``workflow_failure_exception_types``."""

    @workflow.run
    async def run(self) -> None:
        """Raise a plain error.

        Raises:
            ValueError: Always.
        """
        raise ValueError("invalid order")
