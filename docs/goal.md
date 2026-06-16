> **FORMTRIG 的最终说服力先来自收益，再来自设计：先证明它在真实实验里减少 R-to-T 成本、产生 matched-budget terminal/TTE 优势或稳定的可实验搜索收益，再用 `D_F`、BindingSpec、dominance frontier 和 typed mutation 解释这个收益为什么来自 FORMTRIG。**

换句话说，中间产物不是论文里的主指标，也不是和 CmpLog、Redqueen、AFL++ 直接比较的分数。
它们的价值必须体现在收益链上：

```text
Benefit first
  1. same-budget terminal success / first _T / TTE / PRET
  2. repeated-run success rate and cost, including exec/sec
  3. binary TC converted into accepted, saved, replay-stable non-trigger search progress
  4. triage savings: easy/control targets are filtered before long budget is spent

Design second
  5. D_F shows the pre-trigger progress that binary D_T cannot rank
  6. BindingSpec proves the signal is TC-rooted rather than target-specific leakage
  7. dominance frontier proves saved seeds are non-dominated progress, not noise
  8. typed mutation proves the signal is actionable at input-field or event level
```

正式结果表必须先回答“FORMTRIG 带来了什么收益”。只有当收益成立后，才展开解释“这个收益如何由 lift 机制产生”。如果同预算 faithful baseline 也能很快触发，目标应被降为 control/native-readiness 或 negative evidence，不能靠中间信号强行包装成性能优势。

当前 LIBARCHIVE_2936 的 60s signal-repair 结果给出了这个口径的最小正例：

```text
old saturated hit-role BindingSpec:
  _T = 0
  saved_non_trigger_progress = 0
  BindingSignal = fail / constant_lift_signal

path-table-count BindingSpec:
  _T = 0
  saved_non_trigger_progress = 3
  BindingSignal = pass / role_signal_progress_observed

root-distance BindingSpec:
  _T = 0
  saved_non_trigger_progress = 3
  D_F_spec_lifted = [1,0] instead of constant [2]
  non_trigger_candidate_lift_delta = true
  experiment_ready = true

root-distance BindingSpec 10m screen:
  _T = 0
  saved_non_trigger_progress = 10
  D_F_spec_lifted = [1,0]
  old FORMTRIG 10m saved_non_trigger_progress = 0
  AFL++ vanilla/CmpLog 10m _T = 0

root-distance + path-hierarchy typed hook 60s gate:
  terminal crashes = 4
  first terminal crash = 1.196s / exec 32
  first crash op = ftgtype
  crash signal = SIGSEGV
  D_F_spec_lifted = [1,0]
  BindingSignal = pass / role_signal_progress_observed
  hook provenance = binding_spec
```

因此 LIBARCHIVE_2936 的口径已经从“pre-trigger guidance only”推进到“pre-trigger guidance 被 typed mutation 转成 endpoint success”。这仍然不是最终 replicated 性能结论：Redqueen/operand-aware baseline 还缺失，且所有 baseline 需要用相同 terminal timeout/oracle 设置重跑；但它已经可以作为 FORMTRIG 中间产物产生端点收益的正例。

---

> **不是把 TC 的布尔结果或 native distance 直接拿来做 guidance，而是把 TC 提升成一组更细粒度、更稳定、可排序、可归因、可变异的 trigger-progress features。**

也就是说，FORMTRIG 的 lift 不是单纯“加一些 mutator”，而是四层同时发生：

```text
TC expression
  → TC atoms
  → trigger-progress graph
  → lifted progress vector
  → dominance-based progress frontier
  → typed mutation operators
```

其中最核心的是：

```text
D_T: native trigger distance
D_F: lifted trigger-progress signal
```

`D_T` 是直接从 TC 得到的距离。
`D_F` 是从 TC root、producer/use context、guard、event order、object identity、input influence 中提升出来的 progress。

---

# 1. Numeric-margin TC：从“原始数值差”lift 到“可控边界进展”

## 典型 TC

```c
len > cap
idx >= size
offset + n > limit
MIN_HDR_STORE - bytes_in_header > remain
```

## native distance

这类 TC 天然有数值 margin：

```text
D_T = max(0, cap - len + 1)
```

或者：

```text
D_T = max(0, limit - (offset + n) + 1)
```

所以 **numeric-margin 是 native distance 最可能有效的一类**。

FORMTRIG 在这一类上的思想不是强行替代 `D_T`，而是：

> 如果 native distance 是 actionable，就保留它；只有当它退化时才 lift。

## lift 如何体现

对于 numeric-margin，lift 主要体现在三个方面。

### 1.1 语义规范化

