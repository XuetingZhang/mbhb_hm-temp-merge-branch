# 第三层：数据流与参数契约（Data Flow & Parameter Contract）

> **版本：v1.2**  
> **定位：项目级唯一数据契约（single source of truth）**  
> 本文档只定义跨模块必须稳定的数据语义：参数空间、坐标变换、数据 schema、频率边界、事件身份与完成状态。需求文档和 SAD 只引用本契约，不重复维护同一索引表。

---

## 0. 权威性与变更规则

### 0.1 权威范围

本文档是以下内容的唯一权威定义：

- 参数空间：A11、B12、NSF9、E5、S9、C9；
- B12 -> A11、S9 -> C9 等跨空间映射；
- 源 HDF5、PTMCMC M1/M2/M4/M5、NSF checkpoint 的跨模块 schema；
- SNR 的数据归属；
- 时域采样与频率上限的边界；
- batch event identity、manifest 与 `DONE` 完成状态语义。

### 0.2 文档冲突处理

若其他 Requirement / SAD / Agent prompt 与本文档的**数据语义**冲突：

1. 以本文档为准；
2. 若确需改变数据契约，先修改本文档并提升版本；
3. 然后修改受影响 Requirement / SAD；
4. 最后修改代码和 contract tests。

### 0.3 变更原则

以下变化属于 **contract-changing change**：

- 参数列顺序、名称、维度或坐标空间改变；
- HDF5 dataset 名或 shape 语义改变；
- S9/C9 转换改变；
- SNR 从独立字段变成参数维度；
- `DONE` / manifest 的权威状态语义改变；
- 时域数据的 `fs` / `Nt` / Nyquist 语义改变。

内部函数重构、私有类拆分、日志格式变化通常不属于数据契约变更。

---

# 1. 端到端数据流

## 1.1 NSF 主流程

```text
A11 injection / physical parameters
        |
        | waveform + detector response + noise
        v
source HDF5
  noisysignal(N,2,4320)
  params(N,P), P>=12, first 12 columns = B12
        |
        | select NSF9 from B12
        | FlexibleIndexParamTransform: theta -> u -> z
        v
EmbeddingComb + CouplingNSF
        |
        v
checkpoint
        |
        | flow.sample -> inverse label transform
        v
NSF9 physical posterior
        |
        | select E5 when 5-D evaluation is requested
        v
posterior statistics + sky area + P-P diagnostics
```

## 1.2 PTMCMC batch 分支

```text
source HDF5 B12 prefix
        |
        | DF-MAP-B12-A11
        v
A11
        |
        +---- fixed event chi1z / chi2z
        |
        | regenerate reference data d_ref
        +---------------------------> independent SNR
        |
        | SampPara + PTMCMC coordinate selection
        v
S9 internal sampling coordinates
        |
        | M1 atomic event output
        v
DONE
        |
        | M2 only
        | DF-MAP-S9-C9
        v
C9 physical coordinates
        |
        +---- 1-D posterior statistics
        +---- lambda/beta sky statistics
        v
results.hdf5

M1 DONE event
        |
        | M4 reads processed post.npy / true.npy in S9
        | compute ESS and select effective joint rows
        | DF-MAP-S9-C9
        v
results_m4.hdf5 (variable per-event post_c9 / true_c9)
        |
        | M5 uses C9 posterior + truth
        v
results_m5.hdf5 (C9 statistics / sky comparison)
```

---

# 2. 参数空间契约

## 2.1 `DF-PARAM-A11` — 波形 / likelihood 物理参数空间

A11 用于波形生成、likelihood 与基线 PTMCMC 的物理参数输入。

| index | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---:|---|---|---|---|---|---|---|---|---|---|---|
| name | Mc | eta | chi1z | chi2z | dL | tc | phic | lambda | beta | psi | iota |

Canonical physical name for luminosity distance is **`dL`**. `dist`（S9 采样坐标）和 `r`（历史文档/训练代码 alias）均表示同一距离内容；新物理字段统一写 `dL`，不得把它们定义为不同物理量。

## 2.2 `DF-PARAM-B12` — HDF5 注入标签前缀

