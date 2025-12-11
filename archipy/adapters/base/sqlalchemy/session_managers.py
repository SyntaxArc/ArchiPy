from abc import abstractmethod
from asyncio import current_task
from typing import TypeVar, override

from sqlalchemy import URL, Engine, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, scoped_session, sessionmaker

from archipy.adapters.base.sqlalchemy.session_manager_ports import AsyncSessionManagerPort, SessionManagerPort
from archipy.configs.config_template import SQLAlchemyConfig
from archipy.models.errors import (
    DatabaseConfigurationError,
    DatabaseConnectionError,
    DatabaseError,
    InvalidArgumentError,
)

# Generic type variable for SQLAlchemy configurations
ConfigT = TypeVar("ConfigT", bound=SQLAlchemyConfig)


class BaseSQLAlchemySessionManager[ConfigT: SQLAlchemyConfig](SessionManagerPort):
    """Base synchronous SQLAlchemy session manager.

    Implements the SessionManagerPort interface to provide session management for
    synchronous database operations. Database-specific session managers should inherit
    from this class and implement database-specific engine creation.

    Args:
        orm_config: SQLAlchemy configuration. Must match the expected config type for the database.
    """

    def __init__(self, orm_config: ConfigT) -> None:
        """Initialize the base session manager.

        Args:
            orm_config: SQLAlchemy configuration.

        Raises:
            InvalidArgumentError: If the configuration type is invalid.
            DatabaseConnectionError: If there's an error creating the database connection.
            DatabaseConfigurationError: If there's an error in the database configuration.
        """
        if not isinstance(orm_config, self._expected_config_type()):
            raise InvalidArgumentError(
                f"Expected {self._expected_config_type().__name__}, got {type(orm_config).__name__}",
            )
        try:
            self.engine = self._create_engine(orm_config)
            self._session_generator = self._get_session_generator()
        except SQLAlchemyError as e:
            if "configuration" in str(e).lower():
                raise DatabaseConfigurationError(
                    database=self._get_database_name(),
                ) from e
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e

    @abstractmethod
    def _expected_config_type(self) -> type[SQLAlchemyConfig]:
        """Return the expected configuration type for the database.

        Returns:
            The SQLAlchemy configuration class expected by this session manager.
        """

    @abstractmethod
    def _get_database_name(self) -> str:
        """Return the name of the database being used.

        Returns:
            str: The name of the database (e.g., 'postgresql', 'sqlite', 'starrocks').
        """

    @abstractmethod
    def _create_url(self, configs: ConfigT) -> URL:
        """Create a database connection URL.

        Args:
            configs: Database-specific configuration.

        Returns:
            A SQLAlchemy URL object for the database.

        Raises:
            DatabaseConnectionError: If there's an error creating the URL.
        """

    def _create_engine(self, configs: ConfigT) -> Engine:
        """Create a SQLAlchemy engine with common configuration.

        Args:
            configs: SQLAlchemy configuration.

        Returns:
            A configured SQLAlchemy engine.

        Raises:
            DatabaseConnectionError: If there's an error creating the engine.
            DatabaseConfigurationError: If there's an error in the database configuration.
        """
        try:
            url = self._create_url(configs)
            return create_engine(
                url,
                isolation_level=configs.ISOLATION_LEVEL,
                echo=configs.ECHO,
                echo_pool=configs.ECHO_POOL,
                enable_from_linting=configs.ENABLE_FROM_LINTING,
                hide_parameters=configs.HIDE_PARAMETERS,
                pool_pre_ping=configs.POOL_PRE_PING,
                pool_size=configs.POOL_SIZE,
                pool_recycle=configs.POOL_RECYCLE_SECONDS,
                pool_reset_on_return=configs.POOL_RESET_ON_RETURN,
                pool_timeout=configs.POOL_TIMEOUT,
                pool_use_lifo=configs.POOL_USE_LIFO,
                query_cache_size=configs.QUERY_CACHE_SIZE,
                max_overflow=configs.POOL_MAX_OVERFLOW,
                connect_args=self._get_connect_args(),
            )
        except SQLAlchemyError as e:
            if "configuration" in str(e).lower():
                raise DatabaseConfigurationError(
                    database=self._get_database_name(),
                ) from e
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e

    def _get_connect_args(self) -> dict:
        """Return additional connection arguments for the engine.

        Returns:
            A dictionary of connection arguments (default is empty).
        """
        return {}

    def _get_session_generator(self) -> scoped_session:
        """Create a scoped session factory for synchronous sessions.

        Returns:
            A scoped_session instance used by `get_session` to provide thread-safe sessions.

        Raises:
            DatabaseConfigurationError: If there's an error in the database configuration.
        """
        try:
            session_maker = sessionmaker(self.engine)
            return scoped_session(session_maker)
        except SQLAlchemyError as e:
            if "configuration" in str(e).lower():
                raise DatabaseConfigurationError(
                    database=self._get_database_name(),
                ) from e
            raise DatabaseError(
                database=self._get_database_name(),
            ) from e

    @override
    def get_session(self) -> Session:
        """Retrieve a thread-safe SQLAlchemy session.

        Returns:
            Session: A SQLAlchemy session instance for database operations.

        Raises:
            DatabaseConnectionError: If there's an error creating the session.
            DatabaseConfigurationError: If there's an error in the database configuration.
        """
        try:
            return self._session_generator()
        except SQLAlchemyError as e:
            if "configuration" in str(e).lower():
                raise DatabaseConfigurationError(
                    database=self._get_database_name(),
                ) from e
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e

    @override
    def remove_session(self) -> None:
        """Remove the current session from the registry.

        Cleans up the session to prevent resource leaks, typically called at the end
        of a request.

        Raises:
            DatabaseConnectionError: If there's an error removing the session.
            DatabaseConfigurationError: If there's an error in the database configuration.
        """
        try:
            self._session_generator.remove()
        except SQLAlchemyError as e:
            if "configuration" in str(e).lower():
                raise DatabaseConfigurationError(
                    database=self._get_database_name(),
                ) from e
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e


