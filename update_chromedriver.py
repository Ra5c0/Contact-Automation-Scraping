
import platform
import requests
import zipfile
import os
import io
from pathlib import Path

DEST_DIR = Path("chromedriver")

def get_platform_key():
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Windows":
        return "win64" if "64" in machine else "win32"
    elif system == "Linux":
        return "linux64"
    elif system == "Darwin":
        # arm64 for Apple Silicon, mac-x64 for Intel
        return "mac-arm64" if "arm" in machine or "aarch" in machine else "mac-x64"
    else:
        raise RuntimeError(f"Unsupported OS: {system} ({machine})")

def get_latest_chromedriver_url():
    api_url = "https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json"
    response = requests.get(api_url, timeout=30)
    response.raise_for_status()
    data = response.json()

    platform_key = get_platform_key()
    downloads = data["channels"]["Stable"]["downloads"]["chromedriver"]
    for item in downloads:
        if item["platform"] == platform_key:
            return item["url"]
    raise RuntimeError(f"No matching ChromeDriver URL for platform {platform_key}")

def download_and_extract_zip(url: str, extract_to: Path):
    print(f"⬇️ Downloading: {url}")
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    extract_to.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        z.extractall(extract_to)
    print(f"✅ Extracted into: {extract_to.resolve()}")

def main():
    try:
        url = get_latest_chromedriver_url()
        download_and_extract_zip(url, DEST_DIR)
        # Print a hint path for convenience
        # Try to find a binary path for scripting
        import glob
        candidates = glob.glob(str(DEST_DIR / "**" / "chromedriver*"), recursive=True)
        if candidates:
            print(f"🔎 Candidate binary: {os.path.abspath(candidates[0])}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
