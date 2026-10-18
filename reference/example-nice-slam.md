# NICE-SLAM: Neural Implicit Scalable Encoding for SLAM

## 一句话主张

> 用多层特征网格配合冻结的预训练解码器替换单个 MLP，以同时满足细节、实时和未观测区域的补全。

p.1 · “we present NICE-SLAM, a dense SLAM system that incorporates multi-level local information by introducing a hierarchical scene representation”

## 痛点

- **扫描多房间公寓的用户**：重建结果过度平滑，跨房间时追踪误差增大，代价是需要重新扫描，或事后手工修补 mesh（p.1）
- **在真实场景中部署隐式表示的系统**：单个 MLP 每帧都要整体更新，随运行出现遗忘，代价是只能在单间尺度上运行，精度与规模无法同时满足（p.1）

## 创新点

| 创新 | 相对什么 | 来源 | 凭什么算新 | 出处 |
| --- | --- | --- | --- | --- |
| 分层特征网格，并且只更新视锥内的特征 | iMAP 的单个 MLP 全局更新 | 新造的 | 使隐式 SLAM 的表示可以局部更新，这是扩展到大规模场景的前提 | p.1 |
| 粗层网格用于预测未观测区域，为追踪提供几何 | iMAP 不具备外推能力 | 新造的 | 把未观测区域的预测与已观测细节交由容量不同的模块分别承担 | p.3 |
| ConvONet 解码器、NeRF 体渲染与方差归一化深度损失 | ConvONet、NeRF、iMAP | 借来的 | 直接沿用，仅把解码器由训练改为冻结、只训练特征 | p.3 |

## 因果链

1. **前人做法** iMAP 用单个 MLP 表示整个场景，每次新增观测只能整体更新，这会带来容量不足与遗忘。  
   p.1 · “The key limiting factor of iMAP [47] stems from its use of a single multi-layer perceptron (MLP) to represent the entire scene, which can only be updated globally with every new, potentially partial RGB-D observations.”
2. **另一条路的失效点** 传统 TSDF 与体素方法满足实时要求，但对未观测区域无法给出几何估计。  
   p.1 · “they are unable to make plausible geometry estimation for unobserved regions”
3. **多级网格方法的局限** 多级网格特征能保留细节并重建复杂场景，但这些方法多为离线，不具备实时能力。  
   p.2 · “but these are offline methods without real-time capability”
4. **待解决的问题** 场景从单间扩展到多房间时，重建精度与相机追踪精度都会明显下降。  
   p.1 · “significant performance drops are observed in both the dense reconstruction and camera tracking accuracy”
5. **本文的做法** 论文让特征网格承载局部信息，让预训练解码器提供几何先验。  
   p.1 · “Optimizing this representation with pre-trained geometric priors enables detailed reconstruction on large indoor scenes”

## 选择点

| 选择 | 本可以怎么做 | 解决了什么 | 代价 | 出处 |
| --- | --- | --- | --- | --- |
| 几何分粗/中/细三层，粗层故意做到极低分辨率（2m），专门负责没观测到的地方 | 只用一个高分辨率网格，由网络插值填补未观测区域（推断） | 已观测细节与未观测预测由不同容量的模块承担，粗层计算量低且可外推 | 粗层分辨率低，边界与薄结构依赖中、细层；三层需要分别维护更新节奏，实现上分为三个线程 | p.3 |
| 解码器全部冻结，只优化网格里的特征 | 像 iMAP 那样端到端同时训练网络权重与场景表示（推断） | 更新只作用于特征，不牵动全局权重，优化更稳定，收敛更快 | 表达上限受预训练先验约束；预训练数据与目标场景差异较大时，细节难以恢复 | p.3 |
| 关键帧只选与当前帧有视觉重叠的，且只更新视锥范围内的网格 | 按 iMAP 的做法从全部关键帧中选择，以全局更新抑制遗忘（推断） | 每次只需局部更新，计算量与视锥范围相关，同时避免全局更新带来的遗忘 | 视野外的几何保持静止，回环或重访时不会自动校正；快速转动或大范围帧丢失依赖粗层预测 | p.5 |
| 加一步 local bundle adjustment，把 K 个关键帧的位姿和所有层一起联合优化 | 每帧只优化当前相机位姿，位姿之间不联合优化（推断） | 把累积误差限制在关键帧窗口内，提高追踪稳定性 | 增加一个优化阶段，实时预算更紧张；窗口大小 K 同时影响精度与速度 | p.4 |
| 颜色不冻结，特征和解码器一起学，用来给追踪提供额外信号 | 只用深度与几何信号做追踪，颜色仅用于可视化（推断） | 几何部分依赖预训练先验，颜色部分依靠观测数据，追踪多一路光度信号 | 颜色存在与 iMAP 相同的遗忘问题，只保持局部一致；全场颜色需要后处理优化 | p.4 |

