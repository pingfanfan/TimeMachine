"""时光档案馆 · 渲染单文件 HTML demo

读 data/demo/*.json → 输出 dist/index.html
- 博物馆视觉调性(深色 #08101F + 米黄 #EBE0C4 + 红印章 #A8252F)
- 滚动时间轴 + 档案条目 + 真实知乎链接
- 单文件 self-contained,丢哪儿都能开
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT / "data" / "demo"
DIST = ROOT / "dist"
DIST.mkdir(exist_ok=True)


def load_topics() -> list[dict]:
    out = []
    for f in sorted(DATA_DIR.glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            # 跳过年份太少的话题(<2)
            if len(d.get("year_summaries", {})) < 2:
                print(f"skip {f.name}: only {len(d.get('year_summaries', {}))} year")
                continue
            out.append(d)
        except Exception as e:
            print(f"skip {f}: {e}")
    # 按年份覆盖广度排序(广的优先)
    out.sort(key=lambda d: -len(d.get("year_summaries", {})))
    return out


def esc(s):
    if s is None:
        return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>时光档案馆 · 知乎编年观点演变史</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;500;700;900&family=Noto+Sans+SC:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
:root {
  --ink: #08101F;
  --paper: #EBE0C4;
  --stamp: #A8252F;
  --mute: #5A6478;
  --highlight: #F1B644;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { font-family: 'Noto Sans SC', system-ui, sans-serif; background: var(--paper); color: var(--ink); line-height: 1.6; }
.serif { font-family: 'Noto Serif SC', Songti, serif; }
.mono { font-family: 'JetBrains Mono', monospace; letter-spacing: 0.1em; }

/* 顶部导航 */
.nav { position: sticky; top: 0; z-index: 50; background: rgba(235,224,196,0.95); backdrop-filter: blur(8px); border-bottom: 1px solid rgba(8,16,31,0.1); padding: 16px 32px; display: flex; align-items: center; justify-content: space-between; }
.nav-title { font-family: 'Noto Serif SC', serif; font-size: 20px; font-weight: 700; }
.nav-link { font-size: 13px; color: rgba(8,16,31,0.7); text-decoration: none; margin-left: 24px; cursor: pointer; }
.nav-link:hover { color: var(--stamp); }

/* Hero */
.hero { min-height: 80vh; background: var(--ink); color: var(--paper); display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 80px 32px; }
.hero-tag { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 0.3em; color: var(--mute); margin-bottom: 32px; }
.hero-title { font-family: 'Noto Serif SC', serif; font-size: clamp(48px, 9vw, 112px); font-weight: 900; line-height: 1.05; }
.hero-subtitle { font-family: 'Noto Serif SC', serif; font-style: italic; font-size: clamp(18px, 2.5vw, 28px); color: rgba(235,224,196,0.6); margin-top: 16px; }
.hero-stats { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--mute); margin-top: 48px; }
.hero-stats strong { color: var(--paper); font-weight: 500; }
.hero-hint { margin-top: 64px; font-size: 12px; color: var(--mute); animation: float 2s ease-in-out infinite; }
@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(6px); } }

/* 网格 */
.archive-section { padding: 96px 32px; }
.archive-section .container { max-width: 1280px; margin: 0 auto; }
.section-header { margin-bottom: 64px; }
.section-tag { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 0.3em; color: var(--mute); }
.section-title { font-family: 'Noto Serif SC', serif; font-size: 48px; font-weight: 700; margin-top: 8px; }
.section-desc { font-family: 'Noto Serif SC', serif; font-style: italic; color: rgba(8,16,31,0.6); margin-top: 12px; font-size: 18px; }

.topic-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; }
.topic-card { border: 1px solid rgba(8,16,31,0.15); background: var(--paper); padding: 32px; cursor: pointer; transition: border-color 0.2s; position: relative; }
.topic-card:hover { border-color: var(--stamp); }
.topic-stamp { position: absolute; top: 16px; right: 16px; border: 2px solid var(--stamp); color: var(--stamp); font-family: 'JetBrains Mono', monospace; font-size: 11px; padding: 4px 10px; transform: rotate(-3deg); opacity: 0.9; letter-spacing: 0.15em; }
.topic-card .cat { font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--mute); letter-spacing: 0.2em; }
.topic-card h3 { font-family: 'Noto Serif SC', serif; font-size: 22px; font-weight: 700; margin-top: 8px; padding-right: 70px; line-height: 1.3; }
.topic-card .quotes { margin-top: 24px; font-family: 'Noto Serif SC', serif; font-style: italic; font-size: 14px; line-height: 1.7; }
.topic-card .quote-old { color: rgba(8,16,31,0.65); }
.topic-card .quote-new { color: var(--stamp); margin-top: 8px; }
.topic-card .year-tag { font-family: 'JetBrains Mono', monospace; font-style: normal; font-size: 10px; color: var(--mute); margin-left: 8px; letter-spacing: 0.1em; }
.topic-card .data-bar { margin-top: 20px; padding-top: 16px; border-top: 1px solid rgba(8,16,31,0.1); display: flex; gap: 16px; font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--mute); letter-spacing: 0.1em; }

/* 详情视图(隐藏到点击展开) */
.detail-view { display: none; }
.detail-view.active { display: block; }
.detail-hero { background: var(--ink); color: var(--paper); padding: 96px 32px; min-height: 60vh; display: flex; flex-direction: column; justify-content: center; }
.detail-hero .container { max-width: 800px; margin: 0 auto; }
.detail-stamp { display: inline-block; border: 2px solid var(--highlight); color: var(--highlight); font-family: 'JetBrains Mono', monospace; font-size: 12px; padding: 5px 12px; letter-spacing: 0.2em; }
.detail-title { font-family: 'Noto Serif SC', serif; font-size: clamp(40px, 7vw, 80px); font-weight: 900; line-height: 1.1; margin-top: 24px; }
.detail-cat { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--mute); letter-spacing: 0.3em; margin-top: 24px; }
.back-btn { position: fixed; top: 80px; left: 32px; z-index: 60; background: var(--paper); border: 1px solid rgba(8,16,31,0.2); padding: 10px 20px; cursor: pointer; font-family: 'Noto Sans SC'; font-size: 13px; }
.back-btn:hover { border-color: var(--stamp); color: var(--stamp); }

/* 时间轴 */
.timeline { padding: 96px 32px 128px; background: var(--paper); }
.timeline .container { max-width: 760px; margin: 0 auto; position: relative; padding-left: 56px; }
.timeline .container::before { content: ""; position: absolute; left: 24px; top: 0; bottom: 0; width: 2px; background: rgba(8,16,31,0.2); }

.year-card { position: relative; padding: 48px 0; }
.year-card::before { content: ""; position: absolute; left: -39px; top: 60px; width: 20px; height: 20px; border-radius: 50%; background: var(--stamp); }
.year-label { font-family: 'Noto Serif SC', serif; font-size: 80px; font-weight: 700; color: rgba(8,16,31,0.85); line-height: 1; }
.year-era { font-family: 'Noto Sans SC'; font-size: 15px; color: rgba(8,16,31,0.6); margin-top: 12px; }
.year-quote { font-family: 'Noto Serif SC', serif; font-size: 26px; font-style: italic; line-height: 1.55; border-left: 4px solid var(--stamp); padding-left: 20px; margin-top: 32px; }
.year-quote cite { display: block; margin-top: 12px; font-style: normal; font-size: 13px; color: rgba(8,16,31,0.5); font-family: 'Noto Sans SC'; }
.year-quote cite a { color: rgba(8,16,31,0.5); text-decoration: none; border-bottom: 1px dotted; }
.year-quote cite a:hover { color: var(--stamp); }
.year-views { margin-top: 28px; display: flex; flex-direction: column; gap: 10px; }
.year-views p { font-family: 'Noto Sans SC'; font-size: 16px; line-height: 1.7; }
.year-views .primary { color: var(--ink); }
.year-views .primary::before { content: "·"; font-weight: 900; margin-right: 8px; color: var(--stamp); }
.year-views .secondary { color: rgba(8,16,31,0.55); }
.year-views .secondary::before { content: "·"; margin-right: 8px; color: rgba(8,16,31,0.3); }

/* 档案条目 */
.year-archive-toggle { margin-top: 28px; font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 0.2em; color: var(--mute); cursor: pointer; border-bottom: 1px dotted rgba(8,16,31,0.2); padding-bottom: 4px; display: inline-block; }
.year-archive-toggle:hover { color: var(--stamp); border-color: var(--stamp); }
.year-archives { display: none; margin-top: 20px; }
.year-archives.open { display: block; }
.archive-item { padding: 16px 0; border-top: 1px dashed rgba(8,16,31,0.15); }
.archive-item:first-child { border-top: none; }
.archive-item .meta { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--mute); letter-spacing: 0.15em; }
.archive-item a { color: var(--ink); text-decoration: none; }
.archive-item a:hover { color: var(--stamp); }
.archive-item .a-title { font-family: 'Noto Serif SC', serif; font-size: 16px; font-weight: 500; margin-top: 4px; }
.archive-item .a-text { font-size: 13px; color: rgba(8,16,31,0.65); line-height: 1.6; margin-top: 6px; }

/* 2029 预测 */
.prediction { background: var(--ink); color: var(--paper); padding: 64px 40px; margin-top: 48px; border-radius: 4px; }
.prediction h2 { display: flex; align-items: baseline; justify-content: space-between; }
.prediction h2 .y { font-family: 'Noto Serif SC', serif; font-size: 56px; font-weight: 900; }
.prediction h2 .meta { font-family: 'Noto Sans SC'; font-size: 11px; color: rgba(235,224,196,0.45); letter-spacing: 0.15em; }
.pred-tabs { display: flex; gap: 8px; margin-top: 28px; }
.pred-tab { padding: 6px 14px; border-radius: 999px; font-family: 'Noto Sans SC'; font-size: 13px; cursor: pointer; border: 1px solid rgba(235,224,196,0.3); background: transparent; color: var(--paper); }
.pred-tab.active { background: var(--paper); color: var(--ink); border-color: var(--paper); }
.pred-body { font-family: 'Noto Serif SC', serif; font-size: 22px; line-height: 1.55; margin-top: 28px; min-height: 80px; }

/* footer */
footer { padding: 64px 32px; text-align: center; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--mute); letter-spacing: 0.2em; }

@media (max-width: 720px) {
  .archive-section { padding: 64px 20px; }
  .section-title { font-size: 32px; }
  .timeline { padding: 64px 16px; }
  .timeline .container { padding-left: 36px; }
  .timeline .container::before { left: 14px; }
  .year-card::before { left: -27px; }
  .year-label { font-size: 56px; }
  .year-quote { font-size: 20px; }
}
</style>
</head>
<body>

<nav class="nav">
  <div class="nav-title">时光档案馆 <span style="font-style:italic; font-size:13px; color:rgba(8,16,31,0.5); margin-left:8px;">知乎编年观点演变史</span></div>
  <div>
    <a class="nav-link" onclick="showHome()">本馆首页</a>
    <a class="nav-link" href="#">关于</a>
  </div>
</nav>

<!-- Home View -->
<div id="home">

<section class="hero">
  <div class="hero-tag">EST. 2026 · ZHIHU CHRONICLE · MUSEUM OF IDEAS</div>
  <h1 class="hero-title">时光档案馆</h1>
  <p class="hero-subtitle">知乎思想编年志</p>
  <div class="hero-stats">
    馆藏 <strong>__TOPIC_COUNT__</strong> 份档案 · <strong>__QUOTE_COUNT__</strong> 份金句 · 跨越 <strong>__YEAR_SPAN__</strong> 年
  </div>
  <div class="hero-hint">↓ 翻阅本馆</div>
</section>

<section class="archive-section">
  <div class="container">
    <header class="section-header">
      <div class="section-tag">FEATURED ARCHIVES · 精选档案</div>
      <h2 class="section-title">本馆精选 __TOPIC_COUNT__ 份档案</h2>
      <p class="section-desc">每一份档案,都是一个问题在知乎被讨论了多少年的故事。点击任何一份进入它的时光轴。</p>
    </header>
    <div class="topic-grid">
__TOPIC_CARDS__
    </div>
  </div>
</section>

<footer>
  时光档案馆 · 知乎黑客松 2026 参赛作品 · ALL ANSWERS LINK BACK TO ZHIHU
</footer>

</div>

<!-- Detail Views -->
__DETAIL_VIEWS__

<script>
const DATA = __DATA_JSON__;

function showHome() {
  document.getElementById('home').style.display = 'block';
  document.querySelectorAll('.detail-view').forEach(d => d.classList.remove('active'));
  window.scrollTo(0, 0);
}

function showDetail(id) {
  document.getElementById('home').style.display = 'none';
  document.querySelectorAll('.detail-view').forEach(d => d.classList.remove('active'));
  const el = document.getElementById('detail-' + id);
  if (el) {
    el.classList.add('active');
    window.scrollTo(0, 0);
  }
}

function toggleArchives(btn) {
  const next = btn.nextElementSibling;
  if (!next) return;
  next.classList.toggle('open');
  btn.textContent = next.classList.contains('open') ? '↑ 收起档案条目' : '↓ 展开档案条目(原始回答 + 真实链接)';
}

function setPredTab(topicId, scenario) {
  const wrap = document.querySelector(`#detail-${topicId} .prediction`);
  if (!wrap) return;
  wrap.querySelectorAll('.pred-tab').forEach(t => t.classList.remove('active'));
  wrap.querySelector(`[data-s="${scenario}"]`).classList.add('active');
  const text = DATA[topicId].prediction?.[scenario] || '(暂无)';
  wrap.querySelector('.pred-body').textContent = text;
}

// 初始按 hash 决定显示
window.addEventListener('hashchange', () => {
  const h = location.hash.replace('#', '');
  if (h && DATA[h]) showDetail(h);
  else showHome();
});
window.addEventListener('load', () => {
  const h = location.hash.replace('#', '');
  if (h && DATA[h]) showDetail(h);
});
</script>

</body>
</html>"""


