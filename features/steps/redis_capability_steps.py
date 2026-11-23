"""Behavior of the Redis adapters' newer Redis command and connection capabilities."""

import asyncio
import inspect
import socket
import struct
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from time import monotonic
from uuid import uuid4

from behave import then, use_step_matcher, when
from pydantic import ValidationError
from redis import Redis
from redis.cache import CacheConfig, TrackingMode
from redis.commands.metadata import (
    AsyncDynamicMetadataResolver,
    AsyncStaticMetadataResolver,
    DynamicMetadataResolver,
    StaticMetadataResolver,
)
from redis.commands.search.hybrid_query import HybridQuery, HybridSearchQuery, HybridVsimQuery, VectorSearchMethods
from redis.exceptions import ConnectionError as RedisConnectionError
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
    VectorFieldConfig,
)
from archipy.models.errors import CacheError
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

    async def run():
        adapter = scenario.async_adapter or scenario.adapter
        try:
            return await exercise(adapter, uuid4().hex)
        finally:
            if scenario.async_adapter is not None:
                await scenario.async_adapter.close()
                scenario.async_adapter = None

    scenario.store("redis_capability", asyncio.run(run()))


def _result(context):
    return get_current_scenario_context(context).get("redis_capability")


@when("I exercise the Redis set member expiration commands")
def exercise_member_expiration(context):
    async def exercise(adapter, key):
        expiration = int((datetime.now(UTC) + timedelta(minutes=5)).timestamp())
        added = await _call(adapter.saddex, key, "first", "second", ex=60)
        seconds = await _call(adapter.sexpire, key, 70, "first", "missing")
        milliseconds = await _call(adapter.spexpire, key, 80_000, "second", gt=True)
        ttl_first, ttl_second, ttl_missing = await _call(adapter.sttl, key, "first", "second", "missing")
        (pttl_second,) = await _call(adapter.spttl, key, "second")
        expireat = await _call(adapter.sexpireat, key, expiration, "first", xx=True)
        pexpireat = await _call(adapter.spexpireat, key, expiration * 1000 + 37, "second", xx=True)
        deadlines = await _call(adapter.sexpiretime, key, "first", "second")
        millisecond_deadlines = await _call(adapter.spexpiretime, key, "first", "second")
        persisted = await _call(adapter.spersist, key, "first", "second", "missing")
        remaining = await _call(adapter.sttl, key, "first", "second", "missing")
        return (
            added,
            seconds,
            milliseconds,
            0 < ttl_first <= 70,
            0 < ttl_second <= 80,
            ttl_missing,
            0 < pttl_second <= 80_000,
            expireat,
            pexpireat,
            deadlines == [expiration, expiration + 1],
            millisecond_deadlines == [expiration * 1000, expiration * 1000 + 37],
            persisted,
            remaining,
        )

    _run(context, exercise)


@then("Redis reports each member's expiration and preserves the persistent members")
def verify_member_expiration(context):
    result = _result(context)
    assert result == (1, [1, -2], [1], True, True, -2, True, [1], [1], True, True, [1, 1, -2], [-1, -1, -2]), result


@when("I move sorted set members by rank, score and name")
def exercise_sorted_set_moves(context):
    async def exercise(adapter, token):
        source, destination = f"{{{token}}}:source", f"{{{token}}}:destination"
        await _call(adapter.zadd, source, {"a": 1, "b": 2, "c": 3, "d": 4})
        first = await _call(adapter.zmove, source, destination, lowest=True)
        second = await _call(adapter.zmove, source, destination, byscore=(2, 2))
        third = await _call(adapter.bzmove, source, destination, 0.2, highest=True)
        fourth = await _call(adapter.zmovemember, source, destination, "c", nx=True)
        empty = await _call(adapter.zmove, source, destination, lowest=True)
        return first, second, third, fourth, empty, await _call(adapter.zcard, destination)

    _run(context, exercise)


@then("all members arrive in the destination with their original scores")
def verify_sorted_set_moves(context):
    result = _result(context)
    assert result == ([["a", 1.0]], [["b", 2.0]], [["d", 4.0]], [["c", 3.0]], None, 4), result


