"""Keycloak authentication and authorization guards for FastAPI and gRPC."""

from __future__ import annotations

import functools
import hashlib
import inspect
import logging
import threading
import time
from contextvars import ContextVar
from functools import cache
from typing import TYPE_CHECKING, Any, NoReturn

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable, Iterator

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from archipy.adapters.keycloak.adapters import AsyncKeycloakAdapter, KeycloakAdapter
from archipy.models.dtos.keycloak_dtos import ActorDTO, AuthenticatedUserDTO
from archipy.models.errors import (
    BaseError,
    InternalError,
    InvalidArgumentError,
    PermissionDeniedError,
    TokenExpiredError,
    UnauthenticatedError,
)
from archipy.models.types.actor_type import ActorType
from archipy.models.types.language_type import LanguageType

# Enhanced security scheme with OpenAPI documentation
security = HTTPBearer(scheme_name="OAuth2", description="OAuth2 Access Token", auto_error=False)

# Default language for errors
DEFAULT_LANG = LanguageType.FA

logger = logging.getLogger(__name__)

# Guard against pathological nested ``act`` claims.
_MAX_ACTOR_DEPTH = 8

_REMOTE_CACHE_MAX_SIZE = 1024
_remote_cache: dict[tuple[Any, ...], tuple[float, Any]] = {}
_remote_cache_lock = threading.Lock()


def _remote_cache_ttl(keycloak: KeycloakAdapter | AsyncKeycloakAdapter) -> float:
    """Return the configured remote-lookup cache TTL in seconds (0 means disabled)."""
    return float(getattr(keycloak.configs, "REMOTE_CACHE_TTL_SECONDS", 0) or 0)


def _remote_cache_key(
    keycloak: KeycloakAdapter | AsyncKeycloakAdapter,
    operation: str,
    token_str: str,
    extra: object = None,
) -> tuple[Any, ...]:
    """Build a cache key from a token digest so raw tokens are never kept as keys."""
    digest = hashlib.sha256(token_str.encode()).hexdigest()
    return (id(keycloak.configs), operation, digest, extra)


def _remote_cache_get(key: tuple[Any, ...]) -> tuple[bool, Any]:
    """Return ``(hit, value)`` for a non-expired entry; expired entries are dropped."""
    with _remote_cache_lock:
        entry = _remote_cache.get(key)
        if entry is None:
            return False, None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            _remote_cache.pop(key, None)
            return False, None
        return True, value


def _remote_cache_set(key: tuple[Any, ...], value: object, ttl: float) -> None:
    """Store a value, evicting expired and then oldest entries when the cache is full."""
    now = time.monotonic()
    with _remote_cache_lock:
        if key not in _remote_cache and len(_remote_cache) >= _REMOTE_CACHE_MAX_SIZE:
            for stale in [k for k, (expires_at, _) in _remote_cache.items() if expires_at <= now]:
                _remote_cache.pop(stale, None)
            while len(_remote_cache) >= _REMOTE_CACHE_MAX_SIZE:
                _remote_cache.pop(next(iter(_remote_cache)), None)
        _remote_cache[key] = (now + ttl, value)


def clear_keycloak_remote_cache() -> None:
    """Drop every cached UserInfo / permission lookup (useful in tests or after a revocation event)."""
    with _remote_cache_lock:
        _remote_cache.clear()


def _cached_sync_lookup(
    keycloak: KeycloakAdapter,
    operation: str,
    token_str: str,
    extra: object,
    fetch: Callable[[], Any],
) -> Any:  # noqa: ANN401
    """Run a remote Keycloak lookup through the opt-in TTL cache; only truthy results are cached."""
    ttl = _remote_cache_ttl(keycloak)
    if ttl <= 0:
        return fetch()
    key = _remote_cache_key(keycloak, operation, token_str, extra)
    hit, value = _remote_cache_get(key)
    if hit:
        return value
    value = fetch()
    if value:
        _remote_cache_set(key, value, ttl)
    return value


async def _cached_async_lookup(
    keycloak: AsyncKeycloakAdapter,
    operation: str,
    token_str: str,
    extra: object,
    fetch: Callable[[], Awaitable[Any]],
) -> Any:  # noqa: ANN401
    """Async variant of :func:`_cached_sync_lookup`."""
    ttl = _remote_cache_ttl(keycloak)
    if ttl <= 0:
        return await fetch()
    key = _remote_cache_key(keycloak, operation, token_str, extra)
    hit, value = _remote_cache_get(key)
    if hit:
        return value
    value = await fetch()
    if value:
        _remote_cache_set(key, value, ttl)
    return value


