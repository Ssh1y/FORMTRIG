# FORMTRIG Native Handoff - 2026-06-15

本文档是当前 FORMTRIG native 工程线的交接说明。它描述当前目标、已有实现、关键证据、工作树状态、风险和下一步优先级，供后续会话直接接手。

## 当前总目标

目标没有完成，仍要继续：

```text
做一个真实可用的 FORMTRIG，可以进行实验的 FORMTRIG。
最终验收是在 Magma 和真实 CVE 上实现长测，能真正解决二值 TC 无法带来的指导作用。
```

不要再回到 Python FORMTRIG 原型。当前主线是：

```text
AFL++ / native runtime
  + BindingSpec
  + RuntimeSignal
  + spec-driven lifted D_F
  + dominance frontier
  + typed mutation
```

核心研究问题仍然是：当 native trigger distance `D_T` 对二值 TC 退化成 `0/1` 时，FORMTRIG 是否能通过 TC-rooted lift 得到更细粒度、稳定、可排序、可归因、可变异的 `D_F`，并实际指导 fuzzing。

## Benefit-first 叙事和验收规则

后续写论文、汇报实验、选择长测目标时都必须先讲收益，再讲设计。

主收益只能来自可比较的实验结果：

```text
same-budget terminal success
first _T / TTE / PRET
repetition success rate
exec/sec and budget cost
baseline-visible target triage savings
```

`D_F`、BindingSpec、dominance frontier、typed mutation、accepted non-trigger
seed 等中间产物是机制证据。它们说明 FORMTRIG 为什么能把二值或稀疏 TC
转换成搜索进展，但不能单独当作和 CmpLog、Redqueen、AFL++ 比较的性能指标。
如果 faithful matched-budget baseline 也很快触发，同一个 target 应降为
control/native-readiness 或 negative evidence，不能靠中间信号包装成主优势。

结果表和 comparison package 的顺序应固定为：

```text
primary benefit -> endpoint observation -> mechanism benefit -> design attribution -> blockers
```

### 2026-06-17 hard-target evidence update

当前结果仍然不能宣称“已经充分体现 SOTA 工具的痛点”。这里的痛点按当前验收口径指：
faithful baseline 只能靠随机性撞见 TC 触发，且随机撞见的时间成本不可接受。TIF012
和 LIBARCHIVE_2936 都有 FORMTRIG first `_T` speedup/attribution 价值，但最快
baseline 分别在 210s 和 9.456s 触发，所以不能作为主 SOTA-gap 证据。

后续要证明“二值 TC 对 SOTA 没有指导作用”，必须同时满足三条：

```text
1. baseline-visible TC signal 在 `_T` 前是 flat/binary：
   reached-but-not-`_T` seeds 的 unique values 很少，entropy 接近 0，
   accepted non-trigger improvement 为 0。
2. baseline endpoint 表现为随机命中成本：
   repeated runs 里 `_T` late / missing / high-variance，
   且最快强 baseline 不在可接受时间阈值内。
3. FORMTRIG 有 endpoint benefit 和 `_T` 前机制证据：
   same-budget terminal/TTE/exec 优势成立，
   并且有 replay-stable、TC-rooted、accepted/saved 的 `D_F` progress。
```

如果 baseline 在几十秒、210s 或 300s 这种可接受成本内触发，目标必须降为
speedup/control/design evidence，不能写成 hard SOTA-pain。

`tools/analyze_baseline_guidance_gap.py` 现在把这条判据落成独立 artifact。它读取
baseline `summary.json` 和 `run_record.json`，输出
`baseline_guidance_gap.{json,md}` 与逐 run TSV。当前已经生成：

```text
artifacts/formtrig_native_readiness/baseline_guidance_gap/php009_validated_short_600s_1rep_20260617
  status = fail_fast_baseline
  pre-trigger binary flatness = pass
  fastest baseline _T = 120s

artifacts/formtrig_native_readiness/baseline_guidance_gap/tif012_b5_matched_7200s_3rep_20260617
  status = fail_fast_baseline
  pre-trigger binary flatness = pass
  fastest baseline _T = 210s

artifacts/formtrig_native_readiness/baseline_guidance_gap/libarchive_2936_matched_7200s_3rep_20260617
  status = fail_fast_baseline
  pre-trigger binary flatness = not measured by Magma monitor
  fastest baseline terminal crash = 9.456s
```