@when("I inspect bit positions, eviction flags, client records and sketch counter widths")
def inspect_data_and_clients(context):
    async def exercise(adapter, token):
        key = f"{token}:key"
        await _call(adapter.set, key, "A")
        ones = await _call(adapter.bitrangeintarray, key, 0, 7, mode="BIT")
        zeros = await _call(adapter.bitrangeintarray, key, 0, 7, mode="BIT", limit=2, zeros=True)
        blessed = await _call(adapter.bless_set, key, "NO-EVICT")
        flags = await _call(adapter.bless_get, key)
        cursor, keys = await _call(adapter.bless_scan, 0, "NO-EVICT")
        seen = key in keys
        while cursor and not seen:
            cursor, keys = await _call(adapter.bless_scan, cursor, "NO-EVICT")
            seen = key in keys
        cleared = await _call(adapter.bless_clear, key, "NO-EVICT")
        client_id = await _call(adapter.client.client_id)
        clients = list(await _call(adapter.client_list_iter, client_ids=[client_id]))
        dim_key, prob_key = f"{token}:dim", f"{token}:prob"
        assert await _call(adapter.cms_initbydim, dim_key, 12, 5, cell_size=1)
        assert await _call(adapter.cms_initbyprob, prob_key, 0.01, 0.05, cell_size=2)
        dim = await _call(adapter.client.cms().incrby, dim_key, ["item"], [255])
        prob = await _call(adapter.client.cms().incrby, prob_key, ["item"], [256])
        await _call(adapter.client.cms().incrby, dim_key, ["item"], [1])
        assert await _call(adapter.client.cms().query, dim_key, "item") == [255]
        return (
            ones,
            zeros,
            blessed,
            flags,
            seen,
            cleared,
            [client["id"] for client in clients],
            str(client_id),
            dim,
            prob,
        )

    _run(context, exercise)


@then("Redis returns the expected positions, flags, client and counter widths")
def verify_data_and_clients(context):
    result = _result(context)
    assert result[:6] == ([1, 7], [0, 2], 1, ["NO-EVICT"], True, 1), result
    assert result[6] == [result[7]], result
    assert result[8:] == ([255], [256]), result


@when("I run a hybrid Redis search with score explanations")
def explain_hybrid_search(context):
    async def exercise(adapter, token):
        vector = struct.pack("<2f", 1, 0)
        handle = adapter.search_index(token)
        schema = IndexSchemaDTO(fields=[TextFieldConfig(name="title"), VectorFieldConfig(name="vector", dim=2)])
        prefix = f"{token}:"
        assert await _call(handle.create_index, schema, prefix)
        try:
            assert await _call(handle.upsert_hash, prefix + "doc", {"title": "Redis database", "vector": vector})
            deadline = monotonic() + 3
            while True:
                index_info = await _call(handle.info)
                if int(index_info["num_docs"]) == 1 and not int(index_info["indexing"]):
                    break
                assert monotonic() < deadline, index_info
            query = HybridQuery(
                HybridSearchQuery("redis"),
                HybridVsimQuery("@vector", "$vector", VectorSearchMethods.KNN, {"K": 1}),
            )
            return await _call(handle.hybrid_search, query, params_substitution={"vector": vector}, explain_score=True)
        finally:
            await _call(handle.drop_index, delete_documents=True)

    _run(context, exercise)


@then("the hybrid hit includes a numeric score and its explanation")
def verify_hybrid_search(context):
    result = _result(context)
    assert result.total_results == 1, result
    score, explanation = result.results[0]["score"]
    assert isinstance(score, float) and explanation, result


@when("I cache selected Redis reads with both tracking modes")
def exercise_client_cache(context):
    async def exercise(adapter, token):
        config = adapter._configs
        cache_key, other_key = f"{token}:cached", f"{token}:uncached"
        readings = []
        with Redis(host=config.MASTER_HOST, port=config.PORT, decode_responses=True) as writer:
            for mode in (TrackingMode.OPTIN, TrackingMode.OPTOUT):

                def predicate(command, keys):
                    return command == "GET" and keys == (cache_key,)

                with RedisAdapter(
                    config, cache_config=CacheConfig(tracking_mode=mode, cache_predicate=predicate),
                ) as cached:
                    writer.mset({cache_key: "first", other_key: "other"})
                    before = writer.info("commandstats").get("cmdstat_get", {}).get("calls", 0)
                    assert [cached.get(cache_key) for _ in range(2)] == ["first", "first"]
                    assert [cached.get(other_key) for _ in range(2)] == ["other", "other"]
                    calls = writer.info("commandstats")["cmdstat_get"]["calls"] - before
                    writer.set(cache_key, "second")
                    readings.append((calls, cached.get(cache_key)))

        return readings

    _run(context, exercise)


