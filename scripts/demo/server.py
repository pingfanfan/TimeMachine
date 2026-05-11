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


# ───────── 知乎热榜 · 只保留有时光机价值的话题 ─────────

# evergreen 长期议题词典:命中即认为有「跨年代讨论沉淀」
# 顺序很重要(更具体的关键词排前面,先匹配)
TIME_TRAVEL_CONCEPTS = [
    # 教育(长期热议)
    ("学区房", "学区房"),
    ("鸡娃", "鸡娃焦虑"),
    ("双减", "双减政策"),
    ("教培", "教培行业"),
    ("选考", "新高考选考"),
    ("文科生", "文科生 弃理"),
    ("理科生", "选考物理"),
    ("高考", "高考"),
    ("考研", "考研"),
    ("学历贬值", "学历贬值"),
    ("内卷", "教育内卷"),
    # 职场
    ("35岁", "程序员 35 岁"),
    ("35 岁", "35 岁危机"),
    ("中年危机", "中年危机"),
    ("996", "996"),
    ("加班文化", "加班文化"),
    ("副业", "副业"),
    ("躺平", "躺平"),
    ("润学", "润学 出国"),
    ("裁员", "互联网裁员"),
    ("大厂", "互联网大厂"),
    # 婚恋 / 家庭
    ("彩礼", "彩礼"),
    ("天价彩礼", "天价彩礼"),
    ("丁克", "丁克"),
    ("独居", "独居"),
    ("离婚冷静期", "离婚冷静期"),
    ("结婚率", "结婚率下降"),
    ("不婚", "不婚主义"),
    ("生育率", "生育率"),
    ("三胎", "三胎政策"),
    ("二胎", "二胎政策"),
    # 经济 / 房产
    ("买房", "买房"),
    ("房价", "房价"),
    ("公积金", "公积金"),
    ("消费降级", "消费降级"),
    # 科技 / AI
    ("ChatGPT", "ChatGPT"),
    ("大模型", "大模型"),
    ("AI Agent", "AI Agent"),
    ("AI 替代", "AI 替代工作"),
    ("AI换脸", "AI 换脸诈骗"),
    ("AI 换脸", "AI 换脸诈骗"),
    ("自动驾驶", "自动驾驶"),
    ("新能源车", "新能源汽车"),
    ("新能源", "新能源"),
    ("老头乐", "老头乐 低速电动车"),
    ("具身智能", "具身智能"),
    ("芯片", "芯片 卡脖子"),
    ("半导体", "半导体 国产"),
    # 商业 / 金融
    ("共享单车", "共享单车"),
    ("P2P", "P2P 暴雷"),
    ("元宇宙", "元宇宙"),
    ("区块链", "区块链"),
    ("比特币", "比特币"),
    ("跨境电商", "跨境电商"),
    ("直播带货", "直播带货"),
    ("短视频", "短视频"),
    ("出海", "中国企业 出海"),
    # 社会
    ("电信诈骗", "电信诈骗"),
    ("反诈", "反电信诈骗"),
    ("网瘾", "网瘾 戒治"),
    ("家暴", "家暴"),
    ("延迟退休", "延迟退休"),
    ("养老", "养老"),
    ("种植", "种植 农业"),
    # 互联网平台
    ("抖音", "抖音"),
    ("B 站", "B 站"),
    ("微信", "微信生态"),
    ("知乎", "知乎"),
    ("小红书", "小红书"),
]


def extract_timetravel_query(title: str) -> tuple[str, str] | None:
    """从热榜标题里提取一个有时光机价值的关键词,失败返回 None"""
    if not title:
        return None
    for keyword, query in TIME_TRAVEL_CONCEPTS:
        if keyword.lower() in title.lower():
            return (keyword, query)
    return None


@app.get("/api/hotlist")
def hotlist():
    """拉知乎当前热榜 + 过滤出有时光机价值的话题,提取核心关键词"""
    from _lib.zhihu_api import hot_list as fetch_hot
    try:
        r = fetch_hot(limit=30)  # 拉多一点,以便过滤后还有足够数量
        items = r.get("Data", {}).get("Items", [])
        out = []
        for it in items:
            title = (it.get("Title") or "").strip()
            if not title:
                continue
            extracted = extract_timetravel_query(title)
            if not extracted:
                continue  # 没匹配上长期议题词典 = 没时光机价值,跳过
            matched_keyword, query = extracted
            out.append({
                "title":   title,
                "url":     it.get("Url", ""),
                "summary": (it.get("Summary") or "")[:120],
                "matched_keyword": matched_keyword,
                "time_travel_query": query,
            })
            if len(out) >= 8:
                break
        return jsonify({"items": out, "total_scanned": len(items)})
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

    # 拉用户信息(知乎 user_info 是扁平 JSON,无 data 包装)
    user = {}
    try:
        ur = httpx.get(
            f"{OAUTH_BASE}/user",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30,
        )
        if ur.status_code == 200:
            user = ur.json() or {}
            print(f"[user fetched] keys={list(user.keys())}, fullname={user.get('fullname')!r}")
    except Exception as e:
        print(f"[user_info err] {e}")

    resp = make_response(redirect("/?login=ok"))
    resp.set_cookie("zh_oauth_token", access_token, httponly=True, max_age=data.get("expires_in", 3600), secure=True, samesite="Lax")
    if user.get("fullname"):
        resp.set_cookie("zh_user_name", user["fullname"], max_age=3600, secure=True, samesite="Lax")
        resp.set_cookie("zh_user_avatar", user.get("avatar_path", ""), max_age=3600, secure=True, samesite="Lax")
        resp.set_cookie("zh_user_uid", str(user.get("uid", "")), max_age=3600, secure=True, samesite="Lax")
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
