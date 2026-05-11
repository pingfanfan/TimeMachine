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


def load_curation() -> dict:
    p = DATA_DIR / "curation.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def load_topics() -> list[dict]:
    curation = load_curation()
    out = []
    for f in sorted(DATA_DIR.glob("*.json")):
        if f.name.startswith("_") or f.name == "curation.json":
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            # 跳过年份太少的话题(<2)
            if len(d.get("year_summaries", {})) < 2:
                print(f"skip {f.name}: only {len(d.get('year_summaries', {}))} year")
                continue
            # 注入策展元数据
            tid = d["id"]
            if tid in curation:
                d["civic_impact"] = curation[tid].get("civic_impact")
                d["event_anchors"] = curation[tid].get("event_anchors", {})
                d["mood_track"] = curation[tid].get("mood_track", {})
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


HTML = r"""<!DOCTYPE html>
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
  --zhihu: #175199;       /* 知乎蓝 */
  --zhihu-light: #4A90D9;
  --sepia: #6B4423;       /* 旧墨褐 */
  --cyber: #4A7C59;       /* 赛博绿 */
  --era-old-bg: #EBE0C4;
  --era-mid-bg: #F4F0E4;
  --era-new-bg: linear-gradient(135deg, rgba(23,81,153,0.07), rgba(74,124,89,0.04));
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
.hero { min-height: 80vh; background: var(--ink); color: var(--paper); display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 80px 32px; position: relative; overflow: hidden; }
/* 科技感扫描线背景 */
.hero::before {
  content: "";
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(74,124,89,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(23,81,153,0.05) 1px, transparent 1px);
  background-size: 64px 64px;
  pointer-events: none;
}
.hero::after {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 30% 40%, rgba(23,81,153,0.18), transparent 50%),
              radial-gradient(circle at 70% 60%, rgba(74,124,89,0.15), transparent 50%);
  pointer-events: none;
}
.hero > * { position: relative; z-index: 1; }
.hero-tag { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 0.3em; color: var(--mute); margin-bottom: 32px; }
.hero-title { font-family: 'Noto Serif SC', serif; font-size: clamp(48px, 9vw, 112px); font-weight: 900; line-height: 1.05; }
.hero-subtitle { font-family: 'Noto Serif SC', serif; font-style: italic; font-size: clamp(18px, 2.5vw, 28px); color: rgba(235,224,196,0.6); margin-top: 16px; }
.hero-stats { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--mute); margin-top: 48px; }
.hero-stats strong { color: var(--paper); font-weight: 500; }
.hero-hint { margin-top: 64px; font-size: 12px; color: var(--mute); animation: float 2s ease-in-out infinite; }
@keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(6px); } }

/* 今日热榜 · 直达时光机 */
.hotlist-section {
  background: linear-gradient(180deg, var(--ink) 0%, #0F1A2E 50%, var(--ink) 100%);
  color: var(--paper);
  padding: 64px 32px 80px;
  position: relative;
  overflow: hidden;
}
.hotlist-section::before {
  content: "";
  position: absolute; inset: 0;
  background-image: linear-gradient(rgba(74,124,89,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(23,81,153,0.04) 1px, transparent 1px);
  background-size: 32px 32px;
  pointer-events: none;
}
.hotlist-section .container { max-width: 1280px; margin: 0 auto; position: relative; z-index: 1; }
.hotlist-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 32px; gap: 24px; flex-wrap: wrap; }
.hotlist-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.3em;
  color: var(--highlight);
  margin-bottom: 8px;
}
.hotlist-tag::before { content: "● "; color: #E63946; animation: blink 1.5s infinite; }
@keyframes blink { 0%,100%{opacity:1;} 50%{opacity:0.3;} }
.hotlist-title { font-family: 'Noto Serif SC', serif; font-size: 32px; font-weight: 700; }
.hotlist-desc { font-family: 'Noto Serif SC', serif; font-style: italic; color: rgba(235,224,196,0.6); margin-top: 8px; font-size: 14px; max-width: 600px; }
.hotlist-refresh-btn {
  background: transparent;
  border: 1px solid rgba(241,182,68,0.4);
  color: var(--highlight);
  padding: 8px 18px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.15em;
  cursor: pointer;
  transition: all 0.2s;
}
.hotlist-refresh-btn:hover { background: var(--highlight); color: var(--ink); }
.hotlist-loading {
  text-align: center;
  padding: 60px 0;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.25em;
  color: var(--mute);
  animation: pulse-text 1.5s ease-in-out infinite;
}
@keyframes pulse-text { 0%,100%{opacity:0.4;} 50%{opacity:1;} }
.hotlist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.hotlist-meta { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--highlight); letter-spacing: 0.15em; margin-top: 6px; }
.hotlist-card {
  background: rgba(235,224,196,0.04);
  border: 1px solid rgba(235,224,196,0.12);
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.hotlist-card:hover {
  border-color: var(--highlight);
  background: rgba(241,182,68,0.08);
  transform: translateY(-2px);
}
.hotlist-card .rank {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  color: var(--highlight);
  letter-spacing: 0.15em;
}
.hotlist-card .from-title {
  font-family: 'Noto Sans SC';
  font-size: 11px;
  color: rgba(235,224,196,0.45);
  line-height: 1.6;
  padding: 8px 10px;
  background: rgba(8,16,31,0.4);
  border-left: 2px solid rgba(235,224,196,0.25);
}
.hotlist-card .extract-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.hotlist-card .extract-label {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: rgba(235,224,196,0.4);
  letter-spacing: 0.15em;
}
.hotlist-card .extract-kw {
  background: var(--highlight);
  color: var(--ink);
  padding: 3px 10px;
  font-family: 'Noto Sans SC';
  font-weight: 700;
  font-size: 13px;
  border-radius: 2px;
}
.hotlist-card h3 {
  font-family: 'Noto Serif SC', serif;
  font-size: 19px;
  font-weight: 700;
  color: var(--paper);
  line-height: 1.35;
  flex: 1;
}
.hotlist-card .cta {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  color: var(--highlight);
  letter-spacing: 0.2em;
  padding-top: 10px;
  border-top: 1px dashed rgba(235,224,196,0.15);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.hotlist-card .cta-zhihu {
  color: rgba(235,224,196,0.4);
  text-decoration: none;
  border-bottom: 1px dotted rgba(235,224,196,0.3);
}
.hotlist-card .cta-zhihu:hover { color: var(--highlight); }

/* 网格 */
.archive-section { padding: 96px 32px; }
.archive-section .container { max-width: 1280px; margin: 0 auto; }
.section-header { margin-bottom: 64px; }
.section-tag { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 0.3em; color: var(--mute); }
.section-title { font-family: 'Noto Serif SC', serif; font-size: 48px; font-weight: 700; margin-top: 8px; }
.section-desc { font-family: 'Noto Serif SC', serif; font-style: italic; color: rgba(8,16,31,0.6); margin-top: 12px; font-size: 18px; }

.topic-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 24px; }
.featured-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 32px; }
.topic-card { border: 1px solid rgba(8,16,31,0.15); background: var(--paper); padding: 32px; cursor: pointer; transition: border-color 0.2s; position: relative; }
.topic-card.featured { padding: 40px; border-width: 2px; }
.topic-card.featured h3 { font-size: 28px; }
.topic-card:hover { border-color: var(--stamp); }

.archive-section-secondary { padding-top: 0; padding-bottom: 96px; }
.other-section-header { padding-top: 16px; border-top: 1px solid rgba(8,16,31,0.12); margin-bottom: 8px; }
.other-section-header .section-tag { color: var(--mute); }

.card-civic-pill { display: inline-block; margin-top: 10px; padding: 4px 10px; background: var(--stamp); color: var(--paper); font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: 0.15em; }

.mini-mood-track { display: flex; gap: 1px; margin-top: 20px; height: 8px; }
.mt-cell { flex: 1; border-radius: 1px; }
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

.year-card { position: relative; padding: 48px 0 56px; margin: 12px 0; transition: all 0.3s ease; }
.year-card::before { content: ""; position: absolute; left: -39px; top: 60px; width: 20px; height: 20px; border-radius: 50%; background: var(--stamp); transition: all 0.3s ease; }
.year-label { font-family: 'Noto Serif SC', serif; font-size: 80px; font-weight: 700; color: rgba(8,16,31,0.85); line-height: 1; transition: all 0.3s ease; }
.year-era { font-family: 'Noto Sans SC'; font-size: 15px; color: rgba(8,16,31,0.6); margin-top: 12px; }
.year-quote { font-family: 'Noto Serif SC', serif; font-size: 26px; font-style: italic; line-height: 1.55; border-left: 4px solid var(--stamp); padding-left: 20px; margin-top: 32px; transition: all 0.3s ease; }
.year-quote cite { display: block; margin-top: 12px; font-style: normal; font-size: 13px; color: rgba(8,16,31,0.5); font-family: 'Noto Sans SC'; }
.year-quote cite a { color: rgba(8,16,31,0.5); text-decoration: none; border-bottom: 1px dotted; }
.year-quote cite a:hover { color: var(--stamp); }
.year-views { margin-top: 28px; display: flex; flex-direction: column; gap: 10px; }
.year-views p { font-family: 'Noto Sans SC'; font-size: 16px; line-height: 1.7; }
.year-views .primary { color: var(--ink); }
.year-views .primary::before { content: "·"; font-weight: 900; margin-right: 8px; color: var(--stamp); }
.year-views .secondary { color: rgba(8,16,31,0.55); }
.year-views .secondary::before { content: "·"; margin-right: 8px; color: rgba(8,16,31,0.3); }

/* ━━━━━ 三时代视觉演变 · 远到近 ━━━━━ */

/* 每个时代右上角的「时代质感装饰」SVG */
.era-decoration {
  position: absolute;
  top: 16px; right: 20px;
  width: 120px; height: 120px;
  opacity: 0.35;
  pointer-events: none;
  z-index: 0;
}
@media (max-width: 720px) { .era-decoration { width: 70px; height: 70px; top: 12px; right: 12px; opacity: 0.25; } }
.year-card { position: relative; }
.year-card > * { position: relative; z-index: 1; }

/* 旧报纸网点(era-old) — 7x7 圆点矩阵,模拟报纸印刷网点 */
.era-decoration-old circle { fill: var(--sepia); }

/* 流体曲线(era-mid) — 移动互联网时代「数据流」隐喻 */
.era-decoration-mid path { stroke: var(--zhihu); stroke-width: 1.2; fill: none; }
.era-decoration-mid circle { fill: var(--zhihu); }

/* 神经网络节点(era-new) — AI 时代 */
.era-decoration-new line { stroke: url(#cyber-grad); stroke-width: 1; opacity: 0.7; }
.era-decoration-new circle { fill: var(--cyber); }


/* 时代分隔标记(在不同 era 之间显示) */
.era-divider {
  position: relative;
  margin: 48px 0 24px;
  padding: 16px 24px;
  text-align: center;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.3em;
}
.era-divider::before, .era-divider::after {
  content: "";
  position: absolute; top: 50%;
  width: 38%; height: 1px;
}
.era-divider::before { left: 4%; background: linear-gradient(90deg, transparent, currentColor); }
.era-divider::after { right: 4%; background: linear-gradient(90deg, currentColor, transparent); }
.era-divider.to-mid { color: var(--zhihu); }
.era-divider.to-new { color: var(--cyber); }

/* 远年代(2008-2014)· 胶片墨迹复古 */
.year-card.era-old {
  filter: sepia(0.2) saturate(0.85) contrast(0.95);
  padding-left: 20px;
  background: linear-gradient(90deg, rgba(107,68,35,0.05), transparent 60%);
  border-top: 1px dotted rgba(107,68,35,0.18);
}
.year-card.era-old::before {
  background: var(--sepia);
  width: 16px; height: 16px;
  box-shadow: 0 0 0 4px rgba(107,68,35,0.12);
}
.year-card.era-old .year-label {
  font-family: 'Noto Serif SC', serif;
  font-weight: 900;
  color: var(--sepia);
  letter-spacing: -0.02em;
  /* 旧报纸标题微微倾斜 */
  text-shadow: 1px 1px 0 rgba(107,68,35,0.08);
}
.year-card.era-old .year-quote::before {
  content: "▪ 旧报纸纪年 · ";
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  font-style: normal;
  letter-spacing: 0.2em;
  color: var(--sepia);
  opacity: 0.55;
  display: block;
  margin-bottom: 6px;
}
.year-card.era-old .year-quote {
  border-left-color: var(--sepia);
  background: linear-gradient(90deg, rgba(107,68,35,0.04), transparent 30%);
}
.year-card.era-old .year-era {
  font-style: italic;
  color: rgba(107,68,35,0.7);
}
.year-card.era-old .year-views .primary::before { color: var(--sepia); }

/* 中段(2015-2020)· 博客时代/知乎蓝 */
.year-card.era-mid {
  background: linear-gradient(90deg, rgba(23,81,153,0.04), transparent 70%);
  border-top: 1px solid rgba(23,81,153,0.18);
  padding: 48px 16px 56px;
}
.year-card.era-mid::before {
  background: var(--zhihu);
  box-shadow: 0 0 0 4px rgba(23,81,153,0.18);
}
.year-card.era-mid .year-label {
  color: var(--zhihu);
  letter-spacing: -0.01em;
}
.year-card.era-mid .year-quote::before {
  content: "▪ 博客年代 · ";
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  font-style: normal;
  letter-spacing: 0.2em;
  color: var(--zhihu);
  opacity: 0.6;
  display: block;
  margin-bottom: 6px;
}
.year-card.era-mid .year-quote {
  border-left-color: var(--zhihu);
  border-left-width: 3px;
}
.year-card.era-mid .year-era {
  color: rgba(23,81,153,0.7);
}
.year-card.era-mid .year-views .primary::before { color: var(--zhihu); }

/* 近年(2021-2026)· 赛博/科技渐变 */
.year-card.era-new {
  background: var(--era-new-bg);
  border-radius: 4px;
  padding: 48px 24px 56px;
  margin-left: -24px;
  position: relative;
  overflow: hidden;
}
.year-card.era-new::after {
  /* 细微数据网格背景 */
  content: "";
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(23,81,153,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(23,81,153,0.04) 1px, transparent 1px);
  background-size: 32px 32px;
  pointer-events: none;
  z-index: 0;
}
.year-card.era-new > * { position: relative; z-index: 1; }
.year-card.era-new::before {
  background: linear-gradient(135deg, var(--zhihu), var(--cyber));
  box-shadow: 0 0 16px rgba(74,124,89,0.4), 0 0 0 4px rgba(23,81,153,0.18);
  animation: pulse-cyber 2.8s ease-in-out infinite;
}
@keyframes pulse-cyber {
  0%, 100% { box-shadow: 0 0 12px rgba(74,124,89,0.35), 0 0 0 4px rgba(23,81,153,0.15); }
  50%      { box-shadow: 0 0 24px rgba(74,124,89,0.6),  0 0 0 4px rgba(23,81,153,0.25); }
}
.year-card.era-new .year-label {
  background: linear-gradient(135deg, var(--zhihu), var(--cyber) 70%, var(--highlight));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  font-family: 'Noto Serif SC', serif;
  font-weight: 900;
}
.year-card.era-new .year-quote {
  border-left: 3px solid;
  border-image: linear-gradient(180deg, var(--zhihu), var(--cyber)) 1;
  padding-left: 22px;
}
.year-card.era-new .year-quote::before {
  content: "▸ 赛博纪年 · ";
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  font-style: normal;
  letter-spacing: 0.2em;
  background: linear-gradient(90deg, var(--zhihu), var(--cyber));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  opacity: 0.85;
  display: block;
  margin-bottom: 6px;
}
.year-card.era-new .year-era {
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  letter-spacing: 0.05em;
  color: var(--zhihu);
  text-transform: lowercase;
}
.year-card.era-new .year-views .primary::before {
  content: "▸";
  color: var(--cyber);
  font-size: 14px;
}

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

/* 情绪轨迹图 */
.mood-chart-section { background: rgba(8,16,31,0.04); padding: 32px; margin: 32px 0 56px; border: 1px solid rgba(8,16,31,0.08); }
.mood-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 20px; }
.mood-tag { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 0.25em; color: var(--mute); }
.mood-meta { font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--mute); }
.mood-svg { width: 100%; height: auto; display: block; }
.mood-svg .mood-year { font-family: 'JetBrains Mono', monospace; font-size: 11px; fill: rgba(8,16,31,0.7); font-weight: 600; }
.mood-svg .mood-event { font-family: 'Noto Sans SC'; font-size: 11px; opacity: 0.95; font-weight: 500; }
.mood-svg .era-zone-label { font-family: 'JetBrains Mono', monospace; font-size: 9px; letter-spacing: 0.15em; opacity: 0.55; }
.mood-svg .era-old-label { fill: var(--sepia); }
.mood-svg .era-mid-label { fill: var(--zhihu); }
.mood-svg .era-new-label { fill: var(--cyber); font-weight: 500; }
.mood-legend-row { margin-top: 16px; padding-top: 16px; border-top: 1px dashed rgba(8,16,31,0.15); }
.mood-legend-svg { max-width: 380px; height: 16px; display: block; }
.mood-legend-svg .mood-legend { font-family: 'Noto Sans SC'; font-size: 12px; fill: var(--ink); }

/* 简化年份卡(只有事件锚点) */
.year-card-thin { padding: 24px 0; opacity: 0.85; }
.year-card-thin::before { content: ""; position: absolute; left: -34px; top: 36px; width: 10px; height: 10px; border-radius: 50%; background: rgba(8,16,31,0.3); }
.year-label-thin { font-size: 36px; opacity: 0.55; }
.year-anchor-only { margin-top: 4px; font-family: 'Noto Sans SC'; font-size: 14px; color: rgba(8,16,31,0.55); }
.year-anchor-line { margin-top: 12px; padding: 8px 14px; background: rgba(168,37,47,0.08); border-left: 2px solid var(--stamp); font-family: 'Noto Sans SC'; font-size: 13px; color: rgba(8,16,31,0.7); }

/* Civic Impact · 知乎蓝主调 */
.civic-impact { background: linear-gradient(135deg, rgba(235,224,196,0.6), rgba(255,255,255,0.4)); border: 1px solid var(--zhihu); border-left: 4px solid var(--zhihu); padding: 56px 40px; margin: 64px 0 32px; position: relative; overflow: hidden; }
.civic-impact::after {
  content: "";
  position: absolute; top: -40px; right: -40px;
  width: 200px; height: 200px;
  background: radial-gradient(circle, rgba(23,81,153,0.08), transparent 70%);
  pointer-events: none;
}
.civic-impact > * { position: relative; z-index: 1; }
.civic-impact .ci-tag { font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 0.25em; color: var(--zhihu); }
.civic-impact .ci-pill { display: inline-block; margin-top: 12px; padding: 4px 12px; background: var(--zhihu); color: white; font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 0.15em; }
.civic-impact .ci-title { font-family: 'Noto Serif SC', serif; font-size: 28px; font-weight: 700; margin-top: 20px; line-height: 1.35; color: var(--ink); }
.civic-impact .ci-body { font-family: 'Noto Serif SC', serif; font-size: 16px; line-height: 1.85; color: rgba(8,16,31,0.85); margin-top: 24px; }
.civic-impact .ci-sign { margin-top: 28px; font-family: 'Noto Sans SC'; font-size: 13px; color: var(--mute); text-align: right; }

/* 时间轴左侧装饰:渐变色彩条暗示从远到近 */
.timeline .container::before { background: linear-gradient(180deg, var(--sepia) 0%, var(--sepia) 33%, var(--zhihu) 33%, var(--zhihu) 66%, var(--cyber) 66%, var(--cyber) 100%); opacity: 0.4; }

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
  <div style="display:flex; align-items:center; gap:8px;">
    <a class="nav-link" onclick="showHome()">本馆首页</a>
    <input id="nav-search" placeholder="输入老话题…" style="border:1px solid rgba(8,16,31,0.2); padding:6px 12px; font-family:'Noto Sans SC'; font-size:13px; outline:none; width:180px;" onkeydown="if(event.key==='Enter')doSearch(this.value)">
    <button class="nav-link" id="login-btn" onclick="loginZhihu()" style="border:1px solid rgba(8,16,31,0.2); background:transparent; padding:6px 12px; cursor:pointer; font-family:'Noto Sans SC';">登录知乎</button>
    <span id="user-info" style="display:none; align-items:center; gap:8px;">
      <button onclick="openMyPerspective()" style="background:var(--zhihu); color:white; border:none; padding:6px 14px; font-family:'Noto Sans SC'; font-size:13px; cursor:pointer; border-radius:2px;">👤 我的视角</button>
      <img id="user-avatar" style="width:28px; height:28px; border-radius:50%; border:1px solid rgba(8,16,31,0.1);">
      <span id="user-name" style="font-size:13px;"></span>
      <button onclick="logout()" style="background:transparent; border:none; color:var(--stamp); cursor:pointer; font-size:11px;">退出</button>
    </span>
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
  <div style="margin-top:48px; width:100%; max-width:560px;">
    <div style="display:flex; gap:0;">
      <input id="hero-search" placeholder="输入任意老话题,看它在知乎的十五年前世今生…"
             onkeydown="if(event.key==='Enter'){event.preventDefault(); doSearch(this.value);}"
             style="flex:1; padding:16px 20px; background:transparent; border:1px solid rgba(235,224,196,0.3); color:var(--paper); font-family:'Noto Serif SC',serif; font-size:16px; outline:none;">
      <button type="button" onclick="doSearch(document.getElementById('hero-search').value)" style="padding:16px 28px; background:var(--stamp); color:var(--paper); border:none; cursor:pointer; font-family:'Noto Sans SC'; font-size:14px;">检索档案</button>
    </div>
    <div style="margin-top:12px; font-family:'JetBrains Mono',monospace; font-size:10px; color:var(--mute); letter-spacing:0.15em;">
      EXAMPLES: ChatGPT 替代 · 共享单车 · 网瘾 · 区块链 · 二胎政策
    </div>
  </div>
  <div class="hero-hint">↓ 看今日知乎热榜,或翻阅本馆精选</div>
</section>

<!-- 今日热榜直达 -->
<section class="hotlist-section">
  <div class="container">
    <header class="hotlist-header">
      <div>
        <div class="hotlist-tag">LIVE FROM ZHIHU · 今日热榜 · 智能筛选</div>
        <h2 class="hotlist-title">让当下的热点,被时间检验</h2>
        <p class="hotlist-desc">扫描知乎实时热榜,**只保留有跨年代讨论沉淀的话题**(一次性时事新闻被过滤掉),从每条热榜里提取核心议题关键词,一键进入时光机。</p>
        <p class="hotlist-meta" id="hotlist-meta"></p>
      </div>
      <button id="hotlist-refresh" onclick="loadHotlist(true)" class="hotlist-refresh-btn">⟳ 刷新</button>
    </header>
    <div id="hotlist-loading" class="hotlist-loading">FETCHING 知乎热榜 ...</div>
    <div id="hotlist-grid" class="hotlist-grid" style="display:none;"></div>
  </div>
</section>


<section class="archive-section">
  <div class="container">
    <header class="section-header">
      <div class="section-tag">CURATOR'S TOP 7 · 策展人首推</div>
      <h2 class="section-title">本馆七大代表档案</h2>
      <p class="section-desc">关于「持续讨论 → 立法 / 政策 / 制度回应」的真实路径,加 AI 时代「焦虑 → 协作」的高速演变,以及知乎自己的十五年。点击任何一份,翻开它的情绪轨迹。</p>
    </header>
    <div class="featured-grid">
__FEATURED_CARDS__
    </div>
  </div>
</section>

<section class="archive-section archive-section-secondary">
  <div class="container">
    <div class="other-section-header">
      <div class="section-tag">FULL ARCHIVE · 馆藏全部 __OTHER_COUNT__ 份</div>
      <p class="section-desc" style="font-size:14px;">非首推但同样有完整时间跨度的档案,可点开看完整时光机</p>
    </div>
    <div class="topic-grid" style="margin-top:32px;">
__OTHER_CARDS__
    </div>
  </div>
</section>

<footer>
  时光档案馆 · 知乎黑客松 2026 参赛作品 · ALL ANSWERS LINK BACK TO ZHIHU
</footer>

</div>

<!-- 「我的视角」Modal -->
<div id="my-perspective" style="display:none; position:fixed; inset:0; background:rgba(8,16,31,0.85); z-index:100; backdrop-filter:blur(8px);" onclick="if(event.target===this) closeMyPerspective()">
  <div style="max-width:760px; margin:5vh auto; max-height:90vh; overflow-y:auto; background:var(--paper); padding:48px; position:relative;">
    <button onclick="closeMyPerspective()" style="position:absolute; top:16px; right:16px; background:transparent; border:1px solid rgba(8,16,31,0.2); padding:6px 12px; cursor:pointer; font-family:'Noto Sans SC'; font-size:12px;">✕ 关闭</button>

    <div style="font-family:'JetBrains Mono',monospace; font-size:11px; letter-spacing:0.25em; color:var(--zhihu); margin-bottom:8px;">MY PERSPECTIVE · 我的视角</div>
    <h2 style="font-family:'Noto Serif SC',serif; font-size:36px; margin-bottom:32px;">登录后,产品认识你</h2>

    <div id="mp-loading" style="text-align:center; padding:48px 0; color:var(--mute); font-family:'JetBrains Mono',monospace; letter-spacing:0.15em;">FETCHING YOUR DATA · 正在拉取知乎 OAuth 数据</div>
    <div id="mp-content" style="display:none;">

      <!-- Profile -->
      <section style="display:flex; gap:24px; align-items:flex-start; padding-bottom:28px; border-bottom:1px solid rgba(8,16,31,0.1);">
        <img id="mp-avatar" style="width:88px; height:88px; border-radius:50%; border:2px solid var(--zhihu);">
        <div style="flex:1;">
          <h3 id="mp-name" style="font-family:'Noto Serif SC',serif; font-size:28px;"></h3>
          <p id="mp-headline" style="font-family:'Noto Serif SC',serif; font-style:italic; color:rgba(8,16,31,0.7); margin-top:6px;"></p>
          <a id="mp-zhihu-link" target="_blank" rel="noopener" style="display:inline-block; margin-top:10px; font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--zhihu); letter-spacing:0.1em; border-bottom:1px dotted var(--zhihu); text-decoration:none;"></a>
        </div>
      </section>

      <!-- Stats -->
      <section style="display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-top:24px;">
        <div style="text-align:center; padding:18px; background:rgba(23,81,153,0.06); border-left:3px solid var(--zhihu);">
          <div id="mp-followed" style="font-family:'Noto Serif SC',serif; font-size:32px; font-weight:700; color:var(--zhihu);">—</div>
          <div style="font-family:'Noto Sans SC'; font-size:11px; color:var(--mute); letter-spacing:0.15em; margin-top:4px;">你关注的人</div>
        </div>
        <div style="text-align:center; padding:18px; background:rgba(74,124,89,0.06); border-left:3px solid var(--cyber);">
          <div id="mp-followers" style="font-family:'Noto Serif SC',serif; font-size:32px; font-weight:700; color:var(--cyber);">—</div>
          <div style="font-family:'Noto Sans SC'; font-size:11px; color:var(--mute); letter-spacing:0.15em; margin-top:4px;">你的粉丝</div>
        </div>
        <div style="text-align:center; padding:18px; background:rgba(241,182,68,0.10); border-left:3px solid var(--highlight);">
          <div id="mp-visits" style="font-family:'Noto Serif SC',serif; font-size:32px; font-weight:700; color:#8B6914;">—</div>
          <div style="font-family:'Noto Sans SC'; font-size:11px; color:var(--mute); letter-spacing:0.15em; margin-top:4px;">本馆访问足迹</div>
        </div>
      </section>

      <!-- 关注流 -->
      <section style="margin-top:36px;">
        <div style="font-family:'JetBrains Mono',monospace; font-size:11px; letter-spacing:0.25em; color:var(--mute);">FOLLOWING FEED · 你关注的人最近</div>
        <h3 style="font-family:'Noto Serif SC',serif; font-size:22px; margin:8px 0 16px;">他们在讨论什么</h3>
        <div id="mp-moments"></div>
      </section>

      <!-- 本馆访问记录 -->
      <section style="margin-top:36px;">
        <div style="font-family:'JetBrains Mono',monospace; font-size:11px; letter-spacing:0.25em; color:var(--mute);">VISIT HISTORY · 本馆足迹</div>
        <h3 style="font-family:'Noto Serif SC',serif; font-size:22px; margin:8px 0 16px;">你翻过的档案</h3>
        <div id="mp-visit-list"></div>
      </section>

    </div>
    <div id="mp-error" style="display:none; padding:32px; background:rgba(168,37,47,0.06); border-left:3px solid var(--stamp); font-family:'Noto Sans SC'; font-size:14px;"></div>
  </div>
</div>

<!-- Detail Views -->
__DETAIL_VIEWS__

<!-- 搜索结果视图(动态) -->
<div id="search-view" class="detail-view">
  <button class="back-btn" onclick="location.hash=''">← 返回本馆首页</button>
  <section class="detail-hero">
    <div class="container">
      <div class="detail-stamp" id="search-stamp">SEARCHING…</div>
      <h1 class="detail-title" id="search-title">检索中…</h1>
      <div class="detail-cat" id="search-meta">正在调用知乎搜索 API</div>
    </div>
  </section>
  <section class="timeline">
    <div class="container">
      <div id="search-loading" style="text-align:center; padding:80px 0; color:var(--mute); font-family:'JetBrains Mono',monospace; letter-spacing:0.2em;">
        FETCHING DATA · 抓取 · 启发式年份分桶 · 渲染时间轴
      </div>
      <div id="search-results"></div>
      <div id="search-publish" style="display:none; text-align:center; padding:48px 0;">
        <button onclick="publishCurrentSearch()" style="padding:14px 36px; background:var(--stamp); color:var(--paper); border:none; cursor:pointer; font-family:'Noto Sans SC'; font-size:14px;">
          📤 将本次检索发布到「黑客松脑洞补给站」想法
        </button>
      </div>
    </div>
  </section>
</div>

<script>
const DATA = __DATA_JSON__;
let currentSearch = null;

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
    // 记录访问足迹
    const title = el.querySelector('.detail-title')?.textContent || id;
    recordVisit(id, title);
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

// ───────── 搜索 ─────────

function escHtml(s) {
  return (s ?? '').toString().replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function doSearch(q) {
  console.log('[doSearch] called with:', q);
  q = (q || '').trim();
  if (!q) { console.warn('[doSearch] empty'); return; }
  location.hash = 'search?q=' + encodeURIComponent(q);
  document.getElementById('home').style.display = 'none';
  document.querySelectorAll('.detail-view').forEach(d => d.classList.remove('active'));
  document.getElementById('search-view').classList.add('active');
  document.getElementById('search-title').textContent = q;
  document.getElementById('search-stamp').textContent = 'CUSTOM SEARCH · 自定义检索';
  document.getElementById('search-meta').textContent = '正在调用知乎搜索 API…';
  document.getElementById('search-loading').style.display = 'block';
  document.getElementById('search-results').innerHTML = '';
  document.getElementById('search-publish').style.display = 'none';
  window.scrollTo(0, 0);

  try {
    const r = await fetch('/api/search?q=' + encodeURIComponent(q));
    const data = await r.json();
    currentSearch = data;
    renderSearchResults(data);
  } catch (e) {
    document.getElementById('search-loading').innerHTML = '<span style="color:var(--stamp)">检索失败:' + escHtml(e.message) + '</span>';
  }
}

function renderSearchResults(data) {
  document.getElementById('search-loading').style.display = 'none';
  const yc = data.year_count || 0;
  const years = Object.keys(data.by_year || {}).map(Number).sort();
  document.getElementById('search-meta').textContent = `${Object.values(data.by_year || {}).flat().length} 条档案 · ${yc} 个年份切片 · ${years[0] ?? '?'} → ${years.at(-1) ?? '?'}`;

  let html = '';
  for (const y of years) {
    const items = data.by_year[y] || [];
    const summary = data.summaries?.[y];
    const archives = items.slice(0, 6).map(it => `
      <div class="archive-item">
        <div class="meta">${escHtml(it.content_type || '-')} · ${escHtml(it.author_name || '匿名')} · 赞 ${it.vote_up_count} · ${escHtml(it.edit_year ?? '?')}</div>
        <a href="${escHtml(it.url)}" target="_blank" rel="noopener">
          <div class="a-title">${escHtml(it.title)}</div>
          <div class="a-text">${escHtml((it.content_text || '').slice(0, 180))}…</div>
        </a>
      </div>
    `).join('');

    html += `<article class="year-card">
      <div class="year-label">${y}</div>
      <div class="year-era">${items.length} 条原始档案</div>
      ${summary ? `<blockquote class="year-quote">「${escHtml(summary.representative_quote)}…」<cite>— <a href="${escHtml(summary.url)}" target="_blank" rel="noopener">${escHtml(summary.author || '匿名')}</a></cite></blockquote>` : ''}
      <div class="year-archive-toggle" onclick="toggleArchives(this)">↓ 展开档案条目(原始回答 + 真实链接)</div>
      <div class="year-archives">${archives}</div>
    </article>`;
  }
  if (!html) {
    html = '<div style="text-align:center; padding:80px 0; color:var(--mute); font-family:Noto Serif SC,serif; font-size:20px;">这个话题在知乎尚未找到时光档案<br><span style="font-size:12px;">请尝试更具体的关键词,如「ofo 退押金」「魏则西」</span></div>';
  } else {
    document.getElementById('search-publish').style.display = 'block';
  }
  html += `<div style="margin-top:48px; padding:24px; border:1px dashed rgba(8,16,31,0.2); font-size:12px; color:var(--mute); font-family:JetBrains Mono,monospace; letter-spacing:0.1em; text-align:center;">⚠ 自定义检索为实时数据,LLM 摘要功能因配额限制暂停,本馆精选 9 份档案已经过 AI 完整策展。</div>`;
  document.getElementById('search-results').innerHTML = html;
}

// ───────── OAuth 登录 / 发布 ─────────

async function loadMe() {
  try {
    const r = await fetch('/api/me');
    const me = await r.json();
    if (me.logged_in) {
      document.getElementById('login-btn').style.display = 'none';
      const u = document.getElementById('user-info');
      u.style.display = 'inline-flex';
      document.getElementById('user-name').textContent = me.name || '已登录';
      if (me.avatar) document.getElementById('user-avatar').src = me.avatar;
    }
  } catch (e) {}
}

function loginZhihu() {
  location.href = '/api/auth/zhihu';
}

async function logout() {
  await fetch('/api/logout', { method: 'POST' });
  location.reload();
}

// ───────── 今日热榜 ─────────

async function loadHotlist(forceRefresh = false) {
  const grid = document.getElementById('hotlist-grid');
  const loading = document.getElementById('hotlist-loading');
  const btn = document.getElementById('hotlist-refresh');
  loading.style.display = 'block';
  grid.style.display = 'none';
  if (btn) btn.disabled = true;

  try {
    const r = await fetch('/api/hotlist' + (forceRefresh ? '?t=' + Date.now() : ''));
    const data = await r.json();
    const items = data.items || [];
    if (!items.length) {
      loading.textContent = '热榜暂时拉不到 · 试试搜索栏';
      return;
    }
    grid.innerHTML = items.slice(0, 8).map((it, i) => {
      const cleanTitle = (it.title || '').replace(/\s+/g, ' ').trim();
      const q = it.time_travel_query || it.matched_keyword;
      const kw = it.matched_keyword || '';
      return `
        <div class="hotlist-card" onclick="doSearch('${escHtml(q).replace(/'/g, "\\'")}')">
          <div class="rank">HOT-${String(i+1).padStart(2,'0')}</div>
          <div class="from-title">${escHtml(cleanTitle.slice(0, 60))}${cleanTitle.length>60?'…':''}</div>
          <div class="extract-row">
            <span class="extract-label">提取关键词</span>
            <span class="extract-kw">${escHtml(kw)}</span>
          </div>
          <h3>看「${escHtml(q)}」的十五年</h3>
          <div class="cta">
            <span>→ 进入时光机</span>
            <a class="cta-zhihu" href="${escHtml(it.url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">原帖 ↗</a>
          </div>
        </div>
      `;
    }).join('');
    // 显示扫描统计
    const meta = data.total_scanned ? `扫描 ${data.total_scanned} 条热榜 → 过滤出 ${items.length} 条有时光机价值的话题` : '';
    const metaEl = document.getElementById('hotlist-meta');
    if (metaEl) metaEl.textContent = meta;
    loading.style.display = 'none';
    grid.style.display = 'grid';
  } catch (e) {
    loading.textContent = '热榜加载失败:' + e.message;
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ───────── 「我的视角」 ─────────

function recordVisit(id, title) {
  if (!id) return;
  try {
    const k = 'tma-visits';
    const arr = JSON.parse(localStorage.getItem(k) || '[]');
    const filtered = arr.filter(v => v.id !== id);
    filtered.unshift({ id, title, at: Date.now() });
    localStorage.setItem(k, JSON.stringify(filtered.slice(0, 20)));
  } catch (e) {}
}

function getVisits() {
  try {
    return JSON.parse(localStorage.getItem('tma-visits') || '[]');
  } catch (e) { return []; }
}

async function openMyPerspective() {
  const modal = document.getElementById('my-perspective');
  modal.style.display = 'block';
  document.getElementById('mp-loading').style.display = 'block';
  document.getElementById('mp-content').style.display = 'none';
  document.getElementById('mp-error').style.display = 'none';

  try {
    const r = await fetch('/api/me/profile');
    if (r.status === 401) {
      document.getElementById('mp-loading').style.display = 'none';
      document.getElementById('mp-error').style.display = 'block';
      document.getElementById('mp-error').textContent = '尚未登录,请先点「登录知乎」';
      return;
    }
    const data = await r.json();
    renderMyPerspective(data);
  } catch (e) {
    document.getElementById('mp-loading').style.display = 'none';
    document.getElementById('mp-error').style.display = 'block';
    document.getElementById('mp-error').textContent = '加载失败:' + e.message;
  }
}

function closeMyPerspective() {
  document.getElementById('my-perspective').style.display = 'none';
}

function renderMyPerspective(data) {
  document.getElementById('mp-loading').style.display = 'none';
  document.getElementById('mp-content').style.display = 'block';

  const u = data.user || {};
  document.getElementById('mp-avatar').src = u.avatar || '';
  document.getElementById('mp-name').textContent = u.fullname || '(无昵称)';
  document.getElementById('mp-headline').textContent = u.headline || u.description || '(无个人签名)';
  const link = document.getElementById('mp-zhihu-link');
  link.href = u.url || ('https://www.zhihu.com/people/' + u.hash_id);
  link.textContent = '→ ' + (u.url || ('zhihu.com/people/' + u.hash_id));

  document.getElementById('mp-followed').textContent = data.followed_total ?? '?';
  document.getElementById('mp-followers').textContent = data.followers_total ?? '?';

  const visits = getVisits();
  document.getElementById('mp-visits').textContent = visits.length;

  // 关注流
  const m = document.getElementById('mp-moments');
  if (!data.moments || !data.moments.length) {
    m.innerHTML = '<div style="padding:16px; font-family:\'Noto Sans SC\'; color:var(--mute); font-size:13px; background:rgba(8,16,31,0.04);">暂无关注流数据(OAuth 接口可能限制或你关注的人最近没发内容)</div>';
  } else {
    m.innerHTML = data.moments.map(mt => `
      <a href="${escHtml(mt.url)}" target="_blank" rel="noopener" style="display:block; padding:16px; border-bottom:1px dashed rgba(8,16,31,0.12); text-decoration:none; color:var(--ink);">
        <div style="font-family:'Noto Serif SC',serif; font-size:16px; font-weight:500;">${escHtml(mt.title || mt.excerpt.slice(0, 50))}</div>
        ${mt.excerpt ? `<div style="font-size:13px; color:rgba(8,16,31,0.65); margin-top:6px; line-height:1.6;">${escHtml(mt.excerpt)}…</div>` : ''}
        ${mt.author ? `<div style="font-family:'JetBrains Mono',monospace; font-size:10px; color:var(--mute); margin-top:8px; letter-spacing:0.1em;">— ${escHtml(mt.author)}</div>` : ''}
      </a>
    `).join('');
  }

  // 本馆访问足迹
  const v = document.getElementById('mp-visit-list');
  if (!visits.length) {
    v.innerHTML = '<div style="padding:16px; font-family:\'Noto Sans SC\'; color:var(--mute); font-size:13px;">还没翻过任何档案 — 关闭弹窗,去首页选一个档案吧</div>';
  } else {
    v.innerHTML = visits.slice(0, 8).map(vt => `
      <a href="#${escHtml(vt.id)}" onclick="closeMyPerspective()" style="display:flex; justify-content:space-between; align-items:baseline; padding:12px 0; border-bottom:1px dashed rgba(8,16,31,0.1); text-decoration:none; color:var(--ink);">
        <span style="font-family:'Noto Serif SC',serif; font-size:15px;">${escHtml(vt.title || vt.id)}</span>
        <span style="font-family:'JetBrains Mono',monospace; font-size:10px; color:var(--mute);">${new Date(vt.at).toLocaleString()}</span>
      </a>
    `).join('');
  }
}

async function publishCurrentSearch() {
  if (!currentSearch) return;
  const q = currentSearch.q;
  const years = Object.keys(currentSearch.summaries || {}).map(Number).sort();
  if (years.length < 2) {
    alert('当前检索数据不足,无法发布');
    return;
  }
  const lines = years.map(y => `[${y}] ${currentSearch.summaries[y].representative_quote.slice(0, 50)}…`);
  const content = `我在《时光档案馆》查了「${q}」的十五年观点演变:\n\n${lines.join('\n')}\n\n完整时间轴见:http://localhost:7777/#search?q=${encodeURIComponent(q)}\n\n#知乎黑客松2026 #时光档案馆`;
  if (!confirm(`将发布以下想法到「黑客松脑洞补给站」圈子:\n\n${content.slice(0, 300)}…\n\n确认?`)) return;
  try {
    const r = await fetch('/api/publish/pin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });
    const data = await r.json();
    if (data.status === 0) {
      alert('✅ 已发布!想法 token: ' + data.data?.content_token);
    } else {
      alert('❌ 发布失败:' + JSON.stringify(data));
    }
  } catch (e) {
    alert('❌ 网络错误:' + e.message);
  }
}

// ───────── 路由 ─────────

function route() {
  const h = location.hash.replace(/^#/, '');
  if (h.startsWith('search?q=')) {
    const q = decodeURIComponent(h.slice(9));
    if (currentSearch?.q === q) {
      // 已经在这个搜索页
      document.getElementById('home').style.display = 'none';
      document.querySelectorAll('.detail-view').forEach(d => d.classList.remove('active'));
      document.getElementById('search-view').classList.add('active');
    } else {
      doSearch(q);
    }
  } else if (h && DATA[h]) {
    showDetail(h);
  } else {
    showHome();
  }
}

window.addEventListener('hashchange', route);
window.addEventListener('load', () => {
  loadMe();
  loadHotlist();
  route();
  // 登录成功提示
  if (new URLSearchParams(location.search).get('login') === 'ok') {
    alert('登录成功');
    history.replaceState({}, '', location.pathname + location.hash);
  }
});
</script>

</body>
</html>"""


