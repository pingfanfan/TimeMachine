// EdgeOne Edge Function · /api/health
export async function onRequest({ request, env }) {
  return new Response(JSON.stringify({
    ok: true,
    runtime: "edgeone",
    env_secret_set: !!env.ZHIHU_APP_SECRET,
    env_access_set: !!env.ZHIHU_ACCESS_SECRET,
    ts: Date.now(),
  }, null, 2), { headers: { "Content-Type": "application/json; charset=utf-8" } });
}
