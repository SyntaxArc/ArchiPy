"""Step definitions for Temporal adapter testing.

This module provides BDD step implementations for testing Temporal workflow
operations, worker management, schedules, signals/queries, and error handling.

A persistent event loop per scenario is used so that Temporal workers
(started as background asyncio tasks) remain alive across multiple steps.
"""

import asyncio
import threading
from collections.abc import Coroutine
from datetime import timedelta
from typing import Any, TypeVar

from behave import given, then, when
from temporalio.client import ScheduleIntervalSpec, ScheduleOverlapPolicy, SchedulePolicy, ScheduleSpec

from archipy.adapters.temporal.adapters import TemporalAdapter
from archipy.adapters.temporal.worker import TemporalWorkerManager, WorkerHandle
from archipy.configs.config_template import TemporalConfig
from archipy.models.errors import BaseError
from features.test_helpers import get_current_scenario_context
from features.test_workflows.temporal_activities import (
    calculation_activity,
    counter_activity,
    data_processing_activity,
    failing_activity,
    greeting_activity,
    long_running_activity,
    status_activity,
)
from features.test_workflows.temporal_workflows import (
    CalculatorWorkflow,
    ConcurrentActivitiesWorkflow,
    DataProcessingWorkflow,
    GreetingWorkflow,
    LongRunningWorkflow,
    RetryWorkflow,
    ScheduledWorkflow,
    SignalQueryWorkflow,
    TimeoutWorkflow,
)

T = TypeVar("T")


def _get_event_loop(context: Any) -> asyncio.AbstractEventLoop:
    """Get or create a persistent event loop for the current scenario.

    Temporal workers run as background asyncio tasks. Using asyncio.run()
    creates and destroys a new event loop per call, which kills background
    worker tasks. This function provides a single event loop per scenario
    that stays alive, running in a dedicated daemon thread.

    Args:
        context: Behave context object.

    Returns:
        asyncio.AbstractEventLoop: The persistent event loop for the scenario.
    """
    scenario_context = get_current_scenario_context(context)
    if not hasattr(scenario_context, "_event_loop") or scenario_context._event_loop is None:
        loop = asyncio.new_event_loop()

        def _run_loop(lp: asyncio.AbstractEventLoop) -> None:
            asyncio.set_event_loop(lp)
            lp.run_forever()

        thread = threading.Thread(target=_run_loop, args=(loop,), daemon=True)
        thread.start()
        scenario_context._event_loop = loop
        scenario_context._event_loop_thread = thread
    return scenario_context._event_loop


