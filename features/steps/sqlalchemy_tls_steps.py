"""Steps for the TLS options of the PostgreSQL and MySQL SQLAlchemy session managers."""

import asyncio

from behave import then, when
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from archipy.adapters.mysql.sqlalchemy.session_managers import (
    AsyncMySQLSQlAlchemySessionManager,
    MySQLSQlAlchemySessionManager,
)
from archipy.adapters.postgres.sqlalchemy.session_managers import (
    AsyncPostgresSQlAlchemySessionManager,
    PostgresSQlAlchemySessionManager,
)
from archipy.configs.base_config import BaseConfig
from features.test_helpers import get_current_scenario_context

_MANAGERS = {
    ("postgres", "sync"): PostgresSQlAlchemySessionManager,
    ("postgres", "async"): AsyncPostgresSQlAlchemySessionManager,
    ("mysql", "sync"): MySQLSQlAlchemySessionManager,
    ("mysql", "async"): AsyncMySQLSQlAlchemySessionManager,
}
_SSL_FIELD = {"postgres": "SSL_MODE", "mysql": "SSL_MODE"}
_ENCRYPTION_QUERY = {
    "postgres": "SELECT CASE WHEN ssl THEN 'encrypted' ELSE 'unencrypted' END "
    "FROM pg_stat_ssl WHERE pid = pg_backend_pid()",
    "mysql": "SELECT IF(VARIABLE_VALUE = '', 'unencrypted', 'encrypted') "
    "FROM performance_schema.session_status WHERE VARIABLE_NAME = 'Ssl_cipher'",
}


def _probe(db_type: str, kind: str, tls_mode: str) -> str:
    """Connect with the given TLS mode and report whether the session is encrypted, or 'rejected'."""
    global_config = BaseConfig.global_config()
    section = global_config.POSTGRES_SQLALCHEMY if db_type == "postgres" else global_config.MYSQL_SQLALCHEMY
    configs = section.model_copy(update={_SSL_FIELD[db_type]: None if tls_mode == "none" else tls_mode})
    manager = object.__new__(_MANAGERS[db_type, kind])  # skip __init__: it would build a pooled engine
    manager._configs = configs
    url = manager._create_url(configs)
    connect_args = manager._get_connect_args()
    query = text(_ENCRYPTION_QUERY[db_type])
    try:
        if kind == "sync":
            engine = create_engine(url, connect_args=connect_args)
            try:
                with engine.connect() as connection:
                    return str(connection.execute(query).scalar_one())
            finally:
                engine.dispose()

        async def run() -> str:
            engine = create_async_engine(url, connect_args=connect_args)
            try:
                async with engine.connect() as connection:
                    return str((await connection.execute(query)).scalar_one())
            finally:
                await engine.dispose()

        return asyncio.run(run())
    except Exception:
        return "rejected"


@when("I connect to {db_type} through the {kind} driver with TLS mode {tls_mode}")
def step_when_connect_with_tls_mode(context, db_type, kind, tls_mode):
    get_current_scenario_context(context).store("tls_outcome", _probe(db_type, kind, tls_mode))


@then("the connection should be {outcome}")
def step_then_connection_outcome(context, outcome):
    actual = get_current_scenario_context(context).get("tls_outcome")
    assert actual == outcome, f"Expected {outcome}, got {actual}"
