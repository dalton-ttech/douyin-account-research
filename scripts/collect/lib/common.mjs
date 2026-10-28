// 采集脚本的公共工具：文件读写、日志、暂停开关、锁文件与心跳、进入 ego space、页面内请求。
// 在 ego-browser 的 nodejs 环境里运行；taskSpace / claimTaskSpace 是 ego 提供的全局函数。
import fs from "node:fs";
import path from "node:path";

export const BASE =
  "device_platform=webapp&aid=6383&channel=channel_pc_web&pc_client_type=1&version_code=170400&version_name=17.4.0&cookie_enabled=true&platform=PC";

export class PauseError extends Error {}

export const mkdirp = (p) => fs.mkdirSync(p, { recursive: true });

export function readJson(p, dflt = null) {
  try {
    return JSON.parse(fs.readFileSync(p, "utf8").replace(/^\uFEFF/, ""));
  } catch (e) {
    return dflt;
  }
}

export function writeJson(p, obj, indent = 1) {
  mkdirp(path.dirname(p));
  const tmp = `${p}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(obj, null, indent));
  fs.renameSync(tmp, p);
}

export function logger(file) {
  mkdirp(path.dirname(file));
  return (...a) => {
    const s = `[${new Date().toTimeString().slice(0, 8)}] ${a.map((x) => (typeof x === "string" ? x : JSON.stringify(x))).join(" ")}`;
    fs.appendFileSync(file, s + "\n");
    console.log(s);
  };
}

export const sleep = (page, ms, jitter = 800) => page.waitForTimeout(ms + Math.floor(Math.random() * jitter));

// ---------- 暂停开关：任何代理遇到验证码 / verify_check / 登录弹窗就写它，所有抖音代理开始每个号前都检查 ----------
export const pausePath = (W) => `${W}/locks/PAUSE-douyin.flag`;

export function checkPause(W) {
  if (fs.existsSync(pausePath(W))) throw new PauseError(`暂停开关存在：${pausePath(W)}，${fs.readFileSync(pausePath(W), "utf8").slice(0, 200)}`);
}

export function setPause(W, reason) {
  mkdirp(`${W}/locks`);
  if (!fs.existsSync(pausePath(W))) fs.writeFileSync(pausePath(W), `${new Date().toISOString()} ${reason}\n`);
  return new PauseError(reason);
}

// ---------- 锁文件：locks/<代理名>.json，记 space、页面标签、心跳、done 清单 ----------
export const lockPath = (W, agent) => `${W}/locks/${agent}.json`;

export function heartbeat(W, agent, patch = {}) {
  const p = lockPath(W, agent);
  const o = readJson(p, {}) || {};
  Object.assign(o, patch, { heartbeat: new Date().toISOString() });
  writeJson(p, o);
  return o;
}

export function isDone(W, agent, id) {
  return ((readJson(lockPath(W, agent), {}) || {}).done || []).includes(id);
}

export function markDone(W, agent, id) {
  const o = readJson(lockPath(W, agent), {}) || {};
  o.done = [...new Set([...(o.done || []), id])];
  heartbeat(W, agent, { done: o.done });
}

// 进入自己的 space（WORKFLOW 5.3 节）。模式 A：认领用户已建好的 space，在新开的页里工作；
// 模式 B：在指定 profile 下新建自己的 space（共享登录状态），用它自带的 p1。锁文件已存在时沿用原 space 和页面。
export async function enterSpace(run) {
  const { W, agent } = run;
  mkdirp(`${W}/locks`);
  const as = readJson(`${W}/locks/assignment.json`, null);
  const me = (as && as.agents && as.agents[agent]) || { space: run.space, space_id: run.space_id ?? null, profile: run.profile };
  const mode = (as && as.mode) || run.mode || "B";
  const old = readJson(lockPath(W, agent), null);
  for (const f of fs.readdirSync(`${W}/locks`).filter((n) => /^(dy|xt)-[\w]+\.json$/.test(n) && n !== `${agent}.json`)) {
    const o = readJson(`${W}/locks/${f}`, {}) || {};
    if (o.space === me.space || (o.spaceId != null && (o.spaceId === me.space_id || (old && o.spaceId === old.spaceId))))
      throw new Error(`space 已被 ${f} 占用，停止`);
  }
  const fresh = () =>
    mode === "A" ? globalThis.claimTaskSpace(me.space_id) : globalThis.taskSpace(me.space, me.profile ? { profileId: me.profile } : undefined);
  const task = old && old.spaceId != null ? await globalThis.taskSpace(old.spaceId).catch(fresh) : await fresh();
  const pages = await task.pages();
  const page = pages.find((p) => old && p.label === old.page) || (mode === "A" ? await task.newPage() : task.page("p1"));
  const now = new Date().toISOString();
  writeJson(lockPath(W, agent), {
    ...(old || {}), agent, mode, space: me.space, spaceId: task.spaceId, page: page.label,
    started: (old && old.started) || now, heartbeat: now, done: (old && old.done) || [],
  });
  return { task, page, mode, resumed: !!old };
}

// ---------- 页面内同源请求：抖音签名 SDK 会自动给页面内的 XHR 签名。不要设置 xhr.timeout，会和 SDK 冲突 ----------
export async function xget(page, url, timeoutMs = 30000) {
  const req = page
    .evaluate(
      (u) =>
        new Promise((resolve) => {
          const x = new XMLHttpRequest();
          x.open("GET", u, true);
          x.withCredentials = true;
          x.onload = () => resolve({ status: x.status, body: x.responseText });
          x.onerror = () => resolve({ status: -1, body: "" });
          x.send();
        }),
      url,
    )
    .catch((e) => ({ status: -3, body: String(e).slice(0, 200) }));
  const timer = new Promise((resolve) => setTimeout(() => resolve({ status: -2, body: "" }), timeoutMs));
  return Promise.race([req, timer]);
}

const VERIFY = /verify_check|captcha|verifycenter|secsdk_captcha/i;

// 返回 { j, code, body }：status_code 为 0 时 j 是解析后的对象；失败重试 retries 次，间隔 retryWait。
// 返回体里出现验证码 / verify_check 时写暂停开关并抛出 PauseError。
export async function getJson(page, url, { W, retries = 2, retryWait = 15000, log = console.log, okCodes = [0] } = {}) {
  let last = { j: null, code: null, body: "" };
  for (let k = 0; k < retries; k++) {
    const r = await xget(page, url);
    if (VERIFY.test(r.body || "")) throw setPause(W, `接口返回验证码：${url.split("?")[0]}`);
    try {
      const j = JSON.parse(r.body);
      if (okCodes.includes(j.status_code)) return { j, code: j.status_code, body: r.body };
      last = { j: null, code: j.status_code, body: r.body };
      log("  status_code", j.status_code, (j.status_msg || "").slice(0, 80));
      if (j.status_code === 2096) return last;
    } catch (e) {
      last = { j: null, code: r.status, body: r.body };
      log("  parse fail", r.status, (r.body || "").slice(0, 120));
    }
    if (k < retries - 1) await page.waitForTimeout(retryWait);
  }
  return last;
}

// 页面上出现登录弹窗或验证码时写暂停开关（WORKFLOW 6.2 节）。
export async function checkBlockers(page, W, where) {
  const t = await page
    .evaluate(() => {
      const s = document.body ? document.body.innerText.slice(0, 4000) : "";
      const cap = !!document.querySelector('[id*="captcha"],[class*="captcha"],iframe[src*="verify"]');
      return { cap, login: /扫码登录|登录后即可|请先登录/.test(s) && !!document.querySelector('[id*="login"],[class*="login-panel"],[class*="login-modal"]') };
    })
    .catch(() => ({}));
  if (t.cap) throw setPause(W, `${where} 出现验证码`);
  if (t.login) throw setPause(W, `${where} 出现登录弹窗`);
}

export const cst = (t) => (t ? new Date(t * 1000 + 8 * 3600e3).toISOString().slice(0, 16).replace("T", " ") : null);
export const dayStartTs = (d) => Math.floor(new Date(d + "T00:00:00+08:00").getTime() / 1000);
