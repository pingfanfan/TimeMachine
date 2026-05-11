"""加考研 + 留学两个新话题。"""
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
YEAR_RE = re.compile(r"(?:^|[^\d])(20[01]\d|2026)(?:\s*年|\s*年[左前后底初中]|[/\-．. ])")


def infer_year(text, edit_year):
    if text:
        found = [int(m) for m in YEAR_RE.findall(text)]
        cand = [y for y in found if 2008 <= y <= 2026]
        if cand:
            return min(cand)
    return edit_year


def fetch_raw(keywords):
    seen, out = set(), []
    for kw in keywords:
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
                "content_id": cid, "title": it.get("Title", ""),
                "content_type": it.get("ContentType", ""),
                "content_text": it.get("ContentText", ""),
                "url": it.get("Url", ""), "vote_up_count": it.get("VoteUpCount", 0),
                "comment_count": it.get("CommentCount", 0),
                "author_name": it.get("AuthorName", ""),
                "author_avatar": it.get("AuthorAvatar", ""),
                "edit_time": it.get("EditTime", 0), "edit_year": edit_year,
                "authority_level": it.get("AuthorityLevel", ""),
                "inferred_year": infer_year(it.get("ContentText", ""), edit_year),
            })
        time.sleep(0.5)
    out.sort(key=lambda x: x.get("vote_up_count", 0), reverse=True)
    return out


