"""Keyword analytics panel for Claude Monitor.

Renders a Rich Panel+Table showing per-keyword usage stats
(conversations, mentions, tokens, cost, % of total).
"""

from __future__ import annotations

from typing import List

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from claude_monitor.data.keyword_analyzer import KeywordStats
from claude_monitor.terminal.themes import get_cost_style


class KeywordPanel:
    """Renders the keyword analytics panel as a Rich renderable."""

    SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"

    def render(self, stats: List[KeywordStats]) -> Panel:
        """Build the keyword panel renderable.

        Args:
            stats: List of KeywordStats objects (already sorted by cost desc).

        Returns:
            A Rich Panel containing a Table.
        """
        table = Table(
            box=None,
            show_header=True,
            show_edge=False,
            padding=(0, 1),
            expand=False,
        )

        table.add_column("Keyword", style="info", no_wrap=True, min_width=12)
        table.add_column("Convos", justify="right", style="value", min_width=6)
        table.add_column("Mentions", justify="right", style="dim", min_width=8)
        table.add_column("Tokens", justify="right", style="value", min_width=10)
        table.add_column("Cost", justify="right", min_width=10)
        table.add_column("% Cost", justify="right", style="dim", min_width=7)
        table.add_column("Bar", no_wrap=True, min_width=12)

        if not stats:
            table.add_row(
                "[dim]No keyword matches yet.[/]",
                "", "", "", "", "", "",
            )
        else:
            max_cost = stats[0].cost if stats else 1.0

            for stat in stats:
                cost_style = get_cost_style(stat.cost)
                cost_text = Text(f"${stat.cost:.4f}", style=cost_style)

                bar = self._mini_bar(stat.pct_of_total_cost, max_cost_pct=100.0)

                table.add_row(
                    f"[bold]#{stat.keyword}[/bold]",
                    str(stat.conversation_count),
                    str(stat.mention_count),
                    f"{stat.tokens:,}",
                    cost_text,
                    f"{stat.pct_of_total_cost:.1f}%",
                    bar,
                )

        return Panel(
            table,
            title="[bold info]🔍 Keyword Analytics[/bold info]",
            border_style="info",
            padding=(0, 1),
        )

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _mini_bar(pct: float, max_cost_pct: float = 100.0, width: int = 12) -> str:
        """Render a small inline progress bar for the keyword table."""
        capped = min(pct, max_cost_pct)
        filled = int(width * capped / max_cost_pct) if max_cost_pct > 0 else 0
        empty = width - filled

        if pct >= 50:
            style = "cost.high"
        elif pct >= 20:
            style = "cost.medium"
        else:
            style = "cost.low"

        filled_str = f"[{style}]{'█' * filled}[/]"
        empty_str = f"[table.border]{'░' * empty}[/]"
        return filled_str + empty_str
