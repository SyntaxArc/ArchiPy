"""Container manager for test containers"""

import logging

from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.kafka import KafkaContainer
from testcontainers.keycloak import KeycloakContainer
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import (
    ElasticsearchConfig,
    KafkaConfig,
    KeycloakConfig,
    MinioConfig,
    PostgresSQLAlchemyConfig,
    RedisConfig,
    ScyllaDBConfig,
)
from archipy.helpers.metaclasses.singleton import Singleton

logger = logging.getLogger(__name__)

# Mapping of feature tags to container names
TAG_CONTAINER_MAP: dict[str, str] = {
    "needs-postgres": "postgres",
    "needs-kafka": "kafka",
    "needs-elasticsearch": "elasticsearch",
    "needs-minio": "minio",
    "needs-keycloak": "keycloak",
    "needs-redis": "redis",
    "needs-scylladb": "scylladb",
}


class ContainerManager:
    """Registry for managing all test containers."""

    _containers = {}
    _container_instances = {}
    _started = False
    _started_containers: set[str] = set()

    @classmethod
    def register(cls, name: str):
        """Decorator to register containers."""

        def decorator(container_class):
            cls._containers[name] = container_class
            return container_class

        return decorator

    @classmethod
    def get_container(cls, name: str, **kwargs):
        """Get a container instance by name.

        If the container is not started, it will be started lazily.
        """
        if name not in cls._containers:
            raise KeyError(f"Container '{name}' not found. Available: {list(cls._containers.keys())}")

        # Return stored instance if available (Singleton pattern ensures same instance)
        if name in cls._container_instances:
            instance = cls._container_instances[name]
            # Start container if not already running (lazy startup)
            if name not in cls._started_containers:
                instance.start()
                cls._started_containers.add(name)
            return instance

        # Create new instance if not stored yet
        container_class = cls._containers[name]
        instance = container_class(**kwargs)
        cls._container_instances[name] = instance
        # Start container lazily
        instance.start()
        cls._started_containers.add(name)
        return instance

    @classmethod
    def start_all(cls):
        """Start all registered containers."""
        if cls._started:
            return

        for name, container_class in cls._containers.items():
            logger.info(f"Starting {name} container...")
            container = container_class()
            cls._container_instances[name] = container
            container.start()
            cls._started_containers.add(name)

        cls._started = True
        logger.info("All test containers started")

    @classmethod
    def start_containers(cls, container_names: list[str]):
        """Start specific containers by name.

        Args:
            container_names: List of container names to start
        """
        for name in container_names:
            if name not in cls._containers:
                logger.warning(f"Container '{name}' not found. Available: {list(cls._containers.keys())}")
                continue

            if name in cls._started_containers:
                logger.debug(f"Container '{name}' already started, skipping")
                continue

            logger.info(f"Starting {name} container...")
            # get_container will start the container and add it to _started_containers
            cls.get_container(name)

        logger.info(f"Started containers: {sorted(cls._started_containers)}")

    @classmethod
    def extract_containers_from_tags(cls, tags: list[str]) -> set[str]:
        """Extract container names from feature/scenario tags.

        Args:
            tags: List of tag strings (e.g., ["needs-postgres", "needs-kafka"])

        Returns:
            Set of container names that should be started
        """
        containers: set[str] = set()
        for tag in tags:
            # Remove @ prefix if present
            tag_name = tag.lstrip("@")
            if tag_name in TAG_CONTAINER_MAP:
                container_name = TAG_CONTAINER_MAP[tag_name]
                containers.add(container_name)
                logger.debug(f"Tag '{tag}' maps to container '{container_name}'")
            else:
                # Only log warning for tags that look like container tags but aren't mapped
                if tag_name.startswith("needs-"):
                    logger.warning(f"Unknown container tag '{tag}'. Available tags: {list(TAG_CONTAINER_MAP.keys())}")

        return containers

    @classmethod
    def stop_all(cls):
        """Stop all started containers."""
        if not cls._started_containers:
            return

        for name in list(cls._started_containers):
            if name in cls._container_instances:
                logger.info(f"Stopping {name} container...")
                instance = cls._container_instances[name]
                instance.stop()

        cls._container_instances.clear()
        cls._started_containers.clear()
        cls._started = False
        logger.info("All test containers stopped")

    @classmethod
    def reset(cls):
        """Reset the registry state."""
        cls.stop_all()
        cls._containers.clear()
        cls._container_instances.clear()
        cls._started_containers.clear()
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
        self.port: int | None = None
        self.database: int = self.config.DATABASE
        self.password: str | None = self.config.PASSWORD

        # Set up the container
        self._container = RedisContainer(self.image)
        if self.config.PASSWORD:
            self._container.with_env("REDIS_PASSWORD", self.config.PASSWORD)

    def start(self) -> RedisContainer:
        """Start the Redis container."""
        if self._is_running:
            return self._container

        self._container.start()
        self._is_running = True

        # Get dynamic host and port
        self.host = self._container.get_container_host_ip()
        self.port = int(self._container.get_exposed_port(6379))

        # Update global config with actual container endpoint
        global_config = BaseConfig.global_config()
        global_config.REDIS.MASTER_HOST = f"{self.host}:{self.port}"
        global_config.REDIS.PORT = self.port

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
    def __init__(self, config: PostgresSQLAlchemyConfig | None = None, image: str | None = None) -> None:
        self.name = "postgres"
        self.config = config or BaseConfig.global_config().POSTGRES_SQLALCHEMY
        self.image = image or BaseConfig.global_config().POSTGRES__IMAGE
        self._is_running: bool = False

        # Container properties
        self.host: str | None = None
        self.port: int | None = None
        self.database: str | None = self.config.DATABASE
        self.username: str | None = self.config.USERNAME
        self.password: str | None = self.config.PASSWORD

        # Use config values or fallback to defaults for test containers
        dbname = self.database or "test_db"
        username = self.username or "test_user"
        password = self.password or "test_password"

        # Set up the container
        self._container = PostgresContainer(
            image=self.image,
            dbname=dbname,
            username=username,
            password=password,
        )

    def start(self) -> PostgresContainer:
        """Start the PostgreSQL container."""
        if self._is_running:
            return self._container

        self._container.start()
        self._is_running = True

        # Get dynamic host and port
        self.host = self._container.get_container_host_ip()
        self.port = int(self._container.get_exposed_port(5432))

        # Update global config with actual container endpoint
        global_config = BaseConfig.global_config()
        global_config.POSTGRES_SQLALCHEMY.HOST = self.host
        global_config.POSTGRES_SQLALCHEMY.PORT = self.port

        logger.info("PostgreSQL container started on %s:%s", self.host, self.port)

        return self._container

    def stop(self) -> None:
        """Stop the PostgreSQL container."""
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
    def __init__(self, config: KeycloakConfig | None = None, image: str | None = None) -> None:
        self.name = "keycloak"
        self.config = config or BaseConfig.global_config().KEYCLOAK
        self.image = image or BaseConfig.global_config().KEYCLOAK__IMAGE
        self._is_running: bool = False

        # Container properties
        self.host: str | None = None
        self.port: int | None = None
        self.admin_username: str | None = self.config.ADMIN_USERNAME
        self.admin_password: str | None = self.config.ADMIN_PASSWORD
        self.realm: str = self.config.REALM_NAME

        # Use config values or fallback to defaults for test containers
        username = self.admin_username or "admin"
        password = self.admin_password or "admin"

        # Set up the container
        self._container = KeycloakContainer(
            image=self.image,
            username=username,
            password=password,
        )

    def start(self) -> KeycloakContainer:
        """Start the Keycloak container."""
        if self._is_running:
            return self._container

        self._container.start()
        self._is_running = True

        # Get dynamic host and port
        self.host = self._container.get_container_host_ip()
        self.port = int(self._container.get_exposed_port(8080))

        # Update global config with actual container endpoint
        global_config = BaseConfig.global_config()
        global_config.KEYCLOAK.SERVER_URL = f"http://{self.host}:{self.port}"

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
        self.host: str | None = None
        self.port: int | None = None
        self.username: str | None = self.config.HTTP_USER_NAME
        self.password: str | None = self.config.HTTP_PASSWORD.get_secret_value() if self.config.HTTP_PASSWORD else None
        self.cluster_name: str = "test-cluster"

        # Set up the container
        self._container = DockerContainer(self.image)
        self._container.with_env("discovery.type", "single-node")
        self._container.with_env("xpack.security.enabled", "true")
        if self.password:
            self._container.with_env("ELASTIC_PASSWORD", self.password)
        self._container.with_env("cluster.name", self.cluster_name)
        self._container.with_exposed_ports(9200)

    def start(self) -> DockerContainer:
        """Start the Elasticsearch container."""
        if self._is_running:
            return self._container

        # Start the container
        self._container.start()

        # Wait for Elasticsearch to be ready
        wait_for_logs(self._container, "started", timeout=60)

        self._is_running = True

        # Get dynamic host and port
        self.host = self._container.get_container_host_ip()
        self.port = int(self._container.get_exposed_port(9200))

        # Update global config with actual container endpoint
        global_config = BaseConfig.global_config()
        global_config.ELASTIC.HOSTS = [f"http://{self.host}:{self.port}"]

        logger.info("Elasticsearch container started on %s:%s", self.host, self.port)

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

        # Set up the container
        self._container = KafkaContainer(image=self.image)

    def start(self) -> KafkaContainer:
        """Start the Kafka container."""
        if self._is_running:
            return self._container

        self._container.start()
        self._is_running = True

        # Get dynamic host, port, and bootstrap servers from running container
        self.host = self._container.get_container_host_ip()
        self.bootstrap_servers = self._container.get_bootstrap_server()
        # Extract port from bootstrap_servers (format: "host:port")
        _, port_str = self.bootstrap_servers.split(":")
        self.port = int(port_str)

        # Update global config with actual container endpoint
        global_config = BaseConfig.global_config()
        global_config.KAFKA.BROKERS_LIST = [self.bootstrap_servers]

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

        # Set up the container
        self._container = MinioContainer(
            image=self.image,
            access_key=self.access_key,
            secret_key=self.secret_key,
        )

    def start(self) -> MinioContainer:
        """Start the MinIO container."""
        if self._is_running:
            return self._container

        try:
            self._container.start()
            self._is_running = True

            # Get dynamic host and port
            self.host = self._container.get_container_host_ip()
            self.port = int(self._container.get_exposed_port(9000))

            # Update global config with actual container endpoint
            global_config = BaseConfig.global_config()
            global_config.MINIO.ENDPOINT = f"{self.host}:{self.port}"

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


