// 抖音：用综合搜索把抖音号解析成 sec_uid（WORKFLOW 6.3 节）。
// 不要用 type=user 的用户搜索，会触发 verify_check。抓 general/search 流，逐行按 JSON 解析，
// 找带 sec_uid 的 user_info / author 对象，用 unique_id（不区分大小写）或 short_id 匹配。
import { installHook, waitCap, capBodies } from "./lib/hook.mjs";
import { readJson, writeJson, checkPause, setPause, sleep } from "./lib/common.mjs";

function parseStream(raw) {
  const objs = [];
  for (const line of String(raw || "").split(/\r?\n/)) {
    const s = line.trim();
    if (!s.startsWith("{")) continue;
    try { objs.push(JSON.parse(s)); } catch (e) {}
  }
  return objs;
}

function collectUsers(node, acc) {
  if (!node || typeof node !== "object") return;
  if (Array.isArray(node)) { node.forEach((n) => collectUsers(n, acc)); return; }
  if (node.user_info && node.user_info.sec_uid) acc.push(node.user_info);
  if (node.author && node.author.sec_uid) acc.push(node.author);
  for (const k of Object.keys(node)) if (typeof node[k] === "object") collectUsers(node[k], acc);
}

// outFile：W/accounts_<代理名>.json。已解析到的号跳过；每解析一个号就写盘。
export async function resolveIds(page, ids, { W, outFile, log = console.log, pace = {} }) {
  const out = readJson(outFile, {}) || {};
  for (const id of ids) {
    if (out[id] && out[id].found) continue;
    checkPause(W);
    await installHook(page);
    await page.goto(`https://www.douyin.com/search/${encodeURIComponent(id)}?type=general`).catch(() => log(id, "search goto timeout"));
    await waitCap(page, "general/search", 15000);
    await page.waitForTimeout(3000);
    const bodies = await capBodies(page, "general/search");
    const nil = bodies.map((b) => (b.match(/"search_nil_type":"([^"]+)"/) || [])[1]).filter(Boolean);
    const users = [];
    for (const b of bodies) for (const o of parseStream(b)) collectUsers(o, users);
    const low = id.toLowerCase();
    const hit = users.find((u) => (u.unique_id || "").toLowerCase() === low || String(u.short_id) === id);
    if (hit) {
      out[id] = {
        found: true, nickname: hit.nickname, unique_id: hit.unique_id, short_id: hit.short_id, uid: hit.uid, sec_uid: hit.sec_uid,
        follower_count: hit.follower_count, total_favorited: hit.total_favorited, aweme_count: hit.aweme_count,
      };
    } else {
      out[id] = {
        found: false, nil,
        candidates: [...new Map(users.map((u) => [u.uid, u])).values()].slice(0, 6).map((u) => [u.nickname, u.unique_id, u.short_id, u.follower_count]),
      };
    }
    log(id, "resolve", out[id].found ? `ok ${out[id].nickname}` : `未找到 nil=${nil.join(",")} 候选 ${out[id].candidates.length}`);
    writeJson(outFile, out);
    if (nil.includes("verify_check")) throw setPause(W, `${id} 综合搜索返回 verify_check`);
    await sleep(page, pace.search ?? 6000);
  }
  return out;
}
