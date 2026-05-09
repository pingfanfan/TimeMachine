# 《时光档案馆》实施计划增量(v2)

> 在原 v1 plan(`2026-04-23-shiguangda-plan.md`)基础上的增量任务。
> v1 大部分任务沿用,本文档列出**新增 / 修改的**任务,按 v2 spec(`2026-05-09-museum-upgrade.md`)执行。

**Goal:** 把原"时光答"工具产品升级为"时光档案馆"内容机构产品。新增策展三件套(主题/年代/金句)+ 视觉博物馆化 + 首页重构。

**追加架构:** 在 Phase 0 / Phase 1 / Phase 2 各加少量任务;**新增 Phase 2.5 策展页三件套**;Phase 4 海报模板换风格;Phase 5 视觉升级。

---

## 📦 前置材料增量(在 v1 SETUP 基础上)

| # | 材料 | 来源 | 必需? |
|---|---|---|---|
| M15 | **6 篇主题专辑导语**(各 200-400 字) | 半 AI 半人工:DeepSeek 起稿 + 你润色 | ⭐ 必需,Day 0 完成 |
| M16 | **3 篇年代档案导语** | 同上 | ⭐ 必需 |
| M17 | **金句博物馆导语 + 1-3 篇策展人手记** | 同上 | ⭐ 必需 |
| M18 | **入档章 / 档案印章 SVG**(2-3 个变体) | Figma 出图,或纯 CSS 实现 | 🟡 建议 |

---

## Phase 0 增量

### Task P0-T4-v2:LLM 客户端升级(双 LLM 路由 + 本地 embedding)

**Files:** Modify `scripts/_lib/llm.py`, `scripts/pyproject.toml`

> 你已有 Claude API + DeepSeek API。把 `_lib/llm.py` 升级为支持双 LLM 路由 + 本地 bge-m3 embedding。完整设计见 `docs/LLM-ROUTING.md`。

- [ ] **Step 1:** `scripts/pyproject.toml` 加依赖

```toml
dependencies = [
  ...
  "anthropic",
  "sentence-transformers",
  "torch",
]
```

- [ ] **Step 2:** 把 `scripts/_lib/llm.py` 整个替换为 `docs/LLM-ROUTING.md` 第 4 节的版本

- [ ] **Step 3:** `.env.local` 确认有 `DEEPSEEK_API_KEY` + `ANTHROPIC_API_KEY`

- [ ] **Step 4:** 跑通 smoke test

```python
# scripts/smoke_llm.py
from _lib.llm import chat, embed
print(chat([{"role":"user","content":"返回 JSON {\"ok\": true}"}], quality="fast", json_mode=True))
print(chat([{"role":"user","content":"用一句话写'时光档案馆'的产品定位"}], quality="high"))
print(chat([{"role":"user","content":"用克制的衬线感语言写一句博物馆开馆词"}], quality="best"))
print(len(embed(["测试", "今天天气真好"])[0]))  # 应输出 1024
```

- [ ] **Step 5:** Commit

```bash
git add scripts/_lib/llm.py scripts/pyproject.toml scripts/smoke_llm.py
git commit -m "infra(v2): dual-LLM router (DeepSeek+Claude) + local bge-m3 embed"
```

### Task P0-T3-v2:Schema 升级(替换 v1 的 P0-T3)

**Files:** Modify `supabase/migrations/0001_init.sql`(在 v1 的 SQL 后面追加)

- [ ] **Step 1:** 追加新表的 SQL

```sql
-- v2: 给 topics 加档案编号
ALTER TABLE topics ADD COLUMN archive_no TEXT;

-- v2: 给 year_summaries 加情绪 tag(用于金句博物馆筛选)
ALTER TABLE year_summaries ADD COLUMN mood TEXT;

-- v2: 策展专辑
CREATE TABLE collections (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  subtitle TEXT,
  archive_no TEXT NOT NULL,
  category TEXT NOT NULL,           -- theme / decade / mood
  curator_intro TEXT,
  curator_name TEXT DEFAULT '看山',
  cover_image_url TEXT,
  display_rank INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE collection_topics (
  collection_id TEXT REFERENCES collections(id) ON DELETE CASCADE,
  topic_id TEXT REFERENCES topics(id) ON DELETE CASCADE,
  topic_rank INT,
  curator_note TEXT,
  PRIMARY KEY (collection_id, topic_id)
);

CREATE TABLE curator_notes (
  id SERIAL PRIMARY KEY,
  title TEXT,
  body TEXT,
  publish_date DATE,
  curator_name TEXT DEFAULT '看山'
);

CREATE INDEX idx_collections_category ON collections(category);
CREATE INDEX idx_year_summaries_mood ON year_summaries(mood);
```

- [ ] **Step 2:** 在 Supabase SQL Editor 跑

- [ ] **Step 3:** Commit

```bash
git add supabase/ && git commit -m "db: v2 museum schema (collections, mood, archive_no)"
```

---

### Task P0-T5(新):内容种子文件

**Files:** Create `data/collections.seed.json`, `data/curator_notes.seed.json`

