"""Container manager for test containers"""

import datetime
import json
import logging
import os
import tempfile
import time
from pathlib import Path

import httpx2
from opentelemetry.instrumentation.utils import suppress_instrumentation
from testcontainers.community.mysql import MySqlContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.elasticsearch import ElasticSearchContainer
from testcontainers.keycloak import KeycloakContainer
from testcontainers.community.vault import VaultContainer
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import (
    ElasticsearchConfig,
    KafkaConfig,
    KeycloakConfig,
    MinioConfig,
    MySQLSQLAlchemyConfig,
    PostgresSQLAlchemyConfig,
    RedisConfig,
    RedisMode,
    ScyllaDBConfig,
    StarRocksSQLAlchemyConfig,
    TemporalConfig,
    VaultConfig,
)
from archipy.helpers.metaclasses.singleton import Singleton

logger = logging.getLogger(__name__)

# Each limit sits a little above the process sizing below: the JVM heaps and Go/Postgres/StarRocks
# memory settings are what keep actual usage down, the limits only stop a runaway container.
CONTAINER_MEM_LIMITS: dict[str, str] = {
    "postgres": "256m",
    "keycloak": "768m",
    "minio": "256m",
    "starrocks": "1280m",
    "redis": "64m",
    "kafka": "1024m",
    "temporal": "384m",
    "mailpit": "64m",
    "otel-collector": "128m",
    "pushgateway": "64m",
    "apm-server": "256m",
    "otel-collector-apm": "128m",
}

# Test data is tiny and throwaway: small buffers, and no durability work.
POSTGRES_LOW_MEMORY_COMMAND: str = (
    "postgres -c shared_buffers=32MB -c work_mem=2MB -c maintenance_work_mem=16MB"
    " -c fsync=off -c synchronous_commit=off -c full_page_writes=off"
)
# Keycloak otherwise sizes its heap at 70% of the container limit.
KEYCLOAK_HEAP_OPTS: str = "-Xms64m -Xmx256m"
# kafka-server-start.sh defaults to a fixed 1 GiB heap when this is unset.
KAFKA_HEAP_OPTS: str = "-Xms512m -Xmx512m"
# The image ships an 8 GiB FE heap and lets the BE claim 90% of the memory it can see.
STARROCKS_LOW_MEMORY_COMMAND: list[str] = [
    "bash",
    "-c",
    "sed -i 's/-Xmx8192m/-Xmx512m/' /data/deploy/starrocks/fe/conf/fe.conf"
    " && echo 'mem_limit = 512M' >> /data/deploy/starrocks/be/conf/be.conf"
    " && exec ./entrypoint.sh",
]
# No RDB/AOF persistence: a background save forks and can double Redis memory.
REDIS_LOW_MEMORY_COMMAND: str = "redis-server --save '' --appendonly no"
# Soft limit for the Go runtimes (MinIO, Temporal dev server) so they collect before the hard limit.
MINIO_GOMEMLIMIT: str = "192MiB"
TEMPORAL_GOMEMLIMIT: str = "256MiB"

# Mapping of feature tags to container names
TAG_CONTAINER_MAP: dict[str, str] = {
    "needs-postgres": "postgres",
    "needs-mysql": "mysql",
    "needs-kafka": "kafka",
    "needs-elasticsearch": "elasticsearch",
    "needs-minio": "minio",
    "needs-keycloak": "keycloak",
    "needs-redis": "redis",
    "needs-redis-cluster": "redis-cluster",
    "needs-scylladb": "scylladb",
    "needs-starrocks": "starrocks",
    "needs-temporal": "temporal",
    "needs-vault": "vault",
    "needs-mailpit": "mailpit",
    "needs-mailpit-plain": "mailpit-plain",
    "needs-otel-collector": "otel-collector",
    "needs-pushgateway": "pushgateway",
    "needs-apm-server": "apm-server",
    "needs-apm-collector": "otel-collector-apm",
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
            # Only log warning for tags that look like container tags but aren't mapped
            elif tag_name.startswith("needs-"):
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
        self._container.with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["redis"])
        self._container.with_command(REDIS_LOW_MEMORY_COMMAND)

    def start(self) -> RedisContainer:
        """Start the Redis container."""
        if self._is_running:
            return self._container

        # Recreate container if it was stopped
        if self._container is None:
            self._container = RedisContainer(self.image)
            if self.config.PASSWORD:
                self._container.with_env("REDIS_PASSWORD", self.config.PASSWORD)
            self._container.with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["redis"])
            self._container.with_command(REDIS_LOW_MEMORY_COMMAND)

        self._container.start()
        self._is_running = True

        # Get dynamic host and port
        self.host = self._container.get_container_host_ip()
        self.port = int(self._container.get_exposed_port(6379))

        # Update global config with actual container endpoint
        global_config = BaseConfig.global_config()
        global_config.REDIS.MASTER_HOST = self.host
        global_config.REDIS.PORT = self.port
        global_config.REDIS.PASSWORD = None  # Test container has no password

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


_CLUSTER_PORTS = [7001, 7002, 7003, 7004, 7005, 7006]
_CLUSTER_NODE_ADDRESSES = [f"127.0.0.1:{port}" for port in _CLUSTER_PORTS]


def _build_redis_cluster_node(image: str, port: int) -> DockerContainer:
    """Build a Redis cluster node container using host networking."""
    command = (
        f"redis-server --port {port} --cluster-enabled yes "
        f"--cluster-config-file nodes.conf --cluster-node-timeout 5000 "
        f"--cluster-announce-ip 127.0.0.1 --appendonly no"
    )
    return DockerContainer(image).with_kwargs(network_mode="host").with_command(command)


