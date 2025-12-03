"""Tracing decorators for capturing transactions and spans in pure Python applications.

This module provides decorators to instrument code with APM tracing when not using
gRPC or FastAPI frameworks. Supports both Sentry and Elastic APM based on configuration.
"""

import functools
import logging
from collections.abc import Callable
from typing import Any, cast

from archipy.configs.base_config import BaseConfig


def capture_transaction[F: Callable[..., Any]](
    name: str | None = None,
    *,
    op: str = "function",
    description: str | None = None,
) -> Callable[[F], F]:
    """Decorator to capture a transaction for the decorated function.

    This decorator creates a transaction span around the execution of the decorated function.
    It integrates with both Sentry and Elastic APM based on the application configuration.

    Args:
        name: Name of the transaction. If None, uses the function name.
        op: Operation type/category for the transaction. Defaults to "function".
        description: Optional description of the transaction.

    Returns:
        The decorated function with transaction tracing capabilities.

    Example:
        ```python
        @capture_transaction(name="user_processing", op="business_logic")
        def process_user_data(user_id: int) -> dict[str, Any]:
            # Your business logic here
            return {"user_id": user_id, "status": "processed"}

        # Transaction will be automatically captured when function is called
        result = process_user_data(123)
        ```
    """

    def decorator(func: F) -> F:
        transaction_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            config: Any = BaseConfig.global_config()

            # Initialize and track with Sentry if enabled
            sentry_transaction = None
            if config.SENTRY.IS_ENABLED:
                try:
                    import sentry_sdk

                    # Initialize Sentry if not already done
                    if not sentry_sdk.Hub.current.client:
                        sentry_sdk.init(
                            dsn=config.SENTRY.DSN,
                            debug=config.SENTRY.DEBUG,
                            release=config.SENTRY.RELEASE,
                            sample_rate=config.SENTRY.SAMPLE_RATE,
                            traces_sample_rate=config.SENTRY.TRACES_SAMPLE_RATE,
                            environment=getattr(config, "ENVIRONMENT", None),
                        )
                    sentry_transaction = sentry_sdk.start_transaction(
                        name=transaction_name,
                        op=op,
                        description=description or transaction_name,
                    )
                    sentry_transaction.__enter__()
                except ImportError:
                    logging.debug("sentry_sdk is not installed, skipping Sentry transaction capture.")
                except Exception:
                    logging.exception("Failed to initialize Sentry or start transaction")

            # Initialize and track with Elastic APM if enabled
            elastic_client = None
            if config.ELASTIC_APM.IS_ENABLED:
                try:
                    import elasticapm  # type: ignore[import-not-found]

                    # Initialize Elastic APM client with config
                    elastic_client = elasticapm.get_client()
                    if not elastic_client:
                        elastic_client = elasticapm.Client(config.ELASTIC_APM.model_dump())
                    elastic_client.begin_transaction(transaction_type="function")
                except ImportError:
                    logging.debug("elasticapm is not installed, skipping Elastic APM transaction capture.")
                except Exception:
                    logging.exception("Failed to initialize Elastic APM or start transaction")

            try:
                # Execute the function
                result = func(*args, **kwargs)

                # Mark transaction as successful
                if sentry_transaction:
                    sentry_transaction.set_status("ok")
                if elastic_client:
                    elastic_client.end_transaction(name=transaction_name, result="success")

                return result
            except Exception:
                # Mark transaction as failed and capture the exception
                if sentry_transaction:
                    sentry_transaction.set_status("internal_error")
                if elastic_client:
                    elastic_client.end_transaction(name=transaction_name, result="error")
                raise
            finally:
                # Clean up Sentry transaction
                if sentry_transaction:
                    try:
                        sentry_transaction.__exit__(None, None, None)
                    except Exception:
                        logging.exception("Error closing Sentry transaction")

        return cast(F, wrapper)

    return decorator


