// 采集代理的通用执行器。由 make_run.py 生成的轮次脚本调用：
//   const { runAgent } = await import("file:///.../scripts/collect/run_agent.mjs");
//   await runAgent({ W, P, agent: "dy-A", kind: "dy", ids: [...], steps: [...], pace: {...} });
// ego 脚本拿不到 shell 的环境变量，所以参数都由 make_run.py 直接写进轮次脚本。
//
// 抖音（kind=dy）步骤：resolve（全部号先解析 sec_uid）→ 每号依次 posts、comments、fans、shots、assets。
// 星图（kind=xt）步骤：xingtu。
// 每个号开始前检查暂停开关、更新心跳；锁文件 done 里的号跳过；已有产出的步骤不重抓（force 时重抓）。
import { logger, enterSpace, heartbeat, isDone, markDone, checkPause, readJson, sleep, PauseError } from "./lib/common.mjs";
import { resolveIds } from "./dy_resolve.mjs";
import { profilePosts, hasProfilePosts } from "./dy_profile_posts.mjs";
import { comments, hasComments } from "./dy_comments.mjs";
import { fansSample, hasFans } from "./dy_fans.mjs";
import { shots, hasShots } from "./dy_shots.mjs";
import { assets, hasAssets } from "./dy_assets.mjs";
import { openMarket, xtOne, hasXt } from "./xt_collect.mjs";

// [执行函数, 产出是否已存在, 该步骤是否自己打开页面]；不自己打开页面的步骤要求当前页在抖音域名下（同源请求才会被签名）
const DY_STEPS = {
  posts: [profilePosts, hasProfilePosts, true],
  comments: [comments, hasComments, false],
  fans: [fansSample, hasFans, false],
  shots: [shots, hasShots, true],
  assets: [assets, hasAssets, false],
};

function accountsOf(W, agent) {
  return { ...(readJson(`${W}/accounts.json`, {}) || {}), ...(readJson(`${W}/accounts_${agent}.json`, {}) || {}) };
}

export async function runAgent(run) {
  const { W, agent, kind = "dy", ids = [], force = [] } = run;
  const steps = run.steps || (kind === "xt" ? ["xingtu"] : ["resolve", "posts", "comments", "fans", "shots", "assets"]);
  const pace = { req: 3000, account: 20000, search: 6000, retry: 15000, xt: 5000, ...(run.pace || {}) };
  const log = logger(`${W}/logs/${agent}-progress.log`);
  const ctx = { W, log, pace };
  const { task, page, mode, resumed } = await enterSpace(run);
  log("START", agent, `space=${task.spaceId} page=${page.label} mode=${mode} resumed=${resumed}`, "steps", steps.join(","), "ids", ids.join(","));
  const summary = {};
  try {
    if (kind === "xt") {
      await openMarket(page, log);
      const acc = accountsOf(W, agent.replace(/^xt-/, "dy-"));
      for (const id of ids) {
        if (isDone(W, agent, id) && !force.includes(id)) { log(id, "已完成，跳过"); continue; }
        heartbeat(W, agent, { current: id });
        if (hasXt(W, id) && !force.includes(id)) { markDone(W, agent, id); continue; }
        const r = await xtOne(page, id, { ...ctx, acc });
        summary[id] = r;
        if (r.ok) markDone(W, agent, id);
        await page.waitForTimeout(pace.xt + Math.floor(Math.random() * 1000));
      }
    } else {
      await page.goto("https://www.douyin.com/").catch(() => {});
      await page.waitForTimeout(3000);
      if (steps.includes("resolve")) {
        checkPause(W);
        await resolveIds(page, ids, { ...ctx, outFile: `${W}/accounts_${agent}.json` });
      }
      const acc = accountsOf(W, agent);
      const todo = steps.filter((s) => DY_STEPS[s]);
      for (const id of ids) {
        if (!todo.length) break;
        if (isDone(W, agent, id) && !force.includes(id)) { log(id, "已完成，跳过"); continue; }
        checkPause(W);
        heartbeat(W, agent, { current: id });
        const a = acc[id] || {};
        if (!a.sec_uid) { log(id, "缺 sec_uid，跳过（可从星图 need_sec_uid 或红狐 authorSecUid 补，或请用户提供主页链接）"); summary[id] = { err: "no sec_uid" }; continue; }
        const res = {};
        let allOk = true;
        for (const s of todo) {
          const [fn, has, navigates] = DY_STEPS[s];
          if (has(W, id) && !force.includes(id)) { res[s] = "已有"; continue; }
          checkPause(W);
          if (!navigates) {
            const url = await page.url().catch(() => "");
            if (!/douyin\.com/.test(url)) { await page.goto(`https://www.douyin.com/user/${a.sec_uid}`).catch(() => {}); await sleep(page, 4000); }
          }
          const r = await fn(page, id, a, ctx).catch((e) => { if (e instanceof PauseError || (e && e.constructor && e.constructor.name === "PauseError")) throw e; return { ok: false, err: String(e).slice(0, 200) }; });
          res[s] = r && r.ok ? "ok" : `失败 ${(r && r.err) || ""}`;
          if (!(r && r.ok)) allOk = false;
          if (s === "posts" && !(r && r.ok)) break;
          heartbeat(W, agent, { current: id, step: s });
          await sleep(page, pace.req);
        }
        summary[id] = res;
        log(id, "号完成", JSON.stringify(res));
        if (allOk) markDone(W, agent, id);
        await sleep(page, pace.account, 5000);
      }
    }
  } catch (e) {
    if (e instanceof PauseError || (e && e.constructor && e.constructor.name === "PauseError")) log("PAUSED", e.message, "（暂停开关只能由主代理在和用户确认后删除）");
    else log("ERR", String((e && e.stack) || e).slice(0, 500));
  } finally {
    heartbeat(W, agent, { current: null });
    if (run.handoff && mode === "A") {
      await page.close().catch(() => {});
      await task.handOff().catch((e) => log("handOff err", String(e).slice(0, 100)));
    }
    log("END", JSON.stringify(summary));
  }
  return summary;
}
