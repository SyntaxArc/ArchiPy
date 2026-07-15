"""Implementation of steps for testing RedisMock and AsyncRedisMock.

This module contains step definitions for simplified synchronous and asynchronous
Redis mock scenarios as defined in the Redis Mock Testing feature.
"""

import json
import logging

from behave import given, then, use_step_matcher, when
from features.test_containers import ContainerManager
from features.test_helpers import get_current_scenario_context

from archipy.adapters.redis.adapters import AsyncRedisAdapter, RedisAdapter
from archipy.adapters.redis.mocks import AsyncRedisMock, RedisMock
from archipy.configs.config_template import RedisConfig
from archipy.models.dtos.redis.search.aggregation_dto import AggregationDTO
from archipy.models.dtos.redis.search.document_dto import HashDocumentUpsertDTO, JsonDocumentUpsertDTO
from archipy.models.dtos.redis.search.index_schema_dto import (
    IndexSchemaDTO,
    NumericFieldConfig,
    TagFieldConfig,
    TextFieldConfig,
    VectorFieldConfig,
)
from archipy.models.dtos.redis.search.search_query_dto import SearchQueryDTO
from archipy.models.types.redis_search_types import RedisIndexType, VectorAlgorithm, VectorDistanceMetric

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


def _zset_scores_to_dict(result) -> dict[str, float]:
    """Convert a withscores zunion/zinter result into a member-to-score mapping."""
    if not result:
        return {}
    scores: dict[str, float] = {}
    for item in result:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            scores[str(item[0])] = float(item[1])
    return scores


def _format_array_value(value) -> str:
    """Format an array element value for Gherkin assertions."""
    if value is None:
        return "None"
    return str(value)


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


# ---------------------------------------------------------------------------
# Redis 8.8 — Array data structure (sync)
# ---------------------------------------------------------------------------


