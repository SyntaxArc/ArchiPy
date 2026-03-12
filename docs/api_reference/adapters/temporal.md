---
title: Temporal
description: API reference for the Temporal adapter ports, base, adapters, runtime, and worker.
---

# Temporal

The `temporal` adapter provides integration with Temporal, a durable workflow orchestration platform, including workflow and activity definitions, worker management, and runtime configuration.

## Ports

Abstract port interface defining the Temporal adapter contract.

::: archipy.adapters.temporal.ports
    options:
      show_root_toc_entry: false
      heading_level: 3

## Base

Base classes for Temporal workflow and activity implementations.

::: archipy.adapters.temporal.base
    options:
      show_root_toc_entry: false
      heading_level: 3

## Adapters

Concrete Temporal adapter implementing workflow and activity client operations.

::: archipy.adapters.temporal.adapters
    options:
      show_root_toc_entry: false
      heading_level: 3

## Runtime

Temporal runtime configuration and initialization utilities.

::: archipy.adapters.temporal.runtime
    options:
      show_root_toc_entry: false
      heading_level: 3

## Worker

Temporal worker setup for executing workflows and activities.

::: archipy.adapters.temporal.worker
    options:
      show_root_toc_entry: false
      heading_level: 3
