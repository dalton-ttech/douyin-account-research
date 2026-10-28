"""粉丝抽样分析：读 <WORK_DIR>/data_final/<id>/fans_sample.json，写 <WORK_DIR>/fans_analysis.json。

用法：python scripts/analyze/analyze_fans.py --config <batch.json> [抖音号 ...]
疑似僵尸/空壳：0 作品且粉丝 ≤5，并满足默认头像、默认昵称、点赞记录 ≤10 之一。
"""
import json, os, re, sys
from collections import Counter

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
ROOT = str(B.W / "data_final")
DEFAULT_NICK = re.compile(r"^(用户\d{6,}|user\d+|\d{8,})$")
MIDAGE = re.compile(r"(奶奶|姥姥|外婆|外公|爷爷|老伴|退休|夕阳|晚霞|花开富贵|富贵|平安|吉祥|如意|知足|随缘|淡然|静心|福|健康|快乐每一天|开心每一天|岁月|人生|红梅|荷花|莲|兰花|牡丹|玫瑰|梅|芳|霞|秀|英|珍|凤|阿姨|大姐|姐姐|大叔|老王|老李|老张|雪莲|百合|菊|往事|缘|笑口常开|心想事成|好运|顺其自然|一路|阳光|大哥|大爷|老人)")
MOM = re.compile(r"(宝妈|麻麻|妈妈|妈咪|宝宝|宝贝|宝儿|萌宝|二宝|大宝|小宝|.宝$|娃|带娃|育儿|母婴|孕)")
KID = re.compile(r"(小学|一年级|二年级|三年级|四年级|五年级|六年级|初一|初二|奥特曼|小学生|作业|小朋友|童年|蛋仔|迷你世界|我的世界|喜羊羊|熊出没|小猪佩奇|汪汪队|艾莎|公主)")
MARKET = re.compile(r"(微信|vx|VX|v信|薇|Q|q群|加我|合作|商务|代理|招商|批发|厂家|直供|货源|店|超市|工厂|有限公司|传媒|文化|科技|官方|旗舰|带货|团购|种草|好物|推广|互关|互粉|回关|必回)")


def is_default_avatar(f):
    return bool(re.search(r"mosaic-legacy_379", f.get("avatar") or ""))


def classify(f):
    works = f.get("works") or 0
    fans = f.get("fans") or 0
    following = f.get("following") or 0
    liked = f.get("liked") or 0
    nick = f.get("nick") or ""
    da = is_default_avatar(f)
    dn = bool(DEFAULT_NICK.match(nick))
    tags = []
    if da:
        tags.append("默认头像")
    if dn:
        tags.append("默认昵称")
    if works == 0:
        tags.append("0作品")
    if fans == 0:
        tags.append("0粉丝")
    if liked == 0:
        tags.append("0点赞记录")
    if following >= 3000:
        tags.append("关注≥3000")
    zombie = works == 0 and fans <= 5 and (da or dn or liked <= 10)
    low = (not zombie) and works == 0 and liked < 100
    market = bool(MARKET.search(nick + " " + (f.get("sig") or ""))) or (following >= 5000)
    return tags, zombie, low, market


def pct(n, d):
    return round(n * 100.0 / d, 1) if d else None


