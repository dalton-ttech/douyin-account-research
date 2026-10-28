"""分账号详情（简约模式卡片，手机优先、压缩版）：① 账号信息（挂牌行 + 总览样式卡片）② 首页截图（账号信息 + 第一排前 3 条作品，规则见 CROP_RULE.md）③ 结论与评级依据 ④ 数据速览。
输出 <WORK_DIR>/parts/detail_m/acct_<id>.html 与 detail.css。
用法：python scripts/report/build_detail_m.py --config <batch.json> [抖音号 ...]（不带抖音号时生成清单里全部能定位的号）"""
import glob, os, re, sys, html as H

from report_data import ORDER, P, RF, W, OUT as PREV, PARTS, derive, rate, ADVICE, xt_info, dist, listing_line_html
from crop_profile import crop_profile

HERE = PARTS
WD = W
OUT = os.path.join(HERE, "detail_m")
os.makedirs(OUT, exist_ok=True)

SHOT_MODE = "3"
SHOT_PDF_W = 260
e = lambda s: H.escape(str(s))

OVT = open(os.path.join(HERE, "overview_table.html"), encoding="utf-8").read()


def ovt_cells(aid):
    m = re.search(r'<tr data-href="#a-' + re.escape(aid) + r'".*?</tr>', OVT, re.S)
    return re.findall(r"<td>(.*?)</td>", m.group(0), re.S)


def head_crop(aid):
    srcs = [os.path.join(WD, "shots_clean", aid, "01-profile.png"), os.path.join(PREV, aid, "dc-01-profile.jpg")]
    src = next((p for p in srcs if os.path.exists(p)), None)
    if not src:
        return None
    info = crop_profile(src, os.path.join(PREV, aid, "dc-01-home.jpg"), mode=SHOT_MODE, width=SHOT_PDF_W * 2, quality=80)
    return f"{aid}/dc-01-home.jpg", info


def st(res):
    return {"✓": "ok", "△": "mid", "✗": "bad"}.get(res[:1], "na")


def basis_tiles(d, rows):
    p = d["p"]
    short = {
        "近 30 条平均互动率": ("互动率", lambda: "无作品" if d["inter"] is None else f"{d['inter']:.2f}%", f"偏低线 {d['low']}%"),
        "近 30 条单条点赞率（中位数）": ("点赞率中位", lambda: "无作品" if d["like_med"] is None else f"{d['like_med']:.2f}%", "健康 0.5%~5%"),
        "粉丝抽样：疑似僵尸/空壳占比": ("疑似僵尸粉", lambda: "隐私不可见" if d["blocked"] else f"{d['zomb']:.1f}%", "≤10% 达标"),
        "掉粉率（历史最高→当前）": ("掉粉率", lambda: f"{d['drop']:.1f}%", "≤5% 达标"),
        "断更天数": ("断更", lambda: "无作品" if d["days"] is None else f"{d['days']} 天", "≤14 天达标"),
        "获赞能否对上现存作品": ("获赞对得上", lambda: "0%" if d["works"] == 0 else ("未全抓" if d["acc"] is None else f"{d['acc']:.0f}%"), "≥80% 达标"),
        "内容与挂牌类目是否一致": ("内容与挂牌", lambda: {True: "一致", False: "不符"}.get(d["q"]["content_ok"], "未核实"), "不符即 D"),
        "画像与挂牌是否相符": ("画像与挂牌", lambda: "相符" if d["q"]["portrait_ok"] else "无官方画像", "看星图画像"),
        "刷粉/刷赞痕迹": ("刷量痕迹", lambda: "有" if d["q"]["brush"] else "未发现", "出现即 D"),
        "挂牌粉丝与实际差异": ("挂牌粉丝差异", lambda: "—" if p.get("listing_diff_pct") is None else f"{p['listing_diff_pct']:+.1f}%", "±5% 内相符"),
        "爆款依赖（最大爆款 / 均值）": ("爆款依赖", lambda: "—" if p.get("max_over_mean") is None else f"{p['max_over_mean']:.0f} 倍", ">10 倍为依赖"),
    }
    out = []
    for name, actual, thr, res in rows:
        lab, val, sub = short.get(name, (name, lambda: actual, thr))
        s = st(res)
        out.append(f'<div class="bt-t bt-{s}"><div class="bt-l">{e(lab)}</div><div class="bt-v">{e(val())}</div><div class="bt-s">{e(sub)}</div></div>')
    return '<div class="bt-grid">' + "".join(out) + "</div>"


