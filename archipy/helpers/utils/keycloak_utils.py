import functools
import logging
from contextvars import ContextVar
from functools import cache
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable

    from grpc import ServicerContext
    from grpc.aio import ServicerContext as AsyncServicerContext

try:
    from grpc import ServicerContext
    from grpc.aio import ServicerContext as AsyncServicerContext

    GRPC_AVAILABLE = True
    GrpcContextType = ServicerContext
    AsyncGrpcContextType = AsyncServicerContext
except ImportError:
    # Type stubs for when grpc is not available
    ServicerContext: type = object  # Explicit type annotation for shadowing
    AsyncServicerContext: type = object  # Explicit type annotation for shadowing
    GRPC_AVAILABLE = False
    GrpcContextType = object
    AsyncGrpcContextType = object

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from archipy.adapters.keycloak.adapters import AsyncKeycloakAdapter, KeycloakAdapter
from archipy.models.errors import (
    BaseError,
    InternalError,
    InvalidArgumentError,
    PermissionDeniedError,
    TokenExpiredError,
    UnauthenticatedError,
)
from archipy.models.types.language_type import LanguageType

# Enhanced security scheme with OpenAPI documentation
security = HTTPBearer(scheme_name="OAuth2", description="OAuth2 Access Token", auto_error=False)

# Default language for errors
DEFAULT_LANG = LanguageType.FA

logger = logging.getLogger(__name__)


@cache
def _shared_sync_adapter() -> KeycloakAdapter:
    """Return a process-wide shared synchronous Keycloak adapter."""
    return KeycloakAdapter()


@cache
def _shared_async_adapter() -> AsyncKeycloakAdapter:
    """Return a process-wide shared asynchronous Keycloak adapter."""
    return AsyncKeycloakAdapter()


def _abort_grpc_sync_if_servicer_context(error: BaseError, context: object) -> None:
    """Invoke ``error.abort_grpc_sync`` when ``context`` is a sync gRPC servicer context."""
    if not GRPC_AVAILABLE or not hasattr(error, "abort_grpc_sync"):
        return
    if isinstance(context, ServicerContext):
        # Any cast: base_error's ServicerContext alias diverges under optional-grpc typing.
        error.abort_grpc_sync(cast("Any", context))


async def _abort_grpc_async_if_servicer_context(error: BaseError, context: object) -> None:
    """Invoke ``error.abort_grpc_async`` when ``context`` is an async gRPC servicer context."""
    if not GRPC_AVAILABLE or not hasattr(error, "abort_grpc_async"):
        return
    if isinstance(context, AsyncServicerContext):
        # Any cast: base_error's AsyncServicerContext alias diverges under optional-grpc typing.
        await error.abort_grpc_async(cast("Any", context))


def _extract_roles(user_info: dict[str, Any], client_id: str | None) -> set[str]:
    """Collect realm and client roles from a UserInfo response."""
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

    user_info = keycloak.get_userinfo(token_str)
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
        granted = keycloak.check_permissions_batch(token_str, required_permissions)
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

    user_info = await keycloak.get_userinfo(token_str)
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
        granted = await keycloak.check_permissions_batch(token_str, required_permissions)
        missing = set(required_permissions) - granted
        if missing:
            raise PermissionDeniedError(
                lang=lang,
                additional_data={"missing_permissions": [f"{r}#{s}" for r, s in missing]},
            )

    return user_info, token_info, user_roles


class AuthContext(BaseModel):
    """Authentication context passed to business logic."""

    user_id: str
    username: str
    email: str
    roles: list[str]
    token: str
    raw_user_info: dict[str, Any]


def _build_auth_context(user_info: dict[str, Any], token_str: str, user_roles: set[str]) -> AuthContext:
    """Build an :class:`AuthContext` from UserInfo claims."""
    user_id = user_info.get("sub")
    if not user_id:
        raise UnauthenticatedError()
    return AuthContext(
        user_id=user_id,
        username=user_info.get("preferred_username", ""),
        email=user_info.get("email", ""),
        roles=list(user_roles),
        token=token_str,
        raw_user_info=user_info,
    )


