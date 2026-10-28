// 抖音：粉丝列表抽样（WORKFLOW 6.6 节）。抽样计划按规则自动算：
//   最近：max_time=现在，连续 6 页；爆款期：点赞最高作品发布日次日 0 点起，连续 5 页；
//   探针：账号创建时间（uid 推算，推不出用最早作品时间）到现在之间平均取 4 个时间点，各 1 页；
//   另抽约 12 个粉丝主页（最近、爆款期各 6 个）。
// 输出 W/data_final/<id>/fans_sample.json：{id, uid, own, plan, pages, probes, followers, profiles, blocked, privacy, flags, fetched_at}。
import fs from "node:fs";
import { BASE, readJson, writeJson, getJson, sleep, cst } from "./lib/common.mjs";

const day = (t) => new Date(t * 1000 + 8 * 3600e3).toISOString().slice(0, 10);
const dayStart = (d) => Math.floor(new Date(d + "T00:00:00+08:00").getTime() / 1000);

export function uidCreated(uid) {
  try {
    const b = BigInt(String(uid));
    return b > 10n ** 17n ? Number(b >> 32n) : null;
  } catch (e) {
    return null;
  }
}

export function makePlan(uid, posts, now = Math.floor(Date.now() / 1000)) {
  const s = (p) => (p.stats && p.stats.digg_count) || 0;
  const top = [...posts].sort((a, b) => s(b) - s(a))[0];
  const peak = top && top.create_time ? day(top.create_time + 86400) : null;
  const earliest = posts.length ? Math.min(...posts.map((p) => p.create_time || now)) : null;
  const start = uidCreated(uid) || earliest;
  const probes = start && start < now ? [1, 2, 3, 4].map((k) => day(start + ((now - start) * k) / 5)) : [];
  return { uid: String(uid), peak, probes, start: start ? day(start) : null, start_from: uidCreated(uid) ? "uid" : "earliest_post" };
}

const slim = (f, tag, pg) => ({
  tag, pg, uid: f.uid, sec: f.sec_uid, nick: f.nickname, sig: f.signature, uniq: f.unique_id,
  works: f.aweme_count ?? null, fans: f.follower_count ?? null, following: f.following_count ?? null, liked: f.favoriting_count ?? null, got: f.total_favorited ?? null,
  avatar: f.avatar_thumb && f.avatar_thumb.uri, verify: f.custom_verify || f.enterprise_verify_reason || "", ky: f.ky_only_predict, secret: f.secret,
});

