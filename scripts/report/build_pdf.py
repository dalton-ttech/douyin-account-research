"""完整模式 A4 PDF：<PREVIEW_DIR>/report-a4.pdf（封面、带页码可点击目录、总览宽表单独排 A4 横向页、每号从新一页开始）。

用法：python scripts/report/build_pdf.py --config <batch.json> [--no-pages]
源文件是 build_full.py 生成的 report-full.html；中间文件 report-print.html。
用 Edge 命令行无头打印（找不到 Edge 时退回 Playwright），跑两遍：第二遍把 PyMuPDF 找到的页码填进目录。
"""
import re, subprocess, sys, tempfile, html as H
from pathlib import Path
import fitz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
D = B.P
SRC, OUT, PDF = D / "report-full.html", D / "report-print.html", D / "report-a4.pdf"
URL = B.link("report-print.html")
EDGE = config.edge_path(B)
NO_PAGES = "--no-pages" in sys.argv

src = SRC.read_text(encoding="utf-8")
strip = lambda s: re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", "", s))).strip()

chapters = [(m.group(1), strip(m.group(2))) for m in
            re.finditer(r'<section id="([^"]+)"><h2>(.*?)</h2>', src)]
accts = []
for m in re.finditer(r'<section class="acct[^"]*" id="([^"]+)">\s*<h2[^>]*>(.*?)</h2>', src, re.S):
    g = re.search(r'class="g [^"]*">([A-Z—])<', m.group(2))
    dy = re.search(r'抖音号\s*([^<\s]+)', m.group(2))
    name = strip(re.sub(r'<span class="g[^"]*">.*?</span>|<small.*?</small>', "", m.group(2)))
    accts.append((m.group(1), name, dy.group(1) if dy else "", g.group(1) if g else ""))

# “一、总览”标题和宽表放在同一个横向命名页上：只给宽表设横向页时，标题会单独留在竖版页上，下面空出大半页。
# 其余内容显式用竖版命名页，否则 Chromium 会让总览小节里宽表后面的图表也沿用横向页。
# 目录排在报告开头的一句话结论后面，同一页，避免结论单独占一页。
CSS = """
@page{size:A4 portrait;margin:14mm}
@page portrait{size:A4 portrait;margin:14mm}
@page landscape{size:A4 landscape;margin:12mm}
main>*,#overview>*{page:portrait}
#overview>h2,#overview-table{page:landscape}
html,body{-webkit-print-color-adjust:exact;print-color-adjust:exact}
body{color:#1F2329}
.pc-cover{break-after:page;page-break-after:always}
main>p.toc{display:none}
.pc-toc{margin-top:18px}
.pc-cover{padding-top:60mm}
.pc-cover h1{font-size:30px;margin:0 0 10px;color:#1F2329}
.pc-cover .line{height:2px;background:#3370FF;width:100%;margin:14px 0 18px}
.pc-cover .sub{font-size:18px;color:#3370FF;margin:0 0 6px}
.pc-cover .date{color:#646A73;margin:0 0 26px}
.pc-cover table,.pc-toc table{border-collapse:collapse;width:100%;font-size:13px}
.pc-cover td,.pc-cover th{border-bottom:1px solid #DEE0E3;padding:6px 8px;text-align:left}
.pc-cover th{color:#646A73;font-weight:500}
.pc-cover .src{margin-top:22px;font-size:12px;color:#646A73}
.pc-cover .tag{display:inline-block;margin-top:14px;border:1px solid #3370FF;color:#3370FF;padding:2px 10px;font-size:12px}
.pc-toc h1{font-size:22px;border-bottom:2px solid #3370FF;padding-bottom:8px}
.pc-toc td{padding:6px 4px;border-bottom:1px dotted #DEE0E3}
.pc-toc td.pg{text-align:right;width:40px;color:#646A73}
.pc-toc a{color:#1F2329;text-decoration:none}
.pc-toc tr.acc td:first-child{padding-left:22px}
section.acct{break-before:page;page-break-before:always}
img,figure,.figs figure,.card,table tr,svg,canvas,.chart{break-inside:avoid;page-break-inside:avoid}
h2,h3,h4,h5{break-after:avoid;page-break-after:avoid}
img{max-width:100%}
svg{max-width:100%!important;height:auto!important}
#overview-charts svg,[data-chart="timeline"],[data-chart="timeline"] svg{break-inside:avoid;page-break-inside:avoid}
*{overflow:visible!important}
[style*=sticky],thead,th,td,tr{position:static!important}
#overview>h2{margin-top:0}
#overview-table{margin-top:4px!important}
main{max-width:none!important}
#overview-table,#overview-table *{max-width:100%!important;max-height:none!important}
#overview-table .ovt-who{display:block!important}
#overview-table table{width:100%!important;min-width:0!important;table-layout:fixed!important;font-size:9px!important}
#overview-table th,#overview-table td{white-space:normal!important;word-break:break-word;overflow-wrap:anywhere;min-width:0!important;width:auto!important;padding:3px 4px!important;font-size:9px!important}
#overview-table td img{max-width:40px!important;max-height:40px!important;width:auto!important;height:auto!important}
details>summary{list-style:none}
.lightbox,.zoom,.modal,[class*=tooltip],.no-print{display:none!important}
tbody tr:hover td{background:inherit!important}
"""


