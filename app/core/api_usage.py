"""
API usage tracker for job search providers.
Tracks daily/monthly call counts and enforces limits.
"""

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any

from app.core.config import DATA_DIR

logger = logging.getLogger(__name__)

USAGE_FILE = DATA_DIR / "api_usage.json"


def _load_usage() -> Dict[str, Any]:
    """Load usage data from file."""
    if USAGE_FILE.exists():
        try:
            return json.loads(USAGE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {"monthly_calls": 0, "month": "", "daily_searches": {}, "today": ""}


def _save_usage(data: Dict[str, Any]) -> None:
    """Save usage data to file."""
    USAGE_FILE.write_text(json.dumps(data, indent=2))


def _get_usage() -> Dict[str, Any]:
    """Get current usage, resetting counters if month/day has changed."""
    data = _load_usage()
    today = date.today().isoformat()
    current_month = date.today().strftime("%Y-%m")

    # Reset monthly counter if new month
    if data.get("month") != current_month:
        data["monthly_calls"] = 0
        data["month"] = current_month
        data["daily_searches"] = {}
        data["today"] = today
        _save_usage(data)

    # Reset daily searches if new day
    if data.get("today") != today:
        data["daily_searches"] = {}
        data["today"] = today
        _save_usage(data)

    return data


def get_usage_stats() -> Dict[str, Any]:
    """Get current API usage statistics."""
    data = _get_usage()
    from app.core.config import settings
    monthly_limit = settings.ADZUNA_MONTHLY_LIMIT

    return {
        "monthly_calls": data["monthly_calls"],
        "monthly_limit": monthly_limit,
        "remaining": max(0, monthly_limit - data["monthly_calls"]),
        "month": data.get("month", ""),
        "today": data.get("today", ""),
        "searches_today": len(data.get("daily_searches", {})),
        "quota_exhausted": data["monthly_calls"] >= monthly_limit,
    }


def can_search(keywords: str, provider: str = "adzuna") -> Dict[str, Any]:
    """
    Check if a search is allowed.

    Returns:
        Dict with 'allowed' (bool), 'reason' (str if not allowed),
        and 'duplicate' (bool if same search done today)
    """
    data = _get_usage()
    from app.core.config import settings
    monthly_limit = settings.ADZUNA_MONTHLY_LIMIT

    # Normalize the search key
    search_key = f"{provider}:{keywords.lower().strip()}"

    # Check if same search was done today
    if search_key in data.get("daily_searches", {}):
        return {
            "allowed": False,
            "reason": f"Already searched for '{keywords}' today. Try again tomorrow or use different keywords.",
            "duplicate": True,
        }

    # Check monthly quota
    if provider == "adzuna" and data["monthly_calls"] >= monthly_limit:
        return {
            "allowed": False,
            "reason": f"Monthly API limit reached ({monthly_limit} calls). Using fallback provider.",
            "duplicate": False,
            "use_fallback": True,
        }

    return {"allowed": True, "duplicate": False}


def record_search(keywords: str, provider: str = "adzuna", results_count: int = 0) -> None:
    """Record a successful API call."""
    data = _get_usage()
    today = date.today().isoformat()

    # Normalize
    search_key = f"{provider}:{keywords.lower().strip()}"

    # Increment monthly counter
    data["monthly_calls"] = data.get("monthly_calls", 0) + 1

    # Record daily search
    if "daily_searches" not in data:
        data["daily_searches"] = {}
    data["daily_searches"][search_key] = {
        "timestamp": datetime.now().isoformat(),
        "results": results_count,
    }

    data["today"] = today
    _save_usage(data)
    logger.info(f"Recorded API call: {provider} '{keywords}' -> {results_count} results (monthly total: {data['monthly_calls']})")