def render_topic_card(t: dict) -> str:
    years = sorted([int(y) for y in t.get("year_summaries", {}).keys()])
    early_year = years[0] if years else None
    late_year = years[-1] if years else None
    early_q = t["year_summaries"].get(str(early_year), {}).get("golden_quote", "") if early_year else ""
    late_q = t["year_summaries"].get(str(late_year), {}).get("golden_quote", "") if late_year else ""
    raw_count = len(t.get("raw_answers", []))
    quote_count = len(t.get("year_summaries", {}))
    yr_range = f"{early_year}–{late_year}" if early_year and late_year else "—"
    return f"""<article class="topic-card" onclick="location.hash='{esc(t['id'])}'">
  <div class="topic-stamp">ARCHIVE-{(hash(t['id']) % 1000):03d}</div>
  <div class="cat">{esc(t.get('category','—'))} · {esc(yr_range)}</div>
  <h3>{esc(t['title'])}</h3>
  <div class="quotes">
    <div class="quote-old">「{esc(early_q)}」<span class="year-tag">{early_year}</span></div>
    <div class="quote-new">「{esc(late_q)}」<span class="year-tag">{late_year}</span></div>
  </div>
  <div class="data-bar">
    <span>{raw_count} 条档案</span>
    <span>{quote_count} 个年份</span>
    <span>{len(t.get('keywords', []))} 个关键词</span>
  </div>
</article>"""


