# 分账号详情 ② 账号首页截图：裁剪规则

## 1. 最终规则

- **固定用 3 条**：裁“账号信息 + 第一排前 3 条作品”（`mode='3'`），手机 PDF 和 HTML 都用这一张。
- 理由：手机 PDF 正文宽约 358px。6 条版原图宽 1076px，缩到 358px 后关注/粉丝/获赞一行字高不到 5px，抖音号约 3.7px，已经看不清；卡片只有约 54px 宽，点赞数也认不出来。3 条版原图宽 538px，在 260px 宽度下昵称字高约 9px，关注/粉丝/获赞约 7px，抖音号约 5px；按 2 倍像素导出，放大即可看清，缩略图仍能辨认；同时还能保住 2 页。关键数字在 ① 账号卡片里另有大字显示。
- `mode='6'` 只给宽版式备用：显示宽度至少 720px，比如 A4 或桌面整页报告。目前没有版式使用它。

## 2. 裁剪边界定义

按内容定位，不用死坐标（`parts/crop_profile.py` 的 `detect()`）。以下像素值都以“1280 宽视口、设备像素比为 1”的截图为准，其他宽度按 `k = 截图宽 / 1280` 等比换算。

| 边 | 定义 | 本批实测（1280×860） |
|---|---|---|
| 锚点 | “作品 N”标签下的红色下划线：在图片上半部分中，第一条连续 2 行以上、长 40–150px 的红色横线（R>190、G<100、B<140）| y=271，x=190 |
| 左 | 下划线左端 x0 − 8（卡片间距 17px 的一半）| 182 |
| 上 | 头像顶 − 10。头像顶 = 下划线 y − 191，再用头像像素检测校验，两者相差 12px 以内时取检测值 | 69–70 |
| 右 | 第 N 张卡片右边 + 8。卡片左右边界按列判断：缩略图带里有像素与背景色不同的列算卡片列，相邻间隙 ≤ 8px 的合并。第一排不足 N 张时按网格补齐（间距 179.2px，卡片宽 163px）| 3 条：720；6 条：1258 |
| 下 | max(标题行底, 缩略图底 + 26) + 8，且不超过第二排顶 − 3。“第二排顶”= 连续 30 行以上超过一半像素不是背景色的位置 | 580 |

- 背景色取下划线下方 4–10px 的中位数，本批是 RGB(22,24,35)；像素与背景色在任一通道上差值超过 14 即视为“非背景”。
- 结果：3 条版裁剪框 538×511（1280 坐标 182,69 到 720,580），6 条版 1076×511；10 个号完全一致。
- 无标题行的号：按标题行高度补齐，各号裁剪高度保持一致，底部是 26px 深色空白。

## 3. 显示尺寸

| 场景 | 宽度 | 对齐 | 实现 |
|---|---|---|---|
| 手机 PDF（390×844，正文约 358px） | **260px** | 在正文里水平居中 | `@media print{.adet .ad-shot{width:260px}}`，即 `SHOT_PDF_W = 260` |
| HTML（屏幕） | `min(100%, 400px)` | 在 640px 宽的栏内居中 | 外层 `.ad-shotw{max-width:640px}`，图片 `.ad-shot{margin:0 auto}` |

- 导出：JPEG，质量 80，像素宽 = 260 × 2 = **520px**（3 条版 520×494；0 作品版 520×240）。只缩小，不放大。
- 外观：1px 边框 `#DEE0E3`，圆角 10px，底色 `#16161E`。图片带 `width`/`height` 属性，CSS 为 `width:100%;height:auto`。
- 说明写在小标题里：`② 账号首页截图` 后跟灰色小字“账号信息 + 前 3 条作品 · 点图看整页”（0 作品号为“账号信息 · 0 作品 · 点图看整页”）。点图打开 `<aid>/dc-01-profile.jpg` 整页截图。图下不再单独放说明条。

### 2 页约束和配套微调

