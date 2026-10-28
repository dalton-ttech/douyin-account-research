# scripts 使用说明

一批待购抖音号的调研分三段：**浏览器采集**（抖音、巨量星图）→ **数据接口与分析**（红狐、作品/粉丝/评论指标、评级）→ **生成报告**（简约模式手机版、完整模式 A4 版）。

所有脚本都通过 `--config <batch.json>` 拿路径和账号清单，脚本里不写死本机路径、账号或密钥。

## 环境

- Python 3.10+：`pip install -r requirements.txt`
- Microsoft Edge：A4 PDF 用 Edge 无头打印；手机 PDF 和截图用 Playwright 的 `msedge` 通道。没有 Edge 时会退回 Playwright 自带的 Chromium，需要先运行 `playwright install chromium`。
- 采集脚本（`scripts/collect/*.mjs`）在 ego-browser 的 Node 环境里运行（`ego-browser nodejs`），需要已经登录抖音网页版和巨量星图的浏览器窗口。
- 红狐密钥只从环境变量读取，不要写进任何文件，也不要贴进聊天。用隐藏输入设成用户级环境变量（密钥不会出现在屏幕和命令历史里）：

  ```powershell
  $s = Read-Host -AsSecureString '红狐密钥'
  [Environment]::SetEnvironmentVariable('REDFOX_API_KEY', [Net.NetworkCredential]::new('', $s).Password, 'User')
  ```

  新开的窗口会带上这个变量。已经开着的窗口（包括设置之前启动的终端和编辑器）不用重开，运行脚本前先刷新当前进程的值（不会打印密钥）：

  ```powershell
  $env:REDFOX_API_KEY = [Environment]::GetEnvironmentVariable('REDFOX_API_KEY', 'User')
  ```

- 中文字体：生成占位图时依次尝试微软雅黑、黑体、苹方、Noto Sans CJK。

## 批次配置

复制 `config/batch.example.json` 为 `config/<批次名>.json`（`config/` 下除示例外的 json 不会提交），或放在仓库外任意位置。字段说明见示例文件里以 `_` 开头的注释键。

- `work_dir`：采集数据和中间结果；`preview_dir`：报告、截图、PDF。都建议放在仓库外、空间充足的磁盘上。
- 账号清单：`listing`（工作目录里的挂牌清单）或 `accounts`（直接列在配置里）。挂牌行格式：`抖音:<抖音号>---<昵称>---4.6万粉丝---亲子号-----未认证60中间女粉---三无`，昵称可省略。
- `mode`：`simple`（默认）或 `full`，命令行 `--mode` 可覆盖。
- `listing_filter`：挂牌筛选的剔除词表（类型关键词、例外、近似类型、女粉下限），给筛选代理用，脚本不读。
- 环境变量优先于配置：`DY_BATCH_CONFIG`（配置路径）、`DY_WORK_DIR`、`DY_PREVIEW_DIR`、`DY_PREVIEW_URL`、`DY_REPORT_MODE`、`EDGE_PATH`。

## 目录约定

```text
<work_dir>/
  listing/filtered.json        挂牌清单（[{id, line}, ...]）；号多时另有 groups.json（每组 10 个号）
  qual.json                    定性判断（人工填写，格式见下文）
  locks/                       assignment.json（代理分组）、<代理>.json（心跳、已完成）、PAUSE-douyin.flag（暂停开关）、checkpoints.json（每组验收记录）
  accounts_<代理>.json         抖音号 → sec_uid 解析结果；合并后为 accounts.json
  data_final/<id>/             profile.json、posts.json、comments2.json、fans_sample.json、profile_xhr.json
  shots_clean/<id>/            01-profile.png、02-fans.png、03-top-<作品ID>.png、04-recent-<作品ID>.png、res.json
  assets_work/<id>/            总览素材原图（头像、两张封面、meta.json）
  xingtu_data/<id>.json        星图搜索与达人数据
  shots_mine/xingtu/<id>/      星图截图（生成报告前抹掉水印）
  shots_mine/xingtu_raw/<id>/  带水印的星图原图备份（只留工作目录）
  redfox_data.json             红狐账号诊断与作品库；redfox_usage.json 调用记录；redfox_raw/ 原始返回（已去掉密钥）
  analysis_posts.json  fans_analysis.json  comments_analysis.json  coverage.csv
  parts/                       报告片段（总览表、图表、卡片详情、assets_manifest.json）
  logs/                        各代理日志与进度
<preview_dir>/
  report.html  report.pdf              简约模式（手机 HTML + 390×844 手机 PDF）
  report-full.html  report-a4.pdf      完整模式（桌面 HTML + A4 PDF）
  overview-assets/<id>/                总览头像与封面
  <id>/                                报告引用的截图（裁剪、打码后的 JPEG）
  progress/                            检查用的缩略图、裁剪对照图、分段截图
```

