"""生成合成示例批次（不含任何真实账号数据），用于离线演示和回归测试两种报告模式。

用法：python scripts/tools/make_demo_batch.py [输出目录，默认 examples/demo-batch]
之后：python scripts/build_report.py --config examples/demo-batch/batch.json --mode both

生成 3 个示例号，覆盖几种典型情况：
  demo_a 示例账号A：互动达标、星图已入驻、红狐已收录          → 预期 B
  demo_b 示例账号B：互动极低且掉粉 >10%、粉丝列表隐私、星图只搜到相似号、红狐数据偏旧 → 预期 D
  demo_c 示例账号C：断更约 200 天、互动偏低、星图搜不到、红狐未收录 → 预期 C
截图全部是写着“示例截图”的占位图；主页截图按抖音网页版深色版式绘制，裁剪脚本可以正常识别。
随机数种子固定，每次生成结果相同。
"""
import json, math, random, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else REPO / "examples" / "demo-batch"
W, P = OUT / "work", OUT / "preview"
DATE = "2026-10-01"
CST = timezone(timedelta(hours=8))
NOW = datetime.fromisoformat(DATE + "T12:00:00+08:00")
R = random.Random(20261001)
FONTS = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf", "/System/Library/Fonts/PingFang.ttc",
         "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"]


def font(size):
    for f in FONTS:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def ts(dt):
    return int(dt.timestamp())


def wj(path, obj, indent=1):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=indent), encoding="utf-8")


ACCTS = [
    dict(id="demo_a", nick="示例账号A", letter="A", listing="8.6万粉丝", cat="亲子号", portrait="未认证62中间女粉", status="三无",
         fans=86_000, max_fans=89_500, works=48, gap_days=5, last_days=4, like_mu=1900, cmt=60, col=120, shr=40, hit=28_000,
         zombie=0.07, blocked=False, xt="found", rf="ok", created_days=900, color=(255, 140, 90)),
    dict(id="demo_b", nick="示例账号B", letter="B", listing="25万粉丝", cat="剧情号", portrait="未认证55中间女粉", status="三无",
         fans=230_000, max_fans=268_000, works=36, gap_days=9, last_days=140, like_mu=150, cmt=6, col=10, shr=4, hit=52_000,
         zombie=0.0, blocked=True, xt="near", rf="old", created_days=1400, color=(110, 150, 255)),
    dict(id="demo_c", nick="示例账号C", letter="C", listing="4.5万粉丝", cat="美食号", portrait="未认证70中间女粉", status="三无",
         fans=45_000, max_fans=47_800, works=64, gap_days=6, last_days=200, like_mu=330, cmt=14, col=30, shr=12, hit=9_000,
         zombie=0.18, blocked=False, xt="none", rf="none", created_days=1100, color=(90, 200, 150)),
]
TAGS = {"亲子号": ["亲子", "宝宝日常", "萌娃", "育儿"], "剧情号": ["剧情", "搞笑", "情感", "短剧"], "美食号": ["美食", "家常菜", "做饭", "探店"]}
PROVS = ["广东", "河南", "山东", "江苏", "四川", "浙江", "湖北", "河北", "湖南", "福建"]
CMTS = ["好可爱", "[比心][比心]", "学到了", "哈哈哈哈", "宝宝真乖", "支持一下", "[赞][赞][赞]", "已关注", "拍得真好", "这个我也想试试",
        "太真实了", "笑死我了", "[捂脸]", "求教程", "看饿了", "好温馨啊", "收藏了", "第一次刷到", "期待更新", "说得对"]