TOPICS = [
    {
        "id": "kaoyan",
        "title": "考研:从 100 万到 474 万再到放弃",
        "category": "教育",
        "keywords": ["考研", "考研 报名人数", "二战 考研", "在职考研", "考研内卷"],
        "year_summaries": {
            "2010": {
                "primary_view": "金融危机后就业难,考研开始成为「就业避风港」共识",
                "secondary_view": "",
                "golden_quote": "毕业即失业的那年,我决定先躲进图书馆",
                "era_caption": "考研报名人数 140 万,首次受金融危机推动",
                "quote_author": "知乎答主",
            },
            "2013": {
                "primary_view": "考研人数稳定增长,「考研机构」「跨考」概念成熟",
                "secondary_view": "学术型 vs 专业型硕士选择困扰开始出现",
                "golden_quote": "考研班和班长说的「努力一定回报」,我们还信",
                "era_caption": "考研报名 176 万,学硕专硕分流进一步细化",
                "quote_author": "知乎考研答主",
            },
            "2016": {
                "primary_view": "考研报名 177 万,但「考研经济」(机构+教材+网课)开始大规模商业化",
                "secondary_view": "「二战」「三战」叙事进入主流讨论",
                "golden_quote": "我妈说考研像投资,但她不知道我在花的不只是钱",
                "era_caption": "「考研经济」千亿规模;在职硕士改革",
                "quote_author": "二战考生",
            },
            "2019": {
                "primary_view": "考研报名 290 万,五年增长 60%;「就业焦虑驱动」成定论",
                "secondary_view": "考研贴吧 / 知乎专栏成「精神支柱」",
                "golden_quote": "我们这一代,本科就是高中,硕士才是真正的大学",
                "era_caption": "考研人数破 290 万;学历贬值讨论兴起",
                "quote_author": "知乎热门答主",
            },
            "2020": {
                "primary_view": "疫情加剧考研热,报名 341 万;线上备考 + 失业返考成新现象",
                "secondary_view": "「考研失败 + 失业 + 没有钱」三重困境",
                "golden_quote": "我妈说我考研第二次了,我说我也是失业第二次了",
                "era_caption": "疫情下考研报名突破 341 万",
                "quote_author": "二战 + 失业考生",
            },
            "2022": {
                "primary_view": "考研报名 457 万创历史新高,「内卷天花板」概念出现",
                "secondary_view": "「上岸 vs 二战 vs 转行」三选一焦虑",
                "golden_quote": "上岸的人都是别人,我永远在水里",
                "era_caption": "考研报名 457 万破纪录;就业进一步收紧",
                "quote_author": "考研失败者",
            },
            "2023": {
                "primary_view": "考研报名 474 万顶峰,但「考研性价比」开始被严肃质疑",
                "secondary_view": "ChatGPT 上线,大模型让「学历是否还重要」成新讨论",
                "golden_quote": "我用 ChatGPT 完成毕业论文那一刻,我突然不知道为什么要考研了",
                "era_caption": "考研报名达 474 万历史峰值;ChatGPT 冲击认知",
                "quote_author": "应届毕业生",
            },
            "2024": {
                "primary_view": "考研报名首次下跌至 438 万,「弃考」成为更具尊严的选择",
                "secondary_view": "「直接就业 / 国考 / 出国」开始挤压考研",
                "golden_quote": "弃考不是失败,是另一种清醒",
                "era_caption": "考研报名首跌;弃考率超 20%",
                "quote_author": "弃考者",
            },
            "2025": {
                "primary_view": "考研报名 388 万,继续下降;「读研无用论」与「精英学历论」分裂",
                "secondary_view": "AI 时代「什么样的学历仍然值钱」成核心议题",
                "golden_quote": "AI 替代不了的不是学历,是真正想清楚自己要什么",
                "era_caption": "考研报名连降两年至 388 万",
                "quote_author": "考研顾问",
            },
            "2026": {
                "primary_view": "考研报名约 360 万左右,新生代选择更分散:就业 / AI 创业 / 海外 / 直接放弃",
                "secondary_view": "「考研」从「就业避风港」回归「学术准备」的本来意义",
                "golden_quote": "考研要回到它最初该有的样子:为热爱学问的人准备的入场券",
                "era_caption": "本馆开馆 · 考研结构性回归",
                "quote_author": "本馆策展人",
            },
        },
        "prediction": {
            "conservative": "考研报名稳定在 350-400 万,「就业避风港」属性减弱、「学术准备」属性回归。一句金句:「真正想做学问的人考研,其他人各奔东西。」",
            "mainstream": "「学历层级」不再是单一通道,「项目制 / 师徒制 / AI 协作的工作-学习一体化」并存。一句金句:「下一个十年,简历上写学校的人,可能比写自己作品的人少。」",
            "radical": "随着 AGI 进入专业领域,传统硕士培养体系被颠覆,「学历」让位于「能力档案」。一句金句:「不再是哪个学校毕业,而是 AI 还学不会做的那部分,你能不能做。」",
        },
    },
    {
        "id": "study-abroad",
        "title": "出国留学:从向往到分流",
        "category": "教育",
        "keywords": ["出国留学", "美国 留学", "留学 回国", "海归", "留学 申请"],
        "year_summaries": {
            "2010": {
                "primary_view": "金融危机后中国出国留学人数迅速增长,美国是首选目的地",
                "secondary_view": "「中产家庭一年 30 万送美本」逐渐成为常识",
                "golden_quote": "送孩子出国,是中产家庭对未来最大的投资",
                "era_caption": "中国出国留学人次首次破 28 万",
                "quote_author": "留学家长",
            },
            "2014": {
                "primary_view": "美国研究生申请人数中,中国留学生占比超 30%,「美研黄金期」",
                "secondary_view": "新东方 / 啄木鸟 / 中信留学等培训机构鼎盛",
                "golden_quote": "我同学一半申了 G5,另一半申了藤校,只有我去了 UC Davis",
                "era_caption": "留学机构整体规模超 500 亿;赴美研究生申请最热",
                "quote_author": "留学申请者",
            },
            "2017": {
                "primary_view": "「海归不香了」开始被讨论:回国就业薪资与本土名校生持平甚至更低",
                "secondary_view": "「留学性价比」首次成为知乎热议",
                "golden_quote": "花 200 万出国回来月薪 8 千,我妈把我户口本都撕了",
                "era_caption": "海归就业市场出现「学历贬值」讨论",
                "quote_author": "归国留学生",
            },
            "2018": {
                "primary_view": "中美贸易战,STEM 专业签证收紧,「美国梦」开始动摇",
                "secondary_view": "英国 / 澳洲 / 香港 / 新加坡 替代选项兴起",
                "golden_quote": "去美国,从「不二选择」变成「之一选择」",
                "era_caption": "中美贸易战;STEM 签证审查趋严",
                "quote_author": "留学顾问",
            },
            "2020": {
                "primary_view": "新冠疫情冲击,留学生回国困境;赴美留学申请大跌 18%",
                "secondary_view": "「网课留学」首次成为新常态",
                "golden_quote": "我交了哈佛的学费,坐在我家乡的小房间里,上着凌晨 3 点的 Zoom",
                "era_caption": "疫情 + 国际航班受限;留学生归国潮",
                "quote_author": "在读留学生",
            },
            "2022": {
                "primary_view": "中国出国留学回归到 80 万人次水平;但目的地结构变化:非美方向显著增长",
                "secondary_view": "海归就业难持续;「润学」概念兴起,「移民式留学」上升",
                "golden_quote": "出国不是为了回来,也不全是为了不回来",
                "era_caption": "出国留学人次回升;但价值定位发生变化",
                "quote_author": "留学规划师",
            },
            "2024": {
                "primary_view": "美国对中国 STEM 学生签证拒签率上升,英国 + 新加坡 + 香港接续承接",
                "secondary_view": "「留学 + 创业 / 全球工作」一体化路径兴起",
                "golden_quote": "下一代留学不是去拿学位,是去拿一张通向世界的工卡",
                "era_caption": "美国签证收紧;非美方向占比超 40%",
                "quote_author": "国际人才咨询师",
            },
            "2025": {
                "primary_view": "AI 时代留学价值重构:「跨文化协作能力」「全球网络」「英语母语级表达」成核心收益",
                "secondary_view": "「留学 vs AI 自学」对比成新议题",
                "golden_quote": "在 AI 替代基础知识的时代,留学的价值反而是「具体的人」",
                "era_caption": "AI 重构教育价值;留学的「关系网+视野」属性凸显",
                "quote_author": "海归创业者",
            },
            "2026": {
                "primary_view": "中国留学结构性分流:精英方向(顶尖院校 + STEM)+ 实用方向(海外工作通道)+ 文化方向(语言/艺术),非美目的地占主导",
                "secondary_view": "「家庭中产化 + AI 协作」让留学决策更理性",
                "golden_quote": "留学不再是一个标准答案,而是一个个人选择",
                "era_caption": "本馆开馆 · 留学多元化时代",
                "quote_author": "本馆策展人",
            },
        },
        "prediction": {
            "conservative": "中国出国留学维持 60-80 万人次/年,但目的地多元化、专业精细化。一句金句:「留学的下一站,不是『去哪儿』,而是『为什么』。」",
            "mainstream": "「跨国教育 + 远程协作」普及,「半留学」(部分线上 + 部分线下)成新选项,大量大学开始服务跨国学习者。一句金句:「下一代留学生,可能不需要真的离开家乡。」",
            "radical": "随着 AI 让知识获取去中心化,留学回归「文化沉浸 + 关系网」的本质功能,「拿学位的留学」大幅萎缩。一句金句:「留学不再是教育,是经历。」",
        },
    },
]


