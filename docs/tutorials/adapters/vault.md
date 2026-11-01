---
title: Vault Adapter Tutorial
description: Practical examples for using the ArchiPy HashiCorp Vault adapter.
---

# Vault Adapter Tutorial

The Vault adapter provides KV v2 secret management, dynamic credential leases, and transit
encryption against HashiCorp Vault. Under the hood it uses the official
[hvac](https://python-hvac.org/en/stable/overview.html) client
([usage reference](https://python-hvac.org/en/stable/usage/index.html)).

## Installation

```bash
uv add "archipy[vault]"
```

## Configuration

Configure the Vault adapter via environment variables or a `VaultConfig` object.
`create_vault_client()` builds an `hvac.Client` the same way the
[hvac overview](https://python-hvac.org/en/stable/overview.html#initialize-the-client) shows:
`url`, optional `namespace`, `verify` (bool or CA path), and optional mTLS `cert=(cert, key)`.

### Environment Variables

!!! warning
    Keep `VAULT__TOKEN` and other credentials out of source control. For AppRole, userpass and JWT, prefer the `*_FILE`
    variants (for example `VAULT__APPROLE_SECRET_ID_FILE`) over inline secrets.

!!! note
    `VAULT__SECRET_CACHE_TTL=0` disables caching of `read_secret()` results. `VAULT__CONNECT_TIMEOUT` and
    `VAULT__READ_TIMEOUT` default to `5.0` and `10.0` seconds.

```bash
VAULT__ENABLED=true
VAULT__ADDR=https://vault.example.com:8200
VAULT__NAMESPACE=  # Vault Enterprise namespace (optional)
VAULT__AUTH_METHOD=token
VAULT__TOKEN=s.xxxxx
VAULT__MOUNT_POINT=secret
VAULT__VERIFY_SSL=true
# VAULT__CA_CERT_PATH=/etc/ssl/certs/vault-ca.pem
# VAULT__CLIENT_CERT_PATH=/etc/ssl/certs/client.pem
# VAULT__CLIENT_KEY_PATH=/etc/ssl/private/client.key
VAULT__CONNECT_TIMEOUT=5.0
VAULT__READ_TIMEOUT=10.0
VAULT__SECRET_CACHE_TTL=0
VAULT__AUTO_RENEW_TOKEN=false
```

Supported `VAULT__AUTH_METHOD` values (hvac backends):
`token`, `approle`, `kubernetes`, `userpass`, `ldap`, `okta`, `jwt`, `aws`,
`azure`, `gcp`, `github`, `cert`.

AppRole example:

```bash
VAULT__AUTH_METHOD=approle
VAULT__APPROLE_ROLE_ID=...
VAULT__APPROLE_SECRET_ID_FILE=/run/secrets/approle_secret_id
```

Kubernetes example:

```bash
VAULT__AUTH_METHOD=kubernetes
VAULT__KUBERNETES_ROLE=my-app
VAULT__KUBERNETES_JWT_PATH=/var/run/secrets/kubernetes.io/serviceaccount/token
```

Userpass / LDAP / Okta example:

```bash
VAULT__AUTH_METHOD=userpass
VAULT__USERNAME=app-user
VAULT__PASSWORD_FILE=/run/secrets/vault_password
```

JWT example:

```bash
VAULT__AUTH_METHOD=jwt
VAULT__JWT_ROLE=my-role
VAULT__JWT_FILE=/run/secrets/vault.jwt
```

AWS IAM example:

```bash
VAULT__AUTH_METHOD=aws
VAULT__AWS_ACCESS_KEY=...
VAULT__AWS_SECRET_KEY=...
VAULT__AWS_ROLE=my-role
VAULT__AWS_REGION=us-east-1
```

GitHub / cert / cloud JWT (azure, gcp) follow the same pattern — see `VaultConfig`
fields (`GITHUB_TOKEN`, `CERT_NAME` + client cert paths, `AZURE_*`, `GCP_*`).

### Direct Configuration

```python
from archipy.configs.config_template import VaultConfig

config = VaultConfig(
    ENABLED=True,
    ADDR="https://vault.example.com:8200",
    AUTH_METHOD="token",
    TOKEN="s.xxxxx",  # noqa: S106
    MOUNT_POINT="secret",
    VERIFY_SSL=True,
    # CA_CERT_PATH="/etc/ssl/certs/vault-ca.pem",
    # CLIENT_CERT_PATH="/etc/ssl/certs/client.pem",
    # CLIENT_KEY_PATH="/etc/ssl/private/client.key",
)
```

## Basic Usage

KV operations map to hvac
[KV v2](https://python-hvac.org/en/stable/usage/secrets_engines/kv_v2.html)
(`create_or_update_secret`, `read_secret_version`, `list_secrets`,
`delete_metadata_and_all_versions`).

```python
import logging

from archipy.adapters.vault.adapters import VaultAdapter
from archipy.models.errors import ConfigurationError, NotFoundError, PermissionDeniedError

logger = logging.getLogger(__name__)

try:
    vault = VaultAdapter()
except ConfigurationError as e:
    logger.error("Failed to create Vault adapter: %s", e)
    raise
else:
    logger.info("Vault adapter created successfully")

try:
    vault.write_secret("myapp/db", {"password": "s3cret"})
    secret = vault.read_secret("myapp/db")
    logger.info("Loaded secret keys: %s", list(secret.keys()))
except (NotFoundError, PermissionDeniedError) as e:
    logger.error("Vault secret operation failed: %s", e)
    raise
```

## Advanced Features

### Dynamic Credentials

!!! tip
    Dynamic credentials come with a lease. Renew the lease while you still need the credentials, and revoke it when
    you are done.

Without `parameters`, the adapter calls hvac
[
`secrets.database.generate_credentials`](https://python-hvac.org/en/stable/usage/secrets_engines/database.html#generate-credentials)
(with a generic read fallback for non-database mounts). Pass `parameters` (even `{}`) to
force a write to `{mount}/creds/{role}` for engines like SSH OTP. Lease renew/revoke use
[`sys.renew_lease` / `sys.revoke_lease`](https://python-hvac.org/en/stable/usage/system_backend/lease.html).

```python
import logging

from archipy.adapters.vault.adapters import VaultAdapter

logger = logging.getLogger(__name__)
vault = VaultAdapter()

lease = vault.get_dynamic_credentials("database", "readonly")
logger.info("Got dynamic user %s (lease=%s)", lease.data.get("username"), lease.lease_id)

renewed = vault.renew_lease(lease.lease_id)
logger.info("Renewed lease duration=%s", renewed.lease_duration)

vault.revoke_lease(lease.lease_id)
logger.info("Revoked lease %s", lease.lease_id)

# SSH OTP-style engines that require a write body:
# lease = vault.get_dynamic_credentials("ssh", "otp-role", parameters={"ip": "127.0.0.1"})
```

### Transit Encrypt / Decrypt

```python
import logging

from archipy.adapters.vault.adapters import VaultAdapter

logger = logging.getLogger(__name__)
vault = VaultAdapter()

ciphertext = vault.encrypt("app-key", "hello-vault")
plaintext = vault.decrypt("app-key", ciphertext)
logger.info("Round-trip ok: %s", plaintext == "hello-vault")
```

### Startup Secret Injection

When `VAULT__ENABLED=true`, `BaseConfig` also loads KV v2 secrets listed in
`VAULT__SECRET_PATHS` during settings initialization. Flat keys using `__`
map onto nested config fields (e.g. `REDIS__PASSWORD` → `REDIS.PASSWORD`).

See [Configuration Management](../config_management.md) for priority order and
settings-source details.

### Retries and Outages

`VAULT__RETRIES_MAX_ATTEMPTS` retries failed connections for every call. Read errors and
`500`/`502`/`503`/`504` responses are retried only for idempotent reads (`GET`, `HEAD`, `LIST`),
so a write, delete or lease operation is never replayed. When Vault stays unavailable the adapter
raises `UnavailableError` with a fixed message (the Vault address and path are logged, not
returned in the error).

### Good to Know

- `read_secret` returns a copy of the payload, so changing the result never alters the cached value.
- `VAULT__VERIFY_SSL` accepts `1/true/yes/on` and `0/false/no/off` (case-insensitive). Any other value raises a
  `ConfigurationError` instead of silently turning verification off.
- Credential fields of `VaultConfig` (`TOKEN`, `APPROLE_SECRET_ID`, `PASSWORD`, the JWT and AWS secrets) are
  excluded from `repr()`. Error reasons are generic; the underlying detail is logged.
- If two callers request dynamic credentials for the same role, each call creates its own lease. Revoke
  the leases you no longer need.

## See Also

- [hvac overview](https://python-hvac.org/en/stable/overview.html) — Client init and auth
- [hvac usage](https://python-hvac.org/en/stable/usage/index.html) — Secrets engines and system backend
- [Configuration Management](../config_management.md) — Vault-backed settings source
- [Error Handling](../error_handling.md) — Domain error mapping conventions
- [BDD Testing](../testing_strategy.md) — Testcontainers-based adapter tests
- BDD feature files — [`vault_adapter.feature`](https://github.com/SyntaxArc/ArchiPy/blob/master/features/vault_adapter.feature), [`vault_adapter_apm.feature`](https://github.com/SyntaxArc/ArchiPy/blob/master/features/vault_adapter_apm.feature)
- [Vault API Reference](../../api_reference/adapters/vault.md) — Ports and adapter docs
- [Configs API Reference](../../api_reference/configs.md) — `VaultConfig` fields