- [ ] **Step 1:** `data/collections.seed.json` 模板:

```json
[
  {
    "id": "35-of-china",
    "title": "35 岁的中国人",
    "subtitle": "十五年焦虑史",
    "archive_no": "THEME-001",
    "category": "theme",
    "curator_intro": "[在此粘贴 200-400 字导语,Day 0 写好]",
    "display_rank": 1,
    "topic_ids": ["programmer-35", "mid-life-management", "savings-at-35", "marriage-at-35"]
  },
  {
    "id": "marriage-collapse",
    "title": "婚恋观的代际崩塌",
    "subtitle": "从'必须结'到'为什么结'",
    "archive_no": "THEME-002",
    "category": "theme",
    "curator_intro": "[导语]",
    "display_rank": 2,
    "topic_ids": ["marriage-brideprice", "marriage-necessity", "dink", "blind-date"]
  },
  {
    "id": "worker-fall",
    "title": "打工人的精神跌落",
    "subtitle": "从奋斗到躺平到逃离",
    "archive_no": "THEME-003",
    "category": "theme",
    "curator_intro": "[导语]",
    "display_rank": 3,
    "topic_ids": ["996", "lying-flat", "side-hustle", "running-abroad"]
  },
  {
    "id": "consumption-yo-yo",
    "title": "消费观的来回",
    "subtitle": "经济周期里的金钱矛盾",
    "archive_no": "THEME-004",
    "category": "theme",
    "curator_intro": "[导语]",
    "display_rank": 4,
    "topic_ids": ["buy-house", "consumption-downgrade", "savings", "luxury"]
  },
  {
    "id": "ai-anxiety-prequel",
    "title": "AI 焦虑前传",
    "subtitle": "从惊艳到恐慌到接受",
    "archive_no": "THEME-005",
    "category": "theme",
    "curator_intro": "[导语]",
    "display_rank": 5,
    "topic_ids": ["chatgpt-replace", "ai-replace-whitecollar", "programmer-pivot", "ai-agent"]
  },
  {
    "id": "education-lost",
    "title": "教育的迷失",
    "subtitle": "内卷与解构的十五年拉扯",
    "archive_no": "THEME-006",
    "category": "theme",
    "curator_intro": "[导语]",
    "display_rank": 6,
    "topic_ids": ["postgrad-exam", "study-abroad", "tiger-parenting", "double-reduction", "major-choice"]
  },
  {
    "id": "decade-2015",
    "title": "2015",
    "subtitle": "双创热与第一次焦虑",
    "archive_no": "DECADE-2015",
    "category": "decade",
    "curator_intro": "[导语]",
    "display_rank": 7,
    "topic_ids": []
  },
  {
    "id": "decade-2020",
    "title": "2020",
    "subtitle": "疫情下的中国人",
    "archive_no": "DECADE-2020",
    "category": "decade",
    "curator_intro": "[导语]",
    "display_rank": 8,
    "topic_ids": []
  },
  {
    "id": "decade-2024",
    "title": "2024",
    "subtitle": "AI 时代的开端",
    "archive_no": "DECADE-2024",
    "category": "decade",
    "curator_intro": "[导语]",
    "display_rank": 9,
    "topic_ids": []
  }
]
```

> **注:** `topic_ids` 必须和 `data/topics.seed.json` 里的 id 对应。年代档案的 topic_ids 留空,后续脚本根据有该年 year_summary 的话题自动挂上。

- [ ] **Step 2:** `data/curator_notes.seed.json`(3 篇短文,200-400 字/篇):

```json
[
  {
    "title": "本周入档 · 关于'体面'",
    "body": "[策展人手记 #1]",
    "publish_date": "2026-05-12"
  },
  {
    "title": "策展札记 · 时间是怎么回答问题的",
    "body": "[策展人手记 #2]",
    "publish_date": "2026-05-13"
  },
  {
    "title": "致来访者 · 这座馆的来由",
    "body": "[策展人手记 #3]",
    "publish_date": "2026-05-14"
  }
]
```

- [ ] **Step 3:** Commit

```bash
git add data/collections.seed.json data/curator_notes.seed.json
git commit -m "data: seed collections (themes/decades) + curator notes"
```

---

## Phase 1 增量

### Task P1-T7(新):情绪标注 + archive_no 生成

> **路由:** 该任务用 `chat(..., quality="fast")` (DeepSeek)。



**Files:** Create `scripts/08_mood_and_archive_no.py`

- [ ] **Step 1:**

