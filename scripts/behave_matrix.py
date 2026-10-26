#!/usr/bin/env python3
"""Choose which Behave feature groups the CI runs for a change.

Each group is one GitHub job. A group runs when a file it owns changed, so a change in ``packages/redis`` does not
start the Keycloak, Kafka or Elasticsearch containers. A change the script cannot tie to a group (shared code under
``archipy/``, the test steps, the dependencies, ...) runs every group, so a test is never skipped by mistake.

The last group (``core``) is every feature that no other group lists, so a new feature file is picked up on its own.

Usage:
    python scripts/behave_matrix.py [--base GIT_REF]   # changed files = git diff BASE...HEAD; no --base: run all

Output: the matrix as JSON on stdout and, in GitHub Actions, ``matrix`` and ``has_groups`` in ``$GITHUB_OUTPUT``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEATURES_DIR = ROOT / "features"

CORE = "core"


@dataclass(frozen=True)
class Group:
    """One CI job: the features it runs and the paths whose change makes it run."""

    name: str
    features: tuple[str, ...] = ()
    paths: tuple[str, ...] = field(default=())


GROUPS = (
    Group(
        "Keycloak",
        ("keycloak_adapter", "keycloak_dtos", "keycloak_protocol_mapper_configs"),
        ("packages/keycloak/",),
    ),
    Group("Kafka", ("kafka_adapters",), ("packages/kafka/",)),
    Group("Redis", ("redis_adapter", "grpc_rate_limit"), ("packages/redis/",)),
    Group(
        "Elasticsearch",
        ("elastic_adapter", "elastic_apm_telemetry"),
        ("packages/elasticsearch/",),
    ),
    Group("ScyllaDB", ("scylladb_adapter",), ("packages/scylladb/",)),
    Group("Temporal", ("temporal_adapter",), ("packages/temporal/",)),
    Group("MinIO", ("minio_adapter", "fastapi_minio_upload"), ("packages/minio/",)),
    Group("Vault", ("vault_adapter",), ("packages/vault/",)),
    Group(
        "SQL databases",
        ("atomic_transactions", "sqlalchemy_multiple_databases", "database_error_classification"),
        (
            "packages/postgres/",
            "packages/mysql/",
            "packages/sqlite/",
            "packages/starrocks/",
            "archipy/adapters/base/sqlalchemy/",
        ),
    ),
    Group("Email", ("email_adapter",), ("archipy/adapters/email/",)),
    Group(
        "Payment gateways",
        ("parsian_ipg_adapter", "saman_ipg_adapter"),
        ("packages/parsian-ipg/", "packages/saman-ipg/"),
    ),
    Group("Telemetry", ("otel", "otel_configuration"), ("archipy/helpers/utils/_otel/",)),
)

# Changes that cannot affect a test: documentation and the tooling around the repository.
IGNORED_PREFIXES = (
    "docs/",
    ".cursor/",
    ".agents/",
    ".claude/",
    ".idea/",
    ".github/ISSUE_TEMPLATE/",
    ".github/workflows/",
)
IGNORED_SUFFIXES = (".md", ".mdc")
IGNORED_FILES = frozenset({"LICENSE", "mkdocs.yml", ".gitignore", ".gitattributes", ".readthedocs.yaml"})
# Workflows that do not run the features.
RELEVANT_WORKFLOWS = frozenset({".github/workflows/tests.yml"})


def _is_ignored(path: str) -> bool:
    """Whether a changed file cannot change a test result."""
    if path in RELEVANT_WORKFLOWS:
        return False
    return path in IGNORED_FILES or path.startswith(IGNORED_PREFIXES) or path.endswith(IGNORED_SUFFIXES)


def _group_of(path: str) -> Group | None:
    """Return the group that owns a changed file, or nothing when the file is shared."""
    for group in GROUPS:
        if path.startswith(group.paths):
            return group
        if path.startswith("features/") and path.endswith(".feature") and Path(path).stem in group.features:
            return group
    return None


def select(changed: list[str] | None) -> list[str]:
    """Return the names of the groups to run, ``core`` included when it is needed.

    ``changed`` is ``None`` when every group must run.
    """
    names = [group.name for group in GROUPS] + [CORE]
    if changed is None:
        return names
    selected: set[str] = set()
    for path in changed:
        if _is_ignored(path):
            continue
        group = _group_of(path)
        if group is not None:
            selected.add(group.name)
        elif path.startswith("features/") and path.endswith(".feature"):
            selected.add(CORE)
        else:
            return names
    return [name for name in names if name in selected]


def _listed_features() -> set[str]:
    """Return the names of every feature a named group lists."""
    return {name for group in GROUPS for name in group.features}


def matrix(selected: list[str]) -> dict[str, list[dict[str, str]]]:
    """Build the GitHub matrix: ``features`` for a named group, ``exclude`` for the catch-all ``core`` group."""
    listed = sorted(_listed_features())
    include: list[dict[str, str]] = []
    for name in selected:
        if name == CORE:
            include.append({"name": "Core and utilities", "features": "", "exclude": _paths(listed)})
            continue
        group = next(group for group in GROUPS if group.name == name)
        include.append({"name": group.name, "features": _paths(group.features), "exclude": ""})
    return {"include": include}


def _paths(names: tuple[str, ...] | list[str]) -> str:
    """Return feature names as the space separated paths ``make behave`` takes."""
    return " ".join(f"features/{name}.feature" for name in names)


def _changed_files(base: str) -> list[str]:
    """Return the files that differ from ``base``."""
    result = subprocess.run(  # noqa: S603 - fixed argument list
        ["git", "diff", "--name-only", f"{base}...HEAD"],  # noqa: S607
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _check_features_exist() -> None:
    """Fail when a group lists a feature file that does not exist."""
    existing = {path.stem for path in FEATURES_DIR.glob("*.feature")}
    missing = sorted(_listed_features() - existing)
    if missing:
        raise SystemExit(f"behave_matrix.py lists features that do not exist: {', '.join(missing)}")


def main(argv: list[str]) -> int:
    """Print the matrix and export it to GitHub Actions."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", help="git ref to diff against; without it every group runs")
    arguments = parser.parse_args(argv)
    _check_features_exist()
    changed = _changed_files(arguments.base) if arguments.base else None
    selected = select(changed)
    result = matrix(selected)
    print(json.dumps(result, indent=2))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with Path(output).open("a", encoding="utf-8") as handle:
            handle.write(f"matrix={json.dumps(result)}\n")
            handle.write(f"has_groups={'true' if selected else 'false'}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
