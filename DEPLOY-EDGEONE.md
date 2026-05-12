# 部署到腾讯云 EdgeOne Pages · 国内可访问

> 解决 `*.vercel.app` 在中国大陆被 GFW 屏蔽的问题。
> EdgeOne Pages 是腾讯云的 Vercel-like 平台,3200+ 国内 CDN 节点,免备案。

---

## 📦 项目结构(已就绪)

```
TimeMachine/
├── public/                           ← EdgeOne CDN 自动 serve 静态文件
│   ├── index.html
│   └── api-data/                     ← 14 个话题 JSON + manifest
│       ├── manifest.json
│       ├── zhihu-itself.json
│       └── ...
├── functions/                        ← Edge Functions(JS)
│   └── api/
│       ├── health.js                 → GET  /api/health
│       ├── topics.js                 → GET  /api/topics(读 manifest)
│       ├── search.js                 → GET  /api/search?q=...
│       ├── hotlist.js                → GET  /api/hotlist
│       ├── me.js                     → GET  /api/me(简化版)
│       ├── publish/pin.js            → POST /api/publish/pin(HMAC 签名)
│       └── auth/zhihu.js             → GET  /api/auth/zhihu(503 + 提示)
├── edgeone.json                      ← 项目配置
└── vercel.json                       ← Vercel 配置(保留作 backup)
```

---

## 🚀 三步部署 EdgeOne Pages

### 1️⃣ 注册 + 登录 EdgeOne 控制台

打开 **https://edgeone.cloud.tencent.com/pages**(腾讯云中国站)。

- 用**微信** / 腾讯云账号登录
- 或者用 GitHub OAuth(中国站可能不支持,用 QQ / 微信)

### 2️⃣ 新建项目 · 从 GitHub 导入

1. 点 **「Pages → 新建项目 → 从 Git 导入」**
2. 授权 GitHub,选 repo `pingfanfan/TimeMachine`
3. **构建配置**:
   - **Framework**:Other / Static
   - **Build Command**:留空
   - **Output Directory**:`public`
   - **Install Command**:留空
4. **环境变量**(点击「环境变量」展开,加 5 个):

```
ZHIHU_APP_KEY            jzwa
ZHIHU_APP_SECRET         etRR9OwDF6o0g1vBuiLFoG6u9oVLjl9R
ZHIHU_ACCESS_SECRET      etRR9OwDF6o0g1vBuiLFoG6u9oVLjl9R
ZHIHU_RING_ID            2029619126742656657
```

> OAuth 三个变量(ZHIHU_OAUTH_*)**暂不需要** — EdgeOne 版本不支持完整 OAuth,提示用户去 Vercel 备份域。

5. 点 **「部署」** → 1-2 分钟后拿到国内可访问的域名,通常是:
   `https://time-machine-xxx.edgeone.app` 或 `*.eopages.com`

### 3️⃣ 部署后验证

```bash
URL="https://你的-edgeone-url"

# 1. 健康检查
curl "$URL/api/health"

# 2. 话题列表
curl "$URL/api/topics" | head -c 500

# 3. 自定义搜索(URL-encoded 中文)
curl "$URL/api/search?q=$(python3 -c 'import urllib.parse; print(urllib.parse.quote(\"考研\"))')" | head -c 300

# 4. 热榜
curl "$URL/api/hotlist" | head -c 500

# 5. 主页(应返回 200 + HTML)
curl -I "$URL/"
```

如果都 200 + 有数据,**国内域名就 ready 了!** 把这个 URL 用于:
- 知乎黑客松项目提报(作品链接)
- 想法 / 朋友圈分享
- 评委评测

---

## 🔄 双部署策略

| 域名 | 部署 | 用途 |
|---|---|---|
| **EdgeOne** `*.edgeone.app` | 主域(国内可达) | 评委 / 国内分享 / 路演 |
| **Vercel** `www.tmark.top` | 备份(海外可达 + OAuth 完整) | 海外开发 / OAuth 测试 |

---

## ⚠️ EdgeOne vs Vercel 功能差异

| 功能 | Vercel | EdgeOne |
|---|---|---|
| 主页 / 浏览档案 | ✅ | ✅ |
| 自定义搜索 | ✅ | ✅ |
| 今日热榜直达 | ✅ | ✅ |
| 一键发布想法 | ✅ | ✅ |
| 知乎 OAuth 登录 | ✅ | ⚠️ 503 提示用户去 Vercel |
| 「我的视角」 | ✅ | ❌ 简化版 |
| **国内访问** | ❌ 被墙 | ✅ |

OAuth 不迁的理由:**Demo 核心功能不依赖登录**,90% 体验都能用。完整 OAuth 在 Vercel 备份域可用,海外用户能登。

---

## 🛠 后续 OAuth 迁移(可选,P2)

如果想把 OAuth 也迁到 EdgeOne,需要再写 5 个 functions:
- `functions/api/auth/callback.js` — token 交换
- `functions/api/me/profile.js` — 拉用户画像
- `functions/api/logout.js` — 清 cookie
- 完整 `functions/api/auth/zhihu.js` — 取代当前的 503 占位

这部分工作量 1-2 小时,可在 5/14 提报前补完。

---

## 📍 修改后端策略要点

EdgeOne Edge Functions 是 **V8 isolate 运行时**(类似 Cloudflare Workers),不是 Node.js:

- ✅ 标准 Web API:`fetch`、`Request`、`Response`、`crypto.subtle`
- ❌ Node.js 特有 API:`fs`、`process`、`require()`
- ❌ NPM 包(大部分):必须用 ESM + Web-compatible

我们的 functions 全部用 Web API 实现:
- HMAC 签名 → `crypto.subtle.importKey + sign`
- HTTP 请求 → `fetch`
- 数据读取 → `fetch` 同站静态资源

---

## 🌐 拿到 EdgeOne 域名后

更新 share-wechat.md 的链接:
```
之前:https://www.tmark.top
之后:https://你的-edgeone-url
```

更新 share card 的 footer:
```
之前:www.tmark.top
之后:你的-edgeone-url
```

让中国大陆用户也能完整体验产品 ✅
