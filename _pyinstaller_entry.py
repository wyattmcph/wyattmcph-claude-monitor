"""PyInstaller entry point for claude-monitor.

Uses absolute imports instead of the relative imports in __main__.py,
which fail when PyInstaller runs the script outside of a package context.
This file is only used by the build — normal `python -m claude_monitor`
continues to use __main__.py as usual.
"""

import sys

# Bootstrap the console into UTF-8 + truecolor BEFORE any UI module loads,
# so the standalone exe renders box-drawing, gradient bars and icons crisply.
from claude_monitor.terminal.console_setup import setup_console

setup_console()

from claude_monitor.cli.main import main

sys.exit(main() or 0)
