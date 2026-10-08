"""Structural alignment between independently trained representations (new experiment).

For every group and method, all 10 pairs of held-out-seed models (seeds 10-14) are compared on a
shared probe set (fresh sequences, probe seed 999, same fixed observation map). Each model is also
compared with the ground-truth latent state / true generators / true group elements.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bracketnet.alignment import compare, model_probe, random_span_distance  # noqa: E402
from bracketnet.data import make_dataset  # noqa: E402
from bracketnet.groups import GROUPS, true_generators  # noqa: E402
from bracketnet.model import BracketNet  # noqa: E402
from bracketnet.stats import mean_sd  # noqa: E402

torch.set_num_threads(1)
SEEDS = [10, 11, 12, 13, 14]
METHODS = ["local", "comp", "bracketnet", "bracketnetB"]
PROBE_SEED, N_PROBE = 999, 200


def load(phase, group, tag, seed):
    g = GROUPS[group]
    m = BracketNet(g["d"], g["d"], g["K"])
    m.load_state_dict(torch.load(ROOT / f"results/checkpoints/{phase}/{group}_{tag}_s{seed}.pt"))
    return m.eval()


def main(phase="test", groups=("SO2", "T2", "SO3"), methods=METHODS, out="alignment.json"):
    out_all = {}
    for group in groups:
        probe = make_dataset(group, PROBE_SEED, n_train=1, n_test=N_PROBE)
        truth = (probe.z_test, probe.g_test, true_generators(group))
        d, K = GROUPS[group]["d"], GROUPS[group]["K"]
        out_all[group] = dict(chance_subspace_distance=random_span_distance(d, K))
        for tag in methods:
            probes = {s: model_probe(load(phase, group, tag, s), probe.x_test) for s in SEEDS}
            pairs = [compare(*probes[a], *probes[b]) for a, b in itertools.combinations(SEEDS, 2)]
            vs_true = [compare(*probes[s], *truth) for s in SEEDS]
            summ = lambda rows: {k: mean_sd([r[k] for r in rows]) for k in rows[0]}
            out_all[group][tag] = dict(pairwise=summ(pairs), vs_truth=summ(vs_true),
                                       pairwise_raw=pairs, vs_truth_raw=vs_true)
            print(group, tag, {k: f"{v[0]:.3f}±{v[1]:.3f}" for k, v in summ(pairs).items()},
                  "| truth:", {k: f"{v[0]:.3f}" for k, v in summ(vs_true).items()})
    (ROOT / "results" / out).write_text(json.dumps(out_all, indent=1))


if __name__ == "__main__":
    main()
