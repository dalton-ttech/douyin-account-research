"""批次配置与环境变量的公共读取模块。

所有脚本都通过这里拿路径、账号清单和批次数据，不在脚本里写死本机路径或账号。

配置来源（优先级从高到低）：
  1. 环境变量 DY_WORK_DIR、DY_PREVIEW_DIR、DY_PREVIEW_URL、DY_REPORT_MODE
  2. 命令行 --config <batch.json>，或环境变量 DY_BATCH_CONFIG 指向的批次配置
  3. 本模块里的默认值

批次配置里的相对路径，按配置文件所在目录解析；listing、qual 等工作目录内文件的相对路径，按 work_dir 解析。
密钥只从环境变量读：REDFOX_API_KEY。
"""
import json
import os
import re
import shutil
import sys
import datetime as dt
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
ENV_CONFIG = "DY_BATCH_CONFIG"
MODES = ("simple", "full")

DEFAULTS = {
    "batch": "batch",
    "work_dir": ".",
    "preview_dir": "preview",
    "preview_url": "",
    "listing": "listing/filtered.json",
    "accounts": None,
    "qual": "qual.json",
    "mode": "simple",
    "title": "{n} 个待购抖音号：粉丝质量调研报告",
    "cover_title": "抖音账号粉丝质量调研报告",
    "cover_subtitle": "{n} 个待收购账号",
    "cover_sources": "抖音网页公开数据采集、巨量星图、红狐数据",
    "date": None,
    "analysis_time": None,
    "collect_time": "",
    "data_sources": "抖音网页端只读采集、红狐 API、巨量星图",
    "short_names": {},
    "redfox_budget": 200,
    "edge": None,
}


def _pop_config_arg(argv):
    """从 argv 里取出 --config X / --config=X，并把它从 argv 中删除，避免干扰脚本自己的位置参数。"""
    for i, a in enumerate(list(argv)):
        if a == "--config" and i + 1 < len(argv):
            val = argv[i + 1]
            del argv[i:i + 2]
            return val
        if a.startswith("--config="):
            del argv[i]
            return a.split("=", 1)[1]
    return None


class Batch:
    """一次调研批次的配置。属性：name、W（工作目录）、P（预览目录）、url、mode、date 等。"""

    def __init__(self, data, config_path=None):
        self.raw = dict(DEFAULTS)
        self.raw.update({k: v for k, v in (data or {}).items() if not k.startswith("_")})
        self.config_path = Path(config_path).resolve() if config_path else None
        base = self.config_path.parent if self.config_path else Path.cwd()
        r = self.raw
        self.name = str(r["batch"])
        self.W = self._path(os.environ.get("DY_WORK_DIR") or r["work_dir"], base)
        self.P = self._path(os.environ.get("DY_PREVIEW_DIR") or r["preview_dir"], base)
        self.url = (os.environ.get("DY_PREVIEW_URL") or r.get("preview_url") or "").rstrip("/")
        self.mode = (os.environ.get("DY_REPORT_MODE") or r.get("mode") or "simple").lower()
        if self.mode not in MODES:
            raise SystemExit(f"mode 只能是 simple 或 full，当前是 {self.mode!r}")
        self.date = str(r.get("date") or dt.date.today().isoformat())
        self.today = dt.date.fromisoformat(self.date)
        at = r.get("analysis_time") or f"{self.date} 12:00"
        self.analysis_time = dt.datetime.strptime(at, "%Y-%m-%d %H:%M")
        self.collect_time = r.get("collect_time") or ""
        self.data_sources = r.get("data_sources") or DEFAULTS["data_sources"]
        self.short_names = dict(r.get("short_names") or {})
        self.parts = self.W / "parts"

    @staticmethod
    def _path(p, base):
        p = Path(os.path.expandvars(os.path.expanduser(str(p))))
        return (p if p.is_absolute() else (base / p)).resolve()

    def wpath(self, rel):
        p = Path(rel)
        return p if p.is_absolute() else self.W / p

    def get(self, key, default=None):
        return self.raw.get(key, default)

    def text(self, key, **kw):
        """取配置里的文字模板，并替换 {n}、{date}、{batch} 等占位符。"""
        s = self.raw.get(key) or DEFAULTS.get(key) or ""
        kw.setdefault("date", self.date)
        kw.setdefault("batch", self.name)
        try:
            return s.format(**kw)
        except (KeyError, IndexError):
            return s

    def link(self, rel):
        """预览目录里文件的访问地址：有 preview_url 时给 http 链接，否则给本地 file:// 链接。"""
        rel = str(rel).replace("\\", "/").lstrip("/")
        return f"{self.url}/{rel}" if self.url else (self.P / rel).as_uri()

    def __repr__(self):
        return f"Batch({self.name!r}, W={self.W}, P={self.P}, mode={self.mode})"


_CACHE = {}


def load(path=None, argv=None):
    """读取批次配置。path 为空时依次看 --config 参数、环境变量 DY_BATCH_CONFIG。"""
    argv = sys.argv if argv is None else argv
    path = path or _pop_config_arg(argv) or os.environ.get(ENV_CONFIG)
    key = str(Path(path).resolve()) if path else "<env>"
    if key in _CACHE:
        return _CACHE[key]
    data = {}
    if path:
        p = Path(path)
        if not p.exists():
            raise SystemExit(f"找不到批次配置文件：{p}")
        data = json.loads(p.read_text(encoding="utf-8-sig"))
        os.environ[ENV_CONFIG] = key
    elif not os.environ.get("DY_WORK_DIR"):
        raise SystemExit("缺少批次配置：请加 --config <batch.json>，或设置环境变量 DY_BATCH_CONFIG / DY_WORK_DIR")
    b = Batch(data, path)
    _CACHE[key] = b
    return b


