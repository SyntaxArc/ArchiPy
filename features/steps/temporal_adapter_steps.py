"""Step definitions for Temporal adapter testing.

This module provides BDD step implementations for testing Temporal workflow
operations, worker management, schedules, signals/queries, and error handling.

A persistent event loop per scenario is used so that Temporal workers
(started as background asyncio tasks) remain alive across multiple steps.
"""

import asyncio
import socket
import threading
import time
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, TypeVar

import httpx2
from behave import given, then, when
from temporalio.client import Interceptor as ClientInterceptor
from temporalio.client import OutboundInterceptor, StartWorkflowInput, WithStartWorkflowOperation
from temporalio.worker import ActivityInboundInterceptor, ExecuteActivityInput, WorkflowInterceptorClassInput
from temporalio.worker import Interceptor as WorkerInterceptor
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.client import ScheduleIntervalSpec, ScheduleOverlapPolicy, SchedulePolicy, ScheduleSpec
from temporalio.worker import WorkerDeploymentConfig, WorkerDeploymentVersion
from temporalio.runtime import LoggingConfig, TelemetryConfig, TelemetryFilter

from archipy.adapters.temporal import runtime as temporal_runtime_module
from archipy.adapters.temporal.adapters import TemporalAdapter
from archipy.adapters.temporal.base import AtomicActivity, BaseActivity
from archipy.adapters.temporal.runtime import TemporalRuntimeManager
from archipy.adapters.temporal.tracing import MessagingOpenTelemetryInterceptor
from archipy.adapters.temporal.worker import TemporalWorkerManager, WorkerHandle
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import OtelMetricsExporter, TemporalConfig
from archipy.models.errors import BaseError, ConfigurationError, InvalidArgumentError
from features.steps.elastic_apm_steps import apm_endpoint, wait_for_apm_metric
from features.test_helpers import get_current_scenario_context
from features.test_helpers_otel import CollectorTelemetry
from features.test_workflows.temporal_activities import (
    calculation_activity,
    charge_payment,
    counter_activity,
    data_processing_activity,
    failing_activity,
    greeting_activity,
    long_running_activity,
    OrderPayload,
    notify_customer,
    refund_payment,
    release_inventory,
    reserve_inventory,
    ship_order,
    status_activity,
)
from features.test_workflows.temporal_workflows import (
    ChangedGreetingWorkflow,
    BaseGreetingWorkflow,
    CalculatorWorkflow,
    ConcurrentActivitiesWorkflow,
    DailyReminderWorkflow,
    DataProcessingWorkflow,
    EchoOrderWorkflow,
    GreetingWorkflow,
    LongRunningWorkflow,
    NotificationWorkflow,
    OrderSagaWorkflow,
    RetryWorkflow,
    ScheduledWorkflow,
    SignalQueryWorkflow,
    TimeoutWorkflow,
    ValueErrorWorkflow,
)

T = TypeVar("T")


def _quiet_telemetry_config(**kwargs: Any) -> TelemetryConfig:
    """Build the ``TelemetryConfig`` the runtime manager uses, with the Rust core logging errors only.

    A ``Runtime`` cannot be closed, so one created for a test collector keeps exporting after that container is
    stopped and the core warns about every failed export for the rest of the run.
    """
    quiet = LoggingConfig(filter=TelemetryFilter(core_level="ERROR", other_level="ERROR"))
    return TelemetryConfig(logging=quiet, **kwargs)


temporal_runtime_module.TelemetryConfig = _quiet_telemetry_config


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
                    scenario_context.worker_manager.shutdown_all_workers(),
                    loop,
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
    max_concurrent_activities: int | None = None,
    deployment_config: WorkerDeploymentConfig | None = None,
) -> WorkerHandle:
    """Start a test worker with specified workflows and activities.

    Args:
        context: Behave context object.
        task_queue (str): Task queue name for the worker.
        workflows (list[type], optional): List of workflow classes. Defaults to None.
        activities (list, optional): List of activity functions. Defaults to None.
        build_id (str, optional): Build identifier for versioning. Defaults to None.
        max_concurrent_activities (int, optional): Activity slot limit for the worker. Defaults to None.

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
            OrderSagaWorkflow,
            NotificationWorkflow,
            BaseGreetingWorkflow,
            EchoOrderWorkflow,
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
            reserve_inventory,
            release_inventory,
            charge_payment,
            refund_payment,
            ship_order,
            notify_customer,
        ]

    worker_handle = await worker_manager.start_worker(
        task_queue=task_queue,
        workflows=workflows,
        activities=activities,
        build_id=build_id,
        deployment_config=deployment_config,
        max_concurrent_activities=max_concurrent_activities,
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


@given('Temporal adapter is configured with client identity "{identity}"')
def step_temporal_adapter_with_client_identity(context, identity: str) -> None:
    """Configure Temporal adapter with a custom client identity."""
    scenario_context = get_current_scenario_context(context)
    test_containers = scenario_context.get("test_containers")
    temporal_container = test_containers.get_container("temporal")
    temporal_config = temporal_container.config.model_copy(update={"CLIENT_IDENTITY": identity})
    scenario_context.temporal_adapter = TemporalAdapter(temporal_config)
    scenario_context.worker_manager = None
    context.logger.info("Temporal adapter configured with client identity %s", identity)


@given("a Temporal worker manager is configured with worker debug mode enabled")
def step_temporal_worker_manager_with_debug_mode(context) -> None:
    """Configure Temporal worker manager with debug mode enabled."""
    scenario_context = get_current_scenario_context(context)
    test_containers = scenario_context.get("test_containers")
    temporal_container = test_containers.get_container("temporal")
    base_config = (
        scenario_context.temporal_adapter.config
        if hasattr(scenario_context, "temporal_adapter") and scenario_context.temporal_adapter is not None
        else temporal_container.config
    )
    temporal_config = base_config.model_copy(update={"WORKER_DEBUG_MODE": True})
    scenario_context.worker_manager = TemporalWorkerManager(temporal_config)
    context.logger.info("Temporal worker manager configured with debug mode enabled")


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
        "OrderSagaWorkflow": OrderSagaWorkflow,
        "BaseGreetingWorkflow": BaseGreetingWorkflow,
        "EchoOrderWorkflow": EchoOrderWorkflow,
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
            workflow_class,
            None,
            workflow_id=workflow_id,
            task_queue="test-queue",
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
            workflow_class,
            effective_arg,
            workflow_id=workflow_id,
            task_queue="test-queue",
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

    # Use task queue from last worker if available, otherwise default to "test-queue"
    task_queue = "test-queue"
    if hasattr(scenario_context, "last_worker") and scenario_context.last_worker:
        task_queue = scenario_context.last_worker.task_queue

    async def run():
        result = await adapter.execute_workflow(workflow_class, arg, task_queue=task_queue)
        return result

    result = run_async(context, run())
    scenario_context.workflow_result = result
    context.logger.info(f"Executed workflow {workflow_name} on queue {task_queue}, result: {result}")


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
        await adapter.delete_schedule(schedule_id)

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
    assert description.status.name in ["CANCELLED", "CANCELED"], (
        f"Workflow should be cancelled, status: {description.status.name}"
    )
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
    assert description.workflow_type == workflow_type, (
        f"Expected workflow type {workflow_type}, got {description.workflow_type}"
    )
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


def _order_saga_input(**overrides: Any) -> dict[str, Any]:
    """Build the ``OrderSagaWorkflow`` input; defaults are a first-attempt payment, no approval and no failure."""
    return {
        "order_id": "order-1",
        "payment_succeeds_on_attempt": 1,
        "fail_shipping": False,
        "require_approval": False,
        **overrides,
    }


def _last_task_queue(context) -> str:
    """Return the task queue of the scenario's last worker, or the shared default."""
    last_worker = getattr(get_current_scenario_context(context), "last_worker", None)
    return last_worker.task_queue if last_worker else "test-queue"


