---
title: Deprecations
description: Every deprecated ArchiPy import path, name and behavior, with its replacement and removal version.
---

# Deprecations

ArchiPy does not break a public path in a minor release. A moved or renamed name keeps working and emits a
`DeprecationWarning` that names its replacement. Every name on this page is removed in **6.0.0**.

To find the calls in your code, turn the warning into an error:

```bash
uv run python -W error::DeprecationWarning -m your_app
```

## Decorators

Decorators dropped the `_decorator` suffix and detect `async def` functions themselves, so the `async_*` variants
are no longer needed. Import everything from `archipy.helpers.decorators`. Deprecated since 5.10.0.

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

The warning is raised when the deprecated function is called. For a decorator factory that is when the decorator is
applied.

### Deprecated decorator modules

The old submodule paths still export the old names. The implementations moved to modules whose names do not clash
with the new function names. Deprecated since 5.10.0.

| Deprecated import path                       | Replacement                                           |
|----------------------------------------------|-------------------------------------------------------|
| `archipy.helpers.decorators.retry`           | `from archipy.helpers.decorators import retry`        |
| `archipy.helpers.decorators.timeout`         | `from archipy.helpers.decorators import timeout`      |
| `archipy.helpers.decorators.timing`          | `from archipy.helpers.decorators import timing`       |
| `archipy.helpers.decorators.singleton`       | `from archipy.helpers.decorators import singleton`    |
| `archipy.helpers.decorators.cache`           | `from archipy.helpers.decorators import ttl_cache`    |
| `archipy.helpers.decorators.grpc_rate_limit` | `from archipy.helpers.decorators import grpc_rate_limit` |
| `archipy.helpers.decorators.sqlalchemy_atomic` | `archipy.adapters.base.sqlalchemy.atomic`           |

The package exposes the decorator under the same name as the old module, so import the function from
`archipy.helpers.decorators` and not from the submodule. The implementations live in the internal modules
`retry_policy.py`, `timeout_limit.py`, `timing_log.py`, `singleton_class.py`, `ttl_caching.py`,
`grpc_rate_limit_window.py` and `sqlalchemy_transaction.py`.

## SQLAlchemy atomic decorators

The atomic decorators moved to the adapters layer, `archipy.adapters.base.sqlalchemy.atomic`.

| Deprecated                                                                             | Replacement                                                           | Since  |
|----------------------------------------------------------------------------------------|-----------------------------------------------------------------------|--------|
| `archipy.helpers.decorators.sqlalchemy_atomic`                                         | `archipy.adapters.base.sqlalchemy.atomic.sqlalchemy_atomic`           | 5.16.0 |
| `archipy.helpers.decorators.postgres_sqlalchemy_atomic`                                | `archipy.adapters.base.sqlalchemy.atomic.postgres_sqlalchemy_atomic`  | 5.16.0 |
| `archipy.helpers.decorators.mysql_sqlalchemy_atomic`                                   | `archipy.adapters.base.sqlalchemy.atomic.mysql_sqlalchemy_atomic`     | 5.16.0 |
| `archipy.helpers.decorators.sqlite_sqlalchemy_atomic`                                  | `archipy.adapters.base.sqlalchemy.atomic.sqlite_sqlalchemy_atomic`    | 5.16.0 |
| `archipy.helpers.decorators.starrocks_sqlalchemy_atomic`                               | `archipy.adapters.base.sqlalchemy.atomic.starrocks_sqlalchemy_atomic` | 5.16.0 |
| `sqlalchemy_atomic_decorator(db_type, is_async=...)`                                   | `sqlalchemy_atomic(db_type)`; `is_async` is ignored                   | 5.10.0 |
| `postgres_sqlalchemy_atomic_decorator`, `async_postgres_sqlalchemy_atomic_decorator`   | `postgres_sqlalchemy_atomic`                                          | 5.10.0 |
| `mysql_sqlalchemy_atomic_decorator`, `async_mysql_sqlalchemy_atomic_decorator`         | `mysql_sqlalchemy_atomic`                                             | 5.10.0 |
| `sqlite_sqlalchemy_atomic_decorator`, `async_sqlite_sqlalchemy_atomic_decorator`       | `sqlite_sqlalchemy_atomic`                                            | 5.10.0 |
| `starrocks_sqlalchemy_atomic_decorator`, `async_starrocks_sqlalchemy_atomic_decorator` | `starrocks_sqlalchemy_atomic`                                         | 5.10.0 |

