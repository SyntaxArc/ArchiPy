"""Port interfaces for SQLAlchemy session managers."""

from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import Session


class SessionManagerPort:
    """Interface for SQLAlchemy session management operations.

    This interface defines the contract for session management adapters,
    providing methods for retrieving and managing database sessions
    in a synchronous context.

    Implementing classes must provide mechanisms to:
    1. Retrieve a properly configured SQLAlchemy session
    2. Release/remove sessions when they're no longer needed
    """

    @abstractmethod
    def get_session(self) -> Session:
        """Retrieve a SQLAlchemy session.

        This method provides a database session that can be used for
        querying, creating, updating, and deleting data.

        Returns:
            Session: A SQLAlchemy session object

        Examples:
            >>> session = session_manager.get_session()
            >>> results = session.query(User).all()
        """
        raise NotImplementedError

    @abstractmethod
    def remove_session(self) -> None:
        """Remove the current session from the registry.

        This method should be called to clean up the session when it's
        no longer needed, helping to prevent resource leaks and ensure
        proper session management.
        """
        raise NotImplementedError


class AsyncSessionManagerPort:
    """Interface for asynchronous SQLAlchemy session management operations.

    This interface defines the contract for asynchronous session management adapters,
    providing methods for retrieving and managing database sessions in an
    asynchronous context using SQLAlchemy's async capabilities.

    Implementing classes must provide mechanisms to:
    1. Retrieve a properly configured asynchronous SQLAlchemy session
    2. Release/remove sessions asynchronously when they're no longer needed
    """

    @abstractmethod
    def get_session(self) -> AsyncSession:
        """Retrieve an asynchronous SQLAlchemy session.

        This method provides an async database session that can be used for
        asynchronous querying, creating, updating, and deleting data.

        Returns:
            AsyncSession: An asynchronous SQLAlchemy session object
        """
        raise NotImplementedError

    @abstractmethod
    async def remove_session(self) -> None:
        """Asynchronously remove the current session from the registry.

        This method should be called to clean up the session when it's
        no longer needed, helping to prevent resource leaks and ensure
        proper session management in async contexts.
        """
        raise NotImplementedError
