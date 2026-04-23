# 《时光答》实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 48 小时内产出可在路演现场稳定 Demo 的《时光答》 Web 产品,实现"输入话题 → 看历史观点演变 → AI 预测 2029 → 一键生成海报发布知乎想法"的全链路。

**Architecture:** Next.js 14 全栈单体 + Python 离线数据管线(赛前跑完,产出 JSON/入库数据供运行时读)+ Supabase(Postgres)持久层 + Vercel 部署。前端纯静态/ISR,运行时只有搜索兜底 + 2029 预测调 LLM,其他走缓存。

**Tech Stack:** Next.js 14 App Router · TypeScript · Tailwind · Framer Motion · Supabase · satori (poster) · DeepSeek / Claude Haiku / 知乎直答 Agent · Python 3.11 (离线管线) · Vercel

---

## 📦 前置材料清单(按序凑齐 = 零阻塞开干)

| # | 材料 | 来源 | 没有的替代方案 | 必需? |
|---|---|---|---|---|
| M1 | **知乎开放平台 OAuth client_id / secret / redirect_uri** | Hackathon 报名后由组委会发放 | 无替代,必须等官方 | ⭐ 必需 |
| M2 | **知乎开放平台 access_token(管理员级)** | 组委会或 OAuth 流程自取 | OAuth 走用户授权 | ⭐ 必需 |
| M3 | **知乎专属圈子 ID(用于 /openapi/publish/pin)** | 手册里的 ring/moltbook 或后续指定 | 若无则只生成海报图、跳过一键发布 | ⭐ 必需(发布链路) |
| M4 | **DeepSeek API key**(离线管线主力) | platform.deepseek.com | 换成 Claude Haiku 4.5 API key(Anthropic) | ⭐ 二选一必需 |
| M5 | **Claude Haiku 4.5 API key**(质检 + fallback) | console.anthropic.com | 可用 DeepSeek 单跑 | 🟡 建议 |
| M6 | **OpenAI embedding API key**(聚类) | platform.openai.com | 换 bge-m3 本地推理(下载 4GB 模型) | 🟡 建议 |
| M7 | **Supabase 项目**(URL + anon key + service_role key) | supabase.com 免费档 | 换成本地 Postgres + 部署时换 Neon/Railway | ⭐ 必需 |
| M8 | **Vercel 账号 + GitHub repo 授权** | vercel.com | 换 Cloudflare Pages / Netlify(流程类似) | ⭐ 必需(部署) |
| M9 | **域名(可选)** | 任意注册商 | Vercel 默认 `*.vercel.app` | ❌ 非必需 |
| M10 | **话题候选池初稿(30 个)** | `data/topics.seed.json`,赛前手工列 | Task P0-T2 会给模板,直接填即可 | ⭐ 必需 |
| M11 | **视觉稿 / 设计 tokens**(色板、字体、海报模板) | 自己画 or 找设计师朋友 | 按 spec 附录 C 的设计语言直接落,Task P2 有默认方案 | 🟡 建议 |
| M12 | **知乎账号 × 2**(一个发布测试、一个路演演示) | 自有或新注册 | 单账号也行,但演示账号最好干净 | ⭐ 必需 |
| M13 | **刘看山 IP 素材包** | 手册或官方素材库 | 海报角落的"by 刘看山推荐"印章,也可先空着 | ❌ 可后补 |
| M14 | **本机 Node 20+ / Python 3.11+ / git / pnpm / uv** | 本地环境 | pnpm 可换 npm,uv 可换 pip | ⭐ 必需 |

**完整 `.env.local` 模板**(P0-T1 里会生成 `.env.example`):
```
ZHIHU_CLIENT_ID=
ZHIHU_CLIENT_SECRET=
ZHIHU_REDIRECT_URI=https://shiguangda.vercel.app/api/auth/callback
ZHIHU_ACCESS_TOKEN=            # 用于离线管线调搜索/热榜/直答
ZHIHU_RING_ID=moltbook         # 发帖目标圈子
DEEPSEEK_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=                # 仅 embedding
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SENTRY_DSN=                    # 可选
```

---

## 🗂 文件结构(开工前先看这张图)

```
/Users/pingfan/projects/Zhihu/
├── .env.local                               # 私密,不提交
├── .env.example                             # 提交
├── .gitignore
├── package.json                             # pnpm
├── next.config.mjs
├── tailwind.config.ts
├── tsconfig.json
├── vercel.json                              # cron 配置
├── README.md                                # 产品说明 (提报材料)
├── data/
│   ├── topics.seed.json                     # 30 话题候选
│   ├── events.seed.json                     # 事件锚点库(2011-2026)
│   └── cache/                               # 离线管线产出 JSON (可选落盘)
├── scripts/                                 # Python 离线管线
│   ├── pyproject.toml                       # uv 管理
│   ├── _lib/
│   │   ├── zhihu_api.py
│   │   ├── llm.py
│   │   └── db.py
│   ├── 01_fetch_answers.py
│   ├── 02_bucket_by_year.py
│   ├── 03_cluster_opinions.py
│   ├── 04_extract_quotes.py
│   ├── 05_attach_events.py
│   ├── 06_predict_2029.py
│   └── 07_import_to_db.py
├── supabase/
│   └── migrations/0001_init.sql
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                         # 首页
│   │   ├── topic/[id]/page.tsx              # 话题页
│   │   ├── search/page.tsx                  # 搜索兜底落地
│   │   └── api/
│   │       ├── topics/list/route.ts
│   │       ├── topics/[id]/route.ts
│   │       ├── search/route.ts
│   │       ├── predict/[id]/route.ts
│   │       ├── poster/[id]/route.tsx        # satori
│   │       ├── publish/route.ts
│   │       ├── hotlist-today/route.ts       # cron
│   │       └── auth/
│   │           ├── zhihu/route.ts
│   │           └── callback/route.ts
│   ├── components/
│   │   ├── HomeBanner.tsx
│   │   ├── TopicCard.tsx
│   │   ├── TopicGrid.tsx
│   │   ├── SearchBox.tsx
│   │   ├── Timeline.tsx
│   │   ├── YearCard.tsx
│   │   ├── EventAnchor.tsx
│   │   ├── PredictCard.tsx
│   │   └── PosterButton.tsx
│   ├── lib/
│   │   ├── zhihu.ts                         # 知乎 API 封装 (运行时)
│   │   ├── llm.ts
│   │   ├── supabase.ts
│   │   ├── poster.tsx                       # satori 模板
│   │   └── types.ts
│   └── styles/globals.css
└── tests/
    ├── lib/zhihu.test.ts
    ├── lib/poster.test.ts
    └── scripts/cluster_opinions.test.py
```

---

## 🏗 阶段总览

| 阶段 | 时间窗 | 核心产出 |
|---|---|---|
| **Phase 0 · 赛前准备** | 5/11 前 | 脚手架 + 凭证 + 话题池 + 视觉稿 |
| **Phase 1 · 离线数据管线** | 5/11 - 5/12 上午 | 30 话题 × 16 年全量数据入库 |
| **Phase 2 · 前端骨架** | 5/12 13:00-18:00 | 首页 + 话题页 + 时间轴 |
| **Phase 3 · 运行时 API + 搜索兜底** | 5/12 18:00-24:00 | 预测 / 搜索 / 今日热榜 |
| **Phase 4 · 海报 + 分享 + OAuth** | 5/13 上午 | 海报生成 + 一键发布 |
| **Phase 5 · Polish + 部署** | 5/13 下午 | 移动端 / 错误降级 / Vercel 上线 |
| **Phase 6 · 占位 + 演示** | 5/13 晚 - 5/14 上午 | 发海报 / 录视频 / 提报 |

---

## Phase 0 · 赛前准备

### Task P0-T1:脚手架与依赖

**Files:**
- Create: `package.json`, `next.config.mjs`, `tailwind.config.ts`, `tsconfig.json`, `.env.example`
- Create: `src/app/layout.tsx`, `src/app/page.tsx`, `src/styles/globals.css`

- [ ] **Step 1:** 在项目根执行初始化

```bash
pnpm create next-app@14 . --typescript --tailwind --app --no-src-dir --import-alias "@/*" --use-pnpm
# 安装后调整:
mkdir src && mv app src/ && mv ... # Next 的 src-dir 结构,按实际调
pnpm add framer-motion @supabase/supabase-js zod satori resvg-js
pnpm add -D vitest @testing-library/react jsdom
```