class AsyncBaseSQLAlchemySessionManager[ConfigT: SQLAlchemyConfig](AsyncSessionManagerPort):
    """Base asynchronous SQLAlchemy session manager.

    Implements the AsyncSessionManagerPort interface to provide session management for
    asynchronous database operations. Database-specific session managers should inherit
    from this class and implement database-specific async engine creation.

    Args:
        orm_config: SQLAlchemy configuration. Must match the expected config type for the database.
    """

    def __init__(self, orm_config: ConfigT) -> None:
        """Initialize the base async session manager.

        Args:
            orm_config: SQLAlchemy configuration.

        Raises:
            InvalidArgumentError: If the configuration type is invalid.
            DatabaseConnectionError: If there's an error creating the database connection.
            DatabaseConfigurationError: If there's an error in the database configuration.
        """
        if not isinstance(orm_config, self._expected_config_type()):
            raise InvalidArgumentError(
                f"Expected {self._expected_config_type().__name__}, got {type(orm_config).__name__}",
            )
        try:
            self.engine = self._create_async_engine(orm_config)
            self._session_generator = self._get_session_generator()
        except SQLAlchemyError as e:
            if "configuration" in str(e).lower():
                raise DatabaseConfigurationError(
                    database=self._get_database_name(),
                ) from e
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e

    @abstractmethod
    def _expected_config_type(self) -> type[SQLAlchemyConfig]:
        """Return the expected configuration type for the database.

        Returns:
            The SQLAlchemy configuration class expected by this session manager.
        """

    @abstractmethod
    def _get_database_name(self) -> str:
        """Return the name of the database being used.

        Returns:
            str: The name of the database (e.g., 'postgresql', 'sqlite', 'starrocks').
        """

    @abstractmethod
    def _create_url(self, configs: ConfigT) -> URL:
        """Create a database connection URL.

        Args:
            configs: Database-specific configuration.

        Returns:
            A SQLAlchemy URL object for the database.

        Raises:
            DatabaseConnectionError: If there's an error creating the URL.
        """

    def _create_async_engine(self, configs: ConfigT) -> AsyncEngine:
        """Create an async SQLAlchemy engine with common configuration.

        Args:
            configs: SQLAlchemy configuration.

        Returns:
            A configured async SQLAlchemy engine.

        Raises:
            DatabaseConnectionError: If there's an error creating the engine.
            DatabaseConfigurationError: If there's an error in the database configuration.
        """
        try:
            url = self._create_url(configs)
            return create_async_engine(
                url,
                isolation_level=configs.ISOLATION_LEVEL,
                echo=configs.ECHO,
                echo_pool=configs.ECHO_POOL,
                enable_from_linting=configs.ENABLE_FROM_LINTING,
                hide_parameters=configs.HIDE_PARAMETERS,
                pool_pre_ping=configs.POOL_PRE_PING,
                pool_size=configs.POOL_SIZE,
                pool_recycle=configs.POOL_RECYCLE_SECONDS,
                pool_reset_on_return=configs.POOL_RESET_ON_RETURN,
                pool_timeout=configs.POOL_TIMEOUT,
                pool_use_lifo=configs.POOL_USE_LIFO,
                query_cache_size=configs.QUERY_CACHE_SIZE,
                max_overflow=configs.POOL_MAX_OVERFLOW,
                connect_args=self._get_connect_args(),
            )
        except SQLAlchemyError as e:
            if "configuration" in str(e).lower():
                raise DatabaseConfigurationError(
                    database=self._get_database_name(),
                ) from e
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e

    def _get_connect_args(self) -> dict:
        """Return additional connection arguments for the engine.

        Returns:
            A dictionary of connection arguments (default is empty).
        """
        return {}

    def _get_session_generator(self) -> async_scoped_session:
        """Create an async scoped session factory.

        Returns:
            An async_scoped_session instance used by `get_session` to provide task-safe sessions.

        Raises:
            DatabaseConfigurationError: If there's an error in the database configuration.
        """
        try:
            session_maker = async_sessionmaker(self.engine)
            return async_scoped_session(session_maker, scopefunc=current_task)
        except SQLAlchemyError as e:
            if "configuration" in str(e).lower():
                raise DatabaseConfigurationError(
                    database=self._get_database_name(),
                ) from e
            raise DatabaseError(
                database=self._get_database_name(),
            ) from e

    @override
    def get_session(self) -> AsyncSession:
        """Retrieve a task-safe async SQLAlchemy session.

        Returns:
            AsyncSession: An async SQLAlchemy session instance for database operations.

        Raises:
            DatabaseConnectionError: If there's an error creating the session.
            DatabaseConfigurationError: If there's an error in the database configuration.
        """
        try:
            return self._session_generator()
        except SQLAlchemyError as e:
            if "configuration" in str(e).lower():
                raise DatabaseConfigurationError(
                    database=self._get_database_name(),
                ) from e
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e

    @override
    async def remove_session(self) -> None:
        """Remove the current session from the registry.

        Cleans up the session to prevent resource leaks, typically called at the end
        of a request.

        Raises:
            DatabaseConnectionError: If there's an error removing the session.
            DatabaseConfigurationError: If there's an error in the database configuration.
        """
        try:
            await self._session_generator.remove()
        except SQLAlchemyError as e:
            if "configuration" in str(e).lower():
                raise DatabaseConfigurationError(
                    database=self._get_database_name(),
                ) from e
            raise DatabaseConnectionError(
                database=self._get_database_name(),
            ) from e
