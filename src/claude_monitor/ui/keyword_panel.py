"""Keyword analytics panel for Claude Monitor.

Returns a list of Rich renderables (Rule + Table + Rule) instead of a Panel
so it works correctly inside a Live display on all terminals, including old
Windows PowerShell.
"""

from __future__ import annotations

from typing import Any, List

from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from claude_monitor.data.keyword_analyzer import KeywordStats, _KEYWORDS_FILE
from claude_monitor.terminal.themes import get_cost_style


class KeywordPanel:
    """Renders the keyword analytics section as a list of Rich renderables."""

    SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"

    def render(self, stats: List[KeywordStats]) -> List[Any]:
        """Build the keyword analytics section renderables.

        Returns a list that can be directly :meth:`list.extend`-ed into the
        screen buffer — no outer Panel wrapper, so it renders correctly in
        a Rich ``Live`` display on Windows PowerShell.

        Args:
            stats: Pre-sorted :class:`KeywordStats` list (highest cost first).

        Returns:
            ``[top_rule, table, bottom_rule, ""]``
        """
        from claude_monitor.terminal.icons import ICONS as _IC
        _kw = _IC["keyword"]
        title = Text(f"{_kw}  KEYWORD ANALYTICS  {_kw}", style="bold info")
        top_rule  = Rule(title=title, style="info")
        bot_rule  = Rule(style="separator")

        table = Table(
            box=None,
            show_header=True,
            show_edge=False,
            padding=(0, 1),
            expand=False,
        )

        table.add_column("Keyword",  style="info",  no_wrap=True, min_width=12)
        table.add_column("Convos",   justify="right", style="value",  min_width=6)
        table.add_column("Mentions", justify="right", style="dim",    min_width=8)
        table.add_column("Tokens",   justify="right", style="value",  min_width=10)
        table.add_column("Cost",     justify="right",                  min_width=10)
        table.add_column("% Cost",   justify="right", style="dim",    min_width=7)
        table.add_column("Bar",      no_wrap=True,                    min_width=12)

        if not stats:
            # Show a helpful setup hint instead of a blank table
            hint = (
                f"[dim]No keyword matches yet.  "
                f"Add keywords to [bold]{_KEYWORDS_FILE}[/bold][/dim]"
            )
            table.add_row(hint, "", "", "", "", "", "")
        else:
            for stat in stats:
                cost_style = get_cost_style(stat.cost)
                cost_text  = Text(f"${stat.cost:.4f}", style=cost_style)
                bar        = self._mini_bar(stat.pct_of_total_cost)

                table.add_row(
                    f"[bold]#{stat.keyword}[/bold]",
                    str(stat.conversation_count),
                    str(stat.mention_count),
                    f"{stat.tokens:,}",
                    cost_text,
                    f"{stat.pct_of_total_cost:.1f}%",
                    bar,
                )

        return [top_rule, table, bot_rule, ""]

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _mini_bar(pct: float, width: int = 12) -> str:
        """Render a small inline bar for the keyword table."""
        capped = min(pct, 100.0)
        filled = int(width * capped / 100.0) if capped > 0 else 0
        empty  = width - filled

        if pct >= 50:
            style = "cost.high"
        elif pct >= 20:
            style = "cost.medium"
        else:
            style = "cost.low"

        return (
            f"[{style}]{'█' * filled}[/]"
            f"[table.border]{'░' * empty}[/]"
        )
