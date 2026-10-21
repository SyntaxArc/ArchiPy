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
from temporalio.client import (
    ActivityHandle,
    OutboundInterceptor,
    QueryWorkflowInput,
    SignalWorkflowInput,
    StartActivityInput as ClientStartActivityInput,
    StartWorkflowInput,
    StartWorkflowUpdateInput,
    StartWorkflowUpdateWithStartInput,
    WorkflowHandle,
    WorkflowUpdateHandle,
)
from temporalio.contrib.opentelemetry import OpenTelemetryInterceptor
from temporalio.plugin import SimplePlugin
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    StartActivityInput,
    StartChildWorkflowInput,
    WorkflowInterceptorClassInput,
    WorkflowOutboundInterceptor,
    WorkflowRunner,
)
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

from archipy.models.errors import ConfigurationError, InvalidArgumentError

if TYPE_CHECKING:
    from collections.abc import Generator


def _set_messaging_attributes(task_queue: str | None, operation: str = "process") -> None:
    """Mark the current span as a messaging operation, on the given task queue when there is one.

    Args:
        task_queue (str | None): The Temporal task queue the work was consumed from (``process``) or dispatched to
            (``send``). ``None`` for calls addressed to a workflow id, whose destination is left out: Elastic APM
            turns it into a service-map node, and workflow ids are unbounded.
        operation (str): The messaging operation, ``process`` for the worker side or ``send`` for the starting side.
    """
    span = trace.get_current_span()
    span.set_attribute("messaging.system", "temporal")
    # ``messaging.operation`` is deprecated for ``messaging.operation.type``; backends still read the old key.
    span.set_attribute("messaging.operation", operation)
    span.set_attribute("messaging.operation.type", operation)
    if task_queue is not None:
        span.set_attribute("messaging.destination.name", task_queue)


class _MessagingClientInterceptor(OutboundInterceptor):
    """Adds ``send`` attributes to the client spans that ``OpenTelemetryInterceptor`` opened around the call."""

    @override
    async def start_workflow(self, input: StartWorkflowInput) -> WorkflowHandle[Any, Any]:
        """Mark the ``StartWorkflow`` span as a send to the workflow task queue.

        Args:
            input (StartWorkflowInput): The start workflow input.

        Returns:
            WorkflowHandle[Any, Any]: The handle of the started workflow.
        """
        _set_messaging_attributes(input.task_queue, "send")
        return await super().start_workflow(input)

    @override
    async def signal_workflow(self, input: SignalWorkflowInput) -> None:
        """Mark the ``SignalWorkflow`` span as a send to a running workflow.

        Args:
            input (SignalWorkflowInput): The signal input.
        """
        _set_messaging_attributes(None, "send")
        await super().signal_workflow(input)

    @override
    async def query_workflow(self, input: QueryWorkflowInput) -> Any:
        """Mark the ``QueryWorkflow`` span as a send to a running workflow.

        Args:
            input (QueryWorkflowInput): The query input.

        Returns:
            Any: The query result.
        """
        _set_messaging_attributes(None, "send")
        return await super().query_workflow(input)

    @override
    async def start_workflow_update(self, input: StartWorkflowUpdateInput) -> WorkflowUpdateHandle[Any]:
        """Mark the ``StartWorkflowUpdate`` span as a send to a running workflow.

        Args:
            input (StartWorkflowUpdateInput): The update input.

        Returns:
            WorkflowUpdateHandle[Any]: The handle of the started update.
        """
        _set_messaging_attributes(None, "send")
        return await super().start_workflow_update(input)

    @override
    async def start_update_with_start_workflow(
        self,
        input: StartWorkflowUpdateWithStartInput,
    ) -> WorkflowUpdateHandle[Any]:
        """Mark the ``StartUpdateWithStartWorkflow`` span as a send to the workflow task queue.

        Args:
            input (StartWorkflowUpdateWithStartInput): The update-with-start input.

        Returns:
            WorkflowUpdateHandle[Any]: The handle of the started update.
        """
        _set_messaging_attributes(input.start_workflow_input.task_queue, "send")
        return await super().start_update_with_start_workflow(input)

    @override
    async def start_activity(self, input: ClientStartActivityInput) -> ActivityHandle[Any]:
        """Mark the client ``StartActivity`` span as a send to the activity task queue.

        Args:
            input (ClientStartActivityInput): The standalone start activity input.

        Returns:
            ActivityHandle[Any]: The handle of the started activity.
        """
        _set_messaging_attributes(input.task_queue, "send")
        return await super().start_activity(input)


class _MessagingWorkflowOutboundInterceptor(WorkflowOutboundInterceptor):
    """Adds ``send`` attributes to the ``StartActivity`` / ``StartChildWorkflow`` spans opened around it."""

    @override
    def start_activity(self, input: StartActivityInput) -> Any:
        """Mark the ``StartActivity`` span as a send to the activity task queue.

        Args:
            input (StartActivityInput): The start activity input; no task queue means the workflow's own.

        Returns:
            Any: The activity handle.
        """
        _set_messaging_attributes(input.task_queue or workflow.info().task_queue, "send")
        return super().start_activity(input)

    @override
    async def start_child_workflow(self, input: StartChildWorkflowInput) -> Any:
        """Mark the ``StartChildWorkflow`` span as a send to the child's task queue.

        Args:
            input (StartChildWorkflowInput): The start child workflow input; no task queue means the workflow's own.

        Returns:
            Any: The child workflow handle.
        """
        _set_messaging_attributes(input.task_queue or workflow.info().task_queue, "send")
        return await super().start_child_workflow(input)


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
        # Without spans the current span belongs to the caller (e.g. an HTTP request), which must stay untouched.
        self._mark_spans = add_temporal_spans

    @override
    def intercept_client(self, next: OutboundInterceptor) -> OutboundInterceptor:
        """Wrap the next client interceptor so it runs inside the ``StartWorkflow`` span.

        Args:
            next (OutboundInterceptor): The next interceptor in the chain.

        Returns:
            OutboundInterceptor: The span-opening interceptor, around the messaging one when spans are enabled.
        """
        return super().intercept_client(_MessagingClientInterceptor(next) if self._mark_spans else next)

    @override
    def intercept_activity(self, next: ActivityInboundInterceptor) -> ActivityInboundInterceptor:
        """Wrap the next activity interceptor so it runs inside the span opened by ``OpenTelemetryInterceptor``.

        Args:
            next (ActivityInboundInterceptor): The next interceptor in the chain.

        Returns:
            ActivityInboundInterceptor: The span-opening interceptor around the messaging one.
        """
        return super().intercept_activity(_MessagingActivityInterceptor(next) if self._mark_spans else next)

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
        if not hasattr(base, "_workflow_maybe_span"):
            raise ConfigurationError(
                operation="workflow_interceptor_class",
                reason="temporalio no longer provides `_workflow_maybe_span`; update MessagingOpenTelemetryInterceptor",
            )
        mark_spans = self._mark_spans

        class MessagingWorkflowInterceptor(base):  # ty: ignore[unsupported-base]
            @override
            def init(self, outbound: WorkflowOutboundInterceptor) -> None:
                super().init(_MessagingWorkflowOutboundInterceptor(outbound) if mark_spans else outbound)

            @contextmanager
            def _workflow_maybe_span(self, *args: Any, **kwargs: Any) -> Generator[None]:
                with super()._workflow_maybe_span(*args, **kwargs):
                    if mark_spans:
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
