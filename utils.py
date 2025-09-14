import os
from typing import Optional


def load_env_file(path: str = ".env") -> None:
    """Load environment variables from a simple ``.env`` file.

    Each non-empty, non-comment line should be of the form ``KEY=VALUE``.
    Existing environment variables are not overridden.
    """
    if not os.path.isfile(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def getenv_or_file(key: str, filepath: str) -> Optional[str]:
    """Return value from environment or from a local file.

    Parameters
    ----------
    key: The environment variable name.
    filepath: Fallback file whose first line provides the value if the
        environment variable is missing.
    """
    val = os.getenv(key)
    if val:
        return val
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.readline().strip() or None
    except OSError:
        return None