def _wait_for_cluster_ready(container: DockerContainer, port: int, timeout: float = 60.0) -> None:
    """Poll until the Redis cluster reports cluster_state:ok."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = container.exec(["redis-cli", "-p", str(port), "cluster", "info"])
        if b"cluster_state:ok" in result.output:
            return
        time.sleep(0.5)
    msg = f"Redis cluster on port {port} did not reach cluster_state:ok within {timeout}s"
    raise TimeoutError(msg)


@ContainerManager.register("redis-cluster")
class RedisClusterTestContainer(metaclass=Singleton, thread_safe=True):
    """Six-node Redis cluster (3 masters + 3 replicas) using host networking (Linux only)."""

    def __init__(self, image: str | None = None) -> None:
        self.name = "redis-cluster"
        self.image = image or BaseConfig.global_config().REDIS__IMAGE
        self._is_running: bool = False
        self._containers: list[DockerContainer] = []
        self.cluster_config = RedisConfig(
            MODE=RedisMode.CLUSTER,
            CLUSTER_NODES=list(_CLUSTER_NODE_ADDRESSES),
            DECODE_RESPONSES=True,
            PASSWORD=None,
            CLUSTER_REQUIRE_FULL_COVERAGE=True,
            CLUSTER_READ_FROM_REPLICAS=True,
        )

    def _create_containers(self) -> list[DockerContainer]:
        """Create fresh cluster node containers."""
        return [_build_redis_cluster_node(self.image, port) for port in _CLUSTER_PORTS]

    def start(self) -> list[DockerContainer]:
        """Start the Redis cluster nodes and bootstrap the cluster."""
        if self._is_running:
            return self._containers

        if not self._containers:
            self._containers = self._create_containers()

        for container in self._containers:
            container.start()
            wait_for_logs(container, "Ready to accept connections", timeout=30)

        bootstrap_command = [
            "redis-cli",
            "--cluster",
            "create",
            *_CLUSTER_NODE_ADDRESSES,
            "--cluster-replicas",
            "1",
            "--cluster-yes",
        ]
        result = self._containers[0].exec(bootstrap_command)
        if result.exit_code != 0:
            output = result.output.decode() if isinstance(result.output, bytes) else str(result.output)
            msg = f"Redis cluster bootstrap failed (exit {result.exit_code}): {output}"
            raise RuntimeError(msg)

        _wait_for_cluster_ready(self._containers[0], _CLUSTER_PORTS[0])
        self._is_running = True
        logger.info("Redis cluster started on %s", ", ".join(_CLUSTER_NODE_ADDRESSES))
        return self._containers

    def stop(self) -> None:
        """Stop all Redis cluster node containers."""
        if not self._is_running and not self._containers:
            return

        for container in self._containers:
            try:
                container.stop()
            except Exception:
                logger.exception("Error stopping Redis cluster node")

        self._containers = []
        self._is_running = False
        logger.info("Redis cluster stopped")


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
        self._container.with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["postgres"])
        self._container.with_command(POSTGRES_LOW_MEMORY_COMMAND)

    def start(self) -> PostgresContainer:
        """Start the PostgreSQL container."""
        if self._is_running:
            return self._container

        # Recreate container if it was stopped
        if self._container is None:
            dbname = self.database or "test_db"
            username = self.username or "test_user"
            password = self.password or "test_password"

            self._container = PostgresContainer(
                image=self.image,
                dbname=dbname,
                username=username,
                password=password,
            )
            self._container.with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["postgres"])
            self._container.with_command(POSTGRES_LOW_MEMORY_COMMAND)

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


@ContainerManager.register("mysql")
class MySQLTestContainer(metaclass=Singleton, thread_safe=True):
    def __init__(self, config: MySQLSQLAlchemyConfig | None = None, image: str | None = None) -> None:
        self.name = "mysql"
        self.config = config or BaseConfig.global_config().MYSQL_SQLALCHEMY
        self.image = image or BaseConfig.global_config().MYSQL__IMAGE
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
        self._container = MySqlContainer(
            image=self.image,
            dbname=dbname,
            username=username,
            password=password,
        )

    def start(self) -> MySqlContainer:
        """Start the MySQL container."""
        if self._is_running:
            return self._container

        # Recreate container if it was stopped
        if self._container is None:
            dbname = self.database or "test_db"
            username = self.username or "test_user"
            password = self.password or "test_password"

            self._container = MySqlContainer(
                image=self.image,
                dbname=dbname,
                username=username,
                password=password,
            )

        self._container.start()
        self._is_running = True

        # Get dynamic host and port
        self.host = self._container.get_container_host_ip()
        self.port = int(self._container.get_exposed_port(3306))

        # Update global config with actual container endpoint
        global_config = BaseConfig.global_config()
        global_config.MYSQL_SQLALCHEMY.HOST = self.host
        global_config.MYSQL_SQLALCHEMY.PORT = self.port

        logger.info("MySQL container started on %s:%s", self.host, self.port)

        return self._container

    def stop(self) -> None:
        """Stop the MySQL container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False

        # Reset container properties
        self.host = None
        self.port = None

        logger.info("MySQL container stopped")


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
        # enable Organizations feature for Keycloak 25+
        self._container.with_command("start-dev --features organization")
        self._container.with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["keycloak"])
        self._container.with_env("JAVA_OPTS_KC_HEAP", KEYCLOAK_HEAP_OPTS)

    def start(self) -> KeycloakContainer:
        """Start the Keycloak container."""
        if self._is_running:
            return self._container

        # Recreate container if it was stopped
        if self._container is None:
            username = self.admin_username or "admin"
            password = self.admin_password or "admin"

            self._container = KeycloakContainer(
                image=self.image,
                username=username,
                password=password,
            )
            # enable Organizations feature for Keycloak 25+
            self._container.with_command("start-dev --features organization")
            self._container.with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["keycloak"])
            self._container.with_env("JAVA_OPTS_KC_HEAP", KEYCLOAK_HEAP_OPTS)

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


def _build_elasticsearch_container(image: str) -> ElasticSearchContainer:
    container = ElasticSearchContainer(image=image)
    # Default ES heap can OOM-kill the container (exit 137) on shared CI/dev hosts.
    container.with_env("ES_JAVA_OPTS", "-Xms1g -Xmx1g")
    container.with_env("discovery.type", "single-node")
    if container._wait_strategy is not None:
        # ES startup can exceed the default 120s on loaded machines; allow up to 5 minutes.
        container._wait_strategy = container._wait_strategy.with_startup_timeout(300)
    return container


def _wait_for_elasticsearch(url: str, timeout: float = 120.0) -> None:
    """Block until the cluster reports at least yellow health (primary shards allocated).

    The container wait strategy only checks that HTTP answers, which happens before the master is elected and
    shards can be allocated; index creation then fails under load.
    """
    deadline = time.monotonic() + timeout
    last_error = "no response"
    while time.monotonic() < deadline:
        try:
            response = httpx2.get(
                f"{url}/_cluster/health",
                params={"wait_for_status": "yellow", "timeout": "5s"},
                timeout=10,
            )
            if response.status_code == 200 and response.json().get("status") in ("yellow", "green"):
                return
            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
        except (httpx2.HTTPError, ValueError) as e:
            last_error = str(e)
        time.sleep(1)
    raise TimeoutError(f"Elasticsearch cluster not ready after {timeout}s: {last_error}")


