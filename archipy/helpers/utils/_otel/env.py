"""Standard ``OTEL_*`` environment variables as defaults for the settings an OpenTelemetry config leaves unset."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from pydantic import TypeAdapter, ValidationError

from archipy.configs.config_template import OpentelemetryConfig
from archipy.models.errors import ConfigurationError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

# Same logger as OtelUtils, so log filters and handlers that name it keep seeing these records.
logger = logging.getLogger("archipy.helpers.utils.otel_utils")

_SAMPLERS_WITH_RATIO = {"traceidratio", "parentbased_traceidratio"}
_SAMPLERS = {
    "always_on",
    "always_off",
    "traceidratio",
    "parentbased_always_on",
    "parentbased_always_off",
    "parentbased_traceidratio",
}


def _parse_headers(raw: str) -> dict[str, str]:
    """Parse ``key=value,key=value`` (W3C Baggage style) into a dict."""
    from opentelemetry.util.re import parse_env_headers

    return dict(parse_env_headers(raw, liberal=True))


def _parse_propagators(raw: str) -> list[str]:
    return [name.strip().lower() for name in raw.split(",") if name.strip()]


def _signal_settings() -> list[tuple[str, str, Callable[[str], object]]]:
    """Return ``(field, variable, parser)`` for every setting a standard variable can fill in."""
    return [
        ("SERVICE_NAME", "OTEL_SERVICE_NAME", str),
        ("OTLP_ENDPOINT", "OTEL_EXPORTER_OTLP_ENDPOINT", str),
        ("TRACES_ENDPOINT", "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", str),
        ("METRICS_ENDPOINT", "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", str),
        ("LOGS_ENDPOINT", "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT", str),
        ("PROTOCOL", "OTEL_EXPORTER_OTLP_PROTOCOL", str),
        ("OTLP_HEADERS", "OTEL_EXPORTER_OTLP_HEADERS", _parse_headers),
        # The Python SDK reads this variable in seconds, so ArchiPy does too.
        ("TIMEOUT", "OTEL_EXPORTER_OTLP_TIMEOUT", float),
        ("OTLP_COMPRESSION", "OTEL_EXPORTER_OTLP_COMPRESSION", lambda value: value.strip().lower()),
        ("PROPAGATORS", "OTEL_PROPAGATORS", _parse_propagators),
        ("SPAN_BATCH_SCHEDULE_DELAY_MS", "OTEL_BSP_SCHEDULE_DELAY", int),
        ("SPAN_BATCH_EXPORT_TIMEOUT_MS", "OTEL_BSP_EXPORT_TIMEOUT", int),
        ("SPAN_BATCH_MAX_QUEUE_SIZE", "OTEL_BSP_MAX_QUEUE_SIZE", int),
        ("SPAN_BATCH_MAX_EXPORT_BATCH_SIZE", "OTEL_BSP_MAX_EXPORT_BATCH_SIZE", int),
        ("LOG_BATCH_SCHEDULE_DELAY_MS", "OTEL_BLRP_SCHEDULE_DELAY", int),
        ("LOG_BATCH_EXPORT_TIMEOUT_MS", "OTEL_BLRP_EXPORT_TIMEOUT", int),
        ("LOG_BATCH_MAX_QUEUE_SIZE", "OTEL_BLRP_MAX_QUEUE_SIZE", int),
        ("LOG_BATCH_MAX_EXPORT_BATCH_SIZE", "OTEL_BLRP_MAX_EXPORT_BATCH_SIZE", int),
        ("METRIC_EXPORT_INTERVAL_MS", "OTEL_METRIC_EXPORT_INTERVAL", int),
    ]


def sdk_disabled(otel: OpentelemetryConfig, environ: Mapping[str, str] | None = None) -> bool:
    """Tell whether ``OTEL_SDK_DISABLED=true`` switches OpenTelemetry off; only ``USE_STANDARD_ENV`` honours it."""
    environ = os.environ if environ is None else environ
    return otel.USE_STANDARD_ENV and environ.get("OTEL_SDK_DISABLED", "").strip().lower() == "true"


def _collect(otel: OpentelemetryConfig, environ: Mapping[str, str]) -> dict[str, object]:
    """Return the validated values of the standard variables for the fields that ``otel`` leaves unset."""
    updates: dict[str, object] = {}

    def accept(field: str, value: object, variable: str) -> None:
        info = OpentelemetryConfig.model_fields[field]
        try:
            updates[field] = TypeAdapter(info.rebuild_annotation()).validate_python(value)
        except ValidationError:
            logger.warning("Ignoring invalid %s=%r", variable, environ.get(variable))

    for field, variable, parser in _signal_settings():
        raw = environ.get(variable)
        if raw is None or not raw.strip() or field in otel.model_fields_set:
            continue
        try:
            value = parser(raw.strip())
        except ValueError:
            logger.warning("Ignoring invalid %s=%r", variable, raw)
            continue
        accept(field, value, variable)

    _collect_sampler(otel, environ, accept)
    return updates


def _collect_sampler(otel: OpentelemetryConfig, environ: Mapping[str, str], accept: Callable[..., None]) -> None:
    """Collect ``OTEL_TRACES_SAMPLER`` and its argument; an unknown sampler is logged and ignored."""
    sampler = environ.get("OTEL_TRACES_SAMPLER", "").strip().lower()
    if not sampler or "TRACES_SAMPLER" in otel.model_fields_set:
        return
    if sampler not in _SAMPLERS:
        logger.warning("Ignoring unsupported OTEL_TRACES_SAMPLER=%r", sampler)
        return
    accept("TRACES_SAMPLER", sampler, "OTEL_TRACES_SAMPLER")
    argument = environ.get("OTEL_TRACES_SAMPLER_ARG", "").strip()
    if sampler in _SAMPLERS_WITH_RATIO and argument and "TRACES_SAMPLE_RATIO" not in otel.model_fields_set:
        try:
            accept("TRACES_SAMPLE_RATIO", float(argument), "OTEL_TRACES_SAMPLER_ARG")
        except ValueError:
            logger.warning("Ignoring invalid OTEL_TRACES_SAMPLER_ARG=%r", argument)


def apply_standard_env(otel: OpentelemetryConfig, environ: Mapping[str, str] | None = None) -> OpentelemetryConfig:
    """Return ``otel`` with the standard ``OTEL_*`` variables filled in for every setting it leaves unset.

    A field counts as set when it is in ``model_fields_set``, whatever its source (code, ArchiPy environment
    variables, TOML). Without ``USE_STANDARD_ENV`` the config is returned unchanged. An invalid value is logged and
    ignored, as the OpenTelemetry specification asks, and so are values that are valid alone but not together.

    Args:
        otel: OpenTelemetry config section.
        environ: Variables to read; the process environment by default.

    Returns:
        The config itself, or a validated copy with the environment applied.
    """
    if not otel.USE_STANDARD_ENV:
        return otel
    updates = _collect(otel, os.environ if environ is None else environ)
    try:
        # Only the fields the config set go back in, so an unset batch size can still follow a lowered queue size.
        return OpentelemetryConfig.model_validate({**otel.model_dump(exclude_unset=True), **updates})
    except ValidationError, ConfigurationError:
        logger.warning("Ignoring the standard OTEL_* variables: together they make an invalid configuration")
        return otel