@when(
    "I execute the order saga with payment succeeding on attempt {attempt:d} "
    "and shipping failure {fail_shipping:w}",
)
def step_execute_order_saga(context, attempt, fail_shipping):
    """Run ``OrderSagaWorkflow`` to its end and keep the returned state."""
    adapter = get_temporal_adapter(context)
    order = _order_saga_input(payment_succeeds_on_attempt=attempt, fail_shipping=fail_shipping == "true")

    async def run():
        from uuid import uuid4

        client = await adapter.get_client()
        return await client.execute_workflow(
            OrderSagaWorkflow.run,
            order,
            id=f"saga-{uuid4()}",
            task_queue=_last_task_queue(context),
        )

    get_current_scenario_context(context).workflow_result = run_async(context, run())


@when(
    'I start the order saga "{workflow_id}" with payment succeeding on attempt {attempt:d} '
    "and shipping failure {fail_shipping:w} requiring approval",
)
def step_start_order_saga_with_approval(context, workflow_id, attempt, fail_shipping):
    """Start ``OrderSagaWorkflow`` that waits for the ``approve`` or ``cancel`` signal after the payment."""
    adapter = get_temporal_adapter(context)
    order = _order_saga_input(
        payment_succeeds_on_attempt=attempt,
        fail_shipping=fail_shipping == "true",
        require_approval=True,
    )

    async def run():
        return await adapter.start_workflow(
            OrderSagaWorkflow,
            order,
            workflow_id=workflow_id,
            task_queue=_last_task_queue(context),
        )

    run_async(context, run())


@when('I add the note "{note}" to the order saga "{workflow_id}"')
def step_add_note_to_order_saga(context, note, workflow_id):
    """Send the ``add_note`` update and keep the note count it returns."""
    adapter = get_temporal_adapter(context)

    async def run():
        handle = await adapter.get_workflow_handle(workflow_id)
        return await handle.execute_update("add_note", note)

    get_current_scenario_context(context).update_result = run_async(context, run())


@when('I add the note "{note}" to a new order saga "{workflow_id}" with update-with-start')
def step_update_with_start_order_saga(context, note, workflow_id):
    """Start ``OrderSagaWorkflow`` and send ``add_note`` in the same request."""
    adapter = get_temporal_adapter(context)
    order = _order_saga_input()

    async def run():
        client = await adapter.get_client()
        start = WithStartWorkflowOperation(
            OrderSagaWorkflow.run,
            order,
            id=workflow_id,
            task_queue=_last_task_queue(context),
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        )
        update_result = await client.execute_update_with_start_workflow(
            OrderSagaWorkflow.add_note,
            note,
            start_workflow_operation=start,
        )
        workflow_result = await (await start.workflow_handle()).result()
        return update_result, workflow_result

    scenario_context = get_current_scenario_context(context)
    scenario_context.update_result, scenario_context.workflow_result = run_async(context, run())


@when('I try to add a blank note to the order saga "{workflow_id}"')
def step_add_blank_note(context, workflow_id):
    """Send a blank ``add_note`` update and keep the error the validator raised."""
    adapter = get_temporal_adapter(context)

    async def run():
        handle = await adapter.get_workflow_handle(workflow_id)
        try:
            await handle.execute_update("add_note", " ")
        except Exception as error:
            return error
        return None

    get_current_scenario_context(context).update_error = run_async(context, run())


@when('I run a standalone greeting activity for "{name}" on the last worker queue')
def step_standalone_activity(context, name):
    """Start the greeting activity straight from the client, without a workflow."""
    adapter = get_temporal_adapter(context)

    async def run():
        from uuid import uuid4

        client = await adapter.get_client()
        return await client.execute_activity(
            greeting_activity,
            name,
            id=f"standalone-{uuid4()}",
            task_queue=_last_task_queue(context),
            start_to_close_timeout=timedelta(seconds=10),
        )

    get_current_scenario_context(context).activity_result = run_async(context, run())


@then("the blank note should be rejected by the update validator")
def step_blank_note_rejected(context):
    """Assert the update failed instead of being recorded."""
    error = get_current_scenario_context(context).update_error
    assert error is not None, "The blank note was accepted"


@then('the standalone activity should return "{expected}"')
def step_standalone_activity_result(context, expected):
    """Assert the standalone activity result."""
    actual = get_current_scenario_context(context).activity_result
    assert actual == expected, f"Activity result {actual!r} != {expected!r}"


@then('the exported {span_prefix} span should carry messaging "{operation}" attributes without a destination')
def step_span_has_messaging_attributes_without_destination(context, span_prefix, operation):
    """Assert a span addressed to a workflow id carries the messaging type but no destination."""
    spans = get_current_scenario_context(context).get("temporal_spans")
    matching = [span for span in spans if span.name.startswith(f"{span_prefix}:")]
    assert matching, f"No {span_prefix} span among {[span.name for span in spans]}"
    for span in matching:
        assert span.attributes.get("messaging.system") == "temporal", f"{span.name}: {dict(span.attributes)}"
        assert span.attributes.get("messaging.operation.type") == operation, f"{span.name}: {dict(span.attributes)}"
        assert "messaging.destination.name" not in span.attributes, f"{span.name}: {dict(span.attributes)}"


