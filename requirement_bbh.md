# 需求文档（Requirement Spec）— 空间引力波探测器 TianQin 下大质量双黑洞（MBHB）快速空间定位

> 本文档借鉴 **Spec Kit** 的“需求 → 架构 → 代码”分层思想，参考 `Requirement_Template.md` 的文档范式，将本项目（用 **神经样条流 NSF / 条件归一化流 CNF** 对 TianQin 探测到的大质量双黑洞并合事件做**快速完备空间定位**，并以 **PTMCMC** 后验采样作为真值基线）的科学问题逐层拆解为可落地的实现任务。

> **路径约定**：本文档所有路径均为**相对项目根目录 `{ROOT}`** 的相对路径。`{ROOT}` 指本仓库顶层目录（即 `AGENT.md` 所在目录）；迁移到不同运行服务器时，只需在 `AGENT.md` 中修改 `{ROOT}` 的定义，本文档相对路径保持不变。

---

## 0. 文档信息与修订记录

| 字段 | 内容 |
| --- | --- |
| 项目名称 | MBHB 快速空间定位（Neural Spline Flow vs PTMCMC） |
| 文档类型 | Requirement（需求规格 / Layer 1） |
| 版本 | v1.0 |
| 探测器 | TianQin（地心三角形星座，臂长 L = sqrt(3) * 10⁸ m） |
| 波形模型 | IMRPhenomHM（含高阶谐波），TDI 通道 A/E/T |
| 基线方法 | PTMCMC（eryn 并行回火 EnsembleSampler） |
| 替代方法 | 条件归一化流 CNF（glasflow CouplingNSF + EmbeddingComb 编码器） |
| 关键指标 | 天空定位可信区域面积 A90（HEALPix nside=512，90% 覆盖率） |

### 衍生需求文档（增量规格）

> 以下文档是在本文档基线上的**增量规格（delta spec）**，各自描述某一块的变更与新增；实现/评审时与本文档配合阅读，**冲突时以增量文档为准**。

| 文档 | 主题 |
| --- | --- |
| `requirement_ptmcmc_batch.md` | PTMCMC **批量**后验采样 + 天空面积统计（M1 采样 / M2 后处理：事件级并行、原子写断点续跑、JSON 超参、逐事件 1D HPD + A90）——扩展 §7.2 / §7.4 |
| `requirement_network_bbh.md` | TianQin + LISA 双探测器联合天空定位（PTMCMC 阶段） |
| `requirement_detector_response_bbh.md` | 统一探测器响应接口（TianQin / LISA / Taiji，`det` 选 `TQ`/`LISA`/`Taiji`） |
| `requirement_detector_response_validation_tests.md` | 统一响应接口的 validation / slow-test 验证测试（自 `requirement_detector_response_bbh.md` 拆分） |

### 修订记录

| 序号 | 作者 | 问题/动机 | 影响范围 | 修订内容 |
| --- | --- | --- | --- | --- |
| 1 | — | 项目初始化 | 全流程 | 建立 TianQin IMRHM 数据仿真 + PTMCMC 基线 + NSF 快速定位三阶段 |
| 2 | — | 似然评估过慢 | Likelihood.py | 引入 HeterodynedLikelihood（128 稀疏频点）加速 |
| 3 | — | 标签无界分布 | data_norm_flexible.py | 引入 FlexibleIndexParamTransform（theta→u→logit） |
| 4 | — | 9 维子集参数顺序 | run-training 脚本 | 固定 PARAMS_INDEX=(0 7 8 6 1 2 9 10 11) |
| 5 | — | 天空面积量化 | nsf_posterior_statistics.py | DBSCAN 模态聚类 + HEALPix 并集可信面积 |
| 6 | — | 后验校准 | pp_plot 脚本 | 引入 bilby P-P 图 + KS 均匀性检验 |
| 7 | — | 批量 PTMCMC / 双探测器 / 统一响应等增量需求需在主文档留索引 | §0 / §7.2 | §0 新增"衍生需求文档（增量规格）"索引，列出 `requirement_ptmcmc_batch.md` 等增量文档；§7.2 加指针指向批量 PTMCMC 增量规格 |

---

## 1. 项目概述与科学问题

