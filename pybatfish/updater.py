# coding=utf-8
"""Updater module — checks for new versions and downloads updates.

Three independent components:

1. Manifest Fetcher  — downloads and parses version.json
2. Version Comparator — decides whether an update is needed
3. Downloader — saves the new executable to disk
"""

import json
import logging
import os
import shutil
from packaging import version as pkg_version

try:
    from urllib.request import urlopen, Request
    from urllib.error import URLError
except ImportError:
    from urllib2 import urlopen, Request, URLError

logger = logging.getLogger(__name__)

MANIFEST_URL = "https://www.mygoto4it.com/version.json"


# ---------------------------------------------------------------------------
# 1. Manifest Fetcher
# ---------------------------------------------------------------------------

def fetch_manifest(url=None):
    """Download the version manifest and return the latest version and URL.

    Fetches a small JSON file from the server, reads the "latest" version
    value, and reads the download URL.

    :param url: URL of the version manifest. Defaults to MANIFEST_URL.
    :type url: str or None
    :returns: A dict with keys "latest" (version string) and "url" (download link).
    :rtype: dict
    :raises RuntimeError: If the manifest cannot be fetched or is malformed.
    """
    if url is None:
        url = MANIFEST_URL

    try:
        request = Request(url)
        response = urlopen(request, timeout=30)
        data = json.loads(response.read().decode("utf-8"))
    except (URLError, ValueError, OSError) as exc:
        raise RuntimeError(
            "Failed to fetch version manifest from {}: {}".format(url, exc)
        )

    latest = data.get("latest")
    download_url = data.get("url")
    if not latest or not download_url:
        raise RuntimeError(
            "Manifest is missing required fields 'latest' and/or 'url'. "
            "Got: {}".format(data)
        )

    return {"latest": latest, "url": download_url}


# ---------------------------------------------------------------------------
# 2. Version Comparator
# ---------------------------------------------------------------------------

def is_update_needed(current_version, latest_version):
    """Compare the current version with the latest version from the manifest.

    Uses semantic version parsing to decide whether an update is needed.

    :param current_version: The bot's current internal version (e.g. "1.2.0").
    :type current_version: str
    :param latest_version: The latest version string from the manifest.
    :type latest_version: str
    :returns: True if latest_version is newer than current_version.
    :rtype: bool
    """
    return pkg_version.parse(latest_version) > pkg_version.parse(current_version)


# ---------------------------------------------------------------------------
# 3. Downloader
# ---------------------------------------------------------------------------

def download_exe(url, dest_dir=None):
    """Download the new executable and save it to disk.

    Downloads the file from the given URL and saves it into dest_dir.
    This is just a file transfer — no execution, no process control.

    :param url: Download URL for the EXE file.
    :type url: str
    :param dest_dir: Directory to save the file in. Defaults to the current
        working directory.
    :type dest_dir: str or None
    :returns: Full path to the downloaded file.
    :rtype: str
    :raises RuntimeError: If the download fails.
    """
    if dest_dir is None:
        dest_dir = os.getcwd()

    filename = os.path.basename(url) or "update.exe"
    dest_path = os.path.join(dest_dir, filename)

    try:
        request = Request(url)
        response = urlopen(request, timeout=120)
        with open(dest_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)
    except (URLError, OSError) as exc:
        raise RuntimeError(
            "Failed to download EXE from {}: {}".format(url, exc)
        )

    logger.info("Downloaded update to %s", dest_path)
    return dest_path


# ---------------------------------------------------------------------------
# 4. Wrapper — ties all three steps together
# ---------------------------------------------------------------------------

def check_and_update(current_version, download_dir=None, manifest_url=None):
    """Fetch manifest, compare versions, and download the EXE if newer.

    This is the main entry point that combines all three steps:
    fetch_manifest -> is_update_needed -> download_exe.

    :param current_version: The bot's current internal version (e.g. "1.2.0").
    :type current_version: str
    :param download_dir: Directory to save the downloaded EXE. Defaults to cwd.
    :type download_dir: str or None
    :param manifest_url: URL of the version manifest. Defaults to MANIFEST_URL.
    :type manifest_url: str or None
    :returns: Path to the downloaded file if an update was downloaded, or None
        if already up-to-date.
    :rtype: str or None
    :raises RuntimeError: If the manifest cannot be fetched or download fails.
    """
    manifest = fetch_manifest(url=manifest_url)
    latest_version = manifest["latest"]
    exe_url = manifest["url"]

    if not is_update_needed(current_version, latest_version):
        logger.info(
            "Already up-to-date (current=%s, latest=%s).",
            current_version,
            latest_version,
        )
        return None

    logger.info(
        "New version available: %s (current: %s). Downloading...",
        latest_version,
        current_version,
    )

    return download_exe(exe_url, dest_dir=download_dir)
