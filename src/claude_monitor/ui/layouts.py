"""UI layout managers for Claude Monitor.

This module consolidates layout management functionality including:
- Header formatting and styling
- Screen layout and organization
"""

from __future__ import annotations

from typing import Any, Final, Sequence

from rich.rule import Rule
from rich.text import Text


# Plan → rule colour mapping so the header rule matches the plan tier
_PLAN_STYLE: dict[str, str] = {
    "pro": "plan.pro",
    "max5": "plan.max5",
    "max20": "plan.max20",
    "custom": "plan.custom",
}


class HeaderManager:
    """Manager for header layout and formatting."""

    DEFAULT_SEPARATOR_CHAR: Final[str] = "="
    DEFAULT_SEPARATOR_LENGTH: Final[int] = 60

    def __init__(self) -> None:
        """Initialize header manager."""
        self.separator_char: str = self.DEFAULT_SEPARATOR_CHAR
        self.separator_length: int = self.DEFAULT_SEPARATOR_LENGTH

    # ── Rule-based header (works reliably in Live on all terminals) ────────

    def create_header_panel(
        self,
        plan: str = "pro",
        timezone: str = "Europe/Warsaw",
        animation_frame: int = 0,
        animation_level: str = "subtle",
    ) -> list[Any]:
        """Create a header using Rich Rule + text — compatible with all terminals.

        Returns a list of renderables (Rule, Text, str) that can be placed
        directly into the screen_buffer list.

        Args:
            plan: Current plan name.
            timezone: Display timezone string.
            animation_frame: Current global animation frame index.
            animation_level: One of 'none', 'subtle', 'moderate', 'full'.

        Returns:
            List of Rich renderables / strings for the header block.
        """
        from claude_monitor.terminal.themes import AnimationState

        live_dot = AnimationState.live_dot(animation_level)
        plan_style = _PLAN_STYLE.get(plan.lower(), "header")

        # Top rule with title
        title = Text("  CLAUDE CODE USAGE MONITOR  ", style="bold header")
        top_rule = Rule(title=title, style=plan_style)

        # Subtitle line: plan badge | timezone | live dot
        subtitle = Text(justify="center")
        subtitle.append(f" {plan.upper()} ", style=f"bold {plan_style}")
        subtitle.append("  │  ", style="separator")
        subtitle.append(timezone, style="dim")
        subtitle.append("  │  ", style="separator")
        subtitle.append(f"{live_dot} LIVE", style="success")

        # Bottom rule (plain, same colour)
        bottom_rule = Rule(style=plan_style)

        return [top_rule, subtitle, bottom_rule, ""]

    # ── Legacy create_header — now delegates to create_header_panel ────────

    def create_header(
        self, plan: str = "pro", timezone: str = "Europe/Warsaw"
    ) -> list[Any]:
        """Create header renderables.

        Args:
            plan: Current plan name
            timezone: Display timezone

        Returns:
            List of Rich renderables / strings for the header block.
        """
        return self.create_header_panel(plan=plan, timezone=timezone)


class ScreenManager:
    """Manager for overall screen layout and organization."""

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
        """Set screen dimensions for layout calculations."""
        self.screen_width = width
        self.screen_height = height

    def set_margins(
        self, left: int = 0, right: int = 0, top: int = 0, bottom: int = 0
    ) -> None:
        """Set screen margins."""
        self.margin_left = left
        self.margin_right = right
        self.margin_top = top
        self.margin_bottom = bottom

    def create_full_screen_layout(
        self, content_sections: Sequence[Sequence[str]]
    ) -> list[str]:
        """Create full screen layout with multiple content sections."""
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
