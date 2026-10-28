"""PDF 缩略总览：每张图 14 列、最多 5 行，并列出填充不足 60% 的页（接近空白的页）。

用法：python scripts/tools/pdf_sheet.py [--config <batch.json>] [PDF] [TAG] [--out 目录]
  有 --config 时 PDF 默认 <PREVIEW_DIR>/report.pdf，缩略图存 <PREVIEW_DIR>/progress/<TAG>-N.jpg；
  没有配置时必须给 PDF，缩略图存到 PDF 同目录的 progress/ 下。
"""
import os, sys
from pathlib import Path
import fitz
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
argv = sys.argv[1:]
out_dir = None
if "--out" in argv:
    i = argv.index("--out")
    out_dir = argv[i + 1]
    del argv[i:i + 2]
cfg = config._pop_config_arg(argv) or os.environ.get(config.ENV_CONFIG)
B = config.load(cfg, argv=[]) if cfg else None
args = [a for a in argv if not a.startswith("-")]
if args:
    PDF = args[0]
elif B:
    PDF = str(B.P / "report.pdf")
else:
    raise SystemExit("用法：python scripts/tools/pdf_sheet.py --config <batch.json> [PDF] [TAG]，或直接给 PDF 路径")
TAG = args[1] if len(args) > 1 else "pdfm-sheet"
OUT = Path(out_dir) if out_dir else ((B.P / "progress") if B else Path(PDF).resolve().parent / "progress")
OUT.mkdir(parents=True, exist_ok=True)
COLS, TW = 14, 130
doc = fitz.open(PDF)
thumbs = []
fill = []
for p in doc:
    pix = p.get_pixmap(dpi=24)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    g = im.convert("L")
    rows = [min(g.getpixel((x, y)) for x in range(g.width)) for y in range(g.height)]
    foot = max(int(g.height * 0.05), int(24 * g.height / p.rect.height) + 1)
    last = max([i for i, v in enumerate(rows[:-foot]) if v < 235] or [0])
    fill.append(last / g.height)
    thumbs.append(im.resize((TW, int(TW * im.height / im.width))))
th = max(t.height for t in thumbs)
rows_n = (len(thumbs) + COLS - 1) // COLS
for part in range(0, rows_n, 5):
    sub = thumbs[part * COLS:(part + 5) * COLS]
    r = (len(sub) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * (TW + 8) + 8, r * (th + 22) + 8), "#C9CDD4")
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(sub):
        x, y = 8 + (i % COLS) * (TW + 8), 8 + (i // COLS) * (th + 22)
        sheet.paste(t, (x, y))
        n = part * COLS + i
        d.text((x + 2, y + th + 4), f"p{n + 1} {int(fill[n] * 100)}%", fill="#1F2329")
    sheet.save(str(OUT / f"{TAG}-{part // 5 + 1}.jpg"), quality=80)
low = [(i + 1, int(f * 100)) for i, f in enumerate(fill) if f < 0.6]
print("pages", len(doc), "pages <60% filled:", len(low), low)
print("sheet", OUT / f"{TAG}-1.jpg")
