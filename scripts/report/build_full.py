"""完整版（桌面）报告：<PREVIEW_DIR>/report-full.html。两种模式都先跑它，简约模式在它的基础上再加工。

用法：python scripts/report/build_full.py --config <batch.json> [--no-merge]
  第一遍加 --no-merge：只生成基础报告（总览表脚本从这一遍解析数字）。
  第二遍不加：用 merge_parts.merge() 合并 parts/overview_table.html 和 parts/charts/。
每个号依次为 ① 账号信息 → ② 首页截图 → ③ 星图截图 → ④ 全部数据、图表和评级依据。
批次专属的文字放在 qual.json 的 notes 里（见 scripts/README.md），不写进脚本。
"""
import os, re, sys, datetime
from report_data import *  # noqa: F401,F403
from report_data import BATCH, ORDER, P, RF, OUT, DATE, NOTES, e, fig, shots_for, derive, rate, why_full, xt_info, xt_block, dist, bars, \
    qual, nick, listing, listing_line_html, std_rows, TIERS, ADVICE, GCLS, GRADE_NOTES, SRC_NEWRANK, SRC_ZHB, redfox_time, fans_sample_range

NO_MERGE = "--no-merge" in sys.argv
NOW = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

# ---------- build ----------
rows_summary = []
sections = []
grades = {}
for aid in ORDER:
    shots = shots_for(aid)
    d = derive(aid)
    q = qual(aid)
    lst = listing(aid)
    rf = (RF.get("accounts") or {}).get(aid)
    if rf and rf.get("followerCount") is None:
        rf = None
    rfw = (RF.get("works") or {}).get(aid) or {}
    if d is None:
        g, basis, trig = "—", [("账号定位", "抖音号搜索 / 综合搜索 / 红狐 / 星图均无结果", "能打开主页", "✗ 无法定位")], []
    else:
        g, basis, trig = rate(d)
    grades[aid] = g
    nk = nick(aid) if d else "（未能定位）"
    lfans = f"{lst[0]/10000:g} 万" if lst and lst[0] else "—"
    lsub = " · ".join(str(x) for x in lst[1:] if x) if lst else ""
    # summary row
    if d:
        p = d["p"]
        xi = xt_info(aid)
        portrait = []
        if xi and xi["found"]:
            D = dist(xi["api"])
            portrait.append("星图：" + "，".join(x for x in [D.get("性别分布", {}).get("desc"), D.get("年龄分布", {}).get("desc")] if x))
        cip = (d["c"].get("ip_top") or [])[:3]
        if cip:
            portrait.append("评论 IP：" + "、".join(k for k, _ in cip))
        zs = "隐私不可见" if d["blocked"] else f"{d['zomb']:.1f}%（0 作品 {d['zero']:.0f}%）"
        inter_s = "—" if d["inter"] is None else f"{d['inter']:.2f}% / {d['inter_med']:.2f}%<br><small>偏低线 {d['low']}%</small>"
        diff = "—" if p.get("listing_diff_pct") is None else f"{p['listing_diff_pct']:+.1f}%"
        rows_summary.append(f"""<tr><td><b>{e(nk)}</b><br><small>{e(aid)}</small></td><td>{e(lfans)}<br><small>{e(lsub)}</small></td>
<td>{d['fans']/10000:.2f} 万<br><small>{diff}</small></td><td>{p['max_fans']/10000:.2f} 万<br><small>掉粉 {d['drop']:.1f}%</small></td><td>{p['like_fan_ratio']:.2f}</td>
<td>{inter_s}</td><td>{'—' if d['like_med'] is None else f"{d['like_med']:.2f}%"}</td><td>{zs}</td><td><small>{e('；'.join(portrait) or '—')}</small></td>
<td class="g {GCLS[g]}">{g}</td><td><small>{e(ADVICE[g])}</small></td><td><small>{e(q['risks'][0])}</small></td></tr>""")
    else:
        rows_summary.append(f"""<tr><td><b>（未能定位）</b><br><small>{e(aid)}</small></td><td>{e(lfans)}<br><small>{e(lsub)}</small></td><td colspan="7" class="muted">四个渠道均查不到该抖音号，所有指标未能验证</td><td class="g gn">—</td><td><small>{e(ADVICE['—'])}</small></td><td><small>{e(q['risks'][0])}</small></td></tr>""")
    # basis table
    btbl = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td><td class='{('ok' if r_.startswith('✓') else 'bad' if r_.startswith('✗') else 'mid')}'>{e(r_)}</td></tr>" for a, b, c, r_ in basis)
    why = why_full(g, d, trig) if d else why_full("—", None, [])
    rk = "".join(f"<li>{e(x)}</li>" for x in q["risks"])
    if d is None:
        sections.append(f"""<section class="acct" id="a-{e(aid)}">
<h2 class="nw"><span class="g gn">—</span> （未能定位） <small class="nw">抖音号 {e(aid)}</small></h2>
<h3>① 账号信息</h3><p class="listing">{listing_line_html(aid, '（未能定位）')}</p>
<p class="muted">账号无法定位，未采集。</p>
<div class="verdict"><p><b>结论：</b>{e(q['summary'])}</p><p><b>评级：</b><span class="g gn">—</span>　<b>购买建议：</b>{e(ADVICE['—'])}</p>
<p><b>主要风险：</b></p><ul>{rk}</ul>
<div class="basis"><div class="bt">评级依据　<span>{e(why)}</span></div><table><tr><th>指标</th><th>实际值</th><th>门槛</th><th>结果</th></tr>{btbl}</table></div></div>
</section>""")
        continue
    # metrics block
    p = d["p"]
    mk = [
        ("当前粉丝 / 历史最高", f"{d['fans']:,} / {p['max_fans']:,}"), ("总获赞 / 赞粉比", f"{p['likes_total']:,} / {p['like_fan_ratio']:.2f}"),
        ("作品数（抓取）", f"{d['works']}（{d['fetched']}）"), ("量级 / 红狐基准线", f"{d['tname']}：优秀 {d['excellent']}% · 良好 {d['good']}% · 偏低 {d['low']}%"),
        ("近 30 条平均 赞/评/藏/转", "—" if p.get('r30_mean_like') is None else f"{p['r30_mean_like']:.0f} / {p['r30_mean_cmt']:.0f} / {p['r30_mean_collect']:.0f} / {p['r30_mean_share']:.0f}"),
        ("近 30 条中位 赞/评/藏/转", "—" if p.get('r30_med_like') is None else f"{p['r30_med_like']:.0f} / {p['r30_med_cmt']:.0f} / {p['r30_med_collect']:.0f} / {p['r30_med_share']:.0f}"),
        ("互动率 均值 / 中位", "—" if d['inter'] is None else f"{d['inter']:.3f}% / {d['inter_med']:.3f}%"),
        ("点赞率 均值 / 中位", "—" if p.get('like_rate_mean_pct') is None else f"{p['like_rate_mean_pct']:.3f}% / {p['like_rate_med_pct']:.3f}%"),
        ("top3 作品获赞占比 / 最大爆款÷均值", "—" if p.get('top3_share') is None else f"{p['top3_share']*100:.0f}% / {p['max_over_mean']:.1f} 倍"),
        ("首条 / 最后一条作品", f"{p.get('first_post') or '—'} / {p.get('last_post') or '—'}"),
    ]
    bm = p.get("by_month") or {}
    if isinstance(bm, dict) and bm:
        mk.append(("按月发布（条数 / 获赞）", "；".join(f"{k}: {v[0]} 条 / {v[1]:,}" for k, v in list(bm.items())[-8:])))
    mblock = "<table class='kv'>" + "".join(f"<tr><th>{e(a)}</th><td>{e(b)}</td></tr>" for a, b in mk) + "</table>"
    # fans block
    fblock = ""
    if not d["blocked"]:
        fa = d["f"]

        def g3(gn):
            x = fa.get(gn) or {}
            return f"{x.get('n',0)} 人：疑似僵尸 {x.get('疑似僵尸/空壳_pct',0) or 0:.1f}% · 0 作品 {x.get('0作品_pct',0) or 0:.1f}% · 默认头像 {x.get('默认头像_pct',0) or 0:.1f}% · 默认昵称 {x.get('默认昵称_pct',0) or 0:.1f}%"
        al = fa["all"]
        pr = "；".join(f"{x['at']} 附近约 {x.get('per_day','—')} 人/天" for x in fa.get("probes", []))
        fblock = f"""<table class='kv'><tr><th>全部抽样</th><td>{e(g3('all'))}</td></tr><tr><th>最近关注</th><td>{e(g3('recent'))}</td></tr><tr><th>涨粉高峰期</th><td>{e(g3('peak'))}</td></tr><tr><th>历史时间探针</th><td>{e(g3('probe'))}</td></tr>
<tr><th>其他特征</th><td>关注≥3000（互粉/营销）{al.get('关注≥3000_pct',0):.1f}% · 疑似营销 {al.get('疑似营销/互粉_pct',0):.1f}% · 昵称偏中老年 {al.get('昵称偏中老年_pct',0):.1f}% · 偏宝妈/亲子 {al.get('昵称偏宝妈/亲子_pct',0):.1f}% · 粉丝的粉丝数中位 {al.get('粉丝数中位')} · 作品数中位 {al.get('作品数中位')}</td></tr>
<tr><th>涨粉速度（时间探针）</th><td>{e(pr)}</td></tr>
<tr><th>粉丝主页画像抽样</th><td>{fa.get('profiles_n',0)} 人；性别 {e(fa.get('gender'))}；年龄 {e(fa.get('ages'))}；IP {e('、'.join(f'{k}{v}' for k,v in (fa.get('ip') or [])[:6]))}</td></tr></table>"""
    else:
        fblock = "<p>粉丝列表设为隐私，无法抽样。</p>"
    cblock = ""
    if d["c"] and d["c"].get("n"):
        c = d["c"]
        cblock = f"""<table class='kv'><tr><th>样本</th><td>{c['n']} 条评论 / {c['unique_users']} 个用户，来自 {len(c['videos'])} 条作品（最近 3 条 + 爆款 2 条，每条最多 3 页）</td></tr>
<tr><th>评论者 IP Top</th><td>{e('、'.join(f'{k} {v}' for k,v in c['ip_top'][:8]))}（共 {c['ip_distinct']} 个省份，最大省份占 {c['ip_top1_share']}%）</td></tr>
<tr><th>内容特征</th><td>纯表情 {c['emoji_only_pct']}% · 乱码/无意义 {c['garbled_pct']}% · 默认昵称 {e(c['default_nick'])} · 中老年风格昵称 {e(c['midage_nick'])} · 宝妈相关 {e(c['mom_text'])} · 儿童相关 {e(c['kid_text'])}</td></tr>
<tr><th>作者互动</th><td>作者回复 {c['author_comments']} 条 · 作者点赞评论 {c['author_digged']} 条</td></tr></table>"""
    else:
        cblock = "<p>无现存作品，无法采集评论。</p>"
    rblock = ""
    if rf:
        sim = rf.get("similarAccounts") or []
        rblock = f"<table class='kv'><tr><th>红狐账号诊断</th><td>粉丝 {rf.get('followerCount'):,} · IP 属地 {e(rf.get('ipLocation') or '—')} · 作品 {rf.get('awemeCount')} · 抓取时间 {e(rf.get('crawlTime'))}</td></tr><tr><th>红狐作品库</th><td>{('收录 ' + str(rfw.get('total')) + ' 条（现存 ' + str(d['works']) + ' 条）') if rfw.get('code') == 2000 else '未收录'}</td></tr><tr><th>相似账号</th><td>{len(sim)} 个</td></tr></table>"
    else:
        rblock = "<p>红狐账号诊断、作品库、用户搜索均未收录。</p>"
    # figures
    figs = []
    if shots.get("01-profile"): figs.append(fig(shots["01-profile"], f"抖音主页（{DATE} 截图）"))
    if shots.get("02-fans"): figs.append(fig(shots["02-fans"], "粉丝列表弹窗" + ("（粉丝列表设为隐私）" if d["blocked"] else "（粉丝昵称与头像已打码）")))
    top = [k for k in shots if k.startswith("03-top")]
    rec = [k for k in shots if k.startswith("04-recent")]
    if top: figs.append(fig(shots[top[0]], "获赞最高的作品及评论区（评论者昵称与头像已打码）" + (f"：{q['evidence_note']}" if q.get("evidence_note") else "")))
    if rec: figs.append(fig(shots[rec[0]], "最近一条作品及评论区（评论者昵称与头像已打码）"))
    p0 = d["p"]
    kp = [("实际粉丝", f"{d['fans']/10000:.2f} 万"), ("历史最高", f"{p0['max_fans']/10000:.2f} 万"), ("掉粉率", f"{d['drop']:.1f}%"), ("总获赞", f"{p0['likes_total']/10000:.1f} 万"),
          ("作品数", f"{d['works']}"), ("断更天数", "无作品" if d['days'] is None else f"{d['days']} 天"), ("近期点赞率（中位）", "—" if d['like_med'] is None else f"{d['like_med']:.2f}%"), ("评级", g)]
    kpis = "".join(f'<div class="kpi{" kg " + GCLS[g] if k == "评级" else ""}"><div class="kl">{e(k)}</div><div class="kv nw">{e(v)}</div></div>' for k, v in kp)
    fbars = ""
    if not d["blocked"]:
        al = d["f"]["all"]
        fbars = '<div class="chart wide"><h5>粉丝抽样构成（共 ' + str(al["n"]) + ' 人）</h5>' + bars([("疑似僵尸/空壳", al.get("疑似僵尸/空壳_pct", 0), 0), ("0 作品", al.get("0作品_pct", 0), 0), ("默认头像", al.get("默认头像_pct", 0), 0), ("默认昵称", al.get("默认昵称_pct", 0), 0), ("关注≥3000", al.get("关注≥3000_pct", 0), 0)], 6) + "</div>"
    cbars = ""
    if d["c"] and d["c"].get("n"):
        cc = d["c"]

        def pp(v):
            try:
                return float(str(v).split("(")[1].rstrip("%)")) if "(" in str(v) else float(v)
            except Exception:
                return 0.0
        cbars = '<div class="chart wide"><h5>评论类型（共 ' + str(cc["n"]) + ' 条）</h5>' + bars([("纯表情", cc["emoji_only_pct"], 0), ("乱码/无意义", cc["garbled_pct"], 0), ("默认昵称", pp(cc["default_nick"]), 0), ("中老年风格昵称", pp(cc["midage_nick"]), 0)], 6) + "</div>"
        cbars += '<div class="chart wide"><h5>评论者 IP 省份（前 8）</h5>' + bars([(k, v / cc["n"] * 100, v) for k, v in cc["ip_top"][:8]], 8) + "</div>"
    acc_bar = ""
    if d["acc"] is not None:
        acc_bar = '<div class="chart wide"><h5>现存作品获赞占总获赞比例</h5>' + bars([("现存作品", d["acc"], 0), ("已删作品", 100 - d["acc"], 0)], 2) + "</div>"
    elif d["works"] == 0:
        acc_bar = '<div class="chart wide"><h5>现存作品获赞占总获赞比例</h5>' + bars([("现存作品", 0, 0), ("已删作品", 100, 0)], 2) + "</div>"
    drop_bar = '<div class="chart wide"><h5>当前粉丝 vs 历史最高</h5>' + bars([("历史最高", 100, 0), ("当前", d["fans"] / (p0["max_fans"] or d["fans"] or 1) * 100, 0)], 2) + "</div>"
    prof = shots.get("01-profile")
    sections.append(f"""<section class="acct" id="a-{e(aid)}">
<h2 class="nw"><span class="g {GCLS[g]}">{g}</span> {e(nk)} <small class="nw">抖音号 {e(aid)}</small></h2>
<h3>① 账号信息</h3><p class="listing">{listing_line_html(aid, nk)}</p>
<h3>② 账号首页截图</h3><div class="figs">{fig(prof, "抖音主页：昵称、抖音号、粉丝、获赞、作品数", "big") if prof else '<p class="muted">无可用截图。</p>'}</div>
<h3>③ 巨量星图截图</h3>{xt_block(aid, shots)}
<h3>④ 爬取的数据、红狐数据和结论</h3>
<div class="kpis">{kpis}</div>
<div class="charts">{drop_bar}{acc_bar}{fbars}{cbars}</div>
<h4>作品与互动</h4>{mblock}
<h4>粉丝列表抽样</h4>{fblock}
<h4>评论区互动者</h4>{cblock}
<h4>内容方向和质量</h4><p>{e(q['content'])}</p>
<h4>红狐数据（查询时间 {e(redfox_time())}）</h4>{rblock}
<h4>佐证截图</h4><div class="figs">{''.join(figs[1:] if prof else figs) or '<p class="muted">无可用截图。</p>'}</div>
<div class="verdict"><p><b>结论：</b>{e(q['summary'])}</p><p><b>评级：</b><span class="g {GCLS[g]}">{g}</span>　<b>购买建议：</b>{e(ADVICE[g])}</p>
<p><b>主要风险：</b></p><ul>{rk}</ul>
<div class="basis"><div class="bt">评级依据　<span>{e(why)}</span></div><table><tr><th>指标</th><th>实际值</th><th>门槛</th><th>结果</th></tr>{btbl}</table></div></div>
</section>""")

