"""Implementation of steps for testing SQLAlchemy atomic transactions.

This module contains step definitions for both synchronous and asynchronous
atomic transaction scenarios.
"""

import asyncio
import importlib
import inspect
import logging
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime

from behave import given, then, when

from archipy.adapters.mysql.sqlalchemy.adapters import (
    AsyncMySQLSQLAlchemyAdapter,
    MySQLSQLAlchemyAdapter,
)
from archipy.adapters.mysql.sqlalchemy.session_manager_registry import MySQLSessionManagerRegistry
from archipy.adapters.postgres.sqlalchemy.adapters import (
    AsyncPostgresSQLAlchemyAdapter,
    PostgresSQLAlchemyAdapter,
)
from archipy.adapters.postgres.sqlalchemy.session_manager_registry import PostgresSessionManagerRegistry
from archipy.adapters.sqlite.sqlalchemy.adapters import AsyncSQLiteSQLAlchemyAdapter, SQLiteSQLAlchemyAdapter
from archipy.adapters.sqlite.sqlalchemy.session_manager_registry import SQLiteSessionManagerRegistry
from archipy.adapters.starrocks.sqlalchemy.adapters import (
    AsyncStarrocksSQLAlchemyAdapter,
    StarrocksSQLAlchemyAdapter,
)
from archipy.adapters.starrocks.sqlalchemy.session_manager_registry import StarRocksSessionManagerRegistry
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import SQLiteSQLAlchemyConfig
from archipy.adapters.base.sqlalchemy.atomic import (
    ATOMIC_BLOCK_CONFIGS,
    mysql_sqlalchemy_atomic,
    postgres_sqlalchemy_atomic,
    sqlalchemy_atomic,
    sqlite_sqlalchemy_atomic,
    starrocks_sqlalchemy_atomic,
)
from archipy.models.entities.sqlalchemy.base_entities import BaseEntity
from archipy.models.errors import DatabaseError, InternalError
from features.test_entity import RelatedTestEntity, TestAdminEntity, TestEntity, TestManagerEntity
from features.test_entity_factory import TestEntityFactory
from features.test_helpers import (
    async_schema_setup,
    async_schema_setup_autocommit,
    get_adapter,
    get_async_adapter,
    get_current_scenario_context,
    sync_schema_setup_autocommit,
)
from sqlalchemy import select


def store_entity(context, entity, key=None):
    """Store an entity in the scenario context by its UUID for later retrieval."""
    scenario_context = get_current_scenario_context(context)

    # Use class name if no key provided
    if key is None:
        key = entity.__class__.__name__.lower()

    # Store entity UUID
    uuid_str = str(entity.test_uuid)
    scenario_context.entities[uuid_str] = entity
    scenario_context.entity_ids[key] = uuid_str

    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    logger.info(f"Stored entity {key} with UUID {uuid_str}")

    return uuid_str


def get_entity_id(context, key):
    """Get an entity's UUID from the scenario context by its key."""
    scenario_context = get_current_scenario_context(context)

    if key not in scenario_context.entity_ids:
        raise AttributeError(f"No entity stored with key '{key}'")

    return scenario_context.entity_ids[key]


def _get_db_type(context) -> str:
    """Extract database type from scenario outline examples.

    Behave Scenario Outline Examples are accessible via context.active_outline
    which contains the current example row data.
    """
    # Check if we're in a Scenario Outline with active example
    if hasattr(context, "active_outline") and context.active_outline:
        # active_outline is a Row object with cells accessible by heading name
        if hasattr(context.active_outline, "cells"):
            # Try to get db_type from the example row
            for heading, cell in zip(context.active_outline.table.headings, context.active_outline.cells):
                if heading == "db_type":
                    return cell

    # Fallback: check scenario tags or default to sqlite
    if hasattr(context, "scenario") and context.scenario:
        tags = [str(tag) for tag in context.scenario.tags] if hasattr(context.scenario, "tags") else []
        if "needs-postgres" in tags:
            return "postgres"
        if "needs-mysql" in tags:
            return "mysql"
        if "needs-starrocks" in tags:
            return "starrocks"

    return "sqlite"


def _get_atomic_decorator(db_type: str, is_async: bool = False):  # noqa: ARG001
    """Get the appropriate atomic decorator for the database type.

    The decorators detect async functions themselves, so ``is_async`` only documents the call site.

    Args:
        db_type: Database type ('postgres', 'sqlite', 'mysql', or 'starrocks')
        is_async: Whether the decorated function is async

    Returns:
        The appropriate atomic decorator function
    """
    if db_type == "postgres":
        return postgres_sqlalchemy_atomic
    if db_type == "mysql":
        return mysql_sqlalchemy_atomic
    if db_type == "starrocks":
        return starrocks_sqlalchemy_atomic
    return sqlite_sqlalchemy_atomic


def _get_session_registry(db_type: str):
    """Get the appropriate session manager registry for the database type.

    Args:
        db_type: Database type ('postgres', 'sqlite', 'mysql', or 'starrocks')

    Returns:
        The appropriate session manager registry class
    """
    if db_type == "postgres":
        return PostgresSessionManagerRegistry
    if db_type == "mysql":
        return MySQLSessionManagerRegistry
    if db_type == "starrocks":
        return StarRocksSessionManagerRegistry
    return SQLiteSessionManagerRegistry


def _get_adapter_classes(db_type: str):
    """Get the appropriate adapter classes for the database type.

    Args:
        db_type: Database type ('postgres', 'sqlite', 'mysql', or 'starrocks')

    Returns:
        Tuple of (sync_adapter_class, async_adapter_class)
    """
    if db_type == "postgres":
        return PostgresSQLAlchemyAdapter, AsyncPostgresSQLAlchemyAdapter
    if db_type == "mysql":
        return MySQLSQLAlchemyAdapter, AsyncMySQLSQLAlchemyAdapter
    if db_type == "starrocks":
        return StarrocksSQLAlchemyAdapter, AsyncStarrocksSQLAlchemyAdapter
    return SQLiteSQLAlchemyAdapter, AsyncSQLiteSQLAlchemyAdapter


@given("the application database is initialized for {db_type}")
async def step_given_database_initialized(context, db_type: str):
    """Initialize the database for testing with the specified database type.

    Args:
        context: Behave context
        db_type: Database type ('postgres', 'sqlite', 'mysql', or 'starrocks')
    """
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))

    # Get the current scenario context
    scenario_context = get_current_scenario_context(context)

    # Store database type in scenario context for later use
    scenario_context.store("db_type", db_type)

    # Get the appropriate registry and adapter classes
    session_registry = _get_session_registry(db_type)
    sync_adapter_class, async_adapter_class = _get_adapter_classes(db_type)

    if db_type == "postgres":
        # Use PostgreSQL container connection details
        global_config = BaseConfig.global_config()
        postgres_config = global_config.POSTGRES_SQLALCHEMY

        logger.info(f"Creating PostgreSQL adapter with host: {postgres_config.HOST}, port: {postgres_config.PORT}")

        # Create sync adapter
        adapter = sync_adapter_class(orm_config=postgres_config)
        session_registry.set_sync_manager(adapter.session_manager)
        scenario_context.adapter = adapter

        # Set up database schema with sync adapter
        logger.info("Creating database schema with sync PostgreSQL adapter")
        BaseEntity.metadata.drop_all(adapter.session_manager.engine)
        BaseEntity.metadata.create_all(adapter.session_manager.engine)

        # For async tests, create and set up the async adapter
        if any("async" in tag.lower() for tag in context.scenario.tags):
            logger.info("Creating async PostgreSQL adapter")

            try:
                # Create async adapter with same config
                async_adapter = async_adapter_class(orm_config=postgres_config)
                session_registry.set_async_manager(async_adapter.session_manager)
                scenario_context.async_adapter = async_adapter

                # Create schema with async adapter
                logger.info("Creating database schema with async PostgreSQL adapter")
                await async_schema_setup(async_adapter)

                logger.info("Async PostgreSQL adapter and schema setup completed")
            except Exception as e:
                logger.exception(f"Error setting up async PostgreSQL adapter: {e}")

    elif db_type == "mysql":
        # Use MySQL container connection details
        global_config = BaseConfig.global_config()
        mysql_config = global_config.MYSQL_SQLALCHEMY

        logger.info(f"Creating MySQL adapter with host: {mysql_config.HOST}, port: {mysql_config.PORT}")

        # Create sync adapter
        adapter = sync_adapter_class(orm_config=mysql_config)
        session_registry.set_sync_manager(adapter.session_manager)
        scenario_context.adapter = adapter

        # Set up database schema with sync adapter
        logger.info("Creating database schema with sync MySQL adapter")
        BaseEntity.metadata.drop_all(adapter.session_manager.engine)
        BaseEntity.metadata.create_all(adapter.session_manager.engine)

        # For async tests, create and set up the async adapter
        if any("async" in tag.lower() for tag in context.scenario.tags):
            logger.info("Creating async MySQL adapter")

            try:
                # Create async adapter with same config
                async_adapter = async_adapter_class(orm_config=mysql_config)
                session_registry.set_async_manager(async_adapter.session_manager)
                scenario_context.async_adapter = async_adapter

                # Create schema with async adapter
                logger.info("Creating database schema with async MySQL adapter")
                await async_schema_setup(async_adapter)

                logger.info("Async MySQL adapter and schema setup completed")
            except Exception as e:
                logger.exception(f"Error setting up async MySQL adapter: {e}")

    elif db_type == "starrocks":
        # Use StarRocks container connection details
        global_config = BaseConfig.global_config()
        starrocks_config = global_config.STARROCKS_SQLALCHEMY

        logger.info(
            f"Creating StarRocks adapter with host: {starrocks_config.HOST}, port: {starrocks_config.PORT}",
        )

        # Create sync adapter
        adapter = sync_adapter_class(orm_config=starrocks_config)
        session_registry.set_sync_manager(adapter.session_manager)
        scenario_context.adapter = adapter

        # Set up database schema with sync adapter (DDL must use AUTOCOMMIT on StarRocks)
        logger.info("Creating database schema with sync StarRocks adapter")
        sync_schema_setup_autocommit(adapter)

        # For async tests, create and set up the async adapter
        if any("async" in tag.lower() for tag in context.scenario.tags):
            logger.info("Creating async StarRocks adapter")

            try:
                # Create async adapter with same config
                async_adapter = async_adapter_class(orm_config=starrocks_config)
                session_registry.set_async_manager(async_adapter.session_manager)
                scenario_context.async_adapter = async_adapter

                # Create schema with async adapter (AUTOCOMMIT for DDL)
                logger.info("Creating database schema with async StarRocks adapter")
                await async_schema_setup_autocommit(async_adapter)

                logger.info("Async StarRocks adapter and schema setup completed")
            except Exception as e:
                logger.exception(f"Error setting up async StarRocks adapter: {e}")

    else:  # sqlite
        # Use file-based SQLite database
        temp_dir = tempfile.gettempdir()
        scenario_id = scenario_context.scenario_id
        db_file = os.path.join(temp_dir, f"test_db_{scenario_id}.sqlite")

        # If the file already exists, try to remove it
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
                logger.info(f"Removed existing database file: {db_file}")
            except Exception as e:
                logger.exception(f"Failed to remove existing database file: {e}")
                # Generate a new unique name to avoid conflicts
                db_file = os.path.join(temp_dir, f"test_db_{uuid.uuid4().hex}.sqlite")
                logger.info(f"Using alternative database file: {db_file}")

        # Store the file path in the scenario context
        scenario_context.db_file = db_file

        logger.info(f"Creating SQLite adapter with database: {db_file}")

        # Create configuration with file-based database
        sync_config = SQLiteSQLAlchemyConfig(
            DRIVER_NAME="sqlite",
            DATABASE=db_file,
        )

        # Create adapter for tests and store in scenario context
        adapter = sync_adapter_class(orm_config=sync_config)
        session_registry.set_sync_manager(adapter.session_manager)
        scenario_context.adapter = adapter

        # Set up database schema with sync adapter
        logger.info("Creating database schema with sync SQLite adapter")
        BaseEntity.metadata.drop_all(adapter.session_manager.engine)
        BaseEntity.metadata.create_all(adapter.session_manager.engine)

        # For async tests, create and set up the async adapter
        if any("async" in tag.lower() for tag in context.scenario.tags):
            logger.info(f"Creating async SQLite adapter with database: {db_file}")

            # Create async config with the same database file
            async_config = SQLiteSQLAlchemyConfig(
                DRIVER_NAME="sqlite+aiosqlite",
                DATABASE=db_file,
            )

            try:
                # Create a new async adapter
                async_adapter = async_adapter_class(orm_config=async_config)
                session_registry.set_async_manager(async_adapter.session_manager)
                scenario_context.async_adapter = async_adapter

                # Create schema with async adapter
                logger.info("Creating database schema with async SQLite adapter")
                await async_schema_setup(async_adapter)

                logger.info("Async SQLite adapter and schema setup completed")
            except Exception as e:
                logger.exception(f"Error setting up async SQLite adapter: {e}")


