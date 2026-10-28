"""报告数据层：两种模式共用。

对应第一批 build_report_v2.py 中“# ---------- build ----------”之前的部分：
ORDER（账号顺序）、P / F / C / RF / XT（采集与分析数据）、QUAL（定性判断，来自 qual.json）、
derive / rate / ADVICE（来自 analyze/rating.py）、xt_info / dist（星图）、截图转换 shots_for。
其他脚本用 `from report_data import *` 或按名字导入。
"""
import glob, html, json, os, sys
from pathlib import Path
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from analyze import rating
from analyze.rating import TIERS, tier_of, ADVICE, GCLS, rate, why_full, std_rows, GRADE_NOTES  # noqa: F401
from analyze.rating import SRC_REDFOX, SRC_CHANMAMA, SRC_ZOMBIE, SRC_XINGTU, SRC_NEWRANK, SRC_ZHB  # noqa: F401

config.setup_stdout()
BATCH = config.load()
W = str(BATCH.W)
OUT = str(BATCH.P)
PARTS = str(BATCH.parts)
DATE = BATCH.date


def J(p, d=None):
    try:
        return json.load(open(os.path.join(W, p), encoding="utf-8"))
    except Exception:
        return d


P = J("analysis_posts.json", {})
F = J("fans_analysis.json", {})
C = J("comments_analysis.json", {})
RF = J("redfox_data.json", {"accounts": {}, "works": {}})
XT = {os.path.basename(p)[:-5]: json.load(open(p, encoding="utf-8")) for p in glob.glob(os.path.join(W, "xingtu_data", "*.json")) if not os.path.basename(p).startswith("_")}

ROWS = config.listing_rows(BATCH)
LISTING_ROWS = {r["id"]: r for r in ROWS}
ORDER = [r["id"] for r in ROWS]
QUAL, NOTES = config.load_qual(BATCH)

e = lambda s: html.escape(str(s)) if s is not None else "—"

QUAL_DEFAULT = dict(content="未填写（qual.json 缺少该号）", content_ok=None, portrait="未填写", portrait_ok=None, brush=None,
                    risks=["qual.json 里还没有写该号的风险"], summary="qual.json 里还没有写该号的结论。")


def qual(aid):
    q = dict(QUAL_DEFAULT)
    q.update(QUAL.get(aid) or {})
    q["risks"] = list(q.get("risks") or ["—"])
    return q


def listing(aid):
    """挂牌信息 [挂牌粉丝, 类型, 认证与画像原文, 状态]；先取分析结果里的，没有再取账号清单。"""
    lst = (P.get(aid) or {}).get("listing")
    if lst and lst[0]:
        return lst
    r = LISTING_ROWS.get(aid)
    return [r["listing_fans"], r["category"], r["portrait"], r["status"]] if r else None


def nick(aid):
    p = P.get(aid)
    if p:
        return p["nickname"]
    r = LISTING_ROWS.get(aid) or {}
    return r.get("nickname") or "（未能定位）"


def short(aid):
    """图表里用的短昵称：清单里的 short 字段 > batch.json 的 short_names > 超过 8 个字截断。"""
    n = nick(aid)
    s = (LISTING_ROWS.get(aid) or {}).get("short") or BATCH.short_names.get(n)
    if s:
        return s
    return n if len(n) <= 8 else n[:7] + "…"


def listing_segments(aid, nk=None):
    lst = listing(aid) or [None, "", "", ""]
    fans = f"{lst[0]/10000:g}万粉丝" if lst[0] else "挂牌粉丝未知"
    return [f"抖音:{aid}", nk or nick(aid), fans, lst[1], str(lst[2]).replace(" ", ""), lst[3]]


def listing_line_html(aid, nk=None):
    segs = listing_segments(aid, nk)
    seps = ["---", "---", "---", "-----", "---"]
    return f'<span class="nw">{e(segs[0])}</span>' + "".join(f'<span class="sep">{s_}</span><span class="nw">{e(x)}</span>' for s_, x in zip(seps, segs[1:]) if x)


def pct(v, d=1):
    return "—" if v is None else f"{v:.{d}f}%"


def num(v):
    if v is None:
        return "—"
    try:
        v = float(v)
    except Exception:
        return e(v)
    if abs(v) >= 10000:
        return f"{v/10000:.2f} 万"
    return f"{v:,.0f}"


