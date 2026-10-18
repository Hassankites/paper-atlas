# LoRA: Low-Rank Adaptation of Large Language Models

## 一句话主张

> 冻结预训练权重，只训练注入的低秩矩阵，把可训练参数降到原模型的 0.01%，且不增加推理延迟。

p.1 · “freezes the pre-trained model weights and injects trainable rank decomposition matrices into each layer”

## 痛点

- **为每个下游任务部署模型的服务方**：全量微调后每个任务都保存一份完整参数副本，代价是GPT-3 175B 上，部署多个任务实例的开销不可行（p.1）
- **在线推理服务**：Adapter 层必须串行执行，无法与主网络并行，代价是batch size 为 1 时，GPT-2 medium 上延迟增加约 20%–30%（p.3）

## 创新点

| 创新 | 相对什么 | 来源 | 凭什么算新 | 出处 |
| --- | --- | --- | --- | --- |
| 把权重更新写成低秩分解 BA，训练时只学 A、B | Adapter 与 Prefix Tuning | 新造的 | 不增加推理路径，部署时可合并回原权重 | p.4 |
| B 初始化为零，训练开始时增量为零 | 对增量整体做随机初始化 | 新造的 | 训练起点与原模型等价，避免初始阶段的扰动 | p.4 |
| Adapter 层与 Prefix Tuning 作为对照 | Houlsby adapter、prefix tuning | 借来的 | 沿用已有方法，只作为基线 | p.3 |

## 因果链

1. **前人做法** 全量微调为每个任务学习一份与原模型同维度的参数增量。  
   p.3 · “One of the main drawbacks for full fine-tuning is that for each downstream task, we learn a different set of parameters”
2. **Adapter 的失效点** Adapter 层串行执行，在短序列、小批量场景增加延迟。  
   p.3 · “adapter layers have to be processed sequentially”
3. **Prefix Tuning 的失效点** 为适配预留的序列长度会挤占任务输入的长度。  
   p.3 · “reserving a part of the sequence length for adaptation”
4. **待解决的问题** 权重更新是否也具有低内在秩，从而可以用更小的子空间表示。  
   p.4 · “we hypothesize the updates to the weights also have a low”
5. **本文的做法** 冻结 W0，只让低秩矩阵接收梯度。  
   p.4 · “During training, W0 is frozen and does not receive gradient updates”

## 选择点

| 选择 | 本可以怎么做 | 解决了什么 | 代价 | 出处 |
| --- | --- | --- | --- | --- |
| 用秩 r 的低秩分解表示权重更新，r 远小于原始维度 | 为每个任务训练完整的增量矩阵（推断） | 可训练参数降到原模型的 0.01% | 秩过小可能限制容量；秩接近满秩时退化回全量微调 | p.4 |
| A 用高斯初始化，B 初始化为零 | A、B 都做随机初始化（推断） | 训练起点与原模型等价，避免初期扰动 | B 为零时 A 的梯度为零，第一步只更新 B（推断） | p.4 |
| 把增量按 α/r 缩放，α 取第一次尝试的 r 后不再调 | 把 α 当作独立超参与学习率一起调（推断） | 改变秩时不必重新调参 | α 与学习率耦合，更换优化器后仍需重新确定（推断） | p.4 |
| 部署时把 BA 合并回 W0，推理路径不变 | 在推理时保留单独的适配模块（推断） | 不增加推理延迟 | 切换任务需要重新计算合并后的权重（推断） | p.4 |
| 多数实验只对 Wq 与 Wv 应用 LoRA | 对全部线性层应用 LoRA（推断） | 可训练参数更少，效果已经足够 | 选哪些矩阵依赖启发式，没有原则性方法（推断） | p.6 |

## 图表证据

| 图表 | 它回答什么 | 支撑 | 关键数字 | 没证明什么 | 页 |
| --- | --- | --- | --- | --- | --- |
| Figure 1 | 低秩分解加在权重矩阵的哪一侧？ | 低秩更新替代完整增量 | 只训练 A、B，W0 冻结 | 示意图，不含实验数据 | p.1 |
| Figure 2 | 在相同可训练参数下，LoRA 的精度落在什么位置？ | 低秩更新替代完整增量 | WikiSQL 与 MNLI-matched 上的验证精度对比 | 只覆盖两个任务；曲线取自单次训练结果 | p.8 |
| Table 1 | Adapter 到底增加多少延迟？ | Adapter 的延迟代价 | batch size 为 1 时，AdapterL 增加 20.7%，AdapterH 增加 30.3% | 只在 GPT-2 medium、单张 Quadro RTX8000 上测量 | p.4 |
| Table 6 | 秩要取多大才够？ | 低秩假设成立 | 秩取 1 时已有竞争力 | 只在两个分类任务上扫描秩 | p.10 |
| Table 8 | 微调相对少样本学习有多大差距？ | 任务适配仍然必要 | GPT-3 175B 上微调优于少样本 | 附录结果，比较的是微调与少样本，不是 LoRA 与全量微调 | p.17 |

*推断依据*

- 用秩 r 的低秩分解表示权重更新，r 远小于原始维度 —— “for each downstream task, we learn a different set of parameters”（p.4）
- A 用高斯初始化，B 初始化为零 —— “so ∆W = BA is zero at the beginning of training”（p.4）
- 把增量按 α/r 缩放，α 取第一次尝试的 r 后不再调 —— “tuning α is roughly the same as tuning the learning rate”（p.4）
- 部署时把 BA 合并回 W0，推理路径不变 —— “adapter layers have to be processed sequentially”（p.4）
- 多数实验只对 Wq 与 Wv 应用 LoRA —— “We mostly depend on heuristics to select the weight matrices to apply LoRA to”（p.6）

## 证据强度

- 同时报告了 RoBERTa、DeBERTa、GPT-2、GPT-3 四类模型上的结果。  
  p.1 · “LoRA performs on-par or better than fine-tuning in model quality on RoBERTa, DeBERTa, GPT-2, and GPT-3”

## 前置概念

- **low-rank decomposition** — 把一个矩阵写成两个低秩矩阵的乘积，参数量由 d×k 降为 r×(d+k)。 (p.4)
- **intrinsic rank** — 任务适配所需的权重更新可能只在一个低维子空间内变化。 (p.4)

## 术语表

| Term | 中文 |
| --- | --- |
| rank | 秩 |
| adapter layer | 适配层 |
| prefix tuning | 前缀调优 |
| intrinsic dimension | 内在维度 |

## 存疑

> 把 LoRA 加到哪些权重矩阵上，作者依赖启发式，没有给出选择方法。  
> p.13 · “We mostly depend on heuristics to select the weight matrices to apply LoRA to”
