"""Implementation of steps for testing RedisMock and AsyncRedisMock.

This module contains step definitions for simplified synchronous and asynchronous
Redis mock scenarios as defined in the Redis Mock Testing feature.
"""

import logging

from behave import given, then, when
from features.test_helpers import get_current_scenario_context

from archipy.adapters.redis.mocks import AsyncRedisMock, RedisMock
from archipy.configs.config_template import RedisConfig


def store_result(context, key, value):
    """Store a result in the scenario context for later retrieval."""
    scenario_context = get_current_scenario_context(context)
    scenario_context.store(key, value)
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    logger.info(f"Stored result with key '{key}'")


def get_result(context, key):
    """Retrieve a result from the scenario context."""
    scenario_context = get_current_scenario_context(context)
    return scenario_context.get(key)


# Setup steps
@given("a configured Redis mock")
def step_given_configured_redis_mock(context):
    """Set up a RedisMock instance for testing."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)

    logger.info("Configuring RedisMock")
    redis_config = RedisConfig(
        MASTER_HOST="localhost",
        PORT=6379,
        DATABASE=0,
        DECODE_RESPONSES=True,
    )
    redis_mock = RedisMock(redis_config=redis_config)
    scenario_context.adapter = redis_mock
    logger.info("RedisMock configured successfully")


@given("a configured async Redis mock")
def step_given_configured_async_redis_mock(context):
    """Set up an AsyncRedisMock instance for testing."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)

    logger.info("Configuring AsyncRedisMock")
    redis_config = RedisConfig(
        MASTER_HOST="localhost",
        PORT=6379,
        DATABASE=0,
        DECODE_RESPONSES=True,
    )
    async_redis_mock = AsyncRedisMock(redis_config=redis_config)
    scenario_context.async_adapter = async_redis_mock
    logger.info("AsyncRedisMock configured successfully")


# Synchronous Redis Mock Steps
@when('I store the key "{key}" with value "{value}" in Redis mock')
def step_when_store_key_in_redis_mock(context, key, value):
    """Store a key-value pair in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_mock = scenario_context.adapter

    logger.info(f"Storing key '{key}' with value '{value}' in Redis mock")
    result = redis_mock.set(key, value)
    store_result(context, f"store_result_{key}", result)


@then("the sync store operation should succeed")
def step_then_sync_store_operation_succeeds(context):
    """Verify the sync store operation succeeded."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "store the key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else None
    result = get_result(context, f"store_result_{key}")
    expected_value = prev_step.name.split('"')[3] if prev_step else None

    logger.info(f"Verifying sync store operation for key '{key}'")
    assert result in (True, None), f"Sync store operation failed for key '{key}': returned {result}"
    value = scenario_context.adapter.get(key)
    assert value == expected_value, f"Key '{key}' not stored correctly: expected '{expected_value}', got '{value}'"
    logger.info("Sync store operation verified as successful")


@when('I retrieve the value for key "{key}" from Redis mock')
def step_when_retrieve_key_from_redis_mock(context, key):
    """Retrieve a value from the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_mock = scenario_context.adapter

    logger.info(f"Retrieving value for key '{key}' from Redis mock")
    value = redis_mock.get(key)
    store_result(context, f"retrieve_result_{key}", value)


@then('the sync retrieved value should be "{expected_value}"')
def step_then_sync_retrieved_value_is(context, expected_value):
    """Verify the sync retrieved value matches the expected value."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "retrieve the value" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else None
    retrieved_value = get_result(context, f"retrieve_result_{key}")

    logger.info(f"Verifying sync retrieved value for key '{key}' is '{expected_value}'")
    assert retrieved_value == expected_value, f"Expected '{expected_value}', got '{retrieved_value}'"
    logger.info("Sync retrieved value verified successfully")


@when('I remove the key "{key}" from Redis mock')
def step_when_remove_key_from_redis_mock(context, key):
    """Remove a key from the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_mock = scenario_context.adapter

    logger.info(f"Removing key '{key}' from Redis mock")
    result = redis_mock.delete(key)
    store_result(context, f"remove_result_{key}", result)


@then("the sync remove operation should delete one key")
def step_then_sync_remove_operation_deletes_one(context):
    """Verify the sync remove operation deleted one key."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "remove the key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "session-token"
    result = get_result(context, f"remove_result_{key}")

    logger.info(f"Verifying sync remove operation for key '{key}'")
    assert result == 1, f"Sync remove operation returned {result}, expected 1"
    logger.info("Sync remove operation verified successfully")