```python
import json
from _lib.llm import chat
from _lib.db import conn

MOODS = ["焦虑", "希望", "戏谑", "悲怆", "理性", "愤怒", "迷茫", "释然"]

def tag_mood(quote: str, view: str) -> str:
    prompt = f"""下面是一段知乎金句和当年的主流观点:

金句: {quote}
主流观点: {view}

从以下情绪中选 1 个最贴切的: {", ".join(MOODS)}
只返回情绪词,不要其他内容。"""
    return chat([{"role": "user", "content": prompt}]).strip()

def main():
    with conn() as c, c.cursor() as cur:
        # 1. 给所有 topics 分配 archive_no
        cur.execute("SELECT id FROM topics ORDER BY featured_rank, id")
        for i, (tid,) in enumerate(cur.fetchall(), 1):
            cur.execute("UPDATE topics SET archive_no=%s WHERE id=%s", (f"ARCHIVE-{i:03d}", tid))

        # 2. 给所有 year_summaries 打 mood 标签
        cur.execute("SELECT topic_id, year, golden_quote, primary_view FROM year_summaries WHERE mood IS NULL AND golden_quote IS NOT NULL")
        for tid, year, quote, view in cur.fetchall():
            mood = tag_mood(quote, view)
            cur.execute("UPDATE year_summaries SET mood=%s WHERE topic_id=%s AND year=%s", (mood, tid, year))
        c.commit()
        print("mood + archive_no ✓")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2:** 跑 + 提交

```bash
uv run python scripts/08_mood_and_archive_no.py
git add scripts/08_mood_and_archive_no.py
git commit -m "pipeline: mood tagging + archive_no assignment"
```

### Task P1-T8(新):导入 collections + curator_notes

**Files:** Create `scripts/09_import_collections.py`

- [ ] **Step 1:**

```python
import json
from pathlib import Path
from _lib.db import conn

ROOT = Path(__file__).parent.parent

def main():
    cols = json.loads((ROOT / "data/collections.seed.json").read_text())
    notes = json.loads((ROOT / "data/curator_notes.seed.json").read_text())

    with conn() as c, c.cursor() as cur:
        # 1. 入库 collections
        for col in cols:
            cur.execute("""
                INSERT INTO collections (id, title, subtitle, archive_no, category, curator_intro, display_rank)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title, subtitle=EXCLUDED.subtitle, curator_intro=EXCLUDED.curator_intro
            """, (col["id"], col["title"], col["subtitle"], col["archive_no"], col["category"], col["curator_intro"], col["display_rank"]))

            # 2. 关联话题(theme 类用 seed 里的;decade 类自动从 year_summaries 拉)
            if col["category"] == "theme":
                topic_ids = col["topic_ids"]
            elif col["category"] == "decade":
                year = int(col["archive_no"].split("-")[1])
                cur.execute("SELECT DISTINCT topic_id FROM year_summaries WHERE year=%s", (year,))
                topic_ids = [r[0] for r in cur.fetchall()]
            else:
                topic_ids = []

            cur.execute("DELETE FROM collection_topics WHERE collection_id=%s", (col["id"],))
            for rank, tid in enumerate(topic_ids, 1):
                cur.execute("INSERT INTO collection_topics (collection_id, topic_id, topic_rank) VALUES (%s,%s,%s)", (col["id"], tid, rank))

        # 3. 入库手记
        cur.execute("DELETE FROM curator_notes")
        for n in notes:
            cur.execute("INSERT INTO curator_notes (title, body, publish_date) VALUES (%s,%s,%s)", (n["title"], n["body"], n["publish_date"]))

        c.commit()
        print(f"collections: {len(cols)}, notes: {len(notes)} ✓")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2:** 跑 + 提交

```bash
uv run python scripts/09_import_collections.py
git add scripts/09_import_collections.py
git commit -m "pipeline: import collections and curator notes"
```

---

## Phase 2 重构 · 档案馆 Foyer 首页

> **替换 v1 的 P2-T5(原首页)。** 旧的 `src/app/page.tsx` 重写。

### Task P2-T5-v2:档案馆 Foyer 首页

**Files:** Rewrite `src/app/page.tsx`; Create `src/components/FoyerHero.tsx`, `src/components/ArchiveGateways.tsx`, `src/components/CuratorNote.tsx`, `src/components/ArchiveStamp.tsx`

- [ ] **Step 1:** `src/components/ArchiveStamp.tsx`(全局复用的"档案章"组件):

```tsx
export function ArchiveStamp({ no, color = 'stamp' }: { no: string; color?: 'stamp' | 'highlight' }) {
  return (
    <div className={`inline-flex items-center justify-center px-3 py-1 border-2 border-${color} text-${color} font-mono text-xs tracking-widest rotate-[-3deg] opacity-90`}>
      {no}
    </div>
  );
}
```

- [ ] **Step 2:** `src/components/FoyerHero.tsx`(首屏):

```tsx
import { supabase } from '@/lib/supabase';

export async function FoyerHero() {
  const [{ count: tCount }, { count: qCount }] = await Promise.all([
    supabase.from('topics').select('*', { count: 'exact', head: true }),
    supabase.from('year_summaries').select('*', { count: 'exact', head: true }).not('golden_quote', 'is', null),
  ]);
  return (
    <section className="min-h-[80vh] bg-ink text-paper flex flex-col items-center justify-center px-8 text-center">
      <div className="font-mono text-xs tracking-[0.3em] text-mute">EST. 2026 · ZHIHU CHRONICLE</div>
      <h1 className="mt-8 font-song text-6xl md:text-8xl leading-tight">时光档案馆</h1>
      <p className="mt-4 font-song text-xl md:text-2xl text-paper/60 italic">知乎思想编年志</p>
      <div className="mt-12 font-mono text-sm text-mute">
        馆藏 <span className="text-paper">{tCount}</span> 份档案 · <span className="text-paper">{qCount}</span> 份金句 · 跨越 <span className="text-paper">15</span> 年
      </div>
    </section>
  );
}
```

