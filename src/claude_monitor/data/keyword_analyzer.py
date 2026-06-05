"""Keyword analytics for Claude Monitor.

Scans conversation JSONL files for user-defined keywords and aggregates
token usage and cost statistics per keyword.

Config file: ~/.claude-monitor/keywords.txt  (one keyword per line, # = comment)
CLI override: --keywords "unreal,python,git"

Performance note: file contents are cached by modification time so only
changed or new files are re-parsed on subsequent calls.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from claude_monitor.core.models import CostMode
from claude_monitor.core.pricing import PricingCalculator

logger = logging.getLogger(__name__)

_KEYWORDS_FILE = Path.home() / ".claude-monitor" / "keywords.txt"

_DEFAULT_KEYWORDS_CONTENT = """\
# Claude Monitor - keyword tracking list
# One keyword per line. Lines starting with # are comments.
# These defaults track common Claude Code development topics.
# Edit to match your projects and workflows.

python
javascript
typescript
debugging
refactor
test
git
api
database
documentation
"""


@dataclass
class KeywordStats:
    """Statistics for a single tracked keyword."""

    keyword: str
    conversation_count: int = 0
    mention_count: int = 0
    tokens: int = 0
    cost: float = 0.0
    pct_of_total_cost: float = 0.0
    pct_of_total_tokens: float = 0.0


# ── Config helpers ─────────────────────────────────────────────────────────────

def load_keywords(cli_keywords: Optional[str] = None) -> List[str]:
    """Return the active keyword list.

    Priority: CLI flag > config file > empty list.

    Args:
        cli_keywords: Comma-separated string from --keywords flag, or None.

    Returns:
        List of lowercase-stripped keyword strings.
    """
    if cli_keywords:
        return [k.strip().lower() for k in cli_keywords.split(",") if k.strip()]

    # Auto-create the file with defaults on first run
    ensure_keywords_file()

    if _KEYWORDS_FILE.exists():
        try:
            lines = _KEYWORDS_FILE.read_text(encoding="utf-8").splitlines()
            return [
                ln.strip().lower()
                for ln in lines
                if ln.strip() and not ln.startswith("#")
            ]
        except Exception as exc:
            logger.warning("Failed to read keywords file %s: %s", _KEYWORDS_FILE, exc)

    return []


def save_keywords(keywords: List[str]) -> None:
    """Persist a keyword list to the config file."""
    try:
        _KEYWORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        content = "# Claude Monitor - keyword tracking\n" + "\n".join(keywords) + "\n"
        _KEYWORDS_FILE.write_text(content, encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to save keywords to %s: %s", _KEYWORDS_FILE, exc)


def ensure_keywords_file() -> None:
    """Create a default keywords file if none exists."""
    if not _KEYWORDS_FILE.exists():
        try:
            _KEYWORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
            _KEYWORDS_FILE.write_text(_DEFAULT_KEYWORDS_CONTENT, encoding="utf-8")
        except Exception as exc:
            logger.debug("Could not create default keywords file: %s", exc)


# ── Analyzer ───────────────────────────────────────────────────────────────────

class KeywordAnalyzer:
    """Scan JSONL conversation files and produce per-keyword usage stats.

    File contents are cached by modification time. Only files that have
    changed since the last call are re-parsed, so repeated calls are fast
    even on large conversation histories.
    """

    def __init__(self, data_path: str) -> None:
        self.data_path = Path(data_path).expanduser()
        self._pricing  = PricingCalculator()
        # path -> (mtime, per-file session dict)
        self._file_cache: Dict[Path, Tuple[float, Dict]] = {}

    # ── Public API ─────────────────────────────────────────────────────────────

    def analyze(self, keywords: List[str]) -> List[KeywordStats]:
        """Return per-keyword stats across all conversations.

        Args:
            keywords: Keywords to search for (case-insensitive).

        Returns:
            List of KeywordStats sorted by cost descending.
        """
        if not keywords:
            return []

        sessions    = self._build_session_map()
        total_tokens = sum(s["tokens"] for s in sessions.values())
        total_cost   = sum(s["cost"]   for s in sessions.values())

        stats: List[KeywordStats] = []
        for kw in keywords:
            kw_lower = kw.lower()
            matching = [s for s in sessions.values() if kw_lower in s["text"]]
            if not matching:
                continue

            kw_tokens = sum(s["tokens"] for s in matching)
            kw_cost   = sum(s["cost"]   for s in matching)
            mentions  = sum(s["text"].count(kw_lower) for s in matching)

            stats.append(
                KeywordStats(
                    keyword=kw,
                    conversation_count=len(matching),
                    mention_count=mentions,
                    tokens=kw_tokens,
                    cost=kw_cost,
                    pct_of_total_cost=(
                        kw_cost / total_cost * 100 if total_cost > 0 else 0.0
                    ),
                    pct_of_total_tokens=(
                        kw_tokens / total_tokens * 100 if total_tokens > 0 else 0.0
                    ),
                )
            )

        return sorted(stats, key=lambda x: x.cost, reverse=True)

    # ── Session map (mtime-cached) ─────────────────────────────────────────────

    def _build_session_map(self) -> Dict[str, Dict]:
        """Merge per-file session caches into one map.

        For each JSONL file:
          - If the file is in the cache and its mtime hasn't changed, use the
            cached data directly.
          - Otherwise parse the file, cache the result, and use it.

        Deleted files are pruned from the cache automatically.
        """
        if not self.data_path.exists():
            return {}

        jsonl_files   = list(self.data_path.rglob("*.jsonl"))
        current_paths = set(jsonl_files)

        # Prune deleted files
        for removed in set(self._file_cache) - current_paths:
            del self._file_cache[removed]

        merged: Dict[str, Dict] = {}

        for file_path in jsonl_files:
            try:
                mtime = file_path.stat().st_mtime
            except OSError:
                continue

            cached = self._file_cache.get(file_path)
            if cached and cached[0] == mtime:
                file_sessions = cached[1]
            else:
                file_sessions: Dict[str, Dict] = {}
                self._parse_file(file_path, file_sessions)
                self._file_cache[file_path] = (mtime, file_sessions)

            # Merge this file's sessions into the global map
            for sid, sdata in file_sessions.items():
                if sid not in merged:
                    merged[sid] = {"text": "", "tokens": 0, "cost": 0.0}
                merged[sid]["text"]   += sdata["text"]
                merged[sid]["tokens"] += sdata["tokens"]
                merged[sid]["cost"]   += sdata["cost"]

        return merged

    def _parse_file(self, file_path: Path, sessions: Dict) -> None:
        """Parse one JSONL file into a caller-supplied sessions dict."""
        try:
            with open(file_path, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        self._process_entry(json.loads(line), sessions)
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.debug("Failed to read %s: %s", file_path, exc)

    # Legacy alias kept for any external callers
    def _process_file(self, file_path: Path, sessions: Dict) -> None:
        self._parse_file(file_path, sessions)

    def _process_entry(self, entry: Dict, sessions: Dict) -> None:
        """Process one JSON entry and update the sessions map."""
        session_id = entry.get("sessionId", "")
        if not session_id:
            return

        if session_id not in sessions:
            sessions[session_id] = {"text": "", "tokens": 0, "cost": 0.0}

        entry_type = entry.get("type", "")

        if entry_type == "user":
            text = self._extract_user_text(entry)
            if text:
                sessions[session_id]["text"] += " " + text.lower()

        elif entry_type == "assistant":
            msg = entry.get("message", {})
            if not isinstance(msg, dict):
                return

            usage = msg.get("usage", {})
            if not usage:
                return

            model: str  = msg.get("model", "unknown") or "unknown"
            input_t: int = usage.get("input_tokens", 0) or 0
            output_t: int = usage.get("output_tokens", 0) or 0
            cache_create: int = (
                usage.get("cache_creation_input_tokens", 0)
                or usage.get("cache_creation_tokens", 0)
                or 0
            )
            cache_read: int = (
                usage.get("cache_read_input_tokens", 0)
                or usage.get("cache_read_tokens", 0)
                or 0
            )

            sessions[session_id]["tokens"] += input_t + output_t

            try:
                cost = self._pricing.calculate_cost(
                    model=model,
                    input_tokens=input_t,
                    output_tokens=output_t,
                    cache_creation_tokens=cache_create,
                    cache_read_tokens=cache_read,
                )
                sessions[session_id]["cost"] += cost
            except Exception as exc:
                logger.debug("Cost calc failed for %s: %s", model, exc)

    @staticmethod
    def _extract_user_text(entry: Dict) -> str:
        """Pull plain text out of a user message entry."""
        msg = entry.get("message", {})
        if not isinstance(msg, dict):
            return ""

        content = msg.get("content", "")

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
            return " ".join(parts)

        return ""
