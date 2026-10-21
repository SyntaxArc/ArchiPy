"""Prometheus pull scrape server and Pushgateway push loop for the OpenTelemetry metrics registry."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wsgiref.simple_server import WSGIServer

    from prometheus_client import CollectorRegistry

    from archipy.configs.config_template import OpentelemetryConfig
    from archipy.helpers.utils._otel.provider_types import OwnedMeterProvider

# Same logger as OtelUtils, so log filters and handlers that name it keep seeing these records.
logger = logging.getLogger("archipy.helpers.utils.otel_utils")


class MetricsExport:
    """State and workers of the two Prometheus metrics export modes of one runtime.

    The runtime owns the lock and calls the ``*_unlocked`` methods with it held. The pull scrape server and the
    Pushgateway loop share one registry, which is dropped only when neither of them still owns it.
    """

    def __init__(self) -> None:
        self.registry: CollectorRegistry | None = None
        self._pull_httpd: WSGIServer | None = None
        self._pull_thread: threading.Thread | None = None
        self._owns_pull_scrape = False
        self._pushgateway_stop: threading.Event | None = None
        self._pushgateway_thread: threading.Thread | None = None
        self._pushgateway_config: dict[str, Any] | None = None
        self._owns_pushgateway = False

    def drop_handles(self) -> None:
        """Forget the registry, servers and threads without stopping them, as a forked child must."""
        self._pull_httpd = None
        self._pull_thread = None
        self.registry = None
        self._owns_pull_scrape = False
        self._pushgateway_stop = None
        self._pushgateway_thread = None
        self._pushgateway_config = None
        self._owns_pushgateway = False

    def maybe_start_pull_scrape_unlocked(
        self,
        otel: OpentelemetryConfig,
        *,
        owns_meter: bool,
        new_meter: OwnedMeterProvider | None,
    ) -> None:
        """Start pull scrape when owned; leave providers intact on bind failure."""
        if not (otel.METRICS_ENABLED and otel.METRICS_EXPORTER == "pull"):
            return
        if not (owns_meter and new_meter is not None):
            logger.warning(
                "METRICS_EXPORTER=pull but the MeterProvider was adopted; "
                "ArchiPy metrics pull scrape server is not started for this process",
            )
            return
        try:
            self.start_pull_scrape_unlocked(otel)
        except Exception:
            logger.warning(
                "Metrics pull scrape server failed to start on %s:%s; "
                "continuing without scrape (traces/logs/metrics providers remain active)",
                otel.METRICS_PULL_HOST,
                otel.METRICS_PULL_PORT,
                exc_info=True,
            )
            self._pull_httpd = None
            self._pull_thread = None
            self._owns_pull_scrape = False

    def maybe_start_pushgateway_unlocked(
        self,
        otel: OpentelemetryConfig,
        *,
        owns_meter: bool,
        new_meter: OwnedMeterProvider | None,
    ) -> None:
        """Start Pushgateway push loop when owned; never raise into the app."""
        if not (otel.METRICS_ENABLED and otel.METRICS_EXPORTER == "pushgateway"):
            return
        if not (owns_meter and new_meter is not None):
            logger.warning(
                "METRICS_EXPORTER=pushgateway but the MeterProvider was adopted; "
                "ArchiPy Pushgateway push loop is not started for this process",
            )
            return
        try:
            self.start_pushgateway_unlocked(otel)
        except Exception:
            logger.warning(
                "Metrics Pushgateway push loop failed to start; "
                "continuing without push (traces/logs/metrics providers remain active)",
                exc_info=True,
            )
            self.stop_pushgateway_unlocked(delete_group=False)

    def start_pull_scrape_unlocked(self, otel: OpentelemetryConfig) -> None:
        """Start the metrics pull scrape HTTP server if not already running."""
        if self._pull_httpd is not None:
            return
        from prometheus_client import start_http_server

        registry = self.registry
        if registry is None:
            msg = "Metrics pull registry missing before scrape server start"
            raise RuntimeError(msg)

        httpd, thread = start_http_server(
            int(otel.METRICS_PULL_PORT),
            addr=str(otel.METRICS_PULL_HOST),
            registry=registry,
        )
        self._pull_httpd = httpd
        self._pull_thread = thread
        self._owns_pull_scrape = True
        logger.info(
            "Metrics pull scrape server listening on http://%s:%s/metrics",
            otel.METRICS_PULL_HOST,
            otel.METRICS_PULL_PORT,
        )

    def stop_pull_scrape_unlocked(self) -> None:
        """Stop the ArchiPy-owned metrics pull scrape HTTP server."""
        if not self._owns_pull_scrape:
            self._pull_httpd = None
            self._pull_thread = None
            # Keep registry when pushgateway (or another owner) still needs it.
            if not self._owns_pushgateway:
                self.registry = None
            return
        httpd = self._pull_httpd
        if httpd is not None:
            try:
                httpd.shutdown()
            except Exception:
                logger.debug("Error shutting down metrics pull scrape server", exc_info=True)
            try:
                httpd.server_close()
            except Exception:
                logger.debug("Error closing metrics pull scrape server socket", exc_info=True)
        self._pull_httpd = None
        self._pull_thread = None
        if not self._owns_pushgateway:
            self.registry = None
        self._owns_pull_scrape = False

    def start_pushgateway_unlocked(self, otel: OpentelemetryConfig) -> None:
        """Start the daemon thread that pushes metrics to Prometheus Pushgateway."""
        if self._pushgateway_thread is not None and self._pushgateway_thread.is_alive():
            return
        registry = self.registry
        if registry is None:
            msg = "Metrics registry missing before Pushgateway start"
            raise RuntimeError(msg)

        gateway_url = str(otel.METRICS_PUSHGATEWAY_URL or "").strip()
        if not gateway_url:
            msg = "METRICS_PUSHGATEWAY_URL is required when METRICS_EXPORTER=pushgateway"
            raise RuntimeError(msg)

        job = str(otel.METRICS_PUSHGATEWAY_JOB or otel.SERVICE_NAME or "archipy").strip() or "archipy"
        grouping_key = dict(otel.METRICS_PUSHGATEWAY_GROUPING_KEY or {})
        interval = int(otel.METRICS_PUSHGATEWAY_INTERVAL_SECONDS)
        timeout = float(otel.METRICS_PUSHGATEWAY_TIMEOUT_SECONDS)
        delete_on_shutdown = bool(otel.METRICS_PUSHGATEWAY_DELETE_ON_SHUTDOWN)

        stop_event = threading.Event()
        self._pushgateway_stop = stop_event
        self._pushgateway_config = {
            "gateway": gateway_url,
            "job": job,
            "grouping_key": grouping_key,
            "timeout": timeout,
            "delete_on_shutdown": delete_on_shutdown,
        }

        def _push_once() -> None:
            from prometheus_client import push_to_gateway

            try:
                push_to_gateway(
                    gateway=gateway_url,
                    job=job,
                    registry=registry,
                    grouping_key=grouping_key or None,
                    timeout=timeout,
                )
            except Exception:
                logger.warning(
                    "Failed to push metrics to Pushgateway %s (job=%s)",
                    gateway_url,
                    job,
                    exc_info=True,
                )

        def _push_loop() -> None:
            while True:
                _push_once()
                if stop_event.wait(interval):
                    break
            if not delete_on_shutdown:
                # Keep the last interval's metrics; with delete-on-shutdown the group is removed anyway.
                _push_once()

        thread = threading.Thread(
            target=_push_loop,
            name="archipy-metrics-pushgateway",
            daemon=True,
        )
        thread.start()
        self._pushgateway_thread = thread
        self._owns_pushgateway = True
        logger.info(
            "Metrics Pushgateway push loop started (gateway=%s job=%s interval=%ss)",
            gateway_url,
            job,
            interval,
        )

    def stop_pushgateway_unlocked(self, *, delete_group: bool = True) -> None:
        """Stop the Pushgateway push loop and optionally delete the grouping key."""
        stop_event = self._pushgateway_stop
        thread = self._pushgateway_thread
        config = self._pushgateway_config
        registry = self.registry
        owned = self._owns_pushgateway

        if stop_event is not None:
            stop_event.set()
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)

        should_delete = (
            delete_group
            and owned
            and config is not None
            and bool(config.get("delete_on_shutdown"))
            and registry is not None
        )
        if should_delete:
            try:
                from prometheus_client import delete_from_gateway

                delete_from_gateway(
                    gateway=str(config["gateway"]),
                    job=str(config["job"]),
                    grouping_key=config.get("grouping_key") or None,
                    timeout=float(config.get("timeout") or 10.0),
                )
            except Exception:
                logger.warning("Failed to delete Pushgateway metrics group on shutdown", exc_info=True)

        self._pushgateway_stop = None
        self._pushgateway_thread = None
        self._pushgateway_config = None
        self._owns_pushgateway = False
        if owned and not self._owns_pull_scrape:
            self.registry = None
