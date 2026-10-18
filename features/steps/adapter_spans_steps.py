"""Steps that check the OpenTelemetry spans emitted by instrumented adapters.

Every adapter is driven against its real test container with OpenTelemetry exporting to the real collector
container, and the assertions read the spans back from the collector.
"""

import logging
import tempfile
import uuid
from pathlib import Path

import httpx2
from behave import given, then, when
from features.steps.otel_steps import _setup_collector_otel
from features.test_helpers import get_current_scenario_context
from features.test_helpers_otel import CollectorTelemetry

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.otel_utils import OtelUtils

logger = logging.getLogger(__name__)

SPAN_TIMEOUT_SECONDS = 8.0

# (module, class) of every contrib instrumentor ArchiPy applies; used to start each scenario unbound.
_INSTRUMENTORS = (
    ("opentelemetry.instrumentation.sqlalchemy", "SQLAlchemyInstrumentor"),
    ("opentelemetry.instrumentation.redis", "RedisInstrumentor"),
    ("opentelemetry.instrumentation.cassandra", "CassandraInstrumentor"),
    ("opentelemetry.instrumentation.confluent_kafka", "ConfluentKafkaInstrumentor"),
    ("opentelemetry.instrumentation.botocore", "BotocoreInstrumentor"),
    ("opentelemetry.instrumentation.httpx", "HTTPXClientInstrumentor"),
    ("opentelemetry.instrumentation.httpx", "HTTPX2ClientInstrumentor"),
    ("opentelemetry.instrumentation.requests", "RequestsInstrumentor"),
)


def _unwrap_kafka_consumer_leftovers() -> None:
    """Remove the consumer wrappers the Kafka instrumentor forgets to unwrap.

    ``ConfluentKafkaInstrumentor.uninstrument`` unwraps ``poll`` but not ``consume`` or ``close``. Instrumenting
    again then wraps ``consume`` twice, so one batch creates two consume spans and the first is never ended.
    """
    from opentelemetry.instrumentation.confluent_kafka import AutoInstrumentedConsumer
    from opentelemetry.instrumentation.utils import unwrap

    for method in ("consume", "close"):
        if hasattr(getattr(AutoInstrumentedConsumer, method), "__wrapped__"):
            unwrap(AutoInstrumentedConsumer, method)


def _uninstrument_all() -> None:
    """Remove stale instrumentors left from an earlier scenario.

    An instrumentor stays bound to the tracer provider it was first given, so without this the spans of
    the next scenario would go to a provider that was already shut down.
    """
    import importlib

    for module_name, class_name in _INSTRUMENTORS:
        try:
            instrumentor = getattr(importlib.import_module(module_name), class_name)()
        except (ImportError, AttributeError):
            continue
        if getattr(instrumentor, "is_instrumented_by_opentelemetry", False):
            try:
                instrumentor.uninstrument()
                if class_name == "ConfluentKafkaInstrumentor":
                    _unwrap_kafka_consumer_leftovers()
            except Exception:
                # The SQLAlchemy instrumentor unwraps the engine factories first and then removes the engine
                # listeners one by one; it raises when a listener of an already collected engine is gone. Drop
                # its bookkeeping so the next scenario can bind a fresh instrumentor.
                logger.warning("Forcing a reset of the %s instrumentor", class_name, exc_info=True)
                instrumentor._is_instrumented_by_opentelemetry = False
                if class_name == "SQLAlchemyInstrumentor":
                    from opentelemetry.instrumentation.sqlalchemy.engine import EngineTracer

                    EngineTracer._remove_event_listener_params.clear()


def _telemetry(context) -> CollectorTelemetry:
    return get_current_scenario_context(context).get("adapter_span_telemetry")


def _collector(context):
    return get_current_scenario_context(context).get("test_containers").get_container("otel-collector")


def _attribute_matches(span, key: str, expected: str) -> bool:
    value = span.attributes.get(key)
    return value is not None and expected in str(value)


