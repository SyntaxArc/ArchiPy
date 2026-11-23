"""Behavior of the redis-py 8.1 command surfaces exposed by ArchiPy."""

import asyncio
import inspect
import socket
from time import monotonic
from uuid import uuid4

from behave import then, use_step_matcher, when
from pydantic import ValidationError
from redis import Redis
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import LogMessageWaitStrategy

from archipy.adapters.redis.adapters import AsyncRedisAdapter, RedisAdapter
from archipy.configs.base_config import BaseConfig
from archipy.configs.sections.redis import RedisConfig, RedisMode
from archipy.models.dtos.redis.search.aggregation_dto import AggregationDTO
from archipy.models.dtos.redis.search.index_schema_dto import (
    IndexSchemaDTO,
    NumericFieldConfig,
    TagFieldConfig,
    TextFieldConfig,
)
from features.test_containers import ContainerManager
from features.test_helpers import get_current_scenario_context

use_step_matcher("re")


async def _call(method, *args, **kwargs):
    result = method(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


def _run(context, exercise):
    scenario = get_current_scenario_context(context)
    adapter = scenario.async_adapter or scenario.adapter

    async def run():
        try:
            return await exercise(adapter, uuid4().hex)
        finally:
            if scenario.async_adapter is not None:
                await scenario.async_adapter.close()
                scenario.async_adapter = None

    scenario.store("redis81", asyncio.run(run()))


@when("I move a list batch and count overlapping sets through the Redis adapter")
def move_batch_and_count_sets(context):
    async def exercise(adapter, token):
        source, destination = f"{{{token}}}:source", f"{{{token}}}:destination"
        await _call(adapter.rpush, source, "one", "two", "three")
        moved = await _call(adapter.lmovem, source, destination, count=2, ordering="BULK")
        blocked_move = await _call(adapter.blmovem, source, destination, timeout_seconds=0.2)
        missing = await _call(adapter.blmovem, source, destination, timeout_seconds=0.01)
        a, b = f"{{{token}}}:a", f"{{{token}}}:b"
        await _call(adapter.sadd, a, "first", "shared")
        await _call(adapter.sadd, b, "shared", "last")
        diff = await _call(adapter.sdiffcard, [a, b])
        union = await _call(adapter.sunioncard, [a, b])
        limited_union = await _call(adapter.sunioncard, [a, b], limit=2)
        return moved, blocked_move, missing, diff, union, limited_union

    _run(context, exercise)


@then("the batch move and set counts match the stored values")
def verify_batch_and_sets(context):
    result = get_current_scenario_context(context).get("redis81")
    assert result == (["one", "two"], ["three"], None, 1, 3, 2), result


def _stream_ids(reply):
    streams = (
        (entries[0] for entries in reply.values()) if isinstance(reply, dict) else (entries for _, entries in reply)
    )
    return [entry_id for entries in streams for entry_id, _ in entries]


@when("I read a stream and a consumer group with total count and size limits")
def read_limited_streams(context):
    async def exercise(adapter, token):
        a, b = f"{{{token}}}:a", f"{{{token}}}:b"
        for key, entry_id in ((a, "1-0"), (b, "2-0")):
            await _call(adapter.client.xadd, key, {"value": "sample"}, id=entry_id)
            await _call(adapter.client.xgroup_create, key, "count", id="0")
            await _call(adapter.client.xgroup_create, key, "size", id="0")
        positions = {a: "0", b: "0"}
        group_positions = {a: ">", b: ">"}
        replies = [
            await _call(adapter.xread, positions, max_count=1),
            await _call(adapter.xread, positions, max_size=1),
            await _call(adapter.xreadgroup, "count", "reader", group_positions, max_count=1),
            await _call(adapter.xreadgroup, "size", "reader", group_positions, max_size=1),
        ]
        return [_stream_ids(reply) for reply in replies]

    _run(context, exercise)


@then("each stream limit returns the first entry only")
def verify_stream_limits(context):
    result = get_current_scenario_context(context).get("redis81")
    assert result == [["1-0"]] * 4, result


@when("I alias a search index and collect the top values for one group")
def alias_and_collect(context):
    async def exercise(adapter, token):
        prefix = f"{{{token}}}:doc:"
        handle = adapter.search_index(token)
        schema = IndexSchemaDTO(
            fields=[
                TagFieldConfig(name="kind"),
                TextFieldConfig(name="value"),
                NumericFieldConfig(name="rank"),
            ],
        )
        values = ("article", "audiobook", "video")
        for rank, value in enumerate(values):
            assert await _call(handle.upsert_hash, prefix + str(rank), {"kind": "book", "value": value, "rank": rank})
        assert await _call(handle.create_index, schema, prefix)
        try:
            deadline = monotonic() + 3
            while True:
                index_info = await _call(handle.info)
                if int(index_info["num_docs"]) == len(values) and not int(index_info["indexing"]):
                    break
                assert monotonic() < deadline, index_info
            alias = f"alias-{token}"
            assert await _call(handle.add_alias, alias)
            aliases = await _call(handle.list_aliases)
            result = await _call(
                handle.aggregate,
                AggregationDTO(
                    group_by=["kind"],
                    reduce_field="entries",
                    reduce_function="COLLECT",
                    collect_fields=["value", "rank"],
                    collect_sort_by="rank",
                    collect_sort_direction="DESC",
                    collect_limit=(0, 2),
                ),
            )
            return alias in aliases, result
        finally:
            await _call(handle.drop_index, delete_documents=True)

    _run(context, exercise)


@then("Redis lists the alias and returns the top values")
def verify_alias_and_collection(context):
    found, result = get_current_scenario_context(context).get("redis81")
    assert found
    assert result["total"] == 1, result
    (row,) = result["rows"]
    attributes = row.get(b"extra_attributes", row)
    entries = attributes[b"entries"]
    assert [(entry[b"value"], int(entry[b"rank"])) for entry in entries] == [(b"video", 2), (b"audiobook", 1)], result


@when(r'I build a search aggregation with the unsupported reducer "(?P<reducer>[^"]+)"')
def build_unsupported_reducer(context, reducer):
    try:
        AggregationDTO(group_by=["kind"], reduce_function=reducer)
    except ValidationError as error:
        get_current_scenario_context(context).store("redis81", error.errors()[0]["loc"])


@then("the search aggregation is rejected")
def verify_unsupported_reducer(context):
    assert get_current_scenario_context(context).get("redis81") == ("reduce_function",)


@when("I use and close sync and async adapters through a real Redis Sentinel")
def use_and_close_sentinel(context):
    # Reserve two distinct TCP ports before starting Redis and Sentinel on the host network.
    with socket.socket() as primary, socket.socket() as monitor:
        primary.bind(("127.0.0.1", 0))
        monitor.bind(("127.0.0.1", 0))
        primary_port = primary.getsockname()[1]
        sentinel_port = monitor.getsockname()[1]
    command = [
        "sh",
        "-ec",
        f"redis-server --bind 127.0.0.1 --port {primary_port} --daemonize yes\n"
        f"printf '%s\\n' 'bind 127.0.0.1' 'port {sentinel_port}' "
        f"'sentinel monitor archipy 127.0.0.1 {primary_port} 1' > /tmp/archipy-sentinel.conf\n"
        "exec redis-server /tmp/archipy-sentinel.conf --sentinel",
    ]
    config = RedisConfig(
        MODE=RedisMode.SENTINEL,
        SENTINEL={"NODES": [f"127.0.0.1:{sentinel_port}"], "SERVICE_NAME": "archipy", "SOCKET_TIMEOUT": 2},
    )
    image = BaseConfig.global_config().REDIS__IMAGE
    container = (
        DockerContainer(image)
        .with_kwargs(network_mode="host")
        .with_command(command)
        .waiting_for(LogMessageWaitStrategy("\\+monitor master archipy"))
    )
    with container, Redis(host="127.0.0.1", port=sentinel_port, socket_timeout=2) as observer:
        initial = len(observer.client_list())
        with RedisAdapter(config) as adapter:
            adapter.set("redis81:sentinel", "present")
            assert adapter.get("redis81:sentinel") == "present"
            sync_during = len(observer.client_list())
        sync_after = len(observer.client_list())

        async def check_async_sentinel():
            async with AsyncRedisAdapter(config) as adapter:
                assert await adapter.get("redis81:sentinel") == "present"
                return len(observer.client_list())

        async_during = asyncio.run(check_async_sentinel())
        async_after = len(observer.client_list())
    get_current_scenario_context(context).store(
        "sentinel_clients", (initial, sync_during, sync_after, async_during, async_after),
    )


@then("the Sentinel discovery connections are released")
def check_sentinel_clients(context):
    counts = get_current_scenario_context(context).get("sentinel_clients")
    initial, sync_during, sync_after, async_during, async_after = counts
    assert sync_during > initial and async_during > initial, counts
    assert sync_after == async_after == initial, counts


async def _migrate_and_wait_for_notification(client, key, slot, source, destination):
    # PING targets the pre-existing connection. A key command could refresh slots via MOVED
    # and pass this check even if the client never processed the maintenance notification.
    await client.execute_command("PING", target_nodes=source)
    await client.execute_command("CLUSTER MIGRATION IMPORT", slot, slot, target_nodes=destination)
    async with asyncio.timeout(5):
        while client.get_node_from_key(key) != destination:
            await client.execute_command("PING", target_nodes=source)


@when("I migrate a cluster slot while an async RESP3 adapter is connected")
def migrate_redis_slot(context):
    cluster = ContainerManager.get_container("redis-cluster")

    async def exercise():
        config = cluster.cluster_config.model_copy(deep=True)
        config.CLUSTER.READ_FROM_REPLICAS = False
        async with AsyncRedisAdapter(config) as adapter:
            key = f"redis81:migration:{uuid4().hex}"
            client = adapter.client
            await client.initialize()
            slot = client.keyslot(key)
            source = client.get_node_from_key(key)
            help_text = await client.execute_command("CLIENT HELP", target_nodes=source)
            if not any("MAINT_NOTIFICATIONS" in line for line in help_text):
                return None
            await adapter.set(key, "migrated")
            destination = next(node for node in client.get_primaries() if node != source)
            try:
                await _migrate_and_wait_for_notification(client, key, slot, source, destination)
                value = await adapter.get(key)
            finally:
                owner = client.get_node_from_key(key)
                if owner == destination:
                    await _migrate_and_wait_for_notification(client, key, slot, destination, source)
                await adapter.delete(key)
            return value

    value = asyncio.run(exercise())
    if value is None:
        context.scenario.skip("The Redis fixture does not implement CLIENT MAINT_NOTIFICATIONS")
    else:
        get_current_scenario_context(context).store("redis81", value)


@then("the adapter learns the new owner and can read the migrated key")
def verify_migrated_key(context):
    assert get_current_scenario_context(context).get("redis81") == "migrated"
