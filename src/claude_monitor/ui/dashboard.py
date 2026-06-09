"""Centered dashboard card renderer for Claude Monitor.

This is the visual heart of the monitor. Instead of stacking left-aligned
text lines (which always looked "buried in the top-left" and never aligned),
it composes a single rounded, plan-coloured :class:`~rich.panel.Panel` built
from an aligned :class:`~rich.table.Table` grid, then centers it in the
terminal. The card scales gracefully: it grows with the window up to a
comfortable reading width and stays centered at any size.

The public entry point is :func:`render_dashboard`, which returns a Rich
renderable ready to drop straight into the Live display.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from rich.align import Align
from rich.box import ROUNDED
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from claude_monitor.terminal.icons import ICONS as _IC

# ── Layout constants ──────────────────────────────────────────────────────────
_MIN_CARD_WIDTH = 58
_MAX_CARD_WIDTH = 80
_BAR_WIDTH = 26

_PLAN_STYLE: Dict[str, str] = {
    "pro": "plan.pro",
    "max5": "plan.max5",
    "max20": "plan.max20",
    "custom": "plan.custom",
}

_PLAN_LABEL: Dict[str, str] = {
    "pro": "PRO",
    "max5": "MAX 5",
    "max20": "MAX 20",
    "custom": "CUSTOM",
}


# ── Small formatting helpers ──────────────────────────────────────────────────


def _compact(n: float) -> str:
    """Format a token count compactly: 200000 → '200K', 4000000 → '4.0M'."""
    n = float(n)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return f"{n:.0f}"


def _severity(pct: float) -> str:
    """Map a usage percentage to a theme colour key."""
    if pct >= 85:
        return "cost.high"
    if pct >= 60:
        return "cost.medium"
    return "cost.low"


def _bar_width_for(cols: int) -> int:
    """Pick a bar width that fits comfortably for the terminal width."""
    if cols >= 96:
        return 26
    if cols >= 82:
        return 22
    return 16


def _bar(pct: float, width: int = _BAR_WIDTH) -> str:
    """Render a clean single-colour progress bar as Rich markup.

    The whole filled region takes the severity colour for the current value
    (calm green → warm amber → coral) and the remainder is a dim track.
    """
    pct = max(0.0, pct)
    filled = int(round(width * min(pct, 100.0) / 100.0))
    filled = max(0, min(width, filled))
    empty = width - filled
    color = _severity(pct)
    return f"[{color}]{'█' * filled}[/][progress.bar.empty]{'━' * empty}[/]"


def _model_summary(per_model_stats: Optional[Dict[str, Any]]) -> Text:
    """Build a coloured 'Sonnet 80% · Opus 20%' summary from model stats."""
    text = Text()
    if not per_model_stats:
        text.append("—", style="dim")
        return text

    sonnet = opus = other = 0
    for name, stats in per_model_stats.items():
        if not isinstance(stats, dict):
            continue
        toks = stats.get("input_tokens", 0) + stats.get("output_tokens", 0)
        low = name.lower()
        if "sonnet" in low:
            sonnet += toks
        elif "opus" in low:
            opus += toks
        else:
            other += toks

    total = sonnet + opus + other
    if total <= 0:
        text.append("—", style="dim")
        return text

    parts: List[tuple[str, int, str]] = [
        ("Sonnet", sonnet, "model.sonnet"),
        ("Opus", opus, "model.opus"),
        ("Other", other, "model.unknown"),
    ]
    first = True
    for label, toks, style in parts:
        if toks <= 0:
            continue
        if not first:
            text.append("  ·  ", style="dim")
        text.append(f"{label} ", style=style)
        text.append(f"{toks / total * 100:.0f}%", style="dim")
        first = False
    return text


# ── Metric grid ───────────────────────────────────────────────────────────────


def _metric_row(
    grid: Table,
    icon: str,
    label: str,
    pct: float,
    detail: str,
    bar_w: int,
    *,
    show_pct: bool = True,
) -> None:
    """Add one aligned metric row to the grid."""
    pct_cell = f"[{_severity(pct)}]{pct:>4.0f}%[/]" if show_pct else ""
    grid.add_row(
        f"[value]{icon} {label}[/]",
        _bar(pct, bar_w),
        pct_cell,
        detail,
    )


def _build_metric_grid(d: Dict[str, Any], layout: Any, bar_w: int) -> Table:
    """Assemble the aligned metric grid (tokens / cost / messages / time)."""
    grid = Table.grid(padding=(0, 2), expand=False)
    grid.add_column(justify="left", no_wrap=True)  # label
    grid.add_column(justify="left", no_wrap=True)  # bar
    grid.add_column(justify="right", no_wrap=True)  # percentage
    grid.add_column(justify="left", no_wrap=True)  # detail

    tokens_used = d["tokens_used"]
    token_limit = d["token_limit"]
    usage_pct = d["usage_percentage"]

    def show(k: str, default: bool = True) -> bool:
        return getattr(layout, k, default)

    if show("show_token_bar"):
        _metric_row(
            grid,
            _IC["tokens"],
            "Tokens",
            usage_pct,
            f"[value]{tokens_used:,}[/] [dim]/ {_compact(token_limit)}[/]",
            bar_w,
        )

    if show("show_cost_bar"):
        cost = d["session_cost"]
        cost_limit = d.get("cost_limit") or 0.0
        cost_pct = (cost / cost_limit * 100) if cost_limit > 0 else 0.0
        _metric_row(
            grid,
            _IC["cost"],
            "Cost",
            cost_pct,
            f"[value]${cost:,.2f}[/] [dim]/ ${cost_limit:,.0f}[/]",
            bar_w,
        )

    if show("show_messages_bar"):
        msgs = d["sent_messages"]
        msg_limit = d.get("messages_limit") or 0
        msg_pct = (msgs / msg_limit * 100) if msg_limit > 0 else 0.0
        _metric_row(
            grid,
            _IC["messages"],
            "Messages",
            msg_pct,
            f"[value]{msgs:,}[/] [dim]/ {_compact(msg_limit)}[/]",
            bar_w,
        )

    if show("show_time_bar"):
        elapsed = d["elapsed_session_minutes"]
        total = d["total_session_minutes"]
        time_pct = (elapsed / total * 100) if total > 0 else 0.0
        remaining = max(0, total - elapsed)
        h, m = int(remaining // 60), int(remaining % 60)
        _metric_row(
            grid,
            _IC["time"],
            "Session",
            time_pct,
            f"[value]{h}h {m:02d}m[/] [dim]left[/]",
            bar_w,
        )

    return grid


def _build_stats_line(d: Dict[str, Any], layout: Any) -> Optional[Text]:
    """Burn rate + sparkline on the left, model split on the right."""
    if not getattr(layout, "show_burn_rate", True):
        return None

    from claude_monitor.terminal.themes import render_sparkline

    burn = d.get("burn_rate", 0.0)
    line = Text()
    line.append(f"{_IC['burn']} ", style="warning")
    line.append("Burn ", style="value")
    line.append(f"{burn:,.0f}", style="warning")
    line.append(" tok/min", style="dim")

    history = d.get("burn_rate_history") or []
    if getattr(layout, "show_sparkline", False) and history:
        line.append("  ")
        line.append(render_sparkline(history, width=10), style="chart.line")

    line.append("    ")
    line.append(f"{_IC['model']} ", style="value")
    line.append_text(_model_summary(d.get("per_model_stats")))
    return line


def _build_predictions(d: Dict[str, Any]) -> Optional[Text]:
    """Resets-at and runs-out predictions on one tidy line."""
    reset = d.get("reset_time_str")
    runout = d.get("predicted_end_str")
    if not reset and not runout:
        return None

    line = Text()
    line.append(f"{_IC['predict']} ", style="success")
    line.append("Reset at ", style="info")
    line.append(str(reset), style="success")
    if runout:
        line.append("     ")
        line.append("Runs out ", style="info")
        line.append(str(runout), style="warning")
    return line


def _build_notifications(d: Dict[str, Any]) -> List[Text]:
    """Build any active warning lines."""
    lines: List[Text] = []
    if d.get("show_exceed_notification"):
        lines.append(Text(f"{_IC['warning']} Cost limit exceeded", style="error"))
    if d.get("show_tokens_will_run_out"):
        lines.append(
            Text(f"{_IC['warning']} Tokens will run out before reset", style="warning")
        )
    if d.get("show_switch_notification"):
        lines.append(
            Text(f"{_IC['warning']} Token limit auto-expanded", style="warning")
        )
    return lines


# ── Title / footer ────────────────────────────────────────────────────────────


def _build_title(plan: str, animation_level: str) -> Text:
    """Brand on the left, plan badge + live dot on the right of the title."""
    from claude_monitor.terminal.themes import AnimationState

    plan_style = _PLAN_STYLE.get(plan.lower(), "header")
    plan_label = _PLAN_LABEL.get(plan.lower(), plan.upper())
    dot = AnimationState.live_dot(animation_level)

    title = Text()
    title.append(f"{_IC['header']} ", style=plan_style)
    title.append("CLAUDE MONITOR", style="bold value")
    title.append("   ")
    title.append(plan_label, style=f"bold {plan_style}")
    title.append("  ")
    title.append(dot, style="success")
    title.append(" live", style="dim")
    return title


def _build_footer(current_time_str: str) -> Text:
    """Clock + key hints as the panel subtitle."""
    footer = Text()
    footer.append(str(current_time_str), style="dim")
    footer.append("   ")
    footer.append("m", style="value")
    footer.append(" menu", style="dim")
    footer.append("  ")
    footer.append("k", style="value")
    footer.append(" keywords", style="dim")
    footer.append("  ")
    footer.append("a", style="value")
    footer.append(" anim", style="dim")
    footer.append("  ")
    footer.append("^C", style="value")
    footer.append(" quit", style="dim")
    return footer


# ── Public entry point ────────────────────────────────────────────────────────


def card_width(cols: int) -> int:
    """Pick a comfortable, clamped card width for the given terminal width."""
    return max(_MIN_CARD_WIDTH, min(cols - 4, _MAX_CARD_WIDTH))


def info_card(
    plan: str,
    body: RenderableType,
    *,
    footer: Optional[RenderableType] = None,
) -> RenderableType:
    """Wrap arbitrary content in the standard centered, plan-coloured card.

    Used by the loading, idle and error screens so every state of the monitor
    shares one consistent visual frame.
    """
    from claude_monitor.ui.adaptive_layout import get_terminal_size

    plan_style = _PLAN_STYLE.get(plan.lower(), "header")
    plan_label = _PLAN_LABEL.get(plan.lower(), plan.upper())

    title = Text()
    title.append(f"{_IC['header']} ", style=plan_style)
    title.append("CLAUDE MONITOR", style="bold value")
    title.append("   ")
    title.append(plan_label, style=f"bold {plan_style}")

    cols, _rows = get_terminal_size()
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
    return Align.center(panel)


def render_dashboard(
    d: Dict[str, Any],
    layout: Any,
    *,
    cols: int,
    extra: Optional[List[RenderableType]] = None,
) -> RenderableType:
    """Render the full centered dashboard card.

    Args:
        d: Flat dict of the processed session metrics (see session_display).
        layout: The active :class:`LayoutConfig` (controls which rows show).
        cols: Current terminal width in columns.
        extra: Optional renderables to append inside the card (e.g. keywords).

    Returns:
        A centered Rich renderable ready for ``Live.update``.
    """
    plan = d.get("plan", "pro")
    animation_level = d.get("animation_level", "subtle")
    plan_style = _PLAN_STYLE.get(plan.lower(), "header")
    bar_w = _bar_width_for(cols)

    body: List[RenderableType] = [_build_metric_grid(d, layout, bar_w)]

    stats = _build_stats_line(d, layout)
    if stats is not None:
        body.append(Text())
        body.append(stats)

    if getattr(layout, "show_predictions", True):
        preds = _build_predictions(d)
        if preds is not None:
            body.append(Text())
            body.append(preds)

    if getattr(layout, "show_notifications", True):
        notes = _build_notifications(d)
        if notes:
            body.append(Text())
            body.extend(notes)

    if extra:
        body.append(Text())
        body.extend(extra)

    panel = Panel(
        Group(*body),
        box=ROUNDED,
        border_style=plan_style,
        title=_build_title(plan, animation_level),
        title_align="left",
        subtitle=_build_footer(d.get("current_time_str", "")),
        subtitle_align="left",
        padding=(1, 3),
        width=card_width(cols),
    )
    return Align.center(panel)


__all__ = ["render_dashboard", "card_width"]