原始表达式里的 margin 不一定可靠。例如：

```c
offset + n > size
```

可能涉及：

```text
signedness
bitwidth
integer overflow
implicit cast
unit conversion
```

所以 FORMTRIG 不是简单算：

```text
abs(offset + n - size)
```

而是把它 lift 成：

```text
normalized_margin
bitwidth-aware margin
signedness-aware margin
overflow-aware boundary condition
```

也就是说，它把“表面数值差”提升成“符合程序语义的边界距离”。

### 1.2 输入可控性 lift

即使知道：

```text
len > cap
```

也不代表知道该改输入哪个 byte。
所以 FORMTRIG 需要把 runtime operand lift 到 input influence：

```text
len   ← 哪些 input ranges 控制？
cap   ← 哪些 input ranges 控制？
idx   ← 是否由 parser 派生？
size  ← 是否由 header / allocation 决定？
```

因此 progress 不是只有：

```text
margin decreased
```

还包括：

```text
operand became controllable
hot range confidence increased
boundary-related input field identified
```

### 1.3 边界事件 lift

例如：

```text
margin 从 100 降到 20
margin 从 20 降到 1
margin 从 1 跨过边界
```

这些不是普通 coverage 能看到的。
FORMTRIG 会把它们作为 trigger-progress feature：

```text
boundary crossing
near-boundary state
best-so-far margin
root-aligned margin improvement
```

## 这类的 lifted progress 可以写成

```text
D_F_numeric =
  <normalized_margin,
   boundary_crossing_state,
   operand_influence_confidence,
   reach_stability>
```

这里 `D_F` 仍然很接近数值距离，但比 native `D_T` 更语义化、更适合 mutation。

## 这一类的定位

numeric-margin 是 **positive control**：

```text
如果 D_T 有用，FORMTRIG 不应过度 lift。
如果 D_T 无法响应 mutation，再 lift 到 operand producer / input influence。
```

---

# 2. Equality / Magic TC：从“稀疏相等”lift 到“匹配进度和可修复结构”

## 典型 TC

```c
tag == MAGIC
type == PNG_COLOR_TYPE_PALETTE
memcmp(buf, "IHDR", 4) == 0
strcmp(name, "stream") == 0
checksum == computed_checksum
```

## native distance

常见直接距离是：

```text
D_T = |x - MAGIC|
```

或者：

```text
D_T = 0 if equal else 1
```

但这类 native distance 经常是误导性的。

例如：

```text
x1 = 0x0000ffff
x2 = 0x000100ff
target = 0x00010000
```

数值上 `x1` 可能更近，但从 byte-level mutation 看，`x2` 可能只需要改一个 byte。
所以 `|x - MAGIC|` 不等价于 mutation difficulty。

## lift 如何体现

Equality/magic 的 lift 不是把 equality 继续当成连续数值优化，而是提升成 **exact-match progress**。

### 2.1 operand visibility

先判断比较操作数是否可见：

```text
observed_value visible?
magic_value visible?
comparison site observed?
```

如果 operand 不可见，fuzzer 连该往哪里改都不知道。

所以 FORMTRIG 会产生：

```text
operand_visible
field_exposed
comparison_reached
```

这些都是 lifted features。

### 2.2 byte / token matching

对于 magic string 或 multi-byte constant，真正有意义的是：

```text
matched byte count
matched prefix length
hamming distance over bytes
token equality
dictionary hit
```

例如：

```c
memcmp(buf, "IHDR", 4) == 0
```

native distance 不应该是一个整数差，而应该是：

```text
I matched
IH matched
IHD matched
IHDR matched
```

即：

```text
prefix_match = 0,1,2,3,4
```

### 2.3 dictionary / operand lift

一旦 FORMTRIG 观察到：

```text
expected operand = "IHDR"
expected enum = 3
expected type = PALETTE
```

它会把这些提升成 mutation resource：

```text
dictionary token
endian variants
quoted/string variants
field-level replacement candidate
```

### 2.4 transformed equality lift

对于：

```c
checksum == computed_checksum
```

或者：

```c
decoded_len == expected_len
```

简单替换 magic 不够，因为 operand 是派生出来的。

这时 lift 应该变成：

```text
derived_value_alignment
repair_hook_available
checksum_field_identified
length_field_repair_success
```

也就是说，不是随机逼近 checksum，而是识别并修复派生关系。

## 这类的 lifted progress 可以写成

```text
D_F_equality =
  <field_exposed,
   operand_visible,
   matched_bytes_or_prefix,
   dictionary_hit,
   derived_value_alignment,
   repair_success>
```

## 这一类的定位

