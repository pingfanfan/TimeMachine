# 部署到 Vercel · 时光档案馆

> **为什么选 Vercel:** GitHub Pages 只能跑静态,我们有 Flask 后端(`/api/search`、OAuth 回调、`/api/publish/pin`)需要服务端。Vercel 自动 HTTPS + Python serverless functions + 从 GitHub 自动 deploy。

---

## 📁 项目结构(已就绪)

```
/
├── api/
│   ├── index.py         ← Flask serverless function 入口
│   ├── _lib/
│   │   └── zhihu_api.py
│   └── data/            ← 8 个话题 JSON + curation.json
├── public/
│   └── index.html       ← Vercel CDN 自动 serve
├── vercel.json          ← 路由配置
├── requirements.txt     ← Python 依赖
└── scripts/             ← 本地开发(不部署)
```

---

## 🚀 三步部署

### Step 1 · 推到 GitHub

```bash
cd /Users/pingfan/projects/Zhihu
gh repo create shiguang-dangan --public --source=. --remote=origin --push
# 或者手动创建 repo 然后:
# git remote add origin git@github.com:你的用户名/shiguang-dangan.git
# git branch -M main
# git push -u origin main
```

### Step 2 · 在 Vercel 导入项目

1. 打开 https://vercel.com → 用 GitHub 登录
2. **Add New → Project** → 选 `shiguang-dangan` repo
3. **Framework Preset**:选 **Other**(Vercel 会读 `vercel.json`)
4. **Root Directory**:`.`(默认)
5. **Build Command**:留空
6. **Output Directory**:留空
7. 点 **Environment Variables** 区域,添加:

| Key | Value | 说明 |
|---|---|---|
| `ZHIHU_APP_KEY` | `jzwa` | 知乎用户 token |
| `ZHIHU_APP_SECRET` | `etRR9OwDF6o0g1vBuiLFoG6u9oVLjl9R` | 社区 API 签名密钥 |
| `ZHIHU_ACCESS_SECRET` | `etRR9OwDF6o0g1vBuiLFoG6u9oVLjl9R` | 数据平台 Bearer token |
| `ZHIHU_RING_ID` | `2029619126742656657` | 黑客松脑洞补给站 |
| `ZHIHU_API_BASE` | `https://openapi.zhihu.com` | 社区 API base |
| `ZHIHU_DATA_API_BASE` | `https://developer.zhihu.com` | 数据平台 base |

> OAuth 三个变量先留空,等创建知乎项目后回来填:
> - `ZHIHU_OAUTH_APP_ID`
> - `ZHIHU_OAUTH_APP_KEY`
> - `ZHIHU_OAUTH_REDIRECT_URI`

8. 点 **Deploy** → 等约 1-2 分钟

### Step 3 · 部署完成后验证

Vercel 会给你一个 URL,比如:`https://shiguang-dangan-xxx.vercel.app`

测试 4 个关键端点:
```bash
URL=https://shiguang-dangan.vercel.app  # 改成你的

# 1. 首页
curl -I "$URL/" | head -3

# 2. 健康检查
curl "$URL/api/health" | jq

# 3. 精选话题列表
curl "$URL/api/topics" | jq '.topics | length'   # 应 = 8

# 4. 自定义搜索
curl -G "$URL/api/search" --data-urlencode 'q=共享单车' | jq '.year_count'
```

---

## 🔐 部署后开 OAuth

部署成功后,你有了 https 域名。这时候可以去黑客松广场拿 OAuth 凭证。

1. **黑客松广场** → 创建/编辑项目
2. **作品链接** 填:`https://shiguang-dangan.vercel.app`(你的实际域名)
3. **知乎登录回调地址** 填:`https://shiguang-dangan.vercel.app/api/auth/callback`(末尾不要斜杠!)
4. 提交后系统给你 **App_ID + App_Key**(只显示一次,截图保存)
5. 回 Vercel → 项目 Settings → Environment Variables 加 3 个:
   - `ZHIHU_OAUTH_APP_ID` = `<App_ID>`
   - `ZHIHU_OAUTH_APP_KEY` = `<App_Key>`
   - `ZHIHU_OAUTH_REDIRECT_URI` = `https://shiguang-dangan.vercel.app/api/auth/callback`
6. Settings → Deployments → 最新部署 → "..." → **Redeploy** 让新 env 生效
7. 访问站点 → 点右上"登录知乎" → 应跳到知乎授权页

---

## 🧪 本地测试 Vercel 模式(可选)

```bash
# 装 Vercel CLI
npm i -g vercel

# 在项目根目录跑
cd /Users/pingfan/projects/Zhihu
vercel dev

# 或者直接 vercel 部署一次预览
vercel
```

---

## 🆘 常见坑

| 现象 | 解决 |
|---|---|
| Deploy 失败:`No Python found` | `requirements.txt` 必须在项目根目录,确认存在 |
| `/api/search` 返回 500 + `data dir missing` | 确认 `api/data/` 跟着部署了。每次更新数据后跑 `python demo/render_html.py` 自动同步 |
| OAuth 回调失败:`redirect_uri_mismatch` | 知乎平台填的和环境变量必须**一字不差**(含协议、域名、路径、不能有末尾斜杠) |
| Cookie 不工作 | 已加 `secure=True, samesite='Lax'`,Vercel 是 https 自动满足 |
| Function 超 10s 超时 | Vercel 免费版 Function 默认 10s,搜索 API 调用知乎 API 偶尔慢。可在 vercel.json 加 `maxDuration: 30`(Pro 才支持) |
| `api/` 包大小超 50MB | 当前 ~1.3MB,远低于上限,无需担心 |

---

## 🔄 后续更新流程

每次改了 `data/demo/*.json` 或 HTML 后:
```bash
cd /Users/pingfan/projects/Zhihu
# 1. 重渲染(自动同步到 public/ + api/data/)
cd scripts && python demo/render_html.py && cd ..

# 2. 提交并推送
git add -A
git commit -m "update: ..."
git push

# Vercel 会自动重新部署(约 30 秒)
```
