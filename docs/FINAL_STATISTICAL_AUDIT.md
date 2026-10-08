# Final statistical audit

Sources: `results/review/statistical_audit.json` (independent re-implementation, `scripts/review_stats.py`),
`results/final/summary_final.json`, `results/review/summary_review.json`, `results/review/transfer_prediction.json`.

## 1. The six pre-registered primary tests: recomputed independently from raw run files
`review_stats.py` re-implements the paired differences, the exact one-sided sign-flip test (full 2ⁿ enumeration) and
the Holm adjustment, without importing the analysis code. **All six match the reported values exactly**
(`matches_reported = true`).

| Test | n | mean diff | median diff | skew | lower / higher | p (one-sided) | Holm p | t 95 % | sign-flip-inverted 95 % | bootstrap 95 % |
|---|---|---|---|---|---|---|---|---|---|---|
| H1 closure, T² | 20 | −0.2689 | −0.0001 | −1.94 | 16/4 | 4.3e-5 | 2.1e-4 | [−0.543, +0.005] | **[−0.533, −0.007]** | [−0.541, −0.038] |
| H2 GT distance, T² | 20 | −0.0217 | −0.0000 | −2.58 | 16/4 | 0.156 | 0.313 | [−0.067, +0.024] | [−0.066, +0.017] | [−0.069, +0.014] |
| H3 cross-seed, T² | 10 | −0.0157 | −0.0001 | −0.33 | 7/3 | 0.377 | 0.377 | [−0.142, +0.111] | [−0.141, +0.109] | [−0.122, +0.086] |
| H1 closure, SO(3) | 20 | −0.5914 | −0.6501 | −0.18 | 20/0 | 9.5e-7 | 5.7e-6 | [−0.855, −0.328] | [−0.857, −0.327] | [−0.830, −0.357] |
| H2 GT distance, SO(3) | 20 | −0.2324 | −0.3321 | 0.21 | 19/1 | 1.2e-4 | 4.9e-4 | [−0.335, −0.130] | [−0.335, −0.129] | [−0.323, −0.138] |
| H3 cross-seed, SO(3) | 10 | −0.2924 | −0.3466 | 0.30 | 9/1 | 2.9e-3 | 8.8e-3 | [−0.442, −0.142] | [−0.446, −0.144] | [−0.414, −0.166] |

## 2. The T² discrepancy explained
For H1 on T², the exact sign-flip test gives p = 4.3e-5, while the two-sided t-interval includes 0.
* The paired differences are heavily left-skewed (skew −1.94). Most seeds differ by ~10⁻⁴, because both methods close.
  A few seeds, where +Comp. fails to close, differ by −0.6 to −2.
* The t-interval uses the sample s.d., which those few seeds inflate, so it is wide.
* The sign-flip test uses the same mean statistic but references it to the exact permutation distribution, which
  depends on how consistently the signs agree (16 of 20 differences are negative).
* The interval obtained by **inverting the primary sign-flip test** is [−0.533, −0.007] and excludes 0, matching the
  primary inference. The bootstrap interval agrees.

**Reporting decision (not chosen for strength).** The paper reports the primary sign-flip test (pre-registered), the
inverted interval (matched to it), the t-interval (as originally reported), the median difference and the skew. It
describes the T² closure effect as *concentrated in a few seeds*. T² H2 and H3 are not significant under any method.

## 3. Independence
* The 10 disjoint pairs (100,101), …, (118,119) use 20 distinct seeds (`pairs_disjoint.all_seeds_distinct = true`),
  so pair-level statistics have independent units.
* The probe sets (seeds 998 and 997) are fixed evaluation inputs shared by all pairs. Inference is conditional on them;
  they are not resampled.
* The all-pairs (190) analyses (E5, transfer stratification) are reported as descriptive. The E5 intervals use a
  seed-level cluster bootstrap that resamples seeds, never pairs.

## 4. Secondary analyses and wording audit
| Quantity | Result | Wording used |
|---|---|---|
| 10-step transport, BracketNet − +Comp. (synthetic) | T² [−0.0199, +0.0066], SO(3) [−0.0080, +0.0061] | "no detectable difference", never "equivalent" or "no cost" |
| 10-step transport (rendered) | +4.5e-4 [+1.4e-4, +7.7e-4] | "a small transport cost" |
| Correct-closed rate, SO(3), 5/20 → 8/20 | exact McNemar p = 0.25 | "not significant" |
| Oracle intervention (pre-registered), seeds 400–419 | chiral 6 → 0 (McNemar p = 0.031); correct 11 → 20 (p = 0.0039) | "supports but does not isolate the mechanism" |
| Rendered: closure, BracketNet vs +Comp. (pre-registered) | lower on 20/20 seeds, one-sided p = 9.5e-7 | reported |
| E2 trace: \|χ\| at ramp → chiral (pre-registered) | AUC 0.75 (16 closed runs) | "moderate", exploratory |
| E2 trace: closure at ramp → chiral | AUC 0.94 | labelled **post hoc** |
| E5: algebra distance vs CKA for transfer failure (pre-registered) | T²: 0.98 vs 1.00; SO(3): 0.62 vs 0.75, difference CI [−0.40, 0.30] | "**prediction not supported**" |

Terms checked in the manuscript: "significant" is used only for Holm-corrected primary tests and exact tests with
stated p. "Detectable" is used only when a 95 % interval excludes zero. "Equivalent", "unchanged" and "no cost" are
not used for transport.

## 5. Multiplicity
Only the six primary tests are Holm-corrected. All other p-values are reported as secondary, without correction, and
labelled as such. The oracle and rendered tests were pre-registered as separate predictions; their p-values are not
corrected across experiments.

## 6. Limitations of the statistics
n = 20 (n = 10 for pairs and ablations). Effects outside SO(3) are small or concentrated in few seeds. Categorical
outcomes depend on thresholds fixed in advance; a post-hoc sensitivity analysis (appendix) shows the qualitative
pattern is stable across 0.1–5 % (closed) and 5–20 % (correct).
