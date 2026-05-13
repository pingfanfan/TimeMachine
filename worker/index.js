// Cloudflare Worker entry · 路由 /api/* 到对应 handler,其余 fallback 到静态资源
// 复用 functions/api/*.js 的 onRequest(Pages Functions 签名兼容)
// Build: 2026-05-13 — 触发 redeploy 以让新加的 env vars 生效

import { onRequest as health } from "../functions/api/health.js";
import { onRequest as topics } from "../functions/api/topics.js";
import { onRequest as hotlist } from "../functions/api/hotlist.js";
import { onRequest as search } from "../functions/api/search.js";
import { onRequest as me } from "../functions/api/me.js";
import { onRequest as meProfile } from "../functions/api/me/profile.js";
import { onRequest as logout } from "../functions/api/logout.js";
import { onRequest as authZhihu } from "../functions/api/auth/zhihu.js";
import { onRequest as authCallback } from "../functions/api/auth/callback.js";
import { onRequest as publishPin } from "../functions/api/publish/pin.js";

const ROUTES = {
  "/api/health": health,
  "/api/topics": topics,
  "/api/hotlist": hotlist,
  "/api/search": search,
  "/api/me": me,
  "/api/me/profile": meProfile,
  "/api/logout": logout,
  "/api/auth/zhihu": authZhihu,
  "/api/auth/callback": authCallback,
  "/api/publish/pin": publishPin,
};

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const handler = ROUTES[url.pathname];
    if (handler) {
      try {
        return await handler({
          request,
          env,
          params: {},
          waitUntil: (p) => ctx.waitUntil(p),
        });
      } catch (e) {
        return new Response(
          JSON.stringify({ error: String(e), stack: e.stack }),
          { status: 500, headers: { "Content-Type": "application/json; charset=utf-8" } },
        );
      }
    }
    // 其余路径 fallback 到 public/ 静态资源
    return env.ASSETS.fetch(request);
  },
};