这三个包都没有通过 hard SOTA-pain gate。注意：PHP009 和 TIF012 的 `_T` 前
binary oracle 确实是 flat 的，但 endpoint 成本不够硬；LIBARCHIVE_2936 没有
Magma monitor flatness 证据，且 baseline 更早触发。因此下一步要找的不是“又一个
speedup target”，而是 `baseline_guidance_gap.status=measured_pass` 的 target：
flat pre-`_T` signal 加上 late/missing/high-variance baseline endpoint。

### 2026-06-18 PDF003/PDF016 update

PDF003 7200s x3 matched run 现在是第一个通过 baseline no-guidance proof gate
的 Magma hard-target 候选：

```text
baseline_guidance_gap/pdf003_matched_7200s_3rep_20260617T224500Z:
  status = measured_pass
  interpretation = baseline evidence supports a hard binary-TC no-guidance candidate
  pre-trigger binary flatness = pass
  endpoint cost = pass

baselines:
  AFL++ CmpLog: 0/3 _T, total R = 1,573,928, total T = 0
  AFL++ vanilla: 1/3 _T, first _T = 5670s, 2/3 missing
  Redqueen/operand path: 1/3 _T, first _T = 4530s, 2/3 missing

FORMTRIG:
  3/3 _T
  best first _T upper bound = 0.31s
  terminal-triggered counts = 7693, 7246, 6607
  comparison verdict = positive_speedup_matched_comparison
  main claim strength = hard_speedup_or_reliability_candidate
  speedup over fastest successful baseline run = 14612.90x
```

Claim boundary: PDF003 supports hard-target endpoint speedup/reliability plus a
measured baseline binary-TC no-guidance gap. It does not prove strict pre-trigger
FORMTRIG mechanism benefit in this package: all three FORMTRIG reps have
`strict_pretrigger_guidance=false`, `accepted_non_trigger=0`, and
`saved_non_trigger=0`. The reason is that FORMTRIG reaches terminal `_T` almost
immediately, leaving no accepted/saved non-trigger progress sample. Use PDF003
as the current strongest hard SOTA-pain candidate, but keep mechanism claims
to terminal-oracle speedup unless a separate pre-trigger target or ablation
fills this gap.

PDF016 is now buildable/runnable after installing `libtiff-dev` and `liblcms2-dev`.
The native assets are:

```text
executable:
  artifacts/formtrig_native_readiness/magma_native_builds/PDF016/out/afl/pdf_fuzzer
site_map:
  artifacts/formtrig_native_readiness/magma_native_builds/PDF016/out/formtrig_native/formtrig_sites.tsv
site rows:
  47051
```

The lifecycle draft generator and site-map role guidance were fixed so lifecycle
targets require a stateful `root_observe` role. The conservative B3 candidate is:

```text
artifacts/binding_specs/PDF016.native_b3_parser_ref_candidate.yml
roles:
  lifecycle_event + use + root_observe + same_object
audit:
  B3 pass
```

Validation result with `-t 5000`:

```text
artifacts/formtrig_native_readiness/raw/pdf016_b3_binding_validation_600s_t5000:
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

PDF016 should not enter matched long-run yet. It is currently useful as a
negative/spec-repair target: B3 wiring is valid and terminal `_T` is reachable,
but lifecycle/root signal still has not become accepted/saved non-trigger
frontier progress. Next action should be input-influence/range signal or
parser-token typed mutation, not more endpoint budget.

`artifacts/formtrig_native_readiness/hard_target_triage_20260617.{json,csv,md}`
现在显式输出 `sota_pain_class`，避免只靠中间信号或口头解释判断。当前分类是：

```text
TIF012:
  not_visible_baseline_time_cost_acceptable
  main_claim_strength = not_hard_pain_baseline_fast_enough
  FORMTRIG first_T = 0.034s
  fastest successful baseline run = 210s
  fastest baseline-family median = 1410s
  speedup over fastest successful baseline run = 6176.47x

LIBARCHIVE_2936:
  not_visible_baseline_time_cost_acceptable
  main_claim_strength = not_hard_pain_baseline_fast_enough
  fastest successful baseline run = 9.456s

PHP009:
  not_visible_baseline_time_cost_acceptable
  main_claim_strength = not_hard_pain_baseline_fast_enough
  FORMTRIG first_T = 87.04s exact progress time / 120s monitor upper bound
  fastest successful baseline run = 120s
  fastest baseline-family median = 120s
  speedup over fastest successful baseline run = 1.38x by exact progress time

