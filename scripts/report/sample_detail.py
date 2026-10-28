"""简约模式单号页数检查：把一个账号的卡片详情单独做成 <tag>.html、<tag>-print.html、<tag>.pdf（390×844）和每页预览图。

用法：python scripts/report/sample_detail.py --config <batch.json> [抖音号] [tag]
不给抖音号时取清单里第一个能定位的号；tag 默认 sample-detail。末尾打印 pages N，每号都要 ≤2。
依赖 report.html（mobile.py 生成）和 parts/detail_m/（build_detail_m.py 生成）。
"""
import sys
from pathlib import Path
import fitz
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
D = B.P
HERE = B.parts
args = [a for a in sys.argv[1:] if not a.startswith("-")]
if args:
    aid = args[0]
else:
    aid = next((i for i in config.account_ids(B) if (HERE / "detail_m" / f"acct_{i}.html").exists()), None)
    if not aid:
        raise SystemExit("parts/detail_m 里还没有卡片详情，先运行 build_detail_m.py")
tag = args[1] if len(args) > 1 else "sample-detail"

rep = (D / "report.html").read_text(encoding="utf-8")
head = rep[:rep.index("<main>")]
css = (HERE / "detail_m" / "detail.css").read_text(encoding="utf-8")
sec = (HERE / "detail_m" / f"acct_{aid}.html").read_text(encoding="utf-8")
html = head.replace("</style>", css + "</style>", 1) + "<main>" + sec + "</main></body></html>"
(D / f"{tag}.html").write_text(html, encoding="utf-8")

M = (HERE / "mobile_layer.css").read_text(encoding="utf-8")
PCSS = M + """
@page{size:390px 844px;margin:16px 16px 26px}
html,body{background:#fff!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
main{padding:0!important}
a{color:inherit;text-decoration:none}
figure>a::after{display:none!important}
section.acct{break-before:auto}
h2,h3,.ad-sub,.ad-bh{break-after:avoid;page-break-after:avoid}
.acard,.ad-shot,.bt-t,.qk,.ev-row,.chv-fig,.ad-vh,.ad-risk,.listing,li{break-inside:avoid;page-break-inside:avoid}
"""
FOOT = '<div style="width:100%;font-size:8px;color:#8F959E;text-align:center;font-family:Microsoft YaHei,sans-serif"><span class="pageNumber"></span> / <span class="totalPages"></span></div>'
pr = html.replace(' loading="lazy"', "").replace("</head>", f"<style>{PCSS}</style></head>", 1)
(D / f"{tag}-print.html").write_text(pr, encoding="utf-8")
pdf = D / f"{tag}.pdf"
with sync_playwright() as p:
    b = config.launch_browser(p)
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.goto(B.link(f"{tag}-print.html"), wait_until="networkidle")
    pg.wait_for_timeout(500)
    pg.pdf(path=str(pdf), width="390px", height="844px", print_background=True, prefer_css_page_size=True,
           display_header_footer=True, header_template="<span></span>", footer_template=FOOT,
           margin={"top": "16px", "bottom": "26px", "left": "16px", "right": "16px"})
    b.close()
doc = fitz.open(str(pdf))
(D / "progress").mkdir(exist_ok=True)
for i, page in enumerate(doc):
    page.get_pixmap(dpi=144).save(str(D / "progress" / f"{tag}-p{i + 1}.jpg"), jpg_quality=82)
print(aid, "pages", len(doc))
