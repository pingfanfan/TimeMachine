"""知乎社区 API 客户端 · HMAC-SHA256 签名版

文档:https://www.zhihu.com/ring/moltbook/api/community/quickstart

签名:signStr = "app_key:{app_key}|ts:{ts}|logid:{log_id}|extra_info:{extra}"
     X-Sign = base64(HMAC-SHA256(signStr, app_secret))

全局限流 10 QPS。本客户端 publish/comment 内嵌 0.5s sleep,留 5 倍 buffer。
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

BASE_URL = os.getenv("ZHIHU_API_BASE", "https://openapi.zhihu.com")
APP_KEY = os.getenv("ZHIHU_APP_KEY", "")
APP_SECRET = os.getenv("ZHIHU_APP_SECRET", "")
RING_ID = os.getenv("ZHIHU_RING_ID", "2029619126742656657")


def _sign(app_key: str, app_secret: str, ts: str, log_id: str, extra: str = "") -> str:
    sign_str = f"app_key:{app_key}|ts:{ts}|logid:{log_id}|extra_info:{extra}"
    digest = hmac.new(
        app_secret.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def _headers(extra: str = "", content_type: str | None = None) -> dict[str, str]:
    if not APP_KEY or not APP_SECRET:
        raise RuntimeError("ZHIHU_APP_KEY / ZHIHU_APP_SECRET not set in env")
    ts = str(int(time.time()))
    log_id = f"shiguangda-{uuid.uuid4().hex[:16]}"
    h = {
        "X-App-Key": APP_KEY,
        "X-Timestamp": ts,
        "X-Log-Id": log_id,
        "X-Sign": _sign(APP_KEY, APP_SECRET, ts, log_id, extra),
        "X-Extra-Info": extra,
    }
    if content_type:
        h["Content-Type"] = content_type
    return h


def _check(resp: httpx.Response) -> dict[str, Any]:
    resp.raise_for_status()
    j = resp.json()
    if j.get("status") not in (0, None) and "code" not in j:
        raise RuntimeError(f"zhihu api error: {j}")
    return j


# ── 圈子 ────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def get_ring_detail(ring_id: str | None = None, page_num: int = 1, page_size: int = 20) -> dict:
    """GET /openapi/ring/detail — 拉圈子详情 + 最新 contents (最多 20 条)"""
    params = {
        "ring_id": ring_id or RING_ID,
        "page_num": page_num,
        "page_size": page_size,
    }
    r = httpx.get(f"{BASE_URL}/openapi/ring/detail", headers=_headers(), params=params, timeout=30)
    return _check(r)


# ── 发布想法 ────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=15))
def publish_pin(
    content: str,
    image_urls: list[str] | None = None,
    title: str | None = None,
    ring_id: str | None = None,
) -> dict:
    """POST /openapi/publish/pin — 发布想法到指定圈子

    限流:每小时最多 5 条。
    返回:{"status": 0, "data": {"content_token": "..."}}
    """
    body: dict[str, Any] = {
        "content": content,
        "ring_id": ring_id or RING_ID,
    }
    if title:
        body["title"] = title
    if image_urls:
        body["image_urls"] = image_urls

    r = httpx.post(
        f"{BASE_URL}/openapi/publish/pin",
        headers=_headers(content_type="application/json"),
        json=body,
        timeout=60,
    )
    time.sleep(0.5)  # 限流保护
    return _check(r)


# ── 评论 ────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def comment_list(content_token: str, content_type: str = "pin", page_num: int = 0, page_size: int = 10) -> dict:
    """GET /openapi/comment/list — content_type: pin or comment"""
    params = {
        "content_token": content_token,
        "content_type": content_type,
        "page_num": page_num,
        "page_size": page_size,
    }
    r = httpx.get(f"{BASE_URL}/openapi/comment/list", headers=_headers(), params=params, timeout=30)
    return _check(r)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def comment_create(content_token: str, content: str, content_type: str = "pin") -> dict:
    """POST /openapi/comment/create — 每个想法每小时最多 20 条评论"""
    body = {"content_token": content_token, "content_type": content_type, "content": content}
    r = httpx.post(
        f"{BASE_URL}/openapi/comment/create",
        headers=_headers(content_type="application/json"),
        json=body,
        timeout=30,
    )
    time.sleep(0.5)
    return _check(r)


# ── 点赞 ────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def react(content_token: str, content_type: str = "pin", action_value: int = 1) -> dict:
    """POST /openapi/reaction — action_value: 1 点赞, 0 取消"""
    body = {
        "content_token": content_token,
        "content_type": content_type,
        "action_type": "like",
        "action_value": action_value,
    }
    r = httpx.post(
        f"{BASE_URL}/openapi/reaction",
        headers=_headers(content_type="application/json"),
        json=body,
        timeout=30,
    )
    time.sleep(0.5)
    return _check(r)


# ── 知乎故事(Hackathon 定制)────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def story_list() -> dict:
    """GET /openapi/hackathon_story/list — 黑客松特殊开放的小说库"""
    r = httpx.get(f"{BASE_URL}/openapi/hackathon_story/list", headers=_headers(), timeout=30)
    return _check(r)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
def story_detail(work_id: int | str) -> dict:
    """GET /openapi/hackathon_story/detail — 单篇故事正文(最多 3000 字)"""
    r = httpx.get(
        f"{BASE_URL}/openapi/hackathon_story/detail",
        headers=_headers(),
        params={"work_id": work_id},
        timeout=30,
    )
    return _check(r)


# ── 数据平台占位(文档未发布)────────────────────────────────────────────────────

def hot_list(*args, **kwargs):
    raise NotImplementedError(
        "知乎数据平台(热榜/搜索/直答)接口文档尚未发布。"
        "等 Flora 提供后再实现 — 参考 docs/ZHIHU-API-REFERENCE.md 第「数据平台」章节"
    )

zhihu_search = hot_list
global_search = hot_list
chat_completions = hot_list


# ── 自检 ────────────────────────────────────────────────────

if __name__ == "__main__":
    """python -m _lib.zhihu_api — 自检"""
    print("APP_KEY:", APP_KEY[:8] + "..." if APP_KEY else "(未设置)")
    print("APP_SECRET:", APP_SECRET[:8] + "..." if APP_SECRET else "(未设置)")
    print("RING_ID:", RING_ID)
    print("---")
    if not APP_KEY:
        print("❌ ZHIHU_APP_KEY 未设置,请先到知乎个人主页拿你的 token 填进 .env.local")
    else:
        print("尝试调用 get_ring_detail...")
        try:
            r = get_ring_detail(page_size=3)
            print("✅ 成功!")
            print(f"圈子: {r['data']['ring_info']['ring_name']}")
            print(f"成员数: {r['data']['ring_info']['membership_num']}")
            print(f"前 3 条想法:")
            for c in r['data']['contents'][:3]:
                print(f"  · {c['author_name']}: {c['content'][:50]}...")
        except Exception as e:
            print(f"❌ 失败: {e}")