# ---------- 账号、作品 ----------
def make_posts(a):
    posts = []
    t_last = NOW - timedelta(days=a["last_days"])
    hit_k = R.randint(8, min(20, a["works"] - 2))
    for k in range(a["works"]):
        t = t_last - timedelta(days=k * a["gap_days"] + R.random() * 2, hours=R.randint(8, 22))
        f = math.exp(R.gauss(0, 0.45))
        likes = int(a["like_mu"] * f) if k != hit_k else a["hit"]
        posts.append({
            "aweme_id": str(7300000000000000000 + R.randint(10**14, 10**15)), "desc": f"示例作品第 {a['works'] - k} 条 #{R.choice(TAGS[a['cat']])}",
            "create_time": ts(t), "is_top": 1 if k == hit_k else 0, "aweme_type": 0, "duration": R.randint(12, 90) * 1000,
            "stats": {"digg_count": likes, "comment_count": max(0, int(a["cmt"] * f)), "collect_count": max(0, int(a["col"] * f)),
                      "share_count": max(0, int(a["shr"] * f)), "play_count": 0},
            "media_type": 4, "images": 0, "tags": R.sample(TAGS[a["cat"]], 2), "video_tag": [a["cat"].replace("号", "")], "author_uid": None,
        })
    return posts


def uid_for(a):
    created = ts(NOW - timedelta(days=a["created_days"]))
    return str((created << 32) + R.randint(1, 2**31))


# ---------- 粉丝抽样 ----------
DEF_AVATAR = "aweme-avatar/mosaic-legacy_3796936223"


def follower(a, tag, pg, k, zombie):
    uid = str(R.randint(10**15, 10**16))
    if zombie:
        return {"tag": tag, "pg": pg, "uid": uid, "sec": f"SEC_DEMO_{uid}", "nick": f"用户{R.randint(1000000, 9999999)}", "sig": "", "uniq": "",
                "works": 0, "fans": R.randint(0, 3), "following": R.randint(20, 400), "liked": R.randint(0, 8), "got": 0,
                "avatar": DEF_AVATAR, "verify": "", "ky": None, "secret": 0}
    return {"tag": tag, "pg": pg, "uid": uid, "sec": f"SEC_DEMO_{uid}", "nick": f"示例粉丝{R.randint(100, 999)}", "sig": R.choice(["", "热爱生活", "记录日常"]),
            "uniq": "", "works": R.randint(0, 80), "fans": R.randint(5, 600), "following": R.randint(30, 900), "liked": R.randint(50, 6000),
            "got": R.randint(0, 3000), "avatar": "aweme-avatar/demo", "verify": "", "ky": None, "secret": 0}


def cst(t):
    return datetime.fromtimestamp(t, CST).strftime("%Y-%m-%d %H:%M")


def fans_sample(a, uid, posts):
    out = {"id": a["id"], "uid": uid, "fetched_at": NOW.isoformat(), "pages": [], "probes": [], "followers": [], "flags": [],
           "own": {"fans": a["fans"], "max": a["max_fans"], "likes": None, "works": a["works"], "nick": a["nick"]}}
    if a["blocked"]:
        out.update(blocked=True, privacy=True, profiles=[])
        return out
    top = max(posts, key=lambda p: p["stats"]["digg_count"])
    peak_start = top["create_time"] + 86400
    for tag, t0, n in (("recent", ts(NOW), 6), ("peak", peak_start, 5)):
        mt = t0
        for i in range(n):
            span = R.randint(3, 30) * 3600 if tag == "recent" else R.randint(1, 6) * 3600
            fl = [follower(a, tag, i, k, R.random() < a["zombie"]) for k in range(20)]
            out["pages"].append({"tag": tag, "i": i, "n": 20, "min": cst(mt - span), "max": cst(mt), "total": a["fans"], "has_more": True})
            out["followers"] += fl
            mt -= span
    start = ts(NOW - timedelta(days=a["created_days"]))
    for k in range(1, 5):
        at = start + (ts(NOW) - start) * k // 5
        d = datetime.fromtimestamp(at, CST).strftime("%Y-%m-%d")
        fl = [follower(a, "probe:" + d, 0, j, R.random() < a["zombie"]) for j in range(20)]
        span_h = round(R.uniform(6, 60), 2)
        out["probes"].append({"at": d, "n": 20, "min": cst(at - int(span_h * 3600)), "max": cst(at), "span_hours": span_h,
                              "per_day": round(20 / span_h * 24), "zero_works": sum(1 for f in fl if not f["works"]),
                              "default_avatar": sum(1 for f in fl if f["avatar"] == DEF_AVATAR)})
        for f in fl:
            f["tag"] = "probe:" + d
        out["followers"] += fl
    out["profiles"] = []
    for tag in ("recent", "peak"):
        for f in [x for x in out["followers"] if x["tag"] == tag][:6]:
            out["profiles"].append({"tag": tag, "nick": f["nick"], "gender": R.choice([1, 2, 2, 2]), "age": R.choice([24, 29, 33, 37, 41, 46]),
                                    "ip": "IP属地：" + R.choice(PROVS[:6]), "province": "", "city": "", "country": "中国", "works": f["works"],
                                    "fans": f["fans"], "following": f["following"], "got": f["got"], "liked": f["liked"], "sig": f["sig"],
                                    "school": "", "uid": f["uid"], "sec": f["sec"]})
    out.update(blocked=False, privacy=False)
    return out


