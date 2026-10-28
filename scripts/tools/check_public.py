"""公开前检查：扫描仓库里会提交的每个文件，发现敏感内容就报错退出（退出码 1）。

检查项：
  1. 疑似密钥：ak_ 后接 20 位以上十六进制
  2. 个人路径：C:\\Users\\<用户名>、/Users/<用户名>、/home/<用户名>（<用户名>、%USERNAME% 这类占位写法不算）
  3. 邮箱地址（example.com / example.org / example.net 示例域名除外）
  4. 本地拒绝名单 .public-denylist.txt 里的词（账号 ID、昵称、工作目录名、人名等），文件名也查
  另外确认拒绝名单文件本身已被 .gitignore 忽略。

用法：python scripts/tools/check_public.py [--all] [--denylist 路径]
  默认只扫 git 会提交的文件（已跟踪 + 未被忽略的新文件）；--all 扫磁盘上全部文件（.git 除外）。
  文本文件按 UTF-8 读；PDF 额外提取文字和元数据；图片等二进制按原始字节扫（能查到嵌入的元数据）。
拒绝名单每行一个词，# 开头为注释。这个文件只放在本地，不提交。
"""
import argparse, os, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DENY_NAME = ".public-denylist.txt"
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv"}

for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ap = argparse.ArgumentParser()
ap.add_argument("--all", action="store_true", help="扫描磁盘上全部文件，而不只是会提交的文件")
ap.add_argument("--denylist", default=str(REPO / DENY_NAME))
a = ap.parse_args()

SECRET = re.compile(r"ak_[0-9a-fA-F]{20,}")
WINPATH = re.compile(r"[A-Za-z]:(?:\\{1,2}|/)Users(?:\\{1,2}|/)([^\\/\s\"'<>%{}$*`|,;:)\]]+)", re.I)
NIXPATH = re.compile(r"(?<![\w.])/(?:Users|home)/([^/\s\"'<>%{}$*`|,;:)\]]+)")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
OK_USERS = {"public", "default", "all users", "<用户名>", "username", "user", "you", "yourname", "name"}
OK_MAIL = re.compile(r"@(?:[\w-]+\.)*example\.(?:com|org|net)$", re.I)


def load_deny(p):
    p = Path(p)
    if not p.exists():
        print(f"提示：没有找到本地拒绝名单 {p}，只检查通用规则。")
        return []
    words = []
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        w = line.strip()
        if w and not w.startswith("#"):
            words.append(w)
    return words


DENY = load_deny(a.denylist)
DENY_RE = [(w, re.compile((r"(?<![A-Za-z0-9_])" + re.escape(w) + r"(?![A-Za-z0-9_])") if re.fullmatch(r"[\x21-\x7e]+", w) else re.escape(w), re.I)) for w in DENY]


def git_files():
    try:
        out = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             capture_output=True, check=True).stdout
        return [REPO / f for f in out.decode("utf-8").split("\0") if f]
    except Exception:
        return None


def walk():
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            yield Path(root) / f


def mask(s):
    s = str(s)
    return s if len(s) <= 2 else s[:2] + "*" * min(len(s) - 2, 8)


def texts(p):
    """返回 [(来源说明, 文本)]。"""
    raw = p.read_bytes()
    out = []
    try:
        out.append(("", raw.decode("utf-8")))
    except UnicodeDecodeError:
        out.append(("二进制", raw.decode("latin-1")))
        try:
            out.append(("二进制(utf-16)", raw.decode("utf-16", errors="ignore")))
        except Exception:
            pass
    if p.suffix.lower() == ".pdf":
        try:
            import fitz
            doc = fitz.open(str(p))
            out.append(("PDF 元数据", " ".join(str(v) for v in (doc.metadata or {}).values() if v)))
            for i, page in enumerate(doc):
                out.append((f"PDF 第 {i + 1} 页", page.get_text()))
        except Exception as ex:
            print(f"提示：{p.relative_to(REPO)} 无法提取 PDF 文字（{ex}），只按字节检查")
    return out


hits = []


def add(p, where, kind, val, line=None):
    hits.append((str(p.relative_to(REPO)).replace("\\", "/"), where, line, kind, mask(val)))


files = None if a.all else git_files()
mode = "git 会提交的文件" if files is not None else "磁盘上全部文件"
if files is None:
    files = list(walk())
deny_path = Path(a.denylist).resolve()
files = [f for f in files if f.is_file() and f.resolve() != deny_path and not (set(f.relative_to(REPO).parts) & SKIP_DIRS)]

for p in files:
    rel = str(p.relative_to(REPO))
    for w, rx in DENY_RE:
        if rx.search(rel):
            add(p, "文件名", "拒绝名单", w)
    for where, t in texts(p):
        for ln, line in enumerate(t.splitlines(), 1) if not where else [(None, t)]:
            for m in SECRET.finditer(line):
                add(p, where, "疑似密钥", m.group(0), ln)
            for rx in (WINPATH, NIXPATH):
                for m in rx.finditer(line):
                    if m.group(1).lower() not in OK_USERS:
                        add(p, where, "个人路径", m.group(0), ln)
            for m in EMAIL.finditer(line):
                if not OK_MAIL.search(m.group(0)) and not re.search(r"\.(png|jpe?g|gif|webp|svg|js|mjs|py|css)$", m.group(0), re.I):
                    add(p, where, "邮箱", m.group(0), ln)
            for w, rx in DENY_RE:
                if rx.search(line):
                    add(p, where, "拒绝名单", w, ln)

ignored = None
try:
    r = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", DENY_NAME], capture_output=True)
    ignored = r.returncode == 0
except Exception:
    pass

print(f"扫描范围：{mode}，共 {len(files)} 个；拒绝名单 {len(DENY)} 个词")
if ignored is False:
    print(f"错误：{DENY_NAME} 没有被 .gitignore 忽略，会被提交")
seen = set()
for h in hits:
    if h in seen:
        continue
    seen.add(h)
    f, where, ln, kind, val = h
    loc = f + (f":{ln}" if ln else "") + (f"（{where}）" if where else "")
    print(f"  {kind}：{loc}  {val}")
if hits or ignored is False:
    print(f"未通过：{len(seen)} 处问题")
    sys.exit(1)
print("通过：没有发现密钥、个人路径、邮箱或拒绝名单里的词")