# ---------- images ----------
def conv(src, rel, crop_top=0, max_w=1100, blur_boxes=()):
    if not os.path.exists(src):
        return None
    dst = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im = Image.open(src).convert("RGB")
    for box in blur_boxes:
        reg = im.crop(box).filter(ImageFilter.GaussianBlur(9))
        im.paste(reg, box[:2])
    if crop_top:
        im = im.crop((0, crop_top, im.width, im.height))
    if im.width > max_w:
        im = im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)
    im.save(dst, "JPEG", quality=78)
    return rel.replace("\\", "/")


def shots_for(aid):
    """抖音截图（只收 res.json 标了 ok 的）和星图截图（裁掉顶部 92 像素登录名）转成预览目录里的 JPEG。"""
    out = {}
    d = os.path.join(W, "shots_clean", aid)
    res = {}
    try:
        res = json.load(open(os.path.join(d, "res.json"), encoding="utf-8"))
    except Exception:
        pass
    for p in sorted(glob.glob(os.path.join(d, "*.png"))):
        b = os.path.basename(p)[:-4]
        tag = "03-top" if b.startswith("03-top") else ("04-recent" if b.startswith("04-recent") else b)
        if tag in ("03-top", "04-recent"):
            r = res.get(tag) or {}
            if not (r.get("ok") and r.get("url")):
                continue
        if b == "01-profile" and not res.get("profileOk"):
            continue
        boxes = ((975, 50, 1280, 860),) if tag in ("03-top", "04-recent") else ()
        out[b] = conv(p, f"{aid}/dc-{b}.jpg", blur_boxes=boxes)
    xd = os.path.join(W, "shots_mine", "xingtu", aid)
    for p in sorted(glob.glob(os.path.join(xd, "*.png"))):
        b = os.path.basename(p)[:-4]
        if b.startswith("03-home-full"):
            continue
        out["xt-" + b] = conv(p, f"{aid}/xt-{b}.jpg", crop_top=92)
    return out


def fig(src, cap, cls=""):
    if not src:
        return ""
    return f'<figure class="{cls}"><a href="{e(src)}" target="_blank"><img src="{e(src)}" loading="lazy"></a><figcaption>{cap}</figcaption></figure>'


def derive(aid):
    return rating.derive(P.get(aid), F.get(aid), C.get(aid), qual(aid))


# ---------- xingtu helpers ----------
def xt_info(aid):
    x = XT.get(aid)
    if not x:
        return None
    s = x.get("search") or {}
    a0 = (s.get("authors") or [None])[0]
    base = ((x.get("api") or {}).get("base") or {}).get("b") or {}
    matched = bool(a0) and str(base.get("unique_id", "")).lower() == aid.lower()
    out = dict(found=matched, total=s.get("total"), a0=a0, base=base, api=x.get("api") or {}, near=None)
    if a0 and not matched:
        out["near"] = f"{a0.get('nick_name')}（{a0.get('follower')} 粉，抖音号 {base.get('unique_id')}）"
    return out


def dist(api, key="fans_all"):
    b = (api.get(key) or {}).get("b") or {}
    res = {}
    for d0 in (b.get("distributions") or []) if isinstance(b, dict) else []:
        lst = [(i.get("distribution_key"), float(i.get("distribution_value") or 0)) for i in d0.get("distribution_list", [])]
        tot = sum(v for _, v in lst) or 1
        lst = sorted(lst, key=lambda t: -t[1])
        res[d0.get("type_display")] = dict(desc=d0.get("description"), items=[(k, v / tot * 100, v) for k, v in lst], total=tot)
    return res


GENDER = {"female": "女", "male": "男"}


def bars(items, n=8):
    rows = []
    for k, p_, v in items[:n]:
        k = GENDER.get(k, k)
        rows.append(f'<div class="bar"><span class="bk">{e(k)}</span><span class="bt"><i style="width:{min(p_,100):.1f}%"></i></span><span class="bv">{p_:.1f}%</span></div>')
    return "".join(rows)


