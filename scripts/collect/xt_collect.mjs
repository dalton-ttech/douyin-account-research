// 巨量星图（WORKFLOW 6.9 节）。在达人广场切到“昵称找人”，填抖音号搜索，抓 search_for_author_square；
// 只有 get_author_base_info 的 unique_id 等于抖音号（不区分大小写），或 core_user_id 等于抖音 uid，才算找到。
// 找到后在页面里取各接口（参数带 o_author_id=<星图ID>&platform_source=1），并截搜索结果、达人主页和画像标签页。
// 输出 W/xingtu_data/<id>.json（id、found、match、search、aid、api、homeText、tabs）和 W/shots_mine/xingtu/<id>/。
// 截图保留原图；报告生成时统一裁掉顶部 92 像素（登录账号名）。没匹配上时仍保存搜索第一条的基础信息，供报告写明“搜到的是另一个号”。
import fs from "node:fs";
import { readJson, writeJson, mkdirp } from "./lib/common.mjs";

const HOOK = `(()=>{ if (window.__xtHook) return; window.__xtHook = true; window.__xt = [];
  const keep = /\\/gw\\/api\\/gsearch\\/search_for_author_square/;
  const oo = XMLHttpRequest.prototype.open, os = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, u) { this.__u = u; return oo.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function (b) { this.addEventListener("load", () => { try { if (keep.test(this.__u)) window.__xt.push({ u: String(this.__u), req: typeof b === "string" ? b.slice(0, 3000) : "", body: String(this.responseText) }); } catch (e) {} }); return os.apply(this, arguments); };
  const of = window.fetch;
  window.fetch = async function (i, init) { const r = await of.apply(this, arguments); try { const u = typeof i === "string" ? i : i.url; if (keep.test(u)) { r.clone().text().then((t) => window.__xt.push({ u, req: init && typeof init.body === "string" ? init.body.slice(0, 3000) : "", body: t })); } } catch (e) {} return r; };
})();`;

const SEL = 'input.el-input__inner[placeholder*="昵称"]';

function xget(page, u) {
  return page.evaluate((u) => new Promise((res) => {
    const x = new XMLHttpRequest();
    x.open("GET", u, true);
    x.withCredentials = true;
    x.onload = () => res({ s: x.status, b: x.responseText });
    x.onerror = () => res({ s: -1, b: "" });
    x.send();
  }), u).catch((e) => ({ s: -3, b: String(e).slice(0, 200) }));
}

async function getApi(page, u) {
  const r = await xget(page, u);
  let b = r.b;
  try { b = JSON.parse(r.b); if (b && b.base64_qrcode) b.base64_qrcode = "(omitted)"; } catch (e) {}
  return { s: r.s, b };
}

function apis(aid) {
  const Q = `o_author_id=${aid}&platform_source=1`;
  const day = 86400000, now = Date.now();
  const fmt = (t) => new Date(t).toISOString().slice(0, 10);
  const end = fmt(now - day), start = fmt(now - 91 * day);
  return {
    fans_all: `/gw/api/data_sp/get_author_fans_distribution?${Q}&author_type=1`,
    fans_t1: `/gw/api/data_sp/get_author_fans_distribution?${Q}&author_type=1&fans_type=1`,
    fans_t2: `/gw/api/data_sp/get_author_fans_distribution?${Q}&author_type=1&fans_type=2`,
    fans_t3: `/gw/api/data_sp/get_author_fans_distribution?${Q}&author_type=1&fans_type=3`,
    aud5: `/gw/api/data_sp/author_audience_distribution?${Q}&platform_channel=1&link_type=5`,
    aud1: `/gw/api/data_sp/author_audience_distribution?${Q}&platform_channel=1&link_type=1`,
    touch: `/gw/api/data_sp/author_touch_distribution?${Q}&platform_channel=1`,
    spread_p30: `/gw/api/data_sp/get_author_spread_info?${Q}&platform_channel=1&type=1&flow_type=0&only_assign=false&range=2`,
    spread_p90: `/gw/api/data_sp/get_author_spread_info?${Q}&platform_channel=1&type=1&flow_type=0&only_assign=false&range=3`,
    spread_s30: `/gw/api/data_sp/get_author_spread_info?${Q}&platform_channel=1&type=2&flow_type=1&only_assign=true&range=2`,
    cp: `/gw/api/data_sp/author_cp_info?${Q}&platform_channel=1`,
    side: `/gw/api/aggregator/get_author_side_base_info?o_author_id=${aid}`,
    commerce: `/gw/api/aggregator/get_author_commerce_spread_info?o_author_id=${aid}`,
    marketing: `/gw/api/author/get_author_marketing_info?${Q}&platform_channel=1`,
    link_struct: `/gw/api/data_sp/author_link_struct?${Q}&platform_channel=1&industry_id=0`,
    daily_fans: `/gw/api/data_sp/get_author_daily_fans?author_id=${aid}&platform_source=1&start_date=${start}&end_date=${end}&author_type=1`,
    rec_videos: `/gw/api/data_sp/author_rec_videos_v2?${Q}&platform_channel=1`,
    contract: `/gw/api/aggregator/get_author_contract_base_info?o_author_id=${aid}&range=90`,
    price: `/gw/api/gauthor/batch_get_transition_price?author_ids=${aid}`,
  };
}
const baseUrl = (aid) => `/gw/api/author/get_author_base_info?o_author_id=${aid}&platform_source=1&platform_channel=1&recommend=true&need_sec_uid=true&need_linkage_info=true`;

