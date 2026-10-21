"""Temporal OpenTelemetry tracing interceptor that marks activity and workflow spans as messaging operations.

The stock ``temporalio.contrib.opentelemetry.OpenTelemetryInterceptor`` opens the ``RunActivity:*`` and
``RunWorkflow:*`` spans as SERVER spans carrying only the Temporal id attributes. Elastic APM derives
``transaction.type`` from HTTP, RPC or messaging attributes and falls back to ``unknown`` when there are none, so every
Temporal activity and workflow shows up with the type ``unknown``. Activities and workflow tasks are consumed from a
task queue, so their spans are marked as a messaging ``process`` operation.
"""

from __future__ import annotations

import dataclasses
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, override

from opentelemetry import trace
from temporalio import activity, workflow
from temporalio.contrib.opentelemetry import OpenTelemetryInterceptor
from temporalio.plugin import SimplePlugin
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    WorkflowInterceptorClassInput,
    WorkflowRunner,
)
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

from archipy.models.errors import InvalidArgumentError

if TYPE_CHECKING:
    from collections.abc import Generator


def _set_messaging_attributes(task_queue: str) -> None:
    """Mark the current span as a messaging ``process`` operation on the given task queue.

    Args:
        task_queue (str): The Temporal task queue the activity or workflow task was consumed from.
    """
    span = trace.get_current_span()
    span.set_attribute("messaging.system", "temporal")
    # ``messaging.operation`` is deprecated for ``messaging.operation.type``; backends still read the old key.
    span.set_attribute("messaging.operation", "process")
    span.set_attribute("messaging.operation.type", "process")
    span.set_attribute("messaging.destination.name", task_queue)


class _MessagingActivityInterceptor(ActivityInboundInterceptor):
    """Adds messaging attributes to the ``RunActivity`` span that ``OpenTelemetryInterceptor`` opened around it."""

    @override
    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        """Set the messaging attributes on the current span, then run the activity.

        Args:
            input (ExecuteActivityInput): The activity invocation.

        Returns:
            Any: The activity result.
        """
        _set_messaging_attributes(activity.info().task_queue)
        return await super().execute_activity(input)


class MessagingOpenTelemetryInterceptor(OpenTelemetryInterceptor):
    """``OpenTelemetryInterceptor`` that emits Temporal spans, with messaging attributes on activity and workflow spans.

    ``OpenTelemetryInterceptor`` only opens ``StartActivity`` / ``RunActivity`` spans when ``add_temporal_spans`` is
    set, so it is on by default here. The global tracer provider must be a ``ReplaySafeTracerProvider``; ArchiPy's
    OpenTelemetry runtime builds one when ``temporalio`` is installed.
    """

    def __init__(self, add_temporal_spans: bool = True) -> None:
        """Initialize the interceptor.

        Args:
            add_temporal_spans (bool): Whether to open the ``StartWorkflow``, ``RunActivity``, etc. spans.
        """
        super().__init__(add_temporal_spans)

    @override
    def intercept_activity(self, next: ActivityInboundInterceptor) -> ActivityInboundInterceptor:
        """Wrap the next activity interceptor so it runs inside the span opened by ``OpenTelemetryInterceptor``.

        Args:
            next (ActivityInboundInterceptor): The next interceptor in the chain.

        Returns:
            ActivityInboundInterceptor: The span-opening interceptor around the messaging one.
        """
        return super().intercept_activity(_MessagingActivityInterceptor(next))

    @override
    def workflow_interceptor_class(self, input: WorkflowInterceptorClassInput) -> Any:
        """Return the workflow interceptor class whose ``RunWorkflow`` / ``Handle*`` spans carry messaging attributes.

        ``OpenTelemetryInterceptor`` opens those spans in ``_workflow_maybe_span``; the subclass marks the span once it
        is open. On replay the span is not recording, so the attributes are a no-op.

        Args:
            input (WorkflowInterceptorClassInput): The workflow interceptor class input.

        Returns:
            Any: The ``OpenTelemetryInterceptor`` workflow interceptor class, extended with the messaging attributes.
        """
        base = super().workflow_interceptor_class(input)

        class MessagingWorkflowInterceptor(base):  # ty: ignore[unsupported-base]
            @contextmanager
            def _workflow_maybe_span(self, name: str) -> Generator[None]:
                with super()._workflow_maybe_span(name):
                    _set_messaging_attributes(workflow.info().task_queue)
                    yield

        return MessagingWorkflowInterceptor


def _allow_opentelemetry_in_sandbox(runner: WorkflowRunner | None) -> WorkflowRunner:
    """Pass ``opentelemetry`` through the workflow sandbox, as the stock ``OpenTelemetryPlugin`` does.

    Args:
        runner (WorkflowRunner | None): The worker's workflow runner.

    Returns:
        WorkflowRunner: The runner, with ``opentelemetry`` passed through when it is sandboxed.

    Raises:
        InvalidArgumentError: If no workflow runner is provided.
    """
    if not runner:
        raise InvalidArgumentError(argument_name="workflow_runner")
    if isinstance(runner, SandboxedWorkflowRunner):
        return dataclasses.replace(
            runner,
            restrictions=runner.restrictions.with_passthrough_modules("opentelemetry"),
        )
    return runner


class MessagingOpenTelemetryPlugin(SimplePlugin):
    """Temporal plugin that traces with ``MessagingOpenTelemetryInterceptor``.

    It replaces the stock ``OpenTelemetryPlugin`` rather than extending it, so it carries its own name and is not
    registered twice next to it. Register it on the client with ``Client.connect(plugins=[...])``; workers created
    from that client inherit it.
    """

    def __init__(self, *, add_temporal_spans: bool = True) -> None:
        """Initialize the plugin.

        Args:
            add_temporal_spans (bool): Whether to open the ``StartWorkflow``, ``RunActivity``, etc. spans.
        """
        super().__init__(
            "MessagingOpenTelemetryPlugin",
            interceptors=[MessagingOpenTelemetryInterceptor(add_temporal_spans)],
            workflow_runner=_allow_opentelemetry_in_sandbox,
        )
