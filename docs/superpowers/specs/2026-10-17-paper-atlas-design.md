# Paper Atlas — 论文地图 skill 设计文档

日期：2026-10-17
状态：待审阅（v2，已并入构建者审阅）
作者：与用户共同完成（对话式设计）

---

## 1. 这是什么，为什么

一个可分发、可复用的 skill：把一篇计算机方向的论文，读成一张**地图**——主张、因果链、选择点、图表证据——并把地图上的关键位置**写回原文**，成为 Zotero 里的高光和批注。

触发这件事的具体场景：用户在读 NICE-SLAM（CVPR 2022）时，词汇都认识，但说不清"作者为什么非得这么做"，以及"哪张图在替哪句话作证"。读完留不下骨架，回头查的时候只能重读。

所以这个 skill 的价值不在"总结"，在**结构 + 出处**：每一条结论都能点回原文某句话。

## 2. 目标 / 非目标 / 反目标

**目标**
- 给定一篇论文（优先从 Zotero 库里定位 PDF），产出一份可反复打开的地图。
- 地图的每一节都能追溯到页码与原文引文；推论明确标成推论。
- 生成一批锚定在原文的高光与批注，颜色区分角色，总量受控。
- 中英文用户都能用：地图、批注、文档双语可切换。
- 安装即用：clone 进 skills 目录，跑一次 doctor，然后就能用。

**非目标（v1）**
- 不做多篇论文的综述 / 领域脉络图谱。
- 不做通用领域（医学、社科）的适配；先只做 CS，方法/实验结构强的论文。
- 不做扫描件 OCR。
- 不做 Zotero 插件；不替代用户的阅读。
- 不做 Zotero Web API 写入（见 §5.4）。

**反目标（就算做出来了也算失败）**
- 产出一份"看起来很像总结"的泛泛而谈，读者看完还是不知道为什么。
- 批注锚错位置，或者高光划在了不相干的句子上——比没有批注更伤信任。
- 地图和批注各说各话：地图说"选择 A 解决遗忘"，原文高光却划在引言。
- 满纸高光，等于没有高光。
- 需要用户手动改配置才能跑起来。

## 3. 用户与场景

- **主要用户**：读 CS 论文的研究生 / 工程师，用 Zotero 管文献，英文论文为主，母语中文。
- **次要用户**：英文母语用户，同样的工作流。
- **使用时刻**：读完第一遍、想搞清骨架时；或者写 related work、要快速判断"这篇的选择和代价"时。
- **环境**：Zotero 7+（实测环境 Zotero 10.0.2 / Windows），Python 3.10+，本机有 PDF。macOS / Linux 从设计上支持，但 v1 的发布说明只承诺 Windows 实测。

## 4. 用户已经定下的决定

| 决定 | 内容 |
|---|---|
| 领域 | 先做计算机论文 |
| 成品形态 | 地图：可反复打开、可对照原文回看，不是一次对话 |
| 交付方式 | 完整开源包（GitHub），clone 即用 |
| 语言 | 中英都要 |
| 翻译兼容 | 必须与 Zotero 的翻译插件共存，翻译前后批注不乱 |
| Zotero 写回 | 默认零设置；不要求 API key |

## 5. 我做的判断（构建者裁决，待用户否决）

1. **包名 `paper-atlas`**，仓库根目录就是 skill 目录（`SKILL.md` 在根），`git clone <repo> ~/.claude/skills/paper-atlas`（DSH 放 `~/.dsh/skills/`）一步到位。
2. **写回分两段，零设置**：
   - 第一段（自动）：`annotate.py` 把标准 PDF 批注写进文件，并带上 Zotero 认的私有键（§7.5）。重新打开 PDF，Zotero 会把它导入为**外部批注**：能看、能读、能加进笔记，但只读、不按条目同步。
   - 第二段（一次性点击，可选）：Zotero 阅读器里的 **文件 → 导入批注**，会把这些批注转成 Zotero 自己的、可编辑、可同步的真批注，同时把它们从 PDF 里剥离。不需要 API key。
   - 两段都写在 README 的第一屏，用户第一次就知道"看完还能升级"。
