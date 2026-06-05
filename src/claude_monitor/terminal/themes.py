"""Unified theme management for terminal display."""

import logging
import os
import re
import sys
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

# Windows-compatible imports with graceful fallbacks
try:
    import select
    import termios
    import tty

    HAS_TERMIOS: bool = True
except ImportError:
    HAS_TERMIOS: bool = False

from rich.console import Console
from rich.theme import Theme


class BackgroundType(Enum):
    """Background detection types."""

    LIGHT = "light"
    DARK = "dark"
    UNKNOWN = "unknown"


@dataclass
class ThemeConfig:
    """Theme configuration for terminal display.

    Attributes:
        name: Human-readable theme name.
        colors: Mapping of color keys to ANSI/hex color values.
        symbols: Unicode symbols and ASCII fallbacks for theme.
        rich_theme: Rich library theme configuration.
    """

    name: str
    colors: Dict[str, str]
    symbols: Dict[str, Union[str, List[str]]]
    rich_theme: Theme

    def get_color(self, key: str, default: str = "default") -> str:
        """Get color for key with fallback.

        Args:
            key: Color key to look up.
            default: Default color value if key not found.

        Returns:
            Color value string (ANSI code, hex, or color name).
        """
        return self.colors.get(key, default)


class AdaptiveColorScheme:
    """Scientifically-based adaptive color schemes with proper contrast ratios.

    IMPORTANT: This only changes FONT/FOREGROUND colors, never background colors.
    The terminal's background remains unchanged - we adapt text colors for readability.

    All color choices follow WCAG AA accessibility standards for contrast ratios.
    """

    @staticmethod
    def get_light_background_theme() -> Theme:
        """Font colors optimized for light terminal backgrounds.

        Same Claude-inspired palette as dark theme but darkened for
        contrast against light backgrounds.
        """
        return Theme(
            {
                "header":    "#5C4F3D",  # dark warm brown
                "info":      "#3D5F8A",  # dark periwinkle
                "warning":   "#8A4F1F",  # dark Claude orange
                "error":     "#8A3030",  # dark coral-red
                "success":   "#2E6B50",  # dark sage
                "value":     "#2A2520",  # near-black warm
                "dim":       "#7A7870",  # warm mid-grey
                "separator": "#9A9890",  # lighter divider
                "progress_bar": "black",
                "highlight": "#8A3030",

                "cost.low":    "#2E6B50",
                "cost.medium": "#8A4F1F",
                "cost.high":   "#8A3030",

                "table.border":   "#C0BDB6",
                "table.header":   "bold #5C4F3D",
                "table.row":      "#2A2520",
                "table.row.alt":  "#4A453E",

                "progress.bar.fill":    "black",
                "progress.bar":         "black",
                "progress.bar.empty":   "#D8D5CE",
                "progress.percentage":  "bold #2A2520",

                "chart.bar":   "#3D5F8A",
                "chart.line":  "#5C4F3D",
                "chart.point": "#8A3030",
                "chart.axis":  "#9A9890",
                "chart.label": "#2A2520",

                "status.active":   "#2E6B50",
                "status.inactive": "#7A7870",
                "status.warning":  "#8A4F1F",
                "status.error":    "#8A3030",

                "time.elapsed":   "#2A2520",
                "time.remaining": "#8A4F1F",
                "time.duration":  "#3D5F8A",

                "model.opus":    "#5A3D8A",
                "model.sonnet":  "#3D5F8A",
                "model.haiku":   "#2E6B50",
                "model.unknown": "#7A7870",

                "plan.pro":    "#8A4F1F",
                "plan.max5":   "#3D5F8A",
                "plan.max20":  "#5A3D8A",
                "plan.custom": "#2E6B50",
            }
        )

    @staticmethod
    def get_dark_background_theme() -> Theme:
        """Font colors optimized for dark terminal backgrounds.

        Palette inspired by Claude's brand aesthetic: warm off-whites,
        muted sage greens, and Claude's signature warm orange — nothing
        neon or jarring.
        """
        return Theme(
            {
                # ── Core text ────────────────────────────────────────────────
                "header":    "#C8BCA8",  # warm cream — Claude-brand feel
                "info":      "#7B9EC5",  # muted periwinkle blue
                "warning":   "#C97A4A",  # Claude warm orange (muted)
                "error":     "#C06060",  # soft coral-red
                "success":   "#6BA48C",  # muted sage green
                "value":     "#DDD5C5",  # warm off-white
                "dim":       "#787B85",  # cool mid-grey
                "separator": "#52555E",  # dark divider grey
                "progress_bar": "white",
                "highlight": "#C06060",

                # ── Cost / usage levels ───────────────────────────────────────
                # These drive the gradient bars — intentionally muted.
                "cost.low":    "#6BA48C",  # sage green   (< 50 %)
                "cost.medium": "#C97A4A",  # Claude orange (50–80 %)
                "cost.high":   "#C06060",  # soft coral   (> 80 %)

                # ── Table ─────────────────────────────────────────────────────
                "table.border":   "#484B54",
                "table.header":   "bold #C8BCA8",
                "table.row":      "#DDD5C5",
                "table.row.alt":  "#B8B0A2",

                # ── Progress bar internals ────────────────────────────────────
                "progress.bar.fill":    "white",
                "progress.bar":         "white",
                "progress.bar.empty":   "#3A3D45",
                "progress.percentage":  "bold #DDD5C5",

                # ── Charts ───────────────────────────────────────────────────
                "chart.bar":   "#7B9EC5",
                "chart.line":  "#C8BCA8",
                "chart.point": "#C06060",
                "chart.axis":  "#52555E",
                "chart.label": "#DDD5C5",

                # ── Status ───────────────────────────────────────────────────
                "status.active":   "#6BA48C",
                "status.inactive": "#787B85",
                "status.warning":  "#C97A4A",
                "status.error":    "#C06060",

                # ── Time ─────────────────────────────────────────────────────
                "time.elapsed":   "#DDD5C5",
                "time.remaining": "#C97A4A",
                "time.duration":  "#7B9EC5",

                # ── Model breakdown ───────────────────────────────────────────
                "model.opus":    "#9A85C4",  # muted purple  (Opus = powerful)
                "model.sonnet":  "#7B9EC5",  # periwinkle    (Sonnet = default)
                "model.haiku":   "#6BA48C",  # sage          (Haiku = fast)
                "model.unknown": "#787B85",

                # ── Plan colours (used in header Rule + badge) ────────────────
                "plan.pro":    "#C97A4A",  # warm orange  — Pro
                "plan.max5":   "#7B9EC5",  # periwinkle   — Max 5
                "plan.max20":  "#9A85C4",  # muted purple — Max 20
                "plan.custom": "#6BA48C",  # sage green   — Custom
            }
        )

    @staticmethod
    def get_classic_theme() -> Theme:
        """Classic colors for maximum compatibility."""
        return Theme(
            {
                "header": "cyan",
                "info": "blue",
                "warning": "yellow",
                "error": "red",
                "success": "green",
                "value": "white",
                "dim": "bright_black",
                "separator": "white",
                "progress_bar": "green",
                "highlight": "red",
                # Cost styles
                "cost.low": "green",
                "cost.medium": "yellow",
                "cost.high": "red",
                # Table styles
                "table.border": "white",
                "table.header": "bold cyan",
                "table.row": "white",
                "table.row.alt": "bright_black",
                # Progress styles
                "progress.bar.fill": "green",
                "progress.bar.empty": "bright_black",
                "progress.percentage": "bold white",
                # Chart styles
                "chart.bar": "blue",
                "chart.line": "cyan",
                "chart.point": "red",
                "chart.axis": "white",
                "chart.label": "white",
                # Status styles
                "status.active": "green",
                "status.inactive": "bright_black",
                "status.warning": "yellow",
                "status.error": "red",
                # Time styles
                "time.elapsed": "white",
                "time.remaining": "yellow",
                "time.duration": "blue",
                # Model styles
                "model.opus": "cyan",
                "model.sonnet": "blue",
                "model.haiku": "green",
                "model.unknown": "bright_black",
                # Plan styles
                "plan.pro": "yellow",  # Yellow (premium)
                "plan.max5": "cyan",  # Cyan
                "plan.max20": "blue",  # Blue
                "plan.custom": "green",  # Green
            }
        )