def render_archives_in_year(topic: dict, year: int) -> str:
    """渲染某一年的档案条目(原始回答列表 + 真实链接)"""
    raw_by_id = {a["content_id"]: a for a in topic.get("raw_answers", [])}
    ids = topic.get("by_year", {}).get(str(year), [])
    answers = [raw_by_id[i] for i in ids if i in raw_by_id]
    answers.sort(key=lambda x: x.get("vote_up_count", 0), reverse=True)
    items = []
    for a in answers[:8]:
        url = a.get("url", "")
        title_text = a.get("title", "").replace(" - 知乎", "")
        text_preview = a.get("content_text", "")[:180]
        items.append(f"""<div class="archive-item">
  <div class="meta">{esc(a.get('content_type','-'))} · {esc(a.get('author_name','-'))} · 赞 {a.get('vote_up_count', 0)} · {a.get('edit_year','?')}</div>
  <a href="{esc(url)}" target="_blank" rel="noopener">
    <div class="a-title">{esc(title_text)}</div>
    <div class="a-text">{esc(text_preview)}…</div>
  </a>
</div>""")
    return "\n".join(items)


def render_year_card(topic: dict, year: int) -> str:
    s = topic["year_summaries"].get(str(year), {})
    quote = s.get("golden_quote", "—")
    primary = s.get("primary_view", "")
    secondary = s.get("secondary_view", "")
    era = s.get("era_caption", "")
    author = s.get("quote_author", "")
    quote_url = s.get("quote_url", "")
    cite_html = ""
    if author:
        if quote_url:
            cite_html = f'<cite>— <a href="{esc(quote_url)}" target="_blank" rel="noopener">{esc(author)}</a></cite>'
        else:
            cite_html = f'<cite>— {esc(author)}</cite>'
    archives_html = render_archives_in_year(topic, year)
    secondary_html = f'<p class="secondary">{esc(secondary)}</p>' if secondary else ""
    return f"""<article class="year-card">
  <div class="year-label">{year}</div>
  <div class="year-era">{esc(era)}</div>
  <blockquote class="year-quote">「{esc(quote)}」{cite_html}</blockquote>
  <div class="year-views">
    <p class="primary">{esc(primary)}</p>
    {secondary_html}
  </div>
  <div class="year-archive-toggle" onclick="toggleArchives(this)">↓ 展开档案条目(原始回答 + 真实链接)</div>
  <div class="year-archives">
    {archives_html}
  </div>
</article>"""


