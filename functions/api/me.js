// EdgeOne · /api/me - 简化版本(不支持完整 OAuth,evely返回未登录)
// 完整 OAuth 流程暂留 Vercel 备份
export async function onRequest() {
  return new Response(JSON.stringify({
    logged_in: false,
    note: "OAuth 暂未在 EdgeOne 启用,如需登录请访问 Vercel 备份域名(海外可达)",
  }), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}