## 完整流程

### 1. 采集（浏览器）

采集要在有人值守时进行：遇到验证码或登录失效，脚本会写 `locks/PAUSE-douyin.flag` 并停下，由人处理后删掉该文件再续跑。已完成的号和已有产出会自动跳过。

```powershell
$cfg = 'config\batch-001.json'
# 1) 分组：单双号分给 dy-A/dy-B（抖音）和 xt-A/xt-B（星图）
python scripts/collect/make_assignment.py --config $cfg --mode B --profile dy-A=<profile id> --profile dy-B=<profile id> --profile xt-A=<profile id> --profile xt-B=<profile id>
# 2) 为每个代理生成一轮脚本并在后台启动（各代理可并行）
python scripts/collect/make_run.py --config $cfg --agent dy-A
Start-Process -FilePath "<work_dir>\run-dyA-01.cmd" -WindowStyle Hidden
python scripts/collect/make_run.py --config $cfg --agent xt-A
Start-Process -FilePath "<work_dir>\run-xtA-01.cmd" -WindowStyle Hidden
#    进度：<work_dir>\logs\dy-A-progress.log；中断后再运行 make_run.py 会生成下一轮并续跑
# 3) 抖音代理完成后：主页截图裁剪验收、总览素材转 JPEG
python scripts/collect/crop_check.py --config $cfg --agent dy-A
python scripts/collect/assets_finalize.py --config $cfg --agent dy-A
# 4) 红狐（需要 REDFOX_API_KEY）
python scripts/collect/redfox_batch.py --config $cfg
# 5) 合并各代理产出，核对每号必做项
python scripts/analyze/merge_collect.py --config $cfg
python scripts/analyze/check_coverage.py --config $cfg
# 6) 星图截图抹水印（生成报告前；--check 出放大检查图）
python scripts/report/xt_dewatermark.py --config $cfg --check
```

星图页面铺满登录账号名的平铺水印，顶部还有登录名。`xt_collect.mjs` 采集时保留原图；`xt_dewatermark.py` 把带水印的原图备份到 `shots_mine/xingtu_raw/`，再把抹掉水印的图写回 `shots_mine/xingtu/`；生成报告时 `report_data.py` 再裁掉顶部 92 像素。顶部只能裁一次：如果截图在采集时已经裁过，抹水印时加 `--precropped`。

### 2. 定性判断 `qual.json`

放在工作目录下（或 batch.json 的 `qual` 指定的位置）。报告里不出现人名、接口名、状态码、字段名和弹窗原文，写结论时请用业务语言。

```json
{
  "accounts": {
    "<抖音号>": {
      "content": "亲子日常，与挂牌一致", "content_ok": true,
      "portrait": "星图女粉 62%，与挂牌相符", "portrait_ok": true,
      "brush": null,
      "risks": ["断更 82 天", "单条爆款依赖"],
      "summary": "一句话结论",
      "evidence_note": "（可选）补在“获赞最高作品”截图说明后面"
    }
  },
  "notes": {
    "headline": "（可选）封面和结论第一句；不填按评级自动生成",
    "grade_notes": {"C": "（可选）覆盖某个等级的默认说明"},
    "xingtu": "（可选）接在“巨量星图里有 N 个号入驻”后面",
    "verdict": ["（可选）结论部分追加的段落"],
    "third_party": "（可选）方法说明里的第三方平台情况",
    "cross": ["（可选）交叉核对结论"]
  }
}
```

`content_ok`、`portrait_ok`：`true` 相符、`false` 不符、`null` 无法核实。`brush`：发现刷量证据时填一句说明，会直接判 D。

### 3. 生成报告

```powershell
python scripts/build_report.py --config $cfg                      # 简约模式（默认）：report.html + report.pdf
python scripts/build_report.py --config $cfg --mode full          # 完整模式：report-full.html + report-a4.pdf
python scripts/build_report.py --config $cfg --mode both --check  # 两种都出，并做版面检查
```

选项：`--skip-analyze` 跳过三个分析脚本；`--no-pdf` 只出 HTML；`--check` 额外生成主页裁剪对照图、逐号页数检查、PDF 缩略总览（列出填充不足 60% 的页）、手机宽度横向溢出检查。

`build_report.py` 依次运行下列脚本，任何一步失败即停。需要单独重跑某一步时，可以按同样的顺序手动执行：