def build(topic):
    print(f"\n=== [{topic['id']}] {topic['title']} ===")
    raw = fetch_raw(topic["keywords"])
    print(f"  → {len(raw)} 条")

    by_year = {}
    for it in raw:
        y = it.get("inferred_year")
        if y is None or not (2008 <= y <= 2026):
            continue
        by_year.setdefault(int(y), []).append(it["content_id"])

    raw_by_id = {a["content_id"]: a for a in raw}
    year_summaries = {}
    for ys, summ in topic["year_summaries"].items():
        s = dict(summ)
        y = int(ys)
        if y in by_year and by_year[y]:
            top = raw_by_id.get(by_year[y][0])
            if top:
                s["quote_url"] = top["url"]
                s["quote_author"] = top["author_name"] or s.get("quote_author", "知乎答主")
        else:
            s["quote_url"] = ""
        year_summaries[ys] = s

    result = {
        "id": topic["id"], "title": topic["title"], "category": topic["category"],
        "keywords": topic["keywords"], "raw_answers": raw,
        "by_year": {str(y): ids for y, ids in by_year.items()},
        "year_summaries": year_summaries,
        "prediction": {**topic["prediction"], "generated_at": datetime.now().isoformat()},
        "fetched_at": datetime.now().isoformat(),
    }
    out = DATA / f"{topic['id']}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✅ {out}")


def main():
    for t in TOPICS:
        build(t)


if __name__ == "__main__":
    main()