- [ ] **Step 2:** 创建 `.env.example`,贴入前置材料清单里列的所有变量名(值留空)

- [ ] **Step 3:** 在 `tailwind.config.ts` 注入品牌色板和字体:

```ts
// tailwind.config.ts 关键片段
theme: {
  extend: {
    colors: {
      ink: '#0B1026',      // 深夜蓝
      paper: '#F4E4BA',    // 旧纸米黄
      stamp: '#E63946',    // 红印章
    },
    fontFamily: {
      song: ['"Noto Serif SC"', 'serif'],
      hei:  ['"Noto Sans SC"', 'sans-serif'],
    },
  },
}
```

- [ ] **Step 4:** `src/styles/globals.css` 引入字体 CDN(思源宋体/黑体)

- [ ] **Step 5:** 跑一遍

```bash
pnpm dev
# 访问 http://localhost:3000 看到默认页即可
```

- [ ] **Step 6:** 提交

```bash
git add -A
git commit -m "feat: bootstrap Next.js scaffold with tailwind + fonts"
```

---

### Task P0-T2:话题候选池模板

**Files:**
- Create: `data/topics.seed.json`
- Create: `data/events.seed.json`

- [ ] **Step 1:** `data/topics.seed.json` 按此 schema 填 30 条(先填 5-10 条,其余赛前补完):

```json
[
  {
    "id": "programmer-35",
    "title": "程序员 35 岁之后会怎样?",
    "question_id": "22068119",
    "category": "职场",
    "featured_rank": 1,
    "search_keywords": ["35岁 程序员", "大龄程序员", "程序员中年危机"]
  },
  {
    "id": "marriage-brideprice",
    "title": "你怎么看待彩礼这件事?",
    "question_id": "",
    "category": "婚恋",
    "featured_rank": 2,
    "search_keywords": ["彩礼", "天价彩礼", "彩礼 多少合适"]
  }
]
```

**候选池指引**(挑选标准):① 话题在 2011-2026 至少有 3 年高赞答沉淀 ② 主流观点有明显代际差异 ③ 具有争议或共鸣

- [ ] **Step 2:** `data/events.seed.json` 填事件锚点(约 20 条):

```json
[
  { "year": 2013, "title": "微信崛起", "category": "科技" },
  { "year": 2015, "title": "双创热潮", "category": "经济" },
  { "year": 2015, "title": "A 股股灾", "category": "经济" },
  { "year": 2016, "title": "知识付费元年", "category": "文化" },
  { "year": 2018, "title": "互联网寒冬 / 中兴禁令", "category": "科技" },
  { "year": 2019, "title": "996.ICU 反对运动", "category": "职场" },
  { "year": 2020, "title": "新冠疫情爆发", "category": "社会" },
  { "year": 2021, "title": "双减 / 共同富裕", "category": "社会" },
  { "year": 2022, "title": "ChatGPT 发布", "category": "科技" },
  { "year": 2022, "title": "互联网大厂首波裁员", "category": "职场" },
  { "year": 2023, "title": "大模型爆发年", "category": "科技" },
  { "year": 2024, "title": "AI 替代白领白热化", "category": "科技" },
  { "year": 2025, "title": "AI Agent 元年", "category": "科技" },
  { "year": 2025, "title": "一线城市白领二次裁员", "category": "职场" }
]
```

- [ ] **Step 3:** 提交

```bash
git add data/ && git commit -m "data: seed topics and event anchors"
```

---

### Task P0-T3:Supabase schema 迁移

**Files:**
- Create: `supabase/migrations/0001_init.sql`

- [ ] **Step 1:** 写 SQL(直接从 spec 第四节复制过来,已经是完整的):

```sql
CREATE TABLE topics (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  question_id TEXT,
  cover_quote_old TEXT,
  cover_quote_new TEXT,
  category TEXT,
  featured_rank INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE year_summaries (
  topic_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
  year INT NOT NULL,
  primary_view TEXT,
  secondary_view TEXT,
  golden_quote TEXT,
  quote_author TEXT,
  quote_source_url TEXT,
  era_caption TEXT,
  PRIMARY KEY (topic_id, year)
);

CREATE TABLE events (
  id SERIAL PRIMARY KEY,
  year INT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  category TEXT
);

CREATE TABLE topic_events (
  topic_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
  event_id INT REFERENCES events(id) ON DELETE CASCADE,
  PRIMARY KEY (topic_id, event_id)
);

CREATE TABLE predictions (
  topic_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
  target_year INT NOT NULL,
  scenario_conservative TEXT,
  scenario_mainstream TEXT,
  scenario_radical TEXT,
  generated_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (topic_id, target_year)
);

CREATE TABLE raw_answers (
  id BIGSERIAL PRIMARY KEY,
  topic_id TEXT,
  year INT,
  author TEXT,
  content TEXT,
  like_count INT,
  url TEXT,
  fetched_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_year_summaries_topic ON year_summaries(topic_id);
CREATE INDEX idx_raw_answers_topic_year ON raw_answers(topic_id, year);
```

- [ ] **Step 2:** 应用到 Supabase(通过 Supabase CLI 或 Dashboard SQL Editor 直接粘贴运行)

```bash
# 本地开发推荐:
supabase link --project-ref <YOUR_PROJECT_REF>
supabase db push
```

- [ ] **Step 3:** 提交 migration 到 git

```bash
git add supabase/ && git commit -m "db: initial schema"
```

---

### Task P0-T4:Python 离线管线脚手架

**Files:**
- Create: `scripts/pyproject.toml`
- Create: `scripts/_lib/zhihu_api.py`, `scripts/_lib/llm.py`, `scripts/_lib/db.py`

- [ ] **Step 1:** `scripts/pyproject.toml`

```toml
[project]
name = "shiguangda-scripts"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "httpx>=0.27",
  "tenacity>=8",
  "pydantic>=2",
  "python-dotenv>=1",
  "psycopg[binary]>=3",
  "numpy",
  "scikit-learn",
  "openai",       # for embeddings
  "anthropic",    # for Haiku quality check
]
```

- [ ] **Step 2:** 初始化 uv venv

```bash
cd scripts && uv venv && uv sync
```

- [ ] **Step 3:** `scripts/_lib/zhihu_api.py`:

```python
import os, httpx
from tenacity import retry, stop_after_attempt, wait_exponential

BASE = "https://developer.zhihu.com"
TOKEN = os.getenv("ZHIHU_ACCESS_TOKEN")

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def zhihu_search(keyword: str, page: int = 1, size: int = 20) -> dict:
    r = httpx.get(
        f"{BASE}/api/v1/content/zhihu_search",
        params={"keyword": keyword, "page": page, "size": size},
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def zhihu_hotlist(hours: int = 24) -> dict:
    r = httpx.get(
        f"{BASE}/api/v1/content/hot_list",
        params={"hours": hours},
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def zhihu_direct_answer(question: str) -> str:
    r = httpx.post(
        f"{BASE}/v1/chat/completions",
        json={"messages": [{"role": "user", "content": question}]},
        headers={"Authorization": f"Bearer {TOKEN}"},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]
```

- [ ] **Step 4:** `scripts/_lib/llm.py`:

```python
import os
from openai import OpenAI  # 用 OpenAI SDK 兼容调 DeepSeek

deepseek = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

def chat(messages: list[dict], model: str = "deepseek-chat", json_mode: bool = False) -> str:
    resp = deepseek.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"} if json_mode else None,
        temperature=0.3,
    )
    return resp.choices[0].message.content

def embed(texts: list[str]) -> list[list[float]]:
    openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = openai.embeddings.create(model="text-embedding-3-small", input=texts)
    return [d.embedding for d in resp.data]
```

- [ ] **Step 5:** `scripts/_lib/db.py`:

```python
import os, psycopg
from contextlib import contextmanager

@contextmanager
def conn():
    with psycopg.connect(os.getenv("SUPABASE_DB_URL")) as c:
        yield c
```

- [ ] **Step 6:** 提交

```bash
git add scripts/ && git commit -m "scripts: pipeline scaffolding"
```

---

## Phase 1 · 离线数据管线

> **目标:** 赛前把 30 话题的完整数据生成并入库,运行时零 API 依赖(除搜索兜底 + 2029 实时刷新)。
> **总预算:** 搜索 API ≤ 500 次 / 直答 ≤ 30 次 / DeepSeek ≤ 1000 次(成本 < ¥5) / embedding ≤ 10000 tokens。

