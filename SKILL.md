---
name: douyin-account-research
description: 收购抖音号前的粉丝质量调研。用户发来卖家挂牌截图、要筛号并核实粉丝真假、互动和画像、给出 A/B/C/D 评级和购买建议、交付 HTML/PDF 报告时使用；需要 ego-browser 里已登录的抖音网页版和巨量星图窗口，以及红狐数据密钥。
---

# 抖音账号粉丝质量调研

你是主 agent：负责和用户沟通、派子 agent 采集、验收、写定性判断、生成报告。细节都在 `docs/`，这里只列启动顺序、硬规则和入口。

## 启动顺序

1. **问报告模式**：先在正文里给出两种模式的样张链接（`examples/output/`），每个配一句说明，再用 AskQuestion 问“简约模式（默认）还是复杂模式”。没回答就用简约模式。两种模式的采集内容完全一样。
2. **问 profile**：用 AskQuestion **分别**问“抖音登录在哪个 profile”“星图登录在哪个 profile”。推断结果只能作默认选项。同时问：两个抖音窗口是不是同一账号、报告节奏（全部做完出一份总报告，还是每组一份）、红狐积分上限。提醒用户不要最小化代理的窗口。
3. **启动 10 分钟进度定时器**：之后每次被唤醒都汇报进度，并附最新截图链接（WORKFLOW 5.6 节）。
4. **筛选**：按图拆给多个转录 agent，逐条追加写盘；按批次配置的 `listing_filter` 筛选。用户补充剔除词时，对全部行重新应用全部词。先发清单链接，再请用户确认（WORKFLOW 第 1 节）。
5. **分组**：写批次配置；`filtered.json` 主力类型在前。用 `make_assignment.py` 分 A/B，每组 10 个号写进 `groups.json`。红狐先试查一个号（WORKFLOW 4.3、5.3、6.10 节）。
6. **派采集**：同时派 5 个后台子 agent：抖音 A、抖音 B（每组各 5 个号）；星图 A、星图 B（全部号）；红狐。代理先做登录自检，不过就停。每组验收后写检查点、汇报，再 resume 同一个抖音 agent 做下一组（`docs/prompts.md`）。
7. **分析**：依次运行 `merge_collect.py`、`check_coverage.py`；亲手写 `qual.json`；运行 `xt_dewatermark.py --check` 给星图截图抹水印（WORKFLOW 6.12 节）。
8. **报告**：`python scripts/build_report.py --config <batch.json> [--mode full] --no-pdf --check` 出 HTML，请用户审；通过后去掉 `--no-pdf` 出 PDF（WORKFLOW 6.13 节、第 8 节）。
9. **交付**：先说结论（几个号、各级几个），写明报告模式；附 HTML、PDF 和总览截图链接。关闭代理的 space，停掉定时器（WORKFLOW 第 11 节）。

## 硬规则

- 每个号 8 项必做调研一项不能少；确实拿不到的要有证据（WORKFLOW 第 3 节）。
- 只读：不关注、不点赞、不评论、不私信，不下单、不邀约。遇到验证码、登录弹窗就停下汇报，不替用户登录。
- 用户的窗口不关、不登出、不最小化或恢复，不清 cookie。子 agent 不调用 `finish()`，收尾由主 agent 统一做。
- 一个窗口只给一个 agent；一个输出路径只派一个 agent；子 agent 一律后台派发。网络中断时先查产出，再 resume 同一个 agent 续做。
- 密钥只放环境变量 `REDFOX_API_KEY`，不写进文件、日志、报告和聊天。
- 隐私：截图里的昵称和头像打码；星图截图裁掉顶部登录名（只裁一次），并在本地抹掉水印，不绕过平台的防篡改机制。报告里不出现人名、接口名和状态码。
- 脚本直接在仓库里用 `--config` 运行，不从旧批次复制脚本。子 agent 对仓库脚本只读。
- 先给素材链接再提问。聊天里不能内联图片，只发链接。

## 入口

| 要做什么 | 看哪里 |
|---|---|
| 完整流程、指标与评级、报告规范、踩坑 | `docs/WORKFLOW.md` |
| 每个阶段怎么验收 | `docs/checklists.md` |
| 派子 agent 的提示词、派发顺序表 | `docs/prompts.md` |
| 主页截图怎么拍、怎么裁 | `docs/CROP_RULE.md` |
| 每个脚本的用途和命令 | `scripts/README.md` |
| 批次配置模板（含剔除词表） | `config/batch.example.json` |
| 跑通示例 | `python scripts/build_report.py --config examples/demo-batch/batch.json --mode both --check` |