- [ ] **Step 3:** `src/components/ArchiveGateways.tsx`(三大入口):

```tsx
import Link from 'next/link';

const GATES = [
  { href: '/archive/themes',  no: 'THEME',   title: '主题档案',  desc: '《35 岁的中国人》等 6 份策展',  emoji: '📚' },
  { href: '/archive/decades', no: 'DECADE',  title: '年代切片',  desc: '2011-2026 每一年的中国人在想什么', emoji: '📅' },
  { href: '/archive/quotes',  no: 'QUOTES',  title: '金句博物馆', desc: '481 句穿越十五年的精华', emoji: '💎' },
];

export function ArchiveGateways() {
  return (
    <section className="bg-paper py-24 px-8">
      <div className="max-w-6xl mx-auto grid md:grid-cols-3 gap-6">
        {GATES.map(g => (
          <Link key={g.no} href={g.href} className="group border border-ink/15 bg-paper hover:border-stamp transition p-10 flex flex-col">
            <div className="font-mono text-xs text-mute tracking-widest">{g.no}</div>
            <div className="mt-2 text-5xl">{g.emoji}</div>
            <h3 className="mt-6 font-song text-3xl text-ink">{g.title}</h3>
            <p className="mt-3 font-hei text-base text-ink/60">{g.desc}</p>
            <div className="mt-auto pt-8 font-mono text-xs text-stamp group-hover:translate-x-1 transition">→ 进入档案</div>
          </Link>
        ))}
      </div>
    </section>
  );
}
```

- [ ] **Step 4:** `src/components/CuratorNote.tsx`:

```tsx
import { supabase } from '@/lib/supabase';

export async function CuratorNote() {
  const { data } = await supabase.from('curator_notes').select('*').order('publish_date', { ascending: false }).limit(1).single();
  if (!data) return null;
  return (
    <section className="bg-ink text-paper py-24 px-8">
      <div className="max-w-2xl mx-auto">
        <div className="font-mono text-xs text-mute tracking-widest">CURATOR'S NOTE</div>
        <h2 className="mt-4 font-song text-4xl">{data.title}</h2>
        <p className="mt-8 font-song text-lg leading-relaxed text-paper/80 whitespace-pre-line">{data.body}</p>
        <div className="mt-8 font-hei text-sm text-paper/50">— 策展人 · {data.curator_name}</div>
      </div>
    </section>
  );
}
```

- [ ] **Step 5:** Rewrite `src/app/page.tsx`:

```tsx
import { FoyerHero } from '@/components/FoyerHero';
import { ArchiveGateways } from '@/components/ArchiveGateways';
import { TopicGrid } from '@/components/TopicGrid';
import { CuratorNote } from '@/components/CuratorNote';
import { SearchBox } from '@/components/SearchBox';
import { supabase } from '@/lib/supabase';

export const revalidate = 3600;

export default async function Home() {
  const { data: featured } = await supabase
    .from('topics')
    .select('*')
    .order('featured_rank')
    .limit(12);

  return (
    <main className="bg-paper min-h-screen">
      <FoyerHero />
      <ArchiveGateways />
      <SearchBox />
      <section className="max-w-6xl mx-auto px-8 py-16">
        <header className="mb-12">
          <div className="font-mono text-xs text-mute tracking-widest">FEATURED ARCHIVES · 精选档案</div>
          <h2 className="mt-2 font-song text-4xl text-ink">本馆精选条目</h2>
        </header>
        <TopicGrid topics={featured ?? []} />
      </section>
      <CuratorNote />
    </main>
  );
}
```

- [ ] **Step 6:** 同时修改 `TopicCard.tsx`,加 archive_no 印章:

```tsx
import Link from 'next/link';
import { ArchiveStamp } from './ArchiveStamp';
import type { Topic } from '@/lib/types';

export function TopicCard({ t }: { t: Topic }) {
  return (
    <Link href={`/topic/${t.id}`} className="block border border-ink/10 p-6 bg-paper hover:border-stamp transition group relative">
      <div className="absolute top-4 right-4">
        {t.archive_no && <ArchiveStamp no={t.archive_no} />}
      </div>
      <div className="text-xs font-mono text-mute mb-2 tracking-widest">{t.category}</div>
      <h3 className="font-song text-xl leading-snug pr-20">{t.title}</h3>
      <div className="mt-6 space-y-2 text-sm font-song text-ink/70">
        <p className="italic">「{t.cover_quote_old}」<span className="text-mute ml-2 font-mono text-xs">· 早年</span></p>
        <p className="italic text-stamp">「{t.cover_quote_new}」<span className="text-mute ml-2 font-mono text-xs">· 2026</span></p>
      </div>
    </Link>
  );
}
```

