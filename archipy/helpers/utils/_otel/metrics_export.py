"""Prometheus pull scrape server and Pushgateway push loop for the OpenTelemetry metrics registry."""

from __future__ import annotations

import logging
import threading
from typing import Any

# Same logger as OtelUtils, so log filters and handlers that name it keep seeing these records.
logger = logging.getLogger("archipy.helpers.utils.otel_utils")


class MetricsExport:
    """State and workers of the two Prometheus metrics export modes.

    ``OtelUtils`` owns the lock and calls the ``*_unlocked`` methods with it held. The pull scrape server and the
    Pushgateway loop share one registry, which is dropped only when neither of them still owns it.
    """

    registry: Any | None = None
    _pull_httpd: Any | None = None
    _pull_thread: Any | None = None
    _owns_pull_scrape: bool = False
    _pushgateway_stop: threading.Event | None = None
    _pushgateway_thread: threading.Thread | None = None
    _pushgateway_config: dict[str, Any] | None = None
    _owns_pushgateway: bool = False

    @classmethod
    def drop_handles(cls) -> None:
        """Forget the registry, servers and threads without stopping them, as a forked child must."""
        cls._pull_httpd = None
        cls._pull_thread = None
        cls.registry = None
        cls._owns_pull_scrape = False
        cls._pushgateway_stop = None
        cls._pushgateway_thread = None
        cls._pushgateway_config = None
        cls._owns_pushgateway = False

    @classmethod
    def maybe_start_pull_scrape_unlocked(
        cls,
        otel: Any,
        *,
        owns_meter: bool,
        new_meter: Any | None,
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
            cls.start_pull_scrape_unlocked(otel)
        except Exception:
            logger.warning(
                "Metrics pull scrape server failed to start on %s:%s; "
                "continuing without scrape (traces/logs/metrics providers remain active)",
                otel.METRICS_PULL_HOST,
                otel.METRICS_PULL_PORT,
                exc_info=True,
            )
            cls._pull_httpd = None
            cls._pull_thread = None
            cls._owns_pull_scrape = False

    @classmethod
    def maybe_start_pushgateway_unlocked(
        cls,
        otel: Any,
        *,
        owns_meter: bool,
        new_meter: Any | None,
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
            cls.start_pushgateway_unlocked(otel)
        except Exception:
            logger.warning(
                "Metrics Pushgateway push loop failed to start; "
                "continuing without push (traces/logs/metrics providers remain active)",
                exc_info=True,
            )
            cls.stop_pushgateway_unlocked(delete_group=False)

    @classmethod
    def start_pull_scrape_unlocked(cls, otel: Any) -> None:
        """Start the metrics pull scrape HTTP server if not already running."""
        if cls._pull_httpd is not None:
            return
        from prometheus_client import start_http_server

        registry = cls.registry
        if registry is None:
            msg = "Metrics pull registry missing before scrape server start"
            raise RuntimeError(msg)

        httpd, thread = start_http_server(
            int(otel.METRICS_PULL_PORT),
            addr=str(otel.METRICS_PULL_HOST),
            registry=registry,
        )
        cls._pull_httpd = httpd
        cls._pull_thread = thread
        cls._owns_pull_scrape = True
        logger.info(
            "Metrics pull scrape server listening on http://%s:%s/metrics",
            otel.METRICS_PULL_HOST,
            otel.METRICS_PULL_PORT,
        )

    @classmethod
    def stop_pull_scrape_unlocked(cls) -> None:
        """Stop the ArchiPy-owned metrics pull scrape HTTP server."""
        if not cls._owns_pull_scrape:
            cls._pull_httpd = None
            cls._pull_thread = None
            # Keep registry when pushgateway (or another owner) still needs it.
            if not cls._owns_pushgateway:
                cls.registry = None
            return
        httpd = cls._pull_httpd
        if httpd is not None:
            try:
                httpd.shutdown()
            except Exception:
                logger.debug("Error shutting down metrics pull scrape server", exc_info=True)
            try:
                httpd.server_close()
            except Exception:
                logger.debug("Error closing metrics pull scrape server socket", exc_info=True)
        cls._pull_httpd = None
        cls._pull_thread = None
        if not cls._owns_pushgateway:
            cls.registry = None
        cls._owns_pull_scrape = False

    @classmethod
    def start_pushgateway_unlocked(cls, otel: Any) -> None:
        """Start the daemon thread that pushes metrics to Prometheus Pushgateway."""
        if cls._pushgateway_thread is not None and cls._pushgateway_thread.is_alive():
            return
        registry = cls.registry
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
        cls._pushgateway_stop = stop_event
        cls._pushgateway_config = {
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
        cls._pushgateway_thread = thread
        cls._owns_pushgateway = True
        logger.info(
            "Metrics Pushgateway push loop started (gateway=%s job=%s interval=%ss)",
            gateway_url,
            job,
            interval,
        )

    @classmethod
    def stop_pushgateway_unlocked(cls, *, delete_group: bool = True) -> None:
        """Stop the Pushgateway push loop and optionally delete the grouping key."""
        stop_event = cls._pushgateway_stop
        thread = cls._pushgateway_thread
        config = cls._pushgateway_config
        registry = cls.registry
        owned = cls._owns_pushgateway

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

        cls._pushgateway_stop = None
        cls._pushgateway_thread = None
        cls._pushgateway_config = None
        cls._owns_pushgateway = False
        if owned and not cls._owns_pull_scrape:
            cls.registry = None