class BackgroundDetector:
    """Detects terminal background type using multiple methods.

    Uses environment variables, OSC queries, and heuristics to determine
    whether the terminal has a light or dark background for optimal theming.
    """

    @staticmethod
    def detect_background() -> BackgroundType:
        """Detect terminal background using multiple methods.

        Tries multiple detection methods in order of reliability:
        1. COLORFGBG environment variable
        2. Known terminal environment hints
        3. OSC 11 color query (advanced terminals)

        Returns:
            Detected background type, defaults to DARK if unknown.
        """
        # Method 1: Check COLORFGBG environment variable
        colorfgbg_result: BackgroundType = BackgroundDetector._check_colorfgbg()
        if colorfgbg_result != BackgroundType.UNKNOWN:
            return colorfgbg_result

        # Method 2: Check known terminal environment variables
        env_result: BackgroundType = BackgroundDetector._check_environment_hints()
        if env_result != BackgroundType.UNKNOWN:
            return env_result

        # Method 3: Use OSC 11 query (advanced terminals only)
        osc_result: BackgroundType = BackgroundDetector._query_background_color()
        if osc_result != BackgroundType.UNKNOWN:
            return osc_result

        # Default fallback
        return BackgroundType.DARK

    @staticmethod
    def _check_colorfgbg() -> BackgroundType:
        """Check COLORFGBG environment variable.

        COLORFGBG format: "foreground;background" where background
        color 0-7 indicates dark, 8-15 indicates light background.

        Returns:
            Background type based on COLORFGBG or UNKNOWN if unavailable.
        """
        colorfgbg: str = os.environ.get("COLORFGBG", "")
        if not colorfgbg:
            return BackgroundType.UNKNOWN

        try:
            # COLORFGBG format: "foreground;background"
            parts: List[str] = colorfgbg.split(";")
            if len(parts) >= 2:
                bg_color: int = int(parts[-1])
                # Colors 0-7 are typically dark, 8-15 are bright
                return BackgroundType.LIGHT if bg_color >= 8 else BackgroundType.DARK
        except (ValueError, IndexError) as e:
            # COLORFGBG parsing failed - not critical, will use other detection methods
            logger: logging.Logger = logging.getLogger(__name__)
            logger.debug(f"Failed to parse COLORFGBG '{colorfgbg}': {e}")

        return BackgroundType.UNKNOWN

    @staticmethod
    def _check_environment_hints() -> BackgroundType:
        """Check environment variables for theme hints.

        Checks known terminal-specific environment variables and patterns
        to infer the likely background type.

        Returns:
            Background type based on environment hints or UNKNOWN.
        """
        # Windows Terminal session
        if os.environ.get("WT_SESSION"):
            return BackgroundType.DARK

        # Check terminal program
        if "TERM_PROGRAM" in os.environ:
            term_program: str = os.environ["TERM_PROGRAM"]
            if term_program == "Apple_Terminal":
                return BackgroundType.LIGHT
            if term_program == "iTerm.app":
                return BackgroundType.DARK

        # Check TERM variable patterns
        term: str = os.environ.get("TERM", "").lower()
        if "light" in term:
            return BackgroundType.LIGHT
        if "dark" in term:
            return BackgroundType.DARK

        return BackgroundType.UNKNOWN

    @staticmethod
    def _query_background_color() -> BackgroundType:
        """Query terminal background color using OSC 11.

        Sends an OSC (Operating System Command) 11 query to request the terminal's
        background color, then calculates perceived brightness to determine if
        the background is light or dark.

        Returns:
            Background type based on OSC 11 response or UNKNOWN if query fails.
        """
        if not HAS_TERMIOS:
            return BackgroundType.UNKNOWN

        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return BackgroundType.UNKNOWN

        old_settings: Optional[List[Any]] = None
        try:
            # Save terminal settings
            old_settings = termios.tcgetattr(sys.stdin)

            # Set terminal to raw mode
            tty.setraw(sys.stdin.fileno())

            # Send OSC 11 query
            sys.stdout.write("\033]11;?\033\\")
            sys.stdout.flush()

            # Wait for response with timeout
            ready_streams: List[Any] = select.select([sys.stdin], [], [], 0.1)[0]
            if ready_streams:
                # Read available data without blocking
                response: str = ""
                try:
                    # Read character by character with timeout to avoid blocking
                    import fcntl
                    import os

                    # Set stdin to non-blocking mode
                    fd = sys.stdin.fileno()
                    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
                    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

                    # Read up to 50 chars with timeout
                    for _ in range(50):
                        ready = select.select([sys.stdin], [], [], 0.01)[0]
                        if not ready:
                            break
                        char = sys.stdin.read(1)
                        if not char:
                            break
                        response += char
                        # Stop if we get the expected terminator
                        if response.endswith("\033\\"):
                            break

                    # Restore blocking mode
                    fcntl.fcntl(fd, fcntl.F_SETFL, fl)

                except (OSError, ImportError):
                    # Fallback to simple read if fcntl is not available
                    response = sys.stdin.read(50)

                # Parse response: \033]11;rgb:rrrr/gggg/bbbb\033\\
                if response:  # Only proceed if we got a response
                    rgb_match = re.search(
                        r"rgb:([0-9a-f]+)/([0-9a-f]+)/([0-9a-f]+)", response
                    )
                    if rgb_match:
                        r: str
                        g: str
                        b: str
                        r, g, b = rgb_match.groups()
                        # Convert hex to int and calculate brightness
                        red: int = int(r[:2], 16) if len(r) >= 2 else 0
                        green: int = int(g[:2], 16) if len(g) >= 2 else 0
                        blue: int = int(b[:2], 16) if len(b) >= 2 else 0

                        # Calculate perceived brightness using standard formula
                        brightness: float = (
                            red * 299 + green * 587 + blue * 114
                        ) / 1000

                        # Restore terminal settings
                        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

                        return (
                            BackgroundType.LIGHT
                            if brightness > 127
                            else BackgroundType.DARK
                        )

            # Restore terminal settings
            if old_settings is not None:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        except (OSError, termios.error, AttributeError):
            # Restore terminal settings on any error
            if old_settings is not None:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except (OSError, termios.error, AttributeError) as e:
                    # Terminal settings restoration failed - log but continue
                    # This is non-critical as the terminal will be cleaned up on process exit
                    logger: logging.Logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Failed to restore terminal settings during OSC query: {e}"
                    )

        return BackgroundType.UNKNOWN


