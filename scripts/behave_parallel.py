#!/usr/bin/env python3
"""Run the Behave feature files in parallel, one ``behave`` process per feature.

Behave has no parallel runner. Each feature starts the testcontainers it needs (the ``@needs-*`` tags of the
feature) in its own process, so features are independent and can run side by side.

Scheduling:
    * Longest features start first, using the durations of the previous run (``.behave_durations.json``), so the
      wall time approaches the duration of the slowest feature.
    * Features that start a heavy container (StarRocks, Keycloak, Elasticsearch, Kafka, ...) share a smaller
      budget (``--heavy-jobs``) so a small machine is not starved of memory.

Output:
    * One line per finished feature, the tail of the log of a failed one and a summary table.
    * The full output of every feature is in ``.behave-logs/<feature>.log``.

Coverage:
    ``--coverage`` runs each feature under ``coverage run`` (``parallel = true`` in ``pyproject.toml`` gives every
    process its own data file) and combines the data files at the end.

Usage:
    python scripts/behave_parallel.py [-j N] [--heavy-jobs N] [--coverage] [FEATURE ...] [-- BEHAVE_ARGS ...]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEATURES_DIR = ROOT / "features"
LOG_DIR = ROOT / ".behave-logs"
DURATIONS_FILE = ROOT / ".behave_durations.json"

# Containers that need a lot of memory or CPU to start; features tagged with them count against --heavy-jobs.
HEAVY_TAGS = frozenset(
    {
        "needs-starrocks",
        "needs-keycloak",
        "needs-elasticsearch",
        "needs-kafka",
        "needs-temporal",
        "needs-scylladb",
        "needs-redis-cluster",
    },
)
# A feature without tags that still starts a heavy container (the tag is on the scenarios or in the steps).
HEAVY_FEATURES = frozenset({"elastic_adapter", "kafka_adapters", "keycloak_adapter", "scylladb_adapter"})

DEFAULT_DURATION_SECONDS = 30.0
LOG_TAIL_LINES = 40
NOISE = re.compile(r"^%\d\||rdkafka")
SUMMARY_LINE = re.compile(r"(\d+) scenarios? passed, (\d+) failed(?:, (\d+) errors?)?")


@dataclass
class FeatureRun:
    """The outcome of one feature process."""

    name: str
    path: Path
    heavy: bool
    expected_seconds: float
    return_code: int | None = None
    seconds: float = 0.0
    passed: int = 0
    failed: int = 0
    timed_out: bool = False
    log_path: Path = field(init=False)

    def __post_init__(self) -> None:
        """Place the log of the feature next to the others."""
        self.log_path = LOG_DIR / f"{self.name}.log"

    @property
    def ok(self) -> bool:
        """Whether the feature passed."""
        return self.return_code == 0 and not self.timed_out


def _feature_tags(path: Path) -> set[str]:
    """Return the tags on the first tag line of a feature file."""
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("@"):
            return {tag.lstrip("@") for tag in stripped.split()}
        return set()
    return set()


def _load_durations() -> dict[str, float]:
    """Read the durations of the previous run, or nothing when there are none."""
    try:
        data = json.loads(DURATIONS_FILE.read_text(encoding="utf-8"))
    except OSError, ValueError:
        return {}
    return {str(name): float(seconds) for name, seconds in data.items()}


def _save_durations(runs: list[FeatureRun], previous: dict[str, float]) -> None:
    """Remember how long each feature took, so the next run starts the longest first."""
    durations = dict(previous)
    durations.update({run.name: round(run.seconds, 1) for run in runs if run.return_code is not None})
    DURATIONS_FILE.write_text(json.dumps(durations, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _discover(paths: list[str]) -> list[FeatureRun]:
    """Build the runs: the given feature files, or every feature file of ``features/``."""
    files = [Path(p).resolve() for p in paths] if paths else sorted(FEATURES_DIR.glob("*.feature"))
    durations = _load_durations()
    runs = [
        FeatureRun(
            name=path.stem,
            path=path,
            heavy=bool(_feature_tags(path) & HEAVY_TAGS) or path.stem in HEAVY_FEATURES,
            expected_seconds=durations.get(path.stem, DEFAULT_DURATION_SECONDS),
        )
        for path in files
    ]
    return sorted(runs, key=lambda run: run.expected_seconds, reverse=True)


def _display(path: Path) -> str:
    """Return a path relative to the repository when it is inside it."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _command(run: FeatureRun, *, coverage: bool, behave_args: list[str]) -> list[str]:
    """Return the command line that runs one feature."""
    base = [sys.executable, "-m"]
    if coverage:
        base += ["coverage", "run", "-m"]
    return [*base, "behave", _display(run.path), "-f", "plain", "--no-color", *behave_args]