### 1.1 科学问题

空间引力波探测器（TianQin）将探测大质量双黑洞（MBHB，总质量约一万至一千万太阳质量）的旋进-并合-铃宕（Inspiral-Merger-Ringdown, IMR）信号。
传统参数估计（Parameter Estimation, PE）通过 MCMC 从似然函数采样后验分布，可给出完整参数空间（含天空位置 lambda、beta）的不确定性，但**计算代价极高**（单事件需数十万步似然评估），无法满足快速定位的时效性需求。

**核心诉求**：用**条件归一化流（CNF / NSF）**学到一个“给定含噪应变到后验分布”的**摊销（amortized）推断器**。
训练完成后，单次前向即可抽样数万条后验样本，实现比 PTMCMC 快数个数量级的**完备快速空间定位**。

### 1.2 目标（Goals）

1. **数据仿真**：生成 TianQin IMRHM 波形 + 噪声 + 白化后的 2 通道时域应变，附带真值参数标签。
2. **基线真值**：用 PTMCMC 对注入事件做完整参数估计，输出后验样本作为 NSF 的“ground truth”。
3. **模型训练**：训练 CNF，学习 `p(theta | 白化应变)`，theta 覆盖质量、时间、距离、天空位置等 9 维。
4. **快速推断**：对测试事件一次前向抽样，量化 1D 参数 HPD 区间与 2D 天空定位可信面积。
5. **结果校验**：P-P 图（后验校准）、天空直方图、模态图，验证后验统计一致性。

### 1.3 非目标（Non-goals）

- 不做探测器噪声建模的理论研究（直接复用 TianQinNoise 的解析 PSD）。
- 不重写 IMRPhenomHM 波形生成器（依赖第三方库）。
- 不处理多源混叠 / 全盲全局搜索（当前为单源注入）。

---

## 2. 目录结构

```
{ROOT}/
├── Requirement_Template.md            # Layer-1 范式（参考）
├── SAD_Template.md                    # Layer-2 范式（参考）
├── requirement_bbh.md                 # 本文档
├── SAD_Template_bbh.md                # 架构设计文档
├── pipeline_dataflow_bbh.md           # 数据流与参数契约（Layer 3）
├── utils/
│   └── nn_prep.py                     # 设备选择、随机种子固化
├── signal_simulation_hm/              # 【阶段一】数据仿真
│   ├── mydataset.py                   # Torch Dataset：在线生成波形+标签
│   ├── packing_2channels_hpc.py       # HPC 批量打包 → HDF5
│   └── PhenomHM/
│       ├── mbhb_signal_hm.py          # 波形生成 TDIPhenomHM_AET + 白化
│       ├── PSD.py                     # TianQinNoise / LISANoise / TaijiNoise
│       ├── Likelihood.py              # Whittle / Heterodyned 似然
│       ├── ptmcmc_toymodel.py         # PTMCMC 基线（eryn）
│       └── run-ptmcmc.sh              # 启动脚本（conda env bbhx）
├── flow_label_renorm/                 # 【阶段二】CNF 训练
│   ├── flows_labeltranform.py         # 训练主程序（EmbeddingComb + CouplingNSF）
│   ├── data_norm_flexible.py          # 标签变换（theta↔z）+ 参数定义
│   ├── embedding_adjust2.py           # 编码器（Inception 多分支 Conv1d + ResNet50）
│   ├── param_9-dim_override.json      # 9 维参数定义覆盖
│   └── run-training-flows-labeltranform.sh
├── flow_inference/                    # 【阶段三】快速推断与天空面积
│   ├── test_sky_area_overall_updated.py  # 评估主程序（抽样→HPD→sky area）
│   ├── nsf_posterior_statistics.py        # 天空模态聚类/可信面积/统计量
│   └── run-test-generate-eval-samples-all-statistics.sh
└── flow_result_checks/                # 【阶段四】结果诊断
    ├── data_from_hdf5_to_pp_plot/pp_plot_diagnoistic.py   # P-P 图
    └── ...（天空直方图 / 模态图脚本）
```

---

## 3. 运行环境与基础依赖

