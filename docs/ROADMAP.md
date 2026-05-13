# 时光档案馆 · Future Plans

记录已构想但未实施的产品方向,便于将来回顾、重启、或在外部条件变化时快速捡起。

---

## #1 · 用户历史回答 × 时代大事 (Personal Timeline Crossing)

> **状态**:🟡 放弃 · 等知乎 OAuth 开放用户内容 API 后重启
> **首次提出**:2026-05-13 by 平凡
> **关闭于**:2026-05-13(同日,probe 后判定不可行)

### 产品意图

让登录用户看到:**「你 2018 年那篇关于 996 的回答,正好写在 996.ICU 运动爆发后 3 个月」**。

把产品从"看别人的历史"升级到"看你自己在大时代里的位置" —— 用户回头看自己 5 年/10 年前的回答,会有强烈的"我也参与过历史"的情感冲击。同时让登录态有不可替代的产品价值。

### 为什么没做(2026-05-13 探索证据)

**自动 server-side 拉用户回答的所有路径都被堵**:

| 路径 | 结果 | 证据 commit |
|---|---|---|
| **OAuth API**(12 个候选 path:`/user/answers`、`/user/articles`、`/me/answers`、`/users/{uid}/answers` 等) | **全 404** — nginx 层 HTML 404,这些 path 在 `openapi.zhihu.com` 根本不存在 | `3d9efb9` (probe,已 revert at `abc6df0`) |
| **Web API v4 列表**(`zhihu.com/api/v4/members/{url_token}/answers`) | **40352 反爬** — "系统监测到您的网络环境存在异常" | 同上日 |
| **HTML 个人主页**(`zhihu.com/people/{ut}/answers`) | **403** | 同上日 |
| **profile 加 `include=answer_count`** | **40352 反爬** | 简单 profile(name/headline)能拿,但任何统计字段触发反爬 |
| **反查策略**:zhihu_search 14 档案关键词 + filter `AuthorName==用户名` | **0 hit** — 普通作者(就算 2K+ followers)挤不进 zhihu_search 每个话题 top 10 | 同上日 |

**根本原因**:这不是工程问题,是知乎产品策略 —— OAuth 只开放"看别人"权限(followers / followed / moments),不开放"拿自己创作产权"。

### 重启触发条件(满足任一即可重新评估)

1. ⏰ **知乎开放 `/user/answers` 或类似 OAuth API**(关注知乎黑客松官方群、`developer.zhihu.com` 更新)
2. ⏰ **知乎数据平台 `zhihu_search` 加 `AuthorId` filter 参数**
3. ⏰ **拿到知乎内部数据合作**(决赛拿名次后向官方申请数据接入)
4. ⏰ **改部署架构**:浏览器扩展 / 用户主动跑 JS 上传内容(非 server-side 抓)

### 重启路径建议(如果未来要做)

**Phase 0 · 重新 probe**(20 分钟)
逐个验证 `docs/ROADMAP.md` 里列的失败路径是否还是 404 / 反爬。如果某条变绿了,直接进 Phase 1。

**Phase 1 · MVP 后端**(1.5 小时)
- 新建 `functions/api/me/history.js`
- 拉用户最近 N=20 条回答(用上面 work 的 endpoint)
- 提取 `created_time` → 年份
- 读 14 档案的 `event_anchors`(`data/demo/curation.json` + `public/api-data/*.json`)
- 年份硬匹配,返回 `[{answer:{title,url,year}, anchors:[{topic, event_title}]}]`

**Phase 2 · MVP 前端**(1 小时)
- 在 `public/index.html` 「我的视角」模态框 `mp-moments` 下方加 `mp-history` section
- 标题:`📜 你的回答 × 那一年`
- 列表:`{年}「{你的回答标题}」 ↔ 那一年:{档案 1 事件}、{档案 2 事件}`
- 点击跳真实知乎 URL

**Phase 3 · AI 升级**(可选,1.5 小时)
- zhida-thinking 调用 1 次:把用户回答内容 + event_anchors 喂进去,生成一段叙事:
  > "你在 2018 年写下《XXX》时,世界正经历 996.ICU 运动爆发、ofo 押金 1500 万人讨债、彩礼立法启动。你的这一篇,正好站在三个浪潮的交叉点上。"
- 一次 zhida 调用约 0.5 元,可控

### 关键文件位置(留给未来)

| 想看的东西 | 路径 |
|---|---|
| 14 档案的 event_anchors 数据结构 | `data/demo/curation.json` line ~14-50(每个 topic 的 `event_anchors`) |
| 各档案完整 year_summaries | `public/api-data/*.json`(14 个文件) |
| 「我的视角」UI 锚点位置 | `public/index.html:1186-1230`(mp-* IDs) |
| 「我的视角」渲染逻辑 | `public/index.html:7780+`(renderMyProfile) |
| OAuth 工具函数 | `functions/api/me/profile.js`(parseCookies, oauthGet) |
| Worker 路由 | `worker/index.js`(ROUTES 字典) |

### 不要重复踩的坑

- ❌ **别再 probe `/openapi/user_*` 系列** — 全部 404 已确认,根本不是这个路径风格
- ❌ **别再尝试 server-side fetch zhihu.com**(包括 v4 API 和 HTML) — Cloudflare 海外节点 IP 已被知乎风控标记,无论 UA / 频率怎么调都 403/40352
- ❌ **别再用 zhihu_search 反查作者** — 它是基于热度的关键词搜索,不是作者索引

### 已 revert 的代码痕迹(留作参考)

```
3d9efb9 lab: 加 /api/lab/probe-content endpoint(已 revert)
abc6df0 Revert "lab: 加 /api/lab/probe-content"
```

可以从 git history 找回完整 probe 实现代码(`git show 3d9efb9:functions/api/lab/probe-content.js`)。

---

## #2 · (留空 · 未来 idea 往这填)

