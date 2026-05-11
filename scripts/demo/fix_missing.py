"""补漏:对每个话题
1. 缺 year_summaries 的年份 → 重跑 summarize_year
2. 缺 prediction 的 → 重跑(全部用 zhida-fast-1p5,避免 thinking 超时)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from demo.build_demo import (  # noqa: E402
    summarize_year, predict_2029, llm_json
)

DATA_DIR = ROOT / "data" / "demo"


def fix_topic(path: Path) -> bool:
    d = json.loads(path.read_text(encoding="utf-8"))
    tid = d["id"]
    title = d["title"]
    changed = False

    # 准备 raw_answers 按 ContentID 索引
    raw_by_id = {a["content_id"]: a for a in d.get("raw_answers", [])}

    # 1. 补缺失的 year_summaries
    by_year = d.get("by_year", {})  # {"2015": [content_id, ...]}
    year_summaries = d.get("year_summaries", {})
    missing_years = [y for y in by_year if y not in year_summaries]
    if missing_years:
        print(f"  [{tid}] 补 {len(missing_years)} 个年份的 summary: {missing_years}")
        for y in missing_years:
            items = [raw_by_id[i] for i in by_year[y] if i in raw_by_id]
            items.sort(key=lambda x: x.get("vote_up_count", 0), reverse=True)
            s = summarize_year(title, int(y), items)
            if s:
                year_summaries[y] = s
                changed = True
                print(f"      ✅ {y}: {s.get('golden_quote', '')[:50]}")
            time.sleep(1)
        d["year_summaries"] = year_summaries

    # 2. 补 prediction(强制全部用 fast)
    if not d.get("prediction"):
        timeline = [(int(y), year_summaries[y]["primary_view"]) for y in sorted(year_summaries.keys(), key=int)]
        if len(timeline) >= 2:
            print(f"  [{tid}] 补 prediction(fast 模型)...")
            prompt = f"""话题:《{title}》

2010-2026 年观点演变:
{chr(10).join(f"[{y}] {v}" for y, v in timeline)}

任务:推演 2029 年三种情境。每种 40-70 字,以一句金句结尾。

返回 JSON: {{"conservative": "...", "mainstream": "...", "radical": "..."}}

严格只返回 JSON。"""
            try:
                pred = llm_json(prompt, model="zhida-fast-1p5")
                if isinstance(pred, dict):
                    d["prediction"] = pred
                    changed = True
                    print(f"      ✅ {pred.get('mainstream', '')[:60]}")
            except Exception as e:
                print(f"      ❌ {e}")

    if changed:
        path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [{tid}] 已更新")
    return changed


def main():
    for f in sorted(DATA_DIR.glob("*.json")):
        if f.name.startswith("_"):
            continue
        fix_topic(f)


if __name__ == "__main__":
    main()
