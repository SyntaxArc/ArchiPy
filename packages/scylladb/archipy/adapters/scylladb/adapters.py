"""ScyllaDB adapter implementations for sync and async operations.

This module provides concrete implementations of the ScyllaDB port interfaces,
supporting both synchronous and asynchronous database operations.
"""

import asyncio
import logging
import re
import time
import warnings
from typing import Any, Final, Literal, NoReturn, TypedDict, override

from async_lru import alru_cache
from cassandra import (
    AuthenticationFailed,
    ConsistencyLevel,
    DriverException,
    InvalidRequest,
    OperationTimedOut,
    Timeout as DriverTimeout,
    Unavailable,
)
from cassandra.auth import PlainTextAuthProvider
from cassandra.cluster import (
    EXEC_PROFILE_DEFAULT,
    Cluster,
    ExecutionProfile,
    NoHostAvailable,
    ProtocolVersionUnsupported,
    ResponseFuture,
    ResultSet,
    Session,
)
from cassandra.connection import ConnectionException
from cassandra.policies import (
    AddressTranslator,
    ConstantReconnectionPolicy,
    ConstantSpeculativeExecutionPolicy,
    DCAwareRoundRobinPolicy,
    ExponentialBackoffRetryPolicy,
    ExponentialReconnectionPolicy,
    FallthroughRetryPolicy,
    RoundRobinPolicy,
    TokenAwarePolicy,
)
from cassandra.protocol import ProtocolException, RequestValidationException
from cassandra.query import BatchStatement, BatchType, PreparedStatement, SimpleStatement

from archipy.adapters.scylladb.ports import AsyncScyllaDBPort, BatchItem, ScyllaDBPort
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import ScyllaDBConfig
from archipy.helpers.decorators import ttl_cache
from archipy.models.errors import (
    ConfigurationError,
    ConnectionTimeoutError,
    DatabaseConnectionError,
    DatabaseQueryError,
    InvalidArgumentError,
    InvalidCredentialsError,
    NetworkError,
    NotFoundError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)
_CQL_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_BATCH_TYPES: Final = {"LOGGED": BatchType.LOGGED, "UNLOGGED": BatchType.UNLOGGED, "COUNTER": BatchType.COUNTER}
_UNCONFIGURED_TABLE_PATTERN = re.compile(r"unconfigured table\s+\"?([A-Za-z0-9_.]+)", re.IGNORECASE)
# Fixed texts: probe responses must not reveal driver messages, hosts or addresses; details go to the log.
_HEALTH_CHECK_FAILED: Final = "unavailable"
_POOL_STATS_FAILED: Final = "unavailable"


_POOL_SETTING_DEFAULTS: Final = {
    "MAX_CONNECTIONS_PER_HOST": 2,
    "MIN_CONNECTIONS_PER_HOST": 1,
    "CORE_CONNECTIONS_PER_HOST": 1,
    "MAX_REQUESTS_PER_CONNECTION": 100,
}


def _warn_ignored_pool_settings(config: ScyllaDBConfig) -> None:
    """Warn about connection pool settings that scylla-driver does not apply.

    scylla-driver (protocol v3+) keeps one connection per host (per shard when shard-aware); it has no per-host pool
    size or per-connection request limit, so these settings never had an effect.

    Args:
        config (ScyllaDBConfig): The ScyllaDB configuration.
    """
    values = vars(config)  # read without the pydantic deprecation warning
    ignored = [name for name, default in _POOL_SETTING_DEFAULTS.items() if values[name] != default]
    if ignored:
        warnings.warn(
            f"{', '.join(ignored)} {'has' if len(ignored) == 1 else 'have'} no effect: scylla-driver does not support "
            "per-host connection pool sizing, and the setting will be removed in a future release",
            DeprecationWarning,
            stacklevel=3,
        )


_SERIAL_CONSISTENCY_LEVELS: Final = {
    "SERIAL": ConsistencyLevel.SERIAL,
    "LOCAL_SERIAL": ConsistencyLevel.LOCAL_SERIAL,
}


def _cluster_resilience_options(config: ScyllaDBConfig) -> dict[str, Any]:
    """Build the optional ``Cluster`` keyword arguments for heartbeat, timeout and reconnection settings.

    Only settings the caller set are returned, so unset ones keep the driver defaults.

    Args:
        config (ScyllaDBConfig): The ScyllaDB configuration.

    Returns:
        dict[str, Any]: Keyword arguments for ``Cluster``.
    """
    options: dict[str, Any] = {}
    if config.IDLE_HEARTBEAT_INTERVAL is not None:
        options["idle_heartbeat_interval"] = config.IDLE_HEARTBEAT_INTERVAL
    if config.IDLE_HEARTBEAT_TIMEOUT is not None:
        options["idle_heartbeat_timeout"] = config.IDLE_HEARTBEAT_TIMEOUT
    if config.CONTROL_CONNECTION_TIMEOUT is not None:
        options["control_connection_timeout"] = config.CONTROL_CONNECTION_TIMEOUT
    if config.RECONNECTION_POLICY == "CONSTANT":
        options["reconnection_policy"] = ConstantReconnectionPolicy(
            delay=config.RECONNECTION_BASE_DELAY,
            max_attempts=config.RECONNECTION_MAX_ATTEMPTS,
        )
    elif config.RECONNECTION_POLICY == "EXPONENTIAL":
        options["reconnection_policy"] = ExponentialReconnectionPolicy(
            base_delay=config.RECONNECTION_BASE_DELAY,
            max_delay=config.RECONNECTION_MAX_DELAY,
            max_attempts=config.RECONNECTION_MAX_ATTEMPTS,
        )
    return options


def _execution_profile_options(config: ScyllaDBConfig) -> dict[str, Any]:
    """Build the optional ``ExecutionProfile`` keyword arguments for serial consistency and speculative execution.

    Args:
        config (ScyllaDBConfig): The ScyllaDB configuration.

    Returns:
        dict[str, Any]: Keyword arguments for ``ExecutionProfile``.
    """
    options: dict[str, Any] = {}
    if config.SERIAL_CONSISTENCY_LEVEL is not None:
        options["serial_consistency_level"] = _SERIAL_CONSISTENCY_LEVELS[config.SERIAL_CONSISTENCY_LEVEL]
    if config.SPECULATIVE_EXECUTION_DELAY is not None:
        options["speculative_execution_policy"] = ConstantSpeculativeExecutionPolicy(
            delay=config.SPECULATIVE_EXECUTION_DELAY,
            max_attempts=config.SPECULATIVE_EXECUTION_MAX_ATTEMPTS,
        )
    return options


def _tls_cluster_options(config: ScyllaDBConfig) -> dict[str, Any]:
    """Build the optional TLS ``Cluster`` keyword arguments for the server name and session resumption.

    Args:
        config (ScyllaDBConfig): The ScyllaDB configuration.

    Returns:
        dict[str, Any]: Keyword arguments for ``Cluster``; empty when TLS is disabled.
    """
    if not config.TLS_ENABLED:
        return {}
    options: dict[str, Any] = {}
    if config.TLS_SERVER_NAME:
        options["ssl_options"] = {"server_hostname": config.TLS_SERVER_NAME}
    if not config.TLS_SESSION_CACHE_ENABLED:
        options["ssl_session_cache"] = None
    return options


