# TIF012 B5 Matched 7200s x3 Evidence

Source raw run:

```text
artifacts/formtrig_native_readiness/raw/tif012_b5_matched_7200s_3rep_20260616T223012Z
```

This package is the small, reviewable evidence subset from that raw run. It
keeps only the comparison, baseline summary, and FORMTRIG gate outputs.

## Result

The comparison verdict is:

```text
positive_speedup_matched_comparison
```

This is a speedup/control result, not hard SOTA-pain evidence. Matched
baselines also reach `_T`, and one faithful baseline run reaches `_T` within
the acceptable-time threshold.

## First `_T`

FORMTRIG B5:

- rep1: 0.035s, queue/progress exec 146
- rep2: 0.036s, queue/progress exec 146
- rep3: 0.034s, queue/progress exec 146

Matched AFL++ family baselines:

- AFL++ vanilla: 3/3 success, first `_T` at 930s, 1410s, and 1560s
- AFL++ CmpLog: 1/3 success, first `_T` at 4950s; two reps have no `_T` in 7200s
- local AFL++ Redqueen/operand path: 2/3 success, first `_T` at 6540s and 210s; one rep has no `_T` in 7200s

The fastest individual successful baseline run is Redqueen/operand rep3 at
210s. FORMTRIG's best first `_T` is 0.034s, a 6176.47x speedup against that
individual baseline run. Against the fastest successful baseline-family median
(`aflplusplus_vanilla`, 1410s), the observed speedup is 41470.59x.

## Interpretation

This supports a strong TTE speedup claim for this target: FORMTRIG converts
the repaired typed trigger knowledge into stable early terminal inputs. It does
not support the harder claim that baseline random TC hits are too expensive
under this harness/seed design, because the fastest faithful baseline run
reaches `_T` at 210s.

Limits:

- TIF012 is not proof that baselines cannot solve the target, nor proof of
  unacceptable baseline time cost under the current harness/seed design.
- This is one Magma target, not a generality claim across CVEs or all SOTA tools.
- `redqueen_operand` is the local AFL++ Redqueen/CmpLog operand path, not a
  claim about the original Redqueen artifact without a separate equivalence map.
- FORMTRIG's strict pre-trigger gate is mixed in this run: only one rep has
  `strict_pretrigger_guidance=true`; the primary supported benefit is endpoint
  TTE speedup and typed-repair attribution.
