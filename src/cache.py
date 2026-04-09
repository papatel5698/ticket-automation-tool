"""Local cache for analysis results to avoid re-analyzing unchanged issues."""

import json
import os
import hashlib
from dataclasses import asdict
from src.models import TicketAnalysis

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".cache")
CACHE_FILE = os.path.join(CACHE_DIR, "analysis_cache.json")


def _issue_cache_key(issue):
    """Generate a cache key based on issue number and content hash.

    Uses issue number, title, and body — but NOT updated_at.
    This avoids cache invalidation when the tool itself modifies an issue
    (e.g., adding a label updates updated_at on GitHub).
    The cache is still invalidated when the issue content changes.
    """
    content = f"{issue['number']}:{issue['title']}:{issue.get('body', '')}"
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
    return f"{issue['number']}_{content_hash}"


def load_cache():
    """Load the analysis cache from disk."""
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_cache(cache_data):
    """Save the analysis cache to disk."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache_data, f, indent=2)


def get_cached_analysis(issue):
    """Get a cached analysis for an issue, or None if not cached."""
    cache = load_cache()
    key = _issue_cache_key(issue)
    entry = cache.get(key)
    if entry is None:
        return None
    return TicketAnalysis(
        issue_number=entry["issue_number"],
        title=entry["title"],
        type=entry["type"],
        action=entry["action"],
        action_reasoning=entry["action_reasoning"],
        confidence=entry["confidence"],
        priority=entry["priority"],
        complexity=entry["complexity"],
        complexity_reasoning=entry["complexity_reasoning"],
        description=entry["description"],
    )


def cache_analysis(issue, analysis):
    """Cache an analysis result for an issue."""
    cache = load_cache()
    key = _issue_cache_key(issue)
    cache[key] = asdict(analysis)
    save_cache(cache)


def clear_cache():
    """Clear the entire analysis cache."""
    if os.path.exists(CACHE_FILE):
        os.remove(CACHE_FILE)