- [ ] **Step 7:** Commit

```bash
git add -A && git commit -m "feat(v2): museum foyer homepage + archive stamps"
```

---

## Phase 2.5(全新)· 策展页三件套

### Task P25-T1:主题档案首页 + 详情页

**Files:** Create `src/app/archive/themes/page.tsx`, `src/app/archive/themes/[slug]/page.tsx`, `src/components/CollectionCard.tsx`

- [ ] **Step 1:** `src/components/CollectionCard.tsx`:

```tsx
import Link from 'next/link';
import { ArchiveStamp } from './ArchiveStamp';

export function CollectionCard({ c, hrefBase }: { c: any; hrefBase: string }) {
  return (
    <Link href={`${hrefBase}/${c.id}`} className="block bg-ink text-paper p-10 group relative aspect-[3/4]">
      <ArchiveStamp no={c.archive_no} color="highlight" />
      <h3 className="mt-12 font-song text-4xl leading-tight">{c.title}</h3>
      <p className="mt-3 font-song text-paper/60 italic">{c.subtitle}</p>
      <div className="absolute bottom-10 left-10 right-10 font-mono text-xs text-paper/40 tracking-widest">→ 进入策展</div>
    </Link>
  );
}
```

- [ ] **Step 2:** `src/app/archive/themes/page.tsx`:

```tsx
import { supabase } from '@/lib/supabase';
import { CollectionCard } from '@/components/CollectionCard';

export const revalidate = 86400;

export default async function ThemesIndex() {
  const { data } = await supabase.from('collections').select('*').eq('category', 'theme').order('display_rank');
  return (
    <main className="bg-paper min-h-screen px-8 py-16">
      <header className="max-w-4xl mx-auto mb-16">
        <div className="font-mono text-xs text-mute tracking-widest">ARCHIVE · THEMES</div>
        <h1 className="mt-2 font-song text-5xl text-ink">主题档案</h1>
        <p className="mt-4 font-song text-lg text-ink/60 italic">策展人精选的 6 份主题档案,每一份都是一组话题的时代切片故事。</p>
      </header>
      <section className="max-w-6xl mx-auto grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {(data ?? []).map(c => <CollectionCard key={c.id} c={c} hrefBase="/archive/themes" />)}
      </section>
    </main>
  );
}
```

- [ ] **Step 3:** `src/app/archive/themes/[slug]/page.tsx`:

```tsx
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { supabase } from '@/lib/supabase';
import { ArchiveStamp } from '@/components/ArchiveStamp';

export const revalidate = 86400;

export default async function ThemeDetail({ params }: { params: { slug: string } }) {
  const { data: col } = await supabase.from('collections').select('*').eq('id', params.slug).single();
  if (!col) notFound();
  const { data: topics } = await supabase
    .from('collection_topics')
    .select('topic_rank, topics(id, title, archive_no, cover_quote_old, cover_quote_new, category)')
    .eq('collection_id', params.slug)
    .order('topic_rank');

  return (
    <main className="bg-paper min-h-screen">
      {/* 封面 */}
      <section className="bg-ink text-paper py-32 px-8">
        <div className="max-w-4xl mx-auto">
          <ArchiveStamp no={col.archive_no} color="highlight" />
          <h1 className="mt-8 font-song text-6xl md:text-7xl">{col.title}</h1>
          <p className="mt-4 font-song text-2xl text-paper/60 italic">{col.subtitle}</p>
          <div className="mt-12 font-song text-lg leading-relaxed text-paper/80 whitespace-pre-line max-w-2xl">{col.curator_intro}</div>
          <div className="mt-8 font-hei text-sm text-paper/50">— 策展人 · {col.curator_name}</div>
        </div>
      </section>

      {/* 话题列表 */}
      <section className="max-w-3xl mx-auto px-8 py-24">
        <header className="mb-12">
          <div className="font-mono text-xs text-mute tracking-widest">CONTAINS · {topics?.length ?? 0} ENTRIES</div>
          <h2 className="mt-2 font-song text-3xl text-ink">本档案收录</h2>
        </header>
        <ul className="divide-y divide-ink/10">
          {(topics ?? []).map(({ topics: t }: any) => (
            <li key={t.id}>
              <Link href={`/topic/${t.id}`} className="block py-8 group">
                <div className="font-mono text-xs text-mute tracking-widest">{t.archive_no} · {t.category}</div>
                <h3 className="mt-2 font-song text-2xl text-ink group-hover:text-stamp transition">{t.title}</h3>
                <div className="mt-3 text-sm font-song text-ink/60 italic">「{t.cover_quote_new}」</div>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
```

- [ ] **Step 4:** Commit

```bash
git add src/app/archive/themes src/components/CollectionCard.tsx
git commit -m "feat(v2): theme archives index + detail pages"
```

### Task P25-T2:年代档案首页 + 详情页

**Files:** Create `src/app/archive/decades/page.tsx`, `src/app/archive/decades/[year]/page.tsx`

