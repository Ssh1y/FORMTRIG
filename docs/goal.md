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

2026-06-18 PNG007 的复查说明了这一类 TC 的验收边界：

```text
target = PNG007 / png_ptr->palette == NULL
candidate = PNG007.native_b4_pre_root_absence_candidate.yml
result = terminal-only, not pre-trigger guidance

terminal evidence:
  direct POSIX SHM replay wrote flags=15 before segfault
  saved_triggered_progress = 3
  terminal_triggered = true

missing guidance:
  saved_non_trigger_progress = 0
  accepted_non_trigger_progress = 0
  pretrigger_lift_guidance_ready = false
  lift_delta_only_on_triggered = true
```

这说明 FORMTRIG 可以正确看到 PNG007 的 terminal `_T`，但这版 BindingSpec 还没有把
`palette != NULL -> palette == NULL` 的因果链转化成可保存的 non-trigger frontier。
RNT 种子已经是 palette PNG，PLTE deletion/absence 很容易直接跳到 terminal，
中间没有稳定、replay-stable、accepted 的 R-not-T 状态。因此 PNG007 当前只能作为
negative/control/spec-repair target，不能作为 binary-state-null 的正例收益。

## 变量/事件集合如何确定

对 `a == NULL` 这种二值 TC，FORMTRIG 不能也不应该声称求出了“所有影响 `a`
的变量全集”。在 C/C++ native 目标里，这个全集通常受指针别名、跨函数状态、
错误路径、生命周期和 harness API 影响，静态上不可可靠求全，动态上也无法在
实验预算内证明完整。

FORMTRIG 的算法目标是构造并验证一个 **TC-rooted effective guidance subset**：

```text
不是 complete influence set
而是 sufficient, observed, mutable, replay-stable guidance set
```

这个集合由 BindingSpec 和 runtime event map 共同确定，最少要覆盖以下角色：

```text
root_observe:
  直接观察 TC root，例如 a 的 null/non-null 状态或 canary 附近的 root use。

desired_producer:
  可能把 a 推到目标状态的 producer/reset/error path，例如 allocation failure、
  parser field absence、thumbnail data population、cleanup/reset。

guard:
  控制 producer/use 是否执行的条件，例如 type/tag/length/count/version check。

use:
  保证最终消费上下文仍然可达，避免只制造了无关的 NULL。

same_object:
  当 producer/use 跨事件或跨阶段时，证明它们仍指向同一个语义对象。

input_influence:
  能被 typed mutation 作用的输入字段或事件，例如 chunk absence、tag value、
  length/count、offset、object reference、message order。
```

这些角色写进 BindingSpec 仍然不够。一个集合只有通过动态 gate 后，才能被认为是
有效 lift：

```text
1. R-not-T replay 中可以观测到对应 role。
2. _T 前 D_F_spec_lifted 不是常量。
3. role value 至少有一个 candidate 维度发生变化。
4. dominance frontier 接受 accepted/saved non-trigger progress。
5. typed mutation 能改变 input_influence 或 role-producing field。
6. replay-stable，且 heuristic/manual lift 未污染。
```

因此 PHP003 旧 runner 的结论不是“FORMTRIG 不知道怎么 lift `data == NULL`”，
而是：当前集合只覆盖了 `Thumbnail.size < 4` 的 guard/input influence，缺少让
`ImageInfo->Thumbnail.data != NULL` 发生的 producer 生命周期；动态 gate 看到
`D_F_spec_lifted = 0/0` 恒定、`accepted_non_trigger=0`，所以必须判为
observation lift，而不是 effective R2T guidance。

## 如何证明这个集合是 TC-rooted effective subset

证明分两件事：先证明它 **rooted in TC**，再证明它 **effective for guidance**。

TC-rooted 的证据链：