class ThemeManager:
    """Manages themes with auto-detection and thread safety."""

    def __init__(self):
        self._lock = threading.Lock()
        self._current_theme: Optional[ThemeConfig] = None
        self._forced_theme: Optional[str] = None
        self.themes = self._load_themes()

    def _load_themes(self) -> Dict[str, ThemeConfig]:
        """Load all available themes.

        Creates theme configurations for light, dark, and classic themes
        with appropriate Rich theme objects and symbol sets.

        Returns:
            Dictionary mapping theme names to ThemeConfig objects.
        """
        themes: Dict[str, ThemeConfig] = {}

        # Load themes with Rich theme objects
        light_rich: Theme = AdaptiveColorScheme.get_light_background_theme()
        dark_rich: Theme = AdaptiveColorScheme.get_dark_background_theme()
        classic_rich: Theme = AdaptiveColorScheme.get_classic_theme()

        themes["light"] = ThemeConfig(
            name="light",
            colors={},  # No longer using color mappings from defaults.py
            symbols=self._get_symbols_for_theme("light"),
            rich_theme=light_rich,
        )

        themes["dark"] = ThemeConfig(
            name="dark",
            colors={},  # No longer using color mappings from defaults.py
            symbols=self._get_symbols_for_theme("dark"),
            rich_theme=dark_rich,
        )

        themes["classic"] = ThemeConfig(
            name="classic",
            colors={},  # No longer using color mappings from defaults.py
            symbols=self._get_symbols_for_theme("classic"),
            rich_theme=classic_rich,
        )

        return themes

    def _get_symbols_for_theme(
        self, theme_name: str
    ) -> Dict[str, Union[str, List[str]]]:
        """Get symbols based on theme.

        Args:
            theme_name: Name of theme to get symbols for.

        Returns:
            Dictionary mapping symbol names to Unicode or ASCII characters.
            Spinner symbols are returned as a list for animation.
        """
        if theme_name == "classic":
            return {
                "progress_empty": "-",
                "progress_full": "#",
                "bullet": "*",
                "arrow": "->",
                "check": "[OK]",
                "cross": "[X]",
                "spinner": ["|", "/", "-", "\\"],
            }
        return {
            "progress_empty": "░",
            "progress_full": "█",
            "bullet": "•",
            "arrow": "→",
            "check": "✓",
            "cross": "✗",
            "spinner": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        }

    def auto_detect_theme(self) -> str:
        """Auto-detect appropriate theme based on terminal.

        Uses BackgroundDetector to determine terminal background
        and returns appropriate theme name.

        Returns:
            Theme name ('light', 'dark') based on detected background.
            Defaults to 'dark' if detection fails.
        """
        background: BackgroundType = BackgroundDetector.detect_background()

        if background == BackgroundType.LIGHT:
            return "light"
        if background == BackgroundType.DARK:
            return "dark"
        # Default to dark if unknown
        return "dark"

    def get_theme(
        self, name: Optional[str] = None, force_detection: bool = False
    ) -> ThemeConfig:
        """Get theme by name or auto-detect.

        Args:
            name: Theme name ('light', 'dark', 'classic', 'auto') or None for auto.
            force_detection: Force re-detection of terminal background.

        Returns:
            ThemeConfig object for the requested or detected theme.
        """
        with self._lock:
            if name == "auto" or name is None:
                if force_detection or self._forced_theme is None:
                    detected_name: str = self.auto_detect_theme()
                    theme: ThemeConfig = self.themes.get(
                        detected_name, self.themes["dark"]
                    )
                    if not force_detection:
                        self._forced_theme = detected_name
                else:
                    theme = self.themes.get(self._forced_theme, self.themes["dark"])
            else:
                theme = self.themes.get(name, self.themes["dark"])
                self._forced_theme = name if name in self.themes else None

            self._current_theme = theme
            return theme

    def get_console(
        self, theme_name: Optional[str] = None, force_detection: bool = False
    ) -> Console:
        """Get themed console instance.

        Args:
            theme_name: Theme name or None for auto-detection.
            force_detection: Force re-detection of terminal background.

        Returns:
            Rich Console instance configured with the selected theme.
        """
        theme: ThemeConfig = self.get_theme(theme_name, force_detection)
        return Console(theme=theme.rich_theme, force_terminal=True)

    def get_current_theme(self) -> Optional[ThemeConfig]:
        """Get currently active theme.

        Returns:
            Currently active ThemeConfig or None if no theme selected.
        """
        return self._current_theme