def _raise_unauthenticated(lang: LanguageType) -> NoReturn:
    """Raise UnauthenticatedError outside try bodies (TRY301)."""
    raise UnauthenticatedError(lang=lang)


def _raise_invalid_argument(argument_name: str, lang: LanguageType) -> NoReturn:
    """Raise InvalidArgumentError outside try bodies (TRY301)."""
    raise InvalidArgumentError(argument_name=argument_name, lang=lang)


@cache
def _shared_sync_adapter() -> KeycloakAdapter:
    """Return a process-wide shared synchronous Keycloak adapter."""
    return KeycloakAdapter()


@cache
def _shared_async_adapter() -> AsyncKeycloakAdapter:
    """Return a process-wide shared asynchronous Keycloak adapter."""
    return AsyncKeycloakAdapter()


def _abort_grpc_sync_if_servicer_context(error: BaseError, context: object) -> None:
    """Abort ``context`` with ``error`` when it is a sync gRPC servicer context."""
    if GRPC_AVAILABLE and isinstance(context, ServicerContext):
        abort_grpc(error, context)


async def _abort_grpc_async_if_servicer_context(error: BaseError, context: object) -> None:
    """Abort ``context`` with ``error`` when it is an async gRPC servicer context."""
    if GRPC_AVAILABLE and isinstance(context, AsyncServicerContext):
        await abort_grpc(error, context)


try:
    from grpc import ServicerContext, StatusCode as _GrpcStatusCode
    from grpc.aio import AbortError as _GrpcAioAbortError, ServicerContext as AsyncServicerContext

    from archipy.helpers.errors.grpc.abort import abort_grpc

    GRPC_AVAILABLE = True

    _AIO_ABORT_ERRORS: tuple[type[BaseException], ...] = (_GrpcAioAbortError,)
except ImportError:
    GRPC_AVAILABLE = False
    _GrpcStatusCode = None
    _AIO_ABORT_ERRORS = ()


def _is_sync_context_abort(error: Exception, context: object) -> bool:
    """Tell whether ``error`` is the bare exception that ``context.abort()`` raises on a sync servicer context.

    Such an exception already carries a deliberate status (set by the handler or an inner decorator) and must
    pass through instead of being rewritten as an internal error.
    """
    code_getter = getattr(context, "code", None)
    if type(error) is not Exception or not callable(code_getter):
        return False
    return code_getter() not in {None, getattr(_GrpcStatusCode, "OK", None)}


def _raise_sync_failure(error: Exception, context: object, lang: LanguageType) -> NoReturn:
    """Abort the sync gRPC call for ``error`` and raise; unexpected failures are hidden behind an internal error."""
    if _is_sync_context_abort(error, context):
        raise error
    if isinstance(error, BaseError):
        _abort_grpc_sync_if_servicer_context(error, context)
        raise error
    logger.error("Unexpected failure in gRPC handler", exc_info=error)
    # Internal details stay in the log; the client only sees a generic error.
    raise InternalError(lang=lang) from error


async def _abort_async_failure(error: Exception, context: object, lang: LanguageType) -> None:
    """Abort the async gRPC call for ``error``; re-raise when the context cannot be aborted."""
    if isinstance(error, _AIO_ABORT_ERRORS):
        raise error
    if context is None:
        raise error
    if isinstance(error, BaseError) and GRPC_AVAILABLE and isinstance(context, AsyncServicerContext):
        await _abort_grpc_async_if_servicer_context(error, context)
        return
    if GRPC_AVAILABLE and isinstance(context, AsyncServicerContext):
        logger.error("Unexpected failure in gRPC handler", exc_info=error)
        await _abort_grpc_async_if_servicer_context(InternalError(lang=lang), context)
        return
    raise error


