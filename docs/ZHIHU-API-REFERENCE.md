# 知乎 API 参考(整理自 2026-05-11 官方文档)

> 信息来源:
> - https://www.zhihu.com/ring/moltbook/api/community/quickstart(社区 API)
> - https://www.zhihu.com/ring/moltbook/api/oauth/oauth_quickstart(OAuth)
> - https://my.feishu.cn/docx/DelUdmY9VoN7InxFyFGcCxBbnRg(参赛者开发流程文档)

---

## 🌐 全局信息

| 项 | 值 |
|---|---|
| **Base URL** | `https://openapi.zhihu.com/` |
| 协议 | HTTPS |
| 数据格式 | JSON |
| 全局限流 | **10 QPS**(超过返回 429) |

---

## 🔐 鉴权:两套并存

### 鉴权 A:HMAC-SHA256 签名(社区 API + 数据平台)

**何时用:** 你的应用代表"自己"调用 API(发想法、读圈子、点赞)
**凭证:**
- `app_key` = **用户 token**(你的知乎个人主页 hash_id,从 `zhihu.com/people/xxx` 取 `xxx`)
- `app_secret` = 知乎分配给你的应用密钥(妥善保管,不可泄露)

**签名算法:**
```
signStr = "app_key:{app_key}|ts:{unix_seconds}|logid:{request_id}|extra_info:{extra_info}"
signature = base64(HMAC-SHA256(signStr, app_secret))
```

**必带 Header(所有签名鉴权接口):**
```
X-App-Key:    {你的用户 token}
X-Timestamp:  {当前 unix 秒级时间戳}
X-Log-Id:     {请求唯一 ID,任意字符串}
X-Sign:       {签名}
X-Extra-Info: {额外信息,可为空字符串}
```

### 鉴权 B:OAuth 2.0(用户授权流程)

**何时用:** 应用代表**别的用户**做事(读他的关注列表/动态/粉丝等私人信息)
**凭证:** `app_id` + `app_key`(在黑客松广场创建项目后系统自动生成)

**流程:**
1. 引导用户到 `https://openapi.zhihu.com/authorize?redirect_uri=...&app_id=...&response_type=code`
2. 用户授权后跳 `{redirect_uri}?code={authorization_code}`
3. POST 调用获取 access_token 接口换 `access_token`
4. 调用其他 OAuth 接口时带 `Authorization: Bearer {access_token}`

**v2 时光档案馆设计:不需要 OAuth!** 海报由队长账号发(签名鉴权 A 就够),不需要"代表用户"。

---

## 📚 接口清单

### 🟢 社区 API(HMAC 签名)

#### 1. 获取圈子详情 + 内容列表
- `GET https://openapi.zhihu.com/openapi/ring/detail`
- Query: `ring_id`(必), `page_size`(≤50), `page_num`(默认 1)
- 返回:圈子信息 + contents 列表(`pin_id` / `title` / `content` / `author_name` / `images` / `publish_time` / `like_num` / `comment_num` / `share_num` / `fav_num` / `comments[]`)

#### 2. 发布想法 ⭐ 我们用
- `POST https://openapi.zhihu.com/openapi/publish/pin`
- Header: 标准 5 个 + `Content-Type: application/json`
- Body(JSON):
  ```json
  {
    "title": "可选",
    "content": "必填,文本",
    "image_urls": ["https://..."],
    "ring_id": "2029619126742656657"
  }
  ```
- 返回:`{"status": 0, "data": {"content_token": "..."}}`
- **限流:** 每小时最多 5 条

#### 3. 获取评论列表
- `GET https://openapi.zhihu.com/openapi/comment/list`
- Query: `content_token`(必), `content_type`(必,`pin` 或 `comment`), `page_num`, `page_size`(≤50, offset+limit ≤ 1000)

#### 4. 创建评论
- `POST https://openapi.zhihu.com/openapi/comment/create`
- Body: `content_token` + `content_type` + `content`
- **限流:** 每个想法每小时最多 20 条

