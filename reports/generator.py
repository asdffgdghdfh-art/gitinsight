"""Export public GitHub analytics into a self-contained Markdown report."""
from __future__ import annotations

from datetime import datetime, timezone

from analytics.metrics import language_counts, summary, top_repositories


def build_markdown(profile: dict, repos: list[dict], events: list[dict],
                   health: dict | None = None) -> str:
    metrics = summary(repos, events)
    username = profile.get("login", "unknown")
    name = (profile.get("name") or username).replace("\n", " ")
    languages = language_counts(repos)
    lines = [
        f"# GitInsight 开发者报告：{name}",
        "",
        f"> GitHub: https://github.com/{username}",
        f"> 生成时间（UTC）：{datetime.now(timezone.utc):%Y-%m-%d %H:%M}",
        "",
        "## 公开数据总览",
        "",
        f"- 非 Fork 公开仓库：{metrics['repositories']}",
        f"- 仓库获赞总数：{metrics['stars']}",
        f"- 仓库 Fork 总数：{metrics['forks']}",
        f"- 主要编程语言数量：{metrics['languages']}",
        f"- 最近公开事件（可获取部分）：{metrics['events']}",
        "",
        "## 编程语言（按仓库主要语言统计）",
        "",
    ]
    if languages:
        lines.extend(f"- {lang}: {count} 个仓库" for lang, count in
                     sorted(languages.items(), key=lambda item: -item[1]))
    else:
        lines.append("暂无可统计的编程语言。")
    lines += ["", "## 代表仓库", "",
              "| 仓库 | Stars | Forks | 主要语言 |",
              "| --- | ---: | ---: | --- |"]
    for repo in top_repositories(repos, 10):
        repo_name = repo.get("name", "unknown").replace("|", "\\|")
        lines.append(
            f"| [{repo_name}]({repo.get('html_url', '')}) | "
            f"{repo.get('stargazers_count', 0)} | "
            f"{repo.get('forks_count', 0)} | {repo.get('language') or '—'} |")
    if health:
        lines += ["", "## 最近检查的仓库健康度", ""]
        for full_name, result in health.items():
            lines.append(f"- {full_name}: {result['score']}/100（规则评分）")
    lines += [
        "",
        "---",
        "说明：仅基于公开数据；事件接口最多提供最近 30 天的 300 条公开事件。",
        "活动事件数量并非提交次数；健康度是规则检查，并非代码质量评价。",
    ]
    return "\n".join(lines) + "\n"