class _IdempotentSafeRetryPolicy(ExponentialBackoffRetryPolicy):
    """Exponential backoff that retries request errors on the next host only for idempotent statements.

    The driver calls ``on_request_error`` for server errors and connection loss without checking idempotency, and the
    request may already have been applied; retrying a non-idempotent write could apply it twice. Unavailable errors
    are safe to retry because the request was never executed.
    """

    @override
    def on_request_error(self, query: Any, consistency: Any, error: Any, retry_num: int) -> tuple[int, Any, Any]:
        if not getattr(query, "is_idempotent", False):
            return self.RETHROW, None, None
        return super().on_request_error(query, consistency, error, retry_num)


class _HostPoolStat(TypedDict):
    """Per-host connection pool statistics for ScyllaDB monitoring."""

    host: str
    open_connections: int
    in_flight_queries: int


class _FixedAddressTranslator(AddressTranslator):
    """Translates all discovered node addresses to a fixed host address.

    Used in Docker/NAT environments where gossip-discovered internal IPs are unreachable.
    """

    def __init__(self, address: str) -> None:
        self._address = address

    def translate(self, addr: str) -> str:  # noqa: ARG002
        return self._address


class ScyllaDBExceptionHandlerMixin:
    """Mixin class to handle ScyllaDB/Cassandra exceptions in a consistent way."""

    @classmethod
    def _raise_for_cassandra_driver_exception(cls, exception: Exception, operation: str) -> None:
        """Map known driver exceptions by type; return when the exception is not one of them."""
        if isinstance(exception, Unavailable | NoHostAvailable):
            raise ServiceUnavailableError(service="ScyllaDB") from exception

        if isinstance(exception, OperationTimedOut):
            timeout = int(exception.timeout) if exception.timeout is not None else None
            raise ConnectionTimeoutError(service="ScyllaDB", timeout=timeout) from exception

        if isinstance(exception, DriverTimeout):  # ReadTimeout and WriteTimeout
            raise ConnectionTimeoutError(service="ScyllaDB", timeout=None) from exception

        if isinstance(exception, AuthenticationFailed):
            raise InvalidCredentialsError() from exception

        if isinstance(exception, InvalidRequest | RequestValidationException):
            raise InvalidArgumentError(argument_name=operation) from exception

        if isinstance(exception, ProtocolException | ProtocolVersionUnsupported):
            raise ConfigurationError(operation="scylladb", reason="Protocol error") from exception

        if isinstance(exception, ConnectionException | OSError):
            raise NetworkError(service="ScyllaDB") from exception

    @classmethod
    def _handle_scylladb_exception(cls, exception: Exception, operation: str) -> NoReturn:
        """Handle ScyllaDB/Cassandra exceptions and map them to appropriate application errors.

        Exceptions are mapped by type. The server reports a missing table as an ``InvalidRequest`` whose message is
        the only place that names the table, so that one message is parsed.

        Args:
            exception: The original exception
            operation: The name of the operation that failed

        Raises:
            Various application-specific errors based on the exception type
        """
        match = _UNCONFIGURED_TABLE_PATTERN.search(str(exception))
        if match:
            raise NotFoundError(
                resource_type="table",
                additional_data={"table_name": match.group(1)},
            ) from exception

        cls._raise_for_cassandra_driver_exception(exception, operation)

        if "connection" in operation.lower() or "connect" in operation.lower():
            raise DatabaseConnectionError(database="scylladb") from exception
        raise DatabaseQueryError(database="scylladb") from exception

    @classmethod
    def _validate_positive_int(cls, value: int, field_name: str) -> int:
        """Validate a numeric value that is interpolated into CQL text and must be at least 1.

        Args:
            value: Value to validate.
            field_name: Field name for error context.

        Returns:
            The validated integer.

        Raises:
            InvalidArgumentError: If the value is not a positive int.
        """
        if cls._validate_non_negative_int(value, field_name) < 1:
            raise InvalidArgumentError(
                argument_name=field_name,
                additional_data={"error": "Value must be a positive integer"},
            )
        return value

    @staticmethod
    def _validate_cql_identifier(identifier: str, field_name: str) -> str:
        """Validate CQL identifier input used in dynamic query construction.

        Args:
            identifier: Identifier value such as table, keyspace, or column name.
            field_name: Field name for error context.

        Returns:
            The validated identifier.

        Raises:
            InvalidArgumentError: If identifier is empty or contains unsafe characters.
        """
        if not identifier or not _CQL_IDENTIFIER_PATTERN.fullmatch(identifier):
            raise InvalidArgumentError(
                argument_name=field_name,
                additional_data={"error": "Identifier contains invalid characters"},
            )
        return identifier

    @staticmethod
    def _build_batch(statements: list[BatchItem], batch_type: str, consistency_level: int) -> BatchStatement:
        """Build a batch from CQL strings and ``(statement, params)`` pairs.

        Args:
            statements: Items to add to the batch.
            batch_type: One of LOGGED, UNLOGGED or COUNTER.
            consistency_level: Consistency level for the batch.

        Returns:
            The batch statement.

        Raises:
            InvalidArgumentError: If the batch type is unknown or the batch is empty.
        """
        if batch_type not in _BATCH_TYPES or not statements:
            raise InvalidArgumentError(argument_name="batch")
        batch = BatchStatement(batch_type=_BATCH_TYPES[batch_type], consistency_level=consistency_level)
        for item in statements:
            if isinstance(item, str):
                batch.add(SimpleStatement(item))
            else:
                statement, params = item
                batch.add(SimpleStatement(statement) if isinstance(statement, str) else statement, params)
        return batch

    @classmethod
    def _build_create_keyspace_query(
        cls,
        config: ScyllaDBConfig,
        keyspace: str,
        replication_factor: int | None,
    ) -> str:
        """Build the CREATE KEYSPACE statement and warn when it leaves a single replica.

        An explicit ``replication_factor`` applies to every configured datacenter; without one the configured
        ``REPLICATION_CONFIG`` is used.

        Args:
            config: The adapter configuration.
            keyspace: Name of the keyspace to create.
            replication_factor: Explicit replication factor, or None to use the configuration.

        Returns:
            The CQL statement.

        Raises:
            InvalidArgumentError: If an identifier or the replication factor is invalid.
        """
        keyspace = cls._validate_cql_identifier(keyspace, "keyspace")
        if replication_factor is not None:
            replication_factor = cls._validate_non_negative_int(replication_factor, "replication_factor")

        if config.REPLICATION_STRATEGY == "NetworkTopologyStrategy" and config.REPLICATION_CONFIG:
            parts = ["'class': 'NetworkTopologyStrategy'"]
            factors: list[int] = []
            for dc, configured in config.REPLICATION_CONFIG.items():
                validated_dc = cls._validate_cql_identifier(dc, "replication_datacenter")
                factor = configured if replication_factor is None else replication_factor
                factors.append(factor)
                parts.append(f"'{validated_dc}': {factor}")
            replication = ", ".join(parts)
        else:
            factor = 1 if replication_factor is None else replication_factor
            factors = [factor]
            replication = f"'class': 'SimpleStrategy', 'replication_factor': {factor}"

        if max(factors) <= 1:
            logger.warning(
                "ScyllaDB keyspace %s is created with replication factor 1: losing one node loses data; "
                "use at least 3 in production",
                keyspace,
            )
        return f"CREATE KEYSPACE IF NOT EXISTS {keyspace} WITH replication = {{{replication}}}"

    @staticmethod
    def _validate_non_negative_int(value: int, field_name: str) -> int:
        """Validate a numeric value that is interpolated into CQL text.

        Type hints are not enforced at runtime, so a string here would be injected into the query.

        Args:
            value: Value to validate.
            field_name: Field name for error context.

        Returns:
            The validated integer.

        Raises:
            InvalidArgumentError: If the value is not a non-negative int.
        """
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise InvalidArgumentError(
                argument_name=field_name,
                additional_data={"error": "Value must be a non-negative integer"},
            )
        return value

    @classmethod
    def _validate_cql_identifiers(cls, identifiers: list[str], field_name: str) -> list[str]:
        """Validate multiple CQL identifiers.

        Args:
            identifiers: Identifiers to validate.
            field_name: Field name for error context.

        Returns:
            Validated identifiers.

        Raises:
            InvalidArgumentError: If list is empty or any identifier is invalid.
        """
        if not identifiers:
            raise InvalidArgumentError(argument_name=field_name)
        return [cls._validate_cql_identifier(identifier, field_name) for identifier in identifiers]


