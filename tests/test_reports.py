from reports.generator import build_markdown


def test_markdown_report_contains_real_metrics():
    profile = {"login": "dev", "name": "Tester"}
    repos = [{"name": "demo", "fork": False, "stargazers_count": 3,
              "forks_count": 1, "language": "Python",
              "html_url": "https://github.com/dev/demo"}]
    report = build_markdown(profile, repos, [{"id": "event"}])
    assert "Tester" in report
    assert "仓库获赞总数：3" in report
    assert "[demo](https://github.com/dev/demo)" in report
    assert "并非提交次数" in report
