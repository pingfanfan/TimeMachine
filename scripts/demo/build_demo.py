"""时光档案馆 · 10 话题 Demo 数据管线

完整流程:
1. zhihu_search 抓取(多关键词 × Count=10)
2. 启发式 + LLM batch 推断真实写作年代
3. zhida 提炼金句 + 主流观点(按年份)
4. zhida 2029 三情境推演
5. 输出 data/demo/{topic_id}.json

支持断点续跑:--refresh 强制重抓;--only <id> 只跑某话题

全部 LLM 走知乎直答 Agent(zhida-fast-1p5 / zhida-thinking-1p5),零外部依赖。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from _lib.zhihu_api import zhihu_search, chat_completions  # noqa: E402

DATA_DIR = ROOT / "data" / "demo"
DATA_DIR.mkdir(parents=True, exist_ok=True)


TOPICS = [
    {
        "id": "yang-yongxin",
        "title": "杨永信网戒中心",
        "category": "社会",
        "keywords": ["杨永信", "网瘾电击 治疗", "豫章书院", "戒网瘾 学校"],
    },
    {
        "id": "wei-zexi",
        "title": "魏则西事件",
        "category": "社会",
        "keywords": ["魏则西", "魏则西 百度", "莆田系医院", "百度 竞价排名"],
    },
    {
        "id": "ofo-deposit",
        "title": "ofo 退押金潮",
        "category": "商业",
        "keywords": ["ofo 退押金", "小黄车 倒闭", "共享单车 泡沫", "ofo 押金"],
    },
    {
        "id": "996-icu",
        "title": "996.ICU 运动",
        "category": "职场",
        "keywords": ["996.ICU", "996 加班 抗议", "互联网 加班 文化", "马云 996"],
    },
    {
        "id": "programmer-35",
        "title": "程序员 35 岁危机",
        "category": "职场",
        "keywords": ["程序员 35 岁", "大龄程序员 出路", "程序员 中年危机", "35岁 被裁员"],
    },
    {
        "id": "luo-yonghao",
        "title": "罗永浩与锤子科技",
        "category": "商业",
        "keywords": ["罗永浩 锤子", "锤子手机 失败", "罗永浩 直播", "老罗 创业"],
    },
    {
        "id": "school-district",
        "title": "学区房与双减",
        "category": "教育",
        "keywords": ["学区房 北京", "鸡娃 焦虑", "双减 教育改革", "学区房 降温"],
    },
    {
        "id": "bride-price",
        "title": "高额彩礼",
        "category": "婚恋",
        "keywords": ["天价彩礼", "彩礼 多少合适", "彩礼 农村", "彩礼 婚姻"],
    },
    {
        "id": "zte-ban",
        "title": "中兴禁令与科技冷战",
        "category": "科技",
        "keywords": ["中兴 禁令", "中兴 美国 制裁", "芯片 卡脖子", "华为 美国 制裁"],
    },
    {
        "id": "p2p-collapse",
        "title": "P2P 暴雷潮",
        "category": "金融",
        "keywords": ["P2P 暴雷", "P2P 跑路", "网贷 监管", "e租宝"],
    },
]


# ───────── LLM 调用封装 ─────────

def llm(prompt: str, model: str = "zhida-fast-1p5", retries: int = 2) -> str:
    """统一 LLM 入口,带重试"""
    last_err = None
    for _ in range(retries + 1):
        try:
            r = chat_completions(
                messages=[{"role": "user", "content": prompt}],
                model=model,
            )
            return r["choices"][0]["message"]["content"]
        except Exception as e:
            last_err = e
            time.sleep(2)
    raise RuntimeError(f"LLM failed: {last_err}")


def llm_json(prompt: str, model: str = "zhida-fast-1p5") -> dict | list:
    """LLM 返回 JSON,自动提取"""
    text = llm(prompt + "\n\n严格只返回有效 JSON,不要任何其他文字。", model=model)
    # 提取 ```json ... ``` 或第一个 { 到最后一个 }
    if "```" in text:
        m = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.DOTALL)
        if m:
            text = m.group(1)
    # 兜底:找第一个 { 或 [ 开始
    start = min(
        (text.find("{") if text.find("{") >= 0 else len(text)),
        (text.find("[") if text.find("[") >= 0 else len(text)),
    )
    if start < len(text):
        text = text[start:]
        # 找匹配的结束括号
        depth = 0
        in_str = False
        escape = False
        end = len(text)
        for i, c in enumerate(text):
            if escape:
                escape = False
                continue
            if c == "\\":
                escape = True
                continue
            if c == '"' and not escape:
                in_str = not in_str
                continue
            if in_str:
                continue
            if c in "{[":
                depth += 1
            elif c in "}]":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        text = text[:end]
    try:
        return json.loads(text)
    except Exception as e:
        print(f"    [llm_json parse error] {e}  RAW: {text[:200]}")
        raise


# ───────── 抓取 ─────────

def fetch_topic_raw(topic: dict) -> list[dict]:
    """每个关键词调一次 zhihu_search,合并去重"""
    seen = set()
    out = []
    for kw in topic["keywords"]:
        try:
            r = zhihu_search(kw, count=10)
        except Exception as e:
            print(f"    [search err] {kw}: {e}")
            continue
        for it in r.get("Data", {}).get("Items", []):
            cid = it.get("ContentID")
            if not cid or cid in seen:
                continue
            seen.add(cid)
            out.append({
                "content_id": cid,
                "title": it.get("Title", ""),
                "content_type": it.get("ContentType", ""),
                "content_text": it.get("ContentText", ""),
                "url": it.get("Url", ""),
                "vote_up_count": it.get("VoteUpCount", 0),
                "comment_count": it.get("CommentCount", 0),
                "author_name": it.get("AuthorName", ""),
                "author_avatar": it.get("AuthorAvatar", ""),
                "edit_time": it.get("EditTime", 0),
                "edit_year": datetime.fromtimestamp(it["EditTime"]).year if it.get("EditTime") else None,
                "authority_level": it.get("AuthorityLevel", ""),
            })
        time.sleep(0.5)  # 限流保护
    out.sort(key=lambda x: x.get("vote_up_count", 0), reverse=True)
    return out


# ───────── 年代推断 ─────────

YEAR_RE = re.compile(r"(?:^|[^\d])(20[01]\d|2026)(?:\s*年|\s*年[左前后底初中]|[/\-．. ])")
EVENT_TO_YEAR = {
    "杨永信": (2008, 2017),
    "魏则西": (2016, 2016),
    "ofo": (2017, 2019),
    "小黄车": (2017, 2019),
    "996.ICU": (2019, 2019),
    "996icu": (2019, 2019),
    "雷霆战警": (2016, 2017),
    "锤子 T1": (2014, 2015),
    "锤子T1": (2014, 2015),
    "smartisan": (2013, 2018),
    "中兴禁令": (2018, 2018),
    "中兴 通讯": (2018, 2018),
    "e租宝": (2015, 2016),
    "双减": (2021, 2024),
    "学区房 降温": (2024, 2026),
    "新冠": (2020, 2022),
    "疫情": (2020, 2023),
    "chatgpt": (2022, 2024),
    "GPT-4": (2023, 2024),
}


def infer_year_heuristic(text: str, edit_year: int | None) -> tuple[int | None, str]:
    """启发式推断:文本里的具体年份 > 事件锚点 > EditTime"""
    if not text:
        return edit_year, "edit_time only"
    # 1. 提取所有 4 位年份
    found = [int(m) for m in YEAR_RE.findall(text)]
    if found:
        # 取最早出现的(可能是叙事起点)
        candidates = [y for y in found if 2008 <= y <= 2026]
        if candidates:
            min_y = min(candidates)
            return min_y, f"text mentions {min_y}"
    # 2. 事件锚点
    for keyword, (low, high) in EVENT_TO_YEAR.items():
        if keyword.lower() in text.lower():
            return low, f"event keyword {keyword}"
    # 3. EditTime fallback
    return edit_year, "edit_time fallback"


# ───────── 按年总结 ─────────

def summarize_year(title: str, year: int, items: list[dict]) -> dict | None:
    """LLM 提炼当年主流观点 + 金句"""
    if not items:
        return None
    excerpts = []
    for i, it in enumerate(items[:5], 1):
        excerpt = it["content_text"][:400].replace("\n", " ")
        excerpts.append(f'<{i}> [{it["author_name"]}|赞{it["vote_up_count"]}] {excerpt}')

    prompt = f"""话题:《{title}》

