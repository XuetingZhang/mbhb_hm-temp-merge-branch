# AGENT.md — 项目级 Coding Agent 指引

> **定位：每次 Agent 会话自动加载的项目入口 / 约束 / 上下文路由器。**  
> 本文件不复制参数索引、数据 schema、Feature 细节或一次性实现计划。稳定事实放到其唯一权威契约文档。  
> 目标：`小范围读取 -> 小改动 -> 便宜验证 -> 人类可审计`。

## 1. 项目目标与质量优先级

用神经样条流 NSF（条件归一化流 CNF）对 TianQin MBHB 事件做快速完备空间定位，并以 PTMCMC 后验作为参考基线。核心指标包括天空定位可信区域面积**A90**（HEALPix nside=512，90% 覆盖率并集面积。

```text
scientific correctness
  > auditability
  > recoverability
  > testability
  > maintainability
  > performance optimization
```

## 2. 硬约束

所有相对路径以本文件所在仓库顶层 `{ROOT}` 为基准。

1. 只在 `{ROOT}` 内读取任务所需文件、修改和写入项目文件。
2. 禁止修改任何父目录内容。
3. 禁止查看或修改 `flow_training/`。
4. source HDF5 / scientific inputs 默认只读。
5. 禁止凭数组维数、历史习惯或文件名猜测参数语义；必须查 Data Contract。
6. 未经明确需求，不扩大修改范围、不顺手重构无关模块。



### 2.1 Physics core：默认只读

普通 feature / refactor / bug-fix 不得修改：

```text
signal_simulation_hm/PhenomHM/PSD.py
signal_simulation_hm/PhenomHM/Likelihood.py
signal_simulation_hm/PhenomHM/const.py
signal_simulation_hm/PhenomHM/TDIPhemonHM.py
signal_simulation_hm/PhenomHM/TianQinOrbit.py
```

只有人类任务**明确授权 physics-core modification** 时才允许修改。此时任务属于 `physics-changing`，必须增加物理/数值回归，并按适用范围运行 posterior/P-P 等 slow validation。

未显式授权：

```text
PHYSICS CORE = READ ONLY
```



## 3. 单一真源与冲突规则

项目执行 **One Fact, One Authority**：


| 文档                         | 层          | 权威内容                                             |
| -------------------------- | ---------- | ------------------------------------------------ |
| `AGENT.md`                 | Layer 1 需求 | 项目修改边界、Agent 工作方式、上下文路由                          |
| `pipeline_dataflow_bbh.md` | Layer 2 契约 | 参数空间/映射、schema、SNR、frequency、event identity、DONE |
| `requirement_bbh.md`       | Layer 2 需求 | 项目级科学目标、基线行为与验收                                  |
| `requirement_*.md`         | 增量需求（网络扩展） | 子项目新增行为、范围、验收                                    |
| `sad_*.md` / 对应 SAD        | Layer 3 架构 | 模块职责、依赖、接口、状态机、异常/测试边界                           |
| code + tests               | Layer 4测试  | 可执行实现与验证证据                                       |


冲突时：

1. 修改范围/禁区 -> `AGENT.md`。
2. 参数、坐标、字段、shape、schema、SNR、frequency、DONE/identity -> `pipeline_dataflow_bbh.md`。
3. Feature 行为/验收 -> 对应 Requirement。
4. 内部架构/职责/依赖 -> 对应 SAD。

若必须改变 Data Contract：

```text
Data Contract/version
  -> affected Requirement references
  -> affected SAD references
  -> code
  -> contract tests
```

禁止在 Requirement、SAD、JSON、Agent prompt 中维护另一套可独立变化的参数真源。

## 4. 上下文路由：不要默认读取全部文档

每个任务先在内部判断 change type：

```text
implementation-only
architecture-changing
contract-changing
physics-changing
```

- `implementation-only`：私有实现、局部 bug、日志、内部重构；不改变外部行为/边界/契约。
- `architecture-changing`：模块职责、依赖方向、public interface、状态所有权改变。
- `contract-changing`：参数空间、坐标映射、dataset/schema、持久化语义、SNR、frequency、DONE/identity 改变。
- `physics-changing`：waveform/PSD/likelihood/detector/orbit 或科学数学定义改变。