@then("the update result should be {expected:d}")
def step_update_result(context, expected):
    """Assert the value the last workflow update returned."""
    actual = get_current_scenario_context(context).update_result
    assert actual == expected, f"Update result {actual!r} != {expected!r}"


def _assert_order_saga_state(state: dict[str, Any], status: str, steps: str, compensations: str) -> None:
    """Assert the saga status, completed steps and the compensations that ran (comma separated, ``none`` for empty)."""
    expected_steps = [] if steps == "none" else steps.split(",")
    expected_compensations = [] if compensations == "none" else compensations.split(",")
    assert state["status"] == status, f"Saga status {state['status']!r} != {status!r}: {state}"
    assert state["steps"] == expected_steps, f"Saga steps {state['steps']} != {expected_steps}"
    assert state["compensations"] == expected_compensations, (
        f"Compensations {state['compensations']} != {expected_compensations}"
    )


@then("the order saga should end {status:w} after steps {steps} with compensations {compensations}")
def step_order_saga_result(context, status, steps, compensations):
    """Assert the state ``OrderSagaWorkflow`` returned to the client that executed it."""
    _assert_order_saga_state(get_current_scenario_context(context).workflow_result, status, steps, compensations)


@then('the order saga "{workflow_id}" should end {status:w} after steps {steps} with compensations {compensations}')
def step_started_order_saga_result(context, workflow_id, status, steps, compensations):
    """Wait for a started ``OrderSagaWorkflow`` and assert the state it returned."""
    adapter = get_temporal_adapter(context)

    async def run():
        handle = await adapter.get_workflow_handle(workflow_id)
        return await handle.result()

    _assert_order_saga_state(run_async(context, run()), status, steps, compensations)


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
        workflows = await adapter.list_workflows(query="WorkflowType='ScheduledWorkflow'")
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


@then('the temporal adapter config should have client identity "{identity}"')
def step_temporal_adapter_config_should_have_client_identity(context, identity: str) -> None:
    """Verify Temporal adapter config has the expected client identity."""
    adapter = get_temporal_adapter(context)
    assert adapter.config.CLIENT_IDENTITY == identity, (
        f"Expected CLIENT_IDENTITY {identity}, got {adapter.config.CLIENT_IDENTITY}"
    )
    context.logger.info("Temporal adapter config has client identity %s", identity)


@then("the temporal worker manager config should have debug mode enabled")
def step_temporal_worker_manager_config_should_have_debug_mode(context) -> None:
    """Verify Temporal worker manager config has debug mode enabled."""
    worker_manager = get_temporal_worker_manager(context)
    assert worker_manager.config.WORKER_DEBUG_MODE is True, "Expected WORKER_DEBUG_MODE to be enabled"
    context.logger.info("Temporal worker manager config has debug mode enabled")


# --- OpenTelemetry export: real Temporal server, real workers, real OpenTelemetry Collector ---

TEMPORAL_CORE_SERVICE_NAME = "temporal-core-sdk"
TEMPORAL_METRIC_TIMEOUT_SECONDS = 10.0
TEMPORAL_METRICS_ABSENT_WAIT_SECONDS = 3.0
_runtime_endpoint: str | None = None


def _enable_temporal_otel(
    context,
    *,
    enable_metrics: bool,
    protocol: str = "grpc",
    before_init: Callable[[], None] | None = None,
    otlp_endpoint: str | None = None,
) -> None:
    """Point OpenTelemetry at the collector container and rebuild the Temporal adapter and worker manager.

    The Temporal ``Runtime`` is a process singleton that cannot change its endpoint, so it is only reset when
    the collector endpoint differs from the one it was created for.
    """
    global _runtime_endpoint

    from features.steps.otel_steps import _setup_collector_otel

    scenario_context = get_current_scenario_context(context)
    collector = scenario_context.get("test_containers").get_container("otel-collector")
    _setup_collector_otel(
        context,
        traces=True,
        metrics=True,
        protocol=protocol,
        before_init=before_init,
        otlp_endpoint=otlp_endpoint,
    )
    collector.mark()

    endpoint = BaseConfig.global_config().OTEL.OTLP_ENDPOINT
    manager = TemporalRuntimeManager()
    if _runtime_endpoint is not None and _runtime_endpoint != endpoint:
        manager.reset_runtime()
    _runtime_endpoint = endpoint

    temporal_config = scenario_context.get("test_containers").get_container("temporal").config
    temporal_config = temporal_config.model_copy(update={"ENABLE_METRICS": enable_metrics})
    scenario_context.temporal_adapter = TemporalAdapter(temporal_config)
    scenario_context.worker_manager = TemporalWorkerManager(temporal_config)
    scenario_context.store("temporal_metrics_reader", CollectorTelemetry(collector, TEMPORAL_CORE_SERVICE_NAME))


@given("Temporal traces are exported to Elastic APM Server {route}")
def step_temporal_otel_apm_server(context, route) -> None:
    """Enable OpenTelemetry traces towards Elastic APM Server, directly or through a forwarding collector."""
    from features.steps.otel_steps import _setup_collector_otel

    scenario_context = get_current_scenario_context(context)
    _setup_collector_otel(context, traces=True, metrics=False, otlp_endpoint=apm_endpoint(scenario_context, route))
    temporal_config = scenario_context.get("test_containers").get_container("temporal").config
    scenario_context.temporal_adapter = TemporalAdapter(temporal_config)
    scenario_context.worker_manager = TemporalWorkerManager(temporal_config)


@given("Temporal metrics and traces are exported to Elastic APM Server {route}")
def step_temporal_metrics_apm_server(context, route) -> None:
    """Enable OpenTelemetry and Temporal SDK metrics towards Elastic APM Server, directly or through the collector."""
    scenario_context = get_current_scenario_context(context)
    _enable_temporal_otel(context, enable_metrics=True, otlp_endpoint=apm_endpoint(scenario_context, route))


@then('Elastic APM Server should store the Temporal metric "{name}" for task queue "{task_queue}"')
def step_apm_server_temporal_metric(context, name, task_queue) -> None:
    """Check Elasticsearch holds a Temporal SDK metric of the task queue; the SDK exports under its own service."""
    apm_server = get_current_scenario_context(context).get("test_containers").get_container("apm-server")
    found = wait_for_apm_metric(
        lambda: name in apm_server.metric_names(TEMPORAL_CORE_SERVICE_NAME, {"task_queue": task_queue}),
    )
    assert found, f"Temporal metric {name!r} not stored for {task_queue!r}"


