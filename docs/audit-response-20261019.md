# 审查回应（2026-10-19，Codex 审 v0.1）

审查报告在 `work/audit-20261019/`。下面是逐条状态。行号指修复后的位置。

## P1

| 发现 | 状态 | 位置 |
|---|---|---|
| `by -1 points` 被 `by 1 points` 认证通过（负号被删） | 已修 | `paper_atlas/anchors.py` `_match_key`：只有行末断词的连字符才还原，含数字的词保留连字符。测试 `test_a_lost_minus_sign_is_not_a_match`、`test_a_quote_with_its_minus_sign_still_matches` |
| `strength` 标 `inferred` 却带 `quote`，`quote` 被展示成论文原句 | 已修 | `paper_atlas/verify.py`：`inferred` 与 `quote` 互斥，判错；`render.py` 按 `inferred` 决定是否标（推断）。测试 `test_an_inferred_strength_may_not_carry_a_quote` |
| pain / novelty 的 `quote`、concepts 的 `basis_quote` 从未校验 | 已修 | `verify.py`：三者逐条 locate，找不到即错。测试 `test_a_pain_quote_is_checked_too`、`test_a_novelty_row_without_a_quote_is_an_error` |
| `（推断）` 没有进入 PDF 批注 | 已修 | `paper_atlas/annotate.py`：逐字段加标记，`note` 覆盖模板时也保留。测试 `test_an_inferred_field_is_marked_in_the_comment`、`test_the_inference_marker_survives_a_note` |

## P2

| 发现 | 状态 | 位置 |
|---|---|---|
| 公式/上标把高光拉进下一行；断词两半的并集框住相邻栏 | 已修 | `anchors.py`：`_line_band` 限制行高，`_segments` 每半各一个矩形。测试 `test_a_tall_glyph_cannot_stretch_the_quad_into_the_next_line`、`test_a_hyphenated_pair_does_not_cover_the_column_beside_it` |
| 跨页 `basis_quote` 用选择点的页码 | 已修 | `verify.fill_pages` 回填 `basis_page`；`render` 读 `basis_page`。测试 `test_verify_fills_the_page_the_basis_is_on` |
| 图表覆盖与高光预算冲突（DDPM 需 23 行，上限 20） | 已修 | `annotate.plan` 尊重 `"highlight": false`；`render` 在表中标「没高亮」；`reference/map-schema.md` 与 `SKILL.md` 说明"地图是覆盖单位，预算是另一回事"。测试 `test_a_figure_can_stay_in_the_map_without_a_highlight` |
| 样例教了过强的说法（LoRA「不必重调」、NICE-SLAM「解码器全部冻结」） | 已修 | `reference/example-lora.json`、`reference/example-nice-slam.json` 改成论文原意（"降低重新调参的需求"、"几何解码器冻结，颜色解码器从头训练"） |
| `borrowed` 布尔混同"原样复用"与"借鉴思想" | 已修 | `origin` 三值 `reused` / `adapted` / `new`；旧字段只警告。测试 `test_an_unknown_novelty_origin_is_an_error`、`test_the_old_borrowed_flag_only_warns` |
| schema 的最小示例用了被禁的腔调 | 已修 | `reference/map-schema.md` 重写示例（主张 + 痛点 + 创新点 + 一个选择点） |
| `REVIEW.md` 把 Voice 规则误归给 `lieflat-less-ai-tone` | 已修 | `REVIEW.md`「文字风格」一节改为"本 skill 自己的规则" |
| `--lang en` 只换标题，正文仍是中文 | 已修（文档） | `SKILL.md` Language 一节说明它不翻译；`scripts/render_map.py` 在 `--lang en` 且正文含中文时提示 |
| claim 与 chain 可用同一 id，写出重复 `/Zotero:Key` | 已修 | `verify.py` 用 `annotate.plan` 的 id 查重；`apply` 写完把 id 记入 `existing` |
| `count_occurrences` 大小写敏感、无词边界 | 已修 | `anchors.py` 用 `_canon` + 词边界正则，`_match_key` 做 casefold。测试 `test_occurrences_are_case_insensitive`、`test_occurrences_respect_word_boundaries` |
| 英文模板的回声检查失效（脚本用 `lang='zh'` 校验） | 已修 | 两个 CLI 传递 `--lang`；`verify` 同时检查两种语言的模板 |
| 密度上限只按单张地图计算 | 已修 | `verify` 把 PDF 里已有的 paper-atlas 批注计入上限。测试 `test_existing_annotations_count_towards_the_cap` |
| 批注超长被静默截断（切掉最后的 caveat） | 已修 | `annotate._tidy` 只压空白，不截断；`verify` 超 240 字报错 |
| `strength` 在 schema 里是可高亮对象，但从不被高亮 | 已修（文档） | `reference/map-schema.md` 标为 map-only |
| 长图注（>300 字）被丢掉；中文"表 1 所示"被当图注 | 已修 | `paper_atlas/extract.py`：`MAX_CAPTION = 800`，中文图注要求 ≤80 字且不含"所示/显示/如图"等正文标记。测试 `test_a_long_caption_is_still_a_caption`、`test_a_sentence_about_a_figure_is_not_a_caption` |
| 地图里的数字没有任何校验 | 已修 | `verify._number_errors`：地图里出现的每个数字都必须出现在 PDF 里 |
| `find_paper` 命中已删除条目、附件文件名，`%` 当通配符 | 已修 | `paper_atlas/zotero.py` `find_item`：排除 `deletedItems` 与 `itemAttachments`，LIKE 通配符转义 |

## 仍未验证

- Zotero 的 **文件 → 导入批注**（外部批注转可编辑批注）仍无 GUI 实测记录，见 `docs/superpowers/specs/m0-result.md`。本轮没有动这部分。
- 像素级差异（审查报告提到 DDPM 第 7 页 43/255）：内容流一致，未复现，未修。

## 复跑

```bash
python work/audit-20261019/code-review/probe_rerun.py   # 结果：results-rerun.json
python work/audit-20261019/voice-review/probe.py        # 结果：results.json
```

P1 的每一条探针现在都按预期失败：负号不再命中、推断+引文报错、pain/novelty/concepts 的假引文报错、
推断标记出现在批注里。P2 的探针里，重复 id、大小写重复、密度翻倍、超长批注、英文回声都从"通过"变成"拒绝"。
