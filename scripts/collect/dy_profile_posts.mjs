// 抖音：主页与作品（WORKFLOW 6.4 节）。打开主页后在页面里发同源 XHR 取主页和作品列表，
// 输出 W/data_final/<id>/profile.json（接口原始返回，含 user）和 posts.json（精简后的作品列表）。
import fs from "node:fs";
import { installHook, waitCap } from "./lib/hook.mjs";
import { BASE, readJson, writeJson, getJson, sleep, checkBlockers } from "./lib/common.mjs";

export function slimPost(a) {
  return {
    aweme_id: a.aweme_id, desc: a.desc, create_time: a.create_time, is_top: a.is_top, aweme_type: a.aweme_type,
    duration: a.duration || (a.video && a.video.duration), stats: a.statistics, is_aigc: a.is_aigc_media, aigc_info: a.aigc_info,
    music: a.music && { title: a.music.title, owner: a.music.owner_nickname, original: a.music.is_original },
    media_type: a.media_type, images: a.images ? a.images.length : 0,
    tags: (a.text_extra || []).map((t) => t.hashtag_name).filter(Boolean),
    video_tag: (a.video_tag || []).map((t) => t.tag_name), author_uid: a.author && a.author.uid,
    duet: a.duet_origin_item ? 1 : 0, mix: a.mix_info && a.mix_info.mix_name, anchor: a.anchor_info && a.anchor_info.title,
    caption: a.caption, item_title: a.item_title,
  };
}

// acc：accounts_*.json 里该号的记录（至少有 sec_uid，最好有 uid、nickname）。
// 作品翻到 has_more=0；作品很多时最多 maxPosts 条（至少要抓到作品数的 95% 或 60 条，不足时在返回里标出）。
export async function profilePosts(page, id, acc, { W, log = console.log, pace = {}, maxPosts = 400 }) {
  const dir = `${W}/data_final/${id}`;
  const sec = acc.sec_uid;
  if (!sec) return { ok: false, err: "缺 sec_uid" };
  const opt = { W, log, retryWait: pace.retry ?? 15000 };
  await installHook(page);
  await page.goto(`https://www.douyin.com/user/${sec}`).catch(() => log(id, "goto profile timeout"));
  await waitCap(page, "aweme/post", 15000);
  await sleep(page, 2500);
  await checkBlockers(page, W, `${id} 主页`);

  const prof = await getJson(page, `/aweme/v1/web/user/profile/other/?${BASE}&publish_video_strategy_type=2&source=channel_pc_web&sec_user_id=${sec}`, opt);
  if (!prof.j || !prof.j.user) return { ok: false, err: `主页接口失败 code=${prof.code}` };
  const u = prof.j.user;
  if ((u.sec_uid && u.sec_uid !== sec) || (acc.uid && String(u.uid) !== String(acc.uid))) {
    log(id, "防串号：主页返回的 sec_uid/uid 与解析结果不一致，停止该号", u.nickname);
    return { ok: false, err: "串号" };
  }
  writeJson(`${dir}/profile.json`, prof.j, 0);
  const works = u.aweme_count || 0;
  log(id, `profile ${u.nickname} fans=${u.follower_count} max=${u.max_follower_count} works=${works}`);

  const old = readJson(`${dir}/posts.json`, null);
  if (Array.isArray(old) && old.length >= Math.min(works, maxPosts) * 0.95 && old.length) {
    log(id, "posts 已有", old.length, "跳过");
    return { ok: true, nick: u.nickname, fans: u.follower_count, works, posts: old.length };
  }
  const posts = [];
  const seen = new Set();
  let mc = 0, foreign = 0;
  for (let i = 0; i < Math.ceil(maxPosts / 18) + 2; i++) {
    await sleep(page, pace.req ?? 3000);
    const r = await getJson(page, `/aweme/v1/web/aweme/post/?${BASE}&sec_user_id=${sec}&max_cursor=${mc}&locate_query=false&show_live_replay_strategy=1&need_time_list=1&time_list_query=0&whale_cut_token=&cut_version=1&count=18&publish_video_strategy_type=2`, opt);
    if (!r.j) break;
    for (const a of r.j.aweme_list || []) {
      if (a.author && a.author.uid && String(a.author.uid) !== String(u.uid)) { foreign++; continue; }
      if (seen.has(a.aweme_id)) continue;
      seen.add(a.aweme_id);
      posts.push(slimPost(a));
    }
    if (!r.j.has_more || posts.length >= maxPosts) break;
    mc = r.j.max_cursor;
  }
  writeJson(`${dir}/posts.json`, posts);
  const enough = posts.length >= Math.min(works * 0.95, 60);
  log(id, `posts ${posts.length}/${works}${enough ? "" : " 不足（作品数的 95% 或 60 条）"}${foreign ? ` 丢弃非本号作品 ${foreign}` : ""}`);
  return { ok: true, nick: u.nickname, fans: u.follower_count, works, posts: posts.length, enough };
}

export const hasProfilePosts = (W, id) => fs.existsSync(`${W}/data_final/${id}/profile.json`) && fs.existsSync(`${W}/data_final/${id}/posts.json`);