### Task P1-T1:抓取器 `01_fetch_answers.py`

**Files:**
- Create: `scripts/01_fetch_answers.py`

- [ ] **Step 1:** 写代码(先读 topics.seed.json,逐话题逐年抓取高赞答):

```python
import json, time
from pathlib import Path
from _lib.zhihu_api import zhihu_search
from _lib.db import conn

ROOT = Path(__file__).parent.parent
TOPICS = json.loads((ROOT / "data/topics.seed.json").read_text())

def fetch_topic(topic: dict):
    rows = []
    for kw in topic["search_keywords"]:
        for page in (1, 2, 3):  # 至多 60 条
            res = zhihu_search(kw, page=page, size=20)
            for item in res.get("data", []):
                ts = item.get("created_time") or item.get("publish_time")
                year = int(ts[:4]) if isinstance(ts, str) else None
                rows.append({
                    "topic_id": topic["id"],
                    "year": year,
                    "author": item.get("author", {}).get("name"),
                    "content": item.get("excerpt") or item.get("content"),
                    "like_count": item.get("voteup_count", 0),
                    "url": item.get("url"),
                })
            time.sleep(0.5)
    return rows

def main():
    with conn() as c, c.cursor() as cur:
        for t in TOPICS:
            rows = fetch_topic(t)
            cur.executemany(
                "INSERT INTO raw_answers (topic_id, year, author, content, like_count, url) VALUES (%(topic_id)s, %(year)s, %(author)s, %(content)s, %(like_count)s, %(url)s)",
                rows,
            )
            c.commit()
            print(f"[{t['id']}] {len(rows)} rows")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2:** 先只跑 3 个话题试水(注释掉其他):`uv run python scripts/01_fetch_answers.py`

- [ ] **Step 3:** Supabase Table Editor 验证 `raw_answers` 有数据、year 字段正确分布

- [ ] **Step 4:** 全量跑(30 话题,估计 10-20 分钟,API 调用 < 500)

- [ ] **Step 5:** 提交

```bash
git add scripts/01_fetch_answers.py && git commit -m "pipeline: step 1 fetch historical answers"
```

---

### Task P1-T2:按年分桶 + 观点聚类 `03_cluster_opinions.py`

**Files:**
- Create: `scripts/03_cluster_opinions.py`
- Create: `tests/scripts/cluster_opinions.test.py`

> 注:T2 合并了 "按年分桶"(逻辑极简,内嵌)和聚类主体。无需独立 `02_bucket_by_year.py`。

- [ ] **Step 1:** 写一个纯函数测试(聚类纯逻辑)

```python
# tests/scripts/cluster_opinions.test.py
import numpy as np
from scripts.cluster_opinions import cluster_vectors

def test_cluster_vectors_k3():
    # 3 组明显可分的向量
    vecs = np.array([
        [1,0,0],[1,0.1,0],[1,0,0.1],        # A
        [0,1,0],[0,1,0.1],[0.1,1,0],        # B
        [0,0,1],[0.1,0,1],[0,0.1,1],        # C
    ])
    labels = cluster_vectors(vecs, k=3)
    assert len(set(labels)) == 3
```

运行:`uv run pytest tests/scripts/cluster_opinions.test.py -v`,应 FAIL。

- [ ] **Step 2:** 实现

```python
# scripts/03_cluster_opinions.py
import numpy as np
from sklearn.cluster import KMeans
from collections import defaultdict
from _lib.llm import embed, chat
from _lib.db import conn

def cluster_vectors(vecs: np.ndarray, k: int = 3) -> list[int]:
    if len(vecs) <= k:
        return list(range(len(vecs)))
    km = KMeans(n_clusters=k, n_init=5, random_state=42)
    return km.fit_predict(vecs).tolist()

def pick_centroids(vecs: np.ndarray, labels: list[int], rows: list[dict]) -> list[dict]:
    """每一簇里返回最靠近中心的那条"""
    centers = defaultdict(list)
    for row, lab in zip(rows, labels):
        centers[lab].append(row)
    picked = []
    for lab, cluster_rows in centers.items():
        # 简单起见取 like_count 最高
        picked.append(max(cluster_rows, key=lambda r: r["like_count"] or 0))
    return picked

def summarize_year(topic: dict, year: int, rows: list[dict]) -> dict:
    contents = [r["content"] for r in rows if r["content"]]
    if not contents:
        return None
    vecs = np.array(embed(contents))
    labels = cluster_vectors(vecs, k=min(3, len(contents)))
    centroids = pick_centroids(vecs, labels, rows)
    prompt = f"""以下是知乎话题《{topic['title']}》在 {year} 年的 {len(centroids)} 个代表性回答:

{chr(10).join(f"- {c['content'][:300]}" for c in centroids)}

请总结这一年该话题的主流观点,返回 JSON:
{{
  "primary_view": "本年最主流的观点,1 句话",
  "secondary_view": "本年次主流或对立观点,1 句话(可空)",
  "era_caption": "用 1 句话点出这一年的社会背景与话题关联"
}}
"""
    resp = chat([{"role": "user", "content": prompt}], json_mode=True)
    import json
    return json.loads(resp)

def main():
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT DISTINCT topic_id FROM raw_answers")
        topics = [r[0] for r in cur.fetchall()]
        for tid in topics:
            cur.execute("SELECT title FROM topics WHERE id=%s", (tid,))
            title = cur.fetchone()[0]
            cur.execute("SELECT DISTINCT year FROM raw_answers WHERE topic_id=%s AND year IS NOT NULL", (tid,))
            years = [r[0] for r in cur.fetchall()]
            for y in years:
                cur.execute(
                    "SELECT content, like_count, author, url FROM raw_answers WHERE topic_id=%s AND year=%s ORDER BY like_count DESC LIMIT 30",
                    (tid, y),
                )
                rows = [dict(zip(["content","like_count","author","url"], r)) for r in cur.fetchall()]
                summary = summarize_year({"title": title}, y, rows)
                if not summary: continue
                cur.execute(
                    "INSERT INTO year_summaries (topic_id, year, primary_view, secondary_view, era_caption) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (topic_id, year) DO UPDATE SET primary_view=EXCLUDED.primary_view",
                    (tid, y, summary["primary_view"], summary.get("secondary_view"), summary["era_caption"]),
                )
                c.commit()
                print(f"[{tid}] {y} ✓")

if __name__ == "__main__":
    main()
```

- [ ] **Step 3:** `uv run pytest tests/scripts/cluster_opinions.test.py -v` 应 PASS

- [ ] **Step 4:** `uv run python scripts/03_cluster_opinions.py`

- [ ] **Step 5:** 提交

```bash
git add -A && git commit -m "pipeline: cluster opinions per topic per year"
```

---

### Task P1-T3:金句提炼 `04_extract_quotes.py`

**Files:** Create `scripts/04_extract_quotes.py`

- [ ] **Step 1:** 实现

```python
from _lib.llm import chat
from _lib.db import conn
import json

def extract_quote(title: str, year: int, rows: list[dict]) -> dict:
    prompt = f"""话题《{title}》{year} 年的高赞回答节选:

{chr(10).join(f'<{i+1}> [{r["author"]}|赞{r["like_count"]}] {r["content"][:400]}' for i, r in enumerate(rows))}

从以上回答中抽取 1 条最能代表这一年气质的"金句"(可以是原文摘录或轻度改写,15-40 字),返回 JSON:
{{
  "golden_quote": "...",
  "quote_index": 1
}}"""
    res = chat([{"role": "user", "content": prompt}], json_mode=True)
    return json.loads(res)

def main():
    with conn() as c, c.cursor() as cur:
        cur.execute("""
            SELECT ys.topic_id, ys.year, t.title FROM year_summaries ys
            JOIN topics t ON t.id = ys.topic_id
            WHERE ys.golden_quote IS NULL
        """)
        for tid, year, title in cur.fetchall():
            cur.execute("SELECT content, like_count, author, url FROM raw_answers WHERE topic_id=%s AND year=%s ORDER BY like_count DESC LIMIT 5", (tid, year))
            rows = [dict(zip(["content","like_count","author","url"], r)) for r in cur.fetchall()]
            if not rows: continue
            res = extract_quote(title, year, rows)
            src = rows[res["quote_index"]-1] if 1 <= res.get("quote_index", 0) <= len(rows) else rows[0]
            cur.execute(
                "UPDATE year_summaries SET golden_quote=%s, quote_author=%s, quote_source_url=%s WHERE topic_id=%s AND year=%s",
                (res["golden_quote"], src["author"], src["url"], tid, year),
            )
            c.commit()
            print(f"[{tid}] {year} quote ✓")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2:** 跑:`uv run python scripts/04_extract_quotes.py`
