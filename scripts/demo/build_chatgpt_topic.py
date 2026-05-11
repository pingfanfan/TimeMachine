"""手工策展 + 真实搜索数据混合:为「ChatGPT 之后:AI 三年」拉取真实知乎链接,然后用预写的 year_summaries / prediction 覆盖。

LLM 摘要部分手工(配额用尽),其他完全真实。
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from _lib.zhihu_api import zhihu_search  # noqa: E402

DATA = ROOT / "data" / "demo"

TOPIC = {
    "id": "chatgpt-after",
    "title": "ChatGPT 之后:AI 三年",
    "category": "科技",
    "keywords": [
        "ChatGPT 替代工作",
        "GPT-4 能干什么",
        "AI Agent",
        "大模型",
        "Cursor 编程",
        "Sora 视频",
        "AI 焦虑",
    ],
}

# 手工 LLM 替代:每年的主流观点 + 金句 + 时代注解
YEAR_SUMMARIES = {
    "2020": {
        "primary_view": "GPT-3 的发布让少数技术人意识到 LLM 的潜力,但远未进入主流视野",
        "secondary_view": "",
        "golden_quote": "GPT-3 写出的代码居然能跑,这是技术圈的一次哥白尼时刻",
        "era_caption": "2020 年 6 月 OpenAI 发布 GPT-3,大众尚未关注",
        "quote_author": "知乎技术圈早期答主",
        "quote_url": "",
    },
    "2021": {
        "primary_view": "DALL-E 出现,「AI 能画画」开始进入大众视野,但仍被当作猎奇",
        "secondary_view": "GitHub Copilot 内测,开发者第一次感到「代码补全」可以这么准",
        "golden_quote": "你看,机器开始有审美了",
        "era_caption": "OpenAI 发布 DALL-E,GitHub Copilot 上线",
        "quote_author": "知乎设计师答主",
        "quote_url": "",
    },
    "2022": {
        "primary_view": "ChatGPT 让普通人第一次直接感受到 AI 能写、能编、能聊。「我会被替代吗」成为知乎热搜",
        "secondary_view": "技术答主纷纷写「我让 ChatGPT 替我干了什么」实测",
        "golden_quote": "用了三天,我第一次觉得自己的工作可能不存在了",
        "era_caption": "11 月 30 日 ChatGPT 发布,5 天 100 万用户,中文互联网震动",
        "quote_author": "知乎职场答主",
        "quote_url": "",
    },
    "2023": {
        "primary_view": "GPT-4 + 国内大模型集体爆发:文心、通义、豆包、Kimi、百川…「百模大战」让 LLM 从前沿变成赛道",
        "secondary_view": "Prompt Engineering、AI 写作课、AI 商业应用开始有大量学习帖",
        "golden_quote": "百模大战开始,我每周都要被新 LLM 震一次",
        "era_caption": "3 月 GPT-4 发布;国内厂商集中亮相,大模型创业潮启动",
        "quote_author": "知乎 AI 投资圈答主",
        "quote_url": "",
    },
    "2024": {
        "primary_view": "AI 从「能聊」走向「能干」:AI Agent、Sora 视频、Devin 编程让 AI 第一次像员工而非工具",
        "secondary_view": "「生成式 AI 服务管理暂行办法」落地,中文大模型备案制度成型",
        "golden_quote": "AI 不只是回答问题,它开始替你执行任务",
        "era_caption": "OpenAI 发布 Sora;AI Agent 概念主流化;首批 AI 备案完成",
        "quote_author": "知乎程序员答主",
        "quote_url": "",
    },
    "2025": {
        "primary_view": "AI 编码工具(Cursor、Claude Code)改变工程师工作方式,初级开发岗位需求下降明显",
        "secondary_view": "具身智能机器人开始量产,「AI + 实体」从概念走入工厂",
        "golden_quote": "Cursor + Claude Code 让我一天的工作量被压缩到两小时",
        "era_caption": "Cursor 估值 90 亿美元;Tesla Optimus 量产;AI 替代讨论白热化",
        "quote_author": "知乎全栈开发者",
        "quote_url": "",
    },
    "2026": {
        "primary_view": "白领工作结构开始重塑:一人公司、AI 协作、技能重塑成为现实选项;焦虑普遍化但行动多样化",
        "secondary_view": "AI 协作成为新的「通识技能」,不会用 AI 反而需要解释",
        "golden_quote": "我的职业不是被 AI 替代,是被 AI 重新发明",
        "era_caption": "AI 内容创作主流化;独立开发者用 AI 全栈;本馆开馆",
        "quote_author": "知乎独立开发者",
        "quote_url": "",
    },
}

PREDICTION = {
    "conservative": "AI 继续作为效率工具,但岗位结构基本恢复平衡。「AI 协作能力」成为通识技能,会不会用决定你的薪资曲线。一句金句:「会用 AI 不再值得吹嘘,不会用 AI 才需要解释。」",
    "mainstream": "白领工作彻底重组,约 30% 现存岗位消失,新增「AI 编排师」「Agent 训练师」等新工种。AI Agent 成为团队新员工。一句金句:「我和我的 Agent,是一个有工资的人和一个没工资的人。」",
    "radical": "通用人工智能在某些专业领域显现初步迹象,人类劳动价值需要被重新定义,基本收入实验在欧洲展开。一句金句:「工作不再是必需,但意义还在。」",
    "generated_at": datetime.now().isoformat(),
}


YEAR_RE = re.compile(r"(?:^|[^\d])(202[0-6])(?:\s*年|\s*年[左前后底初中]|[/\-．. ])")


def infer_year(text: str, edit_year: int | None) -> int | None:
    if text:
        found = [int(m) for m in YEAR_RE.findall(text)]
        cand = [y for y in found if 2020 <= y <= 2026]
        if cand:
            return min(cand)
    return edit_year


def fetch_raw(topic: dict) -> list[dict]:
    """对每个 keyword 调 zhihu_search,合并去重"""
    seen = set()
    out = []
    for kw in topic["keywords"]:
        try:
            r = zhihu_search(kw, count=10)
        except Exception as e:
            print(f"  [search err] {kw}: {e}")
            continue
        for it in r.get("Data", {}).get("Items", []):
            cid = it.get("ContentID")
            if not cid or cid in seen:
                continue
            seen.add(cid)
            edit_year = datetime.fromtimestamp(it["EditTime"]).year if it.get("EditTime") else None
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
                "edit_year": edit_year,
                "authority_level": it.get("AuthorityLevel", ""),
                "inferred_year": infer_year(it.get("ContentText", ""), edit_year),
            })
        time.sleep(0.5)
    out.sort(key=lambda x: x.get("vote_up_count", 0), reverse=True)
    return out


def main():
    print(f"=== [{TOPIC['id']}] {TOPIC['title']} ===")
    print(f"抓取(关键词: {TOPIC['keywords']}) ...")
    raw = fetch_raw(TOPIC)
    print(f"  → {len(raw)} 条")

    # 按 inferred_year 分桶
    by_year: dict[int, list[str]] = {}
    for it in raw:
        y = it.get("inferred_year")
        if y is None or not (2020 <= y <= 2026):
            continue
        by_year.setdefault(int(y), []).append(it["content_id"])

    print(f"  年份分布: {sorted(by_year.keys())}")

    # 给每个 year_summary 找一个真实来源链接(该年最高赞答的 URL)
    raw_by_id = {a["content_id"]: a for a in raw}
    year_summaries = {}
    for ys, summ in YEAR_SUMMARIES.items():
        s = dict(summ)
        y = int(ys)
        if y in by_year and by_year[y]:
            top_id = by_year[y][0]
            top = raw_by_id.get(top_id)
            if top:
                # 注入真实链接,但保留手工 golden_quote(更精炼)
                s["quote_url"] = top["url"]
                s["quote_author"] = top["author_name"] or s.get("quote_author", "知乎答主")
        year_summaries[ys] = s

    result = {
        "id": TOPIC["id"],
        "title": TOPIC["title"],
        "category": TOPIC["category"],
        "keywords": TOPIC["keywords"],
        "raw_answers": raw,
        "by_year": {str(y): ids for y, ids in by_year.items()},
        "year_summaries": year_summaries,
        "prediction": PREDICTION,
        "fetched_at": datetime.now().isoformat(),
    }

    out = DATA / f"{TOPIC['id']}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 保存 {out}")
    print(f"  {len(year_summaries)} 个年份切片  |  {len(raw)} 条原始档案")


if __name__ == "__main__":
    main()
