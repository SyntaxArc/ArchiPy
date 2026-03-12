---
title: Kafka
description: API reference for the Kafka adapter ports, adapters, and mocks.
---

# Kafka

The `kafka` adapter provides integration with Apache Kafka for producing and consuming messages in event-driven architectures.

## Ports

Abstract port interface defining the Kafka adapter contract for message production and consumption.

::: archipy.adapters.kafka.ports
    options:
      show_root_toc_entry: false
      heading_level: 3

## Adapters

Concrete Kafka adapter implementing producer and consumer patterns with ArchiPy conventions.

::: archipy.adapters.kafka.adapters
    options:
      show_root_toc_entry: false
      heading_level: 3
