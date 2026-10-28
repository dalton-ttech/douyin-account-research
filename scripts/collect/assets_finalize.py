"""总览素材收尾：把 dy_assets.mjs 下载的原图转成 JPEG，并写每号的素材说明（WORKFLOW 6.8 节）。

读  <WORK_DIR>/assets_work/<id>/meta.json、avatar.img、cover1.img、cover2.img
写  <PREVIEW_DIR>/overview-assets/<id>/avatar.jpg（160×160）、cover1.jpg、cover2.jpg（240×240）
    <WORK_DIR>/parts/assets/<id>.json（之后由 analyze/merge_collect.py 合并成 parts/assets_manifest.json）
缺图用灰底占位图；作品清空的号写“作品已清空”。

用法：python scripts/collect/assets_finalize.py --config <batch.json> [--agent dy-A | 号1 号2 ...]
不给号码时处理 assets_work 下所有号；--agent 时只处理 assignment.json 里该代理的号。
"""
import json, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
CST = timezone(timedelta(hours=8))
WORK = B.W / "assets_work"
OUT = B.P / "overview-assets"
FONTS = [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf", "/System/Library/Fonts/PingFang.ttc",
         "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"]

args = sys.argv[1:]
if args[:1] == ["--agent"] and len(args) > 1:
    asg = config.read_json(B.W / "locks" / "assignment.json", {}) or {}
    ids = ((asg.get("agents") or {}).get(args[1]) or {}).get("ids") or []
elif args:
    ids = args
else:
    ids = sorted(p.name for p in WORK.iterdir() if (p / "meta.json").exists()) if WORK.exists() else []


def font(size):
    for f in FONTS:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def placeholder(path, text, size=240):
    im = Image.new("RGB", (size, size), (226, 228, 232))
    d = ImageDraw.Draw(im)
    f = font(22)
    w = d.textlength(text, font=f)
    d.text(((size - w) / 2, size / 2 - 15), text, fill=(128, 132, 140), font=f)
    im.save(path, "JPEG", quality=80, optimize=True)


def square(src, dst, size, quality):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    im.resize((size, size), Image.LANCZOS).save(dst, "JPEG", quality=quality, optimize=True)


done = 0
for aid in ids:
    wd = WORK / aid
    p = config.read_json(wd / "meta.json")
    if not p:
        print(aid, "缺 assets_work/meta.json，跳过（先跑 dy_assets 步骤）")
        continue
    od = OUT / aid
    od.mkdir(parents=True, exist_ok=True)
    entry = {"nickname": p.get("nickname"), "gender": p.get("gender"), "region": p.get("region"), "verified": p.get("verified"),
             "avatar": f"overview-assets/{aid}/avatar.jpg", "covers": []}
    if p.get("custom_verify"):
        entry["verify_note"] = p["custom_verify"]
    try:
        square(wd / "avatar.img", od / "avatar.jpg", 160, 85)
    except Exception:
        placeholder(od / "avatar.jpg", "无头像", 160)
        entry["avatar_note"] = "占位图"
    sel, covers = p.get("sel") or [], p.get("covers") or []
    for i in range(2):
        fname = f"cover{i + 1}.jpg"
        dst, rel = od / fname, f"overview-assets/{aid}/{fname}"
        role = "点赞最高" if i == 0 else "最近非置顶"
        if i < len(sel):
            s = sel[i]
            live = covers[i] if i < len(covers) else {}
            source = "抖音作品详情接口封面"
            try:
                square(wd / f"cover{i + 1}.img", dst, 240, 80)
            except Exception as ex:
                print(aid, i + 1, "封面转换失败", ex)
                placeholder(dst, "封面缺失")
                source = "占位图（封面获取失败）"
            likes = live.get("digg") if live.get("digg") is not None else s.get("likes")
            ct = live.get("create_time") or s.get("create_time")
            entry["covers"].append({"file": rel, "likes": likes, "date": datetime.fromtimestamp(ct, CST).strftime("%Y-%m-%d") if ct else "",
                                    "desc": (s.get("desc") or "")[:20], "aweme_id": s.get("aweme_id"), "role": role, "source": source})
        else:
            placeholder(dst, "作品已清空")
            entry["covers"].append({"file": rel, "likes": None, "date": "", "desc": "", "aweme_id": None, "role": role, "source": "占位图（作品已清空）"})
    if not sel:
        entry["note"] = "作品已清空"
    (B.parts / "assets").mkdir(parents=True, exist_ok=True)
    (B.parts / "assets" / f"{aid}.json").write_text(json.dumps(entry, ensure_ascii=False, indent=1), encoding="utf-8")
    done += 1
    print(aid, entry["nickname"], "avatar", "占位" if entry.get("avatar_note") else "ok", [c["source"][:2] for c in entry["covers"]])
print(f"完成 {done} 个号 → {OUT}；说明文件在 {B.parts / 'assets'}")