Equality/magic 不是 FORMTRIG 最强 novelty，因为 AFL++ CmpLog、RedQueen、Angora 这类方法在 direct comparison 上已经很强。
FORMTRIG 的价值主要是：

```text
把 equality/magic 放进 TC-rooted progress 框架里；
区分 direct equality 和 transformed equality；
在 compound TC 中把 equality atom 和 binary/lifecycle atom 组合起来。
```

---

# 3. Binary-state-null TC：从“0/1 结果”lift 到“状态翻转因果链”

## 典型 TC

```c
ptr == NULL
ctx->palette == NULL
obj->initialized == false
state == CLOSED
resource_exists == false
type_check(obj) == expected_type
```

## native distance

这类的 native distance 几乎必然退化：

```text
D_T =
  0 if ptr == NULL
  1 otherwise
```

在所有 reached-but-not-triggered seeds 上：

```text
D_T = 1
```

因此它只能告诉你：

```text
还没触发
```

但不能告诉你：

```text
哪个 seed 更接近触发
```

这就是 FORMTRIG 最重要的 lift 场景之一。

## lift 如何体现

Binary-state-null 的核心思想是：

> 不优化 final binary predicate，而是优化导致该 predicate 成立的 producer/use 因果路径。

也就是说，不要试图把 pointer 数值 mutate 成 0。
真正应该做的是找：

```text
谁给 root state 赋值？
谁初始化它？
谁清空它？
哪个 guard 决定 producer 是否执行？
哪个 error path 会让它变成 NULL？
哪个 use site 需要保留？
```

## 示例

TC：

```c
ctx->palette == NULL
```

普通 native distance：

```text
D_T = 1 for all non-null palette
```

FORMTRIG lift 后，不再只看 `palette` 当前是不是 NULL，而是构造一个 state-transition progress：

```text
P0: target context reached
P1: root variable ctx->palette observed
P2: guard condition requires palette-related path
P3: palette producer parse_palette() reached
P4: producer skipped / failed / reset executed
P5: no later non-NULL overwrite
P6: use context reached with desired root state
```

这里的 progress 是：

```text
producer reached
desired transition executed
opposite producer bypassed
reset path executed
use reached
root-use aligned
```

而不是：

```text
pointer address closer to zero
```

## 这类的 lifted progress 可以写成

```text
D_F_binary =
  <guard_progress,
   root_observed,
   producer_reached,
   desired_producer_or_reset_executed,
   opposite_producer_bypassed,
   no_overwrite_after_desired_state,
   use_context_reached,
   root_use_alignment>
```

## mutation 如何跟 lift 对应

Binary-state-null 的 mutator 也不是普通 havoc，而是围绕状态翻转：

```text
optional-region deletion
guard-field perturbation
error-path induction
initialization-bypass mutation
reset/cleanup-path mutation
```

例如：

```text
删除可选 chunk，使对象不被初始化；
改变 type tag，使初始化分支不走；
改变 length/count，让 allocation/init 失败；
触发 cleanup/reset path；
保留 use site reachable。
```

## 这一类的本质

Binary-state-null 的 lift 是最典型的：

```text
final predicate distance
  ↓
state-transition distance
```

也就是：

> 从“root 是否已经是目标状态”提升到“执行是否正在沿着导致 root 变成目标状态的因果链前进”。

---

# 4. Compound-sequence-lifecycle TC：从“最终条件”lift 到“事件自动机进度”

## 典型 TC

```text
free(x) before use(x)
open → close → use
init → configure → trigger
parse header → skip object → use object
state A → state B → state C
same object released and later used
```

## native distance

如果直接把 sequence TC 写成布尔条件：

```text
D_T = 0 if free(x) before use(x)
D_T = 1 otherwise
```

那么所有没完整满足 sequence 的 seeds 都一样：

```text
D_T = 1
```

但它们其实完全不同：

```text
seed1: 已经 alloc，只差 free/use
seed2: 已经 alloc+free，但 use 没到
seed3: free 和 use 都到了，但顺序反了
seed4: free 和 use 都到了，但不是同一个对象
seed5: 已经同对象 free，只差后续 use
```

native distance 无法区分这些情况。

## lift 如何体现

Compound/lifecycle 的 lift 是：

> 把 TC 从一个 final predicate 提升成一个 finite-state automaton / event-progress graph。

即：

```text
TC = e1 before e2 before ... before ek
```

lift 成：

```text
automaton prefix
next event reachability
object identity confidence
phase novelty
guarded transition progress
```

## 示例

TC：

```text
free(obj) before use(obj)
```

FORMTRIG 不只看：

```text
free_seen && use_seen
```