LEGEND = '<span class="bt-lg"><b class="ok"></b>达标<b class="mid"></b>临界<b class="bad"></b>不达标<b class="na"></b>未核实</span>'


def why_text(g, d, trig):
    if g == "A":
        return "全部指标达到 A 档门槛"
    if g == "B":
        return "未达到 A 档全部门槛，但互动率不低于偏低线，掉粉、断更、僵尸粉都在 B 档以内，且未触发 D 条件"
    if g == "D":
        return "触发 D 条件：" + "、".join(trig) + ("（有刷量痕迹，单项即 D）" if "刷粉/刷赞痕迹" in trig else f"（共 {len(trig)} 项，≥2 项即 D）")
    parts = [x for x in [
        "互动率低于偏低线" if d["inter"] is None or d["inter"] < d["low"] else "",
        "断更超过 90 天" if d["days"] is None or d["days"] > 90 else "",
        "僵尸粉超过 15%" if (d["zomb"] or 0) > 15 else "",
        "掉粉超过 10%" if d["drop"] > 10 else ""] if x]
    return "未触发 2 项 D 条件，但" + "、".join(parts) + "，最高只能定为 C" + (f"；已触发 1 项 D 条件：{trig[0]}" if trig else "")


def meter(items, total_label=""):
    segs = "".join(f'<i style="width:{max(v, 0):.1f}%;background:{c}"></i>' for _, v, c in items)
    lg = "".join(f'<span><b style="background:{c}"></b>{e(k)}{v:.0f}%</span>' for k, v, c in items)
    return f'<div class="mt-bar">{segs}</div><div class="mt-lg">{lg}</div>'


def quick(aid, d):
    tiles = []
    xi = xt_info(aid)
    if xi and xi["found"]:
        D = dist(xi["api"])
        sex = D.get("性别分布", {}).get("items") or []
        age = D.get("年龄分布", {}).get("items") or []
        fem = next((pc for k, pc, _ in sex if k in ("female", "女")), None)
        a0 = xi["a0"]
        mk = (xi["api"].get("marketing") or {}).get("b") or {}
        price = "暂无报价" if not mk.get("price_info") else "有报价"
        body = ""
        if fem is not None:
            body += meter([("女", fem, "#F06EA9"), ("男", 100 - fem, "#4E83FD")])
        if age:
            body += f'<div class="qk-l"><b>{e(age[0][0])} 岁</b>最多 {age[0][1]:.0f}% · {price}</div>'
        tiles.append(("星图画像", "已入驻", body, "on"))
    else:
        tiles.append(("星图画像", "未入驻", '<div class="qk-l">按抖音号在星图搜不到，没有官方粉丝画像</div>', "off"))
    if d["blocked"]:
        tiles.append(("粉丝抽样", "隐私", '<div class="qk-l">粉丝列表设为不可见，无法抽样</div>', "off"))
    else:
        al = d["f"]["all"]
        z, zero = al.get("疑似僵尸/空壳_pct", 0), al.get("0作品_pct", 0)
        body = meter([("僵尸", z, "#F54A45"), ("0作品", max(zero - z, 0), "#FFC60A"), ("正常", max(100 - zero, 0), "#34C724")])
        tiles.append(("粉丝抽样", f"{al['n']} 人", body, ""))
    c = d["c"]
    if c:
        emo, gar = c["emoji_only_pct"], c["garbled_pct"]
        body = meter([("表情", emo, "#FFC60A"), ("乱码", gar, "#F54A45"), ("有字", max(100 - emo - gar, 0), "#3370FF")])
        body += f'<div class="qk-l">评论 IP：{e("、".join(k for k, _ in c["ip_top"][:3]))}</div>'
        tiles.append(("评论区", f"{c['n']} 条", body, ""))
    else:
        tiles.append(("评论区", "无", '<div class="qk-l">没有现存作品，无法采集评论</div>', "off"))
    rf = (RF.get("accounts") or {}).get(aid)
    if rf and rf.get("followerCount") is not None:
        rfw = (RF.get("works") or {}).get(aid) or {}
        lib = f"收录 {rfw.get('total')} 条作品（现存 {d['works']}）" if rfw.get("code") == 2000 else "作品库未收录"
        body = f'<div class="qk-l">粉丝 <b>{rf["followerCount"]:,}</b> · IP {e(rf.get("ipLocation") or "—")}</div><div class="qk-l">{lib}</div>'
        tiles.append(("红狐数据", "已收录", body, ""))
    else:
        tiles.append(("红狐数据", "未收录", '<div class="qk-l">账号诊断与作品库均未收录</div>', "off"))
    return '<div class="qk-grid">' + "".join(
        f'<div class="qk {cls}"><div class="qk-h"><span>{e(t)}</span><b>{e(v)}</b></div>{b}</div>' for t, v, b, cls in tiles) + "</div>"


