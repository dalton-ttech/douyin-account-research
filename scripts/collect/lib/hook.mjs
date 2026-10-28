// 抓包钩子：用 Page.addScriptToEvaluateOnNewDocument 注入 XHR / fetch 钩子，结果存在 window.__cap。
// 钩子只活在当前脚本进程里，每一轮都要在 goto 之前重新注入。
const KEEP =
  "aweme\\/v1\\/web\\/(user\\/profile\\/other|aweme\\/post|comment\\/list|aweme\\/detail|user\\/follower\\/list|user\\/following\\/list|comment\\/list\\/reply|general\\/search)";

export const HOOK = `(() => {
  if (window.__capHook) return; window.__capHook = true;
  window.__cap = [];
  const keep = new RegExp(${JSON.stringify(KEEP)});
  const oOpen = XMLHttpRequest.prototype.open;
  const oSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function (m, u) { this.__u = String(u); return oOpen.apply(this, arguments); };
  XMLHttpRequest.prototype.send = function () {
    this.addEventListener("load", () => {
      try { if (keep.test(this.__u)) window.__cap.push({ u: this.__u, b: this.responseText, t: Date.now() }); } catch (e) {}
    });
    return oSend.apply(this, arguments);
  };
  const oFetch = window.fetch;
  window.fetch = async function (input, init) {
    const res = await oFetch.apply(this, arguments);
    try {
      const u = typeof input === "string" ? input : input.url;
      if (keep.test(u)) res.clone().text().then((b) => window.__cap.push({ u, b, t: Date.now() }));
    } catch (e) {}
    return res;
  };
})();`;

export async function installHook(page) {
  await page.cdp("Page.enable").catch(() => {});
  await page.cdp("Page.addScriptToEvaluateOnNewDocument", { source: HOOK });
}

export async function waitCap(page, frag, timeout = 15000, minCount = 1) {
  await page
    .waitForFunction(({ f, n }) => (window.__cap || []).filter((c) => c.u.includes(f)).length >= n, { f: frag, n: minCount }, { timeout })
    .catch(() => {});
  return capBodies(page, frag);
}

export async function capBodies(page, frag) {
  return page.evaluate((f) => (window.__cap || []).filter((c) => c.u.includes(f)).map((c) => c.b), frag).catch(() => []);
}

export async function capCount(page, frag) {
  return page.evaluate((f) => (window.__cap || []).filter((c) => c.u.includes(f)).length, frag).catch(() => 0);
}

// 用已抓到的同类请求当模板复制公共参数，在页面里发同源 XHR（签名由页面 SDK 自动加）。
// 不设置 xhr.timeout（会和签名 SDK 冲突），超时在 Node 侧用 Promise.race 处理。
export async function pageApi(page, path, params, tplFrag = "aweme/post", timeoutMs = 30000) {
  const req = page.evaluate(
    async ({ path, params, tplFrag }) => {
      const caps = window.__cap || [];
      const tpl = caps.find((c) => c.u.includes(tplFrag)) || caps.find((c) => c.u.includes("aweme/v1/web"));
      const base = tpl ? new URL(tpl.u, location.origin) : new URL(location.origin);
      const u = new URL(path, location.origin);
      for (const [k, v] of base.searchParams) {
        if (["a_bogus", "X-Bogus", "sec_user_id", "max_cursor", "count", "aweme_id", "cursor", "offset", "user_id"].includes(k)) continue;
        u.searchParams.set(k, v);
      }
      for (const [k, v] of Object.entries(params)) u.searchParams.set(k, String(v));
      const body = await new Promise((resolve) => {
        const x = new XMLHttpRequest();
        x.open("GET", u.pathname + u.search, true);
        x.withCredentials = true;
        x.onload = () => resolve(x.responseText);
        x.onerror = () => resolve("");
        x.send();
      });
      return { len: body.length, body, hasTpl: !!tpl };
    },
    { path, params, tplFrag },
  ).catch((e) => ({ len: 0, body: "", err: String(e).slice(0, 200) }));
  const timer = new Promise((resolve) => setTimeout(() => resolve({ len: 0, body: "", err: "timeout" }), timeoutMs));
  return Promise.race([req, timer]);
}