LIBCOAP_CVE_2023_35862 and PNG006:
  not_visible_baseline_visible_no_formtrig_advantage

promoted hard-target candidates:
  0
```

这个 2026-06-17 triage artifact 尚未纳入 2026-06-18 的 PDF003 7200s x3
measured-pass 结果。更新前的结论仍然成立于 TIF012、LIBARCHIVE_2936、PHP009、
PNG006 和 LIBCOAP：它们不能作为主 SOTA-pain evidence。2026-06-18 已经重跑
hard-target triage/worklist：

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
  demote_to_control_or_negative
  reason = fail_fast_baseline guidance-gap gate

PNG006 / LIBCOAP_CVE_2023_35862:
  demote_to_control_or_negative
  reason = baseline-visible/no FORMTRIG advantage in current package
```

新的主预算队列是：

```text
artifacts/formtrig_native_readiness/hard_target_experiment_worklist_20260618.*

P0:
  PDF003 -> expand_cross_target_hard_evidence
  reason = matched 7200s x3 already complete; use it as one hard-speedup
           data point, then spend new budget on another Magma/real-CVE hard target

P1:
  SSL015 -> validate_binding_spec_then_short_screen
  PDF016 -> validate_binding_spec_then_short_screen
  LIBXML2_1107 -> validate_binding_spec_then_short_screen
  GPAC_3403 -> validate_replay_then_draft_binding_spec
```

PDF016 现在有正式 validation record：

```text
artifacts/formtrig_native_readiness/binding_validation/PDF016.native_b3_parser_ref_candidate.validation.json
  status = terminal_only_variable_semantic_roles_no_pretrigger_guidance
  native_site_map_validated = true
  lift_audit_pass = true
  dynamic_binding_signal_pass = true
  terminal_triggered = true
  pretrigger_lift_guidance_ready = false
```

Planner 已修正：这种状态不再显示为“not native-site-map validated”，而是显示真实
blocker：pre-trigger lift guidance 不 ready，terminal-only，semantic roles 有变化但
没有 accepted non-trigger frontier progress。PDF016 下一步是修 lift 聚合、dominance
frontier 或 parser-token typed mutation，不是 matched long-run。

`artifacts/formtrig_native_readiness/hard_target_experiment_worklist_20260618.*`
现在读取最新 triage artifact。主执行队列会把：

- `not_visible_baseline_visible_no_formtrig_advantage` 目标跳过主预算；
- `not_visible_baseline_time_cost_acceptable` 目标跳过主预算；
- `weak_or_moderate_baseline_time_cost` 或 near-seed/harness-shaped 目标只作为设计改进候选；
- PDF003 标记为已完成当前 matched 7200s x3，应转向 cross-target hard evidence；
- 下一批主预算候选从 SSL015、PDF016、LIBXML2_1107、GPAC_3403 等 target 的
  validation/spec-repair 开始。

这避免了 triage 已经判定“看不出 SOTA pain”的目标继续消耗长测预算。

PHP009 native build 现在有更清晰的 dependency gate。FORMTRIG native build runner
会跳过 autoconf `conftest.{c,cc,cpp,cxx}` 的 pass instrumentation，避免 configure
probe 因未链接 FORMTRIG runtime 而失败，也避免这些 probe 污染 site-map。当前
PHP009 已经在安装 PHP build tools 后执行 native build 成功，并通过后续
native asset discovery：

```text
executable:
  artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out/afl/exif
site-map:
  artifacts/formtrig_native_readiness/magma_native_builds/PHP009/out/formtrig_native/formtrig_sites.tsv
BindingSpec:
  artifacts/binding_specs/PHP009.native_draft_magma_canary.yml
```

源码审计后 PHP009 不再按旧的 `compound-sequence-lifecycle` 初稿处理，而是按
numeric-margin root 处理：`maker_note->offset == value_len - 1`。60s
BindingSpec validation 已通过，记录为 `native_binding_validated` 和
`ready_for_short_gate=true`。关键数值：

```text
execs = 20280
reached = 3995
triggered = 17
accepted_non_trigger_progress = 2
saved_non_trigger_progress = 2
binding_signal = pass / triggered
```

