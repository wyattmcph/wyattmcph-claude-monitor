"""Background PyPI version check.

Runs once per session in a daemon thread. Never blocks startup and never
raises — network errors are silently ignored.

Usage:
    UpdateChecker.get().start()          # call once at startup
    notice = UpdateChecker.get().notice  # None, or a one-line string
"""

from __future__ import annotations

import json
import logging
import threading
import urllib.request
from typing import Optional

from claude_monitor import __version__

logger = logging.getLogger(__name__)

_PYPI_URL = "https://pypi.org/pypi/wyattmcph-claude-monitor/json"


def _parse_version(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.strip().lstrip("v").split("."))
    except Exception:
        return (0,)


class UpdateChecker:
    """Singleton that checks PyPI for a newer release in the background."""

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
        """Start the background check. Safe to call more than once."""
        if self._started:
            return
        self._started = True
        t = threading.Thread(target=self._check, daemon=True, name="update-check")
        t.start()

    def _check(self) -> None:
        try:
            req = urllib.request.Request(
                _PYPI_URL,
                headers={
                    "Accept": "application/json",
                    "User-Agent": f"wyattmcph-claude-monitor/{__version__}",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())

            latest = data["info"]["version"]
            self.latest_version = latest

            if _parse_version(latest) > _parse_version(__version__):
                self.update_available = True
                logger.debug("Update available: %s -> %s", __version__, latest)

        except Exception as exc:
            logger.debug("Update check failed (this is fine): %s", exc)

    @property
    def notice(self) -> Optional[str]:
        """One-line update notice, or None if up to date or check not done."""
        if self.update_available and self.latest_version:
            return (
                f"v{self.latest_version} available -- "
                f"uv tool upgrade wyattmcph-claude-monitor"
            )
        return None