def evidence(aid):
    cand = [("xt-02-home.jpg", "星图主页"), ("xt-01-search.jpg", "星图搜索"), ("dc-02-fans.jpg", "粉丝列表"),
            ("dc-03-top-*.jpg", "最高赞评论区"), ("dc-04-recent-*.jpg", "最近作品评论区"), ("dc-01-profile.jpg", "主页全图")]
    out = []
    seen_xt = False
    for pat, cap in cand:
        hits = sorted(glob.glob(os.path.join(PREV, aid, pat)))
        if not hits:
            continue
        if pat.startswith("xt-"):
            if seen_xt:
                continue
            seen_xt = True
            if pat == "xt-01-search.jpg":
                cap = "星图搜索结果"
        rel = f"{aid}/{os.path.basename(hits[0])}"
        out.append(f'<a class="ev" href="{rel}" target="_blank"><img src="{rel}" loading="lazy" alt=""><span>{e(cap)}</span></a>')
    return '<div class="ev-row">' + "".join(out[:4]) + "</div>"


def squash_chart(f, top=36.0, bot=114.0, k=0.75):
    """把 360×140 时间线图的绘图区（y 36~114）压到 k 倍高、裁掉上下留白；字号和横向坐标不变。"""
    if 'viewBox="0 0 360 140"' not in f:
        return f
    cut = (bot - top) * (1 - k)
    Y = lambda y: y if y <= top else top + (y - top) * k if y <= bot else y - cut

    def el(m):
        t = m.group(0)
        if m.group(1) == "rect":
            y, h = (float(re.search(rf' {a}="([\d.]+)"', t).group(1)) for a in ("y", "height"))
            return re.sub(r' height="[\d.]+"', f' height="{Y(y + h) - Y(y):.1f}"', re.sub(r' y="[\d.]+"', f' y="{Y(y):.1f}"', t))
        if m.group(1) == "polyline":
            return re.sub(r'points="([^"]+)"', lambda p: 'points="' + " ".join(
                f"{x},{Y(float(y)):.1f}" for x, y in (q.split(",") for q in p.group(1).split())) + '"', t)
        return re.sub(r' (y|y1|y2|cy)="([\d.]+)"', lambda a: f' {a.group(1)}="{Y(float(a.group(2))):.1f}"', t)

    f = re.sub(r"<(rect|polyline|text|line|circle)\b[^>]*>", el, f)
    return f.replace('viewBox="0 0 360 140"', f'viewBox="0 3 360 {131 - cut:g}"')


def timeline(aid):
    f = open(os.path.join(HERE, "charts_m", f"acct_{aid}_s.html"), encoding="utf-8").read()
    f = re.sub(r'<div class="chv-note">.*?</div>', "", f, flags=re.S)
    return squash_chart(f).replace('<div class="chv-title">按月发布与获赞</div>', "")


