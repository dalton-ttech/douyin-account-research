"""星图截图抹水印（WORKFLOW 6.9 节）：星图页面铺满浅灰平铺水印，内容是登录账号名，裁掉顶部 92 像素去不掉。
不绕过平台的防篡改，只在本地对截图做后处理：浅色、近中性灰的像素用同位置的中值滤波结果替换，
其余像素（正文、图表、图片）保持原样。白底和浅灰底上的水印会被抹掉；叠在彩色图片上的水印抹不掉，但很淡。

单张：
  python scripts/report/xt_dewatermark.py SRC DST [--width 1100] [--quality 78] [--median 9] [--min-level 222] [--max-chroma 8]
  DST 以 .png 结尾时存无损 PNG，否则存 JPEG。原图不修改。

整批（在生成报告之前运行）：
  python scripts/report/xt_dewatermark.py --config <batch.json> [--check] [--precropped] [号 ...]
  对 <WORK_DIR>/shots_mine/xingtu/<id>/*.png：
    1. 第一次处理时把带水印的原图复制到 <WORK_DIR>/shots_mine/xingtu_raw/<id>/（只留在工作目录，不进预览目录）；
    2. 以 xingtu_raw 里的原图为输入，把抹掉水印的 PNG 写回 shots_mine/xingtu/<id>/，报告脚本照常读取。
  可重复运行，结果相同。
  --check       另存放大检查图 <PREVIEW_DIR>/progress/xt-dewm-check.jpg：每张图取水印最密的一块，放大 2 倍。
                逐块看，认不出任何字才算合格；认得出就调大 --median 或调低 --min-level 后重跑。
  --precropped  这批截图在采集时已经裁掉了顶部 92 像素（例如用自写脚本采集）。报告阶段的 report_data.py
                还会再裁 92 像素，所以这里在顶部补一条 92 像素白边，让报告只裁掉白边、不切内容。
                用仓库的 xt_collect.mjs 采集的截图保留原图，不要加这个参数。
"""
import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

TOP = 92


def dewm_image(im, median=9, min_level=222, max_chroma=8):
    """返回抹掉浅灰平铺水印的新图（RGB）。"""
    im = im.convert("RGB")
    a = np.asarray(im).astype(np.int16)
    med = np.asarray(im.filter(ImageFilter.MedianFilter(median))).astype(np.int16)
    mn, mx = a.min(2), a.max(2)
    mask = (mn >= min_level) & ((mx - mn) <= max_chroma)
    out = a.copy()
    out[mask] = med[mask]
    return Image.fromarray(out.astype(np.uint8))


def save(o, dst, width=None, quality=78):
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if width and o.width > width:
        o = o.resize((width, round(o.height * width / o.width)), Image.LANCZOS)
    if dst.suffix.lower() == ".png":
        o.save(dst, "PNG")
    else:
        o.save(dst, "JPEG", quality=quality)
    return o.size


def dewm(src, dst, width=1100, quality=78, median=9, min_level=222, max_chroma=8):
    o = dewm_image(Image.open(src), median, min_level, max_chroma)
    return save(o, dst, width, quality)


def densest_crop(before, after, w=320, h=200, skip_top=TOP):
    """在抹水印前后差异最多的位置取一块，用来放大检查。"""
    a = np.asarray(before.convert("RGB")).astype(np.int16)
    b = np.asarray(after.convert("RGB")).astype(np.int16)
    diff = (np.abs(a - b).max(2) > 0).astype(np.int32)
    diff[:min(skip_top, diff.shape[0])] = 0
    H, W = diff.shape
    w, h = min(w, W), min(h, H)
    s = np.pad(diff.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    win = s[h:, w:] - s[:-h, w:] - s[h:, :-w] + s[:-h, :-w]
    y, x = np.unravel_index(int(win.argmax()), win.shape)
    return after.crop((x, y, x + w, y + h)).resize((w * 2, h * 2), Image.NEAREST)


def sheet(items, dst, cols=3):
    from PIL import ImageDraw, ImageFont
    if not items:
        return
    tw, th = items[0][1].size
    m, lh = 10, 24
    rows = (len(items) + cols - 1) // cols
    sh = Image.new("RGB", (cols * (tw + m) + m, rows * (th + lh + m) + m), "#E5E6EB")
    d = ImageDraw.Draw(sh)
    font = None
    for f in ("msyh.ttc", "simhei.ttf", "PingFang.ttc", "NotoSansCJK-Regular.ttc"):
        try:
            font = ImageFont.truetype(f, 14)
            break
        except OSError:
            continue
    for i, (lab, im) in enumerate(items):
        x, y = m + (i % cols) * (tw + m), m + (i // cols) * (th + lh + m)
        d.text((x, y + 3), lab, fill="#1F2329", font=font)
        sh.paste(im, (x, y + lh))
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    sh.save(dst, "JPEG", quality=82)


def batch(argv):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import config

    config.setup_stdout()
    B = config.load(argv=argv)
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--precropped", action="store_true")
    ap.add_argument("--median", type=int, default=9)
    ap.add_argument("--min-level", type=int, default=222)
    ap.add_argument("--max-chroma", type=int, default=8)
    a = ap.parse_args(argv)
    base, raw_base = B.W / "shots_mine" / "xingtu", B.W / "shots_mine" / "xingtu_raw"
    ids = a.ids or (sorted(p.name for p in base.iterdir() if p.is_dir()) if base.exists() else [])
    checks, n = [], 0
    for aid in ids:
        d = base / aid
        if not d.is_dir():
            print(aid, "没有星图截图，跳过")
            continue
        for p in sorted(d.glob("*.png")):
            raw = raw_base / aid / p.name
            if not raw.exists():
                raw.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, raw)
            src = Image.open(raw).convert("RGB")
            out = dewm_image(src, a.median, a.min_level, a.max_chroma)
            if a.precropped:
                pad = Image.new("RGB", (out.width, out.height + TOP), "white")
                pad.paste(out, (0, TOP))
                save(pad, p)
            else:
                save(out, p)
            n += 1
            print(aid, p.name, "已抹水印", "（顶部补白边）" if a.precropped else "")
            if a.check and not p.name.startswith("03-home-full"):
                checks.append((f"{aid} {p.stem}", densest_crop(src, out, skip_top=0 if a.precropped else TOP)))
    print(f"共处理 {n} 张；带水印的原图在 {raw_base}（只留工作目录）")
    if a.check:
        dst = B.P / "progress" / "xt-dewm-check.jpg"
        sheet(checks, dst)
        print("放大检查图：", dst, ("→ " + B.link("progress/xt-dewm-check.jpg")) if B.url else "")


def main():
    argv = sys.argv[1:]
    if any(x == "--config" or x.startswith("--config=") for x in argv):
        return batch(argv)
    p = argparse.ArgumentParser(description="星图截图抹水印")
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--width", type=int, default=1100)
    p.add_argument("--quality", type=int, default=78)
    p.add_argument("--median", type=int, default=9)
    p.add_argument("--min-level", type=int, default=222)
    p.add_argument("--max-chroma", type=int, default=8)
    a = p.parse_args(argv)
    print(dewm(a.src, a.dst, a.width, a.quality, a.median, a.min_level, a.max_chroma))


if __name__ == "__main__":
    main()
