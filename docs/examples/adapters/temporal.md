# Temporal Adapter

This example demonstrates how to use the Temporal adapter for workflow orchestration and activity execution with proper error handling and Python 3.14 type hints.

## Basic Usage

```python
import asyncio
import logging

from archipy.adapters.temporal import TemporalAdapter, BaseWorkflow, BaseActivity
from archipy.configs.config_template import TemporalConfig
from archipy.models.errors import ConfigurationError, InternalError
from temporalio import workflow, activity

# Configure logging
logger = logging.getLogger(__name__)

# Configure Temporal connection with all available settings
try:
    temporal_config = TemporalConfig(
        # Connection settings
        HOST="localhost",
        PORT=7233,
        NAMESPACE="default",
        TASK_QUEUE="my-task-queue",

        # TLS settings (optional - for secure connections)
        TLS_CA_CERT="/path/to/ca.crt",
        TLS_CLIENT_CERT="/path/to/client.crt",
        TLS_CLIENT_KEY="/path/to/client.key",

        # Workflow timeout settings (in seconds)
        WORKFLOW_EXECUTION_TIMEOUT=300,  # Maximum total workflow execution time
        WORKFLOW_RUN_TIMEOUT=60,         # Maximum single workflow run time
        WORKFLOW_TASK_TIMEOUT=30,        # Maximum workflow task processing time

        # Activity timeout settings (in seconds)
        ACTIVITY_START_TO_CLOSE_TIMEOUT=30,  # Maximum activity execution time
        ACTIVITY_HEARTBEAT_TIMEOUT=10,       # Activity heartbeat timeout

        # Retry configuration for failed activities
        RETRY_MAXIMUM_ATTEMPTS=3,        # Maximum number of retry attempts
        RETRY_BACKOFF_COEFFICIENT=2.0,   # Backoff multiplier between retries
        RETRY_MAXIMUM_INTERVAL=60        # Maximum interval between retries
    )
except Exception as e:
    logger.error(f"Invalid Temporal configuration: {e}")
    raise ConfigurationError() from e
else:
    logger.info("Temporal configuration created successfully")

# Create adapter
try:
    temporal = TemporalAdapter(temporal_config)
except Exception as e:
    logger.error(f"Failed to create Temporal adapter: {e}")
    raise InternalError() from e
else:
    logger.info("Temporal adapter created successfully")


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
    import time

    logger.info(f"Processing {len(data)} items")
    time.sleep(1)  # Simulate processing

    return f"Processed {len(data)} items"


# Execute workflow
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

## Configuration Override Examples

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
                heartbeat_timeout=timedelta(seconds=30)        # Override default 10 seconds
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
                    maximum_attempts=10,        # Override default 3 attempts
                    backoff_coefficient=1.5,   # Override default 2.0
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
    if random.random() < 0.8:  # 80% failure rate for demo
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

## Environment-Based Configuration

```python
import logging
import os

from archipy.configs.config_template import TemporalConfig
from archipy.models.errors import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)

try:
    # Production configuration
    production_config = TemporalConfig(
        HOST=os.getenv("TEMPORAL_HOST", "temporal.production.com"),
        PORT=int(os.getenv("TEMPORAL_PORT", "7233")),
        NAMESPACE=os.getenv("TEMPORAL_NAMESPACE", "production"),
        TASK_QUEUE=os.getenv("TEMPORAL_TASK_QUEUE", "production-queue"),

        # Production TLS settings
        TLS_CA_CERT=os.getenv("TEMPORAL_TLS_CA_CERT"),
        TLS_CLIENT_CERT=os.getenv("TEMPORAL_TLS_CLIENT_CERT"),
        TLS_CLIENT_KEY=os.getenv("TEMPORAL_TLS_CLIENT_KEY"),

        # Production timeout settings (longer timeouts)
        WORKFLOW_EXECUTION_TIMEOUT=1800,  # 30 minutes
        WORKFLOW_RUN_TIMEOUT=600,         # 10 minutes
        ACTIVITY_START_TO_CLOSE_TIMEOUT=120,  # 2 minutes

        # Production retry settings (more aggressive)
        RETRY_MAXIMUM_ATTEMPTS=5,
        RETRY_BACKOFF_COEFFICIENT=1.5,
        RETRY_MAXIMUM_INTERVAL=300  # 5 minutes
    )
except Exception as e:
    logger.error(f"Failed to create production config: {e}")
    raise ConfigurationError() from e
else:
    logger.info("Production configuration created")

try:
    # Development configuration
    development_config = TemporalConfig(
        HOST="localhost",
        PORT=7233,
        NAMESPACE="development",
        TASK_QUEUE="dev-queue",

        # Development timeout settings (shorter timeouts for faster feedback)
        WORKFLOW_EXECUTION_TIMEOUT=120,  # 2 minutes
        WORKFLOW_RUN_TIMEOUT=60,         # 1 minute
        ACTIVITY_START_TO_CLOSE_TIMEOUT=30,  # 30 seconds

        # Development retry settings (fewer retries for faster failures)
        RETRY_MAXIMUM_ATTEMPTS=2,
        RETRY_BACKOFF_COEFFICIENT=2.0,
        RETRY_MAXIMUM_INTERVAL=30  # 30 seconds
    )
except Exception as e:
    logger.error(f"Failed to create development config: {e}")
    raise ConfigurationError() from e
else:
    logger.info("Development configuration created")

# Select config based on environment
config = production_config if os.getenv("ENV") == "production" else development_config
temporal = TemporalAdapter(config)
```

## Using Atomic Activities

Activities can use atomic transactions for database operations:

```python
import logging

from archipy.adapters.temporal import AtomicActivity
from archipy.helpers.decorators.sqlalchemy_atomic import postgres_sqlalchemy_atomic_decorator
from archipy.models.errors import DatabaseQueryError, DatabaseConnectionError

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

from archipy.models.errors.temporal_errors import (
    TemporalError,
    WorkerConnectionError,
    WorkerShutdownError
)
from archipy.models.errors import (
    DatabaseQueryError,
    DatabaseConnectionError,
    NotFoundError
)

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
            run_timeout=120         # 2 minutes per run
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
            result = await self._execute_with_atomic("process_user_data", activity_input)
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

## Best Practices

1. **Workflow Design**: Keep workflows as coordinators - let activities handle business logic
2. **Error Handling**: Use specific error types and proper error chains with `raise ... from e`
3. **Transactions**: Use `AtomicActivity` for database operations requiring consistency
4. **Testing**: Mock adapters and activities for unit testing
5. **Configuration**: Use environment-specific configurations for different deployments
6. **Monitoring**: Leverage workflow logging and error tracking
7. **Timeouts**: Set appropriate timeouts for workflows and activities
8. **Retries**: Configure retry policies based on error types and business requirements

## See Also

- [Error Handling](../error_handling.md) - Exception handling patterns with proper chaining
- [Configuration Management](../config_management.md) - Temporal configuration setup
- [BDD Testing](../bdd_testing.md) - Testing workflow operations
- [SQLAlchemy Decorators](../helpers/decorators.md#sqlalchemy-transaction-decorators) - Atomic transaction usage
- [API Reference](../../api_reference/adapters.md) - Full Temporal adapter API documentation