@given("test entities are defined")
def step_given_test_entities_defined(context):
    """Verify that test entities are properly defined."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    logger.info("Verifying test entity definitions")

    # Verify TestEntity is properly defined
    assert hasattr(TestEntity, "test_uuid"), "TestEntity should have test_uuid property"
    assert hasattr(TestEntity, "pk_uuid"), "TestEntity should have pk_uuid property as synonym"

    # Verify entity factory works
    test_entity = TestEntityFactory.create_test_entity(description="Test Entity")
    assert test_entity is not None, "TestEntityFactory should create a TestEntity"
    assert test_entity.description == "Test Entity", "TestEntityFactory should set entity properties"

    logger.info("Test entity definitions verified")


@when("a new entity is created in an atomic transaction")
def step_when_entity_created_in_atomic(context):
    """Create a new entity within an atomic transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Generate a UUID for the entity
    test_uuid = uuid.uuid4()

    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def create_entity_atomic():
        """Create a new entity within an atomic block."""
        logger.info(f"Creating entity with UUID {test_uuid}")

        entity = TestEntityFactory.create_test_entity(
            test_uuid=test_uuid,
            description="Entity created in atomic transaction",
        )

        # Use the scenario-specific adapter
        adapter = get_adapter(context)
        adapter.create(entity)

        # Store the entity in the scenario context
        store_entity(context, entity, "test_entity")

        return entity

    # Execute the atomic operation
    create_entity_atomic()
    logger.info("Entity created successfully")


@then("the entity should be retrievable")
def step_then_entity_should_be_retrievable(context):
    """Verify the entity exists after atomic transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Get the entity's UUID from scenario context
    entity_uuid = uuid.UUID(get_entity_id(context, "test_entity"))
    logger.info(f"Retrieving entity with UUID {entity_uuid}")

    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def get_entity():
        # Get the adapter from scenario context
        adapter = get_adapter(context)
        session = adapter.get_session()

        retrieved_entity = session.get(TestEntity, entity_uuid)
        assert retrieved_entity is not None, "Entity not found in database after atomic transaction"
        assert retrieved_entity.description == "Entity created in atomic transaction", (
            "Entity has incorrect description"
        )
        logger.info("Entity retrieved successfully")
        return retrieved_entity

    get_entity()


@when("a new entity creation fails within an atomic transaction")
def step_when_entity_creation_fails_in_atomic(context):
    """Attempt to create an entity with a failure that causes rollback."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Generate a UUID for the entity
    test_uuid = uuid.uuid4()
    scenario_context.rolled_back_uuid = test_uuid
    logger.info(f"Attempting to create entity with UUID {test_uuid} (will fail)")

    try:
        atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

        @atomic_decorator
        def create_entity_with_failure():
            """Create an entity but raise an exception to trigger rollback."""
            entity = TestEntityFactory.create_test_entity(
                test_uuid=test_uuid,
                description="Entity that should be rolled back",
            )
            # Get the adapter from scenario context
            adapter = get_adapter(context)
            adapter.create(entity)

            # Store the UUID for verification
            scenario_context.entity_ids["failed_entity"] = str(test_uuid)

            # Simulate failure
            logger.info("Raising exception to trigger rollback")
            raise ValueError("Simulated failure for testing atomic rollback")

        create_entity_with_failure()
    except Exception as e:
        # We expect this exception
        logger.info(f"Expected exception caught: {type(e).__name__} - {str(e)}")
        print(f"DEBUG: Caught exception type: {type(e).__name__}, message: {str(e)}")
        # Store the exception to verify it later
        scenario_context.store("failed_transaction_exception", e)
    else:
        assert False, "Exception was not raised as expected"


@then("no entity should exist in the database")
def step_then_no_entity_should_exist(context):
    """Verify the entity doesn't exist after failed atomic transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Get a fresh session to verify rollback
    get_adapter(context)
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def check_entity_absence():
        adapter = get_adapter(context)
        session = adapter.get_session()
        retrieved_entity = session.get(TestEntity, scenario_context.rolled_back_uuid)
        assert retrieved_entity is None, "Entity found in database after failed atomic transaction"
        logger.info("Verified entity doesn't exist (rollback successful)")
        return retrieved_entity

    check_entity_absence()


@then("the database session should remain usable")
def step_then_session_should_remain_usable(context):
    """Verify the session is still usable after a failed transaction."""
    logger = context.__dict__.get("logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")
    logger.info("Verifying session is still usable after rollback")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def verify_session_usable():
        # Create a new entity to test the session is still working
        test_uuid = uuid.uuid4()
        logger.info(f"Creating test entity with UUID {test_uuid}")

        # Create a new entity with the fresh session
        entity = TestEntityFactory.create_test_entity(
            test_uuid=test_uuid,
            description="Entity to test session usability",
        )
        adapter = get_adapter(context)
        adapter.create(entity)

        # Try to retrieve it to confirm session is working
        session = adapter.get_session()
        retrieved_entity = session.get(TestEntity, test_uuid)
        assert retrieved_entity is not None, "Session is not usable after error handling"
        assert retrieved_entity.description == "Entity to test session usability", "Entity data mismatch"

        logger.info("Session verified as usable after rollback")
        return True

    # Execute the function and verify the result
    result = verify_session_usable()
    assert result, "Session is not usable after transaction rollback"


@when("I inspect callables of the {db_type} SQLAlchemy session manager module")
def step_when_inspect_session_manager_module_callables(context, db_type):
    scenario_context = get_current_scenario_context(context)
    module = importlib.import_module(f"archipy.adapters.{db_type}.sqlalchemy.session_managers")
    failures: list[str] = []
    for name, obj in vars(module).items():
        members = vars(obj).items() if isinstance(obj, type) else [(None, obj)]
        for member_name, member in members:
            func = member.__func__ if isinstance(member, (staticmethod, classmethod)) else member
            if not inspect.isfunction(func):
                continue
            label = name if member_name is None else f"{name}.{member_name}"
            try:
                inspect.signature(func)
            except NameError as e:
                failures.append(f"{label}: {e}")
    scenario_context.store("session_manager_inspect_failures", failures)


@then("all session manager callable signatures resolve without NameError")
def step_then_session_manager_signatures_resolve(context):
    scenario_context = get_current_scenario_context(context)
    failures = scenario_context.get("session_manager_inspect_failures")
    assert not failures, "Session manager annotation inspection failed:\n" + "\n".join(failures)


_SQLITE_QUERY_SCRIPT = """
import asyncio, sys
from sqlalchemy import text
from archipy.adapters.sqlite.sqlalchemy.adapters import AsyncSQLiteSQLAlchemyAdapter, SQLiteSQLAlchemyAdapter
from archipy.configs.config_template import SQLiteSQLAlchemyConfig
mode, driver, database = sys.argv[1:]
config = SQLiteSQLAlchemyConfig(DRIVER_NAME=driver, DATABASE=database)
if mode == "sync":
    result = SQLiteSQLAlchemyAdapter(config).execute(text("SELECT 1")).scalar()
else:
    result = asyncio.run(AsyncSQLiteSQLAlchemyAdapter(config).execute(text("SELECT 1"))).scalar()
print(result)
"""


@when("I import the {db_type} SQLAlchemy session manager module in a fresh interpreter")
def step_when_import_session_manager_module_fresh(context, db_type):
    scenario_context = get_current_scenario_context(context)
    script = (
        f"import sys, archipy.adapters.{db_type}.sqlalchemy.session_managers; "
        "print('sqlalchemy.ext.asyncio' in sys.modules)"
    )
    completed = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)
    scenario_context.store("fresh_import_result", completed)


@then("sqlalchemy.ext.asyncio should not be loaded")
def step_then_asyncio_extension_not_loaded(context):
    scenario_context = get_current_scenario_context(context)
    completed = scenario_context.get("fresh_import_result")
    assert completed.returncode == 0, f"Import failed:\n{completed.stderr}"
    assert completed.stdout.strip() == "False", "sqlalchemy.ext.asyncio was imported on the sync path"


@when('a {mode} SQLite adapter runs a query with driver "{driver}" on database "{database}"')
def step_when_sqlite_adapter_runs_query(context, mode, driver, database):
    scenario_context = get_current_scenario_context(context)
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = database if database == ":memory:" else os.path.join(temp_dir, "driver_check.sqlite")
        # Session managers are singletons, so each configuration runs in its own interpreter.
        completed = subprocess.run(
            [sys.executable, "-c", _SQLITE_QUERY_SCRIPT, mode, driver, db_path],
            capture_output=True,
            text=True,
            check=False,
        )
    scenario_context.store("sqlite_query_result", completed)


@then("the SQLite query should return 1")
def step_then_sqlite_query_returns_one(context):
    scenario_context = get_current_scenario_context(context)
    completed = scenario_context.get("sqlite_query_result")
    assert completed.returncode == 0, f"SQLite query failed:\n{completed.stderr}"
    assert completed.stdout.strip().splitlines()[-1] == "1"


@when("nested atomic transactions are attempted on StarRocks")
def step_when_nested_atomic_attempted_on_starrocks(context):
    """Attempt nested StarRocks atomic blocks and capture the limitation error."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    atomic_decorator = _get_atomic_decorator("starrocks", is_async=False)

    try:

        @atomic_decorator
        def outer_atomic():
            adapter = get_adapter(context)
            outer_entity = TestEntityFactory.create_test_entity(
                description="Outer entity for StarRocks nested limitation",
            )
            adapter.create(outer_entity)

            @atomic_decorator
            def inner_atomic():
                adapter = get_adapter(context)
                inner_entity = TestEntityFactory.create_test_entity(
                    description="Inner entity for StarRocks nested limitation",
                )
                adapter.create(inner_entity)
                return inner_entity

            return inner_atomic()

        outer_atomic()
    except Exception as e:
        logger.info(f"Caught expected StarRocks nested limitation: {type(e).__name__}")
        scenario_context.store("starrocks_limitation_exception", e)
    else:
        assert False, "Nested StarRocks atomic transactions should raise a limitation error"


