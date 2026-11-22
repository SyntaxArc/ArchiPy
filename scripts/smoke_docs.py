"""Execute the Python examples published in the quickstart and upgrade guide."""

import os
import re
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

QUICKSTART = Path("docs/getting-started/quickstart.md")
UPGRADE = Path("docs/community/deprecations.md")
PYTHON_FENCES = re.compile(r"^```python\n(.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)


def example(page: Path, filename: str) -> str:
    """Read the fenced Python example identified by its filename comment."""
    prefix = f"# {filename}\n"
    matches = [block for block in PYTHON_FENCES.findall(page.read_text(encoding="utf-8")) if block.startswith(prefix)]
    if len(matches) != 1:
        raise SystemExit(f"{page}: expected one Python example for {filename}")
    return matches[0]


def run_python(directory: Path, *args: str, env: dict[str, str] | None = None) -> str:
    """Run an example in a fresh interpreter using the current environment."""
    result = subprocess.run(
        [sys.executable, *args],
        cwd=directory,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    output = result.stdout + result.stderr
    if result.returncode:
        raise SystemExit(f"Example failed: {' '.join(args)}\n{output}")
    return output


def quickstart(directory: Path) -> None:
    """Check the documented CLI output and Redis TTL through the adapter."""
    for filename in ("configs/app_config.py", "adapters/cache_adapter.py", "logics/user_logic.py", "manage.py"):
        target = directory / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(example(QUICKSTART, filename), encoding="utf-8")

    user_id = f"docs-smoke-{uuid4().hex}"
    output = run_python(directory, "manage.py", "run", user_id)
    cache_misses = [line for line in output.splitlines() if f"Cache miss — fetching user {user_id}" in line]
    responses = [line for line in output.splitlines() if line == f"INFO:__main__:User-{user_id}"]
    if len(cache_misses) != 1 or len(responses) != 2:
        raise SystemExit(f"Expected one cache miss and two matching results:\n{output}")

    key = f"user:name:{user_id}"
    run_python(
        directory,
        "-c",
        "import configs.app_config\n"
        "from adapters.cache_adapter import redis\n"
        "import sys\n"
        "key = sys.argv[1]\n"
        "ttl = redis.ttl(key)\n"
        "redis.delete(key)\n"
        "if not 0 < ttl <= 60:\n"
        "    raise SystemExit(f'Expected a cache TTL between 1 and 60 seconds, found {ttl}')\n",
        key,
    )


def upgrade(directory: Path) -> None:
    """Verify that the documented replacement decorator and Redis TLS setting work."""
    retry = example(UPGRADE, "retry_example.py")
    run_python(
        directory,
        "-c",
        f"{retry}\nif result != 'ready':\n    raise SystemExit('Retry example did not recover')\n",
    )

    tls = example(UPGRADE, "redis_tls.py")
    run_python(
        directory,
        "-c",
        f"{tls}\nif not redis_tls_enabled:\n    raise SystemExit('Nested Redis TLS env var was ignored')\n",
        env={**os.environ, "REDIS__TLS__IS_ENABLED": "true"},
    )


def main() -> None:
    """Run the docs smoke checks without reusing project or Redis state."""
    with TemporaryDirectory(prefix="archipy-docs-examples-") as directory:
        root = Path(directory)
        quickstart(root)
        upgrade(root)
    print("Quickstart cache and 6.0 upgrade examples passed.")


if __name__ == "__main__":
    main()
