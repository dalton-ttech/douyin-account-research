"""简约模式手机 PDF：<PREVIEW_DIR>/report.pdf（390×844 CSS px），带首页、目录（页码可点击）和页脚页码。

用法：python scripts/report/build_pdf_m.py --config <batch.json>
源文件为 mobile.py + merge_detail.py 处理后的 report.html；中间文件 report-print-m.html。
总览“一、总览”标题和宽表单独排在 844×390 的横屏页（@page wide），宽表整体缩放到页宽；
其余内容显式用竖屏命名页 tall，否则 Chromium 会让宽表后面的总览图表也沿用横屏页。
页边距与 sample_detail.py 相同，所以每号页数与单号检查一致（每号不超过 2 页）。
"""
import re, sys, html as H
from pathlib import Path
import fitz
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
D = B.P
SRC, OUT, PDF = D / "report.html", D / "report-print-m.html", D / "report.pdf"
URL = B.link("report-print-m.html")
M = (B.parts / "mobile_layer.css").read_text(encoding="utf-8")
_, NOTES = config.load_qual(B)
WIDE_W, WIDE_H, WIDE_M = 844, 390, 12
OVT_PRINT_W = 1032

src = SRC.read_text(encoding="utf-8")
strip = lambda s: re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", "", s))).strip()
chapters = [(m.group(1), strip(m.group(2))) for m in re.finditer(r'<section id="([^"]+)"><h2>(.*?)</h2>', src)]
accts = []
for m in re.finditer(r'<section class="acct[^"]*" id="([^"]+)">\s*<h2[^>]*>(.*?)</h2>', src, re.S):
    g = re.search(r'class="g [^"]*">([A-Z—])<', m.group(2))
    dy = re.search(r"抖音号\s*([^<\s]+)", m.group(2))
    name = strip(re.sub(r'<span class="g[^"]*">.*?</span>|<small.*?</small>', "", m.group(2)))
    accts.append((m.group(1), name, dy.group(1) if dy else "", g.group(1) if g else ""))