@when("multiple inserts into the same table are attempted in one StarRocks transaction")
def step_when_multiple_same_table_inserts_on_starrocks(context):
    """Attempt multiple same-table inserts in one StarRocks transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    atomic_decorator = _get_atomic_decorator("starrocks", is_async=False)

    try:

        @atomic_decorator
        def create_multiple_same_table():
            adapter = get_adapter(context)
            for index in range(2):
                entity = TestEntityFactory.create_test_entity(
                    description=f"StarRocks multi-insert entity {index + 1}",
                )
                adapter.create(entity)

        create_multiple_same_table()
    except Exception as e:
        logger.info(f"Caught expected StarRocks multi-insert limitation: {type(e).__name__}")
        scenario_context.store("starrocks_limitation_exception", e)
    else:
        assert False, "Multiple same-table inserts in one StarRocks transaction should fail"


@when("an insert after update on the same table is attempted in one StarRocks transaction")
def step_when_insert_after_update_on_starrocks(context):
    """Attempt UPDATE then INSERT on the same table in one StarRocks transaction.

    StarRocks forbids further DML against a table already modified earlier in the
    same SQL transaction (error 5303).
    """
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    atomic_decorator = _get_atomic_decorator("starrocks", is_async=False)

    # Seed entity in its own committed transaction first
    seed_uuid = uuid.uuid4()

    @atomic_decorator
    def seed_entity():
        adapter = get_adapter(context)
        entity = TestEntityFactory.create_test_entity(
            test_uuid=seed_uuid,
            description="StarRocks entity before update-then-insert",
        )
        adapter.create(entity)
        return entity

    seed_entity()
    scenario_context.entity_ids["starrocks_update_entity"] = str(seed_uuid)

    try:

        @atomic_decorator
        def update_then_insert():
            adapter = get_adapter(context)
            session = adapter.get_session()
            entity = session.get(TestEntity, seed_uuid)
            assert entity is not None, "Seed entity missing before StarRocks update-then-insert"
            entity.description = "Updated on StarRocks"
            entity.updated_at = datetime.now()
            session.flush()

            follow_up = TestEntityFactory.create_test_entity(
                description="Insert after update on same StarRocks table",
            )
            adapter.create(follow_up)

        update_then_insert()
    except Exception as e:
        logger.info(f"Caught expected StarRocks update-then-insert limitation: {type(e).__name__}")
        scenario_context.store("starrocks_limitation_exception", e)
    else:
        assert False, "INSERT after UPDATE on the same StarRocks table in one transaction should fail"


@then("a StarRocks transaction limitation error should be raised")
def step_then_starrocks_limitation_error_raised(context):
    """Verify StarRocks rejected an unsupported transactional operation."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)

    exception = scenario_context.get("starrocks_limitation_exception")
    assert exception is not None, "Expected a StarRocks transaction limitation error"
    assert isinstance(
        exception,
        DatabaseError | InternalError,
    ), f"Unexpected limitation error type: {type(exception)}"
    logger.info(f"Verified StarRocks limitation error: {type(exception).__name__}")


@when("nested atomic transactions are executed")
def step_when_nested_atomic_executed(context):
    """Test nested atomic transactions, both successful and failing."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Create test UUIDs
    outer_uuid = uuid.uuid4()
    inner_uuid = uuid.uuid4()
    failing_uuid = uuid.uuid4()

    # Store UUIDs for verification
    scenario_context.entity_ids["outer_entity"] = str(outer_uuid)
    scenario_context.entity_ids["inner_entity"] = str(inner_uuid)
    scenario_context.entity_ids["failing_entity"] = str(failing_uuid)

    # Test nesting of atomic blocks
    logger.info("Testing nested atomic transactions")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)
    try:

        @atomic_decorator
        def outer_atomic():
            """Execute the outermost atomic block."""
            logger.info(f"Creating outer entity with UUID {outer_uuid}")

            # Create the outer entity
            adapter = get_adapter(context)
            outer_entity = TestEntityFactory.create_test_entity(
                test_uuid=outer_uuid,
                description="Outer entity from nested transaction",
            )
            adapter.create(outer_entity)

            try:

                @atomic_decorator
                def inner_atomic():
                    """Execute a successful inner atomic block."""
                    logger.info(f"Creating inner entity with UUID {inner_uuid}")

                    # Create the inner entity (should succeed)
                    adapter = get_adapter(context)
                    inner_entity = TestEntityFactory.create_test_entity(
                        test_uuid=inner_uuid,
                        description="Inner entity from nested transaction",
                    )
                    adapter.create(inner_entity)
                    return inner_entity

                inner_entity = inner_atomic()
                logger.info(f"Successfully created inner entity: {inner_entity}")

                # Now test a failing inner transaction
                try:

                    @atomic_decorator
                    def failing_inner_atomic():
                        """Execute a failing inner atomic block."""
                        logger.info(f"Creating entity with UUID {failing_uuid} (will fail)")

                        # Create entity that should be rolled back
                        adapter = get_adapter(context)
                        failing_entity = TestEntityFactory.create_test_entity(
                            test_uuid=failing_uuid,
                            description="Entity from failing nested transaction",
                        )
                        adapter.create(failing_entity)

                        # Simulate failure
                        logger.info("Raising exception to trigger rollback in nested transaction")
                        raise ValueError("Simulated failure in nested transaction")

                    failing_inner_atomic()
                except Exception as e:
                    # We expect this exception
                    logger.info(f"Expected exception caught in inner block: {type(e).__name__} - {str(e)}")
                    print(f"DEBUG: Caught inner exception type: {type(e).__name__}, message: {str(e)}")
                    # Store the exception to verify it later
                    scenario_context.store("failed_inner_exception", e)

                return outer_entity

            except Exception as e:
                logger.error(f"Unexpected error in outer block: {str(e)}")
                raise

        # Execute the transaction
        outer_entity = outer_atomic()
        logger.info(f"Successfully completed nested transactions, with outer entity: {outer_entity}")

    except Exception as e:
        logger.error(f"Unexpected error in nested transaction test: {str(e)}")
        print(f"DEBUG: Unexpected outer exception: {type(e).__name__}, message: {str(e)}")
        raise


@then("operations from successful nested transactions should be visible within outer transaction")
def step_then_successful_nested_visible(context):
    """Verify that entities from successful nested transactions are visible within the outer transaction.

    Note: When a failing inner transaction causes a rollback, it cascades to the outer transaction,
    so all entities (including successful inner and outer) are rolled back.
    """
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Get UUIDs for verification
    entity1_uuid = uuid.UUID(scenario_context.entity_ids["outer_entity"])
    entity2_uuid = uuid.UUID(scenario_context.entity_ids["inner_entity"])

    logger.info("Verifying nested transaction entities after cascading rollback")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def verify_nested_results():
        adapter = get_adapter(context)
        session = adapter.get_session()

        # When a failing inner transaction causes a rollback, it cascades to the outer transaction
        # So all entities (including successful inner and outer) should be rolled back
        # Check entity 1 (outer atomic) - should NOT be visible due to cascading rollback
        entity1 = session.get(TestEntity, entity1_uuid)
        assert entity1 is None, "Entity 1 (outer) found after cascading rollback from failed inner transaction"

        # Check entity 2 (successful inner atomic) - should NOT be visible due to cascading rollback
        entity2 = session.get(TestEntity, entity2_uuid)
        assert entity2 is None, "Entity 2 (inner) found after cascading rollback from failed inner transaction"
        logger.info("Verified that all entities were rolled back due to cascading failure")

        return True

    verify_nested_results()


@then("operations from failed nested transactions should be rolled back")
def step_then_failed_nested_rolled_back(context):
    """Verify that entities from failed nested transactions don't exist."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Get UUID for verification
    entity3_uuid = uuid.UUID(scenario_context.entity_ids["failing_entity"])
    logger.info(f"Verifying entity 3 with UUID {entity3_uuid} doesn't exist")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def verify_rollback():
        adapter = get_adapter(context)
        session = adapter.get_session()

        # Check entity 3 (failed inner atomic) - should not exist
        entity3 = session.get(TestEntity, entity3_uuid)
        assert entity3 is None, "Entity 3 found after failed inner atomic transaction"
        logger.info("Verified entity 3 doesn't exist (rollback successful)")

        return True

    verify_rollback()