## 图表证据

| 图表 | 它回答什么 | 支撑 | 关键数字 | 没证明什么 | 页 |
| --- | --- | --- | --- | --- | --- |
| Figure 1 | 该表示在真实多房间场景中能否保持精度？ | 分层网格让大场景可局部更新 | 定性：整间公寓的 mesh 与完整轨迹，无数值 | 只有单张定性渲染图，没有误差指标，也没有同图对比 | p.1 |
| Table 1 | 重建精度是否高于 iMAP 系列方法？ | 主张：重建质量优于 iMAP 系 | 8 个 Replica 场景平均；iMAP* 是作者自己复现的 | 只在 Replica 这一合成数据集上平均，不能外推到真实场景 | p.6 |
| Figure 3 | 重建改善体现在边缘清晰度，还是完整度？ | 主张：重建更锐利，不是更完整 | 定性对比：iMAP* 的墙面/家具边缘明显更糊 | 场景选择较为有利；基线为作者复现版本 | p.6 |
| Table 3 | 追踪精度在真实数据上是否保持？ | 关键帧只选有重叠的，在真实数据上仍能稳住 | ScanNet 上 ATE RMSE 全面优于对照 | 只报告 ATE，没有漂移随时间的变化，也没有回环实验 | p.6 |
| Figure 5 | 在多房间数据上，该方法能否扩展到更大场景？ | 粗层外推支撑多房间场景 | 自采公寓序列，红色为预测轨迹 | 单一自采序列，没有重复采集与统计 | p.7 |
| Table 4 | 该表示的计算量是多少？ | 分层表示的计算量低于单个 MLP | 查询一个 3D 点所需 FLOPs 为 iMAP 的 1/4；追踪与建图分别快 2 倍和 3 倍以上 | iMAP 的运行时间取自原论文 [47]，不是同一硬件实测；没有给出内存随场景规模的曲线 | p.7 |
| Table 5 | 各个设计选择的独立贡献是多少？ | local BA、颜色表示、关键帧策略的各自贡献 | 各跑 5 次取均值与标准差，ScanNet 6 个场景平均 | 只在 ScanNet 的 6 个场景上平均；消融项之间可能互相影响 | p.8 |
| Figure 8 | 三层结构本身是否必要？ | 三层结构本身带来更快收敛 | 单张深度图上对比 只用高分辨率 / 只用低分辨率 / 本文 | 单帧几何优化，并非完整 SLAM；曲线经过平滑处理 | p.8 |

*推断依据*

- 几何分粗/中/细三层，粗层故意做到极低分辨率（2m），专门负责没观测到的地方 —— “one feature grid with the same resolution as our fine-level representation”（p.3）
- 解码器全部冻结，只优化网格里的特征 —— “only optimize the feature grids”（p.3）
- 关键帧只选与当前帧有视觉重叠的，且只更新视锥范围内的网格 —— “where they select keyframes from the entire scene”（p.5）
- 加一步 local bundle adjustment，把 K 个关键帧的位姿和所有层一起联合优化 —— “the camera tracking is not only significantly less accurate, but also less robust”（p.4）
- 颜色不冻结，特征和解码器一起学，用来给追踪提供额外信号 —— “we compare our method without the photometric loss”（p.4）

## 证据强度

- 作者对每个场景运行 5 次，并报告均值与标准差。  
  p.8 · “We run each scene 5 times and calculate their mean and standard deviation of ATE RMSE”
- 主要基线是作者复现的 iMAP*，对比结果取决于该复现的质量。  
  p.6 · “iMAP∗refers to our iMAP re-implementation”

## 前置概念

- **occupancy field** — 对空间中每一点预测占据概率，取值在 0 到 1 之间；渲染时沿光线积分该概率。 (p.3)
- **volume rendering / ray termination** — 沿相机光线采样若干点，由占据概率计算光线终止的位置，得到深度和颜色。 (p.3)
- **ConvONet prior** — 在 ConvONet 上预训练的占据预测器，本文只使用其解码器作为与分辨率相关的先验。 (p.4)
- **local bundle adjustment** — 在一个关键帧窗口内同时优化相机位姿与场景表示，减少轨迹漂移。 (p.4)

## 术语表

| Term | 中文 |
| --- | --- |
| hierarchical feature grid | 分层特征网格 |
| occupancy | 占据（概率） |
| frame-to-model tracking | 帧到模型追踪 |
| local bundle adjustment | 局部光束法平差 |
| frustum | 视锥 |

## 存疑

> 颜色表示沿用 iMAP 的做法，因此同样存在遗忘，只保持局部一致。  
> p.4 · “this can lead to forgetting problems and the color is only consistent locally”
