"""生成总览“达人列表”表格片段：parts/overview_table.html + overview_table.css，并写预览页 preview-overview-table.html。

数字一律从 <PREVIEW_DIR>/report-full.html 解析（以报告为准，先跑 build_full.py --no-merge）；
内容主题从 data_final/<抖音号>/posts.json 统计；性别、地区、蓝 V、封面点赞数从 parts/assets_manifest.json 读取（不存在则留空）。
可重复运行：python scripts/report/build_overview_table.py --config <batch.json>
"""
import collections
import html
import json
import os
import re
import shutil

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
W = str(B.W)
HERE = str(B.parts)
REPORT = str(B.P / "report-full.html")
PREVIEW_DIR = str(B.P)
OUT_HTML = os.path.join(HERE, "overview_table.html")
OUT_CSS = os.path.join(HERE, "overview_table.css")
MANIFEST = os.path.join(HERE, "assets_manifest.json")


def _wan(n):
    return f"{n / 10000:g}万" if n else "—"


# (抖音号, 昵称, 挂牌粉丝, 类型, 认证与画像, 状态)，来自账号清单 listing/filtered.json
LISTING = [(r["id"], r["nickname"], _wan(r["listing_fans"]), r["category"], r["portrait"], r["status"]) for r in config.listing_rows(B)]
QUAL, _NOTES = config.load_qual(B)
GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3, "—": 4}

esc = html.escape


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def tds(row_html):
    return re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)


def w(n, d=1):
    """整数 → w 单位字符串，如 44403 → 4.4w；小于 1 万直接给整数。"""
    if n is None:
        return "—"
    if abs(n) < 10000:
        return f"{n:,}"
    return f"{n / 10000:.{d}f}w"


def to_int(s):
    s = (s or "").replace(",", "").strip()
    return int(s) if re.fullmatch(r"-?\d+", s) else None


def pct_val(s):
    m = re.search(r"(-?[\d.]+)%", s or "")
    return float(m.group(1)) if m else None


# ---------- 解析 report.html ----------
def from_sections(src):
    """report.html 已合并过、原总览宽表不在时，从各账号小节的明细表取同口径数值。"""
    rep = {}
    for aid, *_r in LISTING:
        sec = re.search(rf'<section class="acct" id="a-{re.escape(aid)}">(.*?)</section>', src, re.S)
        s = sec.group(1) if sec else ""
        g = re.search(r'<h2[^>]*>\s*<span class="g g\w">([^<]+)</span>', s)
        m = re.search(r"挂牌粉丝与实际差异</td><td>([+-]?[\d.]+%)", s)
        lf = re.search(r"<th>总获赞 / 赞粉比</th><td>[\d,]+ / ([\d.]+)", s)
        it = re.search(r"<th>互动率 均值 / 中位</th><td>([\d.]+)% / ([\d.]+)%", s)
        low = re.search(r"近 30 条平均互动率</td><td>.*?</td><td>[^<]*偏低线\s*([\d.]+)%", s, re.S)
        z = re.search(r"疑似僵尸/空壳占比</td><td>([^<]*)</td>", s)
        zt = strip_tags(z.group(1)) if z else ""
        zm = re.match(r"([\d.]+)%（0 作品 ([\d.]+)%", zt)
        rep[aid] = dict(
            diff=m.group(1) if m else "—",
            like_fan=lf.group(1) if lf else "—",
            inter_main=f"{float(it.group(1)):.2f}% / {float(it.group(2)):.2f}%" if it else "—",
            low_line=float(low.group(1)) if low else None,
            like_med="—",
            zombie=(f"{zm.group(1)}%（0 作品 {float(zm.group(2)):.0f}%）" if zm else "隐私不可见"),
            grade=g.group(1).strip() if g else "—",
            advice="", risk="",
        )
    return rep


