"""One-time console bootstrap for crisp Unicode + truecolor output.

This is the single most important fix for the standalone ``.exe``: when a
PyInstaller binary is launched by double-clicking, Windows opens it inside a
legacy ``conhost`` console whose output code page is usually 437 or 1252.
Rich emits UTF-8 bytes, so box-drawing characters, gradient bars and icons
show up as garbage (``ÔöÇ`` instead of ``─``).

Switching the console to code page 65001 (UTF-8) and enabling virtual-terminal
processing makes every modern glyph and 24-bit colour render correctly — the
same as running inside Windows Terminal.

``setup_console()`` is safe to call multiple times and is a no-op on
non-Windows platforms (where UTF-8 + VT are already the default).
"""

from __future__ import annotations

import os
import sys

_DONE = False


def setup_console() -> None:
    """Force the host console into UTF-8 + virtual-terminal mode.

    Must be called as early as possible — before any UI module imports the
    icon set — so that Unicode glyphs are selected over the ASCII fallback.
    All failures are swallowed: a monitor that can't tweak the console should
    still run, just with plainer output.
    """
    global _DONE
    if _DONE:
        return
    _DONE = True

    # Signal the rest of the app that the console is Unicode-capable, so the
    # icon set and box styles can use the pretty glyphs even in a frozen exe.
    os.environ.setdefault("CLAUDE_MONITOR_FORCE_UNICODE", "1")

    if sys.platform != "win32":
        return

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32

        # 1. UTF-8 code page for both input and output (65001).
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)

        # 2. Enable ANSI / virtual-terminal processing on the output handle so
        #    24-bit colour escape sequences are honoured by conhost.
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        STD_OUTPUT_HANDLE = -11
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(
                handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            )
    except Exception:
        pass

    # 3. Make sure Python's own stdout/stderr encode as UTF-8 too.
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except Exception:
                pass
