# 增量需求说明 v4 — Feature Pipeline Core/Optional 与独立诊断

> **定位**：本文件是 `tasks/` 下 Feature Pipeline 子项目的需求增量文档。  
> **不修改**：本文件不修改、不替代 `requirement_bbh.md` 与 `pipeline_dataflow_bbh.md`。  
> **对应数据契约**：接口与 schema 的扩增定义见 `tasks\data_contract_feature_pipeline_interfaces_diagnostics.md`。  
> **核心原则**：Stage 3 + Stage 4 是必须保留的科学主链；Stage 1 / Stage 2 是可关闭、可替换、可不存在的 optional frontend。

---

## 0. Authority and Scope

### 0.1 权威边界

本文件只定义 Feature Pipeline 子项目的任务结构、接口职责、诊断职责与验收要求。

以下内容仍以项目级主文档为准：

```text
requirement_bbh.md
pipeline_dataflow_bbh.md
```

尤其不得在本文件中重定义：

```text
B12 / NSF9 参数语义
source HDF5 语义
physics core
label transform
frequency / Nyquist 语义
event identity / provenance
```

### 0.2 本版本新增重点

v4 明确三件事：

1. `IF-STAGE3-IN` 是 Stage 3 的唯一正式输入边界；
2. `IF-STAGE3-OUT` 是 Stage 4 的唯一正式条件输入来源；
3. Stage 1 / Stage 2 / Stage 3 的 feature taps 进入独立 diagnostics，diagnostics 不改变 forward path。

---

## 1. Stable Requirement Boundary

### 1.1 Mandatory Scientific Core

长期必须保留的最小有效科学流水线是：

```text
IF-STAGE3-IN
      |
      v
Stage 3 — Feature Representation Encoder
      |
      v
IF-STAGE3-OUT
      |
      v
Stage 4 — SBI Posterior Inference
```

Stage 3 与 Stage 4 是 mandatory。

### 1.2 Optional Frontend

Stage 1 与 Stage 2 的职责是减少、重组或筛选进入 Stage 3 的输入复杂度。

```text
OPTIONAL
┌─────────────────────────┐
│ Stage 1 -> Stage 2      │
│ reduce input complexity │
└────────────┬────────────┘
             │
             v
      IF-STAGE3-IN
             │
             v
     ┌──────────────┐
     │   Stage 3    │  mandatory
     │ Feature      │
     │ Encoder      │
     └──────┬───────┘
            │
     IF-STAGE3-OUT
            │
            v
     ┌──────────────┐
     │   Stage 4    │  mandatory
     │     SBI      │
     └──────────────┘
```

Stage 1 / Stage 2 不是科学主链的必要组成部分。

它们可以：

```text
absent
switched off
replaced by another backend
replaced by an external compatible producer
```

---

## 2. Allowed Pipeline Profiles

所有 profile 都必须显式声明任务图，不得通过文件存在性推断。

### 2.1 `CORE_DIRECT`

```text
source waveform
      |
      v
IF-STAGE3-IN / raw_timeseries
      |
      v
Stage 3
      |
      v
IF-STAGE3-OUT
      |
      v
Stage 4
```

用途：主基线。不做显式前端压缩。

### 2.2 `MULTISCALE_ONLY`

```text
source waveform
      |
      v
Optional Stage 1
      |
      v
IF-STAGE3-IN / multiscale_tokens
      |
      v
Stage 3
      |
      v
IF-STAGE3-OUT
      |
      v
Stage 4
```

用途：测试 multi-scale candidate representation 是否提升 Stage 3/4 结果。

### 2.3 `SELECTED_FRONTEND`

```text
source waveform
      |
      v
Optional Stage 1 or compatible candidate producer
      |
      v
Optional Stage 2
      |
      v
IF-STAGE3-IN / selected_windows or selected_features
      |
      v
Stage 3
      |
      v
IF-STAGE3-OUT
      |
      v
Stage 4
```

用途：在 Stage 3 前主动压缩候选特征。

### 2.4 `EXTERNAL_FRONTEND`

```text
externally prepared compatible IF-STAGE3-IN
      |
      v
Stage 3
      |
      v
IF-STAGE3-OUT
      |
      v
Stage 4
```

用途：快速测试新的前端算法，而不修改 mandatory core。

---

## 3. Task Selection Rules

每次运行必须显式声明：

```text
pipeline_profile
enable_stage1
enable_stage2
stage3_backend
stage4_backend
diagnostics.enabled
```

合法关系：

```text
Stage 1 = optional
Stage 2 = optional
Stage 3 = required
Stage 4 = required
```

规则：

1. `Stage 3` 不得把 Stage 1 或 Stage 2 声明为 import-time 必需依赖。
2. `Stage 4` 不得读取 Stage 1 / Stage 2 private payload。
3. `enable_stage2=true` 时，必须存在兼容 candidate representation。
4. candidate representation 可以来自 Stage 1，也可以来自外部兼容 producer。
5. diagnostics 可以读取保存的 feature snapshots，但不得成为 production inference 的必需步骤。

