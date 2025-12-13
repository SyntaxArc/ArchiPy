from ipaddress import ip_address
from math import ceil

from fastapi import HTTPException, Request
from pydantic import StrictInt, StrictStr
from starlette.datastructures import QueryParams
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from archipy.adapters.redis.adapters import AsyncRedisAdapter
from archipy.adapters.redis.ports import RedisResponseType


class FastAPIRestRateLimitHandler:
    """A rate-limiting handler for FastAPI REST endpoints using Redis for tracking.

    This class provides rate-limiting functionality by tracking the number of requests
    made to a specific endpoint within a defined time window. If the request limit is
    exceeded, it raises an HTTP 429 Too Many Requests error.

    Args:
        calls_count (StrictInt): The maximum number of allowed requests within the time window.
        milliseconds (StrictInt): The time window in milliseconds.
        seconds (StrictInt): The time window in seconds.
        minutes (StrictInt): The time window in minutes.
        hours (StrictInt): The time window in hours.
        days (StrictInt): The time window in days.
        query_params (set(StrictStr)): request query parameters for rate-limiting based on query params.
    """

    def __init__(
        self,
        calls_count: StrictInt = 1,
        milliseconds: StrictInt = 0,
        seconds: StrictInt = 0,
        minutes: StrictInt = 0,
        hours: StrictInt = 0,
        days: StrictInt = 0,
        query_params: set[StrictStr] | None = None,
    ) -> None:
        """Initialize the rate limit handler with specified time window and request limits.

        The time window is calculated by combining all time unit parameters into milliseconds.
        At least one time unit parameter should be greater than 0 to create a valid window.

        Args:
            calls_count (StrictInt, optional): Maximum number of allowed requests within the time window.
                Defaults to 1.
            milliseconds (StrictInt, optional): Number of milliseconds in the time window.
                Defaults to 0.
            seconds (StrictInt, optional): Number of seconds in the time window.
                Defaults to 0.
            minutes (StrictInt, optional): Number of minutes in the time window.
                Defaults to 0.
            hours (StrictInt, optional): Number of hours in the time window.
                Defaults to 0.
            days (StrictInt, optional): Number of days in the time window.
                Defaults to 0.
            query_params (set[StrictStr] | None, optional): Set of query parameter names to include
                in rate limit key generation. If None, no query parameters will be used.
                Defaults to None.

        Example:
            >>> # Allow 100 requests per minute
            >>> handler = FastAPIRestRateLimitHandler(calls_count=100, minutes=1)
            >>>
            >>> # Allow 1000 requests per day with specific query params
            >>> handler = FastAPIRestRateLimitHandler(calls_count=1000, days=1, query_params={"user_id", "action"})
        """
        self.query_params = query_params or set()
        self.calls_count = calls_count
        # Calculate total time in milliseconds directly for better readability
        self.milliseconds = (
            milliseconds + 1000 * seconds + 60 * 1000 * minutes + 60 * 60 * 1000 * hours + 24 * 60 * 60 * 1000 * days
        )
        self.redis_client = AsyncRedisAdapter()

    async def _check(self, key: str) -> RedisResponseType:
        """Checks if the request count for the given key exceeds the allowed limit.

        Args:
            key (str): The Redis key used to track the request count.

        Returns:
            int: The remaining time-to-live (TTL) in milliseconds if the limit is exceeded, otherwise 0.
        """
        # Use await for getting value from Redis as it's asynchronous
        current_request = await self.redis_client.get(key)
        if current_request is None:
            await self.redis_client.set(key, 1, px=self.milliseconds)
            return 0

        current_request = int(current_request)
        if current_request < self.calls_count:
            await self.redis_client.incrby(key)
            return 0

        ttl = await self.redis_client.pttl(key)
        if ttl == -1:
            await self.redis_client.delete(key)
        return ttl

    async def __call__(self, request: Request) -> None:
        """Handles the rate-limiting logic for incoming requests.

        Args:
            request (Request): The incoming FastAPI request.

        Raises:
            HTTPException: If the rate limit is exceeded, an HTTP 429 Too Many Requests error is raised.
        """
        rate_key = await self._get_identifier(request)
        key = f"RateLimitHandler:{rate_key}:{request.scope['path']}:{request.method}"
        pexpire = await self._check(key)  # Awaiting the function since it is an async call
        if pexpire != 0:
            await self._create_callback(pexpire)

    @staticmethod
    async def _create_callback(pexpire: int) -> None:
        """Raises an HTTP 429 Too Many Requests error with the appropriate headers.

        Args:
            pexpire (int): The remaining time-to-live (TTL) in milliseconds before the rate limit resets.

        Raises:
            HTTPException: An HTTP 429 Too Many Requests error with the `Retry-After` header.
        """
        expire = ceil(pexpire / 1000)
        raise HTTPException(
            status_code=HTTP_429_TOO_MANY_REQUESTS,
            detail="Too Many Requests",
            headers={"Retry-After": str(expire)},
        )

    async def _get_identifier(self, request: Request) -> str:
        """Extracts a unique identifier from the request, typically an IP address and endpoint.

        Args:
            request (Request): The FastAPI request object containing headers and client info.

        Returns:
            str: A Redis key generated using the extracted identifier and request information.

        Note:
            - Validates IP addresses for proper formatting
            - Handles forwarded IPs with comma-separated values
            - Filters out private, loopback, link-local, and multicast IPs in X-Forwarded-For
            - Falls back to client.host if no valid IP is found
        """
        base_identifier = await self._extract_client_ip(request)
        return self._generate_redis_key(request=request, base_identifier=base_identifier)

    async def _extract_client_ip(self, request: Request) -> str:
        """Extracts and validates client IP from request headers.

        Args:
            request (Request): The FastAPI request object.

        Returns:
            str: Validated IP address or client host.
        """
        # Check X-Real-IP header first
        if real_ip := self._validate_ip_from_header(request.headers.get("X-Real-IP")):
            return real_ip

        # Then check X-Forwarded-For header
        if forwarded_for := self._validate_forwarded_for_header(request.headers.get("X-Forwarded-For")):
            return forwarded_for

        # Fallback to client host
        if request.client is not None:
            return request.client.host
        return "unknown"

    def _validate_ip_from_header(self, header_value: str | None) -> str | None:
        """Validates IP address from header value.

        Args:
            header_value (Optional[str]): IP address from header.

        Returns:
            Optional[str]: First valid IP address or None.
        """
        if not header_value:
            return None

        try:
            ip_str = header_value.split(",")[0].strip()
            ip = ip_address(ip_str)  # Validate IP format
            if not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast):
                return ip_str
        except ValueError:
            pass

        return None

    def _validate_forwarded_for_header(self, forwarded_for: str | None) -> str | None:
        """Validates IP from X-Forwarded-For header.

        Args:
            forwarded_for (Optional[str]): X-Forwarded-For header value.

        Returns:
            Optional[str]: Valid non-private IP, the header or None.
        """
        if not forwarded_for:
            return None

        try:
            ip_str = forwarded_for.split(",")[0].strip()
            ip = ip_address(ip_str)

            if not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast):
                return ip_str

        except ValueError:
            pass
        return forwarded_for

    def _generate_redis_key(self, request: Request, base_identifier: str) -> str:
        """Generates a Redis key for rate limiting based on the request and base identifier.

        Args:
            request (Request): The FastAPI request object containing path and query parameters.
            base_identifier (str): The base identifier (typically an IP address) for the request.

        Returns:
            str: A Redis key string with optional query parameters.
        """
        path_key = f"{base_identifier}:{request.scope['path']}"

        if not self.query_params:
            return path_key

        return self._append_query_params(path_key, request.query_params)

    def _append_query_params(self, base_key: str, query_params: QueryParams) -> str:
        """Appends sorted query parameters to the Redis key.

        Args:
            base_key (str): Base Redis key without query parameters.
            query_params (dict[str, str]): Request query parameters.

        Returns:
            str: Redis key with appended query parameters.
        """
        filtered_params = {k: v for k, v in query_params.items() if k in self.query_params and v is not None}

        if not filtered_params:
            return base_key

        sorted_params = sorted(filtered_params.items())
        query_string = "&".join(f"{k}={v}" for k, v in sorted_params)
        return f"{base_key}?{query_string}"