源 HDF5 必须满足：

```text
params.shape = (N_events, P)
P >= 12
```

前 12 列固定为 B12：

| index | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---:|---|---|---|---|---|---|---|---|---|---|---|---|
| name | Mc | tc | dL | iota | chi1z | chi2z | eta | lambda | beta | psi | phic | e0 |

规则：

- `params[:, 0:12]` 是 MBHB 的稳定数据契约；
- `params[:, 12:]` 是可选扩展字段；
- 当前 PTMCMC batch 不解释这些扩展字段；
- 禁止通过第 12 列以后位置推测 SNR 或其它 MBHB 物理量。

### B12 label-transform metadata

NSF label transform 的当前语义：

| B index | name | kind |
|---:|---|---|
| 0 | Mc | log_linear |
| 1 | tc | linear |
| 2 | dL | power_linear (`power=3`) |
| 3 | iota | angle_pi |
| 4 | chi1z | linear |
| 5 | chi2z | linear |
| 6 | eta | linear |
| 7 | lambda | angle_2pi |
| 8 | beta | linear |
| 9 | psi | angle_pi |
| 10 | phic | angle_2pi |
| 11 | e0 | linear |

## 2.3 `DF-PARAM-NSF9` — NSF 训练 / 推断 9 维物理空间

NSF9 从 B12 通过：

```text
NSF_PARAMS_B_INDEX = [0, 7, 8, 6, 1, 2, 9, 10, 11]
```

得到：

```text
NSF9 = [Mc, lambda, beta, eta, tc, dL, psi, phic, e0]
```

注意：**NSF9 != C9**。NSF9 包含 `e0`，不包含 `iota`。

## 2.4 `DF-PARAM-E5` — NSF 5 维评估空间

```text
E5_B_INDEX = [0, 7, 8, 1, 2]
E5 = [Mc, lambda, beta, tc, dL]
```

天空定位：

```text
lon = E5[:, 1]   # lambda
lat = E5[:, 2]   # beta
```

## 2.5 `DF-PARAM-S9` — PTMCMC M1 内部采样坐标

PTMCMC batch M1 的正式输出坐标为：

```text
S9 = [
    logmc,
    lambda,
    sinbeta,
    eta,
    delta_tc,
    dist,
    cosiota,
    psi,
    phic,
]
```

固定名称：

```text
S9_NAMES = [
    "logmc", "lambda", "sinbeta", "eta", "delta_tc",
    "dist", "cosiota", "psi", "phic"
]
```

规则：

- `post.npy`, `true.npy`, `names.npy` 在 M1 必须保持 S9；
- `post.npy` 的列由 `S9_NAMES` 定义，行顺序继承采样器输出的已处理后验顺序（包括 M1 已配置的 burn-in/thin 结果）；下游不得按参数值排序、重排或丢失行的联合状态对应关系；
- `dist` 是 S9 的历史采样坐标名，对应物理 `dL`；`r` 是同一距离内容的 legacy alias；
- M1 禁止把 S9 覆盖成物理 C9。

## 2.6 `DF-PARAM-C9` — PTMCMC M2/M4/M5 与 NSF 对照公共物理空间

```text
C9 = [
    Mc,
    lambda,
    beta,
    eta,
    tc,
    dL,
    iota,
    psi,
    phic,
]
```

固定名称：

```text
C9_NAMES = [
    "Mc", "lambda", "beta", "eta", "tc",
    "dL", "iota", "psi", "phic"
]
```

对应 B12：

```text
C9_B_INDEX = [0, 7, 8, 6, 1, 2, 3, 9, 10]
```

注意：

```text
C9 != NSF9
```

二者前六维部分相近，但第 7 个物理维度不同：

- C9 使用 `iota`；
- NSF9 使用 `e0`。

任何比较必须显式说明比较的是哪个公共子集，禁止仅凭“都是 9 维”直接逐列比较。

---

# 3. 映射与坐标变换

## 3.1 `DF-MAP-B12-A11`

