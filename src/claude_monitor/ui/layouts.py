"""UI layout managers for Claude Monitor.

This module consolidates layout management functionality including:
- Header formatting and styling
- Screen layout and organization
"""

from __future__ import annotations

from typing import Any, Final, Optional, Sequence

from rich.align import Align
from rich.panel import Panel
from rich.text import Text


# Plan → border colour mapping so the header border matches the plan tier
_PLAN_BORDER: dict[str, str] = {
    "pro": "plan.pro",
    "max5": "plan.max5",
    "max20": "plan.max20",
    "custom": "plan.custom",
}


class HeaderManager:
    """Manager for header layout and formatting."""

    # Type constants for header configuration
    DEFAULT_SEPARATOR_CHAR: Final[str] = "="
    DEFAULT_SEPARATOR_LENGTH: Final[int] = 60
    DEFAULT_SPARKLES: Final[str] = "✦ ✧ ✦ ✧"

    def __init__(self) -> None:
        """Initialize header manager."""
        self.separator_char: str = self.DEFAULT_SEPARATOR_CHAR
        self.separator_length: int = self.DEFAULT_SEPARATOR_LENGTH

    # ── Rich Panel header (new) ────────────────────────────────────────────

    def create_header_panel(
        self,
        plan: str = "pro",
        timezone: str = "Europe/Warsaw",
        animation_frame: int = 0,
        animation_level: str = "subtle",
    ) -> Panel:
        """Create a visually rich header Panel with animated LIVE indicator.

        Args:
            plan: Current plan name.
            timezone: Display timezone string.
            animation_frame: Current global animation frame index.
            animation_level: One of 'none', 'subtle', 'moderate', 'full'.

        Returns:
            A Rich Panel that can be placed directly in a render Group.
        """
        from claude_monitor.terminal.themes import AnimationState

        live_dot = AnimationState.live_dot(animation_level)

        # Build subtitle line: plan badge | timezone | LIVE dot
        subtitle = Text(justify="center")
        plan_style = _PLAN_BORDER.get(plan.lower(), "plan.pro")
        subtitle.append(f" {plan.upper()} ", style=f"bold {plan_style}")
        subtitle.append(" │ ", style="separator")
        subtitle.append(timezone, style="dim")
        subtitle.append(" │ ", style="separator")
        if animation_level == "none":
            subtitle.append("● LIVE", style="success")
        else:
            subtitle.append(f"{live_dot} LIVE", style="success")

        border_style = _PLAN_BORDER.get(plan.lower(), "header")

        return Panel(
            Align.center(subtitle),
            title=Text(
                "✦  CLAUDE CODE USAGE MONITOR  ✦",
                style="bold header",
            ),
            border_style=border_style,
            padding=(0, 2),
        )

    # ── Legacy string-buffer header (kept for backward compat) ────────────

    def create_header(
        self, plan: str = "pro", timezone: str = "Europe/Warsaw"
    ) -> list[Any]:
        """Create header using the new Panel style.

        Returns a one-element list containing a Rich Panel so that it can
        be inserted directly into the existing screen_buffer lists.

        Args:
            plan: Current plan name
            timezone: Display timezone

        Returns:
            List containing a single Rich Panel object followed by an empty line.
        """
        panel = self.create_header_panel(plan=plan, timezone=timezone)
        return [panel, ""]


class ScreenManager:
    """Manager for overall screen layout and organization."""

    # Type constants for screen configuration
    DEFAULT_SCREEN_WIDTH: Final[int] = 80
    DEFAULT_SCREEN_HEIGHT: Final[int] = 24
    DEFAULT_MARGIN: Final[int] = 0

    def __init__(self) -> None:
        """Initialize screen manager."""
        self.screen_width: int = self.DEFAULT_SCREEN_WIDTH
        self.screen_height: int = self.DEFAULT_SCREEN_HEIGHT
        self.margin_left: int = self.DEFAULT_MARGIN
        self.margin_right: int = self.DEFAULT_MARGIN
        self.margin_top: int = self.DEFAULT_MARGIN
        self.margin_bottom: int = self.DEFAULT_MARGIN

    def set_screen_dimensions(self, width: int, height: int) -> None:
        """Set screen dimensions for layout calculations.

        Args:
            width: Screen width in characters
            height: Screen height in lines
        """
        self.screen_width = width
        self.screen_height = height

    def set_margins(
        self, left: int = 0, right: int = 0, top: int = 0, bottom: int = 0
    ) -> None:
        """Set screen margins.

        Args:
            left: Left margin in characters
            right: Right margin in characters
            top: Top margin in lines
            bottom: Bottom margin in lines
        """
        self.margin_left = left
        self.margin_right = right
        self.margin_top = top
        self.margin_bottom = bottom

    def create_full_screen_layout(
        self, content_sections: Sequence[Sequence[str]]
    ) -> list[str]:
        """Create full screen layout with multiple content sections.

        Args:
            content_sections: List of content sections, each being a list of lines

        Returns:
            Combined screen layout as list of lines
        """
        screen_buffer: list[str] = []

        screen_buffer.extend([""] * self.margin_top)

        for i, section in enumerate(content_sections):
            if i > 0:
                screen_buffer.append("")

            for line in section:
                padded_line: str = " " * self.margin_left + line
                screen_buffer.append(padded_line)

        screen_buffer.extend([""] * self.margin_bottom)

        return screen_buffer


__all__ = ["HeaderManager", "ScreenManager"]
