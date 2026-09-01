"""Environment type enumeration for ArchiPy configs."""

import enum
from enum import StrEnum
from logging import DEBUG, INFO, WARNING


class EnvironmentType(StrEnum):
    """Enum representing different application environments.

    This enum defines the available environment types for an application
    and provides helper properties to check the current environment.

    Attributes:
        PRODUCTION: Production environment
        BETA: Beta testing environment (human testing)
        ALPHA: Alpha testing environment (human testing)
        TEST: Automated testing environment
        DEV: Development environment
        LOCAL: Local development environment

    Examples:
        >>> from archipy.configs.environment_type import EnvironmentType
        >>>
        >>> # Setting environment in configuration
        >>> env = EnvironmentType.DEV
        >>>
        >>> # Checking environment type
        >>> if env.is_production:
        ...     print("Running in production mode")
        >>> elif env.is_dev:
        ...     print("Running in development mode")
        >>>
        >>> # Getting appropriate log level
        >>> log_level = env.log_level
        >>> print(f"Log level: {log_level}")
    """

    PRODUCTION = "PRODUCTION"
    BETA = "BETA"  # human test
    ALPHA = "ALPHA"  # human test
    TEST = "TEST"  # automatic test
    DEV = "DEV"
    LOCAL = "LOCAL"

    @enum.property
    def is_local(self) -> bool:
        """Check if the environment is LOCAL.

        Returns:
            bool: True if environment is LOCAL, False otherwise.
        """
        return self == self.LOCAL

    @enum.property
    def is_dev(self) -> bool:
        """Check if the environment is DEV.

        Returns:
            bool: True if environment is DEV, False otherwise.
        """
        return self == self.DEV

    @enum.property
    def is_test(self) -> bool:
        """Check if the environment is a testing environment.

        Returns:
            bool: True if environment is BETA, ALPHA, or TEST, False otherwise.
        """
        return self in (self.BETA, self.ALPHA, self.TEST)

    @enum.property
    def is_production(self) -> bool:
        """Check if the environment is a production environment.

        This returns True for PRODUCTION and False for all other environments.

        Returns:
            bool: True if not a test, dev, or local environment, False otherwise.
        """
        return not self.is_test and not self.is_dev and not self.is_local

    @enum.property
    def log_level(self) -> int:
        """Get the appropriate logging level for this environment.

        Returns:
            int: WARNING for production, INFO for test environments,
                DEBUG for development and local environments.
        """
        if self.is_production:
            return WARNING
        if self.is_test:
            return INFO
        return DEBUG
