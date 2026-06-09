"""Session display components for Claude Monitor.

Handles formatting of active session screens and session data display.
Uses :mod:`adaptive_layout` to pick the right sections based on terminal size.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import pytz

# ── Icon set — chosen at startup based on terminal capability ─────────────────
from claude_monitor.terminal.icons import ICONS as _IC
from claude_monitor.ui.components import CostIndicator, VelocityIndicator
from claude_monitor.ui.progress_bars import (
    ModelUsageBar,
    TimeProgressBar,
    TokenProgressBar,
)
from claude_monitor.utils.time_utils import (
    format_display_time,
    get_time_format_preference,
    percentage,
)

_I_COST = _IC["cost"]
_I_TOKENS = _IC["tokens"]
_I_MESSAGES = _IC["messages"]
_I_BURN = _IC["burn"]
_I_MODEL = _IC["model"]
_I_TIME = _IC["time"]
_I_PREDICT = _IC["predict"]
_I_COSTRATE = _IC["cost_rate"]
_I_STATUS = _IC["status"]
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class SessionDisplayData:
    """Data container for session display information."""

    plan: str
    timezone: str
    tokens_used: int
    token_limit: int
    usage_percentage: float
    tokens_left: int
    elapsed_session_minutes: float
    total_session_minutes: float
    burn_rate: float
    session_cost: float
    per_model_stats: dict[str, Any]
    sent_messages: int
    entries: list[dict]
    predicted_end_str: str
    reset_time_str: str
    current_time_str: str
    show_switch_notification: bool = False
    show_exceed_notification: bool = False
    show_tokens_will_run_out: bool = False
    original_limit: int = 0


class SessionDisplayComponent:
    """Main component for displaying active session information."""

    def __init__(self):
        self.token_progress = TokenProgressBar()
        self.time_progress = TimeProgressBar()
        self.model_usage = ModelUsageBar()

    # ── Wide gradient bar ─────────────────────────────────────────────────────

    def _render_wide_progress_bar(self, pct: float, width: int = 45) -> str:
        """Render a wide green→yellow→red gradient bar.

        Args:
            pct:   Progress percentage (may exceed 100).
            width: Bar width in characters (use ``layout.bar_width``).

        Returns:
            Rich markup string: ``icon [gradient_bar]``.
        """
        icon = "  "  # status conveyed by bar color, not an icon
        bar = TokenProgressBar(width=width)
        filled = bar._calculate_filled_segments(min(pct, 100.0), 100.0)
        return f"{icon} [{bar._render_gradient_bar(filled)}]"

    # ── v2 wrapper ────────────────────────────────────────────────────────────

    def format_active_session_screen_v2(self, data: SessionDisplayData) -> list[str]:
        return self.format_active_session_screen(
            plan=data.plan,
            timezone=data.timezone,
            tokens_used=data.tokens_used,
            token_limit=data.token_limit,
            usage_percentage=data.usage_percentage,
            tokens_left=data.tokens_left,
            elapsed_session_minutes=data.elapsed_session_minutes,
            total_session_minutes=data.total_session_minutes,
            burn_rate=data.burn_rate,
            session_cost=data.session_cost,
            per_model_stats=data.per_model_stats,
            sent_messages=data.sent_messages,
            entries=data.entries,
            predicted_end_str=data.predicted_end_str,
            reset_time_str=data.reset_time_str,
            current_time_str=data.current_time_str,
            show_switch_notification=data.show_switch_notification,
            show_exceed_notification=data.show_exceed_notification,
            show_tokens_will_run_out=data.show_tokens_will_run_out,
            original_limit=data.original_limit,
        )

    # ── Main formatter ────────────────────────────────────────────────────────

    def format_active_session_screen(
        self,
        plan: str,
        timezone: str,
        tokens_used: int,
        token_limit: int,
        usage_percentage: float,
        tokens_left: int,
        elapsed_session_minutes: float,
        total_session_minutes: float,
        burn_rate: float,
        session_cost: float,
        per_model_stats: dict[str, Any],
        sent_messages: int,
        entries: list[dict],
        predicted_end_str: str,
        reset_time_str: str,
        current_time_str: str,
        show_switch_notification: bool = False,
        show_exceed_notification: bool = False,
        show_tokens_will_run_out: bool = False,
        original_limit: int = 0,
        animation_level: str = "subtle",
        burn_rate_history: "list[float] | None" = None,
        keyword_stats: "list | None" = None,
        **kwargs,
    ) -> list[str]:
        """Format the complete active session screen.

        Automatically adapts sections based on terminal height/width via
        :func:`~claude_monitor.ui.adaptive_layout.get_layout_config`.

        Returns:
            List of Rich-markup strings / Rich renderables for the screen buffer.
        """
        from claude_monitor.ui.adaptive_layout import (
            get_layout_config,
            get_terminal_size,
        )
        from claude_monitor.ui.dashboard import render_dashboard

        kw_available = keyword_stats is not None
        layout = get_layout_config(
            animation_level=animation_level,
            keywords_enabled=kw_available,
        )
        cols, _rows = get_terminal_size()

        # Flatten everything the dashboard renderer needs into one dict.
        d: dict[str, Any] = {
            "plan": plan,
            "timezone": timezone,
            "tokens_used": tokens_used,
            "token_limit": token_limit,
            "usage_percentage": usage_percentage,
            "session_cost": session_cost,
            "cost_limit": kwargs.get("cost_limit_p90"),
            "sent_messages": sent_messages,
            "messages_limit": kwargs.get("messages_limit_p90", 0),
            "elapsed_session_minutes": elapsed_session_minutes,
            "total_session_minutes": total_session_minutes,
            "burn_rate": burn_rate,
            "burn_rate_history": burn_rate_history or [],
            "per_model_stats": per_model_stats,
            "predicted_end_str": predicted_end_str,
            "reset_time_str": reset_time_str,
            "current_time_str": current_time_str,
            "animation_level": animation_level,
            "show_switch_notification": show_switch_notification,
            "show_exceed_notification": show_exceed_notification,
            "show_tokens_will_run_out": show_tokens_will_run_out,
        }

        # Keyword analytics ride inside the card on the FULL tier.
        extra: list[Any] = []
        if keyword_stats is not None and layout.show_keywords:
            from claude_monitor.ui.keyword_panel import KeywordPanel

            extra = list(KeywordPanel().render(keyword_stats))

        card = render_dashboard(d, layout, cols=cols, extra=extra or None)

        screen_buffer: list[Any] = [card]

        # A newer-version notice sits as a quiet centered line beneath the card.
        try:
            from claude_monitor.utils.update_check import UpdateChecker

            notice = UpdateChecker.get().notice
            if notice:
                from rich.align import Align
                from rich.text import Text as _Text

                screen_buffer.append(Align.center(_Text(f"↗ {notice}", style="dim")))
        except Exception:
            pass

        return screen_buffer

    # ── Plan display helper ───────────────────────────────────────────────────

    def _render_plan_display(
        self,
        screen_buffer: list,
        layout: Any,
        plan: str,
        tokens_used: int,
        token_limit: int,
        usage_percentage: float,
        session_cost: float,
        sent_messages: int,
        elapsed_session_minutes: float,
        total_session_minutes: float,
        per_model_stats: dict,
        burn_rate: float,
        burn_rate_history: list,
        animation_level: str,
        cost_limit_p90: Optional[float],
        messages_limit_p90: int,
    ) -> None:
        from claude_monitor.core.plans import DEFAULT_COST_LIMIT
        from claude_monitor.terminal.themes import render_sparkline

        if cost_limit_p90 is None:
            cost_limit_p90 = DEFAULT_COST_LIMIT

        bar_w = layout.bar_width

        if plan == "custom":
            screen_buffer.append("")
            screen_buffer.append("[bold]! Session-Based Dynamic Limits[/bold]")
            screen_buffer.append(
                "[dim]Based on your historical usage patterns when hitting limits (P90)[/dim]"
            )
            screen_buffer.append(f"[separator]{'─' * 60}[/]")
        else:
            screen_buffer.append("")

        # Cost bar
        if layout.show_cost_bar:
            cost_pct = (
                min(100, percentage(session_cost, cost_limit_p90))
                if cost_limit_p90 > 0
                else 0
            )
            cost_bar = self._render_wide_progress_bar(cost_pct, width=bar_w)
            screen_buffer.append(
                f"{_I_COST} [value]Cost:[/]     {cost_bar} "
                f"{cost_pct:4.1f}%    [value]${session_cost:.2f}[/] / "
                f"[dim]${cost_limit_p90:.2f}[/]"
            )
            screen_buffer.append("")

        # Token bar
        if layout.show_token_bar:
            token_bar = self._render_wide_progress_bar(usage_percentage, width=bar_w)
            screen_buffer.append(
                f"{_I_TOKENS} [value]Tokens:[/]   {token_bar} "
                f"{usage_percentage:4.1f}%    [value]{tokens_used:,}[/] / "
                f"[dim]{token_limit:,}[/]"
            )
            screen_buffer.append("")

        # Messages bar
        if layout.show_messages_bar:
            msg_pct = (
                min(100, percentage(sent_messages, messages_limit_p90))
                if messages_limit_p90 > 0
                else 0
            )
            msg_bar = self._render_wide_progress_bar(msg_pct, width=bar_w)
            screen_buffer.append(
                f"{_I_MESSAGES} [value]Messages:[/] {msg_bar} "
                f"{msg_pct:4.1f}%    [value]{sent_messages}[/] / "
                f"[dim]{messages_limit_p90:,}[/]"
            )
            screen_buffer.append(f"[separator]{'─' * 60}[/]")

        # Time bar
        if layout.show_time_bar:
            time_pct = (
                percentage(elapsed_session_minutes, total_session_minutes)
                if total_session_minutes > 0
                else 0
            )
            time_bar = self._render_wide_progress_bar(time_pct, width=bar_w)
            time_remaining = max(0, total_session_minutes - elapsed_session_minutes)
            tlh = int(time_remaining // 60)
            tlm = int(time_remaining % 60)
            screen_buffer.append(
                f"{_I_TIME}  [value]Time to Reset:[/] {time_bar} {tlh}h {tlm}m"
            )
            screen_buffer.append("")

        # Model bar
        if layout.show_model_bar:
            model_bar = self.model_usage.render(per_model_stats or {})
            screen_buffer.append(
                f"{_I_MODEL} [value]Model Distribution:[/] {model_bar}"
            )
            screen_buffer.append(f"[separator]{'─' * 60}[/]")

        # Burn rate + optional sparkline
        if layout.show_burn_rate:
            velocity_emoji = VelocityIndicator.get_velocity_emoji(burn_rate)
            sparkline_str = ""
            if layout.show_sparkline and burn_rate_history:
                spark = render_sparkline(burn_rate_history, width=10)
                sparkline_str = f"  [dim]{spark}[/]"
            screen_buffer.append(
                f"{_I_BURN} [value]Burn Rate:[/]  "
                f"[warning]{burn_rate:.1f}[/] [dim]tokens/min[/] "
                f"{velocity_emoji}{sparkline_str}"
            )
            cost_per_min = (
                session_cost / max(1, elapsed_session_minutes)
                if elapsed_session_minutes > 0
                else 0
            )
            screen_buffer.append(
                f"{_I_COSTRATE} [value]Cost Rate:[/]  "
                f"{CostIndicator.render(cost_per_min)} [dim]$/min[/]"
            )

    # ── Simple fallback display ───────────────────────────────────────────────

    def _render_simple_display(
        self,
        screen_buffer: list,
        layout: Any,
        tokens_used: int,
        token_limit: int,
        usage_percentage: float,
        tokens_left: int,
        session_cost: float,
        sent_messages: int,
        elapsed_session_minutes: float,
        total_session_minutes: float,
        per_model_stats: dict,
        burn_rate: float,
        burn_rate_history: list,
        animation_level: str,
    ) -> None:
        from claude_monitor.terminal.themes import render_sparkline

        bar_w = layout.bar_width
        cost_display = CostIndicator.render(session_cost)
        cost_per_min = (
            session_cost / max(1, elapsed_session_minutes)
            if elapsed_session_minutes > 0
            else 0
        )

        screen_buffer.append(f"{_I_COST} [value]Session Cost:[/]  {cost_display}")
        screen_buffer.append(
            f"{_I_COSTRATE} [value]Cost Rate:[/]    "
            f"{CostIndicator.render(cost_per_min)} [dim]$/min[/]"
        )
        screen_buffer.append("")

        if layout.show_token_bar:
            token_bar = TokenProgressBar(width=bar_w).render(usage_percentage)
            screen_buffer.append(f"{_I_TOKENS} [value]Token Usage:[/]   {token_bar}")
            screen_buffer.append("")

        screen_buffer.append(
            f"{_I_TOKENS} [value]Tokens:[/]       "
            f"[value]{tokens_used:,}[/] / [dim]~{token_limit:,}[/] "
            f"([info]{tokens_left:,} left[/])"
        )

        velocity_emoji = VelocityIndicator.get_velocity_emoji(burn_rate)
        sparkline_str = ""
        if layout.show_sparkline and burn_rate_history:
            spark = render_sparkline(burn_rate_history, width=10)
            sparkline_str = f"  [dim]{spark}[/]"
        screen_buffer.append(
            f"{_I_BURN} [value]Burn Rate:[/]    "
            f"[warning]{burn_rate:.1f}[/] [dim]tokens/min[/] "
            f"{velocity_emoji}{sparkline_str}"
        )
        screen_buffer.append(
            f"{_I_MESSAGES} [value]Sent Messages:[/] "
            f"[info]{sent_messages}[/] [dim]messages[/]"
        )

        if per_model_stats and layout.show_model_bar:
            model_bar = self.model_usage.render(per_model_stats)
            screen_buffer.append(f"{_I_MODEL} [value]Model Usage:[/]   {model_bar}")

        screen_buffer.append("")

        if layout.show_time_bar:
            time_bar = self.time_progress.render(
                elapsed_session_minutes, total_session_minutes
            )
            screen_buffer.append(f"{_I_TIME}  [value]Time to Reset:[/]  {time_bar}")
            screen_buffer.append("")

    # ── Notifications ─────────────────────────────────────────────────────────

    def _add_notifications(
        self,
        screen_buffer: list,
        show_switch_notification: bool,
        show_exceed_notification: bool,
        show_tokens_will_run_out: bool,
        original_limit: int,
        token_limit: int,
    ) -> None:
        added = False
        if show_switch_notification and token_limit > original_limit:
            screen_buffer.append(
                f"! [warning]Token limit exceeded ({token_limit:,} tokens)[/]"
            )
            added = True
        if show_exceed_notification:
            screen_buffer.append(
                "! [error]You have exceeded the maximum cost limit![/]"
            )
            added = True
        if show_tokens_will_run_out:
            screen_buffer.append(
                "! [warning]Cost limit will be exceeded before reset![/]"
            )
            added = True
        if added:
            screen_buffer.append("")

    # ── No-session screen ─────────────────────────────────────────────────────

    def format_no_active_session_screen(
        self,
        plan: str,
        timezone: str,
        token_limit: int,
        current_time: Optional[datetime] = None,
        args: Optional[Any] = None,
    ) -> list[str]:
        """Format screen shown when there is no active Claude session."""
        from rich.align import Align
        from rich.box import ROUNDED
        from rich.console import Group
        from rich.panel import Panel
        from rich.text import Text

        from claude_monitor.terminal.themes import AnimationState
        from claude_monitor.ui.adaptive_layout import get_terminal_size
        from claude_monitor.ui.dashboard import _PLAN_LABEL, _PLAN_STYLE, card_width

        animation_level = getattr(args, "animation", "subtle") if args else "subtle"
        plan_style = _PLAN_STYLE.get(plan.lower(), "header")
        plan_label = _PLAN_LABEL.get(plan.lower(), plan.upper())

        # Current time string (best effort)
        current_time_str = "--:--:--"
        if current_time and args:
            try:
                display_tz = pytz.timezone(args.timezone)
                current_time_str = format_display_time(
                    current_time.astimezone(display_tz),
                    get_time_format_preference(args),
                    include_seconds=True,
                )
            except (pytz.exceptions.UnknownTimeZoneError, AttributeError):
                pass

        dot = AnimationState.live_dot(animation_level)

        title = Text()
        title.append(f"{_IC['header']} ", style=plan_style)
        title.append("CLAUDE MONITOR", style="bold value")
        title.append("   ")
        title.append(plan_label, style=f"bold {plan_style}")

        body = Group(
            Text(f"{dot} Waiting for an active Claude session…", style="success"),
            Text(),
            Text.from_markup(
                f"[dim]Send a message in Claude Code to begin tracking. "
                f"Plan limit: [/][value]{token_limit:,}[/][dim] tokens.[/]"
            ),
        )

        cols, _rows = get_terminal_size()
        footer = Text()
        footer.append(current_time_str, style="dim")
        footer.append("   ")
        footer.append("m", style="value")
        footer.append(" menu", style="dim")
        footer.append("  ")
        footer.append("^C", style="value")
        footer.append(" quit", style="dim")

        panel = Panel(
            body,
            box=ROUNDED,
            border_style=plan_style,
            title=title,
            title_align="left",
            subtitle=footer,
            subtitle_align="left",
            padding=(1, 3),
            width=card_width(cols),
        )
        return [Align.center(panel)]