class ScyllaDBAdapter(ScyllaDBPort, ScyllaDBExceptionHandlerMixin):
    """Synchronous adapter for ScyllaDB operations.

    This adapter implements the ScyllaDBPort interface to provide a consistent
    way to interact with ScyllaDB, abstracting the underlying driver implementation.
    It supports connection pooling, prepared statements, and batch operations.

    Args:
        config (ScyllaDBConfig | None): Configuration settings for ScyllaDB.
            If None, retrieves from global config. Defaults to None.
    """

    def __init__(self, config: ScyllaDBConfig | None = None) -> None:
        """Initialize the ScyllaDBAdapter with configuration settings.

        Args:
            config (ScyllaDBConfig | None): Configuration settings for ScyllaDB.
                If None, retrieves from global config. Defaults to None.
        """
        if config is not None:
            self.config = config
        else:
            try:
                self.config = BaseConfig.global_config().SCYLLADB
            except AttributeError:
                # SCYLLADB not configured, use defaults
                self.config = ScyllaDBConfig()
        self.__post_init__()
        try:
            self._cluster = self._create_cluster()
            self._session = self._cluster.connect()
            if self.config.KEYSPACE:
                self._session.set_keyspace(self.config.KEYSPACE)

        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "connect")
            raise

    def _get_consistency_level(self) -> int:
        """Get ConsistencyLevel enum from config string.

        Returns:
            int: The consistency level enum value.
        """
        consistency_map: dict[str, int] = {
            "ONE": ConsistencyLevel.ONE,
            "TWO": ConsistencyLevel.TWO,
            "THREE": ConsistencyLevel.THREE,
            "QUORUM": ConsistencyLevel.QUORUM,
            "ALL": ConsistencyLevel.ALL,
            "LOCAL_QUORUM": ConsistencyLevel.LOCAL_QUORUM,
            "EACH_QUORUM": ConsistencyLevel.EACH_QUORUM,
            "LOCAL_ONE": ConsistencyLevel.LOCAL_ONE,
            "ANY": ConsistencyLevel.ANY,
        }
        # get() returns int | None, but we provide a default
        consistency = consistency_map.get(self.config.CONSISTENCY_LEVEL.upper())
        if consistency is None:
            return ConsistencyLevel.ONE
        return consistency

    def _create_cluster(self) -> Cluster:
        """Create and configure the Cluster instance.

        Returns:
            Cluster: Configured cluster instance.
        """
        auth_provider = None
        if self.config.USERNAME and self.config.PASSWORD:
            auth_provider = PlainTextAuthProvider(
                username=self.config.USERNAME,
                password=self.config.PASSWORD.get_secret_value(),
            )

        # Configure load balancing policy with optional datacenter awareness
        if self.config.LOCAL_DC:
            base_policy = DCAwareRoundRobinPolicy(local_dc=self.config.LOCAL_DC)
            load_balancing_policy = TokenAwarePolicy(base_policy)
        else:
            load_balancing_policy = TokenAwarePolicy(RoundRobinPolicy())

        if self.config.RETRY_POLICY == "FALLTHROUGH":
            retry_policy = FallthroughRetryPolicy()
        else:  # EXPONENTIAL_BACKOFF (default)
            retry_policy = _IdempotentSafeRetryPolicy(
                max_num_retries=self.config.RETRY_MAX_NUM_RETRIES,
                min_interval=self.config.RETRY_MIN_INTERVAL,
                max_interval=self.config.RETRY_MAX_INTERVAL,
            )
        # Shard awareness disabled for Docker/NAT environments
        shard_aware_options = None
        if self.config.DISABLE_SHARD_AWARENESS:
            shard_aware_options = {"disable": True}

        # Address translation for Docker/NAT environments where gossip-discovered
        # internal container IPs are unreachable from the host
        address_translator = None
        if self.config.ADDRESS_TRANSLATION_ENABLED:
            address_translator = _FixedAddressTranslator(self.config.CONTACT_POINTS[0])

        # Cluster is from cassandra.cluster, properly typed
        cluster = Cluster(
            contact_points=self.config.CONTACT_POINTS,
            port=self.config.PORT,
            auth_provider=auth_provider,
            protocol_version=self.config.PROTOCOL_VERSION,
            compression=bool(self.config.COMPRESSION),
            connect_timeout=self.config.CONNECT_TIMEOUT,
            execution_profiles={
                EXEC_PROFILE_DEFAULT: ExecutionProfile(
                    load_balancing_policy=load_balancing_policy,
                    retry_policy=retry_policy,
                    request_timeout=self.config.REQUEST_TIMEOUT,
                    consistency_level=self._get_consistency_level(),
                    **_execution_profile_options(self.config),
                ),
            },
            shard_aware_options=shard_aware_options,
            address_translator=address_translator,
            ssl_context=self.config.build_ssl_context(),
            **_tls_cluster_options(self.config),
            **_cluster_resilience_options(self.config),
        )
        _warn_ignored_pool_settings(self.config)

        return cluster

    @override
    def execute(self, query: str, params: dict[str, Any] | tuple[Any, ...] | list[Any] | None = None) -> ResultSet:
        """Execute a CQL query.

        Args:
            query (str): The CQL query to execute.
            params (dict[str, Any] | tuple[Any, ...] | list[Any] | None): Query parameters for parameterized queries.

        Returns:
            ResultSet: The query result set.
        """
        session = self.get_session()
        try:
            result = session.execute(query, params) if params else session.execute(query)
        except (DriverException, NoHostAvailable, RequestValidationException) as e:
            self._handle_scylladb_exception(e, "execute")
            raise
        else:
            return result

    @override
    def prepare(self, query: str) -> PreparedStatement:
        """Prepare a CQL statement for repeated execution.

        Args:
            query (str): The CQL query to prepare.

        Returns:
            PreparedStatement: The prepared statement object.
        """
        session = self.get_session()
        try:
            if self.config.ENABLE_PREPARED_STATEMENT_CACHE:
                # Use cached version if available - call the cached method
                cached_method: Any = getattr(self, "_prepare_cached", None)
                if cached_method is not None:
                    return cached_method(session.keyspace, query)
            # Direct prepare without cache
            prepared = session.prepare(query)
        except (DriverException, NoHostAvailable, RequestValidationException) as e:
            self._handle_scylladb_exception(e, "prepare")
            raise
        else:
            return prepared

    def __post_init__(self) -> None:
        """Post-initialization hook to apply cache decorator if enabled."""
        if self.config.ENABLE_PREPARED_STATEMENT_CACHE:
            # Create a method to cache
            def _prepare_internal(keyspace: str | None, query: str) -> PreparedStatement:  # noqa: ARG001
                """Prepare a CQL statement; the keyspace only keys the cache."""
                session = self.get_session()
                try:
                    prepared = session.prepare(query)
                except (DriverException, NoHostAvailable, RequestValidationException) as e:
                    self._handle_scylladb_exception(e, "prepare")
                    raise
                else:
                    return prepared

            # Apply cache decorator
            cached_prepare = ttl_cache(
                ttl_seconds=self.config.PREPARED_STATEMENT_CACHE_TTL_SECONDS,
                maxsize=self.config.PREPARED_STATEMENT_CACHE_SIZE,
            )(_prepare_internal)
            # Store the cached version using setattr for dynamic attribute
            self._prepare_cached = cached_prepare

    def _execute_dml(self, query: str, params: tuple[Any, ...] | None, *, idempotent: bool = True) -> ResultSet:
        """Run a query built from validated identifiers and bound values.

        With the prepared statement cache on, the query is prepared (once) and executed with bound values, which keeps
        token and shard aware routing. With it off, the query runs as a plain parameterised statement.

        Args:
            query (str): CQL using ``%s`` placeholders.
            params (tuple[Any, ...] | None): Values to bind.
            idempotent (bool): Whether running the statement twice has the same effect as once. Request errors are only
                retried on another host for idempotent statements. Defaults to True.

        Returns:
            ResultSet: The query result set.
        """
        if self.config.ENABLE_PREPARED_STATEMENT_CACHE:
            statement = self.prepare(query.replace("%s", "?"))
            statement.is_idempotent = idempotent
            return self.execute_prepared(statement, params)
        return self.execute(query, params)

    @override
    def execute_prepared(
        self,
        statement: PreparedStatement,
        params: dict[str, Any] | tuple[Any, ...] | list[Any] | None = None,
    ) -> ResultSet:
        """Execute a prepared statement.

        Args:
            statement (PreparedStatement): The prepared statement object.
            params (dict[str, Any] | tuple[Any, ...] | list[Any] | None): Parameters to bind to the statement.

        Returns:
            ResultSet: The query result set.
        """
        session = self.get_session()
        try:
            result = session.execute(statement, params) if params else session.execute(statement)
        except (DriverException, NoHostAvailable, RequestValidationException) as e:
            self._handle_scylladb_exception(e, "execute_prepared")
            raise
        else:
            return result

    @override
    def create_keyspace(self, keyspace: str, replication_factor: int | None = None) -> None:
        """Create a keyspace with simple replication strategy.

        Args:
            keyspace (str): The name of the keyspace to create.
            replication_factor (int | None): Replicas per datacenter (``NetworkTopologyStrategy``) or in total
                (``SimpleStrategy``). When None, the configured ``REPLICATION_CONFIG`` is used, or 1 for
                ``SimpleStrategy``.
        """
        query = self._build_create_keyspace_query(self.config, keyspace, replication_factor)
        try:
            self.execute(query)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "create_keyspace")
            raise

    @override
    def drop_keyspace(self, keyspace: str) -> None:
        """Drop a keyspace.

        Args:
            keyspace (str): The name of the keyspace to drop.
        """
        keyspace = self._validate_cql_identifier(keyspace, "keyspace")
        query = f"DROP KEYSPACE IF EXISTS {keyspace}"
        try:
            self.execute(query)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "drop_keyspace")
            raise

    @override
    def use_keyspace(self, keyspace: str) -> None:
        """Switch to a different keyspace context.

        Args:
            keyspace (str): The name of the keyspace to use.
        """
        session = self.get_session()
        try:
            keyspace = self._validate_cql_identifier(keyspace, "keyspace")
            session.set_keyspace(keyspace)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "use_keyspace")
            raise

    @override
    def create_table(self, table_schema: str) -> None:
        """Create a table using raw CQL DDL.

        Args:
            table_schema (str): The complete CREATE TABLE CQL statement.
        """
        try:
            self.execute(table_schema)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "create_table")
            raise

    @override
    def drop_table(self, table: str) -> None:
        """Drop a table.

        Args:
            table (str): The name of the table to drop.
        """
        table = self._validate_cql_identifier(table, "table")
        query = f"DROP TABLE IF EXISTS {table}"
        try:
            self.execute(query)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "drop_table")
            raise

    @override
    def insert(
        self,
        table: str,
        data: dict[str, Any],
        ttl: int | None = None,
        if_not_exists: bool = False,
    ) -> None:
        """Insert data into a table.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs representing column names and values.
            ttl (int | None): Time to live in seconds. If None, data persists indefinitely.
            if_not_exists (bool): If True, use lightweight transaction (INSERT ... IF NOT EXISTS).
                              This prevents errors on duplicate primary keys but is slow
        """
        table = self._validate_cql_identifier(table, "table")
        validated_columns = self._validate_cql_identifiers(list(data.keys()), "columns")
        columns = ", ".join(validated_columns)
        placeholders = ", ".join(["%s" for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"  # nosec B608

        if if_not_exists:
            query += " IF NOT EXISTS"

        if ttl is not None:
            query += f" USING TTL {self._validate_non_negative_int(ttl, 'ttl')}"

        try:
            self._execute_dml(query, tuple(data.values()), idempotent=not if_not_exists)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "insert")
            raise

    @override
    def select(
        self,
        table: str,
        columns: list[str] | None = None,
        conditions: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        """Select data from a table.

        Args:
            table (str): The name of the table.
            columns (list[str] | None): List of columns to select. If None, selects all (*).
            conditions (dict[str, Any] | None): WHERE clause conditions as key-value pairs.
            limit (int | None): Maximum number of rows to return. If None, returns every matching row, which can be
                large; pass a limit on big tables.

        Returns:
            list[Any]: List of result rows.
        """
        table = self._validate_cql_identifier(table, "table")
        cols = ", ".join(self._validate_cql_identifiers(columns, "columns")) if columns else "*"
        query = f"SELECT {cols} FROM {table}"  # nosec B608

        params = None
        if conditions:
            condition_keys = self._validate_cql_identifiers(list(conditions.keys()), "conditions")
            where_clause = " AND ".join([f"{key} = %s" for key in condition_keys])
            query += f" WHERE {where_clause}"
            params = tuple(conditions.values())

        if limit is not None:
            query += f" LIMIT {self._validate_positive_int(limit, 'limit')}"

        try:
            result = self._execute_dml(query, params)
            return list(result)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "select")
            raise

    @override
    def update(
        self,
        table: str,
        data: dict[str, Any],
        conditions: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Update data in a table.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs for SET clause.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.
            ttl (int | None): Time to live in seconds. If None, data persists indefinitely.
        """
        table = self._validate_cql_identifier(table, "table")
        set_keys = self._validate_cql_identifiers(list(data.keys()), "data")
        condition_keys = self._validate_cql_identifiers(list(conditions.keys()), "conditions")
        set_clause = ", ".join([f"{key} = %s" for key in set_keys])
        where_clause = " AND ".join([f"{key} = %s" for key in condition_keys])
        query = f"UPDATE {table}"

        if ttl is not None:
            query += f" USING TTL {self._validate_non_negative_int(ttl, 'ttl')}"

        query += f" SET {set_clause} WHERE {where_clause}"

        # Combine params: SET values first, then WHERE values
        params = tuple(data.values()) + tuple(conditions.values())

        try:
            self._execute_dml(query, params)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "update")
            raise

    @override
    def delete(self, table: str, conditions: dict[str, Any]) -> None:
        """Delete data from a table.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.
        """
        table = self._validate_cql_identifier(table, "table")
        condition_keys = self._validate_cql_identifiers(list(conditions.keys()), "conditions")
        where_clause = " AND ".join([f"{key} = %s" for key in condition_keys])
        query = f"DELETE FROM {table} WHERE {where_clause}"  # nosec B608

        try:
            self._execute_dml(query, tuple(conditions.values()))
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "delete")
            raise

    @override
    def batch_execute(
        self,
        statements: list[BatchItem],
        batch_type: Literal["LOGGED", "UNLOGGED", "COUNTER"] = "LOGGED",
    ) -> None:
        """Execute multiple CQL statements in a batch.

        Args:
            statements (list[BatchItem]): CQL strings, or ``(statement, params)`` pairs where the statement is a CQL
                string with ``%s`` placeholders or a prepared statement.
            batch_type (Literal["LOGGED", "UNLOGGED", "COUNTER"]): ``LOGGED`` (default) is atomic across partitions
                but costs a batch log; use ``UNLOGGED`` for statements on one partition and ``COUNTER`` for counters.
        """
        session = self.get_session()

        try:
            batch = self._build_batch(statements, batch_type, self._get_consistency_level())

            session.execute(batch)
        except (DriverException, NoHostAvailable, RequestValidationException) as e:
            self._handle_scylladb_exception(e, "batch_execute")
            raise

    @override
    def get_session(self) -> Session:
        """Get the current session object.

        Returns:
            Session: The active session object.
        """
        return self._session

    @override
    def is_connected(self) -> bool:
        """Check if the adapter is connected to ScyllaDB cluster.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self._session is not None and not self._session.is_shutdown

    def close(self) -> None:
        """Close the connection and clean up resources.

        This method should be called when the adapter is no longer needed
        to properly release resources.
        """
        try:
            if hasattr(self, "_session") and self._session is not None:
                self._session.shutdown()
            if hasattr(self, "_cluster") and self._cluster is not None:
                self._cluster.shutdown()
        except Exception as e:  # noqa: BLE001  # cleanup/health soft-fail; unconstrained errors
            # Ignore errors during cleanup, but log them
            logger.debug("Error during ScyllaDB adapter cleanup: %s", e)

    def __del__(self) -> None:
        """Destructor to ensure resources are cleaned up."""
        try:
            self.close()
        except Exception as e:  # noqa: BLE001  # cleanup/health soft-fail; unconstrained errors
            # Ignore errors during destructor cleanup
            logger.debug("Error in ScyllaDB adapter destructor: %s", e)

    @override
    def health_check(self) -> dict[str, Any]:
        """Perform a health check on the ScyllaDB connection.

        Returns:
            dict[str, Any]: Health check result with status, latency_ms, and optional error.
        """
        if not self.is_connected():
            return {
                "status": "unhealthy",
                "latency_ms": 0.0,
                "error": _HEALTH_CHECK_FAILED,
            }

        try:
            start_time = time.time()
            session = self.get_session()
            # The request timeout lives in the execution profile, so the probe sets its own per call
            session.execute("SELECT now() FROM system.local", timeout=self.config.HEALTH_CHECK_TIMEOUT)
            latency_ms = (time.time() - start_time) * 1000
        except Exception:  # cleanup/health soft-fail; unconstrained errors
            logger.warning("ScyllaDB health check failed", exc_info=True)
            return {
                "status": "unhealthy",
                "latency_ms": 0.0,
                "error": _HEALTH_CHECK_FAILED,
            }
        else:
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
                "error": None,
            }

    @override
    def count(self, table: str, conditions: dict[str, Any] | None = None) -> int:
        """Count rows in a table.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any] | None): WHERE clause conditions as key-value pairs.

        Returns:
            int: The number of rows matching the conditions.
        """
        table = self._validate_cql_identifier(table, "table")
        query = f"SELECT COUNT(*) FROM {table}"  # nosec B608

        params = None
        if conditions:
            condition_keys = self._validate_cql_identifiers(list(conditions.keys()), "conditions")
            where_clause = " AND ".join([f"{key} = %s" for key in condition_keys])
            query += f" WHERE {where_clause} ALLOW FILTERING"
            params = tuple(conditions.values())

        try:
            result = self._execute_dml(query, params)
            row = result.one()
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "count")
            raise
        else:
            return row.count if row else 0

    @override
    def exists(self, table: str, conditions: dict[str, Any]) -> bool:
        """Check if a row exists in a table.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.

        Returns:
            bool: True if at least one row exists, False otherwise.
        """
        table = self._validate_cql_identifier(table, "table")
        condition_keys = self._validate_cql_identifiers(list(conditions.keys()), "conditions")
        where_clause = " AND ".join([f"{key} = %s" for key in condition_keys])
        # COUNT(*) ... LIMIT 1 still aggregates every match; selecting one key column stops at the first row
        query = f"SELECT {condition_keys[0]} FROM {table} WHERE {where_clause} LIMIT 1 ALLOW FILTERING"  # nosec B608

        try:
            result = self._execute_dml(query, tuple(conditions.values()))
            row = result.one()
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "exists")
            raise
        else:
            return row is not None

    @override
    def get_pool_stats(self) -> dict[str, Any]:
        """Get connection pool statistics.

        Returns:
            dict[str, Any]: Pool statistics including open connections, in-flight requests, etc.
        """
        if not self.config.ENABLE_CONNECTION_POOL_MONITORING:
            return {
                "monitoring_enabled": False,
                "message": "Connection pool monitoring is disabled",
            }

        stats: dict[str, Any] = {"monitoring_enabled": True}

        try:
            session = self.get_session()

            # Get pool state for each host (driver returns {host: state})
            hosts_stats: list[_HostPoolStat] = []
            for host, host_pool in session.get_pool_state().items():
                if host_pool:
                    hosts_stats.append(
                        {
                            "host": str(host),
                            "open_connections": int(host_pool.get("open_count", 0) or 0),
                            "in_flight_queries": int(host_pool.get("in_flight", 0) or 0),
                        },
                    )

            stats["hosts"] = hosts_stats
            stats["total_hosts"] = len(hosts_stats)
            stats["total_open_connections"] = sum(h["open_connections"] for h in hosts_stats)
            stats["total_in_flight_queries"] = sum(h["in_flight_queries"] for h in hosts_stats)

        except Exception:  # cleanup/health soft-fail; unconstrained errors
            logger.warning("ScyllaDB pool statistics unavailable", exc_info=True)
            stats["error"] = _POOL_STATS_FAILED

        return stats


