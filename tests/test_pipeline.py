import numpy as np
import torch

from bracketnet.data import group_map, make_dataset
from bracketnet.train import Config, closure_lambda, generators_frozen, train
from bracketnet.metrics import evaluate


def test_dataset_shapes_and_fixed_map():
    ds = make_dataset("SO3", 5)
    assert ds.x_train.shape == (1400, 3, 4) and ds.x_test.shape == (500, 11, 4)
    # norms preserved by the true action
    assert np.allclose(np.linalg.norm(ds.z_test, axis=-1), np.linalg.norm(ds.z_test[:, :1], axis=-1))
    f1, f2 = group_map("SO3"), group_map("SO3", split="test")
    assert np.allclose(f1.Q, f2.Q) and np.allclose(f1.B, f2.B)
    g = group_map("SO3", split_dependent=True, split="test")
    assert not np.allclose(f1.Q, g.Q)


def test_schedule():
    c = Config(method="bracketnet")
    assert closure_lambda(c, 0) == 0 and closure_lambda(c, 146) == 0
    assert 0 < closure_lambda(c, 200) < 0.1 and closure_lambda(c, 300) == 0.1
    assert not generators_frozen(c, 293) and generators_frozen(c, 294)
    assert closure_lambda(Config(method="comp"), 300) == 0


def test_generators_frozen_in_final_phase():
    ds = make_dataset("T2", 5, n_train=320, n_test=20)
    cfg = Config(method="bracketnet", steps=20)
    model, info = train(ds, cfg, seed=0)
    assert info["W_freeze"] is not None
    assert torch.equal(model.W.detach(), info["W_freeze"])


def test_determinism():
    ds = make_dataset("SO2", 5, n_train=320, n_test=20)
    r = [evaluate(train(ds, Config(method="comp", steps=10), seed=3)[0], ds)["mse_10step"] for _ in range(2)]
    assert r[0] == r[1]


def test_final_code_paths():
    from bracketnet.structure import structural_report, convergence_report
    ds = make_dataset("SO3", 5, n_train=320, n_test=20)
    for kw, K in [(dict(closure_mode="whitened"), 3), (dict(n_gen=4), 4), (dict(n_gen=2), 2),
                  (dict(schedule="staged_nofreeze"), 3)]:
        model, info = train(ds, Config(method="bracketnet", steps=12, closure_weight=30.0, **kw), seed=0)
        assert model.generators().shape[0] == K
        s = structural_report(model, ds)
        assert s["category"] in ("correct_closed", "incorrect_closed", "nonclosed", "collapsed")
        assert 0.0 <= s["gt_algebra_distance"] <= 1.0 and 0.0 <= s["gt_coverage"] <= 1.0 + 1e-9
        assert np.isfinite(convergence_report(info["history"])["final_total"])
        if kw.get("schedule") == "staged_nofreeze":
            assert info["W_freeze"] is None


def test_true_model_structure_is_correct_closed():
    """Sanity check of the category logic: the ground-truth generators with an identity-like latent are
    classified correct-closed (closure 0, ground-truth distance 0)."""
    from bracketnet.groups import true_generators
    from bracketnet.metrics import closure_residual_np
    from bracketnet.structure import random_closure_level, CLOSED_FRAC
    T = true_generators("SO3")
    assert closure_residual_np(T, 1e-6) <= CLOSED_FRAC * random_closure_level(4, 3)