@ContainerManager.register("elasticsearch")
class ElasticsearchTestContainer(metaclass=Singleton, thread_safe=True):
    def __init__(self, config: ElasticsearchConfig | None = None, image: str | None = None) -> None:
        self.name = "elasticsearch"
        self.config = config or BaseConfig.global_config().ELASTIC
        self.image = image or BaseConfig.global_config().ELASTIC__IMAGE
        self._is_running: bool = False

        self.host: str | None = None
        self.port: int | None = None
        self.username: str | None = self.config.HTTP_USER_NAME
        self.password: str | None = self.config.HTTP_PASSWORD.get_secret_value() if self.config.HTTP_PASSWORD else None
        self.cluster_name: str = "test-cluster"

        self._container: ElasticSearchContainer | None = _build_elasticsearch_container(self.image)

    def start(self) -> ElasticSearchContainer:
        """Start the Elasticsearch container."""
        if self._is_running:
            return self._container

        if self._container is None:
            # The container is gone after stop(); build a fresh one so the test run can start it again.
            self._container = _build_elasticsearch_container(self.image)

        self._container.start()
        self._is_running = True

        self.host = self._container.get_container_host_ip()
        self.port = int(self._container.get_exposed_port(9200))
        self._wait_until_ready()

        global_config = BaseConfig.global_config()
        global_config.ELASTIC.HOSTS = [f"http://{self.host}:{self.port}"]
        # Loaded CI runners answer index creation slower than the 1s library default.
        global_config.ELASTIC.REQUEST_TIMEOUT = 30.0

        logger.info("Elasticsearch container started on %s:%s", self.host, self.port)

        return self._container

    def _wait_until_ready(self, timeout: float = 120.0) -> None:
        _wait_for_elasticsearch(f"http://{self.host}:{self.port}", timeout)

    def stop(self) -> None:
        """Stop the Elasticsearch container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False

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

        self.host: str | None = None
        self.port: int | None = None
        self.bootstrap_servers: str | None = None
        self._container: DockerContainer | None = None

    def start(self) -> DockerContainer:
        """Start the Kafka container."""
        if self._is_running:
            return self._container

        temp_container = (
            DockerContainer(image=self.image)
            .with_exposed_ports(9092, 9093)
            .with_env("KAFKA_NODE_ID", "1")
            .with_env("KAFKA_PROCESS_ROLES", "broker,controller")
            .with_env("KAFKA_LISTENERS", "PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093")
            .with_env("KAFKA_CONTROLLER_LISTENER_NAMES", "CONTROLLER")
            .with_env(
                "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP",
                "PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT",
            )
            .with_env("KAFKA_CONTROLLER_QUORUM_VOTERS", "1@localhost:9093")
            .with_env("KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR", "1")
            .with_env("KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR", "1")
            .with_env("KAFKA_TRANSACTION_STATE_LOG_MIN_ISR", "1")
            .with_env("KAFKA_LOG_DIRS", "/var/lib/kafka/data")
            .with_env("KAFKA_ENABLE_KRAFT", "true")
            .with_env("KAFKA_AUTO_CREATE_TOPICS_ENABLE", "true")
            .with_env("KAFKA_HEAP_OPTS", KAFKA_HEAP_OPTS)
            .with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["kafka"])
        )

        temp_container.start()
        mapped_port = int(temp_container.get_exposed_port(9092))
        temp_container.stop()
        temp_container = None

        self._container = (
            DockerContainer(image=self.image)
            .with_bind_ports(9092, mapped_port)
            .with_bind_ports(9093, mapped_port + 1)
            .with_env("KAFKA_NODE_ID", "1")
            .with_env("KAFKA_PROCESS_ROLES", "broker,controller")
            .with_env("KAFKA_LISTENERS", "PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093")
            .with_env(
                "KAFKA_ADVERTISED_LISTENERS",
                f"PLAINTEXT://localhost:{mapped_port}",
            )
            .with_env("KAFKA_CONTROLLER_LISTENER_NAMES", "CONTROLLER")
            .with_env(
                "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP",
                "PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT",
            )
            .with_env("KAFKA_CONTROLLER_QUORUM_VOTERS", "1@localhost:9093")
            .with_env("KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR", "1")
            .with_env("KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR", "1")
            .with_env("KAFKA_TRANSACTION_STATE_LOG_MIN_ISR", "1")
            .with_env("KAFKA_LOG_DIRS", "/var/lib/kafka/data")
            .with_env("KAFKA_ENABLE_KRAFT", "true")
            .with_env("KAFKA_AUTO_CREATE_TOPICS_ENABLE", "true")
            .with_env("KAFKA_HEAP_OPTS", KAFKA_HEAP_OPTS)
            .with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["kafka"])
        )

        self._container.start()
        self._is_running = True

        wait_for_logs(self._container, "Kafka Server started", timeout=120)

        self.host = self._container.get_container_host_ip()
        self.port = mapped_port
        self.bootstrap_servers = f"localhost:{self.port}"
        self._wait_until_ready()

        global_config = BaseConfig.global_config()
        global_config.KAFKA.BROKERS_LIST = [self.bootstrap_servers]

        logger.info("Kafka container started on %s:%s", self.host, self.port)
        logger.info("Bootstrap servers: %s", self.bootstrap_servers)

        return self._container

    def _wait_until_ready(self, timeout: float = 120.0) -> None:
        """Block until the broker answers a metadata request and reports a controller."""
        from confluent_kafka.admin import AdminClient

        admin = AdminClient({"bootstrap.servers": self.bootstrap_servers})
        deadline = time.monotonic() + timeout
        last_error = "no response"
        while time.monotonic() < deadline:
            try:
                metadata = admin.list_topics(timeout=5)
                if metadata.brokers and metadata.controller_id >= 0:
                    return
                last_error = "no brokers or controller in metadata"
            except Exception as e:  # noqa: BLE001 - any client error means not ready yet
                last_error = str(e)
            time.sleep(1)
        raise TimeoutError(f"Kafka broker not ready after {timeout}s: {last_error}")

    def stop(self) -> None:
        """Stop the Kafka container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False

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

        self.host: str | None = None
        self.port: int | None = None
        self.access_key = self.config.ACCESS_KEY or "minioadmin"
        self.secret_key = self.config.SECRET_KEY or "minioadmin"

        self._container = MinioContainer(
            image=self.image,
            access_key=self.access_key,
            secret_key=self.secret_key,
        )
        self._container.with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["minio"])
        self._container.with_env("GOMEMLIMIT", MINIO_GOMEMLIMIT)

    def start(self) -> MinioContainer:
        if self._is_running:
            return self._container

        if self._container is None:
            self._container = MinioContainer(
                image=self.image,
                access_key=self.access_key,
                secret_key=self.secret_key,
            )
            self._container.with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["minio"])
            self._container.with_env("GOMEMLIMIT", MINIO_GOMEMLIMIT)

        self._container.start()
        self._is_running = True

        self.host = self._container.get_container_host_ip()
        self.port = int(self._container.get_exposed_port(9000))

        global_config = BaseConfig.global_config()
        global_config.MINIO.ENDPOINT = f"{self.host}:{self.port}"
        global_config.MINIO.ACCESS_KEY = self.access_key
        global_config.MINIO.SECRET_KEY = self.secret_key
        global_config.MINIO.SECURE = False

        logger.info("MinIO container started on %s:%s", self.host, self.port)
        return self._container

    def stop(self) -> None:
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False
        self.host = None
        self.port = None

        logger.info("MinIO container stopped")


