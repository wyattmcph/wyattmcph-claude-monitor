"""CSV exporter for Claude Monitor session data.

Exports session blocks and usage data to CSV files for external analysis.
"""

import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from claude_monitor.core.models import SessionBlock

logger = logging.getLogger(__name__)


def export_sessions_to_csv(
    blocks: List[SessionBlock],
    output_path: Optional[str] = None,
) -> Path:
    """Export session blocks to a CSV file.

    Args:
        blocks: List of SessionBlock objects to export
        output_path: Path to write CSV file. If None, writes to ~/Downloads/claude-monitor-export.csv

    Returns:
        Path to the created CSV file

    Raises:
        ValueError: If blocks list is empty
        IOError: If file cannot be written
    """
    if not blocks:
        raise ValueError("Cannot export empty blocks list")

    if output_path is None:
        output_path = Path.home() / "Downloads" / "claude-monitor-export.csv"
    else:
        output_path = Path(output_path)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            # Write header row
            writer.writerow([
                "Session ID",
                "Start Time (UTC)",
                "End Time (UTC)",
                "Input Tokens",
                "Output Tokens",
                "Cache Creation Tokens",
                "Cache Read Tokens",
                "Total Tokens",
                "Cost (USD)",
                "Models Used",
                "Message Count",
                "Duration (minutes)",
                "Is Active",
                "Is Gap",
                "Burn Rate (tokens/min)",
                "Cost Per Hour (USD)",
            ])

            # Write data rows
            for block in blocks:
                models = ", ".join(block.models) if block.models else "—"
                burn_rate_tpm = (
                    block.burn_rate.tokens_per_minute
                    if block.burn_rate
                    else 0
                )
                burn_rate_cph = (
                    block.burn_rate.cost_per_hour
                    if block.burn_rate
                    else 0
                )

                writer.writerow([
                    block.id,
                    block.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    block.end_time.strftime("%Y-%m-%d %H:%M:%S"),
                    block.token_counts.input_tokens,
                    block.token_counts.output_tokens,
                    block.token_counts.cache_creation_tokens,
                    block.token_counts.cache_read_tokens,
                    block.token_counts.total_tokens,
                    f"{block.cost_usd:.4f}",
                    models,
                    block.sent_messages_count,
                    f"{block.duration_minutes:.1f}",
                    "Yes" if block.is_active else "No",
                    "Yes" if block.is_gap else "No",
                    f"{burn_rate_tpm:.2f}",
                    f"{burn_rate_cph:.4f}",
                ])

        logger.info(f"Exported {len(blocks)} sessions to {output_path}")
        return output_path

    except IOError as e:
        logger.error(f"Failed to write CSV file: {e}")
        raise


def export_summary_to_csv(
    blocks: List[SessionBlock],
    output_path: Optional[str] = None,
) -> Path:
    """Export summary statistics to CSV (one row per model).

    Args:
        blocks: List of SessionBlock objects to analyze
        output_path: Path to write CSV file. If None, writes to ~/Downloads/claude-monitor-summary.csv

    Returns:
        Path to the created CSV file
    """
    if not blocks:
        raise ValueError("Cannot export empty blocks list")

    if output_path is None:
        output_path = Path.home() / "Downloads" / "claude-monitor-summary.csv"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Aggregate data by model
    model_stats = {}
    total_tokens = 0
    total_cost = 0.0

    for block in blocks:
        if not block.is_gap:
            total_tokens += block.token_counts.total_tokens
            total_cost += block.cost_usd

            for model in block.models:
                if model not in model_stats:
                    model_stats[model] = {
                        "token_count": 0,
                        "cost": 0.0,
                        "session_count": 0,
                    }
                if model in block.per_model_stats:
                    stats = block.per_model_stats[model]
                    model_stats[model]["token_count"] += stats.get(
                        "tokens", 0
                    )
                    model_stats[model]["cost"] += stats.get("cost", 0.0)
                model_stats[model]["session_count"] += 1

    try:
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            writer.writerow([
                "Model",
                "Total Tokens",
                "Total Cost (USD)",
                "Sessions Used",
                "% of Total Tokens",
                "% of Total Cost",
            ])

            # Sort by total cost descending
            sorted_models = sorted(
                model_stats.items(),
                key=lambda x: x[1]["cost"],
                reverse=True,
            )

            for model, stats in sorted_models:
                token_pct = (
                    (stats["token_count"] / total_tokens * 100)
                    if total_tokens > 0
                    else 0
                )
                cost_pct = (
                    (stats["cost"] / total_cost * 100)
                    if total_cost > 0
                    else 0
                )

                writer.writerow([
                    model,
                    stats["token_count"],
                    f"{stats['cost']:.4f}",
                    stats["session_count"],
                    f"{token_pct:.1f}%",
                    f"{cost_pct:.1f}%",
                ])

            # Add total row
            writer.writerow([])
            writer.writerow([
                "TOTAL",
                total_tokens,
                f"{total_cost:.4f}",
                len([b for b in blocks if not b.is_gap]),
                "100.0%",
                "100.0%",
            ])

        logger.info(f"Exported summary to {output_path}")
        return output_path

    except IOError as e:
        logger.error(f"Failed to write summary CSV: {e}")
        raise
