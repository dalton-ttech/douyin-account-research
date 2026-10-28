"""作品与互动指标：读 <WORK_DIR>/data_final/<id>/profile.json、posts.json，写 <WORK_DIR>/analysis_posts.json。

用法：python scripts/analyze/analyze_posts.py --config <batch.json> [抖音号 ...]
挂牌信息来自账号清单（listing/filtered.json）；断更天数按 batch.json 的 analysis_time（默认 date 当天 12:00）计算。
"""
import json, os, statistics as st, sys, datetime as dt
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
ROOT = str(B.W / "data_final")
NOW = B.analysis_time
LISTING = {r["id"]: (r["listing_fans"], r["category"], r["portrait"], r["status"]) for r in config.listing_rows(B, include_all=True)}
# 红狐账号诊断分层基准：互动率 优秀/良好/偏低线
TIERS = [(1_000_000, "S 超头部", 2.0, 1.2, 0.6), (100_000, "A 头部", 4.0, 2.5, 1.2), (10_000, "B 腰部", 6.0, 4.0, 2.0), (0, "C 尾部", 8.0, 5.0, 2.5)]


def tier(f):
    for th, name, ex, good, low in TIERS:
        if f >= th:
            return name, ex, good, low


def ts(t):
    return dt.datetime.fromtimestamp(t)


def med(xs):
    return st.median(xs) if xs else 0


