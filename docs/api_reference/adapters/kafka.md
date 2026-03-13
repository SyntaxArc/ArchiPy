---
title: Kafka
description: API reference for the Kafka adapter ports, adapters, and mocks.
---

# Kafka

The `kafka` adapter provides integration with Apache Kafka for producing and consuming messages in
event-driven architectures. It ships **five** adapter classes — one for admin operations and two
sync/async pairs for producing and consuming.

| Class                       | Mode  | Port                     |
|-----------------------------|-------|--------------------------|
| `KafkaAdminAdapter`         | sync  | `KafkaAdminPort`         |
| `KafkaProducerAdapter`      | sync  | `KafkaProducerPort`      |
| `KafkaConsumerAdapter`      | sync  | `KafkaConsumerPort`      |
| `AsyncKafkaProducerAdapter` | async | `AsyncKafkaProducerPort` |
| `AsyncKafkaConsumerAdapter` | async | `AsyncKafkaConsumerPort` |

## Ports

Abstract port interfaces defining the Kafka adapter contracts for sync and async message
production and consumption.

::: archipy.adapters.kafka.ports
options:
show_root_toc_entry: false
heading_level: 3

## Adapters

Concrete Kafka adapter implementations for both sync and async producer/consumer patterns,
built on `confluent_kafka` and `confluent_kafka.aio`.

::: archipy.adapters.kafka.adapters
options:
show_root_toc_entry: false
heading_level: 3