| 依赖 | 版本/说明 | 用途 |
| --- | --- | --- |
| Python | >=3.11 | 运行环境 |
| conda env | `bbhx`（见 run-ptmcmc.sh） | 统一科学计算环境 |
| PyTorch | CUDA 可用 | CNN/NSF 训练与推断 |
| GSL | 2.7.1（LD_LIBRARY_PATH 注入） | 底层数值依赖 |
| glasflow | CouplingNSF | 神经样条流 |
| eryn | EnsembleSampler | PTMCMC 并行回火采样 |
| bilby | Result/P-P plot | 后验诊断与校准 |
| healpy | nside=512 | 天空像素化与可信面积 |
| h5py | — | 数据/结果落盘 |
| numpy / scipy / pandas / matplotlib | — | 数值与可视化 |

> 说明：本需求约束在项目根目录 `{ROOT}` 内完成；`flow_training` 子目录不在本需求范围。

---

## 4. 数据模型（HDF5 Schema）

### 4.1 训练/评估数据文件

打包脚本 [packing_2channels_hpc.py](signal_simulation_hm/packing_2channels_hpc.py) 生成，HDF5 结构：

| Dataset | shape / dtype | 含义 |
| --- | --- | --- |
| `noisysignal` | (N, 2, 4320) float | 白化后 2 通道（A、E）时域应变；4320 = fs*T_obs = 0.01*5d |
| `params` | (N, P), P>=12 float | 参数标签；前 12 列为 B12（详细语义以 `pipeline_dataflow_bbh.md` 为准） |

> 数据规格：fs = 0.01 Hz，T_obs = 5 days，Nt = 4320；频率截断和模型频率网格按 `pipeline_dataflow_bbh.md` 的 `DF-FREQ-001` 与模型频率契约执行；SNR 由均匀分布抽取并经 `scale = snr/opt_snr` 重标定。

### 4.2 推断结果文件

评估脚本 [test_sky_area_overall_updated.py](flow_inference/test_sky_area_overall_updated.py) 生成：

| Dataset | 含义 |
| --- | --- |
| `post` | 后验样本 (N_events, N_samples, N_params) |
| `true` | 真值参数 (N_events, N_params) |
| `names` | 参数名（字节串，需 decode） |
| `skyarea` | 天空定位面积结果 |
| `event_stats` | 每事件统计量（含 1d_hpd / sky_stats） |
| `sampling_time_sec` | 单事件抽样耗时 |

### 4.3 参数空间与索引约定（关键契约）

本项目存在**两套参数索引约定**，是贯穿全文的核心契约，详细推导见 `pipeline_dataflow_bbh.md`。此处给出结论：

**约定 A — 注入/物理参数（11 维，波形与似然、PTMCMC 使用）**

| 索引 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 物理量 | Mc | eta | chi1z | chi2z | dL | tc | phic | lambda(lon) | beta(lat) | psi | iota |

**约定 B — HDF5 标签空间（12 维，NSF 训练/推断使用）**

| 索引 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 物理量 | Mc | tc | dL（legacy alias：r） | iota | chi1z | chi2z | eta | lambda(lon) | beta(lat) | psi | phic | e0(偏心率) |

**训练 9 维子集（PARAMS_INDEX = `0 7 8 6 1 2 9 10 11`）**

`[Mc, lambda, beta, eta, tc, dL, psi, phic, e0]` —— 输出顺序即此序；其中 `dL` 与历史代码中的 `dist`/`r` 表示同一距离内容。

**评估 5 维子集（`0 7 8 1 2`）**

`[Mc, lambda, beta, tc, dL]`，其中 `lambda = 第1列`、`beta = 第2列`（天空定位用）。

### 4.4 参数标签变换（Label Transform）

`data_norm_flexible.FlexibleIndexParamTransform` 对每个参数按 `kind` 做有界变换：

| kind | 变换 | 适用参数 |
| --- | --- | --- |
| linear | theta → u = (theta-lo)/(hi-lo) | tc、beta、eta、chi1z、chi2z、e0 |
| log_linear | 对 log10 theta 线性归一到 (0,1) | Mc |
| power / power_linear | 距离 dL（legacy alias：r/dist）按 dL 的 power 次幂归一 | dL（power=3） |
| angle_2pi | 角度 wrap 到 [0,2pi) 再归一 | lambda、phic |
| angle_pi | 角度 wrap 到 [0,pi) 再归一 | psi、iota |

