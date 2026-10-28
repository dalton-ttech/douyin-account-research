"""把 parts/ 下的总览表、总览图表、各账号图表合并进完整版报告。

build_full.py 会直接调用 merge()；也可以单独运行：
python scripts/report/merge_parts.py --config <batch.json>   # 原地合并 <PREVIEW_DIR>/report-full.html
"""
import os, re, sys, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

B = config.load()
PARTS = str(B.parts)
OUT = str(B.P / "report-full.html")


def rd(p):
    p = os.path.join(PARTS, p)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def sec_end(s, start):
    """从 start 处的 <section> 起按嵌套层级找到与它配对的 </section>，返回这个结束标签的起点。"""
    d = 0
    for m in re.finditer(r"<(/?)section\b[^>]*>", s[start:]):
        d += -1 if m.group(1) else 1
        if d == 0:
            return start + m.start()
    return -1


def merge(s):
    done = []
    css = ""
    ovt, ovcss = rd("overview_table.html"), rd("overview_table.css")
    if ovt:
        s, n = re.subn(r'<table class="sum">.*?</table>\s*<p class="muted">互动率 = .*?</p>', lambda m: ovt, s, count=1, flags=re.S)
        if n:
            done.append("总览表")
            css += (ovcss or "")
    ovc = rd(os.path.join("charts", "overview_charts.html"))
    if ovc and 'id="ov-charts-merged"' not in s:
        i = s.find('<section id="overview">')
        j = sec_end(s, i) if i >= 0 else -1
        if j > 0:
            s = s[:j] + f'<div id="ov-charts-merged">{ovc}</div>' + s[j:]
            done.append("总览图表")
    acct_n = 0
    for p in sorted(os.listdir(os.path.join(PARTS, "charts"))) if os.path.isdir(os.path.join(PARTS, "charts")) else []:
        m = re.match(r"acct_(.+)\.html$", p)
        if not m:
            continue
        aid = m.group(1)
        frag = rd(os.path.join("charts", p))
        pat = re.compile(r'(<section class="acct" id="a-' + re.escape(aid) + r'">.*?<div class="kpis">.*?</div></div>)\s*<div class="charts">.*?</div>\s*(?=<h4>作品与互动</h4>)', re.S)
        s, n = pat.subn(lambda mm: mm.group(1) + f'<div class="acct-charts">{frag}</div>', s, count=1)
        acct_n += n
    if acct_n:
        done.append(f"账号图表 {acct_n} 个")
    ccss = rd(os.path.join("charts", "charts.css"))
    if ccss:
        css += ccss
    if css:
        s = s.replace("</style>", css + "\n</style>", 1)
    return s, done


if __name__ == "__main__":
    config.setup_stdout()
    s = open(OUT, encoding="utf-8").read()
    s, done = merge(s)
    open(OUT, "w", encoding="utf-8").write(s)
    open(os.path.join(PARTS, "INTEGRATED.flag"), "w", encoding="utf-8").write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("merged:", done)
