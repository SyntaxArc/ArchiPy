"""Auto-instrumentation of the installed OpenTelemetry contrib packages."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Sequence

    from opentelemetry.instrumentation.dependencies import DependencyConflict
    from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
    from opentelemetry.metrics import MeterProvider
    from opentelemetry.trace import Span, TracerProvider

    from archipy.configs.base_config import BaseConfig
    from archipy.configs.config_template import OpentelemetryConfig, PydanticAIConfig

# Same logger as OtelUtils, so log filters and handlers that name it keep seeing these records.
logger = logging.getLogger("archipy.helpers.utils.otel_utils")

_REDIS_SEARCH_GUARD_MARKER = "_archipy_original"
_REDIS_SEARCH_ATTRIBUTES_NAME = "_add_search_attributes"
_PYDANTIC_AI_SETTINGS_MARKER = "_archipy_installed"


class Instrumentation:
    """Binds the contrib instrumentors to ArchiPy's providers and remembers which libraries it instrumented."""

    libraries: ClassVar[set[str]] = set()
    """Keys of the instrumented libraries. ``OtelUtils`` exposes this very set, and callers mutate it in place."""

    @classmethod
    def instrument_installed_libraries(
        cls,
        config: BaseConfig,
        *,
        tracer_provider: TracerProvider | None,
        meter_provider: MeterProvider | None,
    ) -> None:
        """Best-effort auto-instrumentation of installed contrib packages.

        Each entry is ``(cache_key, module, class_name)``. Missing packages are
        skipped via ``ImportError`` — install the matching ``archipy[otel-*]``
        extra (or the contrib package directly) to enable them. Instrumentors
        whose target library is absent (e.g. ``httpx`` when only ``httpx2`` is
        installed) raise ``DependencyConflictError`` and are skipped at debug
        level. A target library that is installed outside the instrumentor's
        supported version range is logged at warning level, because no spans
        are emitted for it.

        Driver-level DB instrumentors (psycopg/pymysql/sqlite3) are omitted:
        ArchiPy goes through SQLAlchemy — use ``archipy[otel-sqlalchemy]``.
        """
        instrumentors: Sequence[tuple[str, str, str]] = (
            ("threading", "opentelemetry.instrumentation.threading", "ThreadingInstrumentor"),
            ("system_metrics", "opentelemetry.instrumentation.system_metrics", "SystemMetricsInstrumentor"),
            ("sqlalchemy", "opentelemetry.instrumentation.sqlalchemy", "SQLAlchemyInstrumentor"),
            ("redis", "opentelemetry.instrumentation.redis", "RedisInstrumentor"),
            ("cassandra", "opentelemetry.instrumentation.cassandra", "CassandraInstrumentor"),
            ("confluent_kafka", "opentelemetry.instrumentation.confluent_kafka", "ConfluentKafkaInstrumentor"),
            ("botocore", "opentelemetry.instrumentation.botocore", "BotocoreInstrumentor"),
            ("httpx", "opentelemetry.instrumentation.httpx", "HTTPXClientInstrumentor"),
            ("httpx2", "opentelemetry.instrumentation.httpx", "HTTPX2ClientInstrumentor"),
            ("requests", "opentelemetry.instrumentation.requests", "RequestsInstrumentor"),
        )
        try:
            from opentelemetry.instrumentation.dependencies import DependencyConflictError
        except ImportError:
            logger.debug("Skipping OTel auto-instrumentation (opentelemetry-instrumentation not installed)")
            return
        otel = config.OTEL
        for key, module_name, class_name in instrumentors:
            if key in cls.libraries:
                continue
            if key == "system_metrics" and not (
                otel.METRICS_ENABLED and otel.SYSTEM_METRICS_ENABLED and meter_provider is not None
            ):
                logger.debug("Skipping system metrics instrumentation (disabled by config)")
                continue
            try:
                module = __import__(module_name, fromlist=[class_name])
                instrumentor_cls = getattr(module, class_name)
                instrumentor = instrumentor_cls()
                if getattr(instrumentor, "is_instrumented_by_opentelemetry", False):
                    cls.libraries.add(key)
                    cls._after_library_instrumented(key)
                    logger.debug("Skipping already-instrumented library: %s", key)
                    continue
                cls._instrument_with_providers(instrumentor, tracer_provider, meter_provider)
                cls.libraries.add(key)
                cls._after_library_instrumented(key)
                logger.debug("Instrumented library: %s", key)
            except ImportError:
                logger.debug("Skipping OTel instrumentation for %s (package not installed)", key)
            except DependencyConflictError as e:
                cls._handle_instrumentation_conflict(
                    key,
                    e.conflict,
                    (module_name, class_name),
                    otel,
                    (tracer_provider, meter_provider),
                )
            except Exception:
                logger.debug("Failed to instrument %s", key, exc_info=True)
        if config.PYDANTIC_AI.INSTRUMENTATION_ENABLED:
            cls._instrument_pydantic_ai(config.PYDANTIC_AI, tracer_provider, meter_provider)
        else:
            logger.debug("Skipping Pydantic AI instrumentation (disabled by config)")

    @classmethod
    def _instrument_pydantic_ai(
        cls,
        settings_config: PydanticAIConfig,
        tracer_provider: TracerProvider | None,
        meter_provider: MeterProvider | None,
    ) -> None:
        """Point Pydantic AI's built-in instrumentation at ArchiPy's providers.

        Pydantic AI has no contrib instrumentor; ``Agent.instrument_all`` takes ``InstrumentationSettings``
        that carry the providers. Settings an application installed itself are left alone, and settings
        ArchiPy installed earlier are replaced so a re-initialized runtime does not keep spans going to a
        provider that was shut down.
        """
        key = "pydantic_ai"
        if tracer_provider is None and meter_provider is None:
            return
        try:
            from pydantic_ai import Agent
            from pydantic_ai.models.instrumented import InstrumentationSettings
        except ImportError:
            logger.debug("Skipping OTel instrumentation for %s (package not installed)", key)
            return
        try:
            current = Agent._instrument_default
            if current is not False and not getattr(current, _PYDANTIC_AI_SETTINGS_MARKER, False):
                cls.libraries.add(key)
                logger.debug("Skipping already-instrumented library: %s", key)
                return
            settings = InstrumentationSettings(
                tracer_provider=tracer_provider,
                meter_provider=meter_provider,
                include_content=settings_config.INSTRUMENTATION_INCLUDE_CONTENT,
                include_binary_content=settings_config.INSTRUMENTATION_INCLUDE_BINARY_CONTENT,
                include_model_request_parameters=settings_config.INSTRUMENTATION_INCLUDE_MODEL_REQUEST_PARAMETERS,
                version=settings_config.INSTRUMENTATION_VERSION,
                use_aggregated_usage_attribute_names=settings_config.INSTRUMENTATION_USE_AGGREGATED_USAGE_ATTRIBUTE_NAMES,
            )
            setattr(settings, _PYDANTIC_AI_SETTINGS_MARKER, True)
            Agent.instrument_all(settings)
            cls.libraries.add(key)
            logger.debug("Instrumented library: %s", key)
        except Exception:
            logger.debug("Failed to instrument %s", key, exc_info=True)

    @classmethod
    def _after_library_instrumented(cls, key: str) -> None:
        """Apply the workaround that belongs to an instrumentor once it is bound."""
        if key == "redis":
            cls.guard_redis_search_attributes()

    @classmethod
    def guard_redis_search_attributes(cls) -> None:
        """Keep ``opentelemetry-instrumentation-redis`` from raising into the application on a RESP3 search reply.

        The instrumentor parses an ``FT.SEARCH`` reply as a list, but RESP3 (ArchiPy's default) returns a mapping,
        so reading ``response[0]`` raises ``KeyError`` inside the caller's search. The guard calls the original and,
        when it cannot read the reply, records what it can from a mapping reply instead of raising. Idempotent.
        """
        try:
            import opentelemetry.instrumentation.redis as redis_instrumentation
            from opentelemetry.instrumentation.redis import util as redis_util
        except ImportError:
            return
        original = redis_util._add_search_attributes
        if getattr(original, _REDIS_SEARCH_GUARD_MARKER, None) is not None:
            return

        def guarded(span: Span, response: object, args: object) -> None:
            try:
                original(span, response, args)
            except KeyError, TypeError, IndexError:
                logger.debug("Redis search reply not understood by the OTel instrumentor", exc_info=True)
                total = response.get("total_results") if isinstance(response, dict) else None
                if total is not None:
                    span.set_attribute("redis.search.total", total)

        setattr(guarded, _REDIS_SEARCH_GUARD_MARKER, original)
        # The helper is imported by name into the instrumentor module, so both bindings are replaced.
        for module in (redis_util, redis_instrumentation):
            setattr(module, _REDIS_SEARCH_ATTRIBUTES_NAME, guarded)

    @classmethod
    def restore_redis_search_attributes(cls) -> None:
        """Undo :meth:`guard_redis_search_attributes` (used by tests that need the upstream behaviour)."""
        try:
            import opentelemetry.instrumentation.redis as redis_instrumentation
            from opentelemetry.instrumentation.redis import util as redis_util
        except ImportError:
            return
        original = getattr(redis_util._add_search_attributes, _REDIS_SEARCH_GUARD_MARKER, None)
        if original is not None:
            for module in (redis_util, redis_instrumentation):
                setattr(module, _REDIS_SEARCH_ATTRIBUTES_NAME, original)

    @classmethod
    def _handle_instrumentation_conflict(
        cls,
        key: str,
        conflict: DependencyConflict,
        target: tuple[str, str],
        otel: OpentelemetryConfig,
        providers: tuple[TracerProvider | None, MeterProvider | None],
    ) -> None:
        """React to a ``DependencyConflictError`` raised by an instrumentor.

        A target library that is absent is skipped at debug level. One that is installed but outside the
        instrumentor's supported range would otherwise fail silently, so it is either instrumented anyway (when
        listed in ``OTEL.INSTRUMENTATION_SKIP_DEP_CHECK``) or reported at warning level.
        """
        if not (conflict.found or conflict.found_any):
            logger.debug("Skipping OTel instrumentation for %s (%s)", key, conflict)
        elif key in otel.INSTRUMENTATION_SKIP_DEP_CHECK:
            module_name, class_name = target
            instrumentor_cls = getattr(__import__(module_name, fromlist=[class_name]), class_name)
            cls._instrument_ignoring_version_range(key, instrumentor_cls, providers)
        else:
            # Without this the service would run silently without these spans.
            logger.warning(
                "OTel instrumentation for %s is disabled, no spans will be emitted: the installed version "
                "is outside the range the instrumentor supports (%s)",
                key,
                conflict,
            )

    @classmethod
    def _instrument_ignoring_version_range(
        cls,
        key: str,
        instrumentor_cls: type[BaseInstrumentor],
        providers: tuple[TracerProvider | None, MeterProvider | None],
    ) -> None:
        """Instrument a library whose installed version is newer than the instrumentor's declared range.

        Some instrumentors cap the library version in their metadata long before the runtime hooks they use
        break (for example ``opentelemetry-instrumentation-sqlalchemy`` caps SQLAlchemy below 2.1). Keys listed in
        ``OTEL.INSTRUMENTATION_SKIP_DEP_CHECK`` are instrumented anyway, with a warning.
        """
        try:
            cls._instrument_with_providers(instrumentor_cls(), *providers, skip_dep_check=True)
        except Exception:
            logger.warning(
                "OTel instrumentation for %s is disabled, no spans will be emitted: the installed version is "
                "outside the range the instrumentor supports and instrumenting it anyway failed",
                key,
                exc_info=True,
            )
            return
        cls.libraries.add(key)
        logger.warning(
            "OTel instrumentation for %s is enabled although the installed version is outside the range the "
            "instrumentor declares (OTEL.INSTRUMENTATION_SKIP_DEP_CHECK); remove %r from that setting once the "
            "instrumentor supports this version",
            key,
            key,
        )

    @classmethod
    def _instrument_with_providers(
        cls,
        instrumentor: BaseInstrumentor,
        tracer_provider: TracerProvider | None,
        meter_provider: MeterProvider | None,
        *,
        skip_dep_check: bool = False,
    ) -> None:
        """Instrument with ArchiPy's providers; raise ``DependencyConflictError`` on a missing target library."""
        kwargs: dict[str, Any] = {"skip_dep_check": True} if skip_dep_check else {"raise_exception_on_conflict": True}
        if tracer_provider is not None:
            kwargs["tracer_provider"] = tracer_provider
        if meter_provider is not None:
            kwargs["meter_provider"] = meter_provider
        try:
            instrumentor.instrument(**kwargs)
        except TypeError:
            kwargs.pop("meter_provider", None)
            instrumentor.instrument(**kwargs)
