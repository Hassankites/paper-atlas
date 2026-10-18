# Efficient Memory Management for Large Language Model Serving with PagedAttention

## 一句话主张

> 把 KV cache 切成固定大小的块并按块表寻址，消除连续分配造成的显存浪费，从而提高批量大小与吞吐。

p.2 · “PagedAttention, an attention algorithm inspired by the operating system’s (OS) solution to memory fragmentation and sharing”

## 痛点

- **部署 LLM 推理服务的团队**：按请求最大长度预分配连续显存，产生内部与外部碎片，代价是KV cache 中大量显存无法用于存放请求，批量大小受限（p.2）
- **提供并行采样与 beam search 的服务**：多个输出序列共享同一段提示，但系统无法复用这部分 KV cache，代价是同一提示被重复存储，可用批量进一步下降（p.2）

## 创新点

| 创新 | 相对什么 | 来源 | 凭什么算新 | 出处 |
| --- | --- | --- | --- | --- |
| 把 KV cache 存成非连续的块，按块做注意力计算 | 连续预分配的 KV cache | 新造的 | 块之间不必相邻，显存浪费不再随请求最大长度放大 | p.5 |
| 逻辑块到物理块的块表映射 | 操作系统的虚拟内存分页 | 借来的 | 直接借用分页思想，把块表换成了请求级的映射表 | p.2 |
| 迭代级调度，请求完成即换入新请求 | cellular batching 与 iteration-level scheduling | 借来的 | 沿用已有调度思路，与分块 KV cache 配合使用 | p.3 |

## 因果链

1. **前人做法** 为每个请求按最大可能长度预分配一段连续显存。  
   p.2 · “To store the KV cache of a request in contiguous space, they pre-allocate”
2. **后果** 预分配方案带来三类显存浪费，实际可用容量远低于显存总量。  
   p.4 · “the chunk pre-allocation scheme in existing systems has three primary sources of memory wastes”
3. **待解决的问题** 浪费的显存无法用于新请求，批量大小与吞吐因此受限。  
   p.3 · “The compute utilization in serving LLMs can be improved by batching multiple requests”
4. **本文的做法** 用块级内存管理替代连续预分配。  
   p.2 · “vLLM uses block-level memory management”

## 选择点

| 选择 | 本可以怎么做 | 解决了什么 | 代价 | 出处 |
| --- | --- | --- | --- | --- |
| KV cache 按固定大小切块，注意力在块上计算 | 按请求最大长度一次性分配连续空间（推断） | 显存浪费不再随请求最大长度放大 | 块大小引入块内碎片，最后一块通常填不满（推断） | p.5 |
| 用块表记录逻辑块到物理块的映射 | 用指针链直接串起物理块（推断） | 块可以分散存放，寻址仍是常数时间 | 每次访问多一次块表查询（推断） | p.6 |
| 多个序列共享同一段 KV 块，写入时才复制 | 每个序列各存一份 KV cache（推断） | 并行采样与 beam search 复用提示部分的 KV cache | 写时复制需要额外的引用计数与块管理（推断） | p.7 |
| 显存不足时在换出与重算之间选择 | 直接拒绝新请求或降低批量（推断） | 在显存受限时仍能维持批量 | 换出需要 PCIe 传输，重算需要额外计算（推断） | p.8 |

## 图表证据

| 图表 | 它回答什么 | 支撑 | 关键数字 | 没证明什么 | 页 |
| --- | --- | --- | --- | --- | --- |
| Figure 2 | 现有系统的显存浪费有多少？ | 碎片是主要瓶颈 | 按论文正文，实际用于 KV cache 的比例只有两到四成 | 只统计特定模型与负载，不代表所有服务场景 | p.2 |
| Figure 5 | 分块之后注意力怎么算？ | 分块 KV cache 可行 | 键值向量按块存放，块之间不连续 | 示意图，不含吞吐数据 | p.5 |
| Figure 4 | 系统由哪几部分组成？ | 块级管理落到工程实现 | 调度器与块管理器分工 | 架构图，不含性能证据 | p.5 |
| Figure 6 | 逻辑块怎样 Translation 到物理块？ | 块表映射 | 每个请求维护一张块表 | 示意图，不含访存开销 | p.6 |
| Table 1 | 实验用的模型和硬件是什么？ | 结果的可比范围 | OPT 与 LLM 模型规模、GPU 配置 | 只覆盖论文选定的模型与单机配置 | p.9 |
| Figure 17 | 在真实聊天负载上吞吐如何？ | 端到端收益 | 与 FasterTransformer、Orca 的吞吐对比 | 负载取自特定数据集的请求轨迹 | p.12 |

*推断依据*

- KV cache 按固定大小切块，注意力在块上计算 —— “To store the KV cache of a request in contiguous space, they pre-allocate”（p.5）
- 用块表记录逻辑块到物理块的映射 —— “the mapping between logical and physical KV blocks of each request”（p.6）
- 多个序列共享同一段 KV 块，写入时才复制 —— “the existing systems cannot exploit the opportunities for memory sharing”（p.7）
- 显存不足时在换出与重算之间选择 —— “batch size”（p.8）

## 前置概念

- **KV cache** — 自回归生成时缓存历史 token 的键值向量，避免每个新 token 重算全部注意力。 (p.1)
- **internal fragmentation** — 按最大长度分配后，实际序列较短，剩余空间无法给别的请求使用。 (p.2)
- **copy-on-write** — 多个序列共享同一物理块，任一方要写入时才复制出新块。 (p.7)

## 术语表

| Term | 中文 |
| --- | --- |
| KV cache | 键值缓存 |
| block table | 块表 |
| copy-on-write | 写时复制 |
| throughput | 吞吐量 |

## 存疑

> 换出与重算的速度取决于 CPU 与 GPU 之间的带宽以及 GPU 算力，不是固定收益。  
> p.8 · “The performances of swapping and recomputation depend on the bandwidth between CPU RAM and GPU memory”