- [ ] **Step 1:** `decades/page.tsx`(垂直时间梯,3 个年代档案):

```tsx
import Link from 'next/link';
import { supabase } from '@/lib/supabase';

export const revalidate = 86400;

export default async function DecadesIndex() {
  const { data } = await supabase.from('collections').select('*').eq('category', 'decade').order('archive_no');
  return (
    <main className="bg-paper min-h-screen px-8 py-16">
      <header className="max-w-4xl mx-auto mb-16">
        <div className="font-mono text-xs text-mute tracking-widest">ARCHIVE · DECADES</div>
        <h1 className="mt-2 font-song text-5xl text-ink">年代切片</h1>
        <p className="mt-4 font-song text-lg text-ink/60 italic">每一年的中国人,在想什么。</p>
      </header>
      <section className="max-w-3xl mx-auto">
        {(data ?? []).map(c => {
          const year = c.archive_no.split('-')[1];
          return (
            <Link key={c.id} href={`/archive/decades/${year}`} className="block border-l-4 border-stamp pl-8 py-12 group">
              <div className="font-mono text-xs text-mute tracking-widest">{c.archive_no}</div>
              <div className="mt-2 font-song text-7xl text-ink group-hover:text-stamp transition">{year}</div>
              <p className="mt-4 font-song text-2xl text-ink/70 italic">{c.subtitle}</p>
              <div className="mt-4 text-sm text-mute">{c.curator_intro?.slice(0, 80)}…</div>
            </Link>
          );
        })}
      </section>
    </main>
  );
}
```

- [ ] **Step 2:** `decades/[year]/page.tsx`:

```tsx
import { notFound } from 'next/navigation';
import Link from 'next/link';
import { supabase } from '@/lib/supabase';

export const revalidate = 86400;

export default async function DecadeDetail({ params }: { params: { year: string } }) {
  const archive_no = `DECADE-${params.year}`;
  const { data: col } = await supabase.from('collections').select('*').eq('archive_no', archive_no).single();
  if (!col) notFound();

  // 拉该年的所有 year_summaries
  const { data: summaries } = await supabase
    .from('year_summaries')
    .select('topic_id, primary_view, golden_quote, mood, topics(title, archive_no)')
    .eq('year', parseInt(params.year));

  return (
    <main className="bg-paper min-h-screen">
      <section className="bg-ink text-paper py-32 px-8 text-center">
        <div className="font-mono text-xs text-mute tracking-widest">{col.archive_no}</div>
        <h1 className="mt-4 font-song text-9xl">{params.year}</h1>
        <p className="mt-4 font-song text-3xl text-paper/60 italic">{col.subtitle}</p>
        <div className="mt-12 font-song text-lg max-w-2xl mx-auto leading-relaxed text-paper/80 whitespace-pre-line">{col.curator_intro}</div>
      </section>
      <section className="max-w-3xl mx-auto px-8 py-24">
        <header className="mb-12">
          <div className="font-mono text-xs text-mute tracking-widest">{params.year} 年的所有讨论</div>
          <h2 className="mt-2 font-song text-3xl text-ink">这一年大家在想…</h2>
        </header>
        <ul className="space-y-8">
          {(summaries ?? []).map((s: any) => (
            <li key={s.topic_id} className="border-l-2 border-ink/20 pl-6">
              <Link href={`/topic/${s.topic_id}`} className="group">
                <div className="font-mono text-xs text-mute">{s.topics?.archive_no}</div>
                <h3 className="mt-1 font-song text-xl text-ink group-hover:text-stamp transition">{s.topics?.title}</h3>
                <p className="mt-2 font-song text-base text-ink/70 italic">「{s.golden_quote}」</p>
                {s.mood && <span className="mt-2 inline-block px-2 py-0.5 bg-stamp/10 text-stamp text-xs font-mono">{s.mood}</span>}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
```

- [ ] **Step 3:** Commit

```bash
git add src/app/archive/decades && git commit -m "feat(v2): decade archives index + detail"
```

### Task P25-T3:金句博物馆

**Files:** Create `src/app/archive/quotes/page.tsx`, `src/components/QuoteCard.tsx`, `src/components/QuoteFilters.tsx`

- [ ] **Step 1:** `QuoteCard.tsx`:

```tsx
import Link from 'next/link';

export function QuoteCard({ q }: { q: any }) {
  return (
    <Link href={`/topic/${q.topic_id}#year-${q.year}`} className="block bg-paper border border-ink/10 p-8 hover:border-stamp transition">
      <div className="flex items-baseline justify-between font-mono text-xs text-mute">
        <span>{q.year}</span>
        {q.mood && <span className="text-stamp">{q.mood}</span>}
      </div>
      <blockquote className="mt-4 font-song text-xl leading-relaxed italic text-ink">「{q.golden_quote}」</blockquote>
      {q.quote_author && <cite className="mt-3 block text-sm not-italic font-hei text-ink/60">— {q.quote_author}</cite>}
      <div className="mt-4 text-xs font-hei text-mute">所属档案: {q.topics?.title}</div>
    </Link>
  );
}
```

- [ ] **Step 2:** `QuoteFilters.tsx`(client component for筛选):

```tsx
'use client';
import { useState, useEffect } from 'react';
import { QuoteCard } from './QuoteCard';

