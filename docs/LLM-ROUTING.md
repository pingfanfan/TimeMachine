# LLM 路由策略

> 你已有 Claude API + DeepSeek API。这份文档定义两家 LLM 在 v2 离线管线和运行时各自负责什么任务,以及为什么。
> embedding 改用本地 bge-m3,完全不依赖第三方付费 API。

---

## 🎯 路由原则

不同任务对成本/质量/速度的敏感度不同,简单分三档:

| 档位 | 模型 | 单价 (输入/输出) | 适合任务 | 调用规模 |
|---|---|---|---|---|
| **fast** | DeepSeek-V3 (`deepseek-chat`) | ¥2 / ¥8 / M tokens | 大批量、模板化、容错高 | 数千次 |
| **high** | Claude Haiku 4.5 | $1 / $5 / M tokens | 中批量、需稳定 JSON、需推理 | 数十次 |
| **best** | Claude Sonnet 4.6 | $3 / $15 / M tokens | 决赛级别文案、复杂叙事 | 个位数次 |

---

## 📋 v2 任务路由表

### Phase 1 离线管线

| 脚本 | 调用次数 | 路由 | 理由 |
|---|---|---|---|
| `03_cluster_opinions.py` 主流观点摘要 | 30 话题 × 16 年 ≈ 480 次 | **fast** | 模板化提炼,DeepSeek 完全够 |
| `04_extract_quotes.py` 金句抽取 | 480 次 | **fast** | 同上 |
| `05_attach_events.py` 事件锚点匹配 | 30 次 | **fast** | 简单分类任务 |
| `06_predict_2029.py` 2029 预测 | 30 次 | **high** | 需要推理 + 三种情境的稳定 JSON,Claude Haiku 更稳 |
| `08_mood_and_archive_no.py` 情绪标注 | ~480 次 | **fast** | 单标签分类,DeepSeek 够 |
| `10_curatorial_intros.py`(新)起草 13 篇导语 | 13 次 | **best** | **决定产品调性的内容,Sonnet 4.6 一发入魂** |

### Phase 3 运行时 API

| 路由 | 调用次数 | 路由 | 理由 |
|---|---|---|---|
| `/api/predict/[id]`(2029 预测刷新) | 偶发(7 天缓存) | **high** | 同离线版,质量优先 |
| `/api/search` 搜索兜底浅层时光轴 | 用户搜索时 | **high** | 实时,需要 1 次给好结果,Haiku 速度+质量平衡 |
| 知乎直答 Agent(可选叠加) | 兜底搜索时 | — | 优先用 Claude Haiku;直答额度紧张(100/天) |

---

## 🔧 客户端代码(scripts/_lib/llm.py 升级版)

```python
# scripts/_lib/llm.py
import os
from openai import OpenAI
from anthropic import Anthropic
from typing import Literal

# DeepSeek (OpenAI-compatible)
_deepseek = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)
_claude = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

Quality = Literal["fast", "high", "best"]

def chat(
    messages: list[dict],
    quality: Quality = "fast",
    json_mode: bool = False,
) -> str:
    """统一 chat 入口,按 quality 路由"""
    if quality == "fast":
        return _deepseek_chat(messages, json_mode)
    model = "claude-haiku-4-5" if quality == "high" else "claude-sonnet-4-6"
    return _claude_chat(messages, model, json_mode)

def _deepseek_chat(messages: list[dict], json_mode: bool) -> str:
    resp = _deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        response_format={"type": "json_object"} if json_mode else None,
        temperature=0.3,
    )
    return resp.choices[0].message.content

def _claude_chat(messages: list[dict], model: str, json_mode: bool) -> str:
    # Claude 没有原生 JSON mode,通过 system prompt 强制
    system = "You must respond with valid JSON only, no other text." if json_mode else ""
    resp = _claude.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": m["role"], "content": m["content"]} for m in messages],
    )
    return resp.content[0].text

# Embedding · 本地 bge-m3
_bge = None

def embed(texts: list[str]) -> list[list[float]]:
    global _bge
    if _bge is None:
        from sentence_transformers import SentenceTransformer
        _bge = SentenceTransformer("BAAI/bge-m3")
    return _bge.encode(texts, normalize_embeddings=True).tolist()
```

### 用法示例

```python
from _lib.llm import chat, embed

# 大批量便宜
summary = chat(messages=[...], quality="fast", json_mode=True)

# 单次高质量
prediction = chat(messages=[...], quality="high", json_mode=True)

# 决赛级文案
intro = chat(messages=[...], quality="best")

# embedding(本地)
vecs = embed(["回答1", "回答2", "回答3"])
```

---

## 💰 总成本估算(48h 全程)

| 项 | 调用规模 | 模型 | 估算成本 |
|---|---|---|---|
| 观点摘要 + 金句 + mood + 事件 | ~1500 次 × 800 tokens | DeepSeek | < ¥5 |
| 2029 预测(离线 30 + 运行时 ~5)| 35 次 × 1500 tokens | Claude Haiku | < $0.5 |
| 13 篇策展导语 | 13 次 × 2000 tokens | Claude Sonnet | < $1 |
| 搜索兜底浅层时光轴(运行时) | 50 次 × 1000 tokens | Claude Haiku | < $0.5 |
| Embedding | 30 话题 × ~300 答 × 平均 200 tokens | 本地 bge-m3 | **¥0** |
| **总计** | | | **≈ $2-3 + ¥5** |

不到一杯咖啡。

---

## 🚦 P0-T4 升级提醒

v1 plan 的 `scripts/_lib/llm.py` 只用了 DeepSeek。**升级到本文档第 4 节的代码**,然后所有调用 `chat(...)` 的脚本(03/04/05/06/08/10)按本文档第 2 节的"路由"列指定 `quality=...` 参数。

具体改法:在 v2 plan 的 P0-T4 之后追加一个 patch 步骤(已记录在 `2026-05-09-museum-upgrade-plan.md` 的 Phase 0 增量章节)。

---

## 🔄 fallback 链(任一家挂了的应急)

| 主用 | 失败时 |
|---|---|
| DeepSeek 挂了 | 全部降级到 Claude Haiku(贵 5 倍但能跑完) |
| Claude 挂了 | 2029 预测 / 导语降级到 DeepSeek + 严格 JSON schema 校验 |
| 本地 bge-m3 装不上 | 降级到硅基流动(注册 → 1 块钱跑完全部 embedding) |
| 知乎直答挂了 | 搜索兜底浅层时光轴换 Claude Haiku 直接生成 |

代码层面:`chat(messages, quality="fast")` 调用统一入口,降级只需改 `_lib/llm.py` 的路由逻辑,业务代码零修改。
