---
title: Temporal Adapter Tutorial
description: Practical examples for using the ArchiPy Temporal adapter.
---

# Temporal Adapter Tutorial

This example demonstrates how to use the Temporal adapter for workflow orchestration and activity execution with proper
error handling and Python 3.14 type hints.

## Installation

```bash
uv add "archipy[temporalio]"
```

## Configuration

Configure the Temporal adapter via environment variables or a `TemporalConfig` object.

### Environment Variables

```bash
TEMPORAL__HOST=localhost
TEMPORAL__PORT=7233
TEMPORAL__NAMESPACE=default
TEMPORAL__TASK_QUEUE=my-task-queue
TEMPORAL__ENABLE_METRICS=false
TEMPORAL__CLIENT_IDENTITY=
TEMPORAL__API_KEY=
TEMPORAL__LAZY_CONNECT=false
TEMPORAL__KEEP_ALIVE_INTERVAL_MS=30000
TEMPORAL__KEEP_ALIVE_TIMEOUT_MS=15000
TEMPORAL__CLIENT_RPC_RETRY_MAX_RETRIES=10
TEMPORAL__CLIENT_RPC_RETRY_INITIAL_INTERVAL_MS=100
TEMPORAL__CLIENT_RPC_RETRY_MAX_INTERVAL_MS=5000
TEMPORAL__WORKER_GRACEFUL_SHUTDOWN_SECONDS=30
TEMPORAL__WORKER_MAX_CACHED_WORKFLOWS=1000
TEMPORAL__WORKER_DEBUG_MODE=false
TEMPORAL__WORKER_DISABLE_EAGER_ACTIVITY_EXECUTION=false
TEMPORAL__TLS_CA_CERT=/path/to/ca.crt
TEMPORAL__TLS_CLIENT_CERT=/path/to/client.crt
TEMPORAL__TLS_CLIENT_KEY=/path/to/client.key
TEMPORAL__WORKFLOW_EXECUTION_TIMEOUT=300
TEMPORAL__WORKFLOW_RUN_TIMEOUT=60
TEMPORAL__ACTIVITY_START_TO_CLOSE_TIMEOUT=30
TEMPORAL__RETRY_MAXIMUM_ATTEMPTS=3
TEMPORAL__RETRY_BACKOFF_COEFFICIENT=2.0
TEMPORAL__RETRY_MAXIMUM_INTERVAL=60
TEMPORAL__RETRY_INITIAL_INTERVAL=1
```

> **Note:** `TEMPORAL__API_KEY` is for Temporal Cloud authentication. Local dev servers ignore it.

### Configuration Reference

| Variable | Purpose | Default |
|----------|---------|---------|
| `CLIENT_IDENTITY` | Client identity visible on the Temporal server | `None` |
| `API_KEY` | Temporal Cloud API key | `None` |
| `LAZY_CONNECT` | Defer connection until first client use | `false` |
| `KEEP_ALIVE_INTERVAL_MS` | gRPC keep-alive ping interval | `30000` |
| `KEEP_ALIVE_TIMEOUT_MS` | gRPC keep-alive timeout | `15000` |
| `CLIENT_RPC_RETRY_*` | Client-side RPC retry backoff | SDK defaults |
| `WORKER_GRACEFUL_SHUTDOWN_SECONDS` | Worker shutdown grace period | `30` |
| `WORKER_MAX_CACHED_WORKFLOWS` | In-memory workflow cache size | `1000` |
| `WORKER_DEBUG_MODE` | Enable workflow sandbox debug mode | `false` |
| `WORKER_DISABLE_EAGER_ACTIVITY_EXECUTION` | Disable eager activity execution | `false` |
| `RETRY_INITIAL_INTERVAL` | Initial workflow/activity retry delay (seconds) | `1` |
| `RETRY_NON_RETRYABLE_ERROR_TYPES` | Error types excluded from retries | `None` |

### Direct Configuration

```python
from archipy.configs.config_template import TemporalConfig

config = TemporalConfig(
    HOST="localhost",
    PORT=7233,
    NAMESPACE="default",
    TASK_QUEUE="my-task-queue",
    WORKFLOW_EXECUTION_TIMEOUT=300,
    WORKFLOW_RUN_TIMEOUT=60,
    ACTIVITY_START_TO_CLOSE_TIMEOUT=30,
    RETRY_MAXIMUM_ATTEMPTS=3,
    RETRY_BACKOFF_COEFFICIENT=2.0,
    RETRY_MAXIMUM_INTERVAL=60,
    RETRY_INITIAL_INTERVAL=1,
    CLIENT_IDENTITY="my-service-client",
    WORKER_DEBUG_MODE=False,
)
```