@when('I check if "{key}" exists in Redis mock')
def step_when_check_key_exists_in_redis_mock(context, key):
    """Check if a key exists in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_mock = scenario_context.adapter

    logger.info(f"Checking if key '{key}' exists in Redis mock")
    result = redis_mock.exists(key)
    store_result(context, f"exists_result_{key}", result)


@then("the sync key should not exist")
def step_then_sync_key_does_not_exist(context):
    """Verify the sync key does not exist."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "check if" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "session-token"
    result = get_result(context, f"exists_result_{key}")

    logger.info(f"Verifying sync key '{key}' does not exist")
    assert result == 0, f"Sync key '{key}' exists, expected it to be absent (result: {result})"
    logger.info("Sync key absence verified successfully")


@when('I add "{values}" to the list "{list_name}" in Redis mock')
def step_when_add_to_list_in_redis_mock(context, values, list_name):
    """Add values to a list in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_mock = scenario_context.adapter

    value_list = [v.strip() for v in values.split(",")]
    logger.info(f"Adding values {value_list} to list '{list_name}' in Redis mock")
    result = redis_mock.rpush(list_name, *value_list)
    store_result(context, f"list_add_result_{list_name}", result)


@then('the sync list "{list_name}" should have {count:d} items')
def step_then_sync_list_has_count_items(context, list_name, count):
    """Verify the sync list has the expected number of items."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_mock = scenario_context.adapter

    logger.info(f"Verifying sync list '{list_name}' has {count} items")
    length = redis_mock.llen(list_name)
    assert length == count, f"Sync list '{list_name}' has {length} items, expected {count}"
    logger.info("Sync list item count verified successfully")


@when('I fetch all items from the list "{list_name}" in Redis mock')
def step_when_fetch_list_items_in_redis_mock(context, list_name):
    """Fetch all items from a list in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_mock = scenario_context.adapter

    logger.info(f"Fetching all items from list '{list_name}' in Redis mock")
    items = redis_mock.lrange(list_name, 0, -1)
    store_result(context, f"list_items_{list_name}", items)


@then('the sync list "{list_name}" should contain "{expected_values}"')
def step_then_sync_list_contains_values(context, list_name, expected_values):
    """Verify the sync list contains the expected values."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    expected = [v.strip() for v in expected_values.split(",")]
    retrieved = get_result(context, f"list_items_{list_name}")

    logger.info(f"Verifying sync list '{list_name}' contains {expected}")
    assert retrieved == expected, f"Expected {expected}, got {retrieved}"
    logger.info("Sync list contents verified successfully")


@when('I assign "{field}" to "{value}" in the hash "{hash_name}" in Redis mock')
def step_when_assign_hash_field_in_redis_mock(context, field, hash_name, value):
    """Assign a field-value pair to a hash in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_mock = scenario_context.adapter

    logger.info(f"Assigning '{field}' to '{value}' in hash '{hash_name}' in Redis mock")
    result = redis_mock.hset(hash_name, field, value)
    store_result(context, f"hash_assign_result_{hash_name}_{field}", result)


@then("the sync hash assignment should succeed")
def step_then_sync_hash_assignment_succeeds(context):
    """Verify the sync hash assignment succeeded."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "assign" in s.name),
        None,
    )
    field = prev_step.name.split('"')[1] if prev_step else None
    hash_name = prev_step.name.split('"')[5] if prev_step else None
    result = get_result(context, f"hash_assign_result_{hash_name}_{field}")
    expected_value = prev_step.name.split('"')[3] if prev_step else None

    logger.info(f"Verifying sync hash assignment for '{field}' in '{hash_name}'")
    assert result in (1, None), f"Sync hash assignment failed: returned {result}"
    value = scenario_context.adapter.hget(hash_name, field)
    assert (
        value == expected_value
    ), f"Field '{field}' in '{hash_name}' not set correctly: expected '{expected_value}', got '{value}'"
    logger.info("Sync hash assignment verified successfully")


