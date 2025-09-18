import os
import glob
import random
import time
from collections.abc import Iterable
from shutil import which
from urllib.parse import parse_qs, urlparse, urlunparse, unquote, unquote_plus


def load_env_file(path: str = ".env") -> None:
    """Load simple KEY=VALUE pairs from *path* into ``os.environ``.

    Existing variables are preserved. Lines starting with ``#`` or without an
    ``=`` are ignored.
    """
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip())


def find_chromedriver_binary() -> str | None:
    """Return path to chromedriver if found in common locations or PATH.

    Searches environment hints, typical local folders, and system PATH for a
    ChromeDriver executable. Returns an absolute path if found, otherwise
    ``None``.
    """
    # Environment variables sometimes specify an explicit path
    env_path = os.getenv("CHROMEDRIVER") or os.getenv("CHROMEDRIVER_PATH")
    if env_path and os.path.isfile(env_path):
        return os.path.abspath(env_path)

    # Search in PATH
    path_bin = which("chromedriver")
    if path_bin:
        return os.path.abspath(path_bin)

    # Common local locations (update_chromedriver.py uses chromedriver/)
    candidates = [
        "chromedriver",
        os.path.join("chromedriver", "chromedriver"),
        os.path.join("chromedriver", "chromedriver.exe"),
    ]

    # Expand search inside the chromedriver folder
    candidates.extend(glob.glob("chromedriver/**/chromedriver*", recursive=True))

    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return os.path.abspath(candidate)
    return None


def normalize_linkedin_url(url: str | None) -> str | None:
    """Normalize LinkedIn URLs to https://www.linkedin.com/... without params."""
    if not isinstance(url, str):
        return url
    url = url.strip()
    if not url:
        return url
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    # Force https scheme and www.linkedin.com netloc when relevant
    netloc = parsed.netloc
    if "linkedin.com" in netloc:
        netloc = "www.linkedin.com"
    normalized = urlunparse(
        ("https", netloc, parsed.path, "", "", "")
    )
    return normalized


def decode_duckduckgo_href(href: str | None) -> str | None:
    """Return the resolved URL for a DuckDuckGo redirect *href*.

    DuckDuckGo result links often redirect through ``duckduckgo.com/l/`` with an
    ``uddg`` query parameter that contains the actual destination URL.
    ``decode_duckduckgo_href`` extracts and decodes this parameter. If *href*
    is already a direct URL, it is returned stripped of leading/trailing
    whitespace. ``None`` is returned when *href* is not a string or is empty.
    """

    if not isinstance(href, str):
        return None

    candidate = href.strip()
    if not candidate:
        return None

    parsed = urlparse(candidate)
    netloc = parsed.netloc.lower()
    if "duckduckgo.com" in netloc:
        query = parse_qs(parsed.query)
        uddg_values = query.get("uddg")
        if uddg_values:
            resolved = unquote_plus(uddg_values[0])
            resolved = unquote(resolved)
            return resolved
    return candidate


def find_first_linkedin_url(
    hrefs: Iterable[str], expected_substring: str
) -> str | None:
    """Return the first normalized LinkedIn URL matching *expected_substring*.

    The function iterates over *hrefs*, decodes potential DuckDuckGo redirect
    links and returns the first URL whose lowercase form contains
    *expected_substring* (also compared in lowercase). The resulting URL is
    normalized via :func:`normalize_linkedin_url` before being returned.
    """

    expected_lower = expected_substring.lower()
    for href in hrefs:
        resolved = decode_duckduckgo_href(href)
        if not resolved:
            continue
        if expected_lower in resolved.lower():
            return normalize_linkedin_url(resolved)
    return None


def polite_delay(a: float = 0.6, b: float = 1.4) -> None:
    """Sleep for a random duration between ``a`` and ``b`` seconds."""
    time.sleep(random.uniform(a, b))


def getenv_or_file(key: str, filename: str) -> str | None:
    """Return environment variable ``key`` or read first line of ``filename``.

    If the environment variable is not set and the file exists, the function
    reads the first line of the file (stripped of whitespace) and returns it.
    Returns ``None`` if neither source yields a value.
    """
    val = os.getenv(key)
    if val:
        return val
    if os.path.isfile(filename):
        with open(filename, "r", encoding="utf-8") as f:
            line = f.readline().strip()
            return line or None
    return None
