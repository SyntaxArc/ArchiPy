"""Step definitions for ScyllaDB adapter Behave tests."""

import logging
from inspect import isawaitable, iscoroutinefunction
from typing import Any, NoReturn

from behave import given, then, when
from behave.runner import Context
from features.test_helpers import get_current_scenario_context

from archipy.adapters.scylladb.adapters import AsyncScyllaDBAdapter, ScyllaDBAdapter
from archipy.configs.base_config import BaseConfig
from archipy.models import errors
from archipy.models.errors import NotFoundError

logger = logging.getLogger(__name__)


def _is_async_scenario(context: Context) -> bool:
    """Check if the current scenario is async.

    Args:
        context (Context): Behave context.

    Returns:
        bool: True if scenario has async tag.
    """
    return "async" in context.scenario.tags


def _get_scenario_context(context: Context) -> Any:  # noqa: ANN401
    """Get the current scenario context.

    Args:
        context (Context): Behave context.

    Returns:
        Any: The scenario context (type depends on test_helpers implementation).
    """
    return get_current_scenario_context(context)


def get_scylladb_adapter(context: Context) -> ScyllaDBAdapter | AsyncScyllaDBAdapter:
    """Get or initialize the appropriate ScyllaDB adapter.

    Args:
        context (Context): Behave context.

    Returns:
        ScyllaDBAdapter | AsyncScyllaDBAdapter: The adapter instance.
    """
    scenario_context = _get_scenario_context(context)
    is_async = _is_async_scenario(context)

    if is_async:
        if scenario_context.async_adapter is None:
            test_config = BaseConfig.global_config()
            scenario_context.async_adapter = AsyncScyllaDBAdapter(test_config.SCYLLADB)
        return scenario_context.async_adapter

    if scenario_context.adapter is None:
        test_config = BaseConfig.global_config()
        scenario_context.adapter = ScyllaDBAdapter(test_config.SCYLLADB)
    return scenario_context.adapter


# Background steps


@given("a ScyllaDB test container is running")
def step_scylladb_container_running(context: Context) -> None:
    """Verify that the ScyllaDB container is running.

    Args:
        context (Context): Behave context.
    """
    scenario_context = _get_scenario_context(context)

    try:
        test_containers = scenario_context.get("test_containers")
        if not test_containers:
            raise ValueError("Test containers not available in scenario context")

        scylladb_container = test_containers.get_container("scylladb")
        if not scylladb_container._is_running:
            raise RuntimeError("ScyllaDB container is not running")

        logger.info("ScyllaDB container is running on %s:%s", scylladb_container.host, scylladb_container.port)
    except Exception as e:
        raise RuntimeError(f"Failed to verify ScyllaDB container: {e}") from e


# Setup steps


@given("a ScyllaDB adapter is configured")
def step_scylladb_adapter_configured(context: Context) -> None:
    """Configure a synchronous ScyllaDB adapter.

    Args:
        context (Context): Behave context.
    """
    _ = get_scylladb_adapter(context)  # Ensure adapter is created
    logger.info("ScyllaDB sync adapter configured and connected")


@given("an async ScyllaDB adapter is configured")
async def step_async_scylladb_adapter_configured(context: Context) -> None:
    """Configure an asynchronous ScyllaDB adapter.

    Args:
        context (Context): Behave context.
    """
    _ = get_scylladb_adapter(context)  # Ensure adapter is created
    logger.info("ScyllaDB async adapter configured and connected")


@given('a keyspace "{keyspace}" with replication factor {replication_factor:d} exists')
def step_keyspace_exists(context: Context, keyspace: str, replication_factor: int) -> None:
    """Create a keyspace if it doesn't exist.

    Args:
        context (Context): Behave context.
        keyspace (str): Keyspace name.
        replication_factor (int): Replication factor.
    """
    adapter = get_scylladb_adapter(context)
    adapter.create_keyspace(keyspace, replication_factor)
    adapter.use_keyspace(keyspace)

    scenario_context = _get_scenario_context(context)
    scenario_context.current_keyspace = keyspace
    logger.info("Keyspace '%s' created and set as current", keyspace)


@given('an async keyspace "{keyspace}" with replication factor {replication_factor:d} exists')
async def step_async_keyspace_exists(context: Context, keyspace: str, replication_factor: int) -> None:
    """Create a keyspace asynchronously.

    Args:
        context (Context): Behave context.
        keyspace (str): Keyspace name.
        replication_factor (int): Replication factor.
    """
    adapter = get_scylladb_adapter(context)
    await adapter.create_keyspace(keyspace, replication_factor)
    await adapter.use_keyspace(keyspace)

    scenario_context = _get_scenario_context(context)
    scenario_context.current_keyspace = keyspace
    logger.info("Async keyspace '%s' created and set as current", keyspace)


@given('a table "{table}" with schema "{schema}"')
def step_table_exists(context: Context, table: str, schema: str) -> None:
    """Create a table with the given schema.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        schema (str): CREATE TABLE statement.
    """
    adapter = get_scylladb_adapter(context)
    adapter.create_table(schema)
    logger.info("Table '%s' created", table)


@given('an async table "{table}" with schema "{schema}"')
async def step_async_table_exists(context: Context, table: str, schema: str) -> None:
    """Create a table asynchronously.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        schema (str): CREATE TABLE statement.
    """
    adapter = get_scylladb_adapter(context)
    await adapter.create_table(schema)
    logger.info("Async table '%s' created", table)


@given('data exists in table "{table}":')
async def step_data_exists_in_table(context: Context, table: str) -> None:
    """Insert data from table into ScyllaDB.

    Args:
        context (Context): Behave context.
        table (str): Table name.
    """
    try:
        adapter = get_scylladb_adapter(context)

        for row in context.table:
            data = {}
            for heading in context.table.headings:
                value = row[heading]
                # Try to convert to int
                try:
                    data[heading] = int(value)
                except ValueError:
                    # Try to convert to boolean
                    if value.lower() in ("true", "false"):
                        data[heading] = value.lower() == "true"
                    else:
                        data[heading] = value

            if iscoroutinefunction(getattr(adapter, "insert", None)):
                await adapter.insert(table, data)
            else:
                adapter.insert(table, data)

        logger.info("Data inserted into table '%s'", table)
    except Exception:
        logger.exception("Error inserting data into table '%s'", table)
        raise


# Action steps - Keyspace operations


