import os
import glob
import random
import time
from shutil import which
from urllib.parse import urlparse, urlunparse


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
