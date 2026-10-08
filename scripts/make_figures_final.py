"""Final-protocol figures, generated only from results/final/summary_final.json and alignment_transfer.json."""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import yaml  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
S = json.loads((ROOT / "results/final/summary_final.json").read_text())
AT = json.loads((ROOT / "results/final/alignment_transfer.json").read_text())
P = yaml.safe_load((ROOT / "configs/final_protocol.yaml").read_text())
OUT = ROOT / "figures/final"
OUT.mkdir(parents=True, exist_ok=True)
LAM = P["training"]["closure_weight"]
METHODS = P["evaluation"]["methods"]
LABEL = {"local": "Local", "comp": "+Comp.", "bracketnet": f"BracketNet (λ={LAM:g})", "bracketnet_lam0.1": "BracketNet (λ=0.1)"}
SHORT = {"local": "Local", "comp": "+Comp.", "bracketnet": "BN", "bracketnet_lam0.1": "BN λ=0.1"}
COLOR = {"local": "#2a78d6", "comp": "#eb6834", "bracketnet": "#1baf7a", "bracketnet_lam0.1": "#eda100"}
CATCOL = {"correct_closed": "#0ca30c", "nonclosed": "#fab219", "incorrect_closed": "#d03b3b", "collapsed": "#ec835a"}
CATLAB = {"correct_closed": "correct closed", "incorrect_closed": "incorrect closed", "nonclosed": "not closed", "collapsed": "collapsed"}
CATHATCH = {"correct_closed": "", "incorrect_closed": "xx", "nonclosed": "//", "collapsed": ".."}
GL = {"SO2": "SO(2)", "T2": "T²", "SO3": "SO(3)"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.size": 8, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False, "savefig.dpi": 220,
                     "font.family": "DejaVu Sans", "pdf.fonttype": 42, "ps.fonttype": 42})


def struct0(g):
    """Group-level thresholds (identical for every run of a group) from the first fresh-seed run file."""
    s0 = P["evaluation"]["test_seeds"][0]
    return json.loads((ROOT / f"results/final/runs/test/{g}_comp_s{s0}.json").read_text())["metrics"]["structure"]


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


def strip(ax, g, key, log=False):
    for i, m in enumerate(METHODS):
        v = np.array(S["test"][f"{g}/{m}"]["per_seed"][key], float)
        if log:
            v = np.maximum(v, 1e-8)
        x = i + np.linspace(-0.25, 0.25, len(v))
        ax.scatter(x, v, s=10, color=COLOR[m], edgecolor="white", linewidth=0.4, zorder=3)
        ax.hlines(np.median(v), i - 0.33, i + 0.33, color=INK, lw=1.2, zorder=4)
    ax.set_xticks(range(len(METHODS)), [SHORT[m] for m in METHODS])
    if log:
        ax.set_yscale("log")


# Fig 1: closure and ground-truth distance per fresh seed
fig, axs = plt.subplots(2, 2, figsize=(7.0, 4.4))
for j, g in enumerate(["T2", "SO3"]):
    strip(axs[0, j], g, "closure", log=True)
    axs[0, j].axhline(struct0(g)["tau_closed"], ls="--", color=MUTED, lw=0.9)
    axs[0, j].set_title(f"{GL[g]}: closure residual (dashed: 'closed' threshold)", fontsize=8)
    strip(axs[1, j], g, "gt_distance")
    axs[1, j].axhline(struct0(g)["tau_correct"], ls="--", color=MUTED, lw=0.9)
    axs[1, j].set_title(f"{GL[g]}: ground-truth algebra distance (dashed: 'correct')", fontsize=8)
axs[0, 0].set_ylabel("closure (log)")
axs[1, 0].set_ylabel("subspace distance")
fig.tight_layout()
save(fig, "fig_main_structure")

# Fig 2: structural categories
fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.3), sharey=True)
for ax, g in zip(axs, ["T2", "SO3"]):
    for i, m in enumerate(METHODS):
        c = S["test"][f"{g}/{m}"]["categories"]
        bottom = 0
        for k in ["correct_closed", "incorrect_closed", "nonclosed", "collapsed"]:
            if c[k]:
                ax.bar(i, c[k], 0.62, bottom=bottom, color=CATCOL[k], hatch=CATHATCH[k], edgecolor="white", lw=0.8)
                if c[k] >= 2:
                    ax.text(i, bottom + c[k] / 2, str(c[k]), ha="center", va="center", fontsize=7, color=INK)
                bottom += c[k]
    ax.set_xticks(range(len(METHODS)), [SHORT[m] for m in METHODS])
    ax.set_title(GL[g], fontsize=8)
axs[0].set_ylabel(f"runs (of {S['test']['T2/comp']['n']})")
handles = [plt.Rectangle((0, 0), 1, 1, color=CATCOL[k], hatch=CATHATCH[k], ec="white") for k in CATCOL]
fig.legend(handles, [CATLAB[k] for k in CATCOL], loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.1), fontsize=7)
save(fig, "fig_categories")

