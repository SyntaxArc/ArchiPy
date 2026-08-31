"""OpenTelemetry tracing decorators for function and class instrumentation."""

from __future__ import annotations

import asyncio
import functools
import inspect
from typing import TYPE_CHECKING, Any, Protocol

from archipy.configs.base_config import BaseConfig
from archipy.helpers.utils.otel_utils import OtelUtils
from archipy.models.errors import InvalidArgumentError

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

_ATTR_VALUE_MAX_LEN = 256
_REDACTED_ATTR_VALUE = "***"
_REPR_FAILURE_PLACEHOLDER = "<unreprable>"
# Case-insensitive substring match against parameter names (PII / secrets).
_CAPTURE_ARGS_DENYLIST: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "authorization",
        "api_key",
        "apikey",
        "credential",
        "credentials",
        "private_key",
        "session",
        "cookie",
        "csrf",
    },
)


class _Function(Protocol):
    """A callable with a __name__ attribute."""

    __name__: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


class _AsyncFunction(Protocol):
    """An async callable with a __name__ attribute."""

    __name__: str

    def __call__(self, *args: Any, **kwargs: Any) -> Coroutine[Any, Any, Any]: ...


def _is_sensitive_arg_name(arg_name: str) -> bool:
    """Return True when ``arg_name`` matches the capture_args denylist.

    Args:
        arg_name: Parameter name to check.

    Returns:
        True if the name should be redacted.
    """
    lowered = arg_name.lower()
    return any(token in lowered for token in _CAPTURE_ARGS_DENYLIST)


def _coerce_attr_value(value: object) -> bool | int | float | str:
    """Coerce a Python value to an OpenTelemetry attribute type.

    Args:
        value: The argument value to record on a span.

    Returns:
        A bool, int, float, or str suitable for span attributes. Non-primitive
        values are converted via ``repr`` and truncated to 256 characters.
        Representation failures become a bounded placeholder.
    """
    if isinstance(value, bool | int | float | str):
        if isinstance(value, str) and len(value) > _ATTR_VALUE_MAX_LEN:
            return value[:_ATTR_VALUE_MAX_LEN]
        return value
    try:
        text = repr(value)
    except Exception:
        return _REPR_FAILURE_PLACEHOLDER
    if len(text) > _ATTR_VALUE_MAX_LEN:
        return text[:_ATTR_VALUE_MAX_LEN]
    return text


def _sanitize_attributes(attributes: dict[str, Any] | None) -> dict[str, Any] | None:
    """Redact sensitive keys and coerce values for safe span attributes.

    Args:
        attributes: Optional static attributes from the decorator.

    Returns:
        A sanitized copy, or None when ``attributes`` is None/empty.
    """
    if not attributes:
        return None
    sanitized: dict[str, Any] = {}
    for key, value in attributes.items():
        if _is_sensitive_arg_name(str(key)):
            sanitized[key] = _REDACTED_ATTR_VALUE
        else:
            sanitized[key] = _coerce_attr_value(value)
    return sanitized


def _apply_capture_args(
    span: Any,
    signature: inspect.Signature,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    capture_args: list[str] | None,
) -> None:
    """Record selected bound arguments as span attributes.

    Sensitive parameter names (passwords, tokens, …) are masked as ``***``.

    Args:
        span: The active OpenTelemetry span.
        signature: Pre-cached ``inspect.Signature`` of the decorated function.
        args: Positional call arguments.
        kwargs: Keyword call arguments.
        capture_args: Names of parameters to record, or None to skip.
    """
    if not capture_args:
        return
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    for arg_name in capture_args:
        if arg_name not in bound.arguments:
            continue
        if _is_sensitive_arg_name(arg_name):
            span.set_attribute(arg_name, _REDACTED_ATTR_VALUE)
        else:
            span.set_attribute(arg_name, _coerce_attr_value(bound.arguments[arg_name]))


def _resolve_kind(kind: Any | None) -> Any:
    """Return the span kind, defaulting to ``SpanKind.INTERNAL``.

    Args:
        kind: Explicit span kind, or None for the default.

    Returns:
        An OpenTelemetry ``SpanKind`` value.
    """
    if kind is not None:
        return kind
    from opentelemetry.trace import SpanKind

    return SpanKind.INTERNAL