def comments(a, posts):
    s = lambda p, k: p["stats"][k]
    non_top = sorted([p for p in posts if not p["is_top"]], key=lambda p: -p["create_time"])
    picks = [(p, "recent") for p in non_top if s(p, "comment_count") > 0][:3]
    for p in sorted(posts, key=lambda p: -s(p, "digg_count")):
        if sum(1 for _, w in picks if w == "top") >= 2:
            break
        if all(p is not q for q, _ in picks) and s(p, "comment_count") > 0:
            picks.append((p, "top"))
    out = {}
    for p, why in picks:
        n = min(40, max(3, s(p, "comment_count")))
        lst = []
        for k in range(n):
            lst.append({"text": R.choice(CMTS), "digg": R.randint(0, 30), "reply": R.randint(0, 3), "ip": R.choice(PROVS), "t": p["create_time"] + R.randint(60, 86400 * 3),
                        "nick": R.choice([f"用户{R.randint(1000000, 9999999)}", f"示例用户{R.randint(10, 99)}", "爱生活的小王", "路过的网友"]),
                        "uid": str(R.randint(10**15, 10**16)), "sec": "SEC_DEMO", "avatar": "aweme-avatar/demo", "is_author": False,
                        "author_digged": R.random() < 0.1, "label": None, "sticker": False, "image": False, "reply_preview": []})
        out[p["aweme_id"]] = {"why": why, "create_time": p["create_time"], "desc": p["desc"][:50], "stats": p["stats"], "comments": lst}
    return out


# ---------- 星图、红狐 ----------
def dist(type_display, desc, items):
    return {"type_display": type_display, "description": desc, "distribution_list": [{"distribution_key": k, "distribution_value": v} for k, v in items]}