# ---------- cross validation ----------
cross = []
diffs = []
for aid in ORDER:
    d = derive(aid)
    rf = (RF.get("accounts") or {}).get(aid)
    xi = xt_info(aid)
    nk = nick(aid) if d else "（未能定位）"
    dyf = f"{d['fans']:,}" if d else "—"
    rff = f"{rf.get('followerCount'):,}（{(rf.get('crawlTime') or '')[:16]}）" if rf and rf.get('followerCount') else "未收录"
    xtf = f"{int(xi['a0']['follower']):,}" if xi and xi["found"] else ("未入驻" if xi else "—")
    if d and rf and rf.get("followerCount"):
        diffs.append((abs(rf["followerCount"] - d["fans"]) / max(d["fans"], 1) * 100, nk, (rf.get("crawlTime") or "")[:7]))
    if d and xi and xi["found"]:
        diffs.append((abs(int(xi["a0"]["follower"]) - d["fans"]) / max(d["fans"], 1) * 100, nk, ""))
    reg = []
    if xi and xi["found"]:
        D = dist(xi["api"])
        if D.get("省份分布"):
            reg.append("星图省份：" + "、".join(f"{k}{p_:.0f}%" for k, p_, _ in D["省份分布"]["items"][:3]))
    if rf and rf.get("ipLocation"): reg.append(f"红狐账号 IP：{rf['ipLocation']}")
    if d and d["c"] and d["c"].get("ip_top"): reg.append("评论 IP：" + "、".join(k for k, _ in d["c"]["ip_top"][:3]))
    if d and not d["blocked"]: reg.append("粉丝主页 IP：" + "、".join(k for k, _ in (d["f"].get("ip") or [])[:3] if k != "未显示"))
    sex = "—"
    if xi and xi["found"]:
        D = dist(xi["api"]); sex = "星图：" + ((D.get("性别分布") or {}).get("desc") or "")
    lst = listing(aid)
    cross.append(f"<tr><td>{e(nk)}<br><small>{e(aid)}</small></td><td>{dyf}</td><td>{rff}</td><td>{xtf}</td><td><small>{e('；'.join(reg) or '—')}</small></td><td>{e(lst[2] if lst else '—')}</td><td>{e(sex)}</td></tr>")
