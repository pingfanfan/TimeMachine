# 《时光答》项目就绪度清单

> 本文件是 M1-M14 前置材料的可勾选追踪器。每一项凑齐一个,就在 `- [ ]` 前加 `x`。
> 全部 ✅ 之时 = 可以无缝启动开发,不会被外部依赖卡住。

**开赛时间:** 2026-05-12 13:00
**提报截止:** 2026-05-14 13:00
**今天:** 2026-04-23(距开赛 19 天)

---

## 🎫 Hackathon 报名(前提)

- [ ] **完成报名问卷**(5/11 截止前)
  - 飞书文档里的"报名链接🔗",添加官方助理
  - 耗时:5 分钟
- [ ] **加入官方社群 / 拉群对接**
  - 这是拿 M1-M3 官方 API 凭证的唯一渠道
- [ ] **确认组队**(1-5 人,推荐开发 + 产品/设计 + 创作者)
  - 耗时:按实际社交节奏,建议本周内搞定

---

## 🔑 知乎官方 API 凭证(必需,等官方)

### M1 · OAuth client_id / client_secret / redirect_uri

- [ ] 报名后联系官方助理索取
- **阻塞方:** Hackathon 报名 + 官方发放
- **预计到手时间:** 5/1 前后(可能到开赛前夕)
- **备注:** `redirect_uri` 需要先告知官方你的部署域名(`https://shiguangda.vercel.app/api/auth/callback` 或你自己的域名)

### M2 · ZHIHU_ACCESS_TOKEN(离线管线调 API 用)

- [ ] 询问官方:是发管理员级 token,还是要走 OAuth 流程用自己账号拿 token
- **阻塞方:** M1 就位
- **备注:** 这是离线管线 01/02/... 脚本调 `zhihu_search / hot_list / chat/completions` 的唯一凭证

### M3 · 专属圈子 ID(`ZHIHU_RING_ID`)

- [ ] 确认官方给的圈子是哪个(手册提到 `moltbook`)
- [ ] 确认圈子的发帖权限是开放给所有参赛队还是要申请
- **阻塞方:** 同上
- **备注:** 发帖到想法 / 圈子用的

---

## 🤖 LLM / Embedding 凭证(自办,现在就可以)

### M4 · DeepSeek API key(首选)

- [ ] 注册 https://platform.deepseek.com
- [ ] 充值 ¥50(跑完所有离线管线 + 运行时兜底绝对够)
- [ ] 拿到 API key 写入 `.env.local` → `DEEPSEEK_API_KEY`
- **耗时:** 10 分钟
- **备注:** deepseek-chat 模型便宜,输入 ¥2/M tokens,输出 ¥8/M tokens

### M5 · Claude Haiku 4.5 API key(质检 + fallback)

- [ ] 注册 https://console.anthropic.com
- [ ] 充值 $10
- [ ] 拿到 API key 写入 `.env.local` → `ANTHROPIC_API_KEY`
- **耗时:** 15 分钟(境外支付,准备好 Visa/Mastercard)
- **必要性:** 🟡 若 DeepSeek 单跑够用可省略

### M6 · OpenAI embedding API key

- [ ] 注册 https://platform.openai.com
- [ ] 充值 $5(embedding 极便宜,$0.02/M tokens)
- [ ] 拿到 API key 写入 `.env.local` → `OPENAI_API_KEY`
- **耗时:** 15 分钟
- **替代方案:** 本地跑 bge-m3(需要 ~4GB 内存 + 4GB 模型下载)。若不想付外币,可选这条路

---

## 🗄 数据库与部署(自办,现在就可以)

### M7 · Supabase 项目

- [ ] 注册 https://supabase.com(免费档够用)
- [ ] New Project → 记下:
  - `SUPABASE_URL`(形如 `https://xxx.supabase.co`)
  - `SUPABASE_ANON_KEY`(前端可用)
  - `SUPABASE_SERVICE_ROLE_KEY`(后端专用,⚠️ 绝不可进前端 bundle)
  - `SUPABASE_DB_URL`(Postgres 直连,离线脚本用)
- [ ] 应用迁移:等 Phase 0-T3 的 migration 文件写好后,在 SQL Editor 粘贴运行
- **耗时:** 15 分钟

### M8 · Vercel 账号 + GitHub 授权

- [ ] 注册 https://vercel.com(GitHub 登录即可)
- [ ] 准备一个 GitHub repo(先 private,路演前转 public 供评委看)
- [ ] Vercel 授权 GitHub,稍后直接 import
- **耗时:** 10 分钟

### M9 · 域名(可选)

- [ ] 是否要自定义域名?建议可选:
  - 有:去 Namesilo / 阿里云买一个,配 DNS 到 Vercel,`ZHIHU_REDIRECT_URI` 用自定义域
  - 无:用 `https://<project>.vercel.app`,同样告知官方作为 redirect_uri
- **耗时:** 30 分钟(若买)

---

## 📋 话题与内容(需要你思考/筛选)

### M10 · 30 话题候选池初稿

