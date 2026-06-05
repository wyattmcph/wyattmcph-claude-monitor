"""Simplified CLI entry point using pydantic-settings."""

import argparse
import contextlib
import logging
import signal
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, NoReturn, Optional, Union

from rich.console import Console

from claude_monitor import __version__
from claude_monitor.cli.bootstrap import (
    ensure_directories,
    init_timezone,
    setup_environment,
    setup_logging,
)
from claude_monitor.core.plans import Plans, PlanType, get_token_limit
from claude_monitor.core.settings import Settings
from claude_monitor.data.aggregator import UsageAggregator
from claude_monitor.data.analysis import analyze_usage
from claude_monitor.error_handling import report_error
from claude_monitor.monitoring.orchestrator import MonitoringOrchestrator
from claude_monitor.terminal.manager import (
    enter_alternate_screen,
    handle_cleanup_and_exit,
    handle_error_and_exit,
    restore_terminal,
    setup_terminal,
)
from claude_monitor.terminal.themes import get_themed_console, print_themed
from claude_monitor.ui.display_controller import DisplayController
from claude_monitor.ui.table_views import TableViewsController

# Type aliases for CLI callbacks
DataUpdateCallback = Callable[[Dict[str, Any]], None]
SessionChangeCallback = Callable[[str, str, Optional[Dict[str, Any]]], None]


def get_standard_claude_paths() -> List[str]:
    """Get list of standard Claude data directory paths to check."""
    return ["~/.claude/projects", "~/.config/claude/projects"]


