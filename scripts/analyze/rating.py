"""指标派生与评级：TIERS（红狐分层基准）、derive()、rate()、ADVICE、STD_ROWS。

阈值和行业出处与第一批报告完全一致；改阈值要同时改这里和报告“评级标准”一节（STD_ROWS 由本文件生成，会自动同步）。
本模块只做计算，不读文件；数据由 report/report_data.py 传入。
"""

# 红狐账号诊断分层基准：(名称, 粉丝下限, (优秀, 良好, 偏低线))，互动率单位 %
TIERS = [("S 头部（≥100 万粉）", 1_000_000, (2.0, 1.2, 0.6)), ("A 头部（10~100 万粉）", 100_000, (4.0, 2.5, 1.2)), ("B 腰部（1~10 万粉）", 10_000, (6.0, 4.0, 2.0)), ("C 尾部（<1 万粉）", 0, (8.0, 5.0, 2.5))]


def tier_of(fans):
    for name, lo, lines in TIERS:
        if fans >= lo:
            return name, lines
    return TIERS[-1][0], TIERS[-1][2]


SRC_REDFOX = "https://github.com/redfox-data/redfox-community/blob/main/skills/douyin-account-diagnosis/SKILL.md"
SRC_CHANMAMA = "https://ai.chanmama.com/article/416"
SRC_ZOMBIE = "https://news.huochengrm.cn/qzgl/40714.html"
SRC_XINGTU = "https://www.shuaishou.com/ask/47649.html"
SRC_NEWRANK = "https://xd.newrank.cn/help/p/E48B9256DC20862B111DC72A06D0417F"
SRC_ZHB = "https://www.zhanghaobang.cn/account/trade-risk/account-valuation"

ADVICE = {
    "A": "可以购买，按挂牌价议价。",
    "B": "可以考虑，先让卖家补发 1~2 条新作品验证推流，再成交。",
    "C": "不建议按挂牌价购买；如只需要粉丝底座，可大幅压价，并要求先补发作品验证推流。",
    "D": "不建议购买。",
    "—": "暂不评估；先让卖家提供主页链接或后台截图（含抖音号、粉丝数、作品列表）再核实。",
}
GCLS = {"A": "ga", "B": "gb", "C": "gc", "D": "gd", "—": "gn"}

# 首页“一句话结论”里每个等级的通用说明，批次可在 qual.json 的 notes.grade_notes 里覆盖
GRADE_NOTES = {
    "A": "各项指标都在 A 栏门槛内，可以按挂牌价议价。",
    "B": "基本达标，先让卖家补发作品验证推流再成交。",
    "C": "粉丝基本真实，但互动低或长期断更，只适合压价收作粉丝底座。",
    "D": "有删作品洗号、大量掉粉、刷粉刷赞或主体不符，不建议购买。",
    "—": "账号无法定位，暂不评估。",
}


def derive(p, f, c, q):
    """p：analysis_posts 的一项；f：fans_analysis 的一项；c：comments_analysis 的一项；q：qual.json 里该号的定性判断。"""
    f = f or {}
    c = c or {}
    if not p:
        return None
    fans = p["fans"]
    tname, (good_ex, good, low) = tier_of(fans)
    inter = p.get("inter_rate_mean_pct")
    inter_med = p.get("inter_rate_med_pct")
    like_med = p.get("like_rate_med_pct")
    drop = p.get("fans_drop_pct")
    days = p.get("days_since_last")
    works = p.get("works") or 0
    fetched = p.get("posts_fetched") or 0
    likes_total = p.get("likes_total") or 0
    sumf = p.get("sum_fetched_likes") or 0
    full = works == 0 or fetched >= works * 0.95
    acc = (sumf / likes_total * 100) if likes_total and full else None
    blocked = (f.get("all") or {}).get("n", 0) == 0
    zomb = None if blocked else f["all"].get("疑似僵尸/空壳_pct")
    zero = None if blocked else f["all"].get("0作品_pct")
    return dict(p=p, f=f, c=c, q=q, fans=fans, tname=tname, good=good, low=low, excellent=good_ex, inter=inter, inter_med=inter_med,
                like_med=like_med, drop=drop, days=days, works=works, fetched=fetched, acc=acc, full=full, blocked=blocked, zomb=zomb, zero=zero)


