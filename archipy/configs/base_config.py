"""Base configuration system for ArchiPy applications.

Settings are loaded from multiple sources, applied in the following priority
order (highest priority first):

1. Docker/K8s secret files (`file_secret_settings`)
2. HashiCorp Vault KV v2 secrets (when `VAULT__ENABLED=true`)
3. `pyproject.toml` `[tool.configs]` section
4. `configs.toml` or other specified TOML file
5. OS-level environment variables
6. `.env` file
7. Default class field values / init settings
"""

import importlib
import os
from typing import TypeVar

from pydantic.fields import ModelPrivateAttr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from archipy.configs.config_template import (
    AuthConfig,
    DatetimeConfig,
    ElasticsearchConfig,
    EmailConfig,
    FastAPIConfig,
    FileConfig,
    GrpcConfig,
    GrpcRateLimitConfig,
    KafkaConfig,
    KeycloakConfig,
    MinioConfig,
    MySQLSQLAlchemyConfig,
    OpentelemetryConfig,
    PaginationConfig,
    ParsianShaparakConfig,
    PostgresSQLAlchemyConfig,
    PydanticAIConfig,
    RedisConfig,
    SamanShaparakConfig,
    ScyllaDBConfig,
    SQLAlchemyConfig,
    SQLiteSQLAlchemyConfig,
    StarRocksSQLAlchemyConfig,
    TemporalConfig,
    VaultConfig,
)
from archipy.configs.environment_type import EnvironmentType
from archipy.models.errors import ConfigurationError
from archipy.models.runtime_settings import register_settings_provider
from archipy.models.types import LanguageType

R = TypeVar("R", bound="BaseConfig")  # Runtime Config