3. **API key 不进 v1**。可编辑批注靠上面那次点击就能拿到；只有"自动创建子笔记"才真需要 Web API，留到 v2。
4. **地图 v1 只有 Markdown 文件**。Zotero 里的笔记，用原生"从批注创建笔记"补上——那是 Zotero 自带能力，不用我们写。
5. **不产出译文 PDF**，永远只锚原文件（见 §9）。
6. **幂等**：重复运行不产生重复批注。写入前查两处：PDF 里已有的 `Paper Atlas` 私有键、`zotero.sqlite` 里同一 attachment 下已有的 Paper Atlas 批注；命中则跳过，`--force` 才重写（先删后写）。

## 6. 地图长什么样

固定七节，标题双语：

1. **一句话主张 / The Claim** — 一句话，形如"用 X 换掉 Y，因为 Z"。
2. **因果链 / The Chain** — 编号推理链：前人做法 → 失效点 → 因此需要什么 → 本文怎么做。每节带 `[p.N]` 与原文引文。
3. **选择点 / Decision Points** — 表格四列：选择 / 本可以怎么做 / 解决了什么 / 代价是什么。**"本可以怎么做"是核心列**，没有它，选择就退化成描述。
4. **图表证据 / Evidence Map** — 每个 Figure/Table 一行：回答什么问题、支撑哪条主张、关键数字、**它没证明什么**、页码。
5. **证据强度 / How Strong** — 哪些对照是作者自己复现的（如 iMAP\*）、缺了什么实验、结论能不能外推。
6. **前置概念 / Prerequisites** — 3–5 个读懂本文必须的概念，各一句话 + 在原文哪里出现。
7. **术语表 / Terms** — 论文用词与中文对照，含缩写。

**高光密度**：每篇默认上限 **20 条**——因果链每个节点 1 条、每个选择点 1 条、每张图表 1 条、存疑最多 3 条、主张 1 条。请求"更详细"时上限放宽到 30，仍不逐句高光。

## 7. 技术设计

### 7.1 包结构

```
paper-atlas/
├── SKILL.md                 # 触发描述 + 工作流 + 质量标准（英文，术语双语）
├── README.md                # 英文安装与用法（第一屏写清两段写回）
├── README.zh-CN.md          # 中文安装与用法
├── scripts/
│   ├── doctor.py            # 自检：python/依赖/zotero 库/PDF 可写/版本
│   ├── find_paper.py        # 只读 zotero.sqlite → 条目 + PDF 路径
│   ├── extract.py           # PDF → structure.json + 图表裁图
│   ├── verify_quotes.py     # 校验引文真实存在 + 推论标记合规
│   └── annotate.py          # map.json → PDF 批注（默认 dry-run，幂等）
├── reference/
│   ├── map-schema.md        # map.json 字段说明
│   └── example-nice-slam.md # 完整样例（也是验收用例）
└── tests/
    └── fixtures/            # 小型测试 PDF + 期望输出
```

（v2 才加 `zotero_api.py`。）

### 7.2 流水线

1. **定位** `find_paper.py "NICE-SLAM"` → 只读（`mode=ro` URI）查 `zotero.sqlite`，按标题/作者模糊匹配 → attachment 的 `storage:` 路径 → 真实 PDF。找不到就报错并请用户给路径，不静默。
2. **抽取** `extract.py paper.pdf --out work/` → `structure.json`：每页文本块（bbox、字号）、章节标题、图表题注、参考文献边界；并把每个题注附近的图像区域裁成 PNG（`work/figs/fig3.png`）。
3. **读** agent 读 `structure.json` 与裁图，产出 `map.json` + `map.md`。裁图让模型真的"看见"图，而不是只读图注。
4. **校验** `verify_quotes.py map.json` → 每条 `quote` 必须逐字存在（归一化空白/连字符）；`inferred: true` 的条目必须有 `basis_quote`。失败即阻断，让 agent 重取。
5. **写回** `annotate.py map.json --dry-run` → 报告条数、页码、矩形；确认后 `--apply`（先备份 `*.paper-atlas.bak.pdf`，默认只写可高光字段）。
6. **升级提示** 完成后打印一行：在 Zotero 里打开该 PDF →「文件 → 导入批注」，变成可编辑、可同步的批注。

### 7.3 map.json（机器可读的那份）

