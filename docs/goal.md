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

正式结果表必须先回答“FORMTRIG 带来了什么收益”。只有当收益成立后，才展开解释“这个收益如何由 lift 机制产生”。如果同预算 faithful baseline 比 FORMTRIG 更快或相近触发，目标应被降为 control/native-readiness 或 negative evidence，不能靠中间信号强行包装成性能优势；如果 baseline 也触发但 FORMTRIG 的 first `_T`/TTE/exec 明显更早，那么口径必须是 speedup benefit，而不是“baseline 做不到”。

主 SOTA-pain 证据还必须额外证明二值 TC 对 baseline 没有可用指导，而不是只证明 FORMTRIG 有中间信号。判定条件固定为：

```text
baseline no-guidance proof gate
  1. baseline-visible TC signal 在 `_T` 前是常量/二值平台：
       reached-but-not-`_T` seeds 的 unique values 很少，最好为 1；
       entropy 接近 0；
       accepted non-trigger improvement 为 0。
  2. baseline endpoint 行为表现为随机命中成本：
       多 repetition 下 `_T` late / missing / high-variance；
       最快强 baseline 不能落在可接受时间阈值内。
  3. FORMTRIG 同时满足收益和机制：
       same-budget terminal/TTE/exec 优势成立；
       `_T` 前有 replay-stable、TC-rooted、accepted/saved 的 `D_F` progress。
```

只有同时满足这三条，才能写成“二值 TC 对 SOTA baseline 缺少指导，baseline 主要靠随机撞见 `_T`，FORMTRIG 解决了一部分 R2T 指导问题”。如果 baseline 在 210s、几十秒甚至更早稳定触发，即使 FORMTRIG 更快，也只能写 speedup/control/attribution，不能写 hard SOTA-gap。

这个 gate 现在由 `tools/analyze_baseline_guidance_gap.py` 生成可审计结果。它读取
baseline `summary.json` / `run_record.json`，分开记录：

```text
1. pre-trigger binary flatness:
   Magma monitor 是否显示 first _T 前已经有 R-not-T 区域，
   此时 binary TC oracle 对所有 reached non-trigger executions 都只是同一个 false 值。
2. endpoint cost:
   faithful baselines 是否 late / missing / high-variance，
   且没有任何强 baseline 在 acceptable threshold 600s 内触发。
3. final status:
   measured_pass 才能进入 hard SOTA-pain 候选；
   fail_fast_baseline / not_measured / under_replicated 都不能写主结论。
```

当前三个已分析包都没有通过 hard SOTA-pain gate：

```text
PHP009 600s x1:
  status = fail_fast_baseline
  pre-trigger binary flatness = pass
  fastest baseline _T = 120s

TIF012 B5 7200s x3:
  status = fail_fast_baseline
  pre-trigger binary flatness = pass
  fastest baseline _T = 210s

LIBARCHIVE_2936 7200s x3:
  status = fail_fast_baseline
  pre-trigger binary flatness = not_measured by Magma monitor
  fastest baseline terminal crash = 9.456s
```

PHP009 600s x1 matched short-screen 已完成，结论也按这个 gate 处理：

```text
FORMTRIG:
  strict pre-trigger guidance = true
  first _T = 87.04s exact progress/queue time
  first _T monitor upper bound = 120s
  total _T = 37120
  accepted_non_trigger = 4
  saved_non_trigger = 4
  spec_lifted = 12362

AFL++ vanilla:
  first _T monitor upper bound = 270s
  total _T = 43

AFL++ CmpLog:
  first _T monitor upper bound = 300s
  total _T = 9

local RedQueen/operand path:
  first _T monitor upper bound = 120s
  total _T = 20

comparison verdict:
  positive_speedup_matched_comparison
  main_claim_strength = not_hard_pain_baseline_fast_enough
```