def summarize(fl):
    n = len(fl)
    if not n:
        return {"n": 0}
    c = Counter()
    for f in fl:
        tags, z, low, m = classify(f)
        for t in tags:
            c[t] += 1
        c["疑似僵尸/空壳"] += z
        c["低活跃(0作品且点赞<100)"] += low
        c["疑似营销/互粉"] += m
        c["无签名"] += not (f.get("sig") or "").strip()
        nick = f.get("nick") or ""
        c["昵称偏中老年"] += bool(MIDAGE.search(nick))
        c["昵称偏宝妈/亲子"] += bool(MOM.search(nick + " " + (f.get("sig") or "")))
        c["昵称/签名偏儿童"] += bool(KID.search(nick + " " + (f.get("sig") or "")))
    s = {"n": n}
    for k in ["疑似僵尸/空壳", "低活跃(0作品且点赞<100)", "默认头像", "默认昵称", "0作品", "0粉丝", "0点赞记录", "关注≥3000", "疑似营销/互粉", "无签名", "昵称偏中老年", "昵称偏宝妈/亲子", "昵称/签名偏儿童"]:
        s[k] = f"{c[k]} ({pct(c[k], n)}%)"
        s[k + "_pct"] = pct(c[k], n)
    med = lambda xs: sorted(xs)[len(xs) // 2] if xs else None
    s["关注数中位"] = med([f.get("following") or 0 for f in fl])
    s["点赞记录中位"] = med([f.get("liked") or 0 for f in fl])
    s["作品数中位"] = med([f.get("works") or 0 for f in fl])
    s["粉丝数中位"] = med([f.get("fans") or 0 for f in fl])
    return s


def analyze(acc):
    p = os.path.join(ROOT, acc, "fans_sample.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    fl = d["followers"]
    seen = set()
    uniq = []
    for f in fl:
        if f["uid"] in seen:
            continue
        seen.add(f["uid"])
        uniq.append(f)
    r = {"id": acc, "own": d.get("own"), "blocked": d.get("blocked"), "pages": d["pages"], "probes": d["probes"]}
    r["all"] = summarize(uniq)
    r["recent"] = summarize([f for f in uniq if f["tag"] == "recent"])
    r["peak"] = summarize([f for f in uniq if f["tag"] == "peak"])
    r["probe"] = summarize([f for f in uniq if f["tag"].startswith("probe")])
    prof = d.get("profiles") or []
    g = Counter({0: "未公开", 1: "男", 2: "女"}.get(x.get("gender"), "未公开") for x in prof)
    ages = [x.get("age") for x in prof if x.get("age") and x.get("age") > 0]
    ips = Counter((x.get("ip") or "未显示").replace("IP属地：", "") for x in prof)
    r["profiles_n"] = len(prof)
    r["gender"] = dict(g)
    r["ages"] = sorted(ages)
    r["ip"] = ips.most_common()
    r["profile_samples"] = [f'{x["tag"]}|{x["nick"]}|{ {0:"?",1:"男",2:"女"}.get(x.get("gender"),"?")}|{x.get("age")}|{(x.get("ip") or "").replace("IP属地：","")}|作{x["works"]} 粉{x["fans"]} 关{x["following"]} 赞过{x.get("liked")}|{x.get("sig","")[:20]}' for x in prof]
    zs = [f for f in uniq if classify(f)[1]]
    r["zombie_examples"] = [f'{f["nick"]} 作{f["works"]} 粉{f["fans"]} 关{f["following"]} 赞过{f["liked"]}' for f in zs[:8]]
    r["normal_examples"] = [f'{f["nick"]} 作{f["works"]} 粉{f["fans"]} 关{f["following"]} 赞过{f["liked"]} {(f.get("sig") or "")[:15]}' for f in uniq if not classify(f)[1]][:8]
    return r


if __name__ == "__main__":
    accs = sys.argv[1:] or [a for a in config.account_ids(B) if os.path.isdir(os.path.join(ROOT, a))]
    res = {}
    for a in accs:
        x = analyze(a)
        if x:
            res[a] = x
    json.dump(res, open(os.path.join(os.path.dirname(ROOT), "fans_analysis.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for a, x in res.items():
        print("==", a, x["own"], "blocked" if x["blocked"] else "")
        print(" probes:", [f'{p["at"]}:{p["n"]}人/{p["span_hours"]}h={p["per_day"]}/天 0作{p["zero_works"]} 默认头像{p["default_avatar"]}' for p in x["probes"]])
        print(" pages:", [f'{p["tag"]}{p["i"]}:{p["n"]} {p["min"]}~{p["max"]}' for p in x["pages"]])
        for k in ("all", "recent", "peak"):
            s = x[k]
            print(f" {k}: n={s['n']}", {kk: v for kk, v in s.items() if not kk.endswith("_pct") and kk != "n"})
        print(" gender", x["gender"], "ages", x["ages"], "ip", x["ip"])
        for l in x["profile_samples"]:
            print("   ", l)
        print(" zombies:", x["zombie_examples"])
