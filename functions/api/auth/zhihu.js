// EdgeOne · /api/auth/zhihu - 同上,提示用户去 Vercel 域名
export async function onRequest() {
  const html = `<!doctype html><meta charset=utf-8>
<style>body{font-family:system-ui;padding:60px;max-width:560px;margin:auto;background:#08101F;color:#EBE0C4;line-height:1.7}h1{color:#A8252F}a{color:#F1B644}</style>
<h1>OAuth 暂未在 EdgeOne 国内域名启用</h1>
<p>知乎登录功能正在迁移中。当前 EdgeOne 域名只提供主体功能(浏览档案/搜索/热榜)。</p>
<p>如需用知乎账号登录,请访问海外备份域名(需要稳定网络):</p>
<p><a href="https://time-machine-six-sigma.vercel.app/api/auth/zhihu">→ 跳转 Vercel 备份域</a></p>
<p style="margin-top:32px;font-size:13px;opacity:0.6">本馆主体功能不依赖登录,可<a href="/">返回首页</a>继续浏览。</p>`;
  return new Response(html, {
    status: 503,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