---

## 4. Task Decomposition

### 4.1 Optional Stage 1 — Candidate Construction

Stage 1 只负责：

```text
source observation
    ->
multi-scale / multi-resolution candidate representation
```

允许算法包括：

```text
CWT
STFT
wavelet packet
learned filterbank
scattering transform
multi-resolution CNN
other compatible candidate producer
```

Stage 1 不负责：

```text
final parameter embedding
posterior inference
NSF / SBI training
truth injection at inference
final Top-M decision
```

Stage 1 的保留依据不是“它存在”，而是它是否在可接受信息损失下给 Stage 3 降低输入复杂度。

必须报告：

```text
candidate count
compression or expansion ratio
per-parameter information retention
geometry retention
impact on fixed Stage3+Stage4 posterior quality
```

### 4.2 Optional Stage 2 — Selection / Compression

Stage 2 只负责：

```text
candidate representation
    ->
smaller parameter-aware candidate set
```

典型功能包括：

```text
Top-M selection
cross-attention association
sparse association
graph matching
metric-based selection
differentiable Top-k
```

Stage 2 不负责：

```text
deep final feature extraction
posterior inference
changing NSF9 parameter meaning
using truth at inference
```

Stage 2 的验收不是“必须启用”，而是它的压缩收益是否足以抵消信息损失。

必须报告：

```text
feature reduction ratio
incremental information loss
cumulative information loss
parameter-geometry distortion
fixed-downstream posterior degradation
```

### 4.3 Mandatory Stage 3 — Feature Representation Encoder

Stage 3 是核心特征编码器。

职责：

```text
IF-STAGE3-IN
    ->
parameter-aware representation
    ->
global SBI condition
    ->
IF-STAGE3-OUT
```

Stage 3 必须输出 canonical condition，不得要求 Stage 4 理解具体 Stage 3 backend 的 hidden state。

Stage 3 backend 可替换：

```text
PatchTST
TCN
dilated CNN
SSM
local Transformer
hybrid encoder
other compatible encoder
```

PatchTST 只是候选 backend，不属于接口本身。

Stage 3 必须声明：

```text
supported_input_types
D_param
D_cond
backend_name
backend_version
```

不支持的 input type 必须显式失败，禁止 silent reshape 或 silent reinterpretation。

### 4.4 Mandatory Stage 4 — SBI Posterior Inference

Stage 4 只消费 `IF-STAGE3-OUT` 的 canonical fields。

职责：

```text
IF-STAGE3-OUT
    ->
physical posterior samples
posterior statistics
optional posterior trajectory
```

允许 backend：

```text
NSF
other normalizing flows
diffusion posterior estimator
other calibrated SBI posterior model
```

当前默认 backend 可以是 NSF，但 Stage 4 的稳定接口是 SBI posterior contract，不是 NSF 类名。

除非项目级数据契约正式修改，Stage 4 输出参数空间保持 NSF9。

---

## 5. Cross-module Interfaces

Requirement 层只定义“谁生产、谁消费、用于什么”。字段、shape 与验证规则由对应数据契约定义。

| Interface ID | Producer | Consumer | Required | Purpose |
|---|---|---|---|---|
| `IF-SOURCE-OBS` | existing source HDF5 | Stage 1 / Stage 3 | Yes | 原始观测入口 |
| `IF-CANDIDATE` | Stage 1 or external producer | Stage 2 / Stage 3 | Optional | multi-scale candidate representation |
| `IF-SELECTED` | Stage 2 | Stage 3 | Optional | compressed selected representation |
| `IF-STAGE3-IN` | source adapter / Stage 1 / Stage 2 / external producer | Stage 3 | **Yes** | Stage 3 唯一正式输入边界 |
| `IF-STAGE3-OUT` | Stage 3 | Stage 4 | **Yes** | canonical parameter-aware condition |
| `IF-STAGE4-OUT` | Stage 4 | evaluation / statistics | **Yes** | physical posterior |
| `IF-DIAG-SNAPSHOT` | Stage 1 / Stage 2 / Stage 3 taps | diagnostics only | Optional at runtime, required for scientific diagnostics | 独立特征诊断输入 |

---

## 6. Independent Feature Diagnostics

### 6.1 Design Principle

Diagnostics 是独立子系统。

```text
Stage 1 / Stage 2 / Stage 3 feature taps
          |
          v
IF-DIAG-SNAPSHOT
          |
          v
Independent Diagnostics
          |
          +-- parameter information
          +-- geometry retention
          +-- layer-wise loss
          +-- posterior degradation
```

Forbidden dependency：

```text
diagnostics -> changes model forward result
model forward -> requires diagnostics package
Stage 4 -> reads diagnostics output for formal inference
```

Diagnostics may use truth labels because they are evaluation-only.

Production inference path must not require truth labels or diagnostics outputs.

### 6.2 Diagnostic Targets

Diagnostics must support named feature taps from Stage 1, Stage 2 and Stage 3.