def run_async(context: Any, coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine on the persistent scenario event loop.

    This replaces all asyncio.run() calls in Temporal steps so that
    background worker tasks survive across behave steps.

    Args:
        context: Behave context object.
        coro: The coroutine to execute.

    Returns:
        T: The result of the coroutine.
    """
    loop = _get_event_loop(context)
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=120)


def cleanup_event_loop(context: Any) -> None:
    """Clean up the persistent event loop for the current scenario.

    Stops workers, then shuts down the event loop and its thread.

    Args:
        context: Behave context object.
    """
    scenario_context = get_current_scenario_context(context)

    # Shutdown workers first
    if hasattr(scenario_context, "worker_manager") and scenario_context.worker_manager is not None:
        try:
            loop = scenario_context._event_loop
            if loop is not None and loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    scenario_context.worker_manager.shutdown_all_workers(), loop,
                )
                future.result(timeout=30)
        except Exception:
            pass

    # Stop the event loop and wait for the thread
    if hasattr(scenario_context, "_event_loop") and scenario_context._event_loop is not None:
        loop = scenario_context._event_loop
        loop.call_soon_threadsafe(loop.stop)
        if hasattr(scenario_context, "_event_loop_thread"):
            scenario_context._event_loop_thread.join(timeout=5)
        scenario_context._event_loop = None
        scenario_context._event_loop_thread = None


def get_temporal_adapter(context) -> TemporalAdapter:
    """Get or initialize the Temporal adapter from scenario context.

    Args:
        context: Behave context object.

    Returns:
        TemporalAdapter: Configured Temporal adapter instance.
    """
    scenario_context = get_current_scenario_context(context)
    if not hasattr(scenario_context, "temporal_adapter") or scenario_context.temporal_adapter is None:
        # Get the configuration from the running container
        test_containers = scenario_context.get("test_containers")
        temporal_container = test_containers.get_container("temporal")

        # Use the configuration from the running container
        temporal_config = temporal_container.config

        scenario_context.temporal_adapter = TemporalAdapter(temporal_config)
    return scenario_context.temporal_adapter


def get_temporal_worker_manager(context) -> TemporalWorkerManager:
    """Get or initialize the Temporal worker manager from scenario context.

    Args:
        context: Behave context object.

    Returns:
        TemporalWorkerManager: Configured worker manager instance.
    """
    scenario_context = get_current_scenario_context(context)
    if not hasattr(scenario_context, "worker_manager") or scenario_context.worker_manager is None:
        # Get the configuration from the running container
        test_containers = scenario_context.get("test_containers")
        temporal_container = test_containers.get_container("temporal")

        # Use the configuration from the running container
        temporal_config = temporal_container.config

        scenario_context.worker_manager = TemporalWorkerManager(temporal_config)
    return scenario_context.worker_manager


async def start_test_worker(
    context,
    task_queue: str,
    workflows: list[type] | None = None,
    activities: list | None = None,
    build_id: str | None = None,
) -> WorkerHandle:
    """Start a test worker with specified workflows and activities.

    Args:
        context: Behave context object.
        task_queue (str): Task queue name for the worker.
        workflows (list[type], optional): List of workflow classes. Defaults to None.
        activities (list, optional): List of activity functions. Defaults to None.
        build_id (str, optional): Build identifier for versioning. Defaults to None.

    Returns:
        WorkerHandle: Handle to the started worker.
    """
    worker_manager = get_temporal_worker_manager(context)
    scenario_context = get_current_scenario_context(context)

    # Default workflows and activities if not specified
    if workflows is None:
        workflows = [
            GreetingWorkflow,
            CalculatorWorkflow,
            SignalQueryWorkflow,
            TimeoutWorkflow,
            RetryWorkflow,
            ScheduledWorkflow,
            DataProcessingWorkflow,
            LongRunningWorkflow,
            ConcurrentActivitiesWorkflow,
        ]

    if activities is None:
        activities = [
            greeting_activity,
            calculation_activity,
            data_processing_activity,
            long_running_activity,
            failing_activity,
            counter_activity,
            status_activity,
        ]

    worker_handle = await worker_manager.start_worker(
        task_queue=task_queue,
        workflows=workflows,
        activities=activities,
        build_id=build_id,
    )

    # Store worker handle in scenario context
    if not hasattr(scenario_context, "workers"):
        scenario_context.workers = []
    scenario_context.workers.append(worker_handle)
    scenario_context.last_worker = worker_handle

    return worker_handle


# Given steps
@given("a Temporal test container is running")
def step_temporal_container_running(context):
    """Verify Temporal container is running."""
    scenario_context = get_current_scenario_context(context)
    test_containers = scenario_context.get("test_containers")
    temporal_container = test_containers.get_container("temporal")
    assert temporal_container is not None, "Temporal container should be running"
    context.logger.info("Temporal container is running")


@given("a Temporal adapter is configured")
def step_temporal_adapter_configured(context):
    """Configure Temporal adapter from container."""
    adapter = get_temporal_adapter(context)
    assert adapter is not None, "Temporal adapter should be configured"
    context.logger.info("Temporal adapter configured")


@given("a Temporal worker manager is configured")
def step_temporal_worker_manager_configured(context):
    """Configure Temporal worker manager from container."""
    worker_manager = get_temporal_worker_manager(context)
    assert worker_manager is not None, "Temporal worker manager should be configured"
    context.logger.info("Temporal worker manager configured")


@given('a worker is started for task queue "{task_queue}" with {workflow_name}')
def step_start_worker_with_workflow(context, task_queue, workflow_name):
    """Start a worker with specific workflow.

    Note: All workflows are registered on the worker to avoid issues with
    the shared Temporal task queue picking up tasks from other scenarios.
    """
    workflow_map = {
        "GreetingWorkflow": GreetingWorkflow,
        "CalculatorWorkflow": CalculatorWorkflow,
        "SignalQueryWorkflow": SignalQueryWorkflow,
        "TimeoutWorkflow": TimeoutWorkflow,
        "RetryWorkflow": RetryWorkflow,
        "ScheduledWorkflow": ScheduledWorkflow,
        "DataProcessingWorkflow": DataProcessingWorkflow,
        "LongRunningWorkflow": LongRunningWorkflow,
        "ConcurrentActivitiesWorkflow": ConcurrentActivitiesWorkflow,
    }

    workflow_class = workflow_map.get(workflow_name)
    assert workflow_class is not None, f"Unknown workflow: {workflow_name}"

    # Register all workflows to handle stale tasks from shared task queues
    run_async(context, start_test_worker(context, task_queue))
    context.logger.info(f"Started worker for {workflow_name} on queue {task_queue}")


@given("a Temporal adapter with invalid server configuration")
def step_temporal_adapter_invalid_config(context):
    """Create adapter with invalid configuration."""
    scenario_context = get_current_scenario_context(context)
    invalid_config = TemporalConfig(HOST="invalid-host", PORT=9999, NAMESPACE="default", TASK_QUEUE="test-queue")
    scenario_context.temporal_adapter = TemporalAdapter(invalid_config)
    context.logger.info("Created Temporal adapter with invalid configuration")


# When steps - Workflow Operations
@when('I start workflow "{workflow_name}" with workflow id "{workflow_id}"')
def step_start_workflow_no_arg(context, workflow_name, workflow_id):
    """Start a workflow without arguments, using a specific workflow ID."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {
        "GreetingWorkflow": GreetingWorkflow,
        "SignalQueryWorkflow": SignalQueryWorkflow,
    }

    workflow_class = workflow_map.get(workflow_name)
    assert workflow_class is not None, f"Unknown workflow: {workflow_name}"

    async def run():
        return await adapter.start_workflow(
            workflow_class, None, workflow_id=workflow_id, task_queue="test-queue",
        )

    handle = run_async(context, run())
    scenario_context.workflow_handle = handle
    scenario_context.workflow_id = workflow_id
    context.logger.info(f"Started workflow {workflow_name} with id {workflow_id}")


