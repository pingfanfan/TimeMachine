// EdgeOne Edge Function · /api/health
export async function onRequest({ request, env }) {
  return new Response(JSON.stringify({
    ok: true,
    runtime: "edgeone",
    env_secret_set: !!env.ZHIHU_APP_SECRET,
    env_access_set: !!env.ZHIHU_ACCESS_SECRET,
    env_oauth_app_id: env.ZHIHU_OAUTH_APP_ID || null,
    env_oauth_key_set: !!env.ZHIHU_OAUTH_APP_KEY,
    env_oauth_redirect: env.ZHIHU_OAUTH_REDIRECT_URI || null,
    env_ring_id_set: !!env.ZHIHU_RING_ID,
    ts: Date.now(),
  }, null, 2), { headers: { "Content-Type": "application/json; charset=utf-8" } });
}
