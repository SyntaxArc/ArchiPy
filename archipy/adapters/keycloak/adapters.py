import json
import logging
import time
from collections.abc import Iterable
from typing import Any, NoReturn, cast, override

from async_lru import alru_cache
from keycloak import KeycloakAdmin, KeycloakOpenID, KeycloakUMA
from keycloak.exceptions import (
    KeycloakAuthenticationError,
    KeycloakConnectionError,
    KeycloakError,
    KeycloakGetError,
)
from keycloak.openid_connection import KeycloakOpenIDConnection
from keycloak.uma_permissions import UMAPermission

from archipy.adapters.keycloak.ports import (
    AsyncKeycloakPort,
    KeycloakPort,
    KeycloakRoleType,
    KeycloakTokenType,
    KeycloakUserType,
    PublicKeyType,
)
from archipy.configs.base_config import BaseConfig
from archipy.configs.config_template import KeycloakConfig
from archipy.helpers.decorators import ttl_cache_decorator
from archipy.helpers.utils.string_utils import StringUtils
from archipy.models.errors import (
    ClientAlreadyExistsError,
    ConnectionTimeoutError,
    InsufficientPermissionsError,
    InternalError,
    InvalidCredentialsError,
    KeycloakConnectionTimeoutError,
    KeycloakServiceUnavailableError,
    PasswordPolicyError,
    RealmAlreadyExistsError,
    ResourceNotFoundError,
    RoleAlreadyExistsError,
    UnauthenticatedError,
    UnavailableError,
    UserAlreadyExistsError,
    ValidationError,
)

logger = logging.getLogger(__name__)


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
    def _handle_keycloak_exception(cls, exception: KeycloakError, operation: str) -> NoReturn:
        """Handle Keycloak exceptions and map them to appropriate application errors.

        Args:
            exception: The original Keycloak exception
            operation: The name of the operation that failed

        Raises:
            Various application-specific errors based on the exception type/content
        """
        error_message = cls._extract_error_message(exception)
        response_code = getattr(exception, "response_code", None)
        error_lower = error_message.lower()

        # Common context data
        additional_data = {
            "operation": operation,
            "original_error": error_message,
            "response_code": response_code,
            "keycloak_error_type": type(exception).__name__,
        }

        # Connection and network errors
        if isinstance(exception, KeycloakConnectionError):
            if "timeout" in error_lower:
                raise KeycloakConnectionTimeoutError(additional_data=additional_data) from exception
            raise KeycloakServiceUnavailableError(additional_data=additional_data) from exception

        # Authentication errors
        if isinstance(exception, KeycloakAuthenticationError) or any(
            phrase in error_lower
            for phrase in ["invalid user credentials", "invalid credentials", "authentication failed", "unauthorized"]
        ):
            raise InvalidCredentialsError(additional_data=additional_data) from exception

        # Resource already exists errors
        if "already exists" in error_lower:
            if "realm" in error_lower:
                raise RealmAlreadyExistsError(additional_data=additional_data) from exception
            elif "user exists with same" in error_lower:
                raise UserAlreadyExistsError(additional_data=additional_data) from exception
            elif "client" in error_lower:
                raise ClientAlreadyExistsError(additional_data=additional_data) from exception
            elif "role" in error_lower:
                raise RoleAlreadyExistsError(additional_data=additional_data) from exception

        # Not found errors
        if "not found" in error_lower:
            raise ResourceNotFoundError(additional_data=additional_data) from exception

        # Permission errors
        if any(
            phrase in error_lower
            for phrase in ["forbidden", "access denied", "insufficient permissions", "insufficient scope"]
        ):
            raise InsufficientPermissionsError(additional_data=additional_data) from exception

        # Password policy errors
        if any(
            phrase in error_lower
            for phrase in ["invalid password", "password policy", "minimum length", "password must"]
        ):
            raise PasswordPolicyError(additional_data=additional_data) from exception

        # Validation errors (400 status codes that don't match above)
        if response_code == 400 or any(
            phrase in error_lower for phrase in ["validation", "invalid", "required field", "bad request"]
        ):
            raise ValidationError(additional_data=additional_data) from exception

        # Service unavailable
        if response_code in [503, 504] or "unavailable" in error_lower:
            raise KeycloakServiceUnavailableError(additional_data=additional_data) from exception

        # Default to InternalError for unrecognized errors
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