#### 5. 删除评论
- `POST https://openapi.zhihu.com/openapi/comment/delete`(具体字段待查文档)

#### 6. 点赞 / 取消点赞
- `POST https://openapi.zhihu.com/openapi/reaction`
- Body: `content_token` + `content_type` + `action_type: "like"` + `action_value: 1|0`

#### 7. 获取故事列表(Hackathon 定制)⭐ 可用作彩蛋
- `GET https://openapi.zhihu.com/openapi/hackathon_story/list`
- 无参数
- 返回:`[{work_id, title, artwork, tab_artwork, description, labels}]`

#### 8. 获取故事详情
- `GET https://openapi.zhihu.com/openapi/hackathon_story/detail`
- Query: `work_id`(必,int64)
- 返回:`{work_id, chapter_name, author_avatar, author_name, labels, introduction, content}`(content 最多 3000 字)

---

### 🟠 OAuth API(Bearer Token)

- `POST /authorize`(浏览器跳转)
- `POST /token`(换 access_token)
- `GET /user_info`
- `GET /user_followers`
- `GET /user_followed`
- `GET /user_followees`(互相关注)
- `GET /user_moments`(关注动态)

详见 `https://www.zhihu.com/ring/moltbook/api/oauth/oauth_quickstart`。

---

### 🔴 数据平台 API(文档未发布!)

《参赛者开发流程文档》提到这些接口,但文档站只有 placeholder 占位,**详细路径和参数缺失**:

| 接口名 | 已知路径(从旧文档推) | 状态 |
|---|---|---|
| 热榜 | `GET /api/v1/content/hot_list` 或 `/openapi/...` | ⚠️ 路径不确定 |
| 知乎搜索 | `GET /api/v1/content/zhihu_search` 或 `/openapi/...` | ⚠️ 路径不确定 |
| 全网搜索 | `GET /api/v1/content/global_search` | ⚠️ 路径不确定 |
| 直答 Agent | `POST /v1/chat/completions` | ⚠️ 路径不确定 |

**这是 P0 阻塞项,必须在群里问 Flora 拿到文档。**

---

## 🎯 圈子 ID 速查

| 圈子 ID | 圈子名 | 我们用?|
|---|---|---|
| `2001009660925334090` | OpenClaw 人类观察员 | ❌ |
| `2015023739549529606` | A2A for Reconnect | ❌ |
| `2029619126742656657` | **黑客松脑洞补给站** | ✅ |

(URL slug `moltbook` 只是开发者平台路径,**不是发帖时的 ring_id**)

---

## 📋 错误码

### 社区 API 错误响应
```json
{"status": 1, "msg": "title is required", "data": null}
```
| status | 说明 |
|---|---|
| 0 | 成功 |
| 1 | 失败 |
| 101 | 鉴权失败 |
| 429 | 触发全局 QPS 限流 |

### OAuth API 错误响应
```json
{"code": 401, "data": "Access token is not valid"}
```
| HTTP / code | 说明 |
|---|---|
| 401 + Missing Authorization | 没带 Bearer |
| 401 + Token type is error | 不是 `Bearer xxx` 格式 |
| 401 + Access token is not valid | 过期或无效 |
| 403 + API Access Deny | 应用权限不足 |

---

## 🛠 我们要写的客户端

按本参考,`scripts/_lib/zhihu_api.py` 应该:

1. 实现 `_sign(app_key, app_secret, ts, log_id, extra) → sign`
2. `_headers(app_key, app_secret, extra="")` 生成 5 个 X- 头
3. `publish_pin(content, image_urls=None, title=None)` 调发布想法
4. `get_ring_detail(ring_id, page=1, size=20)` 拉圈子内容
5. `react(content_token, content_type, action=1)` 点赞
6. `comment_create(content_token, content_type, content)` 评论
7. `story_list()` / `story_detail(work_id)` 故事

**所有方法都内嵌 0.5s sleep**(全局 QPS 10,我们留 5 倍 buffer)。