@given("adapter spans are exported to the collector")
def step_adapter_spans_enabled(context):
    """Start OpenTelemetry against the collector with every instrumentor freshly bound."""
    _uninstrument_all()
    # Leave no instrumentor bound for the scenarios of other features that share this process.
    context.add_cleanup(_uninstrument_all)
    telemetry = _setup_collector_otel(context, traces=True, metrics=False)
    _collector(context).mark()
    get_current_scenario_context(context).store("adapter_span_telemetry", telemetry)
    for key in ("sqlalchemy", "redis", "cassandra", "confluent_kafka", "botocore", "httpx2", "requests"):
        logger.info("instrumented %s: %s", key, key in OtelUtils._instrumented_libraries)


def _wait_for_spans(context, predicate, description: str) -> list:
    telemetry = _telemetry(context)
    telemetry.flush()
    spans = telemetry.wait_for(
        lambda: [span for span in telemetry.spans() if predicate(span)],
        timeout=SPAN_TIMEOUT_SECONDS,
    )
    assert spans, (
        f"No span {description}. Exported spans: "
        f"{[(span.name, dict(span.attributes)) for span in telemetry.spans()][:25]}. "
        f"Instrumented libraries: {sorted(OtelUtils._instrumented_libraries)}"
    )
    get_current_scenario_context(context).store("matched_spans", spans)
    return spans


@then('the collector should have a span with attribute "{key}" containing "{value}"')
def step_collector_span_attribute(context, key, value):
    _wait_for_spans(context, lambda span: _attribute_matches(span, key, value), f"with {key} containing {value!r}")


@then('the collector should have a span named "{name}" with attribute "{key}" containing "{value}"')
def step_collector_span_name_attribute(context, name, key, value):
    _wait_for_spans(
        context,
        lambda span: name in span.name and _attribute_matches(span, key, value),
        f"named {name!r} with {key} containing {value!r}",
    )


@then('the collector should have a span whose name contains "{name}"')
def step_collector_span_name(context, name):
    _wait_for_spans(context, lambda span: name in span.name, f"whose name contains {name!r}")


@then('the collector should have a database span for "{system}" containing statement "{statement}"')
def step_collector_database_span(context, system, statement):
    """Match old (``db.system``) and stable (``db.system.name``) database semantic conventions."""

    def predicate(span) -> bool:
        attributes = span.attributes
        system_name = attributes.get("db.system.name") or attributes.get("db.system")
        text = str(attributes.get("db.statement") or attributes.get("db.query.text") or "")
        return system_name == system and statement.lower() in text.lower()

    _wait_for_spans(context, predicate, f"for database {system!r} with statement containing {statement!r}")


# --- Redis ---


@when("I set and get a key through the Redis adapter")
def step_redis_roundtrip(context):
    from archipy.adapters.redis.adapters import RedisAdapter

    adapter = RedisAdapter()
    key = f"span-{uuid.uuid4().hex[:8]}"
    adapter.set(key, "value")
    assert adapter.get(key) in ("value", b"value")


@when("I set and get a key through the async Redis adapter")
async def step_async_redis_roundtrip(context):
    from archipy.adapters.redis.adapters import AsyncRedisAdapter

    adapter = AsyncRedisAdapter()
    key = f"span-async-{uuid.uuid4().hex[:8]}"
    await adapter.set(key, "value")
    assert await adapter.get(key) in ("value", b"value")


# --- Kafka ---


@when('I produce and consume a message on topic "{topic}" through the Kafka adapters')
def step_kafka_roundtrip(context, topic):
    import time

    from features.steps.kafka_adapter_steps import (
        get_kafka_admin_adapter,
        get_kafka_consumer_adapter,
        get_kafka_producer_adapter,
        wait_for_topic_condition,
    )

    admin = get_kafka_admin_adapter(context)
    admin.create_topic(topic, num_partitions=1, replication_factor=1)
    assert wait_for_topic_condition(admin, lambda name, topics: name in topics, topic)

    producer = get_kafka_producer_adapter(context, topic)
    group = f"span-group-{uuid.uuid4().hex[:6]}"
    consumer = get_kafka_consumer_adapter(context, topic, group)
    consumer.subscribe([topic])
    producer.produce("span-message")
    producer.flush(timeout=5)

    deadline = time.monotonic() + 10
    message = None
    while message is None and time.monotonic() < deadline:
        message = consumer.poll(timeout=1)
    assert message is not None, "Consumer received no message"
    # The consume span must end with the commit, not with a later poll or close.
    consumer.commit(message, asynchronous=False)


