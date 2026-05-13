// Cloudflare Pages Function · /api/me/profile
// 登录用户完整画像 — 调 4 个知乎 OAuth API
const OAUTH_BASE = "https://openapi.zhihu.com";

function parseCookies(header) {
  const out = {};
  if (!header) return out;
  for (const pair of header.split(/;\s*/)) {
    const i = pair.indexOf("=");
    if (i < 0) continue;
    out[pair.slice(0, i).trim()] = decodeURIComponent(pair.slice(i + 1).trim());
  }
  return out;
}

async function oauthGet(path, token, params, debugStore) {
  try {
    const url = new URL(OAUTH_BASE + path);
    if (params) for (const [k, v] of Object.entries(params)) url.searchParams.set(k, v);
    const r = await fetch(url, {
      headers: { "Authorization": `Bearer ${token}` },
    });
    const text = await r.text();
    if (debugStore) debugStore[path] = { status: r.status, preview: text.slice(0, 400) };
    if (r.ok) {
      try { return JSON.parse(text); } catch { return null; }
    }
  } catch (e) {
    if (debugStore) debugStore[path] = { error: String(e) };
  }
  return null;
}

// 知乎 OAuth /user/moments 结构:
//   { data: [ { action_text, action_time, target: {title, excerpt, author:{name}}, actor:{name} } ] }
function normalizeMoments(raw) {
  const items = Array.isArray(raw?.data) ? raw.data : [];
  const out = [];
  for (const m of items.slice(0, 8)) {
    if (!m || typeof m !== "object") continue;
    const target = m.target || {};
    const targetAuthor = target.author?.name || target.author_name || "";
    out.push({
      actor: m.actor?.name || "",                       // 你关注的谁
      action: m.action_text || "",                       // 做了什么(赞同/关注/回答)
      title: target.title || "",
      excerpt: (target.excerpt || "").slice(0, 160),
      target_author: targetAuthor,
      url: target.url || "",
      time: m.action_time || 0,
    });
  }
  return out;
}

// /user/followers 和 /user/followed 结构:
//   { data: [ {uid, fullname, headline, avatar_path, hash_id, ...} ] }
function normalizePeopleList(raw) {
  const items = Array.isArray(raw?.data) ? raw.data : [];
  return items.slice(0, 5).map((p) => ({
    uid: p.uid,
    fullname: p.fullname || "",
    headline: (p.headline || "").slice(0, 80),
    avatar: p.avatar_path || "",
    url: p.uid ? `https://www.zhihu.com/people/${p.uid}` : "",
  }));
}

export async function onRequest({ request }) {
  const cookies = parseCookies(request.headers.get("Cookie"));
  const token = cookies.zh_oauth_token;
  if (!token) {
    return new Response(JSON.stringify({ error: "not logged in" }), {
      status: 401,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }

  const url = new URL(request.url);
  const debug = url.searchParams.get("debug") === "1";
  const dbg = debug ? {} : null;

  const user = (await oauthGet("/user", token, null, dbg)) || {};

  // 正确路径(2026-05-13 probe 出来的):/user/followers, /user/followed, /user/moments
  // 拉前 5 条够 demo,不带 total(知乎 OAuth response 不返回 total)
  const followers = (await oauthGet("/user/followers", token, { page: 0, per_page: 5 }, dbg)) || {};
  const followed = (await oauthGet("/user/followed", token, { page: 0, per_page: 5 }, dbg)) || {};
  const moments = (await oauthGet("/user/moments", token, { page: 0, per_page: 8 }, dbg)) || {};

  const uid = user.uid;
  const body = {
    user: {
      uid,
      fullname: user.fullname || "",
      headline: user.headline || "",
      description: user.description || "",
      avatar: user.avatar_path || "",
      url: uid ? `https://www.zhihu.com/people/${uid}` : "https://www.zhihu.com",
      gender: user.gender || "",
      email: user.email || "",
    },
    // 知乎 OAuth 不返回 total,降级展示 sample list + 已加载的数量
    followers_sample: normalizePeopleList(followers),
    followed_sample: normalizePeopleList(followed),
    followers_loaded: (Array.isArray(followers.data) ? followers.data.length : 0),
    followed_loaded: (Array.isArray(followed.data) ? followed.data.length : 0),
    moments: normalizeMoments(moments),
    _raw_user_keys: Object.keys(user),
    _debug: dbg,
  };

  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}
