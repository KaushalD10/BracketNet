"""Training for Local, +Comp. and BracketNet (Eq. 9, Sec. 4.3, Appendix B)."""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field

import numpy as np
import torch

from .data import Dataset
from .model import BracketNet, closure_residual, covariance_penalty, gram_penalty


@dataclass
class Config:
    method: str = "bracketnet"          # 'local' | 'comp' | 'bracketnet'
    steps: int = 420
    batch: int = 160
    lr: float = 2e-3
    weight_decay: float = 1e-5
    clip: float = 5.0
    w_rec: float = 4.0
    w_loc_lat: float = 32.0
    w_loc_obs: float = 2.0
    w_comp: float = 1.2
    closure_weight: float = 0.1          # locked value (Sec. 6.1)
    fit_frac: float = 0.35               # lambda = 0 before this fraction
    close_frac: float = 0.70             # ramp ends; generators frozen afterwards
    schedule: str = "staged"             # 'staged' | 'constant' (rejected pilot) | 'staged_nofreeze'
    closure_mode: str = "reg"            # 'reg' (Eq. 7, evaluated) | 'whitened' (span-only variant)
    n_gen: int | None = None             # generator count K; None = true K of the group
    oracle_actions: bool = False         # intervention: transport uses the TRUE coefficients of each training edge;
                                         # q is trained only by regression to them (for evaluation), comp term off
    w_basis: float = 1.0                 # ASSUMPTION (weight not given)
    gram_target: float = 2.0             # 1.0 reproduces the rejected pilot
    w_cov: float = 1.0                   # ASSUMPTION (form and weight not given)
    eps: float = 1e-6                    # ASSUMPTION (epsilon in P_B not given)
    width: int = 64
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.method not in ("local", "comp", "bracketnet"):
            raise ValueError(self.method)


def closure_lambda(cfg: Config, step: int) -> float:
    if cfg.method != "bracketnet":
        return 0.0
    if cfg.schedule == "constant":
        return cfg.closure_weight
    s = step / cfg.steps
    if s < cfg.fit_frac:
        return 0.0
    if s < cfg.close_frac:  # ASSUMPTION: linear ramp 0 -> closure_weight
        return cfg.closure_weight * (s - cfg.fit_frac) / (cfg.close_frac - cfg.fit_frac)
    return cfg.closure_weight


def generators_frozen(cfg: Config, step: int) -> bool:
    return cfg.method == "bracketnet" and cfg.schedule == "staged" and step / cfg.steps >= cfg.close_frac


def losses(model: BracketNet, x: torch.Tensor, cfg: Config, lam: float, a_true: torch.Tensor | None = None) -> dict:
    """x: (B, 3, p) triples. Returns individual terms and the total of Eq. (9)."""
    A = model.generators()
    z = model.encoder(x)                                      # (B, 3, d)
    a01 = model.infer(z[:, 0], z[:, 1])
    a12 = model.infer(z[:, 1], z[:, 2])
    q_reg = None
    if cfg.oracle_actions:
        # q learns to regress the true coefficients from detached codes; transport uses the true coefficients
        q01 = model.infer(z[:, 0].detach(), z[:, 1].detach())
        q12 = model.infer(z[:, 1].detach(), z[:, 2].detach())
        q_reg = ((q01 - a_true[:, 0]) ** 2).sum(-1).mean() + ((q12 - a_true[:, 1]) ** 2).sum(-1).mean()
        a01, a12 = a_true[:, 0], a_true[:, 1]
    R01, R12 = model.rho(a01, A), model.rho(a12, A)
    rec = ((model.decoder(z) - x) ** 2).sum(-1).sum(-1).mean()
    loc_lat = loc_obs = 0.0
    for t, R in ((0, R01), (1, R12)):
        zp = torch.einsum("bij,bj->bi", R, z[:, t])
        loc_lat = loc_lat + ((zp - z[:, t + 1]) ** 2).sum(-1).mean()
        loc_obs = loc_obs + ((model.decoder(zp) - x[:, t + 1]) ** 2).sum(-1).mean()
    out = dict(rec=rec, loc_lat=loc_lat, loc_obs=loc_obs)
    total = cfg.w_rec * rec + cfg.w_loc_lat * loc_lat + cfg.w_loc_obs * loc_obs
    if q_reg is not None:
        out["q_reg"] = q_reg
        total = total + q_reg
    if cfg.method in ("comp", "bracketnet") and not cfg.oracle_actions:
        R02 = model.rho(model.infer(z[:, 0], z[:, 2]), A)
        comp = ((R02 - R12 @ R01) ** 2).sum((-1, -2)).mean()
        out["comp"] = comp
        total = total + cfg.w_comp * comp
    close = closure_residual(A, cfg.eps, cfg.closure_mode) if A.shape[0] > 1 else A.new_zeros(())
    out["close"] = close
    if lam > 0:
        total = total + lam * close
    basis = gram_penalty(A, cfg.gram_target)
    cov = covariance_penalty(z.reshape(-1, z.shape[-1]))
    out.update(basis=basis, cov=cov)
    total = total + cfg.w_basis * basis + cfg.w_cov * cov
    out["total"] = total
    return out


def train(ds: Dataset, cfg: Config, seed: int, log_every: int = 20, snapshot_steps: tuple = ()):
    torch.manual_seed(seed)
    gen = torch.Generator().manual_seed(seed)
    x = torch.as_tensor(ds.x_train, dtype=torch.float32)
    p, d = x.shape[-1], ds.z_train.shape[-1]
    K = cfg.n_gen or {"SO2": 1, "T2": 2, "SO3": 3, "SO3_d3": 3, "SO3img": 3}[ds.group]
    a_all = torch.as_tensor(ds.a_train, dtype=torch.float32) if cfg.oracle_actions else None
    model = BracketNet(p, d, K, cfg.width)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    history, W_freeze, snapshots = [], None, {}
    perm, ptr = torch.randperm(len(x), generator=gen), 0
    t0 = time.perf_counter()
    for step in range(cfg.steps):
        if ptr + cfg.batch > len(x):   # epoch-wise reshuffle, drop last partial batch
            perm, ptr = torch.randperm(len(x), generator=gen), 0
        idx = perm[ptr:ptr + cfg.batch]
        xb = x[idx]
        ptr += cfg.batch
        lam = closure_lambda(cfg, step)
        if step in snapshot_steps:
            snapshots[step] = model.generators().detach().double().numpy().tolist()
        out = losses(model, xb, cfg, lam, a_all[idx] if a_all is not None else None)
        opt.zero_grad(set_to_none=True)
        out["total"].backward()
        if generators_frozen(cfg, step):
            if W_freeze is None:
                W_freeze = model.W.detach().clone()
            model.W.grad = None          # AdamW skips params without grad: truly frozen
        torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.clip)
        opt.step()
        if step % log_every == 0 or step == cfg.steps - 1:
            history.append(dict(step=step, lam=lam, **{k: float(v.detach()) if torch.is_tensor(v) else float(v) for k, v in out.items()}))
    runtime = time.perf_counter() - t0
    if snapshot_steps:
        snapshots[cfg.steps] = model.generators().detach().double().numpy().tolist()
    return model, dict(history=history, runtime_s=runtime, config=asdict(cfg), W_freeze=W_freeze, snapshots=snapshots)
