"""手机版图表（宽 360）：parts/charts_m/overview_charts.html、acct_<id>.html、acct_<id>_s.html（矮版时间线，供简约详情卡片）。

用法：python scripts/report/build_charts_m.py --config <batch.json>
复用 build_charts.py 的数据与函数；短昵称取账号清单的 short 字段或 batch.json 的 short_names。
"""
import os, math
from build_charts import ORDER, ACC, T, svg, fig, tw, wf, status, FILL, GC, COLS, months, pv, TODAY_M, esc, GRADES, NO_WORKS_NOTE
from report_data import PARTS, DATE, short

OUT = os.path.join(PARTS, "charts_m")
W = 360
GOOD, WARN, BAD = "#2A9D1A", "#D97706", "#D83931"


def legend_grades(x, y):
    out = []
    for g in GRADES:
        out.append(f'<circle cx="{x + 5}" cy="{y - 4}" r="5" fill="{GC[g]}"/>' + T(x + 14, y, f"评级 {g}", 11, "#646A73"))
        x += 62
    return "".join(out)


def likeplot():
    rows = sorted([a for a in ORDER if ACC[a]["d"]["like_med"] is not None], key=lambda a: -ACC[a]["d"]["fans"])
    nw, R, top, rh = 84, 50, 46, 36
    x0, x1 = nw, W - R
    lo, hi = math.log10(0.005), math.log10(10)
    px = lambda v: x0 + (math.log10(min(max(v, 0.005), 10)) - lo) / (hi - lo) * (x1 - x0)
    yb = top + rh * len(rows)
    h = yb + 26
    b = [legend_grades(0, 14)]
    b.append(f'<rect x="{px(0.5):.1f}" y="{top - 8}" width="{px(5) - px(0.5):.1f}" height="{yb - top + 8}" fill="#E8F8E5"/>')
    b.append(T((px(0.5) + px(5)) / 2, top - 14, "健康区间 0.5%~5%", 11, GOOD, "middle"))
    for v in (0.01, 0.1, 1, 10):
        b.append(f'<line x1="{px(v):.1f}" x2="{px(v):.1f}" y1="{top - 8}" y2="{yb}" stroke="#E4E6E9" stroke-dasharray="2 3"/>')
        b.append(T(px(v), yb + 16, f"{v:g}%", 10, "#8F959E", "middle"))
    for i, a in enumerate(rows):
        d = ACC[a]["d"]
        y = top + i * rh + rh / 2
        v = d["like_med"]
        b.append(T(nw - 10, y - 1, short(a), 12, "#1F2329", "end"))
        b.append(T(nw - 10, y + 13, f"{wf(d['fans'])} 粉", 10, "#8F959E", "end"))
        b.append(f'<line x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}" stroke="#DEE0E3"/>')
        b.append(f'<circle cx="{px(v):.1f}" cy="{y:.1f}" r="6.5" fill="{GC[ACC[a]["g"]]}" stroke="#fff" stroke-width="1.5"/>')
        b.append(T(W - 2, y + 4, pv(v), 12, GOOD if v >= 0.5 else BAD, "end", "bold"))
    n_low = sum(1 for a in rows if ACC[a]["d"]["like_med"] < 0.5)
    return fig(f"粉丝量与近期点赞率：{n_low} 个号低于健康区间", svg(W, h, "".join(b)),
               "按粉丝数从多到少排列；点赞率 = 近 30 条作品每条点赞 ÷ 当前粉丝，取中位数，横轴为对数刻度。" + NO_WORKS_NOTE)


def drop_m():
    rows = sorted(ORDER, key=lambda a: -ACC[a]["d"]["drop"])
    top, rh = 34, 46
    mx = max(ACC[a]["d"]["p"]["max_fans"] for a in ORDER)
    sc = lambda v: (W - 2) * v / mx
    h = top + rh * len(rows)
    b = [f'<rect x="0" y="6" width="14" height="10" rx="2" fill="#C9D8FF"/>', T(20, 15, "历史最高", 11, "#646A73"),
         f'<rect x="84" y="8" width="14" height="6" rx="1" fill="#3370FF"/>', T(104, 15, "当前粉丝", 11, "#646A73"),
         T(W, 15, "掉粉率", 11, "#8F959E", "end")]
    for i, a in enumerate(rows):
        d, p = ACC[a]["d"], ACC[a]["d"]["p"]
        y = top + i * rh
        dr = d["drop"]
        col = BAD if dr > 10 else (WARN if dr > 5 else GOOD)
        b.append(T(0, y + 14, short(a), 12, "#1F2329"))
        b.append(T(W - 58, y + 14, f"{wf(d['fans'])} / {wf(p['max_fans'])}", 11, "#8F959E", "end"))
        b.append(T(W, y + 14, f"-{dr:.1f}%", 13, col, "end", "bold"))
        b.append(f'<rect x="0" y="{y + 21}" width="{max(sc(p["max_fans"]), 2):.1f}" height="14" rx="3" fill="#C9D8FF"/>')
        b.append(f'<rect x="0" y="{y + 24}" width="{max(sc(d["fans"]), 2):.1f}" height="8" rx="2" fill="#3370FF"/>')
    over = sum(1 for x in ORDER if ACC[x]["d"]["drop"] > 10)
    return fig(f"掉粉对比：{over} 个号较历史最高掉粉超过 10%", svg(W, h, "".join(b)),
               f"按掉粉率从高到低排列；浅色条为历史最高粉丝，深色条为当前粉丝（{DATE} 查询）。掉粉率 ≤5% 绿、5%~10% 橙、>10% 红（>10% 为 D 级触发条件）。")


HEAD = ["互动", "点赞", "僵尸", "掉粉", "断更", "获赞", "内容", "画像", "刷量", "评级"]
SYM = {"ok": "✓", "mid": "!", "bad": "✗", "na": "–"}


def heat_m():
    nw, top, rh = 62, 30, 32
    cw = (W - nw) / len(HEAD)
    h = top + rh * len(ORDER) + 4
    b = []
    for j, c in enumerate(HEAD):
        b.append(T(nw + cw * j + cw / 2, top - 10, c, 11, "#646A73", "middle", "bold"))
    for i, a in enumerate(ORDER):
        y = top + i * rh
        b.append(T(nw - 8, y + 20, short(a), 12, "#1F2329", "end"))
        for j, (c, key) in enumerate(COLS):
            st = status(ACC[a], key)
            if c == "点赞率中位" and ACC[a]["d"]["like_med"] is None:
                st = "na"
            bg, fg = FILL[st]
            b.append(f'<rect x="{nw + cw * j + 1.5:.1f}" y="{y + 2}" width="{cw - 3:.1f}" height="{rh - 4}" rx="4" fill="{bg}"/>')
            b.append(T(nw + cw * j + cw / 2, y + 21, SYM[st], 13, fg, "middle", "bold"))
        j = len(COLS)
        b.append(f'<rect x="{nw + cw * j + 1.5:.1f}" y="{y + 2}" width="{cw - 3:.1f}" height="{rh - 4}" rx="4" fill="{GC[ACC[a]["g"]]}"/>')
        b.append(T(nw + cw * j + cw / 2, y + 21, ACC[a]["g"], 14, "#fff", "middle", "bold"))
    lg = "".join(f'<span class="chv-lg"><i style="background:{FILL[st][0]}"></i>{SYM[st]} {lab}</span>'
                 for st, lab in (("ok", "达标"), ("mid", "临界"), ("bad", "不达标"), ("na", "无数据")))
    return fig("各评级指标达标情况", svg(W, h, "".join(b)) + f'<div class="chv-legend">{lg}</div>',
               "列名含义：互动 = 近 30 条平均互动率；点赞 = 单条点赞率中位数；僵尸 = 粉丝抽样疑似僵尸占比；掉粉 = 较历史最高；断更 = 距最后一条作品；获赞 = 总获赞能否对上现存作品；内容 = 内容与挂牌类目一致；画像 = 画像与挂牌相符；刷量 = 刷粉刷赞痕迹。具体数值见各账号详情。")