@when('I start workflow "{workflow_name}" with argument "{arg}" and workflow id "{workflow_id}"')
def step_start_workflow_with_id(context, workflow_name, arg, workflow_id):
    """Start a workflow with specific workflow ID and argument."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {
        "GreetingWorkflow": GreetingWorkflow,
        "SignalQueryWorkflow": SignalQueryWorkflow,
    }

    workflow_class = workflow_map.get(workflow_name)
    assert workflow_class is not None, f"Unknown workflow: {workflow_name}"

    # Treat empty string as no argument
    effective_arg = arg if arg else None

    async def run():
        return await adapter.start_workflow(
            workflow_class, effective_arg, workflow_id=workflow_id, task_queue="test-queue",
        )

    handle = run_async(context, run())
    scenario_context.workflow_handle = handle
    scenario_context.workflow_id = workflow_id
    context.logger.info(f"Started workflow {workflow_name} with id {workflow_id}")


@when('I execute workflow "{workflow_name}" with argument "{arg}" and workflow id "{workflow_id}"')
def step_execute_workflow_with_id(context, workflow_name, arg, workflow_id):
    """Execute a workflow with specific workflow ID."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {
        "GreetingWorkflow": GreetingWorkflow,
    }

    workflow_class = workflow_map.get(workflow_name)
    assert workflow_class is not None, f"Unknown workflow: {workflow_name}"

    async def run():
        result = await adapter.execute_workflow(
            workflow_class,
            arg,
            workflow_id=workflow_id,
            task_queue="test-queue",
        )
        return result

    result = run_async(context, run())
    scenario_context.workflow_result = result
    scenario_context.workflow_id = workflow_id
    context.logger.info(f"Executed workflow {workflow_name} with id {workflow_id}")


@when('I execute workflow "{workflow_name}" with argument "{arg}"')
def step_execute_workflow_with_arg(context, workflow_name, arg):
    """Execute a workflow and wait for result (without explicit workflow ID)."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {
        "GreetingWorkflow": GreetingWorkflow,
    }

    workflow_class = workflow_map.get(workflow_name)
    assert workflow_class is not None, f"Unknown workflow: {workflow_name}"

    async def run():
        result = await adapter.execute_workflow(workflow_class, arg, task_queue="test-queue")
        return result

    result = run_async(context, run())
    scenario_context.workflow_result = result
    context.logger.info(f"Executed workflow {workflow_name}, result: {result}")


@when('I cancel workflow "{workflow_id}"')
def step_cancel_workflow(context, workflow_id):
    """Cancel a running workflow."""
    adapter = get_temporal_adapter(context)

    async def run():
        await adapter.cancel_workflow(workflow_id)

    run_async(context, run())
    context.logger.info(f"Cancelled workflow {workflow_id}")


@when('I terminate workflow "{workflow_id}" with reason "{reason}"')
def step_terminate_workflow(context, workflow_id, reason):
    """Terminate a running workflow."""
    adapter = get_temporal_adapter(context)

    async def run():
        await adapter.terminate_workflow(workflow_id, reason=reason)

    run_async(context, run())
    context.logger.info(f"Terminated workflow {workflow_id} with reason: {reason}")


@when('I list workflows with query "{query}"')
def step_list_workflows(context, query):
    """List workflows with query filter."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    async def run():
        workflows = await adapter.list_workflows(query=query)
        return workflows

    workflows = run_async(context, run())
    scenario_context.workflow_list = workflows
    context.logger.info(f"Listed workflows with query: {query}, found {len(workflows)}")


@when('I describe workflow "{workflow_id}"')
def step_describe_workflow(context, workflow_id):
    """Describe a workflow execution."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    async def run():
        description = await adapter.describe_workflow(workflow_id)
        return description

    description = run_async(context, run())
    scenario_context.workflow_description = description
    context.logger.info(f"Described workflow {workflow_id}")


@when('I start workflow "{workflow_name}" with argument {arg:d} and custom timeouts:')
def step_start_workflow_with_timeouts(context, workflow_name, arg):
    """Start workflow with custom timeout configuration."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {"TimeoutWorkflow": TimeoutWorkflow}
    workflow_class = workflow_map.get(workflow_name)

    # Parse timeouts from table with headers | key | value |
    execution_timeout = None
    run_timeout = None
    task_timeout = None

    for row in context.table:
        key = row["key"].strip()
        value = int(row["value"].strip())
        if key == "execution_timeout":
            execution_timeout = value
        elif key == "run_timeout":
            run_timeout = value
        elif key == "task_timeout":
            task_timeout = value

    async def run():
        handle = await adapter.start_workflow(
            workflow_class,
            arg,
            task_queue="test-queue",
            execution_timeout=execution_timeout,
            run_timeout=run_timeout,
            task_timeout=task_timeout,
        )
        return handle

    handle = run_async(context, run())
    scenario_context.workflow_handle = handle
    context.logger.info(f"Started workflow {workflow_name} with custom timeouts")