def _run_traced(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    span_name: str,
    kind: Any | None,
    attributes: dict[str, Any] | None,
    capture_args: list[str] | None,
    signature: inspect.Signature,
    root: bool,
) -> Any:
    """Execute a sync function inside an OpenTelemetry span.

    Args:
        func: The function to invoke.
        args: Positional arguments.
        kwargs: Keyword arguments.
        span_name: Name of the span to create.
        kind: OpenTelemetry span kind (defaults to INTERNAL).
        attributes: Optional static span attributes.
        capture_args: Optional argument names to record as attributes.
        signature: Pre-cached signature for ``capture_args`` binding.
        root: When True, start the span with a fresh (detached) context.

    Returns:
        The return value of ``func``.
    """
    config = BaseConfig.global_config()
    if not OtelUtils.is_traces_enabled(config):
        return func(*args, **kwargs)

    OtelUtils.init_otel_if_needed(config)
    if OtelUtils.import_failed():
        return func(*args, **kwargs)

    tracer = OtelUtils.get_tracer(__name__)
    try:
        resolved_kind = _resolve_kind(kind)
    except ImportError:
        return func(*args, **kwargs)

    # Disable SDK auto-record/status — we handle both manually for BaseError mapping.
    start_kwargs: dict[str, Any] = {
        "kind": resolved_kind,
        "record_exception": False,
        "set_status_on_exception": False,
    }
    sanitized = _sanitize_attributes(attributes)
    if sanitized:
        start_kwargs["attributes"] = sanitized
    if root:
        from opentelemetry import trace
        from opentelemetry.trace import INVALID_SPAN

        start_kwargs["context"] = trace.set_span_in_context(INVALID_SPAN)

    with tracer.start_as_current_span(span_name, **start_kwargs) as span:
        _apply_capture_args(span, signature, args, kwargs, capture_args)
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            span.record_exception(exc)
            status = OtelUtils.status_for_exception(exc)
            if status is not None:
                span.set_status(status)
            raise


async def _run_traced_async(
    func: Callable[..., Coroutine[Any, Any, Any]],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    span_name: str,
    kind: Any | None,
    attributes: dict[str, Any] | None,
    capture_args: list[str] | None,
    signature: inspect.Signature,
    root: bool,
) -> Any:
    """Execute an async function inside an OpenTelemetry span.

    Args:
        func: The coroutine function to invoke.
        args: Positional arguments.
        kwargs: Keyword arguments.
        span_name: Name of the span to create.
        kind: OpenTelemetry span kind (defaults to INTERNAL).
        attributes: Optional static span attributes.
        capture_args: Optional argument names to record as attributes.
        signature: Pre-cached signature for ``capture_args`` binding.
        root: When True, start the span with a fresh (detached) context.

    Returns:
        The return value of ``func``.
    """
    config = BaseConfig.global_config()
    if not OtelUtils.is_traces_enabled(config):
        return await func(*args, **kwargs)

    OtelUtils.init_otel_if_needed(config)
    if OtelUtils.import_failed():
        return await func(*args, **kwargs)

    tracer = OtelUtils.get_tracer(__name__)
    try:
        resolved_kind = _resolve_kind(kind)
    except ImportError:
        return await func(*args, **kwargs)

    # Disable SDK auto-record/status — we handle both manually for BaseError mapping.
    start_kwargs: dict[str, Any] = {
        "kind": resolved_kind,
        "record_exception": False,
        "set_status_on_exception": False,
    }
    sanitized = _sanitize_attributes(attributes)
    if sanitized:
        start_kwargs["attributes"] = sanitized
    if root:
        from opentelemetry import trace
        from opentelemetry.trace import INVALID_SPAN

        start_kwargs["context"] = trace.set_span_in_context(INVALID_SPAN)

    with tracer.start_as_current_span(span_name, **start_kwargs) as span:
        _apply_capture_args(span, signature, args, kwargs, capture_args)
        try:
            return await func(*args, **kwargs)
        except asyncio.CancelledError as exc:
            span.record_exception(exc)
            span.set_status(OtelUtils.status_for_cancellation())
            raise
        except Exception as exc:
            span.record_exception(exc)
            status = OtelUtils.status_for_exception(exc)
            if status is not None:
                span.set_status(status)
            raise