def discover_claude_data_paths(custom_paths: Optional[List[str]] = None) -> List[Path]:
    """Discover all available Claude data directories.

    Args:
        custom_paths: Optional list of custom paths to check instead of standard ones

    Returns:
        List of Path objects for existing Claude data directories
    """
    paths_to_check: List[str] = (
        [str(p) for p in custom_paths] if custom_paths else get_standard_claude_paths()
    )

    discovered_paths: List[Path] = []

    for path_str in paths_to_check:
        path = Path(path_str).expanduser().resolve()
        if path.exists() and path.is_dir():
            discovered_paths.append(path)

    return discovered_paths


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point with direct pydantic-settings integration."""
    if argv is None:
        argv = sys.argv[1:]

    if "--version" in argv or "-v" in argv:
        print(f"claude-monitor {__version__}")
        return 0

    # Standalone config menu — no monitoring needed
    if "--config" in argv or "config" in argv:
        try:
            settings = Settings.load_with_last_used(
                [a for a in argv if a not in ("--config", "config")]
            )
            args = settings.to_namespace()
        except Exception:
            args = None
        from claude_monitor.ui.config_menu import run_config_menu
        run_config_menu(args)
        return 0

    # Set the console window title so the exe shows a real name
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.kernel32.SetConsoleTitleW(f"Claude Monitor {__version__}")
    except Exception:
        pass

    # Startup update check — synchronous, prompts user, defaults to yes.
    # Skipped in popup mode (no interactive prompts there).
    try:
        from claude_monitor.utils.update_check import startup_update_check
        startup_update_check(skip="--popup" in argv)
    except Exception:
        pass

    try:
        settings = Settings.load_with_last_used(argv)

        setup_environment()
        ensure_directories()

        # Auto-create keywords file on first run (no-op if it already exists)
        try:
            from claude_monitor.data.keyword_analyzer import ensure_keywords_file
            ensure_keywords_file()
        except Exception:
            pass  # never crash startup over this

        # Background PyPI update check (daemon thread, populates status bar notice)
        try:
            from claude_monitor.utils.update_check import UpdateChecker
            UpdateChecker.get().start()
        except Exception:
            pass

        if settings.log_file:
            setup_logging(settings.log_level, settings.log_file, disable_console=True)
        else:
            setup_logging(settings.log_level, disable_console=True)

        init_timezone(settings.timezone)

        args = settings.to_namespace()

        # ── First-run plan selection ───────────────────────────────────────
        # Show a one-time plan picker if the user hasn't explicitly chosen a
        # plan before (no saved_plan in last_used.json) AND didn't pass
        # --plan on the CLI this invocation.
        _plan_first_run_check(argv, args)

        # ── Handle export mode ─────────────────────────────────────────────
        if hasattr(args, "export") and args.export:
            _handle_export(args)
            return 0

        _run_monitoring(args)

        return 0

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
        return 0
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Monitor failed: {e}", exc_info=True)
        traceback.print_exc()
        return 1


# ── First-run plan picker ──────────────────────────────────────────────────────

def _plan_first_run_check(
    argv: List[str], args: "argparse.Namespace"
) -> None:
    """Show a one-time plan selection screen if no plan has been saved yet.

    Writes the choice to ``last_used.json`` as ``saved_plan`` so it is
    applied automatically on subsequent runs.

    Args:
        argv: Raw CLI argv (used to detect explicit ``--plan`` flag).
        args: Mutable args namespace — ``args.plan`` is updated in-place.
    """
    import json as _json

    config_dir    = Path.home() / ".claude-monitor"
    last_used_path = config_dir / "last_used.json"

    # Already confirmed a plan before?
    existing: Dict[str, Any] = {}
    if last_used_path.exists():
        try:
            existing = _json.loads(last_used_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    if "saved_plan" in existing:
        return   # already chosen — nothing to do

    # --plan was passed explicitly on the CLI — respect it and save it
    if any(a.startswith("--plan") for a in argv):
        _save_plan_choice(args.plan, config_dir, last_used_path, existing)
        return

    # ── Show the one-time picker ───────────────────────────────────────────
    from rich.console import Console as _Con
    from rich.rule import Rule as _Rule
    from rich.text import Text as _Txt

    c = _Con()
    c.print()
    from claude_monitor.terminal.icons import ICONS as _IC
    _h = _IC["header"]
    title = _Txt(f"{_h}  CLAUDE MONITOR  --  QUICK SETUP  {_h}", style="bold")
    c.print(_Rule(title=title, style="#C97A4A"))
    c.print()
    c.print("  [bold]What Claude plan are you on?[/bold]")
    c.print("  [dim](This sets your token & cost limits correctly. Press [m] later to change.)[/dim]")
    c.print()

    # ── Try to detect plan from history ────────────────────────────────────
    detected_plan = None
    try:
        from claude_monitor.data.plan_detector import detect_plan_from_history
        from pathlib import Path
        from claude_monitor.core.data_fetcher import load_session_blocks

        # Load the history and detect plan
        data_file = Path.home() / ".claude-monitor" / "session_data.json"
        if data_file.exists():
            blocks = load_session_blocks(data_file)
            if blocks:
                detected_plan = detect_plan_from_history(blocks)
    except Exception:
        pass  # Silently fail if detection doesn't work

    c.print("  [bold cyan][1][/bold cyan]  [value]Pro[/value]           [dim]$20/month  — most common[/dim]")
    c.print("  [bold cyan][2][/bold cyan]  [value]Max 5[/value]         [dim]$100/month — 5× usage[/dim]")
    c.print("  [bold cyan][3][/bold cyan]  [value]Max 20[/value]        [dim]$200/month — 20× usage[/dim]")
    c.print("  [bold cyan][4][/bold cyan]  [value]Custom[/value]        [dim]Calculate limits from your usage history[/dim]")

    if detected_plan:
        c.print(f"  [dim]✓ We detected you may be on [bold]{detected_plan.upper()}[/bold] based on your history[/dim]")
    c.print()

    _MAP = {"1": "pro", "2": "max5", "3": "max20", "4": "custom",
            "pro": "pro", "max5": "max5", "max20": "max20", "custom": "custom"}

    # Map detected plan to the default option
    _PLAN_TO_NUM = {"pro": "1", "max5": "2", "max20": "3", "custom": "4"}
    default_choice = _PLAN_TO_NUM.get(detected_plan, "1") if detected_plan else "1"

    from rich.prompt import Prompt as _P
    raw = _P.ask(
        "  [bold cyan]Enter number or name[/bold cyan]",
        default=default_choice,
        console=c,
        show_default=False,
    ).strip().lower()

    chosen = _MAP.get(raw, "pro")
    args.plan = chosen

    c.print()
    c.print(f"  [success]✓ Plan set to [bold]{chosen.upper()}[/bold]. "
            f"Press [m] while running to change it.[/success]")
    c.print()

    _save_plan_choice(chosen, config_dir, last_used_path, existing)


def _save_plan_choice(
    plan: str,
    config_dir: Path,
    last_used_path: Path,
    existing: "Dict[str, Any]",
) -> None:
    """Persist ``saved_plan`` to last_used.json."""
    import json as _json
    from datetime import datetime as _dt

    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        existing["saved_plan"] = plan
        existing.setdefault("timestamp", _dt.now().isoformat())
        tmp = last_used_path.with_suffix(".tmp")
        tmp.write_text(_json.dumps(existing, indent=2), encoding="utf-8")
        tmp.replace(last_used_path)
    except Exception:
        pass


def _run_monitoring(args: argparse.Namespace) -> None:
    """Main monitoring implementation without facade."""
    view_mode = getattr(args, "view", "realtime")

    if hasattr(args, "theme") and args.theme:
        console = get_themed_console(force_theme=args.theme.lower())
    else:
        console = get_themed_console()

    old_terminal_settings = setup_terminal()
    live_display_active: bool = False

    try:
        data_paths: List[Path] = discover_claude_data_paths()
        if not data_paths:
            print_themed("No Claude data directory found", style="error")
            return

        data_path: Path = data_paths[0]
        logger = logging.getLogger(__name__)
        logger.info(f"Using data path: {data_path}")

        # ── Popup / PiP mode ─────────────────────────────────────────────────
        if getattr(args, "popup", False):
            from claude_monitor.ui.popup_window import launch_popup
            launch_popup(args, str(data_path))
            return

        # Handle different view modes
        if view_mode in ["daily", "monthly", "sessions"]:
            _run_table_view(args, data_path, view_mode, console)
            return

        token_limit: int = _get_initial_token_limit(args, str(data_path))

        display_controller = DisplayController()
        display_controller.live_manager._console = console

        refresh_per_second: float = getattr(args, "refresh_per_second", 0.75)
        logger.info(
            f"Display refresh rate: {refresh_per_second} Hz ({1000 / refresh_per_second:.0f}ms)"
        )
        logger.info(f"Data refresh rate: {args.refresh_rate} seconds")

        live_display = display_controller.live_manager.create_live_display(
            auto_refresh=True, console=console, refresh_per_second=refresh_per_second
        )

        loading_display = display_controller.create_loading_display(
            args.plan, args.timezone
        )

        enter_alternate_screen()

        live_display_active = False

        try:
            # Enter live context and show loading screen immediately
            live_display.__enter__()
            live_display_active = True
            live_display.update(loading_display)

            orchestrator = MonitoringOrchestrator(
                update_interval=(
                    args.refresh_rate if hasattr(args, "refresh_rate") else 10
                ),
                data_path=str(data_path),
            )
            orchestrator.set_args(args)

            # Shared mutable container so the key loop can force a re-render
            # immediately without waiting for the next orchestrator tick.
            # _last_data[0] = last raw data dict
            # _last_data[1] = last token_limit
            _last_data: List[Any] = [None, token_limit]

            def _force_render() -> None:
                """Re-render immediately using the last cached data + current args."""
                if _last_data[0] is None or not live_display_active:
                    return
                try:
                    r = display_controller.create_data_display(
                        _last_data[0], args, _last_data[1]
                    )
                    live_display.update(r)
                except Exception:
                    pass

            # Setup monitoring callback
            def on_data_update(monitoring_data: Dict[str, Any]) -> None:
                """Handle data updates from orchestrator."""
                try:
                    data: Dict[str, Any] = monitoring_data.get("data", {})
                    tl: int = monitoring_data.get("token_limit", token_limit)
                    blocks: List[Dict[str, Any]] = data.get("blocks", [])

                    _last_data[0] = data
                    _last_data[1] = tl

                    logger.debug(f"Display data has {len(blocks)} blocks")
                    if blocks:
                        active_blocks: List[Dict[str, Any]] = [
                            b for b in blocks if b.get("isActive")
                        ]
                        logger.debug(f"Active blocks: {len(active_blocks)}")
                        if active_blocks:
                            total_tokens: int = active_blocks[0].get("totalTokens", 0)
                            logger.debug(f"Active block tokens: {total_tokens}")

                    renderable = display_controller.create_data_display(
                        data, args, tl
                    )

                    if live_display:
                        live_display.update(renderable)

                except Exception as e:
                    logger.error(f"Display update error: {e}", exc_info=True)
                    report_error(
                        exception=e,
                        component="cli_main",
                        context_name="display_update_error",
                    )

            # Register callbacks
            orchestrator.register_update_callback(on_data_update)

            # Optional: Register session change callback
            def on_session_change(
                event_type: str, session_id: str, session_data: Optional[Dict[str, Any]]
            ) -> None:
                """Handle session changes."""
                if event_type == "session_start":
                    logger.info(f"New session detected: {session_id}")
                elif event_type == "session_end":
                    logger.info(f"Session ended: {session_id}")

            orchestrator.register_session_callback(on_session_change)

            # Start monitoring
            orchestrator.start()

            # Wait for initial data
            logger.info("Waiting for initial data...")
            if not orchestrator.wait_for_initial_data(timeout=10.0):
                logger.warning("Timeout waiting for initial data")

            # Main loop — key-polling replaces signal.pause() / sleep loop
            # so keyboard shortcuts work on every platform.
            from claude_monitor.ui.key_handler import KeyHandler

            key_handler = KeyHandler()
            key_handler.start()
            _ANIM_LEVELS = ["none", "subtle", "moderate", "full"]
            try:
                while True:
                    key = key_handler.get_key()
                    if key == "m":
                        # ── Open settings menu ──────────────────────────────
                        key_handler.pause()
                        try:
                            with contextlib.suppress(Exception):
                                live_display.__exit__(None, None, None)
                            live_display_active = False

                            from claude_monitor.ui.config_menu import ConfigMenu
                            menu_console = get_themed_console(
                                force_theme=getattr(args, "theme", "auto").lower()
                            )
                            menu = ConfigMenu(args=args, console=menu_console)
                            menu.run()

                            with contextlib.suppress(Exception):
                                live_display.__enter__()
                            live_display_active = True
                        finally:
                            key_handler.resume()

                    elif key == "k":
                        # ── Toggle keyword panel — immediate re-render ──────
                        args.show_keywords = not getattr(args, "show_keywords", True)
                        _force_render()

                    elif key == "a":
                        # ── Cycle animation level — immediate re-render ─────
                        cur = getattr(args, "animation", "subtle")
                        idx = _ANIM_LEVELS.index(cur) if cur in _ANIM_LEVELS else 1
                        args.animation = _ANIM_LEVELS[(idx + 1) % len(_ANIM_LEVELS)]
                        _force_render()

                    time.sleep(0.05)
            finally:
                key_handler.stop()
        finally:
            # Stop monitoring first
            if "orchestrator" in locals():
                orchestrator.stop()

            # Exit live display context if it was activated
            if live_display_active:
                with contextlib.suppress(Exception):
                    live_display.__exit__(None, None, None)

    except KeyboardInterrupt:
        # Clean exit from live display if it's active
        if "live_display" in locals():
            with contextlib.suppress(Exception):
                live_display.__exit__(None, None, None)
        handle_cleanup_and_exit(old_terminal_settings)
    except Exception as e:
        # Clean exit from live display if it's active
        if "live_display" in locals():
            with contextlib.suppress(Exception):
                live_display.__exit__(None, None, None)
        handle_error_and_exit(old_terminal_settings, e)
    finally:
        restore_terminal(old_terminal_settings)


def _get_initial_token_limit(
    args: argparse.Namespace, data_path: Union[str, Path]
) -> int:
    """Get initial token limit for the plan."""
    logger = logging.getLogger(__name__)
    plan: str = getattr(args, "plan", PlanType.PRO.value)

    # For custom plans, check if custom_limit_tokens is provided first
    if plan == "custom":
        # If custom_limit_tokens is explicitly set, use it
        if hasattr(args, "custom_limit_tokens") and args.custom_limit_tokens:
            custom_limit = int(args.custom_limit_tokens)
            print_themed(
                f"Using custom token limit: {custom_limit:,} tokens",
                style="info",
            )
            return custom_limit

        # Otherwise, analyze usage data to calculate P90
        print_themed("Analyzing usage data to determine cost limits...", style="info")

        try:
            # Use quick start mode for faster initial load
            usage_data: Optional[Dict[str, Any]] = analyze_usage(
                hours_back=96 * 2,
                quick_start=False,
                use_cache=False,
                data_path=str(data_path),
            )

            if usage_data and "blocks" in usage_data:
                blocks: List[Dict[str, Any]] = usage_data["blocks"]
                token_limit: int = get_token_limit(plan, blocks)

                print_themed(
                    f"P90 session limit calculated: {token_limit:,} tokens",
                    style="info",
                )

                return token_limit

        except Exception as e:
            logger.warning(f"Failed to analyze usage data: {e}")

        # Fallback to default limit
        print_themed("Using default limit as fallback", style="warning")
        return Plans.DEFAULT_TOKEN_LIMIT

    # For standard plans, just get the limit
    return get_token_limit(plan)


def handle_application_error(
    exception: Exception,
    component: str = "cli_main",
    exit_code: int = 1,
) -> NoReturn:
    """Handle application-level errors with proper logging and exit.

    Args:
        exception: The exception that occurred
        component: Component where the error occurred
        exit_code: Exit code to use when terminating
    """
    logger = logging.getLogger(__name__)

    # Log the error with traceback
    logger.error(f"Application error in {component}: {exception}", exc_info=True)

    # Report to error handling system
    from claude_monitor.error_handling import report_application_startup_error

    report_application_startup_error(
        exception=exception,
        component=component,
        additional_context={
            "exit_code": exit_code,
            "args": sys.argv,
        },
    )

    # Print user-friendly error message
    print(f"\nError: {exception}", file=sys.stderr)
    print("For more details, check the log files.", file=sys.stderr)

    sys.exit(exit_code)


def validate_cli_environment() -> Optional[str]:
    """Validate the CLI environment and return error message if invalid.

    Returns:
        Error message if validation fails, None if successful
    """
    try:
        # Check Python version compatibility
        if sys.version_info < (3, 8):
            return f"Python 3.8+ required, found {sys.version_info.major}.{sys.version_info.minor}"

        # Check for required dependencies
        required_modules = ["rich", "pydantic", "watchdog"]
        missing_modules: List[str] = []

        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)

        if missing_modules:
            return f"Missing required modules: {', '.join(missing_modules)}"

        return None

    except Exception as e:
        return f"Environment validation failed: {e}"


def _handle_export(args: argparse.Namespace) -> None:
    """Handle CSV export of session data.

    Args:
        args: Settings namespace with export path
    """
    logger = logging.getLogger(__name__)
    console = get_themed_console()

    try:
        # Discover Claude data paths
        data_paths: List[Path] = discover_claude_data_paths()
        if not data_paths:
            print_themed("No Claude data directory found", style="error")
            return

        data_path = data_paths[0]
        export_path = args.export

        # Load usage data and create session blocks
        from claude_monitor.data.reader import load_usage_entries
        from claude_monitor.data.analyzer import SessionAnalyzer
        from claude_monitor.data.exporter import export_sessions_to_csv, export_summary_to_csv

        print_themed("Loading usage data...", style="info")
        entries, _ = load_usage_entries(str(data_path))

        if not entries:
            print_themed("No usage data found", style="warning")
            return

        print_themed(f"Processing {len(entries)} entries...", style="info")
        analyzer = SessionAnalyzer()
        blocks = analyzer.transform_to_blocks(entries)

        if not blocks:
            print_themed("No session blocks created", style="warning")
            return

        # Export to CSV
        print_themed(f"Exporting {len(blocks)} sessions to CSV...", style="info")
        sessions_file = export_sessions_to_csv(blocks, export_path)
        print_themed(f"✓ Sessions exported to: {sessions_file}", style="success")

        # Also generate summary
        summary_dir = Path(export_path).parent if export_path else Path.home() / "Downloads"
        summary_path = summary_dir / "claude-monitor-summary.csv"
        summary_file = export_summary_to_csv(blocks, str(summary_path))
        print_themed(f"✓ Summary exported to: {summary_file}", style="success")

    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        print_themed(f"Export failed: {e}", style="error")


def _run_table_view(
    args: argparse.Namespace, data_path: Path, view_mode: str, console: Console
) -> None:
    """Run table view mode (daily/monthly/sessions)."""
    logger = logging.getLogger(__name__)

    try:
        # Create table controller
        controller = TableViewsController(console=console)

        # Handle sessions view mode separately
        if view_mode == "sessions":
            from claude_monitor.data.reader import load_usage_entries
            from claude_monitor.data.analyzer import SessionAnalyzer

            logger.info("Loading session data...")
            entries, _ = load_usage_entries(str(data_path))

            if not entries:
                print_themed("No usage data found for sessions view", style="warning")
                return

            analyzer = SessionAnalyzer()
            blocks = analyzer.transform_to_blocks(entries)

            if not blocks:
                print_themed("No session blocks created", style="warning")
                return

            # Convert blocks to display format
            sessions_data = []
            for block in blocks:
                if not block.is_gap:
                    sessions_data.append({
                        "id": block.id,
                        "start_time": block.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "duration_minutes": block.duration_minutes,
                        "models": block.models,
                        "total_tokens": block.token_counts.total_tokens,
                        "cost": block.cost_usd,
                        "message_count": block.sent_messages_count,
                    })

            # Calculate totals
            totals = {
                "total_tokens": sum(s["total_tokens"] for s in sessions_data),
                "total_cost": sum(s["cost"] for s in sessions_data),
                "message_count": sum(s["message_count"] for s in sessions_data),
            }

            aggregated_data = sessions_data
        else:
            # Use aggregator for daily/monthly modes
            aggregator = UsageAggregator(
                data_path=str(data_path),
                aggregation_mode=view_mode,
                timezone=args.timezone,
            )

            logger.info(f"Loading {view_mode} usage data...")
            aggregated_data = aggregator.aggregate()

            if not aggregated_data:
                print_themed(f"No usage data found for {view_mode} view", style="warning")
                return

            # Calculate totals from aggregated data
            totals = {
                "input_tokens": sum(d["input_tokens"] for d in aggregated_data),
                "output_tokens": sum(d["output_tokens"] for d in aggregated_data),
                "cache_creation_tokens": sum(d["cache_creation_tokens"] for d in aggregated_data),
                "cache_read_tokens": sum(d["cache_read_tokens"] for d in aggregated_data),
                "total_tokens": sum(
                    d["input_tokens"]
                    + d["output_tokens"]
                    + d["cache_creation_tokens"]
                    + d["cache_read_tokens"]
                    for d in aggregated_data
                ),
                "total_cost": sum(d["total_cost"] for d in aggregated_data),
            }

        # Display the table
        controller.display_aggregated_view(
            data=aggregated_data,
            view_mode=view_mode,
            timezone=args.timezone,
            plan=args.plan,
            token_limit=_get_initial_token_limit(args, data_path),
        )

        # Wait for user to press Ctrl+C
        print_themed("\nPress Ctrl+C to exit", style="info")
        try:
            # Use signal.pause() for more efficient waiting
            try:
                signal.pause()
            except AttributeError:
                # Fallback for Windows which doesn't support signal.pause()
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            print_themed("\nExiting...", style="info")

    except Exception as e:
        logger.error(f"Error in table view: {e}", exc_info=True)
        print_themed(f"Error displaying {view_mode} view: {e}", style="error")


if __name__ == "__main__":
    sys.exit(main())