```json
{
  "paper": {"title": "...", "arxiv": "2112.12130", "zotero_key": "ABCD1234", "pdf": "..."},
  "claim": {"text": "...", "quote": "...", "page": 1},
  "chain":   [{"id": "c1", "step": "前人做法", "text": "...", "quote": "...", "page": 2}],
  "choices": [{"id": "d1", "choice": "...", "quote": "...", "page": 4,
               "alternative": "...", "alternative_inferred": true, "basis_quote": "...",
               "solves": "...", "cost": "...", "cost_inferred": true, "figures": ["fig2"]}],
  "figures": [{"label": "Figure 3", "page": 3, "bbox": [0,0,0,0], "crop": "work/figs/fig3.png",
               "question": "...", "supports": "d2", "key_numbers": "...", "caveat": "...",
               "caption_quote": "..."}],
  "strength": [{"text": "...", "inferred": true, "basis_quote": "...", "page": 6}],
  "concepts": [{"term": "...", "gloss": "...", "page": 2}],
  "limits":   [{"text": "...", "quote": "...", "page": 7}]
}
```

### 7.4 引文与推论的边界（核心规则）

- **可高光字段**（`claim`、`chain[].text`、`choices[].choice`、`figures[].caveat` 的证据部分、`limits[].text`）必须逐字引用，`verify_quotes.py` 把关。
- **推论字段**（`alternative`、`cost`、`strength`、`concepts[].gloss`）允许不在原文里直说——它们恰恰是论文通常不写的、也是这张地图最值钱的部分。但它们必须：
  1. 标 `*_inferred: true`，地图上显示"（推断）"；
  2. 附 `basis_quote`：这个推断是从哪句话推出来的，同样要逐字通过校验；
  3. **不进 PDF 高光**，只留在 map.md 里。
- 数字必须来自正文或表格；不估算、不四舍五入到"漂亮值"。

这样既保住反幻觉闸门，又没把最有价值的列砍掉。

### 7.5 锚定与批注

**锚定**：`quote` + 页号 → `page.search_for(quote)` 得到矩形。找不到时依次降级：去连字符 → 归一化空白 → 同段落 bbox；仍失败则**不写**，进报告要求改写引文（绝不猜坐标）。一处多命中时要求 agent 加长引文。

**批注字典**（Zotero 导入器的真实读法，已在本机 10.0.2 上核对）：

| PDF 键 | 用途 |
|---|---|
| `/Subtype /Highlight` | 类型 |
| `/Contents` | 批注正文（**必须与高光文本不同**，Zotero 会清空近似重复的评论） |
| `/C` | 标准颜色（兜底） |
| `/Zotero:Color` | Zotero 认的颜色 |
| `/Zotero:AuthorName` | `Paper Atlas`（**不是 `/T`**） |
| `/Zotero:Key` | 稳定 id：`pa-<paperkey>-<entryid>`，幂等与重写靠它 |
| `/NM` | 同上，兼容旧读法 |

| 角色 | 颜色 | 正文模板 |
|---|---|---|
| 主张 | 黄 `#ffd400` | `[主张] …` |
| 因果链 | 橙 `#ff6666` | `[链条 c1] …` |
| 选择点 | 绿 `#5fb236` | `[选择] 本可以: … ｜ 解决: … ｜ 代价: …` |
| 图表证据 | 蓝 `#2ea8e5` | `[图 3] 支撑: … ｜ 没证明: …` |
| 存疑 | 红 `#e56eee`→用 `#f19837` 橙红 | `[存疑] …` |

正文短于 200 字；长内容留在地图里，批注只放指路的那句。

### 7.6 双语

- `SKILL.md`、脚本英文；README 双语。
- 地图语言跟随用户：用户说中文则全中文（术语保留英文原词），英文用户则全英文。`--lang zh|en` 可强制。
- 批注正文同语言。翻译插件若要再翻译批注显示层，锚点不受影响（§9）。

### 7.7 失败与降级

| 情况 | 行为 |
|---|---|
| 找不到 Zotero 库 / 条目 | 明确报错 + 请用户给 PDF 路径 |
| PDF 无文字层（扫描件） | 检测后拒跑，提示 v1 不支持 |
| 图注识别不出 | agent 读页文本手工补 `figures[]`，标 `detected: manual` |
| 引文校验失败 | 阻断写回，要求重取 |
| Zotero 打开后看不到批注 | doctor 给排查清单（重开文件 / mtime / 是否只读锁定） |
| `importAnnotations` 未触发 | 提示手动「文件 → 导入批注」 |

