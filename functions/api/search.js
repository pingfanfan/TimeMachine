// EdgeOne Edge Function · /api/search?q=...
// 调知乎数据平台 zhihu_search 接口(Bearer Token)

const YEAR_RE = /(?:^|[^\d])(20[01]\d|2026)(?:\s*年|\s*年[左前后底初中]|[/\-．. ])/g;

function inferYear(text, editYear) {
  if (text) {
    const matches = [...text.matchAll(YEAR_RE)].map(m => parseInt(m[1]));
    const cand = matches.filter(y => y >= 2008 && y <= 2026);
    if (cand.length) return Math.min(...cand);
  }
  return editYear;
}

export async function onRequest({ request, env }) {
  const url = new URL(request.url);
  const q = (url.searchParams.get("q") || "").trim();
  if (!q) return jsonResp({ error: "missing q" }, 400);

  const accessSecret = env.ZHIHU_ACCESS_SECRET;
  if (!accessSecret) return jsonResp({ error: "missing ZHIHU_ACCESS_SECRET" }, 500);

  // 多 keyword 扩展
  const queries = [q];
  if (!q.includes("事件")) queries.push(`${q} 事件`);
  if (q.length > 4 && q.includes(" ")) queries.push(q.split(" ")[0]);

  const seen = new Set();
  const rawItems = [];

  for (const kw of queries.slice(0, 3)) {
    try {
      const r = await fetch(`https://developer.zhihu.com/api/v1/content/zhihu_search?Query=${encodeURIComponent(kw)}&Count=10`, {
        headers: {
          "Authorization": `Bearer ${accessSecret}`,
          "X-Request-Timestamp": String(Math.floor(Date.now() / 1000)),
          "Content-Type": "application/json",
        },
      });
      if (!r.ok) continue;
      const data = await r.json();
      const items = (data?.Data?.Items) || [];
      for (const it of items) {
        const cid = it.ContentID;
        if (!cid || seen.has(cid)) continue;
        seen.add(cid);
        rawItems.push(it);
      }
    } catch (e) {
      console.error(`[search err] ${kw}:`, e);
    }
  }

  if (rawItems.length === 0) {
    return jsonResp({ q, items: [], by_year: {}, year_count: 0 });
  }

  // 启发式年份分桶
  const byYear = {};
  for (const it of rawItems) {
    const editYear = it.EditTime ? new Date(it.EditTime * 1000).getFullYear() : null;
    const y = inferYear(it.ContentText || "", editYear);
    if (y === null || y === undefined) continue;
    const yi = parseInt(y);
    (byYear[yi] = byYear[yi] || []).push({
      title: (it.Title || "").replace(" - 知乎", ""),
      content_type: it.ContentType,
      content_text: (it.ContentText || "").slice(0, 300),
      url: it.Url || "",
      vote_up_count: it.VoteUpCount || 0,
      author_name: it.AuthorName,
      edit_year: editYear,
    });
  }

  for (const y in byYear) {
    byYear[y].sort((a, b) => (b.vote_up_count || 0) - (a.vote_up_count || 0));
  }

  const summaries = {};
  for (const y in byYear) {
    const top = byYear[y][0];
    if (top) {
      summaries[y] = {
        representative_quote: (top.content_text || "").slice(0, 120),
        author: top.author_name,
        url: top.url,
      };
    }
  }

  return jsonResp({
    q,
    year_count: Object.keys(byYear).length,
    by_year: Object.fromEntries(Object.keys(byYear).sort().map(y => [y, byYear[y]])),
    summaries: Object.fromEntries(Object.keys(summaries).sort().map(y => [y, summaries[y]])),
  });
}

function jsonResp(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}