def render_topic_card(t: dict, featured: bool = False) -> str:
    years = sorted([int(y) for y in t.get("year_summaries", {}).keys()])
    mt_years = sorted([int(y) for y in t.get("mood_track", {}).keys()]) or years
    early_year = years[0] if years else None
    late_year = years[-1] if years else None
    early_q = t["year_summaries"].get(str(early_year), {}).get("golden_quote", "") if early_year else ""
    late_q = t["year_summaries"].get(str(late_year), {}).get("golden_quote", "") if late_year else ""
    raw_count = len(t.get("raw_answers", []))
    quote_count = len(t.get("year_summaries", {}))
    yr_range = f"{min(mt_years)}–{max(mt_years)}" if mt_years else "—"
    civic = t.get("civic_impact") or {}
    civic_tag = civic.get("tag", "")

    # 迷你情绪条(从 mood_track 拿)
    mini_track = ""
    mt = t.get("mood_track", {})
    if mt:
        items = sorted(mt.items(), key=lambda kv: int(kv[0]))
        cells = []
        for y, p in items:
            mood = p[0] if isinstance(p, list) and len(p) > 0 else "calm"
            intensity = float(p[1]) if isinstance(p, list) and len(p) > 1 else 0.3
            color = MOOD_COLORS.get(mood, "#5A6478")
            cells.append(f'<span class="mt-cell" style="background:{color}; opacity:{0.4 + intensity * 0.55:.2f}"></span>')
        mini_track = f'<div class="mini-mood-track">{"".join(cells)}</div>'

    klass = "topic-card featured" if featured else "topic-card"
    civic_html = f'<div class="card-civic-pill">{esc(civic_tag)}</div>' if civic_tag and featured else ""

    return f"""<article class="{klass}" onclick="location.hash='{esc(t['id'])}'">
  <div class="topic-stamp">ARCHIVE-{(hash(t['id']) % 1000):03d}</div>
  <div class="cat">{esc(t.get('category','—'))} · {esc(yr_range)}</div>
  <h3>{esc(t['title'])}</h3>
  {civic_html}
  <div class="quotes">
    <div class="quote-old">「{esc(early_q)}」<span class="year-tag">{early_year}</span></div>
    <div class="quote-new">「{esc(late_q)}」<span class="year-tag">{late_year}</span></div>
  </div>
  {mini_track}
  <div class="data-bar">
    <span>{raw_count} 条档案</span>
    <span>{quote_count} 个切片</span>
    <span>跨度 {(max(mt_years) - min(mt_years)) if mt_years and len(mt_years) > 1 else 0} 年</span>
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
    event_anchor = topic.get("event_anchors", {}).get(str(year))

    has_summary = bool(s)
    archives_html = render_archives_in_year(topic, year)
    has_archives = bool(archives_html.strip())

    # 三时代视觉:2008-2014 era-old, 2015-2020 era-mid, 2021-2026 era-new
    if year <= 2014:
        era_class = "era-old"
    elif year <= 2020:
        era_class = "era-mid"
    else:
        era_class = "era-new"

    # 时代装饰 SVG(每个年份卡右上角的「时代质感」)
    if era_class == "era-old":
        # 7x7 报纸网点
        dots = ""
        for row in range(7):
            for col in range(7):
                cx = 8 + col * 11
                cy = 8 + row * 11
                # 不规则强度,模拟报纸印刷
                r = 1.5 + ((col * 3 + row) % 3) * 0.6
                dots += f'<circle cx="{cx}" cy="{cy}" r="{r}"/>'
        era_deco_svg = f'<svg class="era-decoration era-decoration-old" viewBox="0 0 80 80">{dots}</svg>'
    elif era_class == "era-mid":
        # 流体曲线 + 节点 — 移动互联网数据流
        era_deco_svg = (
            '<svg class="era-decoration era-decoration-mid" viewBox="0 0 80 80">'
            '<path d="M 10 20 Q 25 8, 40 30 T 70 50" />'
            '<path d="M 10 50 Q 30 35, 50 55 T 75 35" opacity="0.6"/>'
            '<circle cx="10" cy="20" r="2.5"/><circle cx="40" cy="30" r="2.5"/>'
            '<circle cx="70" cy="50" r="2.5"/><circle cx="50" cy="55" r="2"/>'
            '</svg>'
        )
    else:
        # 神经网络节点 — AI 时代
        era_deco_svg = (
            '<svg class="era-decoration era-decoration-new" viewBox="0 0 80 80">'
            '<defs><linearGradient id="cyber-grad" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0%" stop-color="{MOOD_COLORS["hope"]}"/>'
            f'<stop offset="100%" stop-color="{MOOD_COLORS["concern"]}"/>'
            '</linearGradient></defs>'
            # 三层节点
            '<line x1="14" y1="20" x2="40" y2="14"/>'
            '<line x1="14" y1="20" x2="40" y2="40"/>'
            '<line x1="14" y1="20" x2="40" y2="60"/>'
            '<line x1="14" y1="40" x2="40" y2="14"/>'
            '<line x1="14" y1="40" x2="40" y2="40"/>'
            '<line x1="14" y1="40" x2="40" y2="60"/>'
            '<line x1="14" y1="60" x2="40" y2="40"/>'
            '<line x1="14" y1="60" x2="40" y2="60"/>'
            '<line x1="40" y1="14" x2="68" y2="30"/>'
            '<line x1="40" y1="40" x2="68" y2="30"/>'
            '<line x1="40" y1="40" x2="68" y2="55"/>'
            '<line x1="40" y1="60" x2="68" y2="55"/>'
            # nodes
            '<circle cx="14" cy="20" r="2.5"/><circle cx="14" cy="40" r="2.5"/><circle cx="14" cy="60" r="2.5"/>'
            '<circle cx="40" cy="14" r="3"/><circle cx="40" cy="40" r="3"/><circle cx="40" cy="60" r="3"/>'
            '<circle cx="68" cy="30" r="3.5"/><circle cx="68" cy="55" r="3.5"/>'
            '</svg>'
        )

    # 情况 1: 有 LLM summary → 完整卡
    if has_summary:
        quote = s.get("golden_quote", "—")
        primary = s.get("primary_view", "")
        secondary = s.get("secondary_view", "")
        era = s.get("era_caption", "") or event_anchor or ""
        author = s.get("quote_author", "")
        quote_url = s.get("quote_url", "")
        cite_html = ""
        if author:
            if quote_url:
                cite_html = f'<cite>— <a href="{esc(quote_url)}" target="_blank" rel="noopener">{esc(author)}</a></cite>'
            else:
                cite_html = f'<cite>— {esc(author)}</cite>'
        secondary_html = f'<p class="secondary">{esc(secondary)}</p>' if secondary else ""
        anchor_html = f'<div class="year-anchor-line">📌 {esc(event_anchor)}</div>' if event_anchor and event_anchor not in era else ""
        archive_toggle = f'<div class="year-archive-toggle" onclick="toggleArchives(this)">↓ 展开档案条目(原始回答 + 真实链接)</div><div class="year-archives">{archives_html}</div>' if has_archives else ""
        return f"""<article class="year-card {era_class}">
  {era_deco_svg}
  <div class="year-label">{year}</div>
  <div class="year-era">{esc(era)}</div>
  {anchor_html}
  <blockquote class="year-quote">「{esc(quote)}」{cite_html}</blockquote>
  <div class="year-views">
    <p class="primary">{esc(primary)}</p>
    {secondary_html}
  </div>
  {archive_toggle}