cross_notes = list(NOTES.get("cross") or [])
if not cross_notes and diffs:
    mx = max(diffs)
    cross_notes.append(f"三方粉丝数最大差异 {mx[0]:.1f}%（{mx[1]}）；红狐数据有抓取时间，较旧的数据仅作参考。")

# ---------- standards ----------
STD_ROWS = std_rows(DATE)
std_tbl = "".join(f"<tr><td><b>{a}</b></td><td><small>{b}</small></td><td>{c1}</td><td>{c2}</td><td>{c3}</td><td>{c4}</td><td><small>{s}</small></td></tr>" for a, b, c1, c2, c3, c4, s in STD_ROWS)
tier_tbl = "".join(f"<tr><td>{n}</td><td>{l[0]}%</td><td>{l[1]}%</td><td>{l[2]}%</td><td>{l[2]*0.1:.2f}%</td></tr>" for n, _, l in TIERS)

std_figs = "".join(fig(f"standards/{n}", c) for n, c in [("std-redfox-tiers.jpg", "红狐分层互动率基准（GitHub 公开技能文档）"), ("std-chanmama-likerate.jpg", "蝉妈妈：健康点赞率 0.5%~5%"), ("std-xingtu-index.jpg", "星图指数口径说明")] if os.path.exists(os.path.join(OUT, "standards", n)))

