"""Aggregation functions: no network and no Streamlit dependencies."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone


def summary(repos: list[dict], events: list[dict] | None = None) -> dict:
    repos = [r for r in repos if not r.get("fork")]
    languages = {r.get("language") for r in repos if r.get("language")}
    return {
        "repositories": len(repos),
        "stars": sum(int(r.get("stargazers_count") or 0) for r in repos),
        "forks": sum(int(r.get("forks_count") or 0) for r in repos),
        "languages": len(languages),
        "events": len(events or []),
        "top_repo": max(repos, key=lambda r: r.get("stargazers_count") or 0)["name"]
        if repos else "—",
    }


def language_counts(repos: list[dict]) -> dict[str, int]:
    """Count repositories by PRIMARY language, excluding forks."""
    return dict(Counter(r["language"] for r in repos
                        if not r.get("fork") and r.get("language")))


def event_counts(events: list[dict], days: int = 30, today=None) -> dict[str, int]:
    """Count public events by UTC day; zero-fill absent days."""
    now = today or datetime.now(timezone.utc)
    end = now.date()
    start = end - timedelta(days=days - 1)
    counts = {(start + timedelta(days=i)).isoformat(): 0 for i in range(days)}
    for event in events:
        raw = event.get("created_at")
        if not raw:
            continue
        try:
            event_date = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(
                timezone.utc).date().isoformat()
        except (TypeError, ValueError):
            continue
        if event_date in counts:
            counts[event_date] += 1
    return counts


def top_repositories(repos: list[dict], n: int = 8) -> list[dict]:
    return sorted((r for r in repos if not r.get("fork")),
                  key=lambda r: (r.get("stargazers_count") or 0,
                                 r.get("forks_count") or 0), reverse=True)[:n]


def filter_repositories(
    repos: list[dict], search: str = "", language: str = "全部",
    include_forks: bool = False, order: str = "最近推送",
) -> list[dict]:
    items = [
        r for r in repos
        if (include_forks or not r.get("fork"))
        and (not search or search.lower() in (
            r.get("name", "") + " " + (r.get("description") or "")).lower())
        and (language == "全部" or r.get("language") == language)
    ]
    sorts = {
        "最近推送": lambda r: r.get("pushed_at") or "",
        "Star 数": lambda r: r.get("stargazers_count") or 0,
        "Fork 数": lambda r: r.get("forks_count") or 0,
        "创建时间": lambda r: r.get("created_at") or "",
    }
    return sorted(items, key=sorts.get(order, sorts["最近推送"]), reverse=True)