@given("an entity exists in the database")
def step_given_entity_exists(context):
    """Create an entity in the database for testing updates."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Generate a UUID for the entity
    test_uuid = uuid.uuid4()
    logger.info(f"Creating existing entity with UUID {test_uuid}")
    adapter = get_adapter(context)
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def create_entity():
        entity = TestEntityFactory.create_test_entity(test_uuid=test_uuid, description="Original Description")
        # Capture attrs before create: StarRocks forbids SELECT after DML in same txn,
        # and expired ORM attrs would lazy-load after insert.
        original_description = entity.description
        original_updated_at = getattr(entity, "updated_at", None)
        adapter.create(entity)

        # Store the entity for later retrieval
        store_entity(context, entity, "existing_entity")
        scenario_context.store("original_description", original_description)
        scenario_context.store("original_updated_at", original_updated_at)

    create_entity()
    logger.info("Entity created successfully")


@when("the entity is updated within an atomic transaction")
def step_when_entity_updated_in_atomic(context):
    """Update an entity within an atomic transaction."""
    logger = context.__dict__.get("logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Get the entity UUID from context
    entity_uuid = uuid.UUID(scenario_context.entity_ids.get("existing_entity"))
    logger.info(f"Updating entity with UUID {entity_uuid}")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def update_entity():
        adapter = get_adapter(context)
        session = adapter.get_session()
        entity = session.get(TestEntity, entity_uuid)

        # Verify we got the entity before updating
        if entity is None:
            logger.exception(f"Entity with UUID {entity_uuid} not found for update")
            assert False, f"Entity with UUID {entity_uuid} not found for update"

        # Store the original description for verification
        scenario_context.store("original_description", entity.description)
        scenario_context.store("original_updated_at", getattr(entity, "updated_at", None))

        # Update properties
        entity.description = "Updated Description"
        time.sleep(1)
        entity.updated_at = datetime.now()
        entity.is_deleted = True

        # Store the updated entity's values for verification
        scenario_context.store("updated_description", entity.description)
        scenario_context.store("updated_at", entity.updated_at)
        scenario_context.store("is_deleted", entity.is_deleted)

        return entity

    update_entity()
    logger.info("Entity properties updated")


@then("the entity properties should reflect the updates")
def step_then_entity_properties_reflect_updates(context):
    """Verify entity properties are updated correctly."""
    logger = context.__dict__.get("logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Get the entity UUID from context
    entity_uuid = uuid.UUID(scenario_context.entity_ids.get("existing_entity"))
    logger.info(f"Verifying updates for entity with UUID {entity_uuid}")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def verify_entity_updates():
        adapter = get_adapter(context)
        session = adapter.get_session()
        entity = session.get(TestEntity, entity_uuid)

        # Debug log to help troubleshoot
        if entity is None:
            logger.exception(f"Entity with UUID {entity_uuid} not found during verification")
            # List all entities in the database for debugging
            all_entities = session.query(TestEntity).all()
            logger.exception(f"Found {len(all_entities)} entities in database")
            for e in all_entities:
                logger.exception(f"  Entity UUID: {e.test_uuid}, Description: {e.description}")

        # Verify updates
        assert entity is not None, "Updated entity not found"

        # Compare with stored values instead of hardcoded values
        assert entity.description == scenario_context.get(
            "updated_description",
            "Updated Description",
        ), f"Description mismatch. Expected: {scenario_context.get('updated_description')}, Got: {entity.description}"
        assert entity.description != scenario_context.get("original_description", ""), "Description unchanged"
        assert entity.is_deleted is True, "is_deleted flag not updated"

        # Verify updated_at was changed
        original_updated_at = scenario_context.get("original_updated_at")
        if original_updated_at:
            assert entity.updated_at != original_updated_at, "updated_at timestamp unchanged"
        else:
            assert entity.updated_at is not None, "updated_at timestamp not set"

        logger.info("Entity updates verified successfully")
        return True

    verify_entity_updates()


@when("an entity with relationships is created in an atomic transaction")
def step_when_entity_with_relationships_created(context):
    """Create an entity with relationships in an atomic transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Generate UUIDs for the entities
    main_uuid = uuid.uuid4()
    related_uuids = [uuid.uuid4() for _ in range(3)]

    # Store UUIDs in context for later retrieval
    scenario_context.entity_ids["main_entity"] = str(main_uuid)
    for i, uuid_val in enumerate(related_uuids):
        scenario_context.entity_ids[f"related_entity_{i}"] = str(uuid_val)

    logger.info(f"Creating entity with relationships, main UUID: {main_uuid}")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def create_entity_with_relationships():
        # Create main entity directly to avoid StaleDataError
        main_entity = TestEntityFactory.create_test_entity(
            test_uuid=main_uuid,
            description="Main Entity with Relationships",
        )
        adapter = get_adapter(context)
        adapter.create(main_entity)

        # Create related entities with explicit parent_id
        for i, related_uuid in enumerate(related_uuids):
            logger.info(f"Creating related entity {i} with UUID {related_uuid}")
            related_entity = TestEntityFactory.create_related_test_entity(
                related_uuid=related_uuid,
                name=f"Related Entity {i + 1}",
                parent_id=main_uuid,
                value=f"Value {i + 1}",
            )
            adapter.create(related_entity)

        return main_entity

    create_entity_with_relationships()
    logger.info("Entity with relationships created successfully")


@then("the entity and its relationships should be retrievable")
def step_then_entity_and_relationships_retrievable(context):
    """Verify the entity and its relationships can be retrieved."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Get the UUIDs from context
    main_uuid = uuid.UUID(get_entity_id(context, "main_entity"))
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def verify_entity_relationships():
        adapter = get_adapter(context)
        session = adapter.get_session()

        # Get the main entity
        main_entity = session.get(TestEntity, main_uuid)
        assert main_entity is not None, "Main entity not found"
        logger.info(f"Main entity retrieved with UUID {main_uuid}")

        # Query for related entities (order by name for cross-DB determinism)
        related_query = (
            select(RelatedTestEntity).where(RelatedTestEntity.parent_id == main_uuid).order_by(RelatedTestEntity.name)
        )
        related_entities = session.execute(related_query).scalars().all()

        # Verify we have the expected number of related entities
        assert len(related_entities) == 3, f"Expected 3 related entities, found {len(related_entities)}"
        logger.info(f"Found {len(related_entities)} related entities")

        # Verify relationships through ORM
        for i, related in enumerate(related_entities):
            assert related.parent_id == main_uuid, "Related entity has wrong parent_id"
            assert related.name == f"Related Entity {i + 1}", f"Related entity {i} has wrong name"
            logger.info(f"Verified related entity with UUID {related.related_uuid}")

        return True

    verify_entity_relationships()


@when("different types of entities are created in an atomic transaction")
def step_when_different_entities_created_in_atomic(context):
    """Create different types of entities within an atomic transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Generate UUIDs for the entities
    regular_uuid = uuid.uuid4()
    manager_uuid = uuid.uuid4()
    admin_uuid = uuid.uuid4()

    # Store UUIDs in context for later retrieval
    scenario_context.entity_ids["regular_entity"] = str(regular_uuid)
    scenario_context.entity_ids["manager_entity"] = str(manager_uuid)
    scenario_context.entity_ids["admin_entity"] = str(admin_uuid)

    logger.info("Creating different types of entities")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def create_multiple_entity_types():
        # Create a regular test entity
        logger.info(f"Creating regular entity with UUID {regular_uuid}")
        regular_entity = TestEntityFactory.create_test_entity(test_uuid=regular_uuid, description="Regular Test Entity")
        adapter = get_adapter(context)
        adapter.create(regular_entity)

        # Create a manager test entity
        logger.info(f"Creating manager entity with UUID {manager_uuid}")
        manager_entity = TestEntityFactory.create_test_manager_entity(
            test_uuid=manager_uuid,
            description="Manager Test Entity",
        )
        adapter.create(manager_entity)

        # Create an admin test entity
        logger.info(f"Creating admin entity with UUID {admin_uuid}")
        admin_entity = TestEntityFactory.create_test_admin_entity(test_uuid=admin_uuid, description="Admin Test Entity")
        adapter.create(admin_entity)

        return regular_entity, manager_entity, admin_entity

    create_multiple_entity_types()
    logger.info("Different entity types created successfully")


@then("all entity types should be retrievable")
def step_then_all_entity_types_retrievable(context):
    """Verify all different entity types can be retrieved."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Get the UUIDs from context
    regular_uuid = uuid.UUID(get_entity_id(context, "regular_entity"))
    manager_uuid = uuid.UUID(get_entity_id(context, "manager_entity"))
    admin_uuid = uuid.UUID(get_entity_id(context, "admin_entity"))
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def verify_entity_types():
        adapter = get_adapter(context)
        session = adapter.get_session()

        # Verify regular entity
        logger.info(f"Verifying regular entity with UUID {regular_uuid}")
        regular = session.get(TestEntity, regular_uuid)
        assert regular is not None, "Regular entity not found"
        assert regular.description == "Regular Test Entity", "Regular entity has wrong description"

        # Verify manager entity
        logger.info(f"Verifying manager entity with UUID {manager_uuid}")
        manager = session.get(TestManagerEntity, manager_uuid)
        assert manager is not None, "Manager entity not found"
        assert manager.description == "Manager Test Entity", "Manager entity has wrong description"
        assert manager.created_by_uuid is not None, "Manager entity missing created_by_uuid"

        # Verify admin entity
        logger.info(f"Verifying admin entity with UUID {admin_uuid}")
        admin = session.get(TestAdminEntity, admin_uuid)
        assert admin is not None, "Admin entity not found"
        assert admin.description == "Admin Test Entity", "Admin entity has wrong description"
        assert admin.created_by_admin_uuid is not None, "Admin entity missing created_by_admin_uuid"

        logger.info("All entity types verified successfully")
        return True

    verify_entity_types()


@when("an error is triggered within an atomic transaction")
def step_when_error_triggered_in_atomic(context):
    """Trigger different types of errors within atomic transactions to test handlers."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")
    adapter = get_adapter(context)
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    # Test normal exception handling
    logger.info("Testing normal exception handling")
    try:

        @atomic_decorator
        def normal_exception():
            entity = TestEntityFactory.create_test_entity()
            adapter.create(entity)
            logger.info("Raising normal exception")
            raise ValueError("Normal exception test")

        normal_exception()
    except Exception as e:
        scenario_context.store("normal_exception", e)
        logger.info(f"Caught normal exception: {type(e).__name__}")

    # Test deadlock handling (simulated for both databases)
    logger.info("Testing deadlock exception handling")
    try:

        @atomic_decorator
        def deadlock_exception():
            entity = TestEntityFactory.create_test_entity()
            adapter.create(entity)

            # Simulate database deadlock
            from sqlalchemy.exc import OperationalError

            logger.info("Raising database deadlock exception")
            raise OperationalError("database is locked", None, None)

        deadlock_exception()
    except Exception as e:
        scenario_context.store("deadlock_exception", e)
        logger.info(f"Caught deadlock exception: {type(e).__name__}")


@then("the appropriate error should be raised")
def step_then_appropriate_error_raised(context):
    """Verify that appropriate errors were raised for each case."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)

    from archipy.models.errors import DatabaseDeadlockError, InternalError

    # Check normal exception was wrapped as InternalError
    logger.info("Verifying normal exception handling")
    normal_exception = scenario_context.get("normal_exception")
    assert normal_exception is not None, "Normal exception was not captured"
    assert isinstance(
        normal_exception,
        InternalError,
    ), f"Normal exception not wrapped as InternalError: {type(normal_exception)}"

    # Check deadlock exception
    logger.info("Verifying deadlock exception handling")
    deadlock_exception = scenario_context.get("deadlock_exception")
    assert deadlock_exception is not None, "Deadlock exception was not captured"
    assert isinstance(
        deadlock_exception,
        DatabaseDeadlockError,
    ), f"Deadlock failure not handled correctly: {type(deadlock_exception)}"

    logger.info("All exception handling verified successfully")


@then("the transaction should be rolled back")
def step_then_transaction_rolled_back(context):
    """Verify that the transaction was rolled back after errors."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")
    logger.info("Verifying session is still usable after rollback")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def verify_session_usable():
        # Create a new entity to test the session is still working
        test_uuid = uuid.uuid4()
        logger.info(f"Creating test entity with UUID {test_uuid}")

        entity = TestEntityFactory.create_test_entity(test_uuid=test_uuid, description="Entity to verify rollback")
        adapter = get_adapter(context)
        adapter.create(entity)

        # Try to retrieve it
        session = adapter.get_session()
        retrieved_entity = session.get(TestEntity, test_uuid)
        assert retrieved_entity is not None, "Session is not usable after error handling"

        logger.info("Session verified as usable after rollback")
        return True

    assert verify_session_usable(), "Session is not usable after transaction rollback"


