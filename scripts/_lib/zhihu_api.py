"""知乎 API 客户端 · 双平台双鉴权

【两套独立 API 平台】

1. 社区 API(openapi.zhihu.com)— HMAC-SHA256 签名
   - 文档:https://www.zhihu.com/ring/moltbook/api/community/quickstart
   - 用途:圈子/想法/评论/点赞/故事
   - 凭证:ZHIHU_APP_KEY(用户 token) + ZHIHU_APP_SECRET(应用密钥)

2. 数据开放平台(developer.zhihu.com)— Bearer Token
   - 文档:https://developer.zhihu.com/docs
   - 用途:知乎搜索/全网搜索/直答 Agent/热榜
   - 凭证:ZHIHU_ACCESS_SECRET(Access Secret, developer.zhihu.com 个人中心拿)

全局限流(社区)10 QPS。本客户端 publish/comment 内嵌 0.5s sleep。
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import time
import uuid
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

# ───────── 配置 ─────────

COMMUNITY_BASE = os.getenv("ZHIHU_API_BASE", "https://openapi.zhihu.com")
DATA_BASE = os.getenv("ZHIHU_DATA_API_BASE", "https://developer.zhihu.com")

APP_KEY = os.getenv("ZHIHU_APP_KEY", "")                 # 用户 token
APP_SECRET = os.getenv("ZHIHU_APP_SECRET", "")           # 社区 API 应用密钥
ACCESS_SECRET = os.getenv("ZHIHU_ACCESS_SECRET", "")     # 数据平台 Access Secret
RING_ID = os.getenv("ZHIHU_RING_ID", "2029619126742656657")


# ═════════════════════════════════════════════════════
# 社区 API 鉴权 · HMAC-SHA256
# ═════════════════════════════════════════════════════

def _hmac_sign(app_key: str, app_secret: str, ts: str, log_id: str, extra: str = "") -> str:
    sign_str = f"app_key:{app_key}|ts:{ts}|logid:{log_id}|extra_info:{extra}"
    digest = hmac.new(app_secret.encode(), sign_str.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def _community_headers(extra: str = "", content_type: str | None = None) -> dict[str, str]:
    if not APP_KEY or not APP_SECRET:
        raise RuntimeError("ZHIHU_APP_KEY / ZHIHU_APP_SECRET not set")
    ts = str(int(time.time()))
    log_id = f"shiguangda-{uuid.uuid4().hex[:16]}"
    h = {
        "X-App-Key": APP_KEY,
        "X-Timestamp": ts,
        "X-Log-Id": log_id,
        "X-Sign": _hmac_sign(APP_KEY, APP_SECRET, ts, log_id, extra),
        "X-Extra-Info": extra,
    }
    if content_type:
        h["Content-Type"] = content_type
    return h


def _check_community(r: httpx.Response) -> dict[str, Any]:
    r.raise_for_status()
    j = r.json()
    if isinstance(j, dict) and j.get("status") not in (0, None):
        raise RuntimeError(f"community api error: {j}")
    return j


# ═════════════════════════════════════════════════════
# 数据平台鉴权 · Bearer Token
# ═════════════════════════════════════════════════════

def _data_headers(content_type: str | None = "application/json") -> dict[str, str]:
    if not ACCESS_SECRET:
        raise RuntimeError("ZHIHU_ACCESS_SECRET not set — 去 developer.zhihu.com 个人中心拿")
    h = {
        "Authorization": f"Bearer {ACCESS_SECRET}",
        "X-Request-Timestamp": str(int(time.time())),
    }
    if content_type:
        h["Content-Type"] = content_type
    return h


def _check_data(r: httpx.Response) -> dict[str, Any]:
    r.raise_for_status()
    j = r.json()
    if isinstance(j, dict) and j.get("Code") not in (0, None):
        raise RuntimeError(f"data api error: {j}")
    return j


# ═════════════════════════════════════════════════════
# 社区 API
# ═════════════════════════════════════════════════════

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def get_ring_detail(ring_id: str | None = None, page_num: int = 1, page_size: int = 20) -> dict:
    """GET /openapi/ring/detail"""
    r = httpx.get(
        f"{COMMUNITY_BASE}/openapi/ring/detail",
        headers=_community_headers(),
        params={"ring_id": ring_id or RING_ID, "page_num": page_num, "page_size": page_size},
        timeout=30,
    )
    return _check_community(r)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
def publish_pin(content: str, image_urls: list[str] | None = None, title: str | None = None, ring_id: str | None = None) -> dict:
    """POST /openapi/publish/pin · 每小时最多 5 条"""
    body: dict[str, Any] = {"content": content, "ring_id": ring_id or RING_ID}
    if title:
        body["title"] = title
    if image_urls:
        body["image_urls"] = image_urls
    r = httpx.post(
        f"{COMMUNITY_BASE}/openapi/publish/pin",
        headers=_community_headers(content_type="application/json"),
        json=body,
        timeout=60,
    )
    time.sleep(0.5)
    return _check_community(r)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def comment_list(content_token: str, content_type: str = "pin", page_num: int = 0, page_size: int = 10) -> dict:
    r = httpx.get(
        f"{COMMUNITY_BASE}/openapi/comment/list",
        headers=_community_headers(),
        params={"content_token": content_token, "content_type": content_type, "page_num": page_num, "page_size": page_size},
        timeout=30,
    )
    return _check_community(r)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def comment_create(content_token: str, content: str, content_type: str = "pin") -> dict:
    """POST /openapi/comment/create · 每想法每小时最多 20 条评论"""
    r = httpx.post(
        f"{COMMUNITY_BASE}/openapi/comment/create",
        headers=_community_headers(content_type="application/json"),
        json={"content_token": content_token, "content_type": content_type, "content": content},
        timeout=30,
    )
    time.sleep(0.5)
    return _check_community(r)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def react(content_token: str, content_type: str = "pin", action_value: int = 1) -> dict:
    """POST /openapi/reaction · action_value: 1 点赞 / 0 取消"""
    r = httpx.post(
        f"{COMMUNITY_BASE}/openapi/reaction",
        headers=_community_headers(content_type="application/json"),
        json={"content_token": content_token, "content_type": content_type, "action_type": "like", "action_value": action_value},
        timeout=30,
    )
    time.sleep(0.5)
    return _check_community(r)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def story_list() -> dict:
    """GET /openapi/hackathon_story/list · 黑客松特殊开放"""
    r = httpx.get(f"{COMMUNITY_BASE}/openapi/hackathon_story/list", headers=_community_headers(), timeout=30)
    return _check_community(r)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def story_detail(work_id: int | str) -> dict:
    r = httpx.get(
        f"{COMMUNITY_BASE}/openapi/hackathon_story/detail",
        headers=_community_headers(),
        params={"work_id": work_id},
        timeout=30,
    )
    return _check_community(r)


# ═════════════════════════════════════════════════════
# 数据开放平台 API
# ═════════════════════════════════════════════════════

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def zhihu_search(query: str, count: int = 10) -> dict:
    """GET /api/v1/content/zhihu_search · 站内搜索 · Count 最大 10"""
    r = httpx.get(
        f"{DATA_BASE}/api/v1/content/zhihu_search",
        headers=_data_headers(),
        params={"Query": query, "Count": min(count, 10)},
        timeout=30,
    )
    return _check_data(r)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def global_search(query: str, count: int = 20) -> dict:
    """GET /api/v1/content/global_search · 全网搜索 · Count 最大 20"""
    r = httpx.get(
        f"{DATA_BASE}/api/v1/content/global_search",
        headers=_data_headers(),
        params={"Query": query, "Count": min(count, 20)},
        timeout=30,
    )
    return _check_data(r)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def hot_list(limit: int = 30) -> dict:
    """GET /api/v1/content/hot_list · 热榜 · Limit 最大 30 · 无时间窗口参数"""
    r = httpx.get(
        f"{DATA_BASE}/api/v1/content/hot_list",
        headers=_data_headers(),
        params={"Limit": min(limit, 30)},
        timeout=30,
    )
    return _check_data(r)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def chat_completions(messages: list[dict], model: str = "zhida-fast-1p5", stream: bool = False) -> dict:
    """POST /v1/chat/completions · 直答 Agent

    模型档位:
    - zhida-fast-1p5     快速回答
    - zhida-thinking-1p5 深度思考(带 reasoning_content)
    - zhida-agent        智能思考
    """
    r = httpx.post(
        f"{DATA_BASE}/v1/chat/completions",
        headers=_data_headers(),
        json={"model": model, "messages": messages, "stream": stream},
        timeout=120,
    )
    return _check_data(r) if not stream else r


# ═════════════════════════════════════════════════════
# 自检
# ═════════════════════════════════════════════════════

if __name__ == "__main__":
    """python -m _lib.zhihu_api"""
    print("=" * 50)
    print("时光档案馆 · 知乎 API 客户端自检")
    print("=" * 50)
    print(f"APP_KEY:        {APP_KEY!r}")
    print(f"APP_SECRET:     {(APP_SECRET[:8] + '...') if APP_SECRET else '(未设置)'}")
    print(f"ACCESS_SECRET:  {(ACCESS_SECRET[:8] + '...') if ACCESS_SECRET else '(未设置)'}")
    print(f"RING_ID:        {RING_ID}")
    print()

    # 测试 1:社区 API(HMAC)
    print("--- [1] 社区 API · get_ring_detail (HMAC 签名) ---")
    if APP_KEY and APP_SECRET:
        try:
            r = get_ring_detail(page_size=3)
            print(f"✅ 圈子: {r['data']['ring_info']['ring_name']}")
            print(f"   成员: {r['data']['ring_info']['membership_num']}, 讨论: {r['data']['ring_info']['discussion_num']}")
        except Exception as e:
            print(f"❌ 失败: {e}")
    else:
        print("⚠️  APP_KEY / APP_SECRET 未设置,跳过")
    print()

    # 测试 2:数据平台 API(Bearer)
    print("--- [2] 数据平台 · hot_list (Bearer Token) ---")
    if ACCESS_SECRET:
        try:
            r = hot_list(limit=3)
            for item in r["Data"]["Items"][:3]:
                print(f"  · {item['Title'][:50]}")
        except Exception as e:
            print(f"❌ 失败: {e}")
    else:
        print("⚠️  ACCESS_SECRET 未设置 — 请去 developer.zhihu.com 个人中心申请")
    print()

    print("=" * 50)
    print("自检完成")
