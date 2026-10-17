"""GitInsight: explore public GitHub profiles, repos and project health."""
from __future__ import annotations

import html
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.health import evaluate
from analytics.metrics import event_counts, filter_repositories, language_counts, summary, top_repositories
from reports.generator import build_markdown
from services.github_api import GitHubAPIError, GitHubClient, validate_username

st.set_page_config(page_title="GitInsight · Developer Analytics", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.stApp {background:#0b111b;color:#e7edf7}
[data-testid="stSidebar"] {background:#111927;border-right:1px solid #253348}
h1,h2,h3 {letter-spacing:-.035em}
[data-testid="stMetric"] {background:#152132;border:1px solid #25354b;
                           padding:18px;border-radius:15px}
[data-testid="stMetricValue"] {color:#e5f6ff}
[data-testid="stMetricLabel"] {color:#90a9c6}
.gi-eyebrow {text-transform:uppercase;color:#61d5c8;font-size:.83rem;
             font-weight:700;letter-spacing:.16em}
.gi-title {font-size:2.6rem;font-weight:800;color:#eff8ff;line-height:1.2}
.gi-sub {color:#a5b8cd;margin-bottom:1.25rem}
.gi-banner {padding:16px 20px;border:1px solid #293951;border-radius:14px;
            background:linear-gradient(120deg,#142b3d,#142038)}
a {color:#68dbc9}
</style>
""", unsafe_allow_html=True)


def get_token() -> str:
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        return token
    try:
        return st.secrets.get("GITHUB_TOKEN", "")
    except (FileNotFoundError, KeyError):
        return ""


@st.cache_data(ttl=600, show_spinner=False)
def load_public_data(username: str, _token: str) -> dict:
    client = GitHubClient(_token)
    profile = client.user(username)
    repos = client.repositories(username)
    warnings = []
    try:
        events = client.public_events(username)
    except GitHubAPIError as exc:
        events = []
        warnings.append(f"公开活动获取失败：{exc}")
    if len(repos) >= 2000:
        warnings.append("已达到 2000 个公开仓库的采集上限，统计结果可能不完整。")
    return {"profile": profile, "repos": repos, "events": events, "warnings": warnings}


@st.cache_data(ttl=900, show_spinner=False)
def load_health(owner: str, name: str, ref: str, _token: str) -> dict:
    client = GitHubClient(_token)
    repo = client.repository(owner, name)
    tree = client.tree(owner, name, ref)
    return evaluate(repo, tree)


def chart_style(fig, height: int = 340):
    fig.update_layout(paper_bgcolor="#142031", plot_bgcolor="#142031",
                      font_color="#cad8e7", margin=dict(l=16, r=18, t=30, b=20),
                      height=height, legend_title_text="")
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(gridcolor="#26364c", zeroline=False)
    return fig


def render_overview(repos: list[dict], events: list[dict]):
    info = summary(repos, events)
    st.markdown("### 开发者概览")
    cols = st.columns(5)
    labels = [("公开原创仓库", info["repositories"]), ("累计 Stars", info["stars"]),
              ("累计 Forks", info["forks"]), ("主要编程语言", info["languages"]),
              ("近期公开事件", info["events"])]
    for col, (label, val) in zip(cols, labels):
        col.metric(label, f"{val:,}")
    st.caption("Stars / Forks 统计排除 Fork 仓库；公开事件不是提交次数。")

    left, right = st.columns([1, 1.25])
    languages = language_counts(repos)
    with left:
        st.markdown("#### 编程语言分布")
        if languages:
            frame = pd.DataFrame([{"语言": k, "仓库数": v} for k, v in languages.items()])
            fig = px.pie(frame, values="仓库数", names="语言", hole=.67,
                         color_discrete_sequence=px.colors.qualitative.Set3)
            fig.update_traces(textinfo="percent+label", textposition="outside")
            st.plotly_chart(chart_style(fig), use_container_width=True)
            st.caption("按非 Fork 仓库的主要语言计数，而非代码行数。")
        else:
            st.info("尚无可统计的编程语言。")
    with right:
        st.markdown("#### 过去 30 天公开活动")
        activity = event_counts(events)
        frame = pd.DataFrame({"日期": list(activity), "事件数": list(activity.values())})
        fig = px.bar(frame, x="日期", y="事件数", color_discrete_sequence=["#58d6c2"])
        fig.update_traces(hovertemplate="%{x}<br>公开事件：%{y}<extra></extra>")
        st.plotly_chart(chart_style(fig), use_container_width=True)
        st.caption("GitHub 最近 30 天最多 300 条公开事件，存在数据延迟。")
    st.markdown("#### ⭐ 热门项目")
    leaders = top_repositories(repos, 8)
    if leaders:
        frame = pd.DataFrame([{"仓库": r.get("name"), "Stars": r.get("stargazers_count", 0),
                               "Forks": r.get("forks_count", 0)} for r in leaders])
        fig = px.bar(frame.sort_values("Stars"), x="Stars", y="仓库", orientation="h",
                     hover_data=["Forks"], color_discrete_sequence=["#689bff"])
        st.plotly_chart(chart_style(fig, max(270, len(frame)*46)), use_container_width=True)
    else:
        st.info("该用户没有公开原创仓库。")


def render_repositories(repos: list[dict]):
    st.markdown("### 仓库浏览")
    a, b, c, d = st.columns([2.2, 1.1, 1.2, 1.1])
    with a:
        keyword = st.text_input("搜索名称或描述", placeholder="例如：Python / dashboard")
    with b:
        options = ["全部"] + sorted({r["language"] for r in repos if r.get("language")})
        language = st.selectbox("编程语言", options)
    with c:
        order = st.selectbox("排序", ["最近推送", "Star 数", "Fork 数", "创建时间"])
    with d:
        forks = st.toggle("包含 Fork 仓库", value=False)
    filtered = filter_repositories(repos, keyword, language, forks, order)
    st.caption(f"显示 {len(filtered)} / {len(repos)} 个公开仓库")
    if not filtered:
        st.info("暂无符合筛选条件的仓库。")
        return
    rows = [{
        "仓库": r.get("name", ""), "说明": r.get("description") or "—",
        "语言": r.get("language") or "—", "Stars": r.get("stargazers_count") or 0,
        "Forks": r.get("forks_count") or 0, "最近推送": (r.get("pushed_at") or "")[:10] or "—",
        "Fork?": "是" if r.get("fork") else "否", "链接": r.get("html_url", ""),
    } for r in filtered]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,
                 column_config={"链接": st.column_config.LinkColumn("GitHub 仓库")},
                 height=min(610, 64 + len(rows) * 36))


def render_health(username: str, repos: list[dict], token: str):
    st.markdown("### 项目健康度检查")
    st.caption("检查 README、依赖、测试、CI、维护与元数据；规则评分不等于代码质量。")
    if not repos:
        st.info("该账号没有公开仓库。")
        return
    repo_by_name = {r["name"]: r for r in repos}
    selection = st.selectbox("选择仓库", sorted(repo_by_name))
    repo = repo_by_name[selection]
    key = repo.get("full_name", f"{username}/{selection}")
    if "health_results" not in st.session_state:
        st.session_state.health_results = {}
    if st.button("🔍 分析工程健康度", type="primary"):
        with st.spinner("读取公开仓库文件结构..."):
            try:
                result = load_health(username, selection,
                                     repo.get("default_branch") or "main", token)
                st.session_state.health_results[key] = result
            except GitHubAPIError as exc:
                st.error(str(exc))
    result = st.session_state.health_results.get(key)
    if not result:
        st.info("点击分析按钮。每个仓库通常需要额外 2 次 GitHub API 请求。")
        return
    st.metric("工程健康度（规则评分）", f"{result['score']} / 100")
    st.progress(result["score"] / 100)
    if result["truncated"]:
        st.warning("GitHub 返回的文件树不完整，检查结果可能低估实际情况。")
    st.caption(f"已扫描 {result['files_checked']} 个文件条目。")
    for check in result["checks"]:
        a, b = st.columns([3, 1])
        with a:
            st.markdown(f"**{'✅' if check['pass'] else '⚠️'} {check['name']}**")
            if not check["pass"]:
                st.caption(check["tip"])
        with b:
            st.write(f"{check['score']} / {check['max']} 分")
        st.divider()


def render_reports(profile: dict, repos: list[dict], events: list[dict]):
    st.markdown("### 作品集报告")
    st.write("生成一份适合放入项目文档或个人作品集的 Markdown 报告。")
    st.caption("报告仅使用公开数据，以及本次会话已检查的仓库健康度。")
    report = build_markdown(profile, repos, events, st.session_state.get("health_results", {}))
    st.download_button("⬇️ 下载 Markdown 报告", report,
                       file_name=f"gitinsight-{profile.get('login', 'developer')}.md",
                       mime="text/markdown", type="primary")
    with st.expander("预览报告内容", expanded=True):
        st.markdown(report)


def main():
    token = get_token()
    with st.sidebar:
        st.markdown("## ◈ GitInsight")
        st.caption("DEVELOPER ANALYTICS · V1.0")
        default_username = st.query_params.get("user", "asdffgdghdfh-art")
        with st.form("lookup"):
            username_input = st.text_input(
                "GitHub 用户名", value=st.session_state.get("username", default_username),
                placeholder="例如：octocat")
            submitted = st.form_submit_button("分析用户 →", use_container_width=True)
        if submitted:
            try:
                st.session_state.username = validate_username(username_input)
                st.query_params["user"] = st.session_state.username
            except GitHubAPIError as exc:
                st.error(str(exc))
                st.stop()
        username = st.session_state.get("username", default_username)
        page = st.radio("分析工作台",
                        ["📊 数据总览", "📦 仓库浏览", "🩺 项目健康度", "📄 作品集报告"])
        st.divider()
        st.caption("🔒 公开查询无需登录；可选 GITHUB_TOKEN 提高 API 限额。")
        if st.button("刷新数据缓存", use_container_width=True):
            load_public_data.clear()
            load_health.clear()
            st.rerun()
        st.caption("GitHub REST API · Streamlit · Plotly")

    st.markdown('<div class="gi-eyebrow">Explore • Analyze • Improve</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="gi-title">GitInsight</div>', unsafe_allow_html=True)
    st.markdown('<p class="gi-sub">用数据理解每一位开发者的公开 GitHub 项目。</p>',
                unsafe_allow_html=True)
    try:
        username = validate_username(username)
        with st.spinner(f"正在分析 @{username} 的公开资料..."):
            data = load_public_data(username, token)
    except GitHubAPIError as exc:
        st.error(str(exc))
        st.info("检查用户名是否正确，或稍后重试。")
        st.stop()
    profile, repos, events = data["profile"], data["repos"], data["events"]
    safe_name = html.escape(profile.get("name") or profile.get("login") or username)
    safe_login = html.escape(profile.get("login") or username)
    st.markdown(
        f'<div class="gi-banner"><b>👤 {safe_name}</b> · '
        f'<a href="https://github.com/{safe_login}" target="_blank" rel="noopener">'
        f'@{safe_login}</a>　|　{len(repos)} 个公开仓库（含 Fork）</div>',
        unsafe_allow_html=True,
    )
    st.write("")
    for warning in data["warnings"]:
        st.warning(warning)
    if page.startswith("📊"):
        render_overview(repos, events)
    elif page.startswith("📦"):
        render_repositories(repos)
    elif page.startswith("🩺"):
        render_health(username, repos, token)
    else:
        render_reports(profile, repos, events)
    st.divider()
    st.caption("GitInsight · 基于公开 GitHub API · 非 GitHub 官方产品。")


if __name__ == "__main__":
    main()