def _wrap_sync_grpc_handler(
    func: Callable,
    authorize: Callable[[object, object], None],
    lang: LanguageType,
) -> Callable:
    """Wrap a sync servicer method so ``authorize`` runs first and the auth context lives for the whole call.

    Generator handlers (response streams) keep the auth context set while the stream is consumed.
    """
    if inspect.isgeneratorfunction(func):

        @functools.wraps(func)
        def stream_wrapper(self: object, request: object, context: object) -> Iterator[object]:
            try:
                authorize(request, context)
                yield from func(self, request, context)
            # Translated to a typed gRPC failure; never swallowed.
            except Exception as error:  # noqa: BLE001
                _raise_sync_failure(error, context, lang)
            finally:
                AuthContextManager.clear_auth_context()

        return stream_wrapper

    @functools.wraps(func)
    def wrapper(self: object, request: object, context: object) -> object:
        try:
            authorize(request, context)
            return func(self, request, context)
        # Translated to a typed gRPC failure; never swallowed.
        except Exception as error:  # noqa: BLE001
            _raise_sync_failure(error, context, lang)
        finally:
            AuthContextManager.clear_auth_context()

    return wrapper


def _wrap_async_grpc_handler(
    func: Callable,
    authorize: Callable[[object, object], Awaitable[None]],
    lang: LanguageType,
) -> Callable:
    """Wrap an async servicer method so ``authorize`` runs first and the auth context lives for the whole call.

    Async-generator handlers (response streams) are iterated, not awaited, and keep the auth context set.
    """
    if inspect.isasyncgenfunction(func):

        @functools.wraps(func)
        async def stream_wrapper(self: object, request: object, context: object) -> AsyncIterator[object]:
            try:
                await authorize(request, context)
                async for item in func(self, request, context):
                    yield item
            # Translated to a typed gRPC failure; never swallowed.
            except Exception as error:  # noqa: BLE001
                await _abort_async_failure(error, context, lang)
            finally:
                AuthContextManager.clear_auth_context()

        return stream_wrapper

    @functools.wraps(func)
    async def wrapper(self: object, request: object, context: object) -> object:
        try:
            await authorize(request, context)
            return await func(self, request, context)
        # Translated to a typed gRPC failure; never swallowed.
        except Exception as error:  # noqa: BLE001
            await _abort_async_failure(error, context, lang)
            return None  # the abort ends the call; this satisfies the type checker
        finally:
            AuthContextManager.clear_auth_context()

    return wrapper


def _extract_roles(user_info: dict[str, Any], client_id: str | None) -> set[str]:
    """Collect realm and client roles from a UserInfo response.

    Requires the Keycloak "realm roles" / "client roles" mappers to have "Add to userinfo" enabled,
    otherwise stock Keycloak omits ``realm_access`` and ``resource_access`` from UserInfo.
    """
    roles: set[str] = set(user_info.get("realm_access", {}).get("roles", []) or [])
    if client_id:
        roles.update(user_info.get("resource_access", {}).get(client_id, {}).get("roles", []) or [])
    return roles


def _check_resource_access(
    user_info: dict[str, Any],
    resource_uuid: str,
    user_roles: set[str],
    admin_roles: frozenset[str] | None,
    lang: LanguageType,
    resource_type: str | None = None,
) -> None:
    """Verify the caller owns the resource or holds an admin role."""
    sub = user_info.get("sub")
    is_owner = sub == resource_uuid
    is_admin = bool(admin_roles) and not user_roles.isdisjoint(admin_roles)
    if not (is_owner or is_admin):
        additional_data: dict[str, Any] = {"resource_id": resource_uuid}
        if resource_type:
            additional_data["resource_type"] = resource_type
        raise PermissionDeniedError(lang=lang, additional_data=additional_data)