```text
static root binding:
  BindingSpec 的 root/atom 必须来自 TCIR/Magma canary/真实 CVE oracle，
  并映射到 site_map 中的具体 source location / IR instruction。

semantic role binding:
  每个 role 都必须能解释为 root 的 producer、guard、use、same-object 或
  input-influence；不能只因为它在执行路径上或覆盖率相关就纳入。

mapping audit:
  formtrig_lift_spec_audit / formtrig_binding_map 必须给出 exact mapping、
  足够 binding tier、无 semantic_role_collapse、无 missing role。

negative-role rejection:
  对 binary/null，只有 root_observe 而没有 producer/use/influence 不够；
  对 lifecycle，只有 lifecycle_event 而没有 same_object relation 不够。
```

这条静态证据链现在由 `tools/audit_binding_spec_tc_rooted.py` 生成机器可审计
artifact，并被 `tools/summarize_binding_candidate_sweep.py` 写入 validation record 的
`tc_rooted_static` 字段。后续新 TC 不能只靠动态相关性证明指导有效：如果
BindingSpec 在静态 TC-rooted role gate 中失败，即使运行时出现
accepted/saved non-trigger movement，也必须先降级为 `static_binding_not_tc_rooted`，
修正 BindingSpec 后再谈 dynamic guidance。

effective guidance 的证据链：

```text
pre-trigger observability:
  seed readiness / replay 中存在 R=1, T=0, spec_lifted=1。

pre-trigger ordering:
  _T 前 candidate 的 D_F_spec_lifted 不是常量；
  non_trigger_candidate_lift_delta=true；
  lift_delta_only_on_triggered_candidates=false。

frontier causality:
  dominance frontier 接受 accepted_non_trigger_progress > 0，
  最好还能保存 saved_non_trigger_progress > 0。

mutation actionability:
  typed mutation 的 input_influence/hot range 能改变对应 role value 或 D_F，
  否则诊断为 typed_mutation_no_lift_delta。

replay stability:
  accepted/saved progress 重放后仍然 R=1,T=0，并保留同一类 lifted role 信号。

ablation / counterfactual:
  去掉该 BindingSpec、去掉 typed hook、或换成 collapsed/guard-only spec 时，
  non-trigger frontier progress 和 first _T/TTE 收益应下降或消失。
```

因此一个可以写进论文主结果的 binary/null lift，不是“变量集合看起来合理”，而是：

```text
TC root source -> semantic roles -> exact runtime events -> pre-_T nonconstant D_F
-> accepted non-trigger frontier -> typed mutation can move it -> replay/ablation holds
```

只要少任何一环，就必须降级为：

```text
static binding candidate
observation lift
terminal-only control
spec-repair blocker
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

2026-06-19 在 PHP003 current-ABI 3-rep matched baseline 补齐后，已重新生成
post-PHP003 triage/worklist：

```text
artifacts/formtrig_native_readiness/hard_target_triage_20260619.*
artifacts/formtrig_native_readiness/hard_target_experiment_worklist_20260619.*

promoted hard-target candidates = 1
worklist runnable_now = 0

PDF003:
  disposition = candidate_extend_longruns
  sota_pain_class = visible_hard_speedup_or_reliability
  baseline_guidance_gap_status = measured_pass
  FORMTRIG first_T = 0.31s
  fastest successful baseline run = 4530s
  speedup over fastest successful baseline run = 14612.90x
  next = use as one hard-speedup data point, then expand cross-target evidence

PHP003:
  disposition = demote_to_control_or_negative
  verdict = replicated_speedup_control_not_hard_sota_pain
  baseline_guidance_gap_status = measured_pass
  FORMTRIG median exact first_T = 1.942s
  fastest baseline family median first_T = 150s
  speedup over fastest baseline family median = 77.24x
  baseline success = 8/9; AFL++ vanilla = 3/3
  next = keep as speedup/control + mechanism evidence, not hard SOTA-pain