# Solution 1: Using contextvars (Recommended)
_auth_context_var: ContextVar[AuthContext | None] = ContextVar("auth_context", default=None)


class AuthContextManager:
    """Manager for handling auth context in gRPC services."""

    @staticmethod
    def set_auth_context(auth_context: AuthContext) -> None:
        """Set the auth context for the current request."""
        _auth_context_var.set(auth_context)

    @staticmethod
    def get_auth_context() -> AuthContext | None:
        """Get the auth context for the current request."""
        return _auth_context_var.get()

    @staticmethod
    def clear_auth_context() -> None:
        """Clear the auth context for the current request."""
        _auth_context_var.set(None)


class KeycloakUtils:
    """Utility class for Keycloak authentication and authorization in FastAPI applications."""

    @staticmethod
    def _get_keycloak_adapter() -> KeycloakAdapter:
        return _shared_sync_adapter()

    @staticmethod
    def _get_async_keycloak_adapter() -> AsyncKeycloakAdapter:
        return _shared_async_adapter()

    @classmethod
    # Synchronous decorator
    def fastapi_auth(
        cls,
        resource_type_param: str | None = None,
        resource_type: str | None = None,
        required_roles: frozenset[str] | None = None,
        all_roles_required: bool = False,
        required_permissions: tuple[tuple[str, str], ...] | None = None,
        admin_roles: frozenset[str] | None = None,
        lang: LanguageType = DEFAULT_LANG,
    ) -> Callable:
        """FastAPI decorator for Keycloak authentication and resource-based authorization.

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

        def dependency(
            request: Request,
            token: HTTPAuthorizationCredentials = Security(security),
            keycloak: KeycloakAdapter = Depends(cls._get_keycloak_adapter),
        ) -> dict[str, Any]:
            if token is None:
                raise UnauthenticatedError(lang=lang)
            token_str = token.credentials

            resource_uuid: str | None = None
            if resource_type and resource_type_param:
                resource_uuid = request.path_params.get(resource_type_param)
                if not resource_uuid:
                    raise InvalidArgumentError(argument_name=resource_type_param, lang=lang)

            user_info, token_info, user_roles = _authorize_sync(
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
            request.state.user_roles = user_roles
            return user_info

        return dependency

    @classmethod
    def async_fastapi_auth(
        cls,
        resource_type_param: str | None = None,
        resource_type: str | None = None,
        required_roles: frozenset[str] | None = None,
        all_roles_required: bool = False,
        required_permissions: tuple[tuple[str, str], ...] | None = None,
        admin_roles: frozenset[str] | None = None,
        lang: LanguageType = DEFAULT_LANG,
    ) -> Callable:
        """FastAPI async decorator for Keycloak authentication and resource-based authorization.

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
            keycloak: AsyncKeycloakAdapter = Depends(cls._get_async_keycloak_adapter),
        ) -> dict[str, Any]:
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
            request.state.user_roles = user_roles
            return user_info

        return dependency

    @staticmethod
    def _extract_token_from_metadata(context: object) -> str | None:
        """Extract Bearer token from gRPC metadata."""
        get_metadata = getattr(context, "invocation_metadata", None)
        if get_metadata is None or not callable(get_metadata):
            return None
        invocation_metadata_result = get_metadata()
        if invocation_metadata_result is None:
            return None
        # Convert metadata tuples to dict, handling both str and bytes keys
        # invocation_metadata_result is an iterable of tuples at runtime
        metadata: dict[str, str] = {}
        try:
            for key, value in invocation_metadata_result:
                # Normalize key to string
                key_str = key.decode("utf-8") if isinstance(key, bytes) else str(key)
                # Normalize value to string
                value_str = value.decode("utf-8") if isinstance(value, bytes) else str(value)
                metadata[key_str] = value_str
        except TypeError, ValueError:
            # If iteration fails, return None
            return None

        auth_keys = ["authorization", "Authorization", "auth", "token"]

        for key in auth_keys:
            if key in metadata:
                auth_value = metadata[key]
                # Handle both bytes and string values
                auth_value_str = auth_value.decode("utf-8") if isinstance(auth_value, bytes) else str(auth_value)

                if auth_value_str.startswith(("Bearer ", "bearer ")):
                    return auth_value_str[7:]
                return auth_value_str

        return None

    @classmethod
    def grpc_auth(
        cls,
        required_roles: frozenset[str] | None = None,
        all_roles_required: bool = False,
        required_permissions: tuple[tuple[str, str], ...] | None = None,
        resource_attribute_name: str | None = None,
        admin_roles: frozenset[str] | None = None,
        lang: LanguageType = DEFAULT_LANG,
    ) -> Callable[[Callable], Callable]:
        """Synchronous gRPC decorator for authentication and authorization.

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

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(self: object, request: object, context: object) -> object:
                try:
                    token_str = cls._extract_token_from_metadata(context)
                    if not token_str:
                        raise UnauthenticatedError(lang=lang)

                    keycloak = cls._get_keycloak_adapter()

                    resource_uuid: str | None = None
                    if resource_attribute_name:
                        resource_uuid = getattr(request, resource_attribute_name, None)
                        if not resource_uuid:
                            raise InvalidArgumentError(argument_name=resource_attribute_name, lang=lang)

                    user_info, _token_info, user_roles = _authorize_sync(
                        keycloak,
                        token_str,
                        resource_uuid,
                        required_roles,
                        all_roles_required,
                        required_permissions,
                        admin_roles,
                        lang,
                    )

                    auth_context = _build_auth_context(user_info, token_str, user_roles)
                    AuthContextManager.set_auth_context(auth_context)

                    return func(self, request, context)

                except Exception as e:
                    if isinstance(e, BaseError):
                        _abort_grpc_sync_if_servicer_context(e, context)
                        raise
                    raise InternalError(
                        lang=lang,
                        additional_data={"original_error": str(e), "error_type": type(e).__name__},
                    ) from e

                finally:
                    AuthContextManager.clear_auth_context()

            return wrapper

        return decorator

    @classmethod
    def async_grpc_auth(
        cls,
        required_roles: frozenset[str] | None = None,
        all_roles_required: bool = False,
        required_permissions: tuple[tuple[str, str], ...] | None = None,
        resource_attribute_name: str | None = None,
        admin_roles: frozenset[str] | None = None,
        lang: LanguageType = DEFAULT_LANG,
    ) -> Callable[[Callable], Callable]:
        """Simplified gRPC decorator for authentication and authorization.

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

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(self: object, request: object, context: object) -> object:
                try:
                    token_str = cls._extract_token_from_metadata(context)
                    if not token_str:
                        raise UnauthenticatedError(lang=lang)

                    keycloak = cls._get_async_keycloak_adapter()

                    resource_uuid: str | None = None
                    if resource_attribute_name:
                        resource_uuid = getattr(request, resource_attribute_name, None)
                        if not resource_uuid:
                            raise InvalidArgumentError(argument_name=resource_attribute_name, lang=lang)

                    user_info, _token_info, user_roles = await _authorize_async(
                        keycloak,
                        token_str,
                        resource_uuid,
                        required_roles,
                        all_roles_required,
                        required_permissions,
                        admin_roles,
                        lang,
                    )

                    auth_context = _build_auth_context(user_info, token_str, user_roles)
                    AuthContextManager.set_auth_context(auth_context)

                    return await func(self, request, context)

                except Exception as e:
                    grpc_ctx = context
                    if grpc_ctx is None:
                        raise
                    if isinstance(e, BaseError) and GRPC_AVAILABLE and isinstance(grpc_ctx, AsyncServicerContext):
                        await _abort_grpc_async_if_servicer_context(e, grpc_ctx)
                        return None  # abort_grpc_async will terminate, but satisfy type checker
                    if GRPC_AVAILABLE and isinstance(grpc_ctx, AsyncServicerContext):
                        error_instance = InternalError(
                            lang=lang,
                            additional_data={"original_error": str(e), "error_type": type(e).__name__},
                        )
                        await _abort_grpc_async_if_servicer_context(error_instance, grpc_ctx)
                        return None  # abort_grpc_async will terminate, but satisfy type checker
                    raise

                finally:
                    AuthContextManager.clear_auth_context()

            return wrapper

        return decorator