def _temporal_metric_points(context, name: str, task_queue: str | None = None) -> list:
    """Return the latest exported data points of a Temporal SDK metric, optionally for one task queue."""
    reader: CollectorTelemetry = get_current_scenario_context(context).get("temporal_metrics_reader")
    metric = reader.metrics().get(name)
    if metric is None:
        return []
    points = list(metric.data.data_points)
    if task_queue is not None:
        points = [point for point in points if point.attributes.get("task_queue") == task_queue]
    return points


def _wait_for_temporal_metric(context, name: str, task_queue: str | None = None, **labels: str) -> list:
    """Poll (bounded) until a Temporal metric has a data point with the given labels; return those points."""
    reader: CollectorTelemetry = get_current_scenario_context(context).get("temporal_metrics_reader")

    def read() -> list:
        return [
            point
            for point in _temporal_metric_points(context, name, task_queue)
            if all(point.attributes.get(key) == value for key, value in labels.items())
        ]

    points = reader.wait_for(read, timeout=TEMPORAL_METRIC_TIMEOUT_SECONDS)
    assert points, (
        f"Temporal metric {name!r} (task_queue={task_queue!r}, labels={labels}) never reached the collector. "
        f"Exported Temporal metrics: {sorted(reader.metrics())}"
    )
    return points


@given("Temporal metrics and traces are exported to the collector")
def step_temporal_otel_enabled(context) -> None:
    """Enable OpenTelemetry against the collector with Temporal metrics on."""
    _enable_temporal_otel(context, enable_metrics=True)


@given("Temporal traces are exported to the collector while Temporal metrics are disabled")
def step_temporal_otel_metrics_disabled(context) -> None:
    """Enable OpenTelemetry against the collector but leave ``TemporalConfig.ENABLE_METRICS`` off."""
    _enable_temporal_otel(context, enable_metrics=False)


@given('a worker limited to {limit:d} concurrent activities is started for task queue "{task_queue}"')
def step_start_worker_with_activity_limit(context, task_queue, limit):
    """Start a worker whose activity slots are capped."""
    run_async(context, start_test_worker(context, task_queue, max_concurrent_activities=limit))


@when('I execute the failing retry workflow with {max_attempts:d} attempts on task queue "{task_queue}"')
def step_execute_failing_retry_workflow(context, max_attempts, task_queue):
    """Run ``RetryWorkflow`` with an activity that always fails."""
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)

    async def run():
        from uuid import uuid4

        client = await adapter.get_client()
        return await client.execute_workflow(
            RetryWorkflow,
            args=[True, max_attempts],
            id=str(uuid4()),
            task_queue=task_queue,
        )

    scenario_context.workflow_result = run_async(context, run())


@when('I wait for the Temporal metric "{name}" of task queue "{task_queue}"')
def step_wait_for_temporal_metric(context, name, task_queue):
    """Wait (bounded) until the collector has received the metric."""
    _wait_for_temporal_metric(context, name, task_queue)


@then('the collector should expose Temporal metric "{name}" for the task queue "{task_queue}"')
def step_collector_has_temporal_metric(context, name, task_queue):
    """Assert the collector received the metric for the task queue."""
    _wait_for_temporal_metric(context, name, task_queue)


@then('the collector should expose Temporal metric "{name}" for task queue "{task_queue}" where {label} is "{value}"')
def step_collector_has_temporal_metric_label(context, name, task_queue, label, value):
    """Assert the collector received the metric for the task queue with a label value."""
    _wait_for_temporal_metric(context, name, task_queue, **{label: value})


@then('the collector should expose client Temporal metric "{name}" where {label} is "{value}"')
def step_collector_has_temporal_metric_any_queue(context, name, label, value):
    """Assert the collector received the metric (client-side, not tied to a queue) with a label value."""
    _wait_for_temporal_metric(context, name, None, **{label: value})


@then('the Temporal "{name}" count for task queue "{task_queue}" and {label} "{value}" should be at least {minimum:d}')
def step_temporal_counter_at_least(context, name, task_queue, label, value, minimum):
    """Assert a Temporal counter has reached a minimum value for one label value."""
    points = _wait_for_temporal_metric(context, name, task_queue, **{label: value})
    total = sum(point.value for point in points)
    assert total >= minimum, f"{name} {label}={value!r} is {total}, expected at least {minimum}"


@then(
    'the Temporal gauge "{name}" for task queue "{task_queue}" and worker type "{worker_type}" '
    "should settle at {expected:d}",
)
def step_temporal_gauge_settles(context, name, task_queue, worker_type, expected):
    """Assert a worker gauge reaches the expected value (polled, bounded)."""
    reader: CollectorTelemetry = get_current_scenario_context(context).get("temporal_metrics_reader")

    def read() -> list:
        return [
            point
            for point in _temporal_metric_points(context, name, task_queue)
            if point.attributes.get("worker_type") == worker_type and point.value == expected
        ]

    assert reader.wait_for(read, timeout=TEMPORAL_METRIC_TIMEOUT_SECONDS), (
        f"{name} for {task_queue!r}/{worker_type} never settled at {expected}; "
        f"got {[p.value for p in _temporal_metric_points(context, name, task_queue)]}"
    )


@then('the collector should not expose any Temporal metric for task queue "{task_queue}"')
def step_collector_has_no_temporal_metrics(context, task_queue):
    """Assert no Temporal SDK metric reached the collector for the task queue after a bounded wait."""
    import time

    reader: CollectorTelemetry = get_current_scenario_context(context).get("temporal_metrics_reader")
    time.sleep(TEMPORAL_METRICS_ABSENT_WAIT_SECONDS)
    leaked = {
        name: len(_temporal_metric_points(context, name, task_queue))
        for name in reader.metrics()
        if _temporal_metric_points(context, name, task_queue)
    }
    assert not leaked, f"Temporal metrics were exported although ENABLE_METRICS is off: {leaked}"


@then("the collector should have exported Temporal workflow and activity spans:")
def step_collector_has_temporal_spans(context):
    """Assert the tracing interceptor produced the named spans; stores them for the trace id check."""
    scenario_context = get_current_scenario_context(context)
    telemetry: CollectorTelemetry = scenario_context.get("collector_telemetry")
    expected = {row["name"] for row in context.table}

    def read() -> list:
        telemetry.flush()
        spans = telemetry.spans()
        return spans if expected <= {span.name for span in spans} else []

    spans = telemetry.wait_for(read)
    names = sorted({span.name for span in telemetry.spans()})
    assert spans, f"Missing spans {sorted(expected)}; exported spans: {names}"
    scenario_context.store("temporal_spans", [span for span in spans if span.name in expected])