@ContainerManager.register("scylladb")
class ScyllaDBTestContainer(metaclass=Singleton, thread_safe=True):
    """Test container for ScyllaDB."""

    # Minimum aio-max-nr required by ScyllaDB's Seastar framework
    MIN_AIO_MAX_NR = 65536

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

    @staticmethod
    def _check_aio_max_nr() -> None:
        """Check that the host system's fs.aio-max-nr is sufficient for ScyllaDB.

        ScyllaDB's Seastar framework requires a minimum number of AIO slots.
        If the system value is too low, ScyllaDB will crash on startup.

        Raises:
            RuntimeError: If aio-max-nr is below the required minimum.
        """
        aio_path = Path("/proc/sys/fs/aio-max-nr")
        if not aio_path.exists():
            logger.warning("Cannot check aio-max-nr: %s not found (non-Linux system?)", aio_path)
            return

        current_value = int(aio_path.read_text().strip())
        if current_value < ScyllaDBTestContainer.MIN_AIO_MAX_NR:
            msg = (
                f"ScyllaDB requires fs.aio-max-nr >= {ScyllaDBTestContainer.MIN_AIO_MAX_NR}, "
                f"but the current value is {current_value}. "
                f"Fix this by running: sudo sysctl -w fs.aio-max-nr={ScyllaDBTestContainer.MIN_AIO_MAX_NR} "
                f"To make it permanent, add 'fs.aio-max-nr = {ScyllaDBTestContainer.MIN_AIO_MAX_NR}' "
                f"to /etc/sysctl.conf and run 'sudo sysctl -p'."
            )
            raise RuntimeError(msg)

    def start(self) -> DockerContainer:
        """Start the ScyllaDB container.

        Returns:
            DockerContainer: The running container instance.

        Raises:
            RuntimeError: If the host system's aio-max-nr is too low for ScyllaDB.
        """
        if self._is_running:
            return self._container

        # Pre-flight check: verify host AIO configuration
        self._check_aio_max_nr()

        # Recreate container if it was stopped
        if self._container is None:
            self._container = DockerContainer(self.image)
            self._container.with_exposed_ports(9042)  # CQL native transport port
            # Add environment variables for single-node configuration
            self._container.with_env("SCYLLA_ARGS", "--smp 1 --memory 750M")

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


@ContainerManager.register("starrocks")
class StarRocksTestContainer(metaclass=Singleton, thread_safe=True):
    """Test container for StarRocks."""

    def __init__(self, config: StarRocksSQLAlchemyConfig | None = None, image: str | None = None) -> None:
        """Initialize StarRocks test container.

        Args:
            config (StarRocksSQLAlchemyConfig | None): Configuration for StarRocks. Defaults to None.
            image (str | None): Docker image to use. Defaults to None (uses STARROCKS__IMAGE from config).
        """
        self.name = "starrocks"
        self.config = config or BaseConfig.global_config().STARROCKS_SQLALCHEMY
        self.image = image or BaseConfig.global_config().STARROCKS__IMAGE
        self._is_running: bool = False

        # Container properties
        self.host: str | None = None
        self.port: int | None = None
        self.database: str | None = self.config.DATABASE
        self.username: str | None = self.config.USERNAME
        self.password: str | None = self.config.PASSWORD

        # Set up the container
        self._container = DockerContainer(self.image)
        # Expose ports: 9030 (MySQL protocol), 8030 (FE HTTP), 8040 (BE HTTP)
        # These will be mapped to random available host ports automatically
        self._container.with_exposed_ports(9030, 8030, 8040)
        self._container.with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["starrocks"])
        self._container.with_command(STARROCKS_LOW_MEMORY_COMMAND)

    def start(self) -> DockerContainer:
        """Start the StarRocks container.

        Returns:
            DockerContainer: The running container instance.
        """
        if self._is_running:
            return self._container

        # Recreate container if it was stopped
        if self._container is None:
            self._container = DockerContainer(self.image)
            # Expose ports: 9030 (MySQL protocol), 8030 (FE HTTP), 8040 (BE HTTP)
            # These will be mapped to random available host ports automatically
            self._container.with_exposed_ports(9030, 8030, 8040)
            self._container.with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["starrocks"])
            self._container.with_command(STARROCKS_LOW_MEMORY_COMMAND)

        # Start the container
        self._container.start()

        # Wait for StarRocks to be ready
        # StarRocks logs "cluster initialization DONE!" when the cluster is fully initialized
        # This appears after "FE service query port:9030 is alive!" and indicates readiness
        wait_for_logs(self._container, "Enjoy the journey to StarRocks blazing-fast lake-house engine!", timeout=120)

        self._is_running = True

        # Get dynamic host and random port (container port 9030 mapped to random host port)
        self.host = self._container.get_container_host_ip()
        # get_exposed_port returns the random host port that maps to container port 9030
        self.port = int(self._container.get_exposed_port(9030))

        # Create the test database if it doesn't exist
        if self.database:
            self._create_database(self.database)

        # Update global config with actual container endpoint
        global_config = BaseConfig.global_config()
        global_config.STARROCKS_SQLALCHEMY.HOST = self.host
        global_config.STARROCKS_SQLALCHEMY.PORT = self.port

        logger.info("StarRocks container started on %s:%s", self.host, self.port)

        return self._container

    def _create_database(self, database_name: str) -> None:
        """Create a database in StarRocks if it doesn't exist.

        Args:
            database_name: Name of the database to create.
        """
        import pymysql

        try:
            # Connect without specifying a database
            connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.username or "root",
                password=self.password or "",
                connect_timeout=10,
            )

            with connection.cursor() as cursor:
                # Create database if not exists
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
                logger.info(f"Created database '{database_name}' in StarRocks")

            connection.close()
        except Exception as e:
            logger.warning(f"Failed to create database '{database_name}': {e}")
            # Don't fail the container start if database creation fails
            # The adapter might handle this or it might already exist

    def stop(self) -> None:
        """Stop the StarRocks container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False

        # Reset container properties
        self.host = None
        self.port = None

        logger.info("StarRocks container stopped")


@ContainerManager.register("temporal")
class TemporalContainer(metaclass=Singleton, thread_safe=True):
    """Temporal test container for workflow orchestration testing.

    This container uses temporalio/temporal in development mode with embedded SQLite.
    This is a single container with no external database dependencies.

    The server runs with `temporal server start-dev` which includes:
    - Temporal server
    - Embedded SQLite database
    - Auto-configured default namespace
    - Web UI on port 8233

    Note: Development mode is for testing only, not production use.
    """

    def __init__(self) -> None:
        """Initialize the Temporal container with configuration from global config."""
        self.name = "temporal"
        global_config = BaseConfig.global_config()
        self.image = global_config.TEMPORAL__IMAGE

        # Configure Temporal server in development mode with SQLite
        self._container = DockerContainer(self.image)
        self._container.with_exposed_ports(7233, 8233)

        # Use development mode with embedded SQLite
        self._container.with_command(
            "server start-dev --namespace default --db-filename /tmp/temporal.db --ip 0.0.0.0",
        )
        self._container.with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["temporal"])
        self._container.with_env("GOMEMLIMIT", TEMPORAL_GOMEMLIMIT)

        self._is_running = False
        self.host: str | None = None
        self.port: int | None = None
        self.config: TemporalConfig | None = None

    def start(self) -> DockerContainer:
        """Start the Temporal container.

        Returns:
            DockerContainer: The running container instance.
        """
        if self._is_running:
            return self._container

        # Recreate container if it was stopped
        if self._container is None:
            global_config = BaseConfig.global_config()
            self.image = global_config.TEMPORAL__IMAGE

            # Configure Temporal server in development mode with SQLite
            self._container = DockerContainer(self.image)
            self._container.with_exposed_ports(7233, 8233)

            # Use development mode with embedded SQLite
            self._container.with_command(
                "server start-dev --namespace default --db-filename /tmp/temporal.db --ip 0.0.0.0",
            )
            self._container.with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["temporal"])
            self._container.with_env("GOMEMLIMIT", TEMPORAL_GOMEMLIMIT)

        # Start Temporal development server
        logger.info("Starting Temporal development server...")
        self._container.start()

        # Wait for Temporal to be ready
        # The dev server logs "CLI" when it starts
        wait_for_logs(self._container, "CLI", timeout=60)

        self._is_running = True

        # Get dynamic host and port
        self.host = self._container.get_container_host_ip()
        self.port = int(self._container.get_exposed_port(7233))

        # Create Temporal configuration with container endpoint
        self.config = TemporalConfig(
            HOST=self.host,
            PORT=self.port,
            NAMESPACE="default",
            TASK_QUEUE="test-task-queue",
        )

        logger.info("Temporal container started on %s:%s", self.host, self.port)

        return self._container

    def stop(self) -> None:
        """Stop the Temporal container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False

        # Reset container properties
        self.host = None
        self.port = None
        self.config = None

        logger.info("Temporal container stopped")