implementation-only 且边界明确时不要输出冗长分类报告；只有非 implementation-only、存在冲突或用户要求时才报告受影响的 Contract/Requirement/SAD。

### 4.1 常用路由


| 修改主题                             | 下一步读取                                                                             |
| -------------------------------- | --------------------------------------------------------------------------------- |
| 参数/数据错位，A11/B12/NSF9/E5/S9/C9    | `pipeline_dataflow_bbh.md` 相关 Contract IDs/章节                                     |
| PTMCMC batch M1/M2/M4/M5         | `requirement_ptmcmc_batch.md` + `sad_ptmcmc_batch_bbh.md` 相关章节                |
| manifest/event_uid/DONE          | Data Contract identity/lifecycle + PTMCMC batch Requirement/SAD                   |
| S9->C9 / M2 输出                   | Data Contract mapping/schema + M2 converter/writer 设计                             |
| NSF 标签变换                         | Data Contract + `flow_label_renorm/data_norm_flexible.py`                         |
| NSF 模型结构                         | `flow_label_renorm/embedding_adjust2.py` + `flows_labeltranform.py`               |
| 推断/天空面积                          | `flow_inference/test_sky_area_overall_updated.py` + `nsf_posterior_statistics.py` |
| P-P 校准                           | `flow_result_checks/data_from_hdf5_to_pp_plot/pp_plot_diagnoistic.py`             |
| TianQin+LISA / detector response | 对应 `requirement_network_bbh.md` / `requirement_detector_response*.md`             |
| physics core                     | §2.1 + 对应 physics requirement/validation；无授权不得修改                                  |


优先使用 Contract ID、Requirement ID、章节名和精确文件定位；不要因局部任务扫描整个仓库或整份千行文档。

## 5. Data Contract 使用规则

`pipeline_dataflow_bbh.md` 是项目级唯一数据契约。

1. 跨模块数组必须能明确回答当前属于 A11 / B12 / NSF9 / E5 / S9 / C9 中哪一空间。
2. 跨空间变化必须通过显式 mapper/converter；禁止根据“都是 9 维”推断等价。
3. `NSF9 != C9`；比较时必须显式选择公共物理参数。
4. 固定 names/index/schema 应由 executable constants + contract tests 固化，不作为自由超参散落多处。
5. `dL`、`dist`、`r` 表示同一 luminosity-distance 内容；新物理/原始参数字段统一使用 `dL`，S9 采样空间保留 `dist`，`r` 仅作为既有训练/历史文档的 legacy alias。
6. `fs=0.01 Hz` source time-series 涉及 FFT 时遵守 Data Contract Nyquist；历史 `0.02-0.10 Hz` 不得当作 source HDF5 全局可表示频带。

遇到 posterior/truth 错位、sky coordinate 或 HDF5 schema 问题：**先查 Data Contract，不凭物理直觉猜列序。**

## 6. 最小软件工程规则



### 6.1 设计

- Single Responsibility：避免 God Object / God Script。
- Dependency Inversion / Ports & Adapters：physics、sampler、filesystem、SLURM 等具体实现位于边界层，核心语义不依赖具体 infrastructure。
- Explicit State：无隐藏 global state；配置显式传递，优先 immutable config/dataclass。
- Explicit Coordinate Space：禁止 hidden S9<->C9 conversion。
- Preserve Boundaries：M1/M2/NSF/physics-core 不因“少写代码”随意合并。



### 6.2 可读性与配置

- 新增 Python module 有英文 module-level functional description。
- 新增 class/function/method 有英文 docstring；公共接口有 type hints。
- 实现注释默认英文，优先解释 why；中文功能说明只放在需要时的 module header。
- 文档/代码符号优先 ASCII/LaTeX-style names：`lambda/beta/eta/iota`、`sqrt(...)`、`>=`，避免 Unicode 数学符号造成复制/解析差异。
- Bash/main 保持清晰入口、显式参数、失败返回码和可读日志；复杂业务逻辑放 Python，不塞入 shell。
- runtime tunables -> JSON/CLI；fixed scientific/data-contract constants -> executable contract constants。
- 禁止无必要新增依赖。



## 7. 文档更新规则

不要“每次 coding 都先改文档”。


