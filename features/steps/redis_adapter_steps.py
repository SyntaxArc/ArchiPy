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

# ---------------------------------------------------------------------------
# Helper parsers
# ---------------------------------------------------------------------------

def _parse_mapping(text: str) -> dict[str, str]:
    """Parse comma-separated key=value pairs into a dict."""
    mapping: dict[str, str] = {}
    for pair in text.split(","):
        key, value = pair.split("=", 1)
        mapping[key.strip()] = value.strip()
    return mapping


def _parse_zadd_members(text: str) -> dict[str, float]:
    """Parse member=score pairs for zadd."""
    mapping: dict[str, float] = {}
    for pair in text.split(","):
        member, score = pair.split("=", 1)
        mapping[member.strip()] = float(score.strip())
    return mapping


def _create_key_by_type(adapter, key: str, redis_type: str) -> None:
    """Create a Redis key of the given type."""
    if redis_type == "string":
        adapter.set(key, "value")
    elif redis_type == "list":
        adapter.rpush(key, "item")
    elif redis_type == "hash":
        adapter.hset(key, "field", "value")
    elif redis_type == "set":
        adapter.sadd(key, "member")
    elif redis_type == "zset":
        adapter.zadd(key, {"member": 1.0})


def _format_pipeline_results(results: list) -> str:
    """Format pipeline execute results for assertion."""
    formatted = []
    for item in results:
        if item is True or item == "OK":
            formatted.append("True")
        else:
            formatted.append(str(item))
    return ", ".join(formatted)


def _extract_zpop_member(result) -> str:
    """Extract member name from zpopmax/zpopmin result."""
    if not result:
        return ""
    first = result[0]
    if isinstance(first, (list, tuple)):
        return str(first[0])
    return str(first)


def _cleanup_pubsub(pubsub) -> None:
    """Close a sync pubsub connection."""
    try:
        pubsub.close()
    except Exception:
        pass


async def _collect_async_scan_keys(adapter, pattern: str) -> list[str]:
    """Collect keys from async scan_iter across mock and real adapters."""
    scan_iterable = adapter.scan_iter(match=pattern)
    if hasattr(scan_iterable, "__await__"):
        scan_iterable = await scan_iterable
    while hasattr(scan_iterable, "__await__"):
        scan_iterable = await scan_iterable
    if hasattr(scan_iterable, "__aiter__"):
        return [key async for key in scan_iterable]
    return list(scan_iterable)


# ---------------------------------------------------------------------------
# Strings, expiry, counters, multi-key (sync)
# ---------------------------------------------------------------------------

@when(
    r'I store the key "(?P<key>[^"]+)" with value "(?P<value>[^"]+)" '
    r'and expiry (?P<seconds>\d+) seconds in (?P<adapter_type>mock|container|cluster)',
)
def step_when_store_key_with_expiry(context, key, value, seconds, adapter_type):
    """Store a key-value pair with TTL."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.adapter.set(key, value, ex=int(seconds))
    store_result(context, f"store_expiry_result_{key}", result)


@then(r"the sync store with expiry should succeed")
def step_then_sync_store_with_expiry_succeeds(context):
    """Verify sync set with expiry succeeded."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "and expiry" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "ttl-key"
    result = get_result(context, f"store_expiry_result_{key}")
    assert result in (True, None), f"Sync store with expiry failed: {result}"


