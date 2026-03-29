# coding=utf-8
"""Auto-update utility for checking and downloading newer versions."""

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


def check_and_update(current_version, download_dir=None, manifest_url=None):
    """Fetch the remote manifest, compare versions, and download the EXE if newer.

    :param current_version: The bot's current internal version string (e.g. "1.2.0").
    :type current_version: str
    :param download_dir: Directory to save the downloaded EXE. Defaults to
        the current working directory.
    :type download_dir: str or None
    :param manifest_url: URL of the version manifest. Defaults to MANIFEST_URL.
    :type manifest_url: str or None
    :returns: Path to the downloaded file if an update was downloaded, or None
        if already up-to-date.
    :rtype: str or None
    :raises RuntimeError: If the manifest cannot be fetched or parsed.
    """
    if manifest_url is None:
        manifest_url = MANIFEST_URL
    if download_dir is None:
        download_dir = os.getcwd()

    # 1. Fetch the manifest
    latest_version, exe_url = _fetch_manifest(manifest_url)

    # 2. Compare versions
    if pkg_version.parse(latest_version) <= pkg_version.parse(current_version):
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

    # 3. Download the EXE
    dest_path = _download_exe(exe_url, download_dir)
    logger.info("Downloaded update to %s", dest_path)
    return dest_path


def _fetch_manifest(url):
    """Fetch and parse the version manifest JSON.

    :param url: URL of the version manifest.
    :type url: str
    :returns: A tuple of (latest_version, exe_url).
    :rtype: tuple[str, str]
    :raises RuntimeError: If the manifest cannot be fetched or is malformed.
    """
    try:
        request = Request(url)
        response = urlopen(request, timeout=30)
        data = json.loads(response.read().decode("utf-8"))
    except (URLError, ValueError, OSError) as exc:
        raise RuntimeError(
            "Failed to fetch version manifest from {}: {}".format(url, exc)
        )

    latest = data.get("latest")
    exe_url = data.get("url")
    if not latest or not exe_url:
        raise RuntimeError(
            "Manifest is missing required fields 'latest' and/or 'url'. "
            "Got: {}".format(data)
        )
    return latest, exe_url


def _download_exe(url, dest_dir):
    """Download the EXE from the given URL into dest_dir.

    :param url: Download URL for the EXE file.
    :type url: str
    :param dest_dir: Directory to save the file in.
    :type dest_dir: str
    :returns: Full path to the downloaded file.
    :rtype: str
    :raises RuntimeError: If the download fails.
    """
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

    return dest_path
