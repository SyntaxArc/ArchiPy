"""Tracing decorators for capturing transactions and spans in pure Python applications.

This module provides decorators to instrument code with APM tracing when not using
gRPC or FastAPI frameworks. Supports both Sentry and Elastic APM based on configuration.
"""

from __future__ import annotations

import functools
import logging
import warnings
from collections.abc import Callable, Coroutine
from typing import Any

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.tracing_utils import TracingUtils

logger = logging.getLogger(__name__)


def capture_transaction[F: Callable[..., Any]](
    name: str | None = None,
    *,
    op: str = "function",
    description: str | None = None,
) -> Callable[[F], Callable[..., Any]]:
    """Decorator to capture a transaction for the decorated function.

    This decorator creates a transaction span around the execution of the decorated function.
    It integrates with both Sentry and Elastic APM based on the application configuration.

    Args:
        name: Name of the transaction. If None, uses the function name.
        op: Operation type/category for the transaction. Defaults to "function".
        description: Deprecated; ignored. Kept for backward compatibility.

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
    if description is not None:
        warnings.warn(
            "The 'description' parameter is deprecated and will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )

    def decorator(func: F) -> Callable[..., Any]:
        transaction_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = BaseConfig.global_config()
            if not TracingUtils.is_tracing_enabled(config):
                return func(*args, **kwargs)

            TracingUtils.init_tracing_if_needed(config)

            sentry_transaction = None
            if config.SENTRY.IS_ENABLED:
                try:
                    import sentry_sdk

                    sentry_transaction = sentry_sdk.start_transaction(
                        name=transaction_name,
                        op=op,
                    )
                    sentry_transaction.__enter__()
                except ImportError:
                    logger.debug("sentry_sdk is not installed, skipping Sentry transaction capture.")
                except Exception:
                    logger.exception("Failed to start Sentry transaction")

            elastic_client: Any = None
            elastic_apm_module: Any = None
            if config.ELASTIC_APM.IS_ENABLED:
                try:
                    import elasticapm

                    elastic_apm_module = elasticapm
                    elastic_client = elasticapm.get_client()
                    if elastic_client is None:
                        logger.warning("Elastic APM client is not initialized; skipping APM transaction.")
                    else:
                        elastic_client.begin_transaction(transaction_type="function")
                except ImportError:
                    logger.debug("elasticapm is not installed, skipping Elastic APM transaction capture.")
                except Exception:
                    logger.exception("Failed to begin Elastic APM transaction")
                    elastic_client = None

            exc_info: tuple[type[BaseException] | None, BaseException | None, Any] = (None, None, None)
            try:
                result = func(*args, **kwargs)
            except Exception as exception:
                exc_info = (type(exception), exception, exception.__traceback__)
                if sentry_transaction is not None:
                    sentry_transaction.set_status("internal_error")
                if elastic_client is not None and elastic_apm_module is not None:
                    elastic_apm_module.set_transaction_outcome(TracingUtils.outcome_for_exception(exception))
                    elastic_client.end_transaction(name=transaction_name, result="failure")
                raise
            else:
                if sentry_transaction is not None and sentry_transaction.status is None:
                    sentry_transaction.set_status("ok")
                if elastic_client is not None and elastic_apm_module is not None:
                    from elasticapm.conf.constants import OUTCOME

                    elastic_apm_module.set_transaction_outcome(OUTCOME.SUCCESS)
                    elastic_client.end_transaction(name=transaction_name, result="success")
                return result
            finally:
                if sentry_transaction is not None:
                    try:
                        sentry_transaction.__exit__(exc_info[0], exc_info[1], exc_info[2])
                    except Exception:
                        logger.exception("Error closing Sentry transaction")

        wrapper.__wrapped__ = func
        return wrapper

    return decorator


def capture_span[F: Callable[..., Any]](
    name: str | None = None,
    *,
    op: str = "function",
    description: str | None = None,
) -> Callable[[F], Callable[..., Any]]:
    """Decorator to capture a span for the decorated function.

    This decorator creates a span around the execution of the decorated function.
    Spans are child operations within a transaction and help provide detailed
    performance insights. Works with both Sentry and Elastic APM.

    Args:
        name: Name of the span. If None, uses the function name.
        op: Operation type/category for the span. Defaults to "function".
        description: Deprecated; ignored. Kept for backward compatibility.

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
    if description is not None:
        warnings.warn(
            "The 'description' parameter is deprecated and will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )

    def decorator(func: F) -> Callable[..., Any]:
        span_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = BaseConfig.global_config()
            if not TracingUtils.is_tracing_enabled(config):
                return func(*args, **kwargs)

            TracingUtils.init_tracing_if_needed(config)

            sentry_span = None
            if config.SENTRY.IS_ENABLED:
                try:
                    import sentry_sdk

                    sentry_span = sentry_sdk.start_span(
                        op=op,
                        name=span_name,
                    )
                    sentry_span.__enter__()
                except ImportError:
                    logger.debug("sentry_sdk is not installed, skipping Sentry span capture.")
                except Exception:
                    logger.exception("Failed to start Sentry span")

            exc_info: tuple[type[BaseException] | None, BaseException | None, Any] = (None, None, None)
            try:
                if config.ELASTIC_APM.IS_ENABLED:
                    try:
                        import elasticapm
                    except ImportError:
                        logger.debug("elasticapm is not installed, skipping Elastic APM span capture.")
                        try:
                            result = func(*args, **kwargs)
                        except Exception as exception:
                            exc_info = (type(exception), exception, exception.__traceback__)
                            if sentry_span is not None:
                                sentry_span.set_status("internal_error")
                            raise
                        else:
                            if sentry_span is not None and sentry_span.status is None:
                                sentry_span.set_status("ok")
                            return result
                    else:
                        with elasticapm.capture_span(span_name, span_type=op):
                            try:
                                result = func(*args, **kwargs)
                            except Exception as exception:
                                exc_info = (type(exception), exception, exception.__traceback__)
                                if sentry_span is not None:
                                    sentry_span.set_status("internal_error")
                                raise
                            else:
                                if sentry_span is not None and sentry_span.status is None:
                                    sentry_span.set_status("ok")
                                return result
                else:
                    try:
                        result = func(*args, **kwargs)
                    except Exception as exception:
                        exc_info = (type(exception), exception, exception.__traceback__)
                        if sentry_span is not None:
                            sentry_span.set_status("internal_error")
                        raise
                    else:
                        if sentry_span is not None and sentry_span.status is None:
                            sentry_span.set_status("ok")
                        return result
            finally:
                if sentry_span is not None:
                    try:
                        sentry_span.__exit__(exc_info[0], exc_info[1], exc_info[2])
                    except Exception:
                        logger.exception("Error closing Sentry span")

        wrapper.__wrapped__ = func
        return wrapper

    return decorator


def async_capture_transaction[F: Callable[..., Coroutine[Any, Any, Any]]](
    name: str | None = None,
    *,
    op: str = "function",
) -> Callable[[F], Callable[..., Coroutine[Any, Any, Any]]]:
    """Decorator to capture a transaction for an async function.

    Explicit async-only counterpart of ``capture_transaction``.  Unlike
    ``capture_transaction``, this decorator accepts **only** coroutine
    functions and raises ``TypeError`` immediately at decoration time if a
    sync function is passed, making misuse visible at import time rather than
    at call time.

    Args:
        name: Name of the transaction. If None, uses the function name.
        op: Operation type/category for the transaction. Defaults to "function".

    Returns:
        The decorated coroutine function with transaction tracing capabilities.

    Raises:
        TypeError: If the decorated function is not a coroutine function.

    Example:
        ```python
        @async_capture_transaction(name="process_orders", op="business_logic")
        async def process_orders(order_ids: list[int]) -> list[dict]:
            # Your async business logic here
            return [{"order_id": oid} for oid in order_ids]


        # Transaction will be automatically captured when coroutine is awaited
        result = await process_orders([1, 2, 3])
        ```
    """
    import inspect

    def decorator(func: F) -> Callable[..., Coroutine[Any, Any, Any]]:
        if not inspect.iscoroutinefunction(func):
            raise TypeError(
                f"@async_capture_transaction requires a coroutine function, "
                f"but '{func.__name__}' is a plain function. "
                f"Use @capture_transaction for synchronous functions.",
            )

        transaction_name = name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = BaseConfig.global_config()
            if not TracingUtils.is_tracing_enabled(config):
                return await func(*args, **kwargs)

            TracingUtils.init_tracing_if_needed(config)

            sentry_transaction = None
            if config.SENTRY.IS_ENABLED:
                try:
                    import sentry_sdk

                    sentry_transaction = sentry_sdk.start_transaction(
                        name=transaction_name,
                        op=op,
                    )
                    sentry_transaction.__enter__()
                except ImportError:
                    logger.debug("sentry_sdk is not installed, skipping Sentry transaction capture.")
                except Exception:
                    logger.exception("Failed to start Sentry transaction")

            elastic_client: Any = None
            elastic_apm_module: Any = None
            if config.ELASTIC_APM.IS_ENABLED:
                try:
                    import elasticapm

                    elastic_apm_module = elasticapm
                    elastic_client = elasticapm.get_client()
                    if elastic_client is None:
                        logger.warning("Elastic APM client is not initialized; skipping APM transaction.")
                    else:
                        elastic_client.begin_transaction(transaction_type="function")
                except ImportError:
                    logger.debug("elasticapm is not installed, skipping Elastic APM transaction capture.")
                except Exception:
                    logger.exception("Failed to begin Elastic APM transaction")
                    elastic_client = None

            exc_info: tuple[type[BaseException] | None, BaseException | None, Any] = (None, None, None)
            try:
                result = await func(*args, **kwargs)
            except Exception as exception:
                exc_info = (type(exception), exception, exception.__traceback__)
                if sentry_transaction is not None:
                    sentry_transaction.set_status("internal_error")
                if elastic_client is not None and elastic_apm_module is not None:
                    elastic_apm_module.set_transaction_outcome(TracingUtils.outcome_for_exception(exception))
                    elastic_client.end_transaction(name=transaction_name, result="failure")
                raise
            else:
                if sentry_transaction is not None and sentry_transaction.status is None:
                    sentry_transaction.set_status("ok")
                if elastic_client is not None and elastic_apm_module is not None:
                    from elasticapm.conf.constants import OUTCOME

                    elastic_apm_module.set_transaction_outcome(OUTCOME.SUCCESS)
                    elastic_client.end_transaction(name=transaction_name, result="success")
                return result
            finally:
                if sentry_transaction is not None:
                    try:
                        sentry_transaction.__exit__(exc_info[0], exc_info[1], exc_info[2])
                    except Exception:
                        logger.exception("Error closing Sentry transaction")

        wrapper.__wrapped__ = func  # type: ignore[attr-defined]
        return wrapper

    return decorator


def async_capture_span[F: Callable[..., Coroutine[Any, Any, Any]]](
    name: str | None = None,
    *,
    op: str = "function",
) -> Callable[[F], Callable[..., Coroutine[Any, Any, Any]]]:
    """Decorator to capture a span for an async function.

    Explicit async-only counterpart of ``capture_span``.  Unlike
    ``capture_span``, this decorator accepts **only** coroutine functions and
    raises ``TypeError`` immediately at decoration time if a sync function is
    passed.

    Spans are child operations within a transaction and help provide detailed
    performance insights.  Works with both Sentry and Elastic APM.

    Args:
        name: Name of the span. If None, uses the function name.
        op: Operation type/category for the span. Defaults to "function".

    Returns:
        The decorated coroutine function with span tracing capabilities.

    Raises:
        TypeError: If the decorated function is not a coroutine function.

    Example:
        ```python
        @async_capture_transaction(name="user_processing")
        async def process_user_data(user_id: int) -> dict:
            user = await get_user(user_id)
            processed = await transform_data(user)
            await save_result(processed)
            return processed


        @async_capture_span(name="database_query", op="db")
        async def get_user(user_id: int) -> dict:
            # Async database query logic here
            return {"id": user_id, "name": "John"}


        @async_capture_span(name="data_transformation", op="processing")
        async def transform_data(user: dict) -> dict:
            # Async data transformation logic
            return {"processed": True, **user}


        @async_capture_span(name="save_operation", op="db")
        async def save_result(data: dict) -> None:
            # Async save logic here
            pass
        ```
    """
    import inspect

    def decorator(func: F) -> Callable[..., Coroutine[Any, Any, Any]]:
        if not inspect.iscoroutinefunction(func):
            raise TypeError(
                f"@async_capture_span requires a coroutine function, "
                f"but '{func.__name__}' is a plain function. "
                f"Use @capture_span for synchronous functions.",
            )

        span_name = name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = BaseConfig.global_config()
            if not TracingUtils.is_tracing_enabled(config):
                return await func(*args, **kwargs)

            TracingUtils.init_tracing_if_needed(config)

            sentry_span = None
            if config.SENTRY.IS_ENABLED:
                try:
                    import sentry_sdk

                    sentry_span = sentry_sdk.start_span(
                        op=op,
                        name=span_name,
                    )
                    sentry_span.__enter__()
                except ImportError:
                    logger.debug("sentry_sdk is not installed, skipping Sentry span capture.")
                except Exception:
                    logger.exception("Failed to start Sentry span")

            exc_info: tuple[type[BaseException] | None, BaseException | None, Any] = (None, None, None)
            try:
                if config.ELASTIC_APM.IS_ENABLED:
                    try:
                        import elasticapm
                    except ImportError:
                        logger.debug("elasticapm is not installed, skipping Elastic APM span capture.")
                        try:
                            result = await func(*args, **kwargs)
                        except Exception as exception:
                            exc_info = (type(exception), exception, exception.__traceback__)
                            if sentry_span is not None:
                                sentry_span.set_status("internal_error")
                            raise
                        else:
                            if sentry_span is not None and sentry_span.status is None:
                                sentry_span.set_status("ok")
                            return result
                    else:
                        async with elasticapm.async_capture_span(span_name, span_type=op):
                            try:
                                result = await func(*args, **kwargs)
                            except Exception as exception:
                                exc_info = (type(exception), exception, exception.__traceback__)
                                if sentry_span is not None:
                                    sentry_span.set_status("internal_error")
                                raise
                            else:
                                if sentry_span is not None and sentry_span.status is None:
                                    sentry_span.set_status("ok")
                                return result
                else:
                    try:
                        result = await func(*args, **kwargs)
                    except Exception as exception:
                        exc_info = (type(exception), exception, exception.__traceback__)
                        if sentry_span is not None:
                            sentry_span.set_status("internal_error")
                        raise
                    else:
                        if sentry_span is not None and sentry_span.status is None:
                            sentry_span.set_status("ok")
                        return result
            finally:
                if sentry_span is not None:
                    try:
                        sentry_span.__exit__(exc_info[0], exc_info[1], exc_info[2])
                    except Exception:
                        logger.exception("Error closing Sentry span")

        wrapper.__wrapped__ = func  # type: ignore[attr-defined]
        return wrapper

    return decorator