export function QuoteFilters({ initial }: { initial: any[] }) {
  const [year, setYear] = useState<number | null>(null);
  const [mood, setMood] = useState<string | null>(null);
  const filtered = initial.filter(q => (!year || q.year === year) && (!mood || q.mood === mood));

  const years = [...new Set(initial.map(q => q.year))].sort();
  const moods = [...new Set(initial.map(q => q.mood).filter(Boolean))];

  return (
    <>
      <div className="flex flex-wrap gap-2 mb-12">
        <button onClick={() => { setYear(null); setMood(null); }} className="px-3 py-1 border border-ink/20 text-xs font-mono">全部 {initial.length}</button>
        {years.map(y => <button key={y} onClick={() => setYear(y === year ? null : y)} className={`px-3 py-1 border text-xs font-mono ${year===y?'bg-ink text-paper':'border-ink/20'}`}>{y}</button>)}
        <span className="px-2 self-center text-mute">·</span>
        {moods.map(m => <button key={m} onClick={() => setMood(m === mood ? null : m)} className={`px-3 py-1 border text-xs font-mono ${mood===m?'bg-stamp text-paper':'border-stamp/30 text-stamp'}`}>{m}</button>)}
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filtered.map((q, i) => <QuoteCard key={i} q={q} />)}
      </div>
    </>
  );
}
```

- [ ] **Step 3:** `quotes/page.tsx`:

```tsx
import { supabase } from '@/lib/supabase';
import { QuoteFilters } from '@/components/QuoteFilters';

export const revalidate = 86400;

