"""报告总入口：按模式依次运行分析、报告、图表、PDF 各步骤。

用法：
  python scripts/build_report.py --config <batch.json> [--mode simple|full|both] [选项]

选项：
  --mode          simple（默认，取 batch.json 的 mode）：手机优先 report.html + 手机 PDF report.pdf
                  full：桌面版 report-full.html + A4 PDF report-a4.pdf
                  both：两种都生成（文件名不冲突）
  --skip-analyze  跳过三个分析脚本（分析结果已是最新时用）
  --no-pdf        只生成 HTML
  --check         额外检查：主页截图裁剪对照图、简约模式逐号页数（每号 ≤2 页）、PDF 低填充页、手机宽度横向溢出

每一步都是独立的子进程，出错即停，并提示是哪一步。
"""
import argparse, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import config

config.setup_stdout()
ap = argparse.ArgumentParser(description="抖音账号调研报告总入口")
ap.add_argument("--config", required=True, help="批次配置 batch.json")
ap.add_argument("--mode", choices=["simple", "full", "both"], default=None)
ap.add_argument("--skip-analyze", action="store_true")
ap.add_argument("--no-pdf", action="store_true")
ap.add_argument("--check", action="store_true")
a = ap.parse_args()

cfg = str(Path(a.config).resolve())
B = config.load(cfg, argv=[])
mode = a.mode or B.mode
env = dict(os.environ, PYTHONIOENCODING="utf-8")
env[config.ENV_CONFIG] = cfg
PY = sys.executable


def run(title, script, *args, with_config=True):
    t = time.time()
    print(f"\n=== {title}：{script} {' '.join(args)}", flush=True)
    r = subprocess.run([PY, str(HERE / script), *(["--config", cfg] if with_config else []), *args], env=env)
    if r.returncode:
        raise SystemExit(f"步骤失败：{title}（{script}，退出码 {r.returncode}）")
    print(f"--- {title} 完成，{time.time() - t:.1f} 秒", flush=True)


print(f"批次 {B.name}  模式 {mode}  工作目录 {B.W}  预览目录 {B.P}")
B.P.mkdir(parents=True, exist_ok=True)
if not a.skip_analyze:
    run("作品分析", "analyze/analyze_posts.py")
    run("粉丝分析", "analyze/analyze_fans.py")
    run("评论分析", "analyze/analyze_comments.py")
run("第一遍报告（不合并）", "report/build_full.py", "--no-merge")
run("总览宽表", "report/build_overview_table.py")
run("完整版图表", "report/build_charts.py")
run("手机版图表", "report/build_charts_m.py")
run("第二遍报告（合并总览表和图表）", "report/build_full.py")

if mode in ("full", "both") and not a.no_pdf:
    run("A4 PDF", "report/build_pdf.py")
    if a.check:
        run("A4 PDF 低填充页", "tools/pdf_sheet.py", str(B.P / "report-a4.pdf"), "pdf-a4-sheet")

if mode in ("simple", "both"):
    run("手机版 HTML", "report/mobile.py")
    run("卡片详情", "report/build_detail_m.py")
    run("合并卡片详情", "report/merge_detail.py")
    if a.check:
        run("主页截图裁剪对照图", "report/crop_profile.py", "--dir", str(B.W / "shots_clean"), "--out", str(B.P),
            "--mode", "3", "--width", "520", "--sheet", str(B.P / "progress" / "crop-check.jpg"), with_config=False)
        for aid in config.account_ids(B):
            if (B.parts / "detail_m" / f"acct_{aid}.html").exists():
                run(f"页数检查 {aid}", "report/sample_detail.py", aid, f"chk-{aid}")
        run("手机宽度横向溢出", "tools/mshot.py", "report.html", "m", "390", "#overview", "2")
    if not a.no_pdf:
        run("手机 PDF", "report/build_pdf_m.py")
        if a.check:
            run("手机 PDF 低填充页", "tools/pdf_sheet.py", str(B.P / "report.pdf"), "pdfm-sheet")

print("\n全部完成。产物：")
for f in (["report.html", "report.pdf"] if mode in ("simple", "both") else []) + (["report-full.html", "report-a4.pdf"] if mode in ("full", "both") else []):
    p = B.P / f
    print(f"  {p}  {'%.1f MB' % (p.stat().st_size / 1e6) if p.exists() else '（未生成）'}")