{year} 年的相关知乎回答(按赞同数排序,前 5 条节选):

{chr(10).join(excerpts)}

任务:总结这一年该话题在知乎社区的讨论。

返回 JSON 格式:
{{
  "primary_view": "本年最主流的观点 1 句(30-50 字)",
  "secondary_view": "本年次主流或对立观点 1 句(可空字符串)",
  "golden_quote": "最能代表当年气质的金句(从原文摘录或轻度改写,20-40 字)",
  "quote_source_index": 1,
  "era_caption": "用 1 句话点出这一年的社会背景与话题关联"
}}

严格只返回 JSON。"""
    try:
        r = llm_json(prompt)
        if not isinstance(r, dict):
            return None
        # quote_source_index 映射回真实 URL
        idx = r.get("quote_source_index", 1)
        if isinstance(idx, int) and 1 <= idx <= len(items[:5]):
            src = items[idx - 1]
            r["quote_author"] = src["author_name"]
            r["quote_url"] = src["url"]
        return r
    except Exception as e:
        print(f"    [summarize_year err] {year}: {e}")
        return None


def predict_2029(title: str, timeline: list[tuple[int, str]]) -> dict | None:
    """LLM 推演 2029 年三种情境"""
    timeline_str = "\n".join(f"[{y}] {v}" for y, v in timeline)
    prompt = f"""话题:《{title}》