def timeline_m(aid, h=220):
    a = ACC[aid]
    d, p = a["d"], a["d"]["p"]
    bm = p.get("by_month") or {}
    title = "按月发布与获赞"
    if not bm:
        return fig(title, svg(W, 64, f'<rect x="0" y="0" width="{W}" height="64" rx="8" fill="#F5F6F7"/>' + T(W / 2, 38, "作品已清空，无时间线", 14, "#8F959E", "middle")),
                   "现存作品数为 0，历史作品已全部删除。")
    ms = months(min(bm), TODAY_M)
    n = len(ms)
    L, R, Tp, B = 30, 38, 36, 26
    pw = W - L - R
    sw = pw / n
    cnt = [bm.get(m, [0, 0])[0] for m in ms]
    lk = [bm.get(m, [0, 0])[1] for m in ms]
    cmax, lmax = max(cnt) or 1, max(lk) or 1
    ph, yb = h - Tp - B, h - B
    last = max(bm)
    b = []
    i = 0
    while i < n:
        if cnt[i] == 0:
            j = i
            while j + 1 < n and cnt[j + 1] == 0:
                j += 1
            tail = ms[i] > last
            lab = (f"断更 {d['days']} 天" if (d["days"] or 0) > 30 else "") if tail else ("无发布" if d["full"] else "未抓取")
            if lab:
                x0, ww = L + i * sw, (j - i + 1) * sw
                b.append(f'<rect x="{x0:.1f}" y="{Tp}" width="{ww:.1f}" height="{ph}" fill="{"#F2F3F5" if tail else "#F7F8FA"}"/>')
                for fs in (11, 10, 9):
                    if tw(lab, fs) < ww - 2:
                        b.append(T(x0 + ww / 2, Tp + 15, lab, fs, "#8F959E", "middle"))
                        break
            i = j + 1
        else:
            i += 1
    for k in range(5):
        y = yb - ph * k / 4
        b.append(f'<line x1="{L}" x2="{W - R}" y1="{y:.1f}" y2="{y:.1f}" stroke="#EEF0F2"/>')
        if k % 2 == 0:
            b.append(T(L - 5, y + 4, f"{cmax * k / 4:.0f}", 10, "#3370FF", "end"))
            b.append(T(W - R + 5, y + 4, wf(lmax * k / 4), 10, "#E07B00"))
    bw = max(2, min(22, sw * 0.62))
    for k in range(n):
        if cnt[k]:
            bh = ph * cnt[k] / cmax
            x = L + k * sw + (sw - bw) / 2
            b.append(f'<rect x="{x:.1f}" y="{yb - bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="2" fill="#3370FF" fill-opacity="0.85"/>')
            if n <= 9:
                b.append(T(L + k * sw + sw / 2, yb - bh - 4, f"{cnt[k]}", 10, "#3370FF", "middle"))
    step = max(1, math.ceil(n / 4))
    for k, m in enumerate(ms):
        if k % step == 0 or k == n - 1:
            if k != n - 1 and (n - 1 - k) < step * 0.8:
                continue
            lab = m if n <= 6 else m[2:]
            b.append(T(L + k * sw + sw / 2, yb + 16, lab, 10, "#646A73", "middle"))
    b.append(f'<line x1="{L}" x2="{W - R}" y1="{yb}" y2="{yb}" stroke="#BBBFC4"/>')
    pts = [(L + k * sw + sw / 2, yb - ph * lk[k] / lmax) for k in range(n) if cnt[k]]
    if len(pts) > 1:
        b.append('<polyline fill="none" stroke="#FF8800" stroke-width="2" points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + '"/>')
    for x, y in pts:
        b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#FF8800"/>')
    b.append(f'<rect x="0" y="6" width="12" height="10" rx="2" fill="#3370FF"/>' + T(17, 15, "每月发布条数（左轴）", 11, "#646A73"))
    b.append(f'<line x1="160" x2="178" y1="11" y2="11" stroke="#FF8800" stroke-width="2"/>' + T(183, 15, "当月作品获赞（右轴）", 11, "#646A73"))
    cov = f"统计本次抓取到的 {d['fetched']} 条现存作品（共 {d['works']} 条，含置顶旧作）" + ("" if d["full"] else "，中间月份未覆盖，标为“未抓取”")
    return fig(title, svg(W, h, "".join(b)), f"{cov}；获赞为该月发布作品目前的点赞合计；灰色区为无发布或断更月份，截至 {DATE}。")


os.makedirs(OUT, exist_ok=True)
ov = '<section id="overview-charts">' + likeplot() + drop_m() + heat_m() + "</section>"
open(os.path.join(OUT, "overview_charts.html"), "w", encoding="utf-8").write(ov)
for aid in ORDER:
    open(os.path.join(OUT, f"acct_{aid}.html"), "w", encoding="utf-8").write(
        f'<div class="chart-block" data-chart="timeline">{timeline_m(aid)}</div>')
    open(os.path.join(OUT, f"acct_{aid}_s.html"), "w", encoding="utf-8").write(
        f'<div class="chart-block" data-chart="timeline">{timeline_m(aid, 140)}</div>')
print("ok", len(os.listdir(OUT)))