def xingtu(a, uid):
    aid_found = "7100000000000000001"
    if a["xt"] == "none":
        return {"id": a["id"], "t": NOW.isoformat(), "found": False, "search": {"total": 0, "authors": []}, "searchText": "找到 0 个达人（示例）"}
    near = a["xt"] == "near"
    author = {"id": aid_found if not near else "7100000000000000002", "nick_name": a["nick"] if not near else "示例相似号", "follower": str(a["fans"] if not near else 12_300),
              "core_user_id": uid if not near else "123", "fans_increment_within_30d": "1260", "link_star_index": "62.5", "link_spread_index": "58.1",
              "link_shopping_index": "41.3", "link_convert_index": "37.9", "expected_play_num": "21000", "tags_relation": json.dumps({"亲子": [], "生活": []}, ensure_ascii=False),
              "province": "广东", "city": "广州"}
    base = {"unique_id": a["id"] if not near else a["id"] + "8", "nick_name": author["nick_name"], "follower": int(author["follower"]), "core_user_id": author["core_user_id"]}
    rec = {"id": a["id"], "t": NOW.isoformat(), "found": not near, "match": None if near else "unique_id", "search": {"total": 1, "authors": [author]},
           "searchText": "找到 1 个达人（示例）", "aid": author["id"], "api": {"base": {"s": 200, "b": base}}}
    if near:
        return rec
    day0 = NOW - timedelta(days=30)
    daily = [{"date": (day0 + timedelta(days=i)).strftime("%Y-%m-%d"), "fans_cnt": a["fans"] - 1260 + i * 42} for i in range(31)]
    rec["api"].update({
        "fans_all": {"s": 200, "b": {"distributions": [
            dist("性别分布", "粉丝性别", [("female", 620), ("male", 380)]),
            dist("年龄分布", "粉丝年龄", [("18-23", 90), ("24-30", 210), ("31-40", 360), ("41-50", 240), ("50-", 100)]),
            dist("省份分布", "粉丝地域", [("广东", 160), ("河南", 90), ("山东", 80), ("江苏", 70), ("四川", 60), ("其他", 540)]),
            dist("城市等级分布", "粉丝城市等级", [("一线", 120), ("新一线", 190), ("二线", 200), ("三线", 230), ("四线及以下", 260)]),
            dist("八大人群分布", "八大人群", [("精致妈妈", 330), ("小镇中老年", 210), ("都市白领", 150), ("其他", 310)]),
        ]}},
        "spread_p90": {"s": 200, "b": {"play_mid": 18_500, "play_over_rate": {"value": 2350}, "interact_rate": {"value": 610},
                                        "item_rate": {"play_mid": {"overtake": 6400}}, "item_num": 17, "like_avg": 2050}},
        "daily_fans": {"s": 200, "b": {"daily": daily}},
        "marketing": {"s": 200, "b": {"price_info": [{"desc": "1-20s 视频", "price": 1800}, {"desc": "21-60s 视频", "price": 2600}]}},
        "contract": {"s": 200, "b": {"new_credit_score": 100}},
    })
    return rec


def redfox(a, posts):
    if a["rf"] == "none":
        return {"_not_found": True, "code": 3203, "msg": "未收录"}, {"code": 3203, "msg": "未收录", "total": None, "list": []}
    crawl = "2026-09-28 08:12:00" if a["rf"] == "ok" else "2026-05-12 21:40:00"
    fans = a["fans"] if a["rf"] == "ok" else a["max_fans"]
    acc = {"accountId": a["id"], "nickname": a["nick"], "followerCount": fans, "totalFavorited": sum(p["stats"]["digg_count"] for p in posts),
           "awemeCount": a["works"], "ipLocation": "广东", "gender": "女", "age": None, "province": "广东", "city": "广州", "crawlTime": crawl,
           "similarAccounts": [{"nickname": f"示例相似号{i}"} for i in range(1, 4)], "works": []}
    works = {"code": 2000, "msg": "成功", "total": a["works"] - 3, "list": []} if a["rf"] == "ok" else {"code": 3203, "msg": "未收录", "total": None, "list": []}
    return acc, works


# ---------- 图片 ----------
DARK, TXT, GREY, RED = (22, 24, 35), (235, 236, 240), (140, 144, 156), (254, 44, 85)


def profile_shot(path, a, posts, palette):
    im = Image.new("RGB", (1280, 860), DARK)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 176, 860], fill=(26, 28, 40))
    for i, t in enumerate(["推荐", "关注", "朋友", "我的"]):
        d.text((40, 120 + i * 48), t, fill=GREY, font=font(16))
    d.ellipse([190, 79, 302, 191], fill=a["color"])
    d.text((230, 112), a["letter"], fill=(255, 255, 255), font=font(40))
    d.text((330, 88), a["nick"], fill=TXT, font=font(28))
    wan = lambda n: f"{n / 10000:.1f}万" if n >= 10000 else str(n)
    d.text((330, 136), f"关注 {R.randint(5, 90)}   粉丝 {wan(a['fans'])}   获赞 {wan(sum(p['stats']['digg_count'] for p in posts))}", fill=TXT, font=font(16))
    d.text((330, 166), f"抖音号：{a['id']}   示例截图", fill=GREY, font=font(13))
    d.text((900, 110), "示例截图", fill=(70, 74, 90), font=font(56))
    d.text((190, 242), f"作品 {len(posts)}", fill=TXT, font=font(17))
    d.text((300, 242), "推荐", fill=GREY, font=font(17))
    d.text((370, 242), "喜欢", fill=GREY, font=font(17))
    d.rectangle([190, 270, 252, 272], fill=RED)
    for i, t in enumerate(["作品", "合集", "短剧"]):
        x = 190 + i * 70
        d.rounded_rectangle([x, 288, x + 56, 314], radius=6, fill=(40, 43, 58))
        d.text((x + 12, 292), t, fill=TXT, font=font(14))
    order = sorted(posts, key=lambda p: (-p["is_top"], -p["create_time"]))
    for row, top in enumerate((330, 600)):
        for i in range(6):
            k = row * 6 + i
            if k >= len(order):
                break
            x = round(190 + i * 179.2)
            c = palette[k % len(palette)]
            d.rectangle([x, top, x + 162, top + 216], fill=c)
            d.text((x + 36, top + 92), "示例截图", fill=(255, 255, 255), font=font(22))
            d.text((x + 8, top + 192), f"赞 {wan(order[k]['stats']['digg_count'])}", fill=(255, 255, 255), font=font(14))
            if top + 236 < 860:
                d.text((x, top + 222), order[k]["desc"][:9], fill=TXT, font=font(14))
    im.save(path, optimize=True)