# Cost-based styles with thresholds (moved from ui/styles.py)
COST_STYLES: Dict[str, str] = {
    "low": "cost.low",  # Green - costs under $1
    "medium": "cost.medium",  # Yellow - costs $1-$10
    "high": "cost.high",  # Red - costs over $10
}

# Cost thresholds for automatic style selection
COST_THRESHOLDS: List[Tuple[float, str]] = [
    (10.0, COST_STYLES["high"]),
    (1.0, COST_STYLES["medium"]),
    (0.0, COST_STYLES["low"]),
]

# Velocity/burn rate emojis and labels
VELOCITY_INDICATORS: Dict[str, Dict[str, Union[str, float]]] = {
    "slow": {"emoji": "🐌", "label": "Slow", "threshold": 50},
    "normal": {"emoji": "➡️", "label": "Normal", "threshold": 150},
    "fast": {"emoji": "🚀", "label": "Fast", "threshold": 300},
    "very_fast": {"emoji": "⚡", "label": "Very fast", "threshold": float("inf")},
}


# Helper functions for style selection
def get_cost_style(cost: float) -> str:
    """Get appropriate style for a cost value.

    Args:
        cost: Cost value in USD to categorize.

    Returns:
        Rich style name for the cost category.
    """
    for threshold, style in COST_THRESHOLDS:
        if cost >= threshold:
            return style
    return COST_STYLES["low"]


