"""Resource construction: explicit settings over detected attributes."""

from __future__ import annotations

import platform
import socket
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from opentelemetry.sdk.resources import Resource, ResourceDetector

    from archipy.configs.config_template import OpentelemetryConfig


def _host_detector() -> ResourceDetector:
    from opentelemetry.sdk.resources import Resource, ResourceDetector

    class HostResourceDetector(ResourceDetector):
        """Report ``host.name`` and ``host.arch``."""

        def detect(self) -> Resource:
            return Resource({"host.name": socket.gethostname(), "host.arch": platform.machine()})

    return HostResourceDetector()


def _detectors(names: Sequence[str]) -> list[ResourceDetector]:
    from opentelemetry.sdk.resources import (
        OsResourceDetector,
        ProcessResourceDetector,
        ServiceInstanceIdResourceDetector,
    )

    available = {
        "service_instance": ServiceInstanceIdResourceDetector,
        "host": _host_detector,
        "os": OsResourceDetector,
        "process": ProcessResourceDetector,
    }
    detectors: list[ResourceDetector] = []
    for name in dict.fromkeys(names):
        factory = available[name]
        detectors.append(factory())
    return detectors


def create_resource(otel: OpentelemetryConfig) -> Resource:
    """Build the OpenTelemetry resource of the service.

    Precedence, lowest first: detected attributes, ``RESOURCE_ATTRIBUTES``, then the explicit ``SERVICE_NAME``,
    ``SERVICE_VERSION``, ``SERVICE_INSTANCE_ID`` and ``ENVIRONMENT`` settings. ``Resource.create`` also reads
    ``OTEL_SERVICE_NAME`` and ``OTEL_RESOURCE_ATTRIBUTES`` below all of these.

    Args:
        otel: OpenTelemetry config section.

    Returns:
        The SDK ``Resource``.
    """
    from opentelemetry.sdk.resources import Resource, get_aggregated_resources

    explicit: dict[str, Any] = dict(otel.RESOURCE_ATTRIBUTES)
    if otel.SERVICE_NAME:
        explicit["service.name"] = otel.SERVICE_NAME
    if otel.SERVICE_VERSION:
        explicit["service.version"] = otel.SERVICE_VERSION
    if otel.SERVICE_INSTANCE_ID:
        explicit["service.instance.id"] = otel.SERVICE_INSTANCE_ID
    if otel.ENVIRONMENT is not None:
        explicit["deployment.environment.name"] = str(otel.ENVIRONMENT)
    # ``merge`` lets its argument win, so the explicit settings go last; get_aggregated_resources would put them first.
    return get_aggregated_resources(_detectors(otel.RESOURCE_DETECTORS)).merge(Resource.create(explicit))