class AsyncScyllaDBAdapter(AsyncScyllaDBPort, ScyllaDBExceptionHandlerMixin):
    """Asynchronous adapter for ScyllaDB operations.

    This adapter implements the AsyncScyllaDBPort interface to provide async
    database operations using the ScyllaDB driver's async capabilities.

    Args:
        config (ScyllaDBConfig | None): Configuration settings for ScyllaDB.
            If None, retrieves from global config. Defaults to None.
    """

    @classmethod
    async def create(cls, config: ScyllaDBConfig | None = None) -> AsyncScyllaDBAdapter:
        """Create the adapter without blocking the event loop.

        The constructor connects to the cluster synchronously, which blocks the running loop for the duration of the
        connection. Use this factory from async code instead.

        Args:
            config (ScyllaDBConfig | None): Configuration settings for ScyllaDB.
                If None, retrieves from global config. Defaults to None.

        Returns:
            AsyncScyllaDBAdapter: A connected adapter.
        """
        return await asyncio.to_thread(cls, config)

    def __init__(self, config: ScyllaDBConfig | None = None) -> None:
        """Initialize the AsyncScyllaDBAdapter with configuration settings.

        Args:
            config (ScyllaDBConfig | None): Configuration settings for ScyllaDB.
                If None, retrieves from global config. Defaults to None.
        """
        if config is not None:
            self.config = config
        else:
            try:
                self.config = BaseConfig.global_config().SCYLLADB
            except AttributeError:
                # SCYLLADB not configured, use defaults
                self.config = ScyllaDBConfig()
        self.__post_init__()
        try:
            self._cluster = self._create_cluster()
            self._session = self._cluster.connect()
            if self.config.KEYSPACE:
                self._session.set_keyspace(self.config.KEYSPACE)

        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "connect")
            raise

    def _get_consistency_level(self) -> int:
        """Get ConsistencyLevel enum from config string.

        Returns:
            int: The consistency level enum value.
        """
        consistency_map: dict[str, int] = {
            "ONE": ConsistencyLevel.ONE,
            "TWO": ConsistencyLevel.TWO,
            "THREE": ConsistencyLevel.THREE,
            "QUORUM": ConsistencyLevel.QUORUM,
            "ALL": ConsistencyLevel.ALL,
            "LOCAL_QUORUM": ConsistencyLevel.LOCAL_QUORUM,
            "EACH_QUORUM": ConsistencyLevel.EACH_QUORUM,
            "LOCAL_ONE": ConsistencyLevel.LOCAL_ONE,
            "ANY": ConsistencyLevel.ANY,
        }
        # get() returns int | None, but we provide a default
        consistency = consistency_map.get(self.config.CONSISTENCY_LEVEL.upper())
        if consistency is None:
            return ConsistencyLevel.ONE
        return consistency

    def _create_cluster(self) -> Cluster:
        """Create and configure the Cluster instance.

        Returns:
            Cluster: Configured cluster instance.
        """
        auth_provider = None
        if self.config.USERNAME and self.config.PASSWORD:
            auth_provider = PlainTextAuthProvider(
                username=self.config.USERNAME,
                password=self.config.PASSWORD.get_secret_value(),
            )

        # Configure load balancing policy with optional datacenter awareness
        if self.config.LOCAL_DC:
            base_policy = DCAwareRoundRobinPolicy(local_dc=self.config.LOCAL_DC)
            load_balancing_policy = TokenAwarePolicy(base_policy)
        else:
            load_balancing_policy = TokenAwarePolicy(RoundRobinPolicy())

        if self.config.RETRY_POLICY == "FALLTHROUGH":
            retry_policy = FallthroughRetryPolicy()
        else:  # EXPONENTIAL_BACKOFF (default)
            retry_policy = _IdempotentSafeRetryPolicy(
                max_num_retries=self.config.RETRY_MAX_NUM_RETRIES,
                min_interval=self.config.RETRY_MIN_INTERVAL,
                max_interval=self.config.RETRY_MAX_INTERVAL,
            )
        # Shard awareness disabled for Docker/NAT environments
        shard_aware_options = None
        if self.config.DISABLE_SHARD_AWARENESS:
            shard_aware_options = {"disable": True}

        # Address translation for Docker/NAT environments where gossip-discovered
        # internal container IPs are unreachable from the host
        address_translator = None
        if self.config.ADDRESS_TRANSLATION_ENABLED:
            address_translator = _FixedAddressTranslator(self.config.CONTACT_POINTS[0])

        # Cluster is from cassandra.cluster, properly typed
        cluster = Cluster(
            contact_points=self.config.CONTACT_POINTS,
            port=self.config.PORT,
            auth_provider=auth_provider,
            protocol_version=self.config.PROTOCOL_VERSION,
            compression=bool(self.config.COMPRESSION),
            connect_timeout=self.config.CONNECT_TIMEOUT,
            execution_profiles={
                EXEC_PROFILE_DEFAULT: ExecutionProfile(
                    load_balancing_policy=load_balancing_policy,
                    retry_policy=retry_policy,
                    request_timeout=self.config.REQUEST_TIMEOUT,
                    consistency_level=self._get_consistency_level(),
                    **_execution_profile_options(self.config),
                ),
            },
            shard_aware_options=shard_aware_options,
            address_translator=address_translator,
            ssl_context=self.config.build_ssl_context(),
            **_tls_cluster_options(self.config),
            **_cluster_resilience_options(self.config),
        )
        _warn_ignored_pool_settings(self.config)

        return cluster

    async def _await_future(self, future: ResponseFuture) -> ResultSet:
        """Convert ResponseFuture to awaitable without holding an executor thread.

        Bridges cassandra-driver's ResponseFuture (callback-based, fired from the
        driver's internal IO thread) directly to an asyncio.Future, avoiding the
        default ThreadPoolExecutor bottleneck under high concurrency.

        Args:
            future: The ResponseFuture from session.execute_async().

        Returns:
            ResultSet: The query result.
        """
        loop = asyncio.get_running_loop()
        asyncio_future: asyncio.Future[ResultSet] = loop.create_future()

        def _on_success(rows: Any) -> None:
            # add_callback passes raw _final_result (first page rows), not ResultSet;
            # match ResponseFuture.result() which returns ResultSet(self, self._final_result).
            if not asyncio_future.done():
                result_set = ResultSet(future, rows)
                loop.call_soon_threadsafe(asyncio_future.set_result, result_set)

        def _on_error(exc: BaseException) -> None:
            if not asyncio_future.done():
                loop.call_soon_threadsafe(asyncio_future.set_exception, exc)

        future.add_callbacks(_on_success, _on_error)
        return await asyncio_future

    @override
    async def execute(
        self,
        query: str,
        params: dict[str, Any] | tuple[Any, ...] | list[Any] | None = None,
    ) -> ResultSet:
        """Execute a CQL query asynchronously.

        Args:
            query (str): The CQL query to execute.
            params (dict[str, Any] | tuple[Any, ...] | list[Any] | None): Query parameters for parameterized queries.

        Returns:
            ResultSet: The query result set.
        """
        session = await self.get_session()
        try:
            future = session.execute_async(query, params) if params else session.execute_async(query)
            result = await self._await_future(future)
        except (DriverException, NoHostAvailable, RequestValidationException) as e:
            self._handle_scylladb_exception(e, "execute")
            raise
        else:
            return result

    @override
    async def prepare(self, query: str) -> PreparedStatement:
        """Prepare a CQL statement asynchronously.

        Args:
            query (str): The CQL query to prepare.

        Returns:
            PreparedStatement: The prepared statement object.
        """
        session = await self.get_session()
        try:
            if self.config.ENABLE_PREPARED_STATEMENT_CACHE:
                # Use cached version if available - call the cached method
                cached_method: Any = getattr(self, "_prepare_cached", None)
                if cached_method is not None:
                    return await cached_method(session.keyspace, query)
            # Direct prepare without cache
            prepared = await asyncio.to_thread(session.prepare, query)
        except (DriverException, NoHostAvailable, RequestValidationException) as e:
            self._handle_scylladb_exception(e, "prepare")
            raise
        else:
            return prepared

    def __post_init__(self) -> None:
        """Post-initialization hook to apply cache decorator if enabled."""
        if self.config.ENABLE_PREPARED_STATEMENT_CACHE:
            # Create an async method to cache
            async def _prepare_internal(keyspace: str | None, query: str) -> PreparedStatement:  # noqa: ARG001
                """Prepare a CQL statement asynchronously; the keyspace only keys the cache."""
                session = await self.get_session()
                try:
                    prepared = await asyncio.to_thread(session.prepare, query)
                except (DriverException, NoHostAvailable, RequestValidationException) as e:
                    self._handle_scylladb_exception(e, "prepare")
                    raise
                else:
                    return prepared

            # Apply async cache decorator
            cached_prepare = alru_cache(
                ttl=self.config.PREPARED_STATEMENT_CACHE_TTL_SECONDS,
                maxsize=self.config.PREPARED_STATEMENT_CACHE_SIZE,
            )(_prepare_internal)
            # Store the cached version using setattr for dynamic attribute
            self._prepare_cached = cached_prepare

    async def _execute_dml(
        self,
        query: str,
        params: tuple[Any, ...] | None,
        *,
        idempotent: bool = True,
    ) -> ResultSet:
        """Run a query built from validated identifiers and bound values.

        With the prepared statement cache on, the query is prepared (once) and executed with bound values, which keeps
        token and shard aware routing. With it off, the query runs as a plain parameterised statement.

        Args:
            query (str): CQL using ``%s`` placeholders.
            params (tuple[Any, ...] | None): Values to bind.
            idempotent (bool): Whether running the statement twice has the same effect as once. Request errors are only
                retried on another host for idempotent statements. Defaults to True.

        Returns:
            ResultSet: The query result set.
        """
        if self.config.ENABLE_PREPARED_STATEMENT_CACHE:
            statement = await self.prepare(query.replace("%s", "?"))
            statement.is_idempotent = idempotent
            return await self.execute_prepared(statement, params)
        return await self.execute(query, params)

    @override
    async def execute_prepared(
        self,
        statement: PreparedStatement,
        params: dict[str, Any] | tuple[Any, ...] | list[Any] | None = None,
    ) -> ResultSet:
        """Execute a prepared statement asynchronously.

        Args:
            statement (PreparedStatement): The prepared statement object.
            params (dict[str, Any] | tuple[Any, ...] | list[Any] | None): Parameters to bind to the statement.

        Returns:
            ResultSet: The query result set.
        """
        session = await self.get_session()
        try:
            future = session.execute_async(statement, params) if params else session.execute_async(statement)
            result = await self._await_future(future)
        except (DriverException, NoHostAvailable, RequestValidationException) as e:
            self._handle_scylladb_exception(e, "execute_prepared")
            raise
        else:
            return result

    @override
    async def create_keyspace(self, keyspace: str, replication_factor: int | None = None) -> None:
        """Create a keyspace asynchronously.

        Args:
            keyspace (str): The name of the keyspace to create.
            replication_factor (int | None): Replicas per datacenter (``NetworkTopologyStrategy``) or in total
                (``SimpleStrategy``). When None, the configured ``REPLICATION_CONFIG`` is used, or 1 for
                ``SimpleStrategy``.
        """
        query = self._build_create_keyspace_query(self.config, keyspace, replication_factor)
        try:
            await self.execute(query)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "create_keyspace")
            raise

    @override
    async def drop_keyspace(self, keyspace: str) -> None:
        """Drop a keyspace asynchronously.

        Args:
            keyspace (str): The name of the keyspace to drop.
        """
        keyspace = self._validate_cql_identifier(keyspace, "keyspace")
        query = f"DROP KEYSPACE IF EXISTS {keyspace}"
        try:
            await self.execute(query)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "drop_keyspace")
            raise

    @override
    async def use_keyspace(self, keyspace: str) -> None:
        """Switch to a different keyspace context asynchronously.

        Args:
            keyspace (str): The name of the keyspace to use.
        """
        session = await self.get_session()
        try:
            keyspace = self._validate_cql_identifier(keyspace, "keyspace")
            await asyncio.to_thread(session.set_keyspace, keyspace)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "use_keyspace")
            raise

    @override
    async def create_table(self, table_schema: str) -> None:
        """Create a table asynchronously.

        Args:
            table_schema (str): The complete CREATE TABLE CQL statement.
        """
        try:
            await self.execute(table_schema)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "create_table")
            raise

    @override
    async def drop_table(self, table: str) -> None:
        """Drop a table asynchronously.

        Args:
            table (str): The name of the table to drop.
        """
        table = self._validate_cql_identifier(table, "table")
        query = f"DROP TABLE IF EXISTS {table}"
        try:
            await self.execute(query)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "drop_table")
            raise

    @override
    async def insert(
        self,
        table: str,
        data: dict[str, Any],
        ttl: int | None = None,
        if_not_exists: bool = False,
    ) -> None:
        """Insert data into a table asynchronously.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs representing column names and values.
            ttl (int | None): Time to live in seconds. If None, data persists indefinitely.
            if_not_exists (bool): If True, use lightweight transaction (INSERT ... IF NOT EXISTS).
                              This prevents errors on duplicate primary keys but is slow
        """
        table = self._validate_cql_identifier(table, "table")
        validated_columns = self._validate_cql_identifiers(list(data.keys()), "columns")
        columns = ", ".join(validated_columns)
        placeholders = ", ".join(["%s" for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"  # nosec B608

        if if_not_exists:
            query += " IF NOT EXISTS"

        if ttl is not None:
            query += f" USING TTL {self._validate_non_negative_int(ttl, 'ttl')}"

        try:
            await self._execute_dml(query, tuple(data.values()), idempotent=not if_not_exists)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "insert")
            raise

    @override
    async def select(
        self,
        table: str,
        columns: list[str] | None = None,
        conditions: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[Any]:
        """Select data from a table asynchronously.

        Args:
            table (str): The name of the table.
            columns (list[str] | None): List of columns to select. If None, selects all (*).
            conditions (dict[str, Any] | None): WHERE clause conditions as key-value pairs.
            limit (int | None): Maximum number of rows to return. If None, returns every matching row, which can be
                large; pass a limit on big tables.

        Returns:
            list[Any]: List of result rows.
        """
        table = self._validate_cql_identifier(table, "table")
        cols = ", ".join(self._validate_cql_identifiers(columns, "columns")) if columns else "*"
        query = f"SELECT {cols} FROM {table}"  # nosec B608

        params = None
        if conditions:
            condition_keys = self._validate_cql_identifiers(list(conditions.keys()), "conditions")
            where_clause = " AND ".join([f"{key} = %s" for key in condition_keys])
            query += f" WHERE {where_clause}"
            params = tuple(conditions.values())

        if limit is not None:
            query += f" LIMIT {self._validate_positive_int(limit, 'limit')}"

        try:
            result = await self._execute_dml(query, params)
            return list(result)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "select")
            raise

    @override
    async def update(
        self,
        table: str,
        data: dict[str, Any],
        conditions: dict[str, Any],
        ttl: int | None = None,
    ) -> None:
        """Update data in a table asynchronously.

        Args:
            table (str): The name of the table.
            data (dict[str, Any]): Key-value pairs for SET clause.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.
            ttl (int | None): Time to live in seconds. If None, data persists indefinitely.
        """
        table = self._validate_cql_identifier(table, "table")
        set_keys = self._validate_cql_identifiers(list(data.keys()), "data")
        condition_keys = self._validate_cql_identifiers(list(conditions.keys()), "conditions")
        set_clause = ", ".join([f"{key} = %s" for key in set_keys])
        where_clause = " AND ".join([f"{key} = %s" for key in condition_keys])
        query = f"UPDATE {table}"

        if ttl is not None:
            query += f" USING TTL {self._validate_non_negative_int(ttl, 'ttl')}"

        query += f" SET {set_clause} WHERE {where_clause}"

        # Combine params: SET values first, then WHERE values
        params = tuple(data.values()) + tuple(conditions.values())

        try:
            await self._execute_dml(query, params)
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "update")
            raise

    @override
    async def delete(self, table: str, conditions: dict[str, Any]) -> None:
        """Delete data from a table asynchronously.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.
        """
        table = self._validate_cql_identifier(table, "table")
        condition_keys = self._validate_cql_identifiers(list(conditions.keys()), "conditions")
        where_clause = " AND ".join([f"{key} = %s" for key in condition_keys])
        query = f"DELETE FROM {table} WHERE {where_clause}"  # nosec B608

        try:
            await self._execute_dml(query, tuple(conditions.values()))
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "delete")
            raise

    @override
    async def batch_execute(
        self,
        statements: list[BatchItem],
        batch_type: Literal["LOGGED", "UNLOGGED", "COUNTER"] = "LOGGED",
    ) -> None:
        """Execute multiple CQL statements in a batch asynchronously.

        Args:
            statements (list[BatchItem]): CQL strings, or ``(statement, params)`` pairs where the statement is a CQL
                string with ``%s`` placeholders or a prepared statement.
            batch_type (Literal["LOGGED", "UNLOGGED", "COUNTER"]): ``LOGGED`` (default) is atomic across partitions
                but costs a batch log; use ``UNLOGGED`` for statements on one partition and ``COUNTER`` for counters.
        """
        session = await self.get_session()

        try:
            batch = self._build_batch(statements, batch_type, self._get_consistency_level())

            future = session.execute_async(batch)
            await self._await_future(future)
        except (DriverException, NoHostAvailable, RequestValidationException) as e:
            self._handle_scylladb_exception(e, "batch_execute")
            raise

    @override
    async def get_session(self) -> Session:
        """Get the current session object asynchronously.

        Returns:
            Session: The active session object.
        """
        # Session is from cassandra.cluster, properly typed
        return self._session

    @override
    async def is_connected(self) -> bool:
        """Check if the adapter is connected to ScyllaDB cluster.

        Returns:
            bool: True if connected, False otherwise.
        """
        return self._session is not None and not self._session.is_shutdown

    async def close(self) -> None:
        """Close the connection and clean up resources asynchronously.

        This method should be called when the adapter is no longer needed
        to properly release resources.
        """
        try:
            if hasattr(self, "_session") and self._session is not None:
                await asyncio.to_thread(self._session.shutdown)
            if hasattr(self, "_cluster") and self._cluster is not None:
                await asyncio.to_thread(self._cluster.shutdown)
        except Exception as e:  # noqa: BLE001  # cleanup/health soft-fail; unconstrained errors
            # Ignore errors during cleanup, but log them
            logger.debug("Error during async ScyllaDB adapter cleanup: %s", e)

    def __del__(self) -> None:
        """Destructor to ensure resources are cleaned up."""
        try:
            if hasattr(self, "_session") and self._session is not None:
                self._session.shutdown()
            if hasattr(self, "_cluster") and self._cluster is not None:
                self._cluster.shutdown()
        except Exception as e:  # noqa: BLE001  # cleanup/health soft-fail; unconstrained errors
            # Ignore errors during destructor cleanup
            logger.debug("Error in async ScyllaDB adapter destructor: %s", e)

    @override
    async def health_check(self) -> dict[str, Any]:
        """Perform a health check on the ScyllaDB connection.

        Returns:
            dict[str, Any]: Health check result with status, latency_ms, and optional error.
        """
        if not await self.is_connected():
            return {
                "status": "unhealthy",
                "latency_ms": 0.0,
                "error": _HEALTH_CHECK_FAILED,
            }

        try:
            start_time = time.time()
            session = await self.get_session()
            future = session.execute_async("SELECT now() FROM system.local", timeout=self.config.HEALTH_CHECK_TIMEOUT)
            await self._await_future(future)
            latency_ms = (time.time() - start_time) * 1000
        except Exception:  # cleanup/health soft-fail; unconstrained errors
            logger.warning("ScyllaDB health check failed", exc_info=True)
            return {
                "status": "unhealthy",
                "latency_ms": 0.0,
                "error": _HEALTH_CHECK_FAILED,
            }
        else:
            return {
                "status": "healthy",
                "latency_ms": latency_ms,
                "error": None,
            }

    @override
    async def count(self, table: str, conditions: dict[str, Any] | None = None) -> int:
        """Count rows in a table asynchronously.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any] | None): WHERE clause conditions as key-value pairs.

        Returns:
            int: The number of rows matching the conditions.
        """
        table = self._validate_cql_identifier(table, "table")
        query = f"SELECT COUNT(*) FROM {table}"  # nosec B608

        params = None
        if conditions:
            condition_keys = self._validate_cql_identifiers(list(conditions.keys()), "conditions")
            where_clause = " AND ".join([f"{key} = %s" for key in condition_keys])
            query += f" WHERE {where_clause} ALLOW FILTERING"
            params = tuple(conditions.values())

        try:
            result = await self._execute_dml(query, params)
            row = result.one()
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "count")
            raise
        else:
            return row.count if row else 0

    @override
    async def exists(self, table: str, conditions: dict[str, Any]) -> bool:
        """Check if a row exists in a table asynchronously.

        Args:
            table (str): The name of the table.
            conditions (dict[str, Any]): WHERE clause conditions as key-value pairs.

        Returns:
            bool: True if at least one row exists, False otherwise.
        """
        table = self._validate_cql_identifier(table, "table")
        condition_keys = self._validate_cql_identifiers(list(conditions.keys()), "conditions")
        where_clause = " AND ".join([f"{key} = %s" for key in condition_keys])
        # COUNT(*) ... LIMIT 1 still aggregates every match; selecting one key column stops at the first row
        query = f"SELECT {condition_keys[0]} FROM {table} WHERE {where_clause} LIMIT 1 ALLOW FILTERING"  # nosec B608

        try:
            result = await self._execute_dml(query, tuple(conditions.values()))
            row = result.one()
        except (DriverException, NoHostAvailable) as e:
            self._handle_scylladb_exception(e, "exists")
            raise
        else:
            return row is not None

    @override
    async def get_pool_stats(self) -> dict[str, Any]:
        """Get connection pool statistics asynchronously.

        Returns:
            dict[str, Any]: Pool statistics including open connections, in-flight requests, etc.
        """
        if not self.config.ENABLE_CONNECTION_POOL_MONITORING:
            return {
                "monitoring_enabled": False,
                "message": "Connection pool monitoring is disabled",
            }

        stats: dict[str, Any] = {"monitoring_enabled": True}

        try:
            session = await self.get_session()

            # Get pool state for each host (driver returns {host: state})
            hosts_stats: list[_HostPoolStat] = []
            for host, host_pool in session.get_pool_state().items():
                if host_pool:
                    hosts_stats.append(
                        {
                            "host": str(host),
                            "open_connections": int(host_pool.get("open_count", 0) or 0),
                            "in_flight_queries": int(host_pool.get("in_flight", 0) or 0),
                        },
                    )

            stats["hosts"] = hosts_stats
            stats["total_hosts"] = len(hosts_stats)
            stats["total_open_connections"] = sum(h["open_connections"] for h in hosts_stats)
            stats["total_in_flight_queries"] = sum(h["in_flight_queries"] for h in hosts_stats)

        except Exception:  # cleanup/health soft-fail; unconstrained errors
            logger.warning("ScyllaDB pool statistics unavailable", exc_info=True)
            stats["error"] = _POOL_STATS_FAILED

        return stats
