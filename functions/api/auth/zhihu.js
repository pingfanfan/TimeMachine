// Cloudflare Pages Function · /api/auth/zhihu
// 第一步:跳转知乎授权页
export async function onRequest({ env }) {
  const appId = env.ZHIHU_OAUTH_APP_ID;
  const redirectUri = env.ZHIHU_OAUTH_REDIRECT_URI;
  if (!appId || !redirectUri) {
    return new Response(JSON.stringify({
      error: "OAuth not configured",
      message: "管理员需要在 Cloudflare 环境变量配置 ZHIHU_OAUTH_APP_ID / APP_KEY / REDIRECT_URI",
    }), {
      status: 503,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  }
  const params = new URLSearchParams({
    app_id: appId,
    redirect_uri: redirectUri,
    response_type: "code",
  });
  return Response.redirect(`https://openapi.zhihu.com/authorize?${params}`, 302);
}
