---
title: Upgrade to ArchiPy 6.0
description: Replace the deprecated APIs, settings, and behaviors removed in ArchiPy 6.0.
---

# Upgrade to ArchiPy 6.0

Run a representative workload on the latest 5.x release with deprecation warnings enabled to locate calls that
need migration. Review configuration files and environment variables as well.

```bash
uv run python -W default::DeprecationWarning -m your_app
```

## Decorators

Import the replacement names from `archipy.helpers.decorators`. The decorators support synchronous and asynchronous
functions through the same API.

| Deprecated                  | Replacement        |
|-----------------------------|--------------------|
| `retry_decorator`           | `retry`            |
| `timeout_decorator`         | `timeout`          |
| `timing_decorator`          | `timing`           |
| `singleton_decorator`       | `singleton`        |
| `ttl_cache_decorator`       | `ttl_cache`        |
| `grpc_rate_limit_decorator` | `grpc_rate_limit`  |
| `async_measure_duration`    | `measure_duration` |
| `async_count_calls`         | `count_calls`      |
| `async_trace_span`          | `trace_span`       |
| `async_trace_root`          | `trace_root`       |

For example, replace `@retry_decorator` with `@retry` and keep the retry policy explicit:

```python
# retry_example.py
from collections.abc import Iterator

from archipy.helpers.decorators import retry


@retry(max_retries=2, delay=0, retry_on=(ConnectionError,))
def read_value(responses: Iterator[str | None]) -> str:
    """Read a value from a source that can fail temporarily."""
    value = next(responses)
    if value is None:
        raise ConnectionError("Source temporarily unavailable")
    return value


result = read_value(iter((None, "ready")))
```

The first attempt raises `ConnectionError`. The second returns `"ready"`.

### Removed import paths

| Deprecated import path                       | Replacement                                           |
|----------------------------------------------|-------------------------------------------------------|
| `archipy.helpers.decorators.retry`           | `from archipy.helpers.decorators import retry`        |
| `archipy.helpers.decorators.timeout`         | `from archipy.helpers.decorators import timeout`      |
| `archipy.helpers.decorators.timing`          | `from archipy.helpers.decorators import timing`       |
| `archipy.helpers.decorators.singleton`       | `from archipy.helpers.decorators import singleton`    |
| `archipy.helpers.decorators.cache`           | `from archipy.helpers.decorators import ttl_cache`    |
| `archipy.helpers.decorators.grpc_rate_limit` | `from archipy.helpers.decorators import grpc_rate_limit` |
| `archipy.helpers.decorators.sqlalchemy_atomic` | `archipy.adapters.base.sqlalchemy.atomic`           |

The `archipy.helpers.decorators.sqlalchemy_transaction` path also moves to `archipy.adapters.base.sqlalchemy.atomic`.

### SQLAlchemy atomic decorators

Import all atomic decorators from `archipy.adapters.base.sqlalchemy.atomic`.

| Deprecated                                                                             | Replacement                                                           | Since  |
|----------------------------------------------------------------------------------------|-----------------------------------------------------------------------|--------|
| `archipy.helpers.decorators.sqlalchemy_atomic`                                         | `archipy.adapters.base.sqlalchemy.atomic.sqlalchemy_atomic`           | 5.16.0 |
| `archipy.helpers.decorators.postgres_sqlalchemy_atomic`                                | `archipy.adapters.base.sqlalchemy.atomic.postgres_sqlalchemy_atomic`  | 5.16.0 |
| `archipy.helpers.decorators.mysql_sqlalchemy_atomic`                                   | `archipy.adapters.base.sqlalchemy.atomic.mysql_sqlalchemy_atomic`     | 5.16.0 |
| `archipy.helpers.decorators.sqlite_sqlalchemy_atomic`                                  | `archipy.adapters.base.sqlalchemy.atomic.sqlite_sqlalchemy_atomic`    | 5.16.0 |
| `archipy.helpers.decorators.starrocks_sqlalchemy_atomic`                               | `archipy.adapters.base.sqlalchemy.atomic.starrocks_sqlalchemy_atomic` | 5.16.0 |
| `sqlalchemy_atomic_decorator(db_type, is_async=...)`                                   | `sqlalchemy_atomic(db_type)`                   | 5.10.0 |
| `postgres_sqlalchemy_atomic_decorator`, `async_postgres_sqlalchemy_atomic_decorator`   | `postgres_sqlalchemy_atomic`                                          | 5.10.0 |
| `mysql_sqlalchemy_atomic_decorator`, `async_mysql_sqlalchemy_atomic_decorator`         | `mysql_sqlalchemy_atomic`                                             | 5.10.0 |
| `sqlite_sqlalchemy_atomic_decorator`, `async_sqlite_sqlalchemy_atomic_decorator`       | `sqlite_sqlalchemy_atomic`                                            | 5.10.0 |
| `starrocks_sqlalchemy_atomic_decorator`, `async_starrocks_sqlalchemy_atomic_decorator` | `starrocks_sqlalchemy_atomic`                                         | 5.10.0 |

## Error helpers

| Deprecated                                  | Replacement                                                      |
|---------------------------------------------|------------------------------------------------------------------|
| `BaseUtils.capture_exception`               | `archipy.helpers.errors.capture_exception`                       |
| `BaseUtils.async_handle_fastapi_exception`  | `archipy.helpers.errors.fastapi.handle_fastapi_exception`        |
| `BaseUtils.get_fastapi_exception_responses` | `archipy.helpers.errors.fastapi.get_fastapi_exception_responses` |

Import replacement functions directly. The `archipy.helpers.utils.error_utils` module was removed.

## Keycloak