@then("the exported Temporal spans should share one trace id")
def step_temporal_spans_share_trace(context):
    """Assert client and worker spans were stitched into one trace by the tracing interceptor."""
    spans = get_current_scenario_context(context).get("temporal_spans")
    trace_ids = {span.context.trace_id for span in spans}
    assert len(trace_ids) == 1, f"Expected one trace id, got {len(trace_ids)} for {[s.name for s in spans]}"


@then('the exported {span_prefix} span should carry messaging attributes for task queue "{task_queue}"')
@then('the exported {span_prefix} span should carry messaging "{operation}" attributes for task queue "{task_queue}"')
def step_run_span_has_messaging_attributes(context, span_prefix, task_queue, operation="process"):
    """Assert the span has the attributes Elastic APM maps to the ``messaging`` type."""
    spans = get_current_scenario_context(context).get("temporal_spans")
    run_spans = [span for span in spans if span.name.startswith(f"{span_prefix}:")]
    assert run_spans, f"No {span_prefix} span among {[span.name for span in spans]}"
    expected = {
        "messaging.system": "temporal",
        "messaging.operation": operation,
        "messaging.operation.type": operation,
        "messaging.destination.name": task_queue,
    }
    for span in run_spans:
        actual = {key: span.attributes.get(key) for key in expected}
        assert actual == expected, f"{span.name} attributes {actual} != {expected}"


@then("the Temporal runtime manager should reuse one runtime until it is reset")
def step_temporal_runtime_manager(context):
    """Exercise the real ``TemporalRuntimeManager`` against the collector endpoint."""
    collector = get_current_scenario_context(context).get("test_containers").get_container("otel-collector")
    manager = TemporalRuntimeManager()
    assert manager.get_runtime(otel_metrics_enabled=False) is None
    first = manager.get_runtime(otel_metrics_enabled=True, otlp_endpoint=collector.grpc_endpoint)
    assert first is not None, "Runtime with OTLP metrics was not created"
    assert manager.get_runtime(otel_metrics_enabled=True, otlp_endpoint="http://127.0.0.1:1") is first
    manager.reset_runtime()
    second = manager.get_runtime(otel_metrics_enabled=True, otlp_endpoint=collector.grpc_endpoint)
    assert second is not None and second is not first, "reset_runtime() did not allow a new Runtime"
    global _runtime_endpoint
    _runtime_endpoint = collector.grpc_endpoint


def _free_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@given("Temporal metrics are served on a scrape endpoint")
def step_temporal_metrics_scrape_endpoint(context) -> None:
    """Switch the app exporter to ``pull`` so the Temporal SDK serves its own ``/metrics`` endpoint."""
    global _runtime_endpoint

    scenario_context = get_current_scenario_context(context)
    _enable_temporal_otel(context, enable_metrics=True)

    otel = BaseConfig.global_config().OTEL
    otel.METRICS_EXPORTER = OtelMetricsExporter.PULL
    otel.METRICS_PULL_HOST = "127.0.0.1"
    port = _free_local_port()

    # The Runtime was built for the collector in the step above; a scrape endpoint needs a new one, and the
    # next OTLP scenario must replace it again.
    TemporalRuntimeManager().reset_runtime()
    _runtime_endpoint = "scrape-endpoint"

    temporal_config = scenario_context.get("test_containers").get_container("temporal").config
    temporal_config = temporal_config.model_copy(update={"ENABLE_METRICS": True, "METRICS_PULL_PORT": port})
    scenario_context.temporal_adapter = TemporalAdapter(temporal_config)
    scenario_context.worker_manager = TemporalWorkerManager(temporal_config)
    scenario_context.store("temporal_scrape_url", f"http://127.0.0.1:{port}/metrics")


@given("Temporal metrics are exported over OTLP while the app exporter is the Pushgateway")
def step_temporal_metrics_with_pushgateway_exporter(context) -> None:
    """Select ``pushgateway`` as the app exporter; Temporal cannot push, so it must fall back to OTLP."""
    _enable_temporal_otel(context, enable_metrics=True)
    BaseConfig.global_config().OTEL.METRICS_EXPORTER = OtelMetricsExporter.PUSHGATEWAY


@then('the Temporal scrape endpoint should expose "{name}" for task queue "{task_queue}"')
def step_scrape_endpoint_exposes_metric(context, name, task_queue):
    """Poll (bounded) the Temporal SDK ``/metrics`` endpoint until the metric for the task queue shows up."""
    url = get_current_scenario_context(context).get("temporal_scrape_url")
    deadline = time.monotonic() + TEMPORAL_METRIC_TIMEOUT_SECONDS
    body = ""
    while time.monotonic() < deadline:
        try:
            body = httpx2.get(url, timeout=2).text
        except httpx2.HTTPError:
            body = ""
        if any(line.startswith(name) and f'task_queue="{task_queue}"' in line for line in body.splitlines()):
            return
        time.sleep(0.2)
    raise AssertionError(f"{name!r} for task queue {task_queue!r} not found at {url}. Last body:\n{body[:1500]}")


@given("Temporal metrics and traces are exported to the collector over HTTP/protobuf")
def step_temporal_otel_enabled_http(context) -> None:
    """Enable OpenTelemetry against the collector's HTTP receiver with Temporal metrics on."""
    _enable_temporal_otel(context, enable_metrics=True, protocol="http/protobuf")


@given("Temporal traces are exported to the collector after another library registered a plain tracer provider")
def step_temporal_otel_plain_provider(context) -> None:
    """Enable OpenTelemetry against the collector, but let another library register a plain SDK provider first."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    _enable_temporal_otel(
        context,
        enable_metrics=True,
        before_init=lambda: trace.set_tracer_provider(TracerProvider()),
    )


@then("the Temporal client should not carry a tracing interceptor")
def step_temporal_client_has_no_tracing_interceptor(context):
    """Check the connected client was built without ArchiPy's tracing interceptor."""
    adapter = get_temporal_adapter(context)
    client = run_async(context, adapter.get_client())
    interceptors = client.config(active_config=True).get("interceptors") or []
    assert not any(isinstance(item, MessagingOpenTelemetryInterceptor) for item in interceptors), interceptors


