from datetime import datetime, timezone

from analytics.metrics import event_counts, filter_repositories, language_counts, summary


def repo(name, stars=0, language=None, fork=False, pushed_at="2026-10-16T00:00:00Z"):
    return {
        "name": name, "description": None, "stargazers_count": stars,
        "forks_count": 2, "language": language, "fork": fork,
        "pushed_at": pushed_at, "created_at": "2026-01-01T00:00:00Z",
    }


def test_aggregates_exclude_forks():
    repos = [repo("python-api", 5, "Python"), repo("forked", 99, "Go", True),
             repo("dashboard", 2, "Python")]
    data = summary(repos, [{"id": 1}])
    assert data == {
        "repositories": 2, "stars": 7, "forks": 4,
        "languages": 1, "events": 1, "top_repo": "python-api",
    }
    assert language_counts(repos) == {"Python": 2}


def test_no_repositories():
    assert summary([], [])["top_repo"] == "—"
    assert language_counts([]) == {}


def test_filter_and_sort():
    repos = [repo("first", 2, "Python"), repo("second", 7, "Go"),
             repo("forked", 10, "Python", True)]
    assert [r["name"] for r in filter_repositories(repos, language="Python")] == ["first"]
    assert [r["name"] for r in filter_repositories(repos, order="Star 数")] == [
        "second", "first"]
    assert len(filter_repositories(repos, include_forks=True)) == 3
    assert [r["name"] for r in filter_repositories(repos, search="SECOND")] == ["second"]


def test_event_counts_zero_fill_and_invalid():
    events = [
        {"created_at": "2026-10-16T01:00:00Z"},
        {"created_at": "2026-10-16T05:00:00Z"},
        {"created_at": "oops"},
        {"created_at": "2026-01-01T00:00:00Z"},
    ]
    counts = event_counts(events, days=3, today=datetime(2026, 10, 18, tzinfo=timezone.utc))
    assert counts == {"2026-10-16": 2, "2026-10-17": 0, "2026-10-18": 0}