## Basic Usage

```python
import asyncio
import logging
import time

from temporalio import activity, workflow

from archipy.adapters.temporal import BaseActivity, BaseWorkflow, TemporalAdapter
from archipy.configs.config_template import TemporalConfig
from archipy.models.errors import ConfigurationError, InternalError

# Configure logging
logger = logging.getLogger(__name__)


# Define a simple workflow
class MyWorkflow(BaseWorkflow[dict, str]):
    """Simple workflow example."""

    @workflow.run
    async def run(self, workflow_input: dict[str, list[str]]) -> str:
        """Main workflow logic.

        Args:
            workflow_input: Input data for the workflow

        Returns:
            Result message from the workflow
        """
        self._log_workflow_event("workflow_started", {"input": workflow_input})

        # Execute an activity - configuration is automatically applied from TemporalConfig
        try:
            result = await self._execute_activity_with_retry(
                process_data_activity,
                workflow_input
                # start_to_close_timeout, heartbeat_timeout, retry_policy, task_queue
                # are automatically set from TemporalConfig if not provided
            )
        except Exception as e:
            self._log_workflow_event("activity_failed", {"error": str(e)})
            raise
        else:
            self._log_workflow_event("workflow_completed", {"result": result})
            return f"Workflow completed: {result}"


# Define a simple activity function
@activity.defn
async def process_data_activity(data: dict[str, list[str]]) -> str:
    """Process data in an activity.

    Args:
        data: Input data to process

    Returns:
        Processed result
    """
    logger.info(f"Processing {len(data)} items")
    time.sleep(1)  # Simulate processing

    return f"Processed {len(data)} items"


# Execute workflow
temporal = TemporalAdapter()

async def main() -> None:
    """Execute the workflow and handle cleanup."""
    try:
        # Execute workflow and wait for result
        result = await temporal.execute_workflow(
            MyWorkflow,
            {"items": ["a", "b", "c"]},
            workflow_id="my-workflow-123",
            task_queue="my-task-queue"
        )
    except InternalError as e:
        logger.error(f"Workflow execution failed: {e}")
        raise
    else:
        logger.info(f"Workflow result: {result}")
    finally:
        await temporal.close()


# Run the workflow
asyncio.run(main())
```

## Advanced Configuration Overrides

```python
import asyncio
import logging
import random
from datetime import timedelta

from temporalio.common import RetryPolicy
from archipy.models.errors import InternalError

# Configure logging
logger = logging.getLogger(__name__)


class ConfigOverrideWorkflow(BaseWorkflow[dict, str]):
    """Workflow showing how to override default configurations."""

    @workflow.run
    async def run(self, workflow_input: dict[str, str]) -> str:
        """Workflow with custom timeouts and retry policies."""

        try:
            # Override activity timeout for a long-running activity
            long_result = await self._execute_activity_with_retry(
                long_running_activity,
                workflow_input,
                start_to_close_timeout=timedelta(minutes=10),  # Override default 30 seconds
                heartbeat_timeout=timedelta(seconds=30)  # Override default 10 seconds
            )
        except Exception as e:
            logger.error(f"Long running activity failed: {e}")
            raise

        try:
            # Override retry policy for a critical activity
            critical_result = await self._execute_activity_with_retry(
                critical_activity,
                workflow_input,
                retry_policy=RetryPolicy(
                    maximum_attempts=10,  # Override default 3 attempts
                    backoff_coefficient=1.5,  # Override default 2.0
                    maximum_interval=timedelta(seconds=30)  # Override default 60 seconds
                )
            )
        except Exception as e:
            logger.error(f"Critical activity failed after retries: {e}")
            raise

        try:
            # Use custom task queue
            special_result = await self._execute_activity_with_retry(
                special_activity,
                workflow_input,
                task_queue="special-workers"  # Override default task queue
            )
        except Exception as e:
            logger.error(f"Special activity failed: {e}")
            raise

        try:
            # Execute child workflow with custom timeout
            child_result = await self._execute_child_workflow(
                ChildWorkflow,
                {"parent_data": workflow_input},
                execution_timeout=timedelta(minutes=15)  # Override default 5 minutes
            )
        except Exception as e:
            logger.error(f"Child workflow failed: {e}")
            raise
        else:
            return f"All results: {long_result}, {critical_result}, {special_result}, {child_result}"


@activity.defn
async def long_running_activity(data: dict[str, str]) -> str:
    """Activity that takes a long time to complete."""
    logger.info("Starting long running activity")
    await asyncio.sleep(300)  # 5 minutes
    return f"Long work completed: {data}"


@activity.defn
async def critical_activity(data: dict[str, str]) -> str:
    """Critical activity that needs more retry attempts."""
    if random.random() < 0.8:  # 80% failure rate for demo  # noqa: S311
        logger.warning("Critical operation failed, will retry")
        raise Exception("Critical operation failed")
    return f"Critical work completed: {data}"


@activity.defn
async def special_activity(data: dict[str, str]) -> str:
    """Activity that runs on special workers."""
    logger.info("Processing on special worker")
    return f"Special work completed: {data}"


class ChildWorkflow(BaseWorkflow[dict, str]):
    """Child workflow with its own logic."""

    @workflow.run
    async def run(self, workflow_input: dict[str, dict[str, str]]) -> str:
        """Child workflow with its own logic."""
        logger.info(f"Child workflow processing: {workflow_input}")
        return f"Child workflow processed: {workflow_input['parent_data']}"
```

