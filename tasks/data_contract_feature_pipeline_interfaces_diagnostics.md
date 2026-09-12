# Data Contract Delta v4 — Feature Pipeline Interfaces & Diagnostics

> **定位**：本文件是 Feature Pipeline 子项目的扩增数据契约。  
> **不替代**：本文件不替代、不修改项目级唯一数据契约 `pipeline_dataflow_bbh.md`。  
> **对应需求**：任务职责、profile 与验收要求见 `tasks\requirement_multiscalefeature_core.md`。  
> **稳定边界**：Stage 3 + Stage 4 mandatory；Stage 1 / Stage 2 optional；diagnostics independent。

---

## 0. Authority and Inheritance

### 0.1 Inherited authoritative contracts

以下定义只继承，不在本文件重新定义：

```text
B12 source label prefix
NSF9 physical output parameter space
source HDF5 schema
label transform
frequency / Nyquist boundary
event identity
manifest / DONE semantics
```

若本文件与 `pipeline_dataflow_bbh.md` 的数据语义冲突，以 `pipeline_dataflow_bbh.md` 为准。

### 0.2 NSF9 identity

除非项目级数据契约正式修改，本子项目的 Stage 3/4 参数维度必须保持 NSF9。

```text
parameter_names = ["Mc", "lambda", "beta", "eta", "tc", "dL", "psi", "phic", "e0"]
```

Rules：

1. `parameter_names` order is semantic, not display-only metadata.
2. Any tensor axis bound to parameter dimension must align with this order.
3. NSF9 must not be silently treated as C9.
4. Stage 4 posterior last dimension must match NSF9 unless a future project-level contract revision changes it.

---

## `DF-PIPELINE-PROFILE-001`

Legal profile values：

```text
CORE_DIRECT
MULTISCALE_ONLY
SELECTED_FRONTEND
EXTERNAL_FRONTEND
```

Every run must explicitly record：

```text
pipeline_profile
enable_stage1
enable_stage2
stage3_backend
stage3_backend_version
stage3_config_hash
stage4_backend
stage4_backend_version
stage4_config_hash
diagnostics_enabled
```

A formal run must not infer the task graph from file existence.

Invariant：

```text
stage3_enabled = true
stage4_enabled = true
```

---

## `DF-STAGE-OPTIONALITY-001`

```text
Stage 1: optional
Stage 2: optional
Stage 3: required
Stage 4: required
```

Rules：

1. Stage 3 must not declare Stage 1 or Stage 2 as required dependencies.
2. Stage 4 must not read Stage 1 / Stage 2 private payload.
3. Stage 2 may be enabled only when a compatible candidate representation is available.
4. Diagnostics may be disabled at runtime without invalidating core inference.
5. Diagnostics are required for scientific backend evaluation when comparison claims are made.

---

## `DF-INTERFACE-ID-001`

Formal cross-module interfaces：

| Interface ID | Logical object | Required | Producer | Consumer |
|---|---|---:|---|---|
| `IF-SOURCE-OBS` | source observation view | yes | existing source HDF5 adapter | Stage 1 / Stage 3 |
| `IF-CANDIDATE` | candidate representation | no | Stage 1 / external producer | Stage 2 / Stage 3 adapter |
| `IF-SELECTED` | selected candidate representation | no | Stage 2 | Stage 3 adapter |
| `IF-STAGE3-IN` | Stage3 Input Bundle | yes | source adapter / Stage 1 / Stage 2 / external producer | Stage 3 |
| `IF-STAGE3-OUT` | Stage3 Condition Bundle | yes | Stage 3 | Stage 4 |
| `IF-STAGE4-OUT` | SBI Posterior Bundle | yes | Stage 4 | evaluation / statistics |
| `IF-DIAG-SNAPSHOT` | feature snapshot | no at runtime | Stage 1 / Stage 2 / Stage 3 taps | diagnostics |

Rules：

1. Only `IF-STAGE3-IN`, `IF-STAGE3-OUT`, and `IF-STAGE4-OUT` are mandatory for core inference.
2. `IF-DIAG-SNAPSHOT` is mandatory only for scientific diagnostics claims.
3. Interface IDs must be recorded in persisted formal artifacts.

---

## `DF-SOURCE-OBS-001`

`IF-SOURCE-OBS` is an adapter view over existing source HDF5.

Minimum logical fields consumed by this subproject：

```text
event_uid
source_row
noisysignal: (N, 2, T)
```

Evaluation and training may also read：

```text
params: (N, P), P >= 12
```

Rules：