因此 PHP009 能说明 FORMTRIG 的 TC-rooted lift 在 numeric-margin TC 上产生了真实
指导，并把 first `_T` 推到比三条 baseline 的 monitor 上界更早；但它不能证明
SOTA baseline 对二值 TC 没有指导、只能随机撞，因为 fastest baseline 120s 触发
仍在可接受成本内。它保留为 speedup/control/attribution evidence，主 SOTA-pain
证明要继续找 baseline `_T` late/missing/high-variance 且 pre-`_T` 信号 flat/binary
的硬目标。

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
  D_F_spec_lifted values = {0,1} instead of constant {2}
  non_trigger_candidate_lift_delta = true
  experiment_ready = true

root-distance BindingSpec 10m screen:
  _T = 0
  saved_non_trigger_progress = 10
  D_F_spec_lifted values = {0,1}
  old FORMTRIG 10m saved_non_trigger_progress = 0
  AFL++ vanilla/CmpLog 10m _T = 0

root-distance + path-hierarchy typed hook 60s gate:
  terminal crashes = 4
  first terminal crash = 1.196s / exec 32
  first crash op = ftgtype
  crash signal = SIGSEGV
  D_F_spec_lifted values = {0,1}
  BindingSignal = pass / role_signal_progress_observed
  hook provenance = binding_spec

matched 60s x3 with the same -t 5000+ terminal oracle:
  FORMTRIG: 3/3 _T, first _T values = 1.196s, 2.000s, 1.326s; median exec = 32
  AFL++ vanilla: 3/3 crashes, first crash values = 22.883s, 24.450s, 37.648s
  AFL++ CmpLog: 3/3 crashes, first crash values = 34.169s, 28.505s, 60.976s
  AFL++ Redqueen/operand path: 2/3 crashes, successful first crash values = 34.587s, 30.505s
  FORMTRIG vs fastest successful baseline family by median:
    18.44x faster by first _T wall-clock
    1074.34x fewer executions to first terminal crash
  separation: every FORMTRIG rep triggers before every successful baseline rep

matched 10m confirmation with the same -t 5000+ terminal oracle:
  FORMTRIG: first _T = 1.220s / exec 32, saved_crashes = 9
  AFL++ CmpLog: first crash = 20.671s / exec 28677
  AFL++ vanilla: first crash = 25.844s / exec 39789
  AFL++ Redqueen/operand path: first crash = 62.335s / exec 102947
  FORMTRIG vs fastest successful baseline in this run:
    16.94x faster by first _T wall-clock
    896.16x fewer executions to first terminal crash
  mechanism: D_F_spec_lifted values = {0,1}, saved_non_trigger_progress = 5

matched 7200s x3 with the same -t 5000+ terminal oracle:
  FORMTRIG: 3/3 _T, first _T = 1.358s, 2.320s, 1.494s
  AFL++ vanilla: 3/3 _T, median first _T = 56.056s, fastest = 42.154s
  AFL++ CmpLog: 3/3 _T, median first _T = 52.977s, fastest = 51.275s
  AFL++ Redqueen/operand path: 3/3 _T, median first _T = 32.517s, fastest = 9.456s
  FORMTRIG vs fastest successful baseline run:
    6.96x faster by first _T wall-clock
  FORMTRIG vs fastest successful baseline-family median:
    23.94x faster by first _T wall-clock
  experiment strength gate:
    not_hard_pain_baseline_fast_enough
```

因此 LIBARCHIVE_2936 的口径已经从“pre-trigger guidance only”推进到“pre-trigger guidance 被 typed mutation 转成 endpoint success”，并且在同预算、同 timeout/oracle 下复现了 first `_T` speedup。但完整 2h x3 结果也证明：这个目标的当前 harness/RNT 设计不能体现 SOTA 工具的痛点。三个 baseline family 全部 3/3 触发，最快 baseline run 只有 9.456s；这说明该 replay harness 和 seed 对 baseline 也足够友好。它现在只能作为真实 CVE speedup + attribution 工程证据，不能作为主结果里的 hard SOTA-gap 证据。

这不是改论文口径来退缩，而是实验设计 gate 的结果：`tools/compare_formtrig_baselines.py` 现在输出 `experiment_strength.main_claim_strength=not_hard_pain_baseline_fast_enough`；triage/worklist 会把 LIBARCHIVE_2936 降为 speedup/control evidence，要求更高保真/raw-format harness、更远 RNT seeds、no-hook/generic-hook ablation，或把 hard-gap 预算转向 baseline 在可接受时间内无法稳定触发的 Magma/真实 CVE 目标。

LIBARCHIVE_2936 现在也有了第一版 external typed-hook ablation smoke：

```text
60s x1 same seed/oracle ablation:
  hooked BindingSpec target-specific external hook:
    first _T = 1.196s / exec 32, terminal crashes = 4
  no external hook, built-in FORMTRIG typed mutation only:
    first _T = 25.652s / exec 18532, terminal crashes = 7
  generic external delimiter/range hook:
    first _T = 55.178s / exec 44842, terminal crashes = 1