@then("tracking invalidates cached values and ineligible reads still reach Redis")
def verify_client_cache(context):
    assert _result(context) == [(3, "second"), (3, "second")], _result(context)


@when("I read and delete keys spanning two Redis shards")
def exercise_cluster_routing(context):
    async def exercise(adapter, token):
        first = f"{token}:0"
        await _call(adapter.ping)
        first_node = adapter.client.get_node_from_key(first)
        second = next(
            key for i in range(1, 50) if adapter.client.get_node_from_key(key := f"{token}:{i}") != first_node
        )
        await _call(adapter.set, first, "first")
        await _call(adapter.set, second, "second")
        pipeline = await _call(adapter.get_pipeline, transaction=False)
        pipeline.touch(first)
        pipeline.touch(second)
        touched = await _call(pipeline.execute)
        removed = await _call(adapter.delete, first, second, f"{token}:missing")
        return touched, removed, await _call(adapter.exists, first, second)

    _run(context, exercise)


@then("both shards contribute to the Redis command replies")
def verify_cluster_routing(context):
    assert _result(context) == ([1, 1], 2, 0), _result(context)


@when("I connect with RESP negotiation and check a missing Redis Unix socket")
def exercise_connection_resilience(context):
    image = BaseConfig.global_config().REDIS__IMAGE
    container = (
        DockerContainer(image)
        .with_exposed_ports(6379)
        .with_command(["redis-server", "--save", "", "--rename-command", "HELLO", ""])
        .waiting_for(LogMessageWaitStrategy("Ready to accept connections tcp"))
    )
    scenario = get_current_scenario_context(context)
    missing = RedisConfig(
        UNIX_SOCKET_PATH=f"/tmp/redis-{uuid4().hex}.sock",
        RETRY={"ATTEMPTS": 4, "BACKOFF_BASE": 1.0, "BACKOFF_CAP": 1.0, "FAIL_FAST_MISSING_SOCKET": True},
    )
    with container:
        negotiated = RedisConfig(
            MASTER_HOST=container.get_container_host_ip(),
            PORT=int(container.get_exposed_port(6379)),
            PROTOCOL=None,
        )

        async def check(adapter, unreachable):
            assert await _call(adapter.set, "fallback", "resp2")
            assert await _call(adapter.get, "fallback") == "resp2"
            start = monotonic()
            try:
                await _call(unreachable.ping)
            except (RedisConnectionError, CacheError) as error:
                return "No such file" in str(error) and monotonic() - start < 1
            raise AssertionError("Missing Unix socket unexpectedly answered")

        async def check_async():
            async with AsyncRedisAdapter(negotiated) as adapter, AsyncRedisAdapter(missing) as unreachable:
                return await check(adapter, unreachable)

        with RedisAdapter(negotiated) as adapter, RedisAdapter(missing) as unreachable:
            sync_result = asyncio.run(check(adapter, unreachable))
        scenario.store("redis_capability", (sync_result, asyncio.run(check_async())))


@then("both Redis adapters fall back to RESP2 and reject the missing socket without backoff")
def verify_connection_resilience(context):
    assert _result(context) == (True, True), _result(context)


@when("I start, seal, abort and clean up Redis backups")
def exercise_backup(context):
    async def exercise(adapter, token):
        await _call(adapter.set, token, "backed up")
        assert await _call(adapter.backup_start) == "OK"
        deadline = monotonic() + 3
        while (await _call(adapter.backup_status))["state"] in {"pending", "snapshotting"}:
            assert monotonic() < deadline, "Redis did not finish the backup snapshot"
        assert await _call(adapter.backup_seal) == "OK"
        status = await _call(adapter.backup_status)
        artifacts = await _call(adapter.backup_list)
        assert await _call(adapter.backup_cleanup) == "OK"
        assert await _call(adapter.backup_start) == "OK"
        assert await _call(adapter.backup_abort) == "OK"
        aborted = await _call(adapter.backup_status)
        assert await _call(adapter.backup_cleanup) == "OK"
        return status["state"], bool(artifacts), aborted["state"], aborted["error"]

    _run(context, exercise)


