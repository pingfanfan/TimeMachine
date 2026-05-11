// EdgeOne Edge Function · /api/hotlist
// 知乎当前热榜 + 智能筛选(只保留有时光机价值的话题)

const TIME_TRAVEL_CONCEPTS = [
  // 教育
  ["学区房", "学区房"], ["鸡娃", "鸡娃焦虑"], ["双减", "双减政策"], ["教培", "教培行业"],
  ["选考", "新高考选考"], ["文科生", "文科生 弃理"], ["理科生", "选考物理"],
  ["高考", "高考"], ["考研", "考研"], ["学历贬值", "学历贬值"], ["内卷", "教育内卷"],
  // 职场
  ["35岁", "程序员 35 岁"], ["35 岁", "35 岁危机"], ["中年危机", "中年危机"],
  ["996", "996"], ["加班文化", "加班文化"], ["副业", "副业"], ["躺平", "躺平"],
  ["润学", "润学 出国"], ["裁员", "互联网裁员"], ["大厂", "互联网大厂"],
  // 婚恋
  ["彩礼", "彩礼"], ["天价彩礼", "天价彩礼"], ["丁克", "丁克"], ["独居", "独居"],
  ["离婚冷静期", "离婚冷静期"], ["结婚率", "结婚率下降"], ["不婚", "不婚主义"],
  ["生育率", "生育率"], ["三胎", "三胎政策"], ["二胎", "二胎政策"],
  // 经济
  ["买房", "买房"], ["房价", "房价"], ["公积金", "公积金"], ["消费降级", "消费降级"],
  // 科技/AI
  ["ChatGPT", "ChatGPT"], ["大模型", "大模型"], ["AI Agent", "AI Agent"],
  ["AI 替代", "AI 替代工作"], ["AI换脸", "AI 换脸诈骗"], ["AI 换脸", "AI 换脸诈骗"],
  ["自动驾驶", "自动驾驶"], ["新能源车", "新能源汽车"], ["新能源", "新能源"],
  ["老头乐", "老头乐 低速电动车"], ["具身智能", "具身智能"],
  ["芯片", "芯片 卡脖子"], ["半导体", "半导体 国产"],
  // 商业
  ["共享单车", "共享单车"], ["P2P", "P2P 暴雷"], ["元宇宙", "元宇宙"],
  ["区块链", "区块链"], ["比特币", "比特币"], ["跨境电商", "跨境电商"],
  ["直播带货", "直播带货"], ["短视频", "短视频"], ["出海", "中国企业 出海"],
  // 社会
  ["电信诈骗", "电信诈骗"], ["反诈", "反电信诈骗"], ["网瘾", "网瘾 戒治"],
  ["家暴", "家暴"], ["延迟退休", "延迟退休"], ["养老", "养老"],
  // 互联网
  ["抖音", "抖音"], ["B 站", "B 站"], ["微信", "微信生态"], ["知乎", "知乎"], ["小红书", "小红书"],
];

function extractTimetravelQuery(title) {
  if (!title) return null;
  const lower = title.toLowerCase();
  for (const [kw, query] of TIME_TRAVEL_CONCEPTS) {
    if (lower.includes(kw.toLowerCase())) return [kw, query];
  }
  return null;
}

export async function onRequest({ request, env }) {
  const accessSecret = env.ZHIHU_ACCESS_SECRET;
  if (!accessSecret) {
    return new Response(JSON.stringify({ error: "missing ZHIHU_ACCESS_SECRET", items: [] }), {
      status: 500, headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }

  try {
    const r = await fetch("https://developer.zhihu.com/api/v1/content/hot_list?Limit=30", {
      headers: {
        "Authorization": `Bearer ${accessSecret}`,
        "X-Request-Timestamp": String(Math.floor(Date.now() / 1000)),
        "Content-Type": "application/json",
      },
    });
    if (!r.ok) {
      return new Response(JSON.stringify({ error: `upstream ${r.status}`, items: [] }), {
        status: 502, headers: { "Content-Type": "application/json; charset=utf-8" }
      });
    }
    const data = await r.json();
    const items = (data?.Data?.Items) || [];

    const out = [];
    for (const it of items) {
      const title = (it.Title || "").trim();
      if (!title) continue;
      const extracted = extractTimetravelQuery(title);
      if (!extracted) continue;
      const [matchedKeyword, query] = extracted;
      out.push({
        title,
        url: it.Url || "",
        summary: (it.Summary || "").slice(0, 120),
        matched_keyword: matchedKeyword,
        time_travel_query: query,
      });
      if (out.length >= 8) break;
    }

    return new Response(JSON.stringify({ items: out, total_scanned: items.length }), {
      headers: { "Content-Type": "application/json; charset=utf-8" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e), items: [] }), {
      status: 500, headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  }
}
