#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14,<4"
# dependencies = []
# ///

"""Tell when an OpenTelemetry instrumentor supports the library ArchiPy requires.

ArchiPy requires sqlalchemy>=2.1.4, but opentelemetry-instrumentation-sqlalchemy still declares
sqlalchemy<2.1.0 in its "instruments" extra. ArchiPy instruments SQLAlchemy through
OTEL.INSTRUMENTATION_SKIP_DEP_CHECK. The extra is optional, so resolve both requirements
together to detect when the bypass can be removed.

Exit codes:
    0: The conflict is still present.
    1: A pair resolves. Remove its bypass from OTEL.INSTRUMENTATION_SKIP_DEP_CHECK.
    2: The check failed, for example because of a network or index error.
"""

import subprocess
import sys

PAIRS = (("sqlalchemy>=2.1.4", "opentelemetry-instrumentation-sqlalchemy[instruments]>=0.66b1"),)


def main() -> int:
    """Run uv's resolver for each library and instrumentor pair."""
    status = 0
    for library, instrumentor in PAIRS:
        result = subprocess.run(
            ["uv", "pip", "compile", "--python", sys.executable, "--no-header", "--quiet", "-"],
            input=f"{library}\n{instrumentor}\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print(f"SUPPORTED: {instrumentor} now resolves with {library}. Remove the bypass for it.")
            status = 1
        elif "No solution found" in result.stdout:
            print(f"STILL CONFLICTING: {instrumentor} with {library}")
        else:
            print(f"CHECK FAILED for {instrumentor}:\n{result.stdout}", end="")
            return 2
    return status


if __name__ == "__main__":
    raise SystemExit(main())