@then("Redis reports one sealed backup followed by an aborted backup")
def verify_backup(context):
    assert _result(context) == ("sealed", True, "failed", "aborted by user"), _result(context)


@when("I use custom command metadata and refresh pacing on Redis Cluster")
def exercise_cluster_metadata(context):
    async def exercise(adapter, key):
        config = adapter._configs
        config = config.model_copy(
            update={
                "CLUSTER": config.CLUSTER.model_copy(
                    update={"TOPOLOGY_REFRESH_MIN_INTERVAL": 0.25, "READ_FROM_REPLICAS": True},
                ),
            },
        )
        fallback = StaticMetadataResolver()
        get_metadata = fallback.resolve("GET")
        assert get_metadata is not None
        metadata = {"core": {"get": replace(get_metadata, is_readonly=False)}}

        async def check(configured):
            await _call(configured.set, key, "primary")
            replica = configured.client.get_node_from_key(key, replica=True)
            assert replica is not None
            with Redis(host=replica.host, port=replica.port) as reader:
                before = reader.info("commandstats").get("cmdstat_get", {}).get("calls", 0)
                values = [await _call(configured.get, key) for _ in range(4)]
                after = reader.info("commandstats").get("cmdstat_get", {}).get("calls", 0)
            return values, after - before, configured.client.nodes_manager._topology_refresh_min_interval

        if isinstance(adapter, AsyncRedisAdapter):
            async with AsyncRedisAdapter(
                config, metadata_resolver=AsyncDynamicMetadataResolver(metadata, AsyncStaticMetadataResolver()),
            ) as configured:
                return await check(configured)
        with RedisAdapter(config, metadata_resolver=DynamicMetadataResolver(metadata, fallback)) as configured:
            return await check(configured)

    _run(context, exercise)


@then("the custom metadata keeps reads on the primary and the client uses the configured refresh interval")
def verify_cluster_metadata(context):
    assert _result(context) == (["primary"] * 4, 0, 0.25), _result(context)


@when("I subscribe and publish on a Redis shard channel")
def exercise_sharded_pubsub(context):
    async def exercise(adapter, channel):
        subscriber = await _call(adapter.pubsub)
        try:
            await _call(subscriber.ssubscribe, channel)
            confirmation = await _call(subscriber.get_sharded_message, timeout=2)
            assert confirmation is not None and confirmation["type"] == "ssubscribe", confirmation
            receivers = await _call(adapter.spublish, channel, "message")
            message = await _call(subscriber.get_sharded_message, timeout=2)
            return receivers, message
        finally:
            await _call(subscriber.close)

    _run(context, exercise)


@then("the shard subscriber receives the message")
def verify_sharded_pubsub(context):
    receivers, message = _result(context)
    assert receivers == 1 and message is not None, (receivers, message)
    assert message["type"] == "smessage" and message["data"] == "message", message


@when("Redis closes the connection held by the async adapter")
def exercise_server_disconnect(context):
    async def exercise(adapter, key):
        await adapter.set(key, "still present")
        original_id = await adapter.client.client_id()
        config = adapter._configs
        with Redis(host=config.MASTER_HOST, port=config.PORT) as observer:
            assert observer.client_kill_filter(_id=original_id) == 1
        value = await adapter.get(key)
        return value, original_id != await adapter.client.client_id()

    _run(context, exercise)


@then("the adapter reconnects and reads the stored value")
def verify_server_disconnect(context):
    assert _result(context) == ("still present", True), _result(context)


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
    result = _result(context)
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
    result = _result(context)
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
    found, result = _result(context)
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
        get_current_scenario_context(context).store("redis_capability", error.errors()[0]["loc"])


@then("the search aggregation is rejected")
def verify_unsupported_reducer(context):
    assert _result(context) == ("reduce_function",)


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
            adapter.set("redis_capability:sentinel", "present")
            assert adapter.get("redis_capability:sentinel") == "present"
            sync_during = len(observer.client_list())
        sync_after = len(observer.client_list())

        async def check_async_sentinel():
            async with AsyncRedisAdapter(config) as adapter:
                assert await adapter.get("redis_capability:sentinel") == "present"
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
            key = f"redis_capability:migration:{uuid4().hex}"
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
        get_current_scenario_context(context).store("redis_capability", value)


@then("the adapter learns the new owner and can read the migrated key")
def verify_migrated_key(context):
    assert _result(context) == "migrated"