@then("the Temporal client should carry a tracing interceptor")
def step_temporal_client_has_tracing_interceptor(context):
    """Check the real connected client was built with the OpenTelemetry tracing interceptor."""
    adapter = get_temporal_adapter(context)
    client = run_async(context, adapter.get_client())
    interceptors = client.config(active_config=True).get("interceptors") or []
    assert any(isinstance(item, MessagingOpenTelemetryInterceptor) for item in interceptors), (
        f"No MessagingOpenTelemetryInterceptor on the client: {interceptors!r}"
    )


@when('I execute workflow "EchoOrderWorkflow" with order "{order_id}" totalling {total}')
def step_execute_echo_order(context, order_id, total):
    order = OrderPayload(order_id=order_id, total=Decimal(total), placed_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC))
    adapter = get_temporal_adapter(context)
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("sent_order", order)
    result = run_async(context, adapter.execute_workflow(EchoOrderWorkflow, order, task_queue="test-queue"))
    scenario_context.store("echoed_order", result)


@then("the echoed order should equal the sent order")
def step_echoed_order_equal(context):
    scenario_context = get_current_scenario_context(context)
    echoed = scenario_context.get("echoed_order")
    assert isinstance(echoed, OrderPayload), f"Expected OrderPayload, got {type(echoed).__name__}"
    assert echoed == scenario_context.get("sent_order"), echoed
@when('I list workflows with query "{query}" and limit {limit:d}')
def step_list_workflows_with_limit(context, query, limit):
    adapter = get_temporal_adapter(context)
    workflows = run_async(context, adapter.list_workflows(query=query, limit=limit))
    get_current_scenario_context(context).workflow_list = workflows


@then("the workflow list should contain exactly {count:d} workflow")
def step_workflow_list_exact(context, count):
    workflows = get_current_scenario_context(context).workflow_list
    assert len(workflows) == count, f"Expected {count} workflows, got {len(workflows)}"
@when('I request cancellation of workflow "{workflow_id}" with reason "{reason}"')
def step_cancel_workflow_with_reason(context, workflow_id, reason):
    adapter = get_temporal_adapter(context)
    run_async(context, adapter.cancel_workflow(workflow_id, reason=reason))


@then('the cancel request of workflow "{workflow_id}" should carry reason "{reason}"')
def step_cancel_request_reason(context, workflow_id, reason):
    adapter = get_temporal_adapter(context)

    async def _cancel_causes() -> list[str]:
        handle = await adapter.get_workflow_handle(workflow_id)
        history = await handle.fetch_history()
        return [
            event.workflow_execution_cancel_requested_event_attributes.cause
            for event in history.events
            if event.HasField("workflow_execution_cancel_requested_event_attributes")
        ]

    causes = run_async(context, _cancel_causes())
    assert reason in causes, f"Expected cancel reason {reason!r}, got {causes}"
@when("{count:d} callers get the client of a new Temporal adapter at once")
def step_concurrent_get_client(context, count):
    adapter = TemporalAdapter(get_temporal_adapter(context).config)

    async def _get_all() -> list[Any]:
        return await asyncio.gather(*(adapter.get_client() for _ in range(count)))

    get_current_scenario_context(context).store("concurrent_clients", run_async(context, _get_all()))


@then("they should all receive the same client")
def step_same_client(context):
    clients = get_current_scenario_context(context).get("concurrent_clients")
    assert len({id(client) for client in clients}) == 1, "Expected one shared client"
@when("the worker run ends without the handle")
def step_worker_run_ends_outside_handle(context):
    worker_handle = get_current_scenario_context(context).last_worker

    async def _end_run() -> None:
        await worker_handle._worker.shutdown()
        await asyncio.sleep(0)

    run_async(context, _end_run())


@then("the worker should have no run error")
def step_worker_no_run_error(context):
    worker_handle = get_current_scenario_context(context).last_worker
    assert worker_handle.run_error is None, worker_handle.run_error
class CacheKeyActivity(BaseActivity[str, str]):
    """Minimal activity used to check cache key generation."""

    async def _do_execute(self, activity_input: str) -> str:
        return activity_input


@when('I copy a postgres atomic activity with database type "{db_type}"')
def step_copy_atomic_activity(context, db_type):
    scenario_context = get_current_scenario_context(context)
    original = PostgresAtomicActivity()
    scenario_context.store("atomic_original", original)
    try:
        scenario_context.store("atomic_copy", original.with_db_type(db_type))
        scenario_context.store("atomic_error", None)
    except InvalidArgumentError as error:
        scenario_context.store("atomic_error", error)


@then("the atomic activity copy should be {outcome}")
def step_atomic_activity_copy_outcome(context, outcome):
    scenario_context = get_current_scenario_context(context)
    if outcome == "rejected":
        assert isinstance(scenario_context.get("atomic_error"), InvalidArgumentError)
        return
    expected = outcome.removeprefix("on ").split(",")[0]
    copied = scenario_context.get("atomic_copy")
    assert copied.db_type == expected, copied.db_type
    assert scenario_context.get("atomic_original").db_type == "postgres"
@when('I build the activity cache key for input "{activity_input}"')
def step_build_activity_cache_key(context, activity_input):
    key = CacheKeyActivity()._get_cache_key(activity_input)
    get_current_scenario_context(context).store("activity_cache_key", key)


@then('the activity cache key should be "{expected}"')
def step_activity_cache_key_should_be(context, expected):
    actual = get_current_scenario_context(context).get("activity_cache_key")
    assert actual == expected, f"Expected {expected}, got {actual}"


class RaisingActivity(BaseActivity[str, str]):
    """Activity that raises the ArchiPy error named by its input."""

    async def _do_execute(self, activity_input: str) -> str:
        import archipy.models.errors as archipy_errors

        raise getattr(archipy_errors, activity_input)()


@when("a base activity raising {error_name} runs in an activity environment")
def step_run_raising_activity(context, error_name):
    from temporalio.testing import ActivityEnvironment

    scenario_context = get_current_scenario_context(context)
    try:
        run_async(context, ActivityEnvironment().run(RaisingActivity().execute, error_name))
        scenario_context.store("activity_failure", None)
    except Exception as error:
        scenario_context.store("activity_failure", error)


@then("the activity failure should be {outcome}")
def step_activity_failure_outcome(context, outcome):
    from temporalio.exceptions import ApplicationError

    failure = get_current_scenario_context(context).get("activity_failure")
    if outcome == "non-retryable":
        assert isinstance(failure, ApplicationError) and failure.non_retryable, repr(failure)
        assert isinstance(failure.__cause__, BaseError), repr(failure.__cause__)
    else:
        assert isinstance(failure, BaseError) and not isinstance(failure, ApplicationError), repr(failure)


