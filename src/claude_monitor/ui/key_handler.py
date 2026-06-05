"""Non-blocking keyboard input handler for Claude Monitor.

Runs a daemon thread that reads single keypresses without blocking the main
thread.  Provides pause/resume so stdin is free when an interactive menu is
open.

Works on Windows (``msvcrt``) and Unix (``select`` + raw terminal mode).
"""

from __future__ import annotations

import platform
import queue
import threading
import time
from typing import Optional


class KeyHandler:
    """Non-blocking single-keypress reader.

    Usage::

        kh = KeyHandler()
        kh.start()

        while True:
            key = kh.get_key()   # returns str or None
            if key == 'm':
                kh.pause()
                do_something_interactive()
                kh.resume()
            time.sleep(0.05)

        kh.stop()
    """

    def __init__(self) -> None:
        self._queue:   queue.Queue[str] = queue.Queue()
        self._running: bool             = False
        self._enabled: threading.Event  = threading.Event()
        self._enabled.set()
        self._thread:  Optional[threading.Thread] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background key-reading thread."""
        self._running = True
        self._enabled.set()
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the background thread to exit."""
        self._running = False
        self._enabled.set()   # unblock if waiting on pause

    def pause(self) -> None:
        """Temporarily stop consuming stdin (e.g. while a menu is open)."""
        self._enabled.clear()
        # Drain any buffered keys so they don't leak into the menu input
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def resume(self) -> None:
        """Resume consuming stdin after a pause."""
        self._enabled.set()

    # ── Non-blocking key read ─────────────────────────────────────────────────

    def get_key(self) -> Optional[str]:
        """Return the next queued keypress, or ``None`` if the queue is empty."""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    # ── Background reader loop ────────────────────────────────────────────────

    def _read_loop(self) -> None:
        if platform.system() == "Windows":
            self._windows_loop()
        else:
            self._unix_loop()

    def _windows_loop(self) -> None:
        import msvcrt

        while self._running:
            self._enabled.wait()          # blocks while paused
            if not self._running:
                break
            if msvcrt.kbhit():
                try:
                    raw = msvcrt.getch()
                    # Skip special-key prefixes (0x00 / 0xe0)
                    if raw in (b"\x00", b"\xe0"):
                        msvcrt.getch()    # consume the second byte
                    else:
                        ch = raw.decode("utf-8", errors="ignore")
                        if ch:
                            self._queue.put(ch.lower())
                except Exception:
                    pass
            time.sleep(0.04)

    def _unix_loop(self) -> None:
        import select
        import sys
        import termios
        import tty

        fd = sys.stdin.fileno()
        try:
            old_settings = termios.tcgetattr(fd)
        except Exception:
            # stdin is not a tty (e.g. piped input) — just exit
            return

        try:
            tty.setraw(fd)
            while self._running:
                self._enabled.wait()
                if not self._running:
                    break
                readable, _, _ = select.select([sys.stdin], [], [], 0.04)
                if readable:
                    ch = sys.stdin.read(1)
                    if ch:
                        self._queue.put(ch.lower())
        except Exception:
            pass
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass
