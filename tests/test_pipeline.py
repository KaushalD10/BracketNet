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