| 顺序 | 脚本 | 简约 | 完整 |
|---|---|---|---|
| 1 | `analyze/analyze_posts.py`、`analyze_fans.py`、`analyze_comments.py` | ✓ | ✓ |
| 2 | `report/build_full.py --no-merge`（第一遍，生成报告骨架） | ✓ | ✓ |
| 3 | `report/build_overview_table.py`、`build_charts.py`、`build_charts_m.py` | ✓ | ✓ |
| 4 | `report/build_full.py`（第二遍，合并总览表和图表 → report-full.html） | ✓ | ✓ |
| 5 | `report/build_pdf.py`（→ report-a4.pdf） | | ✓ |
| 6 | `report/mobile.py`（→ report.html） | ✓ | |
| 7 | `report/build_detail_m.py`、`merge_detail.py`（卡片式分账号详情） | ✓ | |
| 8 | `report/build_pdf_m.py`（→ report.pdf） | ✓ | |

## 脚本一览

### 入口与配置

- `build_report.py`：报告总入口，见上文。
- `config.py`：批次配置、账号清单、qual.json 的公共读取；`REDFOX_API_KEY` 缺失时给出设置方法；查找 Edge。`python scripts/config.py --config <batch.json>` 可打印解析后的配置和账号清单。

### collect/ 采集

| 脚本 | 作用 | 产出 |
|---|---|---|
| `make_assignment.py` | 分组：`--mode A`（认领已建好的窗口，配 `--space-id`）或 `B`（在指定 profile 下新建）；`--groups 1` 时全部分给 dy-A/xt-A | `locks/assignment.json` |
| `make_run.py` | 生成一轮采集脚本和后台启动 `.cmd`；`--steps`、`--ids`、`--force-ids`、`--pace req=3000,account=20000`、`--handoff` | `<代理>-NN.mjs`、`run-<代理>-NN.cmd` |
| `run_agent.mjs` | 通用执行器：进入窗口、写心跳、按号执行各步骤、遇验证码暂停 | `logs/<代理>-progress.log` |
| `dy_resolve.mjs` | 抖音号 → sec_uid（综合搜索） | `accounts_<代理>.json` |
| `dy_profile_posts.mjs` | 主页信息与作品列表 | `data_final/<id>/profile.json`、`posts.json` |
| `dy_comments.mjs` | 最近 3 条 + 点赞最高 2 条作品的评论 | `comments2.json` |
| `dy_fans.mjs` | 粉丝列表抽样（最近、爆款期、4 个时间探针）和约 12 个粉丝主页 | `fans_sample.json` |
| `dy_shots.mjs` | 主页、粉丝列表、两条作品的截图（打码） | `shots_clean/<id>/` |
| `dy_assets.mjs` | 总览用头像和两张封面原图 | `assets_work/<id>/` |
| `xt_collect.mjs` | 星图按抖音号搜索、核对是否本号、取达人数据并截图 | `xingtu_data/<id>.json`、`shots_mine/xingtu/<id>/` |
| `lib/common.mjs`、`lib/hook.mjs` | 公共工具（锁、心跳、暂停、同源请求）和抓包钩子 | |
| `crop_check.py` | 主页截图裁剪验收（`--agent` 只看该代理的号） | `<preview_dir>/progress/crop-check*.jpg` |
| `assets_finalize.py` | 素材原图转 JPEG，缺图用占位图 | `overview-assets/<id>/`、`parts/assets/<id>.json` |
| `redfox_batch.py` | 红狐账号诊断（批量）+ 作品库（每号一次），带预算控制 | `redfox_data.json` |
| `redfox_call.py` | 单次红狐调用，记录用量，原始返回去掉密钥后存档 | `redfox_usage.json`、`redfox_raw/` |

### analyze/ 分析

| 脚本 | 作用 | 输入 → 输出 |
|---|---|---|
| `merge_collect.py` | 合并各代理产出 | `accounts_*.json` → `accounts.json`；`parts/assets/*.json` → `parts/assets_manifest.json` |
| `check_coverage.py` | 每号 8 项必做调研核对 | → `coverage.csv` |
| `analyze_posts.py` | 粉丝、掉粉、近 30 条互动率、断更、爆款依赖等 | `profile.json`、`posts.json` → `analysis_posts.json` |
| `analyze_fans.py` | 粉丝抽样：疑似僵尸/空壳、0 作品、画像 | `fans_sample.json` → `fans_analysis.json` |
| `analyze_comments.py` | 评论区：纯表情、乱码、IP 分布、重复评论 | `comments2.json` → `comments_analysis.json` |
| `rating.py` | 分层基准、评级规则（`rate()`）、评级标准表（`STD_ROWS`），供报告引用 | |

