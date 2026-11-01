"""Shared helpers and attribute bases for Keycloak adapter mixins."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import TYPE_CHECKING, Any, NoReturn, TypeVar
from urllib.parse import quote

from keycloak import urls_patterns
from keycloak.connection import ConnectionManager
from keycloak.exceptions import (
    KeycloakAuthenticationError,
    KeycloakConnectionError,
    KeycloakDeleteError,
    KeycloakError,
    KeycloakGetError,
    KeycloakPostError,
    KeycloakPutError,
    raise_error_from_response,
)

from archipy.helpers._deprecation import warn_deprecated_name
from archipy.models.dtos.keycloak.base import KeycloakBaseDTO, KeycloakResponseDTO
from archipy.models.dtos.keycloak.common_dtos import KeycloakCreateResultDTO, KeycloakMutationResultDTO
from archipy.models.dtos.keycloak.token_dtos import KeycloakOidcResponseDTO, KeycloakUserInfoDTO
from archipy.models.errors import (
    BaseError,
    ClientAlreadyExistsError,
    ConflictError,
    InsufficientPermissionsError,
    InternalError,
    InvalidCredentialsError,
    KeycloakConnectionTimeoutError,
    KeycloakServiceUnavailableError,
    PasswordPolicyError,
    RateLimitExceededError,
    RealmAlreadyExistsError,
    ResourceNotFoundError,
    RoleAlreadyExistsError,
    UserAlreadyExistsError,
    ValidationError,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable

    from keycloak import KeycloakAdmin, KeycloakOpenID, KeycloakUMA

    from archipy.configs.config_template import KeycloakConfig

logger = logging.getLogger(__name__)

HTTP_BAD_REQUEST = 400
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_CONFLICT = 409
HTTP_UNPROCESSABLE_ENTITY = 422
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR = 500
HTTP_UNAVAILABLE_CODES = frozenset({502, 503, 504})
_CLIENT_ERROR_RANGE = range(400, 500)

T = TypeVar("T")

_RAW_ERRORS: dict[str, type[KeycloakGetError | KeycloakPostError | KeycloakPutError | KeycloakDeleteError]] = {
    "get": KeycloakGetError,
    "post": KeycloakPostError,
    "put": KeycloakPutError,
    "delete": KeycloakDeleteError,
}


def client_options(
    configs: KeycloakConfig,
    *,
    with_proxies: bool = True,
    with_custom_headers: bool = True,
) -> dict[str, Any]:
    """Build the python-keycloak connection keyword arguments shared by every client the adapters create.

    Args:
        configs: Keycloak configuration.
        with_proxies: Add ``proxies``. ``KeycloakAdmin`` and ``KeycloakOpenIDConnection`` do not accept it.
        with_custom_headers: Add ``custom_headers``. ``ConnectionManager`` takes headers as ``headers`` instead.

    Returns:
        Keyword arguments for the python-keycloak client (TLS verification, mTLS cert, timeout, retries, pool and,
        when asked, proxies and headers).
    """
    cert: str | tuple[str, str] | None = None
    if configs.CLIENT_CERT_FILE:
        cert = (
            (configs.CLIENT_CERT_FILE, configs.CLIENT_KEY_FILE) if configs.CLIENT_KEY_FILE else configs.CLIENT_CERT_FILE
        )
    options: dict[str, Any] = {
        "verify": configs.VERIFY_SSL,
        "timeout": configs.TIMEOUT,
        "cert": cert,
        "max_retries": configs.MAX_RETRIES,
        "pool_maxsize": configs.POOL_MAXSIZE,
    }
    if with_proxies:
        options["proxies"] = configs.PROXIES
    if with_custom_headers:
        options["custom_headers"] = dict(configs.CUSTOM_HEADERS) if configs.CUSTOM_HEADERS else None
    return options


def with_sync_proxies[C](client: C, configs: KeycloakConfig) -> C:
    """Apply ``PROXIES`` to the synchronous ``requests`` session of a python-keycloak client.

    python-keycloak hands one proxy mapping to both ``requests`` (keys such as ``https``) and ``httpx`` (keys such as
    ``https://``), and ``httpx`` rejects the plain form. ``PROXIES`` therefore uses the URL form and the plain form is
    applied to the ``requests`` session here. ``KeycloakAdmin`` and ``KeycloakOpenIDConnection`` accept no proxies, so
    this is the only way their synchronous requests use ``PROXIES``.

    Args:
        client: A ``KeycloakOpenID``, ``KeycloakAdmin``, ``KeycloakUMA`` or ``ConnectionManager`` instance.
        configs: Keycloak configuration.

    Returns:
        The same client.
    """
    if configs.PROXIES:
        connection: Any = getattr(client, "connection", client)
        connection._s.proxies.update({key.removesuffix("://"): url for key, url in configs.PROXIES.items()})
    return client


def admin_url(realm_name: str | None, suffix: str) -> str:
    """Build the URL of an admin REST path below the realm, for endpoints python-keycloak has no method for.

    An empty ``realm_name`` addresses the realm collection itself (``admin/realms``).
    """
    if realm_name == "":
        return "admin/realms" + suffix
    return urls_patterns.URL_ADMIN_REALM.format(**{"realm-name": realm_name or ""}) + suffix


def segment(value: str) -> str:
    """Percent-encode one path segment (an id, alias or name) for an admin REST path."""
    return quote(value, safe="")


def admin_body(body: object | None) -> str:
    """Encode a JSON request body for the raw admin connection."""
    return "" if body is None else json.dumps(body)


def to_request_payload(value: KeycloakBaseDTO | dict[str, Any]) -> dict[str, Any]:
    """Return the camelCase payload python-keycloak expects for a request body.

    Plain dicts are still accepted but deprecated; they are passed through unchanged.

    Args:
        value: A Keycloak DTO or a raw payload dict.

    Returns:
        The payload dict.
    """
    if isinstance(value, KeycloakBaseDTO):
        return value.to_payload()
    warn_deprecated_name("Passing a dict payload", "a Keycloak request DTO", stacklevel=4)
    return value


def to_claims_dict(value: KeycloakOidcResponseDTO | Mapping[str, Any] | None) -> dict[str, Any]:
    """Return OIDC claims as a plain dict, whether they arrive as a DTO, a mapping or ``None``."""
    if value is None:
        return {}
    if isinstance(value, KeycloakOidcResponseDTO):
        return value.to_dict()
    return dict(value)


def to_mutation_result[R: KeycloakMutationResultDTO](model: type[R], raw: Mapping[str, Any] | bytes | None) -> R:
    """Validate the body python-keycloak returns for a create, update, delete or assign call.

    Args:
        model: The result DTO for the operation.
        raw: A parsed JSON object, the raw response bytes, or ``None``. Empty and non-JSON bodies are empty results.

    Returns:
        The result as ``model``.
    """
    if isinstance(raw, bytes | bytearray):
        try:
            parsed = json.loads(raw) if raw else {}
        except ValueError:
            parsed = {}
        raw = parsed if isinstance(parsed, dict) else {}
    return model.model_validate(raw or {})


def payload_value(payload: KeycloakBaseDTO | Mapping[str, Any], attribute: str, key: str) -> str | None:
    """Read one string field from a request payload given as a DTO (``attribute``) or a dict (``key``)."""
    value = payload.get(key) if isinstance(payload, Mapping) else getattr(payload, attribute, None)
    return value if isinstance(value, str) else None


def with_created_id(result: KeycloakCreateResultDTO, lookup: Callable[[], str | None]) -> KeycloakCreateResultDTO:
    """Set ``id`` on a create result by looking the new resource up.

    The lookup is skipped when the create was skipped (``skip_exists``). A failed lookup leaves ``id`` unset: the
    resource was created, so the call must not fail.
    """
    if result.msg:
        return result
    try:
        created_id = lookup()
    except BaseError as e:
        logger.debug("Could not look up the id of the created Keycloak resource: %s", e)
        return result
    return result.model_copy(update={"id": created_id})


async def with_created_id_async(
    result: KeycloakCreateResultDTO,
    lookup: Callable[[], Awaitable[str | None]],
) -> KeycloakCreateResultDTO:
    """Async variant of :func:`with_created_id`."""
    if result.msg:
        return result
    try:
        created_id = await lookup()
    except BaseError as e:
        logger.debug("Could not look up the id of the created Keycloak resource: %s", e)
        return result
    return result.model_copy(update={"id": created_id})


def to_text(raw: object) -> str:
    """Return a raw admin response body as text: bytes are decoded and parsed JSON is serialized again."""
    if isinstance(raw, bytes | bytearray):
        return bytes(raw).decode("utf-8", errors="replace")
    if isinstance(raw, str):
        return raw
    return json.dumps(raw) if raw else ""


def to_dto[M: KeycloakResponseDTO](model: type[M], raw: Mapping[str, Any]) -> M:
    """Validate one python-keycloak representation into a response DTO."""
    return model.model_validate(raw)


def to_dto_or_none[M: KeycloakResponseDTO](model: type[M], raw: Mapping[str, Any] | None) -> M | None:
    """Validate an optional python-keycloak representation into a response DTO."""
    return None if raw is None else model.model_validate(raw)


def to_dto_list[M: KeycloakResponseDTO](model: type[M], raw: Iterable[Mapping[str, Any]] | None) -> list[M]:
    """Validate a list of python-keycloak representations into response DTOs."""
    return [model.model_validate(item) for item in raw or []]


def to_wire_roles(roles: str | KeycloakBaseDTO | list[Any]) -> str | list[Any]:
    """Convert role arguments to what python-keycloak expects: a name or a list of names/role payloads.

    Args:
        roles: A role name, a role DTO, or a list of names, DTOs or raw role dicts.

    Returns:
        The role name unchanged, or a list in which every DTO is replaced by its camelCase payload.
    """
    if isinstance(roles, str):
        return roles
    items = roles if isinstance(roles, list) else [roles]
    return [item.to_payload() if isinstance(item, KeycloakBaseDTO) else item for item in items]


class KeycloakExceptionHandlerMixin:
    """Mixin class to handle Keycloak exceptions in a consistent way."""

    @classmethod
    def _extract_error_message(cls, exception: KeycloakError) -> str:
        """Extract the actual error message from Keycloak error response.

        Args:
            exception: The Keycloak exception

        Returns:
            str: The extracted error message
        """
        error_message = str(exception)

        # Try to parse JSON response body
        if hasattr(exception, "response_body") and exception.response_body:
            try:
                body = exception.response_body
                if isinstance(body, bytes):
                    body_str = body.decode("utf-8")
                elif isinstance(body, str):
                    body_str = body
                else:
                    body_str = str(body)

                parsed = json.loads(body_str)
                if isinstance(parsed, dict):
                    error_message = (
                        parsed.get("errorMessage")
                        or parsed.get("error_description")
                        or parsed.get("error")
                        or error_message
                    )
            except json.JSONDecodeError, UnicodeDecodeError:
                pass

        return error_message

    @classmethod
    def _build_keycloak_error_context(
        cls,
        exception: KeycloakError,
        operation: str,
        error_message: str,
    ) -> dict[str, Any]:
        """Build common error context for Keycloak exception mapping.

        The upstream message goes to callers (``BaseError.to_dict``, ``abort_grpc``) only for 4xx answers. Any other
        message, such as a 5xx body or a connection error, may carry internals (database URLs, stack traces), so it
        is logged and left out of the error.
        """
        response_code = getattr(exception, "response_code", None)
        context: dict[str, Any] = {
            "operation": operation,
            "response_code": response_code,
            "keycloak_error_type": type(exception).__name__,
        }
        if response_code in _CLIENT_ERROR_RANGE:
            context["original_error"] = error_message
        else:
            logger.error(
                "Keycloak operation %s failed (%s, response code %s): %s",
                operation,
                type(exception).__name__,
                response_code,
                error_message,
            )
        return context

    @classmethod
    def _raise_for_keycloak_connection_error(
        cls,
        exception: KeycloakError,
        error_lower: str,
        additional_data: dict[str, Any],
    ) -> NoReturn:
        """Map Keycloak connection errors to application errors."""
        if "timeout" in error_lower:
            raise KeycloakConnectionTimeoutError(additional_data=additional_data) from exception
        raise KeycloakServiceUnavailableError(additional_data=additional_data) from exception

    @classmethod
    def _raise_for_keycloak_already_exists(
        cls,
        exception: KeycloakError,
        error_lower: str,
        additional_data: dict[str, Any],
        operation: str = "",
    ) -> None:
        """Raise when the error indicates a duplicate resource.

        The resource comes from the failed operation first (``create_client_role`` is a role even though its message
        may also say "client"), then from the message. A 409 that names no known resource is a ``ConflictError``.
        """
        response_code = additional_data.get("response_code")
        is_conflict = response_code == HTTP_CONFLICT
        if "already exists" not in error_lower and "user exists with same" not in error_lower and not is_conflict:
            return
        operation_lower = operation.lower()
        resource = next((name for name in ("role", "client", "user", "realm") if name in operation_lower), None)
        if resource is None:
            if "realm" in error_lower:
                resource = "realm"
            elif "user exists with same" in error_lower:
                resource = "user"
            elif "client" in error_lower:
                resource = "client"
            elif "role" in error_lower:
                resource = "role"
        error_types = {
            "realm": RealmAlreadyExistsError,
            "user": UserAlreadyExistsError,
            "client": ClientAlreadyExistsError,
            "role": RoleAlreadyExistsError,
        }
        if resource in error_types:
            raise error_types[resource](additional_data=additional_data) from exception
        if is_conflict:
            raise ConflictError(additional_data=additional_data) from exception

    @classmethod
    def _raise_for_keycloak_status_code(
        cls,
        exception: KeycloakError,
        response_code: int | None,
        additional_data: dict[str, Any],
    ) -> None:
        """Map the status codes that never depend on message text (429 and every 5xx)."""
        if response_code == HTTP_TOO_MANY_REQUESTS:
            raise RateLimitExceededError(additional_data=additional_data) from exception
        if response_code is not None and response_code >= HTTP_SERVER_ERROR:
            # A 500 whose body says "invalid" is not a bad request, so no message pattern is tried.
            if response_code in HTTP_UNAVAILABLE_CODES:
                raise KeycloakServiceUnavailableError(additional_data=additional_data) from exception
            raise InternalError(additional_data=additional_data) from exception

    @classmethod
    def _raise_for_keycloak_message_patterns(
        cls,
        exception: KeycloakError,
        error_lower: str,
        response_code: int | None,
        additional_data: dict[str, Any],
        operation: str = "",
    ) -> None:
        """Map message-pattern Keycloak errors."""
        if cls._is_uma_nothing_granted(exception):
            raise InsufficientPermissionsError(additional_data=additional_data) from exception

        auth_phrases = ["invalid user credentials", "invalid credentials", "authentication failed", "unauthorized"]
        if isinstance(exception, KeycloakAuthenticationError) or any(phrase in error_lower for phrase in auth_phrases):
            raise InvalidCredentialsError(additional_data=additional_data) from exception

        cls._raise_for_keycloak_already_exists(exception, error_lower, additional_data, operation)

        if "not found" in error_lower or response_code == HTTP_NOT_FOUND:
            raise ResourceNotFoundError(additional_data=additional_data) from exception

        permission_phrases = ["forbidden", "access denied", "insufficient permissions", "insufficient scope"]
        if response_code == HTTP_FORBIDDEN or any(phrase in error_lower for phrase in permission_phrases):
            raise InsufficientPermissionsError(additional_data=additional_data) from exception

        password_phrases = ["invalid password", "password policy", "minimum length", "password must"]
        if any(phrase in error_lower for phrase in password_phrases):
            raise PasswordPolicyError(additional_data=additional_data) from exception

        # Phrases count only when the answer carries no status code: with one, the status code decides.
        validation_phrases = ["validation", "invalid", "required field", "bad request"]
        if response_code in (HTTP_BAD_REQUEST, HTTP_UNPROCESSABLE_ENTITY) or (
            response_code is None and any(phrase in error_lower for phrase in validation_phrases)
        ):
            raise ValidationError(additional_data=additional_data) from exception

        if "unavailable" in error_lower:
            raise KeycloakServiceUnavailableError(additional_data=additional_data) from exception

    @classmethod
    def _is_uma_nothing_granted(cls, exception: KeycloakError) -> bool:
        """Return True when a UMA permission request failed only because none of the permissions is granted.

        With ``response_mode=permissions`` Keycloak answers 403 ``access_denied`` / ``not_authorized`` when every
        requested permission is denied. That is an authorization result, not a server failure.
        """
        if getattr(exception, "response_code", None) != HTTPStatus.FORBIDDEN:
            return False
        message = cls._extract_error_message(exception).lower()
        return "not_authorized" in message or "access_denied" in message

    @classmethod
    def _handle_keycloak_exception(cls, exception: KeycloakError, operation: str) -> NoReturn:
        """Handle Keycloak exceptions and map them to appropriate application errors.

        Args:
            exception: The original Keycloak exception
            operation: The name of the operation that failed

        Raises:
            Various application-specific errors based on the exception type/content
        """
        error_message = cls._extract_error_message(exception)
        error_lower = error_message.lower()
        additional_data = cls._build_keycloak_error_context(exception, operation, error_message)
        response_code = additional_data["response_code"]

        if isinstance(exception, KeycloakConnectionError):
            cls._raise_for_keycloak_connection_error(exception, error_lower, additional_data)

        cls._raise_for_keycloak_status_code(exception, response_code, additional_data)
        cls._raise_for_keycloak_message_patterns(exception, error_lower, response_code, additional_data, operation)

        raise InternalError(additional_data=additional_data) from exception

    @classmethod
    def _handle_realm_exception(
        cls,
        exception: KeycloakError,
        operation: str,
        realm_name: str | None = None,
    ) -> NoReturn:
        """Handle realm-specific exceptions.

        Args:
            exception: The original Keycloak exception
            operation: The name of the operation that failed
            realm_name: The realm name involved in the operation

        Raises:
            RealmAlreadyExistsError: If realm already exists
            Various other errors from _handle_keycloak_exception
        """
        # Add realm-specific context
        error_message = cls._extract_error_message(exception)

        # Realm-specific error handling
        if realm_name and "already exists" in error_message.lower():
            additional_data = {
                "operation": operation,
                "realm_name": realm_name,
                "original_error": error_message,
                "response_code": getattr(exception, "response_code", None),
            }
            raise RealmAlreadyExistsError(additional_data=additional_data) from exception

        # Fall back to general Keycloak error handling
        cls._handle_keycloak_exception(exception, operation)

    @classmethod
    def _handle_user_exception(
        cls,
        exception: KeycloakError,
        operation: str,
        user_data: dict | None = None,
    ) -> NoReturn:
        """Handle user-specific exceptions.

        Args:
            exception: The original Keycloak exception
            operation: The name of the operation that failed
            user_data: The user data involved in the operation

        Raises:
            UserAlreadyExistsError: If user already exists
            Various other errors from _handle_keycloak_exception
        """
        error_message = cls._extract_error_message(exception)

        # User-specific error handling
        if "user exists with same" in error_message.lower():
            additional_data = {
                "operation": operation,
                "original_error": error_message,
                "response_code": getattr(exception, "response_code", None),
            }
            if user_data:
                additional_data.update(
                    {
                        "username": user_data.get("username"),
                        "email": user_data.get("email"),
                    },
                )
            raise UserAlreadyExistsError(additional_data=additional_data) from exception

        # Fall back to general Keycloak error handling
        cls._handle_keycloak_exception(exception, operation)

    @classmethod
    def _handle_client_exception(
        cls,
        exception: KeycloakError,
        operation: str,
        client_data: dict | None = None,
    ) -> None:
        """Handle client-specific exceptions.

        Args:
            exception: The original Keycloak exception
            operation: The name of the operation that failed
            client_data: The client data involved in the operation

        Raises:
            ClientAlreadyExistsError: If client already exists
            Various other errors from _handle_keycloak_exception
        """
        error_message = cls._extract_error_message(exception)

        # Client-specific error handling
        if "client" in error_message.lower() and "already exists" in error_message.lower():
            additional_data = {
                "operation": operation,
                "original_error": error_message,
                "response_code": getattr(exception, "response_code", None),
            }
            if client_data:
                additional_data.update(
                    {
                        "client_id": client_data.get("clientId"),
                        "client_name": client_data.get("name"),
                    },
                )
            raise ClientAlreadyExistsError(additional_data=additional_data) from exception

        # Fall back to general Keycloak error handling
        cls._handle_keycloak_exception(exception, operation)


class SyncKeycloakMixinBase(KeycloakExceptionHandlerMixin):
    """Shared attribute declarations for sync Keycloak adapter mixins."""

    configs: KeycloakConfig
    _openid_adapter: KeycloakOpenID
    _admin_adapter: KeycloakAdmin | None
    _admin_token_expiry: float
    _uma_adapter: KeycloakUMA | None

    @property
    def admin_adapter(self) -> KeycloakAdmin:
        """Get the admin adapter, refreshing it if necessary."""
        raise NotImplementedError

    @property
    def uma_adapter(self) -> KeycloakUMA:
        """Get the UMA adapter, creating it on first access."""
        raise NotImplementedError

    def clear_all_caches(self) -> None:
        """Clear all cached values."""
        raise NotImplementedError

    def get_userinfo(self, token: str) -> KeycloakUserInfoDTO | None:
        """Get user information from a token."""
        raise NotImplementedError

    def _call_keycloak(self, operation: str, fn: Callable[[], T]) -> T:
        """Run a sync Keycloak call and map KeycloakError to app errors.

        Args:
            operation: Name of the adapter operation for error context.
            fn: Zero-arg callable performing the Keycloak client call.

        Returns:
            Result of ``fn``.

        Raises:
            Mapped application errors from ``_handle_keycloak_exception``.
        """
        try:
            return fn()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, operation)

    def _admin_request(
        self,
        operation: str,
        method: str,
        suffix: str,
        *,
        body: object | None = None,
        params: dict[str, Any] | None = None,
        realm: str | None = None,
        expected: tuple[int, ...] = (HTTPStatus.OK,),
    ) -> Any:
        """Call an admin REST endpoint python-keycloak has no method for, through its connection.

        Args:
            operation: Name of the adapter operation for error context.
            method: ``get``, ``post``, ``put`` or ``delete``.
            suffix: Path below ``admin/realms/{realm}``, starting with ``/``.
            realm: Realm to address instead of the connection's realm; ``""`` addresses ``admin/realms``.
            body: JSON request body for ``post`` and ``put``.
            params: Query parameters.
            realm: Realm to address instead of the connection's realm; ``""`` addresses ``admin/realms``.
            expected: Status codes that mean success.

        Returns:
            The parsed JSON body, ``{}`` for ``204 No Content``, or the raw bytes of a non-JSON body.

        Raises:
            Mapped application errors from ``_handle_keycloak_exception``.
        """

        def call() -> Any:
            connection = self.admin_adapter.connection
            url = admin_url(connection.realm_name if realm is None else realm, suffix)
            query = params or {}
            if method in ("post", "put") or (method == "delete" and body is not None):
                response = getattr(connection, f"raw_{method}")(url, admin_body(body), **query)
            else:
                response = getattr(connection, f"raw_{method}")(url, **query)
            return raise_error_from_response(response, _RAW_ERRORS[method], expected_codes=list(expected))

        return self._call_keycloak(operation, call)

    def _bearer_request(
        self,
        operation: str,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json_body: object | None = None,
        form: dict[str, Any] | None = None,
        expected: tuple[int, ...] = (HTTPStatus.OK,),
    ) -> Any:
        """Call a realm endpoint with the caller's own bearer token instead of the admin session.

        AuthZEN evaluations and RPT requests must come from the end user's or the resource server's token, so they
        use a separate connection with that token in its headers.

        Args:
            operation: Name of the adapter operation for error context.
            method: ``get`` or ``post``.
            path: Path relative to the server URL, such as ``realms/{realm}/authzen/access/v1/evaluation``.
            token: Bearer token to send, if any.
            json_body: JSON request body.
            form: Form-encoded request body.
            expected: Status codes that mean success.

        Returns:
            The parsed JSON body, ``{}`` for ``204 No Content``, or the raw bytes of a non-JSON body.

        Raises:
            Mapped application errors from ``_handle_keycloak_exception``.
        """

        def call() -> Any:
            headers = dict(self.configs.CUSTOM_HEADERS or {})
            if token:
                headers["Authorization"] = f"Bearer {token}"
            if json_body is not None:
                headers["Content-Type"] = "application/json"
            connection = with_sync_proxies(
                ConnectionManager(
                    base_url=self.configs.SERVER_URL or "",
                    headers=headers,
                    **client_options(self.configs, with_custom_headers=False),
                ),
                self.configs,
            )
            if method == "post":
                response = connection.raw_post(path, admin_body(json_body) if json_body is not None else (form or {}))
            else:
                response = connection.raw_get(path)
            return raise_error_from_response(response, _RAW_ERRORS[method], expected_codes=list(expected))

        return self._call_keycloak(operation, call)


class AsyncKeycloakMixinBase(KeycloakExceptionHandlerMixin):
    """Shared attribute declarations for async Keycloak adapter mixins."""

    configs: KeycloakConfig
    openid_adapter: KeycloakOpenID
    _admin_adapter: KeycloakAdmin | None
    _admin_token_expiry: float
    _uma_adapter: KeycloakUMA | None

    @property
    def admin_adapter(self) -> KeycloakAdmin:
        """Get the admin adapter, refreshing it if necessary."""
        raise NotImplementedError

    @property
    def uma_adapter(self) -> KeycloakUMA:
        """Get the UMA adapter, creating it on first access."""
        raise NotImplementedError

    def clear_all_caches(self) -> None:
        """Clear all cached values."""
        raise NotImplementedError

    async def get_userinfo(self, token: str) -> KeycloakUserInfoDTO | None:
        """Get user information from a token."""
        raise NotImplementedError

    async def _async_call_keycloak(self, operation: str, fn: Callable[[], Awaitable[T]]) -> T:
        """Run an async Keycloak call and map KeycloakError to app errors.

        Args:
            operation: Name of the adapter operation for error context.
            fn: Zero-arg async callable performing the Keycloak client call.

        Returns:
            Result of ``fn``.

        Raises:
            Mapped application errors from ``_handle_keycloak_exception``.
        """
        try:
            return await fn()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, operation)

    async def _async_admin_request(
        self,
        operation: str,
        method: str,
        suffix: str,
        *,
        body: object | None = None,
        params: dict[str, Any] | None = None,
        realm: str | None = None,
        expected: tuple[int, ...] = (HTTPStatus.OK,),
    ) -> Any:
        """Async variant of ``_admin_request``."""

        async def call() -> Any:
            connection = self.admin_adapter.connection
            url = admin_url(connection.realm_name if realm is None else realm, suffix)
            query = params or {}
            if method in ("post", "put") or (method == "delete" and body is not None):
                response = await getattr(connection, f"a_raw_{method}")(url, admin_body(body), **query)
            else:
                response = await getattr(connection, f"a_raw_{method}")(url, **query)
            return raise_error_from_response(response, _RAW_ERRORS[method], expected_codes=list(expected))

        return await self._async_call_keycloak(operation, call)

    async def _async_bearer_request(
        self,
        operation: str,
        method: str,
        path: str,
        *,
        token: str | None = None,
        json_body: object | None = None,
        form: dict[str, Any] | None = None,
        expected: tuple[int, ...] = (HTTPStatus.OK,),
    ) -> Any:
        """Async variant of ``_bearer_request``."""

        async def call() -> Any:
            headers = dict(self.configs.CUSTOM_HEADERS or {})
            if token:
                headers["Authorization"] = f"Bearer {token}"
            if json_body is not None:
                headers["Content-Type"] = "application/json"
            connection = with_sync_proxies(
                ConnectionManager(
                    base_url=self.configs.SERVER_URL or "",
                    headers=headers,
                    **client_options(self.configs, with_custom_headers=False),
                ),
                self.configs,
            )
            try:
                if method == "post":
                    response = await connection.a_raw_post(
                        path,
                        admin_body(json_body) if json_body is not None else (form or {}),
                    )
                else:
                    response = await connection.a_raw_get(path)
                return raise_error_from_response(response, _RAW_ERRORS[method], expected_codes=list(expected))
            finally:
                await connection.aclose()

        return await self._async_call_keycloak(operation, call)