@ContainerManager.register("vault")
class VaultTestContainer(metaclass=Singleton, thread_safe=True):
    """Test container for HashiCorp Vault (dev mode)."""

    def __init__(self, config: VaultConfig | None = None, image: str | None = None) -> None:
        """Initialize Vault test container.

        Args:
            config: Optional Vault configuration. Defaults to global VAULT config.
            image: Docker image override. Defaults to VAULT__IMAGE from TestConfig.
        """
        self.name = "vault"
        self.config = config or BaseConfig.global_config().VAULT
        self.image = image or BaseConfig.global_config().VAULT__IMAGE
        self.root_token = "toor"
        self._container: VaultContainer | None = None
        self._is_running = False
        self.host: str | None = None
        self.port: int | None = None
        self.addr: str | None = None

        self._container = VaultContainer(
            image=self.image,
            root_token=self.root_token,
        ).with_kwargs(extra_hosts={"host.docker.internal": "host-gateway"})

    def start(self) -> VaultContainer:
        """Start the Vault container and update global VAULT config."""
        if self._is_running:
            return self._container

        if self._container is None:
            self._container = VaultContainer(
                image=self.image,
                root_token=self.root_token,
            ).with_kwargs(extra_hosts={"host.docker.internal": "host-gateway"})

        self._container.start()
        self._is_running = True

        self.host = self._container.get_container_host_ip()
        self.port = int(self._container.get_exposed_port(8200))
        self.addr = self._container.get_connection_url()

        global_config = BaseConfig.global_config()
        global_config.VAULT.ADDR = self.addr
        global_config.VAULT.TOKEN = self.root_token
        global_config.VAULT.AUTH_METHOD = "token"
        global_config.VAULT.VERIFY_SSL = False
        global_config.VAULT.MOUNT_POINT = "secret"
        global_config.VAULT.ENABLED = False  # settings source opt-in per scenario

        logger.info("Vault container started at %s", self.addr)
        return self._container

    def stop(self) -> None:
        """Stop the Vault container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False
        self.host = None
        self.port = None
        self.addr = None

        logger.info("Vault container stopped")


def _write_self_signed_certificate(directory: Path) -> None:
    """Write a throwaway self-signed ``cert.pem``/``key.pem`` pair into ``directory`` (world-readable)."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    (directory / "cert.pem").write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    (directory / "key.pem").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ),
    )
    directory.chmod(0o755)
    (directory / "cert.pem").chmod(0o644)
    (directory / "key.pem").chmod(0o644)