@when('I retrieve the "{field}" field from the hash "{hash_name}" in Redis mock')
def step_when_retrieve_hash_field_in_redis_mock(context, field, hash_name):
    """Retrieve a field from a hash in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_mock = scenario_context.adapter

    logger.info(f"Retrieving field '{field}' from hash '{hash_name}' in Redis mock")
    value = redis_mock.hget(hash_name, field)
    store_result(context, f"hash_field_{hash_name}_{field}", value)


@then('the sync retrieved field value should be "{expected_value}"')
def step_then_sync_hash_field_value_is(context, expected_value):
    """Verify the sync retrieved hash field value matches the expected value."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "retrieve the" in s.name),
        None,
    )
    field = prev_step.name.split('"')[1] if prev_step else None
    hash_name = prev_step.name.split('"')[3] if prev_step else None
    retrieved_value = get_result(context, f"hash_field_{hash_name}_{field}")

    logger.info(f"Verifying sync retrieved field value for '{field}' in '{hash_name}' is '{expected_value}'")
    assert retrieved_value == expected_value, f"Expected '{expected_value}', got '{retrieved_value}'"
    logger.info("Sync hash field value verified successfully")


@when('I add "{members}" to the set "{set_name}" in Redis mock')
def step_when_add_to_set_in_redis_mock(context, members, set_name):
    """Add members to a set in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_mock = scenario_context.adapter

    member_list = [m.strip() for m in members.split(",")]
    logger.info(f"Adding members {member_list} to set '{set_name}' in Redis mock")
    result = redis_mock.sadd(set_name, *member_list)
    store_result(context, f"set_add_result_{set_name}", result)


@then('the sync set "{set_name}" should have {count:d} members')
def step_then_sync_set_has_count_members(context, set_name, count):
    """Verify the sync set has the expected number of members."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_mock = scenario_context.adapter

    logger.info(f"Verifying sync set '{set_name}' has {count} members")
    cardinality = redis_mock.scard(set_name)
    assert cardinality == count, f"Sync set '{set_name}' has {cardinality} members, expected {count}"
    logger.info("Sync set member count verified successfully")


@when('I fetch all members from the set "{set_name}" in Redis mock')
def step_when_fetch_set_members_in_redis_mock(context, set_name):
    """Fetch all members from a set in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_mock = scenario_context.adapter

    logger.info(f"Fetching all members from set '{set_name}' in Redis mock")
    members = redis_mock.smembers(set_name)
    store_result(context, f"set_members_{set_name}", members)


@then('the sync set "{set_name}" should contain "{expected_members}"')
def step_then_sync_set_contains_members(context, set_name, expected_members):
    """Verify the sync set contains the expected members."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    expected = set(m.strip() for m in expected_members.split(","))
    retrieved = get_result(context, f"set_members_{set_name}")

    logger.info(f"Verifying sync set '{set_name}' contains {expected}")
    assert retrieved == expected, f"Expected {expected}, got {retrieved}"
    logger.info("Sync set members verified successfully")


# Asynchronous Redis Mock Steps
@when('I store the key "{key}" with value "{value}" in async Redis mock')
async def step_when_store_key_in_async_redis_mock(context, key, value):
    """Store a key-value pair in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_mock = scenario_context.async_adapter

    logger.info(f"Storing key '{key}' with value '{value}' in async Redis mock")
    result = await async_redis_mock.set(key, value)
    store_result(context, f"async_store_result_{key}", result)


@then("the async store operation should succeed")
async def step_then_async_store_operation_succeeds(context):
    """Verify the async store operation succeeded."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "store the key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else None
    result = get_result(context, f"async_store_result_{key}")
    expected_value = prev_step.name.split('"')[3] if prev_step else None

    logger.info(f"Verifying async store operation for key '{key}'")
    assert result in (True, None), f"Async store operation failed for key '{key}': returned {result}"
    value = await scenario_context.async_adapter.get(key)
    assert value == expected_value, f"Key '{key}' not stored correctly: expected '{expected_value}', got '{value}'"
    logger.info("Async store operation verified as successful")


