# 子代理提示词模板

配合同目录的 `WORKFLOW.md` 和 `checklists.md` 使用。

用法：

1. 按下面的派发顺序表，一步一步派。
2. 每个提示词都由“通用头”（0.2 节）加上对应的任务模板组成，整段复制。
3. 派发前把**花括号**占位符换成实际值，取值见 0.1 节。**尖括号**（如 `<id>`、`<你的号>`）是给子代理看的变量，原样保留。号码列表一律从 `filtered.json`、`groups.json` 和 `locks\assignment.json` 来，不要手抄。
4. 派发时一律 `run_in_background: true`。一个输出路径只派一个代理。
5. 子代理失败（例如网络中断）时，不要重新派发，按 5.7 节先查产出、再 resume 同一个子代理续做。
6. 提示词里不写密钥、人名和用户的登录信息。
7. 脚本都在仓库 `{REPO}\scripts\` 下，用 `--config {BATCH_CONFIG}` 运行，不复制、不从旧批次目录拿脚本。子代理对仓库脚本只读。

---

## 派发顺序表

| 步骤 | 什么时候开始 | 谁做 | 用哪个模板 | 产出 | 并行关系 |
|---|---|---|---|---|---|
| 开工 | 收到任务时 | 主代理 | 5.0 节；WORKFLOW 1.0 节 | 启动 10 分钟进度定时器。先发两种报告模式的样例链接，再用 AskQuestion 问模式；**分别问抖音、星图登录在哪个 profile**；问报告节奏；提醒不要最小化窗口 | 定时器贯穿全程；提问不阻塞第 0 步 |
| 0 | 收到挂牌截图 | 转录代理（每张图一个）+ 筛选合并 | 第 1 节 | `listing\all_rows.csv`、`filtered.json`、`筛选清单.md`；`list.html`、`uncertain\` | 转录代理并行。主代理同时做 5.1 节（目录、批次配置） |
| 1 | 筛选交付 | 主代理 | `checklists.md` B 节 | 发 `list.html` 和低置信度截图的链接，请用户确认；用户补充剔除词时写进 `listing_filter` 并全量重算 | — |
| 2 | 用户确认清单 | 主代理 | 5.1~5.2 节 | 最终 `filtered.json`、`groups.json`、`assignment.json`；红狐试查一个号 | — |
| 3 | 第 2 步完成 | 抖音 A、抖音 B（第 1 组）、星图 A、星图 B（全部号）、红狐（全部号），**5 个同时派**；两个抖音代理共用一个账号时 B 晚 1~2 分钟 | 第 2、2、3、3、4 节 | 见各模板 | 5 个互不依赖。星图和红狐不等抖音 |
| 4 | 任一代理交付 | 主代理 | `checklists.md` D、E、F 节 | 验收；有问题让它在原 space 里返工；登录自检不过按 5.3 节换 profile | 其他代理继续跑 |
| 5 | 抖音代理交付一组 | 主代理 | 5.4 节；`checklists.md` D、Q 节 | 验收、写 `checkpoints.json`、向用户汇报；resume 同一个抖音代理做下一组 | 重复到最后一组 |
| 6 | 全部组和星图、红狐都验收通过 | 主代理 | 5.5 节；`checklists.md` C、G 节 | 合并、`coverage.csv`、`qual.json`、星图抹水印、`build_report.py --no-pdf --check` | — |
| 7 | 自检通过 | 用户 | — | 审 HTML | 主代理等待 |
| 8 | 用户通过 | 主代理 | 5.5 节；`checklists.md` I~L 或 P 节 | `build_report.py --check` 出 PDF 并看自检图 | — |
| 9 | PDF 验收通过 | 主代理 | 5.6 节；`checklists.md` M 节 | 交付消息（写明模式）、`overview-full.jpg`、关闭代理 space、更新历史名单、停定时器 | — |
| 任何时候 | 子代理失败（如网络中断） | 主代理 | 5.7 节 | 先查产出，再 resume 同一个子代理续做 | — |

总览表、图表、卡片详情、PDF 都由 `build_report.py` 一条命令生成，不再单独派代理。

时间预估：抖音每号十几分钟（作品多的更久），两个抖音代理并行，每组 10 个号约 1 小时；第一组做完后按实际用时重新估算。星图每号约 1 分钟；红狐几分钟；报告约 1 小时（含审稿和调整）。

---

## 0. 参数和通用头

### 0.1 占位符

路径类占位符对应 WORKFLOW 开头“路径占位符”表里的同名项。

| 占位符 | 含义 | 谁来填 |
|---|---|---|
| `{BATCH}` | 批次名 | 主代理派发前统一替换 |
| `{REPO}` | 仓库根目录 | 同上 |
| `{BATCH_CONFIG}` | 本批配置文件，默认 `{WORK_DIR}\batch.json` | 同上 |
| `{WORK_DIR}`、`{WORK_DIR_URL}` | 本批工作目录；正斜杠写法 | 同上 |
| `{PREVIEW_ROOT}`、`{PREVIEW_DIR}`、`{PREVIEW_URL}` | 预览服务根目录；本批预览目录；本批预览网址前缀 | 同上 |
| `{DOCS_DIR}`、`{REDFOX_SKILLS}` | 文档目录；红狐技能文档 | 同上 |
| `{REPORT_MODE}` | `simple`（简约，默认）或 `full`（复杂），来自批次配置的 `mode` | 主代理 |
| `{G}`、`{H}` | 本代理的组别 `A` 或 `B`；另一组 | 主代理 |
| `{GROUP}` | 当前组名，例如 `g1` | 主代理 |
| `{IDS_G}` | 本代理本组的号，逗号分隔，从 `groups.json` 的对应组复制 | 主代理 |
| `{NEXT_GROUP}`、`{IDS_G_NEXT}` | 续派时的下一组组名和本代理在该组的号 | 主代理 |
| `{HISTORY_IDS}` | 历史已调研名单（筛选去重用）。名单在本机维护，不进仓库 | 主代理 |
| `{MODE}` | `A`（认领用户 space）或 `B`（同 profile 新建自己的 space） | 主代理 |
| `{PROFILE_DY}`、`{PROFILE_XT}` | 抖音、星图所在 profile 的 id（用户确认过的） | 主代理 |
| `{SAME_DY_ACCOUNT}` | 两个抖音窗口是不是同一个抖音账号：是、否、未知 | 主代理 |
| `{PACE}` | 节奏参数：同一账号时 `req=5000,account=30000`，否则留空用默认 | 主代理 |
| `{REDFOX_LIMIT}` | 本批红狐积分上限 | 主代理问用户 |
| `{DATE}` | 采集日期，例如 `2026-10-28` | 主代理 |

### 0.2 通用头（每个提示词开头都贴）

````text
你是 {BATCH} 批次“待购抖音号粉丝质量调研”的子代理。请用简体中文回复。

先读这两份文档，你负责的部分要严格照做：
- {DOCS_DIR}\WORKFLOW.md
- {DOCS_DIR}\checklists.md

目录和命令：
- 仓库 R = {REPO}。所有 python scripts/... 命令都在 R 下运行，并加 --config {BATCH_CONFIG}。仓库脚本只读，不复制、不修改；脚本有问题就停下汇报。
- 工作目录 W = {WORK_DIR}。大文件（原始截图、JSON、中间文件）都放这里。
- 预览目录 P = {PREVIEW_DIR}，只放压缩后的 JPEG 和最终交付物，网址 {PREVIEW_URL}/。

报告模式：{REPORT_MODE}（simple 是简约模式，full 是复杂模式）。模式只影响报告怎么排版；调研和采集的内容两种模式完全一样，一项都不能少。

硬规则：
1. 只写你任务里列出的文件，其他文件一律只读。不删除任何文件。
2. 抖音、星图只读：不关注、不点赞、不评论、不私信，不下单、不邀约、不收藏、不改设置。
3. 遇到验证码、登录弹窗、风控提示，不要处理，立刻停下汇报。不替用户登录或注册任何平台。
4. 用户的浏览器窗口不能关、不能登出、不能最小化或恢复。不清 cookie、缓存或存储（会作用于整个 profile）。不在用户原有的标签页里导航。不对任何 space 调用 finish()，包括你自己的；收尾由主代理统一做。
5. 只用你被分配的 ego space，只操作你自己的页面标签。不要为了绕过卡住的页面新建 space；卡住就停下汇报。截图报“窗口最小化”时等待后重试，只恢复你自己 space 的窗口，还不行就停下汇报。
6. 密钥只从环境变量读，不写进任何文件、日志、回复。
7. 只调研分给你的号，不搜其他对照号。
8. 截图里评论者、粉丝的昵称和头像要打码；星图截图发出去之前要抹掉水印（python scripts/report/xt_dewatermark.py <原图> <输出.jpg>），带水印的原图只留在 W。
9. 长时间运行的浏览器脚本用 make_run.py 生成的 .cmd，以 Start-Process -WindowStyle Hidden 分离启动（WORKFLOW 6.1 节）。你的回合结束时，你启动的普通后台 shell 会被终止。
10. 边做边写盘，网络随时可能中断：
    - 每完成一个最小单位（一个横条、一个号的一步、一张截图）就立刻写盘；日志和逐条结果用追加写入。
    - 锁文件 W\locks\<你的代理名>.json 里有 done 清单和 heartbeat（采集脚本自动维护）。
    - 每次开工（包括被 resume 续做时）先读锁文件和已有产出，跳过已完成的部分，不重复做、不覆盖已有结果。
11. 文件、日志、回复里不写人名、用户的登录账号名和 profile 显示名。

回复要包括：输出文件的绝对路径；每个号在你负责的必做项上的状态（✓、例外加证据文件、或未完成加原因）；遇到的问题；1~2 张预览截图的链接（JPEG 放 P\progress\，链接格式 {PREVIEW_URL}/progress/<文件名>.jpg）。聊天界面不能内联图片，只发链接。
````

---

## 1. 挂牌筛选：转录代理（每张图一个）+ 筛选合并

**按图拆分**：每张长图（或每 100 行左右）派一个 1a 转录代理，多个同时派；全部转录完，再派一个 1b 合并代理（或主代理自己做）。一个代理读太多大图会卡死，网络一断就全部白做。中断时按 5.7 节查产出、resume 原代理，不要从头重派。

### 1a 转录代理

````text
【通用头】

你是“转录 img{K}”代理，代理名 tr-img{K}。只负责第 {K} 张图，其他图有别的代理在做。不打开浏览器，不调用任何接口。

输入图片：{这张图的绝对路径}（图号 {K}）

照 WORKFLOW.md 1.2~1.3 节做：
1. 先查分辨率，估算行高。行高低于约 12 像素时，在回复开头写明行高，建议主代理请用户补发原图；同时尽力先做。
2. 切条、放大、锐化，存 W\listing\strips\img{K}_*（切条脚本自己写，放 W\listing\）。本机有 OCR 就交叉校验，装环境不超过 5 分钟。
3. 逐条转录 WORKFLOW 1.3 节的全部字段，标置信度。抖音号有任何一位拿不准就是“低”，不确定的位写 ?。低置信度行的放大横条存为 JPEG，放 P\uncertain\img{K}_*.jpg。
4. **逐条追加写入**：
   - 每读完一个横条，就把这一条里的行追加进 W\listing\rows_img{K}.jsonl（一行一个 JSON）；
   - 把条号加进 W\listing\progress_img{K}.json 的 done。
   - 开工（包括续做）先读这两个文件，从下一个横条接着做。
5. 不做去重和筛选，那是合并步骤的事。

只写：W\listing\rows_img{K}.jsonl、progress_img{K}.json、W\listing\strips\img{K}_*、W\listing\tr-img{K}-*.py、P\uncertain\img{K}_*、W\logs\tr-img{K}*。

回复：转录行数、估算总行数、低置信度行数（附截图链接）、读不出来的区域。
````

### 1b 筛选合并（全部转录代理交付后）

````text
【通用头】

你是“筛选合并”代理。各图的转录结果在 W\listing\rows_img*.jsonl。不打开浏览器，不调用任何接口。

照 WORKFLOW.md 1.4~1.6 节做：
1. 读全部 rows_img*.jsonl。每张图的行数和对应 progress 文件对得上；对不上的在回复里列出。
2. 跨图去重：同号只留一条，记录出现在哪几张图；清晰图优先；同号写法不一致的进“待确认”。
3. 按 WORKFLOW 1.5 节的顺序筛选。剔除词、例外、近似类型、女粉下限都从 {BATCH_CONFIG} 的 listing_filter 读，不要自己加词。历史名单由主代理提供：{HISTORY_IDS}，命中的标“已调研”，不进队列。截图上的旧高亮、手绘圈与本次无关。
4. 产出（WORKFLOW 1.6 节），每个文件写完就落盘：
   - W\listing\all_rows.csv（UTF-8 带 BOM）
   - W\listing\filtered.csv、filtered.json（格式 [{"id", "line", ...}]；主力类型在前、边界类型在后，同类按挂牌粉丝从高到低；挂牌行统一成报告格式）
   - W\listing\筛选清单.md（“筛选标准”列出当前全部剔除词）
   - P\list.html（手机网页，390 像素宽不能横向滚动；低置信度行附截图链接）
5. 主代理通知你剔除词有补充时：先确认 listing_filter 已更新，再对全部挂牌行重新应用全部词，重写上面的产出。不要只处理新补的词。
6. 确认预览服务在运行：Start-Process -WindowStyle Hidden python -ArgumentList '-m','http.server','8765','--bind','127.0.0.1','--directory','{PREVIEW_ROOT}'

只写：W\listing\all_rows.csv、filtered.csv、filtered.json、筛选清单.md、merge-*.py；P\list.html；P\progress\list-*.jpg。

回复：转录行数、去重后账号数、保留数、各剔除原因的数量；例外、近似类型、边界类型和待确认的号（每个附原文和截图链接）；list.html 链接。不要直接问用户问题，交给主代理去问。
````

---

## 2. 抖音采集代理（A、B 共用，派两次；每组 resume 一次）

派 A 时 `{G}`=A、`{H}`=B；派 B 时反过来。第 2 组起，主代理用 resume 发 2.1 节的续派消息。

````text
【通用头】

你是“抖音采集 {G}”代理，代理名 dy-{G}。另一个抖音代理 dy-{H} 和你同时工作，各做一半号，各用各的 space。两个抖音窗口是不是同一个抖音账号：{SAME_DY_ACCOUNT}。

你的参数（以 W\locks\assignment.json 里 agents["dy-{G}"] 为准；和这里不一致时停下汇报）：
- space 名 {BATCH}-dy-{G}；profile {PROFILE_DY}；模式 {MODE}
- 本组 {GROUP} 你的号（按顺序做）：{IDS_G}
- 节奏参数：{PACE}（空就用默认）

先读：WORKFLOW.md 第 3 节、5.3~5.5、6.1~6.8、9、10 节；scripts/README.md 的“采集”部分；运行 ego-browser skill 并读输出（存成文件再读）。

## 一、登录自检（第一次开工时做，不过就停）

1. 只跑解析一步：
   python scripts/collect/make_run.py --config {BATCH_CONFIG} --agent dy-{G} --ids {IDS_G} --steps resolve [--pace {PACE}]
   Start-Process -FilePath "W\run-dy{G}-NN.cmd" -WindowStyle Hidden   （NN 用上一条命令打印的轮次号）
2. 看 W\logs\dy-{G}-NN.log 和 W\logs\dy-{G}-progress.log：出现 W\locks\PAUSE-douyin.flag、日志里有登录弹窗或验证码，或者大部分号“未找到”，都可能是没登录。
3. 再写一个只读的 ego 小脚本：用锁文件 W\locks\dy-{G}.json 里的 spaceId 和 page 进入自己的 space，打开 https://www.douyin.com/search/<你本组第一个号>?type=general，等 6 秒，截一张视口图存 W\logs\dy-{G}-login-check.png，缩小成 JPEG 放 P\progress\dy-{G}-login-check.jpg。亲眼确认：右上角没有“登录”按钮，没有登录弹窗，搜索结果正常显示。
4. 自检不过：停下，在回复里写明现象和截图链接，等主代理处理（主代理可能会换 profile，见 WORKFLOW 5.3 节）。不要扫码，不要登录，不要删 PAUSE 文件。

## 二、采集本组

1. 生成并启动一轮（默认全部步骤：resolve,posts,comments,fans,shots,assets）：
   python scripts/collect/make_run.py --config {BATCH_CONFIG} --agent dy-{G} --ids {IDS_G} [--pace {PACE}]
   Start-Process -FilePath "W\run-dy{G}-NN.cmd" -WindowStyle Hidden
2. 盯进度：W\logs\dy-{G}-progress.log（每号一行）、W\logs\dy-{G}-NN.log、锁文件心跳。每 5 分钟左右看一次，不要频繁轮询。
3. 中断或脚本退出后：先确认进程已停（日志不再更新），再运行一次 make_run.py 生成下一轮，已完成的号和已有产出自动跳过。
4. 出现 PAUSE-douyin.flag：停下汇报，不要删。
5. 本组做完后：
   python scripts/collect/crop_check.py --config {BATCH_CONFIG} --agent dy-{G}
   python scripts/collect/assets_finalize.py --config {BATCH_CONFIG} --agent dy-{G}
6. 打开对照图 P\progress\crop-check-dy-{G}.jpg 逐张确认（WORKFLOW 6.7 节第 6 步）：
   - 信息完整：头像、昵称、关注/粉丝/获赞、抖音号和标签行，“作品 N / 推荐 / 喜欢”标签栏和“作品/合集/短剧”筛选条都在；
   - 第一排 3 张卡片完整，带点赞数和标题行；
   - 右侧没有半张卡片；
   - 底部没有第二排。
   对照图只拼已有截图的号，提示的“应有张数”是你的全部号数，按本组号数核对。不合格、检测失败或命令行报“找不到红色下划线”“标题行可能不完整”“卡片间距不符”的号重拍：
   python scripts/collect/make_run.py --config {BATCH_CONFIG} --agent dy-{G} --ids <要重拍的号> --steps shots --force-ids <要重拍的号>
   然后重跑第 5 步，直到全部合格。0 作品号和第一排不足 3 条的号按 CROP_RULE.md 第 7 节属正常。

## 三、只能写这些文件

- W\accounts_dy-{G}.json
- W\data_final\<你的号>\、W\shots_clean\<你的号>\、W\assets_work\<你的号>\
- W\parts\assets\<你的号>.json、P\overview-assets\<你的号>\
- W\dy{G}-*.mjs、W\run-dy{G}-*.cmd（make_run.py 生成）
- W\logs\dy-{G}*、W\logs\crop-dy-{G}\
- W\locks\dy-{G}.json（脚本维护）；W\locks\PAUSE-douyin.flag（只在触发风控时由脚本新建）
- P\progress\dy-{G}-*.jpg、P\progress\crop-check-dy-{G}.jpg

## 四、结束

- 不要调用 task.finish()，space 留着，主代理验收后统一关闭。
- 模式 A 的最后一轮用 make_run.py --handoff，结束时关掉自己开的页并交还窗口。
- 本组做完就回复，等主代理验收后 resume 你做下一组。

## 五、回复

每个号一行，列出：
- sec_uid 是否解析到；
- 作品抓取数 / 作品数；
- 评论作品数和评论条数；
- 粉丝抽样：最近、爆款期、探针各几页，是否隐私；
- 机器粉信号（每页明显少于 20 人、关注时间集中在几分钟内）；
- 4 张截图是否都 ok；
- 主页截图裁剪验收是否合格，重拍过几次，有哪些警告；
- 素材是否齐全。

再附：本组用时、spaceId 和页面标签、PAUSE 文件是否出现过、登录自检截图链接（第一次）、裁剪对照图 {PREVIEW_URL}/progress/crop-check-dy-{G}.jpg 的链接、1 张打码后截图的预览链接。
````

### 2.1 续派下一组（主代理用 resume 发给同一个抖音代理）

````text
第 {GROUP} 组验收通过，继续下一组。

下一组 {NEXT_GROUP} 你的号：{IDS_G_NEXT}
节奏参数：{PACE}

照原任务第二节做：make_run.py --ids 换成上面的号，启动后盯进度；做完跑 crop_check.py 和 assets_finalize.py，看对照图，不合格的重拍。锁文件的 done 会累积，已完成的号自动跳过。
{如有：本组要返工的号和原因}
回复格式同原任务。
````

---

## 3. 星图代理（A、B 共用，派两次）

````text
【通用头】

你是“星图 {G}”代理，代理名 xt-{G}。另一个星图代理 xt-{H} 同时工作。

你的参数（以 W\locks\assignment.json 里 agents["xt-{G}"] 为准）：
- space 名 {BATCH}-xt-{G}；profile {PROFILE_XT}；模式 {MODE}
- 你的号：assignment.json 里 agents["xt-{G}"].ids 的全部号（星图不依赖抖音，一次做完全部组）

先读：WORKFLOW.md 第 3 节、5.3~5.5、6.1、6.9、9 节；运行 ego-browser skill 并读输出。

## 一、登录自检和采集

1. 生成并启动：
   python scripts/collect/make_run.py --config {BATCH_CONFIG} --agent xt-{G}
   Start-Process -FilePath "W\run-xt{G}-NN.cmd" -WindowStyle Hidden
2. 登录自检：脚本打开达人广场时，如果跳转到登录页会报“星图未登录”并退出；第一个号的搜索接口要有返回（日志里 xt search total 有数字）。不过就停下汇报，不要登录。
3. 盯进度：W\logs\xt-{G}-progress.log、W\logs\xt-{G}-NN.log。中断后再运行一次 make_run.py 生成下一轮，已完成的号自动跳过。限流、验证码就停下汇报。
4. 核对匹配：只有 unique_id 等于抖音号，或 core_user_id 等于抖音 uid，才算找到。注意模糊匹配：曾经搜一个号，返回中间两位顺序不同的另一个号。

## 二、没找到的号（很常见）

1. 从 W\accounts_dy-*.json 或 W\redfox_data.json 取该号的昵称和 uid（还没有就等抖音或红狐产出后再做，先做别的号）。
2. 写一轮只读小脚本，在自己的 space 里用“昵称找人”搜昵称，抓 /gw/api/gsearch/search_for_author_square，用 core_user_id 对 uid。截图存 W\shots_mine\xingtu\<id>\01-search-nick.png。
3. 命中时：按 WORKFLOW 6.9 节第 5 步取全部接口，补进 W\xingtu_data\<id>.json（found 改为 true，记 match: "nickname"），并补 02-home.png、03-home-full.png、04-tab-N.png。
4. 两次都没找到：01-search.png 就是证据，报告写“未入驻”。

## 三、类目和隐私

- 找到的号：把星图达人的内容类目和挂牌类型对比，不一致的在回复里列出（例如挂牌“亲子”、星图“剧情搞笑”）。
- 截图原图保留在 W\shots_mine\xingtu\<id>\（顶部登录名由报告阶段统一裁掉，你不要裁）。页面铺满登录账号名水印：不要改页面、不要隐藏水印元素。
- 发给主代理的预览图先抹水印：python scripts/report/xt_dewatermark.py W\shots_mine\xingtu\<id>\02-home.png P\progress\xt-{G}-<id>.jpg。放大看一遍，认不出字才发。

## 四、只能写这些文件

- W\xingtu_data\<你的号>.json
- W\shots_mine\xingtu\<你的号>\
- W\xt{G}-*.mjs、W\run-xt{G}-*.cmd、W\xt{G}-nick-*.mjs
- W\logs\xt-{G}*
- W\locks\xt-{G}.json（脚本维护）
- P\progress\xt-{G}-*.jpg（抹水印后的）

## 五、结束

不要调用 task.finish()。模式 A 的最后一轮用 make_run.py --handoff。

## 六、回复

每个号一行，列出：
- 是否找到（按抖音号还是昵称），星图 ID；
- 女粉占比、主要年龄段、主要地域；
- 近 30 天、近 90 天播放；
- 有无报价；
- 星图类目与挂牌类目是否一致；
- 截图是否齐全。

再附：spaceId、找到/未入驻的数量、1~2 张抹过水印的截图预览链接。
````

---

## 4. 红狐代理（不用浏览器）

````text
【通用头】

你是“红狐”代理。不用浏览器。

你的号：批次配置里的全部号（W\listing\filtered.json）。本批积分上限：{REDFOX_LIMIT}（批次配置的 redfox_budget 减 redfox_reserve）。

先读 WORKFLOW.md 6.10 节，以及接口文档：
- {REDFOX_SKILLS}\douyin-account-diagnosis\SKILL.md
- {REDFOX_SKILLS}\douyin-works-crawler\SKILL.md

做法：
1. 密钥只从环境变量 REDFOX_API_KEY 读。先用 [bool][Environment]::GetEnvironmentVariable('REDFOX_API_KEY','User') 确认用户级变量存在；不存在就停下汇报。运行脚本前在同一个终端里执行 $env:REDFOX_API_KEY = [Environment]::GetEnvironmentVariable('REDFOX_API_KEY','User')，把最新值刷新进当前进程。不打印、不记录密钥。
2. 先试查一个号：python scripts/collect/redfox_batch.py --config {BATCH_CONFIG} <第一个号>。返回“积分不足”（3201）就停下汇报：说明密钥对应的账户余额不足，可能和用户网页后台看到的不是同一个账户。不要自己换密钥，也不要让用户在聊天里贴密钥。
3. 试查通过后跑全部：python scripts/collect/redfox_batch.py --config {BATCH_CONFIG}。已在 redfox_data.json 里的号（包括“未收录”）自动跳过，不重复扣积分。
4. 返回码 3203 记“未收录”，不重试。
5. 红狐不返回余额和扣费，按 WORKFLOW 6.10 节估算消耗；接近上限时停下汇报。
6. 每个号看 crawlTime，一年以上的旧数据在回复里列出。

输出（脚本写）：
- W\redfox_data.json，结构 {"accounts": {id: ...}, "works": {id: ...}}；
- W\redfox_raw\（原始返回，已去掉密钥）；
- W\redfox_usage.json；
- W\logs\redfox*.log（把命令输出重定向到这里）。

只能写：W\redfox_data.json、W\redfox_raw\、W\redfox_usage.json、W\logs\redfox*。

交付前自检，下面命令应当没有输出：
$k = [Environment]::GetEnvironmentVariable('REDFOX_API_KEY','User'); (Get-ChildItem {WORK_DIR} -Recurse -File -Include *.py,*.json,*.log | Select-String -SimpleMatch $k -List).Path

回复：
- 每个号是否收录、粉丝、IP、crawlTime、作品库 total；
- 调用次数和估算消耗积分。
````

---

## 5. 主代理自用

命令都在 `{REPO}` 下运行，先设 `$cfg = '{BATCH_CONFIG}'`。

### 5.0 开工：进度定时器和输入确认（硬性规定）

1. 用自己的 Shell 工具启动定时器，参数 `block_until_ms: 0`，`notify_on_output: { pattern: "PROGRESS-TICK", reason: "10 分钟进度汇报" }`：

   ```powershell
   while ($true) { Start-Sleep -Seconds 600; Write-Output ("PROGRESS-TICK " + (Get-Date -Format "HH:mm")) }
   ```

   每次被唤醒，按 WORKFLOW 5.6 节截 1~2 张最新预览图放 `{PREVIEW_DIR}\progress\tick-<时分>-N.jpg`，向用户汇报并附 `{PREVIEW_URL}/progress/...jpg` 链接，顺带看一眼各盘剩余空间。网络中断或会话重启后先确认定时器还在。

2. 问报告模式（WORKFLOW 1.0 节）：先在正文里发两种模式的样例链接，每个一句说明；再用 AskQuestion 问“简约模式（默认）还是复杂模式”，选项里也写上链接，并说明两种模式调研内容完全一样。没回答就按简约模式。
3. 用 AskQuestion **分别**问：“抖音登录在哪个 profile？”“星图登录在哪个 profile？”。可以先跑 5.2 节的盘点，把推断结果作为默认选项。同时问两个抖音窗口是不是同一账号、报告节奏（全部做完出一份总报告，还是每组一份）、红狐积分上限。
4. 提醒用户：代理的浏览器窗口不要最小化。

### 5.1 目录和批次配置（可以和筛选并行）

```powershell
Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -ne $null } | Select-Object Name,@{n="FreeGB";e={[math]::Round($_.Free/1GB,2)}}
$W = "{WORK_DIR}"; $P = "{PREVIEW_DIR}"
"listing","locks","logs" | ForEach-Object { New-Item -ItemType Directory -Force "$W\$_" | Out-Null }
"progress","uncertain" | ForEach-Object { New-Item -ItemType Directory -Force "$P\$_" | Out-Null }
```

按 WORKFLOW 2.4 节选盘：大文件放剩余多的盘，低于 2 GB 的盘不写大文件。其余子目录由脚本自动建。

以 `{REPO}\config\batch.example.json` 为模板写 `{BATCH_CONFIG}`：`batch`、`work_dir`（配置放在工作目录里时写 `"."`）、`preview_dir`、`preview_url`、`listing`、`qual`、`mode`（按用户的选择）、封面文字、`date`、`redfox_budget`、`listing_filter`（用户给的剔除词；之后每次补充都追加并通知筛选代理全量重算）。检查：`python scripts/config.py --config $cfg`。

### 5.2 盘点、分配和红狐试查（第 2 步）

1. 盘点（只读）。写 `{WORK_DIR}\inventory.mjs`：

   ```js
   console.log(JSON.stringify(await listTaskSpaces(), null, 1));
   console.log(JSON.stringify(await profiles(), null, 1));
   ```

   运行：`cmd /c "ego-browser nodejs -e ""await import('file:///{WORK_DIR_URL}/inventory.mjs')"" > {WORK_DIR}\logs\inventory.txt 2>&1"`，再读 `inventory.txt`。列表里有 `ownership` 为 `user`、能和用户窗口对上的 space：用模式 A；否则用模式 B。
2. 用户确认清单后，`filtered.json` 按“主力类型在前、边界类型在后、同类按挂牌粉丝从高到低”排好，再写分配表：

   ```powershell
   python scripts/collect/make_assignment.py --config $cfg --mode B --profile dy-A={PROFILE_DY} --profile dy-B={PROFILE_DY} --profile xt-A={PROFILE_XT} --profile xt-B={PROFILE_XT}
   ```

   模式 A 加 `--mode A --space-id dy-A=<id> ...`；重写时加 `--force`（先确认没有代理在用）。
3. 号多时写 `{WORK_DIR}\listing\groups.json`（WORKFLOW 4.3 节）：第 k 组取 `dy-A`、`dy-B` 各自 `ids` 的第 5k+1~5k+5 个。

   ```powershell
   $a = Get-Content {WORK_DIR}\locks\assignment.json -Raw -Encoding utf8 | ConvertFrom-Json
   $A = @($a.agents.'dy-A'.ids); $B = @($a.agents.'dy-B'.ids); $g = @()
   for ($k = 0; $k * 5 -lt [Math]::Max($A.Count, $B.Count); $k++) {
     $ga = @($A | Select-Object -Skip ($k*5) -First 5); $gb = @($B | Select-Object -Skip ($k*5) -First 5)
     $g += [ordered]@{ name = "g$($k+1)"; ids = @($ga + $gb); A = $ga; B = $gb }
   }
   ConvertTo-Json @($g) -Depth 4 | Set-Content {WORK_DIR}\listing\groups.json -Encoding utf8
   ```

4. 红狐试查一个号：`python scripts/collect/redfox_batch.py --config $cfg <第一个号>`。不通就停下请用户核对密钥（WORKFLOW 6.10 节）。

### 5.3 登录自检不过：换 profile（任何时候）

按 WORKFLOW 5.3 节“换 profile”做：

1. 用户确认正确的 profile 后，改 `assignment.json` 里该代理的 `profile`，`space` 名加后缀（例如 `{BATCH}-dy-A-p2`）。
2. 改该代理的锁文件：旧的 `spaceId`、`page`、`space` 移进 `oldSpaces`（带时间），`spaceId`、`page` 置为 `null`，保留 `done`。
3. 暂停开关：先把 `locks\PAUSE-douyin.flag` 的原文复制到 `logs\pause-<时分>.txt`，再删除。
4. 看日志时间，列出在未登录状态下处理过的号，从 `done` 里移出（或续派时用 `--force-ids`）。
5. resume 同一个代理：“已换 profile，space 名改为 …；先重做登录自检；以下号要重做：…”。

### 5.4 每组验收（第 5 步）

1. 按 `checklists.md` D 节验收两个抖音代理本组的产出，看两张裁剪对照图，抽查 3 张打码截图。
2. 写 `{WORK_DIR}\locks\checkpoints.json`（追加一条）：组名、完成时间、每号必做项状态（可先跑 `python scripts/analyze/check_coverage.py --config $cfg` 看 1~7 项）、问题。
3. 向用户汇报这一组：完成的号、发现的问题、对照图链接；第一组做完时按实际用时估算全部完成时间。
4. 用 resume 给两个抖音代理发 2.1 节的续派消息（同一账号时 B 晚 1~2 分钟）。

### 5.5 合并、分析、报告（第 6~8 步）

```powershell
python scripts/analyze/merge_collect.py --config $cfg
python scripts/collect/crop_check.py --config $cfg          # 全部号的裁剪对照图 progress\crop-check.jpg
python scripts/analyze/check_coverage.py --config $cfg
```

1. `coverage.csv` 的 1~7 项和截图证据缺的，打回给对应代理（resume），或补例外证据。
2. 写 `qual.json`（WORKFLOW 6.12 节）：每号 `content`、`content_ok`、`portrait`、`portrait_ok`、`brush`、`risks`、`summary`；批次文字写 `notes`。`summary` 建议不超过 70 字；`risks` 前 2 条每条建议不超过 45 字。
3. 星图抹水印：`python scripts/report/xt_dewatermark.py --config $cfg --check`（采集时已裁过顶部的批次加 `--precropped`）。打开 `{PREVIEW_URL}/progress/xt-dewm-check.jpg`，认不出字才算过。
4. 先出 HTML 给用户审：`python scripts/build_report.py --config $cfg --no-pdf --check`。看自检产出（简约：`crop-check.jpg`、`chk-<id>` 页数、`m-NN.jpg` 溢出；复杂：`mshot.py ... report-full.html d 1280`），按 `checklists.md` I~K 或 P 节核对；再跑一次 `check_coverage.py`，8 项都齐。
5. 发 HTML 链接和 2~3 张截图链接请用户审。改了 `qual.json` 或数据就重跑第 4 步的命令。
6. 用户通过后出 PDF：`python scripts/build_report.py --config $cfg --skip-analyze --check`（复杂模式加 `--mode full`）。看 `pdfm-sheet` 或 `pdf-a4-sheet` 的低填充页，按 `checklists.md` L 或 P 节核对。每号超过 2 页的按 WORKFLOW 8.4 节改 `qual.json` 后重跑。

### 5.6 交付和收尾（第 9 步）

1. `python scripts/tools/snap_overview.py --config $cfg` 生成 `{PREVIEW_DIR}\progress\overview-full.jpg`。
2. 按 WORKFLOW 11.3 节写交付消息，写明用的是哪种报告模式。
3. 关闭代理 space（包括换 profile 留下的 `oldSpaces`）。只关代理的，用户的窗口不动。

   模式 B：写 `{WORK_DIR}\close-spaces.mjs` 后运行：

   ```js
   import fs from "node:fs";
   const W = "{WORK_DIR_URL}";
   for (const n of ["dy-A", "dy-B", "xt-A", "xt-B"]) {
     const p = `${W}/locks/${n}.json`;
     if (!fs.existsSync(p)) continue;
     const lock = JSON.parse(fs.readFileSync(p, "utf8"));
     const ids = [lock.spaceId, ...(lock.oldSpaces || []).map((o) => o.spaceId)].filter((x) => x != null);
     for (const id of ids) {
       const task = await taskSpace(id).catch(() => null);
       if (!task) { console.log(n, id, "已不存在"); continue; }
       if (task.ownership === "user") { console.log(n, id, "是用户的 space，跳过"); continue; }
       await task.finish({ keep: [] });
       console.log(n, "已关闭", id);
     }
   }
   ```

   模式 A：各代理已经 `handOff()`，不调用 `finish()`。
4. 把本批 `filtered.json` 里的号加进历史名单。
5. 停掉 10 分钟进度定时器。

### 5.7 子代理失败后续做（任何时候）

网络中断会让所有子代理同时失败。不要重新派发，按下面做：

1. 查产出：

   ```powershell
   cd {WORK_DIR}
   Get-ChildItem locks\*.json | ForEach-Object { $_.Name; Get-Content $_ -Raw -Encoding utf8 }
   Get-ChildItem logs -File | Sort-Object LastWriteTime -Descending | Select-Object -First 10 Name,Length,LastWriteTime
   Get-ChildItem listing\rows_img*.jsonl -ErrorAction SilentlyContinue | ForEach-Object { "$($_.Name) $((Get-Content $_ -Encoding utf8 | Measure-Object -Line).Lines) 行" }
   ```

2. 用分离进程启动的浏览器脚本可能还在跑：看它的日志最后修改时间，等它停了再续做。
3. 用 Task 的 `resume` 填原子代理的 id，`run_in_background: true`，消息用这个模板：

   ```text
   网络中断后续做。不要从头做，也不要覆盖已有结果。
   已完成：{已完成的号、横条或步骤}
   从这里继续：{下一个号、横条或步骤}
   先读：{锁文件路径}、{产出文件路径}，确认已完成的部分再接着做。
   其余要求和原任务相同。
   ```

4. resume 失败、且旧任务心跳超过 10 分钟没更新时，才用原提示词加上面这段说明派新代理，输出路径不变。
5. 续做完成后按 `checklists.md` O 节核对：没有重复行、重复号，旧结果没有被覆盖。