1. Production inference feature path must not require `params`.
2. Source HDF5 is read-only for this subproject.
3. Time and frequency semantics remain owned by `pipeline_dataflow_bbh.md`.

---

## `DF-CANDIDATE-001`

`IF-CANDIDATE` is used only when Stage 1 or an external candidate producer is enabled.

Minimum logical content：

```text
event_uid
candidate_feature
candidate_valid
candidate_identity
candidate_coordinate_metadata
producer_stage
producer_backend
producer_backend_version
producer_config_hash
```

Recommended canonical token form：

```text
candidate_feature: (N, L, D)
candidate_valid:   (N, L)
time_sec:          (L,)
freq_hz:           (L,)
support_sec:       (L,)
scale_id:          (L,)
token_id:          (L,)
```

Rules：

1. Stage 2 may consume this interface.
2. Stage 3 may consume it directly only through `IF-STAGE3-IN` with `input_type = "multiscale_tokens"`.
3. Stage 1 backend-private arrays are not part of this interface.

---

## `DF-SELECTED-001`

`IF-SELECTED` is used only when Stage 2 is enabled.

Stage 2 must output one of two forms.

### Form A — selected windows

```text
event_uid
parameter_names:     (9,)
value:               (N, 9, M, 2, P)
valid:               (N, 9, M, 2, P)
score:               (N, 9, M)
source_candidate_id: (N, 9, M)
```

### Form B — selected features

```text
event_uid
parameter_names:     (9,)
value:               (N, 9, M, D)
valid:               (N, 9, M)
score:               (N, 9, M)
source_candidate_id: (N, 9, M)
```

Rules：

1. `parameter_names` must follow exact NSF9 order.
2. Candidate rank is best-first.
3. Truth-dependent selection is forbidden at inference.
4. Stage 3 must not know whether selection came from cross-attention, Top-k, graph matching, or another backend.

---

## `DF-STAGE3-INPUT-BUNDLE-001`

`IF-STAGE3-IN` is the only formal Stage 3 input boundary.

Required metadata：

```text
interface_id = "IF-STAGE3-IN"
event_uid
source_row
input_type
input_schema_version
producer_stage
producer_backend
producer_backend_version
producer_config_hash
```

Allowed `input_type` values：

```text
raw_timeseries
multiscale_tokens
selected_windows
selected_features
```

Exactly one payload group must be active.

### Payload A — `raw_timeseries`

Producer：source adapter.

```text
timeseries/value: (N, 2, T)
timeseries/valid: (N, 2, T)
```

### Payload B — `multiscale_tokens`

Producer：Stage 1 or compatible external candidate producer.

```text
tokens/feature:     (N, L, D)
tokens/valid:       (N, L)
tokens/time_sec:    (L,)
tokens/freq_hz:     (L,)
tokens/support_sec: (L,)
tokens/scale_id:    (L,)
tokens/token_id:    (L,) optional
```

### Payload C — `selected_windows`

Producer：Stage 2.

```text
windows/value:           (N, 9, M, 2, P)
windows/valid:           (N, 9, M, 2, P)
windows/score:           (N, 9, M)
windows/source_token_id: (N, 9, M)
parameter_names:         (9,)
```

### Payload D — `selected_features`

Producer：Stage 2.

```text
features/value:           (N, 9, M, D)
features/valid:           (N, 9, M)
features/score:           (N, 9, M)
features/source_token_id: (N, 9, M) optional
parameter_names:          (9,)
```

When present：

```text
parameter_names = ["Mc", "lambda", "beta", "eta", "tc", "dL", "psi", "phic", "e0"]
```

Rules：

1. The payload group must match `input_type`.
2. A bundle with multiple active payload groups is invalid.
3. A bundle with no active payload group is invalid.
4. Tensor rank alone must never determine semantic meaning.
5. A downstream module must validate `input_type`, shape semantics, event identity, version and provenance before execution.

---

## `DF-STAGE3-CAPABILITY-001`

Every Stage 3 backend must declare：

```text
backend_name
backend_version
supported_input_types
D_param
D_cond
requires_parameter_names
```

Rules：

1. A backend receiving an unsupported `input_type` must fail explicitly.
2. Silent reinterpretation or reshape across payload types is forbidden.
3. Backend-private hidden states are not part of `IF-STAGE3-OUT` unless copied into a declared optional payload.

---

## `DF-STAGE3-OUTPUT-001`

`IF-STAGE3-OUT` is the mandatory Stage 3 condition boundary consumed by Stage 4.

Required fields：