@when('I retrieve the value for key "{key}" from async Redis mock')
async def step_when_retrieve_key_from_async_redis_mock(context, key):
    """Retrieve a value from the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_mock = scenario_context.async_adapter

    logger.info(f"Retrieving value for key '{key}' from async Redis mock")
    value = await async_redis_mock.get(key)
    store_result(context, f"async_retrieve_result_{key}", value)


@then('the async retrieved value should be "{expected_value}"')
async def step_then_async_retrieved_value_is(context, expected_value):
    """Verify the async retrieved value matches the expected value."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "retrieve the value" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else None
    retrieved_value = get_result(context, f"async_retrieve_result_{key}")

    logger.info(f"Verifying async retrieved value for key '{key}' is '{expected_value}'")
    assert retrieved_value == expected_value, f"Expected '{expected_value}', got '{retrieved_value}'"
    logger.info("Async retrieved value verified successfully")


@when('I remove the key "{key}" from async Redis mock')
async def step_when_remove_key_from_async_redis_mock(context, key):
    """Remove a key from the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_mock = scenario_context.async_adapter

    logger.info(f"Removing key '{key}' from async Redis mock")
    result = await async_redis_mock.delete(key)
    store_result(context, f"async_remove_result_{key}", result)


@then("the async remove operation should delete one key")
async def step_then_async_remove_operation_deletes_one(context):
    """Verify the async remove operation deleted one key."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "remove the key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "cache-key"
    result = get_result(context, f"async_remove_result_{key}")

    logger.info(f"Verifying async remove operation for key '{key}'")
    assert result == 1, f"Async remove operation returned {result}, expected 1"
    logger.info("Async remove operation verified successfully")


@when('I check if "{key}" exists in async Redis mock')
async def step_when_check_key_exists_in_async_redis_mock(context, key):
    """Check if a key exists in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_mock = scenario_context.async_adapter

    logger.info(f"Checking if key '{key}' exists in async Redis mock")
    result = await async_redis_mock.exists(key)
    store_result(context, f"async_exists_result_{key}", result)


@then("the async key should not exist")
async def step_then_async_key_does_not_exist(context):
    """Verify the async key does not exist."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "check if" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "cache-key"
    result = get_result(context, f"async_exists_result_{key}")

    logger.info(f"Verifying async key '{key}' does not exist")
    assert result == 0, f"Async key '{key}' exists, expected it to be absent (result: {result})"
    logger.info("Async key absence verified successfully")


@when('I add "{values}" to the list "{list_name}" in async Redis mock')
async def step_when_add_to_list_in_async_redis_mock(context, values, list_name):
    """Add values to a list in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_mock = scenario_context.async_adapter

    value_list = [v.strip() for v in values.split(",")]
    logger.info(f"Adding values {value_list} to list '{list_name}' in async Redis mock")
    result = await async_redis_mock.rpush(list_name, *value_list)
    store_result(context, f"async_list_add_result_{list_name}", result)


@then('the async list "{list_name}" should have {count:d} items')
async def step_then_async_list_has_count_items(context, list_name, count):
    """Verify the async list has the expected number of items."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_mock = scenario_context.async_adapter

    logger.info(f"Verifying async list '{list_name}' has {count} items")
    length = await async_redis_mock.llen(list_name)
    assert length == count, f"Async list '{list_name}' has {length} items, expected {count}"
    logger.info("Async list item count verified successfully")


@when('I fetch all items from the list "{list_name}" in async Redis mock')
async def step_when_fetch_list_items_in_async_redis_mock(context, list_name):
    """Fetch all items from a list in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_mock = scenario_context.async_adapter

    logger.info(f"Fetching all items from list '{list_name}' in async Redis mock")
    items = await async_redis_mock.lrange(list_name, 0, -1)
    store_result(context, f"async_list_items_{list_name}", items)


@then('the async list "{list_name}" should contain "{expected_values}"')
async def step_then_async_list_contains_values(context, list_name, expected_values):
    """Verify the async list contains the expected values."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    expected = [v.strip() for v in expected_values.split(",")]
    retrieved = get_result(context, f"async_list_items_{list_name}")

    logger.info(f"Verifying async list '{list_name}' contains {expected}")
    assert retrieved == expected, f"Expected {expected}, got {retrieved}"
    logger.info("Async list contents verified successfully")


