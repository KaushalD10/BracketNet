# Novelty comparison

**Provenance and limits.** The network policy blocked arxiv.org, openreview.net and publisher sites, so the
summaries below are written from prior knowledge of the papers, not from a fresh reading. They describe each
method's *setting* at the level needed to judge overlap. The authors should verify every entry against the papers
before submission, especially the "closure" and "cross-model" columns.

| Work | Input / supervision | What is learned | Lie structure enforced? | Cross-model structural comparison? | Identifiability failures analysed? |
|---|---|---|---|---|---|
| Rao & Ruderman 1999; Sohl-Dickstein et al. 2010 | image pairs related by small transformations | linear generators (operators) acting on pixel space | generators learned; closure not enforced | no | no |
| Cohen & Welling 2014 | pairs of observations under a commutative group | irreducible representations of a compact *commutative* group | abelian structure built in | no | no |
| Dehmamy et al. 2021 (L-conv) | supervised tasks | Lie-algebra-parametrized convolutions | algebra basis learned; closure not explicitly enforced | no | no |
| Yang et al. 2023 (LieGAN) | data distribution (invariance via a discriminator) | generators of a symmetry group in observation space | linear generators; closure not explicitly penalized | no | no |
| Yang et al. 2024 (LaLiGAN) | data distribution + autoencoder | nonlinear map to a latent space with linear symmetries | as LieGAN, in latent space | no | no |
| Gabel et al. 2023 | observations under one-parameter transformations | one-parameter Lie transformations and their distributions | one-parameter (trivially closed) | no | no |
| Park et al. 2022 (symmetric embeddings) | transitions **with known group actions** | equivariant world-model embeddings | group known | no | no |
| Keurti et al. 2023 (Homomorphism AE) | transitions **with action labels** (agent's own actions), group unknown | encoder plus a homomorphism from the action space into a matrix group | homomorphism property enforced via composition of labelled actions | no | limited (mentions representation choices) |
| Higgins et al. 2018 | definition | symmetry-based disentanglement | definitional | no | no |
| Kornblith et al. 2019 (CKA); Williams et al. 2021 (shape metrics); Moschella et al. 2023 | trained networks | similarity / alignment of embeddings | n/a | **embedding** comparison only | n/a |
| Huh et al. 2024 | trained networks | convergence hypothesis for representations | n/a | embedding kernels | n/a |
| **This work** | **unlabelled** transition triples | encoder + endpoint action inference + skew generators | **explicit closure residual**; exact invariance statement | **algebra-level** comparison after alignment; transformation transfer | **yes**: chiral classes, endpoint-ambiguity mechanism, oracle-action intervention |

## Assessment
* **Closure.** Enforcing or regularizing Lie closure of learned generators appears in symmetry-discovery work only
  implicitly, through a parametrization or a group structure assumed known. A closure *penalty* is a simple idea;
  we do not claim it as the main novelty.
* **Closest prior work.** Homomorphism Autoencoders learn group-structured representations from transitions, but they
  use the agent's *action labels*. Our oracle-action intervention is the HAE-like setting: supplying the true action
  coefficients removes the endpoint ambiguity and, by Proposition 5, the composition advantage of chiral solutions.
  The comparison is therefore mechanistically informative, but it is not a reimplementation of HAE and is not
  presented as one.
* **Not compared.** LieGAN and LaLiGAN use distributional, not transition, signals, so no fair head-to-head
  comparison exists on our benchmark. The paper states this.
* **Main original elements, as far as we can tell:**
  1. comparing *transformation algebras* across independently trained models, alongside embedding similarity;
  2. showing that closure turns continuous disagreement into disagreement among a few closed conjugacy classes, with
     the classes classified for the benchmarks;
  3. the endpoint-ambiguity mechanism (Prop. 5), which explains *why* the objective favours a wrong closed algebra,
     and its interventional test;
  4. evidence that transfer between models follows structural correctness, and an AUC comparison with CKA.
* **Not new:** the Lie correspondence, the classification of subalgebras of so(4) and so(5), Dynkin's formula, the
  hairy-ball theorem, quaternion transitivity. The paper labels these as standard.