## 8. 写回 Zotero 的事实依据（已核对本机源码与实测）

- `itemAnnotations.isExternal` 存在；`syncLocal.js` 明确不同步外部批注（PDF 文件同步会带着走）。
- `pdfWorker/manager.js` 在打开文件时调 `pdf.importAnnotations` 并逐条 `saveFromJSON`；`annotation.isExternal = !(transfer && annotation.transferable)`。
- `annotations.js`：`o.readOnly = o.isExternal || !isAuthor`。
- 阅读器「文件 → 导入批注」（仅在存在外部批注时可用）走 `transfer=true`：批注转成真批注（可编辑、可同步），并从 PDF 中剥离。
- 导入器读作者的键是 `/Zotero:AuthorName`；评论来自 `/Contents`；颜色优先 `/Zotero:Color`；ID 来自 `/Zotero:Key` 或 `Zotero-` 前缀的 `/NM`；只对已有外部批注去重；评论与高光文本近似相同会被清空。

结论：**零设置写批注 → 一键升级为真批注**，不需要 API key。这成为 v1 的承重路径。

**M0 仍需实测**：写进去的批注在 Zotero 10.0.2 上 100% 可见、评论正确、颜色正确、重开后无重复、点击导入批注能成功转换。

## 9. 翻译插件的硬约束

- 永不生成译文版 PDF；永不重排文字层。
- 锚点依赖原文件的页与矩形；任何改写原 PDF 的操作由 skill 明确劝阻。
- 地图与批注自带双语，不依赖事后翻译；用户若用 Translate for Zotero，它翻译批注显示层，不影响锚点。

## 10. 验收标准

拿 NICE-SLAM 当验收用例，必须同时满足：

1. `find_paper.py` 能定位到 PDF（或明确说明缺什么）。
2. 地图含 ≥5 个选择点、覆盖 ≥8 个 Figure/Table，每个选择点都有 `alternative`（推论则带 `basis_quote`）。
3. `verify_quotes.py` 通过率 100%（失败即阻断）。
4. `annotate.py --apply` 后重开 PDF：批注全部可见、正文非空且不等于高光文本、颜色语义正确、**再跑一次不产生重复**。
5. 用户点一次「导入批注」后，批注变成可编辑状态。
6. 断网、无 API key 可完成 1–5；`--lang en` 可产出全英文地图。

**M0 不过的退路（预先定好，按顺序）**：
1. 外部批注不被识别 → 放弃"写进 PDF"，改发 `map.md` + 一份可逐条粘贴的批注清单（仍能人工在 Zotero 里建）。
2. 只有部分识别（颜色/评论丢失）→ 降级为只用 `/C` 与 `/Contents`，退化颜色语义为文字前缀。
3. 都不行 → 不发版，回来找用户改架构。

## 11. 里程碑

- **M0 探针（半天）**：在本机 Zotero 10.0.2 上验证写回链路与 `search_for` 在两栏论文上的命中率。产出：通过/不通过报告。
- **M1 脚本**：doctor / find_paper / extract / verify_quotes / annotate，带 fixtures 测试。
- **M2 skill 正文**：SKILL.md 的工作流、提问时机、质量标准；map schema 与样例。
- **M3 端到端**：Nice-SLAM 全流程跑通，产出 `reference/example-nice-slam.md`。
- **M4 打包与文档**：README 双语、安装脚本、GitHub 发布说明。
- **M5 压力测试**：按 writing-skills 的 TDD 方式，用无 skill 的 subagent 跑同一任务看失败点，再验证 skill 能纠正。

## 12. 留给构建者的自由

脚本内部实现、错误文案、fixtures 构造、图注正则、Zotero 笔记的 HTML 样式、仓库元数据（license、CI）。

## 13. 用户已经确认的决定（2026-10-18）

1. **验收在 PDF 副本上跑**：不改动用户真实库；用户把副本临时拖进 Zotero，目视确认批注可见、颜色与评论正确。
2. **一次点击可接受**：写完后在 Zotero 里点一次「文件 → 导入批注」，把外部批注升级为可编辑、可同步的真批注；README 第一屏必须写清这一步。
3. 设计文档整体已获批准，进入计划阶段。
