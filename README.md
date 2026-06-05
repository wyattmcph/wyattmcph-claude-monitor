# 🎯 Claude Code Usage Monitor

[![PyPI Version](https://img.shields.io/pypi/v/claude-monitor.svg)](https://pypi.org/project/claude-monitor/)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A real-time terminal monitor for Claude Code token usage — with keyword analytics, gradient progress bars, an animated Rich UI, and burn-rate sparklines. Track exactly where your tokens and budget are going, broken down by topic.

![Claude Monitor Screenshot](https://raw.githubusercontent.com/Maciek-roboblog/Claude-Code-Usage-Monitor/main/doc/scnew.png)

> **Fork of** [Maciek-roboblog/Claude-Code-Usage-Monitor](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor) — extended with keyword analytics and visual improvements in v3.2.0.

---

## ✨ What's New in v3.2.0

| Feature | Description |
|---|---|
| **🔍 Keyword Analytics** | See how many tokens and dollars went to conversations about `unreal`, `python`, `git`, or any topic you care about |
| **🎨 Gradient Progress Bars** | Bars fill green → yellow → red so you instantly know how urgent each metric is |
| **✨ Rich Panel Header** | Bordered header with plan-colour coding and an animated LIVE dot |
| **📈 Burn Rate Sparkline** | Inline `▁▂▃▄▅▆▇█` chart of your last 20 burn-rate samples |
| **🎛️ Animation Levels** | `--animation none/subtle/moderate/full` — pick how much motion you want |

---

## 🚀 Installation

### Recommended — uv (fastest, no environment issues)

```powershell
# Install uv if you don't have it (Windows)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

```bash
# Install uv (macOS / Linux)
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```bash
# Then install the monitor
uv tool install claude-monitor

# Run it
claude-monitor
```

### pip

```bash
pip install claude-monitor
claude-monitor
```

### pipx

```bash
pipx install claude-monitor
claude-monitor
```

### Install from this fork (latest changes)

```bash
pip install git+https://github.com/wyattmcph/Claude-Code-Usage-Monitor-and-Analyze.git
```

---

## 📖 Usage

```bash
claude-monitor          # default (custom plan, auto-detects limits)
cmonitor                # short alias
ccm                     # shortest alias
claude-code-monitor     # full alias
```

### All CLI Options

| Flag | Default | Description |
|---|---|---|
| `--plan` | `custom` | `pro` · `max5` · `max20` · `custom` |
| `--custom-limit-tokens` | — | Explicit token cap for custom plan |
| `--view` | `realtime` | `realtime` · `daily` · `monthly` |
| `--animation` | `subtle` | `none` · `subtle` · `moderate` · `full` |
| `--keywords` | — | Comma-separated topics to track (e.g. `"unreal,python"`) |
| `--timezone` | auto | Any valid timezone, e.g. `America/New_York` |
| `--time-format` | auto | `12h` · `24h` · `auto` |
| `--theme` | auto | `light` · `dark` · `classic` · `auto` |
| `--refresh-rate` | `10` | Data refresh in seconds (1–60) |
| `--refresh-per-second` | `0.75` | Display refresh in Hz (0.1–20) |
| `--reset-hour` | — | Override daily reset hour (0–23) |
| `--log-file` | — | Path to write log output |
| `--log-level` | `INFO` | `DEBUG` · `INFO` · `WARNING` · `ERROR` |
| `--debug` | — | Shorthand for `--log-level DEBUG` |
| `--clear` | — | Wipe saved preferences |
| `--version` / `-v` | — | Print version and exit |

Your preferences (theme, timezone, animation level, etc.) are saved automatically to `~/.claude-monitor/last_used.json` and restored on the next run. Pass any flag explicitly to override just for that session.

---

## 🔍 Keyword Analytics

Track exactly how much of your Claude budget went towards specific topics.

### Quick start

```bash
# Track a few topics right now
claude-monitor --keywords "unreal,python,git"
```

### Persistent keyword list

Create `~/.claude-monitor/keywords.txt` — one keyword per line, `#` for comments:

```
# My keyword list
unreal
blueprint
python
git
debugging
```

The CLI `--keywords` flag always overrides the file for that session.

### What the panel shows

Once keywords are configured a panel appears below the live display:

```
╭─ 🔍 Keyword Analytics ──────────────────────────────────────────────────╮
│  Keyword      Convos  Mentions    Tokens      Cost    % Cost  Bar        │
│  #unreal          12       143   842,301   $14.23     31.2%  ████████░░  │
│  #python           8        67   421,050    $7.88     17.3%  █████░░░░░  │
│  #git              5        31   187,200    $3.12      6.8%  ██░░░░░░░░  │
╰──────────────────────────────────────────────────────────────────────────╯
```

---

## 🎛️ Animation Levels

```bash
claude-monitor --animation subtle    # pulsing LIVE dot only (default)
claude-monitor --animation moderate  # LIVE dot + burn-rate sparkline
claude-monitor --animation full      # everything on
claude-monitor --animation none      # completely static
```

The setting is remembered between runs.

---

## 📊 Plan Reference

| Plan | Token Limit | Cost Limit | Best For |
|---|---|---|---|
| `custom` | P90 auto-detect | ~$50 | Default — adapts to your history |
| `pro` | ~19,000 | $18 | Claude Pro subscription |
| `max5` | ~88,000 | $35 | Claude Max5 subscription |
| `max20` | ~220,000 | $140 | Claude Max20 subscription |

The `custom` plan analyses the last 8 days of your sessions and uses the 90th-percentile token and cost values as your limits, so it adapts to how you actually work.

---

## 🖥️ Usage Views

```bash
claude-monitor --view realtime   # live monitor (default)
claude-monitor --view daily      # daily usage table
claude-monitor --view monthly    # monthly usage table
```

---

## 🌍 Common Examples

```bash
# US East Coast, dark theme, track Unreal work
claude-monitor --timezone America/New_York --theme dark --keywords "unreal,blueprint"

# Max5 plan with sparkline enabled
claude-monitor --plan max5 --animation moderate

# Daily usage summary
claude-monitor --view daily --timezone UTC

# Debug mode with log file
claude-monitor --debug --log-file ~/.claude-monitor/debug.log

# Reset all saved settings
claude-monitor --clear
```

---

## 🔧 How Sessions Work

Claude Code uses **5-hour rolling session windows**:

- A session starts with your first message and lasts exactly 5 hours
- Token and cost limits apply per session window
- You can have multiple overlapping sessions simultaneously
- The monitor tracks the active session and predicts when it will run out

---

## 🛠️ Development Setup

```bash
# Clone this fork
git clone https://github.com/wyattmcph/Claude-Code-Usage-Monitor-and-Analyze.git
cd Claude-Code-Usage-Monitor-and-Analyze

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest src/tests/ -q

# Run from source
python -m claude_monitor
```

---

## 🐛 Troubleshooting

**"externally-managed-environment" error on Linux**
Use `uv tool install claude-monitor` or `pipx install claude-monitor` instead of bare `pip`.

**`claude-monitor` command not found after pip install**
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

**No active session / no data showing**
Send at least one message in Claude Code first, then wait one refresh cycle (default 10 seconds).

**Keywords panel not appearing**
Make sure you've either created `~/.claude-monitor/keywords.txt` or passed `--keywords "..."`. The panel only shows when at least one keyword is configured.

---

## 📝 License

[MIT](LICENSE) — use and modify freely.

## 🙏 Credits

Built on top of the excellent original by [Maciek-roboblog](https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor). Extended with keyword analytics and visual improvements by [wyattmcph](https://github.com/wyattmcph).

---

<div align="center">

**⭐ Star this repo if you find it useful! ⭐**

[Report Bug](https://github.com/wyattmcph/Claude-Code-Usage-Monitor-and-Analyze/issues) · [Request Feature](https://github.com/wyattmcph/Claude-Code-Usage-Monitor-and-Analyze/issues)

</div>