def xt_block(aid, shots):
    xi = xt_info(aid)
    if xi is None:
        return '<p class="muted">星图：未查询。</p>'
    if not xi["found"]:
        msg = "星图按抖音号搜索结果为 0（未入驻或搜不到）。" if not xi["total"] else f"星图按抖音号只搜到相似号 {e(xi['near'])}，不是本号，视为未入驻。"
        return f'<div class="xt"><p>{msg}</p><div class="figs">{fig(shots.get("xt-01-search"), f"星图按抖音号搜索的结果页：未入驻 / 搜不到（{DATE} 查询）", "big")}</div></div>'
    a0, api = xi["a0"], xi["api"]
    D = dist(api, "fans_all")
    D1 = dist(api, "fans_t1")
    sp = (api.get("spread_p90") or {}).get("b") or {}

    def v100(o):
        return None if not isinstance(o, dict) or o.get("value") is None else o["value"] / 100
    pm = sp.get("play_mid"); por = v100(sp.get("play_over_rate")); ir = v100(sp.get("interact_rate"))
    daily = ((api.get("daily_fans") or {}).get("b") or {}).get("daily") or []
    dtxt = ""
    if daily:
        d0, d1 = daily[0], daily[-1]
        dtxt = f"{d0['date']} {d0['fans_cnt']:,} → {d1['date']} {d1['fans_cnt']:,}（{d1['fans_cnt']-d0['fans_cnt']:+,}）"
    mk = (api.get("marketing") or {}).get("b") or {}
    price = "暂无报价" if not mk.get("price_info") else "；".join(f"{p_.get('desc') or p_.get('video_type')}: ¥{p_.get('price')}" for p_ in mk["price_info"])
    contract = (api.get("contract") or {}).get("b") or {}
    kv = [
        ("星图粉丝数", num(a0.get("follower"))),
        ("近 30 天粉丝变化", f"{int(a0.get('fans_increment_within_30d') or 0):+,}"),
        ("星图近 30 天粉丝变化", dtxt or "—"),
        ("星图指数（总）", a0.get("link_star_index")),
        ("　传播指数 / 种草指数 / 转化指数", f"{a0.get('link_spread_index')} / {a0.get('link_shopping_index')} / {a0.get('link_convert_index')}"),
        ("预期播放量", num(a0.get("expected_play_num"))),
        ("近 90 天个人视频：播放中位数", "—（近 90 天无可统计视频）" if not pm else f"{pm:,}（优于 {sp['item_rate']['play_mid'].get('overtake',0)/100:.1f}% 同类达人）"),
        ("　完播率 / 互动率（互动÷播放）", "—" if por is None else f"{por:.2f}% / {ir:.2f}%"),
        ("　90 天作品数 / 平均点赞", "—" if not sp.get("item_num") else f"{sp.get('item_num')} / {sp.get('like_avg')}"),
        ("报价", price),
        ("信用分", contract.get("new_credit_score", "—")),
        ("内容标签", ", ".join(json.loads(a0.get("tags_relation") or "{}").keys()) or "—"),
    ]
    tbl = "".join(f"<tr><th>{e(k)}</th><td>{e(v)}</td></tr>" for k, v in kv)
    charts = ""
    for name in ["性别分布", "年龄分布", "八大人群分布", "省份分布", "城市等级分布", "设备品牌分布", "兴趣分布"]:
        if name in D:
            charts += f'<div class="chart"><h5>{e(name)}<small>{e(D[name]["desc"])}</small></h5>{bars(D[name]["items"])}</div>'
    return f'''<div class="xt"><div class="figs">{fig(shots.get("xt-02-home"), "星图达人主页：数据概览（传播价值）与报价栏", "big")}{fig(shots.get("xt-01-search"), "星图按抖音号搜索：找到本号，含粉丝、预期播放量和报价列", "big")}</div><h4>星图官方数据（{DATE} 查询）</h4>
<p class="muted">星图主页已升级，原“星图指数五维图”已下线；指数分项取自星图达人广场，粉丝画像为星图官方粉丝分布数据。</p>
<table class="kv">{tbl}</table>
<div class="charts">{charts}</div></div>'''


def redfox_time():
    """红狐查询时间段：从 redfox_usage.json 的调用记录里取最早和最晚时间。"""
    u = J("redfox_usage.json", {}) or {}
    ts = sorted(c.get("time", "") for c in u.get("calls") or [] if c.get("time"))
    if not ts:
        return DATE
    a, b = ts[0].replace("T", " ")[:16], ts[-1].replace("T", " ")[:16]
    return a if a == b else (f"{a}~{b[11:]}" if a[:10] == b[:10] else f"{a}~{b}")


def fans_sample_range():
    ns = [v["all"]["n"] for v in F.values() if (v.get("all") or {}).get("n")]
    if not ns:
        return "—"
    return f"{min(ns)}~{max(ns)}" if min(ns) != max(ns) else str(ns[0])