class KeycloakAdapter(KeycloakPort, KeycloakExceptionHandlerMixin):
    """Concrete implementation of the KeycloakPort interface using python-keycloak library.

    This implementation includes TTL caching for appropriate operations to improve performance
    while ensuring cache entries expire after a configured time to prevent stale data.
    """

    def __init__(self, keycloak_configs: KeycloakConfig | None = None) -> None:
        """Initialize KeycloakAdapter with configuration.

        Args:
            keycloak_configs: Optional Keycloak configuration. If None, global config is used.
        """
        self.configs: KeycloakConfig = (
            BaseConfig.global_config().KEYCLOAK if keycloak_configs is None else keycloak_configs
        )

        # Initialize the OpenID client for authentication
        self._openid_adapter = self._get_openid_client(self.configs)

        # Cache for admin client to avoid unnecessary re-authentication
        self._admin_adapter: KeycloakAdmin | None = None
        self._admin_token_expiry: float = 0.0
        self._uma_adapter: KeycloakUMA | None = None

        # Initialize admin client if admin mode is enabled and credentials are provided
        if self.configs.IS_ADMIN_MODE_ENABLED and (
            self.configs.CLIENT_SECRET_KEY or (self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD)
        ):
            self._initialize_admin_client()

    def clear_all_caches(self) -> None:
        """Clear all cached values."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "clear_cache"):
                attr.clear_cache()

    @staticmethod
    def _get_openid_client(configs: KeycloakConfig) -> KeycloakOpenID:
        """Create and configure a KeycloakOpenID instance.

        Args:
            configs: Keycloak configuration

        Returns:
            Configured KeycloakOpenID client
        """
        server_url = configs.SERVER_URL
        client_id = configs.CLIENT_ID
        if not server_url or not client_id:
            raise ValueError("SERVER_URL and CLIENT_ID must be provided")
        return KeycloakOpenID(
            server_url=server_url,
            client_id=client_id,
            realm_name=configs.REALM_NAME,
            client_secret_key=configs.CLIENT_SECRET_KEY,
            verify=configs.VERIFY_SSL,
            timeout=configs.TIMEOUT,
        )

    def _initialize_admin_client(self) -> None:
        """Initialize or refresh the admin client."""
        try:
            # Check if admin credentials are available
            if self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD:
                # Create admin client using admin credentials
                self._admin_adapter = KeycloakAdmin(
                    server_url=self.configs.SERVER_URL,
                    username=self.configs.ADMIN_USERNAME,
                    password=self.configs.ADMIN_PASSWORD,
                    realm_name=self.configs.REALM_NAME,
                    user_realm_name=self.configs.ADMIN_REALM_NAME,
                    verify=self.configs.VERIFY_SSL,
                    timeout=self.configs.TIMEOUT,
                )
                # Since we're using direct credentials, set a long expiry time
                self._admin_token_expiry = time.time() + 3600  # 1 hour
                logger.debug("Admin client initialized with admin credentials")

            elif self.configs.CLIENT_SECRET_KEY:
                # Get token using client credentials
                token = self._openid_adapter.token(grant_type="client_credentials")

                # Set token expiry time (current time + expires_in - buffer)
                # Using a 30-second buffer to ensure we refresh before expiration
                self._admin_token_expiry = time.time() + token.get("expires_in", 60) - 30

                self._admin_adapter = KeycloakAdmin(
                    server_url=self.configs.SERVER_URL,
                    realm_name=self.configs.REALM_NAME,
                    token=token,
                    verify=self.configs.VERIFY_SSL,
                    timeout=self.configs.TIMEOUT,
                )
                logger.debug("Admin client initialized with client credentials")

            else:
                raise UnauthenticatedError(
                    additional_data={"detail": "Neither admin credentials nor client secret provided"},
                )

        except KeycloakAuthenticationError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            raise UnauthenticatedError(
                additional_data={"detail": "Failed to authenticate with Keycloak service account"},
            ) from e
        except KeycloakConnectionError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            raise ConnectionTimeoutError("Failed to connect to Keycloak server") from e
        except KeycloakError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            self._handle_keycloak_exception(e, "_initialize_admin_client")

    @property
    def admin_adapter(self) -> KeycloakAdmin:
        """Get the admin adapter, refreshing it if necessary.

        Returns:
            KeycloakAdmin instance

        Raises:
            UnauthenticatedError: If admin client is not available due to authentication issues
            UnavailableError: If Keycloak service is unavailable
        """
        if not self.configs.IS_ADMIN_MODE_ENABLED or not (
            self.configs.CLIENT_SECRET_KEY or (self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD)
        ):
            raise UnauthenticatedError(
                additional_data={
                    "data": "Admin mode is disabled or neither admin credentials nor client secret provided",
                },
            )

        # Check if token is about to expire and refresh if needed
        if self._admin_adapter is None or time.time() >= self._admin_token_expiry:
            self._initialize_admin_client()

        if self._admin_adapter is None:
            raise UnavailableError("Keycloak admin client is not available")

        return self._admin_adapter

    @staticmethod
    def _get_uma_client(configs: KeycloakConfig) -> KeycloakUMA:
        """Create and configure a KeycloakUMA instance.

        Args:
            configs: Keycloak configuration

        Returns:
            Configured KeycloakUMA client
        """
        server_url = configs.SERVER_URL
        client_id = configs.CLIENT_ID
        if not server_url or not client_id:
            raise ValueError("SERVER_URL and CLIENT_ID must be provided")
        return KeycloakUMA(
            KeycloakOpenIDConnection(
                server_url=server_url,
                realm_name=configs.REALM_NAME,
                client_id=client_id,
                client_secret_key=configs.CLIENT_SECRET_KEY,
                verify=configs.VERIFY_SSL,
                timeout=configs.TIMEOUT,
            ),
        )

    @property
    def uma_adapter(self) -> KeycloakUMA:
        """Get the UMA adapter, creating it on first access.

        Returns:
            KeycloakUMA instance
        """
        if self._uma_adapter is None:
            self._uma_adapter = self._get_uma_client(self.configs)
        return self._uma_adapter

    @override
    @ttl_cache_decorator(ttl_seconds=3600, maxsize=1)  # Cache for 1 hour, public key rarely changes
    def get_public_key(self) -> PublicKeyType:
        """Get the public key used to verify tokens.

        Returns:
            JWK key object used to verify signatures

        Raises:
            ServiceUnavailableError: If Keycloak service is unavailable
            InternalError: If there's an internal error processing the public key
        """
        try:
            from jwcrypto import jwk

            keys_info = self._openid_adapter.public_key()
            key = f"-----BEGIN PUBLIC KEY-----\n{keys_info}\n-----END PUBLIC KEY-----"
            return jwk.JWK.from_pem(key.encode("utf-8"))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_public_key")
        except Exception as e:
            raise InternalError(additional_data={"operation": "get_public_key", "error": str(e)}) from e

    @override
    def get_token(self, username: str, password: str) -> KeycloakTokenType | None:
        """Get a user token by username and password using the Resource Owner Password Credentials Grant.

        Warning:
            This method uses the direct password grant flow, which is less secure and not recommended
            for user login in production environments. Instead, prefer the web-based OAuth 2.0
            Authorization Code Flow (use `get_token_from_code`) for secure authentication.
            Use this method only for testing, administrative tasks, or specific service accounts
            where direct credential use is acceptable and properly secured.

        Args:
            username: User's username
            password: User's password

        Returns:
            Token response containing access_token, refresh_token, etc.

        Raises:
            InvalidCredentialsError: If username or password is invalid
            ServiceUnavailableError: If Keycloak service is unavailable
        """
        try:
            return self._openid_adapter.token(grant_type="password", username=username, password=password)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token")

    @override
    def refresh_token(self, refresh_token: str) -> KeycloakTokenType | None:
        """Refresh an existing token using a refresh token.

        Args:
            refresh_token: Refresh token string

        Returns:
            New token response containing access_token, refresh_token, etc.

        Raises:
            InvalidTokenError: If refresh token is invalid or expired
            ServiceUnavailableError: If Keycloak service is unavailable
        """
        try:
            return self._openid_adapter.refresh_token(refresh_token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "refresh_token")

    @override
    def validate_token(self, token: str) -> bool:
        """Validate if a token is still valid.

        Args:
            token: Access token to validate

        Returns:
            True if token is valid, False otherwise
        """
        # Not caching validation results as tokens are time-sensitive
        try:
            # Let the underlying adapter handle key selection to align with expected types
            self._openid_adapter.decode_token(token)
        except Exception as e:
            logger.debug(f"Token validation failed: {e!s}")
            return False
        else:
            return True

    @override
    def get_userinfo(self, token: str) -> KeycloakUserType | None:
        """Get user information from a token via the UserInfo endpoint.

        The UserInfo endpoint validates the token server-side, so no local
        validation is needed here.

        Args:
            token: Access token

        Returns:
            User information

        Raises:
            ValueError: If getting user info fails
        """
        try:
            # _get_userinfo_cached returns KeycloakUserType (dict[str, Any])
            # The ttl_cache_decorator loses type info, but runtime behavior is correct
            # Access underlying function for proper typing
            cached_func = self._get_userinfo_cached
            underlying_func = getattr(cached_func, "__wrapped__", None)
            if underlying_func is not None:
                # Call underlying function directly for type checking
                result: KeycloakUserType = underlying_func(self, token)
            else:
                # Fallback to cached version if __wrapped__ not available
                result_raw = cached_func(token)
                if not isinstance(result_raw, dict):
                    return None
                # Type assertion: result_raw is a dict, which matches KeycloakUserType
                # Convert to proper type by creating a new dict with explicit typing
                result: KeycloakUserType = {str(k): v for k, v in result_raw.items()}
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_userinfo")
            return None
        else:
            return result

    @ttl_cache_decorator(ttl_seconds=30, maxsize=100)  # Cache for 30 seconds
    def _get_userinfo_cached(self, token: str) -> KeycloakUserType:
        return cast("KeycloakUserType", self._openid_adapter.userinfo(token))

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_user_by_id(self, user_id: str) -> KeycloakUserType | None:
        """Get user details by user ID.

        Args:
            user_id: User's ID

        Returns:
            User details or None if not found

        Raises:
            ValueError: If getting user fails
        """
        try:
            return self.admin_adapter.get_user(user_id)
        except KeycloakGetError as e:
            if e.response_code == 404:
                return None
            self._handle_keycloak_exception(e, "get_user_by_id")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_id")

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_user_by_username(self, username: str) -> KeycloakUserType | None:
        """Get user details by username.

        Args:
            username: User's username

        Returns:
            User details or None if not found

        Raises:
            ValueError: If query fails
        """
        try:
            users = self.admin_adapter.get_users({"username": username})
            return users[0] if users else None
        except KeycloakError as e:
            raise InternalError() from e

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_user_by_email(self, email: str) -> KeycloakUserType | None:
        """Get user details by email.

        Args:
            email: User's email

        Returns:
            User details or None if not found

        Raises:
            ValueError: If query fails
        """
        try:
            users = self.admin_adapter.get_users({"email": email})
            return users[0] if users else None
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_email")

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_user_roles(self, user_id: str) -> list[KeycloakRoleType] | None:
        """Get roles assigned to a user.

        Args:
            user_id: User's ID

        Returns:
            List of roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return self.admin_adapter.get_realm_roles_of_user(user_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_roles")

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=100)  # Cache for 5 minutes
    def get_client_roles_for_user(self, user_id: str, client_id: str) -> list[KeycloakRoleType]:
        """Get client-specific roles assigned to a user.

        Args:
            user_id: User's ID
            client_id: Client ID

        Returns:
            List of client-specific roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return self.admin_adapter.get_client_roles_of_user(user_id, client_id)
        except KeycloakError as e:
            raise InternalError() from e

    @override
    def create_user(self, user_data: dict[str, Any]) -> str | None:
        """Create a new user in Keycloak.

        Args:
            user_data: User data including username, email, etc.

        Returns:
            ID of the created user

        Raises:
            ValueError: If creating user fails
        """
        # This is a write operation, no caching needed
        try:
            user_id = self.admin_adapter.create_user(user_data)

            # Clear related caches
            self.clear_all_caches()

        except KeycloakError as e:
            self._handle_user_exception(e, "create_user", user_data)
        else:
            return user_id

    @override
    def update_user(self, user_id: str, user_data: dict[str, Any]) -> None:
        """Update user details.

        Args:
            user_id: User's ID
            user_data: User data to update

        Raises:
            ValueError: If updating user fails
        """
        # This is a write operation, no caching needed
        try:
            self.admin_adapter.update_user(user_id, user_data)

            # Clear user-related caches
            self.clear_all_caches()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_user")

    @override
    def reset_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Reset a user's password.

        Args:
            user_id: User's ID
            password: New password
            temporary: Whether the password is temporary and should be changed on next login

        Raises:
            ValueError: If password reset fails
        """
        # This is a write operation, no caching needed
        try:
            self.admin_adapter.set_user_password(user_id, password, temporary)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "reset_password")

    @override
    def assign_realm_role(self, user_id: str, role_name: str) -> None:
        """Assign a realm role to a user.

        Args:
            user_id: User's ID
            role_name: Role name to assign

        Raises:
            ValueError: If role assignment fails
        """
        # This is a write operation, no caching needed
        try:
            # Get role representation
            role = self.admin_adapter.get_realm_role(role_name)
            # Assign role to user
            self.admin_adapter.assign_realm_roles(user_id, [role])

            # Clear role-related caches
            if hasattr(self.get_user_roles, "clear_cache"):
                self.get_user_roles.clear_cache()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "assign_realm_role")

    @override
    def remove_realm_role(self, user_id: str, role_name: str) -> None:
        """Remove a realm role from a user.

        Args:
            user_id: User's ID
            role_name: Role name to remove

        Raises:
            ValueError: If role removal fails
        """
        # This is a write operation, no caching needed
        try:
            # Get role representation
            role = self.admin_adapter.get_realm_role(role_name)
            # Remove role from user
            self.admin_adapter.delete_realm_roles_of_user(user_id, [role])

            # Clear role-related caches
            if hasattr(self.get_user_roles, "clear_cache"):
                self.get_user_roles.clear_cache()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "remove_realm_role")

    @override
    def assign_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Assign a client-specific role to a user.

        Args:
            user_id: User's ID
            client_id: Client ID
            role_name: Role name to assign

        Raises:
            ValueError: If role assignment fails
        """
        # This is a write operation, no caching needed
        try:
            # Get client
            client = self.admin_adapter.get_client_id(client_id)
            if client is None:
                raise ValueError("client_id resolved to None")
            # Get role representation
            # Keycloak admin adapter methods accept these types at runtime
            role = self.admin_adapter.get_client_role(client, role_name)
            # Assign role to user
            self.admin_adapter.assign_client_role(user_id, client, [role])

            # Clear role-related caches
            if hasattr(self.get_client_roles_for_user, "clear_cache"):
                self.get_client_roles_for_user.clear_cache()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "assign_client_role")

    @override
    def create_realm_role(
        self,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
        """Create a new realm role.

        Args:
            role_name: Role name
            description: Optional role description
            skip_exists: Skip creation if realm role already exists

        Returns:
            Created role details

        Raises:
            ValueError: If role creation fails
        """
        # This is a write operation, no caching needed
        try:
            role_data = {"name": role_name}
            if description:
                role_data["description"] = description

            self.admin_adapter.create_realm_role(role_data, skip_exists=skip_exists)

            # Clear realm roles cache
            if hasattr(self.get_realm_roles, "clear_cache"):
                self.get_realm_roles.clear_cache()

            return self.admin_adapter.get_realm_role(role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_realm_role")

    @override
    def create_client_role(
        self,
        client_id: str,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
        """Create a new client role.

        Args:
            client_id: Client ID or client name
            role_name: Role name
            description: Optional role description
            skip_exists: Skip creation if client role already exists

        Returns:
            Created role details

        Raises:
            ValueError: If role creation fails
        """
        # This is a write operation, no caching needed
        try:
            resolved_client_id = self.admin_adapter.get_client_id(client_id)
            if resolved_client_id is None:
                raise ValueError(f"Client ID not found: {client_id}")

            # Prepare role data
            role_data = {"name": role_name}
            if description:
                role_data["description"] = description

            # Create client role
            self.admin_adapter.create_client_role(resolved_client_id, role_data, skip_exists=skip_exists)

            # Clear related caches if they exist
            if hasattr(self.get_client_roles_for_user, "clear_cache"):
                self.get_client_roles_for_user.clear_cache()

            # Return created role
            return self.admin_adapter.get_client_role(resolved_client_id, role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_role")

    @override
    def delete_realm_role(self, role_name: str) -> None:
        """Delete a realm role.

        Args:
            role_name: Role name to delete

        Raises:
            ValueError: If role deletion fails
        """
        # This is a write operation, no caching needed
        try:
            self.admin_adapter.delete_realm_role(role_name)

            # Clear realm roles cache
            if hasattr(self.get_realm_roles, "clear_cache"):
                self.get_realm_roles.clear_cache()

            # We also need to clear user role caches since they might contain this role
            if hasattr(self.get_user_roles, "clear_cache"):
                self.get_user_roles.clear_cache()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_realm_role")

    @override
    @ttl_cache_decorator(ttl_seconds=3600, maxsize=1)  # Cache for 1 hour
    def get_service_account_id(self) -> str | None:
        """Get service account user ID for the current client.

        Returns:
            Service account user ID

        Raises:
            ValueError: If getting service account fails
        """
        try:
            client_id = self.get_client_id(self.configs.CLIENT_ID)
            return self.admin_adapter.get_client_service_account_user(str(client_id)).get("id")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_service_account_id")

    @override
    @ttl_cache_decorator(ttl_seconds=3600, maxsize=1)  # Cache for 1 hour
    def get_well_known_config(self) -> dict[str, Any] | None:
        """Get the well-known OpenID configuration.

        Returns:
            OIDC configuration

        Raises:
            ValueError: If getting configuration fails
        """
        try:
            return self._openid_adapter.well_known()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_well_known_config")

    @override
    @ttl_cache_decorator(ttl_seconds=3600, maxsize=1)  # Cache for 1 hour
    def get_certs(self) -> dict[str, Any] | None:
        """Get the JWT verification certificates.

        Returns:
            Certificate information

        Raises:
            ValueError: If getting certificates fails
        """
        try:
            return self._openid_adapter.certs()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_certs")

    @override
    def get_token_from_code(self, code: str, redirect_uri: str) -> KeycloakTokenType | None:
        """Exchange authorization code for token.

        Args:
            code: Authorization code
            redirect_uri: Redirect URI used in authorization request

        Returns:
            Token response

        Raises:
            ValueError: If token exchange fails
        """
        # Authorization codes can only be used once, don't cache
        try:
            return self._openid_adapter.token(grant_type="authorization_code", code=code, redirect_uri=redirect_uri)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token_from_code")

    @override
    def get_client_credentials_token(self) -> KeycloakTokenType | None:
        """Get token using client credentials.

        Returns:
            Token response

        Raises:
            ValueError: If token acquisition fails
        """
        # Tokens are time-sensitive, don't cache
        try:
            return self._openid_adapter.token(grant_type="client_credentials")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_credentials_token")

    @override
    @ttl_cache_decorator(ttl_seconds=30, maxsize=50)  # Cache for 30 seconds with limited entries
    def search_users(self, query: str, max_results: int = 100) -> list[KeycloakUserType] | None:
        """Search for users by username, email, or name.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of matching users

        Raises:
            ValueError: If search fails
        """
        try:
            # Try searching by different fields
            users = []

            # Search by username
            users.extend(self.admin_adapter.get_users({"username": query, "max": max_results}))

            # Search by email if no results or incomplete results
            if len(users) < max_results:
                remaining = max_results - len(users)
                email_users = self.admin_adapter.get_users({"email": query, "max": remaining})
                # Filter out duplicates
                user_ids = {user["id"] for user in users}
                users.extend([user for user in email_users if user["id"] not in user_ids])

            # Search by firstName if no results or incomplete results
            if len(users) < max_results:
                remaining = max_results - len(users)
                first_name_users = self.admin_adapter.get_users({"firstName": query, "max": remaining})
                # Filter out duplicates
                user_ids = {user["id"] for user in users}
                users.extend([user for user in first_name_users if user["id"] not in user_ids])

            # Search by lastName if no results or incomplete results
            if len(users) < max_results:
                remaining = max_results - len(users)
                last_name_users = self.admin_adapter.get_users({"lastName": query, "max": remaining})
                # Filter out duplicates
                user_ids = {user["id"] for user in users}
                users.extend([user for user in last_name_users if user["id"] not in user_ids])

            return users[:max_results]
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "search_users")

    @override
    @ttl_cache_decorator(ttl_seconds=3600, maxsize=50)  # Cache for 1 hour
    def get_client_secret(self, client_id: str) -> str | None:
        """Get client secret.

        Args:
            client_id: Client ID

        Returns:
            Client secret

        Raises:
            ValueError: If getting secret fails
        """
        try:
            client = self.admin_adapter.get_client(client_id)
            return client.get("secret", "")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_secret")

    @override
    @ttl_cache_decorator(ttl_seconds=3600, maxsize=50)  # Cache for 1 hour
    def get_client_id(self, client_name: str) -> str | None:
        """Get client ID by client name.

        Args:
            client_name: Name of the client

        Returns:
            Client ID

        Raises:
            ValueError: If client not found
        """
        try:
            return self.admin_adapter.get_client_id(client_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_id")

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=1)  # Cache for 5 minutes
    def get_realm_roles(self) -> list[dict[str, Any]] | None:
        """Get all realm roles.

        Returns:
            List of realm roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return self.admin_adapter.get_realm_roles()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm_roles")

    @override
    @ttl_cache_decorator(ttl_seconds=300, maxsize=1)  # Cache for 5 minutes
    def get_realm_role(self, role_name: str) -> dict | None:
        """Get realm role.

        Args:
            role_name: Role name
        Returns:
            A realm role

        Raises:
            ValueError: If getting role fails
        """
        try:
            return self.admin_adapter.get_realm_role(role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm_role")

    @override
    def remove_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Remove a client-specific role from a user.

        Args:
            user_id: User's ID
            client_id: Client ID
            role_name: Role name to remove

        Raises:
            ValueError: If role removal fails
        """
        try:
            client = self.admin_adapter.get_client_id(client_id)
            if client is None:
                raise ValueError("client_id resolved to None")
            # Keycloak admin adapter methods accept these types at runtime
            role = self.admin_adapter.get_client_role(client, role_name)
            self.admin_adapter.delete_client_roles_of_user(user_id, client, [role])

            if hasattr(self.get_client_roles_for_user, "clear_cache"):
                self.get_client_roles_for_user.clear_cache()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "remove_client_role")

    @override
    def clear_user_sessions(self, user_id: str) -> None:
        """Clear all sessions for a user.

        Args:
            user_id: User's ID

        Raises:
            ValueError: If clearing sessions fails
        """
        try:
            self.admin_adapter.user_logout(user_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "clear_user_sessions")

    @override
    def logout(self, refresh_token: str) -> None:
        """Logout user by invalidating their refresh token.

        Args:
            refresh_token: Refresh token to invalidate

        Raises:
            ValueError: If logout fails
        """
        try:
            self._openid_adapter.logout(refresh_token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "logout")

    @override
    def introspect_token(self, token: str) -> dict[str, Any] | None:
        """Introspect token to get detailed information about it.

        Args:
            token: Access token

        Returns:
            Token introspection details

        Raises:
            ValueError: If token introspection fails
        """
        try:
            return self._openid_adapter.introspect(token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "introspect_token")

    @override
    def get_token_info(self, token: str) -> dict[str, Any] | None:
        """Decode token to get its claims.

        Args:
            token: Access token

        Returns:
            Dictionary of token claims

        Raises:
            ValueError: If token decoding fails
        """
        try:
            # Let the underlying adapter handle key selection to align with expected types
            return self._openid_adapter.decode_token(token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token_info")

    @override
    def delete_user(self, user_id: str) -> None:
        """Delete a user from Keycloak by their ID.

        Args:
            user_id: The ID of the user to delete

        Raises:
            ValueError: If the deletion fails
        """
        try:
            self.admin_adapter.delete_user(user_id=user_id)

            if hasattr(self.get_user_by_username, "clear_cache"):
                self.get_user_by_username.clear_cache()

            logger.info(f"Successfully deleted user with ID {user_id}")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_user")

    @override
    def has_role(self, token: str, role_name: str) -> bool:
        """Check if a user has a specific role.

        Args:
            token: Access token
            role_name: Role name to check

        Returns:
            True if user has the role, False otherwise
        """
        # Not caching this result as token validation is time-sensitive
        try:
            user_info = self.get_userinfo(token)
            if not user_info:
                return False

            # Check realm roles
            realm_access = user_info.get("realm_access", {})
            roles = realm_access.get("roles", [])
            if role_name in roles:
                return True

            # Check client roles
            resource_access = user_info.get("resource_access", {})
            client_roles = resource_access.get(self.configs.CLIENT_ID, {}).get("roles", [])
            if role_name in client_roles:
                return True

        except Exception as e:
            logger.debug(f"Role check failed: {e!s}")
            return False
        else:
            return False

    @override
    def has_any_of_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has any of the specified roles.

        Args:
            token: Access token
            role_names: Set of role names to check

        Returns:
            True if user has any of the roles, False otherwise
        """
        try:
            user_info = self.get_userinfo(token)
            if not user_info:
                return False

            # Check realm roles first
            realm_access = user_info.get("realm_access", {})
            realm_roles = set(realm_access.get("roles", []))
            if role_names.intersection(realm_roles):
                return True

            # Check roles for the configured client
            resource_access = user_info.get("resource_access", {})
            client_roles = set(resource_access.get(self.configs.CLIENT_ID, {}).get("roles", []))
            if role_names.intersection(client_roles):
                return True

        except Exception as e:
            logger.debug(f"Role check failed: {e!s}")
            return False
        else:
            return False

    @override
    def has_all_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has all the specified roles.

        Args:
            token: Access token
            role_names: Set of role names to check

        Returns:
            True if user has all the roles, False otherwise
        """
        try:
            user_info = self.get_userinfo(token)
            if not user_info:
                return False

            # Get all user roles
            all_roles = set()

            # Add realm roles
            realm_access = user_info.get("realm_access", {})
            all_roles.update(realm_access.get("roles", []))

            # Add client roles
            resource_access = user_info.get("resource_access", {})
            client_roles = resource_access.get(self.configs.CLIENT_ID, {}).get("roles", [])
            all_roles.update(client_roles)

            # Check if all required roles are present
            return role_names.issubset(all_roles)

        except Exception as e:
            logger.debug(f"All roles check failed: {e!s}")
            return False

    @override
    @ttl_cache_decorator(ttl_seconds=30, maxsize=200)
    def check_permissions_batch(
        self,
        token: str,
        permissions: tuple[tuple[str, str], ...],
    ) -> frozenset[tuple[str, str]]:
        """Return the subset of (resource, scope) pairs the token is authorized for in one UMA call.

        Prefer this over :meth:`check_permissions` when multiple pairs must be checked per request.

        Args:
            token: Access token
            permissions: Tuple of (resource, scope) pairs to check

        Returns:
            Subset of ``permissions`` that are granted
        """
        if not permissions:
            return frozenset()
        perm_strs = [f"{resource}#{scope}" for resource, scope in permissions]
        try:
            results = self._openid_adapter.uma_permissions(token, permissions=perm_strs)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "check_permissions_batch")
        if not results or not isinstance(results, list):
            return frozenset()
        granted: set[tuple[str, str]] = set()
        requested = set(permissions)
        for perm in results:
            rsname = perm.get("rsname")
            for scope in perm.get("scopes", []) or []:
                pair = (rsname, scope)
                if pair in requested:
                    granted.add(pair)
        return frozenset(granted)

    @override
    def check_permissions(self, token: str, resource: str, scope: str) -> bool:
        """Check if a user has permission to access a resource with the specified scope.

        Prefer :meth:`check_permissions_batch` when checking multiple pairs per request.

        Args:
            token: Access token
            resource: Resource name
            scope: Permission scope

        Returns:
            True if permission granted, False otherwise
        """
        try:
            # Use UMA permissions endpoint to check specific resource and scope
            permissions = self._openid_adapter.uma_permissions(token, permissions=f"{resource}#{scope}")

            # Check if the response indicates permission is granted
            if not permissions or not isinstance(permissions, list):
                logger.debug("No permissions returned or invalid response format")
                return False

            # Look for the specific permission in the response
            for perm in permissions:
                if perm.get("rsname") == resource and scope in perm.get("scopes", []):
                    return True

        except KeycloakError as e:
            logger.debug(f"Permission check failed with Keycloak error: {e!s}")
            return False
        except Exception as e:
            logger.debug(f"Permission check failed with unexpected error: {e!s}")
            return False
        else:
            return False

    @override
    def create_realm(self, realm_name: str, skip_exists: bool = True, **kwargs: Any) -> dict[str, Any] | None:
        """Create a Keycloak realm with minimum required fields and optional additional config.

        Args:
            realm_name: The realm identifier (required)
            skip_exists: Skip creation if realm already exists
            kwargs: Additional optional configurations for the realm

        Returns:
            Realm details
        """
        payload = {
            "realm": realm_name,
            "enabled": kwargs.get("enabled", True),
            "displayName": kwargs.get("display_name", realm_name),
        }

        # Add any additional parameters from kwargs
        for key, value in kwargs.items():
            # Skip display_name as it's already handled
            if key == "display_name":
                continue

            # Convert Python snake_case to Keycloak camelCase
            camel_key = StringUtils.snake_to_camel_case(key)
            payload[camel_key] = value

        try:
            self.admin_adapter.create_realm(payload=payload, skip_exists=skip_exists)
        except KeycloakError as e:
            logger.debug(f"Failed to create realm: {e!s}")

            # Handle realm already exists with skip_exists option
            if skip_exists:
                error_message = self._extract_error_message(e).lower()
                if "already exists" in error_message and "realm" in error_message:
                    return {"realm": realm_name, "status": "already_exists", "config": payload}

            # Use the mixin to handle realm-specific errors
            self._handle_realm_exception(e, "create_realm", realm_name)
        else:
            return {"realm": realm_name, "status": "created", "config": payload}

    @override
    def get_realm(self, realm_name: str) -> dict[str, Any] | None:
        """Get realm details by realm name.

        Args:
            realm_name: Name of the realm

        Returns:
            Realm details
        """
        try:
            return self.admin_adapter.get_realm(realm_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm")

    @override
    def update_realm(self, realm_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Update a realm. Kwargs are RealmRepresentation.

        Args:
            realm_name: Realm name (not the realm id).
            **kwargs: RealmRepresentation attributes to update (e.g. displayName).

        Returns:
            Response from Keycloak, or None on error (handled via exception).
        """
        try:
            return self.admin_adapter.update_realm(realm_name, dict(kwargs))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_realm")

    @override
    def create_client(
        self,
        client_id: str,
        realm: str | None = None,
        skip_exists: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Create a Keycloak client with minimum required fields and optional additional config.

        Args:
            client_id: The client identifier (required)
            realm: Target realm name (uses the current realm in KeycloakAdmin if not specified)
            skip_exists: Skip creation if client already exists
            kwargs: Additional optional configurations for the client

        Returns:
            Client details
        """
        original_realm = self.admin_adapter.connection.realm_name

        try:
            # Set the target realm if provided
            if realm and realm != original_realm:
                self.admin_adapter.connection.realm_name = realm

            public_client = kwargs.get("public_client", False)

            # Prepare the minimal client payload
            payload = {
                "clientId": client_id,
                "enabled": kwargs.get("enabled", True),
                "protocol": kwargs.get("protocol", "openid-connect"),
                "name": kwargs.get("name", client_id),
                "publicClient": public_client,
            }

            # Enable service accounts for confidential clients by default
            if not public_client:
                payload["serviceAccountsEnabled"] = kwargs.get("service_account_enabled", True)
                payload["clientAuthenticatorType"] = "client-secret"

            for key, value in kwargs.items():
                if key in ["enabled", "protocol", "name", "public_client", "service_account_enabled"]:
                    continue

                # Convert snake_case to camelCase
                camel_key = StringUtils.snake_to_camel_case(key)
                payload[camel_key] = value

            internal_client_id = None
            try:
                internal_client_id = self.admin_adapter.create_client(payload, skip_exists=skip_exists)
            except KeycloakError as e:
                logger.debug(f"Failed to create client: {e!s}")

                # Handle client already exists with skip_exists option
                if skip_exists:
                    error_message = self._extract_error_message(e).lower()
                    if "already exists" in error_message and "client" in error_message:
                        return {
                            "client_id": client_id,
                            "status": "already_exists",
                            "realm": self.admin_adapter.connection.realm_name,
                        }

                # Use the mixin to handle client-specific errors
                client_data = {"clientId": client_id, "name": kwargs.get("name", client_id)}
                self._handle_client_exception(e, "create_client", client_data)

            return {
                "client_id": client_id,
                "internal_client_id": internal_client_id,
                "realm": self.admin_adapter.connection.realm_name,
                "status": "created",
            }

        finally:
            # Always restore the original realm
            if realm and realm != original_realm:
                self.admin_adapter.connection.realm_name = original_realm

    @override
    def add_realm_roles_to_composite(self, composite_role_name: str, child_role_names: list[str]) -> None:
        """Add realm roles to a composite role.

        Args:
            composite_role_name: Name of the composite realm role
            child_role_names: List of child role names to add
        """
        try:
            child_roles = []
            for role_name in child_role_names:
                try:
                    role = self.admin_adapter.get_realm_role(role_name)
                    child_roles.append(role)
                except KeycloakGetError as e:
                    if e.response_code == 404:
                        logger.warning(f"Child role not found: {role_name}")
                        continue
                    raise

            if child_roles:
                self.admin_adapter.add_composite_realm_roles_to_role(role_name=composite_role_name, roles=child_roles)
                logger.info(f"Added {len(child_roles)} realm roles to composite role: {composite_role_name}")

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_realm_roles_to_composite")

    @override
    def add_client_roles_to_composite(
        self,
        composite_role_name: str,
        client_id: str,
        child_role_names: list[str],
    ) -> None:
        """Add client roles to a composite role.

        Args:
            composite_role_name: Name of the composite client role
            client_id: Client ID or client name
            child_role_names: List of child role names to add
        """
        try:
            internal_client_id = self.admin_adapter.get_client_id(client_id)
            if internal_client_id is None:
                raise ValueError("client_id resolved to None")

            child_roles = []
            for role_name in child_role_names:
                try:
                    # Keycloak admin adapter methods accept these types at runtime
                    role = self.admin_adapter.get_client_role(internal_client_id, role_name)
                    child_roles.append(role)
                except KeycloakGetError as e:
                    if e.response_code == 404:
                        logger.warning(f"Client role not found: {role_name}")
                        continue
                    raise

            if child_roles:
                if internal_client_id is None:
                    raise ValueError("Client ID not found")
                resolved_client_id: str = internal_client_id
                self.admin_adapter.add_composite_client_roles_to_role(
                    role_name=composite_role_name,
                    client_role_id=resolved_client_id,
                    roles=child_roles,
                )
                logger.info(f"Added {len(child_roles)} client roles to composite role: {composite_role_name}")

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_client_roles_to_composite")

    @override
    def get_composite_realm_roles(self, role_name: str) -> list[dict[str, Any]] | None:
        """Get composite roles for a realm role.

        Args:
            role_name: Name of the role

        Returns:
            List of composite roles
        """
        try:
            return self.admin_adapter.get_composite_realm_roles_of_role(role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_composite_realm_roles")

    @override
    def get_organizations(self, query: dict | None = None) -> list[dict[str, Any]]:
        """Fetch all organizations, optionally filtered by query parameters."""
        try:
            return self.admin_adapter.get_organizations(query=query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_organizations")

    @override
    def get_organization(self, organization_id: str) -> dict[str, Any]:
        """Get representation of the organization by ID."""
        try:
            return self.admin_adapter.get_organization(organization_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_organization")

    @override
    def create_organization(self, name: str, alias: str, **kwargs: Any) -> str | None:
        """Create a new organization. Name and alias must be unique. Returns org_id."""
        try:
            payload = {"name": name, "alias": alias}
            for key, value in kwargs.items():
                if key in ["name", "alias"]:
                    continue

                # Convert snake_case to camelCase
                camel_key = StringUtils.snake_to_camel_case(key)
                payload[camel_key] = value

            return self.admin_adapter.create_organization(payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_organization")

    @override
    def update_organization(self, organization_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update an existing organization. Kwargs are organization attributes (e.g. name, alias)."""
        try:
            payload = {}
            for key, value in kwargs.items():
                # Convert snake_case to camelCase
                camel_key = StringUtils.snake_to_camel_case(key)
                payload[camel_key] = value

            return self.admin_adapter.update_organization(organization_id=organization_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_organization")

    @override
    def delete_organization(self, organization_id: str) -> dict[str, Any]:
        """Delete an organization."""
        try:
            return self.admin_adapter.delete_organization(organization_id=organization_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_organization")

    @override
    def get_user_organizations(self, user_id: str) -> list[dict[str, Any]]:
        """Get organizations by user id."""
        try:
            return self.admin_adapter.get_user_organizations(user_id=user_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_organizations")

    @override
    def get_organization_members(self, organization_id: str, query: dict | None = None) -> list[dict[str, Any]]:
        """Get members by organization id, optionally filtered by query parameters."""
        try:
            return self.admin_adapter.get_organization_members(organization_id=organization_id, query=query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_organization_members")

    @override
    def get_organization_members_count(self, organization_id: str) -> int:
        """Get the number of members in the organization."""
        try:
            return self.admin_adapter.get_organization_members_count(organization_id=organization_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_organization_members_count")

    @override
    def organization_user_add(self, user_id: str, organization_id: str) -> bytes:
        """Add a user to an organization."""
        try:
            return self.admin_adapter.organization_user_add(user_id=user_id, organization_id=organization_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "organization_user_add")

    @override
    def organization_user_remove(self, user_id: str, organization_id: str) -> dict[str, Any]:
        """Remove a user from an organization."""
        try:
            return self.admin_adapter.organization_user_remove(user_id=user_id, organization_id=organization_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "organization_user_remove")

    # Group Operations
    @override
    def create_group(self, payload: dict, parent: str | None = None, skip_exists: bool = False) -> str | None:
        """Create a new group."""
        try:
            return self.admin_adapter.create_group(payload=payload, parent=parent, skip_exists=skip_exists)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_group")

    @override
    def update_group(self, group_id: str, payload: dict) -> dict[str, Any]:
        """Update a group."""
        try:
            return self.admin_adapter.update_group(group_id=group_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_group")

    @override
    def delete_group(self, group_id: str) -> dict[str, Any]:
        """Delete a group."""
        try:
            return self.admin_adapter.delete_group(group_id=group_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_group")

    @override
    def get_group(self, group_id: str, full_hierarchy: bool = False, query: dict | None = None) -> dict[str, Any]:
        """Get group representation by ID."""
        try:
            return self.admin_adapter.get_group(group_id=group_id, full_hierarchy=full_hierarchy, query=query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_group")

    @override
    def get_group_by_path(self, path: str) -> dict[str, Any]:
        """Get group representation by path."""
        try:
            return self.admin_adapter.get_group_by_path(path=path)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_group_by_path")

    @override
    def get_group_children(
        self,
        group_id: str,
        query: dict | None = None,
        full_hierarchy: bool = False,
    ) -> list[dict[str, Any]]:
        """Get child groups of a group."""
        try:
            return self.admin_adapter.get_group_children(group_id=group_id, query=query, full_hierarchy=full_hierarchy)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_group_children")

    @override
    def get_groups(self, query: dict | None = None, full_hierarchy: bool = False) -> list[dict[str, Any]]:
        """Get all groups, optionally filtered by query."""
        try:
            return self.admin_adapter.get_groups(query=query, full_hierarchy=full_hierarchy)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_groups")

    @override
    def get_subgroups(self, group: dict, path: str) -> dict[str, Any] | None:
        """Get subgroups for a group at the given path."""
        try:
            return self.admin_adapter.get_subgroups(group=group, path=path)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_subgroups")

    @override
    def groups_count(self, query: dict | None = None) -> dict[str, Any]:
        """Get the number of groups matching the query."""
        try:
            return self.admin_adapter.groups_count(query=query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "groups_count")

    @override
    def group_user_add(self, user_id: str, group_id: str) -> dict[str, Any]:
        """Add a user to a group."""
        try:
            return self.admin_adapter.group_user_add(user_id=user_id, group_id=group_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "group_user_add")

    @override
    def group_user_remove(self, user_id: str, group_id: str) -> dict[str, Any]:
        """Remove a user from a group."""
        try:
            return self.admin_adapter.group_user_remove(user_id=user_id, group_id=group_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "group_user_remove")

    @override
    def group_set_permissions(self, group_id: str, enabled: bool = True) -> dict[str, Any]:
        """Enable or disable fine-grained permissions for a group."""
        try:
            return self.admin_adapter.group_set_permissions(group_id=group_id, enabled=enabled)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "group_set_permissions")

    @override
    def get_group_members(self, group_id: str, query: dict | None = None) -> list[dict[str, Any]]:
        """Get members of a group."""
        try:
            return self.admin_adapter.get_group_members(group_id=group_id, query=query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_group_members")

    @override
    def get_group_client_roles(self, group_id: str, client_id: str) -> list[dict[str, Any]]:
        """Get client roles assigned to a group."""
        try:
            return self.admin_adapter.get_group_client_roles(group_id=group_id, client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_group_client_roles")

    @override
    def get_group_realm_roles(self, group_id: str, brief_representation: bool = True) -> list[dict[str, Any]]:
        """Get realm roles assigned to a group."""
        try:
            return self.admin_adapter.get_group_realm_roles(
                group_id=group_id,
                brief_representation=brief_representation,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_group_realm_roles")

    @override
    def assign_group_client_roles(self, group_id: str, client_id: str, roles: str | list) -> dict[str, Any]:
        """Assign client roles to a group."""
        try:
            return self.admin_adapter.assign_group_client_roles(group_id=group_id, client_id=client_id, roles=roles)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "assign_group_client_roles")

    @override
    def assign_group_realm_roles(self, group_id: str, roles: str | list) -> dict[str, Any]:
        """Assign realm roles to a group."""
        try:
            return self.admin_adapter.assign_group_realm_roles(group_id=group_id, roles=roles)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "assign_group_realm_roles")

    @override
    def delete_group_client_roles(self, group_id: str, client_id: str, roles: str | list) -> dict[str, Any]:
        """Remove client roles from a group."""
        try:
            return self.admin_adapter.delete_group_client_roles(group_id=group_id, client_id=client_id, roles=roles)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_group_client_roles")

    @override
    def delete_group_realm_roles(self, group_id: str, roles: str | list) -> dict[str, Any]:
        """Remove realm roles from a group."""
        try:
            return self.admin_adapter.delete_group_realm_roles(group_id=group_id, roles=roles)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_group_realm_roles")

    @override
    def get_composite_client_roles_of_group(
        self,
        client_id: str,
        group_id: str,
        brief_representation: bool = True,
    ) -> list[dict[str, Any]]:
        """Get composite client roles of a group."""
        try:
            return self.admin_adapter.get_composite_client_roles_of_group(
                client_id=client_id,
                group_id=group_id,
                brief_representation=brief_representation,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_composite_client_roles_of_group")

    @override
    def get_client_role_groups(self, client_id: str, role_name: str, query: Any) -> list[dict[str, Any]]:
        """Get groups that have a specific client role."""
        try:
            return self.admin_adapter.get_client_role_groups(client_id=client_id, role_name=role_name, **query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_role_groups")

    @override
    def get_realm_role_groups(
        self,
        role_name: str,
        query: dict | None = None,
        brief_representation: bool = True,
    ) -> list[dict[str, Any]]:
        """Get groups that have a specific realm role."""
        try:
            return self.admin_adapter.get_realm_role_groups(
                role_name=role_name,
                query=query,
                brief_representation=brief_representation,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm_role_groups")

    # Authentication Flow Operations
    @override
    def create_authentication_flow(self, payload: dict, skip_exists: bool = False) -> bytes:
        """Create a new authentication flow."""
        try:
            return self.admin_adapter.create_authentication_flow(payload=payload, skip_exists=skip_exists)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_authentication_flow")

    @override
    def copy_authentication_flow(self, payload: dict, flow_alias: str) -> bytes:
        """Copy an existing authentication flow."""
        try:
            return self.admin_adapter.copy_authentication_flow(payload=payload, flow_alias=flow_alias)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "copy_authentication_flow")

    @override
    def get_authentication_flows(
        self,
    ) -> list[dict[str, Any]]:
        """Get all authentication flows."""
        try:
            return self.admin_adapter.get_authentication_flows()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authentication_flows")

    @override
    def get_authentication_flow_for_id(self, flow_id: str) -> dict[str, Any]:
        """Get authentication flow by ID."""
        try:
            return self.admin_adapter.get_authentication_flow_for_id(flow_id=flow_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authentication_flow_for_id")

    @override
    def delete_authentication_flow(self, flow_id: str) -> dict[str, Any]:
        """Delete an authentication flow."""
        try:
            return self.admin_adapter.delete_authentication_flow(flow_id=flow_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_authentication_flow")

    @override
    def get_authentication_flow_executions(self, flow_alias: str) -> list[dict[str, Any]]:
        """Get executions for an authentication flow."""
        try:
            return self.admin_adapter.get_authentication_flow_executions(flow_alias=flow_alias)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authentication_flow_executions")

    @override
    def get_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Get a single authentication flow execution."""
        try:
            return self.admin_adapter.get_authentication_flow_execution(execution_id=execution_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authentication_flow_execution")

    @override
    def create_authentication_flow_execution(self, payload: dict, flow_alias: str) -> bytes:
        """Create an execution in an authentication flow."""
        try:
            return self.admin_adapter.create_authentication_flow_execution(payload=payload, flow_alias=flow_alias)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_authentication_flow_execution")

    @override
    def update_authentication_flow_executions(self, payload: dict, flow_alias: str) -> dict[str, Any]:
        """Update executions in an authentication flow."""
        try:
            return self.admin_adapter.update_authentication_flow_executions(payload=payload, flow_alias=flow_alias)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_authentication_flow_executions")

    @override
    def create_authentication_flow_subflow(self, payload: dict, flow_alias: str, skip_exists: bool = False) -> bytes:
        """Create a subflow in an authentication flow."""
        try:
            return self.admin_adapter.create_authentication_flow_subflow(
                payload=payload,
                flow_alias=flow_alias,
                skip_exists=skip_exists,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_authentication_flow_subflow")

    @override
    def delete_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Delete an authentication flow execution."""
        try:
            return self.admin_adapter.delete_authentication_flow_execution(execution_id=execution_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_authentication_flow_execution")

    @override
    def change_execution_priority(self, execution_id: str, diff: int) -> None:
        """Change priority of an authentication flow execution."""
        try:
            return self.admin_adapter.change_execution_priority(execution_id=execution_id, diff=diff)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "change_execution_priority")

    @override
    def update_authentication_flow(self, flow_id: str, payload: dict) -> dict[str, Any]:
        """Update an authentication flow."""
        try:
            return self.admin_adapter.update_authentication_flow(flow_id=flow_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_authentication_flow")

    @override
    def get_authenticator_providers(
        self,
    ) -> list[dict[str, Any]]:
        """Get available authenticator providers."""
        try:
            return self.admin_adapter.get_authenticator_providers()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authenticator_providers")

    @override
    def get_authenticator_provider_config_description(self, provider_id: str) -> dict[str, Any]:
        """Get config description for an authenticator provider."""
        try:
            return self.admin_adapter.get_authenticator_provider_config_description(provider_id=provider_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authenticator_provider_config_description")

    @override
    def get_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Get authenticator configuration by ID."""
        try:
            return self.admin_adapter.get_authenticator_config(config_id=config_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authenticator_config")

    @override
    def update_authenticator_config(self, payload: dict, config_id: str) -> dict[str, Any]:
        """Update authenticator configuration."""
        try:
            return self.admin_adapter.update_authenticator_config(payload=payload, config_id=config_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_authenticator_config")

    @override
    def delete_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Delete authenticator configuration."""
        try:
            return self.admin_adapter.delete_authenticator_config(config_id=config_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_authenticator_config")

    @override
    def create_execution_config(self, execution_id: str, payload: dict) -> bytes:
        """Create configuration for an authentication flow execution."""
        try:
            return self.admin_adapter.create_execution_config(execution_id=execution_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_execution_config")

    # Client Scope Operations
    @override
    def get_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get all client scopes."""
        try:
            return self.admin_adapter.get_client_scopes()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_scopes")

    @override
    def get_client_scope(self, client_scope_id: str) -> dict[str, Any]:
        """Get a client scope by ID."""
        try:
            return self.admin_adapter.get_client_scope(client_scope_id=client_scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_scope")

    @override
    def get_client_scope_by_name(self, client_scope_name: str) -> dict[str, Any] | None:
        """Get a client scope by name."""
        try:
            return self.admin_adapter.get_client_scope_by_name(client_scope_name=client_scope_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_scope_by_name")

    @override
    def create_client_scope(self, payload: dict, skip_exists: bool = False) -> str:
        """Create a new client scope."""
        try:
            return self.admin_adapter.create_client_scope(payload=payload, skip_exists=skip_exists)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_scope")

    @override
    def update_client_scope(self, client_scope_id: str, payload: dict) -> dict[str, Any]:
        """Update a client scope."""
        try:
            return self.admin_adapter.update_client_scope(client_scope_id=client_scope_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_client_scope")

    @override
    def delete_client_scope(self, client_scope_id: str) -> dict[str, Any]:
        """Delete a client scope."""
        try:
            return self.admin_adapter.delete_client_scope(client_scope_id=client_scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_client_scope")

    @override
    def add_mapper_to_client_scope(self, client_scope_id: str, payload: dict) -> bytes:
        """Add a protocol mapper to a client scope."""
        try:
            return self.admin_adapter.add_mapper_to_client_scope(client_scope_id=client_scope_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_mapper_to_client_scope")

    @override
    def get_mappers_from_client_scope(self, client_scope_id: str) -> list[dict[str, Any]]:
        """Get protocol mappers for a client scope."""
        try:
            return self.admin_adapter.get_mappers_from_client_scope(client_scope_id=client_scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_mappers_from_client_scope")

    @override
    def update_mapper_in_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        """Update a protocol mapper in a client scope."""
        try:
            return self.admin_adapter.update_mapper_in_client_scope(
                client_scope_id=client_scope_id,
                protocol_mapper_id=protocol_mapper_id,
                payload=payload,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_mapper_in_client_scope")

    @override
    def delete_mapper_from_client_scope(self, client_scope_id: str, protocol_mapper_id: str) -> dict[str, Any]:
        """Delete a protocol mapper from a client scope."""
        try:
            return self.admin_adapter.delete_mapper_from_client_scope(
                client_scope_id=client_scope_id,
                protocol_mapper_id=protocol_mapper_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_mapper_from_client_scope")

    @override
    def add_mapper_to_client(self, client_id: str, payload: dict) -> bytes:
        """Add a protocol mapper to a client."""
        try:
            return self.admin_adapter.add_mapper_to_client(client_id=client_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_mapper_to_client")

    @override
    def get_mappers_from_client(self, client_id: str) -> list[dict[str, Any]]:
        """Get protocol mappers for a client."""
        try:
            return self.admin_adapter.get_mappers_from_client(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_mappers_from_client")

    @override
    def update_client_mapper(self, client_id: str, mapper_id: str, payload: dict) -> dict[str, Any]:
        """Update a protocol mapper on a client."""
        try:
            return self.admin_adapter.update_client_mapper(client_id=client_id, mapper_id=mapper_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_client_mapper")

    @override
    def remove_client_mapper(self, client_id: str, client_mapper_id: str) -> dict[str, Any]:
        """Remove a protocol mapper from a client."""
        try:
            return self.admin_adapter.remove_client_mapper(client_id=client_id, client_mapper_id=client_mapper_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "remove_client_mapper")

    @override
    def get_client_default_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get default client scopes for a client."""
        try:
            return self.admin_adapter.get_client_default_client_scopes(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_default_client_scopes")

    @override
    def add_client_default_client_scope(self, client_id: str, client_scope_id: str, payload: dict) -> dict[str, Any]:
        """Add a default client scope to a client."""
        try:
            return self.admin_adapter.add_client_default_client_scope(
                client_id=client_id,
                client_scope_id=client_scope_id,
                payload=payload,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_client_default_client_scope")

    @override
    def delete_client_default_client_scope(self, client_id: str, client_scope_id: str) -> dict[str, Any]:
        """Remove a default client scope from a client."""
        try:
            return self.admin_adapter.delete_client_default_client_scope(
                client_id=client_id,
                client_scope_id=client_scope_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_client_default_client_scope")

    @override
    def get_client_optional_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get optional client scopes for a client."""
        try:
            return self.admin_adapter.get_client_optional_client_scopes(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_optional_client_scopes")

    @override
    def add_client_optional_client_scope(self, client_id: str, client_scope_id: str, payload: dict) -> dict[str, Any]:
        """Add an optional client scope to a client."""
        try:
            return self.admin_adapter.add_client_optional_client_scope(
                client_id=client_id,
                client_scope_id=client_scope_id,
                payload=payload,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_client_optional_client_scope")

    @override
    def delete_client_optional_client_scope(self, client_id: str, client_scope_id: str) -> dict[str, Any]:
        """Remove an optional client scope from a client."""
        try:
            return self.admin_adapter.delete_client_optional_client_scope(
                client_id=client_id,
                client_scope_id=client_scope_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_client_optional_client_scope")

    @override
    def get_default_default_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get realm default client scopes."""
        try:
            return self.admin_adapter.get_default_default_client_scopes()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_default_default_client_scopes")

    @override
    def add_default_default_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Add a realm default client scope."""
        try:
            return self.admin_adapter.add_default_default_client_scope(scope_id=scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_default_default_client_scope")

    @override
    def delete_default_default_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Remove a realm default client scope."""
        try:
            return self.admin_adapter.delete_default_default_client_scope(scope_id=scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_default_default_client_scope")

    @override
    def get_default_optional_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get realm optional default client scopes."""
        try:
            return self.admin_adapter.get_default_optional_client_scopes()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_default_optional_client_scopes")

    @override
    def add_default_optional_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Add a realm optional default client scope."""
        try:
            return self.admin_adapter.add_default_optional_client_scope(scope_id=scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_default_optional_client_scope")

    @override
    def delete_default_optional_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Remove a realm optional default client scope."""
        try:
            return self.admin_adapter.delete_default_optional_client_scope(scope_id=scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_default_optional_client_scope")

    # Authorization Service Operations
    @override
    def create_client_authz_resource(self, client_id: str, payload: dict, skip_exists: bool = False) -> dict[str, Any]:
        """Create an authorization resource for a client."""
        try:
            return self.admin_adapter.create_client_authz_resource(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_resource")

    @override
    def get_client_authz_resources(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization resources for a client."""
        try:
            return self.admin_adapter.get_client_authz_resources(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_resources")

    @override
    def get_client_authz_resource(self, client_id: str, resource_id: str) -> dict[str, Any]:
        """Get a single authorization resource."""
        try:
            return self.admin_adapter.get_client_authz_resource(client_id=client_id, resource_id=resource_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_resource")

    @override
    def update_client_authz_resource(self, client_id: str, resource_id: str, payload: dict) -> dict[str, Any]:
        """Update an authorization resource."""
        try:
            return self.admin_adapter.update_client_authz_resource(
                client_id=client_id,
                resource_id=resource_id,
                payload=payload,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_client_authz_resource")

    @override
    def delete_client_authz_resource(self, client_id: str, resource_id: str) -> dict[str, Any]:
        """Delete an authorization resource."""
        try:
            return self.admin_adapter.delete_client_authz_resource(client_id=client_id, resource_id=resource_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_client_authz_resource")

    @override
    def create_client_authz_scopes(self, client_id: str, payload: dict) -> dict[str, Any]:
        """Create authorization scopes for a client."""
        try:
            return self.admin_adapter.create_client_authz_scopes(client_id=client_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_scopes")

    @override
    def get_client_authz_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization scopes for a client."""
        try:
            return self.admin_adapter.get_client_authz_scopes(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_scopes")

    @override
    def create_client_authz_role_based_policy(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create a role-based authorization policy."""
        try:
            return self.admin_adapter.create_client_authz_role_based_policy(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_role_based_policy")

    @override
    def create_client_authz_client_policy(self, payload: dict, client_id: str) -> dict[str, Any]:
        """Create a client-based authorization policy."""
        try:
            return self.admin_adapter.create_client_authz_client_policy(payload=payload, client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_client_policy")

    @override
    def create_client_authz_policy(self, client_id: str, payload: dict, skip_exists: bool = False) -> dict[str, Any]:
        """Create an authorization policy."""
        try:
            return self.admin_adapter.create_client_authz_policy(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_policy")

    @override
    def get_client_authz_policies(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization policies for a client."""
        try:
            return self.admin_adapter.get_client_authz_policies(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_policies")

    @override
    def get_client_authz_policy(self, client_id: str, policy_id: str) -> dict[str, Any]:
        """Get a single authorization policy."""
        try:
            return self.admin_adapter.get_client_authz_policy(client_id=client_id, policy_id=policy_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_policy")

    @override
    def delete_client_authz_policy(self, client_id: str, policy_id: str) -> dict[str, Any]:
        """Delete an authorization policy."""
        try:
            return self.admin_adapter.delete_client_authz_policy(client_id=client_id, policy_id=policy_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_client_authz_policy")

    @override
    def create_client_authz_resource_based_permission(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create a resource-based permission."""
        try:
            return self.admin_adapter.create_client_authz_resource_based_permission(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_resource_based_permission")

    @override
    def create_client_authz_scope_permission(self, payload: dict, client_id: str) -> dict[str, Any]:
        """Create a scope-based permission."""
        try:
            return self.admin_adapter.create_client_authz_scope_permission(payload=payload, client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_scope_permission")

    @override
    def get_client_authz_permissions(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization permissions for a client."""
        try:
            return self.admin_adapter.get_client_authz_permissions(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_permissions")

    @override
    def get_client_authz_scope_permission(self, client_id: str, scope_id: str) -> dict[str, Any]:
        """Get a scope-based permission."""
        try:
            return self.admin_adapter.get_client_authz_scope_permission(client_id=client_id, scope_id=scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_scope_permission")

    @override
    def update_client_authz_scope_permission(self, payload: dict, client_id: str, scope_id: str) -> bytes:
        """Update a scope-based permission."""
        try:
            return self.admin_adapter.update_client_authz_scope_permission(
                payload=payload,
                client_id=client_id,
                scope_id=scope_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_client_authz_scope_permission")

    @override
    def update_client_authz_resource_permission(self, payload: dict, client_id: str, resource_id: str) -> bytes:
        """Update a resource-based permission."""
        try:
            return self.admin_adapter.update_client_authz_resource_permission(
                payload=payload,
                client_id=client_id,
                resource_id=resource_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_client_authz_resource_permission")

    @override
    def get_client_authz_permission_associated_policies(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get policies associated with a permission."""
        try:
            return self.admin_adapter.get_client_authz_permission_associated_policies(
                client_id=client_id,
                policy_id=policy_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_permission_associated_policies")

    @override
    def get_client_authz_settings(self, client_id: str) -> dict[str, Any]:
        """Get authorization settings for a client."""
        try:
            return self.admin_adapter.get_client_authz_settings(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_settings")

    @override
    def get_client_authz_client_policies(self, client_id: str) -> list[dict[str, Any]]:
        """Get client policies for authorization."""
        try:
            return self.admin_adapter.get_client_authz_client_policies(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_client_policies")

    @override
    def get_client_authz_policy_resources(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get resources associated with a policy."""
        try:
            return self.admin_adapter.get_client_authz_policy_resources(client_id=client_id, policy_id=policy_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_policy_resources")

    @override
    def get_client_authz_policy_scopes(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get scopes associated with a policy."""
        try:
            return self.admin_adapter.get_client_authz_policy_scopes(client_id=client_id, policy_id=policy_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_policy_scopes")

    @override
    def import_client_authz_config(self, client_id: str, payload: dict) -> dict[str, Any]:
        """Import authorization configuration for a client."""
        try:
            return self.admin_adapter.import_client_authz_config(client_id=client_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "import_client_authz_config")

    # UMA Operations
    @override
    def resource_set_create(self, payload: dict) -> dict[str, Any]:
        """Create a UMA resource set."""
        try:
            return self.uma_adapter.resource_set_create(payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "resource_set_create")

    @override
    def resource_set_read(self, resource_id: str) -> dict[str, Any]:
        """Read a UMA resource set."""
        try:
            return self.uma_adapter.resource_set_read(resource_id=resource_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "resource_set_read")

    @override
    def resource_set_update(self, resource_id: str, payload: dict) -> dict[str, Any]:
        """Update a UMA resource set."""
        try:
            return self.uma_adapter.resource_set_update(resource_id=resource_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "resource_set_update")

    @override
    def resource_set_delete(self, resource_id: str) -> dict[str, Any]:
        """Delete a UMA resource set."""
        try:
            return self.uma_adapter.resource_set_delete(resource_id=resource_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "resource_set_delete")

    @override
    def resource_set_list(
        self,
    ) -> list[dict[str, Any]]:
        """List all UMA resource sets."""
        try:
            return list(self.uma_adapter.resource_set_list())
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "resource_set_list")

    @override
    def resource_set_list_ids(
        self,
        name: str = "",
        exact_name: bool = False,
        uri: str = "",
        owner: str = "",
        resource_type: str = "",
        scope: str = "",
        matchingUri: bool = False,
        first: int = 0,
        maximum: int = -1,
    ) -> list[dict[str, Any]]:
        """List UMA resource set IDs with optional filters."""
        try:
            return self.uma_adapter.resource_set_list_ids(
                name=name,
                exact_name=exact_name,
                uri=uri,
                owner=owner,
                resource_type=resource_type,
                scope=scope,
                matchingUri=matchingUri,
                first=first,
                maximum=maximum,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "resource_set_list_ids")

    @override
    def policy_resource_create(self, resource_id: str, payload: dict) -> dict[str, Any]:
        """Create a UMA policy for a resource."""
        try:
            return self.uma_adapter.policy_resource_create(resource_id=resource_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "policy_resource_create")

    @override
    def policy_update(self, policy_id: str, payload: dict) -> bytes:
        """Update a UMA policy."""
        try:
            return self.uma_adapter.policy_update(policy_id=policy_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "policy_update")

    @override
    def policy_delete(self, policy_id: str) -> dict[str, Any]:
        """Delete a UMA policy."""
        try:
            return self.uma_adapter.policy_delete(policy_id=policy_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "policy_delete")

    @override
    def policy_query(
        self,
        resource: str = "",
        name: str = "",
        scope: str = "",
        first: int = 0,
        maximum: int = -1,
    ) -> list[dict[str, Any]]:
        """Query UMA policies."""
        try:
            return self.uma_adapter.policy_query(
                resource=resource,
                name=name,
                scope=scope,
                first=first,
                maximum=maximum,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "policy_query")

    @override
    def permission_ticket_create(self, permissions: Iterable[UMAPermission]) -> dict[str, Any]:
        """Create a UMA permission ticket."""
        try:
            return self.uma_adapter.permission_ticket_create(permissions=permissions)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "permission_ticket_create")

    @override
    def permissions_check(self, token: str, permissions: Iterable[UMAPermission], **extra_payload: Any) -> bool:
        """Check UMA permissions for a token."""
        try:
            return self.uma_adapter.permissions_check(token=token, permissions=permissions, **extra_payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "permissions_check")

    # Component Operations
    @override
    def create_component(self, payload: dict) -> str:
        """Create a Keycloak component."""
        try:
            return self.admin_adapter.create_component(payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_component")

    @override
    def get_component(self, component_id: str) -> dict[str, Any]:
        """Get a component by ID."""
        try:
            return self.admin_adapter.get_component(component_id=component_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_component")

    @override
    def get_components(self, query: dict | None = None) -> list[dict[str, Any]]:
        """Get components, optionally filtered by query."""
        try:
            return self.admin_adapter.get_components(query=query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_components")

    @override
    def update_component(self, component_id: str, payload: dict) -> dict[str, Any]:
        """Update a component."""
        try:
            return self.admin_adapter.update_component(component_id=component_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_component")

    @override
    def delete_component(self, component_id: str) -> dict[str, Any]:
        """Delete a component."""
        try:
            return self.admin_adapter.delete_component(component_id=component_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_component")


class AsyncKeycloakAdapter(AsyncKeycloakPort, KeycloakExceptionHandlerMixin):
    """Concrete implementation of the KeycloakPort interface using python-keycloak library.

    This implementation includes TTL caching for appropriate operations to improve performance
    while ensuring cache entries expire after a configured time to prevent stale data.
    """

    def __init__(self, keycloak_configs: KeycloakConfig | None = None) -> None:
        """Initialize KeycloakAdapter with configuration.

        Args:
            keycloak_configs: Optional Keycloak configuration. If None, global config is used.
        """
        self.configs: KeycloakConfig = (
            BaseConfig.global_config().KEYCLOAK if keycloak_configs is None else keycloak_configs
        )

        # Initialize the OpenID client for authentication
        self.openid_adapter = self._get_openid_client(self.configs)

        # Cache for admin client to avoid unnecessary re-authentication
        self._admin_adapter: KeycloakAdmin | None = None
        self._admin_token_expiry: float = 0.0
        self._uma_adapter: KeycloakUMA | None = None

        # Initialize admin client if admin mode is enabled and credentials are provided
        if self.configs.IS_ADMIN_MODE_ENABLED and (
            self.configs.CLIENT_SECRET_KEY or (self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD)
        ):
            self._initialize_admin_client()

    def clear_all_caches(self) -> None:
        """Clear all cached values."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, "cache_clear"):
                attr.cache_clear()

    @staticmethod
    def _get_openid_client(configs: KeycloakConfig) -> KeycloakOpenID:
        """Create and configure a KeycloakOpenID instance.

        Args:
            configs: Keycloak configuration

        Returns:
            Configured KeycloakOpenID client
        """
        server_url = configs.SERVER_URL
        client_id = configs.CLIENT_ID
        if not server_url or not client_id:
            raise ValueError("SERVER_URL and CLIENT_ID must be provided")
        return KeycloakOpenID(
            server_url=server_url,
            client_id=client_id,
            realm_name=configs.REALM_NAME,
            client_secret_key=configs.CLIENT_SECRET_KEY,
            verify=configs.VERIFY_SSL,
            timeout=configs.TIMEOUT,
        )

    def _initialize_admin_client(self) -> None:
        """Initialize or refresh the admin client."""
        try:
            # Check if admin credentials are available
            if self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD:
                # Create admin client using admin credentials
                self._admin_adapter = KeycloakAdmin(
                    server_url=self.configs.SERVER_URL,
                    username=self.configs.ADMIN_USERNAME,
                    password=self.configs.ADMIN_PASSWORD,
                    realm_name=self.configs.REALM_NAME,
                    user_realm_name=self.configs.ADMIN_REALM_NAME,
                    verify=self.configs.VERIFY_SSL,
                    timeout=self.configs.TIMEOUT,
                )
                # Since we're using direct credentials, set a long expiry time
                self._admin_token_expiry = time.time() + 3600  # 1 hour
                logger.debug("Admin client initialized with admin credentials")
            elif self.configs.CLIENT_SECRET_KEY:
                # Get token using client credentials
                token = self.openid_adapter.token(grant_type="client_credentials")

                # Set token expiry time (current time + expires_in - buffer)
                # Using a 30-second buffer to ensure we refresh before expiration
                self._admin_token_expiry = time.time() + token.get("expires_in", 60) - 30

                # Create admin client with the token
                self._admin_adapter = KeycloakAdmin(
                    server_url=self.configs.SERVER_URL,
                    realm_name=self.configs.REALM_NAME,
                    token=token,
                    verify=self.configs.VERIFY_SSL,
                    timeout=self.configs.TIMEOUT,
                )
                logger.debug("Admin client initialized with client credentials")
            else:
                raise UnauthenticatedError(
                    additional_data={"detail": "Neither admin credentials nor client secret provided"},
                )

        except KeycloakAuthenticationError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            raise UnauthenticatedError(
                additional_data={"detail": "Failed to authenticate with Keycloak service account"},
            ) from e
        except KeycloakConnectionError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            raise ConnectionTimeoutError("Failed to connect to Keycloak server") from e
        except KeycloakError as e:
            self._admin_adapter = None
            self._admin_token_expiry = 0
            self._handle_keycloak_exception(e, "_initialize_admin_client")

    @property
    def admin_adapter(self) -> KeycloakAdmin:
        """Get the admin adapter, refreshing it if necessary.

        Returns:
            KeycloakAdmin instance

        Raises:
            UnauthenticatedError: If admin client is not available due to authentication issues
            UnavailableError: If Keycloak service is unavailable
        """
        if not self.configs.IS_ADMIN_MODE_ENABLED or not (
            self.configs.CLIENT_SECRET_KEY or (self.configs.ADMIN_USERNAME and self.configs.ADMIN_PASSWORD)
        ):
            raise UnauthenticatedError(
                additional_data={
                    "detail": "Admin mode is disabled or neither admin credentials nor client secret provided",
                },
            )

        # Check if token is about to expire and refresh if needed
        if self._admin_adapter is None or time.time() >= self._admin_token_expiry:
            self._initialize_admin_client()

        if self._admin_adapter is None:
            raise UnavailableError("Keycloak admin client is not available")

        return self._admin_adapter

    @property
    def uma_adapter(self) -> KeycloakUMA:
        """Get the UMA adapter, creating it on first access.

        Returns:
            KeycloakUMA instance
        """
        if self._uma_adapter is None:
            self._uma_adapter = KeycloakAdapter._get_uma_client(self.configs)
        return self._uma_adapter

    @override
    @alru_cache(ttl=3600, maxsize=1)  # Cache for 1 hour, public key rarely changes
    async def get_public_key(self) -> PublicKeyType:
        """Get the public key used to verify tokens.

        Returns:
            JWK key object used to verify signatures

        Raises:
            ServiceUnavailableError: If Keycloak service is unavailable
            InternalError: If there's an internal error processing the public key
        """
        try:
            from jwcrypto import jwk

            keys_info = await self.openid_adapter.a_public_key()
            key = f"-----BEGIN PUBLIC KEY-----\n{keys_info}\n-----END PUBLIC KEY-----"
            return jwk.JWK.from_pem(key.encode("utf-8"))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_public_key")
        except Exception as e:
            raise InternalError(additional_data={"operation": "get_public_key", "error": str(e)}) from e

    @override
    async def get_token(self, username: str, password: str) -> KeycloakTokenType | None:
        """Get a user token by username and password using the Resource Owner Password Credentials Grant.

        Warning:
            This method uses the direct password grant flow, which is less secure and not recommended
            for user login in production environments. Instead, prefer the web-based OAuth 2.0
            Authorization Code Flow (use `get_token_from_code`) for secure authentication.
            Use this method only for testing, administrative tasks, or specific service accounts
            where direct credential use is acceptable and properly secured.

        Args:
            username: User's username
            password: User's password

        Returns:
            Token response containing access_token, refresh_token, etc.

        Raises:
            InvalidCredentialsError: If username or password is invalid
            ServiceUnavailableError: If Keycloak service is unavailable
        """
        try:
            return await self.openid_adapter.a_token(grant_type="password", username=username, password=password)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token")

    @override
    async def refresh_token(self, refresh_token: str) -> KeycloakTokenType | None:
        """Refresh an existing token using a refresh token.

        Args:
            refresh_token: Refresh token string

        Returns:
            New token response containing access_token, refresh_token, etc.

        Raises:
            InvalidTokenError: If refresh token is invalid or expired
            ServiceUnavailableError: If Keycloak service is unavailable
        """
        try:
            return await self.openid_adapter.a_refresh_token(refresh_token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "refresh_token")

    @override
    async def validate_token(self, token: str) -> bool:
        """Validate if a token is still valid.

        Args:
            token: Access token to validate

        Returns:
            True if token is valid, False otherwise
        """
        # Not caching validation results as tokens are time-sensitive
        try:
            await self.openid_adapter.a_decode_token(
                token,
                key=await self.get_public_key(),
            )
        except Exception as e:
            logger.debug(f"Token validation failed: {e!s}")
            return False
        else:
            return True

    @override
    async def get_userinfo(self, token: str) -> KeycloakUserType | None:
        """Get user information from a token via the UserInfo endpoint.

        The UserInfo endpoint validates the token server-side, so no local
        validation is needed here.

        Args:
            token: Access token

        Returns:
            User information

        Raises:
            ValueError: If getting user info fails
        """
        try:
            return await self._get_userinfo_cached(token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_userinfo")

    @alru_cache(ttl=30, maxsize=100)  # Cache for 30 seconds
    async def _get_userinfo_cached(self, token: str) -> KeycloakUserType:
        return cast("KeycloakUserType", await self.openid_adapter.a_userinfo(token))

    @override
    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_user_by_id(self, user_id: str) -> KeycloakUserType | None:
        """Get user details by user ID.

        Args:
            user_id: User's ID

        Returns:
            User details or None if not found

        Raises:
            ValueError: If getting user fails
        """
        try:
            return await self.admin_adapter.a_get_user(user_id)
        except KeycloakGetError as e:
            if e.response_code == 404:
                return None
            raise InternalError() from e
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_id")

    @override
    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_user_by_username(self, username: str) -> KeycloakUserType | None:
        """Get user details by username.

        Args:
            username: User's username

        Returns:
            User details or None if not found

        Raises:
            ValueError: If query fails
        """
        try:
            users = await self.admin_adapter.a_get_users({"username": username})
            return users[0] if users else None
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_username")

    @override
    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_user_by_email(self, email: str) -> KeycloakUserType | None:
        """Get user details by email.

        Args:
            email: User's email

        Returns:
            User details or None if not found

        Raises:
            ValueError: If query fails
        """
        try:
            users = await self.admin_adapter.a_get_users({"email": email})
            return users[0] if users else None
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_by_email")

    @override
    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_user_roles(self, user_id: str) -> list[KeycloakRoleType] | None:
        """Get roles assigned to a user.

        Args:
            user_id: User's ID

        Returns:
            List of roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return await self.admin_adapter.a_get_realm_roles_of_user(user_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_roles")

    @override
    @alru_cache(ttl=300, maxsize=100)  # Cache for 5 minutes
    async def get_client_roles_for_user(self, user_id: str, client_id: str) -> list[KeycloakRoleType]:
        """Get client-specific roles assigned to a user.

        Args:
            user_id: User's ID
            client_id: Client ID

        Returns:
            List of client-specific roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return await self.admin_adapter.a_get_client_roles_of_user(user_id, client_id)
        except KeycloakError as e:
            raise InternalError() from e

    @override
    async def create_user(self, user_data: dict[str, Any]) -> str | None:
        """Create a new user in Keycloak.

        Args:
            user_data: User data including username, email, etc.

        Returns:
            ID of the created user

        Raises:
            ValueError: If creating user fails
        """
        # This is a write operation, no caching needed
        try:
            user_id = await self.admin_adapter.a_create_user(user_data)

            # Clear related caches
            self.clear_all_caches()
        except KeycloakError as e:
            self._handle_user_exception(e, "create_user", user_data)
        else:
            return user_id

    @override
    async def update_user(self, user_id: str, user_data: dict[str, Any]) -> None:
        """Update user details.

        Args:
            user_id: User's ID
            user_data: User data to update

        Raises:
            ValueError: If updating user fails
        """
        # This is a write operation, no caching needed
        try:
            await self.admin_adapter.a_update_user(user_id, user_data)

            # Clear user-related caches
            self.clear_all_caches()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_user")

    @override
    async def reset_password(self, user_id: str, password: str, temporary: bool = False) -> None:
        """Reset a user's password.

        Args:
            user_id: User's ID
            password: New password
            temporary: Whether the password is temporary and should be changed on next login

        Raises:
            ValueError: If password reset fails
        """
        # This is a write operation, no caching needed
        try:
            await self.admin_adapter.a_set_user_password(user_id, password, temporary)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "reset_password")

    @override
    async def assign_realm_role(self, user_id: str, role_name: str) -> None:
        """Assign a realm role to a user.

        Args:
            user_id: User's ID
            role_name: Role name to assign

        Raises:
            ValueError: If role assignment fails
        """
        # This is a write operation, no caching needed
        try:
            # Get role representation
            role = await self.admin_adapter.a_get_realm_role(role_name)
            # Assign role to user
            await self.admin_adapter.a_assign_realm_roles(user_id, [role])

            # Clear role-related caches
            if hasattr(self.get_user_roles, "cache_clear"):
                self.get_user_roles.cache_clear()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "assign_realm_role")

    @override
    async def remove_realm_role(self, user_id: str, role_name: str) -> None:
        """Remove a realm role from a user.

        Args:
            user_id: User's ID
            role_name: Role name to remove

        Raises:
            ValueError: If role removal fails
        """
        # This is a write operation, no caching needed
        try:
            # Get role representation
            role = await self.admin_adapter.a_get_realm_role(role_name)
            # Remove role from user
            await self.admin_adapter.a_delete_realm_roles_of_user(user_id, [role])

            # Clear role-related caches
            if hasattr(self.get_user_roles, "cache_clear"):
                self.get_user_roles.cache_clear()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "remove_realm_role")

    @override
    async def assign_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Assign a client-specific role to a user.

        Args:
            user_id: User's ID
            client_id: Client ID
            role_name: Role name to assign

        Raises:
            ValueError: If role assignment fails
        """
        # This is a write operation, no caching needed
        try:
            # Get client
            client = await self.admin_adapter.a_get_client_id(client_id)
            if client is None:
                raise ValueError("client_id resolved to None")
            # Get role representation
            # Keycloak admin adapter methods accept these types at runtime
            role = await self.admin_adapter.a_get_client_role(client, role_name)
            # Assign role to user
            await self.admin_adapter.a_assign_client_role(user_id, client, [role])

            # Clear role-related caches
            if hasattr(self.get_client_roles_for_user, "cache_clear"):
                self.get_client_roles_for_user.cache_clear()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "assign_client_role")

    @override
    async def create_realm_role(
        self,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
        """Create a new realm role.

        Args:
            role_name: Role name
            description: Optional role description
            skip_exists: Skip creation if role already exists

        Returns:
            Created role details

        Raises:
            ValueError: If role creation fails
        """
        # This is a write operation, no caching needed
        try:
            role_data = {"name": role_name}
            if description:
                role_data["description"] = description

            await self.admin_adapter.a_create_realm_role(role_data, skip_exists=skip_exists)

            # Clear realm roles cache
            if hasattr(self.get_realm_roles, "cache_clear"):
                self.get_realm_roles.cache_clear()

            return await self.admin_adapter.a_get_realm_role(role_name)

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_realm_role")

    @override
    async def create_client_role(
        self,
        client_id: str,
        role_name: str,
        description: str | None = None,
        skip_exists: bool = True,
    ) -> dict[str, Any] | None:
        """Create a new client role.

        Args:
            client_id: Client ID or client name
            role_name: Role name
            skip_exists: Skip creation if role already exists
            description: Optional role description

        Returns:
            Created role details
        """
        # This is a write operation, no caching needed
        try:
            resolved_client_id = await self.admin_adapter.a_get_client_id(client_id)
            if resolved_client_id is None:
                raise ValueError(f"Client ID not found: {client_id}")

            # Prepare role data
            role_data = {"name": role_name}
            if description:
                role_data["description"] = description

            # Create client role
            await self.admin_adapter.a_create_client_role(resolved_client_id, role_data, skip_exists=skip_exists)

            # Clear related caches if they exist
            if hasattr(self.get_client_roles_for_user, "cache_clear"):
                self.get_client_roles_for_user.cache_clear()

            # Return created role
            return await self.admin_adapter.a_get_client_role(resolved_client_id, role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_role")

    @override
    async def delete_realm_role(self, role_name: str) -> None:
        """Delete a realm role.

        Args:
            role_name: Role name to delete

        Raises:
            ValueError: If role deletion fails
        """
        # This is a write operation, no caching needed
        try:
            await self.admin_adapter.a_delete_realm_role(role_name)

            # Clear realm roles cache
            if hasattr(self.get_realm_roles, "cache_clear"):
                self.get_realm_roles.cache_clear()

            # We also need to clear user role caches since they might contain this role
            if hasattr(self.get_user_roles, "cache_clear"):
                self.get_user_roles.cache_clear()

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_realm_role")

    @override
    @alru_cache(ttl=3600, maxsize=1)  # Cache for 1 hour
    async def get_service_account_id(self) -> str | None:
        """Get service account user ID for the current client.

        Returns:
            Service account user ID

        Raises:
            ValueError: If getting service account fails
        """
        try:
            client_id = await self.get_client_id(self.configs.CLIENT_ID)
            if client_id is None:
                return None
            service_account = await self.admin_adapter.a_get_client_service_account_user(client_id)
            return service_account.get("id")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_service_account_id")

    @override
    @alru_cache(ttl=3600, maxsize=1)  # Cache for 1 hour
    async def get_well_known_config(self) -> dict[str, Any] | None:
        """Get the well-known OpenID configuration.

        Returns:
            OIDC configuration

        Raises:
            ValueError: If getting configuration fails
        """
        try:
            return await self.openid_adapter.a_well_known()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_well_known_config")

    @override
    @alru_cache(ttl=3600, maxsize=1)  # Cache for 1 hour
    async def get_certs(self) -> dict[str, Any] | None:
        """Get the JWT verification certificates.

        Returns:
            Certificate information

        Raises:
            ValueError: If getting certificates fails
        """
        try:
            return await self.openid_adapter.a_certs()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_certs")

    @override
    async def get_token_from_code(self, code: str, redirect_uri: str) -> KeycloakTokenType | None:
        """Exchange authorization code for token.

        Args:
            code: Authorization code
            redirect_uri: Redirect URI used in authorization request

        Returns:
            Token response

        Raises:
            ValueError: If token exchange fails
        """
        # Authorization codes can only be used once, don't cache
        try:
            return await self.openid_adapter.a_token(
                grant_type="authorization_code",
                code=code,
                redirect_uri=redirect_uri,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token_from_code")

    @override
    async def get_client_credentials_token(self) -> KeycloakTokenType | None:
        """Get token using client credentials.

        Returns:
            Token response

        Raises:
            ValueError: If token acquisition fails
        """
        # Tokens are time-sensitive, don't cache
        try:
            return await self.openid_adapter.a_token(grant_type="client_credentials")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_credentials_token")

    @override
    @alru_cache(ttl=30, maxsize=50)  # Cache for 30 seconds with limited entries
    async def search_users(self, query: str, max_results: int = 100) -> list[KeycloakUserType] | None:
        """Search for users by username, email, or name.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of matching users

        Raises:
            ValueError: If search fails
        """
        try:
            # Try searching by different fields
            users = []

            # Search by username
            users.extend(await self.admin_adapter.a_get_users({"username": query, "max": max_results}))

            # Search by email if no results or incomplete results
            if len(users) < max_results:
                remaining = max_results - len(users)
                email_users = await self.admin_adapter.a_get_users({"email": query, "max": remaining})
                # Filter out duplicates
                user_ids = {user["id"] for user in users}
                users.extend([user for user in email_users if user["id"] not in user_ids])

            # Search by firstName if no results or incomplete results
            if len(users) < max_results:
                remaining = max_results - len(users)
                first_name_users = await self.admin_adapter.a_get_users({"firstName": query, "max": remaining})
                # Filter out duplicates
                user_ids = {user["id"] for user in users}
                users.extend([user for user in first_name_users if user["id"] not in user_ids])

            # Search by lastName if no results or incomplete results
            if len(users) < max_results:
                remaining = max_results - len(users)
                last_name_users = await self.admin_adapter.a_get_users({"lastName": query, "max": remaining})
                # Filter out duplicates
                user_ids = {user["id"] for user in users}
                users.extend([user for user in last_name_users if user["id"] not in user_ids])

            return users[:max_results]
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "search_users")

    @override
    @alru_cache(ttl=3600, maxsize=50)  # Cache for 1 hour
    async def get_client_secret(self, client_id: str) -> str | None:
        """Get client secret.

        Args:
            client_id: Client ID

        Returns:
            Client secret

        Raises:
            ValueError: If getting secret fails
        """
        try:
            client = await self.admin_adapter.a_get_client(client_id)
            return client.get("secret", "")
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_secret")

    @override
    @alru_cache(ttl=3600, maxsize=50)  # Cache for 1 hour
    async def get_client_id(self, client_name: str) -> str | None:
        """Get client ID by client name.

        Args:
            client_name: Name of the client

        Returns:
            Client ID

        Raises:
            ValueError: If client not found
        """
        try:
            return await self.admin_adapter.a_get_client_id(client_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_id")

    @override
    @alru_cache(ttl=300, maxsize=1)  # Cache for 5 minutes
    async def get_realm_roles(self) -> list[dict[str, Any]] | None:
        """Get all realm roles.

        Returns:
            List of realm roles

        Raises:
            ValueError: If getting roles fails
        """
        try:
            return await self.admin_adapter.a_get_realm_roles()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm_roles")

    @override
    @alru_cache(ttl=300, maxsize=1)  # Cache for 5 minutes
    async def get_realm_role(self, role_name: str) -> dict | None:
        """Get realm role.

        Args:
            role_name: Role name
        Returns:
            A realm role

        Raises:
            ValueError: If getting role fails
        """
        try:
            return await self.admin_adapter.a_get_realm_role(role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm_role")

    @override
    async def remove_client_role(self, user_id: str, client_id: str, role_name: str) -> None:
        """Remove a client-specific role from a user.

        Args:
            user_id: User's ID
            client_id: Client ID
            role_name: Role name to remove

        Raises:
            ValueError: If role removal fails
        """
        try:
            client = await self.admin_adapter.a_get_client_id(client_id)
            if client is None:
                raise ValueError("client_id resolved to None")
            # Keycloak admin adapter methods accept these types at runtime
            role = await self.admin_adapter.a_get_client_role(client, role_name)
            await self.admin_adapter.a_delete_client_roles_of_user(user_id, client, [role])

            if hasattr(self.get_client_roles_for_user, "cache_clear"):
                self.get_client_roles_for_user.cache_clear()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "remove_client_role")

    @override
    async def clear_user_sessions(self, user_id: str) -> None:
        """Clear all sessions for a user.

        Args:
            user_id: User's ID

        Raises:
            ValueError: If clearing sessions fails
        """
        try:
            await self.admin_adapter.a_user_logout(user_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "clear_user_sessions")

    @override
    async def logout(self, refresh_token: str) -> None:
        """Logout user by invalidating their refresh token.

        Args:
            refresh_token: Refresh token to invalidate

        Raises:
            ValueError: If logout fails
        """
        try:
            await self.openid_adapter.a_logout(refresh_token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "logout")

    @override
    async def introspect_token(self, token: str) -> dict[str, Any] | None:
        """Introspect token to get detailed information about it.

        Args:
            token: Access token

        Returns:
            Token introspection details

        Raises:
            ValueError: If token introspection fails
        """
        try:
            return await self.openid_adapter.a_introspect(token)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "introspect_token")

    @override
    async def get_token_info(self, token: str) -> dict[str, Any] | None:
        """Decode token to get its claims.

        Args:
            token: Access token

        Returns:
            Dictionary of token claims

        Raises:
            ValueError: If token decoding fails
        """
        try:
            return await self.openid_adapter.a_decode_token(
                token,
                key=await self.get_public_key(),
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_token_info")

    @override
    async def delete_user(self, user_id: str) -> None:
        """Delete a user from Keycloak by their ID.

        Args:
            user_id: The ID of the user to delete

        Raises:
            ValueError: If the deletion fails
        """
        try:
            await self.admin_adapter.a_delete_user(user_id=user_id)

            if hasattr(self.get_user_by_username, "cache_clear"):
                self.get_user_by_username.cache_clear()

            logger.info(f"Successfully deleted user with ID {user_id}")

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_user")

    @override
    async def has_role(self, token: str, role_name: str) -> bool:
        """Check if a user has a specific role.

        Args:
            token: Access token
            role_name: Role name to check

        Returns:
            True if user has the role, False otherwise
        """
        # Not caching this result as token validation is time-sensitive
        try:
            user_info = await self.get_userinfo(token)
            if not user_info:
                return False

            # Check realm roles
            realm_access = user_info.get("realm_access", {})
            roles = realm_access.get("roles", [])
            if role_name in roles:
                return True

            # Check roles for the configured client
            resource_access = user_info.get("resource_access", {})
            client_roles = resource_access.get(self.configs.CLIENT_ID, {}).get("roles", [])
            if role_name in client_roles:
                return True

        except Exception as e:
            logger.debug(f"Role check failed: {e!s}")
            return False
        else:
            return False

    @override
    async def has_any_of_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has any of the specified roles.

        Args:
            token: Access token
            role_names: Set of role names to check

        Returns:
            True if user has any of the roles, False otherwise
        """
        try:
            user_info = await self.get_userinfo(token)
            if not user_info:
                return False

            # Check realm roles first
            realm_access = user_info.get("realm_access", {})
            realm_roles = set(realm_access.get("roles", []))
            if role_names.intersection(realm_roles):
                return True

            # Check roles for the configured client
            resource_access = user_info.get("resource_access", {})
            client_roles = set(resource_access.get(self.configs.CLIENT_ID, {}).get("roles", []))
            if role_names.intersection(client_roles):
                return True

        except Exception as e:
            logger.debug(f"Role check failed: {e!s}")
            return False
        else:
            return False

    @override
    async def has_all_roles(self, token: str, role_names: frozenset[str]) -> bool:
        """Check if a user has all the specified roles.

        Args:
            token: Access token
            role_names: Set of role names to check

        Returns:
            True if user has all the roles, False otherwise
        """
        try:
            user_info = await self.get_userinfo(token)
            if not user_info:
                return False

            # Get all user roles
            all_roles = set()

            # Add realm roles
            realm_access = user_info.get("realm_access", {})
            all_roles.update(realm_access.get("roles", []))

            # Add roles from the configured client
            resource_access = user_info.get("resource_access", {})
            client_roles = resource_access.get(self.configs.CLIENT_ID, {}).get("roles", [])
            all_roles.update(client_roles)

            # Check if all required roles are present
            return role_names.issubset(all_roles)

        except Exception as e:
            logger.debug(f"All roles check failed: {e!s}")
            return False

    @override
    @alru_cache(ttl=30, maxsize=200)
    async def check_permissions_batch(
        self,
        token: str,
        permissions: tuple[tuple[str, str], ...],
    ) -> frozenset[tuple[str, str]]:
        """Return the subset of (resource, scope) pairs the token is authorized for in one UMA call.

        Prefer this over :meth:`check_permissions` when multiple pairs must be checked per request.

        Args:
            token: Access token
            permissions: Tuple of (resource, scope) pairs to check

        Returns:
            Subset of ``permissions`` that are granted
        """
        if not permissions:
            return frozenset()
        perm_strs = [f"{resource}#{scope}" for resource, scope in permissions]
        try:
            results = await self.openid_adapter.a_uma_permissions(token, permissions=perm_strs)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "check_permissions_batch")
        if not results or not isinstance(results, list):
            return frozenset()
        granted: set[tuple[str, str]] = set()
        requested = set(permissions)
        for perm in results:
            rsname = perm.get("rsname")
            for scope in perm.get("scopes", []) or []:
                pair = (rsname, scope)
                if pair in requested:
                    granted.add(pair)
        return frozenset(granted)

    @override
    async def check_permissions(self, token: str, resource: str, scope: str) -> bool:
        """Check if a user has permission to access a resource with the specified scope.

        Prefer :meth:`check_permissions_batch` when checking multiple pairs per request.

        Args:
            token: Access token
            resource: Resource name
            scope: Permission scope

        Returns:
            True if permission granted, False otherwise
        """
        try:
            # Use UMA permissions endpoint to check specific resource and scope
            permissions = await self.openid_adapter.a_uma_permissions(token, permissions=f"{resource}#{scope}")

            # Check if the response indicates permission is granted
            if not permissions or not isinstance(permissions, list):
                logger.debug("No permissions returned or invalid response format")
                return False

            # Look for the specific permission in the response
            for perm in permissions:
                if perm.get("rsname") == resource and scope in perm.get("scopes", []):
                    return True

        except KeycloakError as e:
            logger.debug(f"Permission check failed with Keycloak error: {e!s}")
            return False
        except Exception as e:
            logger.debug(f"Permission check failed with unexpected error: {e!s}")
            return False
        else:
            return False

    @override
    async def create_realm(self, realm_name: str, skip_exists: bool = True, **kwargs: Any) -> dict[str, Any] | None:
        """Create a Keycloak realm with minimum required fields and optional additional config.

        Args:
            realm_name: The realm identifier (required)
            skip_exists: Skip creation if realm already exists
            kwargs: Additional optional configurations for the realm

        Returns:
            Dictionary with realm information and status

        Raises:
            InternalError: If realm creation fails
        """
        payload = {
            "realm": realm_name,
            "enabled": kwargs.get("enabled", True),
            "displayName": kwargs.get("display_name", realm_name),
        }

        # Add any additional parameters from kwargs
        for key, value in kwargs.items():
            # Skip display_name as it's already handled
            if key == "display_name":
                continue

            # Convert Python snake_case to Keycloak camelCase
            camel_key = StringUtils.snake_to_camel_case(key)
            payload[camel_key] = value

        try:
            await self.admin_adapter.a_create_realm(payload=payload, skip_exists=skip_exists)
        except KeycloakError as e:
            logger.debug(f"Failed to create realm: {e!s}")

            # Handle realm already exists with skip_exists option
            if skip_exists:
                error_message = self._extract_error_message(e).lower()
                if "already exists" in error_message and "realm" in error_message:
                    return {"realm": realm_name, "status": "already_exists", "config": payload}

            # Use the mixin to handle realm-specific errors
            self._handle_realm_exception(e, "create_realm", realm_name)
        else:
            return {"realm": realm_name, "status": "created", "config": payload}

    @override
    async def get_realm(self, realm_name: str) -> dict[str, Any] | None:
        """Get realm details by realm name.

        Args:
            realm_name: Name of the realm

        Returns:
            Realm details

        Raises:
            InternalError: If getting realm fails
        """
        try:
            return await self.admin_adapter.a_get_realm(realm_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm")

    @override
    async def update_realm(self, realm_name: str, **kwargs: Any) -> dict[str, Any] | None:
        """Update a realm. Kwargs are RealmRepresentation top-level attributes (e.g. displayName, organizationsEnabled).

        Args:
            realm_name: Realm name (not the realm id).
            **kwargs: RealmRepresentation attributes to update (e.g. displayName, organizationsEnabled).

        Returns:
            Response from Keycloak, or None on error (handled via exception).
        """
        try:
            return await self.admin_adapter.a_update_realm(realm_name, dict(kwargs))
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_realm")

    @override
    async def create_client(
        self,
        client_id: str,
        realm: str | None = None,
        skip_exists: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Create a Keycloak client with minimum required fields and optional additional config.

        Args:
            client_id: The client identifier (required)
            realm: Target realm name (uses the current realm in KeycloakAdmin if not specified)
            skip_exists: Skip creation if client already exists
            kwargs: Additional optional configurations for the client

        Returns:
            Dictionary with client information

        Raises:
            InternalError: If client creation fails
        """
        original_realm = self.admin_adapter.connection.realm_name

        try:
            # Set the target realm if provided
            if realm and realm != original_realm:
                self.admin_adapter.connection.realm_name = realm

            public_client = kwargs.get("public_client", False)

            # Prepare the minimal client payload
            payload = {
                "clientId": client_id,
                "enabled": kwargs.get("enabled", True),
                "protocol": kwargs.get("protocol", "openid-connect"),
                "name": kwargs.get("name", client_id),
                "publicClient": public_client,
            }

            # Enable service accounts for confidential clients by default
            if not public_client:
                payload["serviceAccountsEnabled"] = kwargs.get("service_account_enabled", True)
                payload["clientAuthenticatorType"] = "client-secret"

            for key, value in kwargs.items():
                if key in ["enabled", "protocol", "name", "public_client", "service_account_enabled"]:
                    continue

                # Convert snake_case to camelCase
                camel_key = StringUtils.snake_to_camel_case(key)
                payload[camel_key] = value

            internal_client_id = None
            try:
                internal_client_id = await self.admin_adapter.a_create_client(payload, skip_exists=skip_exists)
            except KeycloakError as e:
                logger.debug(f"Failed to create client: {e!s}")

                # Handle client already exists with skip_exists option
                if skip_exists:
                    error_message = self._extract_error_message(e).lower()
                    if "already exists" in error_message and "client" in error_message:
                        return {
                            "client_id": client_id,
                            "status": "already_exists",
                            "realm": self.admin_adapter.connection.realm_name,
                        }

                # Use the mixin to handle client-specific errors
                client_data = {"clientId": client_id, "name": kwargs.get("name", client_id)}
                self._handle_client_exception(e, "create_client", client_data)

            return {
                "client_id": client_id,
                "internal_client_id": internal_client_id,
                "realm": self.admin_adapter.connection.realm_name,
                "status": "created",
            }

        finally:
            # Always restore the original realm
            if realm and realm != original_realm:
                self.admin_adapter.connection.realm_name = original_realm

    @override
    async def add_realm_roles_to_composite(self, composite_role_name: str, child_role_names: list[str]) -> None:
        """Add realm roles to a composite role.

        Args:
            composite_role_name: Name of the composite role
            child_role_names: List of child role names to add
        """
        try:
            child_roles = []
            for role_name in child_role_names:
                try:
                    role = await self.admin_adapter.a_get_realm_role(role_name)
                    child_roles.append(role)
                except KeycloakGetError as e:
                    if e.response_code == 404:
                        logger.warning(f"Child role not found: {role_name}")
                        continue
                    raise

            if child_roles:
                await self.admin_adapter.a_add_composite_realm_roles_to_role(
                    role_name=composite_role_name,
                    roles=child_roles,
                )
                logger.info(f"Added {len(child_roles)} realm roles to composite role: {composite_role_name}")

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_realm_roles_to_composite")

    @override
    async def add_client_roles_to_composite(
        self,
        composite_role_name: str,
        client_id: str,
        child_role_names: list[str],
    ) -> None:
        """Add client roles to a composite role.

        Args:
            composite_role_name: Name of the composite role
            client_id: Client ID or client name
            child_role_names: List of child role names to add
        """
        try:
            internal_client_id = await self.admin_adapter.a_get_client_id(client_id)
            if internal_client_id is None:
                raise ValueError("client_id resolved to None")

            child_roles = []
            for role_name in child_role_names:
                try:
                    # Keycloak admin adapter methods accept these types at runtime
                    role = await self.admin_adapter.a_get_client_role(internal_client_id, role_name)
                    child_roles.append(role)
                except KeycloakGetError as e:
                    if e.response_code == 404:
                        logger.warning(f"Client role not found: {role_name}")
                        continue
                    raise

            if child_roles:
                if internal_client_id is None:
                    raise ValueError("Client ID not found")
                resolved_client_id: str = internal_client_id
                await self.admin_adapter.a_add_composite_client_roles_to_role(
                    role_name=composite_role_name,
                    client_role_id=resolved_client_id,
                    roles=child_roles,
                )
                logger.info(f"Added {len(child_roles)} client roles to composite role: {composite_role_name}")

        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_client_roles_to_composite")

    @override
    async def get_composite_realm_roles(self, role_name: str) -> list[dict[str, Any]] | None:
        """Get composite roles for a realm role.

        Args:
            role_name: Name of the role

        Returns:
            List of composite roles
        """
        try:
            return await self.admin_adapter.a_get_composite_realm_roles_of_role(role_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_composite_realm_roles")

    @override
    async def get_organizations(self, query: dict | None = None) -> list[dict[str, Any]]:
        """Fetch all organizations, optionally filtered by query parameters."""
        try:
            return await self.admin_adapter.a_get_organizations(query=query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_organizations")

    @override
    async def get_organization(self, organization_id: str) -> dict[str, Any]:
        """Get representation of the organization by ID."""
        try:
            return await self.admin_adapter.a_get_organization(organization_id=organization_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_organization")

    @override
    async def create_organization(self, name: str, alias: str, **kwargs: Any) -> str | None:
        """Create a new organization. Name and alias must be unique. Returns org_id."""
        try:
            payload = {"name": name, "alias": alias}
            for key, value in kwargs.items():
                if key in ["name", "alias"]:
                    continue

                # Convert snake_case to camelCase
                camel_key = StringUtils.snake_to_camel_case(key)
                payload[camel_key] = value

            return await self.admin_adapter.a_create_organization(payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_organization")

    @override
    async def update_organization(self, organization_id: str, **kwargs: Any) -> dict[str, Any]:
        """Update an existing organization. Kwargs are organization attributes (e.g. name, alias)."""
        try:
            payload = {}
            for key, value in kwargs.items():
                # Convert snake_case to camelCase
                camel_key = StringUtils.snake_to_camel_case(key)
                payload[camel_key] = value

            return await self.admin_adapter.a_update_organization(organization_id=organization_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_organization")

    @override
    async def delete_organization(self, organization_id: str) -> dict[str, Any]:
        """Delete an organization."""
        try:
            return await self.admin_adapter.a_delete_organization(organization_id=organization_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_organization")

    @override
    async def get_user_organizations(self, user_id: str) -> list[dict[str, Any]]:
        """Get organizations by user id."""
        try:
            return await self.admin_adapter.a_get_user_organizations(user_id=user_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_user_organizations")

    @override
    async def get_organization_members(self, organization_id: str, query: dict | None = None) -> list[dict[str, Any]]:
        """Get members by organization id, optionally filtered by query parameters."""
        try:
            return await self.admin_adapter.a_get_organization_members(organization_id=organization_id, query=query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_organization_members")

    @override
    async def get_organization_members_count(self, organization_id: str) -> int:
        """Get the number of members in the organization."""
        try:
            return await self.admin_adapter.a_get_organization_members_count(organization_id=organization_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_organization_members_count")

    @override
    async def organization_user_add(self, user_id: str, organization_id: str) -> bytes:
        """Add a user to an organization."""
        try:
            return await self.admin_adapter.a_organization_user_add(user_id=user_id, organization_id=organization_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "organization_user_add")

    @override
    async def organization_user_remove(self, user_id: str, organization_id: str) -> dict[str, Any]:
        """Remove a user from an organization."""
        try:
            return await self.admin_adapter.a_organization_user_remove(user_id=user_id, organization_id=organization_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "organization_user_remove")

    # Group Operations
    @override
    async def create_group(self, payload: dict, parent: str | None = None, skip_exists: bool = False) -> str | None:
        """Create a new group."""
        try:
            return await self.admin_adapter.a_create_group(payload=payload, parent=parent, skip_exists=skip_exists)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_group")

    @override
    async def update_group(self, group_id: str, payload: dict) -> dict[str, Any]:
        """Update a group."""
        try:
            return await self.admin_adapter.a_update_group(group_id=group_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_group")

    @override
    async def delete_group(self, group_id: str) -> dict[str, Any]:
        """Delete a group."""
        try:
            return await self.admin_adapter.a_delete_group(group_id=group_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_group")

    @override
    async def get_group(self, group_id: str, full_hierarchy: bool = False, query: dict | None = None) -> dict[str, Any]:
        """Get group representation by ID."""
        try:
            return await self.admin_adapter.a_get_group(group_id=group_id, full_hierarchy=full_hierarchy, query=query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_group")

    @override
    async def get_group_by_path(self, path: str) -> dict[str, Any]:
        """Get group representation by path."""
        try:
            return await self.admin_adapter.a_get_group_by_path(path=path)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_group_by_path")

    @override
    async def get_group_children(
        self,
        group_id: str,
        query: dict | None = None,
        full_hierarchy: bool = False,
    ) -> list[dict[str, Any]]:
        """Get child groups of a group."""
        try:
            return await self.admin_adapter.a_get_group_children(
                group_id=group_id,
                query=query,
                full_hierarchy=full_hierarchy,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_group_children")

    @override
    async def get_groups(self, query: dict | None = None, full_hierarchy: bool = False) -> list[dict[str, Any]]:
        """Get all groups, optionally filtered by query."""
        try:
            return await self.admin_adapter.a_get_groups(query=query, full_hierarchy=full_hierarchy)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_groups")

    @override
    async def get_subgroups(self, group: dict, path: str) -> dict[str, Any] | None:
        """Get subgroups for a group at the given path."""
        try:
            return await self.admin_adapter.a_get_subgroups(group=group, path=path)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_subgroups")

    @override
    async def groups_count(self, query: dict | None = None) -> dict[str, Any]:
        """Get the number of groups matching the query."""
        try:
            return await self.admin_adapter.a_groups_count(query=query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "groups_count")

    @override
    async def group_user_add(self, user_id: str, group_id: str) -> dict[str, Any]:
        """Add a user to a group."""
        try:
            return await self.admin_adapter.a_group_user_add(user_id=user_id, group_id=group_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "group_user_add")

    @override
    async def group_user_remove(self, user_id: str, group_id: str) -> dict[str, Any]:
        """Remove a user from a group."""
        try:
            return await self.admin_adapter.a_group_user_remove(user_id=user_id, group_id=group_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "group_user_remove")

    @override
    async def group_set_permissions(self, group_id: str, enabled: bool = True) -> dict[str, Any]:
        """Enable or disable fine-grained permissions for a group."""
        try:
            return await self.admin_adapter.a_group_set_permissions(group_id=group_id, enabled=enabled)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "group_set_permissions")

    @override
    async def get_group_members(self, group_id: str, query: dict | None = None) -> list[dict[str, Any]]:
        """Get members of a group."""
        try:
            return await self.admin_adapter.a_get_group_members(group_id=group_id, query=query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_group_members")

    @override
    async def get_group_client_roles(self, group_id: str, client_id: str) -> list[dict[str, Any]]:
        """Get client roles assigned to a group."""
        try:
            return await self.admin_adapter.a_get_group_client_roles(group_id=group_id, client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_group_client_roles")

    @override
    async def get_group_realm_roles(self, group_id: str, brief_representation: bool = True) -> list[dict[str, Any]]:
        """Get realm roles assigned to a group."""
        try:
            return await self.admin_adapter.a_get_group_realm_roles(
                group_id=group_id,
                brief_representation=brief_representation,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_group_realm_roles")

    @override
    async def assign_group_client_roles(self, group_id: str, client_id: str, roles: str | list) -> dict[str, Any]:
        """Assign client roles to a group."""
        try:
            return await self.admin_adapter.a_assign_group_client_roles(
                group_id=group_id,
                client_id=client_id,
                roles=roles,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "assign_group_client_roles")

    @override
    async def assign_group_realm_roles(self, group_id: str, roles: str | list) -> dict[str, Any]:
        """Assign realm roles to a group."""
        try:
            return await self.admin_adapter.a_assign_group_realm_roles(group_id=group_id, roles=roles)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "assign_group_realm_roles")

    @override
    async def delete_group_client_roles(self, group_id: str, client_id: str, roles: str | list) -> dict[str, Any]:
        """Remove client roles from a group."""
        try:
            return await self.admin_adapter.a_delete_group_client_roles(
                group_id=group_id,
                client_id=client_id,
                roles=roles,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_group_client_roles")

    @override
    async def delete_group_realm_roles(self, group_id: str, roles: str | list) -> dict[str, Any]:
        """Remove realm roles from a group."""
        try:
            return await self.admin_adapter.a_delete_group_realm_roles(group_id=group_id, roles=roles)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_group_realm_roles")

    @override
    async def get_composite_client_roles_of_group(
        self,
        client_id: str,
        group_id: str,
        brief_representation: bool = True,
    ) -> list[dict[str, Any]]:
        """Get composite client roles of a group."""
        try:
            return await self.admin_adapter.a_get_composite_client_roles_of_group(
                client_id=client_id,
                group_id=group_id,
                brief_representation=brief_representation,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_composite_client_roles_of_group")

    @override
    async def get_client_role_groups(self, client_id: str, role_name: str, query: Any) -> list[dict[str, Any]]:
        """Get groups that have a specific client role."""
        try:
            return await self.admin_adapter.a_get_client_role_groups(client_id=client_id, role_name=role_name, **query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_role_groups")

    @override
    async def get_realm_role_groups(
        self,
        role_name: str,
        query: dict | None = None,
        brief_representation: bool = True,
    ) -> list[dict[str, Any]]:
        """Get groups that have a specific realm role."""
        try:
            return await self.admin_adapter.a_get_realm_role_groups(
                role_name=role_name,
                query=query,
                brief_representation=brief_representation,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_realm_role_groups")

    # Authentication Flow Operations
    @override
    async def create_authentication_flow(self, payload: dict, skip_exists: bool = False) -> bytes:
        """Create a new authentication flow."""
        try:
            return await self.admin_adapter.a_create_authentication_flow(payload=payload, skip_exists=skip_exists)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_authentication_flow")

    @override
    async def copy_authentication_flow(self, payload: dict, flow_alias: str) -> bytes:
        """Copy an existing authentication flow."""
        try:
            return await self.admin_adapter.a_copy_authentication_flow(payload=payload, flow_alias=flow_alias)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "copy_authentication_flow")

    @override
    async def get_authentication_flows(
        self,
    ) -> list[dict[str, Any]]:
        """Get all authentication flows."""
        try:
            return await self.admin_adapter.a_get_authentication_flows()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authentication_flows")

    @override
    async def get_authentication_flow_for_id(self, flow_id: str) -> dict[str, Any]:
        """Get authentication flow by ID."""
        try:
            return await self.admin_adapter.a_get_authentication_flow_for_id(flow_id=flow_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authentication_flow_for_id")

    @override
    async def delete_authentication_flow(self, flow_id: str) -> dict[str, Any]:
        """Delete an authentication flow."""
        try:
            return await self.admin_adapter.a_delete_authentication_flow(flow_id=flow_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_authentication_flow")

    @override
    async def get_authentication_flow_executions(self, flow_alias: str) -> list[dict[str, Any]]:
        """Get executions for an authentication flow."""
        try:
            return await self.admin_adapter.a_get_authentication_flow_executions(flow_alias=flow_alias)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authentication_flow_executions")

    @override
    async def get_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Get a single authentication flow execution."""
        try:
            return await self.admin_adapter.a_get_authentication_flow_execution(execution_id=execution_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authentication_flow_execution")

    @override
    async def create_authentication_flow_execution(self, payload: dict, flow_alias: str) -> bytes:
        """Create an execution in an authentication flow."""
        try:
            return await self.admin_adapter.a_create_authentication_flow_execution(
                payload=payload,
                flow_alias=flow_alias,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_authentication_flow_execution")

    @override
    async def update_authentication_flow_executions(self, payload: dict, flow_alias: str) -> dict[str, Any]:
        """Update executions in an authentication flow."""
        try:
            return await self.admin_adapter.a_update_authentication_flow_executions(
                payload=payload,
                flow_alias=flow_alias,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_authentication_flow_executions")

    @override
    async def create_authentication_flow_subflow(
        self,
        payload: dict,
        flow_alias: str,
        skip_exists: bool = False,
    ) -> bytes:
        """Create a subflow in an authentication flow."""
        try:
            return await self.admin_adapter.a_create_authentication_flow_subflow(
                payload=payload,
                flow_alias=flow_alias,
                skip_exists=skip_exists,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_authentication_flow_subflow")

    @override
    async def delete_authentication_flow_execution(self, execution_id: str) -> dict[str, Any]:
        """Delete an authentication flow execution."""
        try:
            return await self.admin_adapter.a_delete_authentication_flow_execution(execution_id=execution_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_authentication_flow_execution")

    @override
    async def change_execution_priority(self, execution_id: str, diff: int) -> None:
        """Change priority of an authentication flow execution."""
        try:
            return await self.admin_adapter.a_change_execution_priority(execution_id=execution_id, diff=diff)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "change_execution_priority")

    @override
    async def update_authentication_flow(self, flow_id: str, payload: dict) -> dict[str, Any]:
        """Update an authentication flow."""
        try:
            return await self.admin_adapter.a_update_authentication_flow(flow_id=flow_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_authentication_flow")

    @override
    async def get_authenticator_providers(
        self,
    ) -> list[dict[str, Any]]:
        """Get available authenticator providers."""
        try:
            return await self.admin_adapter.a_get_authenticator_providers()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authenticator_providers")

    @override
    async def get_authenticator_provider_config_description(self, provider_id: str) -> dict[str, Any]:
        """Get config description for an authenticator provider."""
        try:
            return await self.admin_adapter.a_get_authenticator_provider_config_description(provider_id=provider_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authenticator_provider_config_description")

    @override
    async def get_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Get authenticator configuration by ID."""
        try:
            return await self.admin_adapter.a_get_authenticator_config(config_id=config_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_authenticator_config")

    @override
    async def update_authenticator_config(self, payload: dict, config_id: str) -> dict[str, Any]:
        """Update authenticator configuration."""
        try:
            return await self.admin_adapter.a_update_authenticator_config(payload=payload, config_id=config_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_authenticator_config")

    @override
    async def delete_authenticator_config(self, config_id: str) -> dict[str, Any]:
        """Delete authenticator configuration."""
        try:
            return await self.admin_adapter.a_delete_authenticator_config(config_id=config_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_authenticator_config")

    @override
    async def create_execution_config(self, execution_id: str, payload: dict) -> bytes:
        """Create configuration for an authentication flow execution."""
        try:
            return await self.admin_adapter.a_create_execution_config(execution_id=execution_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_execution_config")

    # Client Scope Operations
    @override
    async def get_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get all client scopes."""
        try:
            return await self.admin_adapter.a_get_client_scopes()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_scopes")

    @override
    async def get_client_scope(self, client_scope_id: str) -> dict[str, Any]:
        """Get a client scope by ID."""
        try:
            return await self.admin_adapter.a_get_client_scope(client_scope_id=client_scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_scope")

    @override
    async def get_client_scope_by_name(self, client_scope_name: str) -> dict[str, Any] | None:
        """Get a client scope by name."""
        try:
            return await self.admin_adapter.a_get_client_scope_by_name(client_scope_name=client_scope_name)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_scope_by_name")

    @override
    async def create_client_scope(self, payload: dict, skip_exists: bool = False) -> str:
        """Create a new client scope."""
        try:
            return await self.admin_adapter.a_create_client_scope(payload=payload, skip_exists=skip_exists)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_scope")

    @override
    async def update_client_scope(self, client_scope_id: str, payload: dict) -> dict[str, Any]:
        """Update a client scope."""
        try:
            return await self.admin_adapter.a_update_client_scope(client_scope_id=client_scope_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_client_scope")

    @override
    async def delete_client_scope(self, client_scope_id: str) -> dict[str, Any]:
        """Delete a client scope."""
        try:
            return await self.admin_adapter.a_delete_client_scope(client_scope_id=client_scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_client_scope")

    @override
    async def add_mapper_to_client_scope(self, client_scope_id: str, payload: dict) -> bytes:
        """Add a protocol mapper to a client scope."""
        try:
            return await self.admin_adapter.a_add_mapper_to_client_scope(
                client_scope_id=client_scope_id,
                payload=payload,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_mapper_to_client_scope")

    @override
    async def get_mappers_from_client_scope(self, client_scope_id: str) -> list[dict[str, Any]]:
        """Get protocol mappers for a client scope."""
        try:
            return await self.admin_adapter.a_get_mappers_from_client_scope(client_scope_id=client_scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_mappers_from_client_scope")

    @override
    async def update_mapper_in_client_scope(
        self,
        client_scope_id: str,
        protocol_mapper_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        """Update a protocol mapper in a client scope."""
        try:
            return await self.admin_adapter.a_update_mapper_in_client_scope(
                client_scope_id=client_scope_id,
                protocol_mapper_id=protocol_mapper_id,
                payload=payload,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_mapper_in_client_scope")

    @override
    async def delete_mapper_from_client_scope(self, client_scope_id: str, protocol_mapper_id: str) -> dict[str, Any]:
        """Delete a protocol mapper from a client scope."""
        try:
            return await self.admin_adapter.a_delete_mapper_from_client_scope(
                client_scope_id=client_scope_id,
                protocol_mapper_id=protocol_mapper_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_mapper_from_client_scope")

    @override
    async def add_mapper_to_client(self, client_id: str, payload: dict) -> bytes:
        """Add a protocol mapper to a client."""
        try:
            return await self.admin_adapter.a_add_mapper_to_client(client_id=client_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_mapper_to_client")

    @override
    async def get_mappers_from_client(self, client_id: str) -> list[dict[str, Any]]:
        """Get protocol mappers for a client."""
        try:
            return await self.admin_adapter.a_get_mappers_from_client(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_mappers_from_client")

    @override
    async def update_client_mapper(self, client_id: str, mapper_id: str, payload: dict) -> dict[str, Any]:
        """Update a protocol mapper on a client."""
        try:
            return await self.admin_adapter.a_update_client_mapper(
                client_id=client_id,
                mapper_id=mapper_id,
                payload=payload,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_client_mapper")

    @override
    async def remove_client_mapper(self, client_id: str, client_mapper_id: str) -> dict[str, Any]:
        """Remove a protocol mapper from a client."""
        try:
            return await self.admin_adapter.a_remove_client_mapper(
                client_id=client_id,
                client_mapper_id=client_mapper_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "remove_client_mapper")

    @override
    async def get_client_default_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get default client scopes for a client."""
        try:
            return await self.admin_adapter.a_get_client_default_client_scopes(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_default_client_scopes")

    @override
    async def add_client_default_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        """Add a default client scope to a client."""
        try:
            return await self.admin_adapter.a_add_client_default_client_scope(
                client_id=client_id,
                client_scope_id=client_scope_id,
                payload=payload,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_client_default_client_scope")

    @override
    async def delete_client_default_client_scope(self, client_id: str, client_scope_id: str) -> dict[str, Any]:
        """Remove a default client scope from a client."""
        try:
            return await self.admin_adapter.a_delete_client_default_client_scope(
                client_id=client_id,
                client_scope_id=client_scope_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_client_default_client_scope")

    @override
    async def get_client_optional_client_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get optional client scopes for a client."""
        try:
            return await self.admin_adapter.a_get_client_optional_client_scopes(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_optional_client_scopes")

    @override
    async def add_client_optional_client_scope(
        self,
        client_id: str,
        client_scope_id: str,
        payload: dict,
    ) -> dict[str, Any]:
        """Add an optional client scope to a client."""
        try:
            return await self.admin_adapter.a_add_client_optional_client_scope(
                client_id=client_id,
                client_scope_id=client_scope_id,
                payload=payload,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_client_optional_client_scope")

    @override
    async def delete_client_optional_client_scope(self, client_id: str, client_scope_id: str) -> dict[str, Any]:
        """Remove an optional client scope from a client."""
        try:
            return await self.admin_adapter.a_delete_client_optional_client_scope(
                client_id=client_id,
                client_scope_id=client_scope_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_client_optional_client_scope")

    @override
    async def get_default_default_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get realm default client scopes."""
        try:
            return await self.admin_adapter.a_get_default_default_client_scopes()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_default_default_client_scopes")

    @override
    async def add_default_default_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Add a realm default client scope."""
        try:
            return await self.admin_adapter.a_add_default_default_client_scope(scope_id=scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_default_default_client_scope")

    @override
    async def delete_default_default_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Remove a realm default client scope."""
        try:
            return await self.admin_adapter.a_delete_default_default_client_scope(scope_id=scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_default_default_client_scope")

    @override
    async def get_default_optional_client_scopes(
        self,
    ) -> list[dict[str, Any]]:
        """Get realm optional default client scopes."""
        try:
            return await self.admin_adapter.a_get_default_optional_client_scopes()
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_default_optional_client_scopes")

    @override
    async def add_default_optional_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Add a realm optional default client scope."""
        try:
            return await self.admin_adapter.a_add_default_optional_client_scope(scope_id=scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "add_default_optional_client_scope")

    @override
    async def delete_default_optional_client_scope(self, scope_id: str) -> dict[str, Any]:
        """Remove a realm optional default client scope."""
        try:
            return await self.admin_adapter.a_delete_default_optional_client_scope(scope_id=scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_default_optional_client_scope")

    # Authorization Service Operations
    @override
    async def create_client_authz_resource(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create an authorization resource for a client."""
        try:
            return await self.admin_adapter.a_create_client_authz_resource(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_resource")

    @override
    async def get_client_authz_resources(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization resources for a client."""
        try:
            return await self.admin_adapter.a_get_client_authz_resources(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_resources")

    @override
    async def get_client_authz_resource(self, client_id: str, resource_id: str) -> dict[str, Any]:
        """Get a single authorization resource."""
        try:
            return await self.admin_adapter.a_get_client_authz_resource(client_id=client_id, resource_id=resource_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_resource")

    @override
    async def update_client_authz_resource(self, client_id: str, resource_id: str, payload: dict) -> dict[str, Any]:
        """Update an authorization resource."""
        try:
            return await self.admin_adapter.a_update_client_authz_resource(
                client_id=client_id,
                resource_id=resource_id,
                payload=payload,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_client_authz_resource")

    @override
    async def delete_client_authz_resource(self, client_id: str, resource_id: str) -> dict[str, Any]:
        """Delete an authorization resource."""
        try:
            return await self.admin_adapter.a_delete_client_authz_resource(client_id=client_id, resource_id=resource_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_client_authz_resource")

    @override
    async def create_client_authz_scopes(self, client_id: str, payload: dict) -> dict[str, Any]:
        """Create authorization scopes for a client."""
        try:
            return await self.admin_adapter.a_create_client_authz_scopes(client_id=client_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_scopes")

    @override
    async def get_client_authz_scopes(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization scopes for a client."""
        try:
            return await self.admin_adapter.a_get_client_authz_scopes(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_scopes")

    @override
    async def create_client_authz_role_based_policy(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create a role-based authorization policy."""
        try:
            return await self.admin_adapter.a_create_client_authz_role_based_policy(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_role_based_policy")

    @override
    async def create_client_authz_client_policy(self, payload: dict, client_id: str) -> dict[str, Any]:
        """Create a client-based authorization policy."""
        try:
            return await self.admin_adapter.a_create_client_authz_client_policy(payload=payload, client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_client_policy")

    @override
    async def create_client_authz_policy(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create an authorization policy."""
        try:
            return await self.admin_adapter.a_create_client_authz_policy(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_policy")

    @override
    async def get_client_authz_policies(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization policies for a client."""
        try:
            return await self.admin_adapter.a_get_client_authz_policies(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_policies")

    @override
    async def get_client_authz_policy(self, client_id: str, policy_id: str) -> dict[str, Any]:
        """Get a single authorization policy."""
        try:
            return await self.admin_adapter.a_get_client_authz_policy(client_id=client_id, policy_id=policy_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_policy")

    @override
    async def delete_client_authz_policy(self, client_id: str, policy_id: str) -> dict[str, Any]:
        """Delete an authorization policy."""
        try:
            return await self.admin_adapter.a_delete_client_authz_policy(client_id=client_id, policy_id=policy_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_client_authz_policy")

    @override
    async def create_client_authz_resource_based_permission(
        self,
        client_id: str,
        payload: dict,
        skip_exists: bool = False,
    ) -> dict[str, Any]:
        """Create a resource-based permission."""
        try:
            return await self.admin_adapter.a_create_client_authz_resource_based_permission(
                client_id=client_id,
                payload=payload,
                skip_exists=skip_exists,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_resource_based_permission")

    @override
    async def create_client_authz_scope_permission(self, payload: dict, client_id: str) -> dict[str, Any]:
        """Create a scope-based permission."""
        try:
            return await self.admin_adapter.a_create_client_authz_scope_permission(payload=payload, client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_client_authz_scope_permission")

    @override
    async def get_client_authz_permissions(self, client_id: str) -> list[dict[str, Any]]:
        """Get authorization permissions for a client."""
        try:
            return await self.admin_adapter.a_get_client_authz_permissions(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_permissions")

    @override
    async def get_client_authz_scope_permission(self, client_id: str, scope_id: str) -> dict[str, Any]:
        """Get a scope-based permission."""
        try:
            return await self.admin_adapter.a_get_client_authz_scope_permission(client_id=client_id, scope_id=scope_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_scope_permission")

    @override
    async def update_client_authz_scope_permission(self, payload: dict, client_id: str, scope_id: str) -> bytes:
        """Update a scope-based permission."""
        try:
            return await self.admin_adapter.a_update_client_authz_scope_permission(
                payload=payload,
                client_id=client_id,
                scope_id=scope_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_client_authz_scope_permission")

    @override
    async def update_client_authz_resource_permission(self, payload: dict, client_id: str, resource_id: str) -> bytes:
        """Update a resource-based permission."""
        try:
            return await self.admin_adapter.a_update_client_authz_resource_permission(
                payload=payload,
                client_id=client_id,
                resource_id=resource_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_client_authz_resource_permission")

    @override
    async def get_client_authz_permission_associated_policies(
        self,
        client_id: str,
        policy_id: str,
    ) -> list[dict[str, Any]]:
        """Get policies associated with a permission."""
        try:
            return await self.admin_adapter.a_get_client_authz_permission_associated_policies(
                client_id=client_id,
                policy_id=policy_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_permission_associated_policies")

    @override
    async def get_client_authz_settings(self, client_id: str) -> dict[str, Any]:
        """Get authorization settings for a client."""
        try:
            return await self.admin_adapter.a_get_client_authz_settings(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_settings")

    @override
    async def get_client_authz_client_policies(self, client_id: str) -> list[dict[str, Any]]:
        """Get client policies for authorization."""
        try:
            return await self.admin_adapter.a_get_client_authz_client_policies(client_id=client_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_client_policies")

    @override
    async def get_client_authz_policy_resources(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get resources associated with a policy."""
        try:
            return await self.admin_adapter.a_get_client_authz_policy_resources(
                client_id=client_id,
                policy_id=policy_id,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_policy_resources")

    @override
    async def get_client_authz_policy_scopes(self, client_id: str, policy_id: str) -> list[dict[str, Any]]:
        """Get scopes associated with a policy."""
        try:
            return await self.admin_adapter.a_get_client_authz_policy_scopes(client_id=client_id, policy_id=policy_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_client_authz_policy_scopes")

    @override
    async def import_client_authz_config(self, client_id: str, payload: dict) -> dict[str, Any]:
        """Import authorization configuration for a client."""
        try:
            return await self.admin_adapter.a_import_client_authz_config(client_id=client_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "import_client_authz_config")

    # UMA Operations
    @override
    async def resource_set_create(self, payload: dict) -> dict[str, Any]:
        """Create a UMA resource set."""
        try:
            return await self.uma_adapter.a_resource_set_create(payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "resource_set_create")

    @override
    async def resource_set_read(self, resource_id: str) -> dict[str, Any]:
        """Read a UMA resource set."""
        try:
            return await self.uma_adapter.a_resource_set_read(resource_id=resource_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "resource_set_read")

    @override
    async def resource_set_update(self, resource_id: str, payload: dict) -> dict[str, Any]:
        """Update a UMA resource set."""
        try:
            return await self.uma_adapter.a_resource_set_update(resource_id=resource_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "resource_set_update")

    @override
    async def resource_set_delete(self, resource_id: str) -> dict[str, Any]:
        """Delete a UMA resource set."""
        try:
            return await self.uma_adapter.a_resource_set_delete(resource_id=resource_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "resource_set_delete")

    @override
    async def resource_set_list(
        self,
    ) -> list[dict[str, Any]]:
        """List all UMA resource sets."""
        try:
            return [item async for item in self.uma_adapter.a_resource_set_list()]
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "resource_set_list")

    @override
    async def resource_set_list_ids(
        self,
        name: str = "",
        exact_name: bool = False,
        uri: str = "",
        owner: str = "",
        resource_type: str = "",
        scope: str = "",
        matchingUri: bool = False,
        first: int = 0,
        maximum: int = -1,
    ) -> list[dict[str, Any]]:
        """List UMA resource set IDs with optional filters."""
        try:
            return await self.uma_adapter.a_resource_set_list_ids(
                name=name,
                exact_name=exact_name,
                uri=uri,
                owner=owner,
                resource_type=resource_type,
                scope=scope,
                matchingUri=matchingUri,
                first=first,
                maximum=maximum,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "resource_set_list_ids")

    @override
    async def policy_resource_create(self, resource_id: str, payload: dict) -> dict[str, Any]:
        """Create a UMA policy for a resource."""
        try:
            return await self.uma_adapter.a_policy_resource_create(resource_id=resource_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "policy_resource_create")

    @override
    async def policy_update(self, policy_id: str, payload: dict) -> bytes:
        """Update a UMA policy."""
        try:
            return await self.uma_adapter.a_policy_update(policy_id=policy_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "policy_update")

    @override
    async def policy_delete(self, policy_id: str) -> dict[str, Any]:
        """Delete a UMA policy."""
        try:
            return await self.uma_adapter.a_policy_delete(policy_id=policy_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "policy_delete")

    @override
    async def policy_query(
        self,
        resource: str = "",
        name: str = "",
        scope: str = "",
        first: int = 0,
        maximum: int = -1,
    ) -> list[dict[str, Any]]:
        """Query UMA policies."""
        try:
            return await self.uma_adapter.a_policy_query(
                resource=resource,
                name=name,
                scope=scope,
                first=first,
                maximum=maximum,
            )
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "policy_query")

    @override
    async def permission_ticket_create(self, permissions: Iterable[UMAPermission]) -> dict[str, Any]:
        """Create a UMA permission ticket."""
        try:
            return await self.uma_adapter.a_permission_ticket_create(permissions=permissions)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "permission_ticket_create")

    @override
    async def permissions_check(self, token: str, permissions: Iterable[UMAPermission], **extra_payload: Any) -> bool:
        """Check UMA permissions for a token."""
        try:
            return await self.uma_adapter.a_permissions_check(token=token, permissions=permissions, **extra_payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "permissions_check")

    # Component Operations
    @override
    async def create_component(self, payload: dict) -> str:
        """Create a Keycloak component."""
        try:
            return await self.admin_adapter.a_create_component(payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "create_component")

    @override
    async def get_component(self, component_id: str) -> dict[str, Any]:
        """Get a component by ID."""
        try:
            return await self.admin_adapter.a_get_component(component_id=component_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_component")

    @override
    async def get_components(self, query: dict | None = None) -> list[dict[str, Any]]:
        """Get components, optionally filtered by query."""
        try:
            return await self.admin_adapter.a_get_components(query=query)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "get_components")

    @override
    async def update_component(self, component_id: str, payload: dict) -> dict[str, Any]:
        """Update a component."""
        try:
            return await self.admin_adapter.a_update_component(component_id=component_id, payload=payload)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "update_component")

    @override
    async def delete_component(self, component_id: str) -> dict[str, Any]:
        """Delete a component."""
        try:
            return await self.admin_adapter.a_delete_component(component_id=component_id)
        except KeycloakError as e:
            self._handle_keycloak_exception(e, "delete_component")
