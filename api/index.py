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
    # 知乎用非标准字段名 `authorization_code`(不是标准 OAuth 2.0 的 `code`)
    code = request.args.get("code") or request.args.get("authorization_code")
    if not code:
        # 知乎可能传了 error / error_description
        err = request.args.get("error") or "no_code"
        err_desc = request.args.get("error_description") or "(empty)"
        all_args = dict(request.args)
        return (
            f"""<!doctype html><meta charset=utf-8>
<style>body{{font-family:system-ui;padding:40px;max-width:700px;margin:auto;background:#08101F;color:#EBE0C4}}h1{{color:#A8252F}}pre{{background:rgba(255,255,255,0.05);padding:16px;border-radius:4px;overflow:auto}}a{{color:#F1B644}}</style>
<h1>OAuth 回调缺少 code</h1>
<p>知乎跳回来时,URL 里没有 <code>?code=...</code>,只看到这些参数:</p>
<pre>{json.dumps(all_args, ensure_ascii=False, indent=2)}</pre>
<p><strong>error:</strong> {err}<br>
<strong>error_description:</strong> {err_desc}</p>
<hr>
<p>常见原因:</p>
<ul>
  <li>OAuth 应用还在审核中(知乎黑客松项目可能要审核才放真实流量)</li>
  <li>你在知乎授权页点了「拒绝」</li>
  <li>知乎 session 异常,授权页报错跳回</li>
  <li>redirect_uri 在知乎平台没填对</li>
</ul>
<p><a href="/api/auth/zhihu">↩ 再试一次</a> · <a href="/">回到首页</a></p>""",
            400,
            {"Content-Type": "text/html; charset=utf-8"},
        )
    if not OAUTH_APP_ID or not OAUTH_APP_KEY:
        return "OAuth not configured", 503

    # 严格按知乎 access_token 文档字段:
    # https://www.zhihu.com/ring/moltbook/api/oauth/access_token
    data_payload = {
        "app_id": OAUTH_APP_ID,
        "app_key": OAUTH_APP_KEY,
        "grant_type": "authorization_code",
        "redirect_uri": OAUTH_REDIRECT_URI,
        "code": code,
    }
    try:
        r = httpx.post(
            f"{OAUTH_BASE}/access_token",
            data=data_payload,
            timeout=30,
        )
        try:
            data = r.json()
        except Exception:
            return (
                f"<h1>Token endpoint 返回非 JSON</h1><p>HTTP {r.status_code}</p><pre>{r.text[:1000]}</pre>",
                500,
                {"Content-Type": "text/html; charset=utf-8"},
            )
        access_token = data.get("access_token")
        if not access_token:
            # 显示完整调试信息(部署后可以拿掉)
            return (
                f"""<!doctype html><meta charset=utf-8>
<style>body{{font-family:system-ui;padding:40px;max-width:800px;margin:auto;background:#08101F;color:#EBE0C4}}h1{{color:#A8252F}}pre{{background:rgba(255,255,255,0.05);padding:16px;border-radius:4px;overflow:auto;font-size:12px}}</style>
<h1>Token 交换失败</h1>
<p>HTTP {r.status_code}</p>
<p>code (前 8 字符): {code[:8]}…</p>
<p>token endpoint 返回:</p>
<pre>{json.dumps(data, ensure_ascii=False, indent=2)}</pre>
<p><a href="/api/auth/zhihu" style="color:#F1B644">↩ 再试一次</a></p>""",
                500,
                {"Content-Type": "text/html; charset=utf-8"},
            )
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


# ───────── 「我的视角」OAuth 接口 ─────────

def _oauth_get(path: str, token: str, params: dict | None = None) -> dict | None:
    """统一调 OAuth API"""
    try:
        r = httpx.get(
            f"{OAUTH_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params or {},
            timeout=15,
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f"  [oauth_get err] {path}: {e}")
    return None


@app.get("/api/me/profile")
def me_profile():
    """登录用户的完整画像:user_info + 关注 / 粉丝 count + 最近 moments"""
    token = request.cookies.get("zh_oauth_token")
    if not token:
        return jsonify({"error": "not logged in"}), 401

    # 并行拿 4 个接口
    info = _oauth_get("/openapi/user_info", token) or {}
    user = info.get("data", info)  # 兼容两种格式

    followers = _oauth_get("/openapi/user_followers", token, {"page": 0, "per_page": 1}) or {}
    followed = _oauth_get("/openapi/user_followed", token, {"page": 0, "per_page": 1}) or {}
    moments = _oauth_get("/openapi/user_moments", token, {"page": 0, "per_page": 5}) or {}

    return jsonify({
        "user": {
            "hash_id":     user.get("hash_id", ""),
            "fullname":    user.get("fullname", ""),
            "headline":    user.get("headline", ""),
            "description": user.get("description", ""),
            "avatar":      user.get("avatar_path", ""),
            "url":         user.get("url", f"https://www.zhihu.com/people/{user.get('hash_id', '')}") if user else "",
            "gender":      user.get("gender", ""),
        },
        "followers_total": (followers.get("data") or {}).get("total") or followers.get("total"),
        "followed_total":  (followed.get("data") or {}).get("total") or followed.get("total"),
        "moments": _normalize_moments(moments),
        # 原始返回保留供调试
        "_raw_info_keys": list(user.keys()) if user else [],
    })


def _normalize_moments(raw: dict) -> list:
    """兼容多种 moments 返回结构"""
    data = raw.get("data") if isinstance(raw, dict) else None
    if isinstance(data, dict):
        items = data.get("items") or data.get("moments") or data.get("list") or []
    elif isinstance(data, list):
        items = data
    else:
        items = raw.get("items", []) if isinstance(raw, dict) else []

    out = []
    for m in items[:5]:
        if not isinstance(m, dict):
            continue
        out.append({
            "title":   m.get("title") or m.get("question_title") or m.get("content_title") or "",
            "excerpt": (m.get("excerpt") or m.get("content") or m.get("summary") or "")[:160],
            "url":     m.get("url") or m.get("link") or "",
            "author":  (m.get("author") or {}).get("name") if isinstance(m.get("author"), dict) else m.get("author_name", ""),
            "time":    m.get("created_time") or m.get("publish_time") or m.get("updated_time") or "",
        })
    return out


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