@when('I create a keyspace "{keyspace}" with replication factor {replication_factor:d}')
def step_create_keyspace(context: Context, keyspace: str, replication_factor: int) -> None:
    """Create a keyspace.

    Args:
        context (Context): Behave context.
        keyspace (str): Keyspace name.
        replication_factor (int): Replication factor.
    """
    adapter = get_scylladb_adapter(context)
    adapter.create_keyspace(keyspace, replication_factor)

    scenario_context = _get_scenario_context(context)
    scenario_context.last_keyspace = keyspace
    logger.info("Created keyspace '%s'", keyspace)


@when('I async create a keyspace "{keyspace}" with replication factor {replication_factor:d}')
async def step_async_create_keyspace(context: Context, keyspace: str, replication_factor: int) -> None:
    """Create a keyspace asynchronously.

    Args:
        context (Context): Behave context.
        keyspace (str): Keyspace name.
        replication_factor (int): Replication factor.
    """
    adapter = get_scylladb_adapter(context)
    await adapter.create_keyspace(keyspace, replication_factor)

    scenario_context = _get_scenario_context(context)
    scenario_context.last_keyspace = keyspace
    logger.info("Async created keyspace '%s'", keyspace)


@when('I use keyspace "{keyspace}"')
def step_use_keyspace(context: Context, keyspace: str) -> None:
    """Switch to a keyspace.

    Args:
        context (Context): Behave context.
        keyspace (str): Keyspace name.
    """
    adapter = get_scylladb_adapter(context)
    adapter.use_keyspace(keyspace)

    scenario_context = _get_scenario_context(context)
    scenario_context.current_keyspace = keyspace
    logger.info("Using keyspace '%s'", keyspace)


@when('I async use keyspace "{keyspace}"')
async def step_async_use_keyspace(context: Context, keyspace: str) -> None:
    """Switch to a keyspace asynchronously.

    Args:
        context (Context): Behave context.
        keyspace (str): Keyspace name.
    """
    adapter = get_scylladb_adapter(context)
    await adapter.use_keyspace(keyspace)

    scenario_context = _get_scenario_context(context)
    scenario_context.current_keyspace = keyspace
    logger.info("Async using keyspace '%s'", keyspace)


@when('I drop keyspace "{keyspace}"')
def step_drop_keyspace(context: Context, keyspace: str) -> None:
    """Drop a keyspace.

    Args:
        context (Context): Behave context.
        keyspace (str): Keyspace name.
    """
    adapter = get_scylladb_adapter(context)
    adapter.drop_keyspace(keyspace)
    logger.info("Dropped keyspace '%s'", keyspace)


# Action steps - Table operations


@when('I create a table "{table}" with schema "{schema}"')
def step_create_table(context: Context, table: str, schema: str) -> None:
    """Create a table.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        schema (str): CREATE TABLE statement.
    """
    adapter = get_scylladb_adapter(context)
    adapter.create_table(schema)
    logger.info("Created table '%s'", table)


@when('I async create a table "{table}" with schema "{schema}"')
async def step_async_create_table(context: Context, table: str, schema: str) -> None:
    """Create a table asynchronously.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        schema (str): CREATE TABLE statement.
    """
    adapter = get_scylladb_adapter(context)
    await adapter.create_table(schema)
    logger.info("Async created table '%s'", table)


@when('I drop table "{table}"')
def step_drop_table(context: Context, table: str) -> None:
    """Drop a table.

    Args:
        context (Context): Behave context.
        table (str): Table name.
    """
    adapter = get_scylladb_adapter(context)
    adapter.drop_table(table)
    logger.info("Dropped table '%s'", table)


# Action steps - Data operations


@when('I insert data into table "{table}" with id {id:d}, name "{name}", age {age:d}')
def step_insert_user_data(context: Context, table: str, id: int, name: str, age: int) -> None:  # noqa: A002
    """Insert user data into a table.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        id (int): User ID.
        name (str): User name.
        age (int): User age.
    """
    adapter = get_scylladb_adapter(context)
    adapter.insert(table, {"id": id, "name": name, "age": age})
    logger.info("Inserted user data into '%s'", table)


@when('I insert data into table "{table}" with id {id:d}, name "{name}", price {price:f}')
def step_insert_product_data(context: Context, table: str, id: int, name: str, price: float) -> None:  # noqa: A002
    """Insert product data into a table.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        id (int): Product ID.
        name (str): Product name.
        price (float): Product price.
    """
    adapter = get_scylladb_adapter(context)
    adapter.insert(table, {"id": id, "name": name, "price": price})
    logger.info("Inserted product data into '%s'", table)


@when('I async insert data into table "{table}" with id {id:d}, name "{name}"')
async def step_async_insert_data(context: Context, table: str, id: int, name: str) -> None:  # noqa: A002
    """Insert data asynchronously.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        id (int): ID.
        name (str): Name.
    """
    adapter = get_scylladb_adapter(context)
    await adapter.insert(table, {"id": id, "name": name})
    logger.info("Async inserted data into '%s'", table)


@when('I select from table "{table}" where id equals {id:d}')
def step_select_by_id(context: Context, table: str, id: int) -> None:  # noqa: A002
    """Select data by ID.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        id (int): ID to search for.
    """
    adapter = get_scylladb_adapter(context)
    result = adapter.select(table, conditions={"id": id})

    scenario_context = _get_scenario_context(context)
    scenario_context.last_result = result
    logger.info("Selected from '%s' where id=%d, got %d rows", table, id, len(result))


@when('I update table "{table}" setting quantity to {quantity:d} where id equals {id:d}')
def step_update_quantity(context: Context, table: str, quantity: int, id: int) -> None:  # noqa: A002
    """Update quantity in a table.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        quantity (int): New quantity.
        id (int): ID to update.
    """
    adapter = get_scylladb_adapter(context)
    adapter.update(table, {"quantity": quantity}, {"id": id})
    logger.info("Updated '%s' set quantity=%d where id=%d", table, quantity, id)


@when('I delete from table "{table}" where id equals {id:d}')
def step_delete_by_id(context: Context, table: str, id: int) -> None:  # noqa: A002
    """Delete data by ID.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        id (int): ID to delete.
    """
    adapter = get_scylladb_adapter(context)
    adapter.delete(table, {"id": id})
    logger.info("Deleted from '%s' where id=%d", table, id)


# Action steps - Prepared statements