# --- MinIO / botocore ---


@when("I upload and download an object through the MinIO adapter")
def step_minio_roundtrip(context):
    from features.steps.minio_adapter_steps import get_minio_adapter

    adapter = get_minio_adapter(context)
    bucket = f"span-{uuid.uuid4().hex[:8]}"
    adapter.make_bucket(bucket)
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "source.txt"
        source.write_text("span payload")
        adapter.put_object(bucket, "span.txt", str(source))
        adapter.get_object(bucket, "span.txt", str(Path(directory) / "download.txt"))


# --- ScyllaDB / cassandra ---


@when("I run a query through the ScyllaDB adapter")
def step_scylladb_query(context):
    from archipy.adapters.scylladb.adapters import ScyllaDBAdapter

    adapter = ScyllaDBAdapter(BaseConfig.global_config().SCYLLADB)
    adapter.execute("SELECT release_version FROM system.local")


@when("I run a query through the async ScyllaDB adapter")
async def step_async_scylladb_query(context):
    from archipy.adapters.scylladb.adapters import AsyncScyllaDBAdapter

    adapter = AsyncScyllaDBAdapter(BaseConfig.global_config().SCYLLADB)
    await adapter.execute("SELECT release_version FROM system.local")


# --- Elasticsearch ---


def _follow_current_tracer_provider(adapter) -> None:
    """Point the Elasticsearch client at the tracer provider ArchiPy currently owns.

    The client resolves its tracer from the global provider once, when ``elasticsearch`` is imported. The
    global provider can only be set once per process, so a provider that ArchiPy re-creates for another
    scenario would otherwise never receive these spans. A service initializes OpenTelemetry once and is not affected.
    """
    adapter.client._otel.tracer = OtelUtils.get_tracer("elasticsearch-api")


@when("I index and search a document through the Elasticsearch adapter")
def step_elasticsearch_roundtrip(context):
    from archipy.adapters.elasticsearch.adapters import ElasticsearchAdapter

    adapter = ElasticsearchAdapter(BaseConfig.global_config().ELASTIC)
    _follow_current_tracer_provider(adapter)
    index = f"span-{uuid.uuid4().hex[:8]}"
    adapter.index(index=index, document={"title": "span probe"}, doc_id="1", refresh=True)
    adapter.search(index=index, query={"query": {"match": {"title": "span"}}})


@when("I index and search a document through the async Elasticsearch adapter")
async def step_async_elasticsearch_roundtrip(context):
    from archipy.adapters.elasticsearch.adapters import AsyncElasticsearchAdapter

    adapter = AsyncElasticsearchAdapter(BaseConfig.global_config().ELASTIC)
    _follow_current_tracer_provider(adapter)
    index = f"span-async-{uuid.uuid4().hex[:8]}"
    await adapter.index(index=index, document={"title": "span probe"}, doc_id="1", refresh=True)
    await adapter.search(index=index, query={"query": {"match": {"title": "span"}}})


# --- SQLAlchemy ---


def _forget_session_managers(*names: str) -> None:
    """Drop singleton session managers so the adapter builds a new engine after instrumentation.

    The session managers are singletons that own the engine. An engine created by an earlier scenario, before
    SQLAlchemy was instrumented, would otherwise be reused and never emit query spans.
    """
    from archipy.helpers.metaclasses.singleton import Singleton

    for cls in list(Singleton._instances):
        if cls.__name__ in names:
            Singleton._instances.pop(cls, None)
    for key in list(Singleton._keyed_instances):
        if key[0].__name__ in names:
            Singleton._keyed_instances.pop(key, None)