@when("operations are performed across multiple atomic blocks")
def step_when_operations_across_multiple_atomics(context):
    """Test session consistency across multiple atomic blocks."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")
    logger.info("Testing operations across multiple atomic blocks")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    # Generate UUIDs for entities
    entity_uuids = [uuid.uuid4() for _ in range(3)]

    # Store UUIDs in context
    for i, uuid_val in enumerate(entity_uuids):
        scenario_context.entity_ids[f"multi_entity_{i}"] = str(uuid_val)

    # Create initial entities
    @atomic_decorator
    def create_initial_entities():
        logger.info("Creating initial entities in first atomic block")
        entities = []
        for i, uuid_val in enumerate(entity_uuids):
            logger.info(f"Creating entity {i} with UUID {uuid_val}")
            entity = TestEntityFactory.create_test_entity(test_uuid=uuid_val, description=f"Initial Entity {i + 1}")
            adapter = get_adapter(context)
            adapter.create(entity)
            entities.append(entity)

        return entities

    create_initial_entities()

    # Update entities in a separate atomic block
    @atomic_decorator
    def update_entities():
        logger.info("Updating entities in second atomic block")
        adapter = get_adapter(context)
        session = adapter.get_session()

        # Update each entity with a new description
        for i, uuid_val in enumerate(entity_uuids):
            logger.info(f"Updating entity {i} with UUID {uuid_val}")
            db_entity = session.get(TestEntity, uuid_val)
            db_entity.description = f"Updated Entity {i + 1}"
            db_entity.updated_at = datetime.now()

        # No explicit commit - handled by atomic decorator
        return True

    update_entities()

    # Query entities in another atomic block
    @atomic_decorator
    def query_entities():
        logger.info("Querying entities in third atomic block")
        adapter = get_adapter(context)
        session = adapter.get_session()

        # Store results for verification
        results = []
        for i, uuid_val in enumerate(entity_uuids):
            logger.info(f"Querying entity {i} with UUID {uuid_val}")
            db_entity = session.get(TestEntity, uuid_val)
            results.append({"uuid": uuid_val, "description": db_entity.description, "updated_at": db_entity.updated_at})

        scenario_context.store("query_results", results)
        return results

    query_entities()
    logger.info("Operations across multiple atomic blocks completed")


@then("session should maintain consistency across atomic blocks")
def step_then_session_maintains_consistency(context):
    """Verify session consistency is maintained across multiple atomic blocks."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")
    logger.info("Verifying session consistency across multiple atomic blocks")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=False)

    @atomic_decorator
    def verify_consistency():
        adapter = get_adapter(context)
        session = adapter.get_session()

        # Retrieve query results from scenario context
        query_results = scenario_context.get("query_results")

        # Check that each entity has the updated description
        for i, result in enumerate(query_results):
            logger.info(f"Verifying entity {i} with UUID {result['uuid']}")

            expected_description = f"Updated Entity {i + 1}"
            assert result["description"] == expected_description, (
                f"Entity {i + 1} has wrong description: {result['description']}"
            )
            assert result["updated_at"] is not None, f"Entity {i + 1} missing updated_at timestamp"

            # Verify the entity in the database matches our context
            db_entity = session.get(TestEntity, result["uuid"])
            assert db_entity is not None, f"Entity {i + 1} not found in database"
            assert db_entity.description == expected_description, (
                f"Database entity {i + 1} has wrong description: {db_entity.description}"
            )

            logger.info(f"Entity {i} verified successfully")

        logger.info("Session consistency verified successfully")
        return True

    assert verify_consistency(), "Session consistency verification failed"


@given("an async entity exists in the database")
async def step_given_async_entity_exists(context):
    """Create an entity asynchronously for update scenarios."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    test_uuid = uuid.uuid4()
    logger.info(f"Creating existing async entity with UUID {test_uuid}")
    async_adapter = get_async_adapter(context)
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    @atomic_decorator
    async def create_entity():
        entity = TestEntityFactory.create_test_entity(test_uuid=test_uuid, description="Original Description")
        # Capture attrs before create: StarRocks forbids SELECT after DML in same txn.
        original_description = entity.description
        original_updated_at = getattr(entity, "updated_at", None)
        await async_adapter.create(entity)
        store_entity(context, entity, "existing_entity")
        scenario_context.store("original_description", original_description)
        scenario_context.store("original_updated_at", original_updated_at)

    await create_entity()
    logger.info("Async entity created successfully")


@when("the entity is updated within an async atomic transaction")
async def step_when_entity_updated_in_async_atomic(context):
    """Update an entity within an async atomic transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    entity_uuid = uuid.UUID(scenario_context.entity_ids.get("existing_entity"))
    logger.info(f"Updating async entity with UUID {entity_uuid}")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    @atomic_decorator
    async def update_entity():
        async_adapter = get_async_adapter(context)
        session = async_adapter.session_manager.get_session()
        entity = await session.get(TestEntity, entity_uuid)
        if entity is None:
            logger.exception(f"Entity with UUID {entity_uuid} not found for async update")
            assert False, f"Entity with UUID {entity_uuid} not found for async update"

        scenario_context.store("original_description", entity.description)
        scenario_context.store("original_updated_at", getattr(entity, "updated_at", None))

        entity.description = "Updated Description"
        await asyncio.sleep(1)
        entity.updated_at = datetime.now()
        entity.is_deleted = True

        scenario_context.store("updated_description", entity.description)
        scenario_context.store("updated_at", entity.updated_at)
        scenario_context.store("is_deleted", entity.is_deleted)
        return entity

    await update_entity()
    logger.info("Async entity properties updated")


@then("the async entity properties should reflect the updates")
async def step_then_async_entity_properties_reflect_updates(context):
    """Verify async entity properties are updated correctly."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    entity_uuid = uuid.UUID(scenario_context.entity_ids.get("existing_entity"))
    logger.info(f"Verifying async updates for entity with UUID {entity_uuid}")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    @atomic_decorator
    async def verify_entity_updates():
        async_adapter = get_async_adapter(context)
        session = async_adapter.session_manager.get_session()
        entity = await session.get(TestEntity, entity_uuid)
        assert entity is not None, "Updated async entity not found"
        assert entity.description == scenario_context.get(
            "updated_description",
            "Updated Description",
        ), f"Description mismatch. Expected: {scenario_context.get('updated_description')}, Got: {entity.description}"
        assert entity.description != scenario_context.get("original_description", ""), "Description unchanged"
        assert entity.is_deleted is True, "is_deleted flag not updated"

        original_updated_at = scenario_context.get("original_updated_at")
        if original_updated_at:
            assert entity.updated_at != original_updated_at, "updated_at timestamp unchanged"
        else:
            assert entity.updated_at is not None, "updated_at timestamp not set"

        logger.info("Async entity updates verified successfully")
        return True

    await verify_entity_updates()


@when("different types of entities are created in an async atomic transaction")
async def step_when_different_entities_created_in_async_atomic(context):
    """Create different types of entities within an async atomic transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    regular_uuid = uuid.uuid4()
    manager_uuid = uuid.uuid4()
    admin_uuid = uuid.uuid4()
    scenario_context.entity_ids["regular_entity"] = str(regular_uuid)
    scenario_context.entity_ids["manager_entity"] = str(manager_uuid)
    scenario_context.entity_ids["admin_entity"] = str(admin_uuid)

    logger.info("Creating different types of entities asynchronously")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    @atomic_decorator
    async def create_multiple_entity_types():
        async_adapter = get_async_adapter(context)
        logger.info(f"Creating regular async entity with UUID {regular_uuid}")
        regular_entity = TestEntityFactory.create_test_entity(test_uuid=regular_uuid, description="Regular Test Entity")
        await async_adapter.create(regular_entity)

        logger.info(f"Creating manager async entity with UUID {manager_uuid}")
        manager_entity = TestEntityFactory.create_test_manager_entity(
            test_uuid=manager_uuid,
            description="Manager Test Entity",
        )
        await async_adapter.create(manager_entity)

        logger.info(f"Creating admin async entity with UUID {admin_uuid}")
        admin_entity = TestEntityFactory.create_test_admin_entity(test_uuid=admin_uuid, description="Admin Test Entity")
        await async_adapter.create(admin_entity)
        return regular_entity, manager_entity, admin_entity

    await create_multiple_entity_types()
    logger.info("Different async entity types created successfully")


@then("all async entity types should be retrievable")
async def step_then_all_async_entity_types_retrievable(context):
    """Verify all different async entity types can be retrieved."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    regular_uuid = uuid.UUID(get_entity_id(context, "regular_entity"))
    manager_uuid = uuid.UUID(get_entity_id(context, "manager_entity"))
    admin_uuid = uuid.UUID(get_entity_id(context, "admin_entity"))
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    @atomic_decorator
    async def verify_entity_types():
        async_adapter = get_async_adapter(context)
        session = async_adapter.session_manager.get_session()

        logger.info(f"Verifying regular async entity with UUID {regular_uuid}")
        regular = await session.get(TestEntity, regular_uuid)
        assert regular is not None, "Regular entity not found"
        assert regular.description == "Regular Test Entity", "Regular entity has wrong description"

        logger.info(f"Verifying manager async entity with UUID {manager_uuid}")
        manager = await session.get(TestManagerEntity, manager_uuid)
        assert manager is not None, "Manager entity not found"
        assert manager.description == "Manager Test Entity", "Manager entity has wrong description"
        assert manager.created_by_uuid is not None, "Manager entity missing created_by_uuid"

        logger.info(f"Verifying admin async entity with UUID {admin_uuid}")
        admin = await session.get(TestAdminEntity, admin_uuid)
        assert admin is not None, "Admin entity not found"
        assert admin.description == "Admin Test Entity", "Admin entity has wrong description"
        assert admin.created_by_admin_uuid is not None, "Admin entity missing created_by_admin_uuid"

        logger.info("All async entity types verified successfully")
        return True

    await verify_entity_types()


@when("an error is triggered within an async atomic transaction")
async def step_when_error_triggered_in_async_atomic(context):
    """Trigger errors within async atomic transactions to test handlers."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")
    async_adapter = get_async_adapter(context)
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    logger.info("Testing async normal exception handling")
    try:

        @atomic_decorator
        async def normal_exception():
            entity = TestEntityFactory.create_test_entity()
            await async_adapter.create(entity)
            logger.info("Raising normal exception")
            raise ValueError("Normal exception test")

        await normal_exception()
    except Exception as e:
        scenario_context.store("normal_exception", e)
        logger.info(f"Caught normal exception: {type(e).__name__}")

    logger.info("Testing async deadlock exception handling")
    try:

        @atomic_decorator
        async def deadlock_exception():
            entity = TestEntityFactory.create_test_entity()
            await async_adapter.create(entity)
            from sqlalchemy.exc import OperationalError

            logger.info("Raising database deadlock exception")
            raise OperationalError("database is locked", None, None)

        await deadlock_exception()
    except Exception as e:
        scenario_context.store("deadlock_exception", e)
        logger.info(f"Caught deadlock exception: {type(e).__name__}")