PCSS = M + """
@page{size:390px 844px;margin:16px 16px 26px}
@page tall{size:390px 844px;margin:16px 16px 26px}
@page wide{size:__WW__px __WH__px;margin:__WM__px}
main>*,#overview>*{page:tall}
#overview>h2,#overview-table{page:wide}
#overview>h2{margin-top:0}
#overview-table .ovt-box{width:__OW__px!important;zoom:__OZ__!important}
#overview-table .ovt-note{margin:2px 0 0!important;font-size:10.5px!important;line-height:1.4!important}
html,body{background:#fff!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
main{padding:0!important;max-width:none!important}
.mnav,.toc,figure>a::after{display:none!important}
a{color:inherit;text-decoration:none}
.pmk{font-size:1px;line-height:1px;color:#fff;display:block;height:1px;overflow:hidden}
section.acct{break-before:page;page-break-before:always}
#standard,#method,#cross{break-before:page}
#detail>h2+section.acct{break-before:auto;page-break-before:auto}
.verdict{padding-bottom:2px;margin-bottom:0}
table.stk tr:last-child{margin-bottom:0}
h2,h3,h4,.chv-title,.basis .bt,.ad-sub,.ad-bh{break-after:avoid;page-break-after:avoid}
figure,.chv-fig,.chart,.kpi,.verdict p,table.stk tr,table.kv tr,.ovt-section .ovt-table tbody tr,.listing,li{break-inside:avoid;page-break-inside:avoid}
.acard,.ad-shot,.bt-t,.qk,.ev-row,.ad-vh,.ad-risk{break-inside:avoid;page-break-inside:avoid}
img{max-width:100%}
.pc-cover,.pc-toc{break-after:page;page-break-after:always}
.pc-cover{padding-top:120px}
.pc-cover .k{font-size:12px;color:#3370FF;letter-spacing:2px;margin-bottom:12px}
.pc-cover h1{font-size:26px;line-height:1.35;margin:0 0 14px;color:#1F2329}
.pc-cover .line{height:3px;width:48px;background:#3370FF;border-radius:2px;margin:0 0 18px}
.pc-cover .sub{font-size:15px;color:#646A73;margin:0 0 4px}
.pc-cover .grades{display:flex;flex-wrap:wrap;gap:10px;margin:26px 0 22px}
.pc-cover .grades div{flex:1 1 40%;border-radius:10px;padding:12px 14px}
.pc-cover .grades b{display:block;font-size:24px;line-height:1.2}
.pc-cover .grades span{font-size:12px}
.pc-cover .gA{background:#D9F5D6;color:#237B19}.pc-cover .gB{background:#E1EAFF;color:#245BDB}
.pc-cover .gC{background:#FFF0C2;color:#B26A00}.pc-cover .gD{background:#FDE2E2;color:#D83931}.pc-cover .gN{background:#EFF0F1;color:#646A73}
.pc-cover .src{font-size:12px;color:#8F959E;line-height:1.7;margin-top:18px}
.pc-cover .tag{display:inline-block;margin-top:16px;border:1px solid #3370FF;color:#3370FF;border-radius:4px;padding:1px 10px;font-size:12px}
.pc-toc h1{font-size:22px;margin:0 0 14px;padding-bottom:10px;border-bottom:2px solid #1F2329}
.pc-toc a{display:flex;align-items:center;gap:8px;min-height:40px;border-bottom:1px solid #EFF0F1;color:#1F2329;font-size:14.5px}
.pc-toc a .t{flex:1}
.pc-toc a .p{color:#8F959E;font-size:13px;font-variant-numeric:tabular-nums}
.pc-toc .h{font-size:12px;color:#8F959E;margin:16px 0 2px}
.pc-toc .g{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;font-size:12px;font-weight:700;color:#fff}
.pc-toc .gC{background:#FFF0C2;color:#B26A00}.pc-toc .gD{background:#FDE2E2;color:#D83931}.pc-toc .gA{background:#D9F5D6;color:#237B19}.pc-toc .gB{background:#E1EAFF;color:#245BDB}.pc-toc .gN{background:#EFF0F1;color:#646A73}
.pc-toc .id{font-size:12px;color:#8F959E}
""".replace("__WW__", str(WIDE_W)).replace("__WH__", str(WIDE_H)).replace("__WM__", str(WIDE_M)) \
   .replace("__OW__", str(OVT_PRINT_W)).replace("__OZ__", f"{(WIDE_W - 2 * WIDE_M) / OVT_PRINT_W:.4f}")

FOOT = '<div style="width:100%;font-size:8px;color:#8F959E;text-align:center;font-family:Microsoft YaHei,sans-serif"><span class="pageNumber"></span> / <span class="totalPages"></span></div>'
GRADE_BOX = {"A": ("gA", "A 级：各项达标"), "B": ("gB", "B 级：基本健康，可议价"), "C": ("gC", "C 级：粉丝基本真实，可压价收"),
             "D": ("gD", "D 级：不建议购买"), "—": ("gN", "未评级：账号无法定位")}


