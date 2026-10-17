"""Small, testable GitHub REST API client for public developer analytics."""
from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_ROOT = "https://api.github.com"
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")


@dataclass
class GitHubAPIError(Exception):
    message: str
    status_code: int | None = None

    def __str__(self) -> str:
        return self.message


def validate_username(username: str) -> str:
    username = username.strip()
    if not USERNAME_PATTERN.fullmatch(username) or "--" in username:
        raise GitHubAPIError("请输入有效的 GitHub 用户名（1–39 位字母、数字或连字符）。")
    return username


class GitHubClient:
    def __init__(self, token: str = "", session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "GitInsight/1.0",
        })
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        if session is None:
            retries = Retry(
                total=2, backoff_factor=0.6, status_forcelist=[500, 502, 503, 504],
                allowed_methods=["GET"],
            )
            self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def get(self, path: str, params: dict | None = None):
        try:
            response = self.session.get(f"{API_ROOT}{path}", params=params, timeout=12)
        except requests.RequestException as exc:
            raise GitHubAPIError("网络连接失败，请检查网络后重试。") from exc

        if response.status_code == 404:
            raise GitHubAPIError("未找到用户或仓库，可能不存在或不是公开资源。", 404)
        if response.status_code in (403, 429):
            limit = response.headers.get("X-RateLimit-Remaining")
            message = (
                "GitHub API 请求额度已用完，请稍后重试，或配置 GITHUB_TOKEN。"
                if limit == "0" or response.status_code == 429
                else "GitHub API 拒绝了请求，请稍后再试。"
            )
            raise GitHubAPIError(message, response.status_code)
        if not response.ok:
            raise GitHubAPIError(f"GitHub API 返回错误（HTTP {response.status_code}）。", response.status_code)
        try:
            return response.json()
        except ValueError as exc:
            raise GitHubAPIError("GitHub API 返回的数据格式不正确。") from exc

    def paginate(self, path: str, *, max_pages: int = 20, per_page: int = 100) -> list[dict]:
        output: list[dict] = []
        for page in range(1, max_pages + 1):
            batch = self.get(path, params={"page": page, "per_page": per_page})
            if not isinstance(batch, list):
                raise GitHubAPIError("GitHub API 分页返回格式不正确。")
            output.extend(batch)
            if len(batch) < per_page:
                break
        return output

    def user(self, username: str) -> dict:
        username = validate_username(username)
        return self.get(f"/users/{quote(username, safe='')}")

    def repositories(self, username: str) -> list[dict]:
        username = validate_username(username)
        # Public user repositories, capped at 2,000 to avoid excessive calls.
        return self.paginate(f"/users/{quote(username, safe='')}/repos",
                             max_pages=20)

    def public_events(self, username: str) -> list[dict]:
        username = validate_username(username)
        # GitHub only exposes up to 300 public events from the last 30 days.
        return self.paginate(f"/users/{quote(username, safe='')}/events/public",
                             max_pages=3)

    def repository(self, owner: str, name: str) -> dict:
        validate_username(owner)
        return self.get(f"/repos/{quote(owner, safe='')}/{quote(name, safe='')}")

    def tree(self, owner: str, name: str, ref: str) -> dict:
        validate_username(owner)
        return self.get(
            f"/repos/{quote(owner, safe='')}/{quote(name, safe='')}/git/trees/{quote(ref, safe='')}",
            params={"recursive": "1"},
        )
