# archipy-keycloak

Keycloak adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): authentication, authorization and realm administration.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[keycloak]"
```

## Usage

```python
from archipy.adapters.keycloak.adapters import KeycloakAdapter

adapter = KeycloakAdapter()
```

The adapter reads its settings from the `KEYCLOAK` section of the global config, for example `KEYCLOAK__<FIELD>` environment variables.

Classes in `archipy.adapters.keycloak.adapters`: `KeycloakAdapter`, `AsyncKeycloakAdapter`.

See the [Keycloak tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/keycloak/) for the full API.