截图块从约 157px 高变成约 249px 高。分页时结论头部（`.ad-vh`）不能拆开，截图块必须足够矮，结论头才能留在第 1 页。为此同时做了这些微调（都在 `build_detail_m.py` 的 CSS 和 `timeline()` 里）：

- `.adet h3` 外边距 14/7 → 11/7；`.ad-basis` 上边距 10 → 8；`.ad-adv` 上边距 8 → 6；`.ad-risk` 上边距 6 → 4。
- 时间线图：`squash_chart()` 把绘图区（y 36–114）压到 0.75 倍高，字号和横向坐标不变；`viewBox` 从 `0 0 360 140` 变为 `0 3 360 111.5`；SVG 显示宽度 92%、居中；`.chv-fig` 下边距 10 → 6。
- 速览卡片：`.qk` 内边距 6/7/7 → 5/7/6；`.qk-h` 下边距 4 → 3；`.qk-l` 行高 1.55 → 1.5；`.qk-grid` 下边距 12 → 8。
- 评级依据：`.ad-bh` 下边距 6 → 4；`.bt-grid` 间距 5 → 4；`.bt-t` 内边距 4/6/5 → 3/6/4；“主要风险”条目行高 1.55 → 1.5。
- 佐证截图：去掉单独的“佐证截图”小标题，改在 ④ 的标题后加灰色小字“末行为佐证截图 · 点图可放大”；缩略图比例 16:9 → 11:5。

样本号实测余量：第 1 页约 11px，第 2 页约 50px。截图宽度试过 280px：结论头会被挤到第 2 页，总页数变成 3 页。第 1 页的余量取决于截图高度，所以 `SHOT_PDF_W` 不要超过 260。

第一批 10 个号都按这套规则临时渲染过（分段文件写在 C 盘临时目录，没有改动 `parts/detail_m` 里其他号的文件）：**全部 2 页**。分页位置都是“第 1 页到结论摘要为止，第 2 页从购买建议开始”。第 1 页结论摘要底边最低在 791/802px（样本号）；第 2 页最长 783/802px（其中一个号），余量约 19px。

其他号如果超过 2 页，按这个顺序处理：① 截短“主要风险”条目文字；② 再压图表高度；③ 最后才把 `SHOT_PDF_W` 降到 240。截图本身不再裁短，必须保住“账号信息 + 前 3 条作品”的完整性。

## 4. 采集截图要求（以后批次）

1. **视口**：`Emulation.setDeviceMetricsOverride { width: 1280, height: 860, deviceScaleFactor: 1, mobile: false }`（与 `round-47.mjs` 相同）。设备像素比可以设为 2，检测会按 `k` 换算。**CSS 视口宽度必须是 1280**：宽度一变，侧栏和网格的列宽就会变。脚本检测到卡片间距与 179px 不符时会警告。
2. **左侧栏保持展开**（默认状态）：内容区左边界在 x=190。
3. **截图前滚到顶部**：`window.scrollTo(0, 0)`。头部和第一排都要完整出现在视口里，第一排标题行底在 y≈580，小于 860。
4. **等缩略图加载完再截**：打开主页后至少等 6 秒，再确认第一排卡片里的图片都已加载：`img.complete && img.naturalWidth > 0`。没加载完时第一排是灰块，检测会把它当成“没有卡片”。
5. **截图前清场**：关掉登录弹窗、粉丝列表弹窗和各类提示条；把鼠标移到页面空白处，比如 (60, 800)，避免卡片悬停时出现预览或放大。
6. **存无损 PNG**：存为 `shots_clean/<aid>/01-profile.png`。截取视口范围，不用 `fullPage`。裁剪始终从这张原图出发，`dc-01-profile.jpg`（1100 宽压缩图）只作备用来源，检测误差约 ±5px。
7. 旧的 `shots/<aid>/01-profile.png`（1908×943，视口不同）**不适用**。

## 5. 采集时直接用页面元素位置裁剪（可选，需在采集时验证）

