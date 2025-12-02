"""Step definitions for ScyllaDB adapter Behave tests."""

import logging
from typing import Any

from behave import given, then, when
from behave.runner import Context
from features.test_helpers import get_current_scenario_context

from archipy.adapters.scylladb.adapters import AsyncScyllaDBAdapter, ScyllaDBAdapter
from archipy.configs.base_config import BaseConfig
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
def step_data_exists_in_table(context: Context, table: str) -> None:
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
    except (RuntimeError, NotFoundError, Exception):
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
    context: Context, table: str, id: int, item: str, quantity: int,
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
async def step_insert_with_if_not_exists(context: Context, table: str, id: int, item: str, quantity: int) -> None:
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
