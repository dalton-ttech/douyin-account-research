# 验收清单

配合同目录的 `WORKFLOW.md` 使用。主代理收到每个子代理的回复后，按对应小节逐项核对。有一项不过，就打回或自己补，不要带着问题进入下一阶段。

路径占位符的含义见 `WORKFLOW.md` 开头的“路径占位符”一节：`<REPO>` 是仓库根目录（命令都在这里运行），`<BATCH_CONFIG>` 是本批配置文件，`<WORK_DIR>` 是本批工作目录，`<PREVIEW_DIR>` 是本批预览目录，`<PREVIEW_URL>` 是本批预览网址前缀。下文 `$cfg` 指 `<BATCH_CONFIG>`。

---

报告有两种模式，验收时按批次配置的 `mode` 选节：

- **两种模式都要做**：A~H、M~O、Q 节。调研采集项两种模式完全一样，C 节一项都不能少。
- **简约模式**（`simple`，默认）：另做 I、J、K、L 节。
- **复杂模式**（`full`）：另做 I 节中标“两种模式”的项和 P 节。

---

## A. 开工前（主代理）

- [ ] **已问报告模式**（WORKFLOW 1.0 节）：
  - 正文里先给出两种模式的样例链接，每个配一句说明，再用 AskQuestion 提问，问题提示里也写了链接；
  - 用户的选择已写进批次配置的 `mode`（`simple` 或 `full`）；
  - 用户没回答的，按简约模式，并在下次进度汇报里说明。
- [ ] **已用 AskQuestion 分别问了“抖音登录在哪个 profile”“星图登录在哪个 profile”**；盘点推断的结果只作默认选项，用户已确认。
- [ ] 已问清：两个抖音窗口是不是同一个抖音账号；报告节奏（全部做完出一份总报告，还是每组一份）；本批红狐积分上限。
- [ ] 已提醒用户：代理的浏览器窗口不要最小化。
- [ ] 已向所有子代理说明：模式只影响呈现，调研采集项不变。
- [ ] 已实测各盘剩余空间（WORKFLOW 2.4 节的命令）：工作目录（大文件）放在剩余多的盘；低于 2 GB（建议值）的盘不写大文件。不删除任何文件。
- [ ] `<WORK_DIR>` 和 `<PREVIEW_DIR>` 已建好；预览服务在运行：`http://127.0.0.1:8765/` 能打开。
- [ ] 批次配置 `<BATCH_CONFIG>` 已按 `config/batch.example.json` 写好（`batch`、目录、`listing`、`qual`、`mode`、封面文字、`redfox_budget`、`listing_filter`）；`python scripts/config.py --config $cfg` 打印的路径正确。
- [ ] 环境变量 `REDFOX_API_KEY` 存在：`[bool][Environment]::GetEnvironmentVariable('REDFOX_API_KEY','User')` 返回 True。只检查有没有，不打印值。
- [ ] **红狐已试查一个号**：`python scripts/collect/redfox_batch.py --config $cfg <一个号>` 返回成功或“未收录”；返回“积分不足”时已停下请用户核对密钥。
- [ ] 已跑只读盘点（`listTaskSpaces()` 和 `profiles()`），确定是情况 A 还是情况 B（WORKFLOW 5.3 节）。
- [ ] `make_assignment.py` 已写好 `<WORK_DIR>\locks\assignment.json`：4 个代理的 space 名、profile（没有 `Profile ?`）、负责的号；A、B 两组的号不重叠，合起来等于 `filtered.json`。
- [ ] 号多时已写 `listing\groups.json`（WORKFLOW 4.3 节），每组 10 个号，和分配表一致。
- [ ] 没有从旧批次目录复制脚本；所有脚本都在 `<REPO>` 下用 `--config` 运行。

## B. 挂牌筛选