| Change                                            | 更新                                             |
| ------------------------------------------------- | ---------------------------------------------- |
| private implementation only                       | code + tests；长期文档不改                            |
| module responsibility/dependency/public interface | SAD                                            |
| feature behavior/acceptance                       | Requirement                                    |
| parameter/schema/coordinate/frequency/lifecycle   | Data Contract **first**，再更新 Requirement/SAD 引用 |
| 一次性 Task A-H / Codex prompt / 实现顺序                | issue/temporary plan；不写入长期 SAD                 |


长期文档优先记录：`WHY / BOUNDARY / CONTRACT / INVARIANT / DECISION`，不要重复 private implementation details。

## 8. 验证策略

默认从便宜到昂贵：

```text
contract tests
 -> unit tests
 -> fake/mock integration smoke
 -> targeted regression
 -> slow physics / long sampler validation
```

要求：

1. 新增稳定数据语义必须有 contract test。
2. mapping/coordinate conversion 用 known-vector tests。
3. atomic/DONE 等生命周期必须测试 failure path。
4. scheduler/orchestration 默认 fake sampler/fake physics；不要每次跑完整 PTMCMC。
5. physics-changing 才升级到真实 physics/long-chain/P-P 等 slow validation。
6. bug fix 优先增加可复现该 bug 的最小回归测试。



## 9. 运行环境与常用入口


| 项         | 当前值                                                  |
| --------- | ---------------------------------------------------- |
| conda env | `bbhx`                                               |
| Python    | `/public/home/zhangxt57/.conda/envs/bbhx/bin/python` |
| GSL lib   | `/public/software/gsl-2.7.1/lib`                     |
| platform  | Linux/HPC + CUDA GPU                                 |


服务器绝对路径只属于部署信息，不传播到 Requirement/Data Contract。

```bash
# PTMCMC baseline
bash signal_simulation_hm/PhenomHM/run-ptmcmc.sh

# PTMCMC batch local/auto
bash signal_simulation_hm/PhenomHM/run-ptmcmc-batch.sh \
  --config signal_simulation_hm/PhenomHM/batch_ptmcmc.json

# PTMCMC batch SLURM
bash signal_simulation_hm/PhenomHM/run-ptmcmc-batch-slurm.sh \
  --config signal_simulation_hm/PhenomHM/batch_ptmcmc.json

# NSF training
bash flow_label_renorm/run-training-flows-labeltranform.sh

# NSF inference + statistics
bash flow_inference/run-test-generate-eval-samples-all-statistics.sh

# P-P diagnostics
python flow_result_checks/data_from_hdf5_to_pp_plot/pp_plot_diagnoistic.py --hdf5_file <result.hdf5>
```

若某入口尚未在当前 branch 实现，不得伪造成功状态；按 Requirement/SAD 实现和验证。

## 10. 每个 Coding Task 的工作流

1. **Scope**：确认允许修改文件和禁止范围。
2. **Classify**：判断 change type。
3. **Route**：只读取相关 Contract / Requirement / SAD 章节和代码。
4. **Inspect**：先理解现有实现和测试。
5. **Implement**：做满足需求的最小改动，不顺手扩展。
6. **Validate**：运行足以证明本次改动的最低成本测试；高风险变化升级验证。
7. **Report**：简述修改文件、关键行为、测试结果；只有确实发生时才报告 contract/requirement/architecture change。

禁止：

- 为小任务重写整个架构；
- 为“优化”偷偷改变物理或数据语义；
- 扫描无关目录/千行文档；
- 把一次性 Agent prompt 写进长期 SAD；
- 没有实际证据时声称测试或运行成功。



## 11. 人类审计问题

实现应让 Reviewer 快速回答：

1. 修改满足哪个 Requirement？
2. 是否触碰 Data Contract？
3. 是否越过 architecture/physics boundary？
4. 关键数组属于哪个参数空间？
5. 失败路径会不会产生错误正式结果或 DONE？
6. 结果能否追溯到 source/config/event identity/seed？
7. 哪个自动测试证明关键契约仍成立？

如果这些问题无法通过代码、测试和少量相关文档回答，优先改善边界、命名、contract test 或 provenance，而不是增加长篇说明。