这只是 mechanism/readiness evidence，不是 endpoint efficacy。600s matched short
screen 已经完成：FORMTRIG gate pass，strict pre-trigger guidance 为 true，
`accepted_non_trigger=4`，`saved_non_trigger=4`，`spec_lifted=12362`，
`heuristic_lifted=0`，`manual_lifted=0`，`terminal _T=37120`。first `_T`
按 progress/queue 精确时间是 87.04s，按 monitor 采样上界是 120s。

同预算 faithful baselines 也全部触发：

```text
AFL++ vanilla:
  first _T monitor upper bound = 270s
  total _T = 43

AFL++ CmpLog:
  first _T monitor upper bound = 300s
  total _T = 9

local RedQueen/operand path:
  first _T monitor upper bound = 120s
  total _T = 20
```

因此 PHP009 当前结论是：FORMTRIG 在这个 numeric-margin TC 上有真实的
TC-rooted lift 指导，并且 first `_T` 精确时间快于三条 baseline；但最快 baseline
也在 120s 内触发，comparison package 标记为
`main_claim_strength=not_hard_pain_baseline_fast_enough`。它不能证明“二值 TC
对 SOTA 没有指导、baseline 纯靠随机性”，只能作为 positive speedup/control
和机制归因证据。要把这类主张写进论文，必须另选 baseline `_T` late/missing/
high-variance 且 baseline-visible pre-`_T` signal flat/binary 的硬目标。

SSL011 已从错误的 OpenSSL `asn1` runner 修正为 `pkcs7_decode` runner。新的 runner
实际调用 `PKCS7_dataDecode`，已有 FORMTRIG-native executable、source site-map、formal
RNT seed 和 runnable validation worklist。当前 60s BindingSpec validation 是负结果：
static B2 通过，formal RNT seed 也通过 replay，但 campaign 里 reached exec 全部也是
triggered exec，`saved_non_trigger_progress=0`，spec `D_F` 候选值恒为 `[3]`。这说明
SSL011 现在是更好的 hard-target/spec-repair 候选，但当前 spec 还不能作为 endpoint
或 SOTA-pain 证据。

后续复查发现该版 SSL011 root 误绑到同函数内的 `SSL015` canary line 436，而真正
的 `SSL011` canary 是 `pk7_doit.c:514`。root 已修到 line 514 的 Magma macro cmp
集合；20s validation 中 root role 已经出现 `[1,0]` 变化，但结果仍是
terminal-only：`saved_non_trigger_progress=0`，spec scalar `D_F` 候选值恒为 `[2]`。
因此 SSL011 的当前剩余问题不是 native build 或 root site-map，而是 semantic role
变化没有转成 accepted non-trigger frontier progress。下一步应修 D_F 聚合、
dominance frontier 接受或 typed hook，不应把 SSL011 作为主 endpoint/SOTA-pain
证据。

## 当前架构原则

FORMTRIG 当前应保持这个架构：

```text
TC / BindingSpec
  -> normalized lift-spec
  -> runtime event map / binding quality gate
  -> native runtime raw/spec signal
  -> FORMTRIG-side D_F / dominance frontier
  -> AFL++ native guidance / typed mutation
```

必须保持的原则：

- FORMTRIG core 不写 PNG、SQL、CVE target-specific workaround。
- target-specific 语义只允许放在外部 `BindingSpec` 或外部 mutation hook。
- `T` 只能作为 terminal oracle；不能进入 non-trigger `D_F`。
- 正式主实验只能使用 `spec-driven` lifted signal。
- heuristic/manual lift 必须分开作为 ablation 或 exploratory variant。
- “保持 R”不是 progress；它只是前提。
- 被保存的 non-trigger seed 必须是 TC-rooted lifted improvement，且 replay stable。
- 不能把 backend 或 target 直接输出的 `D_F` 当正式主实验的 FORMTRIG lift。

## 当前工作树状态

工作目录：

```text
/home/cwh/FORMTRIG
```

工作树很脏，有大量历史 untracked artifacts。不要执行：

```bash
git add .
```

只 stage 明确相关文件。

当前 tracked 修改主要集中在 native 实现：