export default async function QuotesPage() {
  const { data } = await supabase
    .from('year_summaries')
    .select('topic_id, year, golden_quote, quote_author, mood, topics(title)')
    .not('golden_quote', 'is', null)
    .order('year', { ascending: false });

  return (
    <main className="bg-paper min-h-screen px-8 py-16">
      <header className="max-w-4xl mx-auto mb-16">
        <div className="font-mono text-xs text-mute tracking-widest">ARCHIVE · QUOTE MUSEUM</div>
        <h1 className="mt-2 font-song text-5xl text-ink">金句博物馆</h1>
        <p className="mt-4 font-song text-lg text-ink/60 italic">{data?.length ?? 0} 句穿越十五年的精华,按年份与情绪整理。</p>
      </header>
      <section className="max-w-6xl mx-auto">
        <QuoteFilters initial={data ?? []} />
      </section>
    </main>
  );
}
```

- [ ] **Step 4:** Commit

```bash
git add src/app/archive/quotes src/components/QuoteCard.tsx src/components/QuoteFilters.tsx
git commit -m "feat(v2): quote museum with year + mood filters"
```

---

## Phase 4 修改 · 海报模板换为档案副本风

### Task P4-T1-v2:档案副本风海报

**Files:** Modify `src/lib/poster.tsx`

- [ ] **Step 1:** 替换 satori JSX,改为档案副本风格:

```tsx
const jsx = (
  <div style={{
    width: 1080, height: 1920, background: '#08101F', color: '#EBE0C4',
    padding: 80, fontFamily: 'Song', display: 'flex', flexDirection: 'column',
  }}>
    {/* 顶部档案 header */}
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', borderBottom: '2px solid #5A6478', paddingBottom: 20 }}>
      <div style={{ fontFamily: 'Mono', fontSize: 18, color: '#5A6478', letterSpacing: 4 }}>
        档案 {detail.topic.archive_no} · 馆藏第 {detail.topic.archive_no?.split('-')[1]} 号
      </div>
      <div style={{ fontFamily: 'Mono', fontSize: 18, color: '#A8252F', letterSpacing: 4 }}>ZHIHU CHRONICLE</div>
    </div>

    {/* 标题 */}
    <div style={{ fontSize: 80, marginTop: 60, lineHeight: 1.1, fontWeight: 700 }}>
      {detail.topic.title}
    </div>

    {/* 时间轴金句 */}
    <div style={{ flex: 1, marginTop: 80, display: 'flex', flexDirection: 'column', gap: 32 }}>
      {detail.years.slice(-6).map((y) => (
        <div key={y.year} style={{ display: 'flex', gap: 32 }}>
          <div style={{ fontFamily: 'Mono', fontSize: 36, width: 120, color: '#5A6478' }}>{y.year}</div>
          <div style={{ fontSize: 32, flex: 1, fontStyle: 'italic', borderLeft: '3px solid #A8252F', paddingLeft: 24 }}>「{y.golden_quote}」</div>
        </div>
      ))}
    </div>

    {/* 2029 预测 */}
    {detail.prediction && (
      <div style={{ marginTop: 60, padding: 32, border: '1px solid #5A6478' }}>
        <div style={{ fontSize: 24, color: '#F1B644', fontFamily: 'Mono', letterSpacing: 4 }}>2029 · 主流推演</div>
        <div style={{ fontSize: 28, marginTop: 16, lineHeight: 1.5 }}>{detail.prediction.scenario_mainstream}</div>
      </div>
    )}

    {/* 底部 footer */}
    <div style={{ marginTop: 60, display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #5A6478', paddingTop: 20, fontFamily: 'Mono', fontSize: 18, color: '#5A6478' }}>
      <span>策展人 · 看山</span>
      <span>#知乎黑客松2026 · 时光档案馆</span>
    </div>
  </div>
);
```

- [ ] **Step 2:** Commit

```bash
git add src/lib/poster.tsx && git commit -m "feat(v2): museum-style document poster"
```

---

## Phase 5 增量 · 视觉 polish

### Task P5-T4(新):tailwind tokens 升级

**Files:** Modify `tailwind.config.ts`

- [ ] **Step 1:** 替换 colors:

```ts
colors: {
  ink: '#08101F',
  paper: '#EBE0C4',
  stamp: '#A8252F',
  mute: '#5A6478',
  highlight: '#F1B644',
}
```

- [ ] **Step 2:** 加 fontFamily mono:

```ts
fontFamily: {
  song: ['"Noto Serif SC"', 'serif'],
  hei:  ['"Noto Sans SC"', 'sans-serif'],
  mono: ['Iosevka', '"JetBrains Mono"', 'monospace'],
}
```

- [ ] **Step 3:** Commit

```bash
git add tailwind.config.ts && git commit -m "polish(v2): museum design tokens"
```

### Task P5-T5(新):全局 nav + 面包屑

**Files:** Modify `src/app/layout.tsx`

- [ ] **Step 1:** 新增顶部 nav 组件 `src/components/GlobalNav.tsx`,塞进 layout:

```tsx
import Link from 'next/link';

export function GlobalNav() {
  return (
    <nav className="border-b border-ink/10 bg-paper/95 backdrop-blur sticky top-0 z-40 px-8 py-4">
      <div className="max-w-6xl mx-auto flex items-center justify-between">
        <Link href="/" className="font-song text-xl text-ink">时光档案馆</Link>
        <div className="hidden md:flex gap-6 font-hei text-sm text-ink/70">
          <Link href="/archive/themes" className="hover:text-stamp">主题档案</Link>
          <Link href="/archive/decades" className="hover:text-stamp">年代切片</Link>
          <Link href="/archive/quotes" className="hover:text-stamp">金句博物馆</Link>
        </div>
      </div>
    </nav>
  );
}
```

- [ ] **Step 2:** layout.tsx:

```tsx
import { GlobalNav } from '@/components/GlobalNav';
// ...
return (
  <html><body>
    <GlobalNav />
    {children}
  </body></html>
);
```

- [ ] **Step 3:** Commit

```bash
git add -A && git commit -m "feat(v2): global museum nav"
```

---

## ✅ v2 验收清单(在 v1 基础上新增)

- [ ] 首页是档案馆 Foyer:深色 hero + 三大入口 + 精选条目 + 策展人手记
- [ ] /archive/themes 列出 6 个主题专辑卡
- [ ] 任一主题详情页:封面 + 导语 + 话题列表
- [ ] /archive/decades 三个年代垂直时间梯
- [ ] 任一年代详情页:超大年份 + 当年话题列表
- [ ] /archive/quotes 金句博物馆有筛选,卡片可跳话题对应年份
- [ ] 单话题页带档案编号印章
- [ ] 海报是档案副本风,带档案编号 / 策展人署名
- [ ] 全局顶部 nav 4 入口可见
- [ ] 移动端各页面响应式正常

---

## 🎯 Day 0 必做(5/11 前完成)

- [ ] 写 6 篇主题专辑导语(每篇 200-400 字)
- [ ] 写 3 篇年代档案导语
- [ ] 写 1 篇金句博物馆导语
- [ ] 写 3 篇策展人手记
- [ ] 共 13 段文案。流程:**Claude Sonnet 4.6 起稿(`chat(..., quality="best")`)→ 你润色 30 分钟/篇**,4 小时内能完成。
- [ ] 全部填入 `data/collections.seed.json` 和 `data/curator_notes.seed.json`

---

## 📜 LLM 路由速查(对照 `docs/LLM-ROUTING.md`)

| 脚本 / 路由 | quality | 模型 |
|---|---|---|
| `03_cluster_opinions.py` | `fast` | DeepSeek-V3 |
| `04_extract_quotes.py` | `fast` | DeepSeek-V3 |
| `05_attach_events.py` | `fast` | DeepSeek-V3 |
| `06_predict_2029.py` | `high` | Claude Haiku 4.5 |
| `08_mood_and_archive_no.py` | `fast` | DeepSeek-V3 |
| `10_curatorial_intros.py`(新)| `best` | Claude Sonnet 4.6 |
| `/api/predict/[id]` 运行时 | `high` | Claude Haiku 4.5 |
| `/api/search` 兜底 | `high` | Claude Haiku 4.5 |
| 全部 embedding | — | 本地 bge-m3 |