# ---------- 账号清单 ----------
_LINE_SPLIT = re.compile(r"-{3,}")
_FANS = re.compile(r"([\d.]+)\s*(万|w|W)?\s*粉")


def parse_line(line):
    """解析挂牌行：抖音:12345678901---4.6万粉丝---亲子号-----未认证60中间女粉---三无（中间可以夹昵称）。"""
    segs = [s.strip() for s in _LINE_SPLIT.split(line or "") if s.strip()]
    out = {}
    if segs and re.match(r"^抖音[:：]", segs[0]):
        out["id"] = re.sub(r"^抖音[:：]\s*", "", segs[0])
        segs = segs[1:]
    for i, s in enumerate(segs):
        m = _FANS.search(s)
        if m:
            v = float(m.group(1))
            out["listing_fans"] = int(round(v * 10000 if m.group(2) else v))
            if i == 1:
                out["nickname"] = segs[0]
            rest = segs[i + 1:]
            for k, v2 in zip(("category", "portrait", "status"), rest):
                out[k] = v2
            if len(rest) > 3:
                out["note"] = "；".join(rest[3:])
            break
    return out


def _norm_row(r):
    if isinstance(r, str):
        r = {"id": r}
    r = dict(r)
    aid = r.get("id") or r.get("抖音号") or r.get("douyin_id") or r.get("unique_id")
    parsed = parse_line(r.get("line") or r.get("挂牌行") or r.get("挂牌行原文") or "")
    row = {
        "id": str(aid or parsed.get("id") or "").strip(),
        "nickname": r.get("nickname") or r.get("昵称") or parsed.get("nickname"),
        "listing_fans": r.get("listing_fans") or r.get("挂牌粉丝") or r.get("挂牌粉丝数") or parsed.get("listing_fans"),
        "category": r.get("category") or r.get("类型") or parsed.get("category") or "",
        "portrait": r.get("portrait") or r.get("画像") or r.get("认证与画像") or parsed.get("portrait") or "",
        "status": r.get("status") or r.get("状态") or parsed.get("status") or "",
        "line": r.get("line") or r.get("挂牌行") or r.get("挂牌行原文") or "",
        "short": r.get("short"),
        "include": r.get("include", True) is not False,
    }
    lf = row["listing_fans"]
    if isinstance(lf, str):
        m = _FANS.search(lf + "粉") or re.search(r"([\d.]+)", lf)
        lf = float(m.group(1)) * (10000 if ("万" in lf or "w" in lf.lower()) else 1) if m else None
    row["listing_fans"] = int(round(lf)) if lf else None
    return row


def listing_rows(batch=None, include_all=False):
    """返回账号清单（有序）。来源：batch.json 里的 accounts 列表，或 work_dir 下的 listing/filtered.json。"""
    b = batch or load()
    src = b.get("accounts")
    if not src:
        p = b.wpath(b.get("listing") or DEFAULTS["listing"])
        if not p.exists():
            raise SystemExit(f"找不到账号清单：{p}（batch.json 里的 listing 或 accounts）")
        d = json.loads(p.read_text(encoding="utf-8-sig"))
        src = d if isinstance(d, list) else (d.get("queue") or d.get("rows") or d.get("accounts") or [])
    rows = [_norm_row(r) for r in src]
    rows = [r for r in rows if r["id"]]
    return rows if include_all else [r for r in rows if r["include"]]


def account_ids(batch=None):
    return [r["id"] for r in listing_rows(batch)]


# ---------- 批次数据 ----------
def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def load_qual(batch=None):
    """读 qual.json：{"accounts": {id: {content, content_ok, portrait, portrait_ok, brush, risks, summary}}, "notes": {...}}。
    也接受不带 accounts 外层的旧格式 {id: {...}}。"""
    b = batch or load()
    d = read_json(b.wpath(b.get("qual") or DEFAULTS["qual"]), {}) or {}
    if "accounts" in d and isinstance(d["accounts"], dict):
        return d["accounts"], d.get("notes") or {}
    return {k: v for k, v in d.items() if isinstance(v, dict) and k != "notes"}, d.get("notes") or {}


# ---------- 环境 ----------
def redfox_key():
    key = os.environ.get("REDFOX_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "缺少环境变量 REDFOX_API_KEY。\n"
            "请先在本机设置（不要写进任何文件）：\n"
            "  PowerShell：$env:REDFOX_API_KEY = '<你的密钥>'（当前窗口有效）\n"
            "  或：[Environment]::SetEnvironmentVariable('REDFOX_API_KEY', '<你的密钥>', 'User')（之后新开的窗口有效）")
    return key


EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/microsoft-edge",
]


def edge_path(batch=None):
    """Edge 可执行文件：环境变量 EDGE_PATH > batch.json 的 edge > 常见安装位置 > PATH。找不到返回 None。"""
    cands = [os.environ.get("EDGE_PATH")]
    try:
        cands.append((batch or load()).get("edge"))
    except SystemExit:
        pass
    cands += EDGE_CANDIDATES + [shutil.which("msedge"), shutil.which("microsoft-edge")]
    return next((c for c in cands if c and os.path.exists(c)), None)


def launch_browser(p, **kw):
    """Playwright：优先用本机 Edge（msedge 通道），没有就退回 Playwright 自带的 Chromium。"""
    try:
        return p.chromium.launch(channel="msedge", headless=True, **kw)
    except Exception:
        return p.chromium.launch(headless=True, **kw)


def setup_stdout():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


if __name__ == "__main__":
    setup_stdout()
    b = load()
    print(b)
    for r in listing_rows(b, include_all=True):
        print(r)
