---
title: Scheduler
description: What the ArchiPy scheduler extra installs, and how to run scheduled jobs with APScheduler in an ArchiPy app.
---

# Scheduler

ArchiPy ships a `scheduler` extra that installs [APScheduler](https://apscheduler.readthedocs.io/). ArchiPy has **no
scheduler wrapper, adapter, config section or decorator** of its own: the extra only pins the dependency. You use
APScheduler directly and combine it with ArchiPy pieces (config, logging, the FastAPI lifespan).

## Installation

```bash
uv add "archipy[scheduler]"
```

The extra pins `apscheduler>=3.11.3` (the 3.x API shown below).

## What ArchiPy provides

| Need                          | ArchiPy piece                                                                |
|-------------------------------|------------------------------------------------------------------------------|
| Start and stop with the app   | `lifespan` argument of `AppUtils.create_fastapi_app`                         |
| Timing and tracing of a job   | `measure_duration` and `trace_span` decorators (see [Decorators](helpers/decorators.md)) |
| Retries inside a job          | `retry` decorator (see [Decorators](helpers/decorators.md))                  |
| Durable multi-step schedules  | The [Temporal adapter](adapters/temporal.md)                                 |

## Basic Usage

Run an `AsyncIOScheduler` inside the FastAPI lifespan, so it starts and stops with the app:

```python
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.app_utils import AppUtils

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def cleanup_expired_sessions() -> None:
    """Remove expired sessions."""
    logger.info("Cleaning expired sessions")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Start the scheduler on startup and stop it on shutdown."""
    scheduler.add_job(
        cleanup_expired_sessions,
        "interval",
        minutes=5,
        id="cleanup_expired_sessions",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=True)


config = BaseConfig.global_config()
app = AppUtils.create_fastapi_app(config, lifespan=lifespan)
```

`AppUtils.create_fastapi_app` wraps your lifespan so OpenTelemetry flushes on exit; your lifespan keeps running as
written.

## Job Errors

An unhandled exception in a job is logged by APScheduler and the schedule continues. Catch domain errors in the job,
log them, and chain them when re-raising:

```python
import logging

from archipy.models.errors import InternalError

logger = logging.getLogger(__name__)


async def sync_catalog() -> None:
    """Sync the catalog and report failures with context."""
    try:
        await _fetch_and_store()
    except OSError as e:
        logger.exception("Catalog sync failed")
        raise InternalError() from e


async def _fetch_and_store() -> None:
    """Placeholder for the real work."""
```

## Multiple Workers

Every process that starts the scheduler runs every job. With several Uvicorn workers or replicas, a job runs once per
process. Run the scheduler in one dedicated process (for example a separate `manage.py` command), or move the work to
the [Temporal adapter](adapters/temporal.md), which has schedules and workers built for this.

## Limits

- ArchiPy has no scheduler config section; keep job intervals in your own config model.
- ArchiPy has no BDD scenario for the scheduler; the extra is only installed.

## See Also

- [Decorators](helpers/decorators.md) - `retry`, `measure_duration`, `trace_span`
- [Temporal Adapter](adapters/temporal.md) - Durable workflows and schedules
- [Observability](observability.md) - Tracing code that runs outside FastAPI and gRPC
- [Health Checks and Shutdown](health_checks.md) - Probes and graceful shutdown
- [Installation](../getting-started/installation.md) - All extras
