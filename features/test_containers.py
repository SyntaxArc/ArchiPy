"""Container manager for test containers"""

import logging
from urllib.parse import urlparse

from testcontainers.redis import RedisContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.keycloak import KeycloakContainer
from testcontainers.kafka import KafkaContainer
from testcontainers.minio import MinioContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from archipy.adapters.postgres.sqlalchemy.adapters import PostgresSQLAlchemyAdapter
from archipy.helpers.metaclasses.singleton import Singleton
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import RedisConfig, MinioConfig, KafkaConfig, ElasticsearchConfig, PostgresSQLAlchemyConfig, KeycloakConfig
from archipy.models.entities import BaseEntity

logger = logging.getLogger(__name__)


class ContainerManager:
    """Registry for managing all test containers."""

    _containers = {}
    _started = False

    @classmethod
    def register(cls, name: str):
        """Decorator to register containers."""
        def decorator(container_class):
            cls._containers[name] = container_class
            return container_class

        return decorator

    @classmethod
    def get_container(cls, name: str, **kwargs):
        """Get a container instance by name."""
        if name not in cls._containers:
            raise KeyError(f"Container '{name}' not found. Available: {list(cls._containers.keys())}")

        container_class = cls._containers[name]

        return container_class(**kwargs)

    @classmethod
    def start_all(cls):
        """Start all registered containers."""
        if cls._started:
            return

        for name, container_class in cls._containers.items():
            logger.info(f"Starting {name} container...")
            container = container_class()
            container.start()

        cls._started = True
        logger.info("All test containers started")

    @classmethod
    def stop_all(cls):
        """Stop all registered containers."""
        if not cls._started:
            return

        for name, container_class in cls._containers.items():
            logger.info(f"Stopping {name} container...")
            container = container_class()
            container.stop()

        cls._started = False
        logger.info("All test containers stopped")

    @classmethod
    def reset(cls):
        """Reset the registry state."""
        cls.stop_all()
        cls._containers.clear()
        cls._started = False

    @classmethod
    def get_all_containers(cls):
        """Get all container instances."""
        return {name: cls.get_container(name) for name in cls._containers}


@ContainerManager.register("redis")
class RedisTestContainer(metaclass=Singleton, thread_safe=True):
    def __init__(self, config: RedisConfig | None = None, image: str | None = None) -> None:
        self.name = "redis"
        self.config = config or BaseConfig.global_config().REDIS
        self.image = image or BaseConfig.global_config().REDIS__IMAGE
        self._is_running: bool = False

        # Container properties
        self.host: str | None = None
        self.port: int = self.config.PORT
        self.database: int = self.config.DATABASE
        self.password: str | None = self.config.PASSWORD

        # Set up the container
        self._container = RedisContainer(self.image)
        if self.config.PASSWORD:
            self._container.with_env("REDIS_PASSWORD", self.config.PASSWORD)

        self._container.with_bind_ports(self.config.PORT, 6379)

    def start(self) -> RedisContainer:
        """Start the Redis container."""
        if self._is_running:
            return self._container

        self._container.start()
        self._is_running = True

        self.host = self._container.get_container_host_ip()

        logger.info("Redis container started on %s:%s", self.host, self.port)

        return self._container

    def stop(self) -> None:
        """Stop the Redis container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False

        # Reset container properties
        self.host = None
        self.port = None


        logger.info("Redis container stopped")


@ContainerManager.register("postgres")
class PostgresTestContainer(metaclass=Singleton, thread_safe=True):
    def __init__(self) -> None:
        self.postgres_config = BaseConfig.global_config().POSTGRES_SQLALCHEMY
        self.image = BaseConfig.global_config().POSTGRES_IMAGE
        self._is_running: bool = False

        # Set up the container
        self._container = PostgresContainer(
            image=self.image,
            dbname=self.postgres_config.DATABASE,
            username=self.postgres_config.USERNAME,
            password=self.postgres_config.PASSWORD,
        )
        # set static port
        # default port of container is 5432 if you want to create it on other port you can replace 5432 with your port
        self._container.with_bind_ports(5432, self.postgres_config.PORT)

    def start(self) -> PostgresContainer:
        """Start the PostgreSQL container."""
        if self._is_running:
            return self._container
        try:
            self._container.start()
            self._is_running = True

            adapter = PostgresSQLAlchemyAdapter(orm_config=self.postgres_config)
            BaseEntity.metadata.create_all(adapter.session_manager.engine)

            logger.info("PostgreSQL container started on %s:%s", self.postgres_config.HOST, self.postgres_config.PORT)

            return self._container
        except Exception as e:
            logger.error(f"Failed to start PostgreSQL container: {e}")
            self._container.stop()
            raise

    def stop(self) -> None:
        """Stop the PostgreSQL container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        logger.info("PostgreSQL container stopped")


