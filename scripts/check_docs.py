"""Build the documentation and verify the generated error page and redirects."""

import subprocess
import sys
import tomllib
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit


class PageLinks(HTMLParser):
    """Collect the links needed to verify a generated page."""

    def __init__(self, source: Path) -> None:
        super().__init__()
        self.canonical: str | None = None
        self.refresh: str | None = None
        self.links: set[str] = set()
        self.recovery_links: set[str] = set()
        self._in_recovery_list = False
        self.feed(source.read_text(encoding="utf-8"))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Record canonical, refresh, and visible fallback links."""
        attributes = dict(attrs)
        if tag == "ul" and attributes.get("id") == "docs-recovery":
            self._in_recovery_list = True
        if tag == "a" and (href := attributes.get("href")):
            self.links.add(href)
            if self._in_recovery_list:
                self.recovery_links.add(href)
        if tag == "link" and attributes.get("rel") == "canonical":
            self.canonical = attributes.get("href")
        if tag == "meta" and attributes.get("http-equiv") == "refresh":
            self.refresh = (attributes.get("content") or "").partition("url=")[2]

    def handle_endtag(self, tag: str) -> None:
        """Stop collecting custom recovery links at the end of their list."""
        if tag == "ul":
            self._in_recovery_list = False


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


def check_output(config_path: Path) -> None:
    """Verify each page redirect and the custom 404 recovery links."""
    with config_path.open("rb") as file:
        project = tomllib.load(file)["project"]
    site = config_path.parent / project.get("site_dir", "site")
    site_url = f"{project['site_url'].rstrip('/')}/"
    directory_urls = project.get("use_directory_urls", True)
    redirects = project["plugins"]["redirects"]["redirect_maps"]

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

    recovery = PageLinks(site / "404.html").recovery_links
    if not recovery:
        raise SystemExit("Generated 404.html is missing the custom recovery links")
    missing_url = urljoin(site_url, "missing/deep/page/")
    for href in sorted(recovery):
        if not site_file(site, site_url, urljoin(missing_url, href)).is_file():
            raise SystemExit(f"Broken recovery link in 404.html: {href}")
    print("Verified generated redirects and custom 404 links.")


def main() -> None:
    """Run a strict build and fail on Griffe diagnostics."""
    result = subprocess.run(
        [sys.executable, "-m", "zensical", "build", "--clean", "--strict"],
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
    check_output(Path("zensical.toml"))


if __name__ == "__main__":
    main()
