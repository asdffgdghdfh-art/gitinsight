# ◈ GitInsight — GitHub Developer Analytics

## ✨ New: Editorial Homepage + Interactive Web Dashboard

GitInsight now includes a responsive, framework-free web frontend inspired by warm editorial portfolio design and a pastel modular analytics dashboard:

- `index.html` — cream-colored portfolio landing page with a live dashboard entry point.
- `dashboard.html` — dark sidebar + colorful analytics cards, repo explorer, rule-based health checks, Markdown exports.
- `assets/style.css` — responsive desktop/mobile styling.
- `assets/dashboard.js` — GitHub public REST API integration, filtering, charts, caching, error handling; no token needed.

**Run web frontend locally:** from the repository root run `python3 -m http.server 8502` and open `http://localhost:8502/index.html` (dashboard at `/dashboard.html`). Works on static hosting such as GitHub Pages once Pages is enabled. The dashboard displays live public GitHub data; it does **not** fabricate summary metrics. Unauthenticated GitHub API requests have strict rate limits. No secrets are embedded in the frontend.

The existing Streamlit/Python backend is still present and available with `streamlit run app.py`.

---


## GitInsight V2.1 — refreshed visual workspace

The web experience now includes a cream editorial landing page (`index.html`) and a soft modular dashboard (`dashboard.html`) inspired by pastel product UI cards.

- Dark, compact sidebar and four data-derived overview cards (repositories / Stars / Forks / primary languages).
- Clean activity graph and developer panel. Decorative ring motifs are intentionally *not* presented as data trends.
- New responsive mobile bottom navigation, larger tap targets, and a one-tap sharing link.
- Keyboard-reachable activity bars, focus states, skeleton loading, reduced-motion support and no required web-font CDN.
- The analytics are based on GitHub's public REST API. Project health checks and Markdown exports remain functional.

**Preview locally:** From the repository folder, run `python3 -m http.server 8000` and open `http://localhost:8000/index.html` or `http://localhost:8000/dashboard.html`. The frontend needs no build tools and should be served over HTTP; direct `file://` opening may impose browser restrictions.

**Testing:** The V2.1 browser UI was exercised using Playwright/Chromium with mocked API responses for desktop and mobile (four metrics, navigation, health check, report generation). Mock values belong to tests/screenshots only, **not** production data.

---

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