</article>"""

    # 情况 2: 没 summary,但有 event_anchor 或 archives → 简化卡
    if event_anchor or has_archives:
        archive_toggle = f'<div class="year-archive-toggle" onclick="toggleArchives(this)">↓ 展开档案条目</div><div class="year-archives">{archives_html}</div>' if has_archives else ""
        return f"""<article class="year-card year-card-thin {era_class}">
  <div class="year-label year-label-thin">{year}</div>
  <div class="year-anchor-only">{esc(event_anchor or '此年档案待补')}</div>
  {archive_toggle}
</article>"""

    return ""


def render_civic_impact(topic: dict) -> str:
    ci = topic.get("civic_impact")
    if not ci:
        return ""
    return f"""<section class="civic-impact">
  <div class="ci-tag">CIVIC IMPACT · 知乎的积极作用</div>
  <div class="ci-pill">{esc(ci.get('tag', ''))}</div>
  <h2 class="ci-title">{esc(ci['title'])}</h2>
  <div class="ci-body">{esc(ci['body']).replace(chr(10), '<br><br>')}</div>
  <div class="ci-sign">— 策展人 · 看山</div>
</section>"""


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


MOOD_COLORS = {
    "calm":    "#5A6478",  # 平淡蓝灰
    "concern": "#C8973C",  # 担忧暗黄
    "outrage": "#A8252F",  # 愤怒红
    "hope":    "#4A7C59",  # 希望深绿
}

MOOD_LABELS_CN = {
    "calm":    "平淡",
    "concern": "担忧",
    "outrage": "愤怒",
    "hope":    "转机",
}


def render_mood_track_svg(t: dict) -> str:
    """情绪轨迹图:横向年份色块 + 关键事件 45 度斜排标注 + 三时代分隔"""
    mt = t.get("mood_track", {})
    if not mt:
        return ""
    items = sorted(mt.items(), key=lambda kv: int(kv[0]))
    years = [int(y) for y, _ in items]
    if not years:
        return ""

    min_y, max_y = min(years), max(years)
    span = max_y - min_y if max_y > min_y else 1

    # SVG 尺寸 — 加大底部 padding 给倾斜事件文字
    W = 760
    H = 360
    PAD_L = 28
    PAD_R = 28
    PAD_T = 40
    PAD_B = 200   # 大幅加大,留给 45° 事件文字
    plot_w = W - PAD_L - PAD_R
    plot_h = H - PAD_T - PAD_B

    def x_at(year):
        return PAD_L + (year - min_y) / span * plot_w

    cell_w = plot_w / max(span, 1) if span else 32

    # 三时代分隔(2014/2020 边界)
    era_dividers = []
    era_labels = []
    for boundary, label in [(2014.5, ""), (2020.5, "")]:
        if min_y <= boundary <= max_y:
            x = x_at(boundary)
            era_dividers.append(
                f'<line x1="{x:.1f}" y1="{PAD_T}" x2="{x:.1f}" y2="{PAD_T + plot_h + 18}" stroke="rgba(8,16,31,0.25)" stroke-dasharray="3,3" />'
            )
    # 三时代背景色带
    era_zones = []
    ZONE_OLD = (min_y, min(2014, max_y))
    ZONE_MID = (max(2015, min_y), min(2020, max_y)) if 2015 <= max_y and min_y <= 2020 else None
    ZONE_NEW = (max(2021, min_y), max_y) if max_y >= 2021 else None
    if ZONE_OLD[1] >= ZONE_OLD[0]:
        x1 = x_at(ZONE_OLD[0]) - cell_w / 2
        x2 = x_at(ZONE_OLD[1]) + cell_w / 2
        era_zones.append(f'<rect x="{x1:.1f}" y="{PAD_T}" width="{x2-x1:.1f}" height="{plot_h}" fill="rgba(107,68,35,0.06)" />')
        era_zones.append(f'<text x="{(x1+x2)/2:.1f}" y="{PAD_T - 12}" text-anchor="middle" class="era-zone-label era-old-label">2008-2014 · 旧报纸</text>')
    if ZONE_MID:
        x1 = x_at(ZONE_MID[0]) - cell_w / 2
        x2 = x_at(ZONE_MID[1]) + cell_w / 2
        era_zones.append(f'<rect x="{x1:.1f}" y="{PAD_T}" width="{x2-x1:.1f}" height="{plot_h}" fill="rgba(23,81,153,0.06)" />')
        era_zones.append(f'<text x="{(x1+x2)/2:.1f}" y="{PAD_T - 12}" text-anchor="middle" class="era-zone-label era-mid-label">2015-2020 · 博客时代</text>')
    if ZONE_NEW:
        x1 = x_at(ZONE_NEW[0]) - cell_w / 2
        x2 = x_at(ZONE_NEW[1]) + cell_w / 2
        era_zones.append(f'<rect x="{x1:.1f}" y="{PAD_T}" width="{x2-x1:.1f}" height="{plot_h}" fill="rgba(74,124,89,0.07)" />')
        era_zones.append(f'<text x="{(x1+x2)/2:.1f}" y="{PAD_T - 12}" text-anchor="middle" class="era-zone-label era-new-label">2021-2026 · 赛博</text>')

    blocks = []
    labels = []
    events = []

    for y, payload in items:
        year = int(y)
        if isinstance(payload, list) and len(payload) >= 2:
            mood, intensity = payload[0], float(payload[1])
            evt = payload[2] if len(payload) > 2 else ""
        else:
            mood, intensity, evt = "calm", 0.3, ""

        color = MOOD_COLORS.get(mood, "#5A6478")
        height = 15 + intensity * (plot_h - 20)
        x = x_at(year) - cell_w / 2 + 2
        w = cell_w - 4
        y_pos = PAD_T + plot_h - height

        blocks.append(
            f'<rect x="{x:.1f}" y="{y_pos:.1f}" width="{w:.1f}" height="{height:.1f}" fill="{color}" opacity="{0.55 + intensity * 0.4:.2f}" rx="2"></rect>'
        )

        # 年份标签
        labels.append(
            f'<text x="{x_at(year):.1f}" y="{H - PAD_B + 18}" text-anchor="middle" class="mood-year">{year}</text>'
        )

        # 事件文字 45 度斜排,所有有事件且强度 >= 0.4 的都展示
        if evt and intensity >= 0.4:
            event_x = x_at(year)
            event_y = H - PAD_B + 32
            events.append(
                f'<text x="{event_x:.1f}" y="{event_y}" '
                f'transform="rotate(45 {event_x:.1f} {event_y})" '
                f'class="mood-event" fill="{color}">{esc(evt)}</text>'
            )

    legend = "".join(
        f'<g transform="translate({i * 88},0)">'
        f'<rect x="0" y="0" width="14" height="14" fill="{MOOD_COLORS[m]}" rx="2"></rect>'
        f'<text x="20" y="11" class="mood-legend">{MOOD_LABELS_CN[m]}</text>'
        f'</g>'
        for i, m in enumerate(["calm", "concern", "outrage", "hope"])
    )

    return f"""<section class="mood-chart-section">
  <header class="mood-header">
    <span class="mood-tag">EMOTION TIMELINE · 情绪轨迹</span>
    <span class="mood-meta">{len(items)} 年数据 · 色块高度 = 讨论强度 · 横向看时代,纵向看情绪</span>
  </header>
  <svg viewBox="0 0 {W} {H}" class="mood-svg" preserveAspectRatio="xMidYMid meet">
    {''.join(era_zones)}
    {''.join(era_dividers)}
    <line x1="{PAD_L}" y1="{PAD_T + plot_h:.1f}" x2="{W - PAD_R}" y2="{PAD_T + plot_h:.1f}" stroke="rgba(8,16,31,0.25)"></line>
    {''.join(blocks)}
    {''.join(labels)}
    {''.join(events)}
  </svg>
  <div class="mood-legend-row">
    <svg viewBox="0 0 360 16" class="mood-legend-svg">{legend}</svg>
  </div>