N = len(ORDER)
cnt = {g: sum(1 for v in grades.values() if v == g) for g in "ABCD—"}
xt_found = [a for a in ORDER if (xt_info(a) or {}).get("found")]
title = BATCH.text("title", n=N)
present = [g for g in "ABCD—" if cnt[g]]
missing = [g for g in "AB" if not cnt[g]]
headline = NOTES.get("headline") or (f"{N} 个号里没有 {'、'.join(missing)} 级。" if missing else f"{N} 个号：" + "，".join(f"{g} 级 {cnt[g]} 个" for g in present) + "。")
gnotes = dict(GRADE_NOTES)
gnotes.update(NOTES.get("grade_notes") or {})
verdict_li = "".join(f"<li><b>{g} 级 {cnt[g]} 个</b>：{e(gnotes[g])}</li>" for g in present)
xt_line = (f"巨量星图里有 {len(xt_found)} 个号入驻（{'、'.join(nick(a) for a in xt_found)}）。" if xt_found else "巨量星图里没有号入驻。") + (NOTES.get("xingtu") or "")
extra_verdict = "".join(f"<p>{e(x)}</p>" for x in NOTES.get("verdict") or [])
collect = f"数据采集：{e(BATCH.collect_time or DATE)}（{e(BATCH.data_sources)}）　"
method_extra = f"<li><b>第三方数据平台</b>：{e(NOTES['third_party'])}</li>" if NOTES.get("third_party") else ""
cross_li = "".join(f"<li>{e(x)}</li>" for x in cross_notes)