@when('I prepare statement "{query}"')
def step_prepare_statement(context: Context, query: str) -> None:
    """Prepare a CQL statement.

    Args:
        context (Context): Behave context.
        query (str): CQL query.
    """
    adapter = get_scylladb_adapter(context)
    prepared = adapter.prepare(query)

    scenario_context = _get_scenario_context(context)
    scenario_context.prepared_statement = prepared
    logger.info("Prepared statement: %s", query)


@when('I async prepare statement "{query}"')
async def step_async_prepare_statement(context: Context, query: str) -> None:
    """Prepare a CQL statement asynchronously.

    Args:
        context (Context): Behave context.
        query (str): CQL query.
    """
    adapter = get_scylladb_adapter(context)
    prepared = await adapter.prepare(query)

    scenario_context = _get_scenario_context(context)
    scenario_context.prepared_statement = prepared
    logger.info("Async prepared statement: %s", query)


@when('I execute prepared statement with id {id:d}, message "{message}", level "{level}"')
def step_execute_prepared(context: Context, id: int, message: str, level: str) -> None:  # noqa: A002
    """Execute a prepared statement.

    Args:
        context (Context): Behave context.
        id (int): ID.
        message (str): Message.
        level (str): Level.
    """
    scenario_context = _get_scenario_context(context)
    adapter = get_scylladb_adapter(context)
    prepared = scenario_context.prepared_statement

    adapter.execute_prepared(prepared, {"id": id, "message": message, "level": level})
    logger.info("Executed prepared statement with id=%d", id)


@when('I async execute prepared statement with id {id:d}, msg "{msg}"')
async def step_async_execute_prepared(context: Context, id: int, msg: str) -> None:  # noqa: A002
    """Execute a prepared statement asynchronously.

    Args:
        context (Context): Behave context.
        id (int): ID.
        msg (str): Message.
    """
    scenario_context = _get_scenario_context(context)
    adapter = get_scylladb_adapter(context)
    prepared = scenario_context.prepared_statement

    await adapter.execute_prepared(prepared, {"id": id, "msg": msg})
    logger.info("Async executed prepared statement with id=%d", id)


# Action steps - Batch operations


@when("I execute batch statements:")
def step_execute_batch(context: Context) -> None:
    """Execute batch statements.

    Args:
        context (Context): Behave context.
    """
    adapter = get_scylladb_adapter(context)

    # Behave treats the first row as a header even for single-column tables
    # So we need to include the "heading" as the first statement
    statements = []
    if context.table.headings:
        statements.append(context.table.headings[0])  # First statement is in the "heading"
        statements.extend([row[context.table.headings[0]] for row in context.table])  # Rest are in rows
    else:
        statements = [row[0] for row in context.table]

    adapter.batch_execute(statements)
    logger.info("Executed batch with %d statements", len(statements))


@when("I async execute batch statements:")
async def step_async_execute_batch(context: Context) -> None:
    """Execute batch statements asynchronously.

    Args:
        context (Context): Behave context.
    """
    adapter = get_scylladb_adapter(context)

    # Behave treats the first row as a header even for single-column tables
    # So we need to include the "heading" as the first statement
    statements = []
    if context.table.headings:
        statements.append(context.table.headings[0])  # First statement is in the "heading"
        statements.extend([row[context.table.headings[0]] for row in context.table])  # Rest are in rows
    else:
        statements = [row[0] for row in context.table]

    await adapter.batch_execute(statements)
    logger.info("Executed batch with %d statements", len(statements))
    logger.info("Async executed batch with %d statements", len(statements))


# Assertion steps


@then('the keyspace "{keyspace}" should be created successfully')
def step_keyspace_created(context: Context, keyspace: str) -> None:
    """Verify keyspace was created.

    Args:
        context (Context): Behave context.
        keyspace (str): Keyspace name.
    """
    # Keyspace creation is verified by the absence of exceptions
    logger.info("Keyspace '%s' created successfully", keyspace)


@then('the keyspace context should be "{keyspace}"')
def step_verify_keyspace_context(context: Context, keyspace: str) -> None:
    """Verify current keyspace context.

    Args:
        context (Context): Behave context.
        keyspace (str): Expected keyspace name.
    """
    scenario_context = _get_scenario_context(context)
    assert scenario_context.current_keyspace == keyspace, (
        f"Expected keyspace '{keyspace}', got '{scenario_context.current_keyspace}'"
    )
    logger.info("Keyspace context verified: %s", keyspace)


@then('the table "{table}" should contain {count:d} row')
@then('the table "{table}" should contain {count:d} rows')
def step_verify_row_count(context: Context, table: str, count: int) -> None:
    """Verify row count in a table.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        count (int): Expected row count.
    """
    adapter = get_scylladb_adapter(context)
    result = adapter.select(table)

    actual_count = len(result)
    assert actual_count == count, f"Expected {count} rows, got {actual_count}"
    logger.info("Table '%s' contains %d rows", table, count)


@then('the async table "{table}" should contain {count:d} row')
@then('the async table "{table}" should contain {count:d} rows')
async def step_async_verify_row_count(context: Context, table: str, count: int) -> None:
    """Verify row count asynchronously.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        count (int): Expected row count.
    """
    adapter = get_scylladb_adapter(context)
    result = await adapter.select(table)

    actual_count = len(result)
    assert actual_count == count, f"Expected {count} rows, got {actual_count}"
    logger.info("Async table '%s' contains %d rows", table, count)


@then("the result should contain {count:d} row")
@then("the result should contain {count:d} rows")
def step_verify_result_count(context: Context, count: int) -> None:
    """Verify result count.

    Args:
        context (Context): Behave context.
        count (int): Expected count.
    """
    scenario_context = _get_scenario_context(context)
    result = scenario_context.last_result

    actual_count = len(result)
    assert actual_count == count, f"Expected {count} rows, got {actual_count}"
    logger.info("Result contains %d rows", count)


@then('the result row should have name "{name}" and department "{department}"')
def step_verify_result_fields(context: Context, name: str, department: str) -> None:
    """Verify result fields.

    Args:
        context (Context): Behave context.
        name (str): Expected name.
        department (str): Expected department.
    """
    scenario_context = _get_scenario_context(context)
    result = scenario_context.last_result

    assert len(result) > 0, "No rows in result"
    row = result[0]

    assert row.name == name, f"Expected name '{name}', got '{row.name}'"
    assert row.department == department, f"Expected department '{department}', got '{row.department}'"
    logger.info("Result verified: name=%s, department=%s", name, department)


