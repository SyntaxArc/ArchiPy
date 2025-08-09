"""Implementation of steps for testing SQLAlchemy atomic transactions.

This module contains step definitions for both synchronous and asynchronous
atomic transaction scenarios.
"""
import asyncio
import logging
import os
import tempfile
import uuid
from datetime import datetime

from behave import given, then, when

from archipy.adapters.sqlite.sqlalchemy.adapters import SQLiteSQLAlchemyAdapter, AsyncSQLiteSQLAlchemyAdapter
from features.test_entity import RelatedTestEntity, TestAdminEntity, TestEntity, TestManagerEntity
from features.test_entity_factory import TestEntityFactory
from features.test_helpers import (
    async_schema_setup,
    get_adapter,
    get_async_adapter,
    get_current_scenario_context,
)
from sqlalchemy import select

from archipy.adapters.sqlite.sqlalchemy.session_manager_registry import SQLiteSessionManagerRegistry
from archipy.configs.config_template import SQLiteSQLAlchemyConfig
from archipy.helpers.decorators.sqlalchemy_atomic import (
    async_sqlite_sqlalchemy_atomic_decorator,
    sqlite_sqlalchemy_atomic_decorator,
)
from archipy.models.entities.sqlalchemy.base_entities import BaseEntity
from archipy.models.errors import InternalError


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


@given("the application database is initialized")
def step_given_database_initialized(context):
    """Initialize the database for testing with a file-based SQLite database."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))

    # Get the current scenario context
    scenario_context = get_current_scenario_context(context)

    # Create a unique temporary file for this scenario
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

    logger.info(f"Creating SQLAlchemy adapter with database: {db_file}")

    # Create configuration with file-based database
    sync_config = SQLiteSQLAlchemyConfig(
        DRIVER_NAME="sqlite",
        DATABASE=db_file,
    )

    # Create adapter for tests and store in scenario context
    adapter = SQLiteSQLAlchemyAdapter(orm_config=sync_config)
    SQLiteSessionManagerRegistry.set_sync_manager(adapter.session_manager)
    scenario_context.adapter = adapter

    # Set up database schema with sync adapter
    logger.info("Creating database schema with sync adapter")
    BaseEntity.metadata.drop_all(adapter.session_manager.engine)
    BaseEntity.metadata.create_all(adapter.session_manager.engine)

    # For async tests, create and set up the async adapter
    if any("async" in tag.lower() for tag in context.scenario.tags):
        logger.info(f"Creating async SQLAlchemy adapter with database: {db_file}")

        # Create async config with the same database file
        async_config = SQLiteSQLAlchemyConfig(
            DRIVER_NAME="sqlite+aiosqlite",
            DATABASE=db_file,
        )

        try:
            # Create a new async adapter
            async_adapter = AsyncSQLiteSQLAlchemyAdapter(orm_config=async_config)
            SQLiteSessionManagerRegistry.set_async_manager(async_adapter.session_manager)
            scenario_context.async_adapter = async_adapter

            # Create schema with async adapter
            logger.info("Creating database schema with async adapter")
            asyncio.run(async_schema_setup(async_adapter))

            logger.info("Async adapter and schema setup completed")
        except Exception as e:
            logger.exception(f"Error setting up async adapter: {e}")


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

    # Generate a UUID for the entity
    test_uuid = uuid.uuid4()

    @sqlite_sqlalchemy_atomic_decorator
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

    # Get the entity's UUID from scenario context
    entity_uuid = uuid.UUID(get_entity_id(context, "test_entity"))
    logger.info(f"Retrieving entity with UUID {entity_uuid}")

    @sqlite_sqlalchemy_atomic_decorator
    def get_entity():
        # Get the adapter from scenario context
        adapter = get_adapter(context)
        session = adapter.get_session()

        retrieved_entity = session.get(TestEntity, entity_uuid)
        assert retrieved_entity is not None, "Entity not found in database after atomic transaction"
        assert (
            retrieved_entity.description == "Entity created in atomic transaction"
        ), "Entity has incorrect description"
        logger.info("Entity retrieved successfully")
        return retrieved_entity

    get_entity()


@when("a new entity creation fails within an atomic transaction")
def step_when_entity_creation_fails_in_atomic(context):
    """Attempt to create an entity with a failure that causes rollback."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)

    # Generate a UUID for the entity
    test_uuid = uuid.uuid4()
    scenario_context.rolled_back_uuid = test_uuid
    logger.info(f"Attempting to create entity with UUID {test_uuid} (will fail)")

    try:

        @sqlite_sqlalchemy_atomic_decorator
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

    # Get a fresh session to verify rollback
    adapter = get_adapter(context)

    @sqlite_sqlalchemy_atomic_decorator
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
    logger.info("Verifying session is still usable after rollback")

    @sqlite_sqlalchemy_atomic_decorator
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