@when(r'I check the TTL for key "(?P<key>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_check_ttl(context, key, adapter_type):
    """Check TTL for a key."""
    scenario_context = get_current_scenario_context(context)
    ttl = scenario_context.adapter.ttl(key)
    store_result(context, f"ttl_{key}", ttl)


@then(r"the sync TTL should be between (?P<min_ttl>\d+) and (?P<max_ttl>\d+)")
def step_then_sync_ttl_in_range(context, min_ttl, max_ttl):
    """Verify TTL is within expected range."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "check the TTL" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "ttl-key"
    ttl = get_result(context, f"ttl_{key}")
    min_val = int(min_ttl)
    max_val = int(max_ttl)
    assert ttl is not None, "TTL returned None"
    assert min_val <= ttl <= max_val, f"TTL {ttl} not in range [{min_val}, {max_val}]"


@when(r'I check the PTTL for key "(?P<key>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_check_pttl(context, key, adapter_type):
    """Check PTTL for a key."""
    scenario_context = get_current_scenario_context(context)
    pttl = scenario_context.adapter.pttl(key)
    store_result(context, f"pttl_{key}", pttl)


@then(r"the sync PTTL should be positive")
def step_then_sync_pttl_positive(context):
    """Verify PTTL is positive."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "check the PTTL" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "ttl-key"
    pttl = get_result(context, f"pttl_{key}")
    assert pttl is not None and pttl > 0, f"Expected positive PTTL, got {pttl}"


@when(r'I getset key "(?P<key>[^"]+)" to value "(?P<value>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_getset(context, key, value, adapter_type):
    """GetSet a key."""
    scenario_context = get_current_scenario_context(context)
    old_value = scenario_context.adapter.getset(key, value)
    store_result(context, f"getset_{key}", old_value)


@then(r'the sync getset old value should be "(?P<expected>[^"]+)"')
def step_then_sync_getset_old_value(context, expected):
    """Verify getset returned the old value."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "getset key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else None
    old_value = get_result(context, f"getset_{key}")
    assert old_value == expected, f"Expected getset old value '{expected}', got '{old_value}'"


@when(r'I getdel key "(?P<key>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_getdel(context, key, adapter_type):
    """GetDel a key."""
    scenario_context = get_current_scenario_context(context)
    value = scenario_context.adapter.getdel(key)
    store_result(context, f"getdel_{key}", value)


@then(r'the sync getdel value should be "(?P<expected>[^"]+)"')
def step_then_sync_getdel_value(context, expected):
    """Verify getdel returned the expected value."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "getdel key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else None
    value = get_result(context, f"getdel_{key}")
    assert value == expected, f"Expected getdel value '{expected}', got '{value}'"


@when(r'I append "(?P<value>[^"]+)" to key "(?P<key>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_append(context, value, key, adapter_type):
    """Append to a string key."""
    scenario_context = get_current_scenario_context(context)
    length = scenario_context.adapter.append(key, value)
    store_result(context, f"append_length_{key}", length)


@then(r"the sync append length should be (?P<length>\d+)")
def step_then_sync_append_length(context, length):
    """Verify append returned expected string length."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "append" in s.name),
        None,
    )
    key = prev_step.name.split('"')[3] if prev_step else "app-key"
    actual = get_result(context, f"append_length_{key}")
    assert actual == int(length), f"Expected append length {length}, got {actual}"


@when(r'I create a (?P<redis_type>string|list|hash|set|zset) key "(?P<key>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_create_key_by_type(context, redis_type, key, adapter_type):
    """Create a key of a specific Redis type."""
    scenario_context = get_current_scenario_context(context)
    _create_key_by_type(scenario_context.adapter, key, redis_type)


@when(r'I check the type of key "(?P<key>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_check_type(context, key, adapter_type):
    """Check the Redis type of a key."""
    scenario_context = get_current_scenario_context(context)
    key_type = scenario_context.adapter.type(key)
    store_result(context, f"type_{key}", key_type)


@then(r'the sync key type should be "(?P<expected>[^"]+)"')
def step_then_sync_key_type(context, expected):
    """Verify key type matches expected."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "check the type" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "type-key"
    key_type = get_result(context, f"type_{key}")
    assert str(key_type) == expected, f"Expected type '{expected}', got '{key_type}'"


@when(r'I increment key "(?P<key>[^"]+)" by (?P<amount>-?\d+) in (?P<adapter_type>mock|container|cluster)')
def step_when_incrby(context, key, amount, adapter_type):
    """Increment a counter key."""
    scenario_context = get_current_scenario_context(context)
    value = scenario_context.adapter.incrby(key, int(amount))
    store_result(context, f"counter_{key}", value)


@then(r"the sync counter value should be (?P<expected>-?\d+)")
def step_then_sync_counter_value(context, expected):
    """Verify counter value."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "increment key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "counter"
    value = get_result(context, f"counter_{key}")
    assert value == int(expected), f"Expected counter {expected}, got {value}"


@when(
    r'I mset "(?P<key1>[^"]+)" to "(?P<val1>[^"]+)" and "(?P<key2>[^"]+)" to "(?P<val2>[^"]+)" '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_mset(context, key1, val1, key2, val2, adapter_type):
    """Mset multiple keys."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.adapter.mset({key1: val1, key2: val2})
    store_result(context, "mset_result", result)


@when(r'I mget keys "(?P<key1>[^"]+)" and "(?P<key2>[^"]+)" from (?P<adapter_type>mock|container|cluster)')
def step_when_mget(context, key1, key2, adapter_type):
    """Mget multiple keys."""
    scenario_context = get_current_scenario_context(context)
    key_list = [key1, key2]
    values = scenario_context.adapter.mget(key_list)
    store_result(context, "mget_values", values)


@then(r'the sync mget values should be "(?P<expected>[^"]+)"')
def step_then_sync_mget_values(context, expected):
    """Verify mget returned expected values."""
    expected_list = [v.strip() for v in expected.split(",")]
    values = get_result(context, "mget_values")
    assert list(values) == expected_list, f"Expected {expected_list}, got {values}"


@when(r'I find keys matching "(?P<pattern>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_find_keys(context, pattern, adapter_type):
    """Find keys matching a pattern."""
    scenario_context = get_current_scenario_context(context)
    keys = list(scenario_context.adapter.scan_iter(match=pattern))
    store_result(context, "found_keys", keys)


@then(r'the found keys should include "(?P<key1>[^"]+)" and "(?P<key2>[^"]+)"')
def step_then_found_keys_include(context, key1, key2):
    """Verify found keys include expected keys."""
    keys = get_result(context, "found_keys")
    assert key1 in keys, f"Key '{key1}' not in {keys}"
    assert key2 in keys, f"Key '{key2}' not in {keys}"


@when(r'I scan keys matching "(?P<pattern>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_scan_keys(context, pattern, adapter_type):
    """Scan keys matching a pattern."""
    scenario_context = get_current_scenario_context(context)
    scanned = list(scenario_context.adapter.scan_iter(match=pattern))
    store_result(context, "scanned_keys", scanned)


@then(r'the scanned keys should include "(?P<key1>[^"]+)" and "(?P<key2>[^"]+)"')
def step_then_scanned_keys_include(context, key1, key2):
    """Verify scanned keys include expected keys."""
    keys = get_result(context, "scanned_keys")
    assert key1 in keys, f"Key '{key1}' not in {keys}"
    assert key2 in keys, f"Key '{key2}' not in {keys}"


# ---------------------------------------------------------------------------
# Lists, sets, sorted sets, hashes (sync)
# ---------------------------------------------------------------------------

@when(r'I lpush "(?P<values>[^"]+)" to list "(?P<list_name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_lpush(context, values, list_name, adapter_type):
    """Lpush values to a list."""
    scenario_context = get_current_scenario_context(context)
    value_list = [v.strip() for v in values.split(",")]
    scenario_context.adapter.lpush(list_name, *value_list)


@when(r'I lpop from list "(?P<list_name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_lpop(context, list_name, adapter_type):
    """Lpop from a list."""
    scenario_context = get_current_scenario_context(context)
    value = scenario_context.adapter.lpop(list_name)
    store_result(context, f"popped_{list_name}", value)


@then(r'the sync popped value should be "(?P<expected>[^"]+)"')
def step_then_sync_popped_value(context, expected):
    """Verify popped list value."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "pop from list" in s.name),
        None,
    )
    list_name = prev_step.name.split('"')[1] if prev_step else "mylist"
    value = get_result(context, f"popped_{list_name}")
    assert value == expected, f"Expected popped '{expected}', got '{value}'"


@when(r'I rpop from list "(?P<list_name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_rpop(context, list_name, adapter_type):
    """Rpop from a list."""
    scenario_context = get_current_scenario_context(context)
    value = scenario_context.adapter.rpop(list_name)
    store_result(context, f"popped_{list_name}", value)


@when(
    r'I lrem (?P<count>\d+) "(?P<value>[^"]+)" from list "(?P<list_name>[^"]+)" '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_lrem(context, count, value, list_name, adapter_type):
    """Remove elements from a list."""
    scenario_context = get_current_scenario_context(context)
    scenario_context.adapter.lrem(list_name, int(count), value)


@when(
    r'I lset index (?P<index>\d+) to "(?P<value>[^"]+)" in list "(?P<list_name>[^"]+)" '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_lset(context, index, value, list_name, adapter_type):
    """Set a list element by index."""
    scenario_context = get_current_scenario_context(context)
    scenario_context.adapter.lset(list_name, int(index), value)


@when(r'I check if "(?P<member>[^"]+)" is a member of set "(?P<set_name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_sismember(context, member, set_name, adapter_type):
    """Check set membership."""
    scenario_context = get_current_scenario_context(context)
    is_member = bool(scenario_context.adapter.sismember(set_name, member))
    store_result(context, f"sismember_{set_name}_{member}", is_member)
    store_result(context, "last_sismember_result", is_member)


@then(r"the sync set membership should be (?P<expected>true|false)")
def step_then_sync_set_membership(context, expected):
    """Verify set membership result."""
    is_member = get_result(context, "last_sismember_result")
    expected_bool = expected == "true"
    assert is_member == expected_bool, f"Expected membership {expected_bool}, got {is_member}"


@when(r'I remove "(?P<member>[^"]+)" from set "(?P<set_name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_srem(context, member, set_name, adapter_type):
    """Remove a member from a set."""
    scenario_context = get_current_scenario_context(context)
    scenario_context.adapter.srem(set_name, member)


@when(r'I spop from set "(?P<set_name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_spop(context, set_name, adapter_type):
    """Pop a member from a set."""
    scenario_context = get_current_scenario_context(context)
    scenario_context.adapter.spop(set_name)


@when(r'I union sets "(?P<set1>[^"]+)" and "(?P<set2>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_sunion(context, set1, set2, adapter_type):
    """Union two sets."""
    scenario_context = get_current_scenario_context(context)
    members = scenario_context.adapter.sunion(set1, set2)
    store_result(context, "set_union", members)


@then(r'the sync set union should contain "(?P<expected>[^"]+)"')
def step_then_sync_set_union(context, expected):
    """Verify set union contains expected members."""
    expected_set = {m.strip() for m in expected.split(",")}
    members = get_result(context, "set_union")
    assert members == expected_set, f"Expected union {expected_set}, got {members}"


@when(
    r'I zadd members "(?P<members>[^"]+)" to sorted set "(?P<name>[^"]+)" '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_zadd(context, members, name, adapter_type):
    """Add members to a sorted set."""
    scenario_context = get_current_scenario_context(context)
    mapping = _parse_zadd_members(members)
    scenario_context.adapter.zadd(name, mapping)


@then(r'the sync sorted set "(?P<name>[^"]+)" should have (?P<count>\d+) members')
def step_then_sync_zcard(context, name, count):
    """Verify sorted set cardinality."""
    scenario_context = get_current_scenario_context(context)
    cardinality = scenario_context.adapter.zcard(name)
    assert cardinality == int(count), f"Expected zcard {count}, got {cardinality}"


@when(r'I get zscore of "(?P<member>[^"]+)" in sorted set "(?P<name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_zscore(context, member, name, adapter_type):
    """Get zscore of a member."""
    scenario_context = get_current_scenario_context(context)
    score = scenario_context.adapter.zscore(name, member)
    store_result(context, f"zscore_{name}_{member}", score)


@then(r"the sync zscore should be (?P<expected>[\d.]+)")
def step_then_sync_zscore(context, expected):
    """Verify zscore value."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "get zscore" in s.name),
        None,
    )
    member = prev_step.name.split('"')[1] if prev_step else None
    name = prev_step.name.split('"')[3] if prev_step else None
    score = get_result(context, f"zscore_{name}_{member}")
    assert float(score) == float(expected), f"Expected zscore {expected}, got {score}"


@when(r'I get zrank of "(?P<member>[^"]+)" in sorted set "(?P<name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_zrank(context, member, name, adapter_type):
    """Get zrank of a member."""
    scenario_context = get_current_scenario_context(context)
    rank = scenario_context.adapter.zrank(name, member)
    store_result(context, f"zrank_{name}_{member}", rank)


@then(r"the sync zrank should be (?P<expected>\d+)")
def step_then_sync_zrank(context, expected):
    """Verify zrank value."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "get zrank" in s.name),
        None,
    )
    member = prev_step.name.split('"')[1] if prev_step else None
    name = prev_step.name.split('"')[3] if prev_step else None
    rank = get_result(context, f"zrank_{name}_{member}")
    assert rank == int(expected), f"Expected zrank {expected}, got {rank}"


@when(
    r'I zrange sorted set "(?P<name>[^"]+)" from (?P<start>-?\d+) to (?P<end>-?\d+) '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_zrange(context, name, start, end, adapter_type):
    """Get zrange of a sorted set."""
    scenario_context = get_current_scenario_context(context)
    members = scenario_context.adapter.zrange(name, int(start), int(end))
    store_result(context, "zrange_members", list(members))


@when(
    r'I zrevrange sorted set "(?P<name>[^"]+)" from (?P<start>-?\d+) to (?P<end>-?\d+) '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_zrevrange(context, name, start, end, adapter_type):
    """Get zrevrange of a sorted set."""
    scenario_context = get_current_scenario_context(context)
    members = scenario_context.adapter.zrevrange(name, int(start), int(end))
    store_result(context, "zrange_members", list(members))


@when(
    r'I zrangebyscore sorted set "(?P<name>[^"]+)" from (?P<min_score>\d+) to (?P<max_score>\d+) '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_zrangebyscore(context, name, min_score, max_score, adapter_type):
    """Get zrangebyscore of a sorted set."""
    scenario_context = get_current_scenario_context(context)
    members = scenario_context.adapter.zrangebyscore(name, int(min_score), int(max_score))
    store_result(context, "zrange_members", list(members))


@then(r'the sync zrange members should be "(?P<expected>[^"]+)"')
def step_then_sync_zrange_members(context, expected):
    """Verify zrange member list."""
    expected_list = [m.strip() for m in expected.split(",")]
    members = get_result(context, "zrange_members")
    assert members == expected_list, f"Expected {expected_list}, got {members}"


@when(
    r'I zcount sorted set "(?P<name>[^"]+)" from (?P<min_score>\d+) to (?P<max_score>\d+) '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_zcount(context, name, min_score, max_score, adapter_type):
    """Count members in score range."""
    scenario_context = get_current_scenario_context(context)
    count = scenario_context.adapter.zcount(name, int(min_score), int(max_score))
    store_result(context, "zcount_result", count)


@then(r"the sync zcount should be (?P<expected>\d+)")
def step_then_sync_zcount(context, expected):
    """Verify zcount result."""
    count = get_result(context, "zcount_result")
    assert count == int(expected), f"Expected zcount {expected}, got {count}"


@when(
    r'I zincrby (?P<amount>\d+) "(?P<member>[^"]+)" in sorted set "(?P<name>[^"]+)" '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_zincrby(context, amount, member, name, adapter_type):
    """Increment sorted set member score."""
    scenario_context = get_current_scenario_context(context)
    score = scenario_context.adapter.zincrby(name, float(amount), member)
    store_result(context, f"zscore_{name}_{member}", score)


@when(r'I zrem "(?P<member>[^"]+)" from sorted set "(?P<name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_zrem(context, member, name, adapter_type):
    """Remove member from sorted set."""
    scenario_context = get_current_scenario_context(context)
    scenario_context.adapter.zrem(name, member)


@when(r'I zpopmax from sorted set "(?P<name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_zpopmax(context, name, adapter_type):
    """Pop highest-scored member from sorted set."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.adapter.zpopmax(name)
    store_result(context, "zpop_result", _extract_zpop_member(result))


@then(r'the sync zpop result should be "(?P<expected>[^"]+)"')
def step_then_sync_zpop_result(context, expected):
    """Verify zpop member."""
    member = get_result(context, "zpop_result")
    assert member == expected, f"Expected zpop member '{expected}', got '{member}'"


@when(
    r'I hset mapping "(?P<mapping>[^"]+)" in hash "(?P<hash_name>[^"]+)" '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_hset_mapping(context, mapping, hash_name, adapter_type):
    """Set multiple hash fields."""
    scenario_context = get_current_scenario_context(context)
    field_map = _parse_mapping(mapping)
    scenario_context.adapter.hset(hash_name, mapping=field_map)


@then(r'the sync hash "(?P<hash_name>[^"]+)" should have (?P<count>\d+) fields')
def step_then_sync_hlen(context, hash_name, count):
    """Verify hash field count."""
    scenario_context = get_current_scenario_context(context)
    length = scenario_context.adapter.hlen(hash_name)
    assert length == int(count), f"Expected hlen {count}, got {length}"


@when(
    r'I check if field "(?P<field>[^"]+)" exists in hash "(?P<hash_name>[^"]+)" '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_hexists(context, field, hash_name, adapter_type):
    """Check if hash field exists."""
    scenario_context = get_current_scenario_context(context)
    exists = scenario_context.adapter.hexists(hash_name, field)
    store_result(context, f"hexists_{hash_name}_{field}", exists)


@then(r"the sync hash field exists should be (?P<expected>true|false)")
def step_then_sync_hexists(context, expected):
    """Verify hexists result."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "field" in s.name and "exists in hash" in s.name),
        None,
    )
    field = prev_step.name.split('"')[1] if prev_step else None
    hash_name = prev_step.name.split('"')[3] if prev_step else None
    exists = get_result(context, f"hexists_{hash_name}_{field}")
    expected_bool = expected == "true"
    assert exists == expected_bool, f"Expected hexists {expected_bool}, got {exists}"


@when(
    r'I hmget fields "(?P<fields>[^"]+)" from hash "(?P<hash_name>[^"]+)" '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_hmget(context, fields, hash_name, adapter_type):
    """Get multiple hash fields."""
    scenario_context = get_current_scenario_context(context)
    field_list = [f.strip() for f in fields.split(",")]
    values = scenario_context.adapter.hmget(hash_name, field_list)
    store_result(context, "hmget_values", list(values))


@then(r'the sync hmget values should be "(?P<expected>[^"]+)"')
def step_then_sync_hmget_values(context, expected):
    """Verify hmget values."""
    expected_list = [v.strip() for v in expected.split(",")]
    values = get_result(context, "hmget_values")
    assert list(values) == expected_list, f"Expected {expected_list}, got {values}"


@when(r'I fetch all fields from hash "(?P<hash_name>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_fetch_hash_fields(context, hash_name, adapter_type):
    """Fetch all hash keys and values."""
    scenario_context = get_current_scenario_context(context)
    keys = sorted(scenario_context.adapter.hkeys(hash_name))
    values = [scenario_context.adapter.hget(hash_name, k) for k in keys]
    store_result(context, "hash_keys", keys)
    store_result(context, "hash_values", values)


@then(r'the sync hash keys should be "(?P<expected>[^"]+)"')
def step_then_sync_hash_keys(context, expected):
    """Verify hash keys."""
    expected_keys = [k.strip() for k in expected.split(",")]
    keys = get_result(context, "hash_keys")
    assert keys == expected_keys, f"Expected keys {expected_keys}, got {keys}"


@then(r'the sync hash values should be "(?P<expected>[^"]+)"')
def step_then_sync_hash_values(context, expected):
    """Verify hash values."""
    expected_values = [v.strip() for v in expected.split(",")]
    values = get_result(context, "hash_values")
    assert list(values) == expected_values, f"Expected values {expected_values}, got {values}"


@when(
    r'I delete field "(?P<field>[^"]+)" from hash "(?P<hash_name>[^"]+)" '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_hdel(context, field, hash_name, adapter_type):
    """Delete a hash field."""
    scenario_context = get_current_scenario_context(context)
    scenario_context.adapter.hdel(hash_name, field)


# ---------------------------------------------------------------------------
# Pubsub and pipeline (sync)
# ---------------------------------------------------------------------------

@when(r'I publish "(?P<message>[^"]+)" to channel "(?P<channel>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_publish(context, message, channel, adapter_type):
    """Publish a message to a channel."""
    scenario_context = get_current_scenario_context(context)
    count = scenario_context.adapter.publish(channel, message)
    store_result(context, "publish_count", count)


@then(r"the sync publish count should be at least (?P<min_count>\d+)")
def step_then_sync_publish_count(context, min_count):
    """Verify publish subscriber count."""
    count = get_result(context, "publish_count")
    assert count is not None and count >= int(min_count), f"Expected publish count >= {min_count}, got {count}"


@when(r'I subscribe to channel "(?P<channel>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_subscribe(context, channel, adapter_type):
    """Subscribe to a pubsub channel."""
    scenario_context = get_current_scenario_context(context)
    pubsub = scenario_context.adapter.pubsub()
    pubsub.subscribe(channel)
    pubsub.get_message(timeout=2.0)
    scenario_context.pubsub = pubsub
    scenario_context.pubsub_channel = channel


@then(r'the sync subscribed message should be "(?P<expected>[^"]+)"')
def step_then_sync_subscribed_message(context, expected):
    """Verify message received via subscription."""
    scenario_context = get_current_scenario_context(context)
    pubsub = scenario_context.pubsub
    message = pubsub.get_message(timeout=2.0)
    _cleanup_pubsub(pubsub)
    assert message is not None, "No message received from subscription"
    assert message.get("data") == expected, f"Expected message '{expected}', got {message}"


@when(r'I list pubsub channels matching "(?P<pattern>[^"]+)" in (?P<adapter_type>mock|container|cluster)')
def step_when_pubsub_channels(context, pattern, adapter_type):
    """List active pubsub channels."""
    scenario_context = get_current_scenario_context(context)
    channels = scenario_context.adapter.pubsub_channels(pattern)
    store_result(context, "pubsub_channels", list(channels))


@then(r'the pubsub channels should include "(?P<channel>[^"]+)"')
def step_then_pubsub_channels_include(context, channel):
    """Verify channel is in pubsub channel list."""
    channels = get_result(context, "pubsub_channels")
    channel_names = [str(c) for c in channels]
    assert channel in channel_names, f"Channel '{channel}' not in {channel_names}"


@when(
    r'I run pipeline setting "(?P<key>[^"]+)" to "(?P<value>[^"]+)" and incrementing "(?P<cnt_key>[^"]+)" by 1 '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_run_pipeline(context, key, value, cnt_key, adapter_type):
    """Execute a pipeline with set, incrby, and get."""
    scenario_context = get_current_scenario_context(context)
    pipe = scenario_context.adapter.get_pipeline()
    pipe.set(key, value)
    pipe.incrby(cnt_key, 1)
    pipe.get(key)
    results = pipe.execute()
    store_result(context, "pipeline_results", _format_pipeline_results(results))


@then(r'the sync pipeline results should be "(?P<expected>[^"]+)"')
def step_then_sync_pipeline_results(context, expected):
    """Verify pipeline execute results."""
    results = get_result(context, "pipeline_results")
    assert results == expected, f"Expected pipeline results '{expected}', got '{results}'"


# ---------------------------------------------------------------------------
# Async steps (strings, expiry, counters, multi-key)
# ---------------------------------------------------------------------------

@when(
    r'I store the key "(?P<key>[^"]+)" with value "(?P<value>[^"]+)" '
    r'and expiry (?P<seconds>\d+) seconds in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_store_key_with_expiry(context, key, value, seconds, adapter_type):
    """Store a key-value pair with TTL asynchronously."""
    scenario_context = get_current_scenario_context(context)
    result = await scenario_context.async_adapter.set(key, value, ex=int(seconds))
    store_result(context, f"async_store_expiry_result_{key}", result)


@then(r"the async store with expiry should succeed")
async def step_then_async_store_with_expiry_succeeds(context):
    """Verify async set with expiry succeeded."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "and expiry" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "ttl-key"
    result = get_result(context, f"async_store_expiry_result_{key}")
    assert result in (True, None), f"Async store with expiry failed: {result}"


@when(r'I check the TTL for key "(?P<key>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_check_ttl(context, key, adapter_type):
    """Check TTL for a key asynchronously."""
    scenario_context = get_current_scenario_context(context)
    ttl = await scenario_context.async_adapter.ttl(key)
    store_result(context, f"async_ttl_{key}", ttl)


@then(r"the async TTL should be between (?P<min_ttl>\d+) and (?P<max_ttl>\d+)")
async def step_then_async_ttl_in_range(context, min_ttl, max_ttl):
    """Verify async TTL is within expected range."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "check the TTL" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "ttl-key"
    ttl = get_result(context, f"async_ttl_{key}")
    min_val = int(min_ttl)
    max_val = int(max_ttl)
    assert ttl is not None, "TTL returned None"
    assert min_val <= ttl <= max_val, f"TTL {ttl} not in range [{min_val}, {max_val}]"


@when(r'I check the PTTL for key "(?P<key>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_check_pttl(context, key, adapter_type):
    """Check PTTL for a key asynchronously."""
    scenario_context = get_current_scenario_context(context)
    pttl = await scenario_context.async_adapter.pttl(key)
    store_result(context, f"async_pttl_{key}", pttl)


@then(r"the async PTTL should be positive")
async def step_then_async_pttl_positive(context):
    """Verify async PTTL is positive."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "check the PTTL" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "ttl-key"
    pttl = get_result(context, f"async_pttl_{key}")
    assert pttl is not None and pttl > 0, f"Expected positive PTTL, got {pttl}"


@when(r'I getset key "(?P<key>[^"]+)" to value "(?P<value>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_getset(context, key, value, adapter_type):
    """GetSet a key asynchronously."""
    scenario_context = get_current_scenario_context(context)
    old_value = await scenario_context.async_adapter.getset(key, value)
    store_result(context, f"async_getset_{key}", old_value)


@then(r'the async getset old value should be "(?P<expected>[^"]+)"')
async def step_then_async_getset_old_value(context, expected):
    """Verify async getset returned the old value."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "getset key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else None
    old_value = get_result(context, f"async_getset_{key}")
    assert old_value == expected, f"Expected getset old value '{expected}', got '{old_value}'"


@when(r'I getdel key "(?P<key>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_getdel(context, key, adapter_type):
    """GetDel a key asynchronously."""
    scenario_context = get_current_scenario_context(context)
    value = await scenario_context.async_adapter.getdel(key)
    store_result(context, f"async_getdel_{key}", value)


@then(r'the async getdel value should be "(?P<expected>[^"]+)"')
async def step_then_async_getdel_value(context, expected):
    """Verify async getdel returned the expected value."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "getdel key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else None
    value = get_result(context, f"async_getdel_{key}")
    assert value == expected, f"Expected getdel value '{expected}', got '{value}'"


@when(r'I append "(?P<value>[^"]+)" to key "(?P<key>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_append(context, value, key, adapter_type):
    """Append to a string key asynchronously."""
    scenario_context = get_current_scenario_context(context)
    length = await scenario_context.async_adapter.append(key, value)
    store_result(context, f"async_append_length_{key}", length)


@then(r"the async append length should be (?P<length>\d+)")
async def step_then_async_append_length(context, length):
    """Verify async append returned expected string length."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "append" in s.name),
        None,
    )
    key = prev_step.name.split('"')[3] if prev_step else "app-key"
    actual = get_result(context, f"async_append_length_{key}")
    assert actual == int(length), f"Expected append length {length}, got {actual}"


@when(
    r'I create a (?P<redis_type>string|list|hash|set|zset) key "(?P<key>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_create_key_by_type(context, redis_type, key, adapter_type):
    """Create a key of a specific Redis type asynchronously."""
    scenario_context = get_current_scenario_context(context)
    adapter = scenario_context.async_adapter
    if redis_type == "string":
        await adapter.set(key, "value")
    elif redis_type == "list":
        await adapter.rpush(key, "item")
    elif redis_type == "hash":
        await adapter.hset(key, "field", "value")
    elif redis_type == "set":
        await adapter.sadd(key, "member")
    elif redis_type == "zset":
        await adapter.zadd(key, {"member": 1.0})


@when(r'I check the type of key "(?P<key>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_check_type(context, key, adapter_type):
    """Check the Redis type of a key asynchronously."""
    scenario_context = get_current_scenario_context(context)
    key_type = await scenario_context.async_adapter.type(key)
    store_result(context, f"async_type_{key}", key_type)


@then(r'the async key type should be "(?P<expected>[^"]+)"')
async def step_then_async_key_type(context, expected):
    """Verify async key type matches expected."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "check the type" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "type-key"
    key_type = get_result(context, f"async_type_{key}")
    assert str(key_type) == expected, f"Expected type '{expected}', got '{key_type}'"


@when(r'I increment key "(?P<key>[^"]+)" by (?P<amount>-?\d+) in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_incrby(context, key, amount, adapter_type):
    """Increment a counter key asynchronously."""
    scenario_context = get_current_scenario_context(context)
    value = await scenario_context.async_adapter.incrby(key, int(amount))
    store_result(context, f"async_counter_{key}", value)


@then(r"the async counter value should be (?P<expected>-?\d+)")
async def step_then_async_counter_value(context, expected):
    """Verify async counter value."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "increment key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else "counter"
    value = get_result(context, f"async_counter_{key}")
    assert value == int(expected), f"Expected counter {expected}, got {value}"


@when(
    r'I mset "(?P<key1>[^"]+)" to "(?P<val1>[^"]+)" and "(?P<key2>[^"]+)" to "(?P<val2>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_mset(context, key1, val1, key2, val2, adapter_type):
    """Mset multiple keys asynchronously."""
    scenario_context = get_current_scenario_context(context)
    result = await scenario_context.async_adapter.mset({key1: val1, key2: val2})
    store_result(context, "async_mset_result", result)


@when(r'I mget keys "(?P<key1>[^"]+)" and "(?P<key2>[^"]+)" from async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_mget(context, key1, key2, adapter_type):
    """Mget multiple keys asynchronously."""
    scenario_context = get_current_scenario_context(context)
    key_list = [key1, key2]
    values = await scenario_context.async_adapter.mget(key_list)
    store_result(context, "async_mget_values", values)


@then(r'the async mget values should be "(?P<expected>[^"]+)"')
async def step_then_async_mget_values(context, expected):
    """Verify async mget returned expected values."""
    expected_list = [v.strip() for v in expected.split(",")]
    values = get_result(context, "async_mget_values")
    assert list(values) == expected_list, f"Expected {expected_list}, got {values}"


@when(r'I find keys matching "(?P<pattern>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_find_keys(context, pattern, adapter_type):
    """Find keys matching a pattern asynchronously."""
    scenario_context = get_current_scenario_context(context)
    scanned = await _collect_async_scan_keys(scenario_context.async_adapter, pattern)
    store_result(context, "found_keys", scanned)


@when(r'I scan keys matching "(?P<pattern>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_scan_keys(context, pattern, adapter_type):
    """Scan keys matching a pattern asynchronously."""
    scenario_context = get_current_scenario_context(context)
    scanned = await _collect_async_scan_keys(scenario_context.async_adapter, pattern)
    store_result(context, "scanned_keys", scanned)


# ---------------------------------------------------------------------------
# Async steps (lists, sets, sorted sets, hashes)
# ---------------------------------------------------------------------------

@when(r'I lpush "(?P<values>[^"]+)" to list "(?P<list_name>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_lpush(context, values, list_name, adapter_type):
    """Lpush values to a list asynchronously."""
    scenario_context = get_current_scenario_context(context)
    value_list = [v.strip() for v in values.split(",")]
    await scenario_context.async_adapter.lpush(list_name, *value_list)


@when(r'I lpop from list "(?P<list_name>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_lpop(context, list_name, adapter_type):
    """Lpop from a list asynchronously."""
    scenario_context = get_current_scenario_context(context)
    value = await scenario_context.async_adapter.lpop(list_name)
    store_result(context, f"async_popped_{list_name}", value)


@then(r'the async popped value should be "(?P<expected>[^"]+)"')
async def step_then_async_popped_value(context, expected):
    """Verify async popped list value."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "pop from list" in s.name),
        None,
    )
    list_name = prev_step.name.split('"')[1] if prev_step else "mylist"
    value = get_result(context, f"async_popped_{list_name}")
    assert value == expected, f"Expected popped '{expected}', got '{value}'"


@when(r'I rpop from list "(?P<list_name>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_rpop(context, list_name, adapter_type):
    """Rpop from a list asynchronously."""
    scenario_context = get_current_scenario_context(context)
    value = await scenario_context.async_adapter.rpop(list_name)
    store_result(context, f"async_popped_{list_name}", value)


@when(
    r'I lrem (?P<count>\d+) "(?P<value>[^"]+)" from list "(?P<list_name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_lrem(context, count, value, list_name, adapter_type):
    """Remove elements from a list asynchronously."""
    scenario_context = get_current_scenario_context(context)
    await scenario_context.async_adapter.lrem(list_name, int(count), value)


@when(
    r'I lset index (?P<index>\d+) to "(?P<value>[^"]+)" in list "(?P<list_name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_lset(context, index, value, list_name, adapter_type):
    """Set a list element by index asynchronously."""
    scenario_context = get_current_scenario_context(context)
    await scenario_context.async_adapter.lset(list_name, int(index), value)


@when(
    r'I check if "(?P<member>[^"]+)" is a member of set "(?P<set_name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_sismember(context, member, set_name, adapter_type):
    """Check set membership asynchronously."""
    scenario_context = get_current_scenario_context(context)
    is_member = bool(await scenario_context.async_adapter.sismember(set_name, member))
    store_result(context, f"async_sismember_{set_name}_{member}", is_member)
    store_result(context, "last_async_sismember_result", is_member)


@then(r"the async set membership should be (?P<expected>true|false)")
async def step_then_async_set_membership(context, expected):
    """Verify async set membership result."""
    is_member = get_result(context, "last_async_sismember_result")
    expected_bool = expected == "true"
    assert is_member == expected_bool, f"Expected membership {expected_bool}, got {is_member}"


@when(r'I remove "(?P<member>[^"]+)" from set "(?P<set_name>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_srem(context, member, set_name, adapter_type):
    """Remove a member from a set asynchronously."""
    scenario_context = get_current_scenario_context(context)
    await scenario_context.async_adapter.srem(set_name, member)


@when(r'I spop from set "(?P<set_name>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_spop(context, set_name, adapter_type):
    """Pop a member from a set asynchronously."""
    scenario_context = get_current_scenario_context(context)
    await scenario_context.async_adapter.spop(set_name)


@when(r'I union sets "(?P<set1>[^"]+)" and "(?P<set2>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_sunion(context, set1, set2, adapter_type):
    """Union two sets asynchronously."""
    scenario_context = get_current_scenario_context(context)
    members = await scenario_context.async_adapter.sunion(set1, set2)
    store_result(context, "async_set_union", members)


@then(r'the async set union should contain "(?P<expected>[^"]+)"')
async def step_then_async_set_union(context, expected):
    """Verify async set union contains expected members."""
    expected_set = {m.strip() for m in expected.split(",")}
    members = get_result(context, "async_set_union")
    assert members == expected_set, f"Expected union {expected_set}, got {members}"


@when(
    r'I zadd members "(?P<members>[^"]+)" to sorted set "(?P<name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_zadd(context, members, name, adapter_type):
    """Add members to a sorted set asynchronously."""
    scenario_context = get_current_scenario_context(context)
    mapping = _parse_zadd_members(members)
    await scenario_context.async_adapter.zadd(name, mapping)


@then(r'the async sorted set "(?P<name>[^"]+)" should have (?P<count>\d+) members')
async def step_then_async_zcard(context, name, count):
    """Verify async sorted set cardinality."""
    scenario_context = get_current_scenario_context(context)
    cardinality = await scenario_context.async_adapter.zcard(name)
    assert cardinality == int(count), f"Expected zcard {count}, got {cardinality}"


@when(
    r'I get zscore of "(?P<member>[^"]+)" in sorted set "(?P<name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_zscore(context, member, name, adapter_type):
    """Get zscore of a member asynchronously."""
    scenario_context = get_current_scenario_context(context)
    score = await scenario_context.async_adapter.zscore(name, member)
    store_result(context, f"async_zscore_{name}_{member}", score)


@then(r"the async zscore should be (?P<expected>[\d.]+)")
async def step_then_async_zscore(context, expected):
    """Verify async zscore value."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "get zscore" in s.name),
        None,
    )
    member = prev_step.name.split('"')[1] if prev_step else None
    name = prev_step.name.split('"')[3] if prev_step else None
    score = get_result(context, f"async_zscore_{name}_{member}")
    assert float(score) == float(expected), f"Expected zscore {expected}, got {score}"


@when(
    r'I get zrank of "(?P<member>[^"]+)" in sorted set "(?P<name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_zrank(context, member, name, adapter_type):
    """Get zrank of a member asynchronously."""
    scenario_context = get_current_scenario_context(context)
    rank = await scenario_context.async_adapter.zrank(name, member)
    store_result(context, f"async_zrank_{name}_{member}", rank)


@then(r"the async zrank should be (?P<expected>\d+)")
async def step_then_async_zrank(context, expected):
    """Verify async zrank value."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "get zrank" in s.name),
        None,
    )
    member = prev_step.name.split('"')[1] if prev_step else None
    name = prev_step.name.split('"')[3] if prev_step else None
    rank = get_result(context, f"async_zrank_{name}_{member}")
    assert rank == int(expected), f"Expected zrank {expected}, got {rank}"


@when(
    r'I zrange sorted set "(?P<name>[^"]+)" from (?P<start>-?\d+) to (?P<end>-?\d+) '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_zrange(context, name, start, end, adapter_type):
    """Get zrange of a sorted set asynchronously."""
    scenario_context = get_current_scenario_context(context)
    members = await scenario_context.async_adapter.zrange(name, int(start), int(end))
    store_result(context, "async_zrange_members", list(members))


@when(
    r'I zrevrange sorted set "(?P<name>[^"]+)" from (?P<start>-?\d+) to (?P<end>-?\d+) '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_zrevrange(context, name, start, end, adapter_type):
    """Get zrevrange of a sorted set asynchronously."""
    scenario_context = get_current_scenario_context(context)
    members = await scenario_context.async_adapter.zrevrange(name, int(start), int(end))
    store_result(context, "async_zrange_members", list(members))


@when(
    r'I zrangebyscore sorted set "(?P<name>[^"]+)" from (?P<min_score>\d+) to (?P<max_score>\d+) '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_zrangebyscore(context, name, min_score, max_score, adapter_type):
    """Get zrangebyscore of a sorted set asynchronously."""
    scenario_context = get_current_scenario_context(context)
    members = await scenario_context.async_adapter.zrangebyscore(name, int(min_score), int(max_score))
    store_result(context, "async_zrange_members", list(members))


@then(r'the async zrange members should be "(?P<expected>[^"]+)"')
async def step_then_async_zrange_members(context, expected):
    """Verify async zrange member list."""
    expected_list = [m.strip() for m in expected.split(",")]
    members = get_result(context, "async_zrange_members")
    assert members == expected_list, f"Expected {expected_list}, got {members}"


@when(
    r'I zcount sorted set "(?P<name>[^"]+)" from (?P<min_score>\d+) to (?P<max_score>\d+) '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_zcount(context, name, min_score, max_score, adapter_type):
    """Count members in score range asynchronously."""
    scenario_context = get_current_scenario_context(context)
    count = await scenario_context.async_adapter.zcount(name, int(min_score), int(max_score))
    store_result(context, "async_zcount_result", count)


@then(r"the async zcount should be (?P<expected>\d+)")
async def step_then_async_zcount(context, expected):
    """Verify async zcount result."""
    count = get_result(context, "async_zcount_result")
    assert count == int(expected), f"Expected zcount {expected}, got {count}"


@when(
    r'I zincrby (?P<amount>\d+) "(?P<member>[^"]+)" in sorted set "(?P<name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_zincrby(context, amount, member, name, adapter_type):
    """Increment sorted set member score asynchronously."""
    scenario_context = get_current_scenario_context(context)
    score = await scenario_context.async_adapter.zincrby(name, float(amount), member)
    store_result(context, f"async_zscore_{name}_{member}", score)


@when(
    r'I zrem "(?P<member>[^"]+)" from sorted set "(?P<name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_zrem(context, member, name, adapter_type):
    """Remove member from sorted set asynchronously."""
    scenario_context = get_current_scenario_context(context)
    await scenario_context.async_adapter.zrem(name, member)


@when(r'I zpopmax from sorted set "(?P<name>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_zpopmax(context, name, adapter_type):
    """Pop highest-scored member from sorted set asynchronously."""
    scenario_context = get_current_scenario_context(context)
    result = await scenario_context.async_adapter.zpopmax(name)
    store_result(context, "async_zpop_result", _extract_zpop_member(result))


@then(r'the async zpop result should be "(?P<expected>[^"]+)"')
async def step_then_async_zpop_result(context, expected):
    """Verify async zpop member."""
    member = get_result(context, "async_zpop_result")
    assert member == expected, f"Expected zpop member '{expected}', got '{member}'"


@when(
    r'I hset mapping "(?P<mapping>[^"]+)" in hash "(?P<hash_name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_hset_mapping(context, mapping, hash_name, adapter_type):
    """Set multiple hash fields asynchronously."""
    scenario_context = get_current_scenario_context(context)
    field_map = _parse_mapping(mapping)
    await scenario_context.async_adapter.hset(hash_name, mapping=field_map)


@then(r'the async hash "(?P<hash_name>[^"]+)" should have (?P<count>\d+) fields')
async def step_then_async_hlen(context, hash_name, count):
    """Verify async hash field count."""
    scenario_context = get_current_scenario_context(context)
    length = await scenario_context.async_adapter.hlen(hash_name)
    assert length == int(count), f"Expected hlen {count}, got {length}"


@when(
    r'I check if field "(?P<field>[^"]+)" exists in hash "(?P<hash_name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_hexists(context, field, hash_name, adapter_type):
    """Check if hash field exists asynchronously."""
    scenario_context = get_current_scenario_context(context)
    exists = await scenario_context.async_adapter.hexists(hash_name, field)
    store_result(context, f"async_hexists_{hash_name}_{field}", exists)


@then(r"the async hash field exists should be (?P<expected>true|false)")
async def step_then_async_hexists(context, expected):
    """Verify async hexists result."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "field" in s.name and "exists in hash" in s.name),
        None,
    )
    field = prev_step.name.split('"')[1] if prev_step else None
    hash_name = prev_step.name.split('"')[3] if prev_step else None
    exists = get_result(context, f"async_hexists_{hash_name}_{field}")
    expected_bool = expected == "true"
    assert exists == expected_bool, f"Expected hexists {expected_bool}, got {exists}"


@when(
    r'I hmget fields "(?P<fields>[^"]+)" from hash "(?P<hash_name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_hmget(context, fields, hash_name, adapter_type):
    """Get multiple hash fields asynchronously."""
    scenario_context = get_current_scenario_context(context)
    field_list = [f.strip() for f in fields.split(",")]
    values = await scenario_context.async_adapter.hmget(hash_name, field_list)
    store_result(context, "async_hmget_values", list(values))


@then(r'the async hmget values should be "(?P<expected>[^"]+)"')
async def step_then_async_hmget_values(context, expected):
    """Verify async hmget values."""
    expected_list = [v.strip() for v in expected.split(",")]
    values = get_result(context, "async_hmget_values")
    assert list(values) == expected_list, f"Expected {expected_list}, got {values}"


@when(r'I fetch all fields from hash "(?P<hash_name>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_fetch_hash_fields(context, hash_name, adapter_type):
    """Fetch all hash keys and values asynchronously."""
    scenario_context = get_current_scenario_context(context)
    keys = sorted(await scenario_context.async_adapter.hkeys(hash_name))
    values = [await scenario_context.async_adapter.hget(hash_name, k) for k in keys]
    store_result(context, "async_hash_keys", keys)
    store_result(context, "async_hash_values", values)


@then(r'the async hash keys should be "(?P<expected>[^"]+)"')
async def step_then_async_hash_keys(context, expected):
    """Verify async hash keys."""
    expected_keys = [k.strip() for k in expected.split(",")]
    keys = get_result(context, "async_hash_keys")
    assert keys == expected_keys, f"Expected keys {expected_keys}, got {keys}"


@then(r'the async hash values should be "(?P<expected>[^"]+)"')
async def step_then_async_hash_values(context, expected):
    """Verify async hash values."""
    expected_values = [v.strip() for v in expected.split(",")]
    values = get_result(context, "async_hash_values")
    assert list(values) == expected_values, f"Expected values {expected_values}, got {values}"


@when(
    r'I delete field "(?P<field>[^"]+)" from hash "(?P<hash_name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_hdel(context, field, hash_name, adapter_type):
    """Delete a hash field asynchronously."""
    scenario_context = get_current_scenario_context(context)
    await scenario_context.async_adapter.hdel(hash_name, field)


# ---------------------------------------------------------------------------
# Pubsub and pipeline (async)
# ---------------------------------------------------------------------------

@when(r'I publish "(?P<message>[^"]+)" to channel "(?P<channel>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_publish(context, message, channel, adapter_type):
    """Publish a message to a channel asynchronously."""
    scenario_context = get_current_scenario_context(context)
    count = await scenario_context.async_adapter.publish(channel, message)
    store_result(context, "async_publish_count", count)


@then(r"the async publish count should be at least (?P<min_count>\d+)")
async def step_then_async_publish_count(context, min_count):
    """Verify async publish subscriber count."""
    count = get_result(context, "async_publish_count")
    assert count is not None and count >= int(min_count), f"Expected publish count >= {min_count}, got {count}"


@when(r'I subscribe to channel "(?P<channel>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_subscribe(context, channel, adapter_type):
    """Subscribe to a pubsub channel asynchronously."""
    scenario_context = get_current_scenario_context(context)
    pubsub = await scenario_context.async_adapter.pubsub()
    await pubsub.subscribe(channel)
    await pubsub.get_message(timeout=2.0)
    scenario_context.pubsub = pubsub
    scenario_context.pubsub_channel = channel


@then(r'the async subscribed message should be "(?P<expected>[^"]+)"')
async def step_then_async_subscribed_message(context, expected):
    """Verify message received via async subscription."""
    scenario_context = get_current_scenario_context(context)
    pubsub = scenario_context.pubsub
    message = await pubsub.get_message(timeout=2.0)
    await pubsub.unsubscribe()
    await pubsub.aclose()
    assert message is not None, "No message received from subscription"
    assert message.get("data") == expected, f"Expected message '{expected}', got {message}"


@when(r'I list pubsub channels matching "(?P<pattern>[^"]+)" in async (?P<adapter_type>mock|container|cluster)')
async def step_when_async_pubsub_channels(context, pattern, adapter_type):
    """List active pubsub channels asynchronously."""
    scenario_context = get_current_scenario_context(context)
    channels = await scenario_context.async_adapter.pubsub_channels(pattern)
    store_result(context, "pubsub_channels", list(channels))


@when(
    r'I run pipeline setting "(?P<key>[^"]+)" to "(?P<value>[^"]+)" and incrementing "(?P<cnt_key>[^"]+)" by 1 '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_run_pipeline(context, key, value, cnt_key, adapter_type):
    """Execute a pipeline with set, incrby, and get asynchronously."""
    scenario_context = get_current_scenario_context(context)
    pipe = await scenario_context.async_adapter.get_pipeline()
    pipe.set(key, value)
    pipe.incrby(cnt_key, 1)
    pipe.get(key)
    results = await pipe.execute()
    store_result(context, "async_pipeline_results", _format_pipeline_results(results))


@then(r'the async pipeline results should be "(?P<expected>[^"]+)"')
async def step_then_async_pipeline_results(context, expected):
    """Verify async pipeline execute results."""
    results = get_result(context, "async_pipeline_results")
    assert results == expected, f"Expected pipeline results '{expected}', got '{results}'"