def _authorize_sync(
    keycloak: KeycloakAdapter,
    token_str: str,
    resource_uuid: str | None,
    required_roles: frozenset[str] | None,
    all_roles_required: bool,
    required_permissions: tuple[tuple[str, str], ...] | None,
    admin_roles: frozenset[str] | None,
    lang: LanguageType,
    resource_type: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], set[str]]:
    """Authenticate and authorize a request using local JWT verify and UserInfo.

    Args:
        keycloak: Shared Keycloak adapter instance.
        token_str: Bearer access token.
        resource_uuid: Optional resource identifier for ownership checks.
        required_roles: Roles the caller must hold.
        all_roles_required: Whether all or any of ``required_roles`` must match.
        required_permissions: UMA (resource, scope) pairs that must be granted.
        admin_roles: Roles that bypass resource ownership checks.
        lang: Language for error messages.
        resource_type: Optional resource type label for error payloads.

    Returns:
        Tuple of (user_info, token_info, user_roles).

    Raises:
        TokenExpiredError: If the token fails local validation.
        UnauthenticatedError: If UserInfo cannot be retrieved.
        PermissionDeniedError: If authorization checks fail.
    """
    if not keycloak.validate_token(token_str):
        raise TokenExpiredError(lang=lang)

    token_info = keycloak.get_token_info(token_str)
    if not token_info:
        raise TokenExpiredError(lang=lang)

    user_info = _cached_sync_lookup(
        keycloak,
        "userinfo",
        token_str,
        None,
        lambda: keycloak.get_userinfo(token_str),
    )
    if not user_info:
        raise UnauthenticatedError(lang=lang)

    user_roles = _extract_roles(user_info, keycloak.configs.CLIENT_ID)

    if resource_uuid is not None:
        _check_resource_access(user_info, resource_uuid, user_roles, admin_roles, lang, resource_type)

    if required_roles:
        roles_ok = (
            user_roles.issuperset(required_roles) if all_roles_required else not user_roles.isdisjoint(required_roles)
        )
        if not roles_ok:
            raise PermissionDeniedError(
                lang=lang,
                additional_data={"required_roles": list(required_roles)},
            )

    if required_permissions:
        granted = _cached_sync_lookup(
            keycloak,
            "permissions",
            token_str,
            frozenset(required_permissions),
            lambda: keycloak.check_permissions_batch(token_str, required_permissions),
        )
        missing = set(required_permissions) - granted
        if missing:
            raise PermissionDeniedError(
                lang=lang,
                additional_data={"missing_permissions": [f"{r}#{s}" for r, s in missing]},
            )

    return user_info, token_info, user_roles


async def _authorize_async(
    keycloak: AsyncKeycloakAdapter,
    token_str: str,
    resource_uuid: str | None,
    required_roles: frozenset[str] | None,
    all_roles_required: bool,
    required_permissions: tuple[tuple[str, str], ...] | None,
    admin_roles: frozenset[str] | None,
    lang: LanguageType,
    resource_type: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], set[str]]:
    """Async variant of :func:`_authorize_sync`."""
    if not await keycloak.validate_token(token_str):
        raise TokenExpiredError(lang=lang)

    token_info = await keycloak.get_token_info(token_str)
    if not token_info:
        raise TokenExpiredError(lang=lang)

    user_info = await _cached_async_lookup(
        keycloak,
        "userinfo",
        token_str,
        None,
        lambda: keycloak.get_userinfo(token_str),
    )
    if not user_info:
        raise UnauthenticatedError(lang=lang)

    user_roles = _extract_roles(user_info, keycloak.configs.CLIENT_ID)

    if resource_uuid is not None:
        _check_resource_access(user_info, resource_uuid, user_roles, admin_roles, lang, resource_type)

    if required_roles:
        roles_ok = (
            user_roles.issuperset(required_roles) if all_roles_required else not user_roles.isdisjoint(required_roles)
        )
        if not roles_ok:
            raise PermissionDeniedError(
                lang=lang,
                additional_data={"required_roles": list(required_roles)},
            )

    if required_permissions:
        granted = await _cached_async_lookup(
            keycloak,
            "permissions",
            token_str,
            frozenset(required_permissions),
            lambda: keycloak.check_permissions_batch(token_str, required_permissions),
        )
        missing = set(required_permissions) - granted
        if missing:
            raise PermissionDeniedError(
                lang=lang,
                additional_data={"missing_permissions": [f"{r}#{s}" for r, s in missing]},
            )

    return user_info, token_info, user_roles


def _parse_actor_chain(token_info: dict[str, Any] | None) -> list[ActorDTO]:
    """Flatten the nested RFC 8693 ``act`` claim, outermost (current) actor first.

    Per RFC 8693 §4.1 only the outermost actor is the current acting party; inner
    entries are informational history of earlier delegations.
    """
    chain: list[ActorDTO] = []
    act = (token_info or {}).get("act")
    while isinstance(act, dict):
        if len(chain) >= _MAX_ACTOR_DEPTH:
            logger.info("Actor chain truncated at %d entries", _MAX_ACTOR_DEPTH)
            break
        if user_id := act.get("sub"):
            chain.append(ActorDTO(id=user_id, type=ActorType.USER))
        elif client_id := act.get("client_id") or act.get("azp"):
            chain.append(ActorDTO(id=client_id, type=ActorType.CLIENT))
        act = act.get("act")
    return chain


