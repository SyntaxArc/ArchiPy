from typing import TYPE_CHECKING, ClassVar

from archipy.models.errors import (
    InternalError,
    InvalidArgumentError,
)

if TYPE_CHECKING:
    from archipy.adapters.base.sqlalchemy.session_manager_ports import AsyncSessionManagerPort, SessionManagerPort


class SessionManagerRegistry:
    """Registry for SQLAlchemy session managers.

    This registry provides a centralized access point for both synchronous and
    asynchronous session managers, implementing the Service Locator pattern.

    Subclasses should override get_sync_manager and get_async_manager to provide
    concrete session managers, or use set_sync_manager and set_async_manager to
    register managers manually.

    Examples:
        >>> from archipy.adapters.postgres.sqlalchemy.session_manager_registry import PostgresSessionManagerRegistry
        >>> sync_manager = PostgresSessionManagerRegistry.get_sync_manager()
        >>> session = sync_manager.get_session()
    """

    _sync_instance: ClassVar[SessionManagerPort | None] = None
    _async_instance: ClassVar[AsyncSessionManagerPort | None] = None

    @classmethod
    def get_sync_manager(cls) -> SessionManagerPort:
        """Get the synchronous session manager instance.

        Returns:
            SessionManagerPort: The registered synchronous session manager

        Raises:
            InternalError: If no synchronous session manager is set
            DatabaseConnectionError: If there's an error initializing the session manager
        """
        if cls._sync_instance is None:
            raise InternalError("Synchronous session manager not initialized")
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
            raise InvalidArgumentError("Session manager cannot be None")
        from archipy.adapters.base.sqlalchemy.session_manager_ports import SessionManagerPort

        if not isinstance(manager, SessionManagerPort):
            raise InvalidArgumentError(f"Manager must implement SessionManagerPort, got {type(manager).__name__}")
        cls._sync_instance = manager

    @classmethod
    def get_async_manager(cls) -> AsyncSessionManagerPort:
        """Get the asynchronous session manager instance.

        Returns:
            AsyncSessionManagerPort: The registered asynchronous session manager

        Raises:
            InternalError: If no asynchronous session manager is set
            DatabaseConnectionError: If there's an error initializing the session manager
        """
        if cls._async_instance is None:
            raise InternalError("Asynchronous session manager not initialized")
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
            raise InvalidArgumentError("Session manager cannot be None")
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
