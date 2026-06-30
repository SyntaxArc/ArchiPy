"""Implementation of steps for testing RedisMock and AsyncRedisMock.

This module contains step definitions for simplified synchronous and asynchronous
Redis mock scenarios as defined in the Redis Mock Testing feature.
"""

import logging

from behave import given, then, use_step_matcher, when
from features.test_containers import ContainerManager
from features.test_helpers import get_current_scenario_context

from archipy.adapters.redis.adapters import AsyncRedisAdapter, RedisAdapter
from archipy.adapters.redis.mocks import AsyncRedisMock, RedisMock
from archipy.configs.config_template import RedisConfig

# Use regex matcher to avoid ambiguity between "configured {adapter_type}" and "configured async {adapter_type}"
use_step_matcher("re")


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
@given(r"a configured (?P<adapter_type>mock|container|cluster)")
def step_given_configured_adapter(context, adapter_type):
    """Set up a Redis adapter instance (mock or container) for testing."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)

    if adapter_type == "mock":
        logger.info("Configuring RedisMock")
        redis_config = RedisConfig(
            MASTER_HOST="localhost",
            PORT=6379,
            DATABASE=0,
            DECODE_RESPONSES=True,
        )
        redis_adapter = RedisMock(redis_config=redis_config)
        scenario_context.adapter = redis_adapter
        logger.info("RedisMock configured successfully")
    elif adapter_type == "container":
        logger.info("Configuring Redis container")
        redis_adapter = RedisAdapter()
        scenario_context.adapter = redis_adapter
        logger.info("Redis container adapter configured successfully")
    elif adapter_type == "cluster":
        logger.info("Configuring Redis cluster container")
        cluster_container = ContainerManager.get_container("redis-cluster")
        redis_adapter = RedisAdapter(redis_config=cluster_container.cluster_config)
        scenario_context.adapter = redis_adapter
        logger.info("Redis cluster adapter configured successfully")

@given(r"a configured async (?P<adapter_type>mock|container|cluster)")
def step_given_configured_async_adapter(context, adapter_type):
    """Set up an async Redis adapter instance (mock or container) for testing."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)

    if adapter_type == "mock":
        logger.info("Configuring AsyncRedisMock")
        redis_config = RedisConfig(
            MASTER_HOST="localhost",
            PORT=6379,
            DATABASE=0,
            DECODE_RESPONSES=True,
        )
        async_redis_adapter = AsyncRedisMock(redis_config=redis_config)
        scenario_context.async_adapter = async_redis_adapter
        logger.info("AsyncRedisMock configured successfully")
    elif adapter_type == "container":
        logger.info("Configuring async Redis container")
        async_redis_adapter = AsyncRedisAdapter()
        scenario_context.async_adapter = async_redis_adapter
        logger.info("Async Redis container adapter configured successfully")
    elif adapter_type == "cluster":
        logger.info("Configuring async Redis cluster container")
        cluster_container = ContainerManager.get_container("redis-cluster")
        async_redis_adapter = AsyncRedisAdapter(redis_config=cluster_container.cluster_config)
        scenario_context.async_adapter = async_redis_adapter
        logger.info("Async Redis cluster adapter configured successfully")

