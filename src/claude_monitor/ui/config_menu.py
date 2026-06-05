"""Interactive settings menu for Claude Monitor.

Accessible two ways:
  • Press [m] while the monitor is running
  • Run  ``claude-monitor --config``  directly

All changes are applied immediately to the running session AND persisted to
``~/.claude-monitor/last_used.json`` so they survive restarts.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

_CONFIG_DIR    = Path.home() / ".claude-monitor"
_KW_FILE       = _CONFIG_DIR / "keywords.txt"
_LAST_USED     = _CONFIG_DIR / "last_used.json"


# ── Plan / option lists ────────────────────────────────────────────────────────
_PLANS      = ["pro", "max5", "max20", "custom"]
_ANIMATIONS = ["none", "subtle", "moderate", "full"]
_THEMES     = ["auto", "dark", "light"]


class ConfigMenu:
    """Rich-based interactive settings menu.

    Args:
        args:    The live CLI args namespace (modified in-place on changes).
        console: Rich console to render into (creates a new one if omitted).
    """

    def __init__(
        self,
        args: Optional[Any] = None,
        console: Optional[Console] = None,
    ) -> None:
        self.args    = args
        self.console = console or Console()

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        """Show the menu loop.

        Returns:
            Dict of every setting that was changed (key → new value).
        """
        changes: Dict[str, Any] = {}

        while True:
            self.console.clear()
            self._render_header()
            self._render_current_settings()
            self._render_options()

            choice = self._ask_choice()

            if choice in ("0", "q", ""):
                break

            result = self._dispatch(choice)
            if result:
                changes.update(result)
                self._save_changes(changes)

        return changes

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _render_header(self) -> None:
        self.console.print(Rule(style="cyan"))
        self.console.print("[bold cyan]SETTINGS MENU[/bold cyan]")
        self.console.print(Rule(style="cyan"))
        self.console.print()

    def _render_current_settings(self) -> None:
        """Print the current configuration values in a clean table."""
        if not self.args:
            return

        a = self.args
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column(style="dim",   no_wrap=True)
        table.add_column(style="value", no_wrap=True)

        def _yn(v: bool) -> str:
            return "[success]ON[/success]" if v else "[error]OFF[/error]"

        table.add_row("Plan",            f"[bold]{getattr(a, 'plan', 'custom').upper()}[/bold]")
        table.add_row("Animation",       getattr(a, "animation",    "subtle"))
        table.add_row("Keyword panel",   _yn(getattr(a, "show_keywords", True)))
        table.add_row("Theme",           getattr(a, "theme",        "auto"))
        table.add_row("Timezone",        getattr(a, "timezone",     "auto"))
        table.add_row("Refresh rate",    f"{getattr(a, 'refresh_rate', 10)}s")
        table.add_row("Keywords file",   str(_KW_FILE))

        self.console.print(table)
        self.console.print()

    def _render_options(self) -> None:
        """Print the numbered / lettered option list."""
        self.console.print("[bold]Configuration Options:[/bold]")
        self.console.print()

        options = [
            ("1", "Change plan",           "pro / max5 / max20 / custom"),
            ("2", "Animation level",       "none / subtle / moderate / full"),
            ("3", "Toggle keyword panel",  "show/hide analytics"),
            ("4", "Theme",                 "auto / dark / light"),
            ("5", "Timezone",              "e.g. America/Denver, Europe/London"),
            ("6", "Refresh rate",          "seconds between updates (1-60)"),
            ("7", "Edit keywords file",    "add/remove tracked topics"),
            ("8", "Add a keyword",         "quick-add without opening file"),
        ]

        for key, label, hint in options:
            self.console.print(
                f"  [cyan]{key}[/cyan]  {label:<25} [dim]{hint}[/dim]"
            )

        self.console.print()
        self.console.print("[bold]System Integration:[/bold]")
        self.console.print("  s  Create desktop shortcut   add Monitor to your desktop")
        self.console.print("  x  Toggle auto-start         run on Windows startup")

        self.console.print()
        self.console.print("[bold]Advanced:[/bold]")
        self.console.print("  r  Reset saved settings      clear ~/.claude-monitor/last_used.json")
        self.console.print("  0  Save & return             back to monitor")
        self.console.print()

    # ── Input ─────────────────────────────────────────────────────────────────

    def _ask_choice(self) -> str:
        return Prompt.ask(
            "[bold cyan]Select option[/bold cyan]",
            default="0",
            console=self.console,
            show_default=False,
        ).strip().lower()

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def _dispatch(self, choice: str) -> Optional[Dict[str, Any]]:
        self.console.print()

        if choice == "1":
            return self._change_plan()
        if choice == "2":
            return self._change_animation()
        if choice == "3":
            return self._toggle_keywords()
        if choice == "4":
            return self._change_theme()
        if choice == "5":
            return self._change_timezone()
        if choice == "6":
            return self._change_refresh_rate()
        if choice == "7":
            self._edit_keywords_file()
        if choice == "8":
            return self._add_keyword()
        if choice == "9":
            self._show_popup_info()
        if choice == "s":
            self._create_desktop_shortcut()
        if choice == "x":
            self._toggle_auto_start()
        if choice == "r":
            self._reset_settings()

        return None

    # ── Option handlers ───────────────────────────────────────────────────────

    def _change_plan(self) -> Dict[str, Any]:
        current = getattr(self.args, "plan", "custom") if self.args else "custom"
        val = Prompt.ask(
            "  Plan",
            choices=_PLANS,
            default=current,
            console=self.console,
        )
        self._apply("plan", val)
        self.console.print(f"  [success]Plan set to {val.upper()}[/success]")
        return {"plan": val}

    def _change_animation(self) -> Dict[str, Any]:
        current = getattr(self.args, "animation", "subtle") if self.args else "subtle"
        self.console.print(
            "  [dim]none = static  subtle = pulsing dot (default)  "
            "moderate = dot + sparkline  full = all[/dim]"
        )
        val = Prompt.ask(
            "  Animation",
            choices=_ANIMATIONS,
            default=current,
            console=self.console,
        )
        self._apply("animation", val)
        self.console.print(f"  [success]Animation set to '{val}'[/success]")
        return {"animation": val}

    def _toggle_keywords(self) -> Dict[str, Any]:
        current = getattr(self.args, "show_keywords", True) if self.args else True
        val = not current
        status = "[success]ON[/success]" if val else "[error]OFF[/error]"
        self._apply("show_keywords", val)
        self.console.print(f"  Keyword panel → {status}")
        return {"show_keywords": val}

    def _change_theme(self) -> Dict[str, Any]:
        current = getattr(self.args, "theme", "auto") if self.args else "auto"
        val = Prompt.ask(
            "  Theme",
            choices=_THEMES,
            default=current,
            console=self.console,
        )
        self._apply("theme", val)
        self.console.print(f"  [success]Theme set to '{val}'[/success]")
        return {"theme": val}

    def _change_timezone(self) -> Dict[str, Any]:
        current = getattr(self.args, "timezone", "auto") if self.args else "auto"
        self.console.print(
            "  [dim]Examples: America/Denver  America/New_York  Europe/London  "
            "Asia/Tokyo  UTC[/dim]"
        )
        val = Prompt.ask("  Timezone", default=current, console=self.console)
        import pytz
        if val not in ("auto", "local") and val not in pytz.all_timezones:
            self.console.print(f"  [warning]'{val}' is not a recognised timezone — keeping current[/warning]")
            return {}
        self._apply("timezone", val)
        self.console.print(f"  [success]Timezone set to '{val}'[/success]")
        return {"timezone": val}

    def _change_refresh_rate(self) -> Dict[str, Any]:
        current = str(getattr(self.args, "refresh_rate", 10) if self.args else 10)
        val_str = Prompt.ask(
            "  Refresh rate (seconds, 1–60)",
            default=current,
            console=self.console,
        )
        try:
            val = max(1, min(60, int(val_str)))
        except ValueError:
            self.console.print("  [error]Must be a number between 1 and 60.[/error]")
            return {}
        self._apply("refresh_rate", val)
        self.console.print(f"  [success]Refresh rate set to {val}s[/success]")
        return {"refresh_rate": val}

    def _edit_keywords_file(self) -> None:
        """Show current keywords + open the file in the system editor."""
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not _KW_FILE.exists():
            try:
                from claude_monitor.data.keyword_analyzer import ensure_keywords_file
                ensure_keywords_file()
            except Exception:
                pass

        # Preview current content
        self.console.print(f"  [dim]File:[/dim] [bold]{_KW_FILE}[/bold]")
        self.console.print()
        try:
            lines  = _KW_FILE.read_text(encoding="utf-8").splitlines()
            active = [ln for ln in lines if ln.strip() and not ln.startswith("#")]
            self.console.print(
                f"  [dim]Active keywords ({len(active)} total):[/dim]"
            )
            for kw in active[:20]:
                self.console.print(f"    [value]- {kw}[/value]")
            if len(active) > 20:
                self.console.print(f"    [dim]… and {len(active) - 20} more[/dim]")
        except Exception:
            self.console.print("  [dim](could not read file)[/dim]")

        self.console.print()
        sub = Prompt.ask(
            "  [e] open in editor  [Enter] go back",
            default="",
            console=self.console,
        ).strip().lower()

        if sub == "e":
            try:
                if sys.platform == "win32":
                    os.startfile(str(_KW_FILE))
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", "-e", str(_KW_FILE)])
                else:
                    editor = os.environ.get("EDITOR", "nano")
                    subprocess.Popen([editor, str(_KW_FILE)])
                self.console.print("  [success]Opened in editor — save the file then return here.[/success]")
            except Exception as exc:
                self.console.print(f"  [error]Could not open editor: {exc}[/error]")
            Prompt.ask("  Press Enter to continue", default="", console=self.console)

    def _add_keyword(self) -> Optional[Dict[str, Any]]:
        """Append a keyword to the keywords file."""
        kw = Prompt.ask(
            "  New keyword (Enter to cancel)",
            default="",
            console=self.console,
        ).strip().lower()
        if not kw:
            return None
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(_KW_FILE, "a", encoding="utf-8") as f:
                f.write(f"\n{kw}")
            self.console.print(f"  [success]Added '[bold]{kw}[/bold]' to keywords.[/success]")
        except Exception as exc:
            self.console.print(f"  [error]Could not write: {exc}[/error]")
        # Changes to keyword file don't map to an args key, just refresh on next render
        return None

    def _show_popup_info(self) -> None:
        self.console.print(
            "  The popup window is a floating, always-on-top overlay that shows\n"
            "  your live Claude usage alongside anything else on your screen.\n"
        )
        self.console.print(
            "  Launch it by running this command in a [bold]separate[/bold] terminal:\n"
        )
        self.console.print(
            "    [bold value]claude-monitor --popup[/bold value]\n"
        )
        self.console.print(
            "  [dim]Controls:\n"
            "    Drag the header bar to move it\n"
            "    ⊞ cycles display tiers (nano → compact → full)\n"
            "    📌 toggles always-on-top pin\n"
            "    ⊿ (bottom-right) drag to resize\n"
            "    ✕ to close[/dim]\n"
        )
        Prompt.ask("  Press Enter to go back", default="", console=self.console)

    def _reset_settings(self) -> None:
        if Confirm.ask(
            "  Clear all saved preferences (last_used.json)?",
            default=False,
            console=self.console,
        ):
            try:
                _LAST_USED.unlink(missing_ok=True)
                self.console.print("  [success]Preferences cleared. Defaults will apply on next start.[/success]")
            except Exception as exc:
                self.console.print(f"  [error]Could not delete file: {exc}[/error]")
        Prompt.ask("  Press Enter to continue", default="", console=self.console)

    def _create_desktop_shortcut(self) -> None:
        """Create a desktop shortcut for Claude Monitor."""
        from claude_monitor.utils.system_integration import create_desktop_shortcut

        if create_desktop_shortcut():
            self.console.print("  [success]✓ Desktop shortcut created![/success]")
        else:
            self.console.print("  [error]✗ Failed to create desktop shortcut[/error]")
        Prompt.ask("  Press Enter to continue", default="", console=self.console)

    def _toggle_auto_start(self) -> None:
        """Toggle auto-start on Windows startup."""
        from claude_monitor.utils.system_integration import (
            disable_auto_start,
            enable_auto_start,
            is_auto_start_enabled,
        )

        current_state = is_auto_start_enabled()
        new_state = not current_state

        if new_state:
            if enable_auto_start():
                self.console.print("  [success]✓ Auto-start enabled - Monitor will run on startup[/success]")
            else:
                self.console.print("  [error]✗ Failed to enable auto-start[/error]")
        else:
            if disable_auto_start():
                self.console.print("  [success]✓ Auto-start disabled[/success]")
            else:
                self.console.print("  [error]✗ Failed to disable auto-start[/error]")

        Prompt.ask("  Press Enter to continue", default="", console=self.console)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _apply(self, key: str, val: Any) -> None:
        """Apply a setting to the live args namespace (if present)."""
        if self.args is not None:
            setattr(self.args, key, val)

    def _save_changes(self, changes: Dict[str, Any]) -> None:
        """Persist changed settings to last_used.json."""
        try:
            _CONFIG_DIR.mkdir(parents=True, exist_ok=True)

            existing: Dict[str, Any] = {}
            if _LAST_USED.exists():
                try:
                    existing = json.loads(_LAST_USED.read_text(encoding="utf-8"))
                except Exception:
                    pass

            for k, v in changes.items():
                if k == "plan":
                    # Save plan as saved_plan so it's loaded on next run
                    existing["saved_plan"] = v
                else:
                    existing[k] = v

            existing["timestamp"] = datetime.now().isoformat()

            tmp = _LAST_USED.with_suffix(".tmp")
            tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            tmp.replace(_LAST_USED)
        except Exception:
            pass


# ── Standalone entry point ─────────────────────────────────────────────────────

def run_config_menu(args: Optional[Any] = None) -> None:
    """Launch the settings menu as a standalone command (``--config``)."""
    from claude_monitor.terminal.themes import get_themed_console

    console = get_themed_console()
    menu    = ConfigMenu(args=args, console=console)

    console.print()
    changes = menu.run()
    console.clear()
    if changes:
        console.print(
            f"\n  [success]✓ Saved {len(changes)} change(s) to "
            f"{_LAST_USED}[/success]\n"
        )
    else:
        console.print("\n  [dim]No changes made.[/dim]\n")
