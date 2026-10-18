# archipy-kafka

Kafka adapter for [ArchiPy](https://syntaxarc.github.io/ArchiPy/): producers, consumers and topic administration.

## Install

Install it through the core extra, which pins this package to the matching ArchiPy version:

```bash
uv add "archipy[kafka]"
```

## Usage

```python
from archipy.adapters.kafka.adapters import KafkaProducerAdapter

adapter = KafkaProducerAdapter()
```

The adapter reads its settings from the `KAFKA` section of the global config, for example `KAFKA__<FIELD>` environment variables.

Classes in `archipy.adapters.kafka.adapters`: `KafkaProducerAdapter`, `KafkaConsumerAdapter`, `KafkaAdminAdapter`, `AsyncKafkaProducerAdapter`, `AsyncKafkaConsumerAdapter`.

See the [Kafka tutorial](https://syntaxarc.github.io/ArchiPy/tutorials/adapters/kafka/) for the full API.
