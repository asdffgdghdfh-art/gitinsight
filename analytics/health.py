"""Explainable repository health heuristic (not a code quality grade)."""
from __future__ import annotations

from datetime import datetime, timezone

MANIFESTS = {
    "requirements.txt", "pyproject.toml", "Pipfile", "poetry.lock",
    "package.json", "pnpm-lock.yaml", "yarn.lock", "go.mod", "Cargo.toml",
    "pom.xml", "build.gradle", "Gemfile", "composer.json",
}


def evaluate(repo: dict, tree: dict, now: datetime | None = None) -> dict:
    paths = {entry["path"] for entry in tree.get("tree", [])
             if entry.get("type") == "blob" and entry.get("path")}
    lower = {p.lower() for p in paths}
    now = now or datetime.now(timezone.utc)

    def has_prefix(*prefixes):
        return any(any(p.startswith(prefix) for prefix in prefixes) for p in lower)

    readmes = [p for p in lower if p == "readme.md" or p.startswith("readme.")]
    has_readme = bool(readmes)
    has_manifest = any(p in paths for p in MANIFESTS) or any(
        p.lower() in {m.lower() for m in MANIFESTS} for p in paths)
    has_gitignore = ".gitignore" in lower
    has_tests = has_prefix("tests/", "test/", "__tests__/") or any(
        p.endswith("_test.py") or p.startswith("test_") or p.endswith(".test.js")
        or p.endswith(".spec.ts") or p.endswith(".test.ts") for p in lower)
    has_ci = has_prefix(".github/workflows/") or ".gitlab-ci.yml" in lower
    has_license = bool(repo.get("license")) or any(
        p in lower for p in ("license", "license.md", "license.txt"))
    has_description = bool((repo.get("description") or "").strip())

    pushed = repo.get("pushed_at")
    days_since_push = None
    if pushed:
        try:
            pushed_date = datetime.fromisoformat(pushed.replace("Z", "+00:00"))
            days_since_push = max(0, (now - pushed_date).days)
        except (TypeError, ValueError):
            pass

    maintenance_score = 10 if days_since_push is not None and days_since_push <= 90 else (
        5 if days_since_push is not None and days_since_push <= 365 else 0)
    checks = [
        {"name": "README 文档", "score": 25 if has_readme else 0,
         "max": 25, "pass": has_readme, "tip": "添加项目介绍、安装说明和使用示例。"},
        {"name": "依赖与项目规范", "score": (12 if has_manifest else 0) + (8 if has_gitignore else 0),
         "max": 20, "pass": has_manifest and has_gitignore,
         "tip": "添加依赖清单（如 requirements.txt）和 .gitignore。"},
        {"name": "自动化测试", "score": 20 if has_tests else 0,
         "max": 20, "pass": has_tests, "tip": "添加 tests/ 目录并编写测试。"},
        {"name": "CI 工作流", "score": 15 if has_ci else 0,
         "max": 15, "pass": has_ci, "tip": "增加 .github/workflows/ 测试流程。"},
        {"name": "近期维护", "score": maintenance_score,
         "max": 10, "pass": maintenance_score == 10,
         "tip": "持续提交有价值的修复，维护项目。"},
        {"name": "License", "score": 5 if has_license else 0,
         "max": 5, "pass": has_license, "tip": "按需添加开源许可证。"},
        {"name": "项目描述", "score": 5 if has_description else 0,
         "max": 5, "pass": has_description, "tip": "为仓库补充准确的简短描述。"},
    ]
    return {
        "score": sum(c["score"] for c in checks),
        "checks": checks,
        "truncated": bool(tree.get("truncated")),
        "files_checked": len(paths),
    }
