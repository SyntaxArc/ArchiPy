# Installation

## Prerequisites

Before starting, ensure you have:

- **Python 3.14 or higher**

  ArchiPy requires Python 3.14+. Check your version with:

    ```bash
    python --version
    ```

  If needed, [download Python 3.14+](https://www.python.org/downloads/).

- **UV** (for dependency management)

  UV is a fast Python package installer and resolver. Install it via the [official guide](https://docs.astral.sh/uv/getting-started/installation/).

## Installation Methods

### Using pip

Install the core library:

```bash
pip install archipy
```

With optional dependencies (e.g., database adapters, services):

```bash
pip install archipy[postgres,sqlite,starrocks,redis,keycloak,minio,kafka]
```

### Using UV

Add the core library:

```bash
uv add archipy
```

With optional dependencies:

```bash
uv add "archipy[postgres,sqlite,starrocks,redis,keycloak,minio,kafka]"
```

## Optional Dependencies

ArchiPy supports modular features through optional dependencies:

### Database Adapters

| Feature    | Installation Command | Description                                             |
|------------|----------------------|---------------------------------------------------------|
| PostgreSQL | `archipy[postgres]`  | PostgreSQL database adapter with SQLAlchemy integration |
| SQLite     | `archipy[sqlite]`    | SQLite database adapter with SQLAlchemy integration     |
| StarRocks  | `archipy[starrocks]` | StarRocks database adapter with SQLAlchemy integration  |

### Service Adapters

| Feature  | Installation Command | Description                               |
|----------|----------------------|-------------------------------------------|
| Redis    | `archipy[redis]`     | Redis caching and key-value storage       |
| Keycloak | `archipy[keycloak]`  | Authentication and authorization services |
| MinIO    | `archipy[minio]`     | S3-compatible object storage              |
| Kafka    | `archipy[kafka]`     | Message streaming and event processing    |

### Web Framework Support

| Feature | Installation Command | Description                                       |
|---------|----------------------|---------------------------------------------------|
| FastAPI | `archipy[fastapi]`   | FastAPI integration with middleware and utilities |
| gRPC    | `archipy[grpc]`      | gRPC integration with interceptors                |

### Additional Features

| Feature    | Installation Command  | Description                   |
|------------|-----------------------|-------------------------------|
| JWT        | `archipy[jwt]`        | JSON Web Token utilities      |
| Prometheus | `archipy[prometheus]` | Metrics and monitoring        |
| Sentry     | `archipy[sentry]`     | Error tracking and monitoring |
| Scheduler  | `archipy[scheduler]`  | Task scheduling utilities     |

## Development Installation

For contributors:

```bash
# Clone the repository
git clone https://github.com/SyntaxArc/ArchiPy.git
cd ArchiPy

# Set up the project (installs UV)
make setup

# Install dependencies
make install

# Install all development tools and optional dependencies
make install-dev
```

## Troubleshooting

If issues arise, verify:

1. Python version is 3.14+
2. `pip` or `uv` is updated (e.g., `pip install --upgrade pip` or `uv self update`)
3. Build tools are available (UV handles this automatically)
4. Database-specific dependencies are installed if using database adapters

!!! tip "IDE Integration"
For the best development experience, use an IDE that supports Python type hints, such as PyCharm or VS Code with the
Python extension. The project uses modern Python type hints and benefits from IDE support for type checking and
autocompletion.