@then("the async transaction should be rolled back")
async def step_then_async_transaction_rolled_back(context):
    """Verify the async session remains usable after error rollback."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")
    logger.info("Verifying async session is still usable after rollback")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    @atomic_decorator
    async def verify_session_usable():
        test_uuid = uuid.uuid4()
        logger.info(f"Creating test entity with UUID {test_uuid}")
        entity = TestEntityFactory.create_test_entity(test_uuid=test_uuid, description="Entity to verify rollback")
        async_adapter = get_async_adapter(context)
        await async_adapter.create(entity)
        # Avoid SELECT after DML (StarRocks): identity presence after create is enough.
        assert entity.test_uuid == test_uuid, "Async session not usable after error handling"
        logger.info("Async session verified as usable after rollback")
        return True

    result = await verify_session_usable()
    assert result, "Async session is not usable after transaction rollback"


@when("a new entity is created in an async atomic transaction")
async def step_when_entity_created_in_async_atomic(context):
    """Create a new entity within an async atomic transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Generate a UUID for the entity
    test_uuid = uuid.uuid4()
    scenario_context.entity_ids["async_entity"] = str(test_uuid)

    logger.info(f"Creating async entity with UUID {test_uuid}")
    async_adapter = get_async_adapter(context)
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    @atomic_decorator
    async def create_entity_async_atomic():
        """Create a new entity within an async atomic block."""
        entity = TestEntityFactory.create_test_entity(test_uuid=test_uuid, description="Async Entity")

        # Get the async adapter from scenario context
        await async_adapter.create(entity)
        return entity

    # Execute the async atomic operation
    await create_entity_async_atomic()
    logger.info("Async entity created successfully")


@then("the async entity should be retrievable")
async def step_then_async_entity_should_be_retrievable(context):
    """Verify the entity exists after async atomic transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Get the UUID from context
    async_uuid = uuid.UUID(get_entity_id(context, "async_entity"))
    logger.info(f"Retrieving async entity with UUID {async_uuid}")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    @atomic_decorator
    async def get_entity():
        async_adapter = get_async_adapter(context)
        session = async_adapter.session_manager.get_session()
        retrieved_entity = await session.get(TestEntity, async_uuid)
        assert retrieved_entity is not None, "Entity not found in database after async atomic transaction"
        assert retrieved_entity.description == "Async Entity", "Entity has incorrect description"
        logger.info("Async entity retrieved successfully")
        return retrieved_entity

    await get_entity()


@when("a new async entity creation fails within an atomic transaction")
async def step_when_async_entity_creation_fails(context):
    """Attempt to create an async entity with a failure that causes rollback."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Generate a UUID for the entity
    test_uuid = uuid.uuid4()
    scenario_context.entity_ids["async_failed_entity"] = str(test_uuid)

    logger.info(f"Creating async entity with UUID {test_uuid} (will fail)")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    try:

        @atomic_decorator
        async def create_entity_with_failure():
            """Create an entity but raise an exception to trigger rollback."""
            entity = TestEntityFactory.create_test_entity(
                test_uuid=test_uuid,
                description="Async Entity that should be rolled back",
            )
            async_adapter = get_async_adapter(context)
            await async_adapter.create(entity)

            # Simulate failure
            logger.info("Raising exception to trigger async rollback")
            raise ValueError("Simulated failure for testing async atomic rollback")

        await create_entity_with_failure()
    except Exception as e:
        # We expect this exception
        logger.info(f"Caught expected exception: {type(e).__name__}")
    else:
        assert False, "Exception was not raised as expected"


@then("no async entity should exist in the database")
async def step_then_no_async_entity_should_exist(context):
    """Verify the entity doesn't exist after failed async atomic transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Get the UUID from context
    async_uuid = uuid.UUID(get_entity_id(context, "async_failed_entity"))
    logger.info(f"Verifying async entity with UUID {async_uuid} doesn't exist")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    @atomic_decorator
    async def check_entity_absence():
        async_adapter = get_async_adapter(context)
        session = async_adapter.session_manager.get_session()
        retrieved_entity = await session.get(TestEntity, async_uuid)
        assert retrieved_entity is None, "Entity found in database after failed async atomic transaction"
        logger.info("Verified async entity doesn't exist (rollback successful)")
        return retrieved_entity

    await check_entity_absence()


@then("the async database session should remain usable")
async def step_then_async_session_should_remain_usable(context):
    """Verify the async session is still usable after a failed transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")
    logger.info("Verifying async session is still usable")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    @atomic_decorator
    async def verify_session_usable():
        # Create a new entity to test the session is still working
        test_uuid = uuid.uuid4()
        logger.info(f"Creating test entity with UUID {test_uuid}")

        entity = TestEntityFactory.create_test_entity(
            test_uuid=test_uuid,
            description="Async Entity to test session usability",
        )
        async_adapter = get_async_adapter(context)
        await async_adapter.create(entity)

        # Try to retrieve it
        session = async_adapter.session_manager.get_session()
        retrieved_entity = await session.get(TestEntity, test_uuid)
        assert retrieved_entity is not None, "Async session is not usable after error handling"

        logger.info("Async session verified as usable")
        return True

    result = await verify_session_usable()
    assert result, "Async session is not usable after transaction rollback"


@when("multiple entities are created in an async atomic transaction")
async def step_when_multiple_async_entities_created(context):
    """Create multiple entities in a single async atomic transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Generate UUIDs for entities
    entity_uuids = [uuid.uuid4() for _ in range(5)]

    # Store UUIDs in context
    for i, uuid_val in enumerate(entity_uuids):
        scenario_context.entity_ids[f"multi_async_entity_{i}"] = str(uuid_val)

    logger.info("Creating multiple entities in async atomic transaction")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    @atomic_decorator
    async def create_multiple_entities():
        """Create multiple entities within an async atomic block."""
        entities = []
        for i, uuid_val in enumerate(entity_uuids):
            logger.info(f"Creating async entity {i} with UUID {uuid_val}")
            entity = TestEntityFactory.create_test_entity(test_uuid=uuid_val, description=f"Async Entity {i + 1}")
            async_adapter = get_async_adapter(context)
            await async_adapter.create(entity)
            entities.append(entity)

        logger.info("Multiple async entities created successfully")
        return entities

    # Execute the async atomic operation
    await create_multiple_entities()


@then("all async entities should be retrievable")
async def step_then_all_async_entities_retrievable(context):
    """Verify all entities exist after async atomic transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")
    logger.info("Verifying all async entities are retrievable")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    @atomic_decorator
    async def verify_entities():
        """Verify all entities within an async atomic block."""
        async_adapter = get_async_adapter(context)
        session = async_adapter.session_manager.get_session()

        # Check that all entities were created
        for i in range(5):
            uuid_key = f"multi_async_entity_{i}"
            if uuid_key in scenario_context.entity_ids:
                entity_uuid = uuid.UUID(scenario_context.entity_ids[uuid_key])
                logger.info(f"Verifying async entity {i} with UUID {entity_uuid}")

                retrieved_entity = await session.get(TestEntity, entity_uuid)
                assert retrieved_entity is not None, f"Entity {i + 1} not found after async atomic transaction"
                assert retrieved_entity.description == f"Async Entity {i + 1}", (
                    f"Entity {i + 1} has incorrect description"
                )
                logger.info(f"Async entity {i} verified successfully")

        logger.info("All async entities verified successfully")
        return True

    # Execute the async verification
    result = await verify_entities()
    assert result, "Entity verification failed"


@when("complex async operations are performed in a transaction")
async def step_when_complex_async_operations(context):
    """Demonstrate more complex async operations with proper session management."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Generate UUIDs
    parent_uuid = uuid.uuid4()
    related_uuids = [uuid.uuid4() for _ in range(3)]

    # Store UUIDs in context
    scenario_context.entity_ids["complex_parent"] = str(parent_uuid)
    for i, uuid_val in enumerate(related_uuids):
        scenario_context.entity_ids[f"complex_related_{i}"] = str(uuid_val)

    logger.info(f"Creating complex entity relationship with parent UUID {parent_uuid}")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    # Create a parent entity and related entities in one atomic transaction
    @atomic_decorator
    async def create_entity_with_relations():
        # Create the parent entity
        parent = TestEntityFactory.create_test_entity(
            test_uuid=parent_uuid,
            description="Parent Entity for Complex Operations",
        )
        async_adapter = get_async_adapter(context)
        await async_adapter.create(parent)

        # Create related entities
        for i, related_uuid in enumerate(related_uuids):
            logger.info(f"Creating complex related entity {i} with UUID {related_uuid}")
            related = TestEntityFactory.create_related_test_entity(
                related_uuid=related_uuid,
                name=f"Complex Related {i + 1}",
                parent_id=parent_uuid,
                value=f"Value {i + 1}",
            )
            await async_adapter.create(related)

        logger.info("Complex entity relationships created successfully")
        return parent

    # Execute the async atomic operation
    await create_entity_with_relations()


@then("all related entities should be accessible")
async def step_then_related_entities_accessible(context):
    """Verify that related entities can be accessed through relationships."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")

    # Get UUIDs from context
    parent_uuid = uuid.UUID(get_entity_id(context, "complex_parent"))
    logger.info(f"Verifying related entities for parent UUID {parent_uuid}")
    atomic_decorator = _get_atomic_decorator(db_type, is_async=True)

    @atomic_decorator
    async def verify_relationships():
        async_adapter = get_async_adapter(context)
        session = async_adapter.session_manager.get_session()

        # Get the parent entity
        parent = await session.get(TestEntity, parent_uuid)
        assert parent is not None, "Parent entity not found"
        logger.info("Parent entity retrieved successfully")

        # Query for related entities (order by name for cross-DB determinism)
        stmt = (
            select(RelatedTestEntity).where(RelatedTestEntity.parent_id == parent_uuid).order_by(RelatedTestEntity.name)
        )
        result = await session.execute(stmt)
        related_entities = result.scalars().all()

        # Check the relationship is loaded correctly
        assert len(related_entities) == 3, f"Expected 3 related entities, found {len(related_entities)}"
        logger.info(f"Found {len(related_entities)} related entities")

        # Verify each related entity
        for i, related in enumerate(related_entities):
            assert related.parent_id == parent_uuid, "Related entity has wrong parent_id"
            assert related.name == f"Complex Related {i + 1}", f"Related entity {i} has wrong name"
            logger.info(f"Verified related entity: {related.name}")

        logger.info("All related entities verified successfully")
        return True

    result = await verify_relationships()
    assert result, "Relationship verification failed"