# Synchronous Redis Mock Steps
@when(r'I store the key "(?P<key>[^"]+)" with value "(?P<value>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_store_key_in_adapter(context, key, value, adapter_type):
    """Store a key-value pair in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info(f"Storing key '{key}' with value '{value}' in {adapter_type}")
    result = redis_adapter.set(key, value)
    store_result(context, f"store_result_{key}", result)



@then(r"the sync store operation should succeed")
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


@when(r'I retrieve the value for key "(?P<key>[^"]+)" from (?P<adapter_type>mock|container|cluster)')
def step_when_retrieve_key_from_adapter(context, key, adapter_type):
    """Retrieve a value from the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info(f"Retrieving value for key '{key}' from {adapter_type}")
    value = redis_adapter.get(key)
    store_result(context, f"retrieve_result_{key}", value)


@then(r'the sync retrieved value should be "(?P<expected_value>[^"]+)"')
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


@when(r'I remove the key "(?P<key>[^"]+)" from (?P<adapter_type>mock|container|cluster)')
def step_when_remove_key_from_adapter(context, key, adapter_type):
    """Remove a key from the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info(f"Removing key '{key}' from {adapter_type}")
    result = redis_adapter.delete(key)
    store_result(context, f"remove_result_{key}", result)


@then(r"the sync remove operation should delete one key")
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


@when(r'I check if "(?P<key>[^"]+)" exists in (?P<adapter_type>mock|container|cluster)')
def step_when_check_key_exists_in_adapter(context, key, adapter_type):
    """Check if a key exists in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info(f"Checking if key '{key}' exists in {adapter_type}")
    result = redis_adapter.exists(key)
    store_result(context, f"exists_result_{key}", result)


@then(r"the sync key should not exist")
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


@when(r'I add "(?P<values>[^"]+)" to the list "(?P<list_name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_add_to_list_in_adapter(context, values, list_name, adapter_type):
    """Add values to a list in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    value_list = [v.strip() for v in values.split(",")]
    logger.info(f"Adding values {value_list} to list '{list_name}' in {adapter_type}")
    result = redis_adapter.rpush(list_name, *value_list)
    store_result(context, f"list_add_result_{list_name}", result)


@then(r'the sync list "(?P<list_name>[^"]+)" should have (?P<count>\d+) items')
def step_then_sync_list_has_count_items(context, list_name, count):
    count = int(count)
    """Verify the sync list has the expected number of items."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info(f"Verifying sync list '{list_name}' has {count} items")
    length = redis_adapter.llen(list_name)
    assert length == count, f"Sync list '{list_name}' has {length} items, expected {count}"
    logger.info("Sync list item count verified successfully")


@when(r'I fetch all items from the list "(?P<list_name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_fetch_list_items_in_adapter(context, list_name, adapter_type):
    """Fetch all items from a list in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info(f"Fetching all items from list '{list_name}' in {adapter_type}")
    items = redis_adapter.lrange(list_name, 0, -1)
    store_result(context, f"list_items_{list_name}", items)


@then(r'the sync list "(?P<list_name>[^"]+)" should contain "(?P<expected_values>[^"]+)"')
def step_then_sync_list_contains_values(context, list_name, expected_values):
    """Verify the sync list contains the expected values."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    expected = [v.strip() for v in expected_values.split(",")]
    retrieved = get_result(context, f"list_items_{list_name}")

    logger.info(f"Verifying sync list '{list_name}' contains {expected}")
    assert retrieved == expected, f"Expected {expected}, got {retrieved}"
    logger.info("Sync list contents verified successfully")


@when(r'I assign "(?P<field>[^"]+)" to "(?P<value>[^"]+)" in the hash "(?P<hash_name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_assign_hash_field_in_adapter(context, field, hash_name, value, adapter_type):
    """Assign a field-value pair to a hash in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info(f"Assigning '{field}' to '{value}' in hash '{hash_name}' in {adapter_type}")
    result = redis_adapter.hset(hash_name, field, value)
    store_result(context, f"hash_assign_result_{hash_name}_{field}", result)


@then(r"the sync hash assignment should succeed")
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


@when(r'I retrieve the "(?P<field>[^"]+)" field from the hash "(?P<hash_name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_retrieve_hash_field_in_adapter(context, field, hash_name, adapter_type):
    """Retrieve a field from a hash in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info(f"Retrieving field '{field}' from hash '{hash_name}' in {adapter_type}")
    value = redis_adapter.hget(hash_name, field)
    store_result(context, f"hash_field_{hash_name}_{field}", value)


@then(r'the sync retrieved field value should be "(?P<expected_value>[^"]+)"')
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


@when(r'I add "(?P<members>[^"]+)" to the set "(?P<set_name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_add_to_set_in_adapter(context, members, set_name, adapter_type):
    """Add members to a set in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    member_list = [m.strip() for m in members.split(",")]
    logger.info(f"Adding members {member_list} to set '{set_name}' in {adapter_type}")
    result = redis_adapter.sadd(set_name, *member_list)
    store_result(context, f"set_add_result_{set_name}", result)


@then(r'the sync set "(?P<set_name>[^"]+)" should have (?P<count>\d+) members')
def step_then_sync_set_has_count_members(context, set_name, count):
    count = int(count)
    """Verify the sync set has the expected number of members."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info(f"Verifying sync set '{set_name}' has {count} members")
    cardinality = redis_adapter.scard(set_name)
    assert cardinality == count, f"Sync set '{set_name}' has {cardinality} members, expected {count}"
    logger.info("Sync set member count verified successfully")


@when(r'I fetch all members from the set "(?P<set_name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_fetch_set_members_in_adapter(context, set_name, adapter_type):
    """Fetch all members from a set in the Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info(f"Fetching all members from set '{set_name}' in {adapter_type}")
    members = redis_adapter.smembers(set_name)
    store_result(context, f"set_members_{set_name}", members)


@then(r'the sync set "(?P<set_name>[^"]+)" should contain "(?P<expected_members>[^"]+)"')
def step_then_sync_set_contains_members(context, set_name, expected_members):
    """Verify the sync set contains the expected members."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    expected = set(m.strip() for m in expected_members.split(","))
    retrieved = get_result(context, f"set_members_{set_name}")

    logger.info(f"Verifying sync set '{set_name}' contains {expected}")
    assert retrieved == expected, f"Expected {expected}, got {retrieved}"
    logger.info("Sync set members verified successfully")


# Asynchronous Redis Mock Steps
@when(r'I store the key "(?P<key>[^"]+)" with value "(?P<value>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_store_key_in_async_adapter(context, key, value, adapter_type):
    """Store a key-value pair in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info(f"Storing key '{key}' with value '{value}' in async {adapter_type}")
    result = await async_redis_adapter.set(key, value)
    store_result(context, f"async_store_result_{key}", result)


@then(r"the async store operation should succeed")
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


@when(r'I retrieve the value for key "(?P<key>[^"]+)" from async (?P<adapter_type>mock|container|cluster)')
async def step_when_retrieve_key_from_async_adapter(context, key, adapter_type):
    """Retrieve a value from the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info(f"Retrieving value for key '{key}' from async {adapter_type}")
    value = await async_redis_adapter.get(key)
    store_result(context, f"async_retrieve_result_{key}", value)


@then(r'the async retrieved value should be "(?P<expected_value>[^"]+)"')
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


@when(r'I remove the key "(?P<key>[^"]+)" from async (?P<adapter_type>mock|container|cluster)')
async def step_when_remove_key_from_async_adapter(context, key, adapter_type):
    """Remove a key from the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info(f"Removing key '{key}' from async {adapter_type}")
    result = await async_redis_adapter.delete(key)
    store_result(context, f"async_remove_result_{key}", result)


@then(r"the async remove operation should delete one key")
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


@when(r'I check if "(?P<key>[^"]+)" exists in async (?P<adapter_type>mock|container|cluster)')
async def step_when_check_key_exists_in_async_adapter(context, key, adapter_type):
    """Check if a key exists in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info(f"Checking if key '{key}' exists in async {adapter_type}")
    result = await async_redis_adapter.exists(key)
    store_result(context, f"async_exists_result_{key}", result)


@then(r"the async key should not exist")
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


@when(r'I add "(?P<values>[^"]+)" to the list "(?P<list_name>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_add_to_list_in_async_adapter(context, values, list_name, adapter_type):
    """Add values to a list in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    value_list = [v.strip() for v in values.split(",")]
    logger.info(f"Adding values {value_list} to list '{list_name}' in async {adapter_type}")
    result = await async_redis_adapter.rpush(list_name, *value_list)
    store_result(context, f"async_list_add_result_{list_name}", result)


@then(r'the async list "(?P<list_name>[^"]+)" should have (?P<count>\d+) items')
async def step_then_async_list_has_count_items(context, list_name, count):
    count = int(count)
    """Verify the async list has the expected number of items."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info(f"Verifying async list '{list_name}' has {count} items")
    length = await async_redis_adapter.llen(list_name)
    assert length == count, f"Async list '{list_name}' has {length} items, expected {count}"
    logger.info("Async list item count verified successfully")


@when(r'I fetch all items from the list "(?P<list_name>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_fetch_list_items_in_async_adapter(context, list_name, adapter_type):
    """Fetch all items from a list in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info(f"Fetching all items from list '{list_name}' in async {adapter_type}")
    items = await async_redis_adapter.lrange(list_name, 0, -1)
    store_result(context, f"async_list_items_{list_name}", items)


@then(r'the async list "(?P<list_name>[^"]+)" should contain "(?P<expected_values>[^"]+)"')
async def step_then_async_list_contains_values(context, list_name, expected_values):
    """Verify the async list contains the expected values."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    expected = [v.strip() for v in expected_values.split(",")]
    retrieved = get_result(context, f"async_list_items_{list_name}")

    logger.info(f"Verifying async list '{list_name}' contains {expected}")
    assert retrieved == expected, f"Expected {expected}, got {retrieved}"
    logger.info("Async list contents verified successfully")


@when(r'I assign "(?P<field>[^"]+)" to "(?P<value>[^"]+)" in the hash "(?P<hash_name>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_assign_hash_field_in_async_adapter(context, field, hash_name, value, adapter_type):
    """Assign a field-value pair to a hash in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info(f"Assigning '{field}' to '{value}' in hash '{hash_name}' in async {adapter_type}")
    result = await async_redis_adapter.hset(hash_name, field, value)
    store_result(context, f"async_hash_assign_result_{hash_name}_{field}", result)


@then(r"the async hash assignment should succeed")
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


@when(r'I retrieve the "(?P<field>[^"]+)" field from the hash "(?P<hash_name>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_retrieve_hash_field_in_async_adapter(context, field, hash_name, adapter_type):
    """Retrieve a field from a hash in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info(f"Retrieving field '{field}' from hash '{hash_name}' in async {adapter_type}")
    value = await async_redis_adapter.hget(hash_name, field)
    store_result(context, f"async_hash_field_{hash_name}_{field}", value)


@then(r'the async retrieved field value should be "(?P<expected_value>[^"]+)"')
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


@when(r'I add "(?P<members>[^"]+)" to the set "(?P<set_name>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_add_to_set_in_async_adapter(context, members, set_name, adapter_type):
    """Add members to a set in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    member_list = [m.strip() for m in members.split(",")]
    logger.info(f"Adding members {member_list} to set '{set_name}' in async {adapter_type}")
    result = await async_redis_adapter.sadd(set_name, *member_list)
    store_result(context, f"async_set_add_result_{set_name}", result)


@then(r'the async set "(?P<set_name>[^"]+)" should have (?P<count>\d+) members')
async def step_then_async_set_has_count_members(context, set_name, count):
    count = int(count)
    """Verify the async set has the expected number of members."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info(f"Verifying async set '{set_name}' has {count} members")
    cardinality = await async_redis_adapter.scard(set_name)
    assert cardinality == count, f"Async set '{set_name}' has {cardinality} members, expected {count}"
    logger.info("Async set member count verified successfully")


@when(r'I fetch all members from the set "(?P<set_name>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_fetch_set_members_in_async_adapter(context, set_name, adapter_type):
    """Fetch all members from a set in the async Redis mock."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info(f"Fetching all members from set '{set_name}' in async {adapter_type}")
    members = await async_redis_adapter.smembers(set_name)
    store_result(context, f"async_set_members_{set_name}", members)


@then(r'the async set "(?P<set_name>[^"]+)" should contain "(?P<expected_members>[^"]+)"')
async def step_then_async_set_contains_members(context, set_name, expected_members):
    """Verify the async set contains the expected members."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    expected = set(m.strip() for m in expected_members.split(","))
    retrieved = get_result(context, f"async_set_members_{set_name}")

    logger.info(f"Verifying async set '{set_name}' contains {expected}")
    assert retrieved == expected, f"Expected {expected}, got {retrieved}"
    logger.info("Async set members verified successfully")


def _count_cluster_roles(
    nodes: dict[str, dict[str, str | bool | list[list[str]] | list[dict[str, str]]]],
) -> tuple[int, int]:
    """Count master and replica nodes from a cluster_nodes() response."""
    masters = 0
    replicas = 0
    for node_info in nodes.values():
        role_value = str(node_info.get("role", "")).lower()
        flags_value = str(node_info.get("flags", "")).lower()
        role_text = f"{role_value},{flags_value}"
        if "master" in role_text:
            masters += 1
        elif "slave" in role_text or "replica" in role_text:
            replicas += 1
    return masters, replicas


# Cluster API steps (sync)
@when(r"I query cluster info from the adapter")
def step_when_query_cluster_info(context):
    """Query cluster info from the sync Redis adapter."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info("Querying cluster info from sync adapter")
    cluster_info = redis_adapter.cluster_info()
    store_result(context, "cluster_info", cluster_info)


@then(r"cluster state should be ok")
def step_then_cluster_state_ok(context):
    """Verify cluster_state is ok."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    cluster_info = get_result(context, "cluster_info")

    logger.info("Verifying cluster state is ok")
    assert cluster_info is not None, "cluster_info returned None"
    assert cluster_info.get("cluster_state") == "ok", f"Expected cluster_state ok, got {cluster_info}"
    logger.info("Cluster state verified as ok")


@when(r"I query cluster nodes from the adapter")
def step_when_query_cluster_nodes(context):
    """Query cluster nodes from the sync Redis adapter."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info("Querying cluster nodes from sync adapter")
    cluster_nodes = redis_adapter.cluster_nodes()
    store_result(context, "cluster_nodes", cluster_nodes)


@then(r"cluster should have 3 masters and 3 replicas")
def step_then_cluster_has_masters_and_replicas(context):
    """Verify cluster topology has 3 masters and 3 replicas."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    cluster_nodes = get_result(context, "cluster_nodes")

    logger.info("Verifying cluster has 3 masters and 3 replicas")
    assert cluster_nodes is not None, "cluster_nodes returned None"
    masters, replicas = _count_cluster_roles(cluster_nodes)
    assert masters == 3, f"Expected 3 masters, got {masters}"
    assert replicas == 3, f"Expected 3 replicas, got {replicas}"
    logger.info("Cluster topology verified successfully")


@when(r'I get the cluster slot for key "(?P<key>[^"]+)"')
def step_when_get_cluster_slot_for_key(context, key):
    """Get the cluster slot for a key from the sync Redis adapter."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info(f"Getting cluster slot for key '{key}'")
    slot = redis_adapter.cluster_key_slot(key)
    store_result(context, "cluster_slot", slot)


@then(r"the slot should be between 0 and 16383")
def step_then_slot_in_valid_range(context):
    """Verify the stored cluster slot is in the valid range."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    slot = get_result(context, "cluster_slot")

    logger.info("Verifying cluster slot is between 0 and 16383")
    assert slot is not None, "cluster_slot returned None"
    assert 0 <= slot <= 16383, f"Slot {slot} is outside valid range 0-16383"
    logger.info(f"Cluster slot {slot} verified in valid range")


@when(r'I get the cluster slots for keys "(?P<key1>[^"]+)" and "(?P<key2>[^"]+)"')
def step_when_get_cluster_slots_for_keys(context, key1, key2):
    """Get cluster slots for two keys from the sync Redis adapter."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info(f"Getting cluster slots for keys '{key1}' and '{key2}'")
    slot1 = redis_adapter.cluster_key_slot(key1)
    slot2 = redis_adapter.cluster_key_slot(key2)
    store_result(context, "cluster_slot_1", slot1)
    store_result(context, "cluster_slot_2", slot2)


@then(r"both keys should share the same slot")
def step_then_both_keys_share_slot(context):
    """Verify both stored cluster slots are equal."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    slot1 = get_result(context, "cluster_slot_1")
    slot2 = get_result(context, "cluster_slot_2")

    logger.info("Verifying both keys share the same cluster slot")
    assert slot1 is not None and slot2 is not None, "One or both cluster slots returned None"
    assert slot1 == slot2, f"Expected same slot, got {slot1} and {slot2}"
    logger.info(f"Both keys share cluster slot {slot1}")


@when(r'I inspect keys in the cluster slot for key "(?P<key>[^"]+)"')
def step_when_inspect_keys_in_cluster_slot(context, key):
    """Inspect keys in the cluster slot for a key using sync adapter cluster APIs."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    redis_adapter = scenario_context.adapter

    logger.info(f"Inspecting keys in cluster slot for key '{key}'")
    slot = redis_adapter.cluster_key_slot(key)
    key_count = redis_adapter.cluster_count_keys_in_slot(slot)
    keys_in_slot = redis_adapter.cluster_get_keys_in_slot(slot, 100)
    store_result(context, "cluster_slot", slot)
    store_result(context, "cluster_slot_key_count", key_count)
    store_result(context, "cluster_slot_keys", keys_in_slot)
    store_result(context, "inspected_cluster_key", key)


@then(r"the cluster slot should contain at least 1 key")
def step_then_cluster_slot_has_keys(context):
    """Verify the cluster slot contains at least one key."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    key_count = get_result(context, "cluster_slot_key_count")

    logger.info("Verifying cluster slot contains at least 1 key")
    assert key_count is not None, "cluster_slot_key_count returned None"
    assert key_count >= 1, f"Expected at least 1 key in slot, got {key_count}"
    logger.info(f"Cluster slot contains {key_count} key(s)")


@then(r'the cluster slot should include key "(?P<key>[^"]+)"')
def step_then_cluster_slot_includes_key(context, key):
    """Verify the cluster slot includes the expected key."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    keys_in_slot = get_result(context, "cluster_slot_keys")

    logger.info(f"Verifying cluster slot includes key '{key}'")
    assert keys_in_slot is not None, "cluster_slot_keys returned None"
    assert key in keys_in_slot, f"Key '{key}' not found in slot keys: {keys_in_slot}"
    logger.info(f"Cluster slot includes key '{key}'")


# Cluster API steps (async)
@when(r"I query cluster info from the async adapter")
async def step_when_query_async_cluster_info(context):
    """Query cluster info from the async Redis adapter."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info("Querying cluster info from async adapter")
    cluster_info = await async_redis_adapter.cluster_info()
    store_result(context, "cluster_info", cluster_info)


@when(r"I query cluster nodes from the async adapter")
async def step_when_query_async_cluster_nodes(context):
    """Query cluster nodes from the async Redis adapter."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info("Querying cluster nodes from async adapter")
    cluster_nodes = await async_redis_adapter.cluster_nodes()
    store_result(context, "cluster_nodes", cluster_nodes)


@when(r'I get the cluster slot for key "(?P<key>[^"]+)" from the async adapter')
async def step_when_get_async_cluster_slot_for_key(context, key):
    """Get the cluster slot for a key from the async Redis adapter."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info(f"Getting cluster slot for key '{key}' from async adapter")
    slot = await async_redis_adapter.cluster_key_slot(key)
    store_result(context, "cluster_slot", slot)


@when(r'I get the cluster slots for keys "(?P<key1>[^"]+)" and "(?P<key2>[^"]+)" from the async adapter')
async def step_when_get_async_cluster_slots_for_keys(context, key1, key2):
    """Get cluster slots for two keys from the async Redis adapter."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info(f"Getting cluster slots for keys '{key1}' and '{key2}' from async adapter")
    slot1 = await async_redis_adapter.cluster_key_slot(key1)
    slot2 = await async_redis_adapter.cluster_key_slot(key2)
    store_result(context, "cluster_slot_1", slot1)
    store_result(context, "cluster_slot_2", slot2)


@when(r'I inspect keys in the cluster slot for key "(?P<key>[^"]+)" from the async adapter')
async def step_when_inspect_keys_in_async_cluster_slot(context, key):
    """Inspect keys in the cluster slot for a key using async adapter cluster APIs."""
    logger = getattr(context, "logger", logging.getLogger("behave.steps"))
    scenario_context = get_current_scenario_context(context)
    async_redis_adapter = scenario_context.async_adapter

    logger.info(f"Inspecting keys in cluster slot for key '{key}' from async adapter")
    slot = await async_redis_adapter.cluster_key_slot(key)
    key_count = await async_redis_adapter.cluster_count_keys_in_slot(slot)
    keys_in_slot = await async_redis_adapter.cluster_get_keys_in_slot(slot, 100)
    store_result(context, "cluster_slot", slot)
    store_result(context, "cluster_slot_key_count", key_count)
    store_result(context, "cluster_slot_keys", keys_in_slot)
    store_result(context, "inspected_cluster_key", key)