- [ ] 每张图的行高已估算；行高低于约 12 像素的图已请用户补发原图，或已在清单里标明哪些区域读不出来。
- [ ] 转录按图拆给了多个子代理（每张长图或每 100 行左右一个），没有让一个子代理读全部大图。
- [ ] 每个转录子代理都在逐条追加写 `listing\rows_img<图号>.jsonl`，`progress_img<图号>.json` 记录了已完成的横条；中断后是从断点续做，不是从头重读。
- [ ] 各图的 `.jsonl` 行数加起来，等于各图估算的行数（对不上的图要查漏行）。
- [ ] `<WORK_DIR>\listing\all_rows.csv` 有全部转录行，每行都有筛选结论和原因，UTF-8 带 BOM。
- [ ] 每行都有置信度；抖音号有任何一位不确定的是“低”，不确定的位写成 `?`。
- [ ] 置信度低的行都有放大截图在 `<PREVIEW_DIR>\uncertain\`，`list.html` 里有链接。
- [ ] 跨图去重已做，每个号记录了出现在哪几张图；同号写法不一致的进了“待确认”。
- [ ] 筛选规则按 WORKFLOW 1.5 节的顺序执行，剔除词来自批次配置的 `listing_filter`：
  - 已售剔除；
  - 命中 `exceptions` 的单列请用户确认；
  - 类型包含 `exclude_types` 里任一词的剔除，原因写命中的词；
  - 后排男粉、N%男粉剔除；
  - 女粉低于 `min_female_pct`（默认 55%）剔除；
  - 近似类型（`similar`）、边界类型、画像缺失或看不清的单列；
  - 历史批次的号标“已调研”。
- [ ] **用户每次补充剔除词后，都已追加进 `listing_filter` 并对全部挂牌行重新应用全部词**；`筛选清单.md` 的“筛选标准”列出了当前全部剔除词。
- [ ] 与已剔除类型近似的类型已单列问用户，没有自己决定。
- [ ] 历史名单里的号如果出现，都标了“已调研”，没有进新队列。
- [ ] `filtered.csv`、`filtered.json` 的挂牌行已统一成报告格式；顺序是主力类型在前、边界类型在后，同类按挂牌粉丝从高到低。
- [ ] `筛选清单.md` 有：筛选标准、统计、保留列表、边界类型表、待确认表、剔除列表。
- [ ] `<PREVIEW_DIR>\list.html` 在 390 像素宽下没有横向滚动。
- [ ] 已先发 `list.html` 和 `uncertain\` 的链接（每个配一句说明），再请用户确认；用户确认后的最终队列已写回 `filtered.json`，`groups.json` 已重写。

## C. 每号必做调研核对（不可省略）

每个号 8 项都要有产出，或者有“拿不到”的证据（WORKFLOW 第 3 节最后一列）。**缺一项，这个号就不算完成，不能进入评级。**

运行：`python scripts/analyze/check_coverage.py --config $cfg`。它逐号打印缺什么，并写 `<WORK_DIR>\coverage.csv`。

- 采集阶段看 1~7 项和“截图证据”；“8指标评级”要等分析脚本跑过、`qual.json` 写好后才打勾。
- 脚本每次运行都会重写 `coverage.csv`。“拿不到”的例外，在最后一次运行后由主代理在“例外说明”列补上证据文件名。

- [ ] 每个号要么全部打勾，要么缺的项在“例外说明”里写了证据（例如“粉丝列表隐私，见 shots_clean\<id>\02-fans.png”“星图未入驻，见 01-search.png（抖音号和昵称都搜过）”“红狐未收录”）。
- [ ] 第 5 项：`analysis_posts.json` 里每号有 `uid_created_est`（或最早作品日期）。
- [ ] 第 8 项：`qual.json` 每个号都写了，`content_ok`、`portrait_ok` 没核实的写 `null`。

## D. 抖音采集 A / B（每个代理各自验收；分组时每组验收一次）

- [ ] **登录自检通过**（WORKFLOW 5.3 节）：综合搜索页没有“登录”按钮和登录弹窗，搜索流有返回。没通过的已停下汇报；在未登录状态下处理过的号已列出并重做。
- [ ] 只处理了分给自己的号（分组时只处理本组），没有碰另一组。
- [ ] 锁文件 `<WORK_DIR>\locks\dy-A.json`（或 `dy-B.json`）有 space 名、spaceId、心跳、`done`；没有和其他代理共用 space。换过 profile 的，旧 space 在 `oldSpaces` 里，`done` 还在。
- [ ] 节奏符合 WORKFLOW 6.2 节；两个抖音代理共用一个账号时，用了 `--pace req=5000,account=30000` 并错开启动。
- [ ] `accounts_dy-A.json`（或 `-B`）里每个号都有 `sec_uid` 和 `uid`；`unique_id` 或 `short_id` 与目标一致。
- [ ] 每号 `profile.json` 的昵称、uid 与 `accounts_dy-*.json` 一致，没有串号。
- [ ] 每号作品抓到作品数的 95% 以上（作品很多时至少 60 条）。
- [ ] 每号 `comments2.json` 最多 5 条作品、每条最多 2 页，每条有 `why`。
- [ ] 每号 `fans_sample.json` 有最近、爆款期、探针三类分页，或 `blocked: true`。
- [ ] 每页明显少于 20 人、关注时间集中在几分钟内的批次，已在回复里单独列出。
- [ ] `shots_clean\<id>\` 有 4 张图，`res.json` 全部 `ok: true`；`01-profile.png` 包含头部资料和完整的第一排视频。
- [ ] **主页截图采集要求**（WORKFLOW 6.7 节第 2 步、`CROP_RULE.md` 第 4 节）都做到了：
  - 视口 1280×860（CSS 宽度 1280），左侧栏展开；
  - 滚到顶部；
  - 缩略图加载完才截；
  - 弹窗和提示条已关，鼠标已移开；
  - 存的是视口范围的无损 PNG。
- [ ] **裁剪验收**：抖音代理各出一张 `python scripts/collect/crop_check.py --config $cfg --agent dy-A` → `<PREVIEW_DIR>\progress\crop-check-dy-A.jpg`（B 同理），主代理合并后出全部号的 `crop-check.jpg`。逐张确认：
  - 信息完整：头像、昵称、关注/粉丝/获赞、抖音号和标签行、“作品 N / 推荐 / 喜欢”标签栏、“作品/合集/短剧”筛选条；
  - 第一排 3 张卡片完整，带点赞数和标题行；
  - 右侧没有半张卡片；
  - 底部没有第二排；
  - 对照图张数等于本次应有的号数（检测失败的号不会出现）。报“找不到红色下划线”“标题行可能不完整”“卡片间距不符”的号已重拍；0 作品号和第一排不足 3 条的号按 `CROP_RULE.md` 第 7 节属正常。
- [ ] 主代理亲自抽查至少 3 张：作者正确，评论者和粉丝的昵称、头像已模糊。
- [ ] 素材：`python scripts/collect/assets_finalize.py --config $cfg --agent dy-A` 已跑；`parts\assets\<id>.json` 和 `<PREVIEW_DIR>\overview-assets\<id>\` 的 3 张图都在。图是原图，不是截图裁剪；作品清空的号是灰底占位，并有 `note`。
- [ ] 过程中没有处理验证码；遇到风控或登录弹窗时写了 `PAUSE-douyin.flag` 并停下。
- [ ] 没有对任何 space 调用 `finish()`，没有清 cookie，没有在用户原有标签页里导航，没有去最小化或恢复用户的窗口。
- [ ] 分组时：这一组已写进 `locks\checkpoints.json`，并已向用户汇报；按第一组用时重新估算了全部完成时间。

## E. 星图 A / B

- [ ] **登录自检通过**：达人广场没有跳转到登录页，搜索接口返回成功。
- [ ] 只处理了分给自己的号；锁文件有 space 名和 spaceId。
- [ ] 每号有 `xingtu_data\<id>.json`，含 `found`。
- [ ] 找到的号：`unique_id` 等于抖音号，或 `core_user_id` 等于抖音 uid，不是模糊匹配到的相近号码。
- [ ] 找到的号有画像（性别、年龄、地域）、近 30 天和近 90 天传播、报价；星图类目和挂牌类目不一致的已在回复里列出。
- [ ] 找不到的号：用的是“昵称找人”；已用抖音或红狐的昵称重搜一次并核对 `core_user_id`；有 `01-search.png`。
- [ ] 预览截图（发给主代理和用户的）已用 `xt_dewatermark.py` 抹掉水印，看不到登录账号名；带水印的原图只在工作目录。
- [ ] 截图顶部 92 像素只裁一次：用 `xt_collect.mjs` 采集的保留原图；采集时已裁过的已告知主代理（抹水印时加 `--precropped`）。
- [ ] 没有下单、邀约、收藏、改设置，没有关闭或登出用户的星图窗口；没有改页面或隐藏水印元素。

## F. 红狐

- [ ] 开工时试查过一个号（A 节）。
- [ ] `redfox_data.json` 的 `accounts` 和 `works` 里每个号都有记录（有数据，或标“未收录”）。
- [ ] `redfox_usage.json` 记录了每次调用；按 WORKFLOW 6.10 节估算的消耗没有超出本批积分上限（红狐不返回余额和扣费，只能估算）。
- [ ] 每号的 `crawlTime` 已记录；抓取时间很旧的（一年以上），报告里会注明。
- [ ] 密钥没有出现在任何文件、日志、回复里；换过密钥的，是用户在隐藏输入窗口里设置的。

## G. 指标与评级（主代理）

- [ ] 合并完成：`python scripts/analyze/merge_collect.py --config $cfg` 生成了 `accounts.json`、`parts\assets_manifest.json`。
- [ ] 三个分析脚本都跑过（`build_report.py` 第 1 步），没有报错；批次配置的 `date`、`analysis_time` 是本批的。
- [ ] 评级由 `rating.py` 的 `rate()` 算出，没有手工改。
- [ ] 每号评级依据都有：指标、实际值、门槛、结果。
- [ ] `qual.json`：`summary` 建议不超过 70 个字；`risks` 按重要性排序，前 2 条每条建议不超过 45 个字（卡片只显示前 2 条）；没有人名、接口名、状态码、字段名。
- [ ] 批次专属文字写在 `qual.json` 的 `notes` 里（结论第一句、第三方平台说明、三方对比结论），不是旧批次的文字。
- [ ] 星图截图已整批抹水印：`python scripts/report/xt_dewatermark.py --config $cfg --check`，放大检查图 `progress\xt-dewm-check.jpg` 里认不出任何字。

## H. 密钥与隐私检查

- [ ] 工作目录、预览目录里都没有密钥原文。下面的命令只打印命中的文件路径，应当没有输出：

  ```powershell
  $k = [Environment]::GetEnvironmentVariable('REDFOX_API_KEY','User')
  (Get-ChildItem <WORK_DIR>,<PREVIEW_DIR> -Recurse -File -Include *.py,*.mjs,*.json,*.html,*.md,*.log,*.cmd,*.csv | Select-String -SimpleMatch $k -List).Path
  ```

- [ ] 给子代理的提示词里没有密钥原文。
- [ ] `<PREVIEW_DIR>` 下没有未打码的截图，没有带水印的星图图。
- [ ] 公开发布前（WORKFLOW 9.2 节）：
  - 在 `<REPO>` 下运行 `python scripts/tools/check_public.py` 和 `python scripts/tools/check_public.py --all`，都通过；
  - 搜密钥值和密钥格式，应无命中：

    ```powershell
    $k = [Environment]::GetEnvironmentVariable('REDFOX_API_KEY','User')
    (Get-ChildItem -Recurse -File -Exclude .public-denylist.txt | Where-Object FullName -notmatch '\\\.git\\' | Select-String -SimpleMatch $k -List).Path
    (Get-ChildItem -Recurse -File | Where-Object FullName -notmatch '\\\.git\\' | Select-String -Pattern 'ak_[0-9a-fA-F]{32}' -List).Path
    ```

  - 公开版文档里没有人名、登录账号名、profile 显示名、cookie、真实抖音号、昵称、批次名和本机路径；
  - `git status` 里没有 `.public-denylist.txt`、`__pycache__`、临时文件。

## I. 总览宽表

- [ ] （两种模式）是横屏宽表，不是卡片；8 列依次是：头像和昵称、作品缩略图、挂牌信息、内容主题、粉丝数据、互动数据、风险数据、等级和结论。
- [ ] （两种模式）数量用 w（万）；按评级 A→B→C→D 排序。
- [ ] （简约模式）HTML 里整体缩放到屏幕宽度：390 像素宽下没有横向滚动条，文字和缩略图仍能辨认（截图看过）。
- [ ] （简约模式）手机 PDF 里总览在横屏页上，所有列可见。
- [ ] （复杂模式）A4 PDF 里“一、总览”标题和宽表在同一张 A4 横向页上，评级列完整可见。

## J. 卡片式详情与页数（简约模式）

- [ ] 每个号都用卡片版式，只有四块：
  - ① 账号信息：挂牌行和卡片；
  - ② 首页截图：按 `CROP_RULE.md` 裁成“账号信息 + 第一排前 3 条作品”（`dc-01-home.jpg`），PDF 里宽 260px、居中，HTML 最宽 400px，点图看整页；
  - ③ 结论：摘要、购买建议、最多 2 条风险，加评级依据小块；
  - ④ 压缩可视化：矮时间线、2×2 快览、4 张证据缩略图。
- [ ] 卡片里的数字和总览表同一行一致（卡片复用总览表的单元格）。
- [ ] 每号页数：`build_report.py --check` 逐号打印的 `pages` 都 ≤2。单号重查：`python scripts/report/sample_detail.py --config $cfg <id> chk-<id>`。
- [ ] 超过 2 页的号已按 WORKFLOW 8.4 节调整，没有删掉任何一块，也没有删调研内容。
- [ ] 快览小块里“未入驻”“隐私”“未收录”的写法和 C 节的例外说明一致。

## K. 报告 HTML（简约模式，主代理）

- [ ] `report.html` 里有 `id="overview-table"`；每个号都有 `<section class="acct" id="a-<id>">`，内容是卡片详情。
- [ ] 全文没有这些内容（逐个搜一遍）：“禁止转让”“未能验证的数据与原因”、状态码、接口名、人名、密钥。复杂模式的 HTML 也要搜。
- [ ] 粉丝、获赞用 w（万）；日期写“截至 YYYY-MM-DD”。
- [ ] `python scripts/tools/mshot.py --config $cfg report.html m 390` 输出 0 个溢出元素；分段截图看过，没有挤压、空白和缺图。

## L. 手机 PDF（简约模式）

- [ ] 第 1 页是首页，第 2 页是目录，目录页码正确、可点击。
- [ ] 首页的标题、号数、日期、等级分布是本批的（来自批次配置和 `qual.json`）。
- [ ] 总览在横屏页上。
- [ ] 每号不超过 2 页：看 `build_pdf_m.py` 打印的 `toc`，相邻两个号的页码差。
- [ ] `pdfm-sheet` 缩略图（`build_report.py --check` 生成，或 `python scripts/tools/pdf_sheet.py --config $cfg report.pdf pdfm-sheet`）列出的低填充页都看过，没有异常空白页，图片没有被截断。

## M. 最终交付（主代理）

- [ ] 用户已审过 HTML（或明确要求 HTML 和 PDF 一起给）。
- [ ] `coverage.csv` 每个号都齐全或有例外证据（两种模式相同）。
- [ ] 交付物和批次配置的 `mode` 一致：简约模式是 `report.html` 和 `report.pdf`；复杂模式是 `report-full.html` 和 `report-a4.pdf`（WORKFLOW 8.7 节）。
- [ ] 已生成总览完整截图 `<PREVIEW_DIR>\progress\overview-full.jpg`（`python scripts/tools/snap_overview.py --config $cfg`）。
- [ ] 回复先说结论（几个号、各级几个），写明用的是哪种模式，再逐号一句话，最后给 HTML、PDF、总览截图的链接；写明没完成或没核实的项。
- [ ] 代理 space（含换 profile 留下的 `oldSpaces`）已由主代理统一 `finish({ keep: [] })`（情况 B），或已 `handOff()`（情况 A）。用户自己的窗口还在、仍是登录状态。
- [ ] 本批 `filtered.json` 里的号已加进历史名单。
- [ ] 10 分钟进度定时器已停掉。

## N. 进度汇报（主代理，全程，硬性规定）

- [ ] 开工第一件事已启动定时器（WORKFLOW 5.6 节）：后台 shell 每 600 秒输出一行 `PROGRESS-TICK`，`notify_on_output` 的 pattern 是 `PROGRESS-TICK`。
- [ ] 网络中断或会话重启后，已确认定时器还在；不在就已重新启动。
- [ ] 每次被唤醒都汇报了，没有跳过；两次汇报间隔不超过约 10 分钟。
- [ ] 每次汇报包括：做完了什么、正在做什么、预计还要多久、每个号 8 项的完成数、需要用户做什么。
- [ ] 每次汇报都顺带看了各盘剩余空间：明显下降时写进汇报；工作目录所在盘低于 2 GB 时，已停写大文件并告诉用户。
- [ ] 每次附 1~2 张最新截图链接：JPEG 放 `<PREVIEW_DIR>\progress\`，文件名带时间（如 `tick-1650-1.jpg`），链接格式 `<PREVIEW_URL>/progress/<文件名>.jpg`；星图图已抹水印；发出前确认链接能打开。
- [ ] 请用户做选择前，先在正文里给出每个素材的链接和一句说明，再提问。

## O. 子代理中断与续做（主代理）

- [ ] 每个子代理的提示词里都写了“边做边写盘、追加写入、开工先读锁文件和产出跳过已完成部分”。
- [ ] 收到子代理失败通知后，先查了它的产出文件、进度日志和锁文件，记下完成到哪里。
- [ ] 确认它用分离进程启动的浏览器脚本已经停了（日志不再更新），才续做。
- [ ] 用 resume 让同一个子代理续做，续做消息写明已完成的部分、从哪里继续、先读哪些文件；仍然后台运行。
- [ ] 只有 resume 失败、旧任务心跳超过 10 分钟没更新时，才派新代理；输出路径不变。
- [ ] 续做完成后核对：没有重复行、重复号，没有被覆盖的旧结果（对比续做前记下的完成清单）。

## P. 复杂模式（完整版）的 HTML 和 A4 PDF

只在 `mode = full` 时做。对照 WORKFLOW 8.8 节和仓库 `examples/output/full-*.jpg` 样张。

HTML（桌面版）：

- [ ] 交付的是 `report-full.html`，没有经过 `mobile.py`、`build_detail_m.py`、`merge_detail.py` 处理。
- [ ] `report-full.html` 里有 `id="overview-table"` 和 `ov-charts-merged`（总览图表：散点图、掉粉对比、达标热力表）；“二、评级标准”附出处链接。
- [ ] 每个号的小节按顺序有四块：
  - ① 账号信息（挂牌行中间插入昵称）；
  - ② 账号首页截图（整张视口截图 `dc-01-profile.jpg`，整栏宽，不裁剪；D 节的裁剪验收照样要过）；
  - ③ 巨量星图截图（大图、不折叠、已抹水印；没入驻的放“搜不到”截图）；
  - ④ 爬取数据、红狐数据和结论（指标卡片、图表、作品与互动、粉丝抽样、评论区互动者、内容方向、红狐数据、佐证截图、结论框和评级依据表）。
- [ ] 方法说明、三方对比结论等批次文字是本批的（`qual.json` 的 `notes`）。
- [ ] `python scripts/tools/mshot.py --config $cfg report-full.html d 1280` 输出 0 个溢出元素。

A4 PDF：

- [ ] 第 1 页封面：标题、账号和评级、日期、数据来源；第 2 页目录，可点击跳转，页码正确。
- [ ] “一、总览”标题和宽表在同一张 A4 横向页上，所有列可见，标题下没有大片空白。
- [ ] 每个号都从新的一页开始；图片、图表、表格行没有被分页切断。
- [ ] 星图截图是大图，`<details>` 都已展开。
- [ ] `pdf-a4-sheet` 缩略图（`build_report.py --mode full --check` 生成）列出的低填充页都看过。

## Q. 分组连续调研（号多时，主代理）

- [ ] `groups.json` 每组 10 个号（最后一组可以少），主力类型在前、边界类型在后；和 `assignment.json` 的 A/B 分法一致。
- [ ] 每组：两个抖音代理各 5 个号；做完后按 D 节验收，写 `locks\checkpoints.json`（组名、完成时间、每号必做项状态、问题），向用户汇报，再 resume 同一个代理做下一组。
- [ ] 锁文件的 `done` 跨组累积，没有重复采集已完成的号。
- [ ] 星图和红狐已提前做完全部组，没有等抖音。
- [ ] 第一组做完后已按实际用时估算全部完成时间，写进汇报。
- [ ] 报告节奏符合用户的选择（全部做完出一份总报告，或每组一份）。
