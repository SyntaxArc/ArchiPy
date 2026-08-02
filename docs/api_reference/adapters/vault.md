---
title: Vault
description: API reference for the HashiCorp Vault adapter ports and adapters.
---

# Vault

The `vault` adapter provides integration with HashiCorp Vault for KV v2 secrets, dynamic
credential leases, and transit encryption.

## Ports

Abstract port interface defining the Vault adapter contract.

::: archipy.adapters.vault.ports
options:
show_root_toc_entry: false
heading_level: 3

## Adapters

Concrete Vault adapter wrapping **hvac** with ArchiPy conventions.

::: archipy.adapters.vault.adapters
options:
show_root_toc_entry: false
heading_level: 3