def section(aid):
    d = derive(aid)
    g, rows, trig = rate(d)
    q = d["q"]
    nick = d["p"]["nickname"]
    lline = listing_line_html(aid, nick)
    td = ovt_cells(aid)
    grade = re.search(r'<span class="ovt-grade[^"]*">[A-Z]</span>', td[7]).group(0)
    card = f'''<div class="acard"><div class="ac-top">{td[0]}{grade}</div>
<div class="ac-mid"><div class="ac-mid-l">{td[3]}</div>{td[1]}</div>
<div class="ac-stats"><div class="ac-st"><h6>粉丝</h6>{td[4]}</div><div class="ac-st"><h6>互动 <small>近 30 条</small></h6>{td[5]}</div><div class="ac-st"><h6>风险</h6>{td[6]}</div></div></div>'''
    head, hinfo = head_crop(aid) or (None, None)
    w, h = (hinfo or {}).get("out_size") or ("", "")
    shot = (f'<div class="ad-shotw"><figure class="ad-shot"><a href="{aid}/dc-01-profile.jpg" target="_blank"><img src="{head}" width="{w}" height="{h}" alt=""></a>'
            f'</figure></div>') if head else '<p class="muted">无可用截图。</p>'
    shot_cap = "账号信息 · 0 作品" if hinfo and hinfo["empty"] else f"账号信息 + 前 {SHOT_MODE} 条作品"
    risks = "".join(f"<li>{e(x)}</li>" for x in q["risks"][:2])
    gcls = {"A": "ga", "B": "gb", "C": "gc", "D": "gd"}[g]
    return f'''<section class="acct adet" id="a-{e(aid)}">
<h2 class="ad-h"><span class="g {gcls}">{g}</span> {e(nick)} <small>抖音号 {e(aid)}</small></h2>
<h3>① 账号信息</h3><p class="listing">{lline}</p>{card}
<h3>② 账号首页截图<small>{shot_cap} · 点图看整页</small></h3>{shot}
<h3>③ 结论</h3><div class="ad-verdict ad-{gcls}"><div class="ad-vh"><span class="ad-g">{g}</span><div>{e(q["summary"])}</div></div>
<p class="ad-adv"><span>购买建议</span>{e(ADVICE[g])}</p><div class="ad-risk"><span>主要风险</span><ul>{risks}</ul></div></div>
<div class="ad-basis"><div class="ad-bh">评级依据{LEGEND}<small>{e(why_text(g, d, trig))}</small></div>{basis_tiles(d, rows)}</div>
<h3>④ 数据速览<small>末行为佐证截图 · 点图可放大</small></h3><div class="ad-tl">{timeline(aid)}</div>{quick(aid, d)}
{evidence(aid)}
</section>'''


