# Claude Code Usage Monitor

[![PyPI Version](https://img.shields.io/pypi/v/wyattmcph-claude-monitor.svg)](https://pypi.org/project/wyattmcph-claude-monitor/)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A real-time terminal monitor for Claude Code. A clean, centered dashboard shows token usage, session cost, burn rate, and keyword analytics so you know exactly how you're spending your plan limits — at a glance.

Fork of [Maciek-roboblog/Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor), extended with keyword analytics, an interactive settings menu, adaptive layout, and a floating popup window.

---

## Installation

### Fastest: one-line install (no Python required)

Paste one line into your terminal. It downloads the latest standalone build, puts
`claude-monitor` on your PATH, and (on Windows) adds Desktop + Start Menu shortcuts.

**Windows** (PowerShell):

```powershell
irm https://raw.githubusercontent.com/wyattmcph/wyattmcph-claude-monitor/main/install.ps1 | iex
```

**macOS / Linux**:

```bash
curl -fsSL https://raw.githubusercontent.com/wyattmcph/wyattmcph-claude-monitor/main/install.sh | bash
```

Then just run `claude-monitor` (or launch it from the Desktop shortcut on Windows).

> **Windows SmartScreen:** the exe isn't code-signed, so Defender may show a warning the
> first time. Click **More info → Run anyway**.

---

### Manual download

Prefer to grab the binary yourself? Go to
[Releases](https://github.com/wyattmcph/wyattmcph-claude-monitor/releases/latest):

| Platform | File | How to run |
|----------|------|-----------|
| **Windows** | `claude-monitor-windows.exe` | Double-click, or `.\claude-monitor-windows.exe` |
| **macOS** | `claude-monitor-macos` | `chmod +x claude-monitor-macos`, then `./claude-monitor-macos` |
| **Linux** | `claude-monitor-linux` | `chmod +x claude-monitor-linux`, then `./claude-monitor-linux` |

---

### Python package (for developers)

Install via package manager if you have Python 3.9+. Great if you want to run it from any terminal as `claude-monitor`.

**With uv** (fastest and cleanest):

```bash
# Install uv if you don't have it
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Then install the monitor
uv tool install wyattmcph-claude-monitor
claude-monitor
```

**With pip:**

```bash
pip install wyattmcph-claude-monitor
claude-monitor
```

**From source:**

```bash
git clone https://github.com/wyattmcph/wyattmcph-claude-monitor.git
cd wyattmcph-claude-monitor
pip install -e .
claude-monitor
```

---

### Which should I choose?

| | Standalone .exe | Python package |
|---|---|---|
| Setup time | Instant | ~30 seconds |
| Requires Python | No | Yes (3.9+) |
| Update method | Download new exe | `uv tool upgrade` or `pip install --upgrade` |
| Terminal integration | Works in any terminal | Full integration with `PATH` |
| Best for | One-click usage | Development or power users |

---

## Usage

```bash
claude-monitor          # start the monitor
cmonitor                # short alias
ccm                     # shortest alias
claude-monitor --config # open the settings menu without starting the monitor
```

First run shows a quick plan picker so you start with the right limits. Press `m` at any time to change settings while the monitor is running.

### Keyboard shortcuts (while running)

| Key | Action |
|-----|--------|
| `m` | Open the settings menu |
| `k` | Toggle the keyword analytics panel |
| `a` | Cycle animation level |
| Ctrl+C | Exit |

### All options

| Flag | Default | Description |
|------|---------|-------------|
| `--plan` | `pro` | `pro`, `max5`, `max20`, or `custom` |
| `--custom-limit-tokens` | | Explicit token cap for custom plan |
| `--view` | `realtime` | `realtime`, `daily`, or `monthly` |
| `--animation` | `subtle` | `none`, `subtle`, `moderate`, or `full` |
| `--keywords` | | Comma-separated topics to track, e.g. `"unreal,python"` |
| `--show-keywords` | on | Pass `--no-show-keywords` to hide the keyword panel |
| `--popup` | | Launch as a floating always-on-top window |
| `--config` | | Open settings menu without starting the monitor |
| `--timezone` | auto | Any valid timezone, e.g. `America/New_York` |
| `--time-format` | auto | `12h`, `24h`, or `auto` |
| `--theme` | auto | `light`, `dark`, `classic`, or `auto` |
| `--refresh-rate` | `10` | Seconds between data updates (1-60) |
| `--refresh-per-second` | `0.75` | Display refresh rate in Hz (0.1-20) |
| `--reset-hour` | | Override daily reset hour (0-23) |
| `--log-file` | | Write logs to this path |
| `--log-level` | `INFO` | `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `--debug` | | Shorthand for `--log-level DEBUG` |
| `--clear` | | Wipe saved preferences |
| `--version` / `-v` | | Print version and exit |

Settings are saved to `~/.claude-monitor/last_used.json` and restored on the next run. Passing any flag explicitly overrides the saved value for that session.

---

## Plans

| Plan | Token limit | Cost limit | Use when |
|------|-------------|------------|----------|
| `pro` | 200,000 | $20 | Claude Pro ($20/mo) |
| `max5` | 1,000,000 | $100 | Claude Max 5x ($100/mo) |
| `max20` | 4,000,000 | $400 | Claude Max 20x ($200/mo) |
| `custom` | P90 auto-detect | $50+ | Unknown or variable limits |

**On first run**, the monitor automatically detects your plan based on your usage history. You can always change it:
- Press `m` while running and select option 1
- Or pass `--plan pro` / `--plan max5` / etc. on the command line

The `custom` plan analyzes your session history and uses the 90th-percentile values as your limits. It adapts over time.

---

## Keyword Analytics

The keyword panel tracks how many tokens and dollars went to conversations about specific topics.

**Quick session tracking:**

```bash
claude-monitor --keywords "unreal,python,git"
```

**Persistent list** -- create `~/.claude-monitor/keywords.txt`, one keyword per line:

```
# My projects
unreal
blueprint
python
git
debugging
```

The file is created automatically on first run with some common defaults. Edit it, or use the settings menu (`m` then `7`) to add keywords interactively.

The `--keywords` flag overrides the file for that session.

---

## Popup window

Run a compact floating overlay alongside your Claude window:

```bash
claude-monitor --popup
```

The window is always on top, draggable, and resizable. The `⊞` button in the header cycles between display sizes. Requires tkinter, which comes with Python on Windows and macOS. On Linux: `sudo apt install python3-tk`.

---

## Adaptive layout

The display automatically adjusts to your terminal size:

| Terminal height | What shows |
|----------------|------------|
| Under 18 rows | Token bar, cost, burn rate, status line |
| 18-27 rows | Core metrics and predictions |
| 28-37 rows | Full session stats |
| 38+ rows | Full stats plus keyword panel |

Bar widths also adjust to terminal width. The keyword panel is always the first thing hidden when you shrink the window and the last thing added when you expand it.

---

## Features

### Redesigned dashboard (v3.6)
A single rounded, plan-coloured card centered in your terminal — aligned metric rows,
severity-coloured progress bars, compact limits, burn-rate sparkline and live model split.
It scales as you resize and looks crisp even in the standalone Windows exe.

### CSV Export
Export your session data for analysis in Excel or other tools:

```bash
claude-monitor --export ~/Downloads/sessions.csv
```

Creates two files:
- `sessions.csv` — individual session details (tokens, cost, duration, models)
- `summary.csv` — aggregated stats by model (usage %, cost %)

### Session History View
View a table of all your recent sessions:

```bash
claude-monitor --view sessions
```

Shows session ID, start time, duration, models used, tokens, and cost.

### Auto-Detection
On first run, the monitor analyzes your usage history and automatically suggests the correct plan. No need to guess!

### OS Notifications
Get desktop notifications at 70%, 80%, and 95% token usage so you never hit limits unexpectedly.

---

## Views

```bash
claude-monitor --view realtime   # live monitor (default)
claude-monitor --view daily      # daily usage table
claude-monitor --view monthly    # monthly usage table
claude-monitor --view sessions   # individual session records
```

---

## How sessions work

Claude Code uses 5-hour rolling session windows. A session starts with your first message and runs for exactly 5 hours. Token and cost limits apply per window. The monitor tracks the active session and shows a prediction for when tokens will run out.

---

## Examples

```bash
# Pro plan, US East Coast, track Unreal work
claude-monitor --plan pro --timezone America/New_York --keywords "unreal,blueprint"

# Max5 plan with sparkline chart
claude-monitor --plan max5 --animation moderate

# Daily usage summary
claude-monitor --view daily

# Popup window for side-by-side with Claude
claude-monitor --popup

# Reset all saved settings
claude-monitor --clear
```

---

## Development

```bash
git clone https://github.com/wyattmcph/wyattmcph-claude-monitor.git
cd wyattmcph-claude-monitor
pip install -e ".[dev]"
python -m pytest src/tests/ -q
python -m claude_monitor
```

---

## Troubleshooting

**"externally-managed-environment" error on Linux**
Use `uv tool install wyattmcph-claude-monitor` or `pipx install wyattmcph-claude-monitor` instead of bare pip.

**Command not found after pip install**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

**No data showing**
Send at least one message in Claude Code first, then wait one refresh cycle (default 10 seconds).

**Numbers seem too high or too low**
You probably have the wrong plan selected. Press `m` and choose option 1 to set your plan.

**Keyword panel not appearing**
The panel needs at least one keyword configured. It also only shows when your terminal is tall enough (38+ rows). Press `k` to toggle it or resize the window.

---

## License

[MIT](LICENSE)

## Credits

Original monitor by [Maciek-roboblog](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor). Extended by [wyattmcph](https://github.com/wyattmcph).

[Report a bug](https://github.com/wyattmcph/wyattmcph-claude-monitor/issues) · [Request a feature](https://github.com/wyattmcph/wyattmcph-claude-monitor/issues)
