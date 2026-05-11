"""Vercel serverless function — 时光档案馆后端

Vercel 把这个文件当作单个 serverless function,Flask 内部处理所有 /api/* 路径。
本地开发请用 scripts/demo/server.py。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

import httpx
from flask import Flask, request, jsonify, redirect, make_response

# 加入 _lib 路径
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _lib.zhihu_api import zhihu_search, publish_pin  # noqa: E402

# 数据目录:Vercel 上是 /var/task/api/data/
DATA_DIR = HERE / "data"

app = Flask(__name__)


# ───────── 健康检查 ─────────

@app.get("/api/health")
def health():
    return jsonify({
        "ok": True,
        "data_dir_exists": DATA_DIR.exists(),
        "topic_files": len(list(DATA_DIR.glob("*.json"))) if DATA_DIR.exists() else 0,
    })


# ───────── 精选话题元数据 ─────────

@app.get("/api/topics")
def list_topics():
    out = []
    if not DATA_DIR.exists():
        return jsonify({"topics": [], "error": "data dir missing"}), 500
    for f in sorted(DATA_DIR.glob("*.json")):
        if f.name.startswith("_") or f.name == "curation.json":
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
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


def infer_year_simple(text: str, edit_year):
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

    queries = [q]
    if "事件" not in q:
        queries.append(f"{q} 事件")
    if len(q) > 4 and " " in q:
        queries.append(q.split()[0])

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

    by_year = {}
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

    for y in by_year:
        by_year[y].sort(key=lambda x: x.get("vote_up_count", 0), reverse=True)

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


# ───────── OAuth ─────────

OAUTH_APP_ID = os.getenv("ZHIHU_OAUTH_APP_ID", "")
OAUTH_APP_KEY = os.getenv("ZHIHU_OAUTH_APP_KEY", "")
OAUTH_REDIRECT_URI = os.getenv("ZHIHU_OAUTH_REDIRECT_URI", "")
OAUTH_BASE = "https://openapi.zhihu.com"


@app.get("/api/auth/zhihu")
def auth_zhihu():
    if not OAUTH_APP_ID:
        return jsonify({
            "error": "OAuth not configured",
            "message": "管理员需要在 Vercel 环境变量配置 ZHIHU_OAUTH_APP_ID/APP_KEY/REDIRECT_URI",
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
    resp.set_cookie("zh_oauth_token", access_token, httponly=True, max_age=data.get("expires_in", 3600), secure=True, samesite="Lax")
    if user.get("fullname"):
        resp.set_cookie("zh_user_name", user["fullname"], max_age=3600, secure=True, samesite="Lax")
        resp.set_cookie("zh_user_avatar", user.get("avatar_path", ""), max_age=3600, secure=True, samesite="Lax")
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
    body = request.get_json(force=True, silent=True) or {}
    content = (body.get("content") or "").strip()
    title = body.get("title")
    if not content:
        return jsonify({"error": "missing content"}), 400
    try:
        r = publish_pin(content=content, title=title, image_urls=body.get("image_urls"))
        return jsonify(r)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Vercel Python runtime requires this object name
# (or use `def handler(request): ...` for plain WSGI)