def _sqlalchemy_adapter(db_type: str, *, is_async: bool):
    config = BaseConfig.global_config()
    _forget_session_managers(
        "PostgresSQlAlchemySessionManager",
        "AsyncPostgresSQlAlchemySessionManager",
        "MySQLSQlAlchemySessionManager",
        "AsyncMySQLSQlAlchemySessionManager",
        "SQLiteSQLAlchemySessionManager",
        "AsyncSQLiteSQLAlchemySessionManager",
        "StarRocksSQlAlchemySessionManager",
        "AsyncStarRocksSQlAlchemySessionManager",
    )
    if db_type == "postgres":
        from archipy.adapters.postgres.sqlalchemy.adapters import (
            AsyncPostgresSQLAlchemyAdapter,
            PostgresSQLAlchemyAdapter,
        )

        adapter_class = AsyncPostgresSQLAlchemyAdapter if is_async else PostgresSQLAlchemyAdapter
        return adapter_class(orm_config=config.POSTGRES_SQLALCHEMY)
    if db_type == "mysql":
        from archipy.adapters.mysql.sqlalchemy.adapters import AsyncMySQLSQLAlchemyAdapter, MySQLSQLAlchemyAdapter

        adapter_class = AsyncMySQLSQLAlchemyAdapter if is_async else MySQLSQLAlchemyAdapter
        return adapter_class(orm_config=config.MYSQL_SQLALCHEMY)
    if db_type == "starrocks":
        from archipy.adapters.starrocks.sqlalchemy.adapters import (
            AsyncStarrocksSQLAlchemyAdapter,
            StarrocksSQLAlchemyAdapter,
        )

        adapter_class = AsyncStarrocksSQLAlchemyAdapter if is_async else StarrocksSQLAlchemyAdapter
        return adapter_class(orm_config=config.STARROCKS_SQLALCHEMY)
    if db_type == "sqlite":
        from archipy.adapters.sqlite.sqlalchemy.adapters import (
            AsyncSQLiteSQLAlchemyAdapter,
            SQLiteSQLAlchemyAdapter,
        )
        from archipy.configs.config_template import SQLiteSQLAlchemyConfig

        database = str(Path(tempfile.mkdtemp(prefix="span-sqlite-")) / "span.sqlite")
        driver = "sqlite+aiosqlite" if is_async else "sqlite"
        sqlite_config = SQLiteSQLAlchemyConfig(DRIVER_NAME=driver, DATABASE=database)
        adapter_class = AsyncSQLiteSQLAlchemyAdapter if is_async else SQLiteSQLAlchemyAdapter
        return adapter_class(orm_config=sqlite_config)
    raise AssertionError(f"Unsupported database type {db_type!r}")


@when("I run a query through the {db_type} SQLAlchemy adapter")
def step_sqlalchemy_query(context, db_type):
    from sqlalchemy import text

    adapter = _sqlalchemy_adapter(db_type, is_async=False)
    adapter.execute(text("SELECT 1 AS span_probe"))


@when("I run a query through the {db_type} SQLAlchemy adapter asynchronously")
async def step_async_sqlalchemy_query(context, db_type):
    from sqlalchemy import text

    adapter = _sqlalchemy_adapter(db_type, is_async=True)
    await adapter.execute(text("SELECT 1 AS span_probe"))


# --- HTTP clients ---


def _mailpit_info_url(context) -> str:
    mailpit = get_current_scenario_context(context).get("test_containers").get_container("mailpit")
    return f"{mailpit.api_url}/api/v1/info"


@when("I call the Mailpit API with httpx2")
def step_httpx2_call(context):
    response = httpx2.get(_mailpit_info_url(context), timeout=5)
    assert response.status_code == 200, response.text


@when("I call the Vault API with requests")
def step_requests_call(context):
    import requests

    vault = BaseConfig.global_config().VAULT
    response = requests.get(f"{vault.ADDR}/v1/sys/health", timeout=5)
    assert response.status_code in (200, 429, 472, 473), response.text


@then("no span of this thread should be left active")
def step_no_active_span(context):
    """A consume span that outlives the commit would stay the current span and parent unrelated work."""
    from opentelemetry import trace

    assert not trace.get_current_span().get_span_context().is_valid, (
        f"A span is still active in this thread: {trace.get_current_span()}"
    )