```text
A11[0]  = B12[0]    # Mc
A11[1]  = B12[6]    # eta
A11[2]  = B12[4]    # chi1z
A11[3]  = B12[5]    # chi2z
A11[4]  = B12[2]    # dL
A11[5]  = B12[1]    # tc
A11[6]  = B12[10]   # phic
A11[7]  = B12[7]    # lambda
A11[8]  = B12[8]    # beta
A11[9]  = B12[9]    # psi
A11[10] = B12[3]    # iota
```

`B12[11] = e0` 当前不进入非偏心 PTMCMC A11。

## 3.2 PTMCMC legacy index selector

当前基线代码保留：

```text
mbhb_params = [0, 7, 8, 1, 5, 4, 10, 9, 6]
```

该表必须与 `SampPara(A11)` 的语义一起解释；它不是 C9 的直接 B12 索引表。

## 3.3 `DF-MAP-S9-C9`

给定 `Tobs`：

```text
Mc     = 10 ** logmc
lambda = lambda
beta   = arcsin(clip(sinbeta, -1, 1))
eta    = eta
tc     = delta_tc + Tobs
dL     = dist
iota   = arccos(clip(cosiota, -1, 1))
psi    = psi
phic   = phic
```

要求转换支持：

```text
shape (9,)
shape (N, 9)
```

输出最后一维始终为 9。

## 3.4 天空坐标契约

C9：

```text
lon = C9[:, 1]   # lambda
lat = C9[:, 2]   # beta
```

S9 若直接计算天空坐标：

```text
lon = S9[:, 1]
lat = arcsin(clip(S9[:, 2], -1, 1))
```

禁止把 `sinbeta` 直接当 `beta`。

---

# 4. 数据 Schema

## 4.1 `DF-SCHEMA-SOURCE-H5`

源 HDF5：

| dataset | shape | requirement | meaning |
|---|---|---|---|
| `params` | `(N_events, P)`, `P>=12` | required | first 12 columns = B12 |
| `noisysignal` | `(N_events, 2, 4320)` | pipeline dependent | whitened/noisy time-domain data; current PTMCMC batch likelihood does not consume it |

## 4.2 `DF-SCHEMA-NSF-CHECKPOINT`

跨训练/推断 checkpoint 稳定键：

```text
embedding_state
flow_state
scaler_state
metadata
```

具体内部 state dict 内容不是本数据契约的一部分。

## 4.3 `DF-SCHEMA-M1-EVENT`

成功事件目录：

```text
out_dir/events/{event_uid}/
    post.npy
    true.npy
    names.npy
    snr.npy
    sampling_time_sec.npy
    metadata.json
    sampler_backend.h5
    DONE
```

最小语义：

| item | contract |
|---|---|
| `post.npy` | `(N_samples,9)`, S9 |
| `true.npy` | `(9,)`, S9 |
| `names.npy` | `(9,)`, exactly `S9_NAMES` |
| `snr.npy` | finite positive scalar, independent |
| `sampling_time_sec.npy` | finite non-negative scalar |
| `metadata.json` | event identity + provenance + coordinate-space versions |
| `DONE` | authoritative completion marker, created last |

推荐 metadata 空间标记：

```text
sampling_space = "S9_ptmcmc_internal_v1"
physical_space = "C9_physical_v1"
coordinate_transform = "S9_to_C9_performed_by_M2"
```

## 4.4 `DF-SCHEMA-M2-RESULT`

`results.hdf5`：

| dataset | shape | space |
|---|---|---|
| `post` | `(N_events,N_samples,9)` | S9 |
| `true` | `(N_events,9)` | S9 |
| `names` | `(9,)` | S9 |
| `post_c9` | `(N_events,N_samples,9)` | C9 |
| `true_c9` | `(N_events,9)` | C9 |
| `names_c9` | `(9,)` | C9 |
| `snr` | `(N_events,)` | independent |
| `skyarea` | `(N_events,)` | A90 |
| `sampling_time_sec` | `(N_events,)` | independent |
| `event_uid` | `(N_events,)` | identity |
| `source_event_index` | `(N_events,)` | manifest identity |
| `event_stats` | group | statistics on C9 |

M2 只聚合符合 `DF-LIFECYCLE-DONE` 的事件。


## 4.5 M4 输出 Schema

