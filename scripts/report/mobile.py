"""简约模式第一步：在完整版 report-full.html 的基础上生成手机优先的 report.html。

做的事：总览宽表按 1200px 设计宽度排版、再整体缩放到屏宽（不出现横向滚动条）；表格改为堆叠卡片；
换成手机尺寸图表；加悬浮目录。每次都从 report-full.html 重建，可重复运行。
用法：python scripts/report/mobile.py --config <batch.json>
"""
import os, re, sys, html as H
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
SRC = str(B.P / "report-full.html")
REPORT = str(B.P / "report.html")
CM = str(B.parts / "charts_m")
OVT_W = 1200

s = open(SRC, encoding="utf-8").read()
strip = lambda x: re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", "", x))).strip()
rd = lambda p: open(os.path.join(CM, p), encoding="utf-8").read()

s, n_ovc = re.subn(r'<div id="ov-charts-merged">.*?</section>\s*</div>', lambda _: '<div id="ov-charts-merged">' + rd("overview_charts.html") + "</div>", s, count=1, flags=re.S)

def swap_timeline(m):
    sec = m.group(0)
    aid = m.group(1)
    return re.sub(r'<div class="chart-block" data-chart="timeline">.*?</figure></div>', lambda _: rd(f"acct_{aid}.html"), sec, count=1, flags=re.S)
s, n_acct = re.subn(r'<section class="acct" id="a-([^"]+)">.*?(?=<section class="acct"|</main>)', swap_timeline, s, flags=re.S)

def stack(m):
    attrs, body = m.group(1), m.group(2)
    if "kv" in attrs or "ovt-table" in attrs:
        return m.group(0)
    hd = re.search(r"<tr[^>]*>(.*?)</tr>", body, re.S)
    heads = [strip(x) for x in re.findall(r"<th[^>]*>(.*?)</th>", hd.group(1), re.S)]
    if not heads:
        return m.group(0)
    res = heads[-1] == "结果"
    body = body[:hd.start()] + '<tr class="stk-hd">' + hd.group(1) + "</tr>" + body[hd.end():]

    def row(r):
        if r.group(0).startswith('<tr class="stk-hd"'):
            return r.group(0)
        i = [-1]

        def cell(c):
            i[0] += 1
            lab = heads[i[0]] if i[0] < len(heads) else ""
            if i[0] == 0 or not lab:
                return c.group(0)
            extra = ' data-lg="1"' if len(lab) > 5 else ""
            return f'<td data-l="{H.escape(lab, quote=True)}"{extra}' + c.group(1)
        return re.sub(r"<td((?:\s[^>]*)?>)", cell, r.group(0))
    body = re.sub(r"<tr[^>]*>.*?</tr>", row, body, flags=re.S)
    cls = "stk res" if res else "stk"
    if 'class="' in attrs:
        attrs = attrs.replace('class="', f'class="{cls} ', 1)
    else:
        attrs += f' class="{cls}"'
    return f"<table{attrs}>{body}</table>"
s, n_tab = re.subn(r"<table([^>]*)>(.*?)</table>", stack, s, flags=re.S)
n_stk = s.count('class="stk')

s = s.replace("<h1>", '<h1 id="top">', 1)
chap = re.findall(r'<section id="([^"]+)"><h2>(.*?)</h2>', s)
accts = []
for m in re.finditer(r'<section class="acct" id="([^"]+)">\s*<h2[^>]*>(.*?)</h2>', s, re.S):
    g = re.search(r'class="g [^"]*">([A-Z])<', m.group(2))
    name = strip(re.sub(r'<span class="g[^"]*">.*?</span>|<small.*?</small>', "", m.group(2)))
    accts.append((m.group(1), name, g.group(1) if g else ""))
links = "".join(f'<a href="#{i}">{strip(t)}</a>' for i, t in chap if i != "detail")
links += '<div class="mnav-h">分账号详情</div>' + "".join(
    f'<a href="#{i}"><span class="mnav-g mnav-g{g}">{g}</span>{H.escape(n)}</a>' for i, n, g in accts)