- [ ] **Step 3:** Supabase 抽查 3 条金句质量,不满意就微调 prompt 重跑该话题
- [ ] **Step 4:** 提交

```bash
git add scripts/04_extract_quotes.py && git commit -m "pipeline: extract golden quote per year"
```

---

### Task P1-T4:事件锚点映射 `05_attach_events.py`

**Files:** Create `scripts/05_attach_events.py`

- [ ] **Step 1:** 实现(先把 `data/events.seed.json` 导入 events 表,再为每个 topic 挑 4-6 个相关事件):

```python
import json
from pathlib import Path
from _lib.llm import chat
from _lib.db import conn

EVENTS = json.loads((Path(__file__).parent.parent / "data/events.seed.json").read_text())

def seed_events():
    with conn() as c, c.cursor() as cur:
        cur.execute("DELETE FROM events")
        for e in EVENTS:
            cur.execute(
                "INSERT INTO events (year, title, category, description) VALUES (%s,%s,%s,%s) RETURNING id",
                (e["year"], e["title"], e.get("category"), e.get("description", "")),
            )
        c.commit()

def attach_for_topic(tid: str, title: str, category: str):
    candidates = "\n".join(f"[{e['year']}] {e['title']} ({e.get('category','')})" for e in EVENTS)
    prompt = f"""话题: {title}(分类: {category})
候选事件锚点:
{candidates}

从上面挑 4-6 个与该话题最相关的事件,按年份排序,返回 JSON: {{"event_titles": ["...","..."]}}"""
    res = json.loads(chat([{"role": "user", "content": prompt}], json_mode=True))
    with conn() as c, c.cursor() as cur:
        cur.execute("DELETE FROM topic_events WHERE topic_id=%s", (tid,))
        for et in res["event_titles"]:
            cur.execute("SELECT id FROM events WHERE title=%s LIMIT 1", (et,))
            row = cur.fetchone()
            if row:
                cur.execute("INSERT INTO topic_events (topic_id, event_id) VALUES (%s,%s) ON CONFLICT DO NOTHING", (tid, row[0]))
        c.commit()

def main():
    seed_events()
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT id, title, category FROM topics")
        for tid, title, cat in cur.fetchall():
            attach_for_topic(tid, title, cat)
            print(f"[{tid}] events ✓")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2:** 跑:`uv run python scripts/05_attach_events.py`
- [ ] **Step 3:** 提交

```bash
git add scripts/05_attach_events.py && git commit -m "pipeline: attach event anchors per topic"
```

---

### Task P1-T5:2029 预测预生成 `06_predict_2029.py`

**Files:** Create `scripts/06_predict_2029.py`

- [ ] **Step 1:** 实现

```python
import json
from _lib.llm import chat
from _lib.db import conn

def predict(title: str, summaries: list[dict]) -> dict:
    timeline = "\n".join(f"[{s['year']}] {s['primary_view']}" for s in summaries)
    prompt = f"""话题: {title}
以下是 2011-2026 的观点演变时间线:

{timeline}

基于这一演变轨迹,请外推 2029 年最可能的三种情境。要求:

1. 每种情境 40-60 字,结尾带 1 句代表金句
2. 保守情境 = 当前趋势平稳延续
3. 主流情境 = 综合各信号的最可能未来
4. 激进情境 = 小概率但不可忽视的尾部风险

返回 JSON:
{{"conservative": "...", "mainstream": "...", "radical": "..."}}

请记住:这是基于公开讨论的 AI 推演,不是预言。"""
    return json.loads(chat([{"role": "user", "content": prompt}], json_mode=True))

def main():
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT id, title FROM topics")
        topics = cur.fetchall()
        for tid, title in topics:
            cur.execute("SELECT year, primary_view FROM year_summaries WHERE topic_id=%s ORDER BY year", (tid,))
            summaries = [dict(year=r[0], primary_view=r[1]) for r in cur.fetchall()]
            if len(summaries) < 3: continue
            pred = predict(title, summaries)
            cur.execute(
                "INSERT INTO predictions (topic_id, target_year, scenario_conservative, scenario_mainstream, scenario_radical) VALUES (%s, 2029, %s, %s, %s) ON CONFLICT (topic_id, target_year) DO UPDATE SET scenario_conservative=EXCLUDED.scenario_conservative, scenario_mainstream=EXCLUDED.scenario_mainstream, scenario_radical=EXCLUDED.scenario_radical, generated_at=NOW()",
                (tid, pred["conservative"], pred["mainstream"], pred["radical"]),
            )
            c.commit()
            print(f"[{tid}] 2029 ✓")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2:** 跑:`uv run python scripts/06_predict_2029.py`
- [ ] **Step 3:** 人工抽查 3 条预测质量
- [ ] **Step 4:** 提交

```bash
git add scripts/06_predict_2029.py && git commit -m "pipeline: pre-generate 2029 predictions"
```

---

### Task P1-T6:封面对照金句生成(topics.cover_quote_old/new)

**Files:** Create `scripts/07_cover_quotes.py`

- [ ] **Step 1:** 实现(取每个话题最早一年 + 2026 年的金句作为封面对照):

```python
from _lib.db import conn

def main():
    with conn() as c, c.cursor() as cur:
        cur.execute("SELECT id FROM topics")
        for (tid,) in cur.fetchall():
            cur.execute("SELECT MIN(year), MAX(year) FROM year_summaries WHERE topic_id=%s", (tid,))
            y_min, y_max = cur.fetchone()
            if not y_min: continue
            cur.execute("SELECT golden_quote FROM year_summaries WHERE topic_id=%s AND year=%s", (tid, y_min))
            old = cur.fetchone()
            cur.execute("SELECT golden_quote FROM year_summaries WHERE topic_id=%s AND year=%s", (tid, y_max))
            new = cur.fetchone()
            cur.execute(
                "UPDATE topics SET cover_quote_old=%s, cover_quote_new=%s WHERE id=%s",
                (old[0] if old else None, new[0] if new else None, tid),
            )
        c.commit()
        print("cover quotes ✓")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2:** 跑并提交

```bash
uv run python scripts/07_cover_quotes.py
git add scripts/07_cover_quotes.py && git commit -m "pipeline: generate cover contrast quotes"
```

---

## Phase 2 · 前端骨架

### Task P2-T1:Supabase 客户端封装

**Files:** Create `src/lib/supabase.ts`, `src/lib/types.ts`

- [ ] **Step 1:** `src/lib/types.ts`:

```ts
export type Topic = {
  id: string;
  title: string;
  question_id?: string;
  cover_quote_old?: string;
  cover_quote_new?: string;
  category?: string;
  featured_rank?: number;
};

export type YearSummary = {
  topic_id: string;
  year: number;
  primary_view: string;
  secondary_view?: string;
  golden_quote?: string;
  quote_author?: string;
  quote_source_url?: string;
  era_caption?: string;
};

export type EventAnchor = { year: number; title: string; category?: string };

export type Prediction = {
  scenario_conservative: string;
  scenario_mainstream: string;
  scenario_radical: string;
};

export type TopicDetail = {
  topic: Topic;
  years: YearSummary[];
  events: EventAnchor[];
  prediction?: Prediction;
};
```

- [ ] **Step 2:** `src/lib/supabase.ts`:

```ts
import { createClient } from '@supabase/supabase-js';

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);

export const supabaseAdmin = () => createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
);
```

- [ ] **Step 3:** 提交

```bash
git add src/lib/ && git commit -m "feat: supabase client + shared types"
```

---

### Task P2-T2:话题页数据获取 + 路由

**Files:** Create `src/app/topic/[id]/page.tsx`, `src/app/api/topics/[id]/route.ts`

- [ ] **Step 1:** `src/app/api/topics/[id]/route.ts`:

```ts
import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export const revalidate = 86400; // 24h