# ---- unit scenarios: atomic decorator against a fake session (no database) ----


class _FakeTransaction:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        self.session.active = True
        return self

    def __exit__(self, *_exc):
        self.session.active = False
        return False

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, *exc):
        return self.__exit__(*exc)


class _FakeSession:
    """Records what the atomic decorator does to a session."""

    def __init__(self, *, is_async, rollback_error=None):
        self.info = {}
        self.active = False
        self.is_async = is_async
        self.rollback_error = rollback_error
        self.rolled_back = False
        self.closed = False
        self.committed = False

    def in_transaction(self):
        return self.active

    def begin(self):
        return _FakeTransaction(self)

    def _rollback(self):
        self.rolled_back = True
        if self.rollback_error is not None:
            raise self.rollback_error

    def _close(self):
        self.closed = True

    def _commit(self):
        self.committed = True

    def __getattr__(self, name):
        action = {"rollback": self._rollback, "close": self._close, "commit": self._commit}.get(name)
        if action is None:
            raise AttributeError(name)
        if self.is_async:

            async def coroutine():
                return action()

            return coroutine
        return action


class _FakeSessionManager:
    def __init__(self, session):
        self.session = session

    def get_session(self):
        return self.session

    def remove_session(self):
        if self.session.is_async:

            async def noop():
                return None

            return noop()
        return None


def _fake_registry(session):
    manager = _FakeSessionManager(session)

    class FakeRegistry:
        @staticmethod
        def get_sync_manager():
            return manager

        @staticmethod
        def get_async_manager():
            return manager

    return FakeRegistry


_RAISABLE = {
    "KeyboardInterrupt": KeyboardInterrupt,
    "SystemExit": SystemExit,
    "CancelledError": asyncio.CancelledError,
    "ValueError": ValueError,
}


@given("a fake {mode} session behind the atomic decorator")
def step_given_fake_atomic_session(context, mode):
    from unittest import mock

    from archipy.adapters.base.sqlalchemy import atomic as atomic_module

    sc = get_current_scenario_context(context)
    session = _FakeSession(is_async=mode == "async")
    patcher = mock.patch.object(
        atomic_module, "_load_session_manager_registry", lambda _db_type: _fake_registry(session),
    )
    patcher.start()
    context.add_cleanup(patcher.stop)
    sc.store("fake_session", session)
    sc.store("fake_mode", mode)


@given("the fake session fails to roll back")
def step_given_fake_rollback_fails(context):
    get_current_scenario_context(context).get("fake_session").rollback_error = RuntimeError("rollback broke")


def _run_atomic_function(context, body):
    sc = get_current_scenario_context(context)
    mode = sc.get("fake_mode")
    if mode == "async":

        @sqlalchemy_atomic("sqlite")
        async def work():
            body()

        runner = lambda: asyncio.run(work())  # noqa: E731
    else:

        @sqlalchemy_atomic("sqlite")
        def work():
            body()

        runner = work
    try:
        runner()
        sc.store("atomic_error", None)
    except BaseException as e:  # noqa: BLE001
        sc.store("atomic_error", e)


@when("the atomic function raises {name}")
def step_when_atomic_function_raises(context, name):
    exc_type = _RAISABLE[name]

    def body():
        raise exc_type()

    _run_atomic_function(context, body)


@then("{name} should propagate through the atomic block unchanged")
def step_then_propagates_unchanged(context, name):
    error = get_current_scenario_context(context).get("atomic_error")
    assert type(error) is _RAISABLE[name], f"Got {error!r}"


@then("the fake session should have been rolled back and closed")
def step_then_fake_rolled_back_closed(context):
    session = get_current_scenario_context(context).get("fake_session")
    assert session.rolled_back and session.closed, f"rolled_back={session.rolled_back} closed={session.closed}"


@then("the fake session should have been closed")
def step_then_fake_closed(context):
    assert get_current_scenario_context(context).get("fake_session").closed


@then("an InternalError chained from ValueError should be raised")
def step_then_internal_error_chained(context):
    error = get_current_scenario_context(context).get("atomic_error")
    assert isinstance(error, InternalError), f"Got {error!r}"
    assert isinstance(error.__cause__, ValueError), f"Cause {error.__cause__!r}"


@when("a nested atomic block succeeds on {db_type}")
def step_when_nested_atomic_succeeds(context, db_type):
    """Run an atomic block inside another one on the real database and record the marker at each point."""
    flag = ATOMIC_BLOCK_CONFIGS[db_type]["flag"]
    manager = _get_session_registry(db_type).get_sync_manager()
    atomic = _get_atomic_decorator(db_type, is_async=False)
    seen = {}

    @atomic
    def inner():
        seen["inner"] = manager.get_session().info.get(flag)

    @atomic
    def outer():
        seen["outer_before"] = manager.get_session().info.get(flag)
        inner()
        seen["outer_after_inner"] = manager.get_session().info.get(flag)

    outer()
    seen["after"] = manager.get_session().info.get(flag)
    get_current_scenario_context(context).store("atomic_marker_seen", seen)


@when("a nested async atomic block succeeds on {db_type}")
async def step_when_nested_async_atomic_succeeds(context, db_type):
    """Async variant of the nested atomic block check."""
    flag = ATOMIC_BLOCK_CONFIGS[db_type]["flag"]
    manager = _get_session_registry(db_type).get_async_manager()
    atomic = _get_atomic_decorator(db_type, is_async=True)
    seen = {}

    @atomic
    async def inner():
        seen["inner"] = manager.get_session().info.get(flag)

    @atomic
    async def outer():
        seen["outer_before"] = manager.get_session().info.get(flag)
        await inner()
        seen["outer_after_inner"] = manager.get_session().info.get(flag)

    await outer()
    seen["after"] = manager.get_session().info.get(flag)
    get_current_scenario_context(context).store("atomic_marker_seen", seen)


@then("the atomic marker should be set in both blocks and cleared only after the outermost one")
def step_then_atomic_marker_lifecycle(context):
    seen = get_current_scenario_context(context).get("atomic_marker_seen")
    assert seen == {"inner": True, "outer_before": True, "outer_after_inner": True, "after": None}, f"Got {seen!r}"


@when("a {kind} error with driver code {code} is handled by the atomic decorator")
def step_when_driver_error_handled(context, kind, code):
    from sqlalchemy.exc import IntegrityError, OperationalError

    from archipy.adapters.base.sqlalchemy.atomic import _handle_db_exception

    class _DriverError(Exception):
        pass

    # PostgreSQL codes are strings (pgcode); MySQL-style codes are the first positional arg
    orig = (
        _DriverError(int(code), "driver message")
        if code.isdigit() and len(code) == 4
        else _DriverError("driver message")
    )
    if not (code.isdigit() and len(code) == 4):
        orig.pgcode = code
    error_type = OperationalError if kind == "operational" else IntegrityError
    sqlalchemy_error = error_type("SELECT 1", {}, orig)
    sc = get_current_scenario_context(context)
    try:
        _handle_db_exception(sqlalchemy_error, "sqlite", "work")
        sc.store("atomic_error", None)
    except Exception as e:
        sc.store("atomic_error", e)


@then("the atomic decorator should raise {expected}")
def step_then_named_error_raised(context, expected):
    from archipy.models import errors

    error = get_current_scenario_context(context).get("atomic_error")
    assert type(error) is getattr(errors, expected), f"Got {error!r}"


# --- Search pagination totals ---


def _install_count_counter(context, engine) -> None:
    """Record every COUNT statement the engine runs for the rest of the scenario."""
    from sqlalchemy import event

    statements: list[str] = []
    explains: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def record_count_statement(conn, cursor, statement, parameters, ctx, executemany):  # noqa: ARG001
        lowered = statement.lower()
        if "count(" in lowered:
            statements.append(statement)
        if lowered.startswith("explain"):
            explains.append(statement)

    get_current_scenario_context(context).store("count_statements", statements)
    get_current_scenario_context(context).store("explain_statements", explains)


def _search_query(prefix: str):
    return select(TestEntity).where(TestEntity.description.like(f"{prefix}%"))


def _store_search(context, results, total: int) -> None:
    get_current_scenario_context(context).store("search_result", (results, total))


@given('{count:d} searchable entities exist with description prefix "{prefix}"')
def step_given_searchable_entities(context, count, prefix):
    scenario_context = get_current_scenario_context(context)
    adapter = get_adapter(context)

    @_get_atomic_decorator(scenario_context.get("db_type", "sqlite"))
    def create_entities():
        adapter.bulk_create(
            [TestEntityFactory.create_test_entity(description=f"{prefix}-{index}") for index in range(count)],
        )

    create_entities()
    _install_count_counter(context, adapter.session_manager.engine)


@given('{count:d} async searchable entities exist with description prefix "{prefix}"')
async def step_given_async_searchable_entities(context, count, prefix):
    scenario_context = get_current_scenario_context(context)
    async_adapter = get_async_adapter(context)

    @_get_atomic_decorator(scenario_context.get("db_type", "sqlite"), is_async=True)
    async def create_entities():
        await async_adapter.bulk_create(
            [TestEntityFactory.create_test_entity(description=f"{prefix}-{index}") for index in range(count)],
        )

    await create_entities()
    _install_count_counter(context, async_adapter.session_manager.engine.sync_engine)


@given("the search count cache is enabled with a TTL of {ttl:d} seconds")
def step_given_count_cache_enabled(context, ttl):
    from archipy.adapters.base.sqlalchemy.adapters import _build_async_count_cache, _build_count_cache
    from archipy.configs.config_template import SQLAlchemyConfig

    scenario_context = get_current_scenario_context(context)
    cache_config = SQLAlchemyConfig(COUNT_CACHE_ENABLED=True, COUNT_CACHE_TTL_SECONDS=ttl)
    scenario_context.store("count_cache_ttl", ttl)
    if scenario_context.adapter is not None:
        scenario_context.adapter._cached_count = _build_count_cache(cache_config)  # noqa: SLF001
    if scenario_context.async_adapter is not None:
        scenario_context.async_adapter._cached_count = _build_async_count_cache(cache_config)  # noqa: SLF001


@when('I search page {page:d} of size {size:d} for entities with description prefix "{prefix}"')
def step_when_search_page(context, page, size, prefix):
    from archipy.models.dtos.pagination_dto import PaginationDTO

    scenario_context = get_current_scenario_context(context)
    adapter = get_adapter(context)

    @_get_atomic_decorator(scenario_context.get("db_type", "sqlite"))
    def search():
        return adapter.execute_search_query(
            TestEntity,
            _search_query(prefix),
            pagination=PaginationDTO(page=page, page_size=size),
        )

    _store_search(context, *search())