class BaseConfig[R](BaseSettings):
    """Base configuration class for ArchiPy applications.

    This class provides a comprehensive configuration system that loads settings
    from multiple sources in the following priority order:

    1. Docker/K8s secret files (`file_secret_settings`)
    2. HashiCorp Vault KV v2 secrets (when `VAULT__ENABLED=true`)
    3. pyproject.toml [tool.configs] section
    4. configs.toml or other specified TOML files
    5. OS-level environment variables
    6. Environment variables (.env file)
    7. Default class field values / init settings

    The class implements the Singleton pattern via a global config instance that
    can be set once and accessed throughout the application.

    Attributes:
        APP_NAME (str | None): Application identity; synced into nested configs in ``customize()``
        AUTH (AuthConfig): Authentication and security settings
        DATETIME (DatetimeConfig): Date/time handling configuration
        ELASTIC (ElasticsearchConfig): Elasticsearch configuration
        EMAIL (EmailConfig): Email service configuration
        ENVIRONMENT (EnvironmentType): Application environment (dev, test, prod)
        FASTAPI (FastAPIConfig): FastAPI framework settings
        FILE (FileConfig): File handling configuration
        GRPC (GrpcConfig): gRPC service configuration
        GRPC_RATE_LIMIT (GrpcRateLimitConfig): gRPC server rate limiting settings
        KAFKA (KafkaConfig): Kafka integration configuration
        KEYCLOAK (KeycloakConfig): Keycloak integration configuration
        LANGUAGE (LanguageType): Application default language
        MINIO (MinioConfig): MinIO object storage configuration
        MYSQL_SQLALCHEMY (MySQLSQLAlchemyConfig): MySQL SQLAlchemy configuration
        OTEL (OpentelemetryConfig): OpenTelemetry observability configuration
        PARSIAN_SHAPARAK (ParsianShaparakConfig): Parsian Shaparak payment gateway configuration
        POSTGRES_SQLALCHEMY (PostgresSQLAlchemyConfig): PostgreSQL SQLAlchemy configuration
        PYDANTIC_AI (PydanticAIConfig): Pydantic AI instrumentation configuration
        REDIS (RedisConfig): Redis cache configuration
        SAMAN_SHAPARAK (SamanShaparakConfig): Saman Shaparak (SEP) payment gateway configuration
        SCYLLADB (ScyllaDBConfig): ScyllaDB/Cassandra database configuration
        SQLALCHEMY (SQLAlchemyConfig): Database ORM configuration
        SQLITE_SQLALCHEMY (SqliteSQLAlchemyConfig): SQLite SQLAlchemy configuration
        STARROCKS_SQLALCHEMY (StarrocksSQLAlchemyConfig): Starrocks SQLAlchemy configuration
        TEMPORAL (TemporalConfig): Temporal workflow orchestration configuration
        VAULT (VaultConfig): HashiCorp Vault connection and secrets settings

    Examples:
        >>> from archipy.configs.base_config import BaseConfig
        >>>
        >>> class MyAppConfig(BaseConfig):
        ...     # Override defaults (APP_NAME is a built-in field)
        ...     APP_NAME = "My Application"
        ...     DEBUG = True
        ...
        ...     # Custom configuration
        ...     FEATURE_FLAGS = {"new_ui": True, "advanced_search": False}
        >>>
        >>> # Set as global configuration
        >>> config = MyAppConfig()
        >>> BaseConfig.set_global(config)
        >>>
        >>> # Access from anywhere
        >>> from archipy.configs.base_config import BaseConfig
        >>> current_config = BaseConfig.global_config()
        >>> app_name = current_config.APP_NAME  # "My Application"
    """

    model_config = SettingsConfigDict(
        case_sensitive=True,
        pyproject_toml_depth=3,
        env_file=".env",
        pyproject_toml_table_header=("tool", "configs"),
        extra="ignore",
        env_nested_delimiter="__",
        env_ignore_empty=True,
    )

    __global_config: BaseConfig | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize the settings sources priority order.

        This method defines the priority order for configuration sources.

        Args:
            settings_cls: The settings class
            init_settings: Settings from initialization values
            env_settings: Settings from environment variables
            dotenv_settings: Settings from .env file
            file_secret_settings: Settings from secret files

        Returns:
            A tuple of configuration sources in priority order

        Raises:
            ConfigurationError: If Vault is enabled but the ``vault`` extra is not installed.
        """
        sources: list[PydanticBaseSettingsSource] = [file_secret_settings]

        # Import Vault settings source only when explicitly enabled — avoids loading
        # hvac on cold start for apps that ship with the vault extra but leave it off.
        vault_enabled = os.environ.get("VAULT__ENABLED", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        if vault_enabled:
            try:
                vault_module = importlib.import_module("archipy.configs.vault_settings_source")
            except ImportError as e:
                raise ConfigurationError(
                    operation="vault_import",
                    reason='hvac is not installed; install with uv add "archipy[vault]"',
                ) from e
            sources.append(vault_module.VaultSettingsSource(settings_cls))

        sources.extend(
            [
                PyprojectTomlConfigSettingsSource(settings_cls),
                TomlConfigSettingsSource(settings_cls),
                env_settings,
                dotenv_settings,
                init_settings,
            ],
        )
        return tuple(sources)

    APP_NAME: str | None = None
    AUTH: AuthConfig = AuthConfig()
    DATETIME: DatetimeConfig = DatetimeConfig()
    ELASTIC: ElasticsearchConfig = ElasticsearchConfig()
    EMAIL: EmailConfig = EmailConfig()
    ENVIRONMENT: EnvironmentType = EnvironmentType.LOCAL
    FASTAPI: FastAPIConfig = FastAPIConfig()
    FILE: FileConfig = FileConfig()
    GRPC: GrpcConfig = GrpcConfig()
    GRPC_RATE_LIMIT: GrpcRateLimitConfig = GrpcRateLimitConfig()
    KAFKA: KafkaConfig = KafkaConfig()
    KEYCLOAK: KeycloakConfig = KeycloakConfig()
    MINIO: MinioConfig = MinioConfig()
    OTEL: OpentelemetryConfig = OpentelemetryConfig()
    PAGINATION: PaginationConfig = PaginationConfig()
    PARSIAN_SHAPARAK: ParsianShaparakConfig = ParsianShaparakConfig()
    SAMAN_SHAPARAK: SamanShaparakConfig = SamanShaparakConfig()
    PYDANTIC_AI: PydanticAIConfig = PydanticAIConfig()
    REDIS: RedisConfig = RedisConfig()
    SCYLLADB: ScyllaDBConfig = ScyllaDBConfig()
    SQLALCHEMY: SQLAlchemyConfig = SQLAlchemyConfig()
    STARROCKS_SQLALCHEMY: StarRocksSQLAlchemyConfig = StarRocksSQLAlchemyConfig()
    POSTGRES_SQLALCHEMY: PostgresSQLAlchemyConfig = PostgresSQLAlchemyConfig()
    MYSQL_SQLALCHEMY: MySQLSQLAlchemyConfig = MySQLSQLAlchemyConfig()
    SQLITE_SQLALCHEMY: SQLiteSQLAlchemyConfig = SQLiteSQLAlchemyConfig()
    TEMPORAL: TemporalConfig = TemporalConfig()
    VAULT: VaultConfig = VaultConfig()
    LANGUAGE: LanguageType = LanguageType.FA

    def customize(self) -> None:
        """Customize configuration after loading.

        This method can be overridden in subclasses to perform
        custom configuration modifications after loading settings.
        It is called automatically by `set_global()`.

        When ``APP_NAME`` is set, unset or placeholder nested identity fields are
        filled: ``OTEL.SERVICE_NAME``, ``FASTAPI.PROJECT_NAME``, ``AUTH.JWT_ISSUER``,
        and ``TEMPORAL.CLIENT_IDENTITY``. Explicit nested values always win.

        An unset ``COUNT_THRESHOLD`` of the SQLAlchemy configs is filled with ``PAGINATION.MAX_ITEMS``.

        Examples:
            >>> class MyAppConfig(BaseConfig):
            ...     def customize(self) -> None:
            ...         super().customize()
            ...         self.REDIS.MASTER_HOST = "redis.internal"
            >>> config = MyAppConfig()
            >>> BaseConfig.set_global(config)  # calls customize() automatically
        """
        if self.OTEL.ENVIRONMENT is None:
            self.OTEL.ENVIRONMENT = self.ENVIRONMENT

        if self.APP_NAME:
            if self.OTEL.SERVICE_NAME is None:
                self.OTEL.SERVICE_NAME = self.APP_NAME
            if self.FASTAPI.PROJECT_NAME == "project_name":
                self.FASTAPI.PROJECT_NAME = self.APP_NAME
            if self.AUTH.JWT_ISSUER == "your-app-name":
                self.AUTH.JWT_ISSUER = self.APP_NAME
            if self.TEMPORAL.CLIENT_IDENTITY is None:
                self.TEMPORAL.CLIENT_IDENTITY = self.APP_NAME

        for sqlalchemy_config in (
            self.SQLALCHEMY,
            self.POSTGRES_SQLALCHEMY,
            self.MYSQL_SQLALCHEMY,
            self.SQLITE_SQLALCHEMY,
            self.STARROCKS_SQLALCHEMY,
        ):
            if sqlalchemy_config.COUNT_THRESHOLD is None:
                sqlalchemy_config.COUNT_THRESHOLD = self.PAGINATION.MAX_ITEMS

    @classmethod
    def global_config(cls) -> BaseConfig:
        """Retrieves the global configuration instance.

        Returns:
            BaseConfig: The global configuration instance.

        Raises:
            AssertionError: If the global config hasn't been set with
                BaseConfig.set_global()

        Examples:
            >>> config = BaseConfig.global_config()
            >>> redis_host = config.REDIS.MASTER_HOST
        """
        config_not_set_error = "You should set global configs with BaseConfig.set_global(MyConfig())"
        global_config = cls.__global_config
        # Pydantic wraps unset private attrs in ModelPrivateAttr; ``is None`` alone never fires.
        if global_config is None or isinstance(global_config, ModelPrivateAttr):
            raise AssertionError(config_not_set_error)
        return global_config

    @classmethod
    def set_global(cls, config: BaseConfig) -> None:
        """Sets the global configuration instance.

        This method should be called once during application initialization
        to set the global configuration that will be used throughout the app.

        Args:
            config (BaseConfig): The configuration instance to use globally.

        Examples:
            >>> my_config = MyAppConfig(BaseConfig)
            >>> BaseConfig.set_global(my_config)
        """
        if hasattr(config, "customize") and callable(config.customize):
            config.customize()
        cls.__global_config = config


register_settings_provider(BaseConfig.global_config)
