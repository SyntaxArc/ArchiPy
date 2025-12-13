# Utilities

Examples of ArchiPy's utility functions:

## datetime_utils

Work with dates and times consistently:

```python
import logging

from archipy.helpers.utils.datetime_utils import DatetimeUtils

# Configure logging
logger = logging.getLogger(__name__)

# Get current UTC time
now = DatetimeUtils.get_datetime_utc_now()

# Format for storage/transmission
date_str = DatetimeUtils.get_string_datetime_from_datetime(now)

# Parse date string
parsed = DatetimeUtils.get_datetime_from_string_datetime(date_str)

# Convert to Jalali (Persian) calendar
jalali_date = DatetimeUtils.convert_to_jalali(now)

# Check if date is a holiday in Iran
is_holiday = DatetimeUtils.is_holiday_in_iran(now)
logger.info(f"Is holiday: {is_holiday}")
```

## jwt_utils

Generate and verify JWT tokens:

```python
import logging
from archipy.helpers.utils.jwt_utils import JWTUtils
from uuid import uuid4

# Configure logging
logger = logging.getLogger(__name__)

# Generate a user access token
user_id = uuid4()
access_token = JWTUtils.create_access_token(user_id)

# Generate a refresh token with additional claims
additional_claims = {"user_role": "admin", "permissions": ["read", "write"]}
refresh_token = JWTUtils.create_refresh_token(user_id, additional_claims=additional_claims)

# Verify a token
try:
    payload = JWTUtils.verify_access_token(access_token)
except (InvalidTokenError, TokenExpiredError) as e:
    logger.error(f"Invalid token: {e}")
    raise
else:
    logger.info(f"Token valid for user: {payload['sub']}")

# Get token expiration time
expiry = JWTUtils.get_token_expiry(access_token)
logger.debug(f"Token expires at: {expiry}")

# Extract user UUID from token payload
user_uuid = JWTUtils.extract_user_uuid(payload)
```

## password_utils

Secure password handling:

```python
import logging

from archipy.helpers.utils.password_utils import PasswordUtils
from archipy.models.types.language_type import LanguageType
from archipy.models.errors import InvalidPasswordError

# Configure logging
logger = logging.getLogger(__name__)

# Hash a password
password = "SecureP@ssword123"
hashed = PasswordUtils.hash_password(password)

# Verify password
is_valid = PasswordUtils.verify_password(password, hashed)
logger.info(f"Password valid: {is_valid}")

# Generate a secure password that meets policy requirements
secure_password = PasswordUtils.generate_password()
logger.info(f"Generated password: {secure_password}")

# Validate a password against policy
try:
    PasswordUtils.validate_password(password, lang=LanguageType.EN)
except InvalidPasswordError as e:
    logger.warning(f"Invalid password: {e.requirements}")
    raise
else:
    logger.info("Password meets policy requirements")

# Check password against history
password_history = [hashed]  # Previous password hashes
try:
    PasswordUtils.validate_password_history("NewSecureP@ssword123", password_history)
except InvalidPasswordError as e:
    logger.warning("Password has been used recently")
    raise
else:
    logger.info("Password not previously used")
```

## file_utils

Handle files securely:

```python
import logging

from archipy.helpers.utils.file_utils import FileUtils
from archipy.models.errors import InvalidArgumentError, OutOfRangeError

# Configure logging
logger = logging.getLogger(__name__)

# Create a secure link to a file with expiration
try:
    link = FileUtils.create_secure_link("/path/to/document.pdf", minutes=60)
except (InvalidArgumentError, OutOfRangeError) as e:
    logger.error(f"Error creating link: {e}")
    raise
else:
    logger.info(f"Secure link: {link}")

# Validate file name against allowed extensions
try:
    is_valid = FileUtils.validate_file_name("document.pdf")
except InvalidArgumentError as e:
    logger.error(f"Error validating file: {e}")
    raise
else:
    logger.info(f"File is valid: {is_valid}")
```

## base_utils

Validate and sanitize data:

```python
import logging

from archipy.helpers.utils.base_utils import BaseUtils
from archipy.models.errors import InvalidArgumentError

# Configure logging
logger = logging.getLogger(__name__)

# Sanitize phone number
phone = BaseUtils.sanitize_iranian_landline_or_phone_number("+989123456789")
logger.info(f"Sanitized phone: {phone}")  # 09123456789

# Validate Iranian national code
try:
    BaseUtils.validate_iranian_national_code_pattern("1234567891")
except InvalidArgumentError as e:
    logger.error(f"Invalid national code: {e}")
    raise
else:
    logger.info("National code is valid")
```

## error_utils

Standardized exception handling:

## app_utils

FastAPI application utilities:

```python
import logging

from archipy.helpers.utils.app_utils import AppUtils, FastAPIUtils
from archipy.configs.base_config import BaseConfig

# Configure logging
logger = logging.getLogger(__name__)

# Create a FastAPI app with standard config
app = AppUtils.create_fastapi_app(BaseConfig.global_config())

# Add custom exception handlers
FastAPIUtils.setup_exception_handlers(app)


# Set up CORS
FastAPIUtils.setup_cors(
    app,
    allowed_origins=["https://example.com"]
)

logger.info("FastAPI app configured successfully")
```

## string_utils

String manipulation utilities:

## keycloak_utils

Authentication and authorization utilities with Keycloak integration:

```python
if __name__ == '__main__':
    import uvicorn
    from uuid import UUID
    from archipy.configs.base_config import BaseConfig
    from archipy.helpers.utils.app_utils import AppUtils
    from archipy.helpers.utils.keycloak_utils import KeycloakUtils
    from archipy.models.types.language_type import LanguageType
    from fastapi import Depends

    # Initialize your app configuration
    config = BaseConfig()
    BaseConfig.set_global(config)
    app = AppUtils.create_fastapi_app()

    # Resource-based authorization for users with role and admin access
    @app.get("/users/{user_uuid}/info")
    def get_user_info(user_uuid: UUID, user: dict = Depends(KeycloakUtils.fastapi_auth(
        resource_type_param="user_uuid",
        resource_type="users",
        required_roles={"user"},
        admin_roles={"superusers", "administrators"},
        lang=LanguageType.EN,
    ))):
        return {
            "message": f"User info for {user_uuid}",
            "username": user.get("preferred_username")
        }

    # Async version for employees with multiple acceptable roles
    @app.get("/employees/{employee_uuid}/info")
    async def get_employee_info(employee_uuid: UUID, employee: dict = Depends(KeycloakUtils.async_fastapi_auth(
        resource_type_param="employee_uuid",
        resource_type="employees",
        required_roles={"employee", "manager", "user"},
        all_roles_required=False,  # User can have any of these roles
        admin_roles={"hr_admins", "system_admins"},
        lang=LanguageType.FA,
    ))):
        return {
            "message": f"Employee info for {employee_uuid}",
            "username": employee.get("preferred_username")
        }

    uvicorn.run(app, host="0.0.0.0", port=8000)
```

# Additional Resources

For more examples and detailed documentation:

- [Helpers Overview](../../api_reference/helpers.md)
- [Utils API Reference](../../api_reference/utils.md)
- [Configuration Examples](../config_management.md)
- [Keycloak Adapter](../adapters/keycloak.md)

> **Note**: This page contains examples of using ArchiPy's utility functions. For API details, see
> the [Utils API Reference](../../api_reference/utils.md).
