# Changelog

## [3.3.3] - 2026-06-05

### Added

- **Update notice**: When a newer version is available on PyPI a quiet line appears below the status bar showing the version number and the upgrade command. The check runs in a background thread at startup and never blocks or crashes if the network is unavailable.

### Improved

- **Keyword scan performance**: JSONL files are now cached by modification time inside `KeywordAnalyzer`. On repeat runs, only files that have actually changed are re-parsed. The display controller also rate-limits keyword analysis to once every 30 seconds so the glob + stat calls don't run on every render tick.

[3.3.3]: https://github.com/wyattmcph/wyattmcph-claude-monitor/releases/tag/v3.3.3

---

## [3.3.2] - 2026-06-04

### Fixes

- **Plan picker on first run**: The monitor now shows a one-time plan selection screen before it starts if you haven't set a plan before. Your choice is saved to `last_used.json` and applied on every subsequent run. Pass `--plan` on the command line to override it, or change it through the settings menu.
- **Instant key response**: Pressing `k` or `a` now redraws the screen immediately instead of waiting for the next data refresh cycle.
- **Color palette**: Replaced the neon green/orange/red gradient colors with a muted palette. Progress bars now use sage green, warm orange, and soft coral. Header labels use warm cream tones. Plan badge colors are orange (Pro), periwinkle (Max 5), and muted purple (Max 20).
- **Plan changes saved correctly**: Changing your plan through the settings menu now persists it to `last_used.json` so it's still set next time you run.

[3.3.2]: https://github.com/wyattmcph/wyattmcph-claude-monitor/releases/tag/v3.3.2

---

## [3.3.1] - 2026-06-04

### Added

- **Settings menu**: Press `m` while the monitor is running to open a numbered settings panel. Change plan, animation level, theme, timezone, refresh rate, edit the keywords file, or add a keyword without touching the command line. All changes apply immediately and are saved for next time.
- **Keyboard shortcuts**: `m` opens the settings menu, `k` toggles the keyword panel, `a` cycles animation level. Hints are shown in the status bar at the bottom.
- **Standalone config**: `claude-monitor --config` or `cmonitor config` opens the settings menu without starting the monitor.

[3.3.1]: https://github.com/wyattmcph/wyattmcph-claude-monitor/releases/tag/v3.3.1

---

## [3.3.0] - 2026-06-04

### Added

- **Adaptive layout**: The display adjusts to your terminal size automatically. Under 18 rows shows bare essentials only. 18-27 rows shows core metrics. 28-37 rows shows full session stats. 38+ rows shows everything including the keyword panel. The keyword panel is always the first section hidden when the terminal shrinks and the last one added when it grows. Bar widths also scale with terminal width.
- **Popup window** (`--popup`): A floating always-on-top window that works alongside your Claude window. Frameless, draggable, resizable. The header button cycles through three display sizes. Requires tkinter (bundled with Python on Windows and macOS; `sudo apt install python3-tk` on Linux).
- **New icon set**: Replaced all original emoji with geometric Unicode characters (`◈` `◉` `▷` `⚡` `◆` `⏳` `✦` `↗` `●`).
- **Zero-config keywords**: The keywords file is created automatically on first run with ten common development topics. The panel shows a setup hint when no keywords match yet rather than disappearing.
- **`--no-show-keywords` flag**: Hides the keyword panel. The preference is saved between runs.

[3.3.0]: https://github.com/wyattmcph/wyattmcph-claude-monitor/releases/tag/v3.3.0

---

## [3.2.2] - 2026-06-05

### Fixed

- Gradient bars were invisible because dark and light theme cost styles were both mapped to plain white or plain black. All three segments now use distinct colors so the gradient is actually visible.

[3.2.2]: https://github.com/wyattmcph/wyattmcph-claude-monitor/releases/tag/v3.2.2

---

## [3.2.1] - 2026-06-05

### Fixed

- Blank screen on old Windows PowerShell. A Rich `Panel` component inside the `Live` display was miscalculating terminal height silently. Replaced with `Rule` + `Text` which works on all terminals.

[3.2.1]: https://github.com/wyattmcph/wyattmcph-claude-monitor/releases/tag/v3.2.1

---

## [3.2.0] - 2026-06-04

### Added

- **Keyword analytics**: A panel showing token and cost breakdown by topic. Configure keywords in `~/.claude-monitor/keywords.txt` or pass `--keywords "unreal,python,git"` to override for a session.
- **Gradient progress bars**: Bars fill green to orange to red so you can read usage level at a glance.
- **Animated header**: Rule-based header with plan-color borders and a pulsing live indicator.
- **Burn rate sparkline**: Inline chart showing the last 20 burn rate samples. Enabled with `--animation moderate` or `--animation full`.
- **Animation level flag**: `--animation none/subtle/moderate/full`. Setting is saved between runs.

[3.2.0]: https://github.com/wyattmcph/wyattmcph-claude-monitor/releases/tag/v3.2.0

---

## [3.1.0] - 2025-07-23

### Added

- `--view daily` and `--view monthly` table views for aggregated usage history.

---

## [3.0.0] - 2025-01-13

### Breaking changes

- Package renamed from `claude-usage-monitor` to `claude-monitor`.
- Python minimum version raised from 3.8 to 3.9.
- Complete rewrite to a modular package structure (`src/claude_monitor/`).

### Added

- Modular architecture with separate `cli/`, `core/`, `data/`, `monitoring/`, `ui/`, and `terminal/` packages.
- Pydantic-based settings with validation and last-used parameter persistence.
- P90 percentile calculations for custom plan limit detection.
- Rich terminal UI with progress bars, burn rate indicators, and theme support.
- Automatic light/dark theme detection.
- Multi-Python CI testing (3.9-3.12).

[3.0.0]: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor/releases/tag/v3.0.0