统一流程：`theta → u ∈ (0,1) → z = logit(u)`；反向 `z → sigmoid → u → theta`；并施加 **log|det J| 雅可比修正**。该变换把有界、混合类型参数统一映射到无约束潜变量空间，是 NSF 可训练的关键。

---

## 5. 数据接口约定（跨模块数据契约）

| 接口 | 生产者 → 消费者 | 格式 | 契约 |
| --- | --- | --- | --- |
| 训练数据集 | packing_2channels_hpc.py → flows_labeltranform.py | HDF5 | `noisysignal`(2,4320)、`params`(12) |
| 训练 checkpoint | flows_labeltranform.py → test_sky_area_overall_updated.py | .pth | embedding_state / flow_state / scaler_state / metadata |
| 参数定义覆盖 | param_9-dim_override.json → flows_labeltranform.py | JSON | 9 维 kind/lo/hi/power |
| 推断结果 | test_sky_area_overall_updated.py → pp_plot 脚本 | HDF5 | `post`/`true`/`names` |
| 后验统计 | test_sky_area_overall_updated.py 内部 | dict→HDF5 | `event_stats['sky_stats']['union_by_nside']['512']['0.9000']` = A90 |

**禁止行为**：不得修改 HDF5 dataset 名、不得修改 `params` 列序（否则标签索引错位）、不得修改 checkpoint 的 state 键名。

---

## 6. 通用组件（Components）

位于 `utils/` 与各阶段共享的底层能力：

| 组件 | 文件 | 职责 |
| --- | --- | --- |
| 设备/种子 | utils/nn_prep.py | `get_device()`、`same_seeds(seed)` |
| 波形生成 | signal_simulation_hm/PhenomHM/mbhb_signal_hm.py | `TDIPhenomHM_AET`、白化、`gen_bbh`/`gen_bbh_hh` |
| 噪声 PSD | signal_simulation_hm/PhenomHM/PSD.py | `TianQinNoise`（Na=1e-30, Np=1e-24）等 |
| 似然 | signal_simulation_hm/PhenomHM/Likelihood.py | `WhittleLikelihood`、`HeterodynedLikelihood`、`AET_log_likelihood` |
| 数据集 | signal_simulation_hm/mydataset.py | `Mydataset`（在线生成/读取，`paras_list` 追加 e0） |
| 标签变换 | flow_label_renorm/data_norm_flexible.py | `ParamDef`、`FlexibleIndexParamTransform`、`read_h5_data` |
| 编码器 | flow_label_renorm/embedding_adjust2.py | `Inception3`、`ResNet50`、`EmbeddingComb` |
| 后验统计 | flow_inference/nsf_posterior_statistics.py | `summarize_sky_modes_with_area`、`compute_parameter_statistics` |

---

## 7. 核心服务（Core Services / 阶段流程）

### 7.1 阶段一：信号仿真（signal_simulation_hm）

**输入**：无（仅物理配置）。
**输出**：HDF5 数据集（`noisysignal` + `params`）。

流程：`TianQinNoise().noise_AET(freq)` 建 PSD → `gen_par` 抽样天体物理参数 → `TDIPhenomHM_AET` 生成 A/E/T 三通道 FD 波形 → 取 TDI1/TDI2 两通道 → 按 SNR 重标定距离 → 白化 → 加白化噪声 → 频带截断 → 落盘。

### 7.2 阶段二（基线）：PTMCMC（ptmcmc_toymodel.py）

**输入**：注入事件（11 维约定 A）。
**输出**：后验样本（samples.npy / chains.npy）、corner 图、ChainConsumer 后验。

关键配置：`eryn.EnsembleSampler(nwalkers=80, ntemps=10, nsteps=200000)`，`StretchMove`，`HDFBackend`，`mp.Pool(56)`；似然用 `HeterodynedLikelihood`；先验：log(Mc)、lambda(0,2pi)、sin(beta)(-1,1)、eta(0.05,0.25)、cos(iota)(-1,1)、psi(0,pi)、phic(0,2pi)、tc、dL；周期量 lambda 周期 2pi。