```text
formtrig/llvm/formtrig_pass.cpp
formtrig/runtime/formtrig_runtime.c
formtrig/include/formtrig/formtrig_abi.h
formtrig/tools/formtrig_binding_spec_compile.c
formtrig/tools/formtrig_binding_map.c
formtrig/tools/formtrig_lift_spec_audit.c
formtrig/tools/formtrig_lift_feature_audit.c
formtrig/tools/formtrig_campaign_diagnose.c
formtrig/tools/formtrig_progress_summary.c
formtrig/tools/formtrig_site_map.c
scripts/run_formtrig_aflpp_campaign.sh
scripts/run_formtrig_seed_readiness.sh
scripts/run_formtrig_binding_candidate_sweep.sh
scripts/run_native_formtrig_smoke.sh
scripts/prepare_formtrig_native_env.sh
patches/aflplusplus/formtrig_native_runtime.patch
```

重要 untracked/new files：

```text
formtrig/tools/formtrig_binding_signal_diagnose.c
formtrig/tools/formtrig_lift_signal_entropy.c
scripts/formtrig_site_allowlist_from_lift_spec.sh
artifacts/binding_specs/LIBXML2_1107.native_b2_alloc_fail_candidate.yml
artifacts/formtrig_native_readiness/magma_lift_smoke_20260615.md
```

注意：还有大量历史 artifacts、benchmarks、paper、experiments 等 untracked 文件。不要清理，除非用户明确要求。

## 已实现能力

### BindingSpec / lift-spec 主线

当前 native 主线已经支持高层 BindingSpec 编译成低层 `FORMTRIG_LIFT_SPEC` rows。

支持内容包括：

```text
role_component
component/event
phase/prefix
range/hot_range
source_id
context_hash
value_mode
observe_window
```

BindingSpec 是外部输入。FORMTRIG core 不应该根据 `target_id` 写特殊规则。

### Per-atom category

已经修掉全局 category 的问题。现在支持每个 atom 独立 category：

```text
atom_category 1 binary-state-null
atom_category 2 equality-magic
```

这样 mixed TC 不会用一个全局 `--category` 错误要求或放行所有 atoms。

典型例子：

```c
color_type == PALETTE && palette == NULL
```

应被看成：

```text
atom1: equality/magic
atom2: binary-state-null
```

不能用全局 binary-null 或 equality 统一审计。

### Binding quality gate

`formtrig_binding_map` 和 `formtrig_lift_spec_audit` 已支持：

- exact / ambiguous / missing
- semantic role collapse
- binding tier B0-B4
- per-category minimum tier
- lift_allowed

binding tier 语义：

```text
B0 location-only
B1 root-observed
B2 producer-use-bound
B3 lifecycle-bound
B4 influence-bound
```

最低要求：

```text
numeric-margin: B1
equality/magic direct: B1
equality/magic transformed: B4 or repair hook
binary-state-null: B2
compound-sequence-lifecycle: B3
```

如果 binding 不足，必须 `lift_allowed=false`，不能伪造 lifted progress。

### D_F 来源分离

runtime/summary 区分：

```text
D_F_spec_lifted
D_F_heuristic_lifted
D_F_manual_lifted
D_F
```

正式主实验默认禁用 heuristic/manual：

```text
FORMTRIG_ALLOW_HEURISTIC_LIFT=0
FORMTRIG_OBSERVE_HEURISTIC_LIFT=0
FORMTRIG_ALLOW_MANUAL_LIFT=0
```

主实验应该只使用：

```text
source=spec_generated
source=runtime_raw_event
```

不要把 runtime heuristic 或 target manual API 混进 FORMTRIG-main 的结果里。

### Seed readiness gate

`scripts/run_formtrig_seed_readiness.sh` 能在 campaign 前 replay RNT seeds，检查：

- reached
- not triggered
- spec lifted signal exists
- SHM ABI ok
- heuristic/manual 未污染
- `D_F_spec_lifted` 是否有值
- seed 是否适合进入 AFL++ campaign

这个 gate 对避免 “RNT seed 其实没有 lifted signal” 很重要。

### Dynamic binding signal diagnosis

`formtrig_binding_signal_diagnose` 已能报告：

- role observed counts
- per-role value variability
- candidate/calibration `D_F` values
- non-trigger lift delta
- lift delta 是否只在 triggered candidates 出现
- accepted non-trigger progress events

这是判断 BindingSpec 是否真的可用的关键，不要只看 static gate。

### CVE crash terminal accounting

对真实 CVE crash targets，程序可能在 runtime JSON 写出 trigger 前 SIGSEGV。

已经修复 summary/diagnose，使它读取 AFL++ `fuzzer_stats` 里的 `saved_crashes`，输出：

```text
afl_saved_crashes
terminal_triggered_execs
```

