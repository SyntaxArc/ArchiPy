"""Steps for the timeout and connection options of the PostgreSQL, MySQL and SQLite session managers."""

import asyncio
import json

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
from archipy.adapters.sqlite.sqlalchemy.session_managers import (
    AsyncSQLiteSQLAlchemySessionManager,
    SQLiteSQLAlchemySessionManager,
)
from archipy.configs.base_config import BaseConfig
from features.test_helpers import get_current_scenario_context

_MANAGERS = {
    ("postgres", "sync"): PostgresSQlAlchemySessionManager,
    ("postgres", "async"): AsyncPostgresSQlAlchemySessionManager,
    ("mysql", "sync"): MySQLSQlAlchemySessionManager,
    ("mysql", "async"): AsyncMySQLSQlAlchemySessionManager,
    ("sqlite", "sync"): SQLiteSQLAlchemySessionManager,
    ("sqlite", "async"): AsyncSQLiteSQLAlchemySessionManager,
}
_SECTIONS = {"postgres": "POSTGRES_SQLALCHEMY", "mysql": "MYSQL_SQLALCHEMY", "sqlite": "SQLITE_SQLALCHEMY"}
_SETTING_QUERIES = {
    "statement_timeout": "SHOW statement_timeout",
    "lock_timeout": "SHOW lock_timeout",
    "application_name": "SHOW application_name",
    "max_execution_time": "SELECT @@SESSION.max_execution_time",
    "innodb_lock_wait_timeout": "SELECT @@SESSION.innodb_lock_wait_timeout",
    "busy_timeout": "PRAGMA busy_timeout",
}


def _manager_for(db_type: str, kind: str, field: str, value: str) -> tuple[object, object]:
    """Return a manager shell (no engine) and its configuration with the field set to the JSON value."""
    section = getattr(BaseConfig.global_config(), _SECTIONS[db_type])
    configs = section.model_copy(update={field: json.loads(value)})
    manager = object.__new__(_MANAGERS[db_type, kind])  # skip __init__: it would build a pooled engine
    manager._configs = configs
    return manager, configs


def _read_prepare_threshold(raw_connection: object) -> object:
    """Return the psycopg prepare_threshold of the driver connection behind a SQLAlchemy raw connection."""
    return raw_connection.driver_connection.prepare_threshold


def _read_setting(db_type: str, kind: str, setting: str, field: str, value: str) -> str:
    """Connect with the configured driver options and return the session value of the setting."""
    manager, configs = _manager_for(db_type, kind, field, value)
    url = manager._create_url(configs)
    connect_args = manager._get_connect_args()
    query = None if setting == "prepare_threshold" else text(_SETTING_QUERIES[setting])
    if kind == "sync":
        engine = create_engine(url, connect_args=connect_args)
        try:
            with engine.connect() as connection:
                if query is None:
                    return str(_read_prepare_threshold(connection.connection))
                return str(connection.execute(query).scalar_one())
        finally:
            engine.dispose()

    async def run() -> str:
        engine = create_async_engine(url, connect_args=connect_args)
        try:
            async with engine.connect() as connection:
                if query is None:
                    return str(_read_prepare_threshold(await connection.get_raw_connection()))
                return str((await connection.execute(query)).scalar_one())
        finally:
            await engine.dispose()

    return asyncio.run(run())


@when("I read {setting} from a {kind} {db_type} connection configured with {field} {value}")
def step_when_read_session_setting(context, setting, kind, db_type, field, value):
    get_current_scenario_context(context).store("session_setting", _read_setting(db_type, kind, setting, field, value))


@then("the session setting should be {expected}")
def step_then_session_setting(context, expected):
    actual = get_current_scenario_context(context).get("session_setting")
    assert actual == expected, f"Expected {expected}, got {actual}"


@when("I build the {kind} {db_type} driver options with {field} set to {value}")
def step_when_build_driver_options(context, kind, db_type, field, value):
    manager, _ = _manager_for(db_type, kind, field, value)
    get_current_scenario_context(context).store("driver_options", manager._get_connect_args())


@then("the driver options should be {expected}")
def step_then_driver_options(context, expected):
    actual = get_current_scenario_context(context).get("driver_options")
    assert actual == json.loads(expected), f"Expected {expected}, got {actual}"