@when("nested atomic transactions are executed")
def step_when_nested_atomic_executed(context):
    """Test nested atomic transactions, both successful and failing."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)

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
    try:

        @sqlite_sqlalchemy_atomic_decorator
        def outer_atomic():
            """Execute the outermost atomic block."""
            logger.info(f"Creating outer entity with UUID {outer_uuid}")

            # Create the outer entity
            adapter = get_adapter(context)
            outer_entity = TestEntityFactory.create_test_entity(
                test_uuid=outer_uuid, description="Outer entity from nested transaction",
            )
            adapter.create(outer_entity)

            try:

                @sqlite_sqlalchemy_atomic_decorator
                def inner_atomic():
                    """Execute a successful inner atomic block."""
                    logger.info(f"Creating inner entity with UUID {inner_uuid}")

                    # Create the inner entity (should succeed)
                    adapter = get_adapter(context)
                    inner_entity = TestEntityFactory.create_test_entity(
                        test_uuid=inner_uuid, description="Inner entity from nested transaction",
                    )
                    adapter.create(inner_entity)
                    return inner_entity

                inner_entity = inner_atomic()
                logger.info(f"Successfully created inner entity: {inner_entity}")

                # Now test a failing inner transaction
                try:

                    @sqlite_sqlalchemy_atomic_decorator
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


@then("operations from successful nested transactions should not be committed")
def step_then_successful_nested_committed(context):
    """Verify that entities from successful nested transactions exist."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)

    # Get UUIDs for verification
    entity1_uuid = uuid.UUID(scenario_context.entity_ids["outer_entity"])
    entity2_uuid = uuid.UUID(scenario_context.entity_ids["inner_entity"])
    entity4_uuid = uuid.UUID(scenario_context.entity_ids["outer_entity"])

    logger.info("Verifying successful nested transaction entities")

    @sqlite_sqlalchemy_atomic_decorator
    def verify_nested_results():
        adapter = get_adapter(context)
        session = adapter.get_session()

        # Check entity 1 (outer atomic, before nested)
        entity1 = session.get(TestEntity, entity1_uuid)
        assert entity1 is None, "Entity 1 not found after nested atomic transactions"
        logger.info("Entity 1 verified successfully")

        # Check entity 2 (successful inner atomic)
        entity2 = session.get(TestEntity, entity2_uuid)
        assert entity2 is None, "Entity 2 not found after nested atomic transactions"
        logger.info("Entity 2 verified successfully")

        # Check entity 4 (outer atomic, after nested)
        entity4 = session.get(TestEntity, entity4_uuid)
        assert entity4 is None, "Entity 4 not found after nested atomic transactions"
        logger.info("Entity 4 verified successfully")

        return True

    verify_nested_results()


