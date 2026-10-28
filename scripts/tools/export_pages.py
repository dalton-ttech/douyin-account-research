"""把 PDF 的指定页导出成 JPEG 样张（例如 examples/output/）。

用法：python scripts/tools/export_pages.py <PDF> <输出目录> <前缀> <页码 ...> [--width 900] [--quality 78]
  页码从 1 开始，可写 1 4 16-17；输出 <前缀>-p<页码>.jpg，宽度不超过 --width 像素。
"""
import argparse
from pathlib import Path

import fitz

ap = argparse.ArgumentParser()
ap.add_argument("pdf")
ap.add_argument("out")
ap.add_argument("prefix")
ap.add_argument("pages", nargs="+")
ap.add_argument("--width", type=int, default=900)
ap.add_argument("--quality", type=int, default=78)
a = ap.parse_args()

doc = fitz.open(a.pdf)
nums = []
for s in a.pages:
    lo, _, hi = s.partition("-")
    nums += range(int(lo), int(hi or lo) + 1)
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)
for n in nums:
    if not 1 <= n <= len(doc):
        print(f"跳过第 {n} 页：PDF 只有 {len(doc)} 页")
        continue
    page = doc[n - 1]
    zoom = a.width / page.rect.width
    f = out / f"{a.prefix}-p{n:02d}.jpg"
    page.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).save(str(f), jpg_quality=a.quality)
    print(f, f"{f.stat().st_size // 1024} KB")