def async_capture_transaction[F: Callable[..., Any]](
    name: str | None = None,
    *,
    op: str = "function",
    description: str | None = None,
) -> Callable[[F], F]:
    """Decorator to capture a transaction for the decorated async function.

    This decorator creates a transaction span around the execution of the decorated async function.
    It integrates with both Sentry and Elastic APM based on the application configuration.

    Args:
        name: Name of the transaction. If None, uses the function name.
        op: Operation type/category for the transaction. Defaults to "function".
        description: Optional description of the transaction.

    Returns:
        The decorated async function with transaction tracing capabilities.

    Example:
        ```python
        @async_capture_transaction(name="user_processing", op="business_logic")
        async def process_user_data(user_id: int) -> dict[str, Any]:
            # Your async business logic here
            return {"user_id": user_id, "status": "processed"}

        # Transaction will be automatically captured when function is called
        result = await process_user_data(123)
        ```
    """

    def decorator(func: F) -> F:
        transaction_name = name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            config: Any = BaseConfig.global_config()

            # Initialize and track with Sentry if enabled
            sentry_transaction = None
            if config.SENTRY.IS_ENABLED:
                try:
                    import sentry_sdk

                    # Initialize Sentry if not already done
                    if not sentry_sdk.Hub.current.client:
                        sentry_sdk.init(
                            dsn=config.SENTRY.DSN,
                            debug=config.SENTRY.DEBUG,
                            release=config.SENTRY.RELEASE,
                            sample_rate=config.SENTRY.SAMPLE_RATE,
                            traces_sample_rate=config.SENTRY.TRACES_SAMPLE_RATE,
                            environment=getattr(config, "ENVIRONMENT", None),
                        )
                    sentry_transaction = sentry_sdk.start_transaction(
                        name=transaction_name,
                        op=op,
                        description=description or transaction_name,
                    )
                    sentry_transaction.__enter__()
                except ImportError:
                    logging.debug("sentry_sdk is not installed, skipping Sentry transaction capture.")
                except Exception:
                    logging.exception("Failed to initialize Sentry or start transaction")

            # Initialize and track with Elastic APM if enabled
            elastic_client = None
            if config.ELASTIC_APM.IS_ENABLED:
                try:
                    import elasticapm

                    # Initialize Elastic APM client with config
                    elastic_client = elasticapm.get_client()
                    if not elastic_client:
                        elastic_client = elasticapm.Client(config.ELASTIC_APM.model_dump())
                    elastic_client.begin_transaction(transaction_type="function")
                except ImportError:
                    logging.debug("elasticapm is not installed, skipping Elastic APM transaction capture.")
                except Exception:
                    logging.exception("Failed to initialize Elastic APM or start transaction")

            try:
                # Execute the async function
                result = await func(*args, **kwargs)

                # Mark transaction as successful
                if sentry_transaction:
                    sentry_transaction.set_status("ok")
                if elastic_client:
                    elastic_client.end_transaction(name=transaction_name, result="success")

                return result
            except Exception:
                # Mark transaction as failed and capture the exception
                if sentry_transaction:
                    sentry_transaction.set_status("internal_error")
                if elastic_client:
                    elastic_client.end_transaction(name=transaction_name, result="error")
                raise
            finally:
                # Clean up Sentry transaction
                if sentry_transaction:
                    try:
                        sentry_transaction.__exit__(None, None, None)
                    except Exception:
                        logging.exception("Error closing Sentry transaction")

        return cast(F, wrapper)

    return decorator


def capture_span[F: Callable[..., Any]](
    name: str | None = None,
    *,
    op: str = "function",
    description: str | None = None,
) -> Callable[[F], F]:
    """Decorator to capture a span for the decorated function.

    This decorator creates a span around the execution of the decorated function.
    Spans are child operations within a transaction and help provide detailed
    performance insights. Works with both Sentry and Elastic APM.

    Args:
        name: Name of the span. If None, uses the function name.
        op: Operation type/category for the span. Defaults to "function".
        description: Optional description of the span.

    Returns:
        The decorated function with span tracing capabilities.

    Example:
        ```python
        @capture_transaction(name="user_processing")
        def process_user_data(user_id: int) -> dict[str, Any]:
            user = get_user(user_id)
            processed_data = transform_data(user)
            save_result(processed_data)
            return processed_data

        @capture_span(name="database_query", op="db")
        def get_user(user_id: int) -> dict[str, Any]:
            # Database query logic here
            return {"id": user_id, "name": "John"}

        @capture_span(name="data_transformation", op="processing")
        def transform_data(user: dict[str, Any]) -> dict[str, Any]:
            # Data transformation logic
            return {"processed": True, **user}

        @capture_span(name="save_operation", op="db")
        def save_result(data: dict[str, Any]) -> None:
            # Save logic here
            pass
        ```
    """

    def decorator(func: F) -> F:
        span_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            config: Any = BaseConfig.global_config()

            # Track with Sentry if enabled
            sentry_span = None
            if config.SENTRY.IS_ENABLED:
                try:
                    import sentry_sdk

                    sentry_span = sentry_sdk.start_span(
                        op=op,
                        description=span_name,
                    )
                    sentry_span.__enter__()
                except ImportError:
                    logging.debug("sentry_sdk is not installed, skipping Sentry span capture.")
                except Exception:
                    logging.exception("Failed to start Sentry span")

            # Track with Elastic APM if enabled
            elastic_client = None
            elastic_span = None
            if config.ELASTIC_APM.IS_ENABLED:
                try:
                    import elasticapm

                    elastic_client = elasticapm.get_client()
                    if elastic_client:
                        elastic_span = elastic_client.begin_span(
                            name=span_name,
                            span_type=op,
                        )
                except ImportError:
                    logging.debug("elasticapm is not installed, skipping Elastic APM span capture.")
                except Exception:
                    logging.exception("Failed to start Elastic APM span")

            try:
                # Execute the function
                result = func(*args, **kwargs)

                # Mark span as successful
                if sentry_span:
                    sentry_span.set_status("ok")

                return result
            except Exception as e:
                # Mark span as failed and capture the exception
                if sentry_span:
                    sentry_span.set_status("internal_error")
                    sentry_span.set_tag("error", True)
                    sentry_span.set_data("exception", str(e))

                if elastic_span and elastic_client:
                    elastic_client.capture_exception()

                raise
            finally:
                # Clean up spans
                if elastic_span and elastic_client:
                    try:
                        elastic_client.end_span()
                    except Exception:
                        logging.exception("Error closing Elastic APM span")

                if sentry_span:
                    try:
                        sentry_span.__exit__(None, None, None)
                    except Exception:
                        logging.exception("Error closing Sentry span")

        return cast(F, wrapper)

    return decorator


