import shutil
import sqlite3
import tempfile
from pathlib import Path

from behave import given, then, when
from sqlalchemy import text

from archipy.adapters.base.sqlalchemy.atomic import sqlite_sqlalchemy_atomic
from archipy.adapters.base.sqlalchemy.session_manager_registry import SessionManagerRegistry
from archipy.adapters.sqlite.sqlalchemy.adapters import SQLiteSQLAlchemyAdapter
from archipy.adapters.sqlite.sqlalchemy.session_manager_registry import SQLiteSessionManagerRegistry
from archipy.adapters.sqlite.sqlalchemy.session_managers import SQLiteSQLAlchemySessionManager
from archipy.configs.config_template import SQLiteSQLAlchemyConfig
from archipy.models import errors
from features.test_helpers import get_current_scenario_context


class _FailAfterWriteError(Exception):
    """Raised on purpose to roll an atomic block back."""


def _database(context, name):
    return get_current_scenario_context(context).get("multi_db")[name]


def _insert(registry, value):
    session = registry.get_sync_manager().get_session()
    session.execute(text("INSERT INTO items (name) VALUES (:name)"), {"name": value})


def _count(path):
    with sqlite3.connect(path) as connection:
        return connection.execute("SELECT COUNT(*) FROM items").fetchone()[0]


@given('two SQLite databases "{first}" and "{second}"')
def step_given_two_sqlite_databases(context, first, second):
    directory = Path(tempfile.mkdtemp(prefix="archipy_multi_db_"))
    databases = {}
    for name in (first, second):
        path = str(directory / f"{name}.sqlite")
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE items (name TEXT)")
        config = SQLiteSQLAlchemyConfig(DRIVER_NAME="sqlite", DATABASE=path)
        manager = SQLiteSQLAlchemySessionManager(config)
        registry = type(f"{name.title()}Registry", (SQLiteSessionManagerRegistry,), {})
        registry.set_sync_manager(manager)
        databases[name] = {"path": path, "config": config, "manager": manager, "registry": registry}

    def cleanup():
        for database in databases.values():
            database["manager"].remove_session()
            database["manager"].engine.dispose()
        shutil.rmtree(directory, ignore_errors=True)

    context.add_cleanup(cleanup)
    get_current_scenario_context(context).store("multi_db", databases)


@then('the session manager of "{name}" is the session manager built again from its configuration')
def step_then_manager_is_shared(context, name):
    database = _database(context, name)
    assert SQLiteSQLAlchemySessionManager(database["config"]) is database["manager"]


@then('the session managers of "{first}" and "{second}" are different')
def step_then_managers_differ(context, first, second):
    assert _database(context, first)["manager"] is not _database(context, second)["manager"]


@when('an item "{value}" is added through the adapter of "{name}"')
def step_when_item_added_through_adapter(context, value, name):
    database = _database(context, name)
    adapter = SQLiteSQLAlchemyAdapter(orm_config=database["config"])
    assert adapter.session_manager is database["manager"]
    session = adapter.get_session()
    session.execute(text("INSERT INTO items (name) VALUES (:name)"), {"name": value})
    session.commit()


@then('the registry of "{name}" returns the session manager of "{name2}"')
def step_then_registry_returns_manager(context, name, name2):
    database = _database(context, name)
    assert database["registry"].get_sync_manager() is _database(context, name2)["manager"]


@when('an item "{value}" is added in an atomic block on "{name}"')
def step_when_item_added_atomic(context, value, name):
    registry = _database(context, name)["registry"]

    @sqlite_sqlalchemy_atomic(registry=registry)
    def add() -> None:
        _insert(registry, value)

    add()


@when('an item "{value}" is added in an atomic block on "{name}" that fails')
def step_when_item_added_atomic_fails(context, value, name):
    registry = _database(context, name)["registry"]

    @sqlite_sqlalchemy_atomic(registry=registry)
    def add() -> None:
        _insert(registry, value)
        raise _FailAfterWriteError

    try:
        add()
    except Exception as error:
        get_current_scenario_context(context).store("multi_db_error", error)


@when(
    'an item "{first_value}" is added on "{first}" and "{second_value}" on "{second}" in nested atomic blocks, then the outer block fails'
)
def step_when_nested_blocks(context, first_value, first, second_value, second):
    first_registry = _database(context, first)["registry"]
    second_registry = _database(context, second)["registry"]

    @sqlite_sqlalchemy_atomic(registry=second_registry)
    def inner() -> None:
        _insert(second_registry, second_value)

    @sqlite_sqlalchemy_atomic(registry=first_registry)
    def outer() -> None:
        _insert(first_registry, first_value)
        inner()
        raise _FailAfterWriteError

    try:
        outer()
    except Exception as error:
        get_current_scenario_context(context).store("multi_db_error", error)


@then('the database "{name}" holds {count:d} items')
def step_then_database_holds(context, name, count):
    assert _count(_database(context, name)["path"]) == count


def _scratch_registry():
    """Return a registry subclass that holds no session manager, so no other scenario is touched."""
    return type("ScratchRegistry", (SessionManagerRegistry,), {})


def _remember_registry_outcome(context, action):
    scenario_context = get_current_scenario_context(context)
    try:
        action()
        scenario_context.store("registry_error", None)
    except Exception as error:
        scenario_context.store("registry_error", error)


@when("the {mode} session manager is requested from an empty registry")
def step_when_manager_requested_from_empty_registry(context, mode):
    registry = _scratch_registry()
    getter = registry.get_async_manager if mode == "async" else registry.get_sync_manager
    _remember_registry_outcome(context, getter)


@when("{value} is registered as the {mode} session manager")
def step_when_invalid_manager_registered(context, value, mode):
    registry = _scratch_registry()
    manager = None if value == "nothing" else "not a session manager"
    setter = registry.set_async_manager if mode == "async" else registry.set_sync_manager
    _remember_registry_outcome(context, lambda: setter(manager))


@then("the registry should refuse with {error_name}")
def step_then_registry_refuses(context, error_name):
    error = get_current_scenario_context(context).get("registry_error")
    assert isinstance(error, getattr(errors, error_name)), f"Expected {error_name}, got {error!r}"
