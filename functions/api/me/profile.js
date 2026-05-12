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

function normalizeMoments(raw) {
  if (!raw || typeof raw !== "object") return [];
  let items = [];
  const data = raw.data;
  if (data && typeof data === "object" && !Array.isArray(data)) {
    items = data.items || data.moments || data.list || [];
  } else if (Array.isArray(data)) {
    items = data;
  } else {
    items = raw.items || [];
  }
  const out = [];
  for (const m of items.slice(0, 5)) {
    if (!m || typeof m !== "object") continue;
    const author = m.author && typeof m.author === "object" ? m.author.name : (m.author_name || "");
    out.push({
      title: m.title || m.question_title || m.content_title || "",
      excerpt: (m.excerpt || m.content || m.summary || "").slice(0, 160),
      url: m.url || m.link || "",
      author,
      time: m.created_time || m.publish_time || m.updated_time || "",
    });
  }
  return out;
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
  const followers = (await oauthGet("/openapi/user_followers", token, { page: 0, per_page: 1 }, dbg)) || {};
  const followed = (await oauthGet("/openapi/user_followed", token, { page: 0, per_page: 1 }, dbg)) || {};
  const moments = (await oauthGet("/openapi/user_moments", token, { page: 0, per_page: 5 }, dbg)) || {};

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
    followers_total: (followers.data && followers.data.total) || followers.total,
    followed_total: (followed.data && followed.data.total) || followed.total,
    moments: normalizeMoments(moments),
    _raw_user_keys: Object.keys(user),
    _debug: dbg,
  };

  return new Response(JSON.stringify(body), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}