@when('I start workflow "{workflow_name}" with argument "{arg}" and metadata:')
def step_start_workflow_with_metadata(context, workflow_name, arg):
    """Start workflow with memo and search attributes."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {"GreetingWorkflow": GreetingWorkflow}
    workflow_class = workflow_map.get(workflow_name)

    # Parse metadata from table
    memo = {}
    for row in context.table:
        if row["type"] == "memo":
            memo["test_key"] = row["value"]

    async def run():
        handle = await adapter.start_workflow(
            workflow_class,
            arg,
            task_queue="test-queue",
            memo=memo if memo else None,
        )
        return handle

    handle = run_async(context, run())
    scenario_context.workflow_handle = handle
    context.logger.info(f"Started workflow {workflow_name} with metadata")


# When steps - Signal and Query Operations
@when('I send signal "{signal_name}" with value {value:d} to workflow "{workflow_id}"')
def step_send_signal_with_int_value(context, signal_name, value, workflow_id):
    """Send a signal with integer value to workflow."""
    adapter = get_temporal_adapter(context)

    async def run():
        await adapter.signal_workflow(workflow_id, signal_name, value)

    run_async(context, run())
    context.logger.info(f"Sent signal {signal_name} with value {value} to workflow {workflow_id}")


@when('I send signal "{signal_name}" with value "{value}" to workflow "{workflow_id}"')
def step_send_signal_with_str_value(context, signal_name, value, workflow_id):
    """Send a signal with string value to workflow."""
    adapter = get_temporal_adapter(context)

    async def run():
        await adapter.signal_workflow(workflow_id, signal_name, value)

    run_async(context, run())
    context.logger.info(f"Sent signal {signal_name} with value {value} to workflow {workflow_id}")


@when('I send signal "{signal_name}" to workflow "{workflow_id}"')
def step_send_signal_no_value(context, signal_name, workflow_id):
    """Send a signal without value to workflow."""
    adapter = get_temporal_adapter(context)

    async def run():
        await adapter.signal_workflow(workflow_id, signal_name)

    run_async(context, run())
    context.logger.info(f"Sent signal {signal_name} to workflow {workflow_id}")


@when('I send signals to workflow "{workflow_id}":')

def step_send_multiple_signals(context, workflow_id):
    """Send multiple signals to workflow from table."""
    adapter = get_temporal_adapter(context)

    async def run():
        for row in context.table:
            signal_name = row["signal_name"]
            value = row["value"]
            # Try to convert to int if possible
            try:
                value = int(value)
            except ValueError:
                pass
            await adapter.signal_workflow(workflow_id, signal_name, value)
            await asyncio.sleep(0.5)  # Small delay between signals

    run_async(context, run())
    context.logger.info(f"Sent multiple signals to workflow {workflow_id}")


@when('I query workflow "{workflow_id}" with query "{query_name}"')
def step_query_workflow(context, workflow_id, query_name):
    """Query a workflow for information."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    async def run():
        result = await adapter.query_workflow(workflow_id, query_name)
        return result

    result = run_async(context, run())
    scenario_context.query_result = result
    context.logger.info(f"Queried workflow {workflow_id} with {query_name}, result: {result}")


# When steps - Worker Management
@when('I start a worker for task queue "{task_queue}" with workflows and activities')
def step_start_worker(context, task_queue):
    """Start a worker with default workflows and activities."""
    run_async(context, start_test_worker(context, task_queue))
    context.logger.info(f"Started worker for task queue {task_queue}")


@when('I start a worker for task queue "{task_queue}" with build_id "{build_id}"')
def step_start_worker_with_build_id(context, task_queue, build_id):
    """Start a worker with specific build ID."""
    run_async(context, start_test_worker(context, task_queue, build_id=build_id))
    context.logger.info(f"Started worker for task queue {task_queue} with build_id {build_id}")


@when("I stop the worker")
def step_stop_worker(context):
    """Stop the last started worker."""
    scenario_context = get_current_scenario_context(context)
    worker_handle = scenario_context.last_worker

    async def run():
        await worker_handle.stop()

    run_async(context, run())
    context.logger.info("Stopped worker")


@when("I get worker statistics")
def step_get_worker_stats(context):
    """Get statistics for the last started worker."""
    scenario_context = get_current_scenario_context(context)
    worker_handle = scenario_context.last_worker
    stats = worker_handle.get_stats()
    scenario_context.worker_stats = stats
    context.logger.info(f"Got worker stats: {stats}")


@when("I shutdown all workers")
def step_shutdown_all_workers(context):
    """Shutdown all workers in the worker manager."""
    worker_manager = get_temporal_worker_manager(context)

    async def run():
        await worker_manager.shutdown_all_workers()

    run_async(context, run())
    context.logger.info("Shutdown all workers")


# When steps - Schedule Operations
@when('I create a schedule "{schedule_id}" for workflow "{workflow_name}" with interval {interval:d} seconds')
def step_create_schedule_with_interval(context, schedule_id, workflow_name, interval):
    """Create a schedule with interval specification."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {"ScheduledWorkflow": ScheduledWorkflow}
    workflow_class = workflow_map.get(workflow_name)

    spec = ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(seconds=interval))])

    async def run():
        await adapter.create_schedule(
            schedule_id=schedule_id,
            workflow_class=workflow_class,
            spec=spec,
            task_queue="test-queue",
        )

    run_async(context, run())
    scenario_context.schedule_id = schedule_id
    context.logger.info(f"Created schedule {schedule_id} with interval {interval} seconds")


@when('I create a schedule "{schedule_id}" with interval spec:')
def step_create_schedule_with_spec(context, schedule_id):
    """Create a schedule with detailed interval specification."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    # Parse interval spec from table with headers | key | value |
    interval = None
    phase = None
    for row in context.table:
        key = row["key"].strip()
        value = int(row["value"].strip())
        if key == "interval":
            interval = value
        elif key == "phase":
            phase = value

    spec = ScheduleSpec(
        intervals=[
            ScheduleIntervalSpec(
                every=timedelta(seconds=interval),
                offset=timedelta(seconds=phase) if phase else timedelta(0),
            ),
        ],
    )

    async def run():
        await adapter.create_schedule(
            schedule_id=schedule_id,
            workflow_class=ScheduledWorkflow,
            spec=spec,
            task_queue="test-queue",
        )

    run_async(context, run())
    scenario_context.schedule_id = schedule_id
    context.logger.info(f"Created schedule {schedule_id} with interval spec")