## Using Atomic Activities

Activities can use atomic transactions for database operations:

```python
import logging
from datetime import timedelta

from archipy.adapters.temporal import AtomicActivity
from archipy.helpers.decorators.sqlalchemy_atomic import postgres_sqlalchemy_atomic_decorator
from archipy.models.errors import DatabaseConnectionError, DatabaseQueryError

# Configure logging
logger = logging.getLogger(__name__)


# Define an activity with atomic transaction support
class UserCreationActivity(AtomicActivity[dict, dict]):
    """Activity for creating users with atomic database transactions."""

    def __init__(self, user_service) -> None:
        """Initialize with your business logic service.

        Args:
            user_service: Service containing business logic and repository access
        """
        super().__init__(user_service, db_type="postgres")

    async def _do_execute(self, activity_input: dict[str, str]) -> dict[str, str]:
        """Create user with atomic transaction.

        Args:
            activity_input: User data to create

        Returns:
            Created user information

        Raises:
            DatabaseQueryError: If database operation fails
            DatabaseConnectionError: If database connection fails
        """
        try:
            # Execute business logic with atomic transaction
            user = await self._call_atomic_method("create_user", activity_input)

            # Additional database operations within the same transaction
            profile = await self._call_atomic_method(
                "create_user_profile",
                user.uuid,
                activity_input.get("profile", {})
            )
        except (DatabaseQueryError, DatabaseConnectionError) as e:
            self._log_activity_event("user_creation_failed", {
                "error": str(e),
                "input": activity_input
            })
            raise
        else:
            result = {
                "user_id": str(user.uuid),
                "username": user.username,
                "profile_id": str(profile.uuid)
            }
            logger.info(f"User created successfully: {user.username}")
            return result


# Use in workflow
class UserOnboardingWorkflow(BaseWorkflow[dict, dict]):
    """User onboarding workflow."""

    @workflow.run
    async def run(self, workflow_input: dict[str, dict[str, str]]) -> dict[str, dict[str, str] | bool]:
        """User onboarding workflow.

        Args:
            workflow_input: User registration data

        Returns:
            Onboarding result
        """
        self._log_workflow_event("onboarding_started")

        try:
            # Execute atomic user creation activity
            user_result = await self._execute_activity_with_retry(
                UserCreationActivity.execute_atomic,
                workflow_input["user_data"],
                start_to_close_timeout=timedelta(seconds=60)
            )
        except Exception as e:
            logger.error(f"User creation failed: {e}")
            raise
        else:
            logger.info(f"User created: {user_result['user_id']}")

        try:
            # Execute welcome email activity
            email_result = await self._execute_activity_with_retry(
                send_welcome_email_activity,
                {
                    "user_id": user_result["user_id"],
                    "email": workflow_input["user_data"]["email"]
                }
            )
        except Exception as e:
            logger.error(f"Welcome email failed: {e}")
            # Don't fail the workflow if email fails
            email_result = False

        self._log_workflow_event("onboarding_completed", {
            "user_id": user_result["user_id"]
        })

        return {
            "user": user_result,
            "email_sent": email_result
        }
```