export async function fansSample(page, id, acc, { W, log = console.log, pace = {} }) {
  const dir = `${W}/data_final/${id}`;
  const sec = acc.sec_uid;
  const posts = readJson(`${dir}/posts.json`, []) || [];
  const profJ = readJson(`${dir}/profile.json`, {}) || {};
  const uid = acc.uid || (profJ.user && profJ.user.uid);
  if (!sec || !uid) return { ok: false, err: "缺 sec_uid 或 uid" };
  const plan = makePlan(uid, posts);
  const opt = { W, log, retryWait: pace.retry ?? 15000 };
  const wait = () => sleep(page, pace.req ?? 3000);
  const followerPage = (maxTime) =>
    getJson(page, `/aweme/v1/web/user/follower/list/?${BASE}&user_id=${uid}&sec_user_id=${sec}&offset=0&min_time=0&max_time=${maxTime}&count=20&source_type=1&gps_access=0&address_book_access=0&is_top=1`, opt);
  const profile = (s) => getJson(page, `/aweme/v1/web/user/profile/other/?${BASE}&publish_video_strategy_type=2&source=channel_pc_web&sec_user_id=${s}`, opt);

  const out = { id, uid: String(uid), plan, fetched_at: new Date().toISOString(), pages: [], probes: [], followers: [], flags: [] };
  const own = await profile(sec);
  if (own.j && own.j.user) {
    const u = own.j.user;
    out.own = { fans: u.follower_count, max: u.max_follower_count, likes: u.total_favorited, works: u.aweme_count, nick: u.nickname };
    writeJson(`${dir}/profile_xhr.json`, own.j, 0);
  }
  log(id, "fans plan", JSON.stringify(plan), "own", JSON.stringify(out.own || null));
  await wait();
  let blocked = false, privacy = false;
  const fail = (r) => { blocked = true; if (r.code === 2096) privacy = true; };
  const runs = [["recent", 0, 6]];
  if (plan.peak) runs.push(["peak", dayStart(plan.peak), 5]);
  for (const [tag, start, n] of runs) {
    let mt = start;
    for (let i = 0; i < n; i++) {
      const r = await followerPage(mt);
      if (!r.j) { fail(r); break; }
      const j = r.j;
      const fl = j.followers || [];
      out.pages.push({ tag, i, n: fl.length, min: cst(j.min_time), max: cst(j.max_time), total: j.total, has_more: j.has_more });
      if (fl.length && fl.length < 20 && j.has_more && j.max_time && j.min_time && j.max_time - j.min_time < 600)
        out.flags.push(`${tag}${i}: ${fl.length} 人，关注时间集中在 ${Math.round((j.max_time - j.min_time) / 60)} 分钟内（${cst(j.min_time)}）`);
      for (const f of fl) out.followers.push(slim(f, tag, i));
      if (!j.has_more || !j.min_time || j.min_time === mt) break;
      mt = j.min_time;
      await wait();
    }
    if (blocked) break;
    await wait();
  }
  if (!blocked) {
    for (const d of plan.probes) {
      const r = await followerPage(dayStart(d));
      if (!r.j) { fail(r); break; }
      const j = r.j;
      const fl = j.followers || [];
      const spanH = j.max_time && j.min_time ? (j.max_time - j.min_time) / 3600 : null;
      out.probes.push({
        at: d, n: fl.length, min: cst(j.min_time), max: cst(j.max_time), span_hours: spanH && Math.round(spanH * 100) / 100,
        per_day: spanH ? Math.round((fl.length / Math.max(spanH, 0.01)) * 24) : null,
        zero_works: fl.filter((f) => !f.aweme_count).length,
        default_avatar: fl.filter((f) => /mosaic-legacy_379/.test((f.avatar_thumb && f.avatar_thumb.uri) || "")).length,
      });
      for (const f of fl) out.followers.push(slim(f, "probe:" + d, 0));
      await wait();
    }
  }
  const pool = out.followers.filter((f) => f.tag === "recent").slice(0, 60);
  const pool2 = out.followers.filter((f) => f.tag === "peak").slice(0, 60);
  const pick = [];
  for (const p of [pool, pool2]) for (let k = 0; k < 6 && p.length; k++) pick.push(p[Math.floor((k * p.length) / 6)]);
  out.profiles = [];
  if (!blocked) {
    for (const f of pick) {
      if (!f.sec) continue;
      const r = await profile(f.sec);
      if (!r.j || !r.j.user) { fail(r); break; }
      const u = r.j.user;
      out.profiles.push({
        tag: f.tag, nick: u.nickname, gender: u.gender, age: u.user_age, ip: u.ip_location, province: u.province, city: u.city, country: u.country,
        works: u.aweme_count ?? null, fans: u.follower_count ?? null, following: u.following_count ?? null, got: u.total_favorited ?? null, liked: u.favoriting_count ?? null,
        sig: (u.signature || "").slice(0, 60), school: u.school_name, uid: u.uid, sec: u.sec_uid,
      });
      await wait();
    }
  }
  out.blocked = blocked;
  out.privacy = privacy;
  writeJson(`${dir}/fans_sample.json`, out);
  log(id, "fans pages", out.pages.map((p) => `${p.tag}${p.i}:${p.n}`).join(" "), "probes", out.probes.map((p) => `${p.at}:${p.n}`).join(" "),
    "profiles", out.profiles.length, blocked ? (privacy ? "隐私(2096)" : "中断") : "", out.flags.length ? `机器粉信号 ${out.flags.length}` : "");
  return { ok: true, pages: out.pages.length, probes: out.probes.length, profiles: out.profiles.length, blocked, privacy, flags: out.flags };
}

export const hasFans = (W, id) => fs.existsSync(`${W}/data_final/${id}/fans_sample.json`);
