# 知乎 API 参考(整理自 2026-05-11 官方文档)

> 完整索引两套独立平台 + 双鉴权方案。
> 信息来源:
> - https://www.zhihu.com/ring/moltbook/api/community/*(社区 API · HMAC)
> - https://www.zhihu.com/ring/moltbook/api/oauth/*(OAuth)
> - https://developer.zhihu.com/docs(数据开放平台 · Bearer)

---

## 🌐 两套平台速查

| 平台 | Base URL | 鉴权 | 用途 | 凭证 |
|---|---|---|---|---|
| **社区 API** | `openapi.zhihu.com` | HMAC-SHA256 签名 | 圈子/想法/评论/点赞/故事 | `ZHIHU_APP_KEY` + `ZHIHU_APP_SECRET` |
| **数据开放平台** | `developer.zhihu.com` | Bearer Token | 知乎搜索/全网搜索/直答/热榜 | `ZHIHU_ACCESS_SECRET` |

⚠️ **凭证来源完全独立**:
- 社区 app_secret 在 https://www.zhihu.com/ring/moltbook 申请
- 数据 Access Secret 在 https://developer.zhihu.com 个人中心拿

---

## 🔐 鉴权 A · HMAC-SHA256(社区 API)

**凭证:**
- `app_key` = 你的知乎用户 token(从 `zhihu.com/people/xxx` 取 `xxx`)
- `app_secret` = 知乎分配给你的应用密钥(妥善保管)

**签名算法:**
```
signStr = "app_key:{app_key}|ts:{unix_seconds}|logid:{request_id}|extra_info:{extra_info}"
signature = base64(HMAC-SHA256(signStr, app_secret))
```

**必带 Header:**
```
X-App-Key:    {app_key}
X-Timestamp:  {unix 秒级}
X-Log-Id:     {请求唯一 ID}
X-Sign:       {签名}
X-Extra-Info: {可空}
```

## 🔐 鉴权 B · Bearer Token(数据开放平台)

**凭证:** `Access Secret`(developer.zhihu.com 个人中心)

**必带 Header:**
```
Authorization:        Bearer {access_secret}
X-Request-Timestamp:  {unix 秒级}
Content-Type:         application/json
```

---

## 📚 社区 API 全集(HMAC 鉴权)

### 1. 圈子详情 + 内容列表
- `GET https://openapi.zhihu.com/openapi/ring/detail`
- Query: `ring_id`, `page_num`(默认 1), `page_size`(≤50)

### 2. 发布想法 ⭐
- `POST https://openapi.zhihu.com/openapi/publish/pin`
- Body: `{content, ring_id, title?, image_urls?}`
- 返回: `{status: 0, data: {content_token}}`
- **限流:每小时 5 条**

### 3. 评论列表
- `GET https://openapi.zhihu.com/openapi/comment/list`
- Query: `content_token`, `content_type`(pin/comment), `page_num`, `page_size`(≤50, offset+limit ≤ 1000)

### 4. 创建评论
- `POST https://openapi.zhihu.com/openapi/comment/create`
- Body: `{content_token, content_type, content}`
- **限流:每想法每小时 20 条**

### 5. 删除评论
- `POST https://openapi.zhihu.com/openapi/comment/delete`

### 6. 点赞/取消
- `POST https://openapi.zhihu.com/openapi/reaction`
- Body: `{content_token, content_type, action_type: "like", action_value: 1|0}`

### 7. Hackathon 故事列表
- `GET https://openapi.zhihu.com/openapi/hackathon_story/list`

### 8. Hackathon 故事详情
- `GET https://openapi.zhihu.com/openapi/hackathon_story/detail`
- Query: `work_id`
- 返回:`{chapter_name, author_name, labels, introduction, content}`(content 最多 3000 字)

**圈子 ID 速查:**
| ID | 名 | 我们用 |
|---|---|---|
| `2001009660925334090` | OpenClaw 人类观察员 | ❌ |
| `2015023739549529606` | A2A for Reconnect | ❌ |
| **`2029619126742656657`** | **黑客松脑洞补给站** | ✅ |

---

## 🧠 数据开放平台全集(Bearer 鉴权)