def _reject_coroutine_function(func: _Function, decorator_name: str) -> None:
    """Raise when a sync decorator is applied to an async function.

    Args:
        func: The candidate function.
        decorator_name: Name of the sync decorator for the error payload.

    Raises:
        InvalidArgumentError: If ``func`` is a coroutine function.
    """
    if inspect.iscoroutinefunction(func):
        raise InvalidArgumentError(
            argument_name="func",
            additional_data={
                "decorator": decorator_name,
                "func_name": func.__name__,
                "hint": f"Use the async_* variant instead of {decorator_name}",
            },
        )


def trace_span[F: _Function](
    name: str | None = None,
    *,
    kind: Any | None = None,
    attributes: dict[str, Any] | None = None,
    capture_args: list[str] | None = None,
) -> Callable[[F], Callable[..., Any]]:
    """Decorate a sync function with an OpenTelemetry child span.

    Args:
        name: Span name. Defaults to the function name.
        kind: OpenTelemetry ``SpanKind``. Defaults to ``SpanKind.INTERNAL``.
        attributes: Optional static attributes set on the span.
        capture_args: Parameter names whose call values are recorded as attributes.
            Sensitive names (password, token, …) are redacted to ``***``.

    Returns:
        A decorator that wraps the target function in a span.

    Raises:
        InvalidArgumentError: If the decorated object is a coroutine function.

    Example:
        ```python
        @trace_span(name="load_user", capture_args=["user_id"])
        def load_user(user_id: int) -> dict[str, Any]:
            return {"id": user_id}
        ```
    """

    def decorator(func: F) -> Callable[..., Any]:
        _reject_coroutine_function(func, "trace_span")
        span_name = name or func.__name__
        signature = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return _run_traced(
                func,
                args,
                kwargs,
                span_name=span_name,
                kind=kind,
                attributes=attributes,
                capture_args=capture_args,
                signature=signature,
                root=False,
            )

        return wrapper

    return decorator


def async_trace_span[F: _AsyncFunction](
    name: str | None = None,
    *,
    kind: Any | None = None,
    attributes: dict[str, Any] | None = None,
    capture_args: list[str] | None = None,
) -> Callable[[F], Callable[..., Coroutine[Any, Any, Any]]]:
    """Decorate an async function with an OpenTelemetry child span.

    Args:
        name: Span name. Defaults to the function name.
        kind: OpenTelemetry ``SpanKind``. Defaults to ``SpanKind.INTERNAL``.
        attributes: Optional static attributes set on the span.
        capture_args: Parameter names whose call values are recorded as attributes.
            Sensitive names (password, token, …) are redacted to ``***``.

    Returns:
        A decorator that wraps the target coroutine function in a span.

    Raises:
        InvalidArgumentError: If the decorated object is not a coroutine function.
    """

    def decorator(func: F) -> Callable[..., Coroutine[Any, Any, Any]]:
        if not inspect.iscoroutinefunction(func):
            raise InvalidArgumentError(
                argument_name="func",
                additional_data={
                    "decorator": "async_trace_span",
                    "func_name": func.__name__,
                },
            )

        span_name = name or func.__name__
        signature = inspect.signature(func)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _run_traced_async(
                func,
                args,
                kwargs,
                span_name=span_name,
                kind=kind,
                attributes=attributes,
                capture_args=capture_args,
                signature=signature,
                root=False,
            )

        return wrapper

    return decorator


def trace_root[F: _Function](
    name: str | None = None,
    *,
    kind: Any | None = None,
    attributes: dict[str, Any] | None = None,
    capture_args: list[str] | None = None,
) -> Callable[[F], Callable[..., Any]]:
    """Decorate a sync function with a root OpenTelemetry span.

    Starts the span with a fresh context detached from any parent span
    (``INVALID_SPAN`` context).

    Args:
        name: Span name. Defaults to the function name.
        kind: OpenTelemetry ``SpanKind``. Defaults to ``SpanKind.INTERNAL``.
        attributes: Optional static attributes set on the span.
        capture_args: Parameter names whose call values are recorded as attributes.
            Sensitive names (password, token, …) are redacted to ``***``.

    Returns:
        A decorator that wraps the target function in a root span.

    Raises:
        InvalidArgumentError: If the decorated object is a coroutine function.
    """

    def decorator(func: F) -> Callable[..., Any]:
        _reject_coroutine_function(func, "trace_root")
        span_name = name or func.__name__
        signature = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return _run_traced(
                func,
                args,
                kwargs,
                span_name=span_name,
                kind=kind,
                attributes=attributes,
                capture_args=capture_args,
                signature=signature,
                root=True,
            )

        return wrapper

    return decorator