def placeholder_shot(path, title, sub, dark=True, size=(1280, 860)):
    bg, fg, box = ((22, 24, 35), (235, 236, 240), (44, 47, 62)) if dark else ((245, 246, 248), (31, 35, 41), (225, 228, 233))
    im = Image.new("RGB", size, bg)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, size[0], 56], fill=box)
    d.text((24, 16), title, fill=fg, font=font(20))
    for i in range(6):
        d.rounded_rectangle([60, 110 + i * 110, size[0] - 60, 190 + i * 110], radius=10, fill=box)
    d.text((size[0] // 2 - 150, size[1] // 2 - 60), "示例截图", fill=fg, font=font(72))
    d.text((size[0] // 2 - 150, size[1] // 2 + 30), sub, fill=fg, font=font(22))
    im.save(path, optimize=True)


def square_jpg(path, color, text, size):
    im = Image.new("RGB", (size, size), color)
    d = ImageDraw.Draw(im)
    f = font(size // 4 if len(text) <= 2 else size // 7)
    w = d.textlength(text, font=f)
    d.text(((size - w) / 2, size / 2 - size / 8), text, fill=(255, 255, 255), font=f)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=82, optimize=True)


# ---------- 主流程 ----------
def main():
    for sub in ("data_final", "shots_clean", "shots_mine", "xingtu_data", "parts"):
        p = W / sub
        if p.exists():
            import shutil
            shutil.rmtree(p)
    rows, accounts, qual, manifest = [], {}, {}, {}
    rf_data = {"accounts": {}, "works": {}}
    calls = []
    for a in ACCTS:
        aid = a["id"]
        uid = uid_for(a)
        posts = make_posts(a)
        for p in posts:
            p["author_uid"] = uid
        likes_total = int(sum(p["stats"]["digg_count"] for p in posts) * (1.02 if aid != "demo_c" else 1.15))
        user = {"uid": uid, "sec_uid": f"SEC_DEMO_{aid}", "unique_id": aid, "nickname": a["nick"], "follower_count": a["fans"], "max_follower_count": a["max_fans"],
                "following_count": R.randint(5, 90), "total_favorited": likes_total, "aweme_count": a["works"], "favoriting_count": R.randint(0, 500),
                "gender": 2, "signature": "这是合成的示例账号，用于演示报告格式", "ip_location": "IP属地：广东", "custom_verify": "", "enterprise_verify_reason": ""}
        dd = W / "data_final" / aid
        wj(dd / "profile.json", {"status_code": 0, "user": user}, 0)
        wj(dd / "posts.json", posts)
        wj(dd / "comments2.json", comments(a, posts))
        wj(dd / "fans_sample.json", fans_sample(a, uid, posts))
        accounts[aid] = {"found": True, "nickname": a["nick"], "unique_id": aid, "uid": uid, "sec_uid": user["sec_uid"], "follower_count": a["fans"],
                         "total_favorited": likes_total, "aweme_count": a["works"]}
        rows.append({"id": aid, "line": f"抖音:{aid}---{a['nick']}---{a['listing']}---{a['cat']}-----{a['portrait']}---{a['status']}"})
        # 截图
        sd = W / "shots_clean" / aid
        sd.mkdir(parents=True, exist_ok=True)
        pal = [tuple(max(0, min(255, c + R.randint(-60, 40))) for c in a["color"]) for _ in range(12)]
        profile_shot(sd / "01-profile.png", a, posts, pal)
        placeholder_shot(sd / "02-fans.png", f"{a['nick']} · 粉丝列表", "粉丝列表不可见" if a["blocked"] else "粉丝列表（已打码）")
        top = max(posts, key=lambda p: p["stats"]["digg_count"])
        recent = sorted([p for p in posts if not p["is_top"] and p is not top], key=lambda p: -p["create_time"])[0]
        placeholder_shot(sd / f"03-top-{top['aweme_id']}.png", f"{a['nick']} · 点赞最高作品", "作品页与评论区（已打码）")
        placeholder_shot(sd / f"04-recent-{recent['aweme_id']}.png", f"{a['nick']} · 最近作品", "作品页与评论区（已打码）")
        wj(sd / "res.json", {"id": aid, "profileOk": True, "imagesLoaded": True, "02-fans": {"ok": True},
                             "03-top": {"aw": top["aweme_id"], "ok": True, "url": True, "hits": 12}, "04-recent": {"aw": recent["aweme_id"], "ok": True, "url": True, "hits": 9}})
        xd = W / "shots_mine" / "xingtu" / aid
        xd.mkdir(parents=True, exist_ok=True)
        placeholder_shot(xd / "01-search.png", "巨量星图 · 达人广场 · 昵称找人", "按抖音号搜索的结果页", dark=False)
        if a["xt"] == "found":
            placeholder_shot(xd / "02-home.png", "巨量星图 · 达人主页", "数据概览与报价栏", dark=False)
            placeholder_shot(xd / "04-tab-1.png", "巨量星图 · 连接用户", "粉丝画像", dark=False)
        wj(W / "xingtu_data" / f"{aid}.json", xingtu(a, uid), 0)
        acc, works = redfox(a, posts)
        rf_data["accounts"][aid] = acc
        rf_data["works"][aid] = works
        for k, ep in enumerate(("/story/api/dyUser/queryData", "/story/api/dy/data/listWorkByAccount")):
            calls.append({"time": f"{DATE}T11:{10 + len(calls):02d}:00", "endpoint": ep, "tag": f"demo-{aid}-{k}", "code": works["code"] if k else (2000 if a["rf"] != "none" else 3203), "cost": 0})
        # 总览素材
        od = P / "overview-assets" / aid
        square_jpg(od / "avatar.jpg", a["color"], a["letter"], 160)
        rep = sorted(posts, key=lambda p: -p["stats"]["digg_count"])
        latest = sorted([p for p in posts if not p["is_top"]], key=lambda p: -p["create_time"])[0]
        covers = []
        for i, (p, role) in enumerate(((rep[0], "点赞最高"), (latest if latest is not rep[0] else rep[1], "最近非置顶"))):
            square_jpg(od / f"cover{i + 1}.jpg", pal[i], "示例", 240)
            covers.append({"file": f"overview-assets/{aid}/cover{i + 1}.jpg", "likes": p["stats"]["digg_count"],
                           "date": datetime.fromtimestamp(p["create_time"], CST).strftime("%Y-%m-%d"), "desc": p["desc"][:20], "aweme_id": p["aweme_id"],
                           "role": role, "source": "示例占位图"})
        manifest[aid] = {"nickname": a["nick"], "gender": "女", "region": "广东", "verified": "无", "avatar": f"overview-assets/{aid}/avatar.jpg", "covers": covers}

    qual = {
        "demo_a": {"content": "亲子日常，与挂牌一致", "content_ok": True,
                   "portrait": "星图女粉 62%，与挂牌相符", "portrait_ok": True, "brush": None,
                   "risks": ["互动率达到偏低线，离良好线还有差距"],
                   "summary": "粉丝基本真实（抽样疑似僵尸约 7%），保持更新；互动率达到同量级偏低线以上。"},
        "demo_b": {"content": "剧情类短视频，与挂牌“剧情号”一致", "content_ok": True,
                   "portrait": "星图只搜到相似号，没有本号的官方画像；挂牌写“55 中间女粉”，无法核实", "portrait_ok": None, "brush": None,
                   "risks": ["近 30 条互动率不到偏低线的 10%", "历史最高粉丝到当前掉粉超过 10%", "粉丝列表设为不可见，无法抽样", "断更约 140 天"],
                   "summary": "23 万粉几乎不产生互动，掉粉超过 10%，粉丝列表不可见。"},
        "demo_c": {"content": "家常菜教程，与挂牌“美食号”一致", "content_ok": True,
                   "portrait": "星图搜不到本号，挂牌写“70 中间女粉”，评论区以女性昵称为主，仅作参考", "portrait_ok": None, "brush": None,
                   "risks": ["断更约 200 天", "近 30 条互动率低于偏低线", "抽样疑似僵尸粉接近 20%"],
                   "summary": "粉丝里空壳号偏多，且已断更半年以上，只适合压价收作粉丝底座。"},
    }
    notes = {"xingtu": "示例号的星图画像与挂牌的女粉占比相符。", "third_party": "示例批次没有查询蝉妈妈、飞瓜等第三方平台。",
             "cross": ["三方粉丝数基本一致；示例账号B的红狐数据抓取时间偏旧，粉丝数接近历史最高值。"]}
    wj(W / "listing" / "filtered.json", rows)
    wj(W / "qual.json", {"accounts": qual, "notes": notes})
    wj(W / "accounts.json", accounts)
    wj(W / "redfox_data.json", rf_data)
    wj(W / "redfox_usage.json", {"budget": 200, "reserve": 20, "calls": calls, "cumulative_cost": 0})
    wj(W / "parts" / "assets_manifest.json", manifest)
    batch = {"_说明": "合成示例批次：全部数据由 scripts/tools/make_demo_batch.py 生成，不含真实账号。", "batch": "demo", "work_dir": "work", "preview_dir": "preview",
             "preview_url": "", "listing": "listing/filtered.json", "qual": "qual.json", "mode": "simple", "date": DATE, "analysis_time": f"{DATE} 12:00",
             "collect_time": f"{DATE} 10:00~11:30", "title": "{n} 个示例抖音号：粉丝质量调研报告", "cover_title": "抖音账号粉丝质量调研报告（示例）",
             "cover_subtitle": "{n} 个合成示例账号", "data_sources": "合成示例数据（演示用）", "cover_sources": "合成示例数据（演示用）", "short_names": {}}
    wj(OUT / "batch.json", batch)
    print(f"示例批次已生成：{OUT}")
    print(f"  python scripts/build_report.py --config {OUT / 'batch.json'} --mode both")


if __name__ == "__main__":
    main()
