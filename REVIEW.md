# REVIEW.md — 给审查者的一页说明

这是一个 agent skill 包（`paper-atlas`），不是普通应用。审查前请先知道它想解决什么、哪些是刻意的取舍。

## 一句话

把一篇 CS 论文读成一张可重开的"地图"（主张 / 痛点 / 创新点 / 因果链 / 选择点 / 图表证据），在你点头之后把关键句子写回 PDF，成为 Zotero 桌面端能导入的高光与批注。

## 怎么跑

```bash
python -m pip install -r requirements.txt
python -m pytest -q                 # 80 个测试，约 1.2 秒
python scripts/doctor.py            # 环境自检
```

`work/` 和 `paper-atlas/` 是运行产物，已被 git 忽略；仓库里没有 PDF（版权与体积），
想跑端到端需要自备一篇论文的 PDF。

## 先读哪几个文件

1. `SKILL.md` —— skill 本体，硬规则、工作流、Voice、质量门槛都在这里。
2. `README.md` / `README.zh-CN.md` —— 安装、两步写回、排错。
3. `reference/map-schema.md` —— `map.json` 字段。
4. `reference/example-nice-slam.md` —— 一份完整样例（NICE-SLAM），最好先看这个。
5. `docs/superpowers/specs/2026-10-17-paper-atlas-design.md` —— 设计文档（为什么这么切）。
6. `docs/superpowers/plans/2026-10-18-paper-atlas.md` —— 实现计划与每个任务的验收点。
7. `docs/pressure-test.md` —— 有 skill 与无 skill 两个 agent 的对照结果。

## 刻意的取舍（不是遗漏）

- **只做零设置路径**：写标准 PDF 高光，Zotero 打开时自动导入为只读外部批注；用户点一次「文件 → 导入批注」才变成可编辑批注。Web API 与自动建子笔记是 v2。
- **不写 `zotero.sqlite`**：只通过只读快照读库。
- **不翻译、不重排 PDF**：批注锚在原文文字层，翻译插件叠在上层不影响锚点。
- **默认 20 条高光**：宁可少而准。
- **推断必须标注**：`alternative` / `cost` / `strength` 允许是推断，但要标 `*_inferred` 并给出 `basis_quote`，且不进高光。
- **只测过 Windows + Zotero 10.0.2**：代码是 pathlib/stdlib，macOS/Linux 未实测。

## 文字风格

批注和地图正文按 `lieflat-less-ai-tone` 的规则清理过一遍（禁比喻、禁短句下判断、禁冒号揭晓、
禁翻案腔）。`SKILL.md` 的 Voice 一节是这套规则的精简版，供没装该 skill 的用户使用。如果你觉得
仍有 AI 味，直接指到具体句子即可；`reference/example-nice-slam.md` 里有二十条批注原文可对照。

## 特别想被挑的地方

1. **锚定精度**：`anchors.py` 的降级阶梯（去连字符 → 归一化 → 取最紧凑一处）在真实两栏论文上够不够稳；多命中判定的阈值合不合理。
2. **评论的"人味"**：`SKILL.md` 的 Voice 一节是否真的能约束出像人写的批注，还是仍会滑回报告腔。
3. **痛点 / 创新点两节是否够锋利**：`reference/example-nice-slam.md` 里那两张表，是不是比一份普通总结多说了一层东西；"借来的 / 新造的"这一列会不会被 agent 敷衍掉。
4. **中英双语**：英文路径是否只是中文规则的翻译，`--lang en` 的产出读起来是否自然。
5. **幂等与副作用**：重复 `--apply`、`--force`、备份、以及"先征得同意"这条规则在实际 agent 手里守不守得住。
6. **与无 skill 的差距**：`docs/pressure-test.md` 里那个基线其实很强——如果你认为差距不够大，直接说该砍掉哪一节、该加哪一节。

## 已知未验证

- Zotero 的 **文件 → 导入批注**（外部批注转可编辑批注）只在源码层面确认过，没有 GUI 实测记录，见 `docs/superpowers/specs/m0-result.md`。
- 扫描件、非 CS 领域、多篇综述都在非目标里，没有测。

## 输出建议

按严重程度给结论即可：哪些会让人用错、哪些只是不好看。不用重写代码。
