from typing import Self, TypeVar, cast

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
    ElasticsearchAPMConfig,
    ElasticsearchConfig,
    EmailConfig,
    FastAPIConfig,
    FileConfig,
    GrpcConfig,
    KafkaConfig,
    KavenegarConfig,
    KeycloakConfig,
    MinioConfig,
    ParsianShaparakConfig,
    PostgresSQLAlchemyConfig,
    PrometheusConfig,
    RedisConfig,
    ScyllaDBConfig,
    SentryConfig,
    SQLAlchemyConfig,
    SQLiteSQLAlchemyConfig,
    StarRocksSQLAlchemyConfig,
    TemporalConfig,
)
from archipy.configs.environment_type import EnvironmentType
from archipy.models.types import LanguageType

"""

Priority :
            1. pypoject.toml [tool.configs]
            2. configs.toml or other toml file init
            3. .env file
            4. os level environment variable
            5. class field value
"""
R = TypeVar("R", bound="BaseConfig")  # Runtime Config


class BaseConfig[R](BaseSettings):
    """Base configuration class for ArchiPy applications.

    This class provides a comprehensive configuration system that loads settings
    from multiple sources in the following priority order:

    1. pyproject.toml [tool.configs] section
    2. configs.toml or other specified TOML files
    3. Environment variables (.env file)
    4. OS-level environment variables
    5. Default class field values

    The class implements the Singleton pattern via a global config instance that
    can be set once and accessed throughout the application.

    Attributes:
        AUTH (AuthConfig): Authentication and security settings
        DATETIME (DatetimeConfig): Date/time handling configuration
        ELASTIC (ElasticsearchConfig): Elasticsearch configuration
        ELASTIC_APM (ElasticsearchAPMConfig): Elasticsearch APM configuration
        EMAIL (EmailConfig): Email service configuration
        ENVIRONMENT (EnvironmentType): Application environment (dev, test, prod)
        FASTAPI (FastAPIConfig): FastAPI framework settings
        FILE (FileConfig): File handling configuration
        GRPC (GrpcConfig): gRPC service configuration
        KAFKA (KafkaConfig): Kafka integration configuration
        KAVENEGAR (KavenegarConfig): Kavenegar SMS service configuration
        KEYCLOAK (KeycloakConfig): Keycloak integration configuration
        MINIO (MinioConfig): MinIO object storage configuration
        PARSIAN_SHAPARAK (ParsianShaparakConfig): Parsian Shaparak payment gateway configuration
        POSTGRES_SQLALCHEMY (PostgresSQLAlchemyConfig): PostgreSQL SQLAlchemy configuration
        PROMETHEUS (PrometheusConfig): Prometheus metrics configuration
        REDIS (RedisConfig): Redis cache configuration
        SCYLLADB (ScyllaDBConfig): ScyllaDB/Cassandra database configuration
        SENTRY (SentryConfig): Sentry error tracking configuration
        SQLALCHEMY (SQLAlchemyConfig): Database ORM configuration
        SQLITE_SQLALCHEMY (SqliteSQLAlchemyConfig): SQLite SQLAlchemy configuration
        STARROCKS_SQLALCHEMY (StarrocksSQLAlchemyConfig): Starrocks SQLAlchemy configuration
        TEMPORAL (TemporalConfig): Temporal workflow orchestration configuration

    Examples:
        >>> from archipy.configs.base_config import BaseConfig
        >>>
        >>> class MyAppConfig(BaseConfig):
        ...     # Override defaults
        ...     APP_NAME = "My Application"
        ...     DEBUG = True
        ...
        ...     # Custom configuration
        ...     FEATURE_FLAGS = {
        ...         "new_ui": True,
        ...         "advanced_search": False
        ...     }
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

    __global_config: Self | None = None

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
        """
        return (
            file_secret_settings,
            PyprojectTomlConfigSettingsSource(settings_cls),
            TomlConfigSettingsSource(settings_cls),
            env_settings,
            dotenv_settings,
            init_settings,
        )

    AUTH: AuthConfig = AuthConfig()
    DATETIME: DatetimeConfig = DatetimeConfig()
    ELASTIC: ElasticsearchConfig = ElasticsearchConfig()
    ELASTIC_APM: ElasticsearchAPMConfig = ElasticsearchAPMConfig()
    EMAIL: EmailConfig = EmailConfig()
    ENVIRONMENT: EnvironmentType = EnvironmentType.LOCAL
    FASTAPI: FastAPIConfig = FastAPIConfig()
    FILE: FileConfig = FileConfig()
    GRPC: GrpcConfig = GrpcConfig()
    KAFKA: KafkaConfig = KafkaConfig()
    KAVENEGAR: KavenegarConfig = KavenegarConfig()
    KEYCLOAK: KeycloakConfig = KeycloakConfig()
    MINIO: MinioConfig = MinioConfig()
    PARSIAN_SHAPARAK: ParsianShaparakConfig = ParsianShaparakConfig()
    PROMETHEUS: PrometheusConfig = PrometheusConfig()
    REDIS: RedisConfig = RedisConfig()
    SCYLLADB: ScyllaDBConfig = ScyllaDBConfig()
    SENTRY: SentryConfig = SentryConfig()
    SQLALCHEMY: SQLAlchemyConfig = SQLAlchemyConfig()
    STARROCKS_SQLALCHEMY: StarRocksSQLAlchemyConfig = StarRocksSQLAlchemyConfig()
    POSTGRES_SQLALCHEMY: PostgresSQLAlchemyConfig = PostgresSQLAlchemyConfig()
    SQLITE_SQLALCHEMY: SQLiteSQLAlchemyConfig = SQLiteSQLAlchemyConfig()
    TEMPORAL: TemporalConfig = TemporalConfig()
    LANGUAGE: LanguageType = LanguageType.FA

    def customize(self) -> None:
        """Customize configuration after loading.

        This method can be overridden in subclasses to perform
        custom configuration modifications after loading settings.
        """
        self.ELASTIC_APM.ENVIRONMENT = self.ENVIRONMENT

    @classmethod
    def global_config(cls) -> Self:
        """Retrieves the global configuration instance.

        Returns:
            Self: The global configuration instance.

        Raises:
            AssertionError: If the global config hasn't been set with
                BaseConfig.set_global()

        Examples:
            >>> config = BaseConfig.global_config()
            >>> redis_host = config.REDIS.MASTER_HOST
        """
        config_not_set_error = "You should set global configs with BaseConfig.set_global(MyConfig())"
        if cls.__global_config is None:
            raise AssertionError(config_not_set_error)
        return cls.__global_config

    @classmethod
    def set_global(cls, config: R) -> None:
        """Sets the global configuration instance.

        This method should be called once during application initialization
        to set the global configuration that will be used throughout the app.

        Args:
            config (R): The configuration instance to use globally.

        Examples:
            >>> my_config = MyAppConfig(BaseConfig)
            >>> BaseConfig.set_global(my_config)
        """
        if hasattr(config, "customize") and callable(config.customize):
            config.customize()
        cls.__global_config = cast(Self, config)