@when(
    'I search page {page:d} of size {size:d} for entities with description prefix "{prefix}" and count threshold {threshold:d}',
)
def step_when_search_page_with_threshold(context, page, size, prefix, threshold):
    from archipy.models.dtos.pagination_dto import PaginationDTO

    scenario_context = get_current_scenario_context(context)
    adapter = get_adapter(context)

    @_get_atomic_decorator(scenario_context.get("db_type", "sqlite"))
    def search():
        return adapter.execute_search_query(
            TestEntity,
            _search_query(prefix),
            pagination=PaginationDTO(page=page, page_size=size),
            count_threshold=threshold,
        )

    _store_search(context, *search())


@when('I async search page {page:d} of size {size:d} for entities with description prefix "{prefix}"')
async def step_when_async_search_page(context, page, size, prefix):
    from archipy.models.dtos.pagination_dto import PaginationDTO

    scenario_context = get_current_scenario_context(context)
    async_adapter = get_async_adapter(context)

    @_get_atomic_decorator(scenario_context.get("db_type", "sqlite"), is_async=True)
    async def search():
        return await async_adapter.execute_search_query(
            TestEntity,
            _search_query(prefix),
            pagination=PaginationDTO(page=page, page_size=size),
        )

    _store_search(context, *await search())


@when(
    'I async search page {page:d} of size {size:d} for entities with description prefix "{prefix}" and count threshold {threshold:d}',
)
async def step_when_async_search_page_with_threshold(context, page, size, prefix, threshold):
    from archipy.models.dtos.pagination_dto import PaginationDTO

    scenario_context = get_current_scenario_context(context)
    async_adapter = get_async_adapter(context)

    @_get_atomic_decorator(scenario_context.get("db_type", "sqlite"), is_async=True)
    async def search():
        return await async_adapter.execute_search_query(
            TestEntity,
            _search_query(prefix),
            pagination=PaginationDTO(page=page, page_size=size),
            count_threshold=threshold,
        )

    _store_search(context, *await search())


@when("the cached search total expires")
def step_when_cached_total_expires(context):
    ttl = get_current_scenario_context(context).get("count_cache_ttl")
    time.sleep(ttl + 0.2)


@then("the search should return {rows:d} rows and a total of {total:d}")
def step_then_search_rows_and_total(context, rows, total):
    results, actual_total = get_current_scenario_context(context).get("search_result")
    assert len(results) == rows, f"Expected {rows} rows, got {len(results)}"
    assert actual_total == total, f"Expected total {total}, got {actual_total}"


@then("the search should return {rows:d} rows and a total of at least {minimum:d}")
def step_then_search_rows_and_minimum_total(context, rows, minimum):
    results, actual_total = get_current_scenario_context(context).get("search_result")
    assert len(results) == rows, f"Expected {rows} rows, got {len(results)}"
    assert actual_total >= minimum, f"Expected total of at least {minimum}, got {actual_total}"


@then("{count:d} COUNT queries should have run")
def step_then_count_queries_ran(context, count):
    statements = get_current_scenario_context(context).get("count_statements")
    assert len(statements) == count, f"Expected {count} COUNT queries, got {len(statements)}: {statements}"


@given("the search count threshold config is {threshold:d}")
def step_given_count_threshold_config(context, threshold):
    scenario_context = get_current_scenario_context(context)
    for adapter in (scenario_context.adapter, scenario_context.async_adapter):
        if adapter is not None:
            adapter._count_threshold = threshold  # noqa: SLF001


@given("the global count threshold is {threshold:d}")
def step_given_global_count_threshold(context, threshold):
    sqlalchemy_config = BaseConfig.global_config().POSTGRES_SQLALCHEMY
    context.add_cleanup(setattr, sqlalchemy_config, "COUNT_THRESHOLD", sqlalchemy_config.COUNT_THRESHOLD)
    sqlalchemy_config.COUNT_THRESHOLD = threshold


@given("the global count threshold is not set")
def step_given_global_count_threshold_unset(context):
    sqlalchemy_config = BaseConfig.global_config().POSTGRES_SQLALCHEMY
    context.add_cleanup(setattr, sqlalchemy_config, "COUNT_THRESHOLD", sqlalchemy_config.COUNT_THRESHOLD)
    sqlalchemy_config.COUNT_THRESHOLD = None


@then("the search output DTO reports the total as {kind}")
def step_then_search_output_dto_kind(context, kind):
    from archipy.models.dtos.search_output_dto import SearchOutputDTO

    assert kind in {"estimated", "exact"}, f"Unknown total kind {kind!r}"
    _, total = get_current_scenario_context(context).get("search_result")
    output = SearchOutputDTO(total_count=total)
    assert output.total_count_estimated is (kind == "estimated"), (
        f"Expected the total {total} to be {kind}, got total_count_estimated={output.total_count_estimated}"
    )


@then("the exact search output DTO reports the total as exact")
def step_then_exact_search_output_dto(context):
    from archipy.models.dtos.search_output_dto import ExactSearchOutputDTO

    _, total = get_current_scenario_context(context).get("search_result")
    assert ExactSearchOutputDTO(total_count=total).total_count_estimated is False


@given("the table statistics are refreshed")
def step_given_table_statistics_refreshed(context):
    from sqlalchemy import text

    scenario_context = get_current_scenario_context(context)
    db_type = scenario_context.get("db_type", "sqlite")
    adapter = get_adapter(context)
    statement = "ANALYZE TABLE test_entities" if db_type == "mysql" else "ANALYZE test_entities"

    @_get_atomic_decorator(db_type)
    def analyze():
        adapter.execute(text(statement))

    analyze()


@when('I search page 1 of size {size:d} for a query limited to {limit:d} entities with description prefix "{prefix}"')
def step_when_search_limited_query(context, size, limit, prefix):
    from archipy.models.dtos.pagination_dto import PaginationDTO

    scenario_context = get_current_scenario_context(context)
    adapter = get_adapter(context)

    @_get_atomic_decorator(scenario_context.get("db_type", "sqlite"))
    def search():
        return adapter.execute_search_query(
            TestEntity,
            _search_query(prefix).limit(limit),
            pagination=PaginationDTO(page=1, page_size=size),
        )

    _store_search(context, *search())


@given("entities exist with these descriptions: {descriptions}")
def step_given_entities_with_descriptions(context, descriptions):
    scenario_context = get_current_scenario_context(context)
    adapter = get_adapter(context)
    values = [None if item == "NULL" else item for item in descriptions.split(",")]

    @_get_atomic_decorator(scenario_context.get("db_type", "sqlite"))
    def create_entities():
        adapter.bulk_create([TestEntityFactory.create_test_entity(description=value) for value in values])

    create_entities()


def _filter_value(operation: str, raw_value: str):
    if raw_value == "NULL":
        return None
    if operation in ("IN_LIST", "NOT_IN_LIST"):
        return raw_value.split(",")
    return raw_value


@when('I filter the descriptions with {operation} and value "{raw_value}"')
def step_when_filter_descriptions(context, operation, raw_value):
    from archipy.models.types.base_types import FilterOperationType

    scenario_context = get_current_scenario_context(context)
    adapter = get_adapter(context)
    filter_operation = FilterOperationType[operation]
    value = _filter_value(operation, raw_value)

    @_get_atomic_decorator(scenario_context.get("db_type", "sqlite"))
    def run_filter():
        query = adapter._apply_filter(select(TestEntity), TestEntity.description, value, filter_operation)  # noqa: SLF001
        return list(adapter.scalars(query).all())

    scenario_context.store("filtered_entities", run_filter())


@when('I filter the descriptions with {operation} and the non-list value "{raw_value}"')
def step_when_filter_with_non_list(context, operation, raw_value):
    from archipy.models.types.base_types import FilterOperationType

    scenario_context = get_current_scenario_context(context)
    adapter = get_adapter(context)
    try:
        adapter._apply_filter(  # noqa: SLF001
            select(TestEntity),
            TestEntity.description,
            raw_value,
            FilterOperationType[operation],
        )
    except Exception as error:  # noqa: BLE001
        scenario_context.store("filter_error", error)


@then("the filter should match {count:d} entities")
def step_then_filter_matches(context, count):
    matched = get_current_scenario_context(context).get("filtered_entities")
    assert len(matched) == count, f"Expected {count} entities, got {len(matched)}"


@then("the filter should be rejected with an InvalidArgumentError")
def step_then_filter_rejected(context):
    from archipy.models.errors import InvalidArgumentError

    error = get_current_scenario_context(context).get("filter_error")
    assert isinstance(error, InvalidArgumentError), f"Got {error!r}"


@then("{count:d} EXPLAIN estimates should have run")
def step_then_explain_estimates_ran(context, count):
    statements = get_current_scenario_context(context).get("explain_statements")
    assert len(statements) == count, f"Expected {count} EXPLAIN estimates, got {len(statements)}: {statements}"


@when("I search page {page:d} of size {size:d} for the {shape} descriptions")
def step_when_search_shaped_descriptions(context, page, size, shape):
    from archipy.models.dtos.pagination_dto import PaginationDTO
    from archipy.models.dtos.sort_dto import SortDTO
    from archipy.models.types.sort_order_type import SortOrderType

    scenario_context = get_current_scenario_context(context)
    adapter = get_adapter(context)
    if shape == "distinct":
        query = select(TestEntity.description).distinct()
    else:
        query = select(TestEntity.description).group_by(TestEntity.description)

    @_get_atomic_decorator(scenario_context.get("db_type", "sqlite"))
    def search():
        return adapter.execute_search_query(
            TestEntity,
            query,
            pagination=PaginationDTO(page=page, page_size=size),
            sort_info=SortDTO(column="description", order=SortOrderType.ASCENDING),
        )

    _store_search(context, *search())


@when("I search page {page:d} of size {size:d} for the {shape} descriptions and count threshold {threshold:d}")
def step_when_search_shaped_descriptions_with_threshold(context, page, size, shape, threshold):
    from archipy.models.dtos.pagination_dto import PaginationDTO
    from archipy.models.dtos.sort_dto import SortDTO
    from archipy.models.types.sort_order_type import SortOrderType

    scenario_context = get_current_scenario_context(context)
    adapter = get_adapter(context)
    if shape == "distinct":
        query = select(TestEntity.description).distinct()
    else:
        query = select(TestEntity.description).group_by(TestEntity.description)

    @_get_atomic_decorator(scenario_context.get("db_type", "sqlite"))
    def search():
        return adapter.execute_search_query(
            TestEntity,
            query,
            pagination=PaginationDTO(page=page, page_size=size),
            sort_info=SortDTO(column="description", order=SortOrderType.ASCENDING),
            count_threshold=threshold,
        )

    _store_search(context, *search())
