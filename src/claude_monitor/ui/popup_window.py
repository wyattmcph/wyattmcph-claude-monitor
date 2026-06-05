"""Floating PiP-style monitor popup window.

Launch with:  ``claude-monitor --popup``

Creates an always-on-top frameless window that shows live Claude usage
stats.  Requires tkinter (bundled with Python on Windows and macOS;
``sudo apt install python3-tk`` on most Linux distros).

Controls (header buttons):
  ✕  Close
  ⊞  Cycle display tier: compact → full → nano → compact …
  📌 Toggle always-on-top (pin / unpin)

Drag:    Click-and-drag the header bar to reposition the window.
Resize:  Drag the ⊿ grip in the bottom-right corner.
"""

from __future__ import annotations

import logging
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Dark palette ──────────────────────────────────────────────────────────────
_BG       = "#0d1117"
_BG_HDR   = "#161b22"
_FG       = "#e6edf3"
_FG_DIM   = "#8b949e"
_FG_VAL   = "#cdd9e5"
_FG_GOOD  = "#56d364"   # green  / low usage
_FG_WARN  = "#e3b341"   # orange / medium
_FG_CRIT  = "#f85149"   # red    / high
_FG_INFO  = "#79c0ff"   # blue
_FG_ACC   = "#7c8cf8"   # purple accent (header)


def _pct_tag(pct: float) -> str:
    """Return a text-tag name for a usage percentage."""
    if pct < 50:
        return "good"
    if pct < 80:
        return "warn"
    return "crit"


def _mini_bar(pct: float, width: int = 14) -> tuple[str, str]:
    """Return ``(filled, empty)`` block strings for a compact bar."""
    filled = int(width * min(pct, 100.0) / 100.0)
    return "█" * filled, "░" * (width - filled)


# Each tier: (name, default_w, default_h)
_TIERS: List[tuple[str, int, int]] = [
    ("nano",    280, 115),
    ("compact", 325, 200),
    ("full",    370, 295),
]


