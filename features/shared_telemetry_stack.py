"""Run the telemetry test containers once for a whole parallel Behave run.

``scripts/behave_parallel.py`` starts this module, reads the endpoints it prints and passes them to every feature
process in ``ARCHIPY_SHARED_TELEMETRY``, so features do not each start their own collector, Elasticsearch and
Elastic APM Server. Every scenario exports under its own ``service.name``, which keeps scenarios that share the
containers apart. The containers stop when the process receives SIGTERM or SIGINT.

Usage:
    python -m features.shared_telemetry_stack [--collector] [--apm]
"""

import argparse
import json
import os
import signal
import sys
import threading

# Registers the test configuration (images, memory limits) like a Behave run does.
import features.environment  # noqa: F401
from features.test_containers import (
    SHARED_TELEMETRY_ENV,
    ApmForwardingCollectorTestContainer,
    ApmServerTestContainer,
    OtelCollectorTestContainer,
)


def _collector_entry(collector: OtelCollectorTestContainer) -> dict[str, str]:
    return {"grpc": collector.grpc_endpoint, "http": collector.http_endpoint, "out_dir": str(collector.out_dir)}


def main(argv: list[str]) -> int:
    """Start the requested containers, print their endpoints as one JSON line and wait to be stopped."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collector", action="store_true", help="share the OpenTelemetry Collector")
    parser.add_argument("--apm", action="store_true", help="share Elasticsearch, Elastic APM Server and the forwarder")
    arguments = parser.parse_args(argv)

    os.environ.pop(SHARED_TELEMETRY_ENV, None)
    stop_requested = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop_requested.set())

    started = []
    endpoints: dict = {}
    try:
        if arguments.collector:
            collector = OtelCollectorTestContainer()
            started.append(collector)
            collector.start()
            endpoints["otel_collector"] = _collector_entry(collector)
        if arguments.apm:
            apm_server = ApmServerTestContainer()
            started.append(apm_server)
            apm_server.start()
            forwarder = ApmForwardingCollectorTestContainer()
            started.append(forwarder)
            forwarder.start()
            endpoints.update(
                elasticsearch_url=apm_server.elasticsearch_url,
                apm_endpoint=apm_server.grpc_endpoint,
                apm_collector=_collector_entry(forwarder),
            )
        print(json.dumps(endpoints), flush=True)
        stop_requested.wait()
    finally:
        for container in reversed(started):
            container.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