### 1. 知乎搜索
- `GET https://developer.zhihu.com/api/v1/content/zhihu_search`
- Query: `Query`(必), `Count`(默认 10, **最大 10** ⚠️)
- 返回:`{Code: 0, Data: {HasMore: false, Items: [...]}}`
- **Item 字段:** Title / ContentType / ContentID / ContentText / Url / VoteUpCount / CommentCount / AuthorName / AuthorAvatar / EditTime(unix 秒) / AuthorityLevel(1-4) / RankingScore / CommentInfoList
- ⚠️ **HasMore 当前固定 false,即每个 query 最多 10 条,无分页**

### 2. 全网搜索
- `GET https://developer.zhihu.com/api/v1/content/global_search`
- Query: `Query`(必), `Count`(默认 10, **最大 20**)
- 返回类似 zhihu_search,有 HasMore

### 3. 直答 Agent ⭐
- `POST https://developer.zhihu.com/v1/chat/completions`(⚠️ 没有 `/api/v1` 前缀)
- Body:
```json
{
  "model": "zhida-fast-1p5" | "zhida-thinking-1p5" | "zhida-agent",
  "messages": [{"role": "user", "content": "..."}],
  "stream": false
}
```
- **模型档位:**
  - `zhida-fast-1p5` — 快速回答
  - `zhida-thinking-1p5` — 深度思考(响应含 `reasoning_content`)
  - `zhida-agent` — 智能思考(Agent 模式)
- 兼容 OpenAI Chat Completions 格式

### 4. 知乎热榜
- `GET https://developer.zhihu.com/api/v1/content/hot_list`
- Query: `Limit`(默认 30, **最大 30**)
- 返回:`Items: [{Title, Url, ThumbnailUrl, Summary}]`
- ⚠️ **没有时间窗口参数**(不能按"最近 N 小时"过滤)

**错误码(数据平台):**
| Code | 说明 |
|---|---|
| 0 | 成功 |
| 10001 | 参数错误 |
| 20001 | 鉴权失败 |
| 30001 | 频率限制 |
| 90001 | 内部错误 |

---

## ⚠️ 关键限制(影响 v2 设计)

### 限制 1:zhihu_search Count 最大 10,无分页

之前设计预估每话题 200-500 条原始回答,实际**每个 query 上限 10 条**。

**应对策略:**
- **多关键词扩展**:每话题准备 5-10 个不同 keywords(`程序员35岁` / `大龄程序员` / `中年程序员` / `程序员转管理` / `程序员中年危机`),每个 query 10 条,总计 50-100 条
- **配合 global_search**(最大 20)拿网络上的补充内容
- **直答 Agent 当主力**:不抓原始回答,而是直接问"知乎社区在 X 年对 Y 问题的主流观点"
- **新策略:**
  - search 主要用于"找代表性回答 + 金句来源",不再当数据主力
  - **直答 + LLM 路由**是核心:用 zhida-thinking-1p5 直接生成时光轴

### 限制 2:无时间窗口过滤

`zhihu_search` 无法按年份过滤,只能客户端按 `EditTime`(unix 秒)分桶。
`hot_list` 无 hours 参数,只能取当前热榜。

### 限制 3:搜索 API 不支持流式

直答 API 支持 `stream: true`,搜索不支持。

---

## 🎯 OAuth API(可选,v2 不用)

仅当应用要代表**别的用户**读私人信息(关注流/动态/粉丝)时才用。
v2 海报由队长账号(jzwa)直接发,不需要 OAuth。

详见 https://www.zhihu.com/ring/moltbook/api/oauth/oauth_quickstart。

---

## 🛠 客户端实现

`scripts/_lib/zhihu_api.py` 已实现:

**社区 API(HMAC):**
- `get_ring_detail()` ✅ 自检通过
- `publish_pin()`
- `comment_list()` / `comment_create()`
- `react()` 点赞/取消
- `story_list()` / `story_detail()`

**数据平台(Bearer):**
- `zhihu_search()` Count ≤ 10
- `global_search()` Count ≤ 20
- `hot_list()` Limit ≤ 30
- `chat_completions()` 直答(兼容 OpenAI)

跑自检:
```bash
cd scripts && source .venv/bin/activate
python -m _lib.zhihu_api
```
