// Cloudflare Pages Function · /api/auth/callback
// 第二步:用知乎 code 换 access_token,再拉用户信息,塞 cookie 后跳回首页
const OAUTH_BASE = "https://openapi.zhihu.com";

function htmlError(title, body, status = 400) {
  const html = `<!doctype html><meta charset=utf-8>
<style>body{font-family:system-ui;padding:40px;max-width:700px;margin:auto;background:#08101F;color:#EBE0C4;line-height:1.7}h1{color:#A8252F}pre{background:rgba(255,255,255,0.05);padding:16px;border-radius:4px;overflow:auto;font-size:12px}a{color:#F1B644}</style>
<h1>${title}</h1>${body}
<p><a href="/api/auth/zhihu">↩ 再试一次</a> · <a href="/">回到首页</a></p>`;
  return new Response(html, {
    status,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}

function cookieAttrs(maxAge, httpOnly = false) {
  const parts = [`Path=/`, `Max-Age=${maxAge}`, `Secure`, `SameSite=Lax`];
  if (httpOnly) parts.push("HttpOnly");
  return parts.join("; ");
}

export async function onRequest({ request, env }) {
  const url = new URL(request.url);
  // 知乎用非标准字段名 `authorization_code`(不是标准 OAuth 2.0 的 `code`)
  const code = url.searchParams.get("code") || url.searchParams.get("authorization_code");
  if (!code) {
    const err = url.searchParams.get("error") || "no_code";
    const errDesc = url.searchParams.get("error_description") || "(empty)";
    const allArgs = {};
    for (const [k, v] of url.searchParams.entries()) allArgs[k] = v;
    return htmlError(
      "OAuth 回调缺少 code",
      `<p>知乎跳回来时,URL 里没有 <code>?code=...</code>,只看到这些参数:</p>
<pre>${JSON.stringify(allArgs, null, 2)}</pre>
<p><strong>error:</strong> ${err}<br><strong>error_description:</strong> ${errDesc}</p>`,
    );
  }

  const appId = env.ZHIHU_OAUTH_APP_ID;
  const appKey = env.ZHIHU_OAUTH_APP_KEY;
  const redirectUri = env.ZHIHU_OAUTH_REDIRECT_URI;
  if (!appId || !appKey || !redirectUri) {
    return htmlError("OAuth 未配置", "<p>缺少 ZHIHU_OAUTH_APP_ID / APP_KEY / REDIRECT_URI 环境变量</p>", 503);
  }

  // 知乎 access_token 严格按文档字段
  const tokenBody = new URLSearchParams({
    app_id: appId,
    app_key: appKey,
    grant_type: "authorization_code",
    redirect_uri: redirectUri,
    code,
  });

  let tokenData;
  let tokenStatus;
  try {
    const tr = await fetch(`${OAUTH_BASE}/access_token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: tokenBody,
    });
    tokenStatus = tr.status;
    const text = await tr.text();
    try {
      tokenData = JSON.parse(text);
    } catch {
      return htmlError("Token endpoint 返回非 JSON", `<p>HTTP ${tr.status}</p><pre>${text.slice(0, 1000)}</pre>`, 500);
    }
  } catch (e) {
    return htmlError("Token 请求失败", `<pre>${String(e)}</pre>`, 500);
  }

  const accessToken = tokenData.access_token;
  if (!accessToken) {
    return htmlError(
      "Token 交换失败",
      `<p>HTTP ${tokenStatus}</p>
<p>code (前 8 字符): ${code.slice(0, 8)}…</p>
<p>token endpoint 返回:</p>
<pre>${JSON.stringify(tokenData, null, 2)}</pre>`,
      500,
    );
  }

  // 拉用户信息(知乎是扁平 JSON,无 data 包装)
  let user = {};
  try {
    const ur = await fetch(`${OAUTH_BASE}/user`, {
      headers: { "Authorization": `Bearer ${accessToken}` },
    });
    if (ur.ok) user = await ur.json();
  } catch (e) {
    console.log(`[user_info err] ${e}`);
  }

  const expiresIn = Number(tokenData.expires_in) || 3600;
  const headers = new Headers();
  headers.append("Location", "/?login=ok");
  headers.append("Set-Cookie", `zh_oauth_token=${accessToken}; ${cookieAttrs(expiresIn, true)}`);
  if (user.fullname) {
    const name = encodeURIComponent(user.fullname);
    const avatar = encodeURIComponent(user.avatar_path || "");
    const uid = encodeURIComponent(String(user.uid || ""));
    headers.append("Set-Cookie", `zh_user_name=${name}; ${cookieAttrs(3600)}`);
    headers.append("Set-Cookie", `zh_user_avatar=${avatar}; ${cookieAttrs(3600)}`);
    headers.append("Set-Cookie", `zh_user_uid=${uid}; ${cookieAttrs(3600)}`);
  }
  return new Response(null, { status: 302, headers });
}