nav = f'<nav class="mnav" id="mnav"><details><summary><span>目录</span></summary><div class="mnav-p"><a href="#top">回到顶部</a>{links}</div></details></nav>'
js = """<script>(function(){var d=document.querySelector('#mnav details');if(!d)return;
document.querySelectorAll('#mnav a').forEach(function(a){a.addEventListener('click',function(){d.open=false;});});
document.addEventListener('click',function(e){if(d.open&&!e.target.closest('#mnav'))d.open=false;});})();</script>"""
js += """<script>(function(){function fit(){document.querySelectorAll('#overview-table .ovt-box').forEach(function(b){
b.style.zoom=1;var w=b.parentElement.clientWidth,d=b.offsetWidth;b.style.zoom=d?Math.min(1,w/d):1;});}
fit();window.addEventListener('load',fit);window.addEventListener('resize',fit);})();</script>"""
s = s.replace("</main>", "</main>" + nav, 1).replace("</body>", js + "</body>", 1)

BASE_CSS = r"""
/* ---- mobile layer: shared ---- */
section[id],h2,h3{scroll-margin-top:12px}
.basis .bt{height:auto;flex:none;background:none;border-radius:0;margin-bottom:6px}
.kpi.kg.ga{background:#D9F5D6;border:1px solid #B7EBB0}.kpi.kg.ga .kl,.kpi.kg.ga .kv{color:#237B19}
.kpi.kg.gb{background:#E1EAFF;border:1px solid #BACEFD}.kpi.kg.gb .kl,.kpi.kg.gb .kv{color:#245BDB}
.kpi.kg.gc{background:#FFF0C2;border:1px solid #FFE08A}.kpi.kg.gc .kl,.kpi.kg.gc .kv{color:#B26A00}
.kpi.kg.gd{background:#FDE2E2;border:1px solid #FBC4C2}.kpi.kg.gd .kl,.kpi.kg.gd .kv{color:#D83931}
.listing .nw{white-space:nowrap}
#overview-charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:8px 28px;margin:8px 0 10px}
#overview-charts .chv-fig:last-child{grid-column:1/-1;max-width:640px}
.chart-block .chv-fig{max-width:620px}
.mnav{position:fixed;right:16px;bottom:18px;z-index:50;font-size:14px}
.mnav summary{list-style:none;cursor:pointer;display:flex;align-items:center;justify-content:center;width:56px;height:56px;border-radius:50%;background:#3370FF;color:#fff;font-weight:600;box-shadow:0 6px 18px rgba(51,112,255,.35)}
.mnav summary::-webkit-details-marker{display:none}
.mnav details[open] summary{background:#1F2329;box-shadow:0 6px 18px rgba(31,35,41,.3)}
.mnav details[open] summary span{font-size:0}
.mnav details[open] summary span::after{content:"关闭";font-size:14px}
.mnav-p{position:absolute;right:0;bottom:68px;width:min(300px,calc(100vw - 32px));max-height:70vh;overflow:auto;background:#fff;border-radius:14px;box-shadow:0 12px 32px rgba(31,35,41,.18);padding:6px 0}
.mnav-p a{display:flex;align-items:center;gap:10px;min-height:44px;padding:0 18px;color:#1F2329;text-decoration:none;border-bottom:1px solid #F2F3F5}
.mnav-p a:active{background:#F2F6FF}
.mnav-h{font-size:12px;color:#8F959E;padding:12px 18px 4px}
.mnav-g{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:6px;font-size:12px;font-weight:700}
.mnav-gA{background:#D9F5D6;color:#237B19}.mnav-gB{background:#E1EAFF;color:#245BDB}.mnav-gC{background:#FFF0C2;color:#B26A00}.mnav-gD{background:#FDE2E2;color:#D83931}
@media print{.mnav{display:none!important}}
#overview-table .ovt-box{width:__OVT_W__px;max-width:none;box-sizing:border-box}
""".replace("__OVT_W__", str(OVT_W))