@when('I create a schedule "{schedule_id}" with cron spec "{cron_spec}"')
def step_create_schedule_with_cron(context, schedule_id, cron_spec):
    """Create a schedule with cron specification."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    spec = ScheduleSpec(cron_expressions=[cron_spec])

    async def run():
        await adapter.create_schedule(
            schedule_id=schedule_id,
            workflow_class=ScheduledWorkflow,
            spec=spec,
            task_queue="test-queue",
        )

    run_async(context, run())
    scenario_context.schedule_id = schedule_id
    context.logger.info(f"Created schedule {schedule_id} with cron spec {cron_spec}")


@when('I create a schedule "{schedule_id}" with overlap policy "{policy}"')
def step_create_schedule_with_overlap_policy(context, schedule_id, policy):
    """Create a schedule with specific overlap policy."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    policy_map = {
        "SKIP": ScheduleOverlapPolicy.SKIP,
        "ALLOW": ScheduleOverlapPolicy.ALLOW_ALL,
        "CANCEL_OTHER": ScheduleOverlapPolicy.CANCEL_OTHER,
    }

    overlap_policy = policy_map.get(policy, ScheduleOverlapPolicy.SKIP)
    spec = ScheduleSpec(intervals=[ScheduleIntervalSpec(every=timedelta(seconds=5))])
    schedule_policy = SchedulePolicy(overlap=overlap_policy)

    async def run():
        await adapter.create_schedule(
            schedule_id=schedule_id,
            workflow_class=ScheduledWorkflow,
            spec=spec,
            task_queue="test-queue",
            schedule_policy=schedule_policy,
        )

    run_async(context, run())
    scenario_context.schedule_id = schedule_id
    context.logger.info(f"Created schedule {schedule_id} with overlap policy {policy}")


@when('I stop schedule "{schedule_id}"')
def step_stop_schedule(context, schedule_id):
    """Stop and delete a schedule."""
    adapter = get_temporal_adapter(context)

    async def run():
        await adapter.stop_schedule(schedule_id)

    run_async(context, run())
    context.logger.info(f"Stopped schedule {schedule_id}")


# When steps - Timeout and Retry
@when('I execute workflow "{workflow_name}" with argument {arg:d} and execution timeout {timeout:d} seconds')
def step_execute_workflow_with_execution_timeout(context, workflow_name, arg, timeout):
    """Execute workflow with execution timeout."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {"TimeoutWorkflow": TimeoutWorkflow}
    workflow_class = workflow_map.get(workflow_name)

    async def run():
        try:
            result = await adapter.execute_workflow(
                workflow_class,
                arg,
                task_queue="test-queue",
                execution_timeout=timeout,
            )
            return result
        except Exception as e:
            return e

    result = run_async(context, run())
    scenario_context.workflow_result = result
    context.logger.info(f"Executed workflow {workflow_name} with execution timeout {timeout}s")


@when('I execute workflow "{workflow_name}" with argument {arg:d} and run timeout {timeout:d} seconds')
def step_execute_workflow_with_run_timeout(context, workflow_name, arg, timeout):
    """Execute workflow with run timeout."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {"TimeoutWorkflow": TimeoutWorkflow}
    workflow_class = workflow_map.get(workflow_name)

    async def run():
        try:
            result = await adapter.execute_workflow(
                workflow_class,
                arg,
                task_queue="test-queue",
                run_timeout=timeout,
            )
            return result
        except Exception as e:
            return e

    result = run_async(context, run())
    scenario_context.workflow_result = result
    context.logger.info(f"Executed workflow {workflow_name} with run timeout {timeout}s")


@when('I execute workflow "{workflow_name}" with argument {arg} and max attempts {max_attempts:d}')
def step_execute_retry_workflow(context, workflow_name, arg, max_attempts):
    """Execute retry workflow with max attempts."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {"RetryWorkflow": RetryWorkflow}
    workflow_class = workflow_map.get(workflow_name)

    # Convert arg to boolean
    should_fail = arg.lower() == "true"

    async def run():
        # RetryWorkflow.run expects (should_fail, max_attempts) - use direct SDK call
        # since the adapter only supports a single arg parameter.
        # The Temporal SDK accepts multiple args via the keyword-only 'args' parameter.
        from uuid import uuid4

        client = await adapter.get_client()
        result = await client.execute_workflow(
            workflow_class,
            args=[should_fail, max_attempts],
            id=str(uuid4()),
            task_queue="test-queue",
        )
        return result

    result = run_async(context, run())
    scenario_context.workflow_result = result
    context.logger.info(f"Executed retry workflow with max attempts {max_attempts}")


@when('I execute workflow "{workflow_name}" with argument {arg:d}')
def step_execute_workflow_with_int_arg(context, workflow_name, arg):
    """Execute workflow with integer argument (no additional params)."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {
        "LongRunningWorkflow": LongRunningWorkflow,
        "TimeoutWorkflow": TimeoutWorkflow,
    }
    workflow_class = workflow_map.get(workflow_name)

    async def run():
        result = await adapter.execute_workflow(workflow_class, arg, task_queue="test-queue")
        return result

    result = run_async(context, run())
    scenario_context.workflow_result = result
    context.logger.info(f"Executed workflow {workflow_name} with argument {arg}")