## Async Operations with Workers

```python
import asyncio
import logging

from archipy.adapters.temporal import TemporalWorkerManager
from archipy.models.errors.temporal_errors import WorkerConnectionError, WorkerShutdownError

# Configure logging
logger = logging.getLogger(__name__)


async def run_worker() -> None:
    """Start a Temporal worker to execute workflows and activities."""
    worker_manager = TemporalWorkerManager()

    try:
        # Start worker with workflows and activities
        worker_handle = await worker_manager.start_worker(
            task_queue="my-task-queue",
            workflows=[MyWorkflow, UserOnboardingWorkflow],
            activities=[UserCreationActivity, process_data_activity, send_welcome_email_activity],
            max_concurrent_workflow_tasks=10,
            max_concurrent_activities=20
        )
    except WorkerConnectionError as e:
        logger.error(f"Failed to start worker: {e}")
        raise
    else:
        logger.info(f"Worker started: {worker_handle.identity}")

        try:
            # Keep worker running
            await worker_handle.wait_until_stopped()
        except WorkerShutdownError as e:
            logger.error(f"Worker shutdown error: {e}")
            raise
        finally:
            # Graceful shutdown
            await worker_manager.shutdown_all_workers()


# Activity with business logic integration
@activity.defn
async def send_welcome_email_activity(data: dict[str, str]) -> bool:
    """Send welcome email activity.

    Args:
        data: Email data containing user_id and email

    Returns:
        True if email sent successfully
    """
    logger.info(f"Sending welcome email to {data['email']}")
    # This would integrate with your email service
    return True
```

## Error Handling

```python
import asyncio
import logging

from archipy.models.errors import (
    DatabaseConnectionError,
    DatabaseQueryError,
    InternalError,
    NotFoundError,
)
from archipy.models.errors.temporal_errors import TemporalError, WorkerConnectionError, WorkerShutdownError

# Configure logging
logger = logging.getLogger(__name__)


async def robust_workflow_execution() -> None:
    """Example of proper error handling with Temporal operations."""
    temporal = TemporalAdapter()

    try:
        # Start workflow with error handling
        workflow_handle = await temporal.start_workflow(
            UserOnboardingWorkflow,
            {
                "user_data": {
                    "username": "john_doe",
                    "email": "john@example.com",
                    "profile": {"age": 30, "city": "New York"}
                }
            },
            workflow_id="user-onboarding-001",
            execution_timeout=300,  # 5 minutes
            run_timeout=120  # 2 minutes per run
        )
    except WorkerConnectionError as e:
        logger.error(f"Worker connection failed: {e}")
        raise
    except InternalError as e:
        logger.error(f"Failed to start workflow: {e}")
        raise
    else:
        logger.info(f"Workflow started: {workflow_handle.id}")

        try:
            # Wait for result with timeout
            result = await workflow_handle.result()
        except (DatabaseQueryError, DatabaseConnectionError) as e:
            logger.error(f"Database error in workflow: {e}")
            raise
        except TemporalError as e:
            logger.error(f"Temporal operation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
        else:
            logger.info(f"User onboarded successfully: {result}")
    finally:
        # Always cleanup
        await temporal.close()


# Activity-level error handling
class RobustUserActivity(AtomicActivity[dict, dict]):
    """Activity with comprehensive error handling."""

    def __init__(self, user_service, db_type: str = "postgres") -> None:
        super().__init__(user_service, db_type)

    async def _do_execute(self, activity_input: dict[str, str]) -> dict[str, str]:
        """Execute with comprehensive error handling."""
        try:
            result = await self._call_atomic_method("process_user_data", activity_input)
        except DatabaseQueryError as e:
            self._log_activity_event("database_query_failed", {
                "error": str(e),
                "query_type": "user_creation"
            })
            # Re-raise to let Temporal handle retries
            raise
        except DatabaseConnectionError as e:
            self._log_activity_event("database_connection_failed", {
                "error": str(e)
            })
            # This might be retryable
            raise
        except NotFoundError as e:
            self._log_activity_event("resource_not_found", {
                "error": str(e)
            })
            # This is likely not retryable
            raise
        except Exception as e:
            self._log_activity_event("unexpected_error", {
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise
        else:
            logger.info("Activity executed successfully")
            return result

    async def _handle_error(self, activity_input: dict[str, str], error: Exception) -> None:
        """Custom error handling for this activity."""
        # Log specific error details
        self._log_activity_event("activity_error_handler", {
            "error_type": type(error).__name__,
            "input_username": activity_input.get("username", "unknown"),
            "retry_attempt": getattr(error, "attempt_count", "unknown")
        })

        # Call parent error handler
        await super()._handle_error(activity_input, error)
```

