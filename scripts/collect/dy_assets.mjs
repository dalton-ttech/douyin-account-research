// 抖音：总览素材（WORKFLOW 6.8 节）。头像取主页接口的头像地址；cover1 是点赞最高作品的封面，cover2 是最近非置顶作品的封面
// （video.cover.url_list，图文作品取第一张图）。原图下载到 W/assets_work/<id>/（avatar.img、cover1.img、cover2.img、meta.json），
// 之后由 assets_finalize.py 转成 JPEG 放进 P/overview-assets/<id>/，并写 W/parts/assets/<id>.json。
// 不调用 task.finish()。
import fs from "node:fs";
import { BASE, readJson, writeJson, mkdirp, getJson, sleep } from "./lib/common.mjs";

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36";

export function planAssets(prof, posts) {
  const u = prof.user || prof;
  const g = u.gender;
  let region = u.ip_location || "";
  if (region.startsWith("IP属地：")) region = region.slice(5);
  if (!region) region = [u.province, u.city].filter(Boolean).join(" ") || u.country || "";
  const sel = [];
  if (posts.length) {
    const byLike = [...posts].sort((a, b) => ((b.stats || {}).digg_count || 0) - ((a.stats || {}).digg_count || 0));
    const top = byLike[0];
    let latest = posts.filter((x) => !x.is_top).sort((a, b) => (b.create_time || 0) - (a.create_time || 0))[0] || null;
    if (!latest || latest.aweme_id === top.aweme_id) latest = byLike[1] || null;
    for (const x of [top, latest]) {
      if (x) sel.push({ aweme_id: x.aweme_id, likes: (x.stats || {}).digg_count || 0, create_time: x.create_time, desc: (x.desc || "").trim(), media_type: x.media_type, images: x.images });
    }
  }
  return {
    nickname: u.nickname, sec_uid: u.sec_uid, gender: g === 1 ? "男" : g === 2 ? "女" : "未知", region,
    verified: (u.enterprise_verify_reason || "").trim() ? "企业蓝V" : "无", custom_verify: u.custom_verify || "",
    enterprise_verify_reason: u.enterprise_verify_reason || "", aweme_count: u.aweme_count, posts_local: posts.length,
    avatar_urls: [...((u.avatar_larger || {}).url_list || []), ...((u.avatar_medium || {}).url_list || [])], sel,
  };
}

async function download(urls, dst) {
  for (const u of urls || []) {
    try {
      const res = await fetch(u, { headers: { Referer: "https://www.douyin.com/", "User-Agent": UA } });
      if (!res.ok) continue;
      const buf = Buffer.from(await res.arrayBuffer());
      if (buf.length < 1000) continue;
      fs.writeFileSync(dst, buf);
      return true;
    } catch (e) {}
  }
  return false;
}

const pick = (a) => {
  if (!a) return null;
  const v = a.video || {};
  const imgs = (a.images || []).map((i) => (i.url_list || [])[0]).filter(Boolean);
  return {
    aweme_id: a.aweme_id, create_time: a.create_time, digg: (a.statistics || {}).digg_count,
    urls: [...((v.cover || {}).url_list || []), ...((v.origin_cover || {}).url_list || []), ...imgs.slice(0, 1)],
  };
};

// 页面需停在抖音域名下（例如刚做完主页或截图）。
export async function assets(page, id, acc, { W, log = console.log, pace = {} }) {
  const dd = `${W}/data_final/${id}`;
  const out = `${W}/assets_work/${id}`;
  mkdirp(out);
  const prof = readJson(`${dd}/profile.json`, null);
  if (!prof) return { ok: false, err: "缺 profile.json" };
  const posts = readJson(`${dd}/posts.json`, []) || [];
  const plan = planAssets(prof, posts);
  const opt = { W, log, retries: 2, retryWait: pace.retry ?? 15000 };
  plan.avatar_ok = await download(plan.avatar_urls, `${out}/avatar.img`);
  const got = [];
  for (const s of plan.sel) {
    await sleep(page, pace.req ?? 3000);
    const r = await getJson(page, `/aweme/v1/web/aweme/detail/?${BASE}&aweme_id=${s.aweme_id}`, opt);
    got.push((r.j && pick(r.j.aweme_detail)) || { aweme_id: s.aweme_id, urls: [] });
  }
  if (got.some((x) => !x.urls.length) && plan.sec_uid) {
    const r = await getJson(page, `/aweme/v1/web/aweme/post/?${BASE}&sec_user_id=${plan.sec_uid}&max_cursor=0&count=18`, opt);
    for (const x of got) {
      if (x.urls.length || !r.j) continue;
      const hit = (r.j.aweme_list || []).map(pick).find((a) => a && a.aweme_id === x.aweme_id);
      if (hit) Object.assign(x, hit);
    }
  }
  plan.covers = [];
  for (let i = 0; i < got.length; i++) {
    const ok = await download(got[i].urls, `${out}/cover${i + 1}.img`);
    plan.covers.push({ aweme_id: got[i].aweme_id, digg: got[i].digg, create_time: got[i].create_time, ok });
  }
  delete plan.avatar_urls;
  writeJson(`${out}/meta.json`, plan);
  log(id, "assets avatar", plan.avatar_ok, "covers", plan.covers.map((c) => `${c.aweme_id}:${c.ok}`).join(" ") || "无作品");
  return { ok: true, avatar: plan.avatar_ok, covers: plan.covers.filter((c) => c.ok).length, sel: plan.sel.length };
}

export const hasAssets = (W, id) => fs.existsSync(`${W}/assets_work/${id}/meta.json`);