export async function openMarket(page, log = console.log) {
  await page.cdp("Page.enable").catch(() => {});
  await page.cdp("Page.addScriptToEvaluateOnNewDocument", { source: HOOK }).catch(() => {});
  await page.goto("https://www.xingtu.cn/ad/creator/market", { timeout: 40000 }).catch((e) => log("goto market err", String(e).slice(0, 120)));
  await page.waitForTimeout(5000);
  await page.evaluate(HOOK).catch(() => {});
  const url = await page.url();
  if (/login|passport/.test(url)) throw new Error(`星图未登录（${url.slice(0, 80)}），停止`);
  const has = await page.evaluate((s) => !!document.querySelector(s), SEL).catch(() => false);
  if (!has) { await page.click("span.search-type-radio-item:nth-child(2)", { label: "切换到昵称找人" }).catch(() => {}); await page.waitForTimeout(1200); }
}

// acc：可选，{id: {uid}}（来自 accounts_*.json），用于核对 core_user_id。
export async function xtOne(page, id, { W, log = console.log, acc = {}, maxCandidates = 3 }) {
  const dir = `${W}/shots_mine/xingtu/${id}`;
  mkdirp(dir);
  const rec = { id, t: new Date().toISOString(), found: false };
  try {
    await page.evaluate(() => { window.__xt = []; });
    await page.fill(SEL, id, { clearFirst: true });
    await page.press(SEL, "Enter");
    await page.waitForTimeout(6000);
    const caps = await page.evaluate(() => (window.__xt || []).filter((c) => c.req.includes("keyword")));
    const last = caps[caps.length - 1];
    let j = null;
    try { j = JSON.parse(last.body); } catch (e) {}
    const authors = j ? (j.authors || []).slice(0, 5).map((a) => a.attribute_datas) : [];
    rec.search = j ? { total: j.pagination && j.pagination.total_count, authors } : { err: "no search capture", n: caps.length };
    rec.searchText = await page.evaluate(() => (document.body.innerText.replace(/\s+/g, " ").match(/找到.{0,600}/) || [""])[0]).catch(() => "");
    await page.evaluate(() => { const el = [...document.querySelectorAll("*")].find((e) => e.children.length < 3 && /^找到\s*\d/.test((e.textContent || "").trim())); if (el) el.scrollIntoView({ block: "start" }); }).catch(() => {});
    await page.waitForTimeout(800);
    await page.screenshot({ path: `${dir}/01-search.png` });
    log(id, "xt search total", rec.search.total, authors.map((a) => `${a.nick_name}/${a.follower}/${a.core_user_id}`).join(" | "));

    const uid = acc[id] && acc[id].uid ? String(acc[id].uid) : null;
    let hit = null, hitBase = null, firstBase = null;
    for (const [k, a] of authors.slice(0, maxCandidates).entries()) {
      if (uid && String(a.core_user_id) === uid) { hit = a; rec.match = "core_user_id"; break; }
      const b = await getApi(page, baseUrl(a.id));
      if (k === 0) firstBase = b;
      if (b.b && typeof b.b === "object" && String(b.b.unique_id || "").toLowerCase() === id.toLowerCase()) { hit = a; hitBase = b; rec.match = "unique_id"; break; }
      await page.waitForTimeout(300);
    }
    if (hit) {
      rec.found = true;
      rec.search.authors = [hit, ...authors.filter((a) => a !== hit)];
      const aid = (rec.aid = hit.id);
      rec.api = { base: hitBase || (await getApi(page, baseUrl(aid))) };
      for (const [k, u] of Object.entries(apis(aid))) { rec.api[k] = await getApi(page, u); await page.waitForTimeout(250); }
      log(id, "xt api", Object.entries(rec.api).map(([k, v]) => `${k}:${v.s}`).join(" "));
      await page.goto(`https://www.xingtu.cn/ad/creator/author-homepage/douyin-video/${aid}`, { timeout: 40000 }).catch((e) => log("goto home err", String(e).slice(0, 120)));
      await page.waitForTimeout(8000);
      await page.screenshot({ path: `${dir}/02-home.png` });
      await page.screenshot({ path: `${dir}/03-home-full.png`, fullPage: true }).catch((e) => log("full err", String(e).slice(0, 80)));
      rec.homeText = await page.evaluate(() => document.body.innerText.replace(/\s+/g, " ").slice(0, 4000)).catch(() => "");
      const tabs = await page.evaluate(() => [...document.querySelectorAll("*")].filter((e) => e.children.length === 0 && /^(连接用户|粉丝画像|观众画像|受众画像|商业能力|种草价值|转化价值)$/.test((e.textContent || "").trim())).map((e) => e.textContent.trim())).catch(() => []);
      rec.tabs = tabs;
      let ti = 0;
      for (const t of [...new Set(tabs)].filter((t) => /画像|连接用户/.test(t))) {
        try { await page.click(`text=${t}`, { label: `查看${t}` }); await page.waitForTimeout(3000); await page.screenshot({ path: `${dir}/04-tab-${++ti}.png` }); } catch (e) { log(id, "tab err", t, String(e).slice(0, 80)); }
      }
      await openMarket(page, log);
    } else {
      if (authors[0]) { rec.aid = authors[0].id; rec.api = { base: firstBase || (await getApi(page, baseUrl(authors[0].id))) }; }
      log(id, "星图未找到（搜索结果的抖音号都不一致）");
    }
  } catch (e) {
    rec.err = String(e).slice(0, 300);
    log(id, "xt ERR", rec.err);
    await openMarket(page, log).catch(() => {});
  }
  writeJson(`${W}/xingtu_data/${id}.json`, rec, 0);
  return { ok: !rec.err, found: rec.found, aid: rec.found ? rec.aid : null };
}

export const hasXt = (W, id) => fs.existsSync(`${W}/xingtu_data/${id}.json`);
