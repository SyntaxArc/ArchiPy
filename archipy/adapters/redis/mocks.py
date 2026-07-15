from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import AsyncMock

import fakeredis
from redis.asyncio.client import Redis as AsyncRedis
from redis.client import Redis

from archipy.adapters.redis.adapters import AsyncRedisAdapter, RedisAdapter
from archipy.adapters.redis.ports import AsyncRedisPort
from archipy.configs.config_template import RedisConfig, RedisMode


class FakeRedisClusterWrapper(fakeredis.FakeRedis):
    """Wrapper around FakeRedis that adds cluster-specific methods."""

    def cluster_info(self) -> dict[str, Any]:
        """Return fake cluster info."""
        return {
            "cluster_state": "ok",
            "cluster_slots_assigned": 16384,
            "cluster_slots_ok": 16384,
            "cluster_slots_pfail": 0,
            "cluster_slots_fail": 0,
            "cluster_known_nodes": 6,
            "cluster_size": 3,
        }

    def cluster_nodes(self) -> str:
        """Return fake cluster nodes info."""
        return "fake cluster nodes info"

    def cluster_slots(self) -> list[tuple[int, int, list[str]]]:
        """Return fake cluster slots info."""
        slot1: tuple[int, int, list[str]] = (0, 5460, ["127.0.0.1", "7000"])
        slot2: tuple[int, int, list[str]] = (5461, 10922, ["127.0.0.1", "7001"])
        slot3: tuple[int, int, list[str]] = (10923, 16383, ["127.0.0.1", "7002"])
        return [slot1, slot2, slot3]

    def cluster_keyslot(self, key: str) -> int:
        """Return fake cluster keyslot for a key."""
        return hash(key) % 16384

    def cluster_countkeysinslot(self, slot: int) -> int:
        """Return fake count of keys in a slot."""
        return 0

    def cluster_get_keys_in_slot(self, slot: int, count: int) -> list[str]:
        """Return fake keys in a slot."""
        return []


class RedisMock(RedisAdapter):
    """A Redis adapter implementation using fakeredis for testing."""

    def __init__(self, redis_config: RedisConfig | None = None) -> None:
        # Skip the parent's __init__ which would create real Redis connections
        from archipy.configs.base_config import BaseConfig

        self.config = redis_config or BaseConfig.global_config().REDIS
        self._configs = self.config
        self._search_client: Redis | None = None

        # Create fake redis clients based on mode
        self._setup_fake_clients()

    def _setup_fake_clients(self) -> None:
        """Setup fake Redis clients that simulate different modes."""
        if self.config.MODE == RedisMode.CLUSTER:
            fake_client: Redis = FakeRedisClusterWrapper(decode_responses=True)
        else:
            fake_client = fakeredis.FakeRedis(decode_responses=True)

        self.client = fake_client
        self.read_only_client = fake_client

    def _set_clients(self, configs: RedisConfig) -> None:
        # Override to prevent actual connection setup
        pass

    @staticmethod
    def _get_client(host: str, configs: RedisConfig, *, decode_responses: bool | None = None) -> Redis:
        return fakeredis.FakeRedis(
            decode_responses=configs.DECODE_RESPONSES if decode_responses is None else decode_responses,
        )

    def _get_search_client(self) -> Redis:
        if self._search_client is None:
            self._search_client = fakeredis.FakeRedis(decode_responses=False)
        return self._search_client


class AsyncRedisMock(AsyncRedisAdapter):
    """An async Redis adapter implementation using fakeredis for testing."""

    def __init__(self, redis_config: RedisConfig | None = None) -> None:
        # Skip the parent's __init__ which would create real Redis connections
        from archipy.configs.base_config import BaseConfig

        self.config = redis_config or BaseConfig.global_config().REDIS
        self._configs = self.config
        self._search_client: AsyncRedis | None = None

        # Create fake async redis clients based on mode
        self._setup_async_fake_clients()

    def _setup_async_fake_clients(self) -> None:
        """Setup fake async Redis clients that simulate different modes."""
        self.client = AsyncMock()
        self.read_only_client = self.client

        # Create a synchronous fakeredis instance to handle the actual operations
        self._fake_redis = fakeredis.FakeRedis(decode_responses=True)

        # Set up basic async methods
        self._setup_async_methods()

        # Add mode-specific methods
        if self.config.MODE == RedisMode.CLUSTER:
            # Add cluster-specific async mock methods
            self.client.cluster_info.side_effect = lambda: {
                "cluster_state": "ok",
                "cluster_slots_assigned": 16384,
                "cluster_slots_ok": 16384,
                "cluster_slots_pfail": 0,
                "cluster_slots_fail": 0,
                "cluster_known_nodes": 6,
                "cluster_size": 3,
            }
            self.client.cluster_nodes.side_effect = lambda: "fake cluster nodes info"
            self.client.cluster_slots.side_effect = lambda: [
                (0, 5460, ["127.0.0.1", 7000]),
                (5461, 10922, ["127.0.0.1", 7001]),
                (10923, 16383, ["127.0.0.1", 7002]),
            ]
            self.client.cluster_keyslot.side_effect = lambda key: hash(key) % 16384
            self.client.cluster_countkeysinslot.side_effect = lambda slot: 0
            self.client.cluster_get_keys_in_slot.side_effect = lambda slot, count: []

    def _set_clients(self, configs: RedisConfig) -> None:
        # Override to prevent actual connection setup
        pass

    @staticmethod
    def _get_client(host: str, configs: RedisConfig, *, decode_responses: bool | None = None) -> AsyncRedis:
        return AsyncMock()

    def _get_search_client(self) -> AsyncRedis:
        if self._search_client is None:
            self._search_client = AsyncMock()
            self._search_client.execute_command = self._create_async_wrapper(
                "execute_command",
                self._fake_redis.execute_command,
            )
        return self._search_client

    def _setup_async_methods(self) -> None:
        """Set up all async methods to use a synchronous fakeredis under the hood."""
        # For each async method, implement it to use the synchronous fakeredis
        for method_name in dir(AsyncRedisPort):
            if not method_name.startswith("_") and method_name not in ("pubsub", "get_pipeline"):
                sync_method = getattr(self._fake_redis, method_name, None)
                if sync_method and callable(sync_method):
                    async_method = self._create_async_wrapper(method_name, sync_method)
                    setattr(self.client, method_name, async_method)
                    setattr(self.read_only_client, method_name, async_method)

    def _create_async_wrapper(
        self,
        method_name: str,
        sync_method: Callable[..., Any],
    ) -> Callable[..., Awaitable[Any]]:
        """Create an async wrapper around a synchronous method."""

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Remove 'self' from args when calling the sync method
            if args and args[0] is self:
                args = args[1:]
            return sync_method(*args, **kwargs)

        return wrapper