M4 是独立后处理阶段，只读取满足 `DF-LIFECYCLE-DONE` 的 M1 event。

M4 输入来自 M1：

```text
post.npy
true.npy
names.npy
````

其中 `post.npy`、`true.npy` 均为 S9。M4 不修改 M1-owned 文件或 `DONE`。

M4 输出分为两层：

```text
results_m4.hdf5
    # batch-level ESS/convergence summary

events/{event_uid}/post_ess_m4.hdf5
    # event-level ESS/effective-sample payload
```

不同事件允许不同 `n_saved`，因此 event posterior 不聚合为固定
`(N_events, N_samples, 9)` 数组。

### 4.5.1 `DF-SCHEMA-M4-BATCH-SUMMARY`

M4 batch-level 汇总文件：

```text
results_m4.hdf5
    event_summary/
        event_uid
        sampling_status
        convergence_status
        ess_theta
        tau_theta
        ess_min
        n_saved
        source_row
        run_event_index
        post_ess_m4_path
        post_c9_path
        true_c9_path
        names_s9
        names_c9
```

File attributes：

```text
schema = "DF-SCHEMA-M4-BATCH-SUMMARY"
sampling_space = "S9_ptmcmc_internal_v1"
physical_space = "C9_physical_v1"
event_result_filename = "post_ess_m4.hdf5"
```

设有效 M4 event 数为 `N_events`：

| dataset              |           shape | meaning                                          |
| -------------------- | --------------: | ------------------------------------------------ |
| `event_uid`          |   `(N_events,)` | stable event identity                            |
| `sampling_status`    |   `(N_events,)` | M4 processing status                             |
| `convergence_status` |   `(N_events,)` | ESS convergence status                           |
| `ess_theta`          | `(N_events, 9)` | per-event, per-S9-dimension ESS                  |
| `tau_theta`          | `(N_events, 9)` | per-event, per-S9-dimension autocorrelation time |
| `ess_min`            |   `(N_events,)` | minimum ESS of each event                        |
| `n_saved`            |   `(N_events,)` | number of selected effective posterior rows      |
| `source_row`         |   `(N_events,)` | source HDF5 row                                  |
| `run_event_index`    |   `(N_events,)` | batch run event index                            |
| `post_ess_m4_path`   |   `(N_events,)` | relative path to event-level M4 result           |
| `post_c9_path`       |   `(N_events,)` | locator of event-level `post_c9`                 |
| `true_c9_path`       |   `(N_events,)` | locator of event-level `true_c9`                 |
| `names_s9`           |          `(9,)` | exactly `S9_NAMES`                               |
| `names_c9`           |          `(9,)` | exactly `C9_NAMES`                               |

契约要求：

* `event_uid` 是 batch summary 与 event-level result 的稳定对齐键；
* `ess_theta` 和 `tau_theta` 的第二维严格对应 `S9_NAMES`；
* `ess_min[i] = min(ess_theta[i, :])`；
* `n_saved[i]` 与对应 event-level `post_s9` / `post_c9` 的行数一致；
* `post_ess_m4_path` 使用相对于 batch output root 的 event result 路径；
* `post_c9_path` / `true_c9_path` 使用 `<file-path>::<dataset-path>` locator；
* `names_s9` / `names_c9` 是 batch-level coordinate metadata，不按 event 重复；
* `results_m4.hdf5` 只保存 batch-level summary，不保存变长 posterior payload；
* `results_m4.hdf5` 通过 temporary file + atomic replace 写入。

### 4.5.2 `DF-SCHEMA-M4-EVENT-ESS-RESULT`

每个成功处理的 M4 event 写入：

```text
events/{event_uid}/post_ess_m4.hdf5
```

File attributes：

```text
schema = "DF-SCHEMA-M4-EVENT-ESS-RESULT"
sampling_space = "S9_ptmcmc_internal_v1"
physical_space = "C9_physical_v1"
event_uid
source_file
source_row
run_event_index
```

Datasets：

```text
post_s9
true_s9
names_s9

post_c9
true_c9
names_c9

ess_theta
tau_theta
ess_min
n_saved

