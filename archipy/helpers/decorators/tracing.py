"""Tracing decorators for capturing transactions and spans in pure Python applications.

This module provides decorators to instrument code with APM tracing when not using
gRPC or FastAPI frameworks. Supports both Sentry and Elastic APM based on configuration.
"""

from __future__ import annotations

import functools
import logging
import warnings
from typing import TYPE_CHECKING, Any, Protocol

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.tracing_utils import TracingUtils
from archipy.models.errors import InvalidArgumentError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

logger = logging.getLogger(__name__)

ExcInfo = tuple[type[BaseException] | None, BaseException | None, Any]


class _Function(Protocol):
    """A callable with a __name__ attribute."""

    __name__: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


class _AsyncFunction(Protocol):
    """An async callable with a __name__ attribute."""

    __name__: str

    def __call__(self, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, Any]: ...


def _warn_deprecated_description(description: str | None) -> None:
    """Emit a deprecation warning when ``description`` is provided."""
    if description is not None:
        warnings.warn(
            "The 'description' parameter is deprecated and will be removed in a future version.",
            DeprecationWarning,
            stacklevel=2,
        )


def _start_sentry_transaction(config: Any, transaction_name: str, op: str) -> Any:
    """Start a Sentry transaction when Sentry tracing is enabled."""
    if not config.SENTRY.IS_ENABLED:
        return None
    try:
        import sentry_sdk

        sentry_transaction = sentry_sdk.start_transaction(
            name=transaction_name,
            op=op,
        )
        sentry_transaction.__enter__()
    except ImportError:
        logger.debug("sentry_sdk is not installed, skipping Sentry transaction capture.")
        return None
    except Exception:
        logger.exception("Failed to start Sentry transaction")
        return None
    else:
        return sentry_transaction


def _start_sentry_span(config: Any, span_name: str, op: str) -> Any:
    """Start a Sentry span when Sentry tracing is enabled."""
    if not config.SENTRY.IS_ENABLED:
        return None
    try:
        import sentry_sdk

        sentry_span = sentry_sdk.start_span(
            op=op,
            name=span_name,
        )
        sentry_span.__enter__()
    except ImportError:
        logger.debug("sentry_sdk is not installed, skipping Sentry span capture.")
        return None
    except Exception:
        logger.exception("Failed to start Sentry span")
        return None
    else:
        return sentry_span


def _begin_elastic_transaction(config: Any) -> tuple[Any, Any]:
    """Begin an Elastic APM transaction when Elastic APM tracing is enabled."""
    if not config.ELASTIC_APM.IS_ENABLED:
        return None, None
    try:
        import elasticapm

        elastic_client = elasticapm.get_client()
        if elastic_client is None:
            logger.warning("Elastic APM client is not initialized; skipping APM transaction.")
            return None, None
        elastic_client.begin_transaction(transaction_type="function")
    except ImportError:
        logger.debug("elasticapm is not installed, skipping Elastic APM transaction capture.")
        return None, None
    except Exception:
        logger.exception("Failed to begin Elastic APM transaction")
        return None, None
    else:
        return elastic_client, elasticapm


def _finalize_elastic_transaction_success(
    elastic_client: Any,
    elastic_apm_module: Any,
    transaction_name: str,
) -> None:
    """Record a successful Elastic APM transaction outcome."""
    from elasticapm.conf.constants import OUTCOME

    elastic_apm_module.set_transaction_outcome(OUTCOME.SUCCESS)
    elastic_client.end_transaction(name=transaction_name, result="success")


def _finalize_elastic_transaction_failure(
    elastic_client: Any,
    elastic_apm_module: Any,
    transaction_name: str,
    exception: BaseException,
) -> None:
    """Record a failed Elastic APM transaction outcome."""
    elastic_apm_module.set_transaction_outcome(TracingUtils.outcome_for_exception(exception))
    elastic_client.end_transaction(name=transaction_name, result="failure")


