"""Terminal capability detection and icon set selection.

Detects at import time whether the running terminal supports extended
Unicode, then exposes a single ``ICONS`` dict that all UI modules use.
This means the correct icon set is chosen once at startup — modern
terminals get the geometric glyphs, legacy Windows consoles get ASCII.

Detection logic:
  - If running as a PyInstaller bundle on Windows without a modern host
    (Windows Terminal / VS Code / etc.) → legacy ASCII set.
  - Everything else (uv/pip install, macOS, Linux, or Windows Terminal)
    → modern Unicode set.
"""

from __future__ import annotations

import os
import sys
from typing import Dict


# ── Icon sets ──────────────────────────────────────────────────────────────────

_MODERN: Dict[str, str] = {
    "cost": "◈",
    "tokens": "◉",
    "messages": "▷",
    "burn": "↯",
    "model": "◆",
    "time": "◷",
    "predict": "✦",
    "cost_rate": "↗",
    "status": "●",
    "separator": "◌",
    "keyword": "◈",
    "header": "✦",
    "warning": "⚠",
    "check": "✓",
    "cross": "✗",
}

_LEGACY: Dict[str, str] = {
    "cost": "$",
    "tokens": "%",
    "messages": ">",
    "burn": "~",
    "model": "+",
    "time": "-",
    "predict": "*",
    "cost_rate": "^",
    "status": "*",
    "separator": "o",
    "keyword": "#",
    "header": "*",
    "warning": "!",
    "check": "OK",
    "cross": "X",
}


# ── Detection ──────────────────────────────────────────────────────────────────


def _is_modern_terminal() -> bool:
    """Return True if the terminal can render extended Unicode glyphs.

    When running as a frozen PyInstaller executable on Windows, only
    Windows Terminal (and similar modern hosts) support the Geometric
    Shapes Unicode block.  The legacy cmd-style console falls back to
    the ASCII set.  On every other platform / install method the modern
    set is used.
    """
    if os.environ.get("CLAUDE_MONITOR_FORCE_UNICODE"):
        # Console was bootstrapped into UTF-8 mode (see console_setup.py) —
        # extended glyphs render correctly even in a frozen Windows console.
        return True

    if not getattr(sys, "frozen", False):
        # Not frozen (uv / pip / python -m) — always a capable terminal
        return True

    if sys.platform != "win32":
        # Frozen on macOS or Linux — Terminal.app / iTerm / gnome-terminal etc.
        return True

    # Frozen .exe on Windows: only safe if a modern host is detected
    return bool(
        os.environ.get("WT_SESSION")  # Windows Terminal
        or os.environ.get("TERM_PROGRAM")  # VS Code integrated terminal
        or os.environ.get("COLORTERM")  # truecolor-capable terminals
        or os.environ.get("TERM", "").startswith("xterm")
    )


# Single dict selected at module import time — no runtime branching needed
ICONS: Dict[str, str] = _MODERN if _is_modern_terminal() else _LEGACY
