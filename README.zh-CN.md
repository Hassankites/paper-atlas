# Paper Atlas · 论文地图

一个用来「把论文读成骨架」的 skill：把一篇计算机论文变成一张可以反复打开的地图——主张是什么、前人栽在哪、作者做了哪些选择、每个选择付了什么代价、每张图表到底证明了什么——然后在你点头之后，把这些关键句子写回 PDF，成为**Zotero** 能直接读到的批注和高光。

它的价值不在总结，在**结构 + 出处**：每条结论都能点回原文某句话，每条推断都写清它是从哪句话推出来的。

## 安装

```bash
git clone https://github.com/Hassankites/paper-atlas.git ~/.dsh/skills/paper-atlas
# Claude Code 用 ~/.claude/skills/paper-atlas
# 通用位置用 ~/.agents/skills/paper-atlas
cd ~/.dsh/skills/paper-atlas
python -m pip install -r requirements.txt
python scripts/doctor.py
```

`doctor.py` 会检查 Python ≥ 3.10、PyMuPDF、以及你的 Zotero 数据目录。

## 使用

```bash
python scripts/find_paper.py "nice-slam"          # 从 Zotero 找条目和 PDF 路径
python scripts/extract.py paper.pdf --out work/slam
```

然后对 agent 说：*「给这篇论文建地图」*。它会写 `map.json`、逐条校验引文、渲染地图，并在**动你的文件之前先问你要不要写批注**。

地图落在 **`~/paper-atlas/<条目 key>-<标题 slug>/map.md`**，同目录还有 `map.json`。家目录不可写时（沙箱里的 agent 很常见）会退到 `./paper-atlas/<同名目录>/`。

想把地图留在库里，把 `map.md` 拖到 Zotero 里那条条目上即可，它会变成 PDF 旁边的附件。

## 批注：两步走

1. `annotate.py --apply` 把标准 PDF 高光写进文件。在 Zotero 里重新打开这份 PDF 就能看到——能读，但只读。
2. 在 Zotero 阅读器里点 **文件 → 导入批注**，它们就变成真正的 Zotero 批注：可编辑、可搜索、可同步，也能用「从批注创建笔记」。**不需要 API key。**

颜色就是地图里的角色：黄=主张，橙=因果链，绿=选择，蓝=证据，红=存疑。默认每篇 20 条，`--density detailed` 放宽到 30 条。

没有你的同意，它不会写任何东西：dry run 会先把条数、角色分布、以及会被改动的确切文件摆给你看。

## 它不做什么

- 不翻译、不重排 PDF（批注锚在原文的文字层上）。
- 不写 `zotero.sqlite`（文献库通过只读快照读取）。
- 不猜高光位置：定位不到的引文会被丢弃并报告。
- 不处理没有文字层的扫描件。
- 不做综述、不追引用——一次一篇 CS 论文。

## 排错

| 现象 | 处理 |
| --- | --- |
| 报 `database is locked` | Zotero 开着；脚本走的是快照，重跑一次即可 |
| Zotero 里看不到高光 | 打开的是批注副本而不是原件；或重开一次阅读器 |
| 高光是黑色的 | 该版本把 `/Zotero:Color` 当数组解析——本 skill 只写 `/C` |
| `find_paper.py` 找不到 | 加 `--data-dir ~/Zotero`，或直接给 PDF 路径 |
| 终端里中文是乱码 | `set PYTHONIOENCODING=utf-8`（Windows 另需 `chcp 65001`） |

## 目录

```
SKILL.md              skill 本体（英文，术语双语）
scripts/              doctor / find_paper / extract / verify_quotes / annotate / render_map
paper_atlas/          脚本背后的库
reference/            地图 schema、完整样例、排错
tests/                pytest 测试（python -m pytest）
```
