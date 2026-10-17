from datetime import datetime, timezone

from analytics.health import evaluate

NOW = datetime(2026, 10, 18, tzinfo=timezone.utc)


def test_full_score():
    repo = {
        "description": "Well documented project",
        "license": {"spdx_id": "MIT"},
        "pushed_at": "2026-10-17T00:00:00Z",
    }
    paths = ["README.md", "requirements.txt", ".gitignore", "tests/test_api.py",
             ".github/workflows/tests.yml"]
    tree = {"tree": [{"path": p, "type": "blob"} for p in paths],
            "truncated": False}
    score = evaluate(repo, tree, now=NOW)
    assert score["score"] == 100
    assert len(score["checks"]) == 7
    assert score["truncated"] is False


def test_empty_repo_zero_score():
    score = evaluate({}, {"tree": []}, now=NOW)
    assert score["score"] == 0


def test_maintenance_decay_and_truncated():
    repo = {"pushed_at": "2026-04-01T00:00:00Z"}
    result = evaluate(repo, {"tree": [], "truncated": True}, now=NOW)
    assert result["score"] == 5
    assert result["truncated"] is True
