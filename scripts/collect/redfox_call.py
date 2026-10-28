"""红狐数据接口调用（WORKFLOW 6.10 节）。密钥只从环境变量 REDFOX_API_KEY 读，不写进任何文件、日志或输出。

每次调用：原始返回存 <WORK_DIR>/redfox_raw/<时间>-<tag>.json，调用记录追加到 <WORK_DIR>/redfox_usage.json。
接口不返回扣费信息：成功（code 2000）的调用按 est_cost 估算累计积分；3203（库里没有）不扣积分。
积分上限取 batch.json 的 redfox_budget（默认 200），预留 redfox_reserve（默认 20）。

单独调用：python scripts/collect/redfox_call.py --config <batch.json> <接口路径> '<json 参数>' <tag> [估算积分]
"""
import datetime as dt, json, os, sys, time, urllib.error, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config

BASE = "https://redfox.hk"
OK, NOT_FOUND = 2000, 3203


def _paths():
    B = config.load()
    return B, B.W / "redfox_usage.json", B.W / "redfox_raw"


def load_usage():
    B, usage_p, _ = _paths()
    u = config.read_json(usage_p) or {"calls": []}
    u["budget"] = int(B.get("redfox_budget") or 200)
    u["reserve"] = int(B.get("redfox_reserve") or 20)
    u.setdefault("calls", [])
    return u


def spent(u):
    return round(sum((c.get("cost") or 0) for c in u["calls"]), 2)


def remaining(u=None):
    u = u or load_usage()
    return u["budget"] - u["reserve"] - spent(u)


def call(endpoint, payload, tag, est_cost=1.0):
    key = config.redfox_key()
    B, usage_p, raw_dir = _paths()
    usage = load_usage()
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + endpoint, data=body, method="POST",
                                 headers={"Content-Type": "application/json", "X-API-KEY": key, "User-Agent": "douyin-account-research/1.0"})
    t0 = time.time()
    status, hdrs, text = None, {}, ""
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status, hdrs, text = r.status, dict(r.headers), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        status, hdrs, text = e.code, dict(e.headers), e.read().decode("utf-8", "replace")
    except Exception as e:
        text = json.dumps({"error": str(e)}, ensure_ascii=False)
    text = text.replace(key, "***")
    raw_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    rawf = raw_dir / f"{stamp}-{tag}.json"
    rawf.write_text(text, encoding="utf-8")
    try:
        j = json.loads(text)
    except Exception:
        j = {}
    code = j.get("code")
    rec = {"time": dt.datetime.now().isoformat(timespec="seconds"), "endpoint": endpoint, "tag": tag, "payload": payload,
           "http": status, "code": code, "msg": (j.get("msg") or "")[:120], "elapsed_s": round(time.time() - t0, 2), "raw": rawf.name,
           "headers_cost_like": {k: v for k, v in hdrs.items() if any(s in k.lower() for s in ("cost", "point", "credit", "balance", "quota", "remain"))},
           "cost": est_cost if code == OK else 0}
    usage["calls"].append(rec)
    usage["cumulative_cost"] = spent(usage)
    usage_p.write_text(json.dumps(usage, ensure_ascii=False, indent=1), encoding="utf-8")
    return j, rec


if __name__ == "__main__":
    config.setup_stdout()
    config.load()
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    ep, payload, tag = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]
    est = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
    j, rec = call(ep, payload, tag, est)
    print(json.dumps({k: v for k, v in rec.items() if k != "payload"}, ensure_ascii=False))
    d = j.get("data")
    print("top keys:", list(j.keys()), "data type:", type(d).__name__)
    if isinstance(d, list) and d:
        print("item keys:", list(d[0].keys()))
    elif isinstance(d, dict):
        print("data keys:", list(d.keys()))
