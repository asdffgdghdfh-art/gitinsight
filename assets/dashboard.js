/* GitInsight Web — no external frontend framework, no private data or API keys. */
(() => {
  'use strict';
  const API = 'https://api.github.com';
  const palette = ['#afa9f0', '#f8d26b', '#bacbb5', '#e5b79b', '#8caab3', '#d4c6aa', '#8f96ca'];
  const $ = (id) => document.getElementById(id);
  const state = { profile: null, repos: [], events: [], user: '', health: {}, active: 'overview', pending: false };
  const html = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const humanNumber = (number) => new Intl.NumberFormat('zh-CN').format(number || 0);
  const usernameValid = value => /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$/.test(value) && !value.includes('--');
  const header = { Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' };
  const colors = { Python:'#3776ab',JavaScript:'#e9d46d',TypeScript:'#8f9ee5',HTML:'#de997b',CSS:'#a5a1d7',Java:'#bd8e80',Go:'#96bed4',Rust:'#b38e74',Vue:'#78b596',Shell:'#8baf90' };
  let pendingFetch = null;

  function status(message, error = false) {
    const el = $('status-message'); el.textContent = message || ''; el.classList.toggle('error', error);
  }
  function clearForLoading() {
    ['stat-repos', 'stat-stars', 'stat-forks', 'activity-total', 'lang-number'].forEach(id => $(id).textContent = '—');
    $('featured-repos').innerHTML = '<p class="loading-row">正在加载公开仓库…</p>';
    $('recent-events').innerHTML = '<p class="loading-row">正在获取公开活动…</p>';
    $('repository-list').innerHTML = '<p class="loading-row">正在获取仓库…</p>';
    $('activity-chart').innerHTML = '';
  }
  async function get(path, signal) {
    let res;
    try { res = await fetch(`${API}${path}`, { headers: header, signal }); }
    catch (e) { if (e.name === 'AbortError') throw e; throw new Error('无法连接 GitHub，请检查网络或稍后重试。'); }
    if (res.status === 404) throw new Error('找不到这个公开用户或仓库。');
    if (res.status === 403 || res.status === 429) {
      const limited = res.headers.get('X-RateLimit-Remaining') === '0' || res.status === 429;
      throw new Error(limited ? 'GitHub API 请求额度已用完，请稍后再试。' : 'GitHub 暂时拒绝请求，请稍后再试。');
    }
    if (!res.ok) throw new Error(`GitHub API 请求失败（HTTP ${res.status}）。`);
    return res.json();
  }
  async function allRepos(user, signal) {
    const out = [];
    for (let page = 1; page <= 20; page++) {
      const batch = await get(`/users/${encodeURIComponent(user)}/repos?per_page=100&page=${page}&type=owner&sort=updated`, signal);
      if (!Array.isArray(batch)) throw new Error('GitHub 返回的仓库列表格式有误。');
      out.push(...batch);
      if (batch.length < 100) break;
    }
    return out;
  }
  function fromCache(user) {
    try {
      const item = JSON.parse(sessionStorage.getItem(`gi-v2:${user.toLowerCase()}`));
      if (item && Date.now() - item.at < 10 * 60 * 1000) return item.value;
    } catch { /* privacy mode disables storage */ }
    return null;
  }
  function intoCache(user, value) {
    try { sessionStorage.setItem(`gi-v2:${user.toLowerCase()}`, JSON.stringify({ at: Date.now(), value })); }
    catch { /* no persistent storage required */ }
  }
  async function loadUser(user, useCache = true) {
    if (!usernameValid(user)) { status('请输入有效的 GitHub 用户名（1–39 位字母、数字或连字符）。', true); return; }
    if (pendingFetch) pendingFetch.abort();
    pendingFetch = new AbortController();
    const signal = pendingFetch.signal;
    state.pending = true; $('search-form').querySelector('button').disabled = true;
    $('username-input').value = user;
    clearForLoading(); status(`正在获取 @${user} 的公开数据…`);
    try {
      const cached = useCache ? fromCache(user) : null;
      const profile = cached ? cached.profile : await get(`/users/${encodeURIComponent(user)}`, signal);
      const repos = cached ? cached.repos : await allRepos(user, signal);
      let events = cached ? cached.events : [];
      let warning = '';
      if (!cached) {
        try {
          const eventBatch = await get(`/users/${encodeURIComponent(user)}/events/public?per_page=100&page=1`, signal);
          if (Array.isArray(eventBatch)) {
            events = eventBatch;
            if (eventBatch.length === 100) {
              for (let page = 2; page <= 3; page++) {
                const more = await get(`/users/${encodeURIComponent(user)}/events/public?per_page=100&page=${page}`, signal);
                if (!Array.isArray(more)) break;
                events.push(...more);
                if (more.length < 100) break;
              }
            }
          }
        } catch (e) {
          if (e.name === 'AbortError') throw e;
          warning = `公开活动暂不可用：${e.message}`;
        }
        intoCache(user, { profile, repos, events });
      }
      if (signal.aborted) return;
      state.profile = profile; state.repos = repos; state.events = events; state.user = user;
      state.health = {}; // scores from a different developer must never leak into this report
      $('search-form').querySelector('button').disabled = false;
      $('sidebar-user').textContent = profile.name || profile.login;
      $('profile-name').textContent = profile.name || profile.login;
      $('profile-link').textContent = '@' + profile.login;
      $('profile-link').href = `https://github.com/${encodeURIComponent(profile.login)}`;
      $('sidebar-avatar').src = profile.avatar_url || 'https://github.com/identicons/gitinsight.png';
      $('profile-avatar').src = profile.avatar_url || 'https://github.com/identicons/gitinsight.png';
      $('profile-bio').textContent = profile.bio || '正在用开源项目记录自己的开发旅程。';
      $('profile-location').textContent = 'LOCATION · ' + (profile.location || '—');
      $('profile-followers').textContent = 'FOLLOWERS · ' + humanNumber(profile.followers);
      renderEverything();
      status(warning || `✓ 已加载 @${profile.login} 的公开数据`);
      if (repos.length >= 2000) status('已采集前 2000 个公开仓库，统计可能不完整。', true);
      const url = new URL(location.href); url.searchParams.set('user', profile.login);
      history.replaceState({}, '', url);
    } catch (e) {
      if (e.name !== 'AbortError') status(e.message, true);
    } finally {
      if (pendingFetch?.signal === signal) {
        state.pending = false; $('search-form').querySelector('button').disabled = false;
      }
    }
  }

  function originalRepos() { return state.repos.filter(r => !r.fork); }
  function totals() {
    const rs = originalRepos();
    return { repos: rs.length, stars: rs.reduce((v,r) => v + (r.stargazers_count || 0),0),
      forks: rs.reduce((v,r) => v + (r.forks_count || 0),0) };
  }
  function langCounts() {
    const m = new Map();
    for (const repo of originalRepos()) if (repo.language) m.set(repo.language, (m.get(repo.language) || 0) + 1);
    return [...m].sort((a,b) => b[1] - a[1]);
  }
  function recentDays() {
    const days = [];
    const today = new Date();
    for (let x = 13; x >= 0; x--) {
      const day = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(),today.getUTCDate() - x));
      const key = day.toISOString().slice(0,10);
      days.push({ key, label: `${day.getUTCMonth()+1}/${day.getUTCDate()}`,count:0 });
    }
    const byDay = Object.fromEntries(days.map(d => [d.key,d]));
    for (const event of state.events) {
      const key = (event.created_at || '').slice(0,10);
      if (byDay[key]) byDay[key].count++;
    }
    return days;
  }
  function renderOverview() {
    const t = totals();
    $('stat-repos').textContent = humanNumber(t.repos);
    $('stat-stars').textContent = humanNumber(t.stars);
    $('stat-forks').textContent = humanNumber(t.forks);
    $('activity-total').textContent = humanNumber(state.events.length);
    const days = recentDays(); const max = Math.max(...days.map(d=>d.count),1);
    $('activity-chart').innerHTML = days.map((d,ix) => `<div class="bar-item" title="${d.key}: ${d.count} 个公开事件"><div class="bar-base"></div><div class="bar-fill" style="height:${d.count ? Math.max(5,Math.round(d.count/max*98)) : 1}%"></div><span class="bar-label">${ix%2===0?d.label:''}</span><span class="bar-tip">${d.count} events</span></div>`).join('');
    const ranked = originalRepos().slice().sort((a,b) => (b.stargazers_count||0) - (a.stargazers_count||0) || (b.pushed_at||'').localeCompare(a.pushed_at||'')).slice(0,4);
    $('featured-repos').innerHTML = ranked.length ? ranked.map(r => `<div class="feature-repo"><div><a href="${html(r.html_url)}" target="_blank" rel="noopener noreferrer">${html(r.name)}</a><p>${html(r.description || r.language || '暂无项目简介')}</p></div><span class="repo-stat">★ ${humanNumber(r.stargazers_count)}</span><span class="repo-stat">⑂ ${humanNumber(r.forks_count)}</span><span class="repo-arrow">↗</span></div>`).join('') : '<div class="empty-message">没有可展示的公开原创仓库。</div>';
  }
  function renderLanguages() {
    const langs = langCounts();
    const n = langs.reduce((a,b) => a+b[1],0); $('lang-number').textContent = langs.length;
    const first = langs.slice(0,6), remaining = langs.slice(6).reduce((v,x)=>v+x[1],0);
    if (remaining) first.push(['其他', remaining]);
    let offset=0; const gradient = [];
    for (let ix=0;ix<first.length;ix++) {
      const fraction = n ? first[ix][1]/n*100 : 0;
      gradient.push(`${palette[ix%palette.length]} ${offset.toFixed(2)}% ${(offset+fraction).toFixed(2)}%`); offset+=fraction;
    }
    $('language-donut').style.background = gradient.length ? `conic-gradient(${gradient.join(',')})` : '#ecece6';
    $('language-legend').innerHTML = first.length ? first.map(([name,count],ix) => `<div class="legend-line"><span class="legend-dot" style="background:${palette[ix%palette.length]}"></span><span>${html(name)}</span><strong>${(count/n*100).toFixed(1)}%</strong></div>`).join('') : '<p class="empty-message">尚无语言数据</p>';
  }
  function eventTitle(type) {
    const types = {PushEvent:'代码推送',WatchEvent:'收藏仓库',ForkEvent:'派生仓库',PullRequestEvent:'Pull Request',IssuesEvent:'Issue',CreateEvent:'创建分支/标签',ReleaseEvent:'发布版本',IssueCommentEvent:'Issue 评论',PullRequestReviewEvent:'代码审查'};
    return types[type] || (type ? type.replace(/Event$/, '') : '公开活动');
  }
  function renderEvents() {
    const events = state.events.slice(0,4);
    $('recent-events').innerHTML = events.length ? events.map(e => {
      const name = e.repo?.name || 'GitHub'; const date = (e.created_at||'').slice(0,10);
      return `<div class="event-line"><span class="event-icon">↗</span><div><b>${html(eventTitle(e.type))}</b><small>${html(name)} · ${html(date)}</small></div></div>`;
    }).join('') : '<p class="empty-message">近期暂无可见公开事件。</p>';
  }
  function renderRepositories() {
    const repos = state.repos;
    const previous = $('language-filter').value;
    $('language-filter').innerHTML = '<option value="">全部语言</option>' + [...new Set(repos.map(r=>r.language).filter(Boolean))].sort().map(l => `<option value="${html(l)}">${html(l)}</option>`).join('');
    $('language-filter').value = previous;
    filterRepositories();
    $('health-repo-select').innerHTML = repos.length ? repos.map((r,i)=>`<option value="${i}">${html(r.name)}</option>`).join('') : '<option value="">无公开仓库</option>';
    $('health-output').innerHTML = '<div class="empty-art">✳</div><strong>为你的项目做一次体检</strong><p>点击「开始检查」会读取所选仓库的公开文件树和元数据。</p>';
  }
  function filterRepositories() {
    const word = $('repo-search').value.trim().toLowerCase();
    const lang = $('language-filter').value;
    const withForks = $('include-forks').checked;
    const sort = $('repo-sort').value;
    let repos = state.repos.filter(r => (withForks || !r.fork) && (!lang || r.language===lang) && (!word || `${r.name} ${r.description||''}`.toLowerCase().includes(word)));
    repos = repos.slice().sort((a,b)=> {
      if (sort==='stars') return (b.stargazers_count||0)-(a.stargazers_count||0);
      if (sort==='forks') return (b.forks_count||0)-(a.forks_count||0);
      return (b[sort==='created'?'created_at':'pushed_at'] || '').localeCompare(a[sort==='created'?'created_at':'pushed_at']||'');
    });
    $('repo-count').textContent = `· ${repos.length} 个`;
    $('repository-list').innerHTML = repos.length ? repos.map(r=> `<article class="repo-row"><div><h3><a href="${html(r.html_url)}" target="_blank" rel="noopener noreferrer">${html(r.name)} ↗</a> ${r.fork?'<small>FORK</small>':''}</h3><p>${html(r.description||'暂无项目简介')}</p></div><div class="repo-row-meta"><span><i class="lang-pin" style="background:${colors[r.language]||'#c3b7a7'}"></i>${html(r.language||'—')}</span><span>★ ${humanNumber(r.stargazers_count)}</span><span>⑂ ${humanNumber(r.forks_count)}</span></div></article>`).join('') : '<p class="empty-message">没有找到匹配的仓库。</p>';
  }
  function healthScore(repo, tree) {
    const paths = new Set((tree.tree || []).filter(x=>x.type==='blob'&&x.path).map(x=>x.path.toLowerCase()));
    const list = [...paths];
    const readme = list.some(p=>p==='readme' || p.startsWith('readme.'));
    const manifest = list.some(p=>['requirements.txt','pyproject.toml','pipfile','poetry.lock','package.json','pnpm-lock.yaml','yarn.lock','go.mod','cargo.toml','pom.xml','build.gradle','gemfile','composer.json'].includes(p));
    const ignore = paths.has('.gitignore');
    const tests = list.some(p=>p.startsWith('tests/')||p.startsWith('test/')||p.startsWith('__tests__/')||p.endsWith('_test.py')||p.startsWith('test_')||p.endsWith('.test.js')||p.endsWith('.test.ts')||p.endsWith('.spec.ts'));
    const ci = list.some(p=>p.startsWith('.github/workflows/')||p==='.gitlab-ci.yml');
    const license = Boolean(repo.license) || list.some(p=>['license','license.md','license.txt'].includes(p));
    const desc = Boolean((repo.description||'').trim());
    const age = repo.pushed_at ? (Date.now() - new Date(repo.pushed_at).getTime())/86400000 : 1e9;
    const maintain = age<=90?10:age<=365?5:0;
    const checks = [
      ['README 文档',readme?25:0,25,'补充项目用途、安装方法和示例。'],
      ['依赖与规范',(manifest?12:0)+(ignore?8:0),20,'添加依赖清单与 .gitignore。'],
      ['自动化测试',tests?20:0,20,'增加 tests/ 和可执行测试。'],
      ['CI 工作流',ci?15:0,15,'设置 GitHub Actions 自动测试。'],
      ['近期维护',maintain,10,'维护项目并说明最近的改动。'],
      ['开源协议',license?5:0,5,'按需添加 LICENSE。'],
      ['仓库描述',desc?5:0,5,'补充简明准确的仓库简介。'],
    ];
    return { score: checks.reduce((v,c)=>v+c[1],0), checks, truncated: Boolean(tree.truncated), files: list.length };
  }
  async function runHealth() {
    if (!state.profile) return;
    const index = Number($('health-repo-select').value); const repo = state.repos[index];
    if (!repo) return;
    const el = $('health-output'); el.innerHTML = '<p class="loading-row">正在分析工程结构…</p>';
    $('health-run').disabled = true;
    try {
      const full = await get(`/repos/${encodeURIComponent(state.profile.login)}/${encodeURIComponent(repo.name)}`);
      const branch = encodeURIComponent(full.default_branch || 'main');
      const tree = await get(`/repos/${encodeURIComponent(state.profile.login)}/${encodeURIComponent(repo.name)}/git/trees/${branch}?recursive=1`);
      const score = healthScore(full, tree); state.health[repo.full_name]=score;
      el.innerHTML = `<div class="score-hero"><div class="score-bubble">${score.score}<small>/100</small></div><div><strong>${html(repo.name)}</strong><p>工程规范覆盖度 · 规则评分<br>扫描 ${score.files} 个公开文件条目</p></div></div>${score.truncated?'<p class="status-message error">文件树已截断，评分可能偏低。</p>':''}${score.checks.map(c=>`<div class="check-item"><div><strong>${c[1]===c[2]?'✓':'○'} ${html(c[0])}</strong>${c[1]<c[2]?`<small>${html(c[3])}</small>`:''}</div><b>${c[1]}/${c[2]}</b></div>`).join('')}`;
      renderReport();
    } catch(e) { el.innerHTML = `<p class="status-message error">${html(e.message)}</p>`; }
    finally { $('health-run').disabled = false; }
  }
  function report() {
    const p = state.profile; if (!p) return '# GitInsight 报告\n\n等待获取公开数据。';
    const t = totals(); const langs=langCounts();
    const top=originalRepos().slice().sort((a,b)=>(b.stargazers_count||0)-(a.stargazers_count||0)).slice(0,8);
    const lines=[`# GitInsight — ${p.name||p.login} 的开发者报告`,'',`GitHub：https://github.com/${p.login}`,`生成时间：${new Date().toISOString().slice(0,10)} (UTC)`,'',
      '## 开发者概览',`- 公开原创仓库：${t.repos}`,`- 累计 Stars：${t.stars}`,`- 累计 Forks：${t.forks}`,`- 当前可获取的公开事件：${state.events.length}`,'',
      '## 主要编程语言（按仓库数）',...langs.map(([k,v])=>`- ${k}: ${v} 个`),'','## 代表仓库',...top.map(r=>`- [${r.name}](${r.html_url}) — ★ ${r.stargazers_count||0} · ${r.language||'未标注'}`),''];
    if(Object.keys(state.health).length){lines.push('## 工程规范检查（规则评分）',...Object.entries(state.health).map(([k,v])=>`- ${k}: ${v.score}/100`),'');}
    lines.push('---','说明：仅基于公开 GitHub 数据。Stars、Forks 与语言统计均排除派生仓库。','公开事件最多最近 30 天 300 条，事件数不是提交次数。工程评分不代表代码质量。');
    return lines.join('\n');
  }
  function renderReport() { $('report-preview-text').textContent = report(); }
  function download() {
    if (!state.profile) return;
    const blob = new Blob([report()], {type:'text/markdown;charset=utf-8'});
    const url = URL.createObjectURL(blob); const link = document.createElement('a');
    link.href=url; link.download=`gitinsight-${state.profile.login}.md`;
    document.body.append(link); link.click(); link.remove();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function renderEverything() { renderOverview();renderLanguages();renderEvents();renderRepositories();renderReport(); }
  function navigate(page) {
    if (!['overview','repositories','health','reports'].includes(page)) page='overview';
    state.active=page;
    document.querySelectorAll('.page-section').forEach(el=>el.classList.toggle('is-visible',el.id===`view-${page}`));
    document.querySelectorAll('.side-nav a').forEach(el=>el.classList.toggle('active',el.dataset.page===page));
    $('page-breadcrumb').textContent=page.toUpperCase();
    $('sidebar').classList.remove('open'); $('sidebar-overlay').classList.remove('open');
    $('menu-toggle').setAttribute('aria-expanded','false');
    window.scrollTo({top:0,behavior:'smooth'});
  }
  function init() {
    $('search-form').addEventListener('submit',event=>{event.preventDefault();loadUser($('username-input').value.trim());});
    $('menu-toggle').addEventListener('click',()=>{const open=$('sidebar').classList.toggle('open');$('sidebar-overlay').classList.toggle('open',open);$('menu-toggle').setAttribute('aria-expanded',String(open));});
    $('sidebar-overlay').addEventListener('click',()=>{$('sidebar').classList.remove('open');$('sidebar-overlay').classList.remove('open');});
    document.querySelectorAll('.side-nav a').forEach(a=>a.addEventListener('click',()=>navigate(a.dataset.page)));
    document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>{location.hash=b.dataset.go;navigate(b.dataset.go);}));
    window.addEventListener('hashchange',()=>navigate(location.hash.slice(1)));
    for(const id of ['repo-search','language-filter','repo-sort','include-forks']) $(id).addEventListener('input',filterRepositories);
    $('health-run').addEventListener('click',runHealth);
    $('download-report').addEventListener('click',download);
    navigate(location.hash.slice(1)||'overview');
    const user = new URLSearchParams(location.search).get('user') || 'asdffgdghdfh-art';
    loadUser(user);
  }
  init();
})();