## OpenTelemetry Metrics and Tracing

The Temporal adapter exports SDK metrics over OTLP and attaches Temporal's
`TracingInterceptor` when OpenTelemetry is enabled on `BaseConfig.OTEL`.

### Configuration

Enable OTel globally and flip Temporal's metrics flag:

```python
import logging

from archipy.adapters.temporal import TemporalAdapter, TemporalWorkerManager
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import OpentelemetryConfig, TemporalConfig

logger = logging.getLogger(__name__)

config = BaseConfig()
config.OTEL = OpentelemetryConfig(
    IS_ENABLED=True,
    OTLP_ENDPOINT="http://localhost:4317",
    PROTOCOL="grpc",
    METRICS_ENABLED=True,
    TRACES_ENABLED=True,
    SERVICE_NAME="temporal-worker",
)
BaseConfig.set_global(config)

temporal_config = TemporalConfig(
    HOST="localhost",
    PORT=7233,
    NAMESPACE="default",
    TASK_QUEUE="my-task-queue",
    ENABLE_METRICS=True,  # Uses BaseConfig.OTEL endpoint via OpenTelemetryConfig
)

temporal_adapter = TemporalAdapter(temporal_config)
worker_manager = TemporalWorkerManager(temporal_config)

logger.info("Temporal adapter created with OTLP metrics and TracingInterceptor")
```

### Environment-Based Configuration

```bash
OTEL__IS_ENABLED=true
OTEL__OTLP_ENDPOINT=http://localhost:4317
OTEL__METRICS_ENABLED=true
OTEL__TRACES_ENABLED=true
TEMPORAL__ENABLE_METRICS=true
TEMPORAL__HOST=temporal.production.com
```

### What gets wired

| Feature | When | Mechanism |
|---------|------|-----------|
| Metrics | `TEMPORAL.ENABLE_METRICS` and `OTEL.IS_ENABLED` + `METRICS_ENABLED` | Temporal `Runtime` with `OpenTelemetryConfig` (OTLP URL/headers/protocol from `OTEL`) |
| Traces | `OTEL.IS_ENABLED` and `TRACES_ENABLED` | `temporalio.contrib.opentelemetry.TracingInterceptor` on the client after `OtelUtils.init_otel_if_needed` |

### Available Metrics

When metrics are enabled, the Temporal SDK emits client and worker metrics to your OTLP
collector (same endpoint as the rest of the app). Typical series include:

#### Client-Side Metrics

- `temporal_request_*` — client request counts and latency
- `temporal_long_request_*` — long-polling request metrics
- `temporal_workflow_*` — workflow operation metrics (start, execute, cancel, terminate)
- `temporal_sticky_cache_*` — sticky workflow cache statistics

#### Worker-Side Metrics

- `temporal_worker_task_slots_available` / `_used` — task slot gauges
- `temporal_worker_task_queue_poll_*` — task queue polling metrics
- `temporal_workflow_task_execution_*` / `temporal_activity_task_execution_*` — task execution
- `temporal_workflow_task_replay_latency` — workflow replay latency
- `temporal_activity_execution_*` — activity execution counts and latency

> **Tip:** Query these series in your OTLP backend / Grafana after the collector scrapes or
> receives OTLP — panel setup is backend-specific and isn't covered here.

### Complete Example with Metrics