而是看：

```text
P0: object created
P1: same object identified
P2: release/free event observed
P3: no reallocation/reinitialization invalidates relation
P4: use site reached
P5: use happens after free on same object
```

如果一个 seed 满足：

```text
free(x)
use(y)
x != y
```

它不能算真正的 lifecycle progress。
所以 FORMTRIG 必须加入：

```text
object_identity_confidence
```

这就是 SAME_OBJECT lift。

## 这类的 lifted progress 可以写成

```text
D_F_lifecycle =
  <automaton_prefix_length,
   next_event_reachability,
   object_identity_confidence,
   phase_context_novelty,
   guard_status,
   use_context_reached>
```

## mutation 如何跟 lift 对应

Lifecycle TC 的 mutator 是 sequence-level 的：

```text
event insertion
event deletion
event duplication
event reordering
phase-preserving mutation
object-identity alignment
```

例如：

```text
插入一个 close/free 事件；
删除重新初始化事件；
复制某个 object reference；
调整 chunk/message 顺序；
保留 producer phase，同时推动 use phase。
```

## 这一类的本质

Compound/lifecycle 的 lift 是：

```text
final Boolean TC
  ↓
event-sequence automaton progress
```

也就是：

> 从“最终是否满足顺序关系”提升到“当前执行已经匹配了多少前缀、下一个事件是什么、是否还是同一个对象”。

---

# 5. 四类 TC 的 lift 总表

| TC 类别                       | native distance 形态  | 退化原因                                    | lift 后的 progress                                                              | FORMTRIG 关注点                             |
| --------------------------- | ------------------- | --------------------------------------- | ----------------------------------------------------------------------------- | ---------------------------------------- |
| numeric-margin              | 数值 margin           | attribution 错、overflow/signedness、表达式派生 | normalized margin, boundary crossing, operand influence                       | 保留有用 native distance；必要时 lift 到语义边界和输入控制 |
| equality/magic              | `abs(x-C)` 或 0/1    | 稀疏匹配，数值距离不等于 mutation 距离                | operand visibility, matched bytes, prefix, dictionary, repair hook            | 从数值差 lift 到 exact-match progress         |
| binary-state-null           | 0/1                 | 所有 non-trigger seeds indistinguishable  | producer/use state transition, guard, reset, no-overwrite, root-use alignment | 从 final state lift 到状态翻转因果链              |
| compound-sequence-lifecycle | final Boolean / AND | 丢失顺序、阶段、对象身份                            | automaton prefix, next event, object identity, phase progress                 | 从 final predicate lift 到事件自动机            |

---

# 6. 在算法里，lift 应该体现在哪些位置？

对应你现在的 FORMTRIG 设计，lift 不是一个单独函数，而是贯穿五个位置。

## 6.1 `BuildTCIR`

这里把 TC 从字符串表达式 lift 成结构化 IR：

```text
C
  → atoms
  → ALL_OF / ANY_OF / GUARD / SEQUENCE / SAME_OBJECT
```

例如：

```c
color_type == PALETTE && palette == NULL
```

会被分成：

```text
atom1: equality/magic
atom2: binary-state-null
group: ALL_OF
guard/use relation
```

## 6.2 `BuildTriggerProgressGraph`

这里把 atom lift 到程序上下文：

```text
root variable
producer
guard
use
event order
object identity
input influence range
```

例如：

```text
palette == NULL
```

会关联到：

```text
parse_palette()
palette assignment
palette reset
use_palette()
```

## 6.3 `ComputeSignalHealth`

这里决定 native `D_T` 是否 actionable：

```text
actionable:
  keep native distance

degenerated:
  lift to D_F

unknown:
  hybrid plan
```

这一步非常重要。
FORMTRIG 不是一上来就 lift，而是 **selective lifting**。

## 6.4 `LiftedObservation`

这里把 raw runtime signal lift 成 progress features：

```text
D_F
root_state
producer/use state
lifecycle prefix
object identity confidence
hot ranges
```

注意：

```text
T 不能参与 non-trigger D_F 计算。
```

`T` 只能作为终止 oracle，不能泄漏进 progress。

## 6.5 `ProgressDominatesGlobal`

这里决定哪些 lifted progress 值得保存：

```text
TC-rooted
replay-stable
reach-preserving
non-dominated
no higher-priority regression
```

也就是说，lift 后不是所有 novelty 都保存。
必须是 **TC-rooted progress**。

---

## 7. 当前工程交接

当前 native FORMTRIG 工程状态、已验证证据、风险和下一步执行项记录在：

```text
docs/formtrig_native_handoff_20260615.md
```
