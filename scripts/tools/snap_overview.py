"""总览完整截图（给对接方转交）：<PREVIEW_DIR>/progress/overview-full.jpg。

用法：python scripts/tools/snap_overview.py --config <batch.json> [源 HTML]
  默认源文件：简约模式用 report.html，完整模式用 report-full.html。
  截的是“一、总览”整节（宽表 + 总览图表），宽表按原始设计宽度展开、不缩放。
"""
import os, re, subprocess, sys, tempfile
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
args = [a for a in sys.argv[1:] if not a.startswith("-")]
SRC = Path(args[0]) if args else B.P / ("report-full.html" if B.mode == "full" else "report.html")
if not SRC.is_absolute():
    SRC = B.P / SRC
OUT_HTML = B.P / "overview-snapshot.html"
PNG = B.W / "overview-full.png"
JPG = B.P / "progress" / "overview-full.jpg"
JPG.parent.mkdir(parents=True, exist_ok=True)

html = SRC.read_text(encoding="utf-8")
head = re.search(r"<head>.*?</head>", html, re.S).group(0)
body = re.search(r"<body[^>]*>(.*)</body>", html, re.S).group(1)
start = body.find('<section id="overview-table"')
h2s = [m.start() for m in re.finditer(r"<h2", body)]
before = [p for p in h2s if p < start]
sec_start = before[-1] if before else start
after = [p for p in h2s if p > start]
sec_end = after[0] if after else len(body)
part = body[sec_start:sec_end]

override = """<style>
html,body{background:#fff!important;margin:0}
.snap{padding:28px 36px;width:max-content;min-width:1400px}
.snap *{overflow:visible!important;max-height:none!important}
.snap [style*="sticky"],.snap th,.snap td{position:static!important}
.snap table{width:auto!important}
.snap details{display:block}
</style>"""
OUT_HTML.write_text(
    f"<!doctype html><html>{head.replace('</head>', override + '</head>')}<body><div class='snap'>{part}</div>"
    "<script>document.querySelectorAll('details').forEach(d=>d.open=true);"
    "document.querySelectorAll('img[loading]').forEach(i=>i.removeAttribute('loading'));</script></body></html>",
    encoding="utf-8")

URL = B.link("overview-snapshot.html")
edge = config.edge_path(B)
if edge:
    with tempfile.TemporaryDirectory(prefix="dy-snap-") as prof:
        subprocess.run([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={prof}",
                        "--force-device-scale-factor=1.5", "--window-size=2300,4200",
                        "--virtual-time-budget=6000", f"--screenshot={PNG}", URL], timeout=120)
else:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = config.launch_browser(p)
        pg = b.new_page(viewport={"width": 2300, "height": 4200}, device_scale_factor=1.5)
        pg.goto(URL, wait_until="networkidle")
        pg.screenshot(path=str(PNG))
        b.close()

im = Image.open(PNG).convert("RGB")
gray = im.convert("L").point(lambda v: 255 if v < 250 else 0)
bbox = gray.getbbox()
if bbox:
    l, t, r, b = bbox
    im = im.crop((max(0, l - 30), max(0, t - 30), min(im.width, r + 30), min(im.height, b + 30)))
im.save(JPG, quality=88)
os.remove(PNG)
print("saved", JPG, im.size)