The `*_decorator` and `async_*` names warn about their own replacement.

## Utilities and error handling

Deprecated since 5.15.0. Each method emits a `DeprecationWarning` and returns the same result as its replacement.

| Deprecated                                  | Replacement                                                      |
|---------------------------------------------|------------------------------------------------------------------|
| `BaseUtils.capture_exception`               | `archipy.helpers.errors.capture_exception`                       |
| `BaseUtils.async_handle_fastapi_exception`  | `archipy.helpers.errors.fastapi.handle_fastapi_exception`        |
| `BaseUtils.get_fastapi_exception_responses` | `archipy.helpers.errors.fastapi.get_fastapi_exception_responses` |

## Keycloak

| Deprecated                                                                       | Replacement                                       | Since  | Notes                                                                                      |
|----------------------------------------------------------------------------------|---------------------------------------------------|--------|--------------------------------------------------------------------------------------------|
| `archipy.helpers.utils.keycloak_utils` module                                    | `archipy.adapters.keycloak.auth`                  | 5.16.0 | `AuthContextManager` and `clear_keycloak_remote_cache` warn when read from the old module. |
| `KeycloakUtils` class                                                            | The functions of `archipy.adapters.keycloak.auth` | 5.16.0 | `fastapi_auth` and `grpc_auth` are plain functions of the new module.                      |
| `KeycloakUtils.async_fastapi_auth`, `KeycloakUtils.async_grpc_auth`              | `fastapi_auth`, `grpc_auth`                       | 5.16.0 | `fastapi_auth` is always async and serves both endpoint kinds.                             |
| Reading `request.state.user_info`, `token_info`, `actor_chain`, `user_roles`     | `AuthContextManager.get_auth_context()`           | 5.16.0 | Read `raw_user_info`, `token_info`, `actor_chain` and `roles` of the auth context.         |
| Dict-style access on Keycloak response DTOs (`result["id"]`, `result.get("id")`) | Attribute access (`result.id`)                    | 5.21.0 | Applies to the DTOs that replaced dict return values.                                      |
| Passing a plain `dict` as a Keycloak request payload                             | A `Keycloak*RequestDTO`                           | 5.21.0 | The dict is passed through unchanged until removal.                                        |

### Keycloak type aliases

These aliases point at the pydantic DTOs that replaced the old TypedDicts. They emit no warning at runtime. Deprecated
since 5.21.0.

| Deprecated                   | Replacement                 |
|------------------------------|-----------------------------|
| `KeycloakRoleType`           | `KeycloakRoleDTO`           |
| `KeycloakGroupType`          | `KeycloakGroupDTO`          |
| `KeycloakOrganizationType`   | `KeycloakOrganizationDTO`   |
| `KeycloakClientScopeType`    | `KeycloakClientScopeDTO`    |
| `KeycloakProtocolMapperType` | `KeycloakProtocolMapperDTO` |
| `KeycloakComponentType`      | `KeycloakComponentDTO`      |

## Adding a deprecation

Keep the old name working and route it through `archipy.helpers._deprecation`:

- `warn_deprecated_name(old_name, new_name)` emits the warning from inside a function.
- `deprecated_alias(old_name, replacement)` returns a wrapper that warns and then calls the replacement.

Both put `REMOVAL_VERSION` in the message. Add each new deprecation to this page and to the `Deprecated` section of the
release changelog.

## See Also

- [Changelog](changelog/index.md) - Release notes, including the `Deprecated` section of each release
- [Decorators](../tutorials/helpers/decorators.md#deprecated-names) - Decorator usage and the deprecated names
- [FAQ](faq.md) - Answers to common questions
- [Contributing](contributing.md) - How to propose and land changes