# Fig 3: cross-seed alignment on disjoint pairs (paired lines) and CKA
fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.4))
for ax, g in zip(axs[:2], ["T2", "SO3"]):
    D = np.array([[p["algebra_distance"] for p in AT[g][m]["disjoint_pairs"]] for m in METHODS])
    for j in range(D.shape[1]):
        ax.plot(range(len(METHODS)), D[:, j], color=GRID, lw=0.8, zorder=1)
    for i, m in enumerate(METHODS):
        ax.scatter(np.full(D.shape[1], i), D[i], s=12, color=COLOR[m], edgecolor="white", lw=0.4, zorder=3)
        ax.hlines(np.median(D[i]), i - 0.3, i + 0.3, color=INK, lw=1.2, zorder=4)
    ax.axhline(struct0(g)["gt_chance_distance"], ls="--", color=MUTED, lw=0.9)
    ax.set_xticks(range(len(METHODS)), [SHORT[m] for m in METHODS], fontsize=6.5)
    ax.set_title(f"{GL[g]}: cross-seed algebra distance\n(10 disjoint pairs; dashed: random spans)", fontsize=7.5)
ax = axs[2]
for j, g in enumerate(["T2", "SO3"]):
    for i, m in enumerate(METHODS):
        v = [p["cka"] for p in AT[g][m]["disjoint_pairs"]]
        x = j + (i - 1.5) * 0.18
        ax.scatter(np.full(len(v), x), v, s=8, color=COLOR[m], edgecolor="white", lw=0.3, zorder=3,
                   label=LABEL[m] if j == 0 else None)
        ax.hlines(np.median(v), x - 0.07, x + 0.07, color=INK, lw=1.1, zorder=4)
ax.set_xticks([0, 1], ["T²", "SO(3)"])
ax.set_title("latent linear CKA (pairs)", fontsize=7.5)
fig.legend(*ax.get_legend_handles_labels(), loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.1), fontsize=7)
fig.tight_layout()
save(fig, "fig_alignment")

# Fig 4: transfer gap (0 = native quality, 1 = identity guess)
fig, axs = plt.subplots(1, 2, figsize=(7.0, 2.3), sharey=True)
for ax, key, title in [(axs[0], "transfer", "direct transfer  R ρₐ Rᵀ"), (axs[1], "transfer_projected", "transfer projected into b's algebra")]:
    for j, g in enumerate(["T2", "SO3"]):
        for i, m in enumerate(METHODS):
            v = [p["transfer"][key]["mse1_gap"] for p in AT[g][m]["disjoint_pairs"]]
            x = j + (i - 1.5) * 0.18
            ax.scatter(np.full(len(v), x), v, s=8, color=COLOR[m], edgecolor="white", lw=0.3, zorder=3,
                       label=LABEL[m] if j == 0 else None)
            ax.hlines(np.median(v), x - 0.07, x + 0.07, color=INK, lw=1.1, zorder=4)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.axhline(1, color=MUTED, lw=0.8, ls="--")
    ax.set_xticks([0, 1], ["T²", "SO(3)"])
    ax.set_title(title, fontsize=8)
axs[0].set_ylabel("one-step transfer gap")
fig.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.12), fontsize=7)
save(fig, "fig_transfer")

# Fig 5: dev budget sweep (selection data)
fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.3))
budgets = [420, 1000, 2000, 4000]
for m, tag in [("local", "local_B{}"), ("comp", "comp_B{}"), ("bracketnet", "bracketnet_B{}_lam" + f"{LAM:g}"),
               ("bracketnet_lam0.1", "bracketnet_B{}_lam0.1")]:
    for g, ls in [("T2", "-"), ("SO3", ":")]:
        r = [S["dev"][f"{g}/" + tag.format(B)] for B in budgets]
        axs[0].plot(budgets, [x["mse_10step"][0] for x in r], ls, color=COLOR[m], lw=1.6, marker="o", ms=3,
                    label=f"{LABEL[m]}" if g == "T2" else None)
        axs[1].plot(budgets, [max(x["closure"][0], 1e-8) for x in r], ls, color=COLOR[m], lw=1.6, marker="o", ms=3)
        axs[2].plot(budgets, [x["gt_distance"][0] for x in r], ls, color=COLOR[m], lw=1.6, marker="o", ms=3)
for ax, t in zip(axs, ["dev 10-step MSE", "dev closure (log)", "dev ground-truth distance"]):
    ax.set_xscale("log")
    ax.set_xticks(budgets, [str(b) for b in budgets], fontsize=6.5)
    ax.minorticks_off()
    ax.axvline(P["training"]["steps"], color=MUTED, lw=0.8, ls="--")
    ax.set_title(t, fontsize=8)
    ax.set_xlabel("updates")
axs[1].set_yscale("log")
fig.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.14), fontsize=7)
fig.tight_layout()
save(fig, "fig_dev_budget")

# Fig 6: transport curves
fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.2))
for ax, g in zip(axs, ["SO2", "T2", "SO3"]):
    for m in METHODS:
        r = S["test"][f"{g}/{m}"]
        mu, sd = np.array(r["transport_curve_mean"]), np.array(r["transport_curve_sd"])
        t = np.arange(1, len(mu) + 1)
        ax.plot(t, mu, color=COLOR[m], lw=1.6, label=LABEL[m])
        ax.fill_between(t, mu - sd, mu + sd, color=COLOR[m], alpha=0.1, lw=0)
    ax.set_title(GL[g], fontsize=8)
    ax.set_xlabel("chained edges")
axs[0].set_ylabel("observation MSE")
fig.legend(*axs[0].get_legend_handles_labels(), loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.14), fontsize=7)
fig.tight_layout()
save(fig, "fig_transport")
print("figures:", sorted(p.name for p in OUT.glob("*.pdf")))
