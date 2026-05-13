// Cloudflare · /api/lab/probe-content
// 实验 endpoint:逐个 probe 知乎 OAuth 用户内容相关候选 path,看哪个返回 200。
// 任何用户只能用自己的 token 拿到自己的内容,无安全风险。
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

async function probeOne(path, token) {
  try {
    const u = new URL(OAUTH_BASE + path);
    u.searchParams.set("page", "0");
    u.searchParams.set("per_page", "2");
    const r = await fetch(u, { headers: { Authorization: `Bearer ${token}` } });
    const text = await r.text();
    return { status: r.status, preview: text.slice(0, 500) };
  } catch (e) {
    return { error: String(e) };
  }
}

export async function onRequest({ request }) {
  const cookies = parseCookies(request.headers.get("Cookie"));
  const token = cookies.zh_oauth_token;
  if (!token) {
    return new Response(JSON.stringify({ error: "not logged in" }), {
      status: 401, headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }

  // 先拿到 uid 给 /users/{uid}/... 候选用
  let uid = null;
  try {
    const ur = await fetch(`${OAUTH_BASE}/user`, { headers: { Authorization: `Bearer ${token}` } });
    if (ur.ok) {
      const u = await ur.json();
      uid = u?.uid;
    }
  } catch {}

  const CANDIDATES = [
    "/user/answers",
    "/user/articles",
    "/user/content",
    "/user/posts",
    "/user/activities",
    "/user/zvideos",
    "/user/columns",
    "/user/questions",
    "/me/answers",
    "/answers",
    `/users/${uid}/answers`,
    `/users/${uid}/articles`,
  ];

  const results = {};
  for (const p of CANDIDATES) {
    if (p.includes("undefined") || p.includes("null")) continue;
    results[p] = await probeOne(p, token);
  }

  return new Response(JSON.stringify({
    uid,
    summary: Object.entries(results)
      .map(([p, r]) => `${r.status === 200 ? "✓" : "✗"} ${p} → ${r.status || r.error}`)
      .join("\n"),
    results,
  }, null, 2), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}
