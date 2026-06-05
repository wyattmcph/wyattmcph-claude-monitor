"""Cross-platform OS-level notifications for Claude Monitor.

Sends a desktop notification (toast / balloon / libnotify) when token
usage crosses a threshold.  Falls back silently if the platform does
not support notifications or the required tools are not available.

Usage:
    notify("80% of token limit reached", "You have used 80% of your session tokens.")
"""

from __future__ import annotations

import logging
import subprocess
import sys
from typing import Optional

logger = logging.getLogger(__name__)

_APP_NAME = "Claude Monitor"


def notify(title: str, body: str, urgency: str = "normal") -> None:
    """Send a desktop notification.

    Args:
        title:   Short title shown in the notification banner.
        body:    Longer detail text.
        urgency: ``'low'``, ``'normal'``, or ``'critical'``.
                 Only used on Linux (notify-send).
    """
    try:
        if sys.platform == "win32":
            _notify_windows(title, body)
        elif sys.platform == "darwin":
            _notify_macos(title, body)
        else:
            _notify_linux(title, body, urgency)
    except Exception as exc:
        logger.debug("OS notification failed: %s", exc)


# ── Platform implementations ───────────────────────────────────────────────────

def _notify_windows(title: str, body: str) -> None:
    """Windows balloon-tip via PowerShell — no extra dependencies."""
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$n = New-Object System.Windows.Forms.NotifyIcon;"
        "$n.Icon = [System.Drawing.SystemIcons]::Information;"
        "$n.Visible = $true;"
        f'$n.ShowBalloonTip(6000, "{_esc(title)}", "{_esc(body)}", '
        "[System.Windows.Forms.ToolTipIcon]::Info);"
        "Start-Sleep -Milliseconds 6500;"
        "$n.Dispose()"
    )
    subprocess.Popen(
        ["powershell", "-WindowStyle", "Hidden", "-Command", ps],
        creationflags=0x08000000,  # CREATE_NO_WINDOW
        close_fds=True,
    )


def _notify_macos(title: str, body: str) -> None:
    """macOS notification via osascript."""
    script = (
        f'display notification "{_esc(body)}" '
        f'with title "{_esc(title)}" '
        f'subtitle "{_APP_NAME}"'
    )
    subprocess.Popen(
        ["osascript", "-e", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _notify_linux(title: str, body: str, urgency: str) -> None:
    """Linux notification via notify-send."""
    subprocess.Popen(
        [
            "notify-send",
            "--app-name", _APP_NAME,
            f"--urgency={urgency}",
            "--expire-time=6000",
            title,
            body,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _esc(text: str) -> str:
    """Escape double-quotes for PowerShell / osascript string embedding."""
    return text.replace('"', '\\"').replace("'", "\\'")