def parse_report():
    src = open(REPORT, encoding="utf-8").read()
    rep = {}

    ov = re.search(r'<section id="overview">(.*?)</section>', src, re.S).group(1)
    if '<table class="sum">' not in ov:
        rep = from_sections(src)
    for tr in re.findall(r"<tr>(.*?)</tr>", ov if '<table class="sum">' in ov else "", re.S):
        cells = tds(tr)
        if len(cells) < 12:
            continue
        m = re.search(r"<small>([^<]+)</small>", cells[0])
        aid = m.group(1).strip()
        inter = cells[5]
        low = re.search(r"偏低线\s*([\d.]+)%", inter)
        inter_main = strip_tags(re.sub(r"<br>.*", "", inter, flags=re.S))
        rep[aid] = dict(
            diff=strip_tags(re.search(r"<small>(.*?)</small>", cells[2]).group(1)),
            like_fan=strip_tags(cells[4]),
            inter_main=inter_main,
            low_line=float(low.group(1)) if low else None,
            like_med=strip_tags(cells[6]),
            zombie=strip_tags(cells[7]),
            grade=strip_tags(cells[9]),
            advice=strip_tags(cells[10]),
            risk=strip_tags(cells[11]),
        )

    cross = re.search(r'<section id="cross">(.*?)</section>', src, re.S).group(1)
    for tr in re.findall(r"<tr>(.*?)</tr>", cross, re.S):
        cells = tds(tr)
        if len(cells) < 4:
            continue
        m = re.search(r"<small>([^<]+)</small>", cells[0])
        if m and m.group(1).strip() in rep:
            r = rep[m.group(1).strip()]
            r["fans"] = to_int(strip_tags(cells[1]))
            r["xingtu"] = strip_tags(cells[3])

    for aid in rep:
        sec = re.search(rf'<section class="acct" id="a-{re.escape(aid)}">(.*?)</section>', src, re.S)
        s = sec.group(1) if sec else ""
        r = rep[aid]
        kpi = dict((strip_tags(k), strip_tags(v)) for k, v in re.findall(
            r'<div class="kl">(.*?)</div><div class="kv[^"]*">(.*?)</div>', s, re.S))
        r["kpi"] = kpi
        m = re.search(r"<th>当前粉丝 / 历史最高</th><td>([\d,]+) / ([\d,]+)</td>", s)
        r["max_fans"] = to_int(m.group(2)) if m else None
        if m and r.get("fans") is None:
            r["fans"] = to_int(m.group(1))
        m = re.search(r"<th>总获赞 / 赞粉比</th><td>([\d,]+) /", s)
        r["likes_total"] = to_int(m.group(1)) if m else None
        m = re.search(r"<b>结论：</b>(.*?)</p>", s, re.S)
        r["summary"] = strip_tags(m.group(1)) if m else ""
        m = re.search(r"内容与挂牌类目是否一致</td><td>(.*?)</td><td>.*?</td><td[^>]*>(.*?)</td>", s, re.S)
        r["content_desc"] = strip_tags(m.group(1)) if m else ""
        r["content_ok"] = None if not m else ("✗" not in m.group(2))
    return rep


# ---------- 内容主题 ----------
def topics(aid):
    posts = []
    for d in ("data_final",):
        p = os.path.join(W, d, aid, "posts.json")
        if os.path.exists(p):
            posts = json.load(open(p, encoding="utf-8")) or []
            if posts:
                break
    cats, tags = collections.Counter(), collections.Counter()
    for it in posts:
        vt = it.get("video_tag") or []
        if vt and vt[0]:
            cats[vt[0]] += 1
        for t in set(it.get("tags") or []):
            t = (t or "").strip()
            if t:
                tags[t] += 1
    return [k for k, _ in cats.most_common()], [k for k, _ in tags.most_common()]


def load_manifest():
    if not os.path.exists(MANIFEST):
        return {}, False
    try:
        return json.load(open(MANIFEST, encoding="utf-8")), True
    except Exception:
        return {}, False


# ---------- 渲染 ----------
HEART = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 14s-5.5-3.3-5.5-7.2A3 3 0 0 1 8 4.6a3 3 0 0 1 5.5 2.2C13.5 10.7 8 14 8 14z"/></svg>'
ONERR = "this.onerror=null;this.style.visibility='hidden'"


