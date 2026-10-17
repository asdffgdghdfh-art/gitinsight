# ◈ GitInsight — GitHub Developer Analytics

**一个无需登录、基于真实 GitHub 公开数据的可视化开发者分析工具。**

GitInsight is a Python + Streamlit portfolio project. It is independent of GitHub Inc.

## Features

- 🔍 Search any public GitHub account.
- 📊 Dashboard with repositories, Stars, Forks, primary languages and recent public events.
- 📦 Search, filter, sort and open repository details.
- 🩺 Explainable repository health rubric for README, tests, CI and maintenance.
- 📄 Generate and download a Markdown portfolio report.
- 🔒 Optional GitHub token for higher API limits; no login required.

## Quick start

Requires Python 3.10+.

    git clone https://github.com/asdffgdghdfh-art/gitinsight.git
    cd gitinsight
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    streamlit run app.py

Open the local URL (usually http://localhost:8501).

Windows PowerShell activation: .venv\Scripts\Activate.ps1

Optional GitHub API token for higher request limits:

- On macOS/Linux, set environment variable GITHUB_TOKEN.
- Or create a private .streamlit/secrets.toml file with a GITHUB_TOKEN entry.
- **Never commit a real token!**

## Deploy to Streamlit Community Cloud

1. Connect your GitHub account at https://share.streamlit.io/.
2. Choose this repo, main branch, entry file app.py.
3. (Optional) Configure GITHUB_TOKEN in deployment secrets.
4. Deploy and add the app URL to your GitHub profile or resume.

## Source structure

    gitinsight/
    ├── app.py
    ├── services/github_api.py
    ├── analytics/metrics.py
    ├── analytics/health.py
    ├── reports/generator.py
    ├── tests/
    ├── .github/workflows/tests.yml
    ├── requirements.txt
    └── .streamlit/config.toml

## Data definitions and limits

| Metric | Definition |
| --- | --- |
| Public original repositories | Public repositories excluding forks |
| Stars / Forks | Sum on original public repositories (not stars a user has given) |
| Language distribution | Number of repositories by primary language, not code bytes |
| Public events | At most 300 recent public events from 30 days, **not commits** |
| Last pushed | GitHub's pushed_at value; not necessarily most recent authored commit |
| Health score | Rules based on files and metadata, **not code-quality measurement** |

The client paginates users' public repositories with a safety cap at 2,000. Requests are cached for 10 minutes, selected repo health for 15 minutes. Without authentication, REST API rate limits can be as low as 60 calls/hour per IP. GitHub's public events feed is not real time.

## Health rubric (100 points)

| Criterion | Points |
| --- | ---: |
| README present | 25 |
| Dependency manifest present (12) and .gitignore present (8) | 20 |
| Automated test files or directory | 20 |
| CI configuration | 15 |
| Pushed within 90 days (10) / within 365 days (5) | 10 |
| License | 5 |
| Repository description | 5 |

The health check reads a selected repository's Git tree and metadata via 2 API requests. If the Git tree is truncated, the interface warns about potentially missed files. Results are intentionally heuristic.

## Development and tests

    pip install -r requirements-dev.txt
    python -m pytest -q

GitHub Actions runs the test suite on pushes and pull requests.

## License

MIT.