def render_prediction(t: dict) -> str:
    pred = t.get("prediction") or {}
    main = esc(pred.get("mainstream", "(暂无)"))
    return f"""<section class="prediction">
  <h2><span class="y">2029</span><span class="meta">AI 基于历年讨论的推演,非预言</span></h2>
  <div class="pred-tabs">
    <button class="pred-tab" data-s="conservative" onclick="setPredTab('{esc(t['id'])}', 'conservative')">保守</button>
    <button class="pred-tab active" data-s="mainstream" onclick="setPredTab('{esc(t['id'])}', 'mainstream')">主流</button>
    <button class="pred-tab" data-s="radical" onclick="setPredTab('{esc(t['id'])}', 'radical')">激进</button>
  </div>
  <div class="pred-body">{main}</div>
</section>"""


def render_detail_view(t: dict) -> str:
    years = sorted([int(y) for y in t.get("year_summaries", {}).keys()])
    cards = [render_year_card(t, y) for y in years]
    pred = render_prediction(t) if t.get("prediction") else ""
    return f"""<div id="detail-{esc(t['id'])}" class="detail-view">
  <button class="back-btn" onclick="location.hash=''">← 返回本馆首页</button>
  <section class="detail-hero">
    <div class="container">
      <div class="detail-stamp">ARCHIVE-{(hash(t['id']) % 1000):03d} · {esc(t.get('category','—'))}</div>
      <h1 class="detail-title">{esc(t['title'])}</h1>
      <div class="detail-cat">{len(t.get('raw_answers', []))} 条档案 · {len(years)} 个年份切片 · {min(years) if years else '?'} → {max(years) if years else '?'}</div>
    </div>
  </section>
  <section class="timeline">
    <div class="container">
      {''.join(cards)}
      {pred}
    </div>
  </section>
</div>"""