attribution:
  target-specific hook is 21.45x faster than no-hook by first _T
  target-specific hook is 46.14x faster than generic-hook by first _T

claim boundary:
  this is a 1-rep smoke, so it is not final ablation evidence
  no-hook and generic-hook controls also trigger, so this target remains weak
  SOTA-gap evidence under the current harness/RNT design
```

这个结果有两个作用。第一，它把“是不是 harness 把漏洞写在脸上”进一步拆开：即使不使用 target-specific hook，FORMTRIG 内置 typed stage 和 generic hook 都能在 60s 内触发，说明当前 LIBARCHIVE seed/harness 确实偏近。第二，它证明 target-specific BindingSpec hook 不是没有贡献：它显著降低了 R2T 时间和 exec 成本。后续主证据不能靠 LIBARCHIVE 当前 harness，但 typed-hook 归因实验可以沿用这套 `hooked/nohook/generic` ablation runner 和 summarizer。

当前 TIF012 B5 7200s x3 matched long-run 给出了 Magma 上更长预算的同类结论：

```text
FORMTRIG B5:
  3/3 terminal _T
  first _T = 0.035s, 0.036s, 0.034s
  first trigger queue/progress exec = 146 in all three rows

AFL++ vanilla:
  3/3 terminal _T
  first _T = 930s, 1410s, 1560s
  median first _T = 1410s

AFL++ CmpLog:
  1/3 terminal _T
  first _T = 4950s in the successful rep
  2/3 have no _T in 7200s

local AFL++ Redqueen/operand path:
  2/3 terminal _T
  first _T = 6540s and 210s in successful reps
  1/3 has no _T in 7200s

FORMTRIG vs fastest individual successful baseline run:
  6176.47x faster by first _T wall-clock upper bound

FORMTRIG vs fastest successful baseline-family median:
  41470.59x faster by first _T wall-clock upper bound
```

TIF012 因此也不是“baseline 做不到”或“baseline 时间成本不可接受”的 hard-gap 目标：vanilla 是 3/3 成功，Redqueen/operand 也有一个 210s 成功 rep。它的价值是严格的 speedup/control 证据：FORMTRIG 把同一个 repaired typed trigger knowledge 转成了稳定的早期 terminal evidence，但 faithful baseline 已经在可接受时间内触发，所以当前 harness/seed 设计不能证明随机撞见 TC 触发的概率小到构成 SOTA 痛点。注意这个 run 的 strict pre-trigger gate 是 mixed：3 个 FORMTRIG rep 都 endpoint 成功，但只有 1/3 满足 `strict_pretrigger_guidance=true`；因此论文主收益应写 endpoint TTE speedup 和 typed-repair attribution，不能写成连续非触发 `D_F` 梯度成功，也不能写成 hard SOTA-pain 证据。

当前 PDF003 7200s x3 matched run 是第一个通过 baseline no-guidance proof gate 的
Magma hard-target 候选：

```text
baseline guidance gap:
  status = measured_pass
  interpretation = baseline evidence supports a hard binary-TC no-guidance candidate
  pre-trigger binary flatness = pass
  endpoint cost = pass

AFL++ CmpLog:
  0/3 _T in 7200s
  total R = 1,573,928
  total T = 0
  zero-T rule-of-three upper bound per reached exec ~= 1.91e-6

