"""红狐批量查询：账号诊断（可批量）+ 作品库（每号 1 次），结果写 <WORK_DIR>/redfox_data.json。

  /story/api/dyUser/queryData          {"accountIds": [...]}：昵称、粉丝、获赞、作品数、IP、性别年龄、省市、crawlTime、相似账号、近 7 天作品
  /story/api/dy/data/listWorkByAccount {"uniqueName": 抖音号, pageSize 50}：作品库收录总数 total、authorSecUid

规则：3203 记“未收录”、不重试；其他失败重试 1 次；redfox_data.json 里已有结果（含未收录）的号跳过，不重复扣积分；
估算积分接近上限（batch.json 的 redfox_budget − redfox_reserve）时停下。

用法：python scripts/collect/redfox_batch.py --config <batch.json> [--est-cost 1] [号1 号2 ...]
不给号码时取账号清单里的全部号。
"""
import json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
from redfox_call import call, load_usage, remaining, OK, NOT_FOUND

config.setup_stdout()
B = config.load()
config.redfox_key()
args = sys.argv[1:]
est = 1.0
if "--est-cost" in args:
    i = args.index("--est-cost")
    est = float(args[i + 1])
    del args[i:i + 2]
IDS = args or config.account_ids(B)
out_p = B.W / "redfox_data.json"
out = config.read_json(out_p) or {"accounts": {}, "works": {}}
out.setdefault("accounts", {})
out.setdefault("works", {})
log_p = B.W / "logs" / "redfox.log"
log_p.parent.mkdir(parents=True, exist_ok=True)


def log(*a):
    s = time.strftime("[%H:%M:%S] ") + " ".join(str(x) for x in a)
    print(s)
    with open(log_p, "a", encoding="utf-8") as f:
        f.write(s + "\n")


def save():
    out_p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


def budget_ok(n=1):
    left = remaining(load_usage())
    if left < est * n:
        log(f"估算积分只剩 {left}，不够本次 {est * n}，停止。需要继续请和用户确认后调高 batch.json 的 redfox_budget")
        return False
    return True


def with_retry(endpoint, payload, tag, cost):
    j, rec = call(endpoint, payload, tag, cost)
    if rec["code"] not in (OK, NOT_FOUND):
        time.sleep(3)
        j, rec = call(endpoint, payload, tag + "-retry", cost)
    return j, rec


# 1) 账号诊断：先批量，没返回的号再逐个查
todo = [i for i in IDS if i not in out["accounts"]]
if todo and budget_ok(len(todo)):
    j, rec = with_retry("/story/api/dyUser/queryData", {"accountIds": todo, "source": "抖音账号诊断-workbuddy"}, f"queryData-batch{len(todo)}", est * len(todo))
    log("queryData 批量", rec["code"], rec["msg"][:40], "返回", len(j.get("data") or []))
    for a in j.get("data") or []:
        out["accounts"][str(a.get("accountId"))] = a
    save()
    for i in [x for x in todo if x not in out["accounts"]]:
        if not budget_ok():
            break
        time.sleep(1)
        j, rec = with_retry("/story/api/dyUser/queryData", {"accountIds": [i], "source": "抖音账号诊断-workbuddy"}, f"queryData-{i}", est)
        data = j.get("data") or []
        log("queryData 单号", i, rec["code"], rec["msg"][:40], "返回", len(data))
        if data:
            out["accounts"][i] = data[0]
        elif rec["code"] in (OK, NOT_FOUND):
            out["accounts"][i] = {"_not_found": True, "code": rec["code"], "msg": rec["msg"]}
        save()

# 2) 作品库（广域库），每号最多 50 条
for i in IDS:
    if i in out["works"]:
        continue
    if not budget_ok():
        break
    time.sleep(1)
    j, rec = with_retry("/story/api/dy/data/listWorkByAccount", {"uniqueName": i, "pageNum": 1, "pageSize": 50, "source": "抖音作品爬取"}, f"listWork-{i}", est)
    d = j.get("data") or {}
    lst = d.get("list") if isinstance(d, dict) else None
    if rec["code"] in (OK, NOT_FOUND):
        out["works"][i] = {"code": rec["code"], "msg": rec["msg"], "total": d.get("total") if isinstance(d, dict) else None, "list": lst or []}
        save()
    log("listWork", i, rec["code"], "未收录" if rec["code"] == NOT_FOUND else "", "total", d.get("total") if isinstance(d, dict) else None, "got", len(lst or []))

u = load_usage()
log(f"估算已用积分 {u.get('cumulative_cost', 0)} / 上限 {u['budget']}（预留 {u['reserve']}）；调用 {len(u['calls'])} 次")
for i in IDS:
    a = out["accounts"].get(i, {})
    w = out["works"].get(i, {})
    if a.get("_not_found"):
        log(i, "账号诊断：未收录")
    else:
        log(i, a.get("nickname"), "粉丝", a.get("followerCount"), "IP", a.get("ipLocation"), "crawlTime", a.get("crawlTime"),
            "作品库", "未收录" if w.get("code") == NOT_FOUND else w.get("total"))
