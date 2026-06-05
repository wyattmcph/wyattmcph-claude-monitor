"""Adaptive layout tiers for Claude Monitor.

Reads the current terminal size and returns a :class:`LayoutConfig` that
tells ``session_display.py`` which sections to render.  As the user resizes
their terminal, the display automatically adds or removes sections:

  NANO     (< 18 rows) — bare essentials: token bar + cost only
  COMPACT  (18-27 rows) — core metrics, no keywords/model breakdown
  STANDARD (28-37 rows) — full session stats, no keyword panel
  FULL     (38+ rows)  — everything including keyword analytics panel

Bar width also adapts to terminal *width*:
  < 80 cols  → 20-char bars
  80-109     → 30-char bars
  110+       → 45-char bars
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from enum import Enum


class LayoutTier(Enum):
    """Terminal-height display tiers, smallest → largest."""

    NANO     = "nano"
    COMPACT  = "compact"
    STANDARD = "standard"
    FULL     = "full"


@dataclass
class LayoutConfig:
    """Declarative spec: what to render at a given tier/width."""

    tier: LayoutTier
    bar_width: int

    # Metric sections
    show_cost_bar: bool = True
    show_token_bar: bool = True
    show_messages_bar: bool = True
    show_time_bar: bool = True
    show_model_bar: bool = True

    # Secondary info
    show_burn_rate: bool = True
    show_sparkline: bool = False
    show_predictions: bool = True
    show_notifications: bool = True

    # Keywords panel — only in FULL tier when enabled
    show_keywords: bool = False


def get_terminal_size() -> tuple[int, int]:
    """Return ``(cols, rows)`` for the current terminal."""
    s = shutil.get_terminal_size((80, 24))
    return s.columns, s.lines


def get_layout_config(
    animation_level: str = "subtle",
    keywords_enabled: bool = False,
) -> LayoutConfig:
    """Return a :class:`LayoutConfig` for the current terminal.

    Args:
        animation_level: ``'none'``, ``'subtle'``, ``'moderate'``, or
            ``'full'``.  Sparkline is shown for *moderate* / *full*.
        keywords_enabled: ``True`` when keywords are configured **and** the
            user has not disabled the panel (``--no-keywords``).

    Returns:
        A :class:`LayoutConfig` instance sized for the current terminal.
    """
    cols, rows = get_terminal_size()
    sparkline  = animation_level in ("moderate", "full")

    # Bar width scales with terminal width
    if cols < 80:
        bar_width = 20
    elif cols < 110:
        bar_width = 30
    else:
        bar_width = 45

    # Select tier by available rows
    if rows < 18:
        tier = LayoutTier.NANO
    elif rows < 28:
        tier = LayoutTier.COMPACT
    elif rows < 38:
        tier = LayoutTier.STANDARD
    else:
        tier = LayoutTier.FULL

    if tier is LayoutTier.NANO:
        return LayoutConfig(
            tier=tier, bar_width=bar_width,
            show_cost_bar=False, show_token_bar=True,
            show_messages_bar=False, show_time_bar=False,
            show_model_bar=False, show_burn_rate=True,
            show_sparkline=False, show_predictions=False,
            show_notifications=False, show_keywords=False,
        )

    if tier is LayoutTier.COMPACT:
        return LayoutConfig(
            tier=tier, bar_width=bar_width,
            show_cost_bar=True, show_token_bar=True,
            show_messages_bar=False, show_time_bar=True,
            show_model_bar=False, show_burn_rate=True,
            show_sparkline=False, show_predictions=True,
            show_notifications=True, show_keywords=False,
        )

    if tier is LayoutTier.STANDARD:
        return LayoutConfig(
            tier=tier, bar_width=bar_width,
            show_cost_bar=True, show_token_bar=True,
            show_messages_bar=True, show_time_bar=True,
            show_model_bar=True, show_burn_rate=True,
            show_sparkline=sparkline, show_predictions=True,
            show_notifications=True, show_keywords=False,
        )

    # FULL
    return LayoutConfig(
        tier=tier, bar_width=bar_width,
        show_cost_bar=True, show_token_bar=True,
        show_messages_bar=True, show_time_bar=True,
        show_model_bar=True, show_burn_rate=True,
        show_sparkline=sparkline, show_predictions=True,
        show_notifications=True, show_keywords=keywords_enabled,
    )