@ContainerManager.register("mailpit")
class MailpitTestContainer(metaclass=Singleton, thread_safe=True):
    """Test container for Mailpit, a real SMTP server with an HTTP API to inspect delivered mail.

    SMTP runs with a self-signed certificate (so STARTTLS is advertised) and requires real credentials
    (``USERNAME``/``PASSWORD``). ``PlainMailpitTestContainer`` is the same server without TLS.
    """

    SMTP_PORT = 1025
    API_PORT = 8025
    USERNAME = "mailer@example.com"
    PASSWORD = "s3cret"
    WITH_TLS = True
    NAME = "mailpit"

    def __init__(self, image: str | None = None) -> None:
        """Initialize Mailpit test container.

        Args:
            image: Docker image override. Defaults to MAILPIT__IMAGE from TestConfig.
        """
        self.name = self.NAME
        self.image = image or BaseConfig.global_config().MAILPIT__IMAGE
        self._container: DockerContainer | None = None
        self._cert_dir: tempfile.TemporaryDirectory | None = None
        self._is_running = False
        self.host: str | None = None
        self.smtp_port: int | None = None
        self.api_url: str | None = None

    def _build(self) -> DockerContainer:
        container = (
            DockerContainer(self.image)
            .with_exposed_ports(self.SMTP_PORT, self.API_PORT)
            .with_env("MP_SMTP_AUTH", f"{self.USERNAME}:{self.PASSWORD}")
            # Mailpit resolves the name of every SMTP client; with no DNS in the container each connection waits 20 s.
            .with_env("MP_SMTP_DISABLE_RDNS", "true")
            .with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["mailpit"])
        )
        if self.WITH_TLS:
            self._cert_dir = tempfile.TemporaryDirectory()
            cert_path = Path(self._cert_dir.name)
            _write_self_signed_certificate(cert_path)
            container = (
                container.with_volume_mapping(str(cert_path), "/certs", "ro")
                .with_env("MP_SMTP_TLS_CERT", "/certs/cert.pem")
                .with_env("MP_SMTP_TLS_KEY", "/certs/key.pem")
            )
        else:
            # Without TLS Mailpit only offers AUTH on an insecure connection when told to.
            container = container.with_env("MP_SMTP_AUTH_ALLOW_INSECURE", "1")
        return container

    def start(self) -> DockerContainer:
        """Start Mailpit and wait until its SMTP and HTTP listeners are up."""
        if self._is_running:
            return self._container

        if self._container is None:
            self._container = self._build()

        self._container.start()
        wait_for_logs(self._container, r"\[http\] accessible via", timeout=60)
        wait_for_logs(self._container, r"\[smtpd\] starting on", timeout=60)
        self._is_running = True

        self.host = self._container.get_container_host_ip()
        self.smtp_port = int(self._container.get_exposed_port(self.SMTP_PORT))
        self.api_url = f"http://{self.host}:{self._container.get_exposed_port(self.API_PORT)}"

        logger.info("Mailpit container started: SMTP %s:%s, API %s", self.host, self.smtp_port, self.api_url)
        return self._container

    def stop(self) -> None:
        """Stop the Mailpit container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()
        if self._cert_dir:
            self._cert_dir.cleanup()

        self._container = None
        self._cert_dir = None
        self._is_running = False
        self.host = None
        self.smtp_port = None
        self.api_url = None

        logger.info("Mailpit container stopped")


@ContainerManager.register("mailpit-plain")
class PlainMailpitTestContainer(MailpitTestContainer):
    """Mailpit without TLS: the server does not advertise STARTTLS."""

    WITH_TLS = False
    NAME = "mailpit-plain"


OTEL_COLLECTOR_CONFIG: str = """\
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318
exporters:
  file/traces:
    path: /otel-out/traces.jsonl
    flush_interval: 100ms
  file/metrics:
    path: /otel-out/metrics.jsonl
    flush_interval: 100ms
  file/logs:
    path: /otel-out/logs.jsonl
    flush_interval: 100ms
service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [file/traces]
    metrics:
      receivers: [otlp]
      exporters: [file/metrics]
    logs:
      receivers: [otlp]
      exporters: [file/logs]