def rate(d):
    """Return (grade, basis rows, d_triggers)."""
    rows = []
    trig = []
    q = d["q"]
    inter, good, low = d["inter"], d["good"], d["low"]
    # 1 interaction
    if d["works"] == 0 or inter is None:
        rows.append(("近 30 条平均互动率", "无作品，无法计算", f"偏低线 {low}%（{d['tname']}）", "✗ 无作品"))
    else:
        if inter >= good: res = "✓ 达到良好线（A 档）"
        elif inter >= low: res = "✓ 达到偏低线（B 档）"
        elif inter >= low * 0.1: res = "✗ 低于偏低线（C 档）"
        else: res = "✗ 低于偏低线的 10%（D 触发）"; trig.append("互动率低于偏低线 10%")
        rows.append(("近 30 条平均互动率", f"{inter:.3f}%（中位数 {d['inter_med']:.3f}%）", f"良好线 {good}% / 偏低线 {low}% / D 触发 <{low*0.1:.2f}%（{d['tname']}）", res))
    # 2 like rate
    if d["like_med"] is not None:
        rows.append(("近 30 条单条点赞率（中位数）", f"{d['like_med']:.3f}%", "健康区间 0.5%~5%", "✓ 在健康区间" if 0.5 <= d["like_med"] <= 5 else ("✗ 低于 0.5%" if d["like_med"] < 0.5 else "△ 高于 5%")))
    # 3 zombie
    if d["blocked"]:
        rows.append(("粉丝抽样：疑似僵尸/空壳占比", "粉丝列表隐私不可见，无法抽样", "A ≤10% / B、C ≤15% / D >20%", "— 无法核验（计为风险项）"))
    else:
        z = d["zomb"]
        res = "✓ ≤10%" if z <= 10 else ("△ 10%~15%" if z <= 15 else ("✗ 15%~20%" if z <= 20 else "✗ >20%（D 触发）"))
        if z > 20: trig.append("僵尸粉 >20%")
        rows.append(("粉丝抽样：疑似僵尸/空壳占比", f"{z:.1f}%（0 作品 {d['zero']:.1f}%，n={d['f']['all']['n']}）", "A ≤10% / B、C ≤15% / D >20%；0 作品 >30% 需警惕", res))
    # 4 drop
    dr = d["drop"]
    res = "✓ ≤5%" if dr <= 5 else ("△ 5%~10%" if dr <= 10 else "✗ >10%（D 触发）")
    if dr > 10: trig.append("掉粉 >10%")
    rows.append(("掉粉率（历史最高→当前）", f"{dr:.1f}%（{d['p']['max_fans']:,} → {d['fans']:,}）", "A ≤5% / B ≤10% / D >10%", res))
    # 5 days
    if d["days"] is None:
        rows.append(("断更天数", "无作品", "A ≤14 / B ≤90 / C >90 / D >365", "✗ 无作品"))
    else:
        dd = d["days"]
        res = "✓ ≤14 天" if dd <= 14 else ("△ 15~90 天" if dd <= 90 else ("✗ >90 天（最高 C）" if dd <= 365 else "✗ >365 天（D 触发）"))
        if dd > 365: trig.append("断更 >365 天")
        rows.append(("断更天数", f"{dd} 天（最后一条 {d['p']['last_post']}）", "A ≤14 / B ≤90 / C >90 / D >365", res))
    # 6 likes accounted
    if d["works"] == 0:
        trig.append("作品清空")
        rows.append(("获赞能否对上现存作品", f"作品 0，获赞 {d['p']['likes_total']:,} 全部来自已删作品", "≥80% 对得上 / <50% D 触发", "✗ 作品清空（D 触发）"))
    elif d["acc"] is None:
        rows.append(("获赞能否对上现存作品", f"作品 {d['works']} 条只抓到 {d['fetched']} 条，不判定", "≥80% 对得上 / <50% D 触发", "— 不判定"))
    else:
        a = d["acc"]
        res = "✓ ≥80%" if a >= 80 else ("△ 50%~80%" if a >= 50 else "✗ <50%（D 触发）")
        if a < 50: trig.append("获赞对不上现存作品")
        rows.append(("获赞能否对上现存作品", f"{a:.1f}%（现存 {d['fetched']} 条合计 {d['p']['sum_fetched_likes']:,} / 总获赞 {d['p']['likes_total']:,}）", "≥80% 对得上 / <50% D 触发", res))
    # 7 content
    if q["content_ok"] is False: trig.append("内容/主体与挂牌不符")
    rows.append(("内容与挂牌类目是否一致", q["content"], "一致；明显不符为 D 触发", "✓ 一致" if q["content_ok"] else ("✗ 不符（D 触发）" if q["content_ok"] is False else "— 未核实")))
    # 8 portrait
    rows.append(("画像与挂牌是否相符", q["portrait"], "星图官方画像与挂牌性别/年龄相符", "✓ 相符" if q["portrait_ok"] else "— 无官方画像，未核实"))
    # 9 brush
    if q["brush"]:
        trig.append("刷粉/刷赞痕迹")
        rows.append(("刷粉/刷赞痕迹", q["brush"], "出现即 D", "✗ 有（D 触发）"))
    else:
        rows.append(("刷粉/刷赞痕迹", "抽样未发现集中涌入的机器粉批次", "出现即 D", "✓ 未发现"))
    # 10 listing diff, hit dependency (risk flags)
    ld = d["p"].get("listing_diff_pct")
    rows.append(("挂牌粉丝与实际差异", f"{ld:+.1f}%（挂牌 {d['p']['listing_fans']:,} / 实际 {d['fans']:,}）" if ld is not None else "—", "±5% 内视为相符（风险提示，不单独定级）", "✓ 相符" if ld is not None and abs(ld) <= 5 else "△ 不符"))
    mom = d["p"].get("max_over_mean")
    if mom is not None:
        rows.append(("爆款依赖（最大爆款 / 均值）", f"{mom:.1f} 倍", ">10 倍为单条依赖（风险提示，不单独定级）", "△ 依赖爆款" if mom > 10 else "✓ 正常"))
    # grade
    if "刷粉/刷赞痕迹" in trig or len(trig) >= 2:
        g = "D"
    else:
        ok_inter_b = inter is not None and inter >= low
        stale = d["days"] is None or d["days"] > 90
        zbad = (d["zomb"] or 0) > 15
        if not ok_inter_b or stale or zbad or d["drop"] > 10:
            g = "C"
        else:
            a_ok = inter >= good and (d["like_med"] or 0) >= 0.5 and (d["zomb"] is not None and d["zomb"] <= 10) and d["drop"] <= 5 and d["days"] <= 14 and (d["acc"] or 0) >= 80 and d["q"]["content_ok"] and d["q"]["portrait_ok"]
            g = "A" if a_ok else "B"
    return g, rows, trig


