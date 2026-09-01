"""Registry for PostgreSQL SQLAlchemy session managers."""

from archipy.adapters.base.sqlalchemy.session_manager_ports import AsyncSessionManagerPort, SessionManagerPort
from archipy.adapters.base.sqlalchemy.session_manager_registry import SessionManagerRegistry
from archipy.adapters.postgres.sqlalchemy.session_managers import (
    AsyncPostgresSQlAlchemySessionManager,
    PostgresSQlAlchemySessionManager,
)
from archipy.helpers.metaclasses.singleton import Singleton
from archipy.models.errors import DatabaseConnectionError, InvalidArgumentError, InvalidEntityTypeError


class PostgresSessionManagerRegistry(SessionManagerRegistry, metaclass=Singleton):
    """Registry for PostgreSQL SQLAlchemy session managers.

    This registry provides a centralized access point for both synchronous and
    asynchronous PostgreSQL session managers, implementing the Service Locator pattern.
    It lazily initializes the appropriate session manager when first requested.

    The registry maintains singleton instances of:
    - A synchronous session manager (PostgresSQlAlchemySessionManager)
    - An asynchronous session manager (AsyncPostgresSQlAlchemySessionManager)
    """

    @classmethod
    def get_sync_manager(cls) -> SessionManagerPort:
        """Get the synchronous PostgreSQL session manager instance.

        Lazily initializes a default PostgresSQlAlchemySessionManager if none has been set.

        Returns:
            SessionManagerPort: The registered synchronous session manager

        Raises:
            DatabaseConnectionError: If there's an error initializing the session manager
        """
        if cls._sync_instance is None:
            try:
                cls._sync_instance = PostgresSQlAlchemySessionManager()
            except Exception as e:
                raise DatabaseConnectionError(
                    database="postgresql",
                ) from e
        return cls._sync_instance

    @classmethod
    def set_sync_manager(cls, manager: SessionManagerPort) -> None:
        """Set a custom synchronous session manager.

        Args:
            manager: An instance implementing SessionManagerPort

        Raises:
            InvalidArgumentError: If the manager is None
            InvalidEntityTypeError: If the manager doesn't implement SessionManagerPort
        """
        if manager is None:
            raise InvalidArgumentError(argument_name="postgres_session_manager")

        if not isinstance(manager, SessionManagerPort):
            raise InvalidEntityTypeError(
                expected_type="SessionManagerPort",
                actual_type=type(manager).__name__,
            )
        cls._sync_instance = manager

    @classmethod
    def get_async_manager(cls) -> AsyncSessionManagerPort:
        """Get the asynchronous PostgreSQL session manager instance.

        Lazily initializes a default AsyncPostgresSQlAlchemySessionManager if none has been set.

        Returns:
            AsyncSessionManagerPort: The registered asynchronous session manager

        Raises:
            DatabaseConnectionError: If there's an error initializing the session manager
        """
        if cls._async_instance is None:
            try:
                cls._async_instance = AsyncPostgresSQlAlchemySessionManager()
            except Exception as e:
                raise DatabaseConnectionError(
                    database="postgresql",
                ) from e
        return cls._async_instance

    @classmethod
    def set_async_manager(cls, manager: AsyncSessionManagerPort) -> None:
        """Set a custom asynchronous session manager.

        Args:
            manager: An instance implementing AsyncSessionManagerPort

        Raises:
            InvalidArgumentError: If the manager is None
            InvalidEntityTypeError: If the manager doesn't implement AsyncSessionManagerPort
        """
        if manager is None:
            raise InvalidArgumentError(argument_name="postgres_async_session_manager")

        if not isinstance(manager, AsyncSessionManagerPort):
            raise InvalidEntityTypeError(
                expected_type="AsyncSessionManagerPort",
                actual_type=type(manager).__name__,
            )
        cls._async_instance = manager

    @classmethod
    def reset(cls) -> None:
        """Reset the registry to its initial state.

        This method clears both registered managers, useful for testing.
        """
        cls._sync_instance = None
        cls._async_instance = None
