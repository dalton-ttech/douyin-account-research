"""合并各采集代理的产出：accounts_dy-*.json → accounts.json；parts/assets/*.json → parts/assets_manifest.json。

用法：python scripts/analyze/merge_collect.py --config <batch.json>
同一个号在两个文件里都有时，以 found 为真、字段更多的那份为准，并打印冲突，供人工核对。
"""
import glob, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
W = B.W


def better(a, b):
    if bool(a.get("found")) != bool(b.get("found")):
        return a if a.get("found") else b
    return a if len(a) >= len(b) else b


acc_p = W / "accounts.json"
acc = config.read_json(acc_p, {}) or {}
for f in sorted(glob.glob(str(W / "accounts_*.json"))):
    part = config.read_json(f, {}) or {}
    for k, v in part.items():
        if k in acc and acc[k] != v:
            print("冲突", k, os.path.basename(f), "已按 found/字段数择优")
            v = better(acc[k], v)
        acc[k] = v
    print("合并", os.path.basename(f), len(part), "个号")
acc_p.write_text(json.dumps(acc, ensure_ascii=False, indent=1), encoding="utf-8")

man_p = B.parts / "assets_manifest.json"
man = config.read_json(man_p, {}) or {}
n = 0
for f in sorted(glob.glob(str(B.parts / "assets" / "*.json"))):
    aid = Path(f).stem
    man[aid] = config.read_json(f, {})
    n += 1
if n:
    man_p.parent.mkdir(parents=True, exist_ok=True)
    man_p.write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
ids = config.account_ids(B)
miss_sec = [i for i in ids if not (acc.get(i) or {}).get("sec_uid")]
miss_man = [i for i in ids if i not in man]
print(f"accounts.json：{len(acc)} 个号；缺 sec_uid：{miss_sec or '无'}")
print(f"assets_manifest.json：{len(man)} 个号（本次合并 {n} 个）；缺素材：{miss_man or '无'}")