def get_velocity_indicator(burn_rate: float) -> Dict[str, str]:
    """Get velocity indicator based on burn rate.

    Args:
        burn_rate: Token consumption rate (tokens per minute).

    Returns:
        Dictionary with 'emoji' and 'label' keys for the velocity category.
    """
    for indicator in VELOCITY_INDICATORS.values():
        threshold_value = indicator["threshold"]
        if isinstance(threshold_value, (int, float)) and burn_rate < threshold_value:
            return {"emoji": str(indicator["emoji"]), "label": str(indicator["label"])}
    very_fast = VELOCITY_INDICATORS["very_fast"]
    return {"emoji": str(very_fast["emoji"]), "label": str(very_fast["label"])}


# ──────────────────────────────────────────────────────────────────────────────
# Animation state
# ──────────────────────────────────────────────────────────────────────────────

class AnimationState:
    """Thread-safe global animation frame counter.

    Incremented once per display render cycle so that all animated elements
    in a single render share the same frame index.
    """

    _frame: int = 0
    _lock: threading.Lock = threading.Lock()

    # Subtle: slow pulse ●◉○◉  (period ~4 frames)
    LIVE_FRAMES_SUBTLE: List[str] = ["●", "◉", "○", "◉"]
    # Moderate: braille spinner + live dot
    LIVE_FRAMES_MODERATE: List[str] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    # Full: same spinner, just used everywhere
    LIVE_FRAMES_FULL: List[str] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    @classmethod
    def tick(cls) -> int:
        """Advance frame counter and return new value."""
        with cls._lock:
            cls._frame = (cls._frame + 1) % 1000
            return cls._frame

    @classmethod
    def get(cls) -> int:
        """Return current frame without advancing."""
        return cls._frame

    @classmethod
    def live_dot(cls, animation_level: str = "subtle") -> str:
        """Return the live indicator string for the current frame.

        Args:
            animation_level: One of 'none', 'subtle', 'moderate', 'full'.

        Returns:
            A single Unicode character (or empty if animation is off).
        """
        if animation_level == "none":
            return "●"
        if animation_level in ("moderate", "full"):
            frames = cls.LIVE_FRAMES_MODERATE
        else:
            frames = cls.LIVE_FRAMES_SUBTLE
        return frames[cls._frame % len(frames)]


