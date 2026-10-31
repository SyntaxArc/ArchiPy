"""Step definitions for database driver error classification."""

import logging

from behave import given, then, when
from features.test_helpers import get_current_scenario_context
from sqlalchemy.exc import DBAPIError, OperationalError

import archipy.models.errors as errors_pkg
from archipy.adapters.base.sqlalchemy.driver_errors import classify_driver_error
from archipy.adapters.base.sqlalchemy.mixins import SQLAlchemyExceptionHandlerMixin


class _PostgresDriverError(Exception):
    def __init__(self, sqlstate: str, message: str) -> None:
        super().__init__(message)
        self.sqlstate = sqlstate
        self.pgcode = sqlstate


class _MySQLDriverError(Exception):
    """Mirrors pymysql/aiomysql errors, which carry ``(errno, message)`` in ``args``."""


class _MySQLServerError(Exception):
    """Mirrors pymysql>=1.2/asyncmy>=0.2.14 server errors, which carry ``(errno, message)`` and a ``sqlstate``."""

    def __init__(self, errno: int, message: str, sqlstate: str) -> None:
        super().__init__(errno, message)
        self.sqlstate = sqlstate


class _SQLiteDriverError(Exception):
    def __init__(self, name: str, message: str) -> None:
        super().__init__(message)
        self.sqlite_errorname = name


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _build_driver_error(family: str, code: str, message: str) -> Exception:
    if family == "postgres":
        return _PostgresDriverError(code, message)
    if family in ("mysql", "starrocks"):
        return _MySQLDriverError(int(code), message)
    return _SQLiteDriverError(code, message)


def _wrap(driver_error: Exception) -> DBAPIError:
    return OperationalError("SELECT 1", None, driver_error)


@given('a "{family}" driver error with code "{code}" and message "{message}"')
def step_given_driver_error(context, family, code, message):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("db_error", _wrap(_build_driver_error(family, code, message)))


@given('a {family} server error with errno "{errno}", SQLSTATE "{sqlstate}" and message "{message}"')
def step_given_mysql_server_error(context, family, errno, sqlstate, message):
    driver_error = _MySQLServerError(int(errno), message, sqlstate)
    get_current_scenario_context(context).store("db_error", _wrap(driver_error))


@given('a "{family}" driver error with code "{code}" raised by statement "{statement}"')
def step_given_driver_error_with_statement(context, family, code, statement):
    driver_error = _build_driver_error(family, code, "driver failure")
    get_current_scenario_context(context).store("db_error", OperationalError(statement, None, driver_error))


@given("a driver error without a code that SQLAlchemy flagged as a disconnect")
def step_given_disconnect(context):
    wrapped = OperationalError("SELECT 1", None, Exception("server closed the connection"), connection_invalidated=True)
    get_current_scenario_context(context).store("db_error", wrapped)


@given('an adapted driver error whose cause has SQLSTATE "{sqlstate}"')
def step_given_adapted_driver_error(context, sqlstate):
    adapted = Exception("adapted driver error without a code")
    adapted.__cause__ = _PostgresDriverError(sqlstate, "root cause")
    get_current_scenario_context(context).store("db_error", _wrap(adapted))


@given('a plain exception with message "{message}"')
def step_given_plain_exception(context, message):
    get_current_scenario_context(context).store("db_error", Exception(message))


@when("the driver error is classified")
def step_when_classified(context):
    scenario_context = get_current_scenario_context(context)
    scenario_context.store("classified", classify_driver_error(scenario_context.get("db_error")))


@then('the domain error should be "{expected}"')
def step_then_domain_error(context, expected):
    classified = get_current_scenario_context(context).get("classified")
    if expected == "none":
        assert classified is None, f"Expected no classification, got {classified}"
        return
    assert classified is getattr(errors_pkg, expected), f"Expected {expected}, got {classified}"


@when("the adapter exception handler processes the driver error")
def step_when_handler(context):
    _process_with_handler(context, logging.DEBUG)


@when("the adapter exception handler processes the driver error at DEBUG level")
def step_when_handler_debug(context):
    _process_with_handler(context, logging.DEBUG)


def _process_with_handler(context, level):
    scenario_context = get_current_scenario_context(context)
    handler = _ListHandler()
    logger = logging.getLogger("archipy.adapters.base.sqlalchemy.driver_errors")
    logger.addHandler(handler)
    previous_level = logger.level
    logger.setLevel(level)
    try:
        SQLAlchemyExceptionHandlerMixin._handle_db_exception(scenario_context.get("db_error"), "test_db")
    except errors_pkg.BaseError as exception:
        scenario_context.store("raised", exception)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
    scenario_context.store("log_records", handler.records)


@then('the raised error should be "{expected}"')
def step_then_raised(context, expected):
    raised = get_current_scenario_context(context).get("raised")
    assert type(raised) is getattr(errors_pkg, expected), f"Expected {expected}, got {type(raised).__name__}"


@then("the original driver error should be its cause")
def step_then_cause(context):
    scenario_context = get_current_scenario_context(context)
    assert scenario_context.get("raised").__cause__ is scenario_context.get("db_error")


@then('a "{level}" log record should mention code "{code}"')
def step_then_log(context, level, code):
    records = get_current_scenario_context(context).get("log_records")
    matching = [r for r in records if r.levelname == level and f"code={code}" in r.getMessage()]
    assert matching, f"No {level} record with code={code}: {[r.getMessage() for r in records]}"


@given("the {error_name} type")
def step_given_error_type(context, error_name):
    get_current_scenario_context(context).store("error_type", getattr(errors_pkg, error_name))


@then("it should be a subclass of DatabaseQueryError")
def step_then_query_error_subclass(context):
    error_type = get_current_scenario_context(context).get("error_type")
    assert issubclass(error_type, errors_pkg.DatabaseQueryError), f"{error_type.__name__} is not a DatabaseQueryError"


@then("its HTTP status should be {http_status:d} and its gRPC status should be {grpc_status:d}")
def step_then_statuses(context, http_status, grpc_status):
    error_type = get_current_scenario_context(context).get("error_type")
    assert error_type.http_status == http_status
    assert error_type.grpc_status == grpc_status


@then("its retryable flag should be {expected}")
def step_then_retryable(context, expected):
    error_type = get_current_scenario_context(context).get("error_type")
    assert error_type.retryable is (expected == "true"), f"{error_type.__name__}.retryable is {error_type.retryable}"


@then('the logged statement should be "{expected}"')
def step_then_logged_statement(context, expected):
    records = get_current_scenario_context(context).get("log_records")
    statements = [getattr(r, "db.query.text", None) for r in records]
    assert expected in statements, f"Expected {expected!r} in {statements}"
