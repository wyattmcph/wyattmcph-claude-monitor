"""PyPI version check and auto-update for Claude Monitor.

Two modes:

1. Startup check (synchronous):
   Called before the monitor starts. Fetches the latest version, and if a
   newer one exists, prompts the user to install it (default: yes). On a
   successful upgrade it exits cleanly so the user restarts with the new
   version. Network failures are silently ignored.

2. Background check (async):
   Called after startup. Runs in a daemon thread and stores the result.
   If a newer version is found, a dim notice line appears in the status bar.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import threading
import urllib.request
from typing import Optional

from claude_monitor import __version__

logger = logging.getLogger(__name__)

_PYPI_URL  = "https://pypi.org/pypi/wyattmcph-claude-monitor/json"
_PACKAGE   = "wyattmcph-claude-monitor"
_TIMEOUT   = 4   # seconds for the synchronous startup check


def _parse_version(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.strip().lstrip("v").split("."))
    except Exception:
        return (0,)


def _fetch_latest() -> Optional[str]:
    """Return the latest PyPI version string, or None on any error."""
    try:
        req = urllib.request.Request(
            _PYPI_URL,
            headers={
                "Accept":     "application/json",
                "User-Agent": f"{_PACKAGE}/{__version__}",
            },
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return json.loads(resp.read().decode())["info"]["version"]
    except Exception as exc:
        logger.debug("PyPI fetch failed: %s", exc)
        return None


# ── Startup (synchronous) check ────────────────────────────────────────────────

def startup_update_check(skip: bool = False) -> None:
    """Check for an update before the monitor starts.

    If a newer version is available, prompts the user (default: Y) and
    runs the appropriate upgrade command. On success, prints a message and
    exits so the user restarts with the new version. Silently does nothing
    if the network is unavailable or the user declines.

    Args:
        skip: Pass True to suppress the check entirely (e.g. --popup mode).
    """
    if skip:
        return

    # If running as a standalone executable (PyInstaller), skip update check
    # because pip upgrades won't update the .exe file
    if getattr(sys, "frozen", False):
        logger.debug("Running as standalone executable, skipping update check")
        return

    # If we can't determine the running version, skip to avoid false positives
    if __version__ in ("unknown", ""):
        return

    latest = _fetch_latest()
    if not latest or _parse_version(latest) <= _parse_version(__version__):
        return

    # An update is available
    print(f"\n  Update available: v{latest}  (you have v{__version__})")
    print(f"  Download from: https://github.com/wyattmcph/wyattmcph-claude-monitor/releases\n")

    try:
        raw = input("  Install now? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if raw not in ("", "y", "yes"):
        print()
        return

    # Try uv first, fall back to pip
    upgraded = _try_upgrade_uv(latest) or _try_upgrade_pip(latest)

    if upgraded:
        print(f"\n  Updated to v{latest}. Run claude-monitor again to start.\n")
        sys.exit(0)
    else:
        print(
            f"\n  Automatic upgrade failed.\n"
            f"  Download the latest version from:\n"
            f"  https://github.com/wyattmcph/wyattmcph-claude-monitor/releases\n"
        )


def _try_upgrade_uv(latest: str) -> bool:
    """Attempt upgrade via uv. Returns True on success."""
    try:
        result = subprocess.run(
            ["uv", "tool", "upgrade", _PACKAGE],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            logger.debug("uv upgrade succeeded: %s", result.stdout.strip())
            return True
        logger.debug("uv upgrade failed: %s", result.stderr.strip())
    except FileNotFoundError:
        logger.debug("uv not found, trying pip")
    except Exception as exc:
        logger.debug("uv upgrade error: %s", exc)
    return False


def _try_upgrade_pip(latest: str) -> bool:
    """Attempt upgrade via pip. Returns True on success."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", _PACKAGE],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            logger.debug("pip upgrade succeeded")
            return True
        logger.debug("pip upgrade failed: %s", result.stderr.strip())
    except Exception as exc:
        logger.debug("pip upgrade error: %s", exc)
    return False


# ── Background (async) check ───────────────────────────────────────────────────

class UpdateChecker:
    """Singleton that checks PyPI in a background thread.

    The result is used to show a notice line in the running monitor display.
    """

    _instance: Optional[UpdateChecker] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        self.latest_version: Optional[str] = None
        self.update_available: bool = False
        self._started: bool = False

    @classmethod
    def get(cls) -> UpdateChecker:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def start(self) -> None:
        """Start the background check (idempotent)."""
        if self._started:
            return
        self._started = True
        t = threading.Thread(target=self._check, daemon=True, name="update-check")
        t.start()

    def _check(self) -> None:
        latest = _fetch_latest()
        if latest:
            self.latest_version = latest
            if _parse_version(latest) > _parse_version(__version__):
                self.update_available = True

    @property
    def notice(self) -> Optional[str]:
        """One-line notice for the status bar, or None."""
        if self.update_available and self.latest_version:
            return (
                f"v{self.latest_version} available -- "
                f"uv tool upgrade {_PACKAGE}"
            )
        return None