CSS = r"""
.adet{position:relative;padding-top:4px}
.adet h2.ad-h{position:absolute;width:1px;height:1px;margin:0;padding:0;border:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.adet h3{margin:11px 0 7px;font-size:15px;line-height:1.4}
.adet h2.ad-h+h3{margin-top:2px}
.adet h3 small{font-size:11.5px;font-weight:400;color:#8F959E;margin-left:8px}
.adet .listing{margin:0 0 8px;font-size:13.5px;line-height:1.7;padding:7px 12px}
.acard{border:1px solid #DEE0E3;border-radius:12px;padding:12px 12px 10px;background:#fff;box-shadow:0 1px 3px rgba(31,35,41,.05);color:#1F2329;max-width:640px}
.acard .ac-top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.acard .ovt-who{display:flex;align-items:center;gap:10px;min-width:0}
.acard .ovt-ava{flex:0 0 46px;width:46px;height:46px;border-radius:50%;overflow:hidden;background:#E8EAED;display:block}
.acard .ovt-ava img,.acard .ovt-thumb img{width:100%;height:100%;object-fit:cover;display:block}
.acard .ovt-name{font-weight:600;font-size:16.5px;color:#1F2329;text-decoration:none;line-height:1.35;display:block}
.acard .ovt-id{font-size:12.5px;color:#8F959E}
.acard .ovt-chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:3px}
.acard .ovt-chip{display:inline-flex;align-items:center;gap:3px;font-size:11px;line-height:18px;padding:0 5px;border-radius:4px;background:#F2F3F5;color:#646A73;white-space:nowrap}
.acard .ovt-chip-v{background:#E1EAFF;color:#245BDB}
.acard .ovt-chip-v b{display:inline-block;width:12px;height:12px;line-height:12px;border-radius:50%;background:#3370FF;color:#fff;font-size:9px;text-align:center}
.acard .ovt-grade{flex:none;display:inline-block;text-align:center;font-weight:700;font-size:18px;line-height:34px;min-width:34px;border-radius:8px}
.acard .ovt-gA{background:#D9F5D6;color:#237B19}.acard .ovt-gB{background:#E1EAFF;color:#245BDB}.acard .ovt-gC{background:#FFF0C2;color:#B26A00}.acard .ovt-gD{background:#FDE2E2;color:#D83931}
.acard .ac-mid{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin:8px 0 10px}
.acard .ac-mid-l{min-width:0}
.acard .ovt-tags{display:flex;flex-wrap:wrap;gap:4px}
.acard .ovt-tag{display:inline-block;font-size:12px;line-height:20px;padding:0 6px;border-radius:4px;background:#F2F3F5;color:#646A73;white-space:nowrap;max-width:100%;overflow:hidden;text-overflow:ellipsis}
.acard .ovt-tag-blue{background:#E1EAFF;color:#245BDB}.acard .ovt-tag-orange{background:#FEEAD2;color:#C25705}
.acard .ovt-more{background:#fff;border:1px solid #DEE0E3;line-height:18px;color:#8F959E}
.acard .ovt-thumbs{display:flex;gap:5px;flex:none}
.acard .ovt-thumb{position:relative;flex:0 0 52px;width:52px;height:52px;border-radius:6px;overflow:hidden;background:#E8EAED;display:block}
.acard .ovt-like{position:absolute;right:2px;bottom:2px;display:inline-flex;align-items:center;gap:2px;padding:0 3px;border-radius:3px;background:rgba(0,0,0,.55);color:#fff;font-size:10px;line-height:14px}
.acard .ovt-like svg{width:8px;height:8px;fill:#fff}
.acard .ac-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.acard .ac-st{background:#F7F8FA;border-radius:8px;padding:8px 8px 7px}
.acard .ac-st h6{margin:0 0 3px;font-size:11.5px;font-weight:600;color:#646A73}
.acard .ac-st h6 small{font-weight:400;color:#8F959E}
.acard .ovt-kv{font-size:12px;line-height:1.6;color:#646A73}
.acard .ovt-k{color:#8F959E}
.acard .ovt-kv b{font-size:13.5px;font-weight:600;color:#1F2329}
.acard .ovt-kv .ovt-s{display:block;font-size:11.5px;line-height:1.4;color:#8F959E;margin-bottom:2px}
.acard .ovt-warn b,.acard .ovt-warn .ovt-s{color:#C25705}
.acard .ovt-bad b,.acard .ovt-bad .ovt-s{color:#D83931}
.acard .ovt-mute b{color:#646A73;font-weight:400}
.acard .ovt-on b{color:#245BDB}
.adet .ad-shotw{max-width:640px}
.adet .ad-shot{margin:0 auto;width:min(100%,400px);border:1px solid #DEE0E3;border-radius:10px;overflow:hidden;padding:0;background:#16161E}
.adet .ad-shot img{width:100%;height:auto;display:block}
.ad-verdict{border-radius:12px;padding:10px 12px;background:#F7F8FA;border:1px solid #EFF0F1;max-width:640px}
.ad-verdict .ad-vh{display:flex;gap:10px;align-items:flex-start;font-size:14px;line-height:1.65;font-weight:600;color:#1F2329}
.ad-verdict .ad-g{flex:none;width:34px;height:34px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:19px;font-weight:800}
.ad-gc .ad-g{background:#FFF0C2;color:#B26A00}.ad-gd .ad-g{background:#FDE2E2;color:#D83931}.ad-ga .ad-g{background:#D9F5D6;color:#237B19}.ad-gb .ad-g{background:#E1EAFF;color:#245BDB}
.ad-verdict .ad-vh b{font-size:15px;line-height:1.6;font-weight:600;color:#1F2329}
.ad-verdict .ad-adv{margin:6px 0 0;font-size:13px;line-height:1.6}
.ad-verdict .ad-adv span,.ad-verdict .ad-risk>span{display:inline-block;font-size:11.5px;font-weight:600;color:#3370FF;background:#E1EAFF;border-radius:4px;padding:0 6px;margin-right:6px;line-height:20px}
.ad-verdict .ad-risk{margin-top:4px}
.ad-verdict .ad-risk ul{margin:3px 0 0;padding-left:18px}
.ad-verdict .ad-risk li{font-size:12.5px;line-height:1.5;margin:1px 0;color:#1F2329}
.ad-basis{margin-top:8px;max-width:640px}
.ad-basis .ad-bh{font-size:14px;font-weight:600;margin-bottom:4px}
.ad-basis .ad-bh small{display:block;font-size:12px;font-weight:400;color:#646A73;line-height:1.55;margin-top:1px}
.bt-lg{float:right;font-size:10.5px;font-weight:400;color:#8F959E;display:inline-flex;align-items:center;gap:3px;margin-top:3px}
.bt-lg b{display:inline-block;width:8px;height:8px;border-radius:2px;margin-left:5px}
.bt-lg b.ok{background:#34C724}.bt-lg b.mid{background:#FFC60A}.bt-lg b.bad{background:#F54A45}.bt-lg b.na{background:#BBBFC4}
.bt-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px}
.bt-t{border-radius:7px;padding:3px 6px 4px;background:#F7F8FA;border-top:3px solid #BBBFC4;min-width:0}
.bt-t .bt-l{font-size:10.5px;line-height:1.35;color:#646A73;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bt-t .bt-v{font-size:14px;font-weight:700;line-height:1.3;color:#1F2329;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bt-t .bt-s{font-size:10px;line-height:1.3;color:#8F959E;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bt-ok{border-top-color:#34C724;background:#F2FBF0}
.bt-mid{border-top-color:#FFC60A;background:#FFFAE8}
.bt-bad{border-top-color:#F54A45;background:#FEF1F1}.bt-bad .bt-v{color:#D83931}
.adet .ad-sub{font-size:14px;font-weight:600;margin:4px 0 6px}
.adet .ad-sub small{font-weight:400;font-size:12px;color:#8F959E;margin-left:8px}
.adet .ad-tl{max-width:640px}
.adet .ad-tl .chv-fig{margin:0 0 6px}
.adet .ad-tl .chv-svg{display:block;width:92%;margin:0 auto}
.adet .ad-tl .chv-note{margin-top:2px;font-size:11.5px}
.qk-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin:0 0 8px;max-width:640px}
.qk{border:1px solid #EFF0F1;border-radius:10px;padding:5px 7px 6px;background:#fff;min-width:0}
.qk-h{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:3px}
.qk-h span{font-size:12px;color:#646A73;font-weight:600}
.qk-h b{font-size:14px;color:#1F2329}
.qk.on .qk-h b{color:#245BDB}.qk.off .qk-h b{color:#8F959E}
.qk-l{font-size:11.5px;line-height:1.5;color:#646A73;margin-top:3px}
.qk-l b{color:#1F2329}
.mt-bar{display:flex;height:8px;border-radius:4px;overflow:hidden;background:#EFF0F1}
.mt-bar i{display:block;height:100%}
.mt-lg{display:flex;flex-wrap:wrap;gap:2px 5px;font-size:10px;color:#646A73;margin-top:4px;letter-spacing:-.3px}
.mt-lg span{display:inline-flex;align-items:center;gap:2px;white-space:nowrap}
.mt-lg b{display:inline-block;width:8px;height:8px;border-radius:2px}
.ev-row{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;max-width:640px}
.ev{position:relative;display:block;text-decoration:none;min-width:0;border-radius:6px;overflow:hidden;border:1px solid #DEE0E3}
.ev img{display:block;width:100%;aspect-ratio:11/5;object-fit:cover;object-position:top left;background:#F2F3F5}
.ev span{position:absolute;left:0;right:0;bottom:0;font-size:10.5px;line-height:16px;padding:6px 4px 1px;text-align:center;color:#fff;background:linear-gradient(transparent,rgba(31,35,41,.85))}
@media print{.adet .ad-shot a::after,.ev::after{display:none}.adet .ad-shot{width:__SHOT_PDF_W__px}}
""".replace("__SHOT_PDF_W__", str(SHOT_PDF_W))

ids = [a for a in sys.argv[1:] if not a.startswith("-")] or ORDER
skip = [a for a in ids if not derive(a)]
ids = [a for a in ids if derive(a)]
open(os.path.join(OUT, "detail.css"), "w", encoding="utf-8").write(CSS)
for aid in ids:
    open(os.path.join(OUT, f"acct_{aid}.html"), "w", encoding="utf-8").write(section(aid))
print("ok", ids, "（无法定位、保留完整版小节：" + "、".join(skip) + "）" if skip else "")
