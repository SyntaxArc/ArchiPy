#!/usr/bin/env bash
# Tell when an OpenTelemetry instrumentor supports the library version ArchiPy requires.
#
# ArchiPy requires sqlalchemy>=2.1.4, but opentelemetry-instrumentation-sqlalchemy still declares
# sqlalchemy<2.1.0 in its "instruments" extra, so ArchiPy instruments SQLAlchemy through
# OTEL.INSTRUMENTATION_SKIP_DEP_CHECK. The extra is not a hard dependency, so uv never sees the conflict
# on a normal install. Resolving the extra together with ArchiPy's own bound makes uv report it.
#
# Exit codes:
#   0  conflict still present: the bypass is still needed
#   1  a pair now resolves: remove that key from OTEL.INSTRUMENTATION_SKIP_DEP_CHECK (and its default)
#   2  the check itself failed (network or index problem)
set -uo pipefail

# "<library requirement>|<instrumentor requirement with the instruments extra>"
PAIRS=(
  "sqlalchemy>=2.1.4|opentelemetry-instrumentation-sqlalchemy[instruments]>=0.66b1"
)

status=0
for pair in "${PAIRS[@]}"; do
  library="${pair%%|*}"
  instrumentor="${pair##*|}"
  output=$(printf '%s\n%s\n' "${library}" "${instrumentor}" | uv pip compile --no-header --quiet - 2>&1)
  code=$?
  if [ "${code}" -eq 0 ]; then
    echo "SUPPORTED: ${instrumentor} now resolves with ${library}. Remove the bypass for it."
    status=1
  elif echo "${output}" | grep -q "No solution found"; then
    echo "STILL CONFLICTING: ${instrumentor} with ${library}"
  else
    echo "CHECK FAILED for ${instrumentor}:"
    echo "${output}"
    exit 2
  fi
done
exit "${status}"