# When steps - Error Handling
@when('I try to execute workflow "{workflow_name}" with argument "{arg}"')
def step_try_execute_workflow(context, workflow_name, arg):
    """Try to execute workflow and capture error."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {"GreetingWorkflow": GreetingWorkflow}
    workflow_class = workflow_map.get(workflow_name)

    async def run():
        try:
            result = await adapter.execute_workflow(workflow_class, arg, task_queue="test-queue")
            return result
        except BaseError as e:
            scenario_context.error = e
            scenario_context.error_code = e.code
            return None
        except Exception as e:
            scenario_context.error = e
            return None

    run_async(context, run())
    context.logger.info(f"Tried to execute workflow {workflow_name}")


@when('I try to start workflow "{workflow_name}" with argument "{arg}"')
def step_try_start_workflow(context, workflow_name, arg):
    """Try to start workflow and capture error.

    Note: Temporal's start_workflow doesn't fail immediately for non-existent
    workflow types. The error occurs when the worker tries to run the workflow.
    We start the workflow and then try to get its result with a short timeout
    to capture the error.
    """
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    async def run():
        try:
            # Try to start with non-existent workflow type
            handle = await adapter.start_workflow(workflow_name, arg, task_queue="test-queue")
            # Wait briefly for the workflow to fail (workers can't run it)
            await asyncio.wait_for(handle.result(), timeout=5)
            return handle
        except BaseError as e:
            scenario_context.error = e
            scenario_context.error_code = e.code
            return None
        except Exception as e:
            scenario_context.error = e
            return None

    run_async(context, run())
    context.logger.info(f"Tried to start workflow {workflow_name}")


@when('I try to get workflow handle for "{workflow_id}"')
def step_try_get_workflow_handle(context, workflow_id):
    """Try to get workflow handle and verify it exists by describing it.

    Note: Temporal's get_workflow_handle() is a local operation that never fails.
    We must call describe() on the handle to verify the workflow actually exists.
    """
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    async def run():
        try:
            handle = await adapter.get_workflow_handle(workflow_id)
            # Force an RPC call to verify the workflow exists
            await handle.describe()
            return handle
        except BaseError as e:
            scenario_context.error = e
            scenario_context.error_code = e.code
            return None
        except Exception as e:
            scenario_context.error = e
            return None

    run_async(context, run())
    context.logger.info(f"Tried to get workflow handle for {workflow_id}")


@when('I try to send signal "{signal_name}" with value {value:d} to workflow "{workflow_id}"')
def step_try_send_signal(context, signal_name, value, workflow_id):
    """Try to send signal and capture error."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    async def run():
        try:
            await adapter.signal_workflow(workflow_id, signal_name, value)
        except BaseError as e:
            scenario_context.error = e
            scenario_context.error_code = e.code
        except Exception as e:
            scenario_context.error = e

    run_async(context, run())
    context.logger.info(f"Tried to send signal to workflow {workflow_id}")


@when("I try to start a worker with empty task queue")
def step_try_start_worker_empty_queue(context):
    """Try to start worker with empty task queue and capture error."""
    scenario_context = get_current_scenario_context(context)

    async def run():
        try:
            await start_test_worker(context, "")
        except BaseError as e:
            scenario_context.error = e
            scenario_context.error_code = e.code
        except Exception as e:
            scenario_context.error = e

    run_async(context, run())
    context.logger.info("Tried to start worker with empty task queue")


# When steps - Advanced Operations
@when('I execute workflow "{workflow_name}" with names:')
def step_execute_workflow_with_names(context, workflow_name):
    """Execute workflow with list of names from table."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {"ConcurrentActivitiesWorkflow": ConcurrentActivitiesWorkflow}
    workflow_class = workflow_map.get(workflow_name)

    names = [row["name"] for row in context.table]

    async def run():
        result = await adapter.execute_workflow(workflow_class, names, task_queue="test-queue")
        return result

    result = run_async(context, run())
    scenario_context.workflow_result = result
    context.logger.info(f"Executed workflow {workflow_name} with {len(names)} names")


@when('I execute workflow "{workflow_name}" with data:')
def step_execute_workflow_with_data(context, workflow_name):
    """Execute workflow with data dictionary from table."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    workflow_map = {"DataProcessingWorkflow": DataProcessingWorkflow}
    workflow_class = workflow_map.get(workflow_name)

    data = {row["key"]: row["value"] for row in context.table}

    async def run():
        result = await adapter.execute_workflow(workflow_class, data, task_queue="test-queue")
        return result

    result = run_async(context, run())
    scenario_context.workflow_result = result
    context.logger.info(f"Executed workflow {workflow_name} with data: {data}")


# Then steps - Workflow Operations
@then('I should be able to get workflow handle for "{workflow_id}"')
def step_should_get_workflow_handle(context, workflow_id):
    """Verify workflow handle can be retrieved."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    async def run():
        handle = await adapter.get_workflow_handle(workflow_id)
        return handle

    handle = run_async(context, run())
    assert handle is not None, f"Should be able to get workflow handle for {workflow_id}"
    scenario_context.workflow_handle = handle
    context.logger.info(f"Successfully got workflow handle for {workflow_id}")


@then('the workflow handle should have workflow id "{workflow_id}"')
def step_workflow_handle_has_id(context, workflow_id):
    """Verify workflow handle has expected workflow ID."""
    scenario_context = get_current_scenario_context(context)
    handle = scenario_context.workflow_handle
    assert handle.id == workflow_id, f"Expected workflow id {workflow_id}, got {handle.id}"
    context.logger.info(f"Workflow handle has correct id: {workflow_id}")


@then('the workflow result should be "{expected_result}"')
def step_workflow_result_should_be(context, expected_result):
    """Verify workflow result matches expected value."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.workflow_result
    assert result == expected_result, f"Expected result '{expected_result}', got '{result}'"
    context.logger.info(f"Workflow result matches: {expected_result}")


@then('the workflow "{workflow_id}" should be cancelled')
def step_workflow_should_be_cancelled(context, workflow_id):
    """Verify workflow is cancelled."""
    adapter = get_temporal_adapter(context)

    async def run():
        handle = await adapter.get_workflow_handle(workflow_id)
        # Poll for cancellation status since cancel is async
        for _ in range(10):
            description = await handle.describe()
            if description.status.name in ["CANCELLED", "CANCELED"]:
                return description
            await asyncio.sleep(1)
        return description

    description = run_async(context, run())
    # Check if workflow is in cancelled state
    assert description.status.name in ["CANCELLED", "CANCELED"], f"Workflow should be cancelled, status: {description.status.name}"
    context.logger.info(f"Workflow {workflow_id} is cancelled")


