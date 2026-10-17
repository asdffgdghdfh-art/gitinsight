import pytest

from services.github_api import GitHubAPIError, GitHubClient, validate_username


class FakeResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.payload = payload
        self.headers = headers or {}

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, responses):
        self.headers = {}
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        return next(self.responses)


def test_validate_username():
    assert validate_username("octocat") == "octocat"
    assert validate_username(" oCtO-1 ") == "oCtO-1"
    for bad in ("", "abc--def", "-first", "last-", "x" * 40, "a/b"):
        with pytest.raises(GitHubAPIError):
            validate_username(bad)


def test_paginated_repositories():
    session = FakeSession([
        FakeResponse(payload=[{"name": "a"}, {"name": "b"}]),
        FakeResponse(payload=[{"name": "c"}]),
    ])
    client = GitHubClient(session=session)
    result = client.paginate("/users/octocat/repos", per_page=2)
    assert len(result) == 3
    assert [c[1]["page"] for c in session.calls] == [1, 2]


def test_user_not_found():
    client = GitHubClient(session=FakeSession([FakeResponse(404)]))
    with pytest.raises(GitHubAPIError, match="未找到"):
        client.user("missing")


def test_rate_limit_message():
    client = GitHubClient(session=FakeSession([
        FakeResponse(403, headers={"X-RateLimit-Remaining": "0"}),
    ]))
    with pytest.raises(GitHubAPIError, match="额度已用完"):
        client.user("octocat")