def thumb(aid, idx, cover):
    src = f"overview-assets/{aid}/cover{idx}.jpg"
    likes = cover.get("likes") if cover else None
    role = (cover or {}).get("role") or ("点赞最高" if idx == 1 else "最近作品")
    date = (cover or {}).get("date") or ""
    tip = " · ".join(x for x in [role, date, f"{likes:,} 赞" if likes is not None else ""] if x)
    badge = f'<span class="ovt-like">{HEART}{w(likes)}</span>' if likes is not None else ""
    return (f'<span class="ovt-thumb" title="{esc(tip)}"><img src="{src}" alt="" loading="lazy" '
            f'onerror="{ONERR}">{badge}</span>')


def cls_by(v, warn, bad):
    if v is None:
        return ""
    return " ovt-bad" if v > bad else (" ovt-warn" if v > warn else "")


def build():
    rep = parse_report()
    man, has_man = load_manifest()
    rows = []
    order = {aid: i for i, (aid, *_r) in enumerate(LISTING)}
    for aid, nick, l_fans, l_cat, l_desc, l_state in LISTING:
        r = rep.get(aid) or dict(diff="—", like_fan="—", inter_main="—", low_line=None, like_med="—", zombie="—", grade="—", advice="", risk="",
                                  kpi={}, fans=None, max_fans=None, likes_total=None, xingtu="", content_desc="", content_ok=None,
                                  summary=(QUAL.get(aid) or {}).get("summary") or "账号无法定位，未采集。")
        k = r["kpi"]
        m = man.get(aid, {})
        covers = m.get("covers") or []

        # 达人信息
        chips = []
        g = m.get("gender")
        if g in ("男", "女"):
            chips.append(f'<span class="ovt-chip">{esc(g)}</span>')
        if m.get("region"):
            chips.append(f'<span class="ovt-chip">{esc(m["region"])}</span>')
        if m.get("verified") and m["verified"] not in ("无", ""):
            chips.append(f'<span class="ovt-chip ovt-chip-v"><b>V</b>{esc(m["verified"])}</span>')
        who = (f'<div class="ovt-who"><span class="ovt-ava"><img src="overview-assets/{aid}/avatar.jpg" alt="" '
               f'loading="lazy" onerror="{ONERR}"></span><div class="ovt-who-t">'
               f'<a class="ovt-name" href="#a-{aid}">{esc(nick)}</a>'
               f'<div class="ovt-id">抖音号 {esc(aid)}</div>'
               + (f'<div class="ovt-chips">{"".join(chips)}</div>' if chips else "") + "</div></div>")

        vids = '<div class="ovt-thumbs">' + thumb(aid, 1, covers[0] if covers else None) + \
               thumb(aid, 2, covers[1] if len(covers) > 1 else None) + "</div>"

        lfans = float(l_fans.replace("万", "")) * 10000 if l_fans != "—" else 0
        listing = (f'<div class="ovt-l1"><span class="ovt-tag ovt-tag-blue">{esc(l_cat)}</span>'
                   f'<span class="ovt-num">挂牌 {w(int(round(lfans))) if lfans else "—"}</span></div>'
                   f'<div class="ovt-sub">{esc(l_desc)}<span class="ovt-dot">·</span>'
                   f'<span class="{"ovt-state-ok" if l_state == "状态正常" else ""}">{esc(l_state)}</span></div>')

        cats, tags = topics(aid)
        shown = ([cats[0]] if cats else []) + ([f"#{tags[0]}"] if tags else [])
        pool = cats[1:] + [f"#{t}" for t in tags[1:]]
        while len(shown) < 2 and pool:
            shown.append(pool.pop(0))
        tip = "、".join(cats + [f"#{t}" for t in tags])
        topic_html = "".join(f'<span class="ovt-tag">{esc(t)}</span>' for t in shown)
        if pool:
            topic_html += f'<span class="ovt-tag ovt-more" title="{esc(tip)}">+{len(pool)}</span>'
        if not shown:
            topic_html = '<span class="ovt-muted">作品已清空</span>'
        if r["content_ok"] is False:
            topic_html += f'<span class="ovt-tag ovt-tag-orange" title="{esc(r["content_desc"])}">与挂牌不符</span>'

        drop = pct_val(k.get("掉粉率"))
        inter_mean = pct_val(r["inter_main"].split("/")[0]) if "%" in r["inter_main"] else None
        inter_med = r["inter_main"].split("/")[1].strip() if "/" in r["inter_main"] else ""
        low = r["low_line"]
        z = r["zombie"]
        z_val = pct_val(z.split("（")[0]) if "%" in z else None
        z_sub = re.search(r"（(.*?)）", z)
        days_s = k.get("断更天数", "—")
        days = to_int(days_s.replace("天", "")) if "天" in days_s else None
        xt = r.get("xingtu") or ""
        grade = r["grade"] or "—"

        def cell(main, sub="", cls=""):
            return (f'<td class="ovt-n{cls}"><div class="ovt-v">{main}</div>'
                    + (f'<div class="ovt-s">{sub}</div>' if sub else "") + "</td>")

        def kv(label, val, cls="", sub=""):
            return (f'<div class="ovt-kv{cls}"><span class="ovt-k">{label}</span> <b class="ovt-n">{val}</b>'
                    + (f' <span class="ovt-n ovt-s">{sub}</span>' if sub else "") + "</div>")

        like_med = k.get("近期点赞率（中位）", r["like_med"])
        inter_cls = " ovt-warn" if inter_mean is not None and low and inter_mean < low else ""
        fans_html = (kv("实际", w(r["fans"]), sub=f'较挂牌 {esc(r["diff"])}')
                     + kv("最高", w(r["max_fans"]))
                     + kv("掉粉", esc(k.get("掉粉率", "—")), cls_by(drop, 5, 10)))
        inter_html = (kv("获赞", w(r["likes_total"]))
                      + kv("点赞率", esc(like_med))
                      + kv("互动率", f"{inter_mean:.2f}%" if inter_mean is not None else "—", inter_cls,
                           f"中位 {esc(inter_med)}" if inter_med else ""))
        zombie = "隐私" if "隐私" in z else (f"{z_val:.1f}%" if z_val is not None else "—")
        risk_html = (kv("僵尸粉", zombie, " ovt-mute" if "隐私" in z else cls_by(z_val, 10, 20))
                     + kv("断更", esc(days_s), cls_by(days, 90, 365) if days is not None else " ovt-bad")
                     + kv("星图", "已入驻" if re.search(r"\d", xt) else "未入驻",
                          " ovt-on" if re.search(r"\d", xt) else " ovt-mute"))
        cells = [
            f'<td>{who}</td>',
            f'<td>{vids}</td>',
            f'<td>{listing}</td>',
            f'<td><div class="ovt-tags">{topic_html}</div></td>',
            f'<td>{fans_html}</td>',
            f'<td>{inter_html}</td>',
            f'<td>{risk_html}</td>',
            f'<td><div class="ovt-verdict"><span class="ovt-grade ovt-g{esc(grade)}">{esc(grade)}</span>'
            f'<span class="ovt-vt">{esc(r["summary"])}</span></div></td>',
        ]
        rows.append((GRADE_ORDER.get(grade, 9), order[aid], aid, nick,
                     f'<tr data-href="#a-{aid}" onclick="if(!event.target.closest(\'a\'))location.hash=\'a-{aid}\'" '
                     f'title="查看 {esc(nick)} 详情">' + "".join(cells) + "</tr>"))
    rows.sort(key=lambda x: (x[0], x[1]))

    cols = [("达人信息", "", 17), ("代表视频", "点赞最高 / 最近", 11), ("挂牌信息", "", 14), ("内容主题", "", 11),
            ("粉丝", "", 11), ("互动", "近 30 条", 11), ("风险", "", 8.5), ("评级与结论", "", 16.5)]
    colgroup = "".join(f'<col style="width:{p}%">' for _, _, p in cols)
    head = "<tr>" + "".join(f"<th>{t}" + (f"<small>{s}</small>" if s else "") + "</th>" for t, s, _ in cols) + "</tr>"
    cnt = collections.Counter(x[0] for x in rows)
    frag = f"""<section id="overview-table" class="ovt-section">
<div class="ovt-head"><h3 class="ovt-title">达人列表</h3><span class="ovt-hint">共 {len(rows)} 个号，按评级从好到差排列；点击任一行跳到该号详情</span></div>
<div class="ovt-box"><table class="ovt-table">
<colgroup>{colgroup}</colgroup>
<thead>{head}</thead>
<tbody>
{chr(10).join(x[4] for x in rows)}
</tbody></table></div>
<p class="ovt-note">粉丝、获赞以 w（万）为单位。互动率 = (赞+评+藏+转) ÷ 当前粉丝，取近 30 条作品均值，小字为中位数和同量级偏低线；近期点赞率为近 30 条中位数。疑似僵尸粉为粉丝列表抽样结果，“隐私”表示粉丝列表不对外展示。断更天数截至 {B.date}。代表视频角标为该作品点赞数。</p>
</section>
"""
    open(OUT_HTML, "w", encoding="utf-8").write(frag)
    open(OUT_CSS, "w", encoding="utf-8").write(CSS)

    os.makedirs(os.path.join(PREVIEW_DIR, "progress"), exist_ok=True)
    preview = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>达人列表预览</title>
