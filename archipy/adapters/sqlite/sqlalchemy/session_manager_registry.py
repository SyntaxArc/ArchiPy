from typing import TYPE_CHECKING

from archipy.adapters.base.sqlalchemy.session_manager_registry import SessionManagerRegistry
from archipy.helpers.metaclasses.singleton import Singleton
from archipy.models.errors import DatabaseConnectionError

if TYPE_CHECKING:
    from archipy.adapters.base.sqlalchemy.session_manager_ports import AsyncSessionManagerPort, SessionManagerPort


class SQLiteSessionManagerRegistry(SessionManagerRegistry, metaclass=Singleton):
    """Registry for SQLite SQLAlchemy session managers.

    This registry provides a centralized access point for both synchronous and
    asynchronous SQLite session managers, implementing the Service Locator pattern.
    It lazily initializes the appropriate session manager when first requested.

    The registry maintains singleton instances of:
    - A synchronous session manager (SQLiteSQLAlchemySessionManager)
    - An asynchronous session manager (AsyncSQLiteSQLAlchemySessionManager)
    """

    @classmethod
    def get_sync_manager(cls) -> SessionManagerPort:
        """Get the synchronous SQLite session manager instance.

        Lazily initializes a default SQLiteSQLAlchemySessionManager if none has been set.

        Returns:
            SessionManagerPort: The registered synchronous session manager

        Raises:
            DatabaseConnectionError: If there's an error initializing the session manager
        """
        if cls._sync_instance is None:
            try:
                from archipy.adapters.sqlite.sqlalchemy.session_managers import SQLiteSQLAlchemySessionManager

                cls._sync_instance = SQLiteSQLAlchemySessionManager()
            except Exception as e:
                raise DatabaseConnectionError(
                    database="sqlite",
                ) from e
        return cls._sync_instance

    @classmethod
    def set_sync_manager(cls, manager: SessionManagerPort) -> None:
        """Register a synchronous session manager.

        Args:
            manager: The session manager to register
        """
        cls._sync_instance = manager

    @classmethod
    def get_async_manager(cls) -> AsyncSessionManagerPort:
        """Get the asynchronous SQLite session manager instance.

        Lazily initializes a default AsyncSQLiteSQLAlchemySessionManager if none has been set.

        Returns:
            AsyncSessionManagerPort: The registered asynchronous session manager

        Raises:
            DatabaseConnectionError: If there's an error initializing the session manager
        """
        if cls._async_instance is None:
            try:
                from archipy.adapters.sqlite.sqlalchemy.session_managers import AsyncSQLiteSQLAlchemySessionManager

                cls._async_instance = AsyncSQLiteSQLAlchemySessionManager()
            except Exception as e:
                raise DatabaseConnectionError(
                    database="sqlite",
                ) from e
        return cls._async_instance

    @classmethod
    def set_async_manager(cls, manager: AsyncSessionManagerPort) -> None:
        """Register an asynchronous session manager.

        Args:
            manager: The async session manager to register
        """
        cls._async_instance = manager

    @classmethod
    def reset(cls) -> None:
        """Reset the registry to its initial state.

        This method clears both registered managers, useful for testing.
        """
        cls._sync_instance = None
        cls._async_instance = None