分析脚本都可以在末尾加抖音号只跑部分号，例如 `python scripts/analyze/analyze_posts.py --config $cfg 号1 号2`。

### report/ 报告

| 脚本 | 作用 | 输出 |
|---|---|---|
| `report_data.py` | 两种模式共用的数据层（读分析结果、星图、红狐、截图；星图图裁顶部 92 像素） | |
| `xt_dewatermark.py` | 星图截图抹水印：整批 `--config $cfg [--check] [--precropped]`，或单张 `xt_dewatermark.py SRC DST` | `shots_mine/xingtu/`（原图备份在 `xingtu_raw/`）；`progress/xt-dewm-check.jpg` |
| `build_full.py` | 完整版报告；`--no-merge` 只生成骨架 | `report-full.html` |
| `build_overview_table.py` | 总览 8 列宽表 | `parts/overview_table.html` |
| `build_charts.py` / `build_charts_m.py` | 桌面版 / 手机版图表 | `parts/charts/`、`parts/charts_m/` |
| `merge_parts.py` | 把总览表、图表合并进完整版（`build_full.py` 自动调用） | |
| `build_pdf.py` | A4 PDF：封面、可点击目录、总览横向页；`--no-pages` 跳过目录页码 | `report-a4.pdf` |
| `mobile.py` | 在完整版基础上生成手机优先版 | `report.html` |
| `build_detail_m.py` | 卡片式分账号详情（每号不超过 2 页手机 PDF） | `parts/detail_m/acct_<id>.html` |
| `crop_profile.py` | 主页截图裁剪成“账号信息 + 第一排作品”，规则见 `CROP_RULE.md` | `<id>/dc-01-home.jpg` |
| `merge_detail.py` | 把卡片详情替换进 `report.html` | |
| `build_pdf_m.py` | 手机 PDF（390×844），总览宽表单独排横屏页 | `report.pdf` |
| `sample_detail.py` | 单号卡片页数检查：`sample_detail.py --config $cfg <抖音号> <tag>` | `<tag>.pdf` 和每页预览图 |

### tools/ 检查与辅助

| 脚本 | 作用 |
|---|---|
| `check_public.py` | 公开前检查，发现问题时以退出码 1 结束（见下文） |
| `pdf_sheet.py` | PDF 缩略总览，并列出填充不足 60% 的页：`pdf_sheet.py --config $cfg report-a4.pdf a4-sheet` |
| `mshot.py` | 按手机宽度分段截图并检查横向溢出：`mshot.py --config $cfg report.html m 390 "#overview" 2` |
| `snap_overview.py` | 总览完整长截图（`progress/overview-full.jpg`） |
| `make_demo_batch.py` | 生成合成示例批次 `examples/demo-batch/` |
| `export_pages.py` | 把 PDF 指定页导出成 JPEG 样张：`export_pages.py report.pdf examples/output simple 1 16-17 --width 780` |

## 公开前检查

```powershell
python scripts/tools/check_public.py        # 扫描 git 会提交的文件（已跟踪 + 未忽略的新文件）
python scripts/tools/check_public.py --all  # 扫描磁盘上的全部文件
```

检查内容：`ak_` 开头的密钥、带用户名的个人路径、邮箱，以及仓库根目录 `.public-denylist.txt` 里列出的词（账号 ID、昵称、人名等，每行一个，`#` 开头为注释）。PDF 会检查正文和元数据，文件名也会检查。`.public-denylist.txt` 已被 `.gitignore` 忽略，只放在本机。

## 示例

```powershell
python scripts/tools/make_demo_batch.py
python scripts/build_report.py --config examples/demo-batch/batch.json --mode both --check
```

示例批次是 3 个合成账号（预期评级 B、D、C），截图都是写着“示例截图”的占位图，不含任何真实账号数据。报告产物在 `examples/demo-batch/preview/`（不提交）。

`examples/output/` 是从示例报告导出的样张：

- `simple-p01.jpg` 手机版首页、`simple-p04.jpg` 横屏总览宽表、`simple-p16.jpg` / `simple-p17.jpg` 示例账号A的两页卡片
- `full-p01.jpg` A4 封面、`full-p03.jpg` 总览横向页、`full-p06.jpg` 示例账号A详情首页、`full-p10.jpg` 佐证截图与结论
- `simple-sample.pdf` 手机 PDF 节选（首页、目录、总览、示例账号A）
