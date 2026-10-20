# REVIEW.md — 给审查者的一页说明

这是一个 agent skill 包（`paper-atlas`），不是普通应用。审查前请先知道它想解决什么、哪些是刻意的取舍。

## 一句话

把一篇 CS 论文读成一张可重开的"地图"（主张 / 痛点 / 创新点 / 因果链 / 选择点 / 图表证据），在你点头之后把关键句子写回 PDF，成为 Zotero 桌面端能导入的高光与批注。

## 怎么跑

```bash
python -m pip install -r requirements.txt
python -m pytest -q                 # 114 个测试，约 3 秒
python scripts/doctor.py            # 环境自检
```

`work/` 和 `paper-atlas/` 是运行产物，已被 git 忽略；仓库里没有 PDF（版权与体积），
想跑端到端需要自备一篇论文的 PDF。

## 先读哪几个文件

1. `SKILL.md` —— skill 本体，硬规则、工作流、Voice、质量门槛都在这里。
2. `README.md` / `README.zh-CN.md` —— 安装、两步写回、排错。
3. `reference/map-schema.md` —— `map.json` 字段。
4. `reference/example-nice-slam.md` —— 完整样例（CV / SLAM）。
5. `reference/example-lora.md`、`reference/example-vllm.md` —— 另外两个方向（NLP、系统）的样例，
   用来看这套结构在非视觉论文上是否成立。
6. `docs/superpowers/specs/2026-10-17-paper-atlas-design.md` —— 设计文档（为什么这么切）。
7. `docs/superpowers/plans/2026-10-18-paper-atlas.md` —— 实现计划与每个任务的验收点。
8. `docs/pressure-test.md` —— 有 skill 与无 skill 两个 agent 的对照结果。

## 刻意的取舍（不是遗漏）

- **只做零设置路径**：写标准 PDF 高光，Zotero 打开时自动导入为只读外部批注；用户点一次「文件 → 导入批注」才变成可编辑批注。Web API 与自动建子笔记是 v2。
- **不写 `zotero.sqlite`**：只通过只读快照读库。
- **不翻译、不重排 PDF**：批注锚在原文文字层，翻译插件叠在上层不影响锚点。
- **默认 20 条高光**：宁可少而准。
- **推断必须标注**：`alternative` / `cost` / `strength` 允许是推断，但要标 `*_inferred` 并给出 `basis_quote`，且不进高光。
- **只测过 Windows + Zotero 10.0.2**：代码是 pathlib/stdlib，macOS/Linux 未实测。

## 文字风格

批注和地图正文的规则写在 `SKILL.md` 的 Voice 一节，是**本 skill 自己的规则**：禁比喻、禁短句下判断、
禁冒号揭晓、禁翻案腔。`lieflat-less-ai-tone`（如果装了）是一份更窄的清单，只处理 AI 腔的典型特征，
并且明确保护比喻与长短句节奏——它不能替代 Voice 一节，只能补充。如果你觉得仍有 AI 味，直接指到具体
句子即可；`reference/example-nice-slam.md` 里有二十条批注原文可对照。

## 特别想被挑的地方

1. **锚定精度**：`anchors.py` 的降级阶梯（去连字符 → 归一化 → 取最紧凑一处）在真实两栏论文上够不够稳；多命中判定的阈值合不合理。
2. **评论的"人味"**：`SKILL.md` 的 Voice 一节是否真的能约束出像人写的批注，还是仍会滑回报告腔。
3. **痛点 / 创新点两节是否够锋利**：`reference/example-nice-slam.md` 里那两张表，是不是比一份普通总结多说了一层东西；创新点的「原样复用 / 借鉴后改 / 新造」这一列会不会被 agent 敷衍成整列"新造"。
4. **中英双语**：英文路径是否只是中文规则的翻译。注意 `--lang` 只切换标题与批注模板，不翻译正文——英文请求要求 agent 直接把正文写成英文。
5. **幂等与副作用**：重复 `--apply`、`--force`、备份、以及"先征得同意"这条规则在实际 agent 手里守不守得住。
6. **与无 skill 的差距**：`docs/pressure-test.md` 里那个基线其实很强——如果你认为差距不够大，直接说该砍掉哪一节、该加哪一节。

## 2026-10-19 审查之后的改动

Codex 的审查报告（`work/audit-20261019/`）指出"引用正确、推断身份、高亮范围"都还没有保证。已改：

- **负号消失**：`_match_key` 以前删掉所有连字符，`by -1 points` 会被 `by 1 points` 认证通过。现在只还原行末断词，数字里的连字符保留；`pre-trained` 仍能匹配 `pretrained`。
- **单行矩形**：一个公式或上标不再把高光拉到下一行；行末断词的两半各用一个矩形，不再框住相邻栏。
- **推断身份**：`strength` 的 `inferred` 与 `quote` 互斥，判错；`annotate` 把 `（推断）` 写进批注（写了 `note` 也保留）。
- **逐条校验**：pain / novelty 的 `quote`、concepts 的 `basis_quote`、figures 的 `evidence_quote` 都要在 PDF 里找得到。
- **数字**：地图里出现的每个数字都必须在 PDF 里出现，`999999 percent` 这类直接拒。
- **id 唯一、跨页依据、密度**：重复 id 报错；`basis_page` 自动回填真实页码；同一 PDF 的二次标注把已有批注计入 20 条上限。
- **过长批注**：不再静默截断（截断会切掉最后的 caveat），改为报错要求改写。
- **大小写与词边界**：`WE PROPOSE` 与 `We propose` 算两次出现，歧义引文会被拒；`method` 不再命中 `methodology` 里的子串。
- **英文回声检查**：批注与引文过近时 Zotero 会清空批注，现在两种语言的模板都会检查。
- **样例**：NICE-SLAM 的"解码器全部冻结"改成"几何解码器冻结、颜色解码器从头训练"；LoRA 的"不必重调"改成"降低重新调参的需求"；创新点改用 `origin` 三值。
- 复跑审查脚本的结果在 `work/audit-20261019/code-review/results-rerun.json`：每一条探针现在都按预期失败或拒绝。

## 已知未验证

- Zotero 的 **文件 → 导入批注**（外部批注转可编辑批注）只在源码层面确认过，没有 GUI 实测记录，见 `docs/superpowers/specs/m0-result.md`。
- 扫描件、非 CS 领域、多篇综述都在非目标里，没有测。

## 输出建议

按严重程度给结论即可：哪些会让人用错、哪些只是不好看。不用重写代码。