def _build_auth_context(
    user_info: dict[str, Any],
    token_str: str,
    user_roles: set[str],
    token_info: dict[str, Any] | None = None,
) -> AuthenticatedUserDTO:
    """Build an :class:`AuthContext` from UserInfo and decoded token claims."""
    user_id = user_info.get("sub")
    if not user_id:
        raise UnauthenticatedError()
    actors = _parse_actor_chain(token_info)
    if actors:
        logger.info(
            "Impersonated request: subject=%s actors=%s",
            user_id,
            [a.id for a in actors],
        )
    return AuthenticatedUserDTO(
        user_id=user_id,
        username=user_info.get("preferred_username", ""),
        email=user_info.get("email", ""),
        roles=list(user_roles),
        token=token_str,
        raw_user_info=user_info,
        actor_chain=actors,
    )


# Backward-compatible alias for the previous public name.
AuthContext = AuthenticatedUserDTO


# Solution 1: Using contextvars (Recommended)
_auth_context_var: ContextVar[AuthenticatedUserDTO | None] = ContextVar("auth_context", default=None)


class AuthContextManager:
    """Manager for handling auth context in gRPC services."""

    @staticmethod
    def set_auth_context(auth_context: AuthenticatedUserDTO) -> None:
        """Set the auth context for the current request."""
        _auth_context_var.set(auth_context)

    @staticmethod
    def get_auth_context() -> AuthenticatedUserDTO | None:
        """Get the auth context for the current request."""
        return _auth_context_var.get()

    @staticmethod
    def clear_auth_context() -> None:
        """Clear the auth context for the current request."""
        _auth_context_var.set(None)


def _get_keycloak_adapter() -> KeycloakAdapter:
    return _shared_sync_adapter()


def _get_async_keycloak_adapter() -> AsyncKeycloakAdapter:
    return _shared_async_adapter()


def fastapi_auth(
    resource_type_param: str | None = None,
    resource_type: str | None = None,
    required_roles: frozenset[str] | None = None,
    all_roles_required: bool = False,
    required_permissions: tuple[tuple[str, str], ...] | None = None,
    admin_roles: frozenset[str] | None = None,
    lang: LanguageType = DEFAULT_LANG,
) -> Callable:
    """FastAPI dependency for Keycloak authentication and resource-based authorization.

    The dependency is always asynchronous: FastAPI awaits it on the event loop, whether the endpoint is a ``def``
    or an ``async def`` function. It returns the UserInfo dict and fills ``request.state`` with ``user_info``,
    ``token_info``, ``actor_chain`` and ``user_roles``. It also sets :class:`AuthContextManager` for the request, like
    :func:`grpc_auth` does, so code below the endpoint reads the caller with ``AuthContextManager.get_auth_context()``;
    the context is cleared when the request ends.

    Args:
        resource_type_param: The parameter name in the path (e.g., 'user_uuid', 'employee_uuid')
        resource_type: The type of resource being accessed (e.g., 'users', 'employees')
        required_roles: Set of role names that the user must have
        all_roles_required: If True, user must have all specified roles; if False, any role is sufficient
        required_permissions: List of (resource, scope) tuples to check
        admin_roles: Set of roles that grant administrative access to all resources
        lang: Language for error messages
    Raises:
        UnauthenticatedError: If no valid Authorization header is provided
        InvalidTokenError: If token is invalid
        TokenExpiredError: If token is expired
        PermissionDeniedError: If user lacks required roles, permissions, or resource access
        InvalidArgumentError: If resource_type_param is missing when resource_type is provided
    """

    async def dependency(
        request: Request,
        token: HTTPAuthorizationCredentials = Security(security),
        keycloak: AsyncKeycloakAdapter = Depends(_get_async_keycloak_adapter),
    ) -> AsyncIterator[dict[str, Any]]:
        if token is None:
            raise UnauthenticatedError(lang=lang)
        token_str = token.credentials

        resource_uuid: str | None = None
        if resource_type and resource_type_param:
            resource_uuid = request.path_params.get(resource_type_param)
            if not resource_uuid:
                raise InvalidArgumentError(argument_name=resource_type_param, lang=lang)

        user_info, token_info, user_roles = await _authorize_async(
            keycloak,
            token_str,
            resource_uuid,
            required_roles,
            all_roles_required,
            required_permissions,
            admin_roles,
            lang,
            resource_type,
        )

        request.state.user_info = user_info
        request.state.token_info = token_info
        request.state.actor_chain = _parse_actor_chain(token_info)
        request.state.user_roles = user_roles
        AuthContextManager.set_auth_context(_build_auth_context(user_info, token_str, user_roles, token_info))
        try:
            yield user_info
        finally:
            AuthContextManager.clear_auth_context()

    return dependency


