"""主页截图裁剪验收：只对某个代理自己的号出对照图（WORKFLOW 6.7 节第 6 步、prompts 第 2 节）。

先把自己号的 01-profile.png 复制到 <WORK_DIR>/logs/crop-<代理名>/src/<id>/，再对这个目录跑 crop_profile.py，
不直接对整个 shots_clean 跑（里面有另一个代理的号，可能还在写入）。
对照图：<PREVIEW_DIR>/progress/crop-check-<代理名>.jpg；不加 --agent 时对全部号出 crop-check.jpg（主代理合并后用）。

用法：python scripts/collect/crop_check.py --config <batch.json> [--agent dy-A]
"""
import shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import config

config.setup_stdout()
B = config.load()
args = sys.argv[1:]
agent = args[1] if args[:1] == ["--agent"] and len(args) > 1 else None
crop = HERE.parent / "report" / "crop_profile.py"
(B.P / "progress").mkdir(parents=True, exist_ok=True)
if agent:
    asg = config.read_json(B.W / "locks" / "assignment.json", {}) or {}
    ids = ((asg.get("agents") or {}).get(agent) or {}).get("ids") or []
    base = B.W / "logs" / f"crop-{agent}"
    src, out, sheet = base / "src", base / "out", B.P / "progress" / f"crop-check-{agent}.jpg"
    if src.exists():
        shutil.rmtree(src)
    miss = []
    for i in ids:
        f = B.W / "shots_clean" / i / "01-profile.png"
        if f.exists():
            (src / i).mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, src / i / "01-profile.png")
        else:
            miss.append(i)
    if miss:
        print("没有主页截图的号：", ", ".join(miss))
else:
    ids = config.account_ids(B)
    src, out, sheet = B.W / "shots_clean", B.P, B.P / "progress" / "crop-check.jpg"
r = subprocess.run([sys.executable, str(crop), "--dir", str(src), "--out", str(out), "--mode", "3", "--width", "520", "--sheet", str(sheet)])
print(f"对照图：{sheet}（应有 {len(ids)} 张；少了的是检测失败的号，看上面的报错）")
if B.url:
    print("预览：", B.link(f"progress/{sheet.name}"))
sys.exit(r.returncode)