AFL++ vanilla:
  1/3 _T
  first _T = 5670s
  2/3 missing

local AFL++ Redqueen/operand path:
  1/3 _T
  first _T = 4530s
  2/3 missing

FORMTRIG:
  3/3 _T
  best first _T upper bound = 0.31s
  total terminal-triggered counts by rep = 7693, 7246, 6607
  speedup over fastest successful baseline run = 14612.90x
```

这个包能支撑的收益是 hard-target speedup/reliability：同预算下 baseline 的
pre-`_T` 可见信号 flat/binary，endpoint late/missing/high-variance，而 FORMTRIG
稳定很早触发 `_T`。但它不能支撑严格的 pre-trigger `D_F` 机制胜利：
`strict_pretrigger_guidance=false` for 3/3，`accepted_non_trigger=0`，
`saved_non_trigger=0`。原因不是 baseline gap 不存在，而是 FORMTRIG 几乎立即进入
terminal 区域，缺少 `_T` 前 accepted/saved non-trigger progress 样本。因此 PDF003
现在应写成“hard binary-TC no-guidance candidate with strong endpoint benefit, but
mechanism still needs a separate pre-trigger-guidance target or ablation”，不能把中间机制
夸成已经被这个 target 证明。

PDF016 现在已经从 dependency/native-build blocker 中解锁，但还不是长测目标：

```text
native build:
  executable = artifacts/formtrig_native_readiness/magma_native_builds/PDF016/out/afl/pdf_fuzzer
  site_map = artifacts/formtrig_native_readiness/magma_native_builds/PDF016/out/formtrig_native/formtrig_sites.tsv
  site rows = 47051
  dependency preflight = ok for cairo/openjpeg/tiff/lcms2

B3 BindingSpec:
  artifact = artifacts/binding_specs/PDF016.native_b3_parser_ref_candidate.yml
  roles = lifecycle_event + use + root_observe + same_object
  audit = B3 pass

600s validation with -t 5000:
  status = not_ready
  diagnosis = triggered
  execs = 3431
  reached = 3354
  triggered = 8
  saved_triggered = 1
  accepted_non_trigger_progress = 0
  saved_non_trigger = 0
  binding_signal = pass / triggered
```

PDF016 的当前价值是工程解锁和负向机制诊断：spec wiring 已经能通过 B3 audit，也能触发
terminal oracle，但还没有把 lifecycle/root signal 转成 non-trigger frontier progress。
下一步不能直接上 matched screen；应先补 input-influence/range signal 或 parser-token
typed mutation，让 `_T` 前出现 accepted/saved non-trigger progress。

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

---

## 8. 2026-06-17 证据边界

当前结果还不能宣称“已经充分体现 SOTA 工具的痛点”。

这里的“痛点”按当前验收口径指：faithful baseline 只能靠随机性撞见 TC 触发，且随机撞见的时间成本不可接受。单纯证明 FORMTRIG 更快还不够；如果任一强 baseline 在可接受时间内已经触发，例如 210s，那么该 target 只能支持 speedup/control/attribution，不支持 hard SOTA-pain 主结论。

这个判断现在由 `artifacts/formtrig_native_readiness/hard_target_triage_20260617.*`
里的 `sota_pain_class` 显式给出，而不是靠人工解释：

```text
TIF012:
  sota_pain_class = not_visible_baseline_time_cost_acceptable
  main_claim_strength = not_hard_pain_baseline_fast_enough
  FORMTRIG first_T = 0.034s
  fastest successful baseline run = 210s
  fastest baseline-family median = 1410s
  speedup over fastest successful baseline run = 6176.47x
  interpretation = strong speedup/control evidence, not hard-pain evidence

LIBARCHIVE_2936:
  sota_pain_class = not_visible_baseline_time_cost_acceptable
  main_claim_strength = not_hard_pain_baseline_fast_enough
  FORMTRIG first_T = 1.358s
  fastest successful baseline run = 9.456s
  interpretation = real-CVE speedup/attribution evidence, not hard-pain evidence