def why_full(g, d, trig):
    """完整版报告“评级依据”标题后的一句说明。"""
    if g == "D":
        return "D 触发条件：" + "、".join(trig) + ("（存在刷量痕迹，单项即定为 D）" if "刷粉/刷赞痕迹" in trig else f"（共 {len(trig)} 项，≥2 项即定为 D）")
    if g == "C":
        return "未触发 2 项 D 条件，但" + "、".join(x for x in [
            "互动率低于偏低线" if d["inter"] is None or d["inter"] < d["low"] else "",
            "断更超过 90 天" if d["days"] is None or d["days"] > 90 else "",
            "僵尸粉超过 15%" if (d["zomb"] or 0) > 15 else "",
            "掉粉超过 10%" if d["drop"] > 10 else ""] if x) + "，最高只能定为 C" + (f"；已触发 1 项 D 条件：{trig[0]}" if trig else "")
    if g == "B":
        return "未触发 D 条件，互动率达到偏低线、断更不超过 90 天、僵尸粉和掉粉都在 B 栏门槛内，但未满足 A 级全部条件"
    if g == "A":
        return "所有指标都在 A 栏门槛内"
    return "账号无法定位，不评级"


def std_rows(date):
    """报告“二、评级标准”的门槛表。date 是数据截止日（YYYY-MM-DD）。"""
    return [
        ("近 30 条平均互动率", "(赞+评+藏+转)÷粉丝，取最近 30 条作品均值（同时给出中位数）", "≥良好线", "≥偏低线", "<偏低线", "<偏低线的 10%", f'行业参考：红狐分层基准（四档，见下表）<a href="{SRC_REDFOX}" target="_blank">来源</a>；D 触发线为本次自定'),
        ("单条点赞率", "点赞÷粉丝，最近 30 条中位数", "≥0.5%", "参考", "参考", "—", f'行业参考：蝉妈妈“健康点赞率 0.5%~5%”<a href="{SRC_CHANMAMA}" target="_blank">来源</a>'),
        ("疑似僵尸/空壳粉占比", "粉丝抽样中 0 作品且粉丝≤5，并满足默认头像/默认昵称/点赞记录≤10 之一", "≤10%", "≤15%", "≤15%", ">20%", f'方法参考：抽查粉丝 0 作品比例 >30% 需警惕<a href="{SRC_ZOMBIE}" target="_blank">来源</a>；分档阈值为本次自定'),
        ("掉粉率", "(历史最高粉丝−当前粉丝)÷历史最高", "≤5%", "≤10%", "—", ">10%", "本次自定（参考账号估值中“粉丝稳定性”因素" + f' <a href="{SRC_ZHB}" target="_blank">来源</a>）'),
        ("断更天数", f"距最后一条作品的天数（截至 {date}）", "≤14 天", "≤90 天", ">90 天", ">365 天", f'行业参考：断更 >14 天预警<a href="{SRC_REDFOX}" target="_blank">来源</a>；90/365 天分档为本次自定'),
        ("获赞能否对上现存作品", "现存作品获赞合计÷账号总获赞（作品看全时才判定）", "≥80%", "≥50%", "≥50%", "<50% 或作品清空", "本次自定（用于识别删作品、洗号）"),
        ("内容与挂牌类目一致", "人工核对主页、作品与挂牌类目、认证主体", "一致", "一致", "一致", "明显不符", "本次自定"),
        ("画像与挂牌相符", "星图官方粉丝画像（性别、年龄）对照挂牌描述；无星图时用评论/抽样做参考", "相符", "参考", "参考", "—", f'星图口径说明<a href="{SRC_XINGTU}" target="_blank">来源</a>；判定为本次自定'),
        ("刷粉/刷赞痕迹", "粉丝按关注时间翻页，出现分钟级集中涌入且被平台过滤（每页明显少于 20 人）；或点赞与评论严重失衡", "无", "无", "无", "出现即 D", "本次自定"),
        ("爆款依赖", "最大爆款获赞÷近 30 条均值", "风险提示", "风险提示", "风险提示", "—", f'行业参考：>10 倍为单条依赖<a href="{SRC_REDFOX}" target="_blank">来源</a>'),
        ("挂牌粉丝差异", "(实际−挂牌)÷挂牌", "风险提示", "风险提示", "风险提示", "—", "本次自定：±5% 内视为相符"),
    ]