export async function GET(_req: NextRequest, { params }: { params: { id: string } }) {
  const [topic, years, events, prediction] = await Promise.all([
    supabase.from('topics').select('*').eq('id', params.id).single(),
    supabase.from('year_summaries').select('*').eq('topic_id', params.id).order('year'),
    supabase.rpc('topic_events_full', { tid: params.id }).select('*'),
    supabase.from('predictions').select('*').eq('topic_id', params.id).eq('target_year', 2029).single(),
  ]);
  if (topic.error || !topic.data) return NextResponse.json({ error: 'not found' }, { status: 404 });
  return NextResponse.json({
    topic: topic.data,
    years: years.data || [],
    events: events.data || [],
    prediction: prediction.data,
  });
}
```

注:`topic_events_full` 需要在 Supabase 建个简单 view 把 topic_events JOIN events。若偷懒,直接两次查询 + 客户端 JOIN。

- [ ] **Step 2:** `src/app/topic/[id]/page.tsx`:

```tsx
import { notFound } from 'next/navigation';
import { Timeline } from '@/components/Timeline';
import { PredictCard } from '@/components/PredictCard';
import { PosterButton } from '@/components/PosterButton';
import type { TopicDetail } from '@/lib/types';

async function getTopic(id: string): Promise<TopicDetail | null> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_BASE_URL}/api/topics/${id}`, { next: { revalidate: 86400 } });
  if (!res.ok) return null;
  return res.json();
}

export default async function Page({ params }: { params: { id: string } }) {
  const data = await getTopic(params.id);
  if (!data) notFound();
  return (
    <main className="min-h-screen bg-paper text-ink">
      <header className="px-8 pt-16 pb-8 max-w-3xl mx-auto">
        <h1 className="font-song text-4xl md:text-6xl leading-tight">{data.topic.title}</h1>
        <p className="mt-4 text-ink/60 font-hei text-sm">知乎编年 · 观点十五年</p>
      </header>
      <Timeline years={data.years} events={data.events} />
      {data.prediction && <PredictCard prediction={data.prediction} />}
      <PosterButton topicId={data.topic.id} />
    </main>
  );
}
```

- [ ] **Step 3:** 提交

```bash
git add src/app/topic src/app/api/topics && git commit -m "feat: topic detail page route"
```

---

### Task P2-T3:Timeline 组件(含滚动动画)

**Files:** Create `src/components/Timeline.tsx`, `src/components/YearCard.tsx`, `src/components/EventAnchor.tsx`

- [ ] **Step 1:** `src/components/YearCard.tsx`:

```tsx
'use client';
import { motion } from 'framer-motion';
import type { YearSummary } from '@/lib/types';

export function YearCard({ s }: { s: YearSummary }) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-100px' }}
      transition={{ duration: 0.6, ease: 'easeOut' }}
      className="max-w-2xl mx-auto py-16 border-l-2 border-ink/20 pl-8 relative"
    >
      <div className="absolute -left-3 top-14 w-5 h-5 rounded-full bg-stamp" />
      <div className="font-song text-7xl text-ink/80">{s.year}</div>
      <p className="mt-4 font-hei text-lg text-ink/70">{s.era_caption}</p>
      <blockquote className="mt-6 font-song text-2xl md:text-3xl leading-relaxed italic border-l-4 border-stamp pl-4">
        「{s.golden_quote}」
        {s.quote_author && <cite className="block mt-2 text-sm not-italic text-ink/50">— {s.quote_author}</cite>}
      </blockquote>
      <div className="mt-6 space-y-2 font-hei text-base">
        <p>· {s.primary_view}</p>
        {s.secondary_view && <p className="text-ink/60">· {s.secondary_view}</p>}
      </div>
    </motion.article>
  );
}
```

- [ ] **Step 2:** `src/components/EventAnchor.tsx`:

```tsx
'use client';
import { motion } from 'framer-motion';
import type { EventAnchor as E } from '@/lib/types';

export function EventAnchor({ e }: { e: E }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.8 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true }}
      className="max-w-2xl mx-auto my-8 bg-stamp/10 border border-stamp/30 rounded-lg px-4 py-2 text-center"
    >
      <span className="font-song text-stamp text-sm">{e.year} · {e.title}</span>
    </motion.div>
  );
}
```

- [ ] **Step 3:** `src/components/Timeline.tsx`:

```tsx
import { YearCard } from './YearCard';
import { EventAnchor } from './EventAnchor';
import type { YearSummary, EventAnchor as E } from '@/lib/types';

export function Timeline({ years, events }: { years: YearSummary[]; events: E[] }) {
  // 按年份合并:每年先插事件(该年所有),再插 YearCard
  const byYear = new Map<number, { events: E[]; year?: YearSummary }>();
  years.forEach((y) => byYear.set(y.year, { events: [], year: y }));
  events.forEach((e) => {
    const bucket = byYear.get(e.year) ?? { events: [] };
    bucket.events.push(e);
    byYear.set(e.year, bucket);
  });
  const sorted = [...byYear.entries()].sort(([a], [b]) => a - b);
  return (
    <section>
      {sorted.map(([year, { events, year: y }]) => (
        <div key={year}>
          {events.map((e, i) => <EventAnchor key={i} e={e} />)}
          {y && <YearCard s={y} />}
        </div>
      ))}
    </section>
  );
}
```

- [ ] **Step 4:** 本地跑,访问 `/topic/programmer-35` 验证滚动动画
- [ ] **Step 5:** 提交

```bash
git add src/components/Timeline.tsx src/components/YearCard.tsx src/components/EventAnchor.tsx
git commit -m "feat: timeline component with scroll animations"
```

---

### Task P2-T4:PredictCard(2029 预测)

**Files:** Create `src/components/PredictCard.tsx`

- [ ] **Step 1:**

```tsx
'use client';
import { useState } from 'react';
import { motion } from 'framer-motion';
import type { Prediction } from '@/lib/types';

export function PredictCard({ prediction }: { prediction: Prediction }) {
  const [tab, setTab] = useState<'mainstream'|'conservative'|'radical'>('mainstream');
  const text = {
    conservative: prediction.scenario_conservative,
    mainstream:   prediction.scenario_mainstream,
    radical:      prediction.scenario_radical,
  }[tab];
  return (
    <motion.section
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      className="max-w-2xl mx-auto my-24 p-8 bg-ink text-paper rounded-2xl"
    >
      <header className="flex items-baseline justify-between">
        <h2 className="font-song text-3xl">2029</h2>
        <span className="font-hei text-xs text-paper/50">AI 基于十五年讨论的推演,非预言</span>
      </header>
      <div className="mt-6 flex gap-2">
        {[
          ['conservative','保守'],
          ['mainstream','主流'],
          ['radical','激进'],
        ].map(([k,label]) => (
          <button
            key={k}
            onClick={() => setTab(k as any)}
            className={`px-3 py-1 rounded-full text-sm font-hei ${tab===k ? 'bg-paper text-ink' : 'border border-paper/30'}`}
          >{label}</button>
        ))}
      </div>
      <p className="mt-6 font-song text-2xl leading-relaxed">{text}</p>
    </motion.section>
  );
}
```

- [ ] **Step 2:** 提交

```bash
git add src/components/PredictCard.tsx && git commit -m "feat: 2029 prediction card with three scenarios"
```

---

### Task P2-T5:首页 + TopicCard + TopicGrid + 搜索框占位

**Files:** Create `src/components/TopicCard.tsx`, `src/components/TopicGrid.tsx`, `src/components/HomeBanner.tsx`, `src/components/SearchBox.tsx`, `src/app/page.tsx`

- [ ] **Step 1:** `TopicCard.tsx`:

```tsx
import Link from 'next/link';
import type { Topic } from '@/lib/types';

export function TopicCard({ t }: { t: Topic }) {
  return (
    <Link href={`/topic/${t.id}`} className="block border border-ink/10 rounded-lg p-6 bg-paper hover:border-stamp transition">
      <div className="text-xs font-hei text-ink/50 mb-2">{t.category}</div>
      <h3 className="font-song text-xl leading-snug">{t.title}</h3>
      <div className="mt-6 space-y-2 text-sm font-song text-ink/70">
        <p className="italic">「{t.cover_quote_old}」<span className="text-ink/40 ml-2">· 早年</span></p>
        <p className="italic text-stamp">「{t.cover_quote_new}」<span className="text-ink/40 ml-2">· 2026</span></p>
      </div>
    </Link>
  );
}
```

- [ ] **Step 2:** `TopicGrid.tsx`:

```tsx
import { TopicCard } from './TopicCard';
import type { Topic } from '@/lib/types';

export function TopicGrid({ topics }: { topics: Topic[] }) {
  return (
    <section className="max-w-6xl mx-auto px-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3 py-16">
      {topics.map((t) => <TopicCard key={t.id} t={t} />)}
    </section>
  );
}
```

- [ ] **Step 3:** `HomeBanner.tsx`:

```tsx
import Link from 'next/link';
import type { Topic } from '@/lib/types';

export function HomeBanner({ today }: { today: Topic | null }) {
  if (!today) return null;
  return (
    <section className="relative h-[60vh] bg-ink text-paper flex items-center">
      <div className="max-w-4xl mx-auto px-8">
        <div className="font-hei text-sm text-paper/60">今日热榜 · 时代前世今生</div>
        <Link href={`/topic/${today.id}`}>
          <h1 className="mt-4 font-song text-5xl md:text-7xl leading-tight hover:text-stamp transition">
            {today.title}
          </h1>
        </Link>
        <div className="mt-8 font-song text-xl md:text-2xl text-paper/80 italic">
          <p>「{today.cover_quote_old}」<span className="text-paper/40">· 早年</span></p>
          <p className="mt-2 text-stamp">「{today.cover_quote_new}」<span className="text-paper/40">· 2026</span></p>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 4:** `SearchBox.tsx`:

```tsx
'use client';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export function SearchBox() {
  const r = useRouter();
  const [q, setQ] = useState('');
  return (
    <form
      onSubmit={(e) => { e.preventDefault(); if (q.trim()) r.push(`/search?q=${encodeURIComponent(q)}`); }}
      className="max-w-xl mx-auto px-8 py-6"
    >
      <input
        value={q} onChange={(e) => setQ(e.target.value)}
        placeholder="输入一个话题,看它的十五年前世今生…"
        className="w-full px-6 py-4 bg-white border border-ink/20 rounded-full font-song text-lg outline-none focus:border-stamp"
      />
    </form>
  );
}
```

- [ ] **Step 5:** `src/app/page.tsx`:

```tsx
import { supabase } from '@/lib/supabase';
import { HomeBanner } from '@/components/HomeBanner';
import { TopicGrid } from '@/components/TopicGrid';
import { SearchBox } from '@/components/SearchBox';

export const revalidate = 3600;

export default async function Home() {
  const { data: all } = await supabase.from('topics').select('*').order('featured_rank');
  const topics = all ?? [];
  const today = topics[0] ?? null;
  const rest = topics.slice(1);
  return (
    <main className="bg-paper min-h-screen">
      <HomeBanner today={today} />
      <SearchBox />
      <TopicGrid topics={rest} />
    </main>
  );
}
```

- [ ] **Step 6:** 本地跑,验证首页。提交

```bash
git add src/components src/app/page.tsx && git commit -m "feat: home banner + topic grid + search box"
```

---

## Phase 3 · 运行时 API + 搜索兜底

### Task P3-T1:搜索兜底路由

**Files:** Create `src/app/api/search/route.ts`, `src/app/search/page.tsx`

- [ ] **Step 1:** `src/app/api/search/route.ts`(先 fuzzy match 精选库,再调直答做浅层时光轴):

```ts
import { NextRequest, NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get('q');
  if (!q) return NextResponse.json({ error: 'missing q' }, { status: 400 });

  // 1. fuzzy match 精选库
  const { data: matches } = await supabase
    .from('topics')
    .select('*')
    .textSearch('title', q, { type: 'websearch' })
    .limit(5);
  if (matches?.length) return NextResponse.json({ kind: 'matched', topics: matches });

  // 2. 兜底:调直答做浅层时光轴
  const res = await fetch('https://developer.zhihu.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.ZHIHU_ACCESS_TOKEN}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      messages: [{ role: 'user', content: `话题:${q}。请按 2015/2018/2021/2024/2026 五年切片,各用 1 句话描述当年主流观点。返回 JSON: {"timeline": [{"year":2015, "view":"..."}, ...]}` }],
    }),
  });
  const data = await res.json();
  return NextResponse.json({ kind: 'shallow', raw: data });
}
```

- [ ] **Step 2:** `src/app/search/page.tsx`(Client Component,展示结果):

```tsx
'use client';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';

export default function Search() {
  const sp = useSearchParams();
  const q = sp.get('q') || '';
  const [result, setResult] = useState<any>(null);
  useEffect(() => {
    if (!q) return;
    fetch(`/api/search?q=${encodeURIComponent(q)}`).then(r => r.json()).then(setResult);
  }, [q]);
  if (!result) return <main className="p-16 text-center font-song text-ink/50">为你检索十五年的声音…</main>;
  if (result.kind === 'matched') return (
    <main className="max-w-2xl mx-auto p-16">
      <h2 className="font-song text-2xl mb-6">为你匹配到这些精选话题:</h2>
      {result.topics.map((t: any) => <Link key={t.id} href={`/topic/${t.id}`} className="block py-4 border-b font-song text-xl hover:text-stamp">{t.title}</Link>)}
    </main>
  );
  return <main className="p-8 font-song">{JSON.stringify(result.raw, null, 2)}</main>;
}
```

- [ ] **Step 3:** 提交

```bash
git add src/app/api/search src/app/search && git commit -m "feat: search fallback with fuzzy match + shallow timeline"
```

---

### Task P3-T2:今日热榜 banner cron + topic swap

**Files:** Create `src/app/api/hotlist-today/route.ts`, `vercel.json`

- [ ] **Step 1:** `src/app/api/hotlist-today/route.ts`:

```ts
import { NextResponse } from 'next/server';
import { supabaseAdmin } from '@/lib/supabase';

export async function GET() {
  // 拉热榜 top 50
  const r = await fetch('https://developer.zhihu.com/api/v1/content/hot_list?hours=24', {
    headers: { Authorization: `Bearer ${process.env.ZHIHU_ACCESS_TOKEN}` },
  });
  const hot = await r.json();
  const titles = (hot?.data || []).map((x: any) => x.title || x.question?.title).filter(Boolean);

  // 从精选池找一个关键词命中的话题,提升 featured_rank = 0
  const s = supabaseAdmin();
  const { data: topics } = await s.from('topics').select('id, title');
  const match = topics?.find(t => titles.some((h: string) => h.includes(t.title.slice(0, 4))));
  if (match) {
    await s.from('topics').update({ featured_rank: 0 }).eq('id', match.id);
    // 把之前是 0 的降为 1
    await s.from('topics').update({ featured_rank: 1 }).neq('id', match.id).eq('featured_rank', 0);
  }
  return NextResponse.json({ swapped: !!match, topic: match?.id });
}
```

- [ ] **Step 2:** `vercel.json`:

```json
{
  "crons": [
    { "path": "/api/hotlist-today", "schedule": "0 */4 * * *" }
  ]
}
```

- [ ] **Step 3:** 提交

```bash
git add src/app/api/hotlist-today vercel.json && git commit -m "feat: cron-driven today banner swap"
```

---

### Task P3-T3:2029 预测运行时刷新路由

**Files:** Create `src/app/api/predict/[id]/route.ts`

- [ ] **Step 1:**

```ts
import { NextRequest, NextResponse } from 'next/server';
import { supabase, supabaseAdmin } from '@/lib/supabase';

