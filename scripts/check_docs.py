#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.14,<4"
# dependencies = [
#     "mkdocstrings-python>=2.0.11",
#     "mkdocstrings>=1.0.8",
#     "pymdown-extensions>=13.1.2",
#     "zensical==0.1.3",
# ]
# ///

"""Build the documentation and verify generated diagrams, redirects, and the error page."""

import json
import os
import re
import subprocess
import sys
import tomllib
from contextlib import contextmanager
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING
from urllib.parse import unquote, urljoin, urlsplit

if TYPE_CHECKING:
    from collections.abc import Generator


class PageLinks(HTMLParser):
    """Collect the links needed to verify a generated page."""

    def __init__(self, source: Path) -> None:
        super().__init__()
        self.canonical: str | None = None
        self.refresh: str | None = None
        self.links: set[str] = set()
        self.recovery_links: set[str] = set()
        self.assets: set[str] = set()
        self.mermaid_count = 0
        self.theme_config = ""
        self._in_recovery_navigation = False
        self._in_theme_config = False
        self.feed(source.read_text(encoding="utf-8"))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record the markup needed by the output checks."""
        attributes = dict(attrs)
        if tag == "pre" and "mermaid" in (attributes.get("class") or "").split():
            self.mermaid_count += 1
        if tag == "nav" and attributes.get("id") == "docs-recovery":
            self._in_recovery_navigation = True
        if tag == "a" and (href := attributes.get("href")):
            self.links.add(href)
            if self._in_recovery_navigation:
                self.recovery_links.add(href)
        if tag == "link" and attributes.get("rel") == "canonical":
            self.canonical = attributes.get("href")
        if tag == "link" and attributes.get("rel") in {"icon", "stylesheet"} and (href := attributes.get("href")):
            self.assets.add(href)
        if tag in {"img", "script"} and (src := attributes.get("src")):
            self.assets.add(src)
        if tag == "script" and attributes.get("id") == "__config":
            self._in_theme_config = True
        if tag == "meta" and attributes.get("http-equiv") == "refresh":
            self.refresh = (attributes.get("content") or "").partition("url=")[2]

    def handle_data(self, data: str) -> None:
        """Capture the generated theme settings used by search."""
        if self._in_theme_config:
            self.theme_config += data

    def handle_endtag(self, tag: str) -> None:
        """Stop collecting content when its enclosing element ends."""
        if tag == "nav":
            self._in_recovery_navigation = False
        if tag == "script":
            self._in_theme_config = False


def markdown_url(path: str, directory_urls: bool) -> str:
    """Return the output URL for a docs-relative Markdown path."""
    source = PurePosixPath(path)
    if source.name == "index.md":
        return "" if source.parent == PurePosixPath(".") else f"{source.parent}/"
    return f"{source.with_suffix('')}/" if directory_urls else str(source.with_suffix(".html"))


def site_file(site: Path, site_url: str, url: str) -> Path:
    """Resolve a URL under the published site to its generated file."""
    relative = url.removeprefix(site_url)
    if relative == url:
        raise SystemExit(f"Expected a documentation URL under {site_url}: {url}")
    path = unquote(urlsplit(relative).path)
    return site / (f"{path}index.html" if not path or path.endswith("/") else path)


def check_404(site: Path, site_url: str) -> None:
    """Verify the custom 404 works when served at a nested missing URL."""
    page = PageLinks(site / "404.html")
    missing_url = urljoin(site_url, "missing/deep/page/")
    destinations = {urljoin(missing_url, href) for href in page.recovery_links}
    if site_url not in destinations:
        raise SystemExit("Generated 404.html is missing the documentation home link")
    for url in sorted(destinations):
        if not site_file(site, site_url, url).is_file():
            raise SystemExit(f"Broken recovery link in 404.html: {url}")

    theme = json.loads(page.theme_config)
    search_base = urljoin(missing_url, f"{theme['base'].rstrip('/')}/")
    if search_base != site_url:
        raise SystemExit(f"Invalid search base in 404.html: {search_base}")
    assets = {urljoin(missing_url, asset) for asset in page.assets if not urlsplit(asset).scheme}
    assets.update({urljoin(missing_url, theme["search"]), urljoin(search_base, "search.json")})
    for url in sorted(assets):
        if not site_file(site, site_url, url).is_file():
            raise SystemExit(f"Missing asset in 404.html: {url}")


def check_output(config_path: Path) -> None:
    """Verify Mermaid diagrams, page redirects, and the custom 404."""
    with config_path.open("rb") as file:
        project = tomllib.load(file)["project"]
    site = config_path.parent / project.get("site_dir", "site")
    site_url = f"{project['site_url'].rstrip('/')}/"
    directory_urls = project.get("use_directory_urls", True)
    redirects = project["plugins"]["redirects"]["redirect_maps"]

    for source, expected in (("index.md", 1), ("getting-started/concepts.md", 2)):
        url = urljoin(site_url, markdown_url(source, directory_urls))
        count = PageLinks(site_file(site, site_url, url)).mermaid_count
        if count != expected:
            raise SystemExit(f"{source}: expected {expected} Mermaid diagrams, found {count}")

    for old, new in redirects.items():
        if urlsplit(old).fragment:
            continue  # Section redirects are handled on the destination page.
        old_url = urljoin(site_url, markdown_url(old, directory_urls))
        new_path = urlsplit(new)
        if new_path.scheme:
            expected_url = new
        else:
            expected_url = urljoin(site_url, markdown_url(new_path.path, directory_urls))
            if new_path.fragment:
                expected_url = f"{expected_url}#{new_path.fragment}"
            if not site_file(site, site_url, expected_url).is_file():
                raise SystemExit(f"Redirect target is missing: {new}")
        page = PageLinks(site_file(site, site_url, old_url))
        if (
            not page.canonical
            or page.refresh != page.canonical
            or page.canonical not in page.links
            or urljoin(old_url, page.canonical) != expected_url
        ):
            raise SystemExit(f"Invalid generated redirect: {old} -> {new}")

    check_404(site, site_url)
    print(f"Verified Mermaid diagram markup, redirects, and 404 links and assets under {site_url}")


@contextmanager
def build_config() -> Generator[Path]:
    """Use the current Read the Docs version URL when building there."""
    config = Path("zensical.toml")
    site_url = os.environ.get("READTHEDOCS_CANONICAL_URL")
    if not site_url:
        yield config
        return

    # Zensical resolves paths relative to the config and does not expand environment variables.
    source, replacements = re.subn(
        r"^site_url\s*=[^\n]*",
        lambda _: f"site_url = {json.dumps(site_url, ensure_ascii=False)}",
        config.read_text(encoding="utf-8"),
        count=1,
        flags=re.MULTILINE,
    )
    if not replacements:
        raise SystemExit(f"Missing site_url in {config}")
    with NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=config.parent,
        prefix=".zensical-",
        suffix=".toml",
        delete_on_close=False,
    ) as file:
        file.write(source)
        file.flush()
        yield Path(file.name)


def main() -> None:
    """Run a strict build and fail on Griffe diagnostics."""
    with build_config() as config:
        result = subprocess.run(
            [sys.executable, "-m", "zensical", "build", "--config-file", str(config), "--clean", "--strict"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        print(result.stdout, end="")
        if result.returncode:
            raise SystemExit(result.returncode)
        if any(line.startswith("griffe:") for line in result.stdout.splitlines()):
            raise SystemExit("Correct the Griffe docstring diagnostics above.")
        check_output(config)


if __name__ == "__main__":
    main()