> **增量扩展**：对多个模拟事件做**批量** PTMCMC 采样与后处理（事件级并行、原子写断点续跑、JSON 超参、天空面积统计）的增量规格见 `requirement_ptmcmc_batch.md`；本小节为单事件基线。

### 7.3 阶段三：CNF 训练（flow_label_renorm/flows_labeltranform.py）

**输入**：HDF5 数据集 + `param_9-dim_override.json`。
**输出**：checkpoint（embedding + flow + scaler + metadata）。

关键配置：`EmbeddingComb(input_shape=(2,4320), out_features=128, resnet_type="resnet50", branches=5)` 提取 128 维条件潜变量；`glasflow.CouplingNSF(n_inputs=9, n_conditional_inputs=128, n_neurons=256, n_transforms=50, n_blocks_per_transform=32, num_bins=10, tail_bound=5.0)`；损失 `-mean(log_prob(z|cond) + logdet)`（`use_theta_loss`）；AMP 混合精度、CosineAnnealingLR、早停、checkpoint 保存、FLOPs 剖析、潜空间高斯一致性诊断。

### 7.4 阶段四：快速推断与天空面积（flow_inference）

**输入**：checkpoint + 测试事件。
**输出**：后验样本 + 1D HPD + 天空可信面积。

流程：加载 checkpoint（`load_checkpoint_strict`）→ `generate_samples_for_batch`（`flow.sample` → sigmoid → u_to_theta）→ `compute_parameter_statistics`（1d_hpd，PTMCMC 与 NSF 自适应超参）→ `summarize_sky_modes_with_area`（DBSCAN eps=2sin(eps_deg/2) 模态聚类 + HEALPix 像素并集面积）。**关键指标 A90** = `sky_stats['union_by_nside']['512']['0.9000']`（90% 覆盖率并集面积，deg²）。

### 7.5 阶段五：结果诊断（flow_result_checks）

**输入**：推断结果 HDF5。
**输出**：P-P 图（后验校准）、天空直方图、模态图。

P-P 图脚本 [pp_plot_diagnoistic.py](flow_result_checks/data_from_hdf5_to_pp_plot/pp_plot_diagnoistic.py)：读取 `post`/`true`/`names` → 计算各事件注入值在边缘后验中的可信级别 → KS 检验对均匀分布 → 组合 p 值；判定后验是否校准良好。

---

## 8. 科学方法规范与质量保证（对标 MRV 合规）

| 检查项 | 方法 | 通过标准 |
| --- | --- | --- |
| 后验校准 | P-P 图 | 观测累计分布贴近对角线，KS 检验不显著偏离均匀 |
| 天空定位精度 | 可信面积 A90 | 90% 覆盖率的并集面积小且真实位置落在区域内的覆盖率达标 |
| 抽样完备性 | 潜空间高斯一致性诊断 | 隐变量分布接近标准高斯（NSF 基分布假设） |
| 结果完整性 | `verify_hdf5_file_completeness` | 所有 dataset/事件条目完整无 NaN |
| 复现性 | `same_seeds` + checkpoint | 固定随机种子可复现训练/推断 |

---

## 9. 验收标准（Acceptance Criteria）

1. 训练数据 HDF5 满足 §4.1 schema，标签与真值物理量一致（索引契约无错位）。
2. PTMCMC 后验收敛，corner 图覆盖真值。
3. NSF 训练损失收敛，潜空间高斯诊断通过。
4. 单事件推断抽样耗时远小于 PTMCMC（摊销加速目标）。
5. P-P 图校准良好，A90 面积可量化并稳定。

---

## 10. 风险与约束

| 风险 | 缓解 |
| --- | --- |
| 参数索引错位（约定 A/B 混用） | 统一以 `param_9-dim_override.json` + `data_norm_flexible` 为准，见 Layer 3 契约文档 |
| 似然评估过慢 | 使用 Heterodyned 似然（128 稀疏频点 logspace 插值） |
| 角度/周期参数标签不连续 | angle_2pi / angle_pi wrap 变换 + Jacobian 修正 |
| 天空多模态 | DBSCAN 模态聚类 + 并集可信面积（而非单峰高斯近似） |
| 后验不校准 | P-P 图 + KS 检验闭环反馈 |
