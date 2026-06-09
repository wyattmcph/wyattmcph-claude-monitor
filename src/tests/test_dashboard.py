"""Tests for the centered dashboard card renderer."""

import os

os.environ.setdefault("CLAUDE_MONITOR_FORCE_UNICODE", "1")


from claude_monitor.terminal.themes import get_themed_console
from claude_monitor.ui import dashboard as dash
from claude_monitor.ui.adaptive_layout import LayoutConfig, LayoutTier


def _layout(**kw) -> LayoutConfig:
    base = dict(tier=LayoutTier.FULL, bar_width=26, show_sparkline=True)
    base.update(kw)
    return LayoutConfig(**base)


def _data(**over):
    d = {
        "plan": "pro",
        "timezone": "UTC",
        "tokens_used": 100000,
        "token_limit": 200000,
        "usage_percentage": 50.0,
        "session_cost": 6.2,
        "cost_limit": 20.0,
        "sent_messages": 42,
        "messages_limit": 300,
        "elapsed_session_minutes": 150,
        "total_session_minutes": 300,
        "burn_rate": 120.0,
        "burn_rate_history": [10, 50, 120],
        "per_model_stats": {
            "claude-sonnet-4": {"input_tokens": 60000, "output_tokens": 20000},
            "claude-opus-4": {"input_tokens": 15000, "output_tokens": 5000},
        },
        "predicted_end_str": "1:05 PM",
        "reset_time_str": "2:30 PM",
        "current_time_str": "12:51 PM",
        "animation_level": "moderate",
    }
    d.update(over)
    return d


def _render(renderable, cols=100) -> str:
    console = get_themed_console("dark")
    console.width = cols
    with console.capture() as cap:
        console.print(renderable)
    return cap.get()


def test_compact_formats_thousands_and_millions():
    assert dash._compact(200000) == "200K"
    assert dash._compact(4000000) == "4M"
    assert dash._compact(1500000) == "1.5M"
    assert dash._compact(500) == "500"


def test_severity_thresholds():
    assert dash._severity(10) == "cost.low"
    assert dash._severity(70) == "cost.medium"
    assert dash._severity(95) == "cost.high"


def test_bar_is_full_at_100_and_empty_at_0():
    full = dash._bar(100.0, 10)
    empty = dash._bar(0.0, 10)
    assert "█" * 10 in full
    assert "█" not in empty


def test_bar_width_scales_with_columns():
    assert dash._bar_width_for(120) >= dash._bar_width_for(80)
    assert dash._bar_width_for(70) <= dash._bar_width_for(100)


def test_card_width_is_clamped():
    assert dash.card_width(40) == dash._MIN_CARD_WIDTH
    assert dash.card_width(500) == dash._MAX_CARD_WIDTH


def test_model_summary_includes_both_models():
    text = dash._model_summary(
        {
            "claude-sonnet-4": {"input_tokens": 80, "output_tokens": 0},
            "claude-opus-4": {"input_tokens": 20, "output_tokens": 0},
        }
    )
    plain = text.plain
    assert "Sonnet" in plain and "Opus" in plain


def test_model_summary_handles_empty():
    assert dash._model_summary(None).plain == "—"
    assert dash._model_summary({}).plain == "—"


def test_render_dashboard_contains_key_metrics():
    out = _render(dash.render_dashboard(_data(), _layout(), cols=100))
    assert "CLAUDE MONITOR" in out
    assert "PRO" in out
    assert "Tokens" in out
    assert "100,000" in out
    assert "Reset at" in out


def test_render_dashboard_respects_layout_hiding_rows():
    layout = _layout(show_messages_bar=False, show_cost_bar=False)
    out = _render(dash.render_dashboard(_data(), layout, cols=100))
    assert "Messages" not in out
    assert "Tokens" in out  # token row always present


def test_render_dashboard_shows_notifications():
    out = _render(
        dash.render_dashboard(_data(show_exceed_notification=True), _layout(), cols=100)
    )
    assert "Cost limit exceeded" in out


def test_info_card_wraps_body():
    from rich.text import Text

    out = _render(dash.info_card("max5", Text("hello world")))
    assert "hello world" in out
    assert "MAX 5" in out
