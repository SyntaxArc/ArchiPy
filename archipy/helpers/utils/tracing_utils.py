"""Elastic APM and Sentry tracing helpers (distributed trace propagation, gRPC outcomes)."""

from __future__ import annotations

import functools
import logging
import threading
from collections.abc import Sequence
from typing import Any

from archipy.configs.base_config import BaseConfig

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def _grpc_status_outcome_map() -> dict[Any, Any]:
    """Build gRPC status to Elastic OUTCOME mapping (lazy import of grpc)."""
    import grpc
    from elasticapm.conf.constants import OUTCOME

    return {
        grpc.StatusCode.OK: OUTCOME.SUCCESS,
        grpc.StatusCode.CANCELLED: OUTCOME.SUCCESS,
        grpc.StatusCode.UNKNOWN: OUTCOME.FAILURE,
        grpc.StatusCode.INVALID_ARGUMENT: OUTCOME.SUCCESS,
        grpc.StatusCode.DEADLINE_EXCEEDED: OUTCOME.FAILURE,
        grpc.StatusCode.NOT_FOUND: OUTCOME.SUCCESS,
        grpc.StatusCode.ALREADY_EXISTS: OUTCOME.SUCCESS,
        grpc.StatusCode.PERMISSION_DENIED: OUTCOME.SUCCESS,
        grpc.StatusCode.RESOURCE_EXHAUSTED: OUTCOME.FAILURE,
        grpc.StatusCode.FAILED_PRECONDITION: OUTCOME.FAILURE,
        grpc.StatusCode.ABORTED: OUTCOME.FAILURE,
        grpc.StatusCode.OUT_OF_RANGE: OUTCOME.SUCCESS,
        # Intentionally FAILURE (not elasticapm.contrib.grpc default): UNIMPLEMENTED is a server error (HTTP 501).
        grpc.StatusCode.UNIMPLEMENTED: OUTCOME.FAILURE,
        grpc.StatusCode.INTERNAL: OUTCOME.FAILURE,
        grpc.StatusCode.UNAVAILABLE: OUTCOME.FAILURE,
        grpc.StatusCode.DATA_LOSS: OUTCOME.FAILURE,
        grpc.StatusCode.UNAUTHENTICATED: OUTCOME.SUCCESS,
    }