def build(pages=None):
    pg = lambda i: (str(pages.get(i, "")) if pages else "")
    rows = "".join(f"<tr><td>{H.escape(n)}</td><td>{H.escape(d)}</td><td>{g}</td></tr>" for _, n, d, g in accts)
    cover = f"""<div class="pc-cover"><h1>{H.escape(B.text("cover_title", n=len(accts)))}</h1><div class="line"></div>
<p class="sub">{H.escape(B.text("cover_subtitle", n=len(accts)))}</p><p class="date">{H.escape(B.date)}</p>
<table><tr><th>昵称</th><th>抖音号</th><th>评级</th></tr>{rows}</table>
<p class="src">数据来源：{H.escape(B.text("cover_sources"))}</p><span class="tag">内部资料</span></div>"""
    toc = "".join(f'<tr><td><a href="#{i}">{H.escape(t)}</a></td><td class="pg">{pg(i)}</td></tr>' for i, t in chapters if i != "detail")
    toc += "".join(f'<tr class="acc"><td><a href="#{i}">{g} · {H.escape(n)}（{H.escape(d)}）</a></td><td class="pg">{pg(i)}</td></tr>'
                   for i, n, d, g in accts)
    tochtml = f'<div class="pc-toc"><h1>目录</h1><table>{toc}</table></div>'
    s = src.replace(' loading="lazy"', "")
    s = re.sub(r"<details(?![^>]*\bopen\b)", "<details open", s)
    s = re.sub(r'\s(onclick|title)="[^"]*"', "", s)
    s = re.sub(r"position\s*:\s*(-webkit-)?sticky", "position:static", s)
    s = s.replace("</head>", f"<style media='print'>{CSS}</style></head>", 1)
    s = s.replace("<main>", "<main>" + cover, 1)
    s = s.replace('<section id="overview">', tochtml + '<section id="overview">', 1)
    OUT.write_text(s, encoding="utf-8")
    if EDGE:
        with tempfile.TemporaryDirectory(prefix="dy-pdf-") as prof:
            subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                            f"--user-data-dir={prof}", "--virtual-time-budget=15000", f"--print-to-pdf={PDF}", URL], timeout=180)
    else:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = config.launch_browser(p)
            page = b.new_page()
            page.goto(URL, wait_until="networkidle", timeout=120000)
            page.pdf(path=str(PDF), format="A4", print_background=True, prefer_css_page_size=True)
            b.close()


def find_pages():
    doc = fitz.open(PDF); res = {}
    keys = [(i, t) for i, t in chapters] + [(i, f"{n} 抖音号 {d}") for i, n, d, _ in accts]
    for i, key in keys:
        probe = key.split(" 抖音号")[0] if i.startswith("a-") else key
        alt = key.split("抖音号 ")[-1] if i.startswith("a-") else None
        start = res.get("detail", 3) - 1 if alt else 2
        for p in range(start, len(doc)):
            txt = doc[p].get_text()
            if (alt and f"抖音号 {alt}" in txt and probe in txt) or (not alt and probe in txt):
                res[i] = p + 1; break
    return res


build()
if not NO_PAGES:
    build(find_pages())
doc = fitz.open(PDF)
print("pages", len(doc), "size", PDF.stat().st_size, "engine", "edge" if EDGE else "playwright")
print("p1", doc[0].get_text()[:40].replace("\n", " "), "| p2", doc[1].get_text()[:20].replace("\n", " "))
(D / "progress").mkdir(exist_ok=True)
for n in (1, 3, 4):
    if n <= len(doc):
        doc[n - 1].get_pixmap(dpi=70).save(str(D / "progress" / f"pdf-p{n}.jpg"), jpg_quality=70)