def async_trace_root[F: _AsyncFunction](
    name: str | None = None,
    *,
    kind: Any | None = None,
    attributes: dict[str, Any] | None = None,
    capture_args: list[str] | None = None,
) -> Callable[[F], Callable[..., Coroutine[Any, Any, Any]]]:
    """Decorate an async function with a root OpenTelemetry span.

    Starts the span with a fresh context detached from any parent span
    (``INVALID_SPAN`` context).

    Args:
        name: Span name. Defaults to the function name.
        kind: OpenTelemetry ``SpanKind``. Defaults to ``SpanKind.INTERNAL``.
        attributes: Optional static attributes set on the span.
        capture_args: Parameter names whose call values are recorded as attributes.
            Sensitive names (password, token, …) are redacted to ``***``.

    Returns:
        A decorator that wraps the target coroutine function in a root span.

    Raises:
        InvalidArgumentError: If the decorated object is not a coroutine function.
    """

    def decorator(func: F) -> Callable[..., Coroutine[Any, Any, Any]]:
        if not inspect.iscoroutinefunction(func):
            raise InvalidArgumentError(
                argument_name="func",
                additional_data={
                    "decorator": "async_trace_root",
                    "func_name": func.__name__,
                },
            )

        span_name = name or func.__name__
        signature = inspect.signature(func)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _run_traced_async(
                func,
                args,
                kwargs,
                span_name=span_name,
                kind=kind,
                attributes=attributes,
                capture_args=capture_args,
                signature=signature,
                root=True,
            )

        return wrapper

    return decorator


def _wrap_method(
    cls: type,
    method_name: str,
    func: Callable[..., Any],
    *,
    capture_args: list[str] | None,
) -> Callable[..., Any]:
    """Wrap a class method with a sync or async OpenTelemetry span.

    Args:
        cls: The class that owns the method (used for span naming).
        method_name: The method attribute name.
        func: The underlying function to wrap.
        capture_args: Optional argument names to record as span attributes.

    Returns:
        The wrapped callable.
    """
    span_name = f"{cls.__name__}.{method_name}"
    signature = inspect.signature(func)
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await _run_traced_async(
                func,
                args,
                kwargs,
                span_name=span_name,
                kind=None,
                attributes=None,
                capture_args=capture_args,
                signature=signature,
                root=False,
            )

        return async_wrapper

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        return _run_traced(
            func,
            args,
            kwargs,
            span_name=span_name,
            kind=None,
            attributes=None,
            capture_args=capture_args,
            signature=signature,
            root=False,
        )

    return sync_wrapper


def trace_class(
    *,
    exclude: list[str] | None = None,
    capture_args: list[str] | None = None,
) -> Callable[[type], type]:
    """Decorate a class so public methods are wrapped with OpenTelemetry spans.

    Skips names starting with ``_``, dunder methods, and ``property`` attributes.
    ``staticmethod`` and ``classmethod`` wrappers are preserved after wrapping
    the underlying function. Span names use ``ClassName.method_name``.

    Args:
        exclude: Method names to leave unwrapped.
        capture_args: Parameter names recorded as span attributes on all wrapped methods.
            Sensitive names (password, token, …) are redacted to ``***``.

    Returns:
        A class decorator.

    Example:
        ```python
        @trace_class(exclude=["helper"], capture_args=["user_id"])
        class UserService:
            def get_user(self, user_id: int) -> dict[str, Any]:
                return {"id": user_id}
        ```
    """
    excluded = set(exclude or [])

    def decorator(cls: type) -> type:
        for method_name, attr in list(vars(cls).items()):
            if method_name.startswith("_") or method_name in excluded:
                continue
            if isinstance(attr, property):
                continue

            if isinstance(attr, staticmethod):
                wrapped = _wrap_method(cls, method_name, attr.__func__, capture_args=capture_args)
                setattr(cls, method_name, staticmethod(wrapped))
            elif isinstance(attr, classmethod):
                wrapped = _wrap_method(cls, method_name, attr.__func__, capture_args=capture_args)
                setattr(cls, method_name, classmethod(wrapped))
            elif callable(attr):
                setattr(cls, method_name, _wrap_method(cls, method_name, attr, capture_args=capture_args))

        return cls

    return decorator
