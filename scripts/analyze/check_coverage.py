"""每号 8 项必做调研核对：列出每个号缺什么，写 <WORK_DIR>/coverage.csv。

用法：python scripts/analyze/check_coverage.py --config <batch.json>
“拿不到”的例外（粉丝列表隐私、星图未入驻、红狐未收录等）由主代理在 coverage.csv 的“例外说明”列补证据文件名。
"""
import csv, glob, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

config.setup_stdout()
B = config.load()
W = str(B.W)
J = lambda p, d=None: json.load(open(p, encoding="utf-8")) if os.path.exists(p) else d
ids = config.account_ids(B)
ap = J(os.path.join(W, "analysis_posts.json"), {})
fa = J(os.path.join(W, "fans_analysis.json"), {})
ca = J(os.path.join(W, "comments_analysis.json"), {})
rf = J(os.path.join(W, "redfox_data.json"), {})
qual, _notes = config.load_qual(B)
out = []
for i in ids:
    d, s = os.path.join(W, "data_final", i), os.path.join(W, "shots_clean", i)
    fs = J(os.path.join(d, "fans_sample.json"), {})
    res = J(os.path.join(s, "res.json"), {})
    x = J(os.path.join(W, "xingtu_data", f"{i}.json"))
    c = {
        "1主页数据": os.path.exists(os.path.join(d, "profile.json")),
        "2近期作品": bool(J(os.path.join(d, "posts.json"))),
        "3评论区": os.path.exists(os.path.join(d, "comments2.json")) and bool(glob.glob(os.path.join(s, "03-top-*.png"))) and bool(glob.glob(os.path.join(s, "04-recent-*.png"))),
        "4粉丝抽样": (fs.get("blocked") is True or bool(fs.get("pages"))) and os.path.exists(os.path.join(s, "02-fans.png")),
        "5创建时间": bool((ap.get(i) or {}).get("uid_created_est") or (ap.get(i) or {}).get("first_post")),
        "6星图": x is not None and os.path.exists(os.path.join(W, "shots_mine", "xingtu", i, "01-search.png")),
        "7红狐": i in (rf.get("accounts") or {}) and i in (rf.get("works") or {}),
        "8指标评级": i in ap and i in fa and i in ca and i in qual,
        "截图证据": bool(res.get("profileOk")) and all(v.get("ok") for v in res.values() if isinstance(v, dict)),
    }
    miss = [k for k, v in c.items() if not v]
    out.append({"id": i, **{k: "✓" if v else "" for k, v in c.items()}, "缺": "、".join(miss), "例外说明": ""})
    print(i, "齐全" if not miss else "缺：" + "、".join(miss))
with open(os.path.join(W, "coverage.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()) if out else ["id"])
    w.writeheader(); w.writerows(out)
print(len(ids), "个号，", sum(1 for o in out if not o["缺"]), "个齐全")