sampling_status
convergence_status
```

| dataset              |          shape | meaning                               |
| -------------------- | -------------: | ------------------------------------- |
| `post_s9`            | `(n_saved, 9)` | selected joint posterior rows in S9   |
| `true_s9`            |         `(9,)` | M1 truth in S9                        |
| `names_s9`           |         `(9,)` | exactly `S9_NAMES`                    |
| `post_c9`            | `(n_saved, 9)` | `post_s9` converted by `DF-MAP-S9-C9` |
| `true_c9`            |         `(9,)` | `true_s9` converted by `DF-MAP-S9-C9` |
| `names_c9`           |         `(9,)` | exactly `C9_NAMES`                    |
| `ess_theta`          |         `(9,)` | per-S9-dimension ESS                  |
| `tau_theta`          |         `(9,)` | per-S9-dimension autocorrelation time |
| `ess_min`            |         scalar | `min(ess_theta)`                      |
| `n_saved`            | scalar integer | `floor(ess_min)`                      |
| `sampling_status`    |         string | M4 processing status                  |
| `convergence_status` |         string | ESS convergence classification        |

契约要求：

* `post_s9` 只能从 M1 已处理 `post.npy` 中确定性选择联合样本行；
* 所有 9 个参数必须使用相同的 selected rows，保持每行联合 posterior state；
* posterior 行顺序继承 M1 已处理 posterior，不得按参数值重新排序；
* `true_s9` 来源于 M1 `true.npy`，并必须与 `S9_NAMES` 校验一致；
* `post_c9` 和 `true_c9` 必须通过 `DF-MAP-S9-C9` 显式转换；
* `post_c9` / `true_c9` 的列顺序严格为 `C9_NAMES`；
* `ess_theta` / `tau_theta` 每一维严格对应 `S9_NAMES`；
* `ess_min = min(ess_theta)`；
* `n_saved = floor(ess_min)`；
* 不同事件允许不同 `n_saved`；
* 禁止 NaN padding、复制样本、随机补齐或逐参数独立抽样；
* `sampling_status=COMPLETE` 表示 M4 event-level payload 已成功生成；
* `CONVERGED` / `NOT_CONVERGED` 只表示 M4 ESS 判据，不改变 sampling completion 状态；
* M4 可以在 `events/{event_uid}/` 下新增 `post_ess_m4.hdf5`，但不得修改、替换或删除 M1-owned `post.npy`、`true.npy`、`names.npy`、`DONE` 或其它 M1 正式产物；
* event-level `post_ess_m4.hdf5` 通过 temporary file + atomic replace 写入。


## 4.6 `DF-SCHEMA-M5-RESULT`

M5 的 `results_m5.hdf5` 是独立的、按事件保存的 C9 posterior statistics 和 sky localization 结果。M5 的 posterior/truth 输入均来自 M4，不读取 M2 `results.hdf5` 作为输入。

```text
results_m5.hdf5
    event_summary
    events/{event_uid}/
        post_c9
        true_c9
        names_c9
        event_stats
        sky_stats
        skyarea
        m4_ess_theta
        m4_tau_theta
        m4_ess_min
        m4_n_saved
        m4_convergence_status
        source_stage = "M4"