- Import `fastapi_auth`, `grpc_auth`, `AuthContextManager`, and `clear_keycloak_remote_cache` from
  `archipy.adapters.keycloak.auth`. Replace `KeycloakUtils.async_fastapi_auth` and `KeycloakUtils.async_grpc_auth`
  with the same guard functions.
- Read `raw_user_info`, `token_info`, `actor_chain`, and `roles` from
  `AuthContextManager.get_auth_context()`. FastAPI guards no longer put those values on `request.state`.
- Pass request DTOs to the adapters. Convert existing dictionaries with the matching DTO's `model_validate()`.
  Read response DTO attributes directly, or call `model_dump(by_alias=True, exclude_none=True)` when a dictionary is
  needed.
- Import `ActorDTO` and `AuthenticatedUserDTO` from `archipy.models.dtos.keycloak`.
- Locally verified tokens must have `typ == "Bearer"` and a matching issuer. Set
  `KEYCLOAK__TOKEN_VALIDATION__EXPECTED_ISSUER` if tokens use a different URL from the one configured for the adapter.
  Set `KEYCLOAK__TOKEN_VALIDATION__EXPECTED_AUDIENCE` to validate the audience.

| Deprecated                   | Replacement                 |
|------------------------------|-----------------------------|
| `KeycloakRoleType`           | `KeycloakRoleDTO`           |
| `KeycloakGroupType`          | `KeycloakGroupDTO`          |
| `KeycloakOrganizationType`   | `KeycloakOrganizationDTO`   |
| `KeycloakClientScopeType`    | `KeycloakClientScopeDTO`    |
| `KeycloakProtocolMapperType` | `KeycloakProtocolMapperDTO` |
| `KeycloakComponentType`      | `KeycloakComponentDTO`      |

## Adapter behavior