LIBCOAP_CVE_2023_35862:
  sota_pain_class = not_visible_baseline_visible_no_formtrig_advantage

PNG006:
  sota_pain_class = not_visible_baseline_visible_no_formtrig_advantage

promoted hard-target candidates:
  0
```

因此当前没有任何 target 可以作为主 SOTA-pain 证据。TIF012 和 LIBARCHIVE_2936
仍有价值：它们证明 FORMTRIG 能把 typed trigger knowledge 转成极早 `_T`，也能
支持 attribution 和工具可用性；但它们不能证明“baseline 随机撞见 TC 的成本不可接受”。

同一个判断已经进入执行队列：

```text
artifacts/formtrig_native_readiness/hard_target_experiment_worklist_20260617.*

LIBARCHIVE_2936:
  skipped from main budget
  reason = sota_pain_triage_not_main_budget / baseline time cost acceptable

TIF012:
  skipped from main budget
  reason = sota_pain_triage_not_main_budget / baseline time cost acceptable

PNG006 / LIBCOAP_CVE_2023_35862:
  skipped from main budget by sota_pain_triage_not_main_budget

next main-budget candidates:
  PDF003, SSL015, PDF016, PHP009, LIBXML2_1107, GPAC_3403
```

也就是说，现在不是只在文档里承认“看不出来”，而是实验 planner 会直接阻止这些
target 继续进入主长测预算。

2026-06-18 的更新是：PDF003 7200s x3 matched result 已经进入自动 triage，
并成为当前唯一 promoted hard-target candidate：

```text
artifacts/formtrig_native_readiness/hard_target_triage_20260618.*
  promoted hard-target candidates = 1

PDF003:
  disposition = candidate_extend_longruns
  sota_pain_class = visible_hard_speedup_or_reliability
  baseline_guidance_gap_status = measured_pass
  FORMTRIG first_T = 0.31s
  fastest successful baseline run = 4530s
  speedup over fastest successful baseline run = 14612.90x

TIF012 / PHP009 / LIBARCHIVE_2936:
  disposition = demote_to_control_or_negative
  reason = baseline guidance-gap gate is fail_fast_baseline

PNG006 / LIBCOAP_CVE_2023_35862:
  disposition = demote_to_control_or_negative
  reason = baseline-visible/no FORMTRIG advantage in current package
```

新的 budget 队列是：

```text
artifacts/formtrig_native_readiness/hard_target_experiment_worklist_20260618.*

P0:
  PDF003 -> expand_cross_target_hard_evidence
  rationale = matched 7200s x3 already complete; do not burn budget repeating
              the same campaign until another Magma/real-CVE hard target exists

P1:
  SSL015 -> validate_binding_spec_then_short_screen
  PDF016 -> validate_binding_spec_then_short_screen
  LIBXML2_1107 -> validate_binding_spec_then_short_screen
  GPAC_3403 -> validate_replay_then_draft_binding_spec
```

PDF016 在 2026-06-18 worklist 中也从“未验证”变成明确的 repair/negative target：

```text
artifacts/formtrig_native_readiness/binding_validation/PDF016.native_b3_parser_ref_candidate.validation.json
  status = terminal_only_variable_semantic_roles_no_pretrigger_guidance
  native_site_map_validated = true
  lift_audit_pass = true
  dynamic_binding_signal_pass = true
  terminal_triggered = true
  pretrigger_lift_guidance_ready = false
  blocker = semantic BindingSpec roles varied, but no accepted non-trigger
            frontier progress was observed
```

因此 PDF016 的下一步不是 matched long-run，而是修 lift 聚合、dominance frontier
接受条件或 parser-token typed mutation，让 root role 的 `{1,0}` 变化变成
accepted/saved non-trigger `D_F` progress。

已能支撑的说法是：

```text
TIF012:
  FORMTRIG B5 在 7200s x3 matched run 中显著加速 first _T。
  这是一条强 endpoint/TTE speedup 证据，但因为最快 baseline run 是 210s，
  不是 hard SOTA-pain 证据。