def build(page, pages=None):
    pg = lambda i: str(pages.get(i, "")) if pages else ""
    n = len(accts)
    cnt = {g: sum(1 for a in accts if a[3] == g) for g in GRADE_BOX}
    boxes = "".join(f'<div class="{GRADE_BOX[g][0]}"><b>{cnt[g]} 个</b><span>{GRADE_BOX[g][1]}</span></div>' for g in GRADE_BOX if cnt[g])
    missing = [g for g in "AB" if not cnt[g]]
    head = NOTES.get("headline") or (f"{n} 个号里没有 {'、'.join(missing)} 级。" if missing else "")
    title = H.escape(B.text("title", n=n)).replace("：", "<br>")
    cover = f"""<div class="pc-cover"><div class="k">内部资料 · 采购参考</div><h1>{title}</h1><div class="line"></div>
<p class="sub">数据采集：{H.escape(B.date)}</p><p class="sub">{H.escape(B.text("cover_sources").replace("、", " · "))}</p>
<div class="grades">{boxes}</div>
<p class="src">{H.escape(head)}评级标准、每个号的截图佐证与评级依据见正文。</p><span class="tag">内部资料</span></div>"""
    toc = "".join(f'<a href="#{i}"><span class="t">{H.escape(t)}</span><span class="p">{pg(i)}</span></a>' for i, t in chapters if i != "detail")
    toc += '<div class="h">分账号详情</div>' + "".join(
        f'<a href="#{i}"><span class="g g{GRADE_BOX.get(g, ("gN",))[0][1:]}">{g}</span><span class="t">{H.escape(nm)} <span class="id">{H.escape(d)}</span></span><span class="p">{pg(i)}</span></a>'
        for i, nm, d, g in accts)
    tochtml = f'<div class="pc-toc"><h1>目录</h1>{toc}</div>'
    s = src.replace(' loading="lazy"', "")
    s = re.sub(r'\s(onclick|title)="[^"]*"', "", s)
    s = re.sub(r'<nav class="mnav".*?</nav>', "", s, flags=re.S)
    s = re.sub(r"<script>.*?</script>", "", s, flags=re.S)
    for i, _ in chapters:
        s = s.replace(f'<section id="{i}"><h2>', f'<section id="{i}"><h2><span class="pmk">[[pm{MARKS.index(i)}]]</span>', 1)
    for i, *_ in accts:
        s = re.sub(r'(<section class="acct[^"]*" id="' + re.escape(i) + r'">)', lambda m: m.group(1) + f'<span class="pmk">[[pm{MARKS.index(i)}]]</span>', s, count=1)
    s = s.replace("</head>", f"<style>{PCSS}</style></head>", 1)
    s = s.replace("<main>", "<main>" + cover + tochtml, 1)
    OUT.write_text(s, encoding="utf-8")
    page.goto(URL, wait_until="networkidle", timeout=120000)
    page.wait_for_timeout(800)
    page.pdf(path=str(PDF), width="390px", height="844px", print_background=True, prefer_css_page_size=True,
             display_header_footer=True, header_template="<span></span>", footer_template=FOOT,
             margin={"top": "16px", "bottom": "26px", "left": "16px", "right": "16px"})


MARKS = [i for i, _ in chapters] + [a[0] for a in accts]


def find_pages():
    """标记用序号而不是 id：1px 字号的文字提取会把抖音号里的下划线、点等符号丢掉。"""
    doc = fitz.open(str(PDF))
    res = {}
    for p in range(len(doc)):
        for n in re.findall(r"\[\[pm(\d+)\]\]", doc[p].get_text()):
            if int(n) < len(MARKS):
                res.setdefault(MARKS[int(n)], p + 1)
    return res


with sync_playwright() as p:
    b = config.launch_browser(p)
    page = b.new_page(viewport={"width": 390, "height": 844})
    build(page)
    pages = find_pages()
    build(page, pages)
    b.close()

doc = fitz.open(str(PDF))
print("pages", len(doc), "size", PDF.stat().st_size, "toc", pages)
ids = [a[0] for a in accts]
ends = [pages.get(x) for x in ids[1:]] + [len(doc) + 1]
span = {x: (e - pages[x]) if pages.get(x) and e else None for x, e in zip(ids, ends)}
print("每号页数", {x[2:]: v for x, v in span.items()}, "超过 2 页：", [x[2:] for x, v in span.items() if v and v > 2] or "无")
wide = [i + 1 for i in range(len(doc)) if doc[i].rect.width > doc[i].rect.height]
print("横屏页", wide)
prog = D / "progress"
prog.mkdir(exist_ok=True)
for n in (1, 2, 3, 4, 5):
    if n <= len(doc):
        doc[n - 1].get_pixmap(dpi=110).save(str(prog / f"pdfm-p{n}.jpg"), jpg_quality=80)