但这只用于 terminal success 和评估统计，不进入 non-trigger `D_F`。

当前口径：

```text
terminal_triggered_execs = max(formtrig_triggered_execs, triggered_events) + afl_saved_crashes
```

这样可以兼容 AFL campaign 和直接 replay/runtime log。

### 大 site map truncation 修复

之前两个工具有 `MAX_SITES=65536` 静态数组：

```text
formtrig/tools/formtrig_binding_spec_compile.c
formtrig/tools/formtrig_binding_map.c
```

真实 full-instrumented libxml2 site map 超过 200k rows，会被静默截断，导致 source mapping missing。

现在已经改成动态增长数组。真实 libxml2 full site map 约 212k rows，能够正常绑定。

### 编译期 selective instrumentation 初版

`formtrig/llvm/formtrig_pass.cpp` 新增编译期 site id allowlist：

```bash
FORMTRIG_INSTRUMENT_SITE_IDS="123,456"
FORMTRIG_INSTRUMENT_SITE_ID_FILE=/tmp/sites.txt
```

pass 会只对 allowlist 里的 site id 插桩：

```text
cmp
branch
load/store/memtransfer
arith/div/mod
malloc/free rewrite
```

这不是 runtime filter，而是 IR 层少插桩。目标是将性能往 AFL++ 原生靠。

新增脚本：

```text
scripts/formtrig_site_allowlist_from_lift_spec.sh
```

作用：从 normalized lift-spec 和显式 target-site ids 生成 compile-time allowlist 文件。

推荐两阶段流程：

```text
1. full/slice build target，生成完整 site map
2. 编译 BindingSpec，过 static/dynamic gate
3. 从 normalized lift-spec + target-site ids 生成 allowlist
4. selective rebuild target
5. seed readiness + campaign rerun
6. 比较 exec/s、D_F entropy、queued progress、trigger rate
```

## 最近自检状态

最近已通过：

```bash
cd /home/cwh/FORMTRIG

bash -n \
  scripts/formtrig_site_allowlist_from_lift_spec.sh \
  scripts/run_native_formtrig_smoke.sh \
  scripts/run_formtrig_aflpp_campaign.sh \
  scripts/run_formtrig_seed_readiness.sh

git diff --check

./scripts/run_native_formtrig_smoke.sh
```

最新 native smoke 输出：

```text
FORMTRIG native smoke passed
  queued_progress=84
  typed_execs=112
  typed_finds=0
  stability_checks=167
```

还单独编译过关键工具，均通过 `-Wall -Wextra -Werror`：

```bash
cc -std=c11 -Iformtrig/include -Wall -Wextra -Werror formtrig/tools/formtrig_binding_spec_compile.c -o /tmp/formtrig_binding_spec_compile
cc -std=c11 -Iformtrig/include -Wall -Wextra -Werror formtrig/tools/formtrig_binding_map.c -o /tmp/formtrig_binding_map
cc -std=c11 -Iformtrig/include -Wall -Wextra -Werror formtrig/tools/formtrig_progress_summary.c -o /tmp/formtrig_progress_summary
cc -std=c11 -Iformtrig/include -Wall -Wextra -Werror formtrig/tools/formtrig_campaign_diagnose.c -o /tmp/formtrig_campaign_diagnose
cc -std=c11 -Iformtrig/include -Wall -Wextra -Werror formtrig/tools/formtrig_lift_feature_audit.c -o /tmp/formtrig_lift_feature_audit
cc -std=c11 -Iformtrig/include -Wall -Wextra -Werror formtrig/tools/formtrig_lift_spec_audit.c -o /tmp/formtrig_lift_spec_audit
cc -std=c11 -Iformtrig/include -Wall -Wextra -Werror formtrig/tools/formtrig_site_map.c -o /tmp/formtrig_site_map
cc -std=c11 -Iformtrig/include -Wall -Wextra -Werror formtrig/tools/formtrig_binding_signal_diagnose.c -o /tmp/formtrig_binding_signal_diagnose
```

## 真实 CVE 正例：LIBXML2_1107

目标：

```text
LIBXML2_1107
```

性质：

```text
真实 CVE binary-state-null / alloc-failure path
```

TC 语义：

```c
ret->string = xmlStrdup(string);
ret->len = strlen((const char *) ret->string);
if (ret->string == NULL) ...
```

RNT seed：

```text
00 61
```

PoC/crash：