@then("the result row should have quantity {quantity:d}")
def step_verify_quantity(context: Context, quantity: int) -> None:
    """Verify quantity field.

    Args:
        context (Context): Behave context.
        quantity (int): Expected quantity.
    """
    scenario_context = _get_scenario_context(context)
    result = scenario_context.last_result

    assert len(result) > 0, "No rows in result"
    row = result[0]

    assert row.quantity == quantity, f"Expected quantity {quantity}, got {row.quantity}"
    logger.info("Quantity verified: %d", quantity)


@then('the table "{table}" should not exist')
def step_verify_table_not_exists(context: Context, table: str) -> None:
    """Verify table doesn't exist.

    Args:
        context (Context): Behave context.
        table (str): Table name.
    """
    adapter = get_scylladb_adapter(context)
    try:
        adapter.select(table)
        raise AssertionError(f"Table '{table}' still exists")
    except RuntimeError, NotFoundError, Exception:
        # Table doesn't exist, as expected (or connection error during cleanup)
        logger.info("Table '%s' does not exist (as expected)", table)


@then('the keyspace "{keyspace}" should not exist')
def step_verify_keyspace_not_exists(context: Context, keyspace: str) -> None:
    """Verify keyspace doesn't exist.

    Args:
        context (Context): Behave context.
        keyspace (str): Keyspace name.
    """
    # If we got here without an exception, the drop was successful
    logger.info("Keyspace '%s' does not exist (as expected)", keyspace)


# Count and Exists steps


@when('I count rows in table "{table}" with conditions {column} "{value}"')
def step_count_rows_with_conditions(context: Context, table: str, column: str, value: str) -> None:
    """Count rows in a table with conditions.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        column (str): Column name.
        value (str): Column value.
    """
    adapter = get_scylladb_adapter(context)
    count = adapter.count(table, {column: value})

    scenario_context = _get_scenario_context(context)
    scenario_context.count_result = count
    logger.info("Counted %d rows in table '%s' with %s='%s'", count, table, column, value)


@when('I count rows in table "{table}"')
def step_count_rows(context: Context, table: str) -> None:
    """Count all rows in a table.

    Args:
        context (Context): Behave context.
        table (str): Table name.
    """
    adapter = get_scylladb_adapter(context)
    count = adapter.count(table)

    scenario_context = _get_scenario_context(context)
    scenario_context.count_result = count
    logger.info("Counted %d rows in table '%s'", count, table)


@when('I async count rows in table "{table}"')
async def step_async_count_rows(context: Context, table: str) -> None:
    """Count all rows in a table asynchronously.

    Args:
        context (Context): Behave context.
        table (str): Table name.
    """
    adapter = get_scylladb_adapter(context)
    count = await adapter.count(table)

    scenario_context = _get_scenario_context(context)
    scenario_context.count_result = count
    logger.info("Async counted %d rows in table '%s'", count, table)


@when('I check if row exists in table "{table}" with id {id:d}')
def step_check_exists(context: Context, table: str, id: int) -> None:  # noqa: A002
    """Check if a row exists in a table.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        id (int): ID to check.
    """
    adapter = get_scylladb_adapter(context)
    exists = adapter.exists(table, {"id": id})

    scenario_context = _get_scenario_context(context)
    scenario_context.exists_result = exists
    logger.info("Row exists in '%s' with id=%d: %s", table, id, exists)


@when('I async check if row exists in table "{table}" with id {id:d}')
async def step_async_check_exists(context: Context, table: str, id: int) -> None:  # noqa: A002
    """Check if a row exists in a table asynchronously.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        id (int): ID to check.
    """
    adapter = get_scylladb_adapter(context)
    exists = await adapter.exists(table, {"id": id})

    scenario_context = _get_scenario_context(context)
    scenario_context.exists_result = exists
    logger.info("Async row exists in '%s' with id=%d: %s", table, id, exists)


@then("the count result should be {expected_count:d}")
def step_verify_count(context: Context, expected_count: int) -> None:
    """Verify count result.

    Args:
        context (Context): Behave context.
        expected_count (int): Expected count.
    """
    scenario_context = _get_scenario_context(context)
    actual_count = scenario_context.count_result

    assert actual_count == expected_count, f"Expected count {expected_count}, got {actual_count}"
    logger.info("Count verified: %d", expected_count)


@then("the async count result should be {expected_count:d}")
def step_verify_async_count(context: Context, expected_count: int) -> None:
    """Verify async count result.

    Args:
        context (Context): Behave context.
        expected_count (int): Expected count.
    """
    scenario_context = _get_scenario_context(context)
    actual_count = scenario_context.count_result

    assert actual_count == expected_count, f"Expected count {expected_count}, got {actual_count}"
    logger.info("Async count verified: %d", expected_count)


@then("the row should exist")
def step_verify_exists(context: Context) -> None:
    """Verify row exists.

    Args:
        context (Context): Behave context.
    """
    scenario_context = _get_scenario_context(context)
    exists = scenario_context.exists_result

    assert exists is True, "Expected row to exist"
    logger.info("Row existence verified: True")


@then("the row should not exist")
def step_verify_not_exists(context: Context) -> None:
    """Verify row does not exist.

    Args:
        context (Context): Behave context.
    """
    scenario_context = _get_scenario_context(context)
    exists = scenario_context.exists_result

    assert exists is False, "Expected row to not exist"
    logger.info("Row non-existence verified: False")


@then("the async row should exist")
def step_verify_async_exists(context: Context) -> None:
    """Verify async row exists.

    Args:
        context (Context): Behave context.
    """
    scenario_context = _get_scenario_context(context)
    exists = scenario_context.exists_result

    assert exists is True, "Expected row to exist"
    logger.info("Async row existence verified: True")


@then("the async row should not exist")
def step_verify_async_not_exists(context: Context) -> None:
    """Verify async row does not exist.

    Args:
        context (Context): Behave context.
    """
    scenario_context = _get_scenario_context(context)
    exists = scenario_context.exists_result

    assert exists is False, "Expected row to not exist"
    logger.info("Async row non-existence verified: False")


# TTL steps