export async function POST(_req: NextRequest, { params }: { params: { id: string } }) {
  // 7 天内有结果就直接返回,避免浪费直答配额
  const { data: cached } = await supabase.from('predictions').select('*').eq('topic_id', params.id).eq('target_year', 2029).single();
  if (cached && new Date().getTime() - new Date(cached.generated_at).getTime() < 7 * 864e5) {
    return NextResponse.json(cached);
  }

  // 重新生成
  const { data: topic } = await supabase.from('topics').select('title').eq('id', params.id).single();
  const { data: years } = await supabase.from('year_summaries').select('year, primary_view').eq('topic_id', params.id).order('year');
  const timeline = (years ?? []).map(y => `[${y.year}] ${y.primary_view}`).join('\n');
  const prompt = `话题:${topic?.title}\n\n时间线:\n${timeline}\n\n请外推 2029 年三种情境(保守/主流/激进),每种 40-60 字带金句结尾。返回 JSON: {"conservative":"...","mainstream":"...","radical":"..."}`;

  const r = await fetch('https://developer.zhihu.com/v1/chat/completions', {
    method: 'POST',
    headers: { Authorization: `Bearer ${process.env.ZHIHU_ACCESS_TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages: [{ role: 'user', content: prompt }] }),
  });
  const data = await r.json();
  let parsed;
  try { parsed = JSON.parse(data?.choices?.[0]?.message?.content ?? '{}'); } catch { parsed = {}; }

  await supabaseAdmin().from('predictions').upsert({
    topic_id: params.id,
    target_year: 2029,
    scenario_conservative: parsed.conservative,
    scenario_mainstream: parsed.mainstream,
    scenario_radical: parsed.radical,
    generated_at: new Date().toISOString(),
  });
  return NextResponse.json(parsed);
}
```

- [ ] **Step 2:** 提交

```bash
git add src/app/api/predict && git commit -m "feat: runtime 2029 prediction refresh with 7d cache"
```

---

## Phase 4 · 海报 + 分享 + OAuth

### Task P4-T1:satori 海报模板 + API

**Files:** Create `src/lib/poster.tsx`, `src/app/api/poster/[id]/route.tsx`, `tests/lib/poster.test.ts`

- [ ] **Step 1:** `src/lib/poster.tsx`(JSX 返回给 satori,生成 PNG 1080×1920):

```tsx
import satori from 'satori';
import { Resvg } from '@resvg/resvg-js';
import type { TopicDetail } from './types';

export async function renderPoster(detail: TopicDetail, fontData: ArrayBuffer): Promise<Buffer> {
  const jsx = (
    <div style={{
      width: 1080, height: 1920, background: '#0B1026', color: '#F4E4BA',
      padding: 80, fontFamily: 'Song', display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ fontSize: 28, opacity: 0.6 }}>知乎编年 · 观点十五年</div>
      <div style={{ fontSize: 72, marginTop: 40, lineHeight: 1.2, fontWeight: 700 }}>
        {detail.topic.title}
      </div>
      <div style={{ flex: 1, marginTop: 60, display: 'flex', flexDirection: 'column', gap: 24 }}>
        {detail.years.slice(-6).map((y) => (
          <div key={y.year} style={{ display: 'flex', gap: 24, borderLeft: '4px solid #E63946', paddingLeft: 24 }}>
            <div style={{ fontSize: 40, width: 100, opacity: 0.7 }}>{y.year}</div>
            <div style={{ fontSize: 32, flex: 1, fontStyle: 'italic' }}>「{y.golden_quote}」</div>
          </div>
        ))}
      </div>
      {detail.prediction && (
        <div style={{ marginTop: 40, padding: 40, border: '1px solid #F4E4BA33', borderRadius: 16 }}>
          <div style={{ fontSize: 32, color: '#E63946' }}>2029 · 主流推演</div>
          <div style={{ fontSize: 28, marginTop: 20, lineHeight: 1.5 }}>{detail.prediction.scenario_mainstream}</div>
        </div>
      )}
      <div style={{ marginTop: 40, fontSize: 24, opacity: 0.4, textAlign: 'center' }}>
        #知乎黑客松2026 · 时光答
      </div>
    </div>
  );
  const svg = await satori(jsx, {
    width: 1080, height: 1920,
    fonts: [{ name: 'Song', data: fontData, weight: 400, style: 'normal' }],
  });
  const png = new Resvg(svg).render().asPng();
  return Buffer.from(png);
}
```

- [ ] **Step 2:** 测试:

```ts
// tests/lib/poster.test.ts
import { describe, it, expect } from 'vitest';
import { renderPoster } from '../../src/lib/poster';
import fs from 'fs';

describe('poster', () => {
  it('renders a PNG buffer', async () => {
    const font = fs.readFileSync('./tests/fixtures/NotoSerifSC-Regular.ttf');
    const buf = await renderPoster({
      topic: { id: 'x', title: '测试话题' },
      years: [{ topic_id: 'x', year: 2020, primary_view: '', golden_quote: '测试金句' }],
      events: [],
      prediction: { scenario_conservative: 'a', scenario_mainstream: 'b', scenario_radical: 'c' },
    }, font.buffer);
    expect(buf.length).toBeGreaterThan(1000);
    expect(buf.subarray(1, 4).toString()).toBe('PNG');
  });
});
```

- [ ] **Step 3:** `src/app/api/poster/[id]/route.tsx`:

```ts
import { NextResponse } from 'next/server';
import fs from 'node:fs/promises';
import path from 'node:path';
import { renderPoster } from '@/lib/poster';
import { supabase } from '@/lib/supabase';

export async function GET(_req: Request, { params }: { params: { id: string } }) {
  const [topic, years, prediction] = await Promise.all([
    supabase.from('topics').select('*').eq('id', params.id).single(),
    supabase.from('year_summaries').select('*').eq('topic_id', params.id).order('year'),
    supabase.from('predictions').select('*').eq('topic_id', params.id).eq('target_year', 2029).single(),
  ]);
  if (!topic.data) return NextResponse.json({ error: 'not found' }, { status: 404 });
  const fontPath = path.join(process.cwd(), 'public', 'fonts', 'NotoSerifSC-Regular.ttf');
  const font = await fs.readFile(fontPath);
  const png = await renderPoster(
    { topic: topic.data, years: years.data ?? [], events: [], prediction: prediction.data ?? undefined },
    font.buffer,
  );
  return new Response(png, {
    headers: { 'Content-Type': 'image/png', 'Cache-Control': 'public, max-age=3600' },
  });
}
```

- [ ] **Step 4:** 下载思源宋体 Regular 放到 `public/fonts/`
- [ ] **Step 5:** 跑测试:`pnpm vitest tests/lib/poster.test.ts` 应 PASS
- [ ] **Step 6:** 浏览器访问 `/api/poster/programmer-35` 肉眼看图
- [ ] **Step 7:** 提交

```bash
git add src/lib/poster.tsx src/app/api/poster tests/lib/poster.test.ts public/fonts/
git commit -m "feat: satori-based poster rendering"
```

---

### Task P4-T2:PosterButton UI(下载 + 预览)

**Files:** Create `src/components/PosterButton.tsx`

- [ ] **Step 1:**

```tsx
'use client';
import { useState } from 'react';

export function PosterButton({ topicId }: { topicId: string }) {
  const [open, setOpen] = useState(false);
  const src = `/api/poster/${topicId}`;
  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-8 right-8 z-20 px-6 py-4 bg-stamp text-paper rounded-full shadow-xl font-hei text-sm hover:opacity-90"
      >
        生成《编年海报》
      </button>
      {open && (
        <div className="fixed inset-0 bg-ink/80 z-30 flex items-center justify-center p-8" onClick={() => setOpen(false)}>
          <div className="bg-paper p-6 rounded-lg max-w-md" onClick={e => e.stopPropagation()}>
            <img src={src} alt="poster" className="w-full rounded" />
            <div className="mt-4 flex gap-3">
              <a href={src} download={`${topicId}.png`} className="flex-1 py-3 text-center bg-ink text-paper rounded font-hei">下载</a>
              <button onClick={() => publish(topicId)} className="flex-1 py-3 bg-stamp text-paper rounded font-hei">发布到知乎想法</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

async function publish(topicId: string) {
  const r = await fetch('/api/publish', { method: 'POST', body: JSON.stringify({ topicId }) });
  if (r.status === 401) { location.href = '/api/auth/zhihu'; return; }
  alert((await r.json()).ok ? '已发到知乎想法 🎉' : '失败,请重试');
}
```

- [ ] **Step 2:** 提交

```bash
git add src/components/PosterButton.tsx && git commit -m "feat: poster preview + download + publish button"
```

---

### Task P4-T3:OAuth(知乎登录 + 回调)

**Files:** Create `src/app/api/auth/zhihu/route.ts`, `src/app/api/auth/callback/route.ts`

- [ ] **Step 1:** `api/auth/zhihu/route.ts`:

```ts
import { NextResponse } from 'next/server';
export function GET() {
  const params = new URLSearchParams({
    response_type: 'code',
    client_id: process.env.ZHIHU_CLIENT_ID!,
    redirect_uri: process.env.ZHIHU_REDIRECT_URI!,
    scope: 'publish',
    state: 'shiguangda',
  });
  return NextResponse.redirect(`https://www.zhihu.com/oauth/authorize?${params}`);
}
```

- [ ] **Step 2:** `api/auth/callback/route.ts`:

```ts
import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function GET(req: NextRequest) {
  const code = req.nextUrl.searchParams.get('code');
  if (!code) return NextResponse.redirect('/');
  const r = await fetch('https://www.zhihu.com/oauth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'authorization_code',
      code,
      client_id: process.env.ZHIHU_CLIENT_ID!,
      client_secret: process.env.ZHIHU_CLIENT_SECRET!,
      redirect_uri: process.env.ZHIHU_REDIRECT_URI!,
    }),
  });
  const { access_token, expires_in } = await r.json();
  cookies().set('zh_token', access_token, { httpOnly: true, maxAge: expires_in });
  return NextResponse.redirect('/');
}
```

- [ ] **Step 3:** 提交

```bash
git add src/app/api/auth && git commit -m "feat: zhihu oauth flow"
```

---

### Task P4-T4:一键发布到知乎想法

**Files:** Create `src/app/api/publish/route.ts`

- [ ] **Step 1:**

```ts
import { NextRequest, NextResponse } from 'next/server';
import { cookies } from 'next/headers';