"""

# Same collector, but every signal is also forwarded to Elastic APM Server over OTLP/gRPC, as a collector-based
# production setup does (Elastic advises the ``otlp`` exporter, not the ``elasticsearch`` one).
OTEL_COLLECTOR_APM_CONFIG_TEMPLATE: str = (
    OTEL_COLLECTOR_CONFIG.replace(
        "exporters:\n  file/traces:",
        "exporters:\n  otlp/apm:\n    endpoint: {apm_endpoint}\n    tls:\n      insecure: true\n  file/traces:",
        1,
    )
    .replace("[file/traces]", "[file/traces, otlp/apm]")
    .replace("[file/metrics]", "[file/metrics, otlp/apm]")
    .replace("[file/logs]", "[file/logs, otlp/apm]")
)


@ContainerManager.register("otel-collector")
class OtelCollectorTestContainer(metaclass=Singleton, thread_safe=True):
    """Test container for the official OpenTelemetry Collector (contrib distribution).

    The collector accepts OTLP over gRPC (4317) and HTTP (4318) and writes every signal to an OTLP JSON
    lines file in a directory shared with the host. The image has no shell, so tests read those files
    directly instead of using ``exec``. Call ``mark()`` at the start of a scenario and ``read_signal()``
    afterwards to see only what the scenario exported.
    """

    GRPC_PORT = 4317
    HTTP_PORT = 4318
    SIGNALS = ("traces", "metrics", "logs")
    SHARED_KEY = "otel_collector"

    def __init__(self, image: str | None = None) -> None:
        """Initialize the collector test container.

        Args:
            image: Docker image override. Defaults to OTEL_COLLECTOR__IMAGE from TestConfig.
        """
        self.name = "otel-collector"
        self.image = image or BaseConfig.global_config().OTEL_COLLECTOR__IMAGE
        self._container: DockerContainer | None = None
        self._work_dir: tempfile.TemporaryDirectory | None = None
        self._offsets: dict[str, int] = dict.fromkeys(self.SIGNALS, 0)
        self._is_running = False
        self._shared_out_dir: Path | None = None
        self.host: str | None = None
        self.grpc_endpoint: str | None = None
        self.http_endpoint: str | None = None

    @property
    def out_dir(self) -> Path:
        """Directory the collector writes its OTLP JSON lines to."""
        if self._shared_out_dir is not None:
            return self._shared_out_dir
        if self._work_dir is None:
            raise RuntimeError("OpenTelemetry Collector is not running")
        return Path(self._work_dir.name) / "out"

    def _build(self) -> DockerContainer:
        self._work_dir = tempfile.TemporaryDirectory()
        work_path = Path(self._work_dir.name)
        config_dir = work_path / "config"
        out_dir = work_path / "out"
        config_dir.mkdir()
        out_dir.mkdir()
        # The collector runs as an unprivileged user and must be able to create the output files.
        out_dir.chmod(0o777)
        (config_dir / "config.yaml").write_text(self._config())
        return (
            DockerContainer(self.image)
            .with_exposed_ports(self.GRPC_PORT, self.HTTP_PORT)
            .with_volume_mapping(str(config_dir), "/otel-config", "ro")
            .with_volume_mapping(str(out_dir), "/otel-out", "rw")
            .with_command("--config=/otel-config/config.yaml")
            .with_kwargs(
                mem_limit=CONTAINER_MEM_LIMITS["otel-collector"],
                extra_hosts={"host.docker.internal": "host-gateway"},
            )
        )

    def _config(self) -> str:
        return OTEL_COLLECTOR_CONFIG

    def start(self) -> DockerContainer | None:
        """Start the collector and wait until its OTLP receivers are listening, or adopt the shared one."""
        if self._is_running:
            return self._container

        shared = shared_telemetry_stack()
        if shared is not None and self.SHARED_KEY in shared:
            entry = shared[self.SHARED_KEY]
            self.grpc_endpoint = entry["grpc"]
            self.http_endpoint = entry["http"]
            self._shared_out_dir = Path(entry["out_dir"])
            self._offsets = dict.fromkeys(self.SIGNALS, 0)
            self._is_running = True
            return None

        if self._container is None:
            self._container = self._build()

        self._container.start()
        wait_for_logs(self._container, r"Everything is ready", timeout=60)
        self._is_running = True

        self.host = self._container.get_container_host_ip()
        self.grpc_endpoint = f"http://{self.host}:{self._container.get_exposed_port(self.GRPC_PORT)}"
        self.http_endpoint = f"http://{self.host}:{self._container.get_exposed_port(self.HTTP_PORT)}"
        self._offsets = dict.fromkeys(self.SIGNALS, 0)

        logger.info("OpenTelemetry Collector started: gRPC %s, HTTP %s", self.grpc_endpoint, self.http_endpoint)
        return self._container

    def stop(self) -> None:
        """Stop the collector and remove its working directory."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()
        if self._work_dir:
            self._work_dir.cleanup()

        self._container = None
        self._work_dir = None
        self._shared_out_dir = None
        self._is_running = False
        self.host = None
        self.grpc_endpoint = None
        self.http_endpoint = None

        logger.info("OpenTelemetry Collector stopped")

    def _signal_path(self, signal: str) -> Path:
        return self.out_dir / f"{signal}.jsonl"

    def mark(self) -> None:
        """Remember the current end of every signal file so later reads ignore older data."""
        for signal in self.SIGNALS:
            path = self._signal_path(signal)
            self._offsets[signal] = path.stat().st_size if path.exists() else 0

    def read_signal(self, signal: str) -> list[dict]:
        """Return the OTLP JSON export requests written since the last ``mark()``.

        Args:
            signal: One of ``traces``, ``metrics`` or ``logs``.

        Returns:
            list[dict]: One parsed OTLP JSON document per exported batch, oldest first.
        """
        path = self._signal_path(signal)
        if not path.exists():
            return []
        with path.open("rb") as handle:
            handle.seek(self._offsets[signal])
            payload = handle.read()
        documents: list[dict] = []
        for line in payload.decode("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                documents.append(json.loads(line))
            except json.JSONDecodeError:
                # The exporter may be mid-write on the last line; the next read picks it up.
                break
        return documents


@ContainerManager.register("pushgateway")
class PushgatewayTestContainer(metaclass=Singleton, thread_safe=True):
    """Test container for the official Prometheus Pushgateway with the admin API enabled."""

    PORT = 9091

    def __init__(self, image: str | None = None) -> None:
        """Initialize the Pushgateway test container.

        Args:
            image: Docker image override. Defaults to PUSHGATEWAY__IMAGE from TestConfig.
        """
        self.name = "pushgateway"
        self.image = image or BaseConfig.global_config().PUSHGATEWAY__IMAGE
        self._container: DockerContainer | None = None
        self._is_running = False
        self.host: str | None = None
        self.url: str | None = None

    def _build(self) -> DockerContainer:
        return (
            DockerContainer(self.image)
            .with_exposed_ports(self.PORT)
            .with_command("--web.enable-admin-api")
            .with_kwargs(mem_limit=CONTAINER_MEM_LIMITS["pushgateway"])
        )

    def start(self) -> DockerContainer:
        """Start the Pushgateway and wait until it listens."""
        if self._is_running:
            return self._container

        if self._container is None:
            self._container = self._build()

        self._container.start()
        wait_for_logs(self._container, r"Listening on", timeout=60)
        self._is_running = True

        self.host = self._container.get_container_host_ip()
        self.url = f"http://{self.host}:{self._container.get_exposed_port(self.PORT)}"

        logger.info("Pushgateway container started at %s", self.url)
        return self._container

    def stop(self) -> None:
        """Stop the Pushgateway container."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()

        self._container = None
        self._is_running = False
        self.host = None
        self.url = None

        logger.info("Pushgateway container stopped")

    def groups(self) -> list[dict]:
        """Return the metric groups currently stored, as reported by ``/api/v1/metrics``."""
        response = httpx2.get(f"{self.url}/api/v1/metrics", timeout=5)
        response.raise_for_status()
        return response.json().get("data", [])

    def clear(self) -> None:
        """Delete every stored group through the admin API."""
        response = httpx2.put(f"{self.url}/api/v1/admin/wipe", timeout=5)
        response.raise_for_status()


APM_SERVER_CONFIG_TEMPLATE = """\
apm-server:
  host: "0.0.0.0:8200"
  auth.anonymous.enabled: true
  # Standalone mode without Kibana: the apm-data plugin of Elasticsearch already ships the index templates.
  data_streams.wait_for_integration: false
output.elasticsearch:
  hosts: ["{elasticsearch_url}"]
  # Index what arrived almost at once; the default of one second only slows the assertions down.
  flush_interval: 100ms
"""

# A parallel run starts the collector and the Elastic APM stack once for every feature process
# (``scripts/behave_parallel.py`` through ``python -m features.shared_telemetry_stack``) and passes their
# endpoints here as JSON: ``elasticsearch_url`` and ``apm_endpoint`` for APM Server, and one
# ``{"grpc", "http", "out_dir"}`` entry per collector (``otel_collector``, ``apm_collector``).
SHARED_TELEMETRY_ENV = "ARCHIPY_SHARED_TELEMETRY"


def shared_telemetry_stack() -> dict | None:
    """Return the endpoints of the stack another process started, or None when this process owns its own."""
    raw = os.environ.get(SHARED_TELEMETRY_ENV)
    return json.loads(raw) if raw else None



@ContainerManager.register("apm-server")
class ApmServerTestContainer(metaclass=Singleton, thread_safe=True):
    """Test container for the official Elastic APM Server in standalone mode, with an Elasticsearch of its own.

    It accepts OTLP over gRPC and HTTP on one port and stores traces, metrics and logs in the APM data streams, so
    tests can check what Elastic APM would show (for example ``transaction.type``). Kibana is not needed.

    When ``ARCHIPY_SHARED_TELEMETRY`` is set, another process already runs the stack and this class only points at it;
    every scenario exports under its own ``service.name``, so scenarios sharing the stack do not see each other.
    """

    PORT = 8200
    TRACES_INDEX = "traces-apm*"

    def __init__(self, image: str | None = None) -> None:
        """Initialize the APM Server test container.

        Args:
            image: Docker image override. Defaults to APM_SERVER__IMAGE from TestConfig.
        """
        self.name = "apm-server"
        self.image = image or BaseConfig.global_config().APM_SERVER__IMAGE
        self._container: DockerContainer | None = None
        self._elasticsearch: ElasticSearchContainer | None = None
        self._work_dir: tempfile.TemporaryDirectory | None = None
        self._is_running = False
        self.host: str | None = None
        self.grpc_endpoint: str | None = None
        self.http_endpoint: str | None = None
        self.port: int | None = None
        self.elasticsearch_url: str | None = None

    def _build(self, elasticsearch_port: int) -> DockerContainer:
        self._work_dir = tempfile.TemporaryDirectory()
        config_path = Path(self._work_dir.name) / "apm-server.yml"
        # APM Server rejects a config file that other users can write.
        config_path.write_text(
            APM_SERVER_CONFIG_TEMPLATE.format(elasticsearch_url=f"http://host.docker.internal:{elasticsearch_port}"),
        )
        config_path.chmod(0o644)
        return (
            DockerContainer(self.image)
            .with_exposed_ports(self.PORT)
            .with_volume_mapping(str(config_path), "/usr/share/apm-server/apm-server.yml", "ro")
            .with_kwargs(
                mem_limit=CONTAINER_MEM_LIMITS["apm-server"],
                extra_hosts={"host.docker.internal": "host-gateway"},
            )
        )

    def start(self) -> DockerContainer | None:
        """Start Elasticsearch and APM Server and wait until the intake answers, or adopt the shared stack."""
        if self._is_running:
            return self._container

        shared = shared_telemetry_stack()
        if shared is not None and "apm_endpoint" in shared:
            self.elasticsearch_url = shared["elasticsearch_url"]
            self.grpc_endpoint = shared["apm_endpoint"]
            self.http_endpoint = self.grpc_endpoint
            self.port = int(self.grpc_endpoint.rsplit(":", 1)[1])
            self._is_running = True
            return None

        self._elasticsearch = _build_elasticsearch_container(BaseConfig.global_config().ELASTIC__IMAGE)
        self._elasticsearch.start()
        elasticsearch_host = self._elasticsearch.get_container_host_ip()
        elasticsearch_port = int(self._elasticsearch.get_exposed_port(9200))
        self.elasticsearch_url = f"http://{elasticsearch_host}:{elasticsearch_port}"
        _wait_for_elasticsearch(self.elasticsearch_url)

        self._container = self._build(elasticsearch_port)
        self._container.start()
        wait_for_logs(self._container, r"no longer blocking ingestion", timeout=120)
        self._is_running = True

        self.host = self._container.get_container_host_ip()
        port = self._container.get_exposed_port(self.PORT)
        self.port = int(port)
        self.grpc_endpoint = f"http://{self.host}:{port}"
        self.http_endpoint = self.grpc_endpoint

        logger.info("Elastic APM Server started at %s", self.http_endpoint)
        return self._container

    def stop(self) -> None:
        """Stop APM Server and its Elasticsearch; a shared stack belongs to the process that started it."""
        if not self._is_running:
            return

        if self._container:
            self._container.stop()
        if self._elasticsearch:
            self._elasticsearch.stop()
        if self._work_dir:
            self._work_dir.cleanup()

        self._container = None
        self._elasticsearch = None
        self._work_dir = None
        self._is_running = False
        self.host = None
        self.grpc_endpoint = None
        self.http_endpoint = None
        self.port = None
        self.elasticsearch_url = None

        logger.info("Elastic APM Server stopped")

    def events(self, service_name: str) -> list[dict]:
        """Return the stored APM transactions and spans of one service.

        Args:
            service_name: ``service.name`` the application exported with.

        Returns:
            list[dict]: Each document's ``_source`` limited to the event kind, name, type and subtype fields.
        """
        base = f"{self.elasticsearch_url}/{self.TRACES_INDEX}"
        # The test process is instrumented too; its own queries must not show up as traces of the scenario.
        with suppress_instrumentation():
            httpx2.post(f"{base}/_refresh", timeout=10)
            response = httpx2.post(
                f"{base}/_search",
                json={
                    "size": 200,
                    "query": {"term": {"service.name": service_name}},
                    "_source": [
                        "processor.event",
                        "transaction.name",
                        "transaction.type",
                        "span.name",
                        "span.type",
                        "span.subtype",
                    ],
                },
                timeout=10,
            )
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return [hit["_source"] for hit in response.json()["hits"]["hits"]]

    def _search(self, index: str, body: dict) -> list[dict]:
        base = f"{self.elasticsearch_url}/{index}"
        # The test process is instrumented too; its own queries must not show up as telemetry of the scenario.
        with suppress_instrumentation():
            httpx2.post(f"{base}/_refresh", timeout=10)
            response = httpx2.post(f"{base}/_search", json={"size": 200, **body}, timeout=10)
        if response.status_code == 404:
            return []
        response.raise_for_status()
        return [hit["_source"] for hit in response.json()["hits"]["hits"]]

    def metric_names(self, service_name: str, labels: dict[str, str] | None = None) -> set[str]:
        """Return the names of the application metrics stored for one service.

        Args:
            service_name: ``service.name`` the application exported with.
            labels: Optional metric labels every stored document must carry (for example ``task_queue``).

        Returns:
            set[str]: The metric field names Elastic APM stored (for example ``test.work.calls``).
        """
        filters = [{"term": {"service.name": service_name}}]
        filters += [{"term": {f"labels.{key}": value}} for key, value in (labels or {}).items()]
        documents = self._search("metrics-apm.app.*", {"query": {"bool": {"filter": filters}}})
        # Application metrics are stored as top-level fields next to the metadata objects.
        metadata = {"@timestamp", "agent", "cloud", "data_stream", "ecs", "event", "host", "labels", "metricset"}
        metadata |= {"observer", "processor", "service", "tags", "timestamp_us", "_metric_descriptions"}
        return {key for document in documents for key in document if key not in metadata}

    def logs(self, service_name: str) -> list[dict]:
        """Return the stored application logs of one service with their message and trace id."""
        return self._search(
            "logs-apm.app.*",
            {"query": {"term": {"service.name": service_name}}, "_source": ["message", "log.level", "trace.id"]},
        )

    def transactions(self, service_name: str) -> list[dict]:
        """Return the stored APM transactions of one service."""
        return [item for item in self.events(service_name) if item["processor"]["event"] == "transaction"]


@ContainerManager.register("otel-collector-apm")
class ApmForwardingCollectorTestContainer(OtelCollectorTestContainer):
    """OpenTelemetry Collector that also forwards every signal to the Elastic APM Server container.

    It keeps the file exporters of ``OtelCollectorTestContainer``, so tests can read what the collector received
    and, through ``ApmServerTestContainer``, what Elasticsearch stored.
    """

    SHARED_KEY = "apm_collector"

    def __init__(self, image: str | None = None) -> None:
        """Initialize the forwarding collector.

        Args:
            image: Docker image override. Defaults to OTEL_COLLECTOR__IMAGE from TestConfig.
        """
        super().__init__(image)
        self.name = "otel-collector-apm"

    def _config(self) -> str:
        apm_server = ContainerManager.get_container("apm-server")
        return OTEL_COLLECTOR_APM_CONFIG_TEMPLATE.format(apm_endpoint=f"host.docker.internal:{apm_server.port}")
