"""写 <WORK_DIR>/locks/assignment.json：把账号清单按排序后的单双号分给 A/B 两组抖音、星图代理（WORKFLOW 5.2、5.3 节）。

用法：
  python scripts/collect/make_assignment.py --config <batch.json> [--mode A|B] [--groups 1|2]
      [--profile dy-A=<profile id>] [--profile xt-A=<profile id>] ... [--space-id dy-A=<space id>] ... [--force]

  --mode A：认领用户已建成 space 的窗口（需要 --space-id）；B（默认）：在指定 profile 下新建代理自己的 space。
  --groups 1：只有一个抖音窗口、一个星图窗口时用，全部号分给 dy-A / xt-A。
  已存在 assignment.json 时默认不覆盖（代理可能正在用），确认后加 --force。
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
ap = argparse.ArgumentParser()
ap.add_argument("--mode", choices=["A", "B"], default="B")
ap.add_argument("--groups", type=int, choices=[1, 2], default=2)
ap.add_argument("--profile", action="append", default=[], help="代理名=profile id，可重复")
ap.add_argument("--space-id", action="append", default=[], help="代理名=space id（模式 A），可重复")
ap.add_argument("--force", action="store_true")
a = ap.parse_args()


def kv(items):
    out = {}
    for s in items:
        if "=" not in s:
            raise SystemExit(f"参数格式应为 代理名=值：{s}")
        k, v = s.split("=", 1)
        out[k.strip()] = v.strip()
    return out


prof, sids = kv(a.profile), kv(a.space_id)
ids = config.account_ids(B)
if not ids:
    raise SystemExit("账号清单为空")
groups = {"A": ids[0::2], "B": ids[1::2]} if a.groups == 2 else {"A": ids}
agents = {}
for g, gids in groups.items():
    for kind in ("dy", "xt"):
        name = f"{kind}-{g}"
        agents[name] = {"space": f"{B.name}-{name}", "space_id": sids.get(name), "profile": prof.get(name, "Profile ?"), "ids": gids}
if a.mode == "A":
    miss = [n for n in agents if not agents[n]["space_id"]]
    if miss:
        raise SystemExit(f"模式 A 需要每个代理的 --space-id：缺 {miss}")

p = B.W / "locks" / "assignment.json"
if p.exists() and not a.force:
    raise SystemExit(f"{p} 已存在；确认没有代理在用后加 --force 覆盖")
p.parent.mkdir(parents=True, exist_ok=True)
data = {"batch": B.name, "mode": a.mode, "report_mode": B.mode, "agents": agents}
p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"已写 {p}")
for n, v in agents.items():
    print(f"  {n}: space={v['space']} profile={v['profile']} 号 {len(v['ids'])} 个：{', '.join(v['ids'])}")
if any(v["profile"] == "Profile ?" for v in agents.values()):
    print("提示：还有代理没填 profile（--profile 代理名=<id>），模式 B 下要先问用户每个窗口是哪个 profile")
