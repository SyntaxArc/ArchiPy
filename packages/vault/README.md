# archipy-vault

HashiCorp Vault adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): secrets and dynamic leases.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[vault]"
```

## Usage

```python
from archipy.adapters.vault.adapters import VaultAdapter

adapter = VaultAdapter()
```

The adapter reads its settings from the `VAULT` section of the global config, for example `VAULT__<FIELD>` environment variables.

Classes in `archipy.adapters.vault.adapters`: `VaultAdapter`.

See the [HashiCorp Vault tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/vault/) for the full API.