def _terminate(process: subprocess.Popen[bytes]) -> None:
    """Stop a feature process and the children it started."""
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=20)
    except ProcessLookupError, subprocess.TimeoutExpired:
        with_kill = getattr(signal, "SIGKILL", signal.SIGTERM)
        try:
            os.killpg(process.pid, with_kill)
        except ProcessLookupError:
            pass


def _parse_summary(log_path: Path) -> tuple[int, int]:
    """Return the passed and failed scenario counts a feature printed."""
    passed = failed = 0
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return passed, failed
    for match in SUMMARY_LINE.finditer(text):
        passed, failed = int(match.group(1)), int(match.group(2)) + int(match.group(3) or 0)
    return passed, failed


def _tail(log_path: Path) -> str:
    """Return the last lines of a log, without the container client noise."""
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join([line for line in lines if not NOISE.search(line)][-LOG_TAIL_LINES:])


class Runner:
    """Run features with a general job limit and a smaller one for heavy features."""

    def __init__(self, jobs: int, heavy_jobs: int, timeout: float | None, *, coverage: bool, behave_args: list[str]):
        """Set up the limits and the shared state of the workers."""
        self.jobs = jobs
        self.timeout = timeout
        self.coverage = coverage
        self.behave_args = behave_args
        self.heavy_slots = threading.BoundedSemaphore(max(1, min(heavy_jobs, jobs)))
        self.print_lock = threading.Lock()
        self.stop = threading.Event()
        self.processes: set[subprocess.Popen[bytes]] = set()
        self.processes_lock = threading.Lock()

    def _say(self, message: str) -> None:
        with self.print_lock:
            print(message, flush=True)

    def run_feature(self, run: FeatureRun) -> FeatureRun:
        """Run one feature process and record its outcome."""
        if self.stop.is_set():
            return run
        if run.heavy:
            self.heavy_slots.acquire()
        try:
            if self.stop.is_set():
                return run
            self._execute(run)
        finally:
            if run.heavy:
                self.heavy_slots.release()
        return run

    def _execute(self, run: FeatureRun) -> None:
        LOG_DIR.mkdir(exist_ok=True)
        self._say(f"START  {run.name}")
        started = time.monotonic()
        with run.log_path.open("wb") as log:
            process = subprocess.Popen(  # noqa: S603 - fixed argument list built from this repository's files
                _command(run, coverage=self.coverage, behave_args=self.behave_args),
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            with self.processes_lock:
                self.processes.add(process)
            try:
                run.return_code = process.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                run.timed_out = True
                _terminate(process)
                run.return_code = process.returncode
            finally:
                with self.processes_lock:
                    self.processes.discard(process)
        run.seconds = time.monotonic() - started
        run.passed, run.failed = _parse_summary(run.log_path)
        status = "PASS " if run.ok else ("TIMEOUT" if run.timed_out else "FAIL ")
        self._say(f"{status} {run.name}  {run.seconds:6.1f}s  {run.passed} passed, {run.failed} failed")
        if not run.ok:
            self._say(f"----- tail of {run.log_path.relative_to(ROOT)} -----\n{_tail(run.log_path)}\n-----")

    def interrupt(self) -> None:
        """Stop what is running and stop starting more."""
        self.stop.set()
        with self.processes_lock:
            running = list(self.processes)
        for process in running:
            _terminate(process)

    def run_all(self, runs: list[FeatureRun]) -> None:
        """Run every feature, longest first, at most ``jobs`` at a time."""
        with ThreadPoolExecutor(max_workers=self.jobs) as pool:
            futures = [pool.submit(self.run_feature, run) for run in runs]
            try:
                for future in as_completed(futures):
                    future.result()
            except KeyboardInterrupt:
                self._say("Interrupted: stopping the running features")
                self.interrupt()
                raise


def _summary(runs: list[FeatureRun], wall_seconds: float) -> str:
    """Return the summary table."""
    done = [run for run in runs if run.return_code is not None]
    width = max((len(run.name) for run in done), default=10)
    lines = ["", f"{'feature'.ljust(width)}  {'time':>8}  passed  failed  result"]
    for run in sorted(done, key=lambda item: item.seconds, reverse=True):
        result = "ok" if run.ok else ("timeout" if run.timed_out else "FAILED")
        lines.append(f"{run.name.ljust(width)}  {run.seconds:7.1f}s  {run.passed:6}  {run.failed:6}  {result}")
    cpu_seconds = sum(run.seconds for run in done)
    skipped = len(runs) - len(done)
    lines.append(
        f"\n{len(done)} features, {sum(run.passed for run in done)} scenarios passed, "
        f"{sum(run.failed for run in done)} failed"
        + (f", {skipped} not run" if skipped else "")
        + f"\nwall time {wall_seconds:.0f}s, sequential time would be about {cpu_seconds:.0f}s",
    )
    failed = [run.name for run in done if not run.ok]
    if failed:
        lines.append("failed features: " + ", ".join(failed))
    return "\n".join(lines)


def _write_github_summary(runs: list[FeatureRun], wall_seconds: float) -> None:
    """Add the result table to the job summary when running in GitHub Actions."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    done = sorted((run for run in runs if run.return_code is not None), key=lambda item: item.seconds, reverse=True)
    lines = [
        "### Behave features",
        "",
        f"{len(done)} features in {wall_seconds:.0f}s (about {sum(run.seconds for run in done):.0f}s one after another)",
        "",
        "| feature | time | passed | failed | result |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for run in done:
        result = "ok" if run.ok else ("timeout" if run.timed_out else "**FAILED**")
        lines.append(f"| {run.name} | {run.seconds:.1f}s | {run.passed} | {run.failed} | {result} |")
    with Path(path).open("a", encoding="utf-8") as summary:
        summary.write("\n".join(lines) + "\n")


def _combine_coverage() -> None:
    """Merge the per-process coverage data files and print the report."""
    for command in (["combine", "-q"], ["report"], ["xml", "-q"]):
        subprocess.run([sys.executable, "-m", "coverage", *command], cwd=ROOT, check=False)  # noqa: S603


def _parse_arguments(argv: list[str]) -> tuple[argparse.Namespace, list[str]]:
    """Split the arguments into the runner's own and the ones passed to behave after ``--``."""
    if "--" in argv:
        split = argv.index("--")
        own, behave_args = argv[:split], argv[split + 1 :]
    else:
        own, behave_args = argv, []
    parser = argparse.ArgumentParser(description="Run Behave features in parallel, one process per feature.")
    parser.add_argument("features", nargs="*", help="feature files to run (default: all of features/)")
    parser.add_argument(
        "-j",
        "--jobs",
        type=int,
        default=int(os.environ.get("BEHAVE_JOBS", min(8, os.cpu_count() or 1))),
        help="features to run at the same time (default: BEHAVE_JOBS or min(8, CPUs))",
    )
    parser.add_argument(
        "--heavy-jobs",
        type=int,
        default=int(os.environ.get("BEHAVE_HEAVY_JOBS", 3)),
        help="of those, features with a heavy container to run at the same time (default: BEHAVE_HEAVY_JOBS or 3)",
    )
    parser.add_argument("--timeout", type=float, default=None, help="seconds a single feature may run")
    parser.add_argument("--coverage", action="store_true", help="run under coverage and combine the data files")
    return parser.parse_args(own), behave_args


APM_TAGS = frozenset({"needs-apm-server", "needs-apm-collector"})
COLLECTOR_TAG = "needs-otel-collector"
SHARED_TELEMETRY_ENV = "ARCHIPY_SHARED_TELEMETRY"
SHARED_TELEMETRY_START_TIMEOUT_SECONDS = 600


def _start_shared_telemetry_stack(runs: list[FeatureRun]) -> subprocess.Popen | None:
    """Start the collector and the Elastic APM stack once and export their endpoints to the feature processes.

    Without this every feature process would start its own collector, Elasticsearch and APM Server. Only the parts
    a selected feature asks for through its tags are started.
    """
    tags = set().union(*(_feature_tags(run.path) for run in runs))
    share_apm = bool(tags & APM_TAGS)
    share_collector = share_apm or COLLECTOR_TAG in tags
    if not share_collector:
        return None
    command = [sys.executable, "-m", "features.shared_telemetry_stack", "--collector"]
    if share_apm:
        command.append("--apm")
    print("Starting the shared telemetry containers...", flush=True)
    stack = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, text=True)
    result: list[str] = []
    reader = threading.Thread(target=lambda: result.append(stack.stdout.readline()), daemon=True)
    reader.start()
    reader.join(SHARED_TELEMETRY_START_TIMEOUT_SECONDS)
    if not result or not result[0].strip():
        _stop_shared_telemetry_stack(stack)
        raise RuntimeError("The shared telemetry containers did not start")
    os.environ[SHARED_TELEMETRY_ENV] = result[0].strip()
    print(f"Shared telemetry containers ready: {result[0].strip()}", flush=True)
    return stack