- [ ] 用 `data/topics.seed.json` 模板填 **至少 10 条优先级最高的**,剩余 20 条可以在离线管线第一轮跑完后补
- [ ] 每个话题的 `search_keywords` 要精心挑(2-4 个最能命中高赞老答的关键词)
- [ ] **筛选标准**:① 知乎上至少有 10 年讨论沉淀 ② 不同时代的主流答案有明显差异 ③ 能激起共鸣/争议
- **建议方向**(任选 30):
  - **职场类:** 程序员 35 岁、互联网加班、副业、体制内 vs 互联网、考公、辞职、跳槽、产品经理前景
  - **婚恋类:** 彩礼、婚姻价值、独身主义、丁克、异地恋、相亲
  - **消费/经济类:** 买房、消费降级、攒钱、贷款、买车、奢侈品
  - **教育类:** 考研、留学、鸡娃、双减后、专业选择、学区房
  - **社会类:** 生育、啃老、体面、润学、性别、原生家庭、抑郁
  - **科技/时代类:** AI 替代、ChatGPT 使用、大模型恐慌、短视频、元宇宙、币圈
  - **生活方式:** 健身、读书、躺平、断舍离、极简、户外
- **耗时:** 3-5 小时(仔细筛选)
- **建议时间:** 4/25-4/30,留出时间推进和调整

### M11 · 视觉设计稿 / 设计 tokens

- [ ] 色板(已在 spec 附录 C 敲定,可直接用或微调)
- [ ] 字体(思源宋体 + 思源黑体,公开 CDN 可用)
- [ ] **海报模板**:1080×1920 竖版,建议找设计师朋友帮出 1-2 个变体
- [ ] Figma / Sketch 文件链接(如有)
- **耗时:** 设计师朋友 4-8 小时,自己 1-2 天(可与开发并行,必要性中)
- **兜底方案:** 用 plan 里 P4-T1 给的默认 JSX 布局,素朴但在线

---

## 👥 账号与身份

### M12 · 知乎测试账号 × 2

- [ ] 账号 A:开发测试用(可以用你主账号,但注意 OAuth 授权后的发布痕迹)
- [ ] 账号 B:路演演示用(干净,只发"时光答"产出的海报 pin,给评委看的时候专业)
- [ ] 确保这两个账号都能正常使用 OAuth 登录
- **耗时:** 现有账号就够,新注册 20 分钟

### M13 · 刘看山 IP 素材

- [ ] 向官方要 IP 素材包(矢量图、表情包、配色指引)
- [ ] 海报角落可选放一个"by 刘看山推荐"印章
- **必要性:** 🟡 即使蹭不上也不影响核心流程,后补即可

---

## 💻 本机开发环境

### M14 · 工具链

- [ ] Node.js 20+:`node -v`
- [ ] pnpm:`npm i -g pnpm` 后 `pnpm -v`
- [ ] Python 3.11+:`python3 --version`
- [ ] uv(Python 包管理):`curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ ] Supabase CLI(可选):`brew install supabase/tap/supabase`
- [ ] Git:已有
- **耗时:** 15 分钟

---

## 🚦 就绪度总表

| # | 项目 | 今日状态 | 阻塞 | 建议完成日 |
|---|---|---|---|---|
| Hackathon 报名 | ⬜ | - | 本周(4/27) |
| 组队 | ⬜ | - | 本周 |
| M1 OAuth 凭证 | ⬜ | 报名 → 官方 | 5/5-5/11 |
| M2 ACCESS_TOKEN | ⬜ | M1 | 5/5-5/11 |
| M3 圈子 ID | ⬜ | M1 | 5/5-5/11 |
| M4 DeepSeek key | ⬜ | - | 本周 |
| M5 Anthropic key | ⬜ | - | 本周 |
| M6 OpenAI key | ⬜ | - | 本周 |
| M7 Supabase 项目 | ⬜ | - | 本周 |
| M8 Vercel + GitHub | ⬜ | - | 本周 |
| M9 域名(可选) | ⬜ | - | 无压力 |
| M10 话题池初稿 | ⬜ | - | 4/30 |
| M11 视觉稿 | ⬜ | - | 5/5 |
| M12 知乎账号 ×2 | ⬜ | - | 本周 |
| M13 刘看山素材 | ⬜ | M1 | 5/11 |
| M14 本机工具链 | ⬜ | - | 今天 |

---

## 🎯 真正开跑的触发条件(Green Light)

当以下条件**同时满足**,就可以调用 superpowers:subagent-driven-development 开始执行 plan:

1. ✅ M1/M2/M3(官方凭证)到手,**或** 有 mock 明确计划
2. ✅ M4/M6/M7/M8(自办凭证)全部就位
3. ✅ M10(话题池)至少有 10 条初稿
4. ✅ M14(本机工具链)完备
5. ✅ 已到 **2026-05-12 13:00**(官方开赛)

**在 Green Light 之前**:don't code yet. 只做凭证收集、话题筛选、视觉稿讨论,以及 spec/plan 的微调。

---

## 📞 遇到卡点怎么办

- **M1-M3 官方始终没发**:联系官方助理催;同时在 plan 里为所有 API 调用准备 mock 层(`MOCK_ZHIHU_API=1` 环境变量,所有 fetch 换成读本地 fixture)
- **DeepSeek / Anthropic 境外支付不方便**:用国内代理服务商(如 API2D、硅基流动),或全换 DeepSeek 单跑
- **Supabase 在国内访问慢**:换成 Neon / Railway / 本地 Postgres + ngrok
- **话题池想不满 30 个**:先 15 个高质量跑起来,剩余决赛前补

---

更新这份清单时,直接 `git commit -m "setup: <哪项就绪>"` 就行。赛前我们能清楚看到"还剩几个项目没齐"。
