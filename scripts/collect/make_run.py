"""生成采集代理的轮次脚本和后台启动脚本（ego 脚本拿不到环境变量，参数直接写进生成的 .mjs）。

用法：
  python scripts/collect/make_run.py --config <batch.json> --agent dy-A [--round 01] [--steps resolve,posts,comments,fans,shots,assets]
      [--ids 号1,号2] [--force-ids 号] [--pace req=3000,account=20000] [--handoff]

  --agent    dy-A / dy-B（抖音）或 xt-A / xt-B（星图）；号码默认取 locks/assignment.json 里该代理的 ids
  --round    轮次编号，默认自动取下一个
  --steps    抖音默认全部步骤；星图固定 xingtu
  --force-ids  这些号即使已有产出也重抓
  --handoff  模式 A 的最后一轮：结束时关掉自己开的页并把窗口交还用户（不会调用 finish）

产出（都在 <WORK_DIR> 下）：
  dyA-01.mjs        轮次脚本：import scripts/collect/run_agent.mjs 并传入参数
  run-dyA-01.cmd    后台启动脚本，输出追加到 logs/dy-A-01.log
启动：Start-Process -FilePath "<WORK_DIR>\\run-dyA-01.cmd" -WindowStyle Hidden
进度：<WORK_DIR>/logs/dy-A-progress.log（每号一行）；锁文件 <WORK_DIR>/locks/dy-A.json（心跳、done 清单）
"""
import argparse, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("--agent", required=True)
ap.add_argument("--round")
ap.add_argument("--steps")
ap.add_argument("--ids")
ap.add_argument("--force-ids", default="")
ap.add_argument("--pace", default="")
ap.add_argument("--handoff", action="store_true")
a = ap.parse_args()

m = re.fullmatch(r"(dy|xt)-([A-Za-z0-9]+)", a.agent)
if not m:
    raise SystemExit("--agent 应为 dy-A、dy-B、xt-A、xt-B 这类名字")
kind, group = m.groups()
W = B.W
asg = config.read_json(W / "locks" / "assignment.json", {}) or {}
me = (asg.get("agents") or {}).get(a.agent) or {}
ids = [s.strip() for s in a.ids.split(",") if s.strip()] if a.ids else list(me.get("ids") or [])
if not ids:
    raise SystemExit(f"没有号码：先运行 make_assignment.py，或用 --ids 指定")
if not me:
    print(f"提示：assignment.json 里没有 {a.agent}，将按模式 B 用 space 名 {B.name}-{a.agent} 新建 space（未指定 profile）")
steps = [s.strip() for s in a.steps.split(",")] if a.steps else (["xingtu"] if kind == "xt" else ["resolve", "posts", "comments", "fans", "shots", "assets"])
known = {"dy": {"resolve", "posts", "comments", "fans", "shots", "assets"}, "xt": {"xingtu"}}[kind]
bad = [s for s in steps if s not in known]
if bad:
    raise SystemExit(f"未知步骤 {bad}，可选：{sorted(known)}")
pace = {}
for kv in filter(None, a.pace.split(",")):
    k, v = kv.split("=", 1)
    pace[k.strip()] = int(v)

stem = f"{kind}{group}"
if a.round:
    rnd = a.round.zfill(2)
else:
    nums = [int(x.stem.split("-")[-1]) for x in W.glob(f"{stem}-*.mjs") if x.stem.split("-")[-1].isdigit()]
    rnd = f"{(max(nums) + 1) if nums else 1:02d}"
run = {
    "W": W.as_posix(), "P": B.P.as_posix(), "agent": a.agent, "kind": kind, "ids": ids, "steps": steps,
    "force": [s.strip() for s in a.force_ids.split(",") if s.strip()], "pace": pace, "handoff": a.handoff,
    "space": me.get("space") or f"{B.name}-{a.agent}", "space_id": me.get("space_id"), "profile": me.get("profile") if me.get("profile") not in (None, "Profile ?") else None,
    "mode": asg.get("mode") or "B",
}
lib = (HERE / "run_agent.mjs").as_uri()
mjs = W / f"{stem}-{rnd}.mjs"
mjs.write_text(
    f"// 由 make_run.py 生成：{a.agent} 第 {rnd} 轮。要改参数请重新生成，不要手改共享库。\n"
    f"const {{ runAgent }} = await import({json.dumps(lib)});\n"
    f"await runAgent({json.dumps(run, ensure_ascii=False, indent=1)});\n",
    encoding="utf-8",
)
log = f"logs\\{a.agent}-{rnd}.log"
cmd = W / f"run-{stem}-{rnd}.cmd"
cmd.write_text(
    "\r\n".join([
        "@echo off",
        "chcp 65001 >nul",
        f'cd /d "{W}"',
        "if not exist logs mkdir logs",
        f"echo BEGIN %date% %time% >> {log}",
        f"ego-browser nodejs -e \"await import('{mjs.as_uri()}')\" >> {log} 2>&1",
        f"echo END %date% %time% exit=%errorlevel% >> {log}",
        "",
    ]),
    encoding="utf-8",
)
print(f"轮次脚本：{mjs}")
print(f"启动脚本：{cmd}")
print(f"号码 {len(ids)} 个：{', '.join(ids)}；步骤：{', '.join(steps)}")
print("后台启动（PowerShell）：")
print(f'  Start-Process -FilePath "{cmd}" -WindowStyle Hidden')
print(f"前台运行：ego-browser nodejs -e \"await import('{mjs.as_uri()}')\"")
print(f"进度日志：{W / 'logs' / (a.agent + '-progress.log')}；锁文件：{W / 'locks' / (a.agent + '.json')}")