def _exit_sentry_context(
    sentry_context: Any,
    exc_info: ExcInfo,
    *,
    context_label: str,
) -> None:
    """Exit a Sentry transaction or span context manager."""
    if sentry_context is not None:
        try:
            sentry_context.__exit__(exc_info[0], exc_info[1], exc_info[2])
        except Exception:
            logger.exception("Error closing Sentry %s", context_label)


def _import_elasticapm_for_span() -> Any:
    """Import elasticapm for span capture, logging and returning None on ImportError."""
    try:
        import elasticapm
    except ImportError:
        logger.debug("elasticapm is not installed, skipping Elastic APM span capture.")
        return None
    else:
        return elasticapm


def _call_with_sentry_span_status(
    sentry_span: Any,
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    exc_info_holder: list[ExcInfo],
) -> Any:
    """Invoke a sync function and update Sentry span status on success or failure."""
    try:
        result = func(*args, **kwargs)
    except Exception as exception:
        exc_info_holder[0] = (type(exception), exception, exception.__traceback__)
        if sentry_span is not None:
            sentry_span.set_status("internal_error")
        raise
    else:
        if sentry_span is not None and sentry_span.status is None:
            sentry_span.set_status("ok")
        return result


async def _call_with_sentry_span_status_async(
    sentry_span: Any,
    func: Callable[..., Coroutine[Any, Any, Any]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    exc_info_holder: list[ExcInfo],
) -> Any:
    """Invoke an async function and update Sentry span status on success or failure."""
    try:
        result = await func(*args, **kwargs)
    except Exception as exception:
        exc_info_holder[0] = (type(exception), exception, exception.__traceback__)
        if sentry_span is not None:
            sentry_span.set_status("internal_error")
        raise
    else:
        if sentry_span is not None and sentry_span.status is None:
            sentry_span.set_status("ok")
        return result


def _run_sync_transaction(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    transaction_name: str,
    op: str,
) -> Any:
    """Execute a sync function inside Sentry and Elastic APM transaction tracing."""
    config = BaseConfig.global_config()
    if not TracingUtils.is_tracing_enabled(config):
        return func(*args, **kwargs)

    TracingUtils.init_tracing_if_needed(config)

    sentry_transaction = _start_sentry_transaction(config, transaction_name, op)
    elastic_client, elastic_apm_module = _begin_elastic_transaction(config)

    exc_info: ExcInfo = (None, None, None)
    try:
        result = func(*args, **kwargs)
    except Exception as exception:
        exc_info = (type(exception), exception, exception.__traceback__)
        if sentry_transaction is not None:
            sentry_transaction.set_status("internal_error")
        if elastic_client is not None and elastic_apm_module is not None:
            _finalize_elastic_transaction_failure(
                elastic_client,
                elastic_apm_module,
                transaction_name,
                exception,
            )
        raise
    else:
        if sentry_transaction is not None and sentry_transaction.status is None:
            sentry_transaction.set_status("ok")
        if elastic_client is not None and elastic_apm_module is not None:
            _finalize_elastic_transaction_success(elastic_client, elastic_apm_module, transaction_name)
        return result
    finally:
        _exit_sentry_context(sentry_transaction, exc_info, context_label="transaction")


async def _run_async_transaction(
    func: Callable[..., Coroutine[Any, Any, Any]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    transaction_name: str,
    op: str,
) -> Any:
    """Execute an async function inside Sentry and Elastic APM transaction tracing."""
    config = BaseConfig.global_config()
    if not TracingUtils.is_tracing_enabled(config):
        return await func(*args, **kwargs)

    TracingUtils.init_tracing_if_needed(config)

    sentry_transaction = _start_sentry_transaction(config, transaction_name, op)
    elastic_client, elastic_apm_module = _begin_elastic_transaction(config)

    exc_info: ExcInfo = (None, None, None)
    try:
        result = await func(*args, **kwargs)
    except Exception as exception:
        exc_info = (type(exception), exception, exception.__traceback__)
        if sentry_transaction is not None:
            sentry_transaction.set_status("internal_error")
        if elastic_client is not None and elastic_apm_module is not None:
            _finalize_elastic_transaction_failure(
                elastic_client,
                elastic_apm_module,
                transaction_name,
                exception,
            )
        raise
    else:
        if sentry_transaction is not None and sentry_transaction.status is None:
            sentry_transaction.set_status("ok")
        if elastic_client is not None and elastic_apm_module is not None:
            _finalize_elastic_transaction_success(elastic_client, elastic_apm_module, transaction_name)
        return result
    finally:
        _exit_sentry_context(sentry_transaction, exc_info, context_label="transaction")


def _run_sync_span(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    span_name: str,
    op: str,
) -> Any:
    """Execute a sync function inside Sentry and Elastic APM span tracing."""
    config = BaseConfig.global_config()
    if not TracingUtils.is_tracing_enabled(config):
        return func(*args, **kwargs)

    TracingUtils.init_tracing_if_needed(config)

    sentry_span = _start_sentry_span(config, span_name, op)
    exc_info_holder: list[ExcInfo] = [(None, None, None)]

    try:
        if config.ELASTIC_APM.IS_ENABLED:
            elasticapm = _import_elasticapm_for_span()
            if elasticapm is None:
                return _call_with_sentry_span_status(sentry_span, func, args, kwargs, exc_info_holder)
            with elasticapm.capture_span(span_name, span_type=op):
                return _call_with_sentry_span_status(sentry_span, func, args, kwargs, exc_info_holder)
        return _call_with_sentry_span_status(sentry_span, func, args, kwargs, exc_info_holder)
    finally:
        _exit_sentry_context(sentry_span, exc_info_holder[0], context_label="span")


async def _run_async_span(
    func: Callable[..., Coroutine[Any, Any, Any]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    span_name: str,
    op: str,
) -> Any:
    """Execute an async function inside Sentry and Elastic APM span tracing."""
    config = BaseConfig.global_config()
    if not TracingUtils.is_tracing_enabled(config):
        return await func(*args, **kwargs)

    TracingUtils.init_tracing_if_needed(config)

    sentry_span = _start_sentry_span(config, span_name, op)
    exc_info_holder: list[ExcInfo] = [(None, None, None)]

    try:
        if config.ELASTIC_APM.IS_ENABLED:
            elasticapm = _import_elasticapm_for_span()
            if elasticapm is None:
                return await _call_with_sentry_span_status_async(
                    sentry_span,
                    func,
                    args,
                    kwargs,
                    exc_info_holder,
                )
            async with elasticapm.async_capture_span(span_name, span_type=op):
                return await _call_with_sentry_span_status_async(
                    sentry_span,
                    func,
                    args,
                    kwargs,
                    exc_info_holder,
                )
        return await _call_with_sentry_span_status_async(
            sentry_span,
            func,
            args,
            kwargs,
            exc_info_holder,
        )
    finally:
        _exit_sentry_context(sentry_span, exc_info_holder[0], context_label="span")


def capture_transaction[F: _Function](
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
    _warn_deprecated_description(description)

    def decorator(func: F) -> Callable[..., Any]:
        transaction_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return _run_sync_transaction(
                func,
                args,
                kwargs,
                transaction_name=transaction_name,
                op=op,
            )

        return wrapper

    return decorator


def capture_span[F: _Function](
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
    _warn_deprecated_description(description)

    def decorator(func: F) -> Callable[..., Any]:
        span_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return _run_sync_span(func, args, kwargs, span_name=span_name, op=op)

        return wrapper

    return decorator


def async_capture_transaction[F: _AsyncFunction](
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
            raise InvalidArgumentError(
                argument_name="func",
                additional_data={
                    "decorator": "async_capture_transaction",
                    "func_name": func.__name__,
                },
            )

        transaction_name = name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _run_async_transaction(
                func,
                args,
                kwargs,
                transaction_name=transaction_name,
                op=op,
            )

        return wrapper

    return decorator


def async_capture_span[F: _AsyncFunction](
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
            raise InvalidArgumentError(
                argument_name="func",
                additional_data={
                    "decorator": "async_capture_span",
                    "func_name": func.__name__,
                },
            )

        span_name = name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _run_async_span(func, args, kwargs, span_name=span_name, op=op)

        return wrapper

    return decorator