def _extract_token_from_metadata(context: object) -> str | None:
    """Extract Bearer token from gRPC metadata."""
    get_metadata = getattr(context, "invocation_metadata", None)
    if get_metadata is None or not callable(get_metadata):
        return None
    invocation_metadata_result = get_metadata()
    if invocation_metadata_result is None:
        return None
    # Keep every value per key: a repeated header is ambiguous and must not silently pick one of them.
    metadata: dict[str, set[str]] = {}
    try:
        for key, value in invocation_metadata_result:
            key_str = (key.decode("utf-8") if isinstance(key, bytes) else str(key)).lower()
            value_str = value.decode("utf-8") if isinstance(value, bytes) else str(value)
            metadata.setdefault(key_str, set()).add(value_str)
    except TypeError, ValueError:
        # If iteration fails, return None
        return None

    for key in ("authorization", "auth", "token"):
        values = metadata.get(key)
        if not values:
            continue
        if len(values) > 1:
            return None
        auth_value = next(iter(values))
        scheme, _, credentials = auth_value.partition(" ")
        if scheme.lower() == "bearer":
            return credentials.strip() or None
        return auth_value

    return None


def _grpc_token_and_resource(
    request: object,
    context: object,
    resource_attribute_name: str | None,
    lang: LanguageType,
) -> tuple[str, str | None]:
    """Return the bearer token and the resource UUID named by ``resource_attribute_name`` for a gRPC call."""
    token_str = _extract_token_from_metadata(context)
    if not token_str:
        _raise_unauthenticated(lang)
    resource_uuid: str | None = None
    if resource_attribute_name:
        resource_uuid = getattr(request, resource_attribute_name, None)
        if not resource_uuid:
            _raise_invalid_argument(resource_attribute_name, lang)
    return token_str, resource_uuid


def grpc_auth(
    required_roles: frozenset[str] | None = None,
    all_roles_required: bool = False,
    required_permissions: tuple[tuple[str, str], ...] | None = None,
    resource_attribute_name: str | None = None,
    admin_roles: frozenset[str] | None = None,
    lang: LanguageType = DEFAULT_LANG,
) -> Callable[[Callable], Callable]:
    """Decorate gRPC servicer methods with authentication and authorization, sync or ``async def``.

    The kind of the decorated method (plain, generator, coroutine or async generator) is detected automatically.

    This decorator handles:
    1. Token validation
    2. Role/permission checking
    3. Passing auth context to business logic

    Resource ownership is handled in the business logic layer.

    Args:
        required_roles: Set of roles, user must have at least one (or all if all_roles_required=True)
        all_roles_required: If True, user must have all required_roles; if False, any one role is sufficient
        required_permissions: Tuple of (resource, scope) pairs that must be satisfied
        resource_attribute_name: Attribute name to extract resource UUID from context for ownership checking
        admin_roles: Set of admin roles that bypass resource ownership checks
        lang: Language for error messages

    Returns:
        Decorated function with authentication and authorization
    """

    def authorize_sync(request: object, context: object) -> None:
        token_str, resource_uuid = _grpc_token_and_resource(request, context, resource_attribute_name, lang)
        user_info, token_info, user_roles = _authorize_sync(
            _get_keycloak_adapter(),
            token_str,
            resource_uuid,
            required_roles,
            all_roles_required,
            required_permissions,
            admin_roles,
            lang,
        )
        AuthContextManager.set_auth_context(_build_auth_context(user_info, token_str, user_roles, token_info))

    async def authorize_async(request: object, context: object) -> None:
        token_str, resource_uuid = _grpc_token_and_resource(request, context, resource_attribute_name, lang)
        user_info, token_info, user_roles = await _authorize_async(
            _get_async_keycloak_adapter(),
            token_str,
            resource_uuid,
            required_roles,
            all_roles_required,
            required_permissions,
            admin_roles,
            lang,
        )
        AuthContextManager.set_auth_context(_build_auth_context(user_info, token_str, user_roles, token_info))

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func) or inspect.isasyncgenfunction(func):
            return _wrap_async_grpc_handler(func, authorize_async, lang)
        return _wrap_sync_grpc_handler(func, authorize_sync, lang)

    return decorator


__all__ = [
    "AuthContextManager",
    "clear_keycloak_remote_cache",
    "fastapi_auth",
    "grpc_auth",
]