2010-2026 年观点演变:
{timeline_str}

任务:基于这段演变趋势,推演 2029 年最可能出现的三种情境。
明确说明这是 AI 推演,不是预言。

返回 JSON:
{{
  "conservative": "保守情境(当前趋势平稳延续)40-70 字,以一句金句结尾",
  "mainstream": "主流情境(综合各信号的最可能未来)40-70 字,以一句金句结尾",
  "radical": "激进情境(小概率但不可忽视的尾部风险)40-70 字,以一句金句结尾"
}}

严格只返回 JSON。"""
    for model in ("zhida-thinking-1p5", "zhida-fast-1p5"):
        try:
            return llm_json(prompt, model=model)
        except Exception as e:
            print(f"    [predict_2029 {model} err]: {e}")
            continue
    return None


# ───────── 主流程 ─────────

def process_topic(topic: dict, force: bool = False) -> dict:
    cache = DATA_DIR / f"{topic['id']}.json"
    if cache.exists() and not force:
        print(f"  [cached] {topic['id']}")
        return json.loads(cache.read_text(encoding="utf-8"))

    print(f"\n=== [{topic['id']}] {topic['title']} ===")

    # 1. 抓取
    print(f"  抓取(关键词: {topic['keywords']}) ...")
    raw = fetch_topic_raw(topic)
    print(f"    → {len(raw)} 条去重后回答")

    # 2. 年代推断(启发式优先)
    print("  年代推断(启发式)...")
    for it in raw:
        y, why = infer_year_heuristic(it["content_text"], it.get("edit_year"))
        it["inferred_year"] = y
        it["year_evidence"] = why

    # 3. 按年分桶
    by_year: dict[int, list[dict]] = {}
    for it in raw:
        y = it.get("inferred_year")
        if y is None:
            continue
        by_year.setdefault(int(y), []).append(it)
    for y in by_year:
        by_year[y].sort(key=lambda x: x.get("vote_up_count", 0), reverse=True)

    print(f"    年份分布: {sorted(by_year.keys())}")
    print(f"    每年数量: { {y: len(v) for y, v in sorted(by_year.items())} }")

    # 4. 按年总结(LLM)
    print("  按年总结(LLM)...")
    year_summaries: dict[int, dict] = {}
    for y in sorted(by_year.keys()):
        s = summarize_year(topic["title"], y, by_year[y])
        if s:
            year_summaries[y] = s
            print(f"    [{y}] {s.get('golden_quote', '?')[:50]}")
        time.sleep(0.5)

    # 5. 2029 预测
    print("  2029 预测...")
    timeline = [(y, year_summaries[y]["primary_view"]) for y in sorted(year_summaries)]
    prediction = predict_2029(topic["title"], timeline) if len(timeline) >= 2 else None

    # 6. 组装
    result = {
        "id": topic["id"],
        "title": topic["title"],
        "category": topic["category"],
        "keywords": topic["keywords"],
        "raw_answers": raw,
        "by_year": {str(y): [a["content_id"] for a in by_year[y]] for y in by_year},
        "year_summaries": {str(y): s for y, s in year_summaries.items()},
        "prediction": prediction,
        "fetched_at": datetime.now().isoformat(),
    }
    cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ 保存到 {cache}")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="强制重新抓取并重跑")
    ap.add_argument("--only", help="只跑某个话题 id")
    args = ap.parse_args()

    targets = [t for t in TOPICS if not args.only or t["id"] == args.only]
    if not targets:
        print(f"❌ 未找到 id={args.only}")
        sys.exit(1)

    all_data = []
    for t in targets:
        try:
            all_data.append(process_topic(t, force=args.refresh))
        except Exception as e:
            print(f"❌ {t['id']} 失败: {e}")
            import traceback
            traceback.print_exc()

    # 索引文件
    index = {
        "generated_at": datetime.now().isoformat(),
        "topics": [
            {"id": d["id"], "title": d["title"], "category": d["category"]}
            for d in all_data
        ],
    }
    (DATA_DIR / "_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2))
    print(f"\n✅ 全部完成,共 {len(all_data)} 话题")


if __name__ == "__main__":
    main()
