# Temporal

The `temporal` adapter provides integration with Temporal, a durable workflow orchestration platform, including workflow and activity definitions, worker management, and runtime configuration.

## ports

Abstract port interface defining the Temporal adapter contract.

::: archipy.adapters.temporal.ports
    options:
      show_root_heading: true
      show_source: true

## base

Base classes for Temporal workflow and activity implementations.

::: archipy.adapters.temporal.base
    options:
      show_root_heading: true
      show_source: true

## adapters

Concrete Temporal adapter implementing workflow and activity client operations.

::: archipy.adapters.temporal.adapters
    options:
      show_root_heading: true
      show_source: true

## runtime

Temporal runtime configuration and initialization utilities.

::: archipy.adapters.temporal.runtime
    options:
      show_root_heading: true
      show_source: true

## worker

Temporal worker setup for executing workflows and activities.

::: archipy.adapters.temporal.worker
    options:
      show_root_heading: true
      show_source: true