现有采集脚本里，主页上只验证过 `[data-e2e="user-info-fans"]` 这一个选择器。`[data-e2e="user-info"]`、`[data-e2e="user-post-list"]`、`[data-e2e="scroll-list"]`，以及“卡片 `li` 是否包含标题行”，都**需在采集时验证**；所以下面的 JS 都带兜底逻辑。返回的 `css` 框可以直接传给 ego-browser 的 `page.screenshot({ path, clip })`，它用 CSS 像素。如果是对整页截图做后期裁剪，就用 `px` 框（已乘设备像素比）。

```js
// ego-browser：const r = await page.evaluate(PROFILE_CLIP, 3);  // 3 或 6
// 截图：await page.screenshot({ path: `${dir}/01-home.png`, clip: { x: r.css.x, y: r.css.y, width: r.css.width, height: r.css.height } });
const PROFILE_CLIP = (N) => {
  const pad = 8;
  const R = (el) => el.getBoundingClientRect();
  window.scrollTo(0, 0);
  // 头部资料区：优先 data-e2e="user-info"（需验证）；兜底从粉丝数元素（已验证）往上找到含头像的祖先
  let head = document.querySelector('[data-e2e="user-info"]');
  const fans = document.querySelector('[data-e2e="user-info-fans"]');
  if (!head && fans) { head = fans; while (head.parentElement && !head.querySelector("img")) head = head.parentElement; }
  // 头像：页面上部最大的近似正方形图片
  const ava = [...document.querySelectorAll("img")].map((i) => R(i))
    .filter((r) => r.width >= 60 && Math.abs(r.width - r.height) < 4 && r.top < 400)
    .sort((a, b) => b.width - a.width)[0] || (head && R(head));
  // 作品卡片：作品列表里的 li（选择器需验证）；兜底用指向 /video/ 或 /note/ 的链接所在 li
  const list = document.querySelector('[data-e2e="user-post-list"]') || document.querySelector('[data-e2e="scroll-list"]');
  let cards = list ? [...list.querySelectorAll("li")] : [];
  if (!cards.length) cards = [...new Set([...document.querySelectorAll('a[href*="/video/"],a[href*="/note/"]')].map((a) => a.closest("li") || a))];
  cards = cards.filter((el) => { const r = R(el); return r.width > 80 && r.height > 80; });
  if (!ava) return { error: "找不到头部" };
  if (!cards.length) return { error: "第一排没有作品卡片（0 作品或未加载）" };
  const top0 = Math.min(...cards.map((el) => R(el).top));
  const row = cards.filter((el) => Math.abs(R(el).top - top0) < 10).sort((a, b) => R(a).left - R(b).left).slice(0, N);
  // 卡片下边含标题行：取卡片内所有可见后代的最大 bottom（li 不含标题时也能兜住）
  const bottomOf = (el) => Math.max(R(el).bottom, ...[...el.querySelectorAll("*")].map((c) => R(c)).filter((r) => r.height > 0).map((r) => r.bottom));
  const x = Math.floor(Math.min(ava.left, R(row[0]).left) - pad);
  const y = Math.floor(ava.top - pad - 2);
  const right = Math.ceil(R(row[row.length - 1]).right + pad);
  const bottom = Math.ceil(Math.max(...row.map(bottomOf)) + pad);
  const dpr = window.devicePixelRatio || 1;
  const css = { x, y, width: right - x, height: bottom - y };
  const px = { x: Math.round(x * dpr), y: Math.round(y * dpr), width: Math.round(css.width * dpr), height: Math.round(css.height * dpr) };
  // 头部文字跨过右边界时提示（比如认证说明很长）
  const over = head ? [...head.querySelectorAll("span,div,p,h1")].some((el) => el.children.length === 0 && el.innerText.trim() && R(el).right > right && R(el).left < right && R(el).bottom < top0) : false;
  return { n: row.length, dpr, css, px, warn: over ? "头部文字跨过右边界" : "" };
};
```

