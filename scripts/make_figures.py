"""Generate every figure from results/summary.json and results/alignment.json (no hand-entered numbers)."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "results/summary.json").read_text())
AL = json.loads((ROOT / "results/alignment.json").read_text())
OUT = ROOT / "figures"
OUT.mkdir(exist_ok=True)

# Validated categorical palette (dataviz reference slots 1-4, fixed order); hatches give a non-color cue.
METHODS = ["local", "comp", "bracketnet", "bracketnetB"]
LABEL = {"local": "Local", "comp": "+Comp.", "bracketnet": "BracketNet A (λ=0.1)", "bracketnetB": "BracketNet B (λ=30)"}
COLOR = {"local": "#2a78d6", "comp": "#eb6834", "bracketnet": "#1baf7a", "bracketnetB": "#eda100"}
HATCH = {"local": "", "comp": "//", "bracketnet": "..", "bracketnetB": "xx"}
GLABEL = {"SO2": "SO(2)", "T2": "T²", "SO3": "SO(3)"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
                     "legend.frameon": False, "savefig.dpi": 220, "font.family": "DejaVu Sans"})


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


def bars(ax, groups, metric, phase="test", log=False):
    w = 0.2
    for i, m in enumerate(METHODS):
        for j, g in enumerate(groups):
            r = S[phase][f"{g}/{m}"]
            x = j + (i - 1.5) * w
            vals = np.array(r["per_seed"][metric])
            ax.bar(x, r[metric][0], w * 0.9, color=COLOR[m], hatch=HATCH[m], edgecolor="white", linewidth=0.6,
                   label=LABEL[m] if j == 0 else None)
            ax.scatter(np.full(len(vals), x), vals, s=9, color=INK, zorder=3, linewidths=0)
    ax.set_xticks(range(len(groups)), [GLABEL[g] for g in groups])
    if log:
        ax.set_yscale("log")


# Figure 2: transport and closure
fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.6))
bars(a, ["SO2", "T2", "SO3"], "mse_10step")
a.set_ylabel("10-step chained transport MSE")
a.set_title("Transport fidelity (bars: mean; dots: seeds)", fontsize=8.5, color=INK)
bars(b, ["T2", "SO3"], "closure_residual", log=True)
b.set_ylabel("Lie-closure residual (log)")
b.set_title("Algebraic fidelity (SO(2): identically 0)", fontsize=8.5, color=INK)
fig.legend(*a.get_legend_handles_labels(), loc="lower center", ncol=4, fontsize=7, bbox_to_anchor=(0.5, -0.07))
save(fig, "fig2_main")

# Figure 3: commutator norm per seed with validation threshold
thr = S["threshold"]["threshold"]
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.4), sharey=True)
for ax, g in zip(axs, ["T2", "SO3"]):
    for i, m in enumerate(METHODS):
        v = S["test"][f"{g}/{m}"]["per_seed"]["commutator_norm"]
        ax.scatter(np.full(len(v), i) + np.linspace(-0.12, 0.12, len(v)), v, s=22, color=COLOR[m],
                   edgecolor="white", linewidth=0.6, zorder=3)
    ax.axhline(thr, ls="--", color=MUTED, lw=1)
    ax.text(3.45, thr, f" threshold {thr:.2f}", va="bottom", ha="right", color=MUTED, fontsize=7)
    if g == "SO3":
        ax.axhline(np.sqrt(2), ls=":", color=INK, lw=0.8)
        ax.text(-0.4, np.sqrt(2) + 0.03, "true so(3): √2", color=INK, fontsize=7)
    ax.set_xticks(range(4), ["Local", "+Comp.", "A", "B"])
    ax.set_title(GLABEL[g] + (" (abelian)" if g == "T2" else " (non-abelian)"), fontsize=8.5)
axs[0].set_ylabel("Mean pairwise commutator norm")
save(fig, "fig3_commutator")

# Figure 4: transport error vs path length
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.5))
for ax, g in zip(axs, ["T2", "SO3"]):
    for m in METHODS:
        r = S["test"][f"{g}/{m}"]
        mu, sd = np.array(r["transport_curve_mean"]), np.array(r["transport_curve_sd"])
        t = np.arange(1, len(mu) + 1)
        ax.plot(t, mu, color=COLOR[m], lw=2, label=LABEL[m])
        ax.fill_between(t, mu - sd, mu + sd, color=COLOR[m], alpha=0.12, lw=0)
    ax.set_title(GLABEL[g], fontsize=8.5)
    ax.set_xlabel("Chained transformations")
axs[0].set_ylabel("Observation-space MSE")
axs[0].legend(fontsize=7)
save(fig, "fig4_curves")

# Figure 5: validation closure-weight sweep
lams = [0.05, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0]
gcol = {"T2": "#2a78d6", "SO3": "#eb6834"}
fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.5))
for g in ["T2", "SO3"]:
    tr = [S["validation"][f"{g}/bracketnet_lam{l:g}"]["mse_10step"][0] for l in lams]
    cl = [S["validation"][f"{g}/bracketnet_lam{l:g}"]["closure_residual"][0] for l in lams]
    a.plot(lams, tr, "-o", color=gcol[g], lw=2, ms=4, label=GLABEL[g])
    b.plot(lams, cl, "-o", color=gcol[g], lw=2, ms=4, label=GLABEL[g])
    a.axhline(S["validation"][f"{g}/comp"]["mse_10step"][0], color=gcol[g], ls=":", lw=1)
    b.axhline(S["validation"][f"{g}/comp"]["closure_residual"][0], color=gcol[g], ls=":", lw=1)
for ax in (a, b):
    ax.set_xscale("log")
    ax.set_xlabel("Closure weight λ")
    ax.axvspan(0.04, 1.2, color=GRID, alpha=0.5, lw=0)
b.set_yscale("log")
a.set_ylabel("10-step transport MSE")
b.set_ylabel("Closure residual")
a.set_title("Validation transport (dotted: +Comp.)", fontsize=8.5)
b.set_title("Validation closure (shaded: manuscript grid)", fontsize=8.5)
a.legend(fontsize=7)
save(fig, "fig5_validation")

# Figure 6: cross-seed structural alignment
fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.5))
specs = [("cka", "pairwise", "Latent linear CKA\n(seed pairs)"),
         ("algebra_subspace_distance", "pairwise", "Algebra distance after\nProcrustes (seed pairs)"),
         ("algebra_subspace_distance", "vs_truth", "Algebra distance\nto ground truth")]
for ax, (k, which, title) in zip(axs, specs):
    w = 0.2
    for i, m in enumerate(METHODS):
        for j, g in enumerate(["T2", "SO3"]):
            raw = [r[k] for r in AL[g][m][which + "_raw"]]
            x = j + (i - 1.5) * w
            ax.bar(x, np.mean(raw), w * 0.9, color=COLOR[m], hatch=HATCH[m], edgecolor="white", lw=0.6,
                   label=LABEL[m] if j == 0 else None)
            ax.scatter(np.full(len(raw), x), raw, s=5, color=INK, zorder=3, linewidths=0)
        if k == "algebra_subspace_distance":
            for j, g in enumerate(["T2", "SO3"]):
                ax.hlines(AL[g]["chance_subspace_distance"], j - 0.45, j + 0.45, colors=MUTED, linestyles="--", lw=1)
    ax.set_xticks([0, 1], ["T²", "SO(3)"])
    ax.set_title(title, fontsize=8)
axs[0].set_ylim(0.6, 1.0)
axs[2].text(0.02, 0.98, "dashed: random spans", transform=axs[2].transAxes, ha="left", va="top", color=MUTED, fontsize=6.5)
for ax in axs[1:]:
    ax.set_ylim(0, 0.9)
fig.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncol=4, fontsize=7, bbox_to_anchor=(0.5, -0.08))
save(fig, "fig6_alignment")

# Figure 7: training budget sensitivity (ablation phase, 2000 updates) vs 420-update test runs
fig, ax = plt.subplots(figsize=(3.6, 2.5))
pairs = [("local", "local_steps2000"), ("comp", "comp_steps2000"),
         ("bracketnet", "bracketnet_steps2000_lam0.1"), ("bracketnetB", "bracketnet_steps2000_lam30")]
for j, g in enumerate(["T2", "SO3"]):
    for i, (m, a2000) in enumerate(pairs):
        x = j + (i - 1.5) * 0.2
        v420 = S["test"][f"{g}/{m}"]["closure_residual"][0]
        v2000 = S["ablation"][f"{g}/{a2000}"]["closure_residual"][0]
        ax.plot([x, x], [v420, v2000], color=COLOR[m], lw=1.2)
        ax.scatter([x], [v420], color=COLOR[m], s=18, marker="o", label=LABEL[m] if j == 0 else None, zorder=3)
        ax.scatter([x], [v2000], color=COLOR[m], s=22, marker="^", edgecolor=INK, lw=0.5, zorder=3)
ax.set_yscale("log")
ax.set_xticks([0, 1], ["T²", "SO(3)"])
ax.set_ylabel("Closure residual (mean)")
ax.set_title("420 (●) → 2000 (▲) updates", fontsize=8.5)
ax.legend(fontsize=6, loc="lower left")
save(fig, "fig7_budget")
print("figures written:", sorted(p.name for p in OUT.glob("*.png")))
