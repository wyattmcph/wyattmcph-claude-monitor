"""Infer Claude plan from historical session data.

Looks at the maximum tokens used in completed sessions and compares
against known plan limits.  If a user has ever had a session near a
plan's token ceiling, that plan is the most likely candidate.

Returns None when there is not enough data to be confident.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Known token limits per plan (approximate upper bound of a full session)
_LIMITS: List[tuple[int, str]] = [
    (220_000, "max20"),
    (88_000,  "max5"),
    (19_000,  "pro"),
]

# A session must have reached this fraction of the limit to count as evidence
_CONFIDENCE = 0.75


def detect_plan_from_history(blocks: List[Dict[str, Any]]) -> Optional[str]:
    """Return the most likely plan name, or None if undetermined.

    Args:
        blocks: List of session block dicts from the usage data.
                Each block should have ``totalTokens``, ``isGap``, and
                optionally ``isActive``.

    Returns:
        ``'pro'``, ``'max5'``, ``'max20'``, or ``None``.
    """
    if not blocks:
        return None

    completed_tokens = [
        b.get("totalTokens", 0)
        for b in blocks
        if isinstance(b, dict)
        and not b.get("isGap", False)
        and not b.get("isActive", False)
        and b.get("totalTokens", 0) > 0
    ]

    if not completed_tokens:
        return None

    max_tokens = max(completed_tokens)
    logger.debug("Plan detection: max session tokens = %d", max_tokens)

    for limit, plan in _LIMITS:
        if max_tokens >= limit * _CONFIDENCE:
            logger.debug("Detected plan: %s (limit %d, max %d)", plan, limit, max_tokens)
            return plan

    # Insufficient usage to distinguish plans
    return None


def suggest_plan(blocks: List[Dict[str, Any]], current_plan: str) -> Optional[str]:
    """Return a suggested plan if detection disagrees with the current one.

    Args:
        blocks:       Historical session blocks.
        current_plan: The plan currently configured.

    Returns:
        Suggested plan name, or None if no change recommended.
    """
    detected = detect_plan_from_history(blocks)
    if detected and detected != current_plan:
        return detected
    return None