@ContainerManager.register("keycloak")
class KeycloakTestContainer(metaclass=Singleton, thread_safe=True):
    def __init__(self, config: KeycloakConfig | None = None, image: str | None = None) -> None:
        self.name = "keycloak"
        self.config = config or BaseConfig.global_config().KEYCLOAK
        self.image = image or BaseConfig.global_config().KEYCLOAK__IMAGE
        self._is_running: bool = False

        # Container properties
        self.port: int | None = None
        self.admin_username: str | None = self.config.ADMIN_USERNAME
        self.admin_password: str | None = self.config.ADMIN_PASSWORD
        self.realm: str = self.config.REALM_NAME

        # Parse Port From Server URL
        parsed_url = urlparse(self.config.SERVER_URL)
        self.port = parsed_url.port or 8080

        # Use config values or fallback to defaults for test containers
        username = self.admin_username or "admin"
        password = self.admin_password or "admin"

        # Set up the container
        self._container = KeycloakContainer(
            image=self.image,
            username=username,
            password=password,
        )
        self._container.with_bind_ports(self.port, 8080)

    def start(self) -> KeycloakContainer:
        """Start the Keycloak container."""
        if self._is_running:
            return self._container

        self._container.start()
        self._is_running = True

        # Set container properties
        self.host = self._container.get_container_host_ip()

        logger.info("Keycloak container started on %s:%s", self.host, self.port)

        return self._container

    def stop(self) -> None:
        """Stop the Keycloak container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False

        # Reset container properties
        self.host = None
        self.port = None

        logger.info("Keycloak container stopped")


@ContainerManager.register("elasticsearch")
class ElasticsearchTestContainer(metaclass=Singleton, thread_safe=True):
    def __init__(self, config: ElasticsearchConfig | None = None, image: str | None = None) -> None:
        self.name = "elasticsearch"
        self.config = config or BaseConfig.global_config().ELASTIC
        self.image = image or BaseConfig.global_config().ELASTIC__IMAGE
        self._is_running: bool = False

        # Container properties
        self.port: int | None = None
        self.username: str | None = self.config.HTTP_USER_NAME
        self.password: str | None = self.config.HTTP_PASSWORD.get_secret_value() if self.config.HTTP_PASSWORD else None
        self.cluster_name: str = "test-cluster"

        # Parse Port From Server URL
        parsed_url = urlparse(self.config.HOSTS[0])
        self.port = parsed_url.port or 9200

        # Set up the container
        self._container = DockerContainer(self.image)
        self._container.with_env("discovery.type", "single-node")
        self._container.with_env("xpack.security.enabled", "true")
        if self.password:
            self._container.with_env("ELASTIC_PASSWORD", self.password)
        self._container.with_env("cluster.name", self.cluster_name)
        self._container.with_bind_ports(self.port, 9200)

    def start(self) -> DockerContainer:
        """Start the Elasticsearch container."""
        if self._is_running:
            return self._container

        # Start the container
        self._container.start()

        # Wait for Elasticsearch to be ready
        wait_for_logs(self._container, "started", timeout=60)

        self._is_running = True
        self.host = self._container.get_container_host_ip()

        return self._container

    def stop(self) -> None:
        """Stop the Elasticsearch container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False

        # Reset container properties
        self.host = None
        self.port = None

        logger.info("Elasticsearch container stopped")


@ContainerManager.register("kafka")
class KafkaTestContainer(metaclass=Singleton, thread_safe=True):
    def __init__(self, config: KafkaConfig | None = None, image: str | None = None) -> None:
        self.name = "kafka"
        self.config = config or BaseConfig.global_config().KAFKA
        self.image = image or BaseConfig.global_config().KAFKA__IMAGE
        self._is_running: bool = False

        # Container Properties
        self.host: str | None = None
        self.port: int | None = None
        self.bootstrap_servers: str | None = None

        # Parse Port From Server URL
        _, port = self.config.BROKERS_LIST[0].split(":")
        self.port = int(port) if port else 9092

        # Set up the container
        self._container = KafkaContainer(image=self.image)
        self._container.with_bind_ports(self.port, 9092)

    def start(self) -> KafkaContainer:
        """Start the Kafka container."""
        if self._is_running:
            return self._container

        self._container.start()
        self._is_running = True

        # Set container properties from running container
        self.host = self._container.get_container_host_ip()
        self.bootstrap_servers = self._container.get_bootstrap_server()
        self.config.BROKERS_LIST = [self.bootstrap_servers]

        logger.info("Kafka container started on %s:%s", self.host, self.port)
        logger.info("Bootstrap servers: %s", self.bootstrap_servers)

        return self._container

    def stop(self) -> None:
        """Stop the Kafka container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False

        # Reset container properties
        self.host = None
        self.port = None
        self.bootstrap_servers = None

        logger.info("Kafka container stopped")


@ContainerManager.register("minio")
class MinioTestContainer(metaclass=Singleton, thread_safe=True):
    def __init__(self, config: MinioConfig | None = None, image: str | None = None) -> None:
        self.name = "minio"
        self.config = config or BaseConfig.global_config().MINIO
        self.image = image or BaseConfig.global_config().MINIO__IMAGE
        self._container: MinioContainer | None = None
        self._is_running: bool = False

        # Container properties
        self.host: str | None = None
        self.port: int | None = None
        self.access_key = self.config.ACCESS_KEY or "minioadmin"
        self.secret_key = self.config.SECRET_KEY or "minioadmin"

        # Parse Port From Server URL
        host, port = self.config.ENDPOINT.split(":")
        self.port = int(port) if port else 9000

        # Set up the container
        self._container = MinioContainer(
            image=self.image,
            access_key=self.access_key,
            secret_key=self.secret_key,
        )
        self._container.with_bind_ports(self.port, 9000)

    def start(self) -> MinioContainer:
        """Start the MinIO container."""
        if self._is_running:
            return self._container

        try:
            self._container.start()
            self._is_running = True

            # Update container properties
            self.host = self._container.get_container_host_ip()

            logger.info("MinIO container started on %s:%s", self.host, self.port)
            return self._container

        except Exception as e:
            logger.error(f"Failed to start MinIO container: {e}")
            raise

    def stop(self) -> None:
        """Stop the MinIO container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False

        # Reset container properties
        self.host = None
        self.port = None

        logger.info("MinIO container stopped")
