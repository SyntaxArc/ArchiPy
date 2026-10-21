"""Temporal OpenTelemetry tracing interceptor that marks activity spans as messaging operations.

The stock ``temporalio.contrib.opentelemetry.TracingInterceptor`` opens the ``RunActivity:*`` span as a SERVER span
carrying only the ``temporalActivityID``, ``temporalWorkflowID`` and ``temporalRunID`` attributes. Elastic APM derives
``transaction.type`` from HTTP, RPC or messaging attributes and falls back to ``unknown`` when there are none, so every
Temporal activity shows up with the type ``unknown``. Activities are consumed from a task queue, so the span is marked
as a messaging ``process`` operation.
"""

from __future__ import annotations

from typing import Any, override

from opentelemetry import trace
from temporalio import activity
from temporalio.contrib.opentelemetry import TracingInterceptor
from temporalio.worker import ActivityInboundInterceptor, ExecuteActivityInput


class _MessagingActivityInterceptor(ActivityInboundInterceptor):
    """Adds messaging attributes to the ``RunActivity`` span that ``TracingInterceptor`` opened around it."""

    @override
    async def execute_activity(self, input: ExecuteActivityInput) -> Any:
        """Set the messaging attributes on the current span, then run the activity.

        Args:
            input (ExecuteActivityInput): The activity invocation.

        Returns:
            Any: The activity result.
        """
        span = trace.get_current_span()
        span.set_attribute("messaging.system", "temporal")
        span.set_attribute("messaging.operation", "process")
        span.set_attribute("messaging.destination.name", activity.info().task_queue)
        return await super().execute_activity(input)


class ArchiPyTracingInterceptor(TracingInterceptor):
    """``TracingInterceptor`` whose activity spans carry messaging attributes."""

    @override
    def intercept_activity(self, next: ActivityInboundInterceptor) -> ActivityInboundInterceptor:
        """Wrap the next activity interceptor so it runs inside the span opened by ``TracingInterceptor``.

        Args:
            next (ActivityInboundInterceptor): The next interceptor in the chain.

        Returns:
            ActivityInboundInterceptor: ``TracingInterceptor``'s span-opening interceptor around the messaging one.
        """
        return super().intercept_activity(_MessagingActivityInterceptor(next))