</section>"""


def render_detail_view(t: dict) -> str:
    summary_years = sorted(int(y) for y in t.get("year_summaries", {}).keys())
    # 只展示有 LLM summary 的年份 — 体现"时间跨度"靠 mood_track 可视化
    cards = []
    prev_era = None
    for y in summary_years:
        if y <= 2014:
            cur_era = "old"
        elif y <= 2020:
            cur_era = "mid"
        else:
            cur_era = "new"
        # 在 era 切换处插分隔标记
        if prev_era and prev_era != cur_era:
            if cur_era == "mid":
                cards.append('<div class="era-divider to-mid">— ENTERING · 2015 · 博客时代 —</div>')
            elif cur_era == "new":
                cards.append('<div class="era-divider to-new">— ENTERING · 2021 · 赛博时代 —</div>')
        rendered = render_year_card(t, y)
        if rendered:
            cards.append(rendered)
            prev_era = cur_era

    pred = render_prediction(t) if t.get("prediction") else ""
    civic = render_civic_impact(t)
    mood_chart = render_mood_track_svg(t)

    mt_years = sorted([int(y) for y in t.get("mood_track", {}).keys()]) or sorted(summary_years)
    return f"""<div id="detail-{esc(t['id'])}" class="detail-view">
  <button class="back-btn" onclick="location.hash=''">← 返回本馆首页</button>
  <section class="detail-hero">
    <div class="container">
      <div class="detail-stamp">ARCHIVE-{(hash(t['id']) % 1000):03d} · {esc(t.get('category','—'))}</div>
      <h1 class="detail-title">{esc(t['title'])}</h1>
      <div class="detail-cat">{len(t.get('raw_answers', []))} 条档案 · {len(summary_years)} 个深度切片 · 跨度 {min(mt_years) if mt_years else '?'} → {max(mt_years) if mt_years else '?'}</div>
    </div>
  </section>
  <section class="timeline">
    <div class="container">
      {mood_chart}
      {''.join(cards)}
      {civic}
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

    # TOP 7 推荐(针对评委关注点 + 时间纵深 + 立法案例)
    FEATURED_IDS = [
        "chatgpt-after",     # AI 三年 · 高速演变 (李笛/李大海/颜鑫)
        "zhihu-itself",      # 知乎自指(周源/张荣乐)
        "yang-yongxin",      # 18 年立法链路
        "996-icu",           # 讨论 → 司法表态
        "phone-scam",        # 反诈立法(史中/emmett)
        "china-open-source", # 中国开源(颜鑫/李大海)
        "ofo-deposit",       # 群体自救 → 监管
    ]
    featured = [t for t in topics if t["id"] in FEATURED_IDS]
    # 保持 FEATURED_IDS 的顺序
    featured.sort(key=lambda t: FEATURED_IDS.index(t["id"]))
    other = [t for t in topics if t["id"] not in FEATURED_IDS]

    featured_cards = "\n".join(render_topic_card(t, featured=True) for t in featured)
    other_cards = "\n".join(render_topic_card(t, featured=False) for t in other)

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
    html = html.replace("__FEATURED_CARDS__", featured_cards)
    html = html.replace("__OTHER_CARDS__", other_cards)
    html = html.replace("__OTHER_COUNT__", str(len(other)))
    html = html.replace("__DETAIL_VIEWS__", details)
    html = html.replace("__DATA_JSON__", json.dumps(data_for_js, ensure_ascii=False))

    out = DIST / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"✅ 渲染到 {out}  ({len(html)/1024:.1f} KB)")

    # 同步到 public/(Vercel 部署目录)
    public = ROOT / "public"
    public.mkdir(exist_ok=True)
    (public / "index.html").write_text(html, encoding="utf-8")
    # 同步 api/data/(serverless function 内部数据)
    api_data = ROOT / "api" / "data"
    api_data.mkdir(parents=True, exist_ok=True)
    for f in DATA_DIR.glob("*.json"):
        (api_data / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"✅ 同步到 public/ + api/data/(供 Vercel 部署)")


if __name__ == "__main__":
    main()
