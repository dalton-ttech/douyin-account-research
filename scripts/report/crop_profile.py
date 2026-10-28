"""抖音网页版主页截图 → “账号信息 + 第一排前 N 条作品”裁剪图（分账号详情 ② 账号首页截图）。

按内容定位，不用死坐标：
  1. 锚点：“作品 N”标签下的红色下划线（#FE2C55 一类，3px 高、约 50~140px 宽）→ 内容区左边界 x0、标签栏 y。
  2. 头部顶边：下划线 y − 191（1280 视口实测）与头像像素检测互相校验。
  3. 第一排卡片：下划线以下第一条“超过一半像素不是背景色”的行 = 卡片顶；按列找卡片左右边界；
     按行找缩略图底边、标题行底边（无标题的号按标题行高度补齐，保证各号裁剪高度一致）。
  4. 裁剪框：左 = x0 − 半个卡片间距，右 = 第 N 张卡片右边 + 半个间距，上 = 头部顶 − 10，下 = 标题行底 + 8。
所有像素常量按“截图宽 / 1280”等比换算，1100 宽的 dc-01-profile.jpg 也能用，但优先用 1280 宽无损原图。

用法：
  python crop_profile.py SRC DST [--mode 3|6] [--width PX] [--quality 80] [--debug DEBUG.jpg]
  python crop_profile.py --dir <WORK_DIR>/shots_clean --out <PREVIEW_DIR> [--mode 3] [--width 520] [--name dc-01-home.jpg] [--sheet crop-check.jpg]
      对 --dir 下每个 <aid>/01-profile.png 输出 <out>/<aid>/<name>；--sheet 另拼一张对照图。
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw

REF_W = 1280
HEAD_ABOVE_TAB = 191
GAP = 17
PITCH = 179.2
CARD_W = 163
THUMB_H = 217
TITLE_H = 26
PAD = 8
PAD_TOP = 10
PAD_BOTTOM = 8


def _runs(mask):
    out, s = [], None
    for i, v in enumerate(mask):
        if v and s is None:
            s = i
        elif not v and s is not None:
            out.append((s, i - 1))
            s = None
    if s is not None:
        out.append((s, len(mask) - 1))
    return out


def _find_tab(im, k):
    h, w, _ = im.shape
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    red = (r > 190) & (g < 100) & (b < 140) & (r - g > 120)
    lo, hi = int(40 * k), int(150 * k)
    for y in range(int(h * 0.12), int(h * 0.6)):
        for s, e in _runs(red[y, : w // 2]):
            if lo <= e - s + 1 <= hi and red[y + 1, s + 2 : e - 1].mean() > 0.8:
                return y, s, e
    return None


def detect(img, mode="3"):
    """返回检测结果 dict：box（裁剪框 l,t,r,b）、cards、empty、titles、warn。"""
    n = 6 if str(mode) == "6" else 3
    im = np.asarray(img.convert("RGB")).astype(int)
    h, w, _ = im.shape
    k = w / REF_W
    tab = _find_tab(im, k)
    if not tab:
        raise ValueError("找不到“作品”标签下的红色下划线：截图不是抖音网页版主页，或没滚到顶部")
    ty, x0, _ = tab
    bg = np.median(im[ty + int(4 * k) : ty + int(10 * k), x0 : x0 + int(600 * k)].reshape(-1, 3), axis=0)
    nb = np.abs(im - bg).max(axis=2) > 14
    lum = 0.3 * im[..., 0] + 0.59 * im[..., 1] + 0.11 * im[..., 2]
    warn = []

    anchor = ty - round(HEAD_ABOVE_TAB * k)
    reg = nb[max(anchor - int(40 * k), 0) : ty - int(60 * k), x0 : x0 + int(112 * k)]
    rows = np.nonzero(reg.sum(1) >= 3)[0]
    det = max(anchor - int(40 * k), 0) + rows[0] if len(rows) else anchor
    head_top = det if abs(det - anchor) <= 12 * k else anchor

    gx1 = min(w, x0 + int((6 * PITCH) * k))
    frac = nb[:, x0:gx1].mean(1)
    gy = next((y for y in range(ty + int(40 * k), h) if frac[y] > 0.5), None)
    pad, gap, pitch = round(PAD * k), round(GAP * k), PITCH * k
    out = {"src_size": [w, h], "tab_y": int(ty), "x0": int(x0), "head_top": int(head_top), "mode": str(n), "warn": warn}

    if gy is None or gy > h - 60 * k:
        chip = np.nonzero((lum[ty + int(5 * k) : ty + int(80 * k), x0 : x0 + int(250 * k)] > 100).sum(1) > 0)[0]
        bottom = ty + int(5 * k) + (chip[-1] if len(chip) else int(45 * k)) + round(12 * k)
        right = round(x0 + (n - 1) * pitch + CARD_W * k) + 1 + pad
        out.update(empty=True, titles=False, cards=[], box=[int(x0 - pad), int(head_top - PAD_TOP * k), int(min(right, w)), int(bottom)])
        warn.append("第一排没有作品卡片（0 作品或未加载），只裁头部和标签栏")
        return out

    bh = int(146 * k)
    band = nb[gy + int(4 * k) : gy + int(4 * k) + bh, :].sum(0) > bh * 0.06
    band[: max(x0 - round(6 * k), 0)] = False
    cr = _runs(band)
    merged = []
    for s, e in cr:
        if merged and s - merged[-1][1] <= gap // 2:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    cards = [(s, e) for s, e in merged if e - s > 60 * k]
    if len(cards) >= 2:
        pitch = (cards[min(len(cards), n) - 1][0] - cards[0][0]) / max(min(len(cards), n) - 1, 1)
        if abs(pitch - PITCH * k) > 6 * k:
            warn.append(f"卡片间距 {pitch:.0f}px 与常规 {PITCH * k:.0f}px 不符，检查是否换了视口宽度")
    if len(cards) < n:
        warn.append(f"第一排只有 {len(cards)} 张卡片，右边界按 {n} 张的网格补齐")
        right = round(x0 + (n - 1) * pitch + CARD_W * k) + 1 + pad
    else:
        right = cards[n - 1][1] + 1 + pad
    right = min(right, w)

    cx0, cx1 = cards[0][0], (cards[min(n, len(cards)) - 1][1] + 1)
    full = nb[:, cx0:cx1].mean(1) > 0.5
    run = int(30 * k)
    solid = np.array([full[y : y + run].all() for y in range(h)])
    tb = gy
    while tb + 1 < h and full[tb + 1]:
        tb += 1
    if abs((tb - gy + 1) - THUMB_H * k) > 15 * k:
        warn.append(f"缩略图高 {tb - gy + 1}px 与常规 {THUMB_H * k:.0f}px 不符，按常规高度计算")
        tb = gy + round(THUMB_H * k) - 1
    txt = (lum[:, cx0:cx1] > 100).sum(1) >= 2
    title_end, y = None, tb + 1
    lim = min(h, tb + int(45 * k))
    while y < lim and not txt[y] and not solid[y]:
        y += 1
    if y < lim and y - tb <= 20 * k and not solid[y]:
        while y < lim and txt[y] and not solid[y]:
            y += 1
        title_end = y - 1
    row2 = next((yy for yy in range(tb + int(10 * k), h) if solid[yy]), None)
    bottom = max(title_end or 0, tb + round(TITLE_H * k)) + round(PAD_BOTTOM * k)
    if row2 is not None:
        bottom = min(bottom, row2 - round(3 * k))
    bottom = min(bottom, h)
    if row2 is None and h - tb < 30 * k:
        warn.append("截图底部离第一排缩略图太近，标题行可能不完整")
    left = max(x0 - pad, 0)
    top = max(head_top - round(PAD_TOP * k), 0)
    edge = lum[top : ty - int(15 * k), max(right - 3, 0) : right] > 110
    if edge.any():
        warn.append("头部有文字跨过右边界，可能被截断")
    out.update(empty=False, titles=title_end is not None, thumb=[int(gy), int(tb)], row2_top=None if row2 is None else int(row2),
               cards=[[int(s), int(e)] for s, e in cards], box=[int(left), int(top), int(right), int(bottom)])
    return out


def crop_profile(src, dst, mode="3", width=None, quality=80, debug=None):
    """从主页截图 src 裁出“账号信息 + 第一排前 mode 条作品”，存为 JPEG dst。
    width：输出像素宽（按显示宽 × 2 给）；只缩小不放大。返回检测结果 dict（含 out_size）。"""
    img = Image.open(src).convert("RGB")
    info = detect(img, mode)
    crop = img.crop(tuple(info["box"]))
    if width and width < crop.width:
        crop = crop.resize((width, round(crop.height * width / crop.width)), Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    crop.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)
    info["out_size"] = list(crop.size)
    if debug:
        dbg = img.copy()
        d = ImageDraw.Draw(dbg)
        for s, e in info["cards"]:
            d.rectangle([s, info["thumb"][0], e, info["thumb"][1]], outline="#00E5FF", width=2)
        d.rectangle(info["box"], outline="#FFE100", width=3)
        d.line([info["x0"], info["tab_y"], info["x0"] + 80, info["tab_y"]], fill="#00FF66", width=3)
        dbg.save(debug, "JPEG", quality=70)
    return info


def contact_sheet(items, dst, cols=5, tw=400):
    """items：[(标签, 图片路径)]，拼成 cols 列的对照图，每张缩到 tw 宽。"""
    from PIL import ImageFont
    ims = [(lab, Image.open(p)) for lab, p in items]
    th = max(round(im.height * tw / im.width) for _, im in ims)
    m, lh = 12, 26
    rows = (len(ims) + cols - 1) // cols
    sh = Image.new("RGB", (cols * (tw + m) + m, rows * (th + lh + m) + m), "#E5E6EB")
    d = ImageDraw.Draw(sh)
    try:
        font = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 15)
    except OSError:
        font = None
    for i, (lab, im) in enumerate(ims):
        x, y = m + (i % cols) * (tw + m), m + (i // cols) * (th + lh + m)
        t = im.resize((tw, round(im.height * tw / im.width)), Image.LANCZOS)
        d.text((x, y + 2), f"{i + 1}. {lab}  {im.width}x{im.height}", fill="#1F2329", font=font)
        sh.paste(t, (x, y + lh))
        d.rectangle([x - 1, y + lh - 1, x + tw, y + lh + t.height], outline="#8F959E")
    sh.save(dst, "JPEG", quality=80, optimize=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", nargs="?")
    ap.add_argument("dst", nargs="?")
    ap.add_argument("--mode", default="3", choices=["3", "6"])
    ap.add_argument("--width", type=int, default=None)
    ap.add_argument("--quality", type=int, default=80)
    ap.add_argument("--debug")
    ap.add_argument("--dir")
    ap.add_argument("--out")
    ap.add_argument("--name", default=None)
    ap.add_argument("--sheet", help="批量模式下把所有裁剪图拼成对照图（JPEG）")
    a = ap.parse_args()
    if a.dir:
        name = a.name or ("dc-01-home.jpg" if a.mode == "3" else "dc-01-home6.jpg")
        res = {}
        for aid in sorted(os.listdir(a.dir)):
            src = os.path.join(a.dir, aid, "01-profile.png")
            if not os.path.exists(src):
                continue
            try:
                res[aid] = crop_profile(src, os.path.join(a.out or a.dir, aid, name), a.mode, a.width, a.quality)
            except ValueError as ex:
                res[aid] = {"error": str(ex)}
            r = res[aid]
            print(aid, r.get("box"), r.get("out_size"), "无标题行" if r.get("titles") is False and not r.get("empty") else "",
                  "; ".join(r.get("warn", [])) or r.get("error", ""))
        if a.sheet:
            contact_sheet([(aid, os.path.join(a.out or a.dir, aid, name)) for aid in res if "box" in res[aid]], a.sheet)
        return res
    if not (a.src and a.dst):
        ap.error("需要 SRC DST，或用 --dir 批量")
    print(json.dumps(crop_profile(a.src, a.dst, a.mode, a.width, a.quality, a.debug), ensure_ascii=False))


if __name__ == "__main__":
    main()
