# Agent 代码验收通用规范 v0.1

## 1. 目标

本规范定义所有 AI Agent 代码任务共同遵守的最低验收标准。

原则：

> Agent 可以生成代码、测试和文档，但不能自行降低、修改或重新定义验收标准。

任务只有在：

```text
Requirement satisfied
+
Automated tests passed
+
Human-required items reviewed
```

三者均满足后，才可认为完成。

---

## 2. 权威来源

验收时按以下项目文件确定正确性：

| 类型                      | 项目文件                       | 权威内容                                             |
| ----------------------- | -------------------------- | ------------------------------------------------ |
| Project Rules           | `AGENT.md`                 | Agent 修改边界、工作方式、禁止事项                             |
| Data Contract           | `pipeline_dataflow_bbh.md` | 参数空间、映射、schema、SNR、frequency、event identity、DONE |
| Project Requirement     | `requirement_bbh.md`       | 项目级科学目标和基线行为                                     |
| Feature Requirement     | `requirement_*.md`         | 当前子任务的功能行为和 Acceptance Criteria                  |
| Architecture            | `sad_*.md`                 | 模块职责、依赖、接口、状态机和异常边界                              |
| Implementation Evidence | code + tests               | 实现与自动验证证据                                        |

验收优先级：

```text
AGENT.md                 -> 修改边界
pipeline_dataflow_bbh.md -> 数据语义
relevant requirement_*.md -> Feature 正确行为
relevant sad_*.md        -> 软件架构边界
code + tests             -> 实现证据
```

Agent 不应自行猜测哪个 Requirement/SAD 与任务相关，应根据 `AGENT.md` §4 的上下文路由选择对应文件。

若无法确定对应 Requirement 或 SAD：

```text
NEEDS_HUMAN_REVIEW
```

不得自行选择一个文件作为权威来源。


---

# 3. 每个 Agent 任务必须提交的内容

至少包括：

```text
1. Implementation
2. Unit tests
3. Relevant integration/contract tests
4. Documentation update（如需要）
5. Runnable example（新增用户功能时）
6. Test report
7. Changed-files summary
8. Known limitations
```

Agent 不得仅报告：

```text
"Implementation completed."
"All tests passed."
```

必须提供实际执行证据。

---

# 4. 自动验收最低要求

## A1. Basic correctness

必须满足：

* 无 syntax error；
* 可正常 import；
* 正常输入可运行；
* 非法输入有明确失败；
* 不产生意外 NaN / Inf；
* 输出 shape / dtype 符合要求。

结果：

```text
PASS / FAIL
```

---

## A2. Unit tests

新增或修改的核心逻辑必须有 unit tests。

至少覆盖：

```text
normal case
boundary case
invalid input
```

关键计算还应验证：

```text
expected numerical result
```

禁止只有：

```python
assert result is not None
```

或：

```python
assert len(result) > 0
```

这类只能证明代码执行过的弱测试。

---

## A3. Test Oracle

关键测试必须能够回答：

> expected result 从哪里来？

允许的依据：

```text
Data Contract
analytical solution
independent mathematical calculation
trusted reference implementation
validated benchmark
manually constructed deterministic case
```

禁止用被测试实现自己生成 expected value。

---

## A4. Integration / Contract

如果修改跨模块行为，必须测试：

```text
producer
   ↓
interface / data contract
   ↓
consumer
```

至少检查：

* names；
* shape；
* parameter order；
* coordinate space；
* status；
* file/schema；
* input/output ownership。

只修改纯内部实现且没有跨模块影响时，可以不增加 integration test。

---

## A5. Regression

Agent 必须回答：

```text
What existing behavior could this change break?
```

若存在明确风险，应增加 regression test。

已有正确行为不得因为新增功能而无意改变。

---

## A6. Failure path

不仅测试成功路径。

至少确认相关失败场景：

```text
bad input
missing input
corrupt input
dependency failure
write failure
```

失败必须：

```text
fail explicitly
or
produce defined skip/error status
```

禁止：

```text
catch Exception
→ silently continue
```

也禁止自动伪造数据使流程继续。

---

# 5. 修改范围验收

Agent 必须报告：

```text
Files changed:
- ...

Expected:
- ...

Unexpected:
- NONE
```

Reviewer 应特别关注：

```text
Data Contract
Requirement
CI configuration
test thresholds
public config
persistent schema
physics/math core
```

如果任务没有授权修改这些文件，却发生修改：

```text
REVIEW REQUIRED
```

---

# 6. Agent 禁止自行修改的内容

除非任务明确授权，Agent 不得为了使任务通过而：

* 修改 Requirement；
* 修改 Data Contract；
* 降低测试阈值；
* 删除失败测试；
* 放宽 assertion；
* 增加忽略规则；
* 修改 CI gate；
* 将错误状态改成成功状态；
* 修改 benchmark/reference answer。

例如：

```text
test failed
→ lower tolerance
→ PASS
```

不是有效修复。

---

# 7. 测试结果状态

统一使用：

```text
PASS_AUTOMATED
FAIL_AUTOMATED
NEEDS_HUMAN_REVIEW
```

Test Agent 不得自行给出：

```text
FINAL_ACCEPTED
```

最终 acceptance 属于人类 Reviewer。

---

# 8. Human Review 最小检查

人类不需要逐行检查所有代码。

必须确认：

```text
[ ] 任务实现的是正确 Requirement

[ ] 没有违反 Data Contract / public interface

[ ] 核心数学/物理/业务语义正确

[ ] Test Oracle 独立可信

[ ] 没有未经授权扩大修改范围

[ ] 没有降低测试或 CI 标准

[ ] 高风险 regression 已有 evidence
```

这些通过后才：

```text
APPROVE
```

否则：

```text
REQUEST CHANGES
```

---

# 9. Hard Reject Conditions

出现以下任一情况，直接判定验收失败：

### H1

违反已定义的数据契约。

### H2

关键 Requirement 没有对应 implementation。

### H3

关键 Requirement 没有测试 evidence。

### H4

测试 expected value 来自被测试实现自身。

### H5

Agent 为通过测试而降低标准。

### H6

未经授权修改 public schema / API / parameter semantics。

### H7

未经授权修改 CI / test gate。

### H8

隐藏或忽略真实失败。

---

# 10. 每个子任务的专项验收

通用规范不为每个功能定义具体数学和业务正确性。

每个任务只需增加一个很短的：

```text
Task Acceptance Criteria
```

建议格式：

```text
Task:
<feature name>

Inputs:
<expected inputs>

Outputs:
<expected outputs>

Must:
1. ...
2. ...
3. ...

Must not:
1. ...
2. ...

Tests required:
- ...
- ...

Human audit:
- ...
```

专项规则只描述这个任务独有的风险和正确性条件。

---

# 11. Test Agent 标准输出

Test Agent 完成检查后统一报告：

```text
Task:
...

Automated Result:
PASS_AUTOMATED | FAIL_AUTOMATED

Tests executed:
- ...

Passed:
- ...

Failed:
- ...

Contract violations:
- NONE / ...

Unexpected changes:
- NONE / ...

Regression risks:
- ...

Human review required:
- ...

Final human acceptance:
NOT PERFORMED
```

---

# 12. 核心原则

整个项目只维护：

```text
One common acceptance standard
        +
Small task-specific acceptance criteria
```

而不是：

```text
one completely different testing standard
for every task
```

目标是：

```text
Agent负责执行
CI负责客观检查
Human负责定义和判断正确性
```
