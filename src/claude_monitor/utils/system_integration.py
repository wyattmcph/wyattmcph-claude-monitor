"""System integration utilities for Claude Monitor.

Handles desktop shortcuts, auto-start configuration, and Windows integration.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def create_desktop_shortcut() -> bool:
    """Create a shortcut on the user's desktop to launch Claude Monitor.

    Returns:
        True if successful, False otherwise.
    """
    if sys.platform != "win32":
        logger.info("Desktop shortcut creation is Windows-only")
        return False

    try:
        import winshell  # type: ignore
        from win32com.client import Dispatch  # type: ignore

        # Get the path to the executable
        if getattr(sys, "frozen", False):
            exe_path = sys.executable
        else:
            # Running from pip - use python -m entry point
            import shutil
            exe_path = shutil.which("claude-monitor")
            if not exe_path:
                logger.error("Could not find claude-monitor command")
                return False

        # Desktop path
        desktop = Path.home() / "Desktop"
        shortcut_path = desktop / "Claude Monitor.lnk"

        # Create shortcut using COM
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.TargetPath = exe_path
        shortcut.WorkingDirectory = str(Path.home())
        shortcut.Description = "Real-time Claude Code token usage monitor"
        shortcut.save()

        logger.info(f"Desktop shortcut created: {shortcut_path}")
        return True

    except ImportError:
        logger.error("pywin32 not available - install with: pip install pywin32")
        return False
    except Exception as e:
        logger.error(f"Failed to create desktop shortcut: {e}")
        return False


def enable_auto_start() -> bool:
    """Enable Claude Monitor to run automatically on Windows startup.

    Returns:
        True if successful, False otherwise.
    """
    if sys.platform != "win32":
        logger.info("Auto-start is Windows-only")
        return False

    try:
        import winreg

        # Get the executable path
        if getattr(sys, "frozen", False):
            exe_path = sys.executable
        else:
            import shutil
            exe_path = shutil.which("claude-monitor")
            if not exe_path:
                logger.error("Could not find claude-monitor command")
                return False

        # Registry path for startup
        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        # Add to startup registry
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "Claude Monitor", 0, winreg.REG_SZ, exe_path)
            logger.info("Auto-start enabled")
            return True
        except PermissionError:
            logger.error("Permission denied - run as administrator to enable auto-start")
            return False

    except Exception as e:
        logger.error(f"Failed to enable auto-start: {e}")
        return False


def disable_auto_start() -> bool:
    """Disable Claude Monitor auto-start.

    Returns:
        True if successful, False otherwise.
    """
    if sys.platform != "win32":
        logger.info("Auto-start is Windows-only")
        return False

    try:
        import winreg

        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_WRITE) as key:
                winreg.DeleteValue(key, "Claude Monitor")
            logger.info("Auto-start disabled")
            return True
        except FileNotFoundError:
            logger.debug("Auto-start entry not found")
            return True
        except PermissionError:
            logger.error("Permission denied - run as administrator to disable auto-start")
            return False

    except Exception as e:
        logger.error(f"Failed to disable auto-start: {e}")
        return False


def is_auto_start_enabled() -> bool:
    """Check if Claude Monitor is set to auto-start.

    Returns:
        True if auto-start is enabled, False otherwise.
    """
    if sys.platform != "win32":
        return False

    try:
        import winreg

        reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path) as key:
                winreg.QueryValueEx(key, "Claude Monitor")
                return True
        except FileNotFoundError:
            return False

    except Exception:
        return False