LIBARCHIVE_2936:
  FORMTRIG 有速度和 hook attribution 收益。
  但 faithful baseline 9.456s 就能触发，所以它不能作为主 SOTA-pain 证据。

PDF003:
  更适合作为 hard binary/lifecycle TC 的下一条验证线。
  当前 blocker 是 native Poppler build 依赖，不是算法证据。

PHP009:
  已从旧的 lifecycle 初稿修正为 numeric-margin BindingSpec root：
    maker_note->offset == value_len - 1
  native build 已用 clang-15/libstdc++ 执行成功，生成 exif executable 和
  source-matching site-map。
  60s BindingSpec validation 通过：
    status = native_binding_validated
    ready_for_short_gate = true
    execs = 20280
    reached = 3995
    triggered = 17
    accepted_non_trigger_progress = 2
    saved_non_trigger_progress = 2
    binding_signal = pass / triggered
  这说明 PHP009 已有 pre-trigger lifted guidance readiness，但仍不是
  endpoint efficacy。当前 benefit-first worklist 已把 PHP009 提升为
  run_validated_matched_short_screen，下一步是 600s matched FORMTRIG vs
  faithful AFL++ family baseline。只有 baseline binary TC flatness 和
  late/missing/high-variance `_T` 同时成立时，才能把它升级成 hard SOTA-pain
  证据；如果 baselines 很早触发，则降为 speedup/control/design evidence。

SSL011:
  OpenSSL native build 已从错误的 asn1 runner 收敛到 pkcs7_decode runner。
  pkcs7_decode 覆盖 PKCS7_dataDecode workflow，已有 native executable、
  source-matching site-map、formal RNT seed 和 runnable validation worklist。
  第一版 60s BindingSpec validation 是负结果：
  static B2 通过，seed readiness 也能看到 R=1/T=0/spec_lifted，
  campaign 中 14033 个 reached exec 全部也是 triggered exec，
  saved_non_trigger_progress=0，spec D_F candidate values 恒为 [3]。
  复查后发现该版 root_observe 错绑到 SSL015 canary 的 pk7_doit.c:436。
  已修到真正的 SSL011 canary pk7_doit.c:514 macro cmp 集合。
  root514 20s validation 仍然是负结果，但诊断更精确：
  root_observe 已经变成 variable role，说明语义 root 现在确实在动；
  campaign 仍是 terminal-only，2026 reached exec 全部也是 triggered exec，
  saved_non_trigger_progress=0，spec D_F candidate values 恒为 [2]。
  这说明 SSL011 的剩余问题已经从 native/site-map/root 绑定错误收敛到
  “semantic roles varied, but no accepted non-trigger frontier progress”：
  下一步应修 D_F 聚合、dominance frontier 接受或 typed hook，而不是进入主比较。
```

下一步主线不是修改论文定位，而是改善实验设计：

```text
1. 解锁 PDF003/SSL/PHP 等 hard Magma target 的 native site-map/executable。
2. 先做 BindingSpec validation 和 non-trigger guidance gate；像 SSL011 这种
   “native/RNT/root 均可跑，但语义角色变化没有转成 accepted non-trigger frontier
   progress”的结果，必须先修 D_F 聚合、dominance frontier 接受、producer/use/typed
   hook 或 seed-distance 设计，不能直接进入主比较。
3. 再跑 same-budget faithful baselines: AFL++ vanilla, CmpLog, local Redqueen/operand。
4. 只有当 baseline 出现低成功率、长 R2T tail 或高方差，而 FORMTRIG 改善 first _T / success rate / cost 时，才作为主 SOTA-pain 结果。
   如果最快 baseline 已经在 600s 内触发，该 target 默认降为 speedup/control；
   只有无 baseline 成功，或最快成功明显超过 hard-pain 阈值，才进入主 hard-pain 叙事。
```

中间信号的角色保持不变：

```text
D_F / BindingSpec / dominance frontier / typed mutation
  = 解释收益和归因的机制证据

first _T / total _T / TTE / success rate / cost
  = 和 SOTA 比较的性能证据
```