```

契约要求：

- `post_c9` 直接来自 M4，M5 不再次执行 S9 -> C9、burn-in、thin 或 ESS 抽样；
- `true_c9` 来源于 M1 `true.npy` 的 S9 真值，经 M4 使用 `DF-MAP-S9-C9` 转换后传递；
- posterior statistics、sky statistics 和 A90 均在 C9 上计算，天空输入为 C9 的 `lambda` / `beta`；
- `CONVERGED` 与 `NOT_CONVERGED` 均为有效 M5 输入，M5 必须透传 M4 状态；
- `event_uid`、`names_c9`、统计字段、Nside、coverage 和 A90 键名与 M2 保持可比；
- 不得以 M2 的 truth、posterior 或结果文件替代缺失/无效的 M4 输入。

## 4.7 A90 稳定键

```text
A90 = sky_stats["union_by_nside"]["512"]["0.9000"]
```

单位：`deg^2`。

---

# 5. 时间与频率契约

## 5.1 `DF-TIME-001`

标准时域存储：

```text
fs = 0.01 Hz
Tobs = 5 days
Nt = 4320
```

并满足：

```text
Nt = fs * Tobs
```

## 5.2 `DF-FREQ-001` — Nyquist 边界

任何从 `noisysignal` 时域数组通过 FFT 得到的频域数据必须满足：

```text
|f| <= fs/2 = 0.005 Hz
```

因此历史文档中的：

```text
0.02 - 0.10 Hz
```

**不再是 source HDF5 time-series 的全局频带契约**。

它如果仍存在于某个频域 waveform / likelihood 函数中，只能解释为该函数自己的局部物理/数值配置，必须与时域 Nyquist 语义分开。

## 5.3 模型频率网格

直接由频域物理模型生成的数据可以使用模型自己的频率支持，例如：

```text
model_frequency_grid intersect configured_physical_band
```

若该计算同时消费 `noisysignal` FFT，则还必须：

```text
intersect Nyquist_band
```

---

# 6. SNR 契约

## `DF-SNR-001`

SNR 是事件级独立标量，不属于 A11/B12/NSF9/E5/S9/C9。

PTMCMC batch 当前 SNR 来源：

```text
d_ref = regenerated injection waveform
snr = sqrt(<d_ref | d_ref>)
```

要求：

```text
isfinite(snr)
snr > 0
```

禁止：

```text
append snr to true
append "snr" to names
read params[:,12] as snr
```

---

# 7. 事件身份与生命周期契约

## 7.1 `DF-IDENTITY-001`

首次 batch run 创建 immutable `input_manifest.json`。

每个 entry 至少包含：

```text
run_event_index
event_uid
source_file
source_row
```

`event_uid` 必须稳定，可由 normalized source path、source row 和 B12 hash 的 deterministic hash 构造。

后续断点续跑不得重新用 glob 顺序解释已有 event identity。

## 7.2 `DF-LIFECYCLE-DONE`

```text
events/{event_uid}/DONE
```

是 M1 event 完成状态的唯一 source of truth。

规则：

1. 所有正式输出先写临时路径；
2. close/flush；
3. atomic rename/replace；
4. 校验最终输出；
5. 最后创建 `DONE`。

缺 `DONE` 的事件即使有部分文件也属于 incomplete，M2 不得做正式统计。

---

# 8. 契约断言（Contract Tests）

建议每条稳定契约对应自动测试，而不是依赖人工重复审查。

| Contract ID | automated assertion |
|---|---|
| DF-PARAM-B12 | `params.shape[1] >= 12`; prefix semantics stable |
| DF-PARAM-NSF9 | index list and names exactly match |
| DF-PARAM-S9 | names/shape exactly match S9 |
| DF-PARAM-C9 | names/shape exactly match C9 |
| DF-MAP-B12-A11 | known-vector mapping test |
| DF-MAP-S9-C9 | scalar + batch transform, clipping test |
| DF-SNR-001 | SNR independent from `true/names` |
| DF-SCHEMA-M1-EVENT | required files + shapes + finite values + sampler-defined row order |
| DF-SCHEMA-M2-RESULT | S9/C9 datasets coexist and align |
| DF-SCHEMA-M4-RESULT | variable per-event S9/C9 effective samples, truth conversion, ESS/status alignment |
| DF-SCHEMA-M5-RESULT | M4 C9 posterior/truth input, statistics/sky parity and status propagation |
| DF-FREQ-001 | time-series FFT does not exceed Nyquist |
| DF-LIFECYCLE-DONE | partial output without DONE is incomplete |
| A90 | key `512/0.9000` exists and is finite positive |

---

# 9. 一句话总结

> 项目级参数与数据链统一为：**A11（waveform/likelihood）↔ B12 prefix（source labels）→ NSF9/E5（NSF 分支）以及 B12 → A11 → S9（PTMCMC M1）→ C9（PTMCMC M2）**。S9 与 C9 必须显式区分，NSF9 与 C9 也不得因同为 9 维而混同；SNR、event identity 和 DONE 均为独立契约字段。
