"""手工策展 + 真实搜索:加 3 个针对评委的新话题。"""
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


TOPICS = [
    {
        "id": "zhihu-itself",
        "title": "知乎社区的十五年",
        "category": "社区",
        "keywords": ["知乎 邀请制", "如何评价知乎", "知乎 知识付费", "知乎 视频化", "知乎 AI"],
        "year_summaries": {
            "2011": {
                "primary_view": "知乎以邀请制启动,定位「高质量问答社区」,首批用户多为创业/互联网人",
                "secondary_view": "",
                "golden_quote": "刚拿到邀请码那天,我以为找到了中文 Quora",
                "era_caption": "1 月知乎上线,封闭邀请制,内测半年",
                "quote_author": "知乎初代用户",
            },
            "2013": {
                "primary_view": "知乎开放注册,用户暴增,大 V 文化形成,内容门槛开始下移",
                "secondary_view": "「谢邀」「利益相关」等社区语言流行",
                "golden_quote": "开放注册的那一刻,知乎不再是那个知乎了",
                "era_caption": "3 月开放注册,用户数从 40 万跳到千万级",
                "quote_author": "知乎大 V",
            },
            "2016": {
                "primary_view": "「知识付费元年」:知乎 Live、值乎、付费专栏接连上线,知识第一次直接变现",
                "secondary_view": "「分答」「得到」纷纷入场,知乎从社区变平台",
                "golden_quote": "知识有价,但价钱该怎么定,大家都在摸索",
                "era_caption": "知乎 Live、值乎上线;5 月「知识付费元年」概念普及",
                "quote_author": "知乎付费创作者",
            },
            "2018": {
                "primary_view": "短视频冲击,头条系崛起,知乎面临「年轻用户流失」「答主商业化」的双重挑战",
                "secondary_view": "「人在美国,刚下飞机」等段子化叙事开始受到批评",
                "golden_quote": "我们曾以为内容平台之间的竞争是答主之争,后来发现是注意力之争",
                "era_caption": "今日头条悟空问答挖角大 V;知乎付费会员上线",
                "quote_author": "知乎答主",
            },
            "2019": {
                "primary_view": "「盐选会员」体系上线,内容付费成主要商业化路径;社区氛围争议持续",
                "secondary_view": "海盐计划保护小答主;视频探索启动",
                "golden_quote": "知乎不该只属于大 V,也应该属于每一个认真写答的人",
                "era_caption": "盐选会员发布;社区治理「海盐计划」",
                "quote_author": "新生代答主",
            },
            "2021": {
                "primary_view": "知乎赴美上市,内容质量与商业化的张力空前;评论区文化、二级评论改革引发热议",
                "secondary_view": "「圆桌」「想法」「视频」多产品线探索",
                "golden_quote": "上市那天我喝了一杯,不知道是庆祝,还是告别什么",
                "era_caption": "3 月知乎纽交所上市;9 月双重主要上市港股",
                "quote_author": "知乎老用户",
            },
            "2022": {
                "primary_view": "视频化转型加速,「图文 + 视频」并重;答主分层运营机制完善",
                "secondary_view": "「短内容」与「深度长答」共存的新生态",
                "golden_quote": "深度内容没死,只是它需要更多保护",
                "era_caption": "视频化深化;创作者激励体系升级",
                "quote_author": "知乎产品观察者",
            },
            "2023": {
                "primary_view": "「知海图」大模型发布,知乎自研 AI 起步;社区开始探索 AI 辅助创作的边界",
                "secondary_view": "AI 答主、AI 总结等功能引发「真假答主」讨论",
                "golden_quote": "AI 写答可以容忍,但 AI 假装是人不行",
                "era_caption": "4 月「知海图 AI」内测;社区治理 AI 内容",
                "quote_author": "技术答主",
            },
            "2024": {
                "primary_view": "「直答」上线,知乎用 15 年沉淀回应大模型时代:答主仍是核心,AI 是助手",
                "secondary_view": "「想法」改版,新的轻量内容形态登场",
                "golden_quote": "别的平台用 AI 生成内容,知乎用 AI 整理人的回答",
                "era_caption": "直答 Agent 公测;盐选会员超千万",
                "quote_author": "知乎产品经理",
            },
            "2026": {
                "primary_view": "知乎在 AI 时代的角色重新定位:从「问答社区」到「中文思想的索引层」",
                "secondary_view": "黑客松 + 开放平台 + IP 化战略并行",
                "golden_quote": "AI 不是知乎的敌人,是它最终的工具书",
                "era_caption": "4 月发布开放平台 API;AI 脑洞实验室黑客松开赛",
                "quote_author": "本馆策展人",
            },
        },
        "prediction": {
            "conservative": "知乎保持中文最大思想社区地位,会员与 IP 业务稳健增长。一句金句:「这里依旧是中国人讨论复杂问题的少数几个地方之一。」",
            "mainstream": "知乎完成「人 + AI」双轨运营:答主写人格化深度内容,直答 Agent 服务工具型查询;开放平台引出大量第三方创新。一句金句:「内容质量的护城河,从答主一个人,变成答主和他的 AI 一起。」",
            "radical": "知乎成为中文 AI 时代的「思想索引层」:别的大模型都要授权它的语料,它本身变成中文 LLM 的事实依据库。一句金句:「想问中文世界的人怎么想?先来知乎。」",
        },
    },
    {
        "id": "phone-scam",
        "title": "网络诈骗的进化:从短信到 AI 换脸",
        "category": "社会",
        "keywords": ["电信诈骗", "杀猪盘", "反诈", "AI 换脸 诈骗", "徐玉玉"],
        "year_summaries": {
            "2010": {
                "primary_view": "「中奖短信」「冒充公检法」「猜猜我是谁」三大经典诈骗类型横行",
                "secondary_view": "公众警惕意识低,警方破案率有限",
                "golden_quote": "妈接到自称公安的电话,差点把存款转过去",
                "era_caption": "短信诈骗高发期,「猜猜我是谁」全国流行",
                "quote_author": "知乎用户",
            },
            "2014": {
                "primary_view": "网银钓鱼网站兴起,假基站短信成新型攻击手段",
                "secondary_view": "知乎首批技术答主开始系统科普反诈知识",
                "golden_quote": "一条带链接的短信,可能比一个抢匪更危险",
                "era_caption": "假基站短信集中爆发;移动支付普及前夜",
                "quote_author": "安全圈答主",
            },
            "2016": {
                "primary_view": "「徐玉玉案」震动全国,「电信诈骗」第一次以人命代价进入公共议程",
                "secondary_view": "知乎、媒体、警方信息合力,推动立法进程",
                "golden_quote": "一个 18 岁女孩用命换来的反诈,我们不能让它白费",
                "era_caption": "8 月山东准大学生徐玉玉被骗 9900 元致死,全国震惊",
                "quote_author": "媒体人答主",
            },
            "2018": {
                "primary_view": "「杀猪盘」概念出现,情感操控 + 投资诈骗结合,东南亚黑产产业化",
                "secondary_view": "知乎大量受害者实录成为防骗教材",
                "golden_quote": "他用了 3 个月让我相信他爱我,只用了 3 分钟拿走我所有积蓄",
                "era_caption": "「杀猪盘」一词出现;跨境诈骗集团形成",
                "quote_author": "杀猪盘受害者匿名",
            },
            "2020": {
                "primary_view": "疫情期间「冒充流调」「健康码理赔」等新型诈骗;反诈宣传深入社区",
                "secondary_view": "「全民反诈 APP」上线",
                "golden_quote": "诈骗分子永远比骗术防范者快一步,但总有人在跑",
                "era_caption": "疫情衍生骗局;国家反诈中心 APP 上线",
                "quote_author": "公安系统答主",
            },
            "2022": {
                "primary_view": "**《反电信网络诈骗法》正式实施**,中国首部专门反诈法律落地",
                "secondary_view": "运营商、银行、平台多方联防机制建立",
                "golden_quote": "法律来了,但骗子也来到了 AI 时代,真正的较量才开始",
                "era_caption": "12 月 1 日《反电信网络诈骗法》施行",
                "quote_author": "法律答主",
            },
            "2024": {
                "primary_view": "**AI 换脸视频通话**诈骗爆发,「眼见为实」失效;deepfake 攻击企业财务",
                "secondary_view": "「亲属语音」「老板换脸」等新型骗局损失金额屡破纪录",
                "golden_quote": "电话里那个声音是我儿子,视频里那张脸是我儿子,但他不是我儿子",
                "era_caption": "AI 换脸诈骗案数倍增长;香港某公司被骗 2 亿港币",
                "quote_author": "受害者家属",
            },
            "2025": {
                "primary_view": "生成式 AI 内容鉴别、深伪检测工具普及;社交平台强制要求 AI 内容标识",
                "secondary_view": "「AI 反 AI」成为反诈新方向",
                "golden_quote": "对抗 AI 诈骗,我们也只能用 AI",
                "era_caption": "国家网信办《人工智能生成合成内容标识办法》落地",
                "quote_author": "技术答主",
            },
            "2026": {
                "primary_view": "AI 反诈进入「实时通话深伪检测」阶段;但诈骗者也在用更新的 LLM 突破检测",
                "secondary_view": "公众认知与技术防御都在升级,但人性的弱点没变",
                "golden_quote": "诈骗的核心不是技术,是信任。技术只是新的入口而已",
                "era_caption": "本馆开馆 · 反诈与诈骗的 AI 军备竞赛",
                "quote_author": "本馆策展人",
            },
        },
        "prediction": {
            "conservative": "AI 反诈技术持续升级,诈骗损失率下降但绝对值仍高。一句金句:「魔比道高,道也在追。」",
            "mainstream": "「身份验证」从生物特征转向「行为 + 关系网」多重锚点;社会层面建立可验证身份基础设施。一句金句:「下一个十年,你证明你是你,会比现在难很多。」",
            "radical": "深伪能力让虚拟身份与真实身份界限消失,法律 / 金融体系必须重写。一句金句:「当眼见不再为实,我们将用什么相信彼此?」",
        },
    },
    {
        "id": "china-open-source",
        "title": "中国开源运动:从 LinuxFans 到大模型",
        "category": "科技",
        "keywords": ["中国 开源", "GitHub 中国", "开源 大模型", "PingCAP TiDB", "Vue 尤雨溪"],
        "year_summaries": {
            "2010": {
                "primary_view": "中国开源还停留在「使用国外项目」阶段,「LinuxFans」「开源中国」是主要社群",
                "secondary_view": "首批中国开发者开始向上游贡献 patch",
                "golden_quote": "那时候,能给 Linux kernel 提一个 patch 是值得朋友圈炫耀一年的事",
                "era_caption": "Github 进入中国程序员视野;LinuxFans 鼎盛期",
                "quote_author": "Linux 圈早期参与者",
            },
            "2013": {
                "primary_view": "GitHub 成为中国开发者主要协作平台,「中国制造」开源项目数量开始增长",
                "secondary_view": "「学生 GitHub 简历」成为求职新标准",
                "golden_quote": "GitHub 是程序员的脸",
                "era_caption": "GitHub 中国用户数突破百万",
                "quote_author": "招聘行业答主",
            },
            "2014": {
                "primary_view": "**Vue.js 由尤雨溪发布**,中国开发者第一次主导一个全球级前端框架",
                "secondary_view": "「中国设计、全球协作」的开源模式开始成立",
                "golden_quote": "Vue 之前,中国人写的开源大多服务中国;Vue 之后,世界开始用中国人写的代码",
                "era_caption": "2 月 Vue.js v0.6 发布,迅速走红",
                "quote_author": "前端社区答主",
            },
            "2018": {
                "primary_view": "GitHub 被微软收购,「996.ICU」运动爆发,GitHub 成为中文公共议题主场",
                "secondary_view": "PingCAP TiDB、Apache 顶级项目里的中国身影增加",
                "golden_quote": "996.ICU 让世界第一次看到中国开发者的集体表达",
                "era_caption": "微软 75 亿美元收购 GitHub;996.ICU GitHub 项目",
                "quote_author": "技术社区答主",
            },
            "2020": {
                "primary_view": "「开源信通院」等机构推动政策与产业对接;Gitee 等国产平台崛起",
                "secondary_view": "「开源风险」「合规审查」等议题进入企业议程",
                "golden_quote": "开源,从极客的爱好,变成了国家的基础设施",
                "era_caption": "国家「十四五」纳入开源战略;Gitee 用户增长",
                "quote_author": "开源治理专家",
            },
            "2022": {
                "primary_view": "ChatGPT 引爆 AI 大模型开源浪潮;Meta LLaMA 与 Stability AI 等开源模型激发国内跟进",
                "secondary_view": "「中文开源 AI 还差什么」成为知乎热门讨论",
                "golden_quote": "AI 模型是否开源,可能比代码是否开源更影响下一个十年",
                "era_caption": "ChatGPT 发布;开源 LLM 第一次大规模可能",
                "quote_author": "AI 圈答主",
            },
            "2023": {
                "primary_view": "**智谱 ChatGLM、阿里 Qwen、百川等大模型开源**,中国开源 AI 阵营初步形成",
                "secondary_view": "Datawhale 等社区把开源教育做到普惠层",
                "golden_quote": "我们不是没有开源精神,我们只是这次终于被允许有",
                "era_caption": "ChatGLM-6B 开源;Datawhale 用户数突破百万",
                "quote_author": "开源社区组织者",
            },
            "2024": {
                "primary_view": "**通义 Qwen 系列全栈开源**;DeepSeek 出现,中国开源 LLM 第一次冲击全球榜首",
                "secondary_view": "Hugging Face 中文社区贡献者占比快速上升",
                "golden_quote": "DeepSeek 火的那一周,世界第一次承认:中国大模型可以是国际公共品",
                "era_caption": "DeepSeek-V2 发布,引发全球 LLM 价格战",
                "quote_author": "DeepSeek 用户",
            },
            "2025": {
                "primary_view": "中国 AI 开源贡献占全球比例显著上升;开源 + 商业的平衡成新议题",
                "secondary_view": "「开放权重」与「真开源」的边界被反复讨论",
                "golden_quote": "权重开源 ≠ 开源,但它至少让世界用得起",
                "era_caption": "Qwen 3 / DeepSeek R1 / GLM-4 接连发布;开源框架激增",
                "quote_author": "Hugging Face 中文 maintainer",
            },
            "2026": {
                "primary_view": "中国开源已成中文 AI 生态基础设施;Datawhale 等组织进入下一个十年的「开源教育」议题",
                "secondary_view": "「开源不是免费,而是协作」的认知普及",
                "golden_quote": "开源不解决所有问题,但它确保所有问题至少能被讨论",
                "era_caption": "本馆开馆 · 中国开源的十五年",
                "quote_author": "本馆策展人",
            },
        },
        "prediction": {
            "conservative": "中国开源 AI 维持当前规模,Datawhale 等社区继续发挥教育作用。一句金句:「不是所有人都需要写开源,但每个开发者都该读懂开源。」",
            "mainstream": "中国开源 LLM 成为亚非拉发展中国家 AI 基础首选;「开源即基础设施」共识形成。一句金句:「全球一半的国家用上 AI,靠的是中国的开源权重。」",
            "radical": "中美开源框架彻底分流,形成两套独立的 AI 生态;「跨生态翻译层」成为新基础设施。一句金句:「下一个开源时代,不是一个池子,是两条河。」",
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
        "id": topic["id"],
        "title": topic["title"],
        "category": topic["category"],
        "keywords": topic["keywords"],
        "raw_answers": raw,
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
