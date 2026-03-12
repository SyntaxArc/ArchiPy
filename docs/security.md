---
title: Security Policy
description: Vulnerability reporting process, supported versions, and security hardening checklist for ArchiPy.
---

# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in ArchiPy, **please do not open a public GitHub issue**. Instead, report
it privately so the maintainers can triage and patch it before public disclosure.

**How to report:**

1. Email the maintainers at the address listed in `pyproject.toml` under `[project.authors]`, or
2. Use GitHub's [private vulnerability reporting](https://github.com/SyntaxArc/ArchiPy/security/advisories/new)
   feature (Settings → Security → Advisories → New advisory).

Include as much detail as possible:

- A description of the vulnerability and its potential impact
- Steps to reproduce, including a minimal code example if possible
- The ArchiPy version(s) affected
- Any suggested mitigations you are aware of

You will receive an acknowledgment within **48 hours** and a status update within **7 days**.

!!! warning "Coordinated Disclosure"
Please allow the maintainers reasonable time (typically 90 days) to prepare and release a fix before
disclosing the vulnerability publicly.

---

## Supported Versions

Only the latest released version of ArchiPy receives security patches. Older versions are not actively
maintained.

| Version | Supported |
|---------|-----------|
| Latest  | Yes       |
| Older   | No        |

If you are running an older version, upgrade to the latest release to receive security fixes:

```bash
uv add archipy --upgrade
```

---

## Security Hardening Checklist

Follow these practices when building applications with ArchiPy.

### Configuration & Secrets

- [ ] **Never hardcode secrets** — use environment variables or a secrets manager.
- [ ] **Add `.env` to `.gitignore`** — commit only `.env.example` with placeholder values.
- [ ] **Use `pydantic-settings` validators** to reject missing or malformed secrets at startup (fail fast).
- [ ] **Rotate credentials regularly** — Redis passwords, database URLs, JWT secrets.
- [ ] **Set `SECRET_KEY` to a cryptographically random value** (at least 32 bytes):

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### JWT Utilities

- [ ] **Use short expiry times** — access tokens should expire in minutes, not hours.
- [ ] **Use asymmetric keys (RS256)** for tokens consumed by third parties.
- [ ] **Validate `aud` and `iss` claims** to prevent token reuse across services.
- [ ] **Never log full JWT tokens** — log only the token ID (`jti`) if needed.

```python
from archipy.helpers.utils.jwt_utils import JWTUtils

# Always specify algorithm and expiry explicitly
token = JWTUtils.encode(
    payload={"sub": user_id, "jti": str(uuid4())},
    expiry_minutes=15,
)
```

### Database Adapters

- [ ] **Use least-privilege database users** — application users should not have `DROP` or `CREATE` rights.
- [ ] **Enable SSL/TLS** for all database connections in production.
- [ ] **Never interpolate user input directly into SQL** — use parameterized queries (SQLAlchemy does this by
  default).
- [ ] **Use connection pooling limits** to prevent connection exhaustion attacks.

### Redis Adapter

- [ ] **Enable Redis `requirepass`** in production.
- [ ] **Restrict Redis to localhost** or a private network; never expose port 6379 publicly.
- [ ] **Set `maxmemory` and an eviction policy** to prevent unbounded memory growth.
- [ ] **Use TLS** (`rediss://`) for Redis connections in production.

### Keycloak Adapter

- [ ] **Verify the token signature** using the Keycloak public key — do not skip signature validation.
- [ ] **Use PKCE** for public clients (e.g., SPAs).
- [ ] **Restrict redirect URIs** in the Keycloak client configuration.
- [ ] **Set short session timeouts** and enforce re-authentication for sensitive actions.

### Password Utilities

- [ ] **Always hash passwords** using `PasswordUtils` before storage — never store plaintext.
- [ ] **Use a high cost factor** (bcrypt rounds ≥ 12) for production workloads.

```python
from archipy.helpers.utils.password_utils import PasswordUtils

hashed = PasswordUtils.hash_password(plain_password)
is_valid = PasswordUtils.verify_password(plain_password, hashed)
```

### Kafka Adapter

- [ ] **Enable SASL/SSL** authentication for Kafka brokers in production.
- [ ] **Validate message schemas** before processing — do not trust incoming payloads blindly.
- [ ] **Use separate topics per environment** to prevent cross-environment message leakage.

### MinIO Adapter

- [ ] **Use IAM policies** to restrict bucket and object access per service.
- [ ] **Enable server-side encryption** for buckets containing sensitive data.
- [ ] **Disable public bucket access** unless explicitly required.
- [ ] **Set pre-signed URL expiry** to the minimum required duration.

### Logging & Observability

- [ ] **Do not log sensitive data** — passwords, tokens, credit card numbers, PII.
- [ ] **Use structured logging** (`logging` module with JSON formatters) to ease log analysis.
- [ ] **Redact secrets** in exception messages before they reach error trackers (Sentry, Elastic APM).

### Dependency Management

- [ ] **Pin dependency versions** with `uv lock` and commit `uv.lock` to version control.
- [ ] **Run `uv audit`** regularly to check for known vulnerabilities in dependencies.
- [ ] **Update dependencies** with `make update` and review the diff before merging.

---

## See Also

- [Configuration Management](examples/config_management.md) — environment variables and secrets management
- [JWT Utilities](examples/helpers/utils.md) — encoding and decoding JSON Web Tokens
- [Installation](installation.md) — optional extras and dependencies
- [Contributing](contributing.md) — responsible disclosure and code review process