def analyze(acc):
    d = os.path.join(ROOT, acc)
    u = json.load(open(os.path.join(d, "profile.json"), encoding="utf-8"))["user"]
    try:
        posts = json.load(open(os.path.join(d, "posts.json"), encoding="utf-8"))
    except Exception:
        posts = []
    fans = u["follower_count"]
    lst = LISTING.get(acc) or (None, "", "", "")
    tname, ex, good, low = tier(fans)
    r = {
        "id": acc, "nickname": u["nickname"], "uid": u["uid"], "fans": fans, "max_fans": u.get("max_follower_count"),
        "fans_drop": (u.get("max_follower_count") or fans) - fans,
        "fans_drop_pct": round(((u.get("max_follower_count") or fans) - fans) * 100 / (u.get("max_follower_count") or fans), 1) if (u.get("max_follower_count") or fans) else 0.0,
        "listing_fans": lst[0], "listing_diff_pct": round((fans - lst[0]) * 100 / lst[0], 1) if lst[0] else None, "listing": list(lst),
        "following": u["following_count"], "likes_total": u["total_favorited"], "works": u["aweme_count"],
        "like_fan_ratio": round(u["total_favorited"] / fans, 2) if fans else None,
        "tier": tname, "tier_lines": (ex, good, low), "gender": {1: "男", 2: "女"}.get(u.get("gender"), "未填"),
        "signature": (u.get("signature") or "")[:60], "verify": u.get("custom_verify") or u.get("enterprise_verify_reason") or "",
    }
    if r["max_fans"] is None:
        r["max_fans"] = fans
    uid = int(u["uid"])
    if uid > 10 ** 17:
        r["uid_created_est"] = ts(uid >> 32).strftime("%Y-%m-%d")
    s = lambda p, k: (p.get("stats") or {}).get(k, 0) or 0
    ps = sorted(posts, key=lambda p: p["create_time"], reverse=True)
    r["posts_fetched"] = len(ps)
    r["sum_fetched_likes"] = sum(s(p, "digg_count") for p in ps)
    r["likes_unaccounted"] = r["likes_total"] - r["sum_fetched_likes"] if len(ps) >= u["aweme_count"] else None
    if not ps:
        return r
    r["first_post"] = ts(ps[-1]["create_time"]).strftime("%Y-%m-%d")
    r["last_post"] = ts(ps[0]["create_time"]).strftime("%Y-%m-%d")
    r["days_since_last"] = (NOW - ts(ps[0]["create_time"])).days
    recent = [p for p in ps if not p.get("is_top")][:30]
    r["recent_n"] = len(recent)
    for k, name in (("digg_count", "like"), ("comment_count", "cmt"), ("collect_count", "collect"), ("share_count", "share")):
        xs = [s(p, k) for p in recent]
        r[f"r30_mean_{name}"] = round(st.mean(xs), 1) if xs else 0
        r[f"r30_med_{name}"] = med(xs)
    inter = [s(p, "digg_count") + s(p, "comment_count") + s(p, "collect_count") + s(p, "share_count") for p in recent]
    r["r30_mean_inter"] = round(st.mean(inter), 1)
    r["r30_med_inter"] = med(inter)
    r["inter_rate_mean_pct"] = round(st.mean(inter) / fans * 100, 3)
    r["inter_rate_med_pct"] = round(med(inter) / fans * 100, 3)
    r["like_rate_mean_pct"] = round(r["r30_mean_like"] / fans * 100, 3)
    r["like_rate_med_pct"] = round(r["r30_med_like"] / fans * 100, 3)
    r["vs_low_line"] = round(r["inter_rate_mean_pct"] / low, 3)
    r["zero_like_posts"] = sum(1 for p in recent if s(p, "digg_count") == 0)
    allL = sorted([s(p, "digg_count") for p in ps], reverse=True)
    tot = sum(allL) or 1
    r["top1_share"] = round(allL[0] / tot, 3)
    r["top3_share"] = round(sum(allL[:3]) / tot, 3)
    mean_all = st.mean(allL) if allL else 0
    r["max_over_mean"] = round(allL[0] / mean_all, 1) if mean_all else None
    r["hits_over_fan5pct"] = sum(1 for x in allL if x >= fans * 0.05)
    half = len(recent) // 2
    if half >= 3:
        newer = st.mean(inter[:half])
        older = st.mean(inter[half:])
        r["trend_newer_vs_older"] = round(newer / older, 2) if older else None
    r["top_posts"] = [
        {"aweme_id": p["aweme_id"], "t": ts(p["create_time"]).strftime("%Y-%m-%d"), "likes": s(p, "digg_count"), "cmt": s(p, "comment_count"), "collect": s(p, "collect_count"), "share": s(p, "share_count"), "desc": (p.get("desc") or "")[:40]}
        for p in sorted(ps, key=lambda p: -s(p, "digg_count"))[:3]
    ]
    r["recent5"] = [
        {"aweme_id": p["aweme_id"], "t": ts(p["create_time"]).strftime("%Y-%m-%d"), "likes": s(p, "digg_count"), "cmt": s(p, "comment_count"), "collect": s(p, "collect_count"), "share": s(p, "share_count"), "desc": (p.get("desc") or "")[:40]}
        for p in recent[:5]
    ]
    bm, cm = Counter(), Counter()
    for p in ps:
        m = ts(p["create_time"]).strftime("%Y-%m")
        bm[m] += s(p, "digg_count")
        cm[m] += 1
    r["by_month"] = {m: [cm[m], bm[m]] for m in sorted(bm)}
    r["top_tags"] = Counter(t for p in ps for t in p.get("tags", [])).most_common(8)
    r["video_tags"] = Counter(t for p in ps for t in p.get("video_tag", []) if t).most_common(6)
    r["image_posts"] = sum(1 for p in ps if p.get("images"))
    return r


if __name__ == "__main__":
    accs = sys.argv[1:] or [a for a in config.account_ids(B) if os.path.isdir(os.path.join(ROOT, a))]
    res = {}
    for a in accs:
        if os.path.exists(os.path.join(ROOT, a, "profile.json")):
            res[a] = analyze(a)
    json.dump(res, open(os.path.join(os.path.dirname(ROOT), "analysis_posts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for a, r in res.items():
        print(a, r["nickname"], "粉", r["fans"], "挂牌差%", r["listing_diff_pct"], "掉粉", r["fans_drop"], f'({r["fans_drop_pct"]}%)', "赞粉比", r["like_fan_ratio"], r["tier"],
              "作品", r["works"], "抓", r["posts_fetched"], "末更", r.get("last_post"), r.get("days_since_last"),
              "近30均互动率%", r.get("inter_rate_mean_pct"), "中位%", r.get("inter_rate_med_pct"), "点赞率均%", r.get("like_rate_mean_pct"), "中位%", r.get("like_rate_med_pct"),
              "/偏低线", r.get("vs_low_line"), "top3", r.get("top3_share"), "max/mean", r.get("max_over_mean"), "趋势", r.get("trend_newer_vs_older"), "未计入赞", r.get("likes_unaccounted"),
              "创建", r.get("uid_created_est") or "无法推算")