@when('I assign "{field}" to "{value}" in the hash "{hash_name}" in async Redis mock')
async def step_when_assign_hash_field_in_async_redis_mock(context, field, hash_name, value):
    """Assign a field-value pair to a hash in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_mock = scenario_context.async_adapter

    logger.info(f"Assigning '{field}' to '{value}' in hash '{hash_name}' in async Redis mock")
    result = await async_redis_mock.hset(hash_name, field, value)
    store_result(context, f"async_hash_assign_result_{hash_name}_{field}", result)


@then("the async hash assignment should succeed")
async def step_then_async_hash_assignment_succeeds(context):
    """Verify the async hash assignment succeeded."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "assign" in s.name),
        None,
    )
    field = prev_step.name.split('"')[1] if prev_step else None
    hash_name = prev_step.name.split('"')[5] if prev_step else None
    result = get_result(context, f"async_hash_assign_result_{hash_name}_{field}")
    expected_value = prev_step.name.split('"')[3] if prev_step else None

    logger.info(f"Verifying async hash assignment for '{field}' in '{hash_name}'")
    assert result in (1, None), f"Async hash assignment failed: returned {result}"
    value = await scenario_context.async_adapter.hget(hash_name, field)
    assert (
        value == expected_value
    ), f"Field '{field}' in '{hash_name}' not set correctly: expected '{expected_value}', got '{value}'"
    logger.info("Async hash assignment verified successfully")


@when('I retrieve the "{field}" field from the hash "{hash_name}" in async Redis mock')
async def step_when_retrieve_hash_field_in_async_redis_mock(context, field, hash_name):
    """Retrieve a field from a hash in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_mock = scenario_context.async_adapter

    logger.info(f"Retrieving field '{field}' from hash '{hash_name}' in async Redis mock")
    value = await async_redis_mock.hget(hash_name, field)
    store_result(context, f"async_hash_field_{hash_name}_{field}", value)


@then('the async retrieved field value should be "{expected_value}"')
async def step_then_async_hash_field_value_is(context, expected_value):
    """Verify the async retrieved hash field value matches the expected value."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "retrieve the" in s.name),
        None,
    )
    field = prev_step.name.split('"')[1] if prev_step else None
    hash_name = prev_step.name.split('"')[3] if prev_step else None
    retrieved_value = get_result(context, f"async_hash_field_{hash_name}_{field}")

    logger.info(f"Verifying async retrieved field value for '{field}' in '{hash_name}' is '{expected_value}'")
    assert retrieved_value == expected_value, f"Expected '{expected_value}', got '{retrieved_value}'"
    logger.info("Async hash field value verified successfully")


@when('I add "{members}" to the set "{set_name}" in async Redis mock')
async def step_when_add_to_set_in_async_redis_mock(context, members, set_name):
    """Add members to a set in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_mock = scenario_context.async_adapter

    member_list = [m.strip() for m in members.split(",")]
    logger.info(f"Adding members {member_list} to set '{set_name}' in async Redis mock")
    result = await async_redis_mock.sadd(set_name, *member_list)
    store_result(context, f"async_set_add_result_{set_name}", result)


@then('the async set "{set_name}" should have {count:d} members')
async def step_then_async_set_has_count_members(context, set_name, count):
    """Verify the async set has the expected number of members."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_mock = scenario_context.async_adapter

    logger.info(f"Verifying async set '{set_name}' has {count} members")
    cardinality = await async_redis_mock.scard(set_name)
    assert cardinality == count, f"Async set '{set_name}' has {cardinality} members, expected {count}"
    logger.info("Async set member count verified successfully")


@when('I fetch all members from the set "{set_name}" in async Redis mock')
async def step_when_fetch_set_members_in_async_redis_mock(context, set_name):
    """Fetch all members from a set in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_mock = scenario_context.async_adapter

    logger.info(f"Fetching all members from set '{set_name}' in async Redis mock")
    members = await async_redis_mock.smembers(set_name)
    store_result(context, f"async_set_members_{set_name}", members)


@then('the async set "{set_name}" should contain "{expected_members}"')
async def step_then_async_set_contains_members(context, set_name, expected_members):
    """Verify the async set contains the expected members."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    expected = set(m.strip() for m in expected_members.split(","))
    retrieved = get_result(context, f"async_set_members_{set_name}")

    logger.info(f"Verifying async set '{set_name}' contains {expected}")
    assert retrieved == expected, f"Expected {expected}, got {retrieved}"
    logger.info("Async set members verified successfully")
