// EdgeOne Edge Function · /api/topics
// 直接从静态 manifest 读 — 等价于 Vercel Flask 的 /api/topics

export async function onRequest({ request, env }) {
  const url = new URL(request.url);
  try {
    // Workers+Assets 模式:用 env.ASSETS 直拿静态资源,避免循环走回 Worker
    const assetReq = new Request(`${url.origin}/api-data/manifest.json`);
    const r = env?.ASSETS ? await env.ASSETS.fetch(assetReq) : await fetch(assetReq);
    if (!r.ok) return new Response(JSON.stringify({ error: "manifest missing" }), {
      status: 500, headers: { "Content-Type": "application/json; charset=utf-8" }
    });
    const manifest = await r.json();
    return new Response(JSON.stringify(manifest), {
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }
}