<style>body{{margin:0;background:#f5f6f7;font-family:"PingFang SC","Microsoft YaHei",sans-serif;color:#1F2329}}
main{{max-width:var(--pv-w,1480px);margin:0 auto;padding:28px 32px;background:#fff}}</style>
<style>
{CSS}</style></head><body><main>
{frag}</main>
<script>var w=new URLSearchParams(location.search).get('w');if(w)document.documentElement.style.setProperty('--pv-w',w+'px');</script>
</body></html>"""
    open(os.path.join(PREVIEW_DIR, "preview-overview-table.html"), "w", encoding="utf-8").write(preview)
    print(f"rows={len(rows)} grades={dict(cnt)} manifest={'yes' if has_man else 'no'}")
    print("wrote", OUT_HTML, OUT_CSS, os.path.join(PREVIEW_DIR, "preview-overview-table.html"))



CSS = r"""/* 达人列表（总览）——所有选择器以 .ovt- 为前缀；不横向滚动，固定布局按百分比分列 */
.ovt-section{--ovt-blue:#3370FF;--ovt-text:#1F2329;--ovt-sub:#646A73;--ovt-faint:#8F959E;--ovt-line:#EFF0F1;--ovt-head:#F5F6F7;--ovt-hover:#F2F6FF;
  width:min(1200px,calc(100vw - 32px));margin:18px 0 26px calc(50% - min(600px,calc(50vw - 16px)));color:var(--ovt-text);box-sizing:border-box}
.ovt-section .ovt-head{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin:0 0 10px}
.ovt-section .ovt-title{margin:0;font-size:17px}
.ovt-section .ovt-hint{font-size:12px;color:var(--ovt-faint)}
.ovt-section .ovt-box{border:1px solid #DEE0E3;border-radius:8px;background:#fff}
.ovt-section .ovt-table{table-layout:fixed;width:100%;border-collapse:separate;border-spacing:0;margin:0;font-size:13px;line-height:1.5;font-variant-numeric:tabular-nums}
.ovt-section .ovt-table th,.ovt-section .ovt-table td{border:0;border-bottom:1px solid var(--ovt-line);padding:14px 8px;text-align:left;vertical-align:middle;background:#fff;word-break:normal;overflow-wrap:anywhere}
.ovt-section .ovt-table th:first-child,.ovt-section .ovt-table td:first-child{padding-left:14px}
.ovt-section .ovt-table thead th{background:var(--ovt-head);color:var(--ovt-sub);font-weight:500;font-size:12px;padding:10px 8px;border-bottom:1px solid #DEE0E3}
.ovt-section .ovt-table thead th:first-child{border-top-left-radius:8px}
.ovt-section .ovt-table thead th:last-child{border-top-right-radius:8px}
.ovt-section .ovt-table th small{display:block;font-weight:400;color:var(--ovt-faint);font-size:11px}
.ovt-section .ovt-table tbody tr{cursor:pointer;break-inside:avoid;page-break-inside:avoid}
.ovt-section .ovt-table tbody tr:last-child td{border-bottom:0}
.ovt-section .ovt-table tbody tr:hover td{background:var(--ovt-hover)}
.ovt-section .ovt-n{white-space:nowrap}
/* 达人信息 */
.ovt-section .ovt-who{display:flex;align-items:center;gap:8px}
.ovt-section .ovt-ava{flex:0 0 40px;width:40px;height:40px;border-radius:50%;overflow:hidden;background:#E8EAED;display:block}
.ovt-section .ovt-ava img{width:100%;height:100%;object-fit:cover;display:block}
.ovt-section .ovt-who-t{min-width:0}
.ovt-section .ovt-name{font-weight:600;font-size:14px;color:var(--ovt-text);text-decoration:none;line-height:1.35;display:block}
.ovt-section .ovt-name:hover{color:var(--ovt-blue)}
.ovt-section .ovt-id{font-size:12px;color:var(--ovt-faint);margin-top:1px}
.ovt-section .ovt-chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}
.ovt-section .ovt-chip{display:inline-flex;align-items:center;gap:3px;font-size:11px;line-height:18px;padding:0 5px;border-radius:4px;background:#F2F3F5;color:var(--ovt-sub);white-space:nowrap}
.ovt-section .ovt-chip-v{background:#E1EAFF;color:#245BDB}
.ovt-section .ovt-chip-v b{display:inline-block;width:12px;height:12px;line-height:12px;border-radius:50%;background:var(--ovt-blue);color:#fff;font-size:9px;text-align:center}
/* 代表视频 */
.ovt-section .ovt-thumbs{display:flex;gap:6px}
.ovt-section .ovt-thumb{position:relative;flex:0 0 52px;width:52px;height:52px;border-radius:6px;overflow:hidden;background:#E8EAED;display:block}
.ovt-section .ovt-thumb img{width:100%;height:100%;object-fit:cover;display:block}
.ovt-section .ovt-like{position:absolute;right:2px;bottom:2px;display:inline-flex;align-items:center;gap:2px;padding:0 3px;border-radius:3px;background:rgba(0,0,0,.55);color:#fff;font-size:10px;line-height:14px;white-space:nowrap}
.ovt-section .ovt-like svg{width:8px;height:8px;fill:#fff}
/* 标签与挂牌 */
.ovt-section .ovt-tags{display:flex;flex-wrap:wrap;gap:4px}
.ovt-section .ovt-tag{display:inline-block;font-size:12px;line-height:20px;padding:0 6px;border-radius:4px;background:#F2F3F5;color:var(--ovt-sub);white-space:nowrap;max-width:100%;overflow:hidden;text-overflow:ellipsis;vertical-align:middle;box-sizing:border-box}
.ovt-section .ovt-tag-blue{background:#E1EAFF;color:#245BDB}
.ovt-section .ovt-tag-orange{background:#FEEAD2;color:#C25705}
.ovt-section .ovt-more{background:#fff;border:1px solid #DEE0E3;line-height:18px;color:var(--ovt-faint)}
.ovt-section .ovt-l1{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.ovt-section .ovt-num{font-size:13px;white-space:nowrap}
.ovt-section .ovt-sub{font-size:12px;color:var(--ovt-sub);margin-top:5px}
.ovt-section .ovt-dot{margin:0 3px;color:#BBBFC4}
.ovt-section .ovt-state-ok{color:#2EA121}
.ovt-section .ovt-muted{font-size:12px;color:var(--ovt-faint)}
/* 数据：标签 + 数值分行 */
.ovt-section .ovt-kv{font-size:12px;line-height:1.75;color:var(--ovt-sub)}
.ovt-section .ovt-k{color:var(--ovt-faint)}
.ovt-section .ovt-kv b{font-size:13px;font-weight:600;color:var(--ovt-text)}
.ovt-section .ovt-kv .ovt-s{font-size:12px;color:var(--ovt-faint)}
.ovt-section .ovt-warn b,.ovt-section .ovt-warn .ovt-s{color:#C25705}
.ovt-section .ovt-bad b,.ovt-section .ovt-bad .ovt-s{color:#D83931}
.ovt-section .ovt-mute b{color:var(--ovt-sub);font-weight:400}
.ovt-section .ovt-on b{color:#245BDB}
/* 评级与结论 */
.ovt-section .ovt-verdict{display:flex;align-items:flex-start;gap:8px}
.ovt-section .ovt-grade{flex:0 0 auto;display:inline-block;min-width:26px;text-align:center;font-weight:700;font-size:15px;line-height:26px;border-radius:6px;padding:0 5px}
.ovt-section .ovt-gA{background:#D9F5D6;color:#237B19}
.ovt-section .ovt-gB{background:#E1EAFF;color:#245BDB}
.ovt-section .ovt-gC{background:#FFF0C2;color:#B26A00}
.ovt-section .ovt-gD{background:#FDE2E2;color:#D83931}
.ovt-section .ovt-vt{font-size:12px;line-height:1.6;color:var(--ovt-sub);min-width:0}
.ovt-section .ovt-note{font-size:12px;color:var(--ovt-faint);margin:10px 0 0;line-height:1.7}
@media print{
.ovt-section{width:100%;margin:10px 0 14px}
.ovt-section .ovt-box{border-color:#DEE0E3}
.ovt-section .ovt-table{font-size:9.5px;line-height:1.4}
.ovt-section .ovt-table th,.ovt-section .ovt-table td{padding:6px 4px}
.ovt-section .ovt-table th:first-child,.ovt-section .ovt-table td:first-child{padding-left:6px}
.ovt-section .ovt-table thead th{font-size:9px;padding:5px 4px}
.ovt-section .ovt-table th small{font-size:8px}
.ovt-section .ovt-table tbody tr:hover td{background:#fff}
.ovt-section .ovt-who{gap:4px}
.ovt-section .ovt-ava{flex-basis:22px;width:22px;height:22px}
.ovt-section .ovt-name{font-size:10px}
.ovt-section .ovt-id,.ovt-section .ovt-sub,.ovt-section .ovt-muted,.ovt-section .ovt-vt,.ovt-section .ovt-kv,.ovt-section .ovt-kv .ovt-s,.ovt-section .ovt-hint,.ovt-section .ovt-note{font-size:8.5px}
.ovt-section .ovt-kv b,.ovt-section .ovt-num{font-size:9.5px}
.ovt-section .ovt-chip{font-size:8px;line-height:12px;padding:0 3px}
.ovt-section .ovt-thumbs{gap:3px}
.ovt-section .ovt-thumb{flex-basis:30px;width:30px;height:30px;border-radius:4px}
.ovt-section .ovt-like{font-size:6.5px;line-height:9px;padding:0 2px;right:1px;bottom:1px}
.ovt-section .ovt-like svg{width:5px;height:5px}
.ovt-section .ovt-tag{font-size:8px;line-height:13px;padding:0 3px}
.ovt-section .ovt-more{line-height:11px}
.ovt-section .ovt-grade{font-size:10px;line-height:16px;min-width:16px;padding:0 3px}
.ovt-section .ovt-verdict{gap:4px}
#overview-table.ovt-section .ovt-who{display:flex!important}
#overview-table.ovt-section .ovt-ava,#overview-table.ovt-section .ovt-thumb{overflow:hidden!important}
#overview-table.ovt-section .ovt-ava img,#overview-table.ovt-section .ovt-thumb img{width:100%!important;height:100%!important;max-width:none!important;max-height:none!important;object-fit:cover}
}
"""

if __name__ == "__main__":
    build()