| Removed behavior | Migration |
|------------------|-----------|
| SMTP opportunistic `auto` TLS and clear-text login | Use verified `starttls` (the default) or `implicit`. Set `EMAIL__TLS__CA_FILE` for a private CA. Use `none` only for unauthenticated SMTP. |
| SMTP certificate-verification toggle | Remove `EMAIL__TLS__VERIFY` or `EMAIL__TLS_VERIFY`. ArchiPy always verifies certificates and hostnames when using TLS. |
| Kafka implicit empty key | Omit the key to send a Kafka null key. Pass `key=""` explicitly to send an empty key. Remove `KAFKA__EMPTY_KEY_FOR_MISSING_KEY`. |
| Raw Elasticsearch API and transport errors | Catch the [ArchiPy errors](../tutorials/adapters/elasticsearch.md#error-mapping). Remove `ELASTIC__MAP_ERRORS`. |
| Redis HASH upsert `replace` argument | Remove the argument from `upsert_hash` and `upsert_hash_dto`. Both methods merge the supplied fields. |
| Temporal `stop_schedule` | Use `delete_schedule` to remove a schedule or `pause_schedule` to keep it. |
| Temporal `start_worker(build_id=...)` | Pass `deployment_config=WorkerDeploymentConfig(...)` with a `WorkerDeploymentVersion`. |
| Temporal `TLS_CERT_PARTS_REQUIRED` | Configure server TLS through `TEMPORAL.TLS`. Supply client certificate and key together when using mTLS. |
| Temporal span attribute `messaging.operation` | Read `messaging.operation.type`. |
| OpenTelemetry SDK logging handler fallback | Install the `otel` extra to get `opentelemetry-instrumentation-logging`. |
| ScyllaDB per-host pool-size fields | Remove `MAX_CONNECTIONS_PER_HOST`, `MIN_CONNECTIONS_PER_HOST`, `CORE_CONNECTIONS_PER_HOST`, and `MAX_REQUESTS_PER_CONNECTION`. The driver manages the connections. |

## Configuration

Use the paths below in Python code. For environment variables, replace each dot with a double underscore.
For example, `REDIS__SSL=true` becomes `REDIS__TLS__IS_ENABLED=true`. If you set a value under both 5.x names,
keep the value you configured under the nested name.

With `REDIS__TLS__IS_ENABLED=true` set in the environment, use the nested settings in Python:

```python
# redis_tls.py
from archipy.configs.base_config import BaseConfig

config = BaseConfig()
redis_tls_enabled = config.REDIS.TLS.IS_ENABLED
```

### AUTH

| 5.x field | 6.0 field |
|-----------|-----------|
| `AUTH.ACCESS_TOKEN_EXPIRES_IN` | `AUTH.JWT.ACCESS_TOKEN_EXPIRES_IN` |
| `AUTH.REFRESH_TOKEN_EXPIRES_IN` | `AUTH.JWT.REFRESH_TOKEN_EXPIRES_IN` |
| `AUTH.HASH_ALGORITHM` | `AUTH.JWT.ALGORITHM` |
| `AUTH.JWT_ISSUER` | `AUTH.JWT.ISSUER` |
| `AUTH.JWT_AUDIENCE` | `AUTH.JWT.AUDIENCE` |
| `AUTH.TOKEN_VERSION` | `AUTH.JWT.TOKEN_VERSION` |
| `AUTH.JWT_LEEWAY` | `AUTH.JWT.LEEWAY` |
| `AUTH.ENABLE_JTI_CLAIM` | `AUTH.JWT.ENABLE_JTI_CLAIM` |
| `AUTH.ENABLE_TOKEN_ROTATION` | `AUTH.JWT.ENABLE_TOKEN_ROTATION` |
| `AUTH.REFRESH_TOKEN_REUSE_INTERVAL` | `AUTH.JWT.REFRESH_TOKEN_REUSE_INTERVAL` |
| `AUTH.TOTP_SECRET_KEY` | `AUTH.TOTP.SECRET_KEY` |
| `AUTH.TOTP_HASH_ALGORITHM` | `AUTH.TOTP.HASH_ALGORITHM` |
| `AUTH.TOTP_LENGTH` | `AUTH.TOTP.LENGTH` |
| `AUTH.TOTP_EXPIRES_IN` | `AUTH.TOTP.EXPIRES_IN` |
| `AUTH.TOTP_TIME_STEP` | `AUTH.TOTP.TIME_STEP` |
| `AUTH.TOTP_VERIFICATION_WINDOW` | `AUTH.TOTP.VERIFICATION_WINDOW` |
| `AUTH.TOTP_MAX_ATTEMPTS` | `AUTH.TOTP.MAX_ATTEMPTS` |
| `AUTH.TOTP_LOCKOUT_TIME` | `AUTH.TOTP.LOCKOUT_TIME` |
| `AUTH.LOGIN_RATE_LIMIT` | `AUTH.RATE_LIMITS.LOGIN` |
| `AUTH.TOTP_RATE_LIMIT` | `AUTH.RATE_LIMITS.TOTP` |
| `AUTH.PASSWORD_RESET_RATE_LIMIT` | `AUTH.RATE_LIMITS.PASSWORD_RESET` |
| `AUTH.HASH_ITERATIONS` | `AUTH.PASSWORD_POLICY.HASH_ITERATIONS` |
| `AUTH.MIN_LENGTH` | `AUTH.PASSWORD_POLICY.MIN_LENGTH` |
| `AUTH.REQUIRE_DIGIT` | `AUTH.PASSWORD_POLICY.REQUIRE_DIGIT` |
| `AUTH.REQUIRE_LOWERCASE` | `AUTH.PASSWORD_POLICY.REQUIRE_LOWERCASE` |
| `AUTH.REQUIRE_SPECIAL` | `AUTH.PASSWORD_POLICY.REQUIRE_SPECIAL` |
| `AUTH.REQUIRE_UPPERCASE` | `AUTH.PASSWORD_POLICY.REQUIRE_UPPERCASE` |
| `AUTH.SALT_LENGTH` | `AUTH.PASSWORD_POLICY.SALT_LENGTH` |
| `AUTH.SPECIAL_CHARACTERS` | `AUTH.PASSWORD_POLICY.SPECIAL_CHARACTERS` |
| `AUTH.PASSWORD_HISTORY_SIZE` | `AUTH.PASSWORD_POLICY.HISTORY_SIZE` |

### ELASTIC

| 5.x field | 6.0 field |
|-----------|-----------|
| `ELASTIC.HTTP_USER_NAME` | `ELASTIC.AUTH.USER_NAME` |
| `ELASTIC.HTTP_PASSWORD` | `ELASTIC.AUTH.PASSWORD` |
| `ELASTIC.API_KEY` | `ELASTIC.AUTH.API_KEY` |
| `ELASTIC.API_SECRET` | `ELASTIC.AUTH.API_SECRET` |
| `ELASTIC.BEARER_AUTH` | `ELASTIC.AUTH.BEARER` |
| `ELASTIC.CA_CERTS` | `ELASTIC.TLS.CA_CERTS` |
| `ELASTIC.SSL_ASSERT_FINGERPRINT` | `ELASTIC.TLS.ASSERT_FINGERPRINT` |
| `ELASTIC.VERIFY_CERTS` | `ELASTIC.TLS.VERIFY_CERTS` |
| `ELASTIC.CLIENT_CERT` | `ELASTIC.TLS.CLIENT_CERT` |
| `ELASTIC.CLIENT_KEY` | `ELASTIC.TLS.CLIENT_KEY` |
| `ELASTIC.SSL_VERSION` | `ELASTIC.TLS.VERSION` |
| `ELASTIC.SSL_CONTEXT` | `ELASTIC.TLS.CONTEXT` |
| `ELASTIC.MAX_RETRIES` | `ELASTIC.RETRY.MAX_RETRIES` |
| `ELASTIC.RETRY_ON_TIMEOUT` | `ELASTIC.RETRY.ON_TIMEOUT` |
| `ELASTIC.RETRY_ON_STATUS` | `ELASTIC.RETRY.ON_STATUS` |
| `ELASTIC.RETRY_BACKOFF_BASE` | `ELASTIC.RETRY.BACKOFF_BASE` |
| `ELASTIC.RETRY_BACKOFF_CAP` | `ELASTIC.RETRY.BACKOFF_CAP` |
| `ELASTIC.SNIFF_ON_START` | `ELASTIC.SNIFFING.ON_START` |
| `ELASTIC.SNIFF_BEFORE_REQUESTS` | `ELASTIC.SNIFFING.BEFORE_REQUESTS` |
| `ELASTIC.SNIFF_ON_NODE_FAILURE` | `ELASTIC.SNIFFING.ON_NODE_FAILURE` |
| `ELASTIC.MIN_DELAY_BETWEEN_SNIFFING` | `ELASTIC.SNIFFING.MIN_DELAY` |

### EMAIL

| 5.x field | 6.0 field |
|-----------|-----------|
| `EMAIL.TLS_MODE` | `EMAIL.TLS.MODE` |
| `EMAIL.TLS_CA_FILE` | `EMAIL.TLS.CA_FILE` |
| `EMAIL.POOL_SIZE` | `EMAIL.POOL.SIZE` |
| `EMAIL.CONNECTION_TIMEOUT` | `EMAIL.POOL.CONNECTION_TIMEOUT` |
| `EMAIL.CONNECTION_REFRESH_SECONDS` | `EMAIL.POOL.CONNECTION_REFRESH_SECONDS` |
| `EMAIL.ATTACHMENT_URL_TIMEOUT` | `EMAIL.ATTACHMENTS.URL_TIMEOUT` |
| `EMAIL.ATTACHMENT_URL_ALLOWED_HOSTS` | `EMAIL.ATTACHMENTS.URL_ALLOWED_HOSTS` |
| `EMAIL.ATTACHMENT_MAX_SIZE` | `EMAIL.ATTACHMENTS.MAX_SIZE` |

### FASTAPI

| 5.x field | 6.0 field |
|-----------|-----------|
| `FASTAPI.CORS_MIDDLEWARE_ALLOW_CREDENTIALS` | `FASTAPI.CORS.ALLOW_CREDENTIALS` |
| `FASTAPI.CORS_MIDDLEWARE_ALLOW_HEADERS` | `FASTAPI.CORS.ALLOW_HEADERS` |
| `FASTAPI.CORS_MIDDLEWARE_ALLOW_METHODS` | `FASTAPI.CORS.ALLOW_METHODS` |
| `FASTAPI.CORS_MIDDLEWARE_ALLOW_ORIGIN_REGEX` | `FASTAPI.CORS.ALLOW_ORIGIN_REGEX` |
| `FASTAPI.CORS_MIDDLEWARE_ALLOW_ORIGINS` | `FASTAPI.CORS.ALLOW_ORIGINS` |
| `FASTAPI.CORS_MIDDLEWARE_EXPOSE_HEADERS` | `FASTAPI.CORS.EXPOSE_HEADERS` |
| `FASTAPI.CORS_MIDDLEWARE_MAX_AGE` | `FASTAPI.CORS.MAX_AGE` |
| `FASTAPI.GZIP_MIDDLEWARE_IS_ENABLED` | `FASTAPI.GZIP.IS_ENABLED` |
| `FASTAPI.GZIP_MIDDLEWARE_MINIMUM_SIZE` | `FASTAPI.GZIP.MINIMUM_SIZE` |
| `FASTAPI.GZIP_MIDDLEWARE_COMPRESSLEVEL` | `FASTAPI.GZIP.COMPRESSLEVEL` |
| `FASTAPI.TRUSTED_HOST_MIDDLEWARE_IS_ENABLED` | `FASTAPI.TRUSTED_HOST.IS_ENABLED` |
| `FASTAPI.TRUSTED_HOST_MIDDLEWARE_ALLOWED_HOSTS` | `FASTAPI.TRUSTED_HOST.ALLOWED_HOSTS` |
| `FASTAPI.TRUSTED_HOST_MIDDLEWARE_WWW_REDIRECT` | `FASTAPI.TRUSTED_HOST.WWW_REDIRECT` |
| `FASTAPI.HTTPS_REDIRECT_MIDDLEWARE_IS_ENABLED` | `FASTAPI.HTTPS_REDIRECT.IS_ENABLED` |
| `FASTAPI.ACCESS_LOG` | `UVICORN.ACCESS_LOG` |
| `FASTAPI.BACKLOG` | `UVICORN.LIMITS.BACKLOG` |
| `FASTAPI.DATE_HEADER` | `UVICORN.DATE_HEADER` |
| `FASTAPI.FORWARDED_ALLOW_IPS` | `UVICORN.FORWARDED_ALLOW_IPS` |
| `FASTAPI.LIMIT_CONCURRENCY` | `UVICORN.LIMITS.CONCURRENCY` |
| `FASTAPI.LIMIT_MAX_REQUESTS` | `UVICORN.LIMITS.MAX_REQUESTS` |
| `FASTAPI.PROXY_HEADERS` | `UVICORN.PROXY_HEADERS` |
| `FASTAPI.RELOAD` | `UVICORN.RELOAD` |
| `FASTAPI.SERVER_HEADER` | `UVICORN.SERVER_HEADER` |
| `FASTAPI.TIMEOUT_GRACEFUL_SHUTDOWN` | `UVICORN.TIMEOUT_GRACEFUL_SHUTDOWN` |
| `FASTAPI.TIMEOUT_KEEP_ALIVE` | `UVICORN.TIMEOUT_KEEP_ALIVE` |
| `FASTAPI.WORKERS_COUNT` | `UVICORN.WORKERS_COUNT` |
| `FASTAPI.WS_MAX_SIZE` | `UVICORN.WEBSOCKET.MAX_SIZE` |
| `FASTAPI.WS_PER_MESSAGE_DEFLATE` | `UVICORN.WEBSOCKET.PER_MESSAGE_DEFLATE` |
| `FASTAPI.WS_PING_INTERVAL` | `UVICORN.WEBSOCKET.PING_INTERVAL` |
| `FASTAPI.WS_PING_TIMEOUT` | `UVICORN.WEBSOCKET.PING_TIMEOUT` |

### GRPC

| 5.x field | 6.0 field |
|-----------|-----------|
| `GRPC.TLS_ENABLED` | `GRPC.TLS.IS_ENABLED` |
| `GRPC.TLS_CERT_FILE` | `GRPC.TLS.CERT_FILE` |
| `GRPC.TLS_KEY_FILE` | `GRPC.TLS.KEY_FILE` |
| `GRPC.TLS_CA_FILE` | `GRPC.TLS.CA_FILE` |
| `GRPC.TLS_REQUIRE_CLIENT_AUTH` | `GRPC.TLS.REQUIRE_CLIENT_AUTH` |
| `GRPC.STUB_TLS_ENABLED` | `GRPC.STUB_TLS.IS_ENABLED` |
| `GRPC.STUB_TLS_CA_FILE` | `GRPC.STUB_TLS.CA_FILE` |
| `GRPC.STUB_TLS_CERT_FILE` | `GRPC.STUB_TLS.CERT_FILE` |
| `GRPC.STUB_TLS_KEY_FILE` | `GRPC.STUB_TLS.KEY_FILE` |

### KAFKA

| 5.x field | 6.0 field |
|-----------|-----------|
| `KAFKA.SASL_MECHANISM` | `KAFKA.SASL.MECHANISM` |
| `KAFKA.USERNAME` | `KAFKA.SASL.USERNAME` |
| `KAFKA.PASSWORD` | `KAFKA.SASL.PASSWORD` |
| `KAFKA.SSL_CA_FILE` | `KAFKA.SSL.CA_FILE` |
| `KAFKA.SSL_CERT_FILE` | `KAFKA.SSL.CERT_FILE` |
| `KAFKA.SSL_KEY_FILE` | `KAFKA.SSL.KEY_FILE` |
| `KAFKA.SSL_ENDPOINT_IDENTIFICATION_ALGORITHM` | `KAFKA.SSL.ENDPOINT_IDENTIFICATION_ALGORITHM` |

### KEYCLOAK

| 5.x field | 6.0 field |
|-----------|-----------|
| `KEYCLOAK.IS_ADMIN_MODE_ENABLED` | `KEYCLOAK.ADMIN.IS_ENABLED` |
| `KEYCLOAK.ADMIN_USERNAME` | `KEYCLOAK.ADMIN.USERNAME` |
| `KEYCLOAK.ADMIN_PASSWORD` | `KEYCLOAK.ADMIN.PASSWORD` |
| `KEYCLOAK.ADMIN_REALM_NAME` | `KEYCLOAK.ADMIN.REALM_NAME` |
| `KEYCLOAK.VERIFY_SSL` | `KEYCLOAK.TLS.VERIFY_SSL` |
| `KEYCLOAK.CLIENT_CERT_FILE` | `KEYCLOAK.TLS.CLIENT_CERT_FILE` |
| `KEYCLOAK.CLIENT_KEY_FILE` | `KEYCLOAK.TLS.CLIENT_KEY_FILE` |
| `KEYCLOAK.TOKEN_LEEWAY_SECONDS` | `KEYCLOAK.TOKEN_VALIDATION.LEEWAY_SECONDS` |
| `KEYCLOAK.EXPECTED_ISSUER` | `KEYCLOAK.TOKEN_VALIDATION.EXPECTED_ISSUER` |
| `KEYCLOAK.EXPECTED_AUDIENCE` | `KEYCLOAK.TOKEN_VALIDATION.EXPECTED_AUDIENCE` |
| `KEYCLOAK.REQUIRE_ORGANIZATION` | `KEYCLOAK.TOKEN_VALIDATION.REQUIRE_ORGANIZATION` |

### OTEL

| 5.x field | 6.0 field |
|-----------|-----------|
| `OTEL.METRICS_PUSHGATEWAY_URL` | `OTEL.PUSHGATEWAY.URL` |
| `OTEL.METRICS_PUSHGATEWAY_JOB` | `OTEL.PUSHGATEWAY.JOB` |
| `OTEL.METRICS_PUSHGATEWAY_INTERVAL_SECONDS` | `OTEL.PUSHGATEWAY.INTERVAL_SECONDS` |
| `OTEL.METRICS_PUSHGATEWAY_TIMEOUT_SECONDS` | `OTEL.PUSHGATEWAY.TIMEOUT_SECONDS` |
| `OTEL.METRICS_PUSHGATEWAY_GROUPING_KEY` | `OTEL.PUSHGATEWAY.GROUPING_KEY` |
| `OTEL.METRICS_PUSHGATEWAY_DELETE_ON_SHUTDOWN` | `OTEL.PUSHGATEWAY.DELETE_ON_SHUTDOWN` |

### REDIS

| 5.x field | 6.0 field |
|-----------|-----------|
| `REDIS.CLUSTER_NODES` | `REDIS.CLUSTER.NODES` |
| `REDIS.CLUSTER_REQUIRE_FULL_COVERAGE` | `REDIS.CLUSTER.REQUIRE_FULL_COVERAGE` |
| `REDIS.CLUSTER_READ_FROM_REPLICAS` | `REDIS.CLUSTER.READ_FROM_REPLICAS` |
| `REDIS.SENTINEL_NODES` | `REDIS.SENTINEL.NODES` |
| `REDIS.SENTINEL_SERVICE_NAME` | `REDIS.SENTINEL.SERVICE_NAME` |
| `REDIS.SENTINEL_SOCKET_TIMEOUT` | `REDIS.SENTINEL.SOCKET_TIMEOUT` |
| `REDIS.SENTINEL_PASSWORD` | `REDIS.SENTINEL.PASSWORD` |
| `REDIS.SENTINEL_USERNAME` | `REDIS.SENTINEL.USERNAME` |
| `REDIS.SSL` | `REDIS.TLS.IS_ENABLED` |
| `REDIS.SSL_CA_CERTS` | `REDIS.TLS.CA_CERTS` |
| `REDIS.SSL_CERTFILE` | `REDIS.TLS.CERTFILE` |
| `REDIS.SSL_KEYFILE` | `REDIS.TLS.KEYFILE` |
| `REDIS.SSL_CHECK_HOSTNAME` | `REDIS.TLS.CHECK_HOSTNAME` |
| `REDIS.RETRY_ATTEMPTS` | `REDIS.RETRY.ATTEMPTS` |
| `REDIS.RETRY_BACKOFF_BASE` | `REDIS.RETRY.BACKOFF_BASE` |
| `REDIS.RETRY_BACKOFF_CAP` | `REDIS.RETRY.BACKOFF_CAP` |
| `REDIS.RETRY_ON_TIMEOUT` | `REDIS.RETRY.ON_TIMEOUT` |

### SCYLLADB

| 5.x field | 6.0 field |
|-----------|-----------|
| `SCYLLADB.TLS_ENABLED` | `SCYLLADB.TLS.IS_ENABLED` |
| `SCYLLADB.TLS_CA_FILE` | `SCYLLADB.TLS.CA_FILE` |
| `SCYLLADB.TLS_CERT_FILE` | `SCYLLADB.TLS.CERT_FILE` |
| `SCYLLADB.TLS_KEY_FILE` | `SCYLLADB.TLS.KEY_FILE` |
| `SCYLLADB.TLS_VERIFY_MODE` | `SCYLLADB.TLS.VERIFY_MODE` |
| `SCYLLADB.TLS_CHECK_HOSTNAME` | `SCYLLADB.TLS.CHECK_HOSTNAME` |
| `SCYLLADB.TLS_SERVER_NAME` | `SCYLLADB.TLS.SERVER_NAME` |
| `SCYLLADB.TLS_SESSION_CACHE_ENABLED` | `SCYLLADB.TLS.SESSION_CACHE_ENABLED` |
| `SCYLLADB.RETRY_POLICY` | `SCYLLADB.RETRY.POLICY` |
| `SCYLLADB.RETRY_MAX_NUM_RETRIES` | `SCYLLADB.RETRY.MAX_NUM_RETRIES` |
| `SCYLLADB.RETRY_MIN_INTERVAL` | `SCYLLADB.RETRY.MIN_INTERVAL` |
| `SCYLLADB.RETRY_MAX_INTERVAL` | `SCYLLADB.RETRY.MAX_INTERVAL` |
| `SCYLLADB.RECONNECTION_POLICY` | `SCYLLADB.RECONNECTION.POLICY` |
| `SCYLLADB.RECONNECTION_BASE_DELAY` | `SCYLLADB.RECONNECTION.BASE_DELAY` |
| `SCYLLADB.RECONNECTION_MAX_DELAY` | `SCYLLADB.RECONNECTION.MAX_DELAY` |
| `SCYLLADB.RECONNECTION_MAX_ATTEMPTS` | `SCYLLADB.RECONNECTION.MAX_ATTEMPTS` |
| `SCYLLADB.SPECULATIVE_EXECUTION_DELAY` | `SCYLLADB.SPECULATIVE_EXECUTION.DELAY` |
| `SCYLLADB.SPECULATIVE_EXECUTION_MAX_ATTEMPTS` | `SCYLLADB.SPECULATIVE_EXECUTION.MAX_ATTEMPTS` |
| `SCYLLADB.ENABLE_PREPARED_STATEMENT_CACHE` | `SCYLLADB.PREPARED_CACHE.IS_ENABLED` |
| `SCYLLADB.PREPARED_STATEMENT_CACHE_SIZE` | `SCYLLADB.PREPARED_CACHE.SIZE` |
| `SCYLLADB.PREPARED_STATEMENT_CACHE_TTL_SECONDS` | `SCYLLADB.PREPARED_CACHE.TTL_SECONDS` |
| `SCYLLADB.IDLE_HEARTBEAT_INTERVAL` | `SCYLLADB.HEARTBEAT.IDLE_INTERVAL` |
| `SCYLLADB.IDLE_HEARTBEAT_TIMEOUT` | `SCYLLADB.HEARTBEAT.IDLE_TIMEOUT` |
| `SCYLLADB.REPLICATION_STRATEGY` | `SCYLLADB.REPLICATION.STRATEGY` |
| `SCYLLADB.REPLICATION_CONFIG` | `SCYLLADB.REPLICATION.CONFIG` |

### SQLALCHEMY

The same groups apply in `MYSQL_SQLALCHEMY`, `POSTGRES_SQLALCHEMY`, `SQLITE_SQLALCHEMY`, and
`STARROCKS_SQLALCHEMY`.

| 5.x field | 6.0 field |
|-----------|-----------|
| `SQLALCHEMY.POOL_MAX_OVERFLOW` | `SQLALCHEMY.POOL.MAX_OVERFLOW` |
| `SQLALCHEMY.POOL_PRE_PING` | `SQLALCHEMY.POOL.PRE_PING` |
| `SQLALCHEMY.POOL_RECYCLE_SECONDS` | `SQLALCHEMY.POOL.RECYCLE_SECONDS` |
| `SQLALCHEMY.POOL_RESET_ON_RETURN` | `SQLALCHEMY.POOL.RESET_ON_RETURN` |
| `SQLALCHEMY.POOL_SIZE` | `SQLALCHEMY.POOL.SIZE` |
| `SQLALCHEMY.POOL_TIMEOUT` | `SQLALCHEMY.POOL.TIMEOUT` |
| `SQLALCHEMY.POOL_USE_LIFO` | `SQLALCHEMY.POOL.USE_LIFO` |
| `SQLALCHEMY.COUNT_CACHE_ENABLED` | `SQLALCHEMY.COUNT_CACHE.IS_ENABLED` |
| `SQLALCHEMY.COUNT_CACHE_MAX_SIZE` | `SQLALCHEMY.COUNT_CACHE.MAX_SIZE` |
| `SQLALCHEMY.COUNT_CACHE_TTL_SECONDS` | `SQLALCHEMY.COUNT_CACHE.TTL_SECONDS` |

### TEMPORAL

| 5.x field | 6.0 field |
|-----------|-----------|
| `TEMPORAL.TLS_ENABLED` | `TEMPORAL.TLS.IS_ENABLED` |
| `TEMPORAL.TLS_CA_CERT` | `TEMPORAL.TLS.CA_CERT` |
| `TEMPORAL.TLS_CLIENT_CERT` | `TEMPORAL.TLS.CLIENT_CERT` |
| `TEMPORAL.TLS_CLIENT_KEY` | `TEMPORAL.TLS.CLIENT_KEY` |
| `TEMPORAL.TLS_SERVER_NAME` | `TEMPORAL.TLS.SERVER_NAME` |
| `TEMPORAL.TLS_VERIFICATION_SERVER_NAME` | `TEMPORAL.TLS.VERIFICATION_SERVER_NAME` |
| `TEMPORAL.WORKER_GRACEFUL_SHUTDOWN_SECONDS` | `TEMPORAL.WORKER.GRACEFUL_SHUTDOWN_SECONDS` |
| `TEMPORAL.WORKER_MAX_CACHED_WORKFLOWS` | `TEMPORAL.WORKER.MAX_CACHED_WORKFLOWS` |
| `TEMPORAL.WORKER_DEBUG_MODE` | `TEMPORAL.WORKER.DEBUG_MODE` |
| `TEMPORAL.WORKER_MAX_CONCURRENT_LOCAL_ACTIVITIES` | `TEMPORAL.WORKER.MAX_CONCURRENT_LOCAL_ACTIVITIES` |
| `TEMPORAL.WORKER_DISABLE_EAGER_ACTIVITY_EXECUTION` | `TEMPORAL.WORKER.DISABLE_EAGER_ACTIVITY_EXECUTION` |
| `TEMPORAL.WORKER_MAX_EAGER_ACTIVITY_RESERVATIONS` | `TEMPORAL.WORKER.MAX_EAGER_ACTIVITY_RESERVATIONS` |
| `TEMPORAL.WORKER_POLLER_AUTOSCALING` | `TEMPORAL.WORKER.POLLER_AUTOSCALING` |
| `TEMPORAL.WORKER_MAX_ACTIVITIES_PER_SECOND` | `TEMPORAL.WORKER.MAX_ACTIVITIES_PER_SECOND` |
| `TEMPORAL.WORKER_MAX_TASK_QUEUE_ACTIVITIES_PER_SECOND` | `TEMPORAL.WORKER.MAX_TASK_QUEUE_ACTIVITIES_PER_SECOND` |
| `TEMPORAL.CLIENT_RPC_RETRY_MAX_RETRIES` | `TEMPORAL.CLIENT_RETRY.MAX_RETRIES` |
| `TEMPORAL.CLIENT_RPC_RETRY_INITIAL_INTERVAL_MS` | `TEMPORAL.CLIENT_RETRY.INITIAL_INTERVAL_MS` |
| `TEMPORAL.CLIENT_RPC_RETRY_MAX_INTERVAL_MS` | `TEMPORAL.CLIENT_RETRY.MAX_INTERVAL_MS` |
| `TEMPORAL.KEEP_ALIVE_INTERVAL_MS` | `TEMPORAL.KEEP_ALIVE.INTERVAL_MS` |
| `TEMPORAL.KEEP_ALIVE_TIMEOUT_MS` | `TEMPORAL.KEEP_ALIVE.TIMEOUT_MS` |
| `TEMPORAL.WORKFLOW_EXECUTION_TIMEOUT` | `TEMPORAL.WORKFLOW.EXECUTION_TIMEOUT` |
| `TEMPORAL.WORKFLOW_RUN_TIMEOUT` | `TEMPORAL.WORKFLOW.RUN_TIMEOUT` |
| `TEMPORAL.WORKFLOW_TASK_TIMEOUT` | `TEMPORAL.WORKFLOW.TASK_TIMEOUT` |
| `TEMPORAL.WORKFLOW_RETRY_ENABLED` | `TEMPORAL.WORKFLOW.RETRY_ENABLED` |
| `TEMPORAL.ACTIVITY_START_TO_CLOSE_TIMEOUT` | `TEMPORAL.ACTIVITY.START_TO_CLOSE_TIMEOUT` |
| `TEMPORAL.ACTIVITY_HEARTBEAT_TIMEOUT` | `TEMPORAL.ACTIVITY.HEARTBEAT_TIMEOUT` |
| `TEMPORAL.RETRY_MAXIMUM_ATTEMPTS` | `TEMPORAL.RETRY.MAXIMUM_ATTEMPTS` |
| `TEMPORAL.RETRY_BACKOFF_COEFFICIENT` | `TEMPORAL.RETRY.BACKOFF_COEFFICIENT` |
| `TEMPORAL.RETRY_MAXIMUM_INTERVAL` | `TEMPORAL.RETRY.MAXIMUM_INTERVAL` |
| `TEMPORAL.RETRY_INITIAL_INTERVAL` | `TEMPORAL.RETRY.INITIAL_INTERVAL` |
| `TEMPORAL.RETRY_NON_RETRYABLE_ERROR_TYPES` | `TEMPORAL.RETRY.NON_RETRYABLE_ERROR_TYPES` |

### UVICORN

| 5.x field | 6.0 field |
|-----------|-----------|
| `UVICORN.SSL_KEYFILE` | `UVICORN.TLS.KEYFILE` |
| `UVICORN.SSL_CERTFILE` | `UVICORN.TLS.CERTFILE` |
| `UVICORN.SSL_CA_CERTS` | `UVICORN.TLS.CA_CERTS` |
| `UVICORN.WS_MAX_SIZE` | `UVICORN.WEBSOCKET.MAX_SIZE` |
| `UVICORN.WS_PER_MESSAGE_DEFLATE` | `UVICORN.WEBSOCKET.PER_MESSAGE_DEFLATE` |
| `UVICORN.WS_PING_INTERVAL` | `UVICORN.WEBSOCKET.PING_INTERVAL` |
| `UVICORN.WS_PING_TIMEOUT` | `UVICORN.WEBSOCKET.PING_TIMEOUT` |
| `UVICORN.BACKLOG` | `UVICORN.LIMITS.BACKLOG` |
| `UVICORN.LIMIT_CONCURRENCY` | `UVICORN.LIMITS.CONCURRENCY` |
| `UVICORN.LIMIT_MAX_REQUESTS` | `UVICORN.LIMITS.MAX_REQUESTS` |

### VAULT

| 5.x field | 6.0 field |
|-----------|-----------|
| `VAULT.APPROLE_ROLE_ID` | `VAULT.APPROLE.ROLE_ID` |
| `VAULT.APPROLE_SECRET_ID` | `VAULT.APPROLE.SECRET_ID` |
| `VAULT.APPROLE_SECRET_ID_FILE` | `VAULT.APPROLE.SECRET_ID_FILE` |
| `VAULT.APPROLE_MOUNT_POINT` | `VAULT.APPROLE.MOUNT_POINT` |
| `VAULT.KUBERNETES_ROLE` | `VAULT.KUBERNETES.ROLE` |
| `VAULT.KUBERNETES_JWT_PATH` | `VAULT.KUBERNETES.JWT_PATH` |
| `VAULT.KUBERNETES_MOUNT_POINT` | `VAULT.KUBERNETES.MOUNT_POINT` |
| `VAULT.USERPASS_MOUNT_POINT` | `VAULT.USERPASS.MOUNT_POINT` |
| `VAULT.LDAP_MOUNT_POINT` | `VAULT.LDAP.MOUNT_POINT` |
| `VAULT.OKTA_MOUNT_POINT` | `VAULT.OKTA.MOUNT_POINT` |
| `VAULT.JWT_ROLE` | `VAULT.JWT_AUTH.ROLE` |
| `VAULT.JWT` | `VAULT.JWT_AUTH.JWT` |
| `VAULT.JWT_FILE` | `VAULT.JWT_AUTH.JWT_FILE` |
| `VAULT.JWT_MOUNT_POINT` | `VAULT.JWT_AUTH.MOUNT_POINT` |
| `VAULT.AWS_ACCESS_KEY` | `VAULT.AWS.ACCESS_KEY` |
| `VAULT.AWS_SECRET_KEY` | `VAULT.AWS.SECRET_KEY` |
| `VAULT.AWS_SESSION_TOKEN` | `VAULT.AWS.SESSION_TOKEN` |
| `VAULT.AWS_ROLE` | `VAULT.AWS.ROLE` |
| `VAULT.AWS_REGION` | `VAULT.AWS.REGION` |
| `VAULT.AWS_MOUNT_POINT` | `VAULT.AWS.MOUNT_POINT` |
| `VAULT.AZURE_ROLE` | `VAULT.AZURE.ROLE` |
| `VAULT.AZURE_JWT` | `VAULT.AZURE.JWT` |
| `VAULT.AZURE_JWT_FILE` | `VAULT.AZURE.JWT_FILE` |
| `VAULT.AZURE_SUBSCRIPTION_ID` | `VAULT.AZURE.SUBSCRIPTION_ID` |
| `VAULT.AZURE_RESOURCE_GROUP_NAME` | `VAULT.AZURE.RESOURCE_GROUP_NAME` |
| `VAULT.AZURE_VM_NAME` | `VAULT.AZURE.VM_NAME` |
| `VAULT.AZURE_VMSS_NAME` | `VAULT.AZURE.VMSS_NAME` |
| `VAULT.AZURE_MOUNT_POINT` | `VAULT.AZURE.MOUNT_POINT` |
| `VAULT.GCP_ROLE` | `VAULT.GCP.ROLE` |
| `VAULT.GCP_JWT` | `VAULT.GCP.JWT` |
| `VAULT.GCP_JWT_FILE` | `VAULT.GCP.JWT_FILE` |
| `VAULT.GCP_MOUNT_POINT` | `VAULT.GCP.MOUNT_POINT` |
| `VAULT.GITHUB_TOKEN` | `VAULT.GITHUB.TOKEN` |
| `VAULT.GITHUB_TOKEN_FILE` | `VAULT.GITHUB.TOKEN_FILE` |
| `VAULT.GITHUB_MOUNT_POINT` | `VAULT.GITHUB.MOUNT_POINT` |
| `VAULT.CERT_NAME` | `VAULT.CERT.NAME` |
| `VAULT.CERT_MOUNT_POINT` | `VAULT.CERT.MOUNT_POINT` |
| `VAULT.VERIFY_SSL` | `VAULT.TLS.VERIFY_SSL` |
| `VAULT.CA_CERT_PATH` | `VAULT.TLS.CA_CERT_PATH` |
| `VAULT.CLIENT_CERT_PATH` | `VAULT.TLS.CLIENT_CERT_PATH` |
| `VAULT.CLIENT_KEY_PATH` | `VAULT.TLS.CLIENT_KEY_PATH` |
| `VAULT.CONNECT_TIMEOUT` | `VAULT.HTTP.CONNECT_TIMEOUT` |
| `VAULT.READ_TIMEOUT` | `VAULT.HTTP.READ_TIMEOUT` |
| `VAULT.RETRIES_MAX_ATTEMPTS` | `VAULT.HTTP.RETRIES_MAX_ATTEMPTS` |
| `VAULT.AUTO_RENEW_TOKEN` | `VAULT.TOKEN_RENEWAL.AUTO_RENEW_TOKEN` |
| `VAULT.RENEW_THRESHOLD_SECONDS` | `VAULT.TOKEN_RENEWAL.RENEW_THRESHOLD_SECONDS` |