def async_capture_span[F: Callable[..., Any]](
    name: str | None = None,
    *,
    op: str = "function",
    description: str | None = None,
) -> Callable[[F], F]:
    """Decorator to capture a span for the decorated async function.

    This decorator creates a span around the execution of the decorated async function.
    Spans are child operations within a transaction and help provide detailed
    performance insights. Works with both Sentry and Elastic APM.

    Args:
        name: Name of the span. If None, uses the function name.
        op: Operation type/category for the span. Defaults to "function".
        description: Optional description of the span.

    Returns:
        The decorated async function with span tracing capabilities.

    Example:
        ```python
        @async_capture_transaction(name="user_processing")
        async def process_user_data(user_id: int) -> dict[str, Any]:
            user = await get_user(user_id)
            processed_data = await transform_data(user)
            await save_result(processed_data)
            return processed_data

        @async_capture_span(name="database_query", op="db")
        async def get_user(user_id: int) -> dict[str, Any]:
            # Async database query logic here
            return {"id": user_id, "name": "John"}

        @async_capture_span(name="data_transformation", op="processing")
        async def transform_data(user: dict[str, Any]) -> dict[str, Any]:
            # Async data transformation logic
            return {"processed": True, **user}

        @async_capture_span(name="save_operation", op="db")
        async def save_result(data: dict[str, Any]) -> None:
            # Async save logic here
            pass
        ```
    """

    def decorator(func: F) -> F:
        span_name = name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            config: Any = BaseConfig.global_config()

            # Track with Sentry if enabled
            sentry_span = None
            if config.SENTRY.IS_ENABLED:
                try:
                    import sentry_sdk

                    sentry_span = sentry_sdk.start_span(
                        op=op,
                        description=span_name,
                    )
                    sentry_span.__enter__()
                except ImportError:
                    logging.debug("sentry_sdk is not installed, skipping Sentry span capture.")
                except Exception:
                    logging.exception("Failed to start Sentry span")

            # Track with Elastic APM if enabled
            elastic_client = None
            elastic_span_context = None
            if config.ELASTIC_APM.IS_ENABLED:
                try:
                    import elasticapm

                    elastic_client = elasticapm.get_client()
                    if elastic_client:
                        # Use async context manager for proper async handling
                        elastic_span_context = elasticapm.async_capture_span(span_name, span_type=op)
                        await elastic_span_context.__aenter__()
                except ImportError:
                    logging.debug("elasticapm is not installed, skipping Elastic APM span capture.")
                except Exception:
                    logging.exception("Failed to start Elastic APM span")

            try:
                # Execute the async function
                result = await func(*args, **kwargs)

                # Mark Sentry span as successful
                if sentry_span:
                    sentry_span.set_status("ok")

                return result
            except Exception as e:
                # Mark span as failed
                if sentry_span:
                    sentry_span.set_status("internal_error")
                    sentry_span.set_tag("error", True)
                    sentry_span.set_data("exception", str(e))

                if elastic_client:
                    elastic_client.capture_exception()

                raise
            finally:
                # Clean up Elastic APM span
                if elastic_span_context:
                    try:
                        await elastic_span_context.__aexit__(None, None, None)
                    except Exception:
                        logging.exception("Error closing Elastic APM span")

                # Clean up Sentry span
                if sentry_span:
                    try:
                        sentry_span.__exit__(None, None, None)
                    except Exception:
                        logging.exception("Error closing Sentry span")

        return cast(F, wrapper)

    return decorator
