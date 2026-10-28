"""评论区分析：读 <WORK_DIR>/data_final/<id>/comments2.json，写 <WORK_DIR>/comments_analysis.json。

用法：python scripts/analyze/analyze_comments.py --config <batch.json> [抖音号 ...]
"""
import json, os, re, sys, datetime as dt
from collections import Counter

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
ROOT = str(B.W / "data_final")
DEFAULT_NICK = re.compile(r"^(用户\d{6,}|user\d+|\d{8,})$")
EMOJI_ONLY = re.compile(r"^(\[[^\]]{1,8}\]\s*)+$")
HAS_CJK = re.compile(r"[\u4e00-\u9fff]")
MIDAGE_NICK = re.compile(r"(奶奶|姥姥|外婆|外公|爷爷|退休|夕阳|花开富贵|富贵|平安|吉祥|如意|知足|随缘|淡然|静心|福|健康|岁月|人生|荷花|莲|兰|牡丹|玫瑰|梅|芳|霞|秀|英|珍|凤|阿姨|大姐|姐姐|大叔|雪莲|百合|菊|缘|笑口常开|心想事成|好运|顺其自然|阳光|大哥|大爷)")
MOM_TEXT = re.compile(r"(宝宝|孩子|我家|娃|女儿|儿子|闺女|小朋友|宝贝|当妈|带娃|幼儿园|我儿|我女)")
KID_TEXT = re.compile(r"(奥特曼|作业|老师|上学|小学|一年级|二年级|三年级|妈妈不让|偷偷|蛋仔|迷你世界|我的世界|喜羊羊|熊出没|佩奇|汪汪队)")
GENERIC = re.compile(r"^(好看|好|支持|赞|太棒了|真棒|厉害|666+|哈+|来了|打卡|好可爱|可爱|真好|不错|加油|真好看|好美|美|顶|沙发|第一)[!！。~～\s]*$")


def is_garbled(t):
    t = (t or "").strip()
    if not t:
        return True
    if EMOJI_ONLY.match(t):
        return False
    plain = re.sub(r"\[[^\]]{1,8}\]", "", t).strip()
    if not plain:
        return False
    if HAS_CJK.search(plain):
        # repeated same char / nonsense like "啊啊啊啊啊啊啊"
        return bool(re.fullmatch(r"(.)\1{5,}", plain))
    # no CJK: letters/digits/symbols noise like "jjjjhhhb", "ggvbbb", "。。。"
    return bool(re.fullmatch(r"[A-Za-z0-9\s\.\,\!\?\~\-\_\=\+\*\/\\@#%&。，！？、…·]{1,40}", plain)) and not re.fullmatch(r"\d{1,3}", plain)


def analyze(acc):
    p = os.path.join(ROOT, acc, "comments2.json")
    if not os.path.exists(p):
        return None
    d = json.load(open(p, encoding="utf-8"))
    allc = []
    vids = []
    for aid, v in d.items():
        cs = v["comments"]
        vids.append({"aweme_id": aid, "why": v["why"], "date": dt.datetime.fromtimestamp(v["create_time"]).strftime("%Y-%m-%d"), "desc": v["desc"], "cmt_total": (v.get("stats") or {}).get("comment_count"), "likes": (v.get("stats") or {}).get("digg_count"), "sampled": len(cs)})
        for c in cs:
            c["_vid"] = aid
            allc.append(c)
    n = len(allc)
    r = {"id": acc, "videos": vids, "n": n}
    if not n:
        return r
    pct = lambda k: round(k * 100.0 / n, 1)
    ips = Counter((c.get("ip") or "未显示") for c in allc)
    r["ip_top"] = ips.most_common(10)
    r["ip_distinct"] = len(ips)
    top_share = ips.most_common(1)[0][1] / n
    r["ip_top1_share"] = round(top_share * 100, 1)
    emo = sum(1 for c in allc if EMOJI_ONLY.match((c.get("text") or "").strip()))
    garb = sum(1 for c in allc if is_garbled(c.get("text")))
    dn = sum(1 for c in allc if DEFAULT_NICK.match(c.get("nick") or ""))
    da = sum(1 for c in allc if re.search(r"mosaic-legacy_379", c.get("avatar") or ""))
    gen = sum(1 for c in allc if GENERIC.match((c.get("text") or "").strip()))
    mid = sum(1 for c in allc if MIDAGE_NICK.search(c.get("nick") or ""))
    mom = sum(1 for c in allc if MOM_TEXT.search(c.get("text") or ""))
    kid = sum(1 for c in allc if KID_TEXT.search(c.get("text") or ""))
    texts = Counter((c.get("text") or "").strip() for c in allc if (c.get("text") or "").strip())
    dups = [(t, k) for t, k in texts.most_common(8) if k >= 2]
    users = Counter(c.get("uid") for c in allc)
    multi = sum(1 for u, k in users.items() if k >= 3)
    author_top = sum(1 for c in allc if c.get("is_author"))
    author_reply = sum(1 for c in allc for rp in (c.get("reply_preview") or []) if rp.get("is_author") or (rp.get("label") or "") == "作者")
    author_digg = sum(1 for c in allc if c.get("author_digged"))
    r.update({
        "emoji_only": f"{emo} ({pct(emo)}%)", "emoji_only_pct": pct(emo),
        "garbled": f"{garb} ({pct(garb)}%)", "garbled_pct": pct(garb),
        "default_nick": f"{dn} ({pct(dn)}%)", "default_avatar": f"{da} ({pct(da)}%)",
        "generic_praise": f"{gen} ({pct(gen)}%)", "midage_nick": f"{mid} ({pct(mid)}%)", "mom_text": f"{mom} ({pct(mom)}%)", "kid_text": f"{kid} ({pct(kid)}%)",
        "dup_texts": dups, "users_3plus_comments": multi, "unique_users": len(users),
        "author_comments": author_top, "author_replies_seen": author_reply, "author_digged": author_digg,
        "with_sticker_or_image": sum(1 for c in allc if c.get("sticker") or c.get("image")),
    })
    r["samples"] = [f'{c.get("nick")}（{c.get("ip") or "-"}）：{(c.get("text") or "")[:36]}  赞{c.get("digg")}' for c in sorted(allc, key=lambda c: -(c.get("digg") or 0))[:6]]
    r["samples_random"] = [f'{c.get("nick")}（{c.get("ip") or "-"}）：{(c.get("text") or "")[:36]}' for c in allc[::max(1, n // 8)][:8]]
    return r


if __name__ == "__main__":
    accs = sys.argv[1:] or [a for a in config.account_ids(B) if os.path.isdir(os.path.join(ROOT, a))]
    res = {}
    for a in accs:
        x = analyze(a)
        if x:
            res[a] = x
    json.dump(res, open(os.path.join(os.path.dirname(ROOT), "comments_analysis.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for a, x in res.items():
        print("==", a, "n", x["n"], [(v["why"], v["date"], v["sampled"], v["cmt_total"]) for v in x["videos"]])
        print({k: v for k, v in x.items() if k not in ("videos", "samples", "samples_random", "id", "n") and not k.endswith("_pct")})
        for s_ in x.get("samples", []) + ["--"] + x.get("samples_random", []):
            print("   ", s_)