```text
02 61
```

full instrumented binary：

```text
/tmp/formtrig_libxml2_1107_full_20260615T090425Z/libxml2_regexp_strdup_fail_replay_formtrig_full
```

site map：

```text
/tmp/formtrig_libxml2_1107_full_20260615T090425Z/native_env/site_map.tsv
```

重要 site ids：

```text
target/reach branch xmlregexp.c:738: 820871835
root null check xmlregexp.c:741 inst 39: 787463692
strlen use load xmlregexp.c:740 inst 31: 921684644
malloc guard hook line 15 inst 10: 1816698454
malloc fail-count cmp line 15 inst 15: 1900586549
```

BindingSpec：

```text
artifacts/binding_specs/LIBXML2_1107.native_b2_alloc_fail_candidate.yml
```

核心绑定：

```text
root_observe: ret->string null check
desired_producer: input-selected malloc fail count distance_to_b 2
use: strlen load of ret->string
guard: fail-count enabled guard
input_influence: byte 0, mutation hint set_byte 2
```

注意：这个 BindingSpec 是外部语义输入，不是 core workaround。它绑定的是 harness allocation-failure semantics。后续论文/实验里要如实标注这是 harness-level BindingSpec。

## CVE 30s strict sweep 结果

结果目录：

```text
/tmp/formtrig_libxml2_1107_full_strict_sweep_30s
```

关键 summary：

```json
{
  "candidate": "artifacts/binding_specs/LIBXML2_1107.native_b2_alloc_fail_candidate.yml",
  "status": "triggered",
  "exit_code": 0,
  "experiment_ready": true,
  "pretrigger_lift_guidance_ready": true,
  "queued_progress": 1,
  "reached_execs": 19467,
  "triggered_execs": 2,
  "accepted_non_trigger_progress_events": 1,
  "saved_non_trigger_progress_events": 1,
  "saved_triggered_progress_events": 0,
  "non_trigger_candidate_lift_delta": true,
  "lift_delta_only_on_triggered_candidates": false,
  "binding_signal_diagnosis": "role_signal_progress_observed"
}
```

binding signal diagnosis：

```text
spec_d_f_calibration_values: [4]
spec_d_f_non_trigger_candidate_values: [1, 3, 2, 4]
accepted_non_trigger_progress_events: 1
triggered_events: 0
heuristic/manual: 0
```

saved non-trigger progress 证据：

```json
{
  "event": "saved_progress",
  "reason": "root_aligned_state_transition",
  "triggered": 0,
  "stable": 1,
  "d_t": 1,
  "d_f_spec_lifted": 1,
  "d_f_heuristic_lifted": -1,
  "d_f_manual_lifted": -1
}
```

解释：

这是当前最重要的正证据。它说明在真实 CVE binary-null 场景里，`D_T` 仍是二值 `1`，但 BindingSpec-driven `D_F` 在 non-trigger candidates 上移动，并被 dominance frontier 接受。随后 AFL 保存 crash，terminal success 来自 `afl_saved_crashes=2`。

限制：

这次用的是 full instrumentation，约 731 exec/s，不是最终性能形态。下一步必须用 selective instrumentation 重建这个 CVE target 并复跑。

## Magma 当前证据

证据文档：

```text
artifacts/formtrig_native_readiness/magma_lift_smoke_20260615.md
```

已有结论：

- PNG006 无 input influence 时：static 可能过，但 dynamic `D_F` constant，不能声称有效 lift。
- PNG006 加外部 eXIf mutation hook 后：出现有效 pre-trigger lift/progress，是 Magma 正例方向。
- PNG007 PLTE deletion：目前偏 terminal-trigger-only，不足以证明 pre-trigger binary-null lift。
- SQL013：DeepSeek 曾辅助看 BindingSpec，结论是 `insufficient_binding`，因为没有真实绑定 `pNew` / same-object / planner internal root；不能伪造 `nLSlot/nLTerm`。

SQL013 分类要记住：

```text
atom-level: numeric-margin
target/progress-level: compound-sequence-lifecycle gated numeric-margin
```

如果绑定不到 `pNew->nLSlot` 和 `pNew->nLTerm`，只能先做 planner/lifecycle phase lift，不能假造 numeric margin。

## 常用检查命令

基础自检：