@when("I resolve a workflow timeout override of {override} against a configured {default:d} seconds")
def step_resolve_timeout_override(context, override, default):
    value = None if override == "none" else int(override)
    get_current_scenario_context(context).store("resolved_timeout", TemporalAdapter._timeout(value, default))


@then("the resolved workflow timeout should be {resolved}")
def step_resolved_timeout(context, resolved):
    actual = get_current_scenario_context(context).get("resolved_timeout")
    expected = None if resolved == "none" else timedelta(seconds=int(resolved))
    assert actual == expected, f"Expected {expected}, got {actual}"


@given('a worker is started for task queue "{task_queue}" that fails workflows on ValueError')
def step_worker_with_failure_types(context, task_queue):
    worker_manager = get_temporal_worker_manager(context)

    async def _start() -> WorkerHandle:
        return await worker_manager.start_worker(
            task_queue=task_queue,
            workflows=[ValueErrorWorkflow],
            workflow_failure_exception_types=[ValueError],
        )

    worker_handle = run_async(context, _start())
    scenario_context = get_current_scenario_context(context)
    if not hasattr(scenario_context, "workers"):
        scenario_context.workers = []
    scenario_context.workers.append(worker_handle)
    scenario_context.last_worker = worker_handle


@when('I execute workflow "{workflow_name}" on task queue "{task_queue}"')
def step_execute_workflow_on_queue(context, workflow_name, task_queue):
    from temporalio.client import WorkflowFailureError

    scenario_context = get_current_scenario_context(context)
    adapter = get_temporal_adapter(context)
    try:
        run_async(context, adapter.execute_workflow(workflow_name, task_queue=task_queue, execution_timeout=30))
        scenario_context.store("workflow_failure", None)
    except WorkflowFailureError as error:
        scenario_context.store("workflow_failure", error)


@then("the workflow execution should fail")
def step_workflow_execution_failed(context):
    assert get_current_scenario_context(context).get("workflow_failure") is not None, "Expected the workflow to fail"


@when('I replay the history of workflow "{workflow_id}" with {definition}')
def step_replay_workflow_history(context, workflow_id, definition):
    from temporalio.worker import Replayer

    workflow_class = GreetingWorkflow if definition == "the same definition" else ChangedGreetingWorkflow
    adapter = get_temporal_adapter(context)

    async def _replay() -> Exception | None:
        handle = await adapter.get_workflow_handle(workflow_id)
        history = await handle.fetch_history()
        result = await Replayer(workflows=[workflow_class]).replay_workflow(history, raise_on_replay_failure=False)
        return result.replay_failure

    get_current_scenario_context(context).store("replay_failure", run_async(context, _replay()))


@then("the replay should be {outcome}")
def step_replay_outcome(context, outcome):
    failure = get_current_scenario_context(context).get("replay_failure")
    if outcome == "deterministic":
        assert failure is None, f"Replay failed: {failure!r}"
    else:
        assert failure is not None, "Expected the changed workflow to break determinism"


@when("I run DailyReminderWorkflow for {days:d} days in a time-skipping test environment")
def step_run_time_skipping(context, days):
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker

    async def _run() -> str:
        async with await WorkflowEnvironment.start_time_skipping() as env:
            async with Worker(env.client, task_queue="time-skipping-queue", workflows=[DailyReminderWorkflow]):
                return await env.client.execute_workflow(
                    DailyReminderWorkflow.run,
                    days,
                    id=f"daily-reminder-{days}",
                    task_queue="time-skipping-queue",
                )

    get_current_scenario_context(context).store("time_skipping_result", run_async(context, _run()))


@then('the time-skipping result should be "{expected}"')
def step_time_skipping_result(context, expected):
    actual = get_current_scenario_context(context).get("time_skipping_result")
    assert actual == expected, f"Expected {expected!r}, got {actual!r}"


@then('the activities scheduled by workflow "{workflow_id}" should have no heartbeat timeout')
def step_activities_without_heartbeat(context, workflow_id):
    adapter = get_temporal_adapter(context)

    async def _heartbeat_timeouts() -> list[float]:
        handle = await adapter.get_workflow_handle(workflow_id)
        history = await handle.fetch_history()
        return [
            event.activity_task_scheduled_event_attributes.heartbeat_timeout.ToTimedelta().total_seconds()
            for event in history.events
            if event.HasField("activity_task_scheduled_event_attributes")
        ]

    timeouts = run_async(context, _heartbeat_timeouts())
    assert timeouts, "Expected at least one scheduled activity"
    assert all(timeout == 0 for timeout in timeouts), f"Unexpected heartbeat timeouts: {timeouts}"


@when('I start workflow "{workflow_name}" with workflow id "{workflow_id}" twice using conflict policy {policy}')
def step_start_workflow_twice_with_conflict_policy(context, workflow_name, workflow_id, policy):
    adapter = get_temporal_adapter(context)
    conflict_policy = WorkflowIDConflictPolicy[policy]

    async def _start_twice() -> list[str | None]:
        handles = [
            await adapter.start_workflow(
                workflow_name,
                workflow_id=workflow_id,
                task_queue="test-queue",
                id_conflict_policy=conflict_policy,
            )
            for _ in range(2)
        ]
        return [handle.result_run_id for handle in handles]

    get_current_scenario_context(context).store("started_run_ids", run_async(context, _start_twice()))


@then("both starts should return the same run id")
def step_same_run_id(context):
    run_ids = get_current_scenario_context(context).get("started_run_ids")
    assert run_ids[0] is not None and run_ids[0] == run_ids[1], run_ids


@given("a Temporal worker manager is configured with poller autoscaling and {rate:d} activities per second")
def step_temporal_worker_manager_tuned(context, rate):
    scenario_context = get_current_scenario_context(context)
    temporal_config = get_temporal_adapter(context).config.model_copy(
        update={"WORKER_POLLER_AUTOSCALING": True, "WORKER_MAX_ACTIVITIES_PER_SECOND": float(rate)},
    )
    scenario_context.worker_manager = TemporalWorkerManager(temporal_config)


@when('I start a worker for task queue "{task_queue}" in deployment "{deployment}" with build id "{build_id}"')
def step_start_worker_in_deployment(context, task_queue, deployment, build_id):
    deployment_config = WorkerDeploymentConfig(
        version=WorkerDeploymentVersion(deployment_name=deployment, build_id=build_id),
        use_worker_versioning=False,
    )
    run_async(context, start_test_worker(context, task_queue, deployment_config=deployment_config))