@ContainerManager.register("scylladb")
class ScyllaDBTestContainer(metaclass=Singleton, thread_safe=True):
    """Test container for ScyllaDB."""

    def __init__(self, config: ScyllaDBConfig | None = None, image: str | None = None) -> None:
        """Initialize ScyllaDB test container.

        Args:
            config (ScyllaDBConfig | None): Configuration for ScyllaDB. Defaults to None.
            image (str | None): Docker image to use. Defaults to None (uses SCYLLADB__IMAGE from config).
        """
        self.name = "scylladb"
        # Get config from global or create default
        if config is not None:
            self.config = config
        else:
            try:
                self.config = BaseConfig.global_config().SCYLLADB
            except AttributeError:
                # SCYLLADB not configured in global config, use defaults
                self.config = ScyllaDBConfig()
        self.image = image or BaseConfig.global_config().SCYLLADB__IMAGE
        self._is_running: bool = False

        # Container properties
        self.host: str | None = None
        self.port: int | None = None

        # Set up the container
        self._container = DockerContainer(self.image)
        self._container.with_exposed_ports(9042)  # CQL native transport port

        # Add environment variables for single-node configuration
        self._container.with_env("SCYLLA_ARGS", "--smp 1 --memory 750M")

    def start(self) -> DockerContainer:
        """Start the ScyllaDB container.

        Returns:
            DockerContainer: The running container instance.
        """
        if self._is_running:
            return self._container

        # Start the container
        self._container.start()

        # Wait for ScyllaDB to be ready
        # ScyllaDB logs "Starting listening for CQL clients" when ready
        wait_for_logs(self._container, "Starting listening for CQL clients", timeout=120)

        self._is_running = True

        # Get dynamic host and port
        self.host = self._container.get_container_host_ip()
        self.port = int(self._container.get_exposed_port(9042))

        # Update global config with actual container endpoint
        global_config = BaseConfig.global_config()
        if global_config.SCYLLADB is None:
            from archipy.configs.config_template import ScyllaDBConfig

            global_config.SCYLLADB = ScyllaDBConfig()

        global_config.SCYLLADB.CONTACT_POINTS = [self.host]
        global_config.SCYLLADB.PORT = self.port

        logger.info("ScyllaDB container started on %s:%s", self.host, self.port)

        return self._container

    def stop(self) -> None:
        """Stop the ScyllaDB container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False

        # Reset container properties
        self.host = None
        self.port = None

        logger.info("ScyllaDB container stopped")
