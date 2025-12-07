from typing import TYPE_CHECKING

from archipy.adapters.base.sqlalchemy.session_manager_registry import SessionManagerRegistry
from archipy.helpers.metaclasses.singleton import Singleton
from archipy.models.errors import DatabaseConnectionError, InvalidArgumentError

if TYPE_CHECKING:
    from archipy.adapters.base.sqlalchemy.session_manager_ports import AsyncSessionManagerPort, SessionManagerPort


class StarRocksSessionManagerRegistry(SessionManagerRegistry, metaclass=Singleton):
    """Registry for StarRocks SQLAlchemy session managers.

    This registry provides a centralized access point for both synchronous and
    asynchronous StarRocks session managers, implementing the Service Locator pattern.
    It lazily initializes the appropriate session manager when first requested.

    The registry maintains singleton instances of:
    - A synchronous session manager (StarRocksSQlAlchemySessionManager)
    - An asynchronous session manager (AsyncStarRocksSQlAlchemySessionManager)
    """

    @classmethod
    def get_sync_manager(cls) -> SessionManagerPort:
        """Get the synchronous StarRocks session manager instance.

        Lazily initializes a default StarRocksSQlAlchemySessionManager if none has been set.

        Returns:
            SessionManagerPort: The registered synchronous session manager

        Raises:
            DatabaseConnectionError: If there's an error initializing the session manager
        """
        if cls._sync_instance is None:
            try:
                from archipy.adapters.starrocks.sqlalchemy.session_managers import StarRocksSQlAlchemySessionManager

                cls._sync_instance = StarRocksSQlAlchemySessionManager()
            except Exception as e:
                raise DatabaseConnectionError(
                    database="starrocks",
                ) from e
        return cls._sync_instance

    @classmethod
    def set_sync_manager(cls, manager: SessionManagerPort) -> None:
        """Set a custom synchronous session manager.

        Args:
            manager: An instance implementing SessionManagerPort

        Raises:
            InvalidArgumentError: If the manager is None or doesn't implement SessionManagerPort
        """
        if manager is None:
            raise InvalidArgumentError("StarRocks session manager cannot be None")
        from archipy.adapters.base.sqlalchemy.session_manager_ports import SessionManagerPort

        if not isinstance(manager, SessionManagerPort):
            raise InvalidArgumentError(f"Manager must implement SessionManagerPort, got {type(manager).__name__}")
        cls._sync_instance = manager

    @classmethod
    def get_async_manager(cls) -> AsyncSessionManagerPort:
        """Get the asynchronous StarRocks session manager instance.

        Lazily initializes a default AsyncStarRocksSQlAlchemySessionManager if none has been set.

        Returns:
            AsyncSessionManagerPort: The registered asynchronous session manager

        Raises:
            DatabaseConnectionError: If there's an error initializing the session manager
        """
        if cls._async_instance is None:
            try:
                from archipy.adapters.starrocks.sqlalchemy.session_managers import (
                    AsyncStarRocksSQlAlchemySessionManager,
                )

                cls._async_instance = AsyncStarRocksSQlAlchemySessionManager()
            except Exception as e:
                raise DatabaseConnectionError(
                    database="starrocks",
                ) from e
        return cls._async_instance

    @classmethod
    def set_async_manager(cls, manager: AsyncSessionManagerPort) -> None:
        """Set a custom asynchronous session manager.

        Args:
            manager: An instance implementing AsyncSessionManagerPort

        Raises:
            InvalidArgumentError: If the manager is None or doesn't implement AsyncSessionManagerPort
        """
        if manager is None:
            raise InvalidArgumentError("StarRocks async session manager cannot be None")
        from archipy.adapters.base.sqlalchemy.session_manager_ports import AsyncSessionManagerPort

        if not isinstance(manager, AsyncSessionManagerPort):
            raise InvalidArgumentError(f"Manager must implement AsyncSessionManagerPort, got {type(manager).__name__}")
        cls._async_instance = manager

    @classmethod
    def reset(cls) -> None:
        """Reset the registry to its initial state.

        This method clears both registered managers, useful for testing.
        """
        cls._sync_instance = None
        cls._async_instance = None
