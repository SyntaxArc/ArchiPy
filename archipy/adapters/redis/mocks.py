"""Mock Redis adapters for testing."""

from typing import TYPE_CHECKING, Any

import fakeredis
from fakeredis import FakeAsyncRedis, FakeServer

from archipy.adapters.redis.adapters import AsyncRedisAdapter, RedisAdapter
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import RedisConfig, RedisMode

if TYPE_CHECKING:
    from redis import RedisCluster
    from redis.asyncio import RedisCluster as AsyncRedisCluster
    from redis.asyncio.client import Redis as AsyncRedis
    from redis.client import Redis


def _fake_cluster_info() -> dict[str, Any]:
    """Return fake cluster info payload."""
    return {
        "cluster_state": "ok",
        "cluster_slots_assigned": 16384,
        "cluster_slots_ok": 16384,
        "cluster_slots_pfail": 0,
        "cluster_slots_fail": 0,
        "cluster_known_nodes": 6,
        "cluster_size": 3,
    }


def _fake_cluster_slots() -> list[tuple[int, int, list[str]]]:
    """Return fake cluster slots mapping."""
    slot1: tuple[int, int, list[str]] = (0, 5460, ["127.0.0.1", "7000"])
    slot2: tuple[int, int, list[str]] = (5461, 10922, ["127.0.0.1", "7001"])
    slot3: tuple[int, int, list[str]] = (10923, 16383, ["127.0.0.1", "7002"])
    return [slot1, slot2, slot3]


class FakeRedisClusterWrapper(fakeredis.FakeRedis):
    """Wrapper around FakeRedis that adds cluster-specific methods."""

    def cluster_info(self) -> dict[str, Any]:
        """Return fake cluster info."""
        return _fake_cluster_info()

    def cluster_nodes(self) -> str:
        """Return fake cluster nodes info."""
        return "fake cluster nodes info"

    def cluster_slots(self) -> list[tuple[int, int, list[str]]]:
        """Return fake cluster slots info."""
        return _fake_cluster_slots()

    def cluster_keyslot(self, key: str) -> int:
        """Return fake cluster keyslot for a key."""
        return hash(key) % 16384

    def cluster_countkeysinslot(self, slot: int) -> int:
        """Return fake count of keys in a slot."""
        return 0

    def cluster_get_keys_in_slot(self, slot: int, count: int) -> list[str]:
        """Return fake keys in a slot."""
        return []


class FakeAsyncRedisClusterWrapper(FakeAsyncRedis):
    """Wrapper around FakeAsyncRedis that adds cluster-specific methods."""

    async def cluster_info(self) -> dict[str, Any]:
        """Return fake cluster info."""
        return _fake_cluster_info()

    async def cluster_nodes(self) -> str:
        """Return fake cluster nodes info."""
        return "fake cluster nodes info"

    async def cluster_slots(self) -> list[tuple[int, int, list[str]]]:
        """Return fake cluster slots info."""
        return _fake_cluster_slots()

    async def cluster_keyslot(self, key: str) -> int:
        """Return fake cluster keyslot for a key."""
        return hash(key) % 16384

    async def cluster_countkeysinslot(self, slot: int) -> int:
        """Return fake count of keys in a slot."""
        return 0

    async def cluster_get_keys_in_slot(self, slot: int, count: int) -> list[str]:
        """Return fake keys in a slot."""
        return []


class RedisMock(RedisAdapter):
    """A Redis adapter implementation using fakeredis for testing."""

    def __init__(self, redis_config: RedisConfig | None = None) -> None:
        """Initialize RedisMock."""
        # Skip the parent's __init__ which would create real Redis connections
        self.config = redis_config or BaseConfig.global_config().REDIS
        self._configs = self.config
        self._server = FakeServer()
        self._search_client: Redis | RedisCluster | None = None

        # Create fake redis clients based on mode
        self._setup_fake_clients()

    def _setup_fake_clients(self) -> None:
        """Setup fake Redis clients that simulate different modes."""
        decode_responses = self.config.DECODE_RESPONSES
        if self.config.MODE == RedisMode.CLUSTER:
            fake_client: Redis = FakeRedisClusterWrapper(
                decode_responses=decode_responses,
                server=self._server,
            )
        else:
            fake_client = fakeredis.FakeRedis(
                decode_responses=decode_responses,
                server=self._server,
            )

        self.client = fake_client
        self.read_only_client = fake_client

    def _set_clients(self, configs: RedisConfig) -> None:
        # Override to prevent actual connection setup
        pass

    def _get_client(self, host: str, configs: RedisConfig, *, decode_responses: bool | None = None) -> Redis:
        return fakeredis.FakeRedis(
            decode_responses=configs.DECODE_RESPONSES if decode_responses is None else decode_responses,
            server=self._server,
        )

    def _get_search_client(self) -> Redis | RedisCluster:
        if self._search_client is None:
            self._search_client = fakeredis.FakeRedis(
                decode_responses=False,
                server=self._server,
            )
        return self._search_client


class AsyncRedisMock(AsyncRedisAdapter):
    """An async Redis adapter implementation using FakeAsyncRedis for testing."""

    def __init__(self, redis_config: RedisConfig | None = None) -> None:
        """Initialize AsyncRedisMock."""
        # Skip the parent's __init__ which would create real Redis connections
        self.config = redis_config or BaseConfig.global_config().REDIS
        self._configs = self.config
        self._server = FakeServer()
        self._search_client: AsyncRedis | AsyncRedisCluster | None = None

        # Create fake async redis clients based on mode
        self._setup_async_fake_clients()

    def _setup_async_fake_clients(self) -> None:
        """Setup fake async Redis clients that simulate different modes."""
        decode_responses = self.config.DECODE_RESPONSES
        if self.config.MODE == RedisMode.CLUSTER:
            fake_client: AsyncRedis = FakeAsyncRedisClusterWrapper(
                decode_responses=decode_responses,
                server=self._server,
            )
        else:
            fake_client = FakeAsyncRedis(
                decode_responses=decode_responses,
                server=self._server,
            )

        self.client = fake_client
        self.read_only_client = fake_client

    def _set_clients(self, configs: RedisConfig) -> None:
        # Override to prevent actual connection setup
        pass

    def _get_client(self, host: str, configs: RedisConfig, *, decode_responses: bool | None = None) -> AsyncRedis:
        return FakeAsyncRedis(
            decode_responses=configs.DECODE_RESPONSES if decode_responses is None else decode_responses,
            server=self._server,
        )

    def _get_search_client(self) -> AsyncRedis | AsyncRedisCluster:
        if self._search_client is None:
            self._search_client = FakeAsyncRedis(
                decode_responses=False,
                server=self._server,
            )
        return self._search_client
