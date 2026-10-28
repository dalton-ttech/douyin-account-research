"""简约模式：把 parts/detail_m/acct_<id>.html 卡片详情替换进 report.html 的分账号小节，并加入 detail.css。

用法：python scripts/report/merge_detail.py --config <batch.json> [输出文件]
默认原地覆盖 <PREVIEW_DIR>/report.html；可先给一个临时输出文件检查。
必须是“替换数 = 号数，找不到：无，<section> 开/闭相等”。每次重新跑 mobile.py 后都要重跑本脚本。
"""
import os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
W, P = str(B.W), str(B.P)
args = [a for a in sys.argv[1:] if not a.startswith("-")]
OUT = args[0] if args else os.path.join(P, "report.html")
D = os.path.join(W, "parts", "detail_m")


def sec_end(h, s):
    d = 0
    for m in re.finditer(r"<(/?)section\b[^>]*>", h[s:]):
        d += -1 if m.group(1) else 1
        if d == 0:
            return s + m.end()
    raise ValueError("section 未闭合")


h = open(os.path.join(P, "report.html"), encoding="utf-8").read()
done, miss = [], []
for f in sorted(os.listdir(D)):
    m = re.fullmatch(r"acct_(.+)\.html", f)
    if not m:
        continue
    aid = m.group(1)
    s = h.find(f'<section class="acct" id="a-{aid}">')
    if s < 0:
        s = h.find(f'id="a-{aid}"')
        s = h.rfind("<section", 0, s) if s >= 0 else -1
    if s < 0:
        miss.append(aid)
        continue
    e = sec_end(h, s)
    h = h[:s] + open(os.path.join(D, f), encoding="utf-8").read().strip() + h[e:]
    done.append(aid)
h = h.replace("每个账号单独一节，依次为账号信息、首页截图、星图截图、数据与结论（含评级依据）。",
              "每个账号单独一节，依次为账号信息、首页截图、结论与评级依据、数据速览。", 1)
if 'id="detail-m-css"' not in h:
    css = open(os.path.join(D, "detail.css"), encoding="utf-8").read()
    h = h.replace("</head>", f'<style id="detail-m-css">\n{css}\n</style>\n</head>', 1)
open(OUT, "w", encoding="utf-8").write(h)
print("替换", len(done), "个号；报告里找不到：", miss or "无")
print("卡片小节", h.count('<section class="acct adet"'), "；<section> 开/闭", len(re.findall(r"<section\b", h)), "/", h.count("</section>"))