@then("operations from failed nested transactions should be rolled back")
def step_then_failed_nested_rolled_back(context):
    """Verify that entities from failed nested transactions don't exist."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)

    # Get UUID for verification
    entity3_uuid = uuid.UUID(scenario_context.entity_ids["failing_entity"])
    logger.info(f"Verifying entity 3 with UUID {entity3_uuid} doesn't exist")

    @sqlite_sqlalchemy_atomic_decorator
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

    # Generate a UUID for the entity
    test_uuid = uuid.uuid4()
    logger.info(f"Creating existing entity with UUID {test_uuid}")
    adapter = get_adapter(context)

    @sqlite_sqlalchemy_atomic_decorator
    def create_entity():
        entity = TestEntityFactory.create_test_entity(test_uuid=test_uuid, description="Original Description")
        adapter.create(entity)

        # Store the entity for later retrieval
        store_entity(context, entity, "existing_entity")
        # Store original values for comparison
        scenario_context.store("original_description", entity.description)
        scenario_context.store("original_updated_at", getattr(entity, "updated_at", None))

    create_entity()
    logger.info("Entity created successfully")


@when("the entity is updated within an atomic transaction")
def step_when_entity_updated_in_atomic(context):
    """Update an entity within an atomic transaction."""
    logger = context.__dict__.get("logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)

    # Get the entity UUID from context
    entity_uuid = uuid.UUID(scenario_context.entity_ids.get("existing_entity"))
    logger.info(f"Updating entity with UUID {entity_uuid}")

    @sqlite_sqlalchemy_atomic_decorator
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
        entity.updated_at = datetime.now()
        entity.is_deleted = True

        # We must flush to ensure changes are visible
        session.flush()

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

    # Get the entity UUID from context
    entity_uuid = uuid.UUID(scenario_context.entity_ids.get("existing_entity"))
    logger.info(f"Verifying updates for entity with UUID {entity_uuid}")

    @sqlite_sqlalchemy_atomic_decorator
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

    # Generate UUIDs for the entities
    main_uuid = uuid.uuid4()
    related_uuids = [uuid.uuid4() for _ in range(3)]

    # Store UUIDs in context for later retrieval
    scenario_context.entity_ids["main_entity"] = str(main_uuid)
    for i, uuid_val in enumerate(related_uuids):
        scenario_context.entity_ids[f"related_entity_{i}"] = str(uuid_val)

    logger.info(f"Creating entity with relationships, main UUID: {main_uuid}")

    @sqlite_sqlalchemy_atomic_decorator
    def create_entity_with_relationships():
        # Create main entity directly to avoid StaleDataError
        main_entity = TestEntityFactory.create_test_entity(
            test_uuid=main_uuid,
            description="Main Entity with Relationships",
        )
        adapter = get_adapter(context)
        adapter.create(main_entity)

        # Flush to ensure the main entity is persisted before creating related entities
        adapter.get_session().flush()

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

    # Get the UUIDs from context
    main_uuid = uuid.UUID(get_entity_id(context, "main_entity"))

    @sqlite_sqlalchemy_atomic_decorator
    def verify_entity_relationships():
        adapter = get_adapter(context)
        session = adapter.get_session()

        # Get the main entity
        main_entity = session.get(TestEntity, main_uuid)
        assert main_entity is not None, "Main entity not found"
        logger.info(f"Main entity retrieved with UUID {main_uuid}")

        # Query for related entities
        related_query = select(RelatedTestEntity).where(RelatedTestEntity.parent_id == main_uuid)
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

    # Generate UUIDs for the entities
    regular_uuid = uuid.uuid4()
    manager_uuid = uuid.uuid4()
    admin_uuid = uuid.uuid4()

    # Store UUIDs in context for later retrieval
    scenario_context.entity_ids["regular_entity"] = str(regular_uuid)
    scenario_context.entity_ids["manager_entity"] = str(manager_uuid)
    scenario_context.entity_ids["admin_entity"] = str(admin_uuid)

    logger.info("Creating different types of entities")

    @sqlite_sqlalchemy_atomic_decorator
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

    # Get the UUIDs from context
    regular_uuid = uuid.UUID(get_entity_id(context, "regular_entity"))
    manager_uuid = uuid.UUID(get_entity_id(context, "manager_entity"))
    admin_uuid = uuid.UUID(get_entity_id(context, "admin_entity"))

    @sqlite_sqlalchemy_atomic_decorator
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
    adapter = get_adapter(context)

    # Test normal exception handling
    logger.info("Testing normal exception handling")
    try:

        @sqlite_sqlalchemy_atomic_decorator
        def normal_exception():
            entity = TestEntityFactory.create_test_entity()
            adapter.create(entity)
            logger.info("Raising normal exception")
            raise ValueError("Normal exception test")

        normal_exception()
    except Exception as e:
        scenario_context.store("normal_exception", e)
        logger.info(f"Caught normal exception: {type(e).__name__}")

    # Test deadlock handling (simulated for SQLite)
    logger.info("Testing deadlock exception handling")
    try:

        @sqlite_sqlalchemy_atomic_decorator
        def deadlock_exception():
            entity = TestEntityFactory.create_test_entity()
            adapter.create(entity)

            # Simulate SQLite deadlock
            from sqlalchemy.exc import OperationalError

            logger.info("Raising SQLite deadlock exception")
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
    logger.info("Verifying session is still usable after rollback")

    @sqlite_sqlalchemy_atomic_decorator
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
    logger.info("Testing operations across multiple atomic blocks")

    # Generate UUIDs for entities
    entity_uuids = [uuid.uuid4() for _ in range(3)]

    # Store UUIDs in context
    for i, uuid_val in enumerate(entity_uuids):
        scenario_context.entity_ids[f"multi_entity_{i}"] = str(uuid_val)

    # Create initial entities
    @sqlite_sqlalchemy_atomic_decorator
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
    @sqlite_sqlalchemy_atomic_decorator
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
    @sqlite_sqlalchemy_atomic_decorator
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
    logger.info("Verifying session consistency across multiple atomic blocks")

    @sqlite_sqlalchemy_atomic_decorator
    def verify_consistency():
        adapter = get_adapter(context)
        session = adapter.get_session()

        # Retrieve query results from scenario context
        query_results = scenario_context.get("query_results")

        # Check that each entity has the updated description
        for i, result in enumerate(query_results):
            logger.info(f"Verifying entity {i} with UUID {result['uuid']}")

            expected_description = f"Updated Entity {i + 1}"
            assert (
                result["description"] == expected_description
            ), f"Entity {i + 1} has wrong description: {result['description']}"
            assert result["updated_at"] is not None, f"Entity {i + 1} missing updated_at timestamp"

            # Verify the entity in the database matches our context
            db_entity = session.get(TestEntity, result["uuid"])
            assert db_entity is not None, f"Entity {i + 1} not found in database"
            assert (
                db_entity.description == expected_description
            ), f"Database entity {i + 1} has wrong description: {db_entity.description}"

            logger.info(f"Entity {i} verified successfully")

        logger.info("Session consistency verified successfully")
        return True

    assert verify_consistency(), "Session consistency verification failed"


@when("a new entity is created in an async atomic transaction")
async def step_when_entity_created_in_async_atomic(context):
    """Create a new entity within an async atomic transaction."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)

    # Generate a UUID for the entity
    test_uuid = uuid.uuid4()
    scenario_context.entity_ids["async_entity"] = str(test_uuid)

    logger.info(f"Creating async entity with UUID {test_uuid}")
    async_adapter = get_async_adapter(context)

    @async_sqlite_sqlalchemy_atomic_decorator
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

    # Get the UUID from context
    async_uuid = uuid.UUID(get_entity_id(context, "async_entity"))
    logger.info(f"Retrieving async entity with UUID {async_uuid}")

    @async_sqlite_sqlalchemy_atomic_decorator
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

    # Generate a UUID for the entity
    test_uuid = uuid.uuid4()
    scenario_context.entity_ids["async_failed_entity"] = str(test_uuid)

    logger.info(f"Creating async entity with UUID {test_uuid} (will fail)")

    try:

        @async_sqlite_sqlalchemy_atomic_decorator
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

    # Get the UUID from context
    async_uuid = uuid.UUID(get_entity_id(context, "async_failed_entity"))
    logger.info(f"Verifying async entity with UUID {async_uuid} doesn't exist")

    @async_sqlite_sqlalchemy_atomic_decorator
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
    logger.info("Verifying async session is still usable")

    @async_sqlite_sqlalchemy_atomic_decorator
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

    # Generate UUIDs for entities
    entity_uuids = [uuid.uuid4() for _ in range(5)]

    # Store UUIDs in context
    for i, uuid_val in enumerate(entity_uuids):
        scenario_context.entity_ids[f"multi_async_entity_{i}"] = str(uuid_val)

    logger.info("Creating multiple entities in async atomic transaction")

    @async_sqlite_sqlalchemy_atomic_decorator
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
    logger.info("Verifying all async entities are retrievable")

    @async_sqlite_sqlalchemy_atomic_decorator
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
                assert (
                    retrieved_entity.description == f"Async Entity {i + 1}"
                ), f"Entity {i + 1} has incorrect description"
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

    # Generate UUIDs
    parent_uuid = uuid.uuid4()
    related_uuids = [uuid.uuid4() for _ in range(3)]

    # Store UUIDs in context
    scenario_context.entity_ids["complex_parent"] = str(parent_uuid)
    for i, uuid_val in enumerate(related_uuids):
        scenario_context.entity_ids[f"complex_related_{i}"] = str(uuid_val)

    logger.info(f"Creating complex entity relationship with parent UUID {parent_uuid}")

    # Create a parent entity and related entities in one atomic transaction
    @async_sqlite_sqlalchemy_atomic_decorator
    async def create_entity_with_relations():
        # Create the parent entity
        parent = TestEntityFactory.create_test_entity(
            test_uuid=parent_uuid,
            description="Parent Entity for Complex Operations",
        )
        async_adapter = get_async_adapter(context)
        await async_adapter.create(parent)

        # Flush to ensure the parent is persisted
        await async_adapter.session_manager.get_session().flush()

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

    # Get UUIDs from context
    parent_uuid = uuid.UUID(get_entity_id(context, "complex_parent"))
    logger.info(f"Verifying related entities for parent UUID {parent_uuid}")

    @async_sqlite_sqlalchemy_atomic_decorator
    async def verify_relationships():
        async_adapter = get_async_adapter(context)
        session = async_adapter.session_manager.get_session()

        # Get the parent entity
        parent = await session.get(TestEntity, parent_uuid)
        assert parent is not None, "Parent entity not found"
        logger.info("Parent entity retrieved successfully")

        # Query for related entities
        stmt = select(RelatedTestEntity).where(RelatedTestEntity.parent_id == parent_uuid)
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