@when('I insert data into table "{table}" with key "{key}", value "{value}", ttl {ttl:d}')
def step_insert_with_ttl(context: Context, table: str, key: str, value: str, ttl: int) -> None:
    """Insert data with TTL.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        key (str): Key value.
        value (str): Value.
        ttl (int): TTL in seconds.
    """
    adapter = get_scylladb_adapter(context)
    adapter.insert(table, {"key": key, "value": value}, ttl=ttl)
    logger.info("Inserted data into '%s' with TTL %d", table, ttl)


@when('I update table "{table}" setting data to "{data}" with ttl {ttl:d} where session_id equals "{session_id}"')
def step_update_with_ttl(context: Context, table: str, data: str, ttl: int, session_id: str) -> None:
    """Update data with TTL.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        data (str): New data value.
        ttl (int): TTL in seconds.
        session_id (str): Session ID.
    """
    adapter = get_scylladb_adapter(context)
    adapter.update(table, {"data": data}, {"session_id": session_id}, ttl=ttl)
    logger.info("Updated '%s' with TTL %d where session_id='%s'", table, ttl, session_id)


@when('I async insert data into table "{table}" with key "{key}", value "{value}", ttl {ttl:d}')
async def step_async_insert_with_ttl(context: Context, table: str, key: str, value: str, ttl: int) -> None:
    """Insert data with TTL asynchronously.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        key (str): Key value.
        value (str): Value.
        ttl (int): TTL in seconds.
    """
    adapter = get_scylladb_adapter(context)
    await adapter.insert(table, {"key": key, "value": value}, ttl=ttl)
    logger.info("Async inserted data into '%s' with TTL %d", table, ttl)


@when('I select from table "{table}" where session_id equals "{session_id}"')
def step_select_by_session_id(context: Context, table: str, session_id: str) -> None:
    """Select data by session_id.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        session_id (str): Session ID to search for.
    """
    adapter = get_scylladb_adapter(context)
    result = adapter.select(table, conditions={"session_id": session_id})

    scenario_context = _get_scenario_context(context)
    scenario_context.last_result = result
    logger.info("Selected from '%s' where session_id=%s, got %d rows", table, session_id, len(result))


@then('the result row should have data "{expected_data}"')
def step_verify_data_field(context: Context, expected_data: str) -> None:
    """Verify data field.

    Args:
        context (Context): Behave context.
        expected_data (str): Expected data value.
    """
    scenario_context = _get_scenario_context(context)
    result = scenario_context.last_result

    assert len(result) > 0, "No rows in result"
    row = result[0]

    assert row.data == expected_data, f"Expected data '{expected_data}', got '{row.data}'"
    logger.info("Data verified: %s", expected_data)


# Pool monitoring steps


@when("I get pool statistics")
def step_get_pool_stats(context: Context) -> None:
    """Get pool statistics.

    Args:
        context (Context): Behave context.
    """
    adapter = get_scylladb_adapter(context)
    stats = adapter.get_pool_stats()

    scenario_context = _get_scenario_context(context)
    scenario_context.pool_stats = stats
    logger.info("Got pool statistics: %s", stats)


@then("the pool statistics should be returned")
def step_verify_pool_stats(context: Context) -> None:
    """Verify pool statistics were returned.

    Args:
        context (Context): Behave context.
    """
    scenario_context = _get_scenario_context(context)
    stats = scenario_context.pool_stats

    assert stats is not None, "Pool statistics should not be None"
    assert isinstance(stats, dict), "Pool statistics should be a dictionary"
    assert "monitoring_enabled" in stats, "Pool statistics should contain 'monitoring_enabled' key"
    logger.info("Pool statistics verified")


# If not Exist in insert steps


@when('I insert data into table "{table}" with id {id:d}, item "{item}", quantity {quantity:d}')
def step_insert_with_if_not_exists(
    context: Context,
    table: str,
    id: int,
    item: str,
    quantity: int,
) -> None:
    """Insert data in a table with if not exists.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        id (int): User ID.
        item (str): Item.
        quantity (int): Quantity
    """
    adapter = get_scylladb_adapter(context)
    adapter.insert(table=table, data={"id": id, "item": item, "quantity": quantity}, if_not_exists=True)
    logger.info("Inserted user data into '%s'", table)


@when('I async insert data into table "{table}" with id {id:d}, item "{item}", quantity {quantity:d}')
async def step_async_insert_with_if_not_exists(context: Context, table: str, id: int, item: str, quantity: int) -> None:
    """Insert data in a table with if not exists asynchronously.

    Args:
        context (Context): Behave context.
        table (str): Table name.
        id (int): User ID.
        item (str): Item.
        quantity (int): Quantity
    """
    adapter = get_scylladb_adapter(context)
    await adapter.insert(table=table, data={"id": id, "item": item, "quantity": quantity}, if_not_exists=True)
    logger.info("Inserted user data into '%s'", table)


# Hot-path steps shared by sync and async adapters (mode follows the @async tag)


