"""完整版图表：parts/charts/charts.css、overview_charts.html（散点、掉粉、指标热力表）、acct_<id>.html（按月时间线）。

用法：python scripts/report/build_charts.py --config <batch.json>
build_charts_m.py 复用这里的函数和 ACC。只画能定位到的号。
"""
import os, math, html
from report_data import ORDER as _ALL, P, derive, rate, DATE, PARTS, short

OUT = os.path.join(PARTS, "charts")
ORDER = [a for a in _ALL if derive(a)]
esc = lambda s: html.escape(str(s))
GC = {"A": "#34C724", "B": "#3370FF", "C": "#FF8800", "D": "#F54A45"}
FONT = "Microsoft YaHei, PingFang SC, sans-serif"
TODAY_M = DATE[:7]


def tw(s, fs):
    return sum(fs if ord(c) > 255 else fs * 0.6 for c in str(s))


def wf(v):
    return f"{v / 10000:.2f}w" if v >= 10000 else f"{v:,.0f}"


def svg(w, h, body):
    return f'<svg class="chv-svg" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}" role="img">{body}</svg>'


def T(x, y, s, fs=12, fill="#1F2329", anchor="start", weight="normal"):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">{esc(s)}</text>'


def fig(title, body, note):
    return f'<figure class="chv-fig"><div class="chv-title">{esc(title)}</div>{body}<div class="chv-note">{esc(note)}</div></figure>'


ACC = {}
for aid in ORDER:
    d = derive(aid)
    g, rows, trig = rate(d)
    ACC[aid] = dict(d=d, g=g, rows={r[0]: r for r in rows}, nick=d["p"]["nickname"])
GRADES = [g for g in "ABCD" if any(ACC[a]["g"] == g for a in ORDER)]
NO_WORKS = [ACC[a]["nick"] for a in ORDER if ACC[a]["d"]["like_med"] is None]
NO_WORKS_NOTE = f"{'、'.join(NO_WORKS)}作品已清空，不在图中。" if NO_WORKS else ""


def label(aid):
    n = ACC[aid]["nick"]
    return n if len(n) <= 10 else short(aid)


# ---------- overview: scatter ----------
def scatter():
    w, h, L, R, Tp, B = 780, 430, 70, 30, 20, 50
    y0, y1 = math.log10(0.005), math.log10(10)
    px = lambda f: L + (math.log10(min(max(f, 1e4), 1e6)) - 4) / 2 * (w - L - R)
    py = lambda v: Tp + (y1 - math.log10(v)) / (y1 - y0) * (h - Tp - B)
    b = []
    b.append(f'<rect x="{L}" y="{py(5):.1f}" width="{w - L - R}" height="{py(0.5) - py(5):.1f}" fill="#E8F8E5"/>')
    for v in (0.01, 0.1, 1, 10):
        b.append(f'<line x1="{L}" x2="{w - R}" y1="{py(v):.1f}" y2="{py(v):.1f}" stroke="#EEF0F2"/>')
        b.append(T(L - 8, py(v) + 4, f"{v:g}%", 11, "#646A73", "end"))
    for v in (0.5, 5):
        b.append(T(L - 8, py(v) + 4, f"{v:g}%", 11, "#34C724", "end"))
    for f, lab in ((1e4, "1w"), (1e5, "10w"), (1e6, "100w")):
        b.append(f'<line x1="{px(f):.1f}" x2="{px(f):.1f}" y1="{Tp}" y2="{h - B}" stroke="#EEF0F2"/>')
        b.append(T(px(f), h - B + 18, lab, 11, "#646A73", "middle"))
    for f in (2e4, 5e4, 2e5, 5e5):
        b.append(f'<line x1="{px(f):.1f}" x2="{px(f):.1f}" y1="{h - B}" y2="{h - B + 4}" stroke="#BBBFC4"/>')
    b.append(f'<line x1="{L}" x2="{w - R}" y1="{h - B}" y2="{h - B}" stroke="#BBBFC4"/>')
    b.append(T((L + w - R) / 2, h - 8, "实际粉丝数（对数刻度）", 12, "#646A73", "middle"))
    b.append(f'<text x="16" y="{(Tp + h - B) / 2:.0f}" font-size="12" fill="#646A73" text-anchor="middle" transform="rotate(-90 16 {(Tp + h - B) / 2:.0f})">近 30 条点赞率中位数（对数刻度）</text>')
    boxes = []
    t1 = "健康区间 0.5%~5%"
    b.append(T(w - R - 6, py(5) + 16, t1, 11, "#2A9D1A", "end"))
    boxes.append((w - R - 6 - tw(t1, 11), py(5) + 4, w - R - 6, py(5) + 18))
    for (fa, fb, v, lab) in ((1e4, 1e5, 2, "1w~10w 偏低线 2%"), (1e5, 1e6, 1.2, "10w~100w 偏低线 1.2%")):
        b.append(f'<line x1="{px(fa):.1f}" x2="{px(fb):.1f}" y1="{py(v):.1f}" y2="{py(v):.1f}" stroke="#8F959E" stroke-width="1.5" stroke-dasharray="6 4"/>')
        b.append(T(px(fa) + 6, py(v) - 5, lab, 11, "#646A73"))
        boxes.append((px(fa) + 6, py(v) - 16, px(fa) + 6 + tw(lab, 11), py(v) - 2))
    pts = []
    for aid in ORDER:
        a = ACC[aid]
        if a["d"]["like_med"] is None:
            continue
        x, y = px(a["d"]["fans"]), py(max(a["d"]["like_med"], 0.006))
        pts.append((aid, x, y))
        boxes.append((x - 7, y - 7, x + 7, y + 7))
    for aid, x, y in pts:
        a = ACC[aid]
        lab = f'{label(aid)} {a["d"]["like_med"]:.2f}%'
        lw = tw(lab, 12)
        cands = [(x + 10, y + 4), (x - 10 - lw, y + 4), (x - lw / 2, y - 11), (x - lw / 2, y + 20), (x + 10, y - 9), (x + 10, y + 17), (x - 10 - lw, y - 9), (x - 10 - lw, y + 17), (x - lw / 2, y - 24), (x - lw / 2, y + 33)]
        pick = cands[0]
        for cx, cy in cands:
            bx = (cx, cy - 11, cx + lw, cy + 3)
            if bx[0] < L or bx[2] > w - R or bx[1] < Tp or bx[3] > h - B:
                continue
            if all(bx[2] < o[0] or bx[0] > o[2] or bx[3] < o[1] or bx[1] > o[3] for o in boxes):
                pick = (cx, cy)
                break
        boxes.append((pick[0], pick[1] - 11, pick[0] + lw, pick[1] + 3))
        b.append(T(pick[0], pick[1], lab, 12, "#1F2329"))
    for aid, x, y in pts:
        b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="{GC[ACC[aid]["g"]]}" stroke="#fff" stroke-width="1.5"/>')
    lx = L + 8
    for g in GRADES:
        b.append(f'<circle cx="{lx + 6}" cy="{Tp + 14}" r="5" fill="{GC[g]}"/>')
        b.append(T(lx + 16, Tp + 18, f"评级 {g}", 11, "#646A73"))
        lx += 70
    below = sum(1 for aid, _x, _y in pts if ACC[aid]["d"]["like_med"] < 0.5)
    inside = sum(1 for aid, _x, _y in pts if 0.5 <= ACC[aid]["d"]["like_med"] <= 5)
    sub = "多数号落在健康区间下方" if below * 2 > len(pts) else ("多数号落在健康区间内" if inside * 2 > len(pts) else f"{below} 个号低于健康区间")
    return fig(f"粉丝数与近期点赞率：{sub}", svg(w, h, "".join(b)),
               "点赞率 = 近 30 条作品每条点赞 ÷ 当前粉丝，取中位数；绿色带为健康区间 0.5%~5%，虚线为同量级互动率偏低线（供参考）。" + NO_WORKS_NOTE)


# ---------- overview: fans drop ----------
def drop_chart():
    w, rh, top = 800, 34, 34
    h = top + rh * len(ORDER) + 10
    bx0, bx1 = 150, 590
    mx = max(ACC[a]["d"]["p"]["max_fans"] for a in ORDER)
    sc = lambda v: (bx1 - bx0) * v / mx
    b = [T(bx0, 18, "■", 12, "#C9D8FF"), T(bx0 + 16, 18, "历史最高粉丝", 11, "#646A73"), T(bx0 + 110, 18, "■", 12, "#3370FF"), T(bx0 + 126, 18, "当前粉丝", 11, "#646A73"),
         T(610, 18, "当前 / 最高", 11, "#8F959E"), T(780, 18, "掉粉率", 11, "#8F959E", "end")]
    for i, aid in enumerate(ORDER):
        a = ACC[aid]
        p = a["d"]["p"]
        y = top + i * rh
        b.append(T(bx0 - 10, y + 17, label(aid), 12, "#1F2329", "end"))
        b.append(f'<rect x="{bx0}" y="{y + 5}" width="{sc(p["max_fans"]):.1f}" height="18" rx="3" fill="#C9D8FF"/>')
        b.append(f'<rect x="{bx0}" y="{y + 9}" width="{sc(a["d"]["fans"]):.1f}" height="10" rx="2" fill="#3370FF"/>')
        b.append(T(610, y + 18, f'{wf(a["d"]["fans"])} / {wf(p["max_fans"])}', 11, "#646A73"))
        dr = a["d"]["drop"]
        col = "#F54A45" if dr > 10 else ("#FF8800" if dr > 5 else "#2A9D1A")
        b.append(T(780, y + 18, f"-{dr:.1f}%", 13, col, "end", "bold"))
    over = sum(1 for x in ORDER if ACC[x]["d"]["drop"] > 10)
    return fig(f"掉粉对比：{over} 个号较历史最高掉粉超过 10%", svg(w, h, "".join(b)),
               f"浅色条为历史最高粉丝，深色条为当前粉丝（{DATE} 查询）；掉粉率 ≤5% 绿、5%~10% 橙、>10% 红（>10% 为 D 触发条件）。")


# ---------- overview: heat table ----------
COLS = [("互动率", "近 30 条平均互动率"), ("点赞率中位", "近 30 条单条点赞率（中位数）"), ("僵尸粉", "粉丝抽样：疑似僵尸/空壳占比"),
        ("掉粉率", "掉粉率（历史最高→当前）"), ("断更", "断更天数"), ("获赞对得上", "获赞能否对上现存作品"),
        ("内容一致", "内容与挂牌类目是否一致"), ("画像相符", "画像与挂牌是否相符"), ("刷量痕迹", "刷粉/刷赞痕迹")]
FILL = {"ok": ("#D9F5D3", "#1F6B12"), "mid": ("#FFF1C2", "#8A6100"), "bad": ("#FDDCDB", "#B42318"), "na": ("#EFF0F1", "#646A73")}


def pv(v):
    return f"{v:.3f}%" if v < 0.1 else f"{v:.2f}%"


def cell_val(a, col):
    d = a["d"]
    if col == "互动率":
        return "无作品" if d["inter"] is None else pv(d["inter"])
    if col == "点赞率中位":
        return "无作品" if d["like_med"] is None else pv(d["like_med"])
    if col == "僵尸粉":
        return "隐私" if d["blocked"] else f"{d['zomb']:.1f}%"
    if col == "掉粉率":
        return f"{d['drop']:.1f}%"
    if col == "断更":
        return "无作品" if d["days"] is None else f"{d['days']} 天"
    if col == "获赞对得上":
        return "0%（已清空）" if d["works"] == 0 else ("未全抓" if d["acc"] is None else f"{d['acc']:.1f}%")
    if col == "内容一致":
        return {True: "一致", False: "不符"}.get(d["q"]["content_ok"], "未核实")
    if col == "画像相符":
        return "相符" if d["q"]["portrait_ok"] else "无画像"
    if col == "刷量痕迹":
        return "有" if d["q"]["brush"] else "未发现"


def status(a, key):
    r = a["rows"].get(key)
    if not r:
        return "na"
    c = r[3][:1]
    return {"✓": "ok", "△": "mid", "✗": "bad"}.get(c, "na")