```bash
cd /home/cwh/FORMTRIG

bash -n \
  scripts/formtrig_site_allowlist_from_lift_spec.sh \
  scripts/run_native_formtrig_smoke.sh \
  scripts/run_formtrig_aflpp_campaign.sh \
  scripts/run_formtrig_seed_readiness.sh

git diff --check
./scripts/run_native_formtrig_smoke.sh
```

查看 CVE sweep：

```bash
jq '{candidate,status:.diagnosis,exit_code,experiment_ready,pretrigger_lift_guidance_ready,queued_progress,reached_execs,triggered_execs,accepted_non_trigger_progress_events,saved_non_trigger_progress_events,saved_triggered_progress_events,non_trigger_candidate_lift_delta,lift_delta_only_on_triggered_candidates,binding_signal_diagnosis}' \
  /tmp/formtrig_libxml2_1107_full_strict_sweep_30s/summary.jsonl
```

查看 accepted non-trigger progress：

```bash
grep -n 'saved_progress' \
  /tmp/formtrig_libxml2_1107_full_strict_sweep_30s/candidates/001_LIBXML2_1107.native_b2_alloc_fail_candidate.yml/default/formtrig_progress.jsonl
```

## 下一步优先级

### 1. 对 LIBXML2_1107 做 selective rebuild

目标：验证不用 full instrumentation，也能保留同样的 spec `D_F` movement 和 crash，同时 exec/s 更接近 AFL++ native。

推荐流程：

```text
1. full/slice build target，生成完整 site map
2. 用 BindingSpec compile 得到 normalized lift-spec
3. 用 scripts/formtrig_site_allowlist_from_lift_spec.sh 生成 allowlist
4. selective rebuild target
5. seed readiness
6. 30s / 120s sweep
7. 对比 full instrumentation 的 exec/s、D_F entropy、queued progress、trigger rate
```

### 2. 把 selective build 流程脚本化

现在 pass 和 allowlist 脚本已就绪，但还缺完整一键流程：

```text
full-map
  -> compile spec
  -> allowlist
  -> selective rebuild
  -> sweep
```

这应该成为下一轮工程重点。

### 3. 补跑真实 CVE 稍长测试

当前只有 30s 正例。需要 30min / 2h 级别验证稳定性：

- non-trigger progress 是否稳定出现
- queued progress 是否稳定
- terminal crash 是否稳定
- exec/s 是否可接受
- selective instrumentation 是否保持 lift 信号

### 4. Magma 继续找真正 pre-trigger binary/lifecycle 正例

PNG007 当前证据不够。不要强行声称。

如果 producer/use/root binding 不足，应报告：

```text
insufficient_binding
```

而不是让 heuristic 或 terminal-only trigger 被解释成 pre-trigger lift。

### 5. SQL013 不能硬做

除非能绑定 planner internal root 或可信 lifecycle/same-object events。LLM 可以离线生成候选 BindingSpec，但必须经过 deterministic static/dynamic gate。

不能伪造：

```text
pNew->nLSlot
pNew->nLTerm
```

如果只能观察 SQL script phases，就只能声称 planner/lifecycle phase lift。

### 6. 更新 AFL++ patch

`patches/aflplusplus/formtrig_native_runtime.patch` 有修改，但需要确认是否完整包含：

- latest runtime ABI
- source split
- summary/diagnose terminal crash口径
- selective instrumentation 相关行为

不要假设 patch 已经完全同步。

## 风险和禁止事项

不要做：

- 不要把 Python prototype 当主线继续修。
- 不要把 target-specific PNG/SQL/CVE parser 或 repair 写进 FORMTRIG core。
- 不要把 `D_T=1` 当 near trigger。
- 不要把 `R` preserved 当 progress。
- 不要让 backend/target 直接输出正式实验用的 `D_F`。
- 不要混用 spec-driven 和 heuristic-driven lift 做主结果。
- 不要在 BindingSpec 不足时硬声称 binary/lifecycle lift。
- 不要清理大批 untracked artifacts，除非用户明确要求。
- 不要 `git add .`。

## 当前一句话状态

FORMTRIG native 已经有一条可信正线：真实 CVE `LIBXML2_1107` 上，spec-driven `D_F` 在 `D_T=1,T=0` 的 non-trigger seed 上产生了可接受进展，并最终找到 crash。

但它还不是最终实验级实现，因为这条证据目前依赖 full instrumentation。下一步必须把 BindingSpec/site-id selective instrumentation 用到真实 target 上，验证性能和稳定性。