Stage 1 examples：

```text
stage1/input
stage1/scale_<id>
stage1/candidate_tokens
stage1/output
```

Stage 2 examples：

```text
stage2/input_candidates
stage2/association_features
stage2/pre_selection
stage2/selected_features
stage2/output
```

Stage 3 examples：

```text
stage3/input_adapter
stage3/block_00
stage3/block_01
...
stage3/block_K
stage3/parameter_condition
stage3/condition_embedding
```

Exact tap names are backend-configurable, but every saved tap must have a stable `tap_id`.

### 6.3 Required Diagnostic Questions

Diagnostics must answer four independent scientific questions.

| Question | Required evidence |
|---|---|
| parameter information | per-parameter probe retention and information loss |
| geometry retention | distance preservation, kNN overlap, 9x9 parameter geometry matrix |
| layer-wise loss | incremental and cumulative loss across ordered taps |
| posterior degradation | fixed-downstream posterior width, calibration, A90 or equivalent posterior metric change |

No single scalar mean may replace per-parameter results.

### 6.4 Probe Comparability

Formal comparisons must hold fixed：

```text
same target transform
same train/validation split
same probe family
same optimization budget
same stopping rule
same Stage3 backend/config when evaluating Stage1/2
same Stage4 backend/config when evaluating Stage1/2/3
```

A comparison is invalid if candidate and reference use different data splits or unequal probe training budgets.

---

## 7. Scientific Comparison Boundary

### 7.1 Evaluate Stage 1 / Stage 2

Hold fixed：

```text
Stage3 backend/config
Stage4 backend/config
data split
target transform
evaluation protocol
```

This lets differences be attributed to optional frontend behavior.

### 7.2 Evaluate Stage 3

Hold fixed：

```text
IF-STAGE3-IN
Stage4 backend/config
evaluation protocol
```

### 7.3 Evaluate Stage 4

Hold fixed：

```text
IF-STAGE3-OUT
evaluation protocol
```

---

## 8. Recommended Repository Structure

This section defines recommended responsibilities, not absolute server paths.

```text
{ROOT}/
├── tasks/
│   ├── data_contract_feature_pipeline_interfaces_diagnostics.md
│   └── requirement_multiscalefeature_core.md
│
├── feature_sbi_pipeline/
│   ├── pipeline.py
│   ├── registry.py
│   ├── configs/
│   │   ├── pipeline_profiles/
│   │   ├── stage1/
│   │   ├── stage2/
│   │   ├── stage3/
│   │   ├── stage4/
│   │   └── diagnostics/
│   ├── interfaces/
│   │   ├── source_input.py
│   │   ├── stage3_input_bundle.py
│   │   ├── stage3_condition_bundle.py
│   │   ├── stage4_posterior_bundle.py
│   │   └── feature_snapshot.py
│   ├── stage1_optional/
│   ├── stage2_optional/
│   ├── stage3_encoder/
│   ├── stage4_sbi/
│   ├── diagnostics/
│   ├── io/
│   └── utils/
└── tests/
    ├── contract/
    ├── unit/
    └── integration/
```

Directory rules：

1. `stage1_optional/` and `stage2_optional/` must not become Stage 3 import-time required dependencies.
2. `stage3_encoder/` may depend on `interfaces/`, not concrete Stage 1/2 backends.
3. `stage4_sbi/` may consume only Stage 3 canonical condition.
4. `diagnostics/` must not be required by Stage 1/2/3/4 forward path.
5. `interfaces/` contains stable cross-module data objects and validation, not concrete model logic.

---

## 9. Definition of Done

### 9.1 Core Pipeline Profile

A core profile is complete when：

```text
1. IF-STAGE3-IN validation PASS
2. IF-STAGE3-OUT validation PASS
3. IF-STAGE4-OUT validation PASS
4. no-truth-leakage PASS
5. provenance COMPLETE
```

### 9.2 Optional Frontend Evaluation

A Stage 1 or Stage 2 backend is scientifically evaluated only when：

```text
1. corresponding optional interface contract PASS
2. IF-STAGE3-IN compatibility PASS
3. feature taps exported when diagnostics are requested
4. parameter information report COMPLETE
5. geometry retention report COMPLETE
6. layer-wise loss report COMPLETE when ordered taps exist
7. fixed-downstream posterior degradation report COMPLETE
8. diagnostic provenance COMPLETE
```

### 9.3 Stage 3 Backend Evaluation

A Stage 3 backend is scientifically evaluated only when：

```text
1. IF-STAGE3-IN validation PASS
2. IF-STAGE3-OUT validation PASS
3. supported_input_types declaration PASS
4. parameter information report COMPLETE
5. geometry retention report COMPLETE
6. layer-wise loss report COMPLETE when internal taps are exported
7. fixed Stage4 posterior degradation report COMPLETE
8. diagnostic provenance COMPLETE
```

Stage 1/2 remain optional pipeline tasks even though diagnostics are required when scientifically comparing their backends.
