// 抖音：评论区（WORKFLOW 6.5 节）。每号选最近 3 条有评论的作品 + 点赞最高 2 条，每条取 2 页评论，
// 输出 W/data_final/<id>/comments2.json：{作品ID: {why, create_time, desc, stats, comments: [...]}}。
// 需要先有 posts.json，并且页面已经停在抖音域名下（同源请求才会被签名）。
import fs from "node:fs";
import { BASE, readJson, writeJson, getJson, sleep } from "./lib/common.mjs";

export function pickCommentPosts(posts, nRecent = 3, nTop = 2) {
  const s = (p, k) => (p.stats && p.stats[k]) || 0;
  const nonTop = posts.filter((p) => !p.is_top).sort((a, b) => b.create_time - a.create_time);
  const picks = [];
  for (const p of nonTop) { if (picks.length >= nRecent) break; if (s(p, "comment_count") > 0) picks.push({ ...p, why: "recent" }); }
  for (const p of [...posts].sort((a, b) => s(b, "digg_count") - s(a, "digg_count"))) {
    if (picks.filter((x) => x.why === "top").length >= nTop) break;
    if (!picks.some((x) => x.aweme_id === p.aweme_id) && s(p, "comment_count") > 0) picks.push({ ...p, why: "top" });
  }
  return picks;
}

export async function comments(page, id, acc, { W, log = console.log, pace = {}, pagesPerPost = 2 }) {
  const dir = `${W}/data_final/${id}`;
  const posts = readJson(`${dir}/posts.json`, []) || [];
  const s = (p, k) => (p.stats && p.stats[k]) || 0;
  const opt = { W, log, retryWait: pace.retry ?? 15000 };
  const out = {};
  for (const p of pickCommentPosts(posts)) {
    const list = [];
    let cursor = 0;
    for (let i = 0; i < pagesPerPost; i++) {
      await sleep(page, pace.req ?? 3000);
      const r = await getJson(page, `/aweme/v1/web/comment/list/?${BASE}&aweme_id=${p.aweme_id}&cursor=${cursor}&count=20&item_type=0&insert_ids=&whale_cut_token=&cut_version=1&rcFT=`, opt);
      const j = r.j;
      if (!j) break;
      for (const c of j.comments || []) {
        list.push({
          text: c.text, digg: c.digg_count, reply: c.reply_comment_total, ip: c.ip_label, t: c.create_time,
          nick: c.user && c.user.nickname, uid: c.user && c.user.uid, sec: c.user && c.user.sec_uid,
          avatar: c.user && c.user.avatar_thumb && c.user.avatar_thumb.uri,
          is_author: c.user && c.user.uid === p.author_uid, author_digged: c.is_author_digged, label: c.label_text,
          sticker: !!c.sticker, image: !!(c.image_list && c.image_list.length),
          reply_preview: (c.reply_comment || []).map((r2) => ({ text: r2.text, nick: r2.user && r2.user.nickname, is_author: r2.user && r2.user.uid === p.author_uid, label: r2.label_text })),
        });
      }
      if (!j.has_more) break;
      cursor = j.cursor;
    }
    out[p.aweme_id] = { why: p.why, create_time: p.create_time, desc: (p.desc || "").slice(0, 50), stats: p.stats, comments: list };
    log(id, "comments", p.why, p.aweme_id, list.length, "of", s(p, "comment_count"));
  }
  writeJson(`${dir}/comments2.json`, out);
  const n = Object.values(out).reduce((t, x) => t + x.comments.length, 0);
  return { ok: true, posts: Object.keys(out).length, comments: n };
}

export const hasComments = (W, id) => fs.existsSync(`${W}/data_final/${id}/comments2.json`);
