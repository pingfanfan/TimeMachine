// EdgeOne Edge Function · POST /api/publish/pin
// 用 HMAC-SHA256 签名调知乎社区 API 发布想法

async function hmacSign(appKey, appSecret, ts, logId, extra = "") {
  const signStr = `app_key:${appKey}|ts:${ts}|logid:${logId}|extra_info:${extra}`;
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw", enc.encode(appSecret),
    { name: "HMAC", hash: "SHA-256" },
    false, ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(signStr));
  // base64 encode
  const bytes = new Uint8Array(sig);
  let str = "";
  for (const b of bytes) str += String.fromCharCode(b);
  return btoa(str);
}

function randId() {
  return "tma-" + Array.from(crypto.getRandomValues(new Uint8Array(8)))
    .map(b => b.toString(16).padStart(2, "0")).join("");
}

export async function onRequest({ request, env }) {
  if (request.method !== "POST") {
    return new Response(JSON.stringify({ error: "method not allowed" }), {
      status: 405, headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }

  const appKey = env.ZHIHU_APP_KEY;
  const appSecret = env.ZHIHU_APP_SECRET;
  const ringId = env.ZHIHU_RING_ID || "2029619126742656657";
  if (!appKey || !appSecret) {
    return new Response(JSON.stringify({ error: "missing APP_KEY / APP_SECRET" }), {
      status: 500, headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }

  let body;
  try {
    body = await request.json();
  } catch (e) {
    return new Response(JSON.stringify({ error: "invalid json" }), {
      status: 400, headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }
  const content = (body.content || "").trim();
  if (!content) {
    return new Response(JSON.stringify({ error: "missing content" }), {
      status: 400, headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }

  const ts = String(Math.floor(Date.now() / 1000));
  const logId = randId();
  const sign = await hmacSign(appKey, appSecret, ts, logId);

  const payload = { content, ring_id: ringId };
  if (body.title) payload.title = body.title;
  if (body.image_urls) payload.image_urls = body.image_urls;

  try {
    const r = await fetch("https://openapi.zhihu.com/openapi/publish/pin", {
      method: "POST",
      headers: {
        "X-App-Key": appKey,
        "X-Timestamp": ts,
        "X-Log-Id": logId,
        "X-Sign": sign,
        "X-Extra-Info": "",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const data = await r.json();
    return new Response(JSON.stringify(data), {
      status: r.status,
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }
}