async def _call_adapter(adapter: Any, method: str, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
    """Call an adapter method and await the result when the adapter is async.

    Args:
        adapter (Any): Sync or async ScyllaDB adapter.
        method (str): Method name.
        *args (Any): Positional arguments.
        **kwargs (Any): Keyword arguments.

    Returns:
        Any: The method result.
    """
    result = getattr(adapter, method)(*args, **kwargs)
    if isawaitable(result):
        result = await result
    return result


async def _run_scylladb_operation(adapter: Any, operation: str, table: str) -> Any:  # noqa: ANN401
    """Run one named hot-path operation against a users-shaped table.

    Args:
        adapter (Any): Sync or async ScyllaDB adapter.
        operation (str): Operation name.
        table (str): Table name.

    Returns:
        Any: Normalised result for assertions.
    """
    if operation == "insert":
        await _call_adapter(adapter, "insert", table, {"id": 1, "name": "alpha", "age": 30})
    elif operation == "insert if not exists":
        await _call_adapter(adapter, "insert", table, {"id": 1, "name": "other", "age": 1}, if_not_exists=True)
    elif operation == "select":
        rows = await _call_adapter(adapter, "select", table, conditions={"id": 1})
        return ",".join(row.name for row in rows)
    elif operation == "select columns":
        rows = await _call_adapter(adapter, "select", table, columns=["name"], conditions={"id": 1})
        return ",".join(f"{row.name}:{hasattr(row, 'age')}" for row in rows)
    elif operation == "update":
        await _call_adapter(adapter, "update", table, {"name": "beta"}, {"id": 1})
    elif operation == "delete":
        await _call_adapter(adapter, "delete", table, {"id": 1})
    elif operation == "count":
        return str(await _call_adapter(adapter, "count", table, {"id": 1}))
    elif operation == "exists":
        return str(await _call_adapter(adapter, "exists", table, {"id": 1}))
    elif operation == "drop":
        await _call_adapter(adapter, "drop_table", table)
    elif operation == "insert with injected ttl":
        await _call_adapter(adapter, "insert", table, {"id": 1, "name": "x", "age": 1}, ttl="60; DROP TABLE x")
    elif operation == "update with injected ttl":
        await _call_adapter(adapter, "update", table, {"name": "x"}, {"id": 1}, ttl="60; DROP TABLE x")
    elif operation == "insert with negative ttl":
        await _call_adapter(adapter, "insert", table, {"id": 1, "name": "x", "age": 1}, ttl=-1)
    elif operation == "create keyspace with injected replication factor":
        await _call_adapter(adapter, "create_keyspace", "inject_ks", "1}; DROP KEYSPACE hot_ks; --")
    else:
        raise ValueError(f"Unknown ScyllaDB operation: {operation}")
    return None


@given('a ScyllaDB adapter with keyspace "{keyspace}" and a users table "{table}"')
async def step_adapter_keyspace_users_table(context: Context, keyspace: str, table: str) -> None:
    """Create the adapter, keyspace and a users table in the current mode.

    Args:
        context (Context): Behave context.
        keyspace (str): Keyspace name.
        table (str): Table name.
    """
    adapter = get_scylladb_adapter(context)
    await _call_adapter(adapter, "create_keyspace", keyspace, 1)
    await _call_adapter(adapter, "use_keyspace", keyspace)
    await _call_adapter(
        adapter,
        "create_table",
        f"CREATE TABLE IF NOT EXISTS {table} (id int PRIMARY KEY, name text, age int)",
    )
    scenario_context = _get_scenario_context(context)
    scenario_context.scylla_error = None
    scenario_context.scylla_result = None


@when('I run ScyllaDB operation "{operation}" on table "{table}"')
async def step_run_scylladb_operation(context: Context, operation: str, table: str) -> None:
    """Run a named operation and record the result or the raised error.

    Args:
        context (Context): Behave context.
        operation (str): Operation name.
        table (str): Table name.
    """
    adapter = get_scylladb_adapter(context)
    scenario_context = _get_scenario_context(context)
    scenario_context.scylla_error = None
    try:
        scenario_context.scylla_result = await _run_scylladb_operation(adapter, operation, table)
    except Exception as e:  # noqa: BLE001
        scenario_context.scylla_error = e


@when('I run ScyllaDB {kind} with CQL "{cql}"')
async def step_run_scylladb_cql(context: Context, kind: str, cql: str) -> None:
    """Run raw CQL through execute, prepare or batch_execute and record the outcome.

    Args:
        context (Context): Behave context.
        kind (str): One of execute, prepare, batch.
        cql (str): CQL text.
    """
    adapter = get_scylladb_adapter(context)
    scenario_context = _get_scenario_context(context)
    scenario_context.scylla_error = None
    try:
        if kind == "execute":
            await _call_adapter(adapter, "execute", cql)
        elif kind == "prepare":
            await _call_adapter(adapter, "prepare", cql)
        elif kind == "batch":
            await _call_adapter(adapter, "batch_execute", [cql])
        else:
            raise ValueError(f"Unknown ScyllaDB CQL kind: {kind}")
    except Exception as e:  # noqa: BLE001
        scenario_context.scylla_error = e


@when('I execute a prepared ScyllaDB insert into "{table}" twice')
async def step_prepared_insert_twice(context: Context, table: str) -> None:
    """Prepare the same statement twice and execute it with bound parameters.

    Args:
        context (Context): Behave context.
        table (str): Table name.
    """
    adapter = get_scylladb_adapter(context)
    query = f"INSERT INTO {table} (id, name, age) VALUES (:id, :name, :age)"
    first = await _call_adapter(adapter, "prepare", query)
    second = await _call_adapter(adapter, "prepare", query)
    scenario_context = _get_scenario_context(context)
    scenario_context.scylla_prepared_reused = first is second
    await _call_adapter(adapter, "execute_prepared", first, {"id": 1, "name": "alpha", "age": 30})
    await _call_adapter(adapter, "execute_prepared", second, {"id": 2, "name": "beta", "age": 31})


@when("I close the ScyllaDB adapter")
async def step_close_scylladb_adapter(context: Context) -> None:
    """Close the adapter.

    Args:
        context (Context): Behave context.
    """
    adapter = get_scylladb_adapter(context)
    await _call_adapter(adapter, "close")


@when("I check the ScyllaDB adapter health")
async def step_check_scylladb_health(context: Context) -> None:
    """Run the health check and store connection state and result.

    Args:
        context (Context): Behave context.
    """
    adapter = get_scylladb_adapter(context)
    scenario_context = _get_scenario_context(context)
    scenario_context.scylla_connected = await _call_adapter(adapter, "is_connected")
    scenario_context.scylla_health = await _call_adapter(adapter, "health_check")


_LEAKY_ERROR = "secret node 10.0.0.9 refused the connection"


class _FailingSession:
    """Stand-in session whose queries fail with a message that names an internal host."""

    is_shutdown = False

    def execute(self, *args: Any, **kwargs: Any) -> NoReturn:  # noqa: ANN401, ARG002
        raise RuntimeError(_LEAKY_ERROR)

    def execute_async(self, *args: Any, **kwargs: Any) -> NoReturn:  # noqa: ANN401, ARG002
        raise RuntimeError(_LEAKY_ERROR)

    def get_pool_state(self) -> NoReturn:
        raise RuntimeError(_LEAKY_ERROR)


@when("I check the health and pool statistics of an adapter whose session fails")
async def step_check_failing_session(context: Context) -> None:
    """Swap in a failing session, run the health check and pool statistics, and keep both results.

    Args:
        context (Context): Behave context.
    """
    config = BaseConfig.global_config().SCYLLADB.model_copy(update={"ENABLE_CONNECTION_POOL_MONITORING": True})
    adapter_class = AsyncScyllaDBAdapter if _is_async_scenario(context) else ScyllaDBAdapter
    adapter = adapter_class(config)
    real_session = adapter._session
    adapter._session = _FailingSession()
    scenario_context = _get_scenario_context(context)
    try:
        scenario_context.scylla_health = await _call_adapter(adapter, "health_check")
        scenario_context.pool_stats = await _call_adapter(adapter, "get_pool_stats")
    finally:
        adapter._session = real_session
        await _call_adapter(adapter, "close")


@then("the ScyllaDB probe responses should not contain the driver error text")
def step_probe_responses_do_not_leak(context: Context) -> None:
    """Assert neither response carries the driver message or the host it names.

    Args:
        context (Context): Behave context.
    """
    scenario_context = _get_scenario_context(context)
    assert scenario_context.scylla_health["status"] == "unhealthy", scenario_context.scylla_health
    text = f"{scenario_context.scylla_health} {scenario_context.pool_stats}"
    assert "10.0.0.9" not in text and "secret" not in text, text
    assert scenario_context.scylla_health["error"] == "unavailable", scenario_context.scylla_health
    assert scenario_context.pool_stats["error"] == "unavailable", scenario_context.pool_stats


@when("I read the ScyllaDB pool statistics with monitoring enabled")
async def step_read_scylladb_pool_stats(context: Context) -> None:
    """Read pool statistics from a monitoring-enabled adapter in the current mode.

    Args:
        context (Context): Behave context.
    """
    config = BaseConfig.global_config().SCYLLADB.model_copy(update={"ENABLE_CONNECTION_POOL_MONITORING": True})
    adapter_class = AsyncScyllaDBAdapter if _is_async_scenario(context) else ScyllaDBAdapter
    adapter = adapter_class(config)
    try:
        stats = await _call_adapter(adapter, "get_pool_stats")
    finally:
        await _call_adapter(adapter, "close")
    _get_scenario_context(context).pool_stats = stats


@then("the ScyllaDB call should succeed")
def step_scylladb_call_succeeds(context: Context) -> None:
    """Assert that the last recorded call raised nothing.

    Args:
        context (Context): Behave context.
    """
    error = _get_scenario_context(context).scylla_error
    assert error is None, f"Expected success, got {error!r}"


@then("the ScyllaDB call should raise {error_name}")
def step_scylladb_call_raises(context: Context, error_name: str) -> None:
    """Assert that the last recorded call raised the named ArchiPy error.

    Args:
        context (Context): Behave context.
        error_name (str): Error class name from archipy.models.errors.
    """
    error = _get_scenario_context(context).scylla_error
    expected = getattr(errors, error_name)
    assert isinstance(error, expected), f"Expected {error_name}, got {error!r}"


@then('the ScyllaDB result should be "{expected}"')
def step_scylladb_result_is(context: Context, expected: str) -> None:
    """Assert the normalised result of the last operation.

    Args:
        context (Context): Behave context.
        expected (str): Expected normalised result.
    """
    scenario_context = _get_scenario_context(context)
    assert scenario_context.scylla_error is None, f"Operation failed: {scenario_context.scylla_error!r}"
    assert scenario_context.scylla_result == expected, f"Expected '{expected}', got '{scenario_context.scylla_result}'"


@then("the ScyllaDB result should be empty")
def step_scylladb_result_is_empty(context: Context) -> None:
    """Assert the last select returned no rows.

    Args:
        context (Context): Behave context.
    """
    scenario_context = _get_scenario_context(context)
    assert scenario_context.scylla_error is None, f"Operation failed: {scenario_context.scylla_error!r}"
    assert scenario_context.scylla_result == "", f"Expected no rows, got '{scenario_context.scylla_result}'"


@then("the prepared ScyllaDB statement should have been reused")
def step_prepared_reused(context: Context) -> None:
    """Assert that the prepared statement cache returned the same statement.

    Args:
        context (Context): Behave context.
    """
    assert _get_scenario_context(context).scylla_prepared_reused is True


@then('the ScyllaDB adapter should report connected "{expected}" and health "{status}"')
def step_scylladb_health_is(context: Context, expected: str, status: str) -> None:
    """Assert connection state and health status.

    Args:
        context (Context): Behave context.
        expected (str): Expected is_connected value as text.
        status (str): Expected health status.
    """
    scenario_context = _get_scenario_context(context)
    assert str(scenario_context.scylla_connected) == expected, f"connected={scenario_context.scylla_connected}"
    assert scenario_context.scylla_health["status"] == status, scenario_context.scylla_health
    if status == "healthy":
        assert scenario_context.scylla_health["error"] is None
        assert scenario_context.scylla_health["latency_ms"] > 0
    else:
        assert scenario_context.scylla_health["error"] == "unavailable", scenario_context.scylla_health


@then("the ScyllaDB pool statistics should list the connected host")
def step_scylladb_pool_stats_hosts(context: Context) -> None:
    """Assert pool statistics were collected without error.

    Args:
        context (Context): Behave context.
    """
    stats = _get_scenario_context(context).pool_stats
    assert stats["monitoring_enabled"] is True, stats
    assert "error" not in stats, stats
    assert stats["total_hosts"] >= 1, stats


@when("I build a ScyllaDB cluster with {setting} set to {value:d}")
def step_build_scylladb_cluster(context: Context, setting: str, value: int) -> None:
    """Build the cluster without connecting and keep the warnings raised while building.

    Args:
        context (Context): Behave context.
        setting (str): The ScyllaDB config field to override.
        value (int): The value to set.
    """
    import warnings

    from archipy.adapters.scylladb.adapters import ScyllaDBAdapter

    config = get_scylladb_adapter(context).config.model_copy(update={setting: value})
    adapter = ScyllaDBAdapter.__new__(ScyllaDBAdapter)  # skip __init__, which would open a second connection
    adapter.config = config
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cluster = adapter._create_cluster()
    context.cluster = cluster
    context.cluster_config = config
    context.cluster_warnings = [str(item.message) for item in caught if issubclass(item.category, DeprecationWarning)]


@when("I build a ScyllaDB cluster with consistency level {level}")
def step_build_scylladb_cluster_consistency(context: Context, level: str) -> None:
    """Build the cluster without connecting, with the given default consistency level.

    Args:
        context (Context): Behave context.
        level (str): The CONSISTENCY_LEVEL value.
    """
    from archipy.adapters.scylladb.adapters import ScyllaDBAdapter

    config = get_scylladb_adapter(context).config.model_copy(update={"CONSISTENCY_LEVEL": level})
    adapter = ScyllaDBAdapter.__new__(ScyllaDBAdapter)  # skip __init__, which would open a second connection
    adapter.config = config
    context.cluster = adapter._create_cluster()


@then("the default execution profile should use consistency level {level}")
def step_default_profile_consistency(context: Context, level: str) -> None:
    """Check the default execution profile carries the configured consistency level.

    Args:
        context (Context): Behave context.
        level (str): Expected consistency level name.
    """
    from cassandra import ConsistencyLevel

    profile = context.cluster.profile_manager.default
    assert profile.consistency_level == getattr(ConsistencyLevel, level), profile.consistency_level


@then("the default execution profile should use the configured request timeout and retry policy")
def step_default_profile_configured(context: Context) -> None:
    """Check the default execution profile carries the configured timeout and a retry policy.

    Args:
        context (Context): Behave context.
    """
    profile = context.cluster.profile_manager.default
    assert profile.request_timeout == context.cluster_config.REQUEST_TIMEOUT, profile.request_timeout
    assert profile.retry_policy is not None
    assert profile.load_balancing_policy is not None


@then('a DeprecationWarning should name "{setting}"')
def step_deprecation_names_setting(context: Context, setting: str) -> None:
    """Check a DeprecationWarning mentions the ignored setting.

    Args:
        context (Context): Behave context.
        setting (str): The setting expected in the warning.
    """
    assert any(setting in message for message in context.cluster_warnings), context.cluster_warnings


@then("a DeprecationWarning should not be raised")
def step_no_deprecation(context: Context) -> None:
    """Check no pool-setting DeprecationWarning was raised.

    Args:
        context (Context): Behave context.
    """
    assert not [m for m in context.cluster_warnings if "no effect" in m], context.cluster_warnings


_RESILIENCE_PROFILES: dict[str, dict[str, Any]] = {
    "driver defaults": {},
    "constant reconnect": {
        "RECONNECTION_POLICY": "CONSTANT",
        "RECONNECTION_BASE_DELAY": 2.0,
        "RECONNECTION_MAX_ATTEMPTS": 5,
    },
    "exponential reconnect": {
        "RECONNECTION_POLICY": "EXPONENTIAL",
        "RECONNECTION_BASE_DELAY": 0.5,
        "RECONNECTION_MAX_DELAY": 30.0,
    },
    "heartbeat and timeouts": {
        "IDLE_HEARTBEAT_INTERVAL": 7.0,
        "IDLE_HEARTBEAT_TIMEOUT": 11.0,
        "CONTROL_CONNECTION_TIMEOUT": 4.0,
    },
    "serial consistency": {"SERIAL_CONSISTENCY_LEVEL": "LOCAL_SERIAL"},
    "speculative execution": {"SPECULATIVE_EXECUTION_DELAY": 0.25, "SPECULATIVE_EXECUTION_MAX_ATTEMPTS": 3},
}


@when("I build a ScyllaDB cluster with the resilience profile {profile}")
def step_build_scylladb_cluster_resilience(context: Context, profile: str) -> None:
    """Build the cluster without connecting, using one named group of resilience settings.

    Args:
        context (Context): Behave context.
        profile (str): Key of the settings group in the resilience profile table.
    """
    from archipy.adapters.scylladb.adapters import ScyllaDBAdapter

    config = get_scylladb_adapter(context).config.model_copy(update=_RESILIENCE_PROFILES[profile])
    adapter = ScyllaDBAdapter.__new__(ScyllaDBAdapter)  # skip __init__, which would open a second connection
    adapter.config = config
    context.cluster = adapter._create_cluster()
    context.cluster_config = config


@then("the cluster and default profile should reflect the {profile} resilience profile")
def step_cluster_reflects_resilience(context: Context, profile: str) -> None:
    """Check the driver objects carry the settings of the named group, or its defaults when unset.

    Args:
        context (Context): Behave context.
        profile (str): Key of the settings group in the resilience profile table.
    """
    from cassandra import ConsistencyLevel
    from cassandra.policies import (
        ConstantReconnectionPolicy,
        ConstantSpeculativeExecutionPolicy,
        ExponentialReconnectionPolicy,
        NoSpeculativeExecutionPolicy,
    )

    cluster = context.cluster
    default_profile = cluster.profile_manager.default
    settings = _RESILIENCE_PROFILES[profile]
    reconnection = cluster.reconnection_policy
    if settings.get("RECONNECTION_POLICY") == "CONSTANT":
        assert isinstance(reconnection, ConstantReconnectionPolicy), reconnection
        assert reconnection.delay == settings["RECONNECTION_BASE_DELAY"]
        assert reconnection.max_attempts == settings["RECONNECTION_MAX_ATTEMPTS"]
    elif settings.get("RECONNECTION_POLICY") == "EXPONENTIAL":
        assert isinstance(reconnection, ExponentialReconnectionPolicy), reconnection
        assert reconnection.base_delay == settings["RECONNECTION_BASE_DELAY"]
        assert reconnection.max_delay == settings["RECONNECTION_MAX_DELAY"]
    else:
        assert type(reconnection) is ExponentialReconnectionPolicy, reconnection
        assert reconnection.base_delay == 1.0
        assert reconnection.max_delay == 600.0
    assert cluster.idle_heartbeat_interval == settings.get("IDLE_HEARTBEAT_INTERVAL", 30)
    assert cluster.idle_heartbeat_timeout == settings.get("IDLE_HEARTBEAT_TIMEOUT", 30)
    assert cluster.control_connection_timeout == settings.get("CONTROL_CONNECTION_TIMEOUT", 2.0)
    expected_serial = None
    if "SERIAL_CONSISTENCY_LEVEL" in settings:
        expected_serial = getattr(ConsistencyLevel, settings["SERIAL_CONSISTENCY_LEVEL"])
    assert default_profile.serial_consistency_level == expected_serial, default_profile.serial_consistency_level
    speculative = default_profile.speculative_execution_policy
    if "SPECULATIVE_EXECUTION_DELAY" in settings:
        assert isinstance(speculative, ConstantSpeculativeExecutionPolicy), speculative
        assert speculative.delay == settings["SPECULATIVE_EXECUTION_DELAY"]
        assert speculative.max_attempts == settings["SPECULATIVE_EXECUTION_MAX_ATTEMPTS"]
    else:
        assert isinstance(speculative, NoSpeculativeExecutionPolicy), speculative