M = r"""
html{-webkit-text-size-adjust:100%}
body{font-size:15px;line-height:1.75;background:#fff}
main{max-width:none;padding:18px 16px 96px}
h1{font-size:22px;line-height:1.4;margin:6px 0 8px}
h2{white-space:normal;font-size:19px;line-height:1.45;margin-top:26px}
h2.nw{display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px;border-bottom:2px solid #1F2329}
h2.nw small{flex-basis:100%;font-size:13px;font-weight:400;color:#646A73}
h2 .g{font-size:16px;line-height:28px;min-width:28px;border-radius:6px}
h3{font-size:16px;margin:26px 0 10px}
h4{font-size:15px;margin:20px 0 8px}
p,ul{margin:8px 0 12px} ul{padding-left:20px}
.muted{font-size:13px}
.nw,td small,th small{white-space:normal}
td,th{word-break:normal;overflow-wrap:anywhere}
.verdict{padding:12px 14px;margin:16px 0;border-radius:8px}
.listing{font-size:14px;line-height:1.8;padding:10px 12px}
.toc{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:16px 0}
.toc b{grid-column:1/-1}
.toc a{margin:0;white-space:normal;display:flex;align-items:center;justify-content:center;text-align:center;min-height:44px;padding:4px 6px;border:1px solid #DEE0E3;border-radius:8px;color:#1F2329;text-decoration:none;font-size:13px;line-height:1.35;background:#fff}
.kpis{grid-template-columns:repeat(2,1fr);gap:8px;margin:12px 0 16px}
.kpi{padding:8px 12px}.kpi .kv{font-size:19px}
.figs{display:block;margin:8px 0 14px}
figure,figure.big,figure.half{max-width:100%;margin:0 0 12px;border-radius:8px;padding:4px}
figcaption{font-size:12.5px;line-height:1.55;padding:2px 4px}
figure>a{position:relative;display:block}
figure>a::after{content:"点击放大";position:absolute;right:6px;bottom:6px;font-size:11px;line-height:18px;color:#fff;background:rgba(31,35,41,.6);padding:0 7px;border-radius:9px}
.listing .nw{white-space:nowrap}
.xt{padding:10px;border-radius:8px}
.charts{grid-template-columns:1fr;gap:10px}
.chart{border-radius:8px;padding:8px 10px}
.bk{width:76px}.bv{width:46px}
.chv-title{font-size:15px}.chv-note{font-size:12.5px}
#overview-charts{display:block}
table.kv,table.kv tbody,table.kv tr,table.kv th,table.kv td{display:block;width:auto;border:0}
table.kv{margin:6px 0 14px;border-top:1px solid #EFF0F1}
table.kv tr{padding:9px 0;border-bottom:1px solid #EFF0F1}
table.kv th{background:none;padding:0 0 2px;font-size:12.5px;font-weight:400;color:#8F959E}
table.kv td{padding:0;font-size:14px;line-height:1.65}
table.stk,table.stk tbody{display:block;width:100%;border:0;margin:6px 0 14px}
table.stk tr.stk-hd{display:none}
table.stk tr{display:flex;flex-wrap:wrap;align-items:flex-start;gap:6px 8px;border:1px solid #DEE0E3;border-radius:10px;padding:10px 12px;margin:0 0 10px;background:#fff}
table.stk td{display:block;width:100%;border:0;padding:0 0 0 5.4em;position:relative;font-size:13.5px;line-height:1.6;background:none}
table.stk td:first-child{padding:0;width:auto;flex:1 1 0;font-weight:600;font-size:14.5px;color:#1F2329}
table.stk td[data-l]::before{content:attr(data-l);position:absolute;left:0;top:1px;width:5em;font-size:12px;line-height:1.6;color:#8F959E;font-weight:400}
table.stk td[data-lg]{padding-left:0}
table.stk td[data-lg]::before{position:static;display:block;width:auto}
table.stk.res td:last-child{order:-1;flex:none;width:auto;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600;align-self:flex-start;background:#F2F3F5;color:#646A73}
table.stk.res td:first-child{order:-2}
table.stk.res td:last-child::before{display:none}
table.stk.res td.ok:last-child{background:#E4F7E0;color:#237B19}
table.stk.res td.mid:last-child{background:#FFF1C2;color:#8A6100}
table.stk.res td.bad:last-child{background:#FDE2E2;color:#B42318}
.basis .bt{font-size:14px;line-height:1.6;margin-bottom:6px}
.basis .bt span{display:block;font-size:13px}
.ovt-section{width:auto;margin:14px 0 18px}
.ovt-section .ovt-head{gap:2px 10px}
.ovt-section .ovt-note{font-size:12.5px}
"""

css = BASE_CSS + "\n@media (max-width:640px){" + M + "}\n"
s = s.replace("</style>", css + "</style>", 1)
open(os.path.join(B.parts, "mobile_layer.css"), "w", encoding="utf-8").write(M)
open(REPORT, "w", encoding="utf-8").write(s)
print(f"overview_charts={n_ovc} accts={n_acct} tables={n_tab} stacked={n_stk} chapters={len(chap)} nav_accts={len(accts)}")
