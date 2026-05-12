// Cloudflare Pages Function · /api/logout
export async function onRequest({ request }) {
  if (request.method !== "POST" && request.method !== "GET") {
    return new Response("Method Not Allowed", { status: 405 });
  }
  const headers = new Headers({ "Content-Type": "application/json; charset=utf-8" });
  const expire = "Path=/; Max-Age=0; Secure; SameSite=Lax";
  headers.append("Set-Cookie", `zh_oauth_token=; ${expire}; HttpOnly`);
  headers.append("Set-Cookie", `zh_user_name=; ${expire}`);
  headers.append("Set-Cookie", `zh_user_avatar=; ${expire}`);
  headers.append("Set-Cookie", `zh_user_uid=; ${expire}`);
  return new Response(JSON.stringify({ ok: true }), { headers });
}