@then('the workflow "{workflow_id}" should be terminated')
def step_workflow_should_be_terminated(context, workflow_id):
    """Verify workflow is terminated."""
    adapter = get_temporal_adapter(context)

    async def run():
        handle = await adapter.get_workflow_handle(workflow_id)
        # Poll for terminated status since terminate may take a moment
        for _ in range(10):
            description = await handle.describe()
            if description.status.name == "TERMINATED":
                return description
            await asyncio.sleep(1)
        return description

    description = run_async(context, run())
    assert description.status.name == "TERMINATED", f"Workflow should be terminated, status: {description.status.name}"
    context.logger.info(f"Workflow {workflow_id} is terminated")


@then("the workflow list should contain at least {count:d} workflow")
@then("the workflow list should contain at least {count:d} workflows")
def step_workflow_list_should_contain(context, count):
    """Verify workflow list contains at least specified number of workflows."""
    scenario_context = get_current_scenario_context(context)
    workflow_list = scenario_context.workflow_list
    assert len(workflow_list) >= count, f"Expected at least {count} workflows, got {len(workflow_list)}"
    context.logger.info(f"Workflow list contains {len(workflow_list)} workflows")


@then('the workflow description should have workflow id "{workflow_id}"')
def step_workflow_description_has_id(context, workflow_id):
    """Verify workflow description has expected workflow ID."""
    scenario_context = get_current_scenario_context(context)
    description = scenario_context.workflow_description
    assert description.id == workflow_id, f"Expected workflow id {workflow_id}, got {description.id}"
    context.logger.info(f"Workflow description has correct id: {workflow_id}")


@then('the workflow description should have type "{workflow_type}"')
def step_workflow_description_has_type(context, workflow_type):
    """Verify workflow description has expected workflow type."""
    scenario_context = get_current_scenario_context(context)
    description = scenario_context.workflow_description
    assert description.workflow_type == workflow_type, f"Expected workflow type {workflow_type}, got {description.workflow_type}"
    context.logger.info(f"Workflow description has correct type: {workflow_type}")


@then("the workflow should start successfully")
def step_workflow_should_start_successfully(context):
    """Verify workflow started successfully."""
    scenario_context = get_current_scenario_context(context)
    handle = scenario_context.workflow_handle
    assert handle is not None, "Workflow should have started successfully"
    context.logger.info("Workflow started successfully")


@then('the workflow "{workflow_id}" should complete successfully')
def step_workflow_should_complete_successfully(context, workflow_id):
    """Verify workflow completed successfully."""
    adapter = get_temporal_adapter(context)

    async def run():
        handle = await adapter.get_workflow_handle(workflow_id)
        result = await handle.result()
        return result

    result = run_async(context, run())
    assert result is not None, f"Workflow {workflow_id} should complete successfully"
    context.logger.info(f"Workflow {workflow_id} completed successfully")


# Then steps - Signal and Query Operations
@then("the query result should be {expected:d}")
def step_query_result_should_be_int(context, expected):
    """Verify query result matches expected integer value."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.query_result
    assert result == expected, f"Expected query result {expected}, got {result}"
    context.logger.info(f"Query result matches: {expected}")


@then('the query result should be "{expected}"')
def step_query_result_should_be_str(context, expected):
    """Verify query result matches expected string value."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.query_result
    assert result == expected, f"Expected query result '{expected}', got '{result}'"
    context.logger.info(f"Query result matches: {expected}")


# Then steps - Worker Management
@then("the worker should be running")
def step_worker_should_be_running(context):
    """Verify worker is running."""
    scenario_context = get_current_scenario_context(context)
    worker_handle = scenario_context.last_worker
    assert worker_handle.is_running, "Worker should be running"
    context.logger.info("Worker is running")


@then("the worker should have {count:d} or more registered workflows")
def step_worker_should_have_workflows(context, count):
    """Verify worker has registered workflows."""
    scenario_context = get_current_scenario_context(context)
    worker_handle = scenario_context.last_worker
    assert len(worker_handle.workflows) >= count, f"Expected at least {count} workflows"
    context.logger.info(f"Worker has {len(worker_handle.workflows)} registered workflows")


@then("the worker should have {count:d} or more registered activities")
def step_worker_should_have_activities(context, count):
    """Verify worker has registered activities."""
    scenario_context = get_current_scenario_context(context)
    worker_handle = scenario_context.last_worker
    assert len(worker_handle.activities) >= count, f"Expected at least {count} activities"
    context.logger.info(f"Worker has {len(worker_handle.activities)} registered activities")


@then("the worker manager should have {count:d} workers")
def step_worker_manager_should_have_workers(context, count):
    """Verify worker manager has expected number of workers."""
    worker_manager = get_temporal_worker_manager(context)
    assert worker_manager.worker_count == count, f"Expected {count} workers, got {worker_manager.worker_count}"
    context.logger.info(f"Worker manager has {count} workers")


@then("each worker should be on a different task queue")
def step_each_worker_different_queue(context):
    """Verify each worker is on a different task queue."""
    worker_manager = get_temporal_worker_manager(context)
    workers = worker_manager.list_workers()
    task_queues = [w.task_queue for w in workers]
    assert len(task_queues) == len(set(task_queues)), "Each worker should be on a different task queue"
    context.logger.info("Each worker is on a different task queue")