def main():
    topics = load_topics()
    print(f"加载 {len(topics)} 个话题")

    if not topics:
        print("❌ 无数据,先跑 build_demo.py")
        return

    # 统计
    topic_count = len(topics)
    quote_count = sum(len(t.get("year_summaries", {})) for t in topics)
    all_years = []
    for t in topics:
        all_years.extend(int(y) for y in t.get("year_summaries", {}).keys())
    if all_years:
        year_span = max(all_years) - min(all_years)
    else:
        year_span = 0

    # 渲染
    cards = "\n".join(render_topic_card(t) for t in topics)
    details = "\n".join(render_detail_view(t) for t in topics)

    # 给前端 JS 用的精简数据(只要 prediction 的 3 段文字)
    data_for_js = {
        t["id"]: {
            "title": t["title"],
            "prediction": t.get("prediction") or {},
        } for t in topics
    }

    html = HTML
    html = html.replace("__TOPIC_COUNT__", str(topic_count))
    html = html.replace("__QUOTE_COUNT__", str(quote_count))
    html = html.replace("__YEAR_SPAN__", str(year_span))
    html = html.replace("__TOPIC_CARDS__", cards)
    html = html.replace("__DETAIL_VIEWS__", details)
    html = html.replace("__DATA_JSON__", json.dumps(data_for_js, ensure_ascii=False))

    out = DIST / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"✅ 渲染到 {out}  ({len(html)/1024:.1f} KB)")


if __name__ == "__main__":
    main()