# ──────────────────────────────────────────────────────────────────────────────
# Sparkline helper
# ──────────────────────────────────────────────────────────────────────────────

_SPARKLINE_CHARS = "▁▂▃▄▅▆▇█"


def render_sparkline(values: List[float], width: int = 10) -> str:
    """Render a mini sparkline from a list of float values.

    Args:
        values: Recent values (latest at the end).
        width: Number of characters in the sparkline.

    Returns:
        Unicode sparkline string of exactly *width* characters.
    """
    if not values:
        return "─" * width

    # Use last *width* values, pad with zeros on the left if short
    vals = list(values[-width:])
    if len(vals) < width:
        vals = [0.0] * (width - len(vals)) + vals

    max_v = max(vals) if max(vals) > 0 else 1.0
    chars = [_SPARKLINE_CHARS[min(7, int(v / max_v * 8))] for v in vals]
    return "".join(chars)


# Global theme manager instance
_theme_manager: ThemeManager = ThemeManager()


def get_theme(name: Optional[str] = None) -> Theme:
    """Get Rich theme by name or auto-detect.

    Args:
        name: Theme name ('light', 'dark', 'classic') or None for auto-detection

    Returns:
        Rich Theme object
    """
    theme_config = _theme_manager.get_theme(name)
    return theme_config.rich_theme


def get_themed_console(force_theme: Optional[Union[str, bool]] = None) -> Console:
    """Get themed console - backward compatibility wrapper.

    Args:
        force_theme: Theme name to force, or None for auto-detection.

    Returns:
        Rich Console instance with appropriate theme.
    """
    if force_theme and isinstance(force_theme, str):
        return _theme_manager.get_console(force_theme)
    return _theme_manager.get_console(None)


def print_themed(text: str, style: str = "info") -> None:
    """Print text with themed styling - backward compatibility.

    Args:
        text: Text to print with styling.
        style: Rich style name to apply.
    """
    console: Console = _theme_manager.get_console()
    console.print(f"[{style}]{text}[/]")
