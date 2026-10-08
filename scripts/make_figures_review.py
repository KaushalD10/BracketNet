"""Review figures (mechanism, rendered benchmark), generated only from result files."""
import glob
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bracketnet.so4 import chirality  # noqa: E402

OUT = ROOT / "figures/review"
OUT.mkdir(parents=True, exist_ok=True)
S = json.loads((ROOT / "results/review/summary_review.json").read_text())
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
METHOD_COL = {"local": "#2a78d6", "comp": "#eb6834", "bracketnet": "#1baf7a", "bracketnet_lam0.1": "#eda100"}
METHOD_LAB = {"local": "Local", "comp": "+Comp.", "bracketnet": "BracketNet", "bracketnet_lam0.1": "BN λ=0.1"}
CAT_COL = {"correct_closed": "#0ca30c", "incorrect_closed-chiral": "#d03b3b", "nonclosed": "#fab219", "collapsed": "#ec835a"}
CAT_LAB = {"correct_closed": "correct (diagonal)", "incorrect_closed-chiral": "chiral", "nonclosed": "not closed"}
CAT_HATCH = {"correct_closed": "", "incorrect_closed-chiral": "xx", "nonclosed": "//"}
plt.rcParams.update({"font.size": 7.5, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True, "legend.frameon": False,
                     "savefig.dpi": 220, "font.family": "DejaVu Sans", "pdf.fonttype": 42, "ps.fonttype": 42})


def cls(r):
    s = r["metrics"]["structure"]
    return s["category"] + ("-" + s["incorrect_subtype"] if s["incorrect_subtype"] else "")


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


fig, axs = plt.subplots(1, 4, figsize=(7.2, 2.0), gridspec_kw=dict(width_ratios=[1.25, 1, 1, 1.15]))
# (a) final chirality vs closure, all SO(3) fresh-seed runs
ax = axs[0]
for m in METHOD_COL:
    pts = []
    for p in sorted(glob.glob(str(ROOT / f"results/final/runs/test/SO3_{m}_s*.json"))):
        r = json.loads(Path(p).read_text())
        A = np.array(r["metrics"]["generators"])
        pts.append((chirality(A), max(r["metrics"]["closure_residual"], 1e-6)))
    pts = np.array(pts)
    ax.scatter(pts[:, 0], pts[:, 1], s=9, color=METHOD_COL[m], edgecolor="white", lw=0.3, label=METHOD_LAB[m], zorder=3)
ax.set_yscale("log")
ax.set_xlabel("chirality χ = e_L − e_R")
ax.set_ylabel("closure residual")
ax.set_xticks([-1, 0, 1], ["−1\nsu(2)_R", "0\ndiagonal", "+1\nsu(2)_L"])
ax.set_title("(a) final SO(3) spans", fontsize=7.5)
meth_handles = ax.get_legend_handles_labels()

# (b) trace: closure at ramp start by final class
ax = axs[1]
rows = S["E2"]["rows"]
ramp = S["E2"]["steps"][1]
for i, c in enumerate(["correct_closed", "incorrect_closed-chiral", "nonclosed"]):
    v = [max(r[f"closure_{ramp}"], 1e-6) for r in rows if r["final_class"] == c]
    ax.scatter(np.full(len(v), i) + np.linspace(-0.15, 0.15, len(v)), v, s=11, color=CAT_COL[c], edgecolor="white", lw=0.3, zorder=3)
ax.set_yscale("log")
ax.set_xticks([0, 1, 2], ["correct", "chiral", "not\nclosed"])
ax.set_xlabel("final outcome (BracketNet)")
ax.set_title("(b) closure before the ramp", fontsize=7.5)

# (c) composition error by class
ax = axs[2]
for i, c in enumerate(["correct_closed", "incorrect_closed-chiral", "nonclosed"]):
    v = [json.loads(Path(p).read_text()) for p in glob.glob(str(ROOT / "results/final/runs/test/SO3_*.json"))]
    v = [r["metrics"]["composition_mse"] for r in v if cls(r) == c]
    ax.scatter(np.full(len(v), i) + np.random.default_rng(i).uniform(-0.18, 0.18, len(v)), v, s=6, color=CAT_COL[c],
               edgecolor="white", lw=0.2, zorder=3)
    ax.hlines(np.median(v), i - 0.25, i + 0.25, color=INK, lw=1.1, zorder=4)
ax.set_yscale("log")
ax.set_xticks([0, 1, 2], ["correct", "chiral", "not\nclosed"])
ax.set_title("(c) composition error", fontsize=7.5)

# (d) oracle intervention outcomes
ax = axs[3]
if "E3" in S:
    tags = [("comp", "+Comp."), ("bracketnet", "BN"), ("oracle_local", "oracle\nno closure"), ("oracle_bn", "oracle\nBN")]
    for i, (t, lab) in enumerate(tags):
        c = S["E3"][t]["counts"]
        bottom = 0
        for k in ["correct_closed", "incorrect_closed-chiral", "nonclosed"]:
            n = c.get(k, 0)
            if n:
                ax.bar(i, n, 0.62, bottom=bottom, color=CAT_COL[k], hatch=CAT_HATCH[k], edgecolor="white", lw=0.6)
                if n >= 2:
                    ax.text(i, bottom + n / 2, str(n), ha="center", va="center", fontsize=6)
                bottom += n
    ax.set_xticks(range(4), [l for _, l in tags], fontsize=6)
    ax.set_ylabel("runs (of 20)")
    ax.set_title("(d) true coefficients, seeds 400–419", fontsize=7.5)
handles = [plt.Rectangle((0, 0), 1, 1, color=CAT_COL[k], hatch=CAT_HATCH[k], ec="white") for k in CAT_LAB]
fig.legend(handles, list(CAT_LAB.values()), loc="lower center", ncol=3, bbox_to_anchor=(0.66, -0.17), fontsize=6.5)
fig.legend(*meth_handles, loc="lower center", ncol=2, bbox_to_anchor=(0.14, -0.22), fontsize=6, handletextpad=0.1,
           columnspacing=0.6)
fig.tight_layout(w_pad=0.6)
save(fig, "fig_mechanism")
print("written", sorted(p.name for p in OUT.glob("*.pdf")))
