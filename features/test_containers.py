"""Container manager for test containers"""

import logging

from testcontainers.redis import RedisContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.keycloak import KeycloakContainer
from testcontainers.kafka import KafkaContainer
from testcontainers.minio import MinioContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from archipy.helpers.metaclasses.singleton import Singleton
from features.test_containers_config import test_config

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
    def get_container(cls, name: str):
        """Get a container instance by name."""
        if name not in cls._containers:
            raise KeyError(f"Container '{name}' not found. Available: {list(cls._containers.keys())}")

        container_class = cls._containers[name]

        return container_class()

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
    def __init__(self) -> None:
        self.name = "redis"
        self.image = test_config.REDIS_IMAGE
        self._container: RedisContainer | None = None
        self._is_running: bool = False

        # Container properties
        self.host: str | None = None
        self.port: int | None = None
        self.database: int = test_config.REDIS_DATABASE
        self.password: str | None = test_config.REDIS_PASSWORD

    def start(self) -> RedisContainer:
        if self._is_running:
            return self._container

        self._container = RedisContainer(self.image)
        self._container.start()
        self._is_running = True

        # Set container properties
        self.host = self._container.get_container_host_ip()
        self.port = self._container.get_exposed_port(test_config.REDIS_PORT)

        logger.info("Redis container started on %s:%s", self.host, self.port)

        return self._container

    def stop(self) -> None:
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
        self.name = "postgres"
        self.image = test_config.POSTGRES_IMAGE
        self._container: PostgresContainer | None = None
        self._is_running: bool = False

        # Container properties
        self.host: str | None = None
        self.port: int | None = None
        self.database: str = test_config.POSTGRES_DATABASE
        self.username: str = test_config.POSTGRES_USERNAME
        self.password: str = test_config.POSTGRES_PASSWORD

    def start(self) -> PostgresContainer:
        if self._is_running:
            return self._container

        self._container = PostgresContainer(
            image=self.image,
            dbname=test_config.POSTGRES_DATABASE,
            username=test_config.POSTGRES_USERNAME,
            password=test_config.POSTGRES_PASSWORD,
        )

        self._container.start()
        self._is_running = True

        # Set container properties
        self.host = self._container.get_container_host_ip()
        self.port = self._container.get_exposed_port(test_config.POSTGRES_PORT)

        logger.info("PostgreSQL container started on %s:%s", self.host, self.port)

        return self._container

    def stop(self) -> None:
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False

        # Reset container properties
        self.host = None
        self.port = None

        logger.info("PostgreSQL container stopped")


@ContainerManager.register("keycloak")
class KeycloakTestContainer(metaclass=Singleton, thread_safe=True):
    def __init__(self) -> None:
        self.name = "keycloak"
        self.image = test_config.KEYCLOAK_IMAGE
        self._container: KeycloakContainer | None = None
        self._is_running: bool = False

        # Container properties
        self.host: str | None = None
        self.port: int | None = None
        self.admin_username: str = test_config.KEYCLOAK_ADMIN_USERNAME
        self.admin_password: str = test_config.KEYCLOAK_ADMIN_PASSWORD
        self.realm: str = test_config.KEYCLOAK_REALM

    def start(self) -> KeycloakContainer:
        if self._is_running:
            return self._container

        self._container = KeycloakContainer(
            image=self.image,
            username=test_config.KEYCLOAK_ADMIN_USERNAME,
            password=test_config.KEYCLOAK_ADMIN_PASSWORD,
        )

        self._container.start()
        self._is_running = True

        # Set container properties
        self.host = self._container.get_container_host_ip()
        self.port = self._container.get_exposed_port(test_config.KEYCLOAK_PORT)

        logger.info("Keycloak container started on %s:%s", self.host, self.port)

        return self._container

    def stop(self) -> None:
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
    def __init__(self) -> None:
        self.name = "elasticsearch"
        self.image = test_config.ELASTICSEARCH_IMAGE
        self._container: DockerContainer | None = None
        self._is_running: bool = False

        # Container properties
        self.host: str | None = None
        self.port: int | None = None
        self.username: str = test_config.ELASTICSEARCH_USERNAME
        self.password: str = test_config.ELASTICSEARCH_PASSWORD
        self.cluster_name: str = test_config.ELASTICSEARCH_CLUSTER_NAME

    def start(self) -> DockerContainer:
        if self._is_running:
            return self._container

        self._container = DockerContainer(self.image)

        # Set environment variables
        self._container.with_env("discovery.type", "single-node")
        self._container.with_env("xpack.security.enabled", "true")
        self._container.with_env("ELASTIC_PASSWORD", self.password)
        self._container.with_env("cluster.name", self.cluster_name)

        # Expose ports
        self._container.with_exposed_ports(test_config.ELASTICSEARCH_PORT)

        # Start the container
        self._container.start()

        # Wait for Elasticsearch to be ready
        wait_for_logs(self._container, "started", timeout=60)

        self._is_running = True

        # Set container properties
        self.host = self._container.get_container_host_ip()
        self.port = self._container.get_exposed_port(test_config.ELASTICSEARCH_PORT)

        logger.info("Elasticsearch container started on %s:%s", self.host, self.port)

        return self._container

    def stop(self) -> None:
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
    def __init__(self) -> None:
        self.name = "kafka"
        self.image = test_config.KAFKA_IMAGE
        self._container: KafkaContainer | None = None
        self._is_running: bool = False

        # Container properties
        self.host: str | None = None
        self.port: int | None = None
        self.bootstrap_servers: str | None = None

    def start(self) -> KafkaContainer:
        if self._is_running:
            return self._container

        # Kafka container handles Zookeeper internally
        self._container = KafkaContainer(image=self.image)
        self._container.start()
        self._is_running = True

        # Set container properties
        self.host = self._container.get_container_host_ip()
        self.port = self._container.get_exposed_port(test_config.KAFKA_PORT)
        self.bootstrap_servers = self._container.get_bootstrap_server()

        logger.info("Kafka container started on %s:%s", self.host, self.port)
        logger.info("Bootstrap servers: %s", self.bootstrap_servers)

        return self._container

    def stop(self) -> None:
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
    def __init__(self) -> None:
        self.name = "minio"
        self.image = test_config.MINIO_IMAGE
        self._container: MinioContainer | None = None
        self._is_running: bool = False

        # Container properties
        self.host: str | None = None
        self.port: int | None = None
        self.access_key: str = test_config.MINIO_ACCESS_KEY
        self.secret_key: str = test_config.MINIO_SECRET_KEY

    def start(self) -> MinioContainer:
        if self._is_running:
            return self._container

        try:
            self._container = MinioContainer(
                image=self.image,
                port=self.port or test_config.MINIO_PORT,
                access_key=self.access_key,
                secret_key=self.secret_key,
            )
            self._container.start()

            # Update container properties
            self.host = self._container.get_container_host_ip()
            self.port = self._container.get_exposed_port(test_config.MINIO_PORT)
            self._is_running = True

            logger.info(f"MinIO container started on {self.host}:{self.port}")
            return self._container

        except Exception as e:
            logger.error(f"Failed to start MinIO container: {e}")
            raise

    def stop(self) -> None:
        if not self._is_running or not self._container:
            return

        try:
            self._container.stop()
            self._is_running = False
            self.host = None
            self.port = None
            logger.info("MinIO container stopped")
        except Exception as e:
            logger.error(f"Failed to stop MinIO container: {e}")
            raise