class CountingInterceptor(ClientInterceptor, WorkerInterceptor):
    """Client and worker interceptor that counts workflow starts and activity executions."""

    def __init__(self) -> None:
        self.workflow_starts = 0
        self.activity_executions = 0

    def intercept_client(self, next: OutboundInterceptor) -> OutboundInterceptor:
        counter = self

        class _Outbound(OutboundInterceptor):
            async def start_workflow(self, input: StartWorkflowInput) -> Any:
                counter.workflow_starts += 1
                return await super().start_workflow(input)

        return _Outbound(next)

    def intercept_activity(self, next: ActivityInboundInterceptor) -> ActivityInboundInterceptor:
        counter = self

        class _Inbound(ActivityInboundInterceptor):
            async def execute_activity(self, input: ExecuteActivityInput) -> Any:
                counter.activity_executions += 1
                return await super().execute_activity(input)

        return _Inbound(next)


@given("a Temporal adapter and worker manager are configured with a counting interceptor")
def step_configure_counting_interceptor(context):
    scenario_context = get_current_scenario_context(context)
    temporal_config = get_temporal_adapter(context).config
    interceptor = CountingInterceptor()
    scenario_context.store("counting_interceptor", interceptor)
    scenario_context.temporal_adapter = TemporalAdapter(temporal_config, interceptors=[interceptor])
    scenario_context.worker_manager = TemporalWorkerManager(temporal_config, interceptors=[interceptor])


@then("the counting interceptor should have seen {starts:d} workflow start and {executions:d} activity execution")
def step_counting_interceptor_saw(context, starts, executions):
    interceptor = get_current_scenario_context(context).get("counting_interceptor")
    assert interceptor.workflow_starts == starts, interceptor.workflow_starts
    assert interceptor.activity_executions == executions, interceptor.activity_executions


@when("I build the messaging tracing workflow interceptor class")
def step_build_messaging_workflow_interceptor_class(context):
    scenario_context = get_current_scenario_context(context)
    try:
        interceptor_class = MessagingOpenTelemetryInterceptor().workflow_interceptor_class(
            WorkflowInterceptorClassInput(unsafe_extern_functions={}),
        )
        scenario_context.store("tracing_interceptor_error", None)
        scenario_context.store("tracing_interceptor_class", interceptor_class)
    except ConfigurationError as error:
        scenario_context.store("tracing_interceptor_error", error)


@then("the workflow interceptor class should be built without a ConfigurationError")
def step_workflow_interceptor_class_built(context):
    scenario_context = get_current_scenario_context(context)
    error = scenario_context.get("tracing_interceptor_error")
    assert error is None, f"temporalio changed its private span hook: {error}"
    assert scenario_context.get("tracing_interceptor_class") is not None


@when('I build a Temporal Runtime exporting metrics to "{endpoint}"')
def step_build_runtime_with_endpoint(context, endpoint):
    scenario_context = get_current_scenario_context(context)
    manager = TemporalRuntimeManager()
    manager.reset_runtime()
    try:
        manager.get_runtime(otel_metrics_enabled=True, otlp_endpoint=endpoint, global_tags={"service": "bdd"})
        scenario_context.store("runtime_error", None)
    except ConfigurationError as error:
        scenario_context.store("runtime_error", error)
    finally:
        manager.reset_runtime()


@then("building the Temporal Runtime should raise a ConfigurationError")
def step_runtime_raised_configuration_error(context):
    error = get_current_scenario_context(context).get("runtime_error")
    assert isinstance(error, ConfigurationError), f"Expected ConfigurationError, got {error!r}"


@when('I try to start workflow "{workflow_name}" with workflow id "{workflow_id}" again')
def step_try_start_workflow_again(context, workflow_name, workflow_id):
    scenario_context = get_current_scenario_context(context)
    adapter = get_temporal_adapter(context)
    try:
        run_async(context, adapter.start_workflow(workflow_name, workflow_id=workflow_id, task_queue="test-queue"))
    except BaseError as error:
        scenario_context.error = error


@then("the error should be the ArchiPy {error_name}")
def step_error_is_archipy_error(context, error_name):
    import archipy.models.errors as archipy_errors
    from archipy.models.errors import temporal_errors

    error = get_current_scenario_context(context).error
    expected = getattr(archipy_errors, error_name, None) or getattr(temporal_errors, error_name)
    assert isinstance(error, expected), f"Expected {error_name}, got {type(error).__name__}: {error!r}"


@when('I pause schedule "{schedule_id}" with note "{note}"')
def step_pause_schedule(context, schedule_id, note):
    run_async(context, get_temporal_adapter(context).pause_schedule(schedule_id, note=note))


@when('I unpause schedule "{schedule_id}"')
def step_unpause_schedule(context, schedule_id):
    run_async(context, get_temporal_adapter(context).unpause_schedule(schedule_id))


@when('I trigger schedule "{schedule_id}"')
def step_trigger_schedule(context, schedule_id):
    run_async(context, get_temporal_adapter(context).trigger_schedule(schedule_id))


@then('schedule "{schedule_id}" should be paused')
def step_schedule_paused(context, schedule_id):
    description = run_async(context, get_temporal_adapter(context).describe_schedule(schedule_id))
    assert description.schedule.state.paused, "Expected the schedule to be paused"


@then('schedule "{schedule_id}" should not be paused')
def step_schedule_not_paused(context, schedule_id):
    description = run_async(context, get_temporal_adapter(context).describe_schedule(schedule_id))
    assert not description.schedule.state.paused, "Expected the schedule to be running"


@then('the schedule list should contain "{schedule_id}"')
def step_schedule_list_contains(context, schedule_id):
    schedules = run_async(context, get_temporal_adapter(context).list_schedules())
    assert schedule_id in [schedule.id for schedule in schedules], [schedule.id for schedule in schedules]


@when('I call the deprecated stop_schedule for "{schedule_id}"')
def step_call_deprecated_stop_schedule(context, schedule_id):
    import warnings

    adapter = get_temporal_adapter(context)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        run_async(context, adapter.stop_schedule(schedule_id))
    get_current_scenario_context(context).store("caught_warnings", caught)


@then("a DeprecationWarning should have been emitted")
def step_deprecation_warning_emitted(context):
    caught = get_current_scenario_context(context).get("caught_warnings")
    assert any(issubclass(item.category, DeprecationWarning) for item in caught), [str(item.message) for item in caught]


class PostgresAtomicActivity(AtomicActivity[str, str]):
    """Minimal atomic activity used to check ``with_db_type``."""
