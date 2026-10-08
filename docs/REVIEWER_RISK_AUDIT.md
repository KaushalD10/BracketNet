# Reviewer risk audit and simulated reviews

These are simulated critical reviews, written by the same AI system that produced the work. They are not
independent peer review. They aim to anticipate objections; scores are subjective and given only after the final
artifacts were examined.

---

## Reviewer 1: mathematical correctness and novelty

**Summary.** The paper studies a Lie-closure penalty for transition-based latent symmetry learners. It gives the
transformation law of the penalty, a local BCH bound, a classification of closed subalgebras for the benchmarks, and an
"endpoint ambiguity" proposition explaining why a chiral su(2) can be preferred over the true so(3).

**Strengths.**
* The invariance analysis is now precise: the GL(K) law, regularized-projector behaviour, and gradient-equivalence of
  the Gram target.
* Prop. 3 (endpoint ambiguity) is the most interesting result. Part (a) is a clean consequence of quaternion
  transitivity. Part (b) uses a correct topological argument: a flat local trivialization on S² would give a section of
  SO(3) → S², contradicting the hairy-ball theorem. Part (c) is a standard MMSE argument.
* The classification is stated with the conjugation group made explicit (three classes under SO(4), two under O(4)),
  and it is checked by an optimization that does not presuppose it.

**Weaknesses.**
* Prop. 1 and Prop. 2 are standard facts or routine applications. The authors say so, but they take space.
* Prop. 3 is qualitative. Part (b) excludes *exact* transport plus composition for continuous endpoint rules. It
  does not bound the composition loss away from zero, and it does not show that the global minimum of the full
  objective is chiral. The paper is careful to state this, but readers may over-read it.
* The BCH bound covers only rotations of about 0.12 rad or less, so its practical relevance is limited.
* Proofs were checked numerically and line by line by the same system that wrote them; no external expert has
  verified them.

**Technical questions.**
1. Can Prop. 3(b) be made quantitative, e.g. a lower bound on the composition loss in terms of the transition scale σ?
2. Does the chiral preference persist for encoders far from the ground truth?

**Validity concerns.** None blocking. The "exact on the coefficient domain" caveat (8.6 % of chiral coefficients
clipped) should remain visible.

**Originality.** Moderate. The mathematics is standard; its use to explain a concrete failure of symmetry learning is
new to the reviewer's knowledge.

**Recommendation:** weak accept. **Confidence:** 3/5.

---

## Reviewer 2: experimental methodology and statistical rigor

**Summary.** Controlled objective variants on three synthetic groups, with selection on development seeds, a frozen
protocol, 20 fresh seeds, pre-registered primary tests with Holm correction, disjoint seed pairs for cross-model
statistics, an oracle intervention on 20 new seeds, a rendered-image benchmark and extensive ablations.

**Strengths.**
* Unusually careful separation of selection and evaluation, with a git-timestamped pre-registration and a disclosed
  amendment.
* The independent recomputation of the primary tests reproduces every number. Sign-flip-inverted intervals are
  provided where t-intervals are misleading.
* The negative result (CKA vs. structure for predicting transfer) is reported as a failed prediction.
* All runs are bit-reproducible, and every manuscript number is a generated macro.

**Weaknesses.**
* Small scale: 20 seeds, low-dimensional latents, CPU-sized networks. The T² effect is concentrated in a few seeds.
* The oracle intervention adds information (true coefficients), so it does not isolate endpoint ambiguity. The paper
  says so.
* The closure-at-ramp diagnostic (AUC 0.94) is post hoc. The pre-registered chirality predictor is moderate
  (AUC 0.75).
* The transfer stratification pools methods that share seeds and is descriptive only.
* No external baseline is run. The justification (different supervision) is reasonable, but reviewers may still want
  one.
* The λ rule needed an amendment, and the chosen λ trades some development transport for structure.

**Technical questions.**
1. How sensitive are the category counts to the 1 % and 10 % thresholds? Continuous metrics are reported, but a
   threshold sweep would help.
2. Would more development seeds change λ?

**Validity concerns.** No evidence of test-set tuning. Thresholds fixed in advance.

**Recommendation:** weak accept / accept for a workshop. **Confidence:** 4/5.

---

## Reviewer 3: UniReps fit and significance

**Summary.** The paper asks when independently trained transformation models agree, distinguishing five levels of
agreement, and shows that closure produces agreement among a few closed classes, not identification.

**Strengths.**
* A direct fit to UniReps: it shows that embedding similarity (CKA) and transformation-algebra agreement capture
  different failure modes, and that transfer of actions between models depends on agreement in algebra, not on
  correctness.
* The "agreement without correctness" corollary is a crisp, memorable message for the representational-alignment
  community.
* The negative findings are presented as findings.

**Weaknesses.**
* Synthetic only. The rendered benchmark helps but is not a natural-data experiment.
* The method (a closure penalty) is simple, and its practical recipe is unclear given frequent chiral failures.
* The connection to large-model representations is speculative and correctly not claimed.

**Recommendation:** accept (workshop). **Confidence:** 3/5.

---

## Meta-review
The submission is technically careful and honest about its limitations. Its main value is conceptual and diagnostic:
closure regularization turns continuous disagreement into discrete disagreement among closed subalgebras, and a proven
endpoint-ambiguity mechanism explains why the wrong class is often chosen. Weaknesses are scale, synthetic scope, the
qualitative nature of the main proposition, and the absence of an external baseline. None is a correctness flaw.

**Subjective assessment** (assigned after the final artifacts were examined; see SUBMISSION_READINESS.md): a solid
workshop paper. **Scientific readiness: yes. Formatting/venue readiness: conditional** on the official style file and
the venue rules being confirmed by a human.

## Risk register
| Risk | Likelihood | Mitigation in the paper |
|---|---|---|
| "Standard math dressed up as new" | medium | "What is not new" paragraph; standard facts labelled |
| "Synthetic only" | high | rendered benchmark; explicit scope limitation |
| "No baselines" | medium | oracle (HAE-like) intervention; comparison table; justification |
| "Post-hoc storytelling" | medium | pre-registration commits; post-hoc labels; failed prediction reported |
| "Page limit / template" | high if not fixed | official style must be applied (human action) |
| "AI-generated work" | depends on venue policy | disclosure paragraph; authors must verify all claims |