class TracingUtils:
    """Static helpers for Elastic APM and Sentry distributed tracing.

    Provides idempotent client initialization, gRPC metadata propagation
    (W3C trace context and Sentry ``sentry-trace`` / ``baggage``), inbound trace
    extraction, and gRPC status to APM outcome mapping aligned with
    ``elasticapm.contrib.grpc``.
    """

    SENTRY_TRACE_HEADER = "sentry-trace"
    BAGGAGE_HEADER = "baggage"
    _lock = threading.Lock()

    @staticmethod
    def is_tracing_enabled(config: BaseConfig) -> bool:
        """Return True when either Sentry or Elastic APM tracing is enabled.

        Args:
            config: Application configuration.

        Returns:
            True if Sentry or Elastic APM is enabled for tracing.
        """
        return bool(config.SENTRY.IS_ENABLED or config.ELASTIC_APM.IS_ENABLED)

    @staticmethod
    def init_tracing_if_needed(config: BaseConfig) -> None:
        """Initialize Sentry and Elastic APM clients once (idempotent, thread-safe).

        Safe to call from interceptors, decorators, or app startup. Uses lazy imports
        so optional extras are not required at import time.

        Args:
            config: Application configuration.
        """
        with TracingUtils._lock:
            if config.SENTRY.IS_ENABLED:
                try:
                    import sentry_sdk

                    if not sentry_sdk.is_initialized():
                        sentry_sdk.init(
                            dsn=config.SENTRY.DSN,
                            debug=config.SENTRY.DEBUG,
                            release=config.SENTRY.RELEASE,
                            sample_rate=config.SENTRY.SAMPLE_RATE,
                            traces_sample_rate=config.SENTRY.TRACES_SAMPLE_RATE,
                            environment=config.ENVIRONMENT,
                        )
                except ImportError:
                    logger.debug("sentry_sdk is not installed, skipping Sentry initialization.")
                except Exception:
                    logger.exception("Failed to initialize Sentry")

            if config.ELASTIC_APM.IS_ENABLED:
                try:
                    import elasticapm

                    if elasticapm.get_client() is None:
                        elasticapm.Client(config.ELASTIC_APM.model_dump())
                        elasticapm.instrument()
                except ImportError:
                    logger.debug("elasticapm is not installed, skipping Elastic APM initialization.")
                except Exception:
                    logger.exception("Failed to initialize Elastic APM client")

    @staticmethod
    def grpc_status_indicates_success(status_code: Any) -> bool:
        """Map a gRPC status code to success vs failure for APM/Sentry outcomes.

        Mostly aligned with ``elasticapm.contrib.grpc.utils.STATUS_TO_OUTCOME``;
        ``UNIMPLEMENTED`` is treated as failure (server error).

        Args:
            status_code: A ``grpc.StatusCode`` value.

        Returns:
            True when the status should be treated as a successful outcome.
        """
        from elasticapm.conf.constants import OUTCOME

        outcome = _grpc_status_outcome_map().get(status_code, OUTCOME.SUCCESS)
        return outcome is OUTCOME.SUCCESS

    @staticmethod
    def _metadata_key_set(metadata: Sequence[tuple[str, str | bytes]]) -> set[str]:
        """Return lowercase keys present in gRPC metadata."""
        keys: set[str] = set()
        for item in metadata:
            if not item:
                continue
            keys.add(str(item[0]).lower())
        return keys

    @staticmethod
    def inject_outbound_metadata(
        metadata: Sequence[tuple[str, str | bytes]] | Any | None,
        apm_span: Any,
        *,
        include_sentry: bool = True,
    ) -> list[tuple[str, str | bytes]]:
        """Append trace propagation headers to gRPC client metadata.

        Adds W3C ``traceparent`` / ``tracestate`` from the current Elastic span when
        available, and ``sentry-trace`` / ``baggage`` when Sentry is initialized.
        Skips headers whose keys are already present (case-insensitive).

        Args:
            metadata: Existing metadata tuples, or None.
            apm_span: Current Elastic APM span from ``capture_span``, or ``DroppedSpan``.
            include_sentry: When False, only Elastic headers are considered.

        Returns:
            A new metadata list suitable for ``ClientCallDetails``.
        """
        from elasticapm.conf import constants
        from elasticapm.traces import DroppedSpan

        meta: list[tuple[str, str | bytes]] = list(metadata) if metadata else []
        keys = TracingUtils._metadata_key_set(meta)

        if constants.TRACEPARENT_HEADER_NAME.lower() not in keys:
            if apm_span is not None and not isinstance(apm_span, DroppedSpan):
                transaction = getattr(apm_span, "transaction", None)
                if transaction is not None:
                    trace_parent = transaction.trace_parent.copy_from(span_id=apm_span.id)
                    meta.append((constants.TRACEPARENT_HEADER_NAME, trace_parent.to_string()))
                    tracestate = trace_parent.tracestate
                    if tracestate and constants.TRACESTATE_HEADER_NAME.lower() not in keys:
                        meta.append((constants.TRACESTATE_HEADER_NAME, tracestate))
                    keys = TracingUtils._metadata_key_set(meta)

        if include_sentry:
            try:
                import sentry_sdk

                if sentry_sdk.is_initialized():
                    if TracingUtils.SENTRY_TRACE_HEADER.lower() not in keys:
                        traceparent = sentry_sdk.get_traceparent()
                        if traceparent:
                            meta.append((TracingUtils.SENTRY_TRACE_HEADER, traceparent))
                            keys = TracingUtils._metadata_key_set(meta)
                    if TracingUtils.BAGGAGE_HEADER.lower() not in keys:
                        baggage = sentry_sdk.get_baggage()
                        if baggage:
                            meta.append((TracingUtils.BAGGAGE_HEADER, baggage))
            except ImportError:
                logger.debug("sentry_sdk is not installed, skipping Sentry trace header injection.")

        return meta

    @staticmethod
    def extract_inbound_trace(metadata_dict: dict[str, str]) -> tuple[Any | None, dict[str, str]]:
        """Parse distributed trace context from inbound gRPC metadata.

        Args:
            metadata_dict: Lowercase or mixed-case keys merged to lookup-friendly dict.

        Returns:
            A tuple of ``(elastic_trace_parent | None, sentry_header_dict)`` where
            ``sentry_header_dict`` contains keys suitable for ``sentry_sdk.continue_trace``.
            ``elastic_trace_parent`` is None when ``elasticapm`` is not installed.
        """
        parent: Any | None = None
        try:
            import elasticapm

            parent = elasticapm.trace_parent_from_headers(metadata_dict)
        except ImportError:
            logger.debug("elasticapm is not installed, skipping Elastic trace parent extraction.")

        sentry_headers: dict[str, str] = {}
        for key, value in metadata_dict.items():
            lk = key.lower()
            if lk == TracingUtils.SENTRY_TRACE_HEADER.lower():
                sentry_headers[TracingUtils.SENTRY_TRACE_HEADER] = value
            elif lk == TracingUtils.BAGGAGE_HEADER.lower():
                sentry_headers[TracingUtils.BAGGAGE_HEADER] = value

        return parent, sentry_headers
