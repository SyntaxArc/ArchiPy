"""Actor type enumeration."""

from enum import StrEnum


class ActorType(StrEnum):
    """Kind of party named in an RFC 8693 ``act`` claim.

    Attributes:
        USER: A user acting on behalf of the subject (e.g. an admin impersonating them).
        CLIENT: An OAuth client acting on behalf of the subject (e.g. a delegated application or AI agent).
    """

    USER = "USER"
    CLIENT = "CLIENT"