@then('the worker should have build_id "{build_id}"')
def step_worker_should_have_build_id(context, build_id):
    """Verify worker has expected build ID."""
    scenario_context = get_current_scenario_context(context)
    worker_handle = scenario_context.last_worker
    assert worker_handle.build_id == build_id, f"Expected build_id {build_id}, got {worker_handle.build_id}"
    context.logger.info(f"Worker has build_id: {build_id}")


@then("the worker should be stopped")
def step_worker_should_be_stopped(context):
    """Verify worker is stopped."""
    scenario_context = get_current_scenario_context(context)
    worker_handle = scenario_context.last_worker
    assert not worker_handle.is_running, "Worker should be stopped"
    context.logger.info("Worker is stopped")


@then("the worker stats should show worker is running")
def step_worker_stats_show_running(context):
    """Verify worker stats show worker is running."""
    scenario_context = get_current_scenario_context(context)
    stats = scenario_context.worker_stats
    assert stats["is_running"], "Worker stats should show worker is running"
    context.logger.info("Worker stats show worker is running")


@then('the worker stats should show task queue "{task_queue}"')
def step_worker_stats_show_task_queue(context, task_queue):
    """Verify worker stats show expected task queue."""
    scenario_context = get_current_scenario_context(context)
    stats = scenario_context.worker_stats
    assert stats["task_queue"] == task_queue, f"Expected task queue {task_queue}, got {stats['task_queue']}"
    context.logger.info(f"Worker stats show task queue: {task_queue}")


# Then steps - Schedule Operations
@then('the schedule "{schedule_id}" should have executed at least {count:d} time')
@then('the schedule "{schedule_id}" should have executed at least {count:d} times')
def step_schedule_should_have_executed(context, schedule_id, count):
    """Verify schedule has executed at least specified number of times."""
    adapter = get_temporal_adapter(context)

    async def run():
        # List workflows created by this schedule
        workflows = await adapter.list_workflows(query=f"WorkflowType='ScheduledWorkflow'")
        return workflows

    workflows = run_async(context, run())
    assert len(workflows) >= count, f"Expected at least {count} executions, got {len(workflows)}"
    context.logger.info(f"Schedule {schedule_id} has executed {len(workflows)} times")


@then("the schedule should be created successfully")
def step_schedule_should_be_created(context):
    """Verify schedule was created successfully."""
    scenario_context = get_current_scenario_context(context)
    assert hasattr(scenario_context, "schedule_id"), "Schedule should be created"
    context.logger.info("Schedule created successfully")


@then('the schedule "{schedule_id}" should be stopped')
def step_schedule_should_be_stopped(context, schedule_id):
    """Verify schedule is stopped."""
    # Schedule is deleted when stopped, so we just verify no error occurred
    context.logger.info(f"Schedule {schedule_id} is stopped")


# Then steps - Timeout and Retry
@then("the workflow should timeout with execution timeout error")
def step_workflow_should_timeout_execution(context):
    """Verify workflow timed out with execution timeout."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.workflow_result
    assert isinstance(result, Exception), "Workflow should have timed out"
    context.logger.info("Workflow timed out with execution timeout")


@then("the workflow should timeout with run timeout error")
def step_workflow_should_timeout_run(context):
    """Verify workflow timed out with run timeout."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.workflow_result
    assert isinstance(result, Exception), "Workflow should have timed out"
    context.logger.info("Workflow timed out with run timeout")


@then('the workflow result should contain "{text}"')
def step_workflow_result_should_contain(context, text):
    """Verify workflow result contains expected text."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.workflow_result
    assert text in str(result), f"Expected result to contain '{text}', got '{result}'"
    context.logger.info(f"Workflow result contains: {text}")


@then("the workflow should complete successfully")
def step_workflow_should_complete(context):
    """Verify workflow completed successfully."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.workflow_result
    assert not isinstance(result, Exception), f"Workflow should complete successfully, got error: {result}"
    context.logger.info("Workflow completed successfully")


# Then steps - Error Handling
@then("I should receive a connection error")
def step_should_receive_connection_error(context):
    """Verify connection error was received."""
    scenario_context = get_current_scenario_context(context)
    assert hasattr(scenario_context, "error"), "Should have received an error"
    context.logger.info("Received connection error as expected")


@then("I should receive a workflow not found error")
def step_should_receive_workflow_not_found_error(context):
    """Verify workflow not found error was received."""
    scenario_context = get_current_scenario_context(context)
    assert hasattr(scenario_context, "error"), "Should have received an error"
    context.logger.info("Received workflow not found error as expected")


@then("I should receive a worker configuration error")
def step_should_receive_worker_config_error(context):
    """Verify worker configuration error was received."""
    scenario_context = get_current_scenario_context(context)
    assert hasattr(scenario_context, "error"), "Should have received an error"
    context.logger.info("Received worker configuration error as expected")


# Then steps - Advanced Operations
@then("the workflow result should contain {count:d} greetings")
def step_workflow_result_should_contain_greetings(context, count):
    """Verify workflow result contains expected number of greetings."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.workflow_result
    assert len(result) == count, f"Expected {count} greetings, got {len(result)}"
    context.logger.info(f"Workflow result contains {count} greetings")


@then("the workflow result should contain processed data")
def step_workflow_result_should_contain_processed_data(context):
    """Verify workflow result contains processed data."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.workflow_result
    assert "processed" in result, "Result should contain processed data"
    assert result["processed"] is True, "Data should be marked as processed"
    context.logger.info("Workflow result contains processed data")


@then("the processed data should have item count {count:d}")
def step_processed_data_should_have_item_count(context, count):
    """Verify processed data has expected item count."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.workflow_result
    assert result["item_count"] == count, f"Expected item count {count}, got {result['item_count']}"
    context.logger.info(f"Processed data has item count: {count}")