def heat():
    nw, cw, rh, top = 118, 72, 32, 40
    w = nw + cw * (len(COLS) + 1) + 4
    h = top + rh * len(ORDER) + 6
    b = []
    for j, (c, _) in enumerate(COLS + [("评级", None)]):
        b.append(T(nw + cw * j + cw / 2, top - 14, c, 12, "#646A73", "middle", "bold"))
    for i, aid in enumerate(ORDER):
        a = ACC[aid]
        y = top + i * rh
        b.append(T(nw - 10, y + 20, label(aid), 12, "#1F2329", "end"))
        for j, (c, key) in enumerate(COLS):
            st = status(a, key)
            if c == "点赞率中位" and a["d"]["like_med"] is None:
                st = "na"
            bg, fg = FILL[st]
            v = cell_val(a, c)
            fs = 12 if tw(v, 12) < cw - 8 else 10
            b.append(f'<rect x="{nw + cw * j + 1}" y="{y + 1}" width="{cw - 2}" height="{rh - 2}" rx="3" fill="{bg}"/>')
            b.append(T(nw + cw * j + cw / 2, y + 20, v, fs, fg, "middle"))
        g = a["g"]
        j = len(COLS)
        b.append(f'<rect x="{nw + cw * j + 1}" y="{y + 1}" width="{cw - 2}" height="{rh - 2}" rx="3" fill="{GC[g]}"/>')
        b.append(T(nw + cw * j + cw / 2, y + 21, g, 14, "#fff", "middle", "bold"))
    lg = ""
    lx = 0
    for st, lab in (("ok", "达标"), ("mid", "临界"), ("bad", "不达标"), ("na", "无数据 / 无法核验")):
        lg += f'<span class="chv-lg"><i style="background:{FILL[st][0]}"></i>{lab}</span>'
    return fig("各评级指标达标情况", svg(w, h, "".join(b)) + f'<div class="chv-legend">{lg}</div>',
               "门槛与报告评级依据一致：互动率按量级偏低线；点赞率健康区间 0.5%~5%；僵尸粉 ≤10% 达标、>15% 不达标；掉粉 ≤5% 达标、>10% 不达标；断更 ≤14 天达标、>90 天不达标；现存作品获赞占比 ≥80% 达标、<50% 不达标。“未全抓”表示作品太多未全部抓取，不判定。")