def _stop_shared_telemetry_stack(stack: subprocess.Popen | None) -> None:
    if stack is None:
        return
    stack.send_signal(signal.SIGTERM)
    try:
        stack.wait(timeout=120)
    except subprocess.TimeoutExpired:
        stack.kill()
    os.environ.pop(SHARED_TELEMETRY_ENV, None)


def main(argv: list[str]) -> int:
    """Run the features and return the exit code: 0 when every feature passed."""
    arguments, behave_args = _parse_arguments(argv)
    runs = _discover(arguments.features)
    if not runs:
        print("No feature files found", file=sys.stderr)
        return 2
    if arguments.coverage:
        for stale in ROOT.glob(".coverage*"):
            stale.unlink()
    print(
        f"Running {len(runs)} features, {arguments.jobs} at a time ({arguments.heavy_jobs} heavy at a time). "
        f"Logs: {LOG_DIR.relative_to(ROOT)}/",
        flush=True,
    )
    runner = Runner(
        arguments.jobs,
        arguments.heavy_jobs,
        arguments.timeout,
        coverage=arguments.coverage,
        behave_args=behave_args,
    )
    started = time.monotonic()
    telemetry_stack = _start_shared_telemetry_stack(runs)
    try:
        runner.run_all(runs)
    except KeyboardInterrupt:
        _save_durations(runs, _load_durations())
        print(_summary(runs, time.monotonic() - started))
        return 130
    finally:
        _stop_shared_telemetry_stack(telemetry_stack)
    wall_seconds = time.monotonic() - started
    _save_durations(runs, _load_durations())
    print(_summary(runs, wall_seconds))
    _write_github_summary(runs, wall_seconds)
    if arguments.coverage:
        _combine_coverage()
    return 0 if all(run.ok for run in runs) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
