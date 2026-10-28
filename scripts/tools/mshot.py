"""按手机（或桌面）宽度分段截图，并检查横向溢出：打印 scrollWidth 和溢出元素，截图存 <PREVIEW_DIR>/progress/<TAG>-NN.jpg。

用法：python scripts/tools/mshot.py --config <batch.json> [网址或文件] [TAG] [宽度] [起始选择器] [最多段数]
  默认检查 <PREVIEW_DIR>/report.html、TAG=mobile、宽度 390。本地文件会转成 file:// 地址。
  例：python scripts/tools/mshot.py --config batch.json report.html m 390 "#overview" 2
验收：overflowing: 0。环境变量 MSHOT_SCALE 控制截图缩放（默认 0.5）。
"""
import sys, os
from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()


def to_url(x):
    if x.startswith(("http://", "https://", "file:")):
        return x
    p = Path(x)
    if not p.is_absolute():
        p = (B.P / x) if (B.P / x).exists() else p.resolve()
    return p.as_uri()


args = sys.argv[1:]
URL = to_url(args[0]) if len(args) > 0 else B.link("report.html")
TAG = args[1] if len(args) > 1 else "mobile"
W = int(args[2]) if len(args) > 2 else 390
START = args[3] if len(args) > 3 else None
MAXSEG = int(args[4]) if len(args) > 4 else 999
OUT = str(B.P / "progress")
os.makedirs(OUT, exist_ok=True)
VH = 1200
SCALE = float(os.environ.get("MSHOT_SCALE", "0.5"))

with sync_playwright() as p:
    b = config.launch_browser(p)
    ctx = b.new_context(viewport={"width": W, "height": VH}, device_scale_factor=2, is_mobile=W < 700, has_touch=W < 700)
    pg = ctx.new_page()
    pg.goto(URL, wait_until="networkidle", timeout=60000)
    pg.evaluate("""async () => {for (let y=0; y<document.body.scrollHeight; y+=900){window.scrollTo(0,y); await new Promise(r=>setTimeout(r,40));} window.scrollTo(0,0);}""")
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(600)
    sw = pg.evaluate("document.documentElement.scrollWidth")
    over = pg.evaluate("""() => {const W=document.documentElement.clientWidth;const r=[];
      const ov=e=>{const b=e.getBoundingClientRect();return b.width>0&&b.right>W+1;};
      const hidden=e=>{for(let a=e;a&&a!==document.body;a=a.parentElement){const c=getComputedStyle(a);
        if(c.clip==='rect(0px, 0px, 0px, 0px)'||(c.overflow==='hidden'&&a.getBoundingClientRect().width<=1))return true;}return false;};
      for (const e of document.querySelectorAll('main *')) {
        if (!ov(e) || (e.parentElement && ov(e.parentElement)) || hidden(e)) continue;
        const sec=e.closest('section[id]');const cls=typeof e.className==='string'?e.className:'';
        r.push((sec?sec.id:'-')+' '+e.tagName+'.'+cls.slice(0,30)+' w='+Math.round(e.getBoundingClientRect().width)+' '+(e.innerText||'').slice(0,30).replace(/\\s+/g,' '));}
      return r;}""")
    print("scrollWidth", sw, "overflowing:", len(over))
    for o in over[:60]:
        print("  ", o)
    total = pg.evaluate("document.documentElement.scrollHeight")
    y0 = 0
    if START:
        y0 = int(pg.evaluate(f"(()=>{{const e=document.querySelector('{START}');return e?e.getBoundingClientRect().top+window.scrollY:0;}})()"))
    pg.add_style_tag(content=".mnav{display:none!important}")
    n = 0
    for y in range(y0, total, VH):
        if n >= MAXSEG:
            break
        pg.evaluate(f"window.scrollTo(0,{y})")
        pg.wait_for_timeout(120)
        n += 1
        path = os.path.join(OUT, f"{TAG}-{n:02d}.png")
        pg.screenshot(path=path)
        im = Image.open(path).convert("RGB")
        im = im.resize((int(im.width * SCALE), int(im.height * SCALE)))
        im.save(path[:-4] + ".jpg", quality=82)
        os.remove(path)
    b.close()
print("height", total, "segments", n)