```python
import asyncio
import logging

from temporalio import activity, workflow

from archipy.adapters.temporal import BaseWorkflow, TemporalAdapter, TemporalWorkerManager
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import OpentelemetryConfig, TemporalConfig

logger = logging.getLogger(__name__)

config = BaseConfig()
config.OTEL = OpentelemetryConfig(
    IS_ENABLED=True,
    OTLP_ENDPOINT="http://localhost:4317",
    METRICS_ENABLED=True,
    TRACES_ENABLED=True,
)
BaseConfig.set_global(config)

temporal_config = TemporalConfig(
    HOST="localhost",
    PORT=7233,
    NAMESPACE="default",
    TASK_QUEUE="metrics-demo",
    ENABLE_METRICS=True,
)


class MetricsWorkflow(BaseWorkflow[str, str]):
    """Workflow with OTel metrics collection."""

    @workflow.run
    async def run(self, name: str) -> str:
        """Process with metrics tracking."""
        self._log_workflow_event("workflow_started", {"name": name})

        result = await self._execute_activity_with_retry(
            greet_activity,
            name,
        )

        self._log_workflow_event("workflow_completed", {"result": result})
        return result


@activity.defn
async def greet_activity(name: str) -> str:
    """Activity with metrics tracking."""
    logger.info("Processing greeting for %s", name)
    await asyncio.sleep(0.1)
    return f"Hello, {name}!"


async def main() -> None:
    """Run workflow with OTLP metrics collection."""
    temporal_adapter = TemporalAdapter(temporal_config)
    worker_manager = TemporalWorkerManager(temporal_config)

    try:
        await worker_manager.start_worker(
            task_queue="metrics-demo",
            workflows=[MetricsWorkflow],
            activities=[greet_activity],
        )
        logger.info("Worker started with OTLP metrics enabled")

        results = []
        for i in range(10):
            result = await temporal_adapter.execute_workflow(
                MetricsWorkflow,
                f"User{i}",
                workflow_id=f"metrics-workflow-{i}",
                task_queue="metrics-demo",
            )
            results.append(result)

        logger.info("Completed %d workflows; metrics exported via OTLP", len(results))

    finally:
        await worker_manager.shutdown_all_workers()
        await temporal_adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### Monitoring Best Practices

1. **Set Alerts**: Alert on high failure rates or latency in your OTLP backend
2. **Track Task Queues**: Monitor task queue depths and worker availability
3. **Workflow Duration**: Alert on workflows exceeding expected execution time
4. **Activity Failures**: Track activity failure patterns for debugging
5. **Worker Health**: Monitor worker task slot usage and availability
6. **Resource Usage**: Correlate Temporal metrics with system resource metrics

### Troubleshooting

If metrics or traces are missing:

1. Verify `OTEL.IS_ENABLED = True` and `METRICS_ENABLED` / `TRACES_ENABLED` as needed
2. Verify `ENABLE_METRICS = True` in `TemporalConfig` for SDK metrics
3. Confirm the OTLP collector is reachable at `OTEL.OTLP_ENDPOINT`
4. Ensure `temporalio` is installed (`archipy[temporalio]`)
5. Check logs for Runtime / TracingInterceptor initialization errors

The Temporal Runtime with OTLP is created lazily on first client connection using
`TemporalRuntimeManager` (singleton). Once created with metrics enabled, the Runtime cannot be
reconfigured in-process (Temporal SDK limitation).

## Best Practices

1. **Workflow Design**: Keep workflows as coordinators - let activities handle business logic
2. **Error Handling**: Use specific error types and proper error chains with `raise ... from e`
3. **Transactions**: Use `AtomicActivity` for database operations requiring consistency
4. **Testing**: Mock adapters and activities for unit testing
5. **Configuration**: Use environment-specific configurations for different deployments
6. **Monitoring**: Leverage workflow logging and OTel tracing/metrics
7. **Timeouts**: Set appropriate timeouts for workflows and activities
8. **Retries**: Configure retry policies based on error types and business requirements
9. **Metrics**: Enable `ENABLE_METRICS` with global `OTEL` for production observability

## See Also

- [Error Handling](../error_handling.md) — Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) — Temporal configuration setup
- [Observability](../observability.md) — OpenTelemetry OTLP traces and metrics
- [BDD Testing](../testing_strategy.md) — Testing workflow operations
- [SQLAlchemy Decorators](../helpers/decorators.md#sqlalchemy-transaction-decorators) — Atomic transaction usage
- [API Reference](../../api_reference/adapters/temporal.md) — Full Temporal adapter API documentation
