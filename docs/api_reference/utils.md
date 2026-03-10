# Utils

The `utils` module provides helper classes with static methods for common operations across the application.

## datetime_utils

Utilities for date and time operations.

```python
from archipy.helpers.utils.datetime_utils import DateTimeUtils

# Get current UTC time
now = DateTimeUtils.get_utc_now()

# Format datetime
formatted = DateTimeUtils.format_datetime(now, format="%Y-%m-%d %H:%M:%S")
```

::: archipy.helpers.utils.datetime_utils
    options:
      show_root_heading: true
      show_source: true

## file_utils

Utilities for file operations.

```python
from archipy.helpers.utils.file_utils import FileUtils

# Read file content
content = FileUtils.read_file("path/to/file.txt")

# Write to file
FileUtils.write_file("path/to/output.txt", "content")

# Get file hash
file_hash = FileUtils.get_file_hash("path/to/file.txt")

# Validate file type
is_valid = FileUtils.validate_file_type("path/to/file.pdf", allowed_types=["pdf", "doc"])
```

::: archipy.helpers.utils.file_utils
    options:
      show_root_heading: true
      show_source: true

## jwt_utils

Utilities for JWT (JSON Web Token) operations.

```python
from archipy.helpers.utils.jwt_utils import JWTUtils

# Generate JWT
token = JWTUtils.generate_jwt(
    payload={"user_id": "123"},
    secret="your-secret",
    expires_in=3600
)

# Verify JWT
is_valid = JWTUtils.verify_jwt(token, secret="your-secret")

# Decode JWT
payload = JWTUtils.decode_jwt(token)
```

::: archipy.helpers.utils.jwt_utils
    options:
      show_root_heading: true
      show_source: true

## password_utils

Utilities for password operations.

```python
from archipy.helpers.utils.password_utils import PasswordUtils

# Hash password
hashed = PasswordUtils.hash_password("my-password")

# Verify password
is_valid = PasswordUtils.verify_password("my-password", hashed)

# Generate secure password
password = PasswordUtils.generate_password(length=12)

# Validate password strength
is_strong = PasswordUtils.validate_password_strength("my-password")
```

::: archipy.helpers.utils.password_utils
    options:
      show_root_heading: true
      show_source: true

## string_utils

Utilities for string operations.

```python
from archipy.helpers.utils.string_utils import StringUtils

# Convert to slug
slug = StringUtils.slugify("My Article Title")

# Truncate string
truncated = StringUtils.truncate("Long text here", length=10)

# Generate random string
random_str = StringUtils.generate_random_string(length=8)

# Sanitize HTML
clean_html = StringUtils.sanitize_html("<script>alert('xss')</script>")
```

::: archipy.helpers.utils.string_utils
    options:
      show_root_heading: true
      show_source: true

## totp_utils

Utilities for TOTP (Time-based One-Time Password) operations.

```python
from archipy.helpers.utils.totp_utils import TOTPUtils

# Generate TOTP
totp_code = TOTPUtils.generate_totp(secret_key="your-secret")

# Verify TOTP
is_valid = TOTPUtils.verify_totp(totp_code, secret_key="your-secret")

# Generate secret key
secret_key = TOTPUtils.generate_secret_key()

# Get TOTP URI for QR code
totp_uri = TOTPUtils.get_totp_uri(
    secret_key=secret_key,
    issuer="MyApp",
    account_name="user@example.com"
)
```

::: archipy.helpers.utils.totp_utils
    options:
      show_root_heading: true
      show_source: true

## keycloak_utils

Utilities for Keycloak integration.

```python
from archipy.helpers.utils.keycloak_utils import KeycloakUtils

# Get token
token = KeycloakUtils.get_keycloak_token(
    username="user",
    password="pass",
    client_id="my-client"
)

# Validate token
is_valid = KeycloakUtils.validate_keycloak_token(token)

# Get user info
user_info = KeycloakUtils.get_keycloak_userinfo(token)

# Check role
has_role = KeycloakUtils.has_keycloak_role(token, "admin")
```

::: archipy.helpers.utils.keycloak_utils
    options:
      show_root_heading: true
      show_source: true

## Key Classes

### DateTimeUtils

Class: `archipy.helpers.utils.datetime_utils.DateTimeUtils`

Provides datetime operations with features:

- Timezone-aware
- Microsecond precision
- Consistent across the application

### JWTUtils

Class: `archipy.helpers.utils.jwt_utils.JWTUtils`

Provides JWT operations with features:

- Configurable expiration
- Custom payload support
- Multiple signing algorithms
- Token refresh capability

### PasswordUtils

Class: `archipy.helpers.utils.password_utils.PasswordUtils`

Provides password operations with features:

- Secure hashing algorithm
- Salt generation
- Configurable work factor
- Protection against timing attacks
