"""时光档案馆 Demo 服务端

提供:
  GET  /                        静态首页(dist/index.html)
  GET  /api/topics              精选话题元数据
  GET  /api/search?q=...        自定义话题实时搜索 + 启发式年份分桶
  GET  /api/auth/zhihu          跳转知乎 OAuth
  GET  /api/auth/callback       OAuth 回调,存 cookie
  GET  /api/me                  返回当前登录用户
  POST /api/publish/pin         用 OAuth token 发想法到圈子

OAuth 凭证(.env.local):
  ZHIHU_OAUTH_APP_ID
  ZHIHU_OAUTH_APP_KEY        # 即 client_secret
  ZHIHU_OAUTH_REDIRECT_URI

签名搜索用:
  ZHIHU_APP_KEY               # 用户 token(jzwa)
  ZHIHU_APP_SECRET            # HMAC secret
  ZHIHU_ACCESS_SECRET         # 数据平台 Bearer token
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import httpx
from flask import Flask, request, jsonify, redirect, make_response

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from _lib.zhihu_api import zhihu_search, publish_pin, hot_list, RING_ID  # noqa: E402

DATA_DIR = ROOT / "data" / "demo"
DIST = ROOT / "dist"

app = Flask(__name__, static_folder=str(DIST), static_url_path="")


# ───────── 首页 ─────────

@app.get("/")
def home():
    return app.send_static_file("index.html")


# ───────── 精选话题元数据 ─────────

@app.get("/api/topics")
def list_topics():
    out = []
    for f in sorted(DATA_DIR.glob("*.json")):
        if f.name.startswith("_"):
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        if len(d.get("year_summaries", {})) < 2:
            continue
        years = sorted(int(y) for y in d.get("year_summaries", {}).keys())
        out.append({
            "id": d["id"],
            "title": d["title"],
            "category": d.get("category"),
            "year_range": [years[0], years[-1]] if years else None,
            "year_count": len(years),
        })
    return jsonify({"topics": out})


# ───────── 自定义话题搜索 ─────────

YEAR_RE = re.compile(r"(?:^|[^\d])(20[01]\d|2026)(?:\s*年|\s*年[左前后底初中]|[/\-．. ])")


def infer_year_simple(text: str, edit_year: int | None) -> int | None:
    if text:
        found = [int(m) for m in YEAR_RE.findall(text)]
        cand = [y for y in found if 2008 <= y <= 2026]
        if cand:
            return min(cand)
    return edit_year


@app.get("/api/search")
def search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"error": "missing q"}), 400

    # 多关键词扩展:原 query + 几个常见变体
    queries = [q]
    if "事件" not in q:
        queries.append(f"{q} 事件")
    if len(q) > 4:
        queries.append(q.split()[0] if " " in q else q[:3])

    seen = set()
    raw_items = []
    for kw in queries[:3]:
        try:
            r = zhihu_search(kw, count=10)
            for it in r.get("Data", {}).get("Items", []):
                cid = it.get("ContentID")
                if not cid or cid in seen:
                    continue
                seen.add(cid)
                raw_items.append(it)
        except Exception as e:
            print(f"  [search err] {kw}: {e}")
            continue

    if not raw_items:
        return jsonify({"q": q, "items": [], "by_year": {}, "year_count": 0})

    # 启发式年份分桶
    by_year: dict[int, list[dict]] = {}
    for it in raw_items:
        edit_year = datetime.fromtimestamp(it["EditTime"]).year if it.get("EditTime") else None
        y = infer_year_simple(it.get("ContentText", ""), edit_year)
        if y is None:
            continue
        by_year.setdefault(int(y), []).append({
            "title": it.get("Title", "").replace(" - 知乎", ""),
            "content_type": it.get("ContentType"),
            "content_text": (it.get("ContentText") or "")[:300],
            "url": it.get("Url", ""),
            "vote_up_count": it.get("VoteUpCount", 0),
            "author_name": it.get("AuthorName"),
            "edit_year": edit_year,
        })

    # 每年按赞同数排序
    for y in by_year:
        by_year[y].sort(key=lambda x: x.get("vote_up_count", 0), reverse=True)

    # 取每年最高赞的 ContentText 节选作"代表片段"
    summaries = {}
    for y, items in by_year.items():
        if items:
            top = items[0]
            summaries[y] = {
                "representative_quote": top["content_text"][:120],
                "author": top["author_name"],
                "url": top["url"],
            }

    return jsonify({
        "q": q,
        "year_count": len(by_year),
        "by_year": {str(y): by_year[y] for y in sorted(by_year)},
        "summaries": {str(y): summaries[y] for y in summaries},
    })


# ───────── 知乎热榜直达 ─────────

@app.get("/api/hotlist")
def hotlist():
    try:
        r = hot_list(limit=10)
        items = r.get("Data", {}).get("Items", [])
        return jsonify({"items": [
            {
                "title": it.get("Title", "").strip(),
                "url": it.get("Url", ""),
                "summary": (it.get("Summary") or "")[:120],
                "thumb": it.get("ThumbnailUrl", ""),
            }
            for it in items if it.get("Title")
        ]})
    except Exception as e:
        return jsonify({"error": str(e), "items": []}), 500


# ───────── OAuth ─────────

OAUTH_APP_ID = os.getenv("ZHIHU_OAUTH_APP_ID", "")
OAUTH_APP_KEY = os.getenv("ZHIHU_OAUTH_APP_KEY", "")
OAUTH_REDIRECT_URI = os.getenv("ZHIHU_OAUTH_REDIRECT_URI", "http://localhost:7777/api/auth/callback")
OAUTH_BASE = "https://openapi.zhihu.com"


@app.get("/api/auth/zhihu")
def auth_zhihu():
    if not OAUTH_APP_ID:
        return jsonify({
            "error": "OAuth not configured",
            "message": "管理员需要在 .env.local 配置 ZHIHU_OAUTH_APP_ID 和 ZHIHU_OAUTH_APP_KEY。这两个值在 5/12 黑客松广场创建项目后由系统自动分配。",
        }), 503
    params = urlencode({
        "app_id": OAUTH_APP_ID,
        "redirect_uri": OAUTH_REDIRECT_URI,
        "response_type": "code",
    })
    return redirect(f"{OAUTH_BASE}/authorize?{params}")


@app.get("/api/auth/callback")
def auth_callback():
    code = request.args.get("code")
    if not code:
        return "missing code", 400
    if not OAUTH_APP_ID or not OAUTH_APP_KEY:
        return "OAuth not configured", 503

    # 用 code 换 access_token
    try:
        r = httpx.post(
            f"{OAUTH_BASE}/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "app_id": OAUTH_APP_ID,
                "app_key": OAUTH_APP_KEY,
                "redirect_uri": OAUTH_REDIRECT_URI,
            },
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        access_token = data.get("access_token")
        if not access_token:
            return jsonify({"error": "no token", "raw": data}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # 拿用户信息
    user = {}
    try:
        ur = httpx.get(
            f"{OAUTH_BASE}/user_info",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        if ur.status_code == 200:
            user = ur.json().get("data", {})
    except Exception:
        pass

    resp = make_response(redirect("/?login=ok"))
    resp.set_cookie("zh_oauth_token", access_token, httponly=True, max_age=data.get("expires_in", 3600))
    if user.get("fullname"):
        resp.set_cookie("zh_user_name", user["fullname"], max_age=3600)
        resp.set_cookie("zh_user_avatar", user.get("avatar_path", ""), max_age=3600)
    return resp


@app.get("/api/me")
def me():
    token = request.cookies.get("zh_oauth_token")
    if not token:
        return jsonify({"logged_in": False})
    return jsonify({
        "logged_in": True,
        "name": request.cookies.get("zh_user_name", ""),
        "avatar": request.cookies.get("zh_user_avatar", ""),
    })


@app.post("/api/logout")
def logout():
    resp = make_response(jsonify({"ok": True}))
    resp.delete_cookie("zh_oauth_token")
    resp.delete_cookie("zh_user_name")
    resp.delete_cookie("zh_user_avatar")
    return resp


# ───────── 发布想法 ─────────

@app.post("/api/publish/pin")
def publish():
    """两种模式:
    1. 有 OAuth token → 用户的身份发(需要 OAuth 平台允许)
    2. 无 token → 用 app_key 签名发(以 jzwa 身份)
    """
    body = request.get_json(force=True)
    content = body.get("content", "").strip()
    title = body.get("title")
    if not content:
        return jsonify({"error": "missing content"}), 400

    # 当前实现:统一用签名鉴权(app_key 身份)
    # OAuth token 模式留作未来扩展
    try:
        r = publish_pin(content=content, title=title, image_urls=body.get("image_urls"))
        return jsonify(r)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ───────── 启动 ─────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", "7777"))
    print(f"\n🦊 时光档案馆 Demo  http://localhost:{port}/\n")
    app.run(host="0.0.0.0", port=port, debug=False)