验证方法：在一个已知号上跑一次。用返回的 `css` 截图，再用 `crop_profile.py` 处理同一时刻的整页截图，两者的边界应相差不超过 3px。

## 6. 脚本与函数

- `parts/crop_profile.py`
  - `crop_profile(src, dst, mode='3', width=None, quality=80, debug=None) -> dict`：检测并裁剪，输出 JPEG。返回 `box`、`cards`、`titles`、`empty`、`warn`、`out_size`；`debug` 给路径时，会另存一张标出检测框的原图。
  - `detect(img, mode)`：只检测，不写文件。`contact_sheet(items, dst)`：拼对照图。
  - 单张：`python parts/crop_profile.py SRC DST --mode 3 --width 520`
  - 批量 + 对照图：`python scripts/report/crop_profile.py --dir <WORK_DIR>/shots_clean --out <PREVIEW_DIR> --mode 3 --width 520 --sheet <PREVIEW_DIR>\progress\crop-check.jpg`
- `parts/build_detail_m.py`
  - `SHOT_MODE = "3"`，`SHOT_PDF_W = 260`。
  - `head_crop(aid)`：来源优先 `shots_clean/<aid>/01-profile.png`，备用 `<PREVIEW_DIR>\<aid>\dc-01-profile.jpg`；输出 `<PREVIEW_DIR>\<aid>\dc-01-home.jpg`，返回 `(相对路径, 检测结果)`。
  - `section()`：生成 ② 的小标题说明和图片；CSS 写入 `parts/detail_m/detail.css`。
  - `squash_chart()`：压低时间线图的绘图区高度（见第 3 节）。
- `parts/sample_detail.py <aid>`：重出样本 `sample-detail.html`、`sample-detail-print.html`、`sample-detail.pdf`，页面图在 `progress/sample-detail-pN.jpg`。
- `pdf_sheet.py <pdf> <tag>`：缩略总览，并检查有没有填充不足 60% 的页。

## 7. 已知例外

- **0 作品号**（第一批有 1 个）：第一排没有卡片，只裁到“作品 0”标签栏和筛选条（538×248，导出 520×240），小标题说明改为“账号信息 · 0 作品”。“暂无内容”的空状态图标在内容区正中，3 条版的宽度会把它切成两半，所以不裁进来。
- **无标题行的号**（第一批有 3 个）：卡片下没有标题，底部按标题行高度补齐，留 26px 深色空白，与其他号等高。
- **长认证说明**（第一批有 1 个）：头部右端到 x≈704，仍在 720 的边界内。以后如果超出边界，脚本会警告“头部有文字跨过右边界”；这时人工确认，必要时把这个号改用 `mode='6'` 的宽图，或接受截断（① 卡片里已有完整信息）。
- **第一排不足 3 条**（作品数 1–2）：右边界按网格补齐，保持宽度一致，右侧留出深色空位；脚本会给出警告。
- **头像顶部偏暗**（第一批有 1 个）：头像边缘和背景色很接近，所以检测阈值放得很低（一行里有 3 个非背景像素即算头像顶）。如果检测值偏离“下划线 y − 191”超过 12px，比如头像图片整片发黑，就改用锚点值。
- **截图没滚到顶，或下划线被弹窗遮住**：检测失败，报“找不到红色下划线”。这时按第 4 节的要求重新采集。

## 8. 验收清单

- 对照图 `progress/crop-check.jpg`（带检测框的版本：`progress/crop-check-box.jpg`；3 条与 6 条对比：`progress/crop-3v6.jpg`）：每张都有完整的头像、昵称、关注/粉丝/获赞、抖音号/标签行，以及“作品 N / 推荐 / 喜欢”和“作品/合集/短剧”；第一排 3 张卡片完整，带点赞数和标题行；右侧没有半张卡片，底部没有第二排。
- 样本 PDF 为 2 页，`pdf_sheet.py` 没有报告填充不足 60% 的页。
