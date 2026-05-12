// Cloudflare Pages Function · /api/me
// 读 cookie 返回登录状态(简化版,用于顶部 nav 显示头像)
function parseCookies(header) {
  const out = {};
  if (!header) return out;
  for (const pair of header.split(/;\s*/)) {
    const i = pair.indexOf("=");
    if (i < 0) continue;
    const k = pair.slice(0, i).trim();
    const v = pair.slice(i + 1).trim();
    if (k) out[k] = decodeURIComponent(v);
  }
  return out;
}

export async function onRequest({ request }) {
  const cookies = parseCookies(request.headers.get("Cookie"));
  const token = cookies.zh_oauth_token;
  if (!token) {
    return new Response(JSON.stringify({ logged_in: false }), {
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }
  return new Response(JSON.stringify({
    logged_in: true,
    name: cookies.zh_user_name || "",
    avatar: cookies.zh_user_avatar || "",
  }), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}