@when(
    r'I arset index (?P<index>\d+) to "(?P<values>[^"]+)" in array "(?P<name>[^"]+)" '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_arset(context, index, values, name, adapter_type):
    """Set contiguous values in a Redis 8.8 array."""
    scenario_context = get_current_scenario_context(context)
    value_list = [v.strip() for v in values.split(",")]
    result = scenario_context.adapter.arset(name, int(index), *value_list)
    store_result(context, f"arset_result_{name}", result)


@then(r'the sync array "(?P<name>[^"]+)" should have (?P<count>\d+) elements')
def step_then_sync_arlen(context, name, count):
    """Verify array element count."""
    scenario_context = get_current_scenario_context(context)
    length = scenario_context.adapter.arlen(name)
    assert length == int(count), f"Expected array length {count}, got {length}"


@when(
    r'I get array index (?P<index>\d+) from "(?P<name>[^"]+)" '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_arget(context, index, name, adapter_type):
    """Get a value from a Redis 8.8 array by index."""
    scenario_context = get_current_scenario_context(context)
    value = scenario_context.adapter.arget(name, int(index))
    store_result(context, "array_value", _format_array_value(value))


@then(r'the sync array value should be "(?P<expected>[^"]+)"')
def step_then_sync_array_value(context, expected):
    """Verify array element value."""
    value = get_result(context, "array_value")
    assert value == expected, f"Expected array value '{expected}', got '{value}'"


@when(
    r'I delete array index (?P<index>\d+) from "(?P<name>[^"]+)" '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_ardel(context, index, name, adapter_type):
    """Delete an index from a Redis 8.8 array."""
    scenario_context = get_current_scenario_context(context)
    scenario_context.adapter.ardel(name, int(index))


@when(
    r'I arring size (?P<size>\d+) with "(?P<values>[^"]+)" into array "(?P<name>[^"]+)" '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_arring(context, size, values, name, adapter_type):
    """Insert values into an array ring buffer."""
    scenario_context = get_current_scenario_context(context)
    value_list = [v.strip() for v in values.split(",")]
    scenario_context.adapter.arring(name, int(size), *value_list)


# ---------------------------------------------------------------------------
# Redis 8.8 — Array data structure (async)
# ---------------------------------------------------------------------------


@when(
    r'I arset index (?P<index>\d+) to "(?P<values>[^"]+)" in array "(?P<name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_arset(context, index, values, name, adapter_type):
    """Set contiguous values in a Redis 8.8 array asynchronously."""
    scenario_context = get_current_scenario_context(context)
    value_list = [v.strip() for v in values.split(",")]
    result = await scenario_context.async_adapter.arset(name, int(index), *value_list)
    store_result(context, f"arset_result_{name}", result)


@then(r'the async array "(?P<name>[^"]+)" should have (?P<count>\d+) elements')
async def step_then_async_arlen(context, name, count):
    """Verify array element count asynchronously."""
    scenario_context = get_current_scenario_context(context)
    length = await scenario_context.async_adapter.arlen(name)
    assert length == int(count), f"Expected array length {count}, got {length}"


@when(
    r'I get array index (?P<index>\d+) from "(?P<name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_arget(context, index, name, adapter_type):
    """Get a value from a Redis 8.8 array by index asynchronously."""
    scenario_context = get_current_scenario_context(context)
    value = await scenario_context.async_adapter.arget(name, int(index))
    store_result(context, "async_array_value", _format_array_value(value))


@then(r'the async array value should be "(?P<expected>[^"]+)"')
async def step_then_async_array_value(context, expected):
    """Verify array element value asynchronously."""
    value = get_result(context, "async_array_value")
    assert value == expected, f"Expected array value '{expected}', got '{value}'"


@when(
    r'I arring size (?P<size>\d+) with "(?P<values>[^"]+)" into array "(?P<name>[^"]+)" '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_arring(context, size, values, name, adapter_type):
    """Insert values into an array ring buffer asynchronously."""
    scenario_context = get_current_scenario_context(context)
    value_list = [v.strip() for v in values.split(",")]
    await scenario_context.async_adapter.arring(name, int(size), *value_list)


# ---------------------------------------------------------------------------
# Redis 8.8 — INCREX rate limiter (sync)
# ---------------------------------------------------------------------------


@when(
    r'I increx key "(?P<key>[^"]+)" by (?P<amount>\d+) with upper bound (?P<ubound>\d+) '
    r'and expiry (?P<seconds>\d+) seconds in (?P<adapter_type>mock|container|cluster)',
)
def step_when_increx(context, key, amount, ubound, seconds, adapter_type):
    """Increment a windowed counter using INCREX."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.adapter.increx(
        key,
        byint=int(amount),
        ubound=int(ubound),
        ex=int(seconds),
    )
    store_result(context, f"increx_result_{key}", result)


@then(r"the sync increx counter should be (?P<expected>\d+)")
def step_then_sync_increx_counter(context, expected):
    """Verify INCREX new counter value."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "increx key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else None
    result = get_result(context, f"increx_result_{key}")
    assert result is not None and int(result[0]) == int(expected), f"Expected counter {expected}, got {result}"


@then(r"the sync increx applied increment should be (?P<expected>\d+)")
def step_then_sync_increx_applied(context, expected):
    """Verify INCREX applied increment amount."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "increx key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else None
    result = get_result(context, f"increx_result_{key}")
    assert result is not None and int(result[1]) == int(expected), f"Expected applied increment {expected}, got {result}"


# ---------------------------------------------------------------------------
# Redis 8.8 — INCREX rate limiter (async)
# ---------------------------------------------------------------------------


@when(
    r'I increx key "(?P<key>[^"]+)" by (?P<amount>\d+) with upper bound (?P<ubound>\d+) '
    r'and expiry (?P<seconds>\d+) seconds in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_increx(context, key, amount, ubound, seconds, adapter_type):
    """Increment a windowed counter using INCREX asynchronously."""
    scenario_context = get_current_scenario_context(context)
    result = await scenario_context.async_adapter.increx(
        key,
        byint=int(amount),
        ubound=int(ubound),
        ex=int(seconds),
    )
    store_result(context, f"async_increx_result_{key}", result)


@then(r"the async increx counter should be (?P<expected>\d+)")
async def step_then_async_increx_counter(context, expected):
    """Verify INCREX new counter value asynchronously."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "increx key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else None
    result = get_result(context, f"async_increx_result_{key}")
    assert result is not None and int(result[0]) == int(expected), f"Expected counter {expected}, got {result}"


@then(r"the async increx applied increment should be (?P<expected>\d+)")
async def step_then_async_increx_applied(context, expected):
    """Verify INCREX applied increment amount asynchronously."""
    prev_step = next(
        (s for s in reversed(context.scenario.steps) if s.step_type == "when" and "increx key" in s.name),
        None,
    )
    key = prev_step.name.split('"')[1] if prev_step else None
    result = get_result(context, f"async_increx_result_{key}")
    assert result is not None and int(result[1]) == int(expected), f"Expected applied increment {expected}, got {result}"


# ---------------------------------------------------------------------------
# Redis 8.8 — ZUNION/ZINTER COUNT aggregator (sync)
# ---------------------------------------------------------------------------


@when(
    r'I zunion sets "(?P<set1>[^"]+)" and "(?P<set2>[^"]+)" with COUNT aggregator '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_zunion_count(context, set1, set2, adapter_type):
    """Compute sorted set union with COUNT aggregator."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.adapter.zunion([set1, set2], aggregate="COUNT", withscores=True)
    store_result(context, "zunion_count_scores", _zset_scores_to_dict(result))


@then(r'the sync zunion COUNT score for "(?P<member>[^"]+)" should be (?P<expected>[\d.]+)')
def step_then_sync_zunion_count_score(context, member, expected):
    """Verify ZUNION COUNT aggregator score for a member."""
    scores = get_result(context, "zunion_count_scores")
    assert member in scores, f"Member '{member}' not in zunion result: {scores}"
    assert scores[member] == float(expected), f"Expected score {expected} for '{member}', got {scores[member]}"


@when(
    r'I zinter sets "(?P<set1>[^"]+)" and "(?P<set2>[^"]+)" with COUNT aggregator '
    r'in (?P<adapter_type>mock|container|cluster)',
)
def step_when_zinter_count(context, set1, set2, adapter_type):
    """Compute sorted set intersection with COUNT aggregator."""
    scenario_context = get_current_scenario_context(context)
    result = scenario_context.adapter.zinter([set1, set2], aggregate="COUNT", withscores=True)
    store_result(context, "zinter_count_scores", _zset_scores_to_dict(result))


@then(r'the sync zinter COUNT score for "(?P<member>[^"]+)" should be (?P<expected>[\d.]+)')
def step_then_sync_zinter_count_score(context, member, expected):
    """Verify ZINTER COUNT aggregator score for a member."""
    scores = get_result(context, "zinter_count_scores")
    assert member in scores, f"Member '{member}' not in zinter result: {scores}"
    assert scores[member] == float(expected), f"Expected score {expected} for '{member}', got {scores[member]}"


# ---------------------------------------------------------------------------
# Redis 8.8 — ZUNION/ZINTER COUNT aggregator (async)
# ---------------------------------------------------------------------------


@when(
    r'I zunion sets "(?P<set1>[^"]+)" and "(?P<set2>[^"]+)" with COUNT aggregator '
    r'in async (?P<adapter_type>mock|container|cluster)',
)
async def step_when_async_zunion_count(context, set1, set2, adapter_type):
    """Compute sorted set union with COUNT aggregator asynchronously."""
    scenario_context = get_current_scenario_context(context)
    result = await scenario_context.async_adapter.zunion([set1, set2], aggregate="COUNT", withscores=True)
    store_result(context, "async_zunion_count_scores", _zset_scores_to_dict(result))


@then(r'the async zunion COUNT score for "(?P<member>[^"]+)" should be (?P<expected>[\d.]+)')
async def step_then_async_zunion_count_score(context, member, expected):
    """Verify ZUNION COUNT aggregator score for a member asynchronously."""
    scores = get_result(context, "async_zunion_count_scores")
    assert member in scores, f"Member '{member}' not in zunion result: {scores}"
    assert scores[member] == float(expected), f"Expected score {expected} for '{member}', got {scores[member]}"


# ---------------------------------------------------------------------------
# Redis 8.8 — Hash subkey notifications (sync)
# ---------------------------------------------------------------------------


@when(r"I enable hash subkey notifications in (?P<adapter_type>mock|container|cluster)")
def step_when_enable_subkey_notifications(context, adapter_type):
    """Enable Redis 8.8 hash subkey notifications."""
    scenario_context = get_current_scenario_context(context)
    scenario_context.adapter.config_set("notify-keyspace-events", "STIVh")


@when(r"I psubscribe to subkeyevent hset channel in (?P<adapter_type>mock|container|cluster)")
def step_when_psubscribe_subkeyevent_hset(context, adapter_type):
    """Subscribe to hash field hset subkeyevent notifications."""
    scenario_context = get_current_scenario_context(context)
    pubsub = scenario_context.adapter.pubsub()
    pubsub.psubscribe("__subkeyevent@0__:hset")
    pubsub.get_message(timeout=2.0)
    scenario_context.pubsub = pubsub


@then(r'the sync subkey notification should include field "(?P<field>[^"]+)"')
def step_then_sync_subkey_notification(context, field):
    """Verify a hash subkey notification was received for the given field."""
    scenario_context = get_current_scenario_context(context)
    pubsub = scenario_context.pubsub
    message = pubsub.get_message(timeout=2.0)
    _cleanup_pubsub(pubsub)
    assert message is not None, "No subkey notification received"
    data = str(message.get("data", ""))
    assert field in data, f"Expected field '{field}' in notification data '{data}'"


# ---------------------------------------------------------------------------
# Redis 8.8 — Hash subkey notifications (async)
# ---------------------------------------------------------------------------


@when(r"I enable hash subkey notifications in async (?P<adapter_type>mock|container|cluster)")
async def step_when_async_enable_subkey_notifications(context, adapter_type):
    """Enable Redis 8.8 hash subkey notifications asynchronously."""
    scenario_context = get_current_scenario_context(context)
    await scenario_context.async_adapter.config_set("notify-keyspace-events", "STIVh")


@when(r"I psubscribe to subkeyevent hset channel in async (?P<adapter_type>mock|container|cluster)")
async def step_when_async_psubscribe_subkeyevent_hset(context, adapter_type):
    """Subscribe to hash field hset subkeyevent notifications asynchronously."""
    scenario_context = get_current_scenario_context(context)
    pubsub = await scenario_context.async_adapter.pubsub()
    await pubsub.psubscribe("__subkeyevent@0__:hset")
    await pubsub.get_message(timeout=2.0)
    scenario_context.pubsub = pubsub


@then(r'the async subkey notification should include field "(?P<field>[^"]+)"')
async def step_then_async_subkey_notification(context, field):
    """Verify a hash subkey notification was received for the given field asynchronously."""
    scenario_context = get_current_scenario_context(context)
    pubsub = scenario_context.pubsub
    message = await pubsub.get_message(timeout=2.0)
    await pubsub.unsubscribe()
    await pubsub.aclose()
    assert message is not None, "No subkey notification received"
    data = str(message.get("data", ""))
    assert field in data, f"Expected field '{field}' in notification data '{data}'"


def _parse_index_type(index_type: str) -> RedisIndexType:
    """Parse a Gherkin index type label into RedisIndexType."""
    return RedisIndexType(index_type)


def _search_schema(index_type: RedisIndexType) -> IndexSchemaDTO:
    """Build a default RediSearch schema for the given index document type."""
    return IndexSchemaDTO(
        fields=[
            TextFieldConfig(name="title"),
            TagFieldConfig(name="category"),
            VectorFieldConfig(
                name="embedding",
                dim=3,
                distance_metric=VectorDistanceMetric.COSINE,
                algorithm=VectorAlgorithm.HNSW,
            ),
        ],
        index_type=index_type,
    )


def _upsert_search_document(
    handle,
    doc_id: str,
    fields: dict[str, str],
    vector: list[float],
    index_type: RedisIndexType,
) -> None:
    """Upsert a document into a HASH or JSON search index."""
    if index_type == RedisIndexType.HASH:
        handle.upsert_hash(
            doc_id,
            fields,
            vector_field="embedding",
            vector=vector,
        )
        return
    handle.upsert_json(doc_id, {**fields, "embedding": vector})


def _parse_search_vector(raw_vector: str) -> list[float]:
    return [float(value) for value in json.loads(raw_vector)]


def _search_index_field_names(info: dict) -> list[str]:
    """Extract indexed field names from a RediSearch FT.INFO response."""
    attributes = info.get("attributes", [])
    field_names: list[str] = []
    for attribute in attributes:
        field_name: str | None = None
        if isinstance(attribute, dict):
            raw_name = attribute.get("identifier") or attribute.get("attribute")
            field_name = str(raw_name) if raw_name is not None else None
        elif isinstance(attribute, (list, tuple)):
            decoded = [
                item.decode() if isinstance(item, bytes) else str(item)
                for item in attribute
            ]
            if "identifier" in decoded:
                field_name = decoded[decoded.index("identifier") + 1]
        if field_name is None:
            continue
        if field_name.startswith("$."):
            field_name = field_name[2:]
        field_names.append(field_name)
    return field_names


def _get_search_document(context, doc_id: str, index_name: str) -> dict:
    return get_current_scenario_context(context).adapter.search_index(index_name).get_document(doc_id)


@given(
    r'search index "(?P<index_name>[^"]+)" exists with prefix "(?P<prefix>[^"]+)" for (?P<index_type>HASH|JSON) documents',
)
def step_given_search_index_exists(context, index_name, prefix, index_type):
    """Create a search index if it does not already exist."""
    scenario_context = get_current_scenario_context(context)
    adapter = scenario_context.adapter
    handle = adapter.search_index(index_name)
    resolved_type = _parse_index_type(index_type)
    if index_name not in adapter.list_search_indexes():
        handle.create_index(_search_schema(resolved_type), prefix=prefix, index_type=resolved_type)
    scenario_context.store("last_index_name", index_name)
    scenario_context.store("last_index_type", index_type)


@given(
    r'async search index "(?P<index_name>[^"]+)" exists with prefix "(?P<prefix>[^"]+)" for (?P<index_type>HASH|JSON) documents',
)
async def step_given_async_search_index_exists(context, index_name, prefix, index_type):
    """Create a search index asynchronously if needed."""
    scenario_context = get_current_scenario_context(context)
    adapter = scenario_context.async_adapter
    indexes = await adapter.list_search_indexes()
    handle = adapter.search_index(index_name)
    resolved_type = _parse_index_type(index_type)
    if index_name not in indexes:
        await handle.create_index(_search_schema(resolved_type), prefix=prefix, index_type=resolved_type)
    scenario_context.store("last_index_name", index_name)
    scenario_context.store("last_index_type", index_type)


@when(
    r'I create search index "(?P<index_name>[^"]+)" with prefix "(?P<prefix>[^"]+)" for (?P<index_type>HASH|JSON) documents',
)
def step_when_create_search_index(context, index_name, prefix, index_type):
    """Create a HASH or JSON search index."""
    scenario_context = get_current_scenario_context(context)
    adapter = scenario_context.adapter
    handle = adapter.search_index(index_name)
    resolved_type = _parse_index_type(index_type)
    handle.create_index(_search_schema(resolved_type), prefix=prefix, index_type=resolved_type)
    scenario_context.store("last_index_name", index_name)
    scenario_context.store("last_index_type", index_type)


@when(
    r'I upsert search document "(?P<doc_id>[^"]+)" with title "(?P<title>[^"]+)" and vector "(?P<vector>[^"]+)" '
    r'for (?P<index_type>HASH|JSON) documents',
)
def step_when_upsert_search_document(context, doc_id, title, vector, index_type):
    """Upsert a HASH or JSON search document with a vector embedding."""
    scenario_context = get_current_scenario_context(context)
    index_name = scenario_context.get("last_index_name")
    handle = scenario_context.adapter.search_index(index_name)
    _upsert_search_document(
        handle,
        doc_id,
        {"title": title},
        _parse_search_vector(vector),
        _parse_index_type(index_type),
    )


@when(
    r'I upsert search document "(?P<doc_id>[^"]+)" asynchronously with title "(?P<title>[^"]+)" '
    r'and vector "(?P<vector>[^"]+)" for (?P<index_type>HASH|JSON) documents',
)
async def step_when_upsert_search_document_async(context, doc_id, title, vector, index_type):
    """Upsert a HASH or JSON search document asynchronously."""
    scenario_context = get_current_scenario_context(context)
    index_name = scenario_context.get("last_index_name")
    handle = scenario_context.async_adapter.search_index(index_name)
    resolved_type = _parse_index_type(index_type)
    if resolved_type == RedisIndexType.HASH:
        await handle.upsert_hash(
            doc_id,
            {"title": title},
            vector_field="embedding",
            vector=_parse_search_vector(vector),
        )
    else:
        await handle.upsert_json(
            doc_id,
            {"title": title, "embedding": _parse_search_vector(vector)},
        )


@given(
    r'search document "(?P<doc_id>[^"]+)" exists with title "(?P<title>[^"]+)" and vector "(?P<vector>[^"]+)" '
    r'for (?P<index_type>HASH|JSON) documents',
)
def step_given_search_document_exists(context, doc_id, title, vector, index_type):
    """Seed a HASH or JSON document in the active search index."""
    step_when_upsert_search_document(context, doc_id, title, vector, index_type)


@given(
    r'search document "(?P<doc_id>[^"]+)" exists with title "(?P<title>[^"]+)" category "(?P<category>[^"]+)" '
    r'and vector "(?P<vector>[^"]+)" for (?P<index_type>HASH|JSON) documents',
)
def step_given_search_document_with_category_exists(context, doc_id, title, category, vector, index_type):
    """Seed a HASH or JSON document with a category tag."""
    scenario_context = get_current_scenario_context(context)
    index_name = scenario_context.get("last_index_name")
    handle = scenario_context.adapter.search_index(index_name)
    _upsert_search_document(
        handle,
        doc_id,
        {"title": title, "category": category},
        _parse_search_vector(vector),
        _parse_index_type(index_type),
    )


@when(r'I upsert json document "(?P<doc_id>[^"]+)" with payload (?P<payload>\{.*\})')
def step_when_upsert_json_document(context, doc_id, payload):
    """Upsert a JSON document."""
    scenario_context = get_current_scenario_context(context)
    index_name = scenario_context.get("last_index_name")
    handle = scenario_context.adapter.search_index(index_name)
    handle.upsert_json(doc_id, json.loads(payload))


@when(
    r'I search index "(?P<index_name>[^"]+)" for nearest vector "(?P<vector>[^"]+)" with k (?P<k>\d+)',
)
def step_when_knn_search(context, index_name, vector, k):
    """Run a KNN search against a search index."""
    handle = get_current_scenario_context(context).adapter.search_index(index_name)
    result = handle.search(
        SearchQueryDTO.from_knn(_parse_search_vector(vector), k=int(k), return_fields=["title"]),
    )
    store_result(context, "search_result", result)


@when(
    r'I search index "(?P<index_name>[^"]+)" asynchronously for nearest vector "(?P<vector>[^"]+)" with k (?P<k>\d+)',
)
async def step_when_knn_search_async(context, index_name, vector, k):
    """Run a KNN search asynchronously."""
    handle = get_current_scenario_context(context).async_adapter.search_index(index_name)
    result = await handle.search(
        SearchQueryDTO.from_knn(_parse_search_vector(vector), k=int(k), return_fields=["title"]),
    )
    store_result(context, "async_search_result", result)


@when(
    r'I hybrid search index "(?P<index_name>[^"]+)" for text "(?P<text_query>[^"]+)" '
    r'and vector "(?P<vector>[^"]+)" with k (?P<k>\d+)',
)
def step_when_hybrid_search(context, index_name, text_query, vector, k):
    """Run a hybrid text and vector search."""
    handle = get_current_scenario_context(context).adapter.search_index(index_name)
    result = handle.search(
        SearchQueryDTO.from_hybrid(
            text_query,
            _parse_search_vector(vector),
            k=int(k),
            return_fields=["title"],
        ),
    )
    store_result(context, "search_result", result)


@when(r'I aggregate search index "(?P<index_name>[^"]+)" grouped by category')
def step_when_aggregate(context, index_name):
    """Run a simple aggregation grouped by category."""
    handle = get_current_scenario_context(context).adapter.search_index(index_name)
    result = handle.aggregate(
        AggregationDTO(
            query="*",
            group_by=["@category"],
            reduce_function="COUNT",
            reduce_field="total",
        ),
    )
    store_result(context, "aggregation_result", result)


@when(r'I drop search index "(?P<index_name>[^"]+)"')
def step_when_drop_search_index(context, index_name):
    """Drop a search index."""
    get_current_scenario_context(context).adapter.search_index(index_name).drop_index(delete_documents=True)


@when(
    r'I add field "(?P<field_name>[^"]+)" as numeric to search index "(?P<index_name>[^"]+)" '
    r'for (?P<index_type>HASH|JSON) documents',
)
def step_when_add_numeric_field_to_search_index(context, field_name, index_name, index_type):
    """Add a numeric field to an existing search index schema."""
    handle = get_current_scenario_context(context).adapter.search_index(index_name)
    handle.alter_schema_add(
        NumericFieldConfig(name=field_name),
        index_type=_parse_index_type(index_type),
    )


@when(r'I add alias "(?P<alias>[^"]+)" to search index "(?P<index_name>[^"]+)"')
def step_when_add_search_alias(context, alias, index_name):
    """Add an alias for a search index."""
    result = get_current_scenario_context(context).adapter.search_index(index_name).add_alias(alias)
    store_result(context, "alias_operation_result", result)


@when(r'I delete alias "(?P<alias>[^"]+)" from search index "(?P<index_name>[^"]+)"')
def step_when_delete_search_alias(context, alias, index_name):
    """Delete a search index alias."""
    result = get_current_scenario_context(context).adapter.search_index(index_name).delete_alias(alias)
    store_result(context, "alias_operation_result", result)


@when(r'I delete document "(?P<doc_id>[^"]+)" from search index "(?P<index_name>[^"]+)"')
def step_when_delete_search_document(context, doc_id, index_name):
    """Delete a document from a search index."""
    get_current_scenario_context(context).adapter.search_index(index_name).delete_document(doc_id)


@when(
    r'I upsert search document "(?P<doc_id>[^"]+)" via DTO with title "(?P<title>[^"]+)" '
    r'and vector "(?P<vector>[^"]+)" for (?P<index_type>HASH|JSON) documents',
)
def step_when_upsert_search_document_via_dto(context, doc_id, title, vector, index_type):
    """Upsert a HASH or JSON search document using DTO helpers."""
    scenario_context = get_current_scenario_context(context)
    index_name = scenario_context.get("last_index_name")
    handle = scenario_context.adapter.search_index(index_name)
    parsed_vector = _parse_search_vector(vector)
    if _parse_index_type(index_type) == RedisIndexType.HASH:
        handle.upsert_hash_dto(
            HashDocumentUpsertDTO(
                doc_id=doc_id,
                fields={"title": title},
                vector_field="embedding",
                vector=parsed_vector,
            ),
        )
        return
    handle.upsert_json_dto(
        JsonDocumentUpsertDTO(
            doc_id=doc_id,
            payload={"title": title, "embedding": parsed_vector},
        ),
    )


@then(r'search index "(?P<index_name>[^"]+)" should exist')
def step_then_search_index_exists(context, index_name):
    """Assert that a search index exists."""
    adapter = get_current_scenario_context(context).adapter
    assert index_name in adapter.list_search_indexes()


@then(r'search index "(?P<index_name>[^"]+)" should not exist')
def step_then_search_index_not_exists(context, index_name):
    """Assert that a search index does not exist."""
    adapter = get_current_scenario_context(context).adapter
    assert index_name not in adapter.list_search_indexes()


@then(r'document "(?P<doc_id>[^"]+)" should exist in search index "(?P<index_name>[^"]+)"')
def step_then_document_exists(context, doc_id, index_name):
    """Assert that a document can be loaded from the index."""
    document = _get_search_document(context, doc_id, index_name)
    assert document["id"] == doc_id


@then(
    r'document "(?P<doc_id>[^"]+)" in search index "(?P<index_name>[^"]+)" should have title "(?P<title>[^"]+)"',
)
def step_then_document_has_title(context, doc_id, index_name, title):
    """Assert that a loaded search document contains the expected title."""
    document = _get_search_document(context, doc_id, index_name)
    assert document.get("title") == title


@then(r'document "(?P<doc_id>[^"]+)" should not exist in search index "(?P<index_name>[^"]+)"')
def step_then_document_not_exists(context, doc_id, index_name):
    """Assert that a document was removed from the search index."""
    document = _get_search_document(context, doc_id, index_name)
    assert document.get("title") is None


@then(r'search index "(?P<index_name>[^"]+)" should have field "(?P<field_name>[^"]+)"')
def step_then_search_index_has_field(context, index_name, field_name):
    """Assert that a search index schema includes the given field."""
    info = get_current_scenario_context(context).adapter.search_index(index_name).info()
    field_names = _search_index_field_names(info)
    assert field_name in field_names, f"Expected field '{field_name}' in {field_names!r}"


@then(r"the alias operation should succeed")
def step_then_alias_operation_succeeds(context):
    """Assert the last alias-related operation returned success."""
    result = get_result(context, "alias_operation_result")
    assert result is True


@then(r"the search should return at least (?P<count>\d+) hits?")
def step_then_search_hits(context, count):
    """Assert synchronous search hit count."""
    result = get_result(context, "search_result")
    assert result is not None
    assert len(result.hits) >= int(count)


@then(r"the async search should return at least (?P<count>\d+) hits?")
def step_then_async_search_hits(context, count):
    """Assert asynchronous search hit count."""
    result = get_result(context, "async_search_result")
    assert result is not None
    assert len(result.hits) >= int(count)


@then(r'the top hit id should be "(?P<doc_id>[^"]+)"')
def step_then_top_hit_id(context, doc_id):
    """Assert the first search hit document ID."""
    result = get_result(context, "search_result")
    assert result is not None
    assert result.hits[0].doc_id == doc_id


@then(r"the aggregation should return at least (?P<count>\d+) rows?")
def step_then_aggregation_rows(context, count):
    """Assert aggregation row count."""
    result = get_result(context, "aggregation_result")
    assert result is not None
    assert len(result["rows"]) >= int(count)
