// 抖音：截图证据（WORKFLOW 6.7 节、CROP_RULE.md 第 4 节）。视口 1280×860，评论区和粉丝列表打码。
// 每号输出 W/shots_clean/<id>/：01-profile.png（主页）、02-fans.png（粉丝弹窗）、
// 03-top-<作品ID>.png（点赞最高作品+评论区）、04-recent-<作品ID>.png（最近一条作品+评论区）、res.json。
// 只有 res.json 里 ok 的图会进报告；右侧“相关推荐”区域在生成报告时统一打码。
import fs from "node:fs";
import { readJson, writeJson, mkdirp, checkBlockers } from "./lib/common.mjs";

const BLUR = (names) => {
  const st = document.createElement("style");
  st.textContent =
    '[data-e2e="comment-item"] img,[data-e2e="comment-item"] a[href*="/user/"],[data-e2e="user-fans-container"] img,[data-e2e="user-fans-container"] a[href*="/user/"]{filter:blur(8px)!important}';
  document.head.appendChild(st);
  const set = new Set(names);
  let hits = 0;
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    const t = n.textContent.trim();
    if (t && (set.has(t) || /^用户\d{5,}$/.test(t))) { n.parentElement.style.filter = "blur(8px)"; hits++; }
  }
  return hits;
};

// 代表作品：点赞最高；最近一条非置顶（与点赞最高相同时取下一条）
export function representative(posts) {
  const s = (p) => (p.stats && p.stats.digg_count) || 0;
  const top = [...posts].sort((a, b) => s(b) - s(a))[0];
  const recent = posts.filter((p) => !p.is_top).sort((a, b) => b.create_time - a.create_time).find((p) => !top || p.aweme_id !== top.aweme_id);
  return { top: top && top.aweme_id, recent: recent && recent.aweme_id };
}

async function waitImages(page, ms = 10000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    const ok = await page
      .evaluate(() => [...document.images].filter((i) => { const r = i.getBoundingClientRect(); return r.top < 860 && r.bottom > 0 && r.width > 40; }).every((i) => i.complete && i.naturalWidth > 0))
      .catch(() => true);
    if (ok) return true;
    await page.waitForTimeout(500);
  }
  return false;
}

async function clearScreen(page) {
  await page.keyboard.press("Escape").catch(() => {});
  await page.waitForTimeout(300);
  await page.evaluate(() => {
    window.scrollTo(0, 0);
    const c = document.querySelector(".route-scroll-container");
    if (c) c.scrollTop = 0;
  }).catch(() => {});
  await page.mouse.move(60, 800).catch(() => {});
  await page.waitForTimeout(500);
}

export async function shots(page, id, acc, { W, log = console.log }) {
  const dir = `${W}/shots_clean/${id}`;
  mkdirp(dir);
  const dd = `${W}/data_final/${id}`;
  const posts = readJson(`${dd}/posts.json`, []) || [];
  const prof = (readJson(`${dd}/profile.json`, {}) || {}).user || {};
  const nick = prof.nickname || acc.nickname || "";
  const probe = nick.slice(0, 6);
  let names = [];
  const cm = readJson(`${dd}/comments2.json`, {}) || {};
  for (const v of Object.values(cm)) for (const c of v.comments || []) { names.push(c.nick); for (const r of c.reply_preview || []) names.push(r.nick); }
  const fs1 = readJson(`${dd}/fans_sample.json`, {}) || {};
  names.push(...(fs1.followers || []).map((f) => f.nick), ...(fs1.profiles || []).map((f) => f.nick));
  names = [...new Set(names.filter(Boolean))].filter((x) => x !== nick);
  const shot = (p) => page.screenshot({ path: p }).catch((e) => log(id, "shot err", String(e).slice(0, 80)));
  const res = { id, t: new Date().toISOString() };
  await page.cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 860, deviceScaleFactor: 1, mobile: false }).catch(() => {});
  try {
    await page.goto(`https://www.douyin.com/user/${acc.sec_uid}`, { timeout: 30000 }).catch(() => log(id, "goto profile timeout"));
    await page.waitForTimeout(6000);
    await checkBlockers(page, W, `${id} 截图主页`);
    await clearScreen(page);
    res.imagesLoaded = await waitImages(page);
    res.profileOk = !!probe && (await page.evaluate((n) => document.title.includes(n) || document.body.innerText.slice(0, 3000).includes(n), probe).catch(() => false));
    await shot(`${dir}/01-profile.png`);
    const fansEl = await page.evaluate(() => !!document.querySelector("[data-e2e=user-info-fans]")).catch(() => false);
    if (fansEl) {
      await page.click("[data-e2e=user-info-fans]", { label: "打开粉丝列表（只读）" }).catch((e) => log(id, "click err", String(e).slice(0, 80)));
      await page.waitForTimeout(4000);
      res.fansBlur = await page.evaluate(BLUR, names).catch(() => 0);
      await page.evaluate(() => {
        const c = document.querySelector('[data-e2e="user-fans-container"]');
        if (c) c.querySelectorAll("li, [class*=item]").forEach((el) => { if (!/粉丝指数/.test(el.innerText)) el.style.filter = "blur(8px)"; });
      }).catch(() => {});
      res.fansText = await page.evaluate(() => (document.body.innerText.match(/粉丝[^\n]{0,30}|TA还没有粉丝|隐私/g) || []).slice(0, 4).join(" | ")).catch(() => "");
      await shot(`${dir}/02-fans.png`);
      res["02-fans"] = { ok: true };
      await page.keyboard.press("Escape").catch(() => {});
      await page.waitForTimeout(800);
    } else res.fans = "no fans element";
    const rep = representative(posts);
    for (const [tag, aw] of [["03-top", rep.top], ["04-recent", rep.recent]]) {
      if (!aw) continue;
      await page.goto(`https://www.douyin.com/video/${aw}`, { timeout: 30000 }).catch(() => log(id, "goto video timeout", aw));
      await page.waitForTimeout(6000);
      await checkBlockers(page, W, `${id} 作品页`);
      await page.evaluate(() => document.querySelectorAll("video").forEach((v) => { v.muted = true; v.pause(); })).catch(() => {});
      await page.mouse.move(500, 400).catch(() => {});
      await page.mouse.wheel(0, 380).catch(() => {});
      await page.waitForTimeout(3000);
      const ok = !!probe && (await page.evaluate((n) => document.body.innerText.includes(n), probe).catch(() => false));
      const url = await page.url();
      const hits = await page.evaluate(BLUR, names).catch(() => 0);
      await page.waitForTimeout(500);
      await shot(`${dir}/${tag}-${aw}.png`);
      res[tag] = { aw, ok, url: url.includes(aw), hits };
    }
  } catch (e) {
    if (e && e.constructor && e.constructor.name === "PauseError") throw e;
    res.err = String(e).slice(0, 200);
  } finally {
    await page.cdp("Emulation.clearDeviceMetricsOverride").catch(() => {});
    writeJson(`${dir}/res.json`, res);
  }
  log(id, "shots", JSON.stringify({ profileOk: res.profileOk, imagesLoaded: res.imagesLoaded, top: res["03-top"] && res["03-top"].ok, recent: res["04-recent"] && res["04-recent"].ok, err: res.err }));
  return { ok: !res.err && !!res.profileOk, res };
}

export const hasShots = (W, id) => fs.existsSync(`${W}/shots_clean/${id}/res.json`);