```text
interface_id = "IF-STAGE3-OUT"
event_uid
parameter_names:       (9,)
parameter_condition:   (N, 9, D_param)
parameter_valid:       (N, 9)
condition_embedding:   (N, D_cond)
stage3_backend
stage3_backend_version
stage3_config_hash
input_reference_id
```

Optional fields：

```text
candidate_embedding
candidate_valid
backend_payload/*
```

Semantic requirements：

```text
parameter_condition[n, p, :] <-> parameter_names[p]
parameter_valid[n, p]       <-> parameter_names[p]
```

Rules：

1. Stage 4 may depend only on canonical required fields unless an explicit future interface revision allows more.
2. `condition_embedding` is the compact global condition for Stage 4.
3. `parameter_condition` is retained so parameter geometry is not carried only by one irreversible global vector.
4. `backend_payload/*` is diagnostic or debugging payload and is not required by Stage 4.
5. `parameter_names` must match exact NSF9 order.

---

## `DF-STAGE4-SBI-001`

Stage 4 input is `IF-STAGE3-OUT`.

Required consumed fields：

```text
event_uid
parameter_names
parameter_condition
parameter_valid
condition_embedding
```

Stage 4 output is `IF-STAGE4-OUT`.

Minimum physical output：

```text
interface_id = "IF-STAGE4-OUT"
event_uid
parameter_names
posterior_samples
posterior_mean
posterior_std
step_status
stage4_backend
stage4_backend_version
stage4_config_hash
stage3_output_reference_id
```

Default posterior shape：

```text
posterior_samples: (N, R, 9)
```

Optional trajectory posterior shape：

```text
posterior_samples: (N, S, R, 9)
trajectory_step:   (S,)
trajectory_semantics
```

Rules：

1. Unless the project-level data contract is revised, the last dimension is exact NSF9 order.
2. Stage 4 backend type is provenance, not tensor semantics.
3. Stage 4 must not read Stage 1 / Stage 2 private files.
4. Stage 4 must not require diagnostics output for formal inference.

---

## `DF-DIAG-SNAPSHOT-001`

`IF-DIAG-SNAPSHOT` is the independent diagnostics input for Stage 1 / Stage 2 / Stage 3 feature taps.

Diagnostics consume persisted feature snapshots and do not depend on concrete model classes.

Required metadata：

```text
interface_id = "IF-DIAG-SNAPSHOT"
stage_id
tap_id
feature_space_type
axis_semantics
backend_name
backend_version
backend_config_hash
source_reference_id
snapshot_schema_version
```

Required datasets：

```text
event_uid
feature_value
feature_valid
```

Optional datasets where applicable：

```text
parameter_names
candidate_rank
time_sec
freq_hz
scale_id
source_candidate_id
layer_index
```

Examples of `axis_semantics`：

```text
["event", "token", "feature"]
["event", "parameter", "candidate", "feature"]
["event", "parameter", "feature"]
["event", "feature"]
```

Rules：

1. `axis_semantics` is authoritative for snapshot axes.
2. Tensor rank alone must never determine semantic meaning.
3. Diagnostics may read truth labels from evaluation data.
4. Snapshots used in production inference path must not require truth labels.
5. Snapshot writing may be disabled at runtime.
6. Saved snapshots are evaluation artifacts, not mandatory Stage 3/4 inference inputs.
7. Snapshot identity must include enough provenance to trace the producing backend and config.

---

## `DF-DIAG-METRICS-001`

For every evaluated tap, minimum numerical outputs：

```text
tap_id
parameter_names:                       (9,)
probe_retention:                       (9,)
probe_information_loss:                (9,)
directional_sensitivity_retention:     (9,)
distance_spearman:                     scalar
knn_overlap:                           scalar
compression_ratio:                     scalar
```

For parameter-aware taps：

```text
geometry_matrix:            (9, 9)
geometry_matrix_normalized: (9, 9)
```

For posterior degradation reports：

```text
hpd_width_ratio: (9,)
a90_ratio:       scalar
calibration_delta optional
posterior_metric_delta optional
```

Every diagnostic result must identify：

```text
candidate_tap_id
reference_type
reference_tap_id or reference_artifact
feature_adapter
probe_family
data_split_id
target_transform_id
training_budget
stopping_rule
seed
```

Rules：

1. Parameter information must be reported per NSF9 parameter.
2. Geometry retention must include local or pairwise geometry evidence, not only one scalar average.
3. Layer-wise loss must use ordered taps and report incremental and cumulative values.
4. Posterior degradation must be measured with downstream configuration held fixed.
5. No single scalar average may replace per-parameter metrics.

---

## `DF-DIAG-COMPARISON-001`

Supported reference modes：