class MonitorPopup:
    """Floating always-on-top window showing live Claude usage."""

    def __init__(self, args: Any, data_path: str) -> None:
        self.args      = args
        self.data_path = data_path

        self._tier_idx: int = 1          # start at 'compact'
        self._pinned:   bool = True
        self._running:  bool = True

        self._latest_data: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()

        # Drag state
        self._dx = self._dy = 0
        # Resize state
        self._rx0 = self._ry0 = self._rw0 = self._rh0 = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Build window and enter the tkinter event loop (blocks)."""
        self._build_window()
        self._start_data_thread()
        self._schedule_refresh()
        self.root.mainloop()

    # ── Window construction ───────────────────────────────────────────────────

    def _build_window(self) -> None:
        self.root = tk.Tk()
        self.root.title("Claude Monitor")
        self.root.configure(bg=_BG)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.94)
        self.root.overrideredirect(True)   # frameless

        _, w, h = _TIERS[self._tier_idx]
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        # Default position: bottom-right corner
        self.root.geometry(f"{w}x{h}+{sw - w - 24}+{sh - h - 60}")
        self.root.minsize(240, 100)
        self.root.resizable(True, True)

        # ── Header strip ──────────────────────────────────────────────────────
        hbar = tk.Frame(self.root, bg=_BG_HDR, height=26)
        hbar.pack(fill="x", side="top")
        hbar.pack_propagate(False)

        title_lbl = tk.Label(
            hbar, text="✦ CLAUDE MONITOR",
            bg=_BG_HDR, fg=_FG_ACC,
            font=("Consolas", 9, "bold"), anchor="w", padx=8,
        )
        title_lbl.pack(side="left", fill="y")

        # Close
        self._make_btn(hbar, "✕", _FG_CRIT, self._close)
        # Tier cycle
        self._make_btn(hbar, "⊞", _FG_INFO,  self._cycle_tier)
        # Pin / always-on-top
        self._pin_btn = self._make_btn(hbar, "📌", _FG_GOOD, self._toggle_pin)

        # Drag support on header
        for w2 in (hbar, title_lbl):
            w2.bind("<ButtonPress-1>", self._drag_start)
            w2.bind("<B1-Motion>",     self._drag_move)

        # ── Content area ──────────────────────────────────────────────────────
        cf = tk.Frame(self.root, bg=_BG, padx=6, pady=4)
        cf.pack(fill="both", expand=True)

        self._font      = tkfont.Font(family="Consolas", size=9)
        self._font_bold = tkfont.Font(family="Consolas", size=9, weight="bold")

        self.text = tk.Text(
            cf, bg=_BG, fg=_FG, font=self._font,
            bd=0, relief="flat", state="disabled",
            wrap="none", cursor="arrow",
            selectbackground=_BG_HDR,
        )
        self.text.pack(fill="both", expand=True)

        # Colour tags for the text widget
        _tags: Dict[str, tuple[str, bool]] = {
            "val":  (_FG_VAL,   False),
            "good": (_FG_GOOD,  False),
            "warn": (_FG_WARN,  False),
            "crit": (_FG_CRIT,  False),
            "info": (_FG_INFO,  False),
            "dim":  (_FG_DIM,   False),
            "acc":  (_FG_ACC,   True),
        }
        for tag, (color, bold) in _tags.items():
            self.text.tag_configure(
                tag,
                foreground=color,
                font=self._font_bold if bold else self._font,
            )

        # ── Resize grip ───────────────────────────────────────────────────────
        grip = tk.Label(
            self.root, text="⊿", bg=_BG, fg=_FG_DIM,
            font=("Consolas", 9), cursor="size_nw_se",
        )
        grip.place(relx=1.0, rely=1.0, anchor="se")
        grip.bind("<ButtonPress-1>", self._resize_start)
        grip.bind("<B1-Motion>",     self._resize_move)

        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _make_btn(
        self, parent: tk.Frame, text: str, fg: str, cmd: Any
    ) -> tk.Label:
        btn = tk.Label(
            parent, text=text, bg=_BG_HDR, fg=fg,
            font=("Consolas", 11), cursor="hand2", padx=5,
        )
        btn.pack(side="right")
        btn.bind("<Button-1>", lambda _: cmd())
        return btn

    # ── Background data thread ────────────────────────────────────────────────

    def _start_data_thread(self) -> None:
        t = threading.Thread(target=self._data_loop, daemon=True)
        t.start()

    def _data_loop(self) -> None:
        """Fetch usage data in a background thread."""
        from claude_monitor.data.analysis import analyze_usage

        interval = max(5, getattr(self.args, "refresh_rate", 10))
        while self._running:
            try:
                data = analyze_usage(
                    hours_back=6,
                    quick_start=True,
                    use_cache=True,
                    data_path=self.data_path,
                )
                with self._lock:
                    self._latest_data = data
            except Exception as exc:
                logger.debug("Popup data fetch error: %s", exc)
            time.sleep(interval)

    # ── Periodic display refresh ──────────────────────────────────────────────

    def _schedule_refresh(self) -> None:
        self._do_refresh()
        self.root.after(2000, self._schedule_refresh)

    def _do_refresh(self) -> None:
        with self._lock:
            data = self._latest_data

        self.text.configure(state="normal")
        self.text.delete("1.0", "end")

        if data is None:
            self._w("  ◌ Connecting...\n", "dim")
            self.text.configure(state="disabled")
            return

        blocks: List[Dict[str, Any]] = data.get("blocks", [])
        active = next(
            (b for b in blocks if isinstance(b, dict) and b.get("isActive")),
            None,
        )

        if active is None:
            self._w("  ◌ No active session\n", "dim")
            self._w("  Waiting for Claude activity…\n", "dim")
        else:
            tier_name = _TIERS[self._tier_idx][0]
            self._render_stats(active, tier_name)

        self.text.configure(state="disabled")

    # ── Stats rendering ───────────────────────────────────────────────────────

    def _render_stats(self, block: Dict[str, Any], tier: str) -> None:
        """Write coloured stat lines into the text widget."""
        from claude_monitor.core.plans import get_cost_limit, get_token_limit

        tokens_used: int = block.get("totalTokens", 0)
        cost:        float = block.get("costUSD", 0.0)
        sent:        int = block.get("sentMessagesCount", 0)
        plan:        str = getattr(self.args, "plan", "custom")

        tok_lim  = get_token_limit(plan) or 200_000
        cost_lim = get_cost_limit(plan)  or 100.0

        tok_pct  = min(100.0, tokens_used / tok_lim  * 100)
        cost_pct = min(100.0, cost        / cost_lim * 100)

        t_fill, t_empty = _mini_bar(tok_pct,  14)
        c_fill, c_empty = _mini_bar(cost_pct, 14)

        # ── Always shown ──────────────────────────────────────────────────────
        self._w("  ◉ Tokens  ", "dim")
        self._w(t_fill, _pct_tag(tok_pct))
        self._w(t_empty, "dim")
        self._w(f"  {tok_pct:5.1f}%\n", "val")

        self._w("  ◈ Cost    ", "dim")
        self._w(c_fill, _pct_tag(cost_pct))
        self._w(c_empty, "dim")
        self._w(f"  ${cost:.2f}\n", "val")

        if tier == "nano":
            return

        # ── Compact+ ─────────────────────────────────────────────────────────
        self._w("  ▷ Sent    ", "dim")
        self._w(f"{sent:,}", "val")
        self._w(" msgs\n", "dim")

        end_str = block.get("endTime", "")
        if end_str:
            try:
                from datetime import datetime, timezone as _tz
                end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                rem    = max(0.0, (end_dt - datetime.now(_tz.utc)).total_seconds())
                h, m   = int(rem // 3600), int((rem % 3600) // 60)
                self._w("  ⏳ Resets  ", "dim")
                self._w(f"{h}h {m}m\n", "info")
            except Exception:
                pass

        if tier == "compact":
            return

        # ── Full ─────────────────────────────────────────────────────────────
        self._w("\n")

        per_model: Dict[str, Any] = block.get("perModelStats", {})
        if isinstance(per_model, dict) and per_model:
            total_mt = sum(
                (v.get("input_tokens", 0) + v.get("output_tokens", 0))
                for v in per_model.values()
                if isinstance(v, dict)
            )
            self._w("  ◆ Models\n", "dim")
            for mname, stats in list(per_model.items())[:3]:
                if not isinstance(stats, dict):
                    continue
                mt   = stats.get("input_tokens", 0) + stats.get("output_tokens", 0)
                mpct = mt / total_mt * 100 if total_mt else 0.0
                short = (mname.split("-")[-1] if "-" in mname else mname)[:12]
                f, e  = _mini_bar(mpct, 10)
                self._w(f"    {short:<12} ", "dim")
                self._w(f"{f}", "info")
                self._w(f"{e}", "dim")
                self._w(f" {mpct:4.0f}%\n", "val")

    def _w(self, text: str, tag: str = "") -> None:
        """Insert text (optionally tagged with a colour)."""
        if tag:
            self.text.insert("end", text, tag)
        else:
            self.text.insert("end", text)

    # ── Controls ─────────────────────────────────────────────────────────────

    def _cycle_tier(self) -> None:
        """Advance to the next display tier and resize accordingly."""
        self._tier_idx = (self._tier_idx + 1) % len(_TIERS)
        _, w, h = _TIERS[self._tier_idx]
        x, y = self.root.winfo_x(), self.root.winfo_y()
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _toggle_pin(self) -> None:
        """Toggle the always-on-top attribute."""
        self._pinned = not self._pinned
        self.root.attributes("-topmost", self._pinned)
        self._pin_btn.configure(fg=_FG_GOOD if self._pinned else _FG_DIM)

    def _close(self) -> None:
        self._running = False
        self.root.destroy()

    # ── Drag ─────────────────────────────────────────────────────────────────

    def _drag_start(self, e: Any) -> None:
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e: Any) -> None:
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    # ── Resize ───────────────────────────────────────────────────────────────

    def _resize_start(self, e: Any) -> None:
        self._rx0, self._ry0 = e.x_root, e.y_root
        self._rw0 = self.root.winfo_width()
        self._rh0 = self.root.winfo_height()

    def _resize_move(self, e: Any) -> None:
        nw = max(240, self._rw0 + (e.x_root - self._rx0))
        nh = max(100, self._rh0 + (e.y_root - self._ry0))
        self.root.geometry(f"{nw}x{nh}+{self.root.winfo_x()}+{self.root.winfo_y()}")


# ── Module-level launcher ─────────────────────────────────────────────────────

def launch_popup(args: Any, data_path: str) -> None:
    """Launch the popup window.  Blocks until the window is closed.

    Args:
        args:      Parsed CLI namespace (needs ``plan``, ``refresh_rate``, …).
        data_path: Path to the Claude projects data directory.
    """
    try:
        MonitorPopup(args, data_path).run()
    except Exception as exc:
        logger.error("Popup launch failed: %s", exc)
        print(
            "\n⚠  Could not open the popup window.\n"
            "   Windows: tkinter is bundled with Python — this shouldn't happen.\n"
            "   Linux:   sudo apt install python3-tk\n"
            "   macOS:   brew install python-tk\n"
            f"\n   Error: {exc}\n"
        )
