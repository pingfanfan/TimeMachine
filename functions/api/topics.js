// EdgeOne Edge Function · /api/topics
// 直接从静态 manifest 读 — 等价于 Vercel Flask 的 /api/topics

export async function onRequest({ request }) {
  const url = new URL(request.url);
  try {
    const r = await fetch(`${url.origin}/api-data/manifest.json`);
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