```text
SOURCE_REFERENCE
PREVIOUS_TAP
CORE_DIRECT_STAGE3_REFERENCE
CUSTOM_REFERENCE
```

For an ordered feature sequence：

```text
tap_0 -> tap_1 -> ... -> tap_K
```

Diagnostics must support：

```text
incremental_loss(k):
    tap_(k-1) -> tap_k

cumulative_loss(k):
    declared reference -> tap_k
```

Formal comparison invariants：

```text
same target transform
same train/validation split
same probe family
same optimization budget
same stopping rule
same feature_adapter declaration
same Stage3 backend/config when evaluating Stage1/2
same Stage4 backend/config when evaluating Stage1/2/3
```

A comparison is invalid if candidate and reference use different data splits or unequal probe training budgets.

---

## `DF-POSTERIOR-DEGRADATION-001`

Posterior degradation compares a candidate representation against a declared reference under fixed downstream conditions.

Minimum required inputs：

```text
candidate IF-STAGE3-IN or IF-STAGE3-OUT
reference IF-STAGE3-IN or IF-STAGE3-OUT
fixed Stage3 backend/config when input is IF-STAGE3-IN
fixed Stage4 backend/config
evaluation split
posterior metric definition
```

Minimum outputs：

```text
hpd_width_ratio: (9,)
a90_ratio: scalar
posterior_mean_shift: (9,) optional
posterior_std_ratio: (9,) optional
calibration_delta optional
```

Rules：

1. Posterior degradation may not be attributed to Stage 1/2 unless Stage 3 and Stage 4 are fixed.
2. Posterior degradation may not be attributed to Stage 3 unless Stage 4 is fixed.
3. The metric definition and reference mode must be recorded in provenance.

---

## `DF-INTERFACE-VALIDATION-001`

Before a downstream module consumes a formal cross-module artifact, it must validate：

```text
interface_id
required fields
shape semantics
axis semantics when applicable
event identity
parameter_names when applicable
finite-value requirements
schema/interface version
producer provenance
supported input type when applicable
```

Failure of any required validation prevents formal downstream execution.

Validation requirements by interface：

| Interface | Required validation |
|---|---|
| `IF-STAGE3-IN` | metadata, exactly one payload, input type, shapes, event identity, provenance |
| `IF-STAGE3-OUT` | canonical fields, NSF9 names, shape semantics, finite values, Stage 3 provenance |
| `IF-STAGE4-OUT` | posterior shapes, NSF9 names, step status, Stage 4 provenance |
| `IF-DIAG-SNAPSHOT` | tap identity, axis semantics, feature validity, snapshot provenance |

---

## `DF-RESOURCE-ROLE-001`

Resource metrics remain diagnostic：

```text
peak_gpu_memory_mb
peak_cpu_memory_mb
runtime_sec_per_event
parameter_count
flops_per_event
snapshot_storage_mb
```

They are not default scientific acceptance criteria.

Humans may use them to choose among scientifically acceptable profiles or backends.

---

## `DF-CORE-DONE-001`

A core profile is complete only if：

```text
IF-STAGE3-IN validation PASS
IF-STAGE3-OUT validation PASS
IF-STAGE4-OUT validation PASS
no-truth-leakage PASS
provenance COMPLETE
```

A backend scientific evaluation is complete only if the required diagnostic bundle also contains：

```text
parameter information report COMPLETE
geometry retention report COMPLETE
layer-wise loss report COMPLETE when ordered taps exist
posterior degradation report COMPLETE when downstream comparison is claimed
diagnostic provenance COMPLETE
```

Stage 1 / Stage 2 contract tests are required only when those tasks are enabled.

Diagnostics are optional at production runtime but required for scientific comparison claims.

---

## Stable Summary

Stable：

```text
IF-STAGE3-IN boundary
IF-STAGE3-OUT boundary
IF-STAGE4-OUT posterior boundary
IF-DIAG-SNAPSHOT diagnostics boundary
NSF9 parameter identity
event identity / provenance
information-loss measurement
geometry-retention measurement
posterior-degradation measurement
```

Optional / replaceable：

```text
Stage 1 existence
Stage 2 existence
multi-scale algorithm
selection algorithm
Stage 3 backend
Stage 4 SBI backend
hidden dimensions
candidate count M
storage profile
resource budget
snapshot writing at runtime
```

Architecture statement：

```text
optional frontend -> IF-STAGE3-IN -> mandatory Stage 3 -> IF-STAGE3-OUT -> mandatory Stage 4

Stage 1 / Stage 2 / Stage 3 taps -> IF-DIAG-SNAPSHOT -> independent diagnostics
```