GPAC_3403:
  disposition = needs_lifecycle_alias_repair
  action = repair_real_cve_lifecycle_alias_to_endpoint
  runnable = false
  current evidence = GPAC typed mutation now has endpoint-scale parser/import
                     evidence: op44-op47 variants reach HEVC/L-HEVC import
                     states, match all positive-control parser/import signatures,
                     and exceed the positive-control import scale
                     (221 samples / 550 NALUs vs 172 / 413), while still not
                     producing ASAN/double-free terminal behavior
  lifecycle audit = artifacts/formtrig_native_readiness/gpac3403_lifecycle_gap_audit_20260619.json
  endpoint-scale repair = artifacts/formtrig_native_readiness/gpac3403_endpoint_scale_repair_20260619.json
  blocked claims = same_object relation runtime proof is false; endpoint-scale
                   variants still have 0 ASAN/double-free files; remaining
                   missing signatures are asan and asan_double_free

LIBXML2_1107:
  skipped = harness_admissibility_not_core_evidence
  status = inadmissible_core_evidence
  reason = harness exposes an artificial allocation-failure trigger-control knob
```

这个更新修正了三个旧调度错误：PHP003 已完成 current-ABI endpoint comparison，
不再进入主预算 runnable queue；GPAC_3403 也不再是“没有 BindingSpec”，因为
real-CVE readiness 已经证明 B5/B6/B8/B12 这一线有 BindingSpec、short-gate 和
typed-retained parser-frontier evidence；2026-06-19 的 op44-op47 repair 又把
HEVC/L-HEVC parser neighborhood 推进到 PoC 级 endpoint-scale import：16 个
variant 全部进入 HEVC/L-HEVC import，最高 221 samples / 550 NALUs，正控制为
172 / 413；signature audit 只剩 asan 和 asan_double_free 没匹配。因此 GPAC
现在的 blocker 不再是“样本规模不够”，而是“sample->data 到
GF_BitStream->original 的 alias/free terminal 关系没有闭合”。它仍不能直接进入
7200s x3 endpoint 长测，除非先出现 ASAN/double-free 或等价的 lifecycle-alias
runtime proof。下一轮主预算不是继续跑 PHP003，也不是继续把 LIBXML2_1107 当
core real-CVE 正例；LIBXML2 只能保留为 native pipeline / BindingSpec /
crash-accounting sanity evidence。主预算应围绕 PDF003 的 cross-target hard
evidence、GPAC_3403 的 lifecycle-alias repair，以及新的自然输入驱动 real-CVE
target 展开。

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

PHP003:
  2026-06-18 validated short screen 已补齐 faithful baseline 侧证据：
    artifacts/formtrig_native_readiness/baseline_guidance_gap/php003_validated_short_600s_1rep_r2
    status = measured_pass
    AFL++ CmpLog: R = 29,955, T = 0 in 600s
    AFL++ vanilla: R = 10,711, T = 0 in 600s
    Redqueen/operand path: R = 7,816, T = 0 in 600s
  FORMTRIG 同预算 600s：
    strict_pretrigger_guidance = true
    accepted_non_trigger = 6
    saved_non_trigger = 6
    spec_lifted = 4,203
    terminal _T = 0
  当前 comparison verdict 是 `pretrigger_guidance_only`。这是一条重要机制证据：
  baseline pain gate 已经通过，FORMTRIG 也确实产生了 TC-rooted non-trigger
  guidance；但 endpoint 还没有出现，所以不能写成性能正例或 hard SOTA-pain
  主结果。下一步是修 PHP003 的 typed mutation/BindingSpec 终态转换，或提高预算
  直到 FORMTRIG 出现同 oracle terminal `_T`，再进入 matched endpoint 比较。
  最新 R-to-T repair 诊断已经落盘：
    artifacts/formtrig_native_readiness/signal_path/php003_validated_short_600s_1rep_r2
    verdict = strict_pretrigger_guidance_observed
    terminal_gap.status = saved_frontier_blocked_on_producer
    saved non-T frontier = 6
    saved T = 0
    latest saved queue = 466 / exec 119606 / trace 6ed559e280b60e5d
    latest missing role = desired_producer
    latest observed-but-unsatisfied roles = root_observe, use
    desired_producer candidate values = constant zero
    typed fallback_no_hot_range stages = 52
    saved frontier hot-range events = 0
  这说明 PHP003 的指导方向是正的，但可变异链条还没闭合：frontier 从
  root-only 推进到 root+guard+use，但 producer 没满足，root/use 目标值仍未满足，
  typed mutation 没拿到输入 hot range。下一步优先级不是重复 matched 600s，而是
  修 producer/input-influence/hot-range 或 typed mutation 的字段定位。
  2026-06-18 已把 BindingSpec validation gate 收紧：
    artifacts/formtrig_native_readiness/binding_validation/PHP003.native_b2_thumbnail_guard_candidate.validation.json
    status = needs_terminal_repair
    ready_for_short_gate = false
    producer_constant_zero = true
    typed_mutation_hook_enabled = false
    blocker = producer role has no positive candidate signal: desired_producer
  重新生成的 20260618 benefit-first worklist 已把 PHP003 保持在
  `repair_guidance_to_terminal`，并把 comparison + validation summary 一起作为
  evidence；不能再把该 TC 当作 ready matched-short target 调度。
  2026-06-18 B3/B4 repair 继续收敛了负例原因：
    artifacts/formtrig_native_readiness/php003_repair_b3_b4_diagnosis_20260618.md
    B3 local thumbnail site candidates = 3/3 not_ready / constant_lift_signal
    B4 thumbnail-length hook = enabled, typed_execs 120, typed_finds 7
    B4 spec_lifted_events = 1210, role_signal_events = 1210
    B4 d_f_spec_lifted_min/max = 0/0, constant = true
    B4 accepted_non_trigger = 0, saved_non_trigger = 0, terminal _T = 0
    B4 queue files with IFD1 JPEGInterchangeFormatLength < 4 = 6
  这说明当前 PHP003 的 lift 程度只是 observation lift，不是有效 R2T guidance。
  Hook 已经能把 size 半边打到 `<4`，但 current php-fuzz-exif runner 用一个参数
  调 `exif_read_data`，`read_thumbnail=false`，thumbnail extraction/build 会跳过，
  因而 `ImageInfo->Thumbnail.data` 不被填充。PHP003 的 canary 是
  `MAGMA_AND((bool)data, ImageInfo->Thumbnail.size < 4)`，所以 data 半边不满足时
  再跑更久也不会自然闭合 `_T`。下一步必须换/补 harness 到 `exif_thumbnail` 或
  `exif_read_data(..., read_thumbnail=true)`，重建 native FORMTRIG 后再做
  BindingSpec validation；当前 runner 下 PHP003 只能作为 harness-lifecycle
  negative/control，不能作为主正例。
  同日已把这个修复转成可执行 native asset 入口：
    artifacts/formtrig_native_readiness/php003_thumbnail_runner_repair_20260618.md
    artifacts/formtrig_native_readiness/magma_native_builds/PHP003_exif_thumbnail/build_plan.json
    program = exif_thumbnail
    target_cmd = .../PHP003_exif_thumbnail/out/afl/exif_thumbnail @@
  builder 会派生 `sapi/fuzzer/fuzzer-exif_thumbnail.c`，三参数调用
  `exif_thumbnail(stream, width, height)`，以确保进入 `exif_scan_thumbnail`。
  该 build plan 已执行成功，新 site-map 有 `284140` 行，`exif_scan_thumbnail`
  和 `zif_exif_thumbnail` 都已进入 runtime map。

  新 `exif_thumbnail` runner 上的 B4 BindingSpec 结果：
    seed readiness:
      status = pass
      reached = 5/5
      triggered = 0/5
      spec_lifted = 5/5
      desired_producer = 1
      spec_d_f_unique = 1
    20s screen:
      pretrigger_lift_guidance_ready = true
      queued_progress = 1
      accepted_non_trigger_progress = 1
      saved_non_trigger = 1
      terminal _T = 0
      variable role = use
    120s screen:
      diagnosis = triggered
      first _T monitor upper bound = 60s
      terminal _T = 277
      queued_progress = 32
      saved_non_trigger = 1
      saved_triggered = 31
      typed_execs / typed_finds = 490 / 45

  这把 PHP003 从旧 runner 的 harness-lifecycle negative 推进到了 repaired-runner
  endpoint smoke：同一个 B4 BindingSpec 在新 runner 下出现 pre-trigger
  TC-rooted role-level guidance，并最终触达 `_T`。

  2026-06-18 follow-up 修复了 scalar aggregation：runtime 现在把单个
  spec component distance 与多角色 residual role-graph distance 分开，避免
  `root_observe/input_influence` 的 lower-is-better `0` 把整个
  `D_F_spec_lifted` 压成 `0`。重建 `exif_thumbnail` 后：
    seed replay:
      artifact = artifacts/formtrig_native_readiness/raw/php003_exif_thumbnail_seed_readiness_role_df_20260618_r2/formtrig_seed_readiness.json
      RNT/spec_lifted = 5/5
      D_F_spec_lifted values = {2}
    20s sweep:
      artifact = artifacts/formtrig_native_readiness/raw/php003_exif_thumbnail_b4_hook_20s_role_df_20260618/summary.tsv
      diagnosis = triggered
      D_F_spec_lifted constant = false
      D_F_spec_lifted values = {2,3}
      non-trigger candidate D_F_spec_lifted values = {2,3}
      terminal _T = 277

  PHP003 已经不是“baseline 同 runner 对照缺失”的状态。2026-06-18 的
  same-runner 600s x1 package 已经落盘：
    comparison = artifacts/formtrig_native_readiness/comparisons/php003_native_b4_same_runner_600s_1rep_20260618/comparison.md
    baseline_gap = artifacts/formtrig_native_readiness/baseline_guidance_gap/php003_native_b4_same_runner_600s_1rep_20260618/baseline_guidance_gap.json
    verdict = speedup_but_under_replicated
    FORMTRIG first _T = 1.985s exact queue/progress time
    FORMTRIG terminal _T = 21024
    AFL++ CmpLog = 0/1 _T in 600s
    AFL++ vanilla first _T = 180s, terminal _T = 31
    Redqueen/operand first _T = 330s, terminal _T = 11
    speedup over fastest successful baseline = 90.68x
    baseline pre-trigger binary flatness = pass
    baseline guidance gap status = fail_fast_baseline
  因此 PHP003 当前只能作为 same-runner speedup/control + mechanism evidence：
  baseline 的二值 oracle 在 `_T` 前确实 flat，但 vanilla 在 600s 可接受阈值内
  触发，所以它不能写成 hard SOTA-pain 主证据。它还 under-replicated，只是
  1 rep。

  2026-06-19 用 ABI-current AFL++ 重新确认了同一 B4 repaired-runner 路径，
  避免旧 standalone `experiments/aflplusplus/AFLplusplus/afl-fuzz` 污染证据：
    artifact = artifacts/formtrig_native_readiness/raw/php003_exif_thumbnail_b4_current_abi_20s_20260619T203504Z/summary.tsv
    validation = artifacts/formtrig_native_readiness/binding_validation/PHP003.native_b4_thumbnail_length_hook_candidate.current_abi.validation.json
    readout = artifacts/formtrig_native_readiness/comparisons/php003_native_b4_same_runner_600s_1rep_20260618/current_abi_readout_20260619.md
    afl-fuzz = experiments/magma_workspace/magma/fuzzers/formtrig_native/repo/afl-fuzz
    diagnosis = triggered
    pretrigger_lift_guidance_ready = true
    accepted/saved non-trigger progress = 2/2
    queued_progress = 7
    terminal _T = 43
    execs_done / reached_execs = 7290 / 1556
    D_F_spec_lifted constant = false
    D_F_spec_lifted values = {2,3}
    non-trigger candidate D_F_spec_lifted values = {2,3}
    typed_execs / typed_finds = 124 / 11
  同日已经补跑 current-ABI 600s FORMTRIG arm：
    artifact = artifacts/formtrig_native_readiness/raw/php003_native_b4_current_abi_600s_1rep_formtrig_20260619T204624Z/batch_summary.jsonl
    first _T = 7.595s exact queue time
    first _T queue = id:000083,src:000000,time:7595,execs:1815,op:havoc,rep:1,+cov
    first _T monitor upper bound = 60s
    terminal _T = 70678
    accepted/saved non-trigger progress = 2/2
    saved triggered progress = 7855
    execs_done / reached_execs = 118021 / 71991
    D_F_spec_lifted values = {2,3}
    typed_execs / typed_finds = 242 / 44
    stability_failures = 0
    speedup over fastest successful baseline by exact queue time = 23.70x

  2026-06-19 继续补了 current-ABI 600s FORMTRIG reps 2-3：
    artifact = artifacts/formtrig_native_readiness/raw/php003_native_b4_current_abi_600s_reps2_3_formtrig_20260619T210244Z/batch_summary.jsonl
    current-ABI FORMTRIG success = 3/3
    exact first _T values = 7.595s, 1.942s, 1.929s
    exact first _T median/min/max = 1.942s / 1.929s / 7.595s
    terminal _T total = 170365
    saved non-trigger progress total = 6
    saved triggered progress total = 18936
    D_F_spec_lifted values = {2,3} in all reps
    typed_execs / typed_finds total = 1073 / 217
    stability_failures total = 1
  同日已补齐 faithful baseline reps 2-3，并生成 current-ABI matched 3rep
  comparison package：
    comparison = artifacts/formtrig_native_readiness/comparisons/php003_native_b4_current_abi_matched_600s_3rep_20260619/comparison.md
    baseline reps2-3 = artifacts/formtrig_native_readiness/raw/php003_native_b4_current_abi_matched_600s_baselines_reps2_3_20260619T212832Z/summary.tsv
    verdict = replicated_speedup_control_not_hard_sota_pain
    FORMTRIG success = 3/3
    baseline success = 8/9
    AFL++ CmpLog first _T values = NA, 360s, 480s; success = 2/3
    AFL++ vanilla first _T values = 180s, 150s, 150s; success = 3/3
    Redqueen/operand first _T values = 330s, 240s, 240s; success = 3/3
    fastest baseline family median first _T = AFL++ vanilla at 150s
    FORMTRIG median exact first _T = 1.942s
    median exact first _T speedup over fastest baseline family median = 77.24x
    slowest FORMTRIG exact first _T speedup over fastest baseline family median = 19.75x
  结论边界已经收敛：PHP003 repaired runner 上 FORMTRIG 侧 R2T validation
  和 600s FORMTRIG arm 都已经在 current ABI 下闭合，且 FORMTRIG 侧
  endpoint/TC-rooted guidance 是 3/3 稳定；但 replicated baselines 并没有
  late/missing/high-variance，反而整体 8/9 成功，vanilla 3/3 且 median 150s。
  因此 PHP003 只能作为 replicated speedup/control + mechanism evidence，
  不能作为 hard SOTA-pain 主证据。主痛点预算应转向 faithful baselines
  在可接受时间内无法稳定触发的 Magma/真实 CVE 目标。

PNG007:
  属于 binary-state-null TC，TrigFuzz 也把它当作 binary triggering-distance
  痛点例子。2026-06-18 B4/pre-root 复查证明 runtime 和 AFL++ 都能看到 terminal
  `_T`，但 validation 仍是 terminal-only：
    status = terminal_only_variable_semantic_roles_no_pretrigger_guidance
    saved_triggered_progress = 3
    saved_non_trigger_progress = 0
    accepted_non_trigger_progress = 0
    pretrigger_lift_guidance_ready = false
    lift_delta_only_on_triggered = true
  当前不能写成 FORMTRIG 正例。它的价值是 negative/control/spec-repair：
  说明只触发 `_T` 不等于解决 R2T guidance；必须先产生稳定的 accepted
  non-trigger frontier，才进入 matched baseline 比较。

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