export async function POST(req: NextRequest) {
  const token = cookies().get('zh_token')?.value;
  if (!token) return NextResponse.json({ error: 'auth required' }, { status: 401 });
  const { topicId } = await req.json();
  const posterUrl = `${process.env.NEXT_PUBLIC_BASE_URL}/api/poster/${topicId}`;

  // 1. 下载 PNG
  const png = Buffer.from(await (await fetch(posterUrl)).arrayBuffer());

  // 2. TODO: 若官方有图片上传接口,先上传拿 CDN URL;否则想法里只放文字 + 链接
  // 此处假设想法支持带外链
  const content = `我在《时光答》里看到了这个问题的十五年观点演变,太震撼了。\n\n${posterUrl}\n\n#知乎黑客松2026 #时光答`;

  const r = await fetch('https://developer.zhihu.com/openapi/publish/pin', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ ring_id: process.env.ZHIHU_RING_ID, content }),
  });
  const data = await r.json();
  return NextResponse.json({ ok: r.ok, data });
}
```

- [ ] **Step 2:** 注:若知乎 API 的图片上传 endpoint 确定了再补。先发纯文字 + 链接版,跑通链路
- [ ] **Step 3:** 提交

```bash
git add src/app/api/publish && git commit -m "feat: one-click publish poster to zhihu pin"
```

---

## Phase 5 · Polish + 部署

### Task P5-T1:移动端响应式与视觉微调

**Files:** Modify all `src/components/*.tsx`

- [ ] **Step 1:** 用 Chrome DevTools iPhone 13 Pro 和 iPad mini 两档逐页面走
- [ ] **Step 2:** 重点修:Timeline 在 <640px 时 padding 压缩、YearCard 标题 `text-5xl`、HomeBanner `h-[50vh]`、PredictCard 标签 wrap
- [ ] **Step 3:** 提交:`git commit -am "polish: mobile responsive pass"`

---

### Task P5-T2:错误边界 + 降级提示

**Files:** Create `src/app/error.tsx`, `src/app/not-found.tsx`

- [ ] **Step 1:** `app/error.tsx`:

```tsx
'use client';
export default function Err({ error, reset }: any) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-paper font-song text-ink p-16">
      <div>
        <h2 className="text-3xl">时光的齿轮卡住了</h2>
        <p className="mt-4 text-ink/60">{error.message}</p>
        <button onClick={reset} className="mt-6 px-4 py-2 bg-stamp text-paper rounded">重试</button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2:** `app/not-found.tsx`:

```tsx
import Link from 'next/link';
export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-paper font-song text-ink p-16 text-center">
      <div>
        <h2 className="text-4xl">这段时光还没被写下</h2>
        <Link href="/" className="mt-6 inline-block text-stamp underline">回到编年</Link>
      </div>
    </div>
  );
}
```

- [ ] **Step 3:** 提交

```bash
git add src/app/error.tsx src/app/not-found.tsx && git commit -m "polish: error + 404 pages with brand voice"
```

---

### Task P5-T3:部署到 Vercel

**Files:** None (Vercel dashboard)

- [ ] **Step 1:** `git push -u origin main`(如果还没推)
- [ ] **Step 2:** 在 Vercel 控制台 "Add New Project" → import repo
- [ ] **Step 3:** 在 Environment Variables 里把 `.env.local` 所有键值复制过去(注意 `NEXT_PUBLIC_*` 前缀的才会进前端)
- [ ] **Step 4:** 部署成功后访问 `https://<project>.vercel.app`,走一遍首页 → 话题页 → 海报 → (登录) → 发布
- [ ] **Step 5:** 注册一个短域名(可选),绑定 Vercel,更新 `ZHIHU_REDIRECT_URI`
- [ ] **Step 6:** 记录 URL 用于路演

---

## Phase 6 · 占位 + 演示

### Task P6-T1:知乎想法手动占位(刷人气奖)

**Files:** None

- [ ] **Step 1:** 选 5 个最震撼的精选话题,每个生成海报、下载
- [ ] **Step 2:** 用真人账号发布到知乎想法,文案模板:

> 我让 AI 把 [话题] 在知乎十五年的所有高赞答梳理了一遍,看到了观点的时代漂移:
>
> 2015:[早年金句]
> 2020:[中期金句]
> 2026:[当代金句]
>
> AI 还给了 2029 的推演:[主流情境]
>
> 完整时间线:shiguangda.com/topic/xxx
>
> #知乎黑客松2026 #时光答

- [ ] **Step 3:** 每天发 1-2 条,最后确保到 5/20 前有 5-8 条高质量内容挂在想法上

---

### Task P6-T2:Demo 视频脚本 + 录制

**Files:** Create `docs/demo-script.md`, `README.md`

- [ ] **Step 1:** 把 spec 第十二节的路演脚本复制到 `docs/demo-script.md`,补上每个镜头的产品画面对照
- [ ] **Step 2:** 用 Loom 或 OBS 录 3 分钟视频(含旁白)
- [ ] **Step 3:** `README.md` 写产品介绍(直接采用 spec 的"一、产品定位"为主体)
- [ ] **Step 4:** 提交

```bash
git add docs/ README.md && git commit -m "docs: demo script + product readme"
```

---

### Task P6-T3:作品提交

**Files:** None

- [ ] **Step 1:** 截止 5/14 13:00 前,在官方提交页填写:
  - 项目名:时光答 / Chronoq
  - 体验链接:Vercel 生产域名
  - 产品说明:从 README.md 复制
  - 代码仓库:GitHub 链接(提交前先 `git push`)
  - 赛道勾选:灵感引擎(主)+ 引力场(次)

---

## ✅ 最终验收清单(提报前 walkthrough)

- [ ] 首页:Banner 展示今日热榜话题,下面 3 列瀑布流 30 个精选
- [ ] 搜索框输入任意词,精选库命中跳话题页;未命中展示浅层时光轴
- [ ] 点进任一话题:标题 + 时间轴(每年卡 + 事件锚点气泡)+ 2029 预测三情境 + 浮动海报按钮
- [ ] 点"生成编年海报":模态框里展示 PNG,可下载,可点"发布到知乎想法"
- [ ] 未登录时点发布 → 跳 OAuth → 回来自动发帖
- [ ] 移动端 iPhone 尺寸体验流畅
- [ ] 404 / 500 页有品牌调性
- [ ] Vercel 生产环境稳定 24h 无宕机
- [ ] 想法广场有 5+ 条海报占位
- [ ] Demo 视频 3 分钟、场景完整
- [ ] 代码仓库 README 完整

---

## 📋 若进入决赛路演前的增强项(optional,5/15)

- 现场投屏稳定性测试(用 4G 热点跑一次,防止 798 网络)
- 路演用话题选最戏剧的 3 个,提前预热缓存
- 路演结束 Q&A 准备:隐私 / 伦理 / 商业化 / 差异化 / 扩展性
- Backup:如果 Vercel 挂了,有本地 localhost 兜底

---

## 🔚 结束语

这份计划里每个任务都做到"照着抄就能跑"的颗粒度。如果前置材料清单的 M1-M14 齐了,Phase 0 可以赛前一天完成,Phase 1 可以赛前一晚 + 开赛第一晚并行跑,Phase 2-5 严格按 48h 切片走。

技术栈所有选择都是可兜底的:LLM 可切、DB 可切、部署可切、视觉风格已设计稿定案,理论风险全部在 spec 第十一节里被 mitigate 过。

**剩下的就是执行。**