# ---------- account: timeline ----------
def months(a, b):
    y, m = map(int, a.split("-"))
    out = []
    while f"{y:04d}-{m:02d}" <= b:
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def timeline(aid):
    a = ACC[aid]
    d, p = a["d"], a["d"]["p"]
    bm = p.get("by_month") or {}
    title = "按月发布与获赞"
    if not bm:
        return fig(title, svg(760, 90, f'<rect x="0" y="0" width="760" height="90" rx="6" fill="#F5F6F7"/>' + T(380, 50, "作品已清空，无时间线", 14, "#8F959E", "middle")), "现存作品数为 0，历史作品已全部删除。")
    ms = months(min(bm), TODAY_M)
    n = len(ms)
    w, h, L, R, Tp, B = 760, 250, 48, 60, 34, 40
    pw = w - L - R
    sw = pw / n
    cnt = [bm.get(m, [0, 0])[0] for m in ms]
    lk = [bm.get(m, [0, 0])[1] for m in ms]
    cmax = max(cnt) or 1
    lmax = max(lk) or 1
    ph = h - Tp - B
    yb = h - B
    b = []
    last = max(bm)
    i = 0
    while i < n:
        if cnt[i] == 0:
            j = i
            while j + 1 < n and cnt[j + 1] == 0:
                j += 1
            tail = ms[i] > last
            if tail:
                lab = f"断更 {d['days']} 天" if (d["days"] or 0) > 30 else ""
                fill = "#F2F3F5"
            else:
                lab = "无发布" if d["full"] else "未抓取"
                fill = "#F7F8FA"
            if lab:
                x0 = L + i * sw
                ww = (j - i + 1) * sw
                b.append(f'<rect x="{x0:.1f}" y="{Tp}" width="{ww:.1f}" height="{ph}" fill="{fill}"/>')
                if tw(lab, 11) < ww - 4:
                    b.append(T(x0 + ww / 2, Tp + 16, lab, 11, "#8F959E", "middle"))
                elif tw(lab, 9) < ww + 20:
                    b.append(T(x0 + ww / 2, Tp + 16, lab, 9, "#8F959E", "middle"))
            i = j + 1
        else:
            i += 1
    for k in range(5):
        y = yb - ph * k / 4
        b.append(f'<line x1="{L}" x2="{w - R}" y1="{y:.1f}" y2="{y:.1f}" stroke="#EEF0F2"/>')
        b.append(T(L - 6, y + 4, f"{cmax * k / 4:.0f}", 10, "#3370FF", "end"))
        b.append(T(w - R + 6, y + 4, wf(lmax * k / 4), 10, "#FF8800"))
    bw = max(2, min(28, sw * 0.6))
    for k, m in enumerate(ms):
        if cnt[k]:
            bh = ph * cnt[k] / cmax
            x = L + k * sw + (sw - bw) / 2
            b.append(f'<rect x="{x:.1f}" y="{yb - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="2" fill="#3370FF" fill-opacity="0.85"/>')
            if n <= 18:
                b.append(T(L + k * sw + sw / 2, yb - bh - 4, f"{cnt[k]}", 10, "#3370FF", "middle"))
    step = max(1, math.ceil(n / 10))
    for k, m in enumerate(ms):
        if k % step == 0 or k == n - 1:
            if k != n - 1 and (n - 1 - k) < step * 0.7:
                continue
            b.append(T(L + k * sw + sw / 2, yb + 16, m, 10, "#646A73", "middle"))
    b.append(f'<line x1="{L}" x2="{w - R}" y1="{yb}" y2="{yb}" stroke="#BBBFC4"/>')
    pts = [(L + k * sw + sw / 2, yb - ph * lk[k] / lmax) for k in range(n) if cnt[k]]
    if len(pts) > 1:
        b.append('<polyline fill="none" stroke="#FF8800" stroke-width="2" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '"/>')
    for x, y in pts:
        b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#FF8800"/>')
    b.append(f'<rect x="{L}" y="8" width="12" height="10" rx="2" fill="#3370FF"/>' + T(L + 16, 17, "当月发布数（条，左轴）", 11, "#646A73"))
    b.append(f'<line x1="{L + 170}" x2="{L + 190}" y1="13" y2="13" stroke="#FF8800" stroke-width="2"/>' + T(L + 196, 17, "当月作品获赞（右轴）", 11, "#646A73"))
    cov = f"统计本次抓取到的 {d['fetched']} 条现存作品（共 {d['works']} 条，含置顶旧作）" + ("" if d["full"] else "，中间月份未覆盖，标为“未抓取”")
    return fig(title, svg(w, h, "".join(b)), f"{cov}；获赞为该月发布作品目前的点赞合计；灰色区为无发布或断更月份，截至 {DATE}。")


# ---------- write ----------
CSS = """.chv-fig{margin:18px 0 22px;font-family:"Microsoft YaHei","PingFang SC",sans-serif;color:#1F2329;break-inside:avoid;page-break-inside:avoid}
.chv-title{font-size:15px;font-weight:600;margin:0 0 8px}
.chv-note{font-size:12px;color:#8F959E;margin-top:6px;line-height:1.6}
.chv-svg{display:block;width:100%;height:auto;max-width:100%}
.chv-legend{font-size:12px;color:#646A73;margin-top:6px}
.chv-lg{display:inline-flex;align-items:center;margin-right:14px}
.chv-lg i{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:5px}
"""
if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "charts.css"), "w", encoding="utf-8").write(CSS)
    ov = '<section id="overview-charts">' + scatter() + drop_chart() + heat() + "</section>"
    open(os.path.join(OUT, "overview_charts.html"), "w", encoding="utf-8").write(ov)
    for aid in ORDER:
        frag = f'<div class="chart-block" data-chart="timeline">{timeline(aid)}</div>'
        open(os.path.join(OUT, f"acct_{aid}.html"), "w", encoding="utf-8").write(frag)
    print("ok", sorted(os.listdir(OUT)), {a: ACC[a]["g"] for a in ORDER})