HTML = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<style>
body{{font-family:"PingFang SC","Microsoft YaHei",sans-serif;color:#1d2433;margin:0;background:#f4f5f7;line-height:1.6;font-size:14px}}
main{{max-width:1180px;margin:0 auto;padding:24px 28px;background:#fff}}
h1{{font-size:26px;margin:8px 0}} h2{{font-size:20px;border-bottom:2px solid #1d2433;padding-bottom:6px;margin-top:8px}} h3{{font-size:16px;margin:18px 0 6px;color:#2a3b5c}} h4{{font-size:14px;margin:12px 0 4px}}
small{{color:#5b6475}} .muted{{color:#6b7280}}
table{{border-collapse:collapse;width:100%;margin:6px 0 10px;font-size:13px}} th,td{{border:1px solid #d9dde4;padding:5px 7px;vertical-align:top;text-align:left}} th{{background:#f0f2f6;font-weight:600}}
table.kv th{{width:230px}}
.sum td{{font-size:12.5px}}
.g{{font-weight:800;text-align:center;display:inline-block;min-width:26px;border-radius:4px;padding:0 6px;color:#fff}}
td.g{{display:table-cell;font-size:18px}}
.ga{{background:#1f8a4c}} .gb{{background:#3d7bd9}} .gc{{background:#d98b1f}} .gd{{background:#c43d3d}} .gn{{background:#7b8190}}
.verdict{{background:#f8f9fb;border:1px solid #d9dde4;border-left:5px solid #2a3b5c;padding:10px 14px;margin:10px 0}}
.basis{{font-size:12px;margin:6px 0}} .basis .bt{{font-weight:700;color:#2a3b5c}} .basis .bt span{{font-weight:400;color:#5b6475}} .basis table{{font-size:12px}}
td.ok{{color:#1f8a4c}} td.bad{{color:#c43d3d}} td.mid{{color:#a86a10}}
.figs{{display:flex;flex-wrap:wrap;gap:10px}} figure{{margin:0;flex:1 1 360px;max-width:560px;break-inside:avoid;page-break-inside:avoid;border:1px solid #e3e6eb;padding:6px;background:#fff}} figure.half{{max-width:560px}}
figure img{{width:100%;display:block}} figcaption{{font-size:12px;color:#5b6475;margin-top:4px}}
.charts{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px;margin:8px 0}} .chart{{border:1px solid #e3e6eb;padding:6px 8px;break-inside:avoid}} .chart h5{{margin:0 0 4px;font-size:13px}} .chart h5 small{{display:block;font-weight:400}}
.bar{{display:flex;align-items:center;font-size:12px;gap:6px}} .bk{{width:70px;white-space:nowrap;overflow:hidden}} .bt{{flex:1;background:#eef0f4;height:9px;border-radius:3px}} .bt i{{display:block;height:9px;background:#3d7bd9;border-radius:3px}} .bv{{width:44px;text-align:right}}
.xt{{border:1px dashed #b7c3d8;padding:8px 12px;margin:8px 0;background:#fbfcff}}
.listing{{color:#5b6475;margin:2px 0}}
section.acct{{break-before:page;page-break-before:always;padding-top:6px}}
.toc a{{margin-right:12px;white-space:nowrap}}
body{{line-height:1.7;font-size:15px}} main{{max-width:960px;padding:32px 36px}} p,ul{{margin:10px 0 14px}} li{{margin:4px 0}}
h2{{white-space:nowrap;margin-top:28px}} h3{{margin:30px 0 12px;font-size:17px;color:#3370FF;border-left:4px solid #3370FF;padding-left:10px}} h4{{margin:22px 0 8px}}
.nw{{white-space:nowrap}} .sep{{color:#8f959e;margin:0 2px}} .listing{{font-size:15px;color:#1f2329;background:#f5f6f7;padding:10px 14px;border-radius:6px}}
td,th{{word-break:keep-all}} td small,th small{{white-space:nowrap}} .g{{white-space:nowrap}}
.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0 18px}} .kpi{{background:#f5f8ff;border:1px solid #dbe5ff;border-radius:8px;padding:10px 12px}} .kpi .kl{{font-size:12px;color:#646a73}} .kpi .kv{{font-size:20px;font-weight:700;color:#1f2329}}
.kpi.kg{{color:#fff;border:none}} .kpi.kg .kl,.kpi.kg .kv{{color:#fff}}
figure.big{{flex:1 1 100%;max-width:100%}} .figs{{gap:16px;margin:10px 0 16px}} .chart.wide{{padding:10px 12px}} .bk{{width:110px}} .bt i{{background:#3370FF}}
.charts{{grid-template-columns:repeat(2,1fr);gap:14px}} .verdict{{margin:22px 0;padding:14px 18px;border-left-color:#3370FF}}
@media (max-width:1100px){{.kpis{{grid-template-columns:repeat(2,1fr)}} .charts{{grid-template-columns:1fr}}}}
@media print{{body{{background:#fff}} main{{padding:0}} a{{color:inherit;text-decoration:none}} *{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body><main>
<h1>{e(title)}</h1>
<p class="muted">{collect}报告生成：{NOW}　用途：内部采购参考</p>
<div class="verdict"><p><b>一句话结论：</b>{e(headline)}</p><ul>{verdict_li}</ul><p>{e(xt_line)}</p>{extra_verdict}</div>
<p class="toc"><b>目录：</b><a href="#overview">总览</a><a href="#standard">评级标准</a><a href="#method">方法与数据源</a><a href="#cross">三方数据交叉对比</a>{''.join(f'<a href="#a-{e(a)}">{e(nick(a))}</a>' for a in ORDER)}</p>

<section id="overview"><h2>一、总览</h2>
<table class="sum"><tr><th>账号</th><th>挂牌</th><th>实际粉丝<br><small>vs 挂牌</small></th><th>历史最高<br><small>掉粉率</small></th><th>赞粉比</th><th>近 30 条互动率<br><small>均值 / 中位</small></th><th>点赞率<br><small>中位</small></th><th>疑似僵尸/空壳<br><small>粉丝抽样</small></th><th>画像</th><th>评级</th><th>购买建议</th><th>主要风险</th></tr>
{''.join(rows_summary)}</table>
<p class="muted">互动率 = (赞+评+藏+转) ÷ 当前粉丝；“偏低线”按粉丝量级取红狐分层基准。疑似僵尸/空壳为本次粉丝列表抽样结果（每号 {fans_sample_range()} 人）。画像优先采用星图官方数据，没有星图数据时列出评论者 IP 作参考。</p></section>

<section id="standard"><h2>二、评级标准</h2>
<p><b>定级规则：</b></p>
<ul>
<li><b>A</b>：下表所有指标都在 A 栏门槛内，即互动率达到良好线、点赞率中位 ≥0.5%、僵尸粉 ≤10%、掉粉 ≤5%、断更 ≤14 天、获赞 ≥80% 能对上现存作品、内容和画像与挂牌一致。</li>
<li><b>B</b>：互动率 ≥ 偏低线，掉粉 ≤10%，断更 ≤90 天，僵尸粉 ≤15%，且未触发 D 条件。</li>
<li><b>C</b>：未触发 D，但出现以下任一项：互动率低于偏低线、断更超过 90 天、僵尸粉超过 15%、掉粉超过 10%。粉丝基本真实，只适合压价收作粉丝底座。</li>
<li><b>D</b>：满足任意 2 项 D 触发条件；或出现刷粉/刷赞痕迹（单项即为 D）。</li>
<li><b>—</b>：账号无法定位，不评级。</li></ul>
<table><tr><th>指标</th><th>计算方法</th><th>A</th><th>B</th><th>C</th><th>D 触发</th><th>出处</th></tr>{std_tbl}</table>
<h4>红狐分层互动率基准（行业参考）</h4>
<table><tr><th>粉丝量级</th><th>优秀</th><th>良好（A 门槛）</th><th>偏低线（B 门槛）</th><th>偏低线 10%（D 触发，本次自定）</th></tr>{tier_tbl}</table>
<p class="muted">红狐原文另有两条规则：粉丝 >5 万且互动率低于偏低线时触发“僵尸粉预警”；断更 >14 天触发预警。</p>
<div class="figs">{std_figs}</div></section>

<section id="method"><h2>三、方法与数据源</h2>
<ul>
<li><b>抖音网页版（只读）</b>：查看主页、作品、评论和粉丝列表。</li><li>作品尽量看全；评论看最近 3 条和获赞最高 2 条作品。</li><li>全程不关注、不点赞、不评论、不私信。</li>
<li><b>粉丝抽样</b>：每号抽 {fans_sample_range()} 个粉丝，覆盖最近关注、涨粉高峰期和几个历史时间点。</li><li>另看 10~12 个粉丝主页的性别、年龄、IP 属地。</li><li>同一时段集中涌入、又被平台过滤掉的粉丝，视为机器粉。</li>
<li><b>红狐数据</b>：粉丝数、IP 属地、相似账号、历史收录作品数（用来看删了多少作品）。红狐不提供粉丝画像。</li>
<li><b>巨量星图</b>：按抖音号逐个搜索并截图，只读。</li><li>已入驻的号查看粉丝画像、传播表现、粉丝变化、报价和信用分。</li>
{method_extra}
</ul>
<p class="muted">参考：新榜指数 NRI 口径 <a href="{SRC_NEWRANK}" target="_blank">来源</a>；账号估值影响因素 <a href="{SRC_ZHB}" target="_blank">来源</a>。</p></section>

<section id="cross"><h2>四、三方数据交叉对比</h2>
<table><tr><th>账号</th><th>抖音实时粉丝</th><th>红狐粉丝（抓取时间）</th><th>星图粉丝</th><th>地域（星图 / 红狐 / 评论 / 粉丝主页）</th><th>挂牌画像</th><th>星图性别</th></tr>{''.join(cross)}</table>
{('<p>对比结论：</p><ul>' + cross_li + '</ul>') if cross_li else ''}</section>

<section id="detail"><h2>五、分账号详情</h2><p class="muted">每个账号单独一节，依次为账号信息、首页截图、星图截图、数据与结论（含评级依据）。</p></section>
{''.join(sections)}

</main></body></html>"""

merged = []
if not NO_MERGE:
    from merge_parts import merge
    HTML, merged = merge(HTML)
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "report-full.html"), "w", encoding="utf-8") as fh:
    fh.write(HTML)
print("OK report-full.html", len(HTML), "merged:", merged or "（未合并）", grades)
assert not re.search(r"ak_[0-9a-fA-F]{20,}", HTML), "报告里出现了疑似密钥"
