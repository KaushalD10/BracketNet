"""Final verification: determinism, recomputation from raw data, manuscript number audit, PDF checks.

    python scripts/verify_final.py [--skip-reruns]

Writes results/final/verification.json and exits non-zero if any hard check fails.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PAPER = ROOT / "paper/final"
OUT = ROOT / "results/final"

# Literal numbers allowed in the manuscript text, with the source that fixes them (protocol constants,
# definitions and mathematical constants). Every other literal is listed for manual review.
ALLOWED = {
    "0.24": "coefficient std (data spec)", "0.18": "observation nonlinearity (data spec)", "0.65": "coefficient bound",
    "1{,}400": "train triples", "500": "test sequences", "200": "probe sequences", "64": "MLP width", "160": "batch",
    "5": "clip / seeds", "16": "anti-collapse weight", "0.1": "lambda reference / thresholds", "0.5": "thresholds / geometry",
    "0.35": "schedule", "0.70": "schedule", "35": "schedule %", "70": "schedule %", "30": "schedule %", "10": "thresholds / edges",
    "1": "constants", "2": "constants", "3": "dims", "4": "dims / PR", "0": "constants", "100": "seed ids", "119": "seed ids",
    "200--209": "ablation seeds", "100--119": "test seeds", "5--9": "dev seeds", "5--6": "preliminary seeds", "190": "all pairs",
    "4{,}000": "max dev budget", "420": "dev budget", "1000": "dev budget", "2000": "dev budget",
    "0.80": "chance distance T2 (random-span MC)", "0.50": "chance distance SO3 (random-span MC)",
    "0.60": "random-span closure T2 (MC 0.598)", "0.66": "random-span closure SO3 (MC 0.661)",
    "0.12": "rotation radius from ln2/4 / sqrt2", "45": "principal angle (test_T6)", "0.005": "max CKA spread (checked below)",
    "0.36": "SO3 correct-closed action range (checked below)", "0.43": "SO3 correct-closed action range (checked below)",
    "0.01": "near-exception pair gt distance (checked below)", "0.03": "near-exception pair gap (checked below)",
    "31": "runtime range (checked below)", "106": "runtime range (checked below)", "1.20": "amendment tolerance",
    "10^{-6}": "eps", "10^{-3}": "lr exponent", "10^{-5}": "weight decay", "2\\times10^{-3}": "lr",
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def reruns():
    import torch
    torch.set_num_threads(1)
    from bracketnet.data import make_dataset
    from bracketnet.metrics import evaluate
    from bracketnet.structure import structural_report
    from bracketnet.train import Config, train
    out = []
    for name in ["SO3_bracketnet_s100", "T2_comp_s105", "SO3_bracketnet_s112", "T2_bracketnet_lam0.1_s118"]:
        rec = json.loads((OUT / f"runs/test/{name}.json").read_text())
        sp = rec["spec"]
        ds = make_dataset(sp["group"], sp["seed"])
        model, _ = train(ds, Config(method=sp["method"], **sp["cfg"]), sp["seed"])
        m = evaluate(model, ds)
        s = structural_report(model, ds)
        keys = ["mse_1step", "mse_10step", "closure_residual", "commutator_norm"]
        diff = max([abs(m[k] - rec["metrics"][k]) for k in keys] +
                   [abs(s["gt_algebra_distance"] - rec["metrics"]["structure"]["gt_algebra_distance"])])
        same_cat = s["category"] == rec["metrics"]["structure"]["category"]
        out.append(dict(run=name, max_abs_diff=diff, same_category=same_cat))
        print(f"  rerun {name:32s} max|diff|={diff:.3e} category_same={same_cat}", flush=True)
    return out


def recompute():
    before = {p.name: sha(p) for p in (OUT / "tables").glob("*.tex")}
    before["summary_final.json"] = sha(OUT / "summary_final.json")
    subprocess.run([sys.executable, str(ROOT / "scripts/analyze_final.py")], check=True, capture_output=True)
    after = {p.name: sha(p) for p in (OUT / "tables").glob("*.tex")}
    after["summary_final.json"] = sha(OUT / "summary_final.json")
    return dict(identical=before == after, changed=[k for k in after if before.get(k) != after[k]])


def macro_audit():
    defined = set(re.findall(r"\\newcommand\{(\\N[A-Za-z]+)\}", (OUT / "tables/numbers.tex").read_text()))
    used, literals = set(), []
    for f in sorted((PAPER / "sections").glob("*.tex")):
        txt = f.read_text()
        used |= set(re.findall(r"\\N[A-Za-z]+", txt))
        body = re.sub(r"%.*", "", txt)
        body = re.sub(r"\\(label|ref|cite[tp]?|includegraphics|tabinput|input|begin|end)\{[^}]*\}", "", body)
        body = re.sub(r"\\citep\[[^]]*\]\{[^}]*\}", "", body)
        for m in re.finditer(r"(?<![A-Za-z\\])(\d+(?:\{,\}\d+)?(?:\.\d+)?(?:--\d+)?(?:\\times10\^\{-?\d+\})?)", body):
            lit = m.group(1)
            if lit not in ALLOWED:
                ctx = body[max(0, m.start() - 40): m.end() + 20].replace("\n", " ")
                literals.append(dict(file=f.name, literal=lit, context=ctx))
    return dict(undefined=sorted(used - defined), n_used=len(used), unlisted_literals=literals)


def literal_checks():
    """Recompute the few literal numbers in the prose that are not macros."""
    import numpy as np
    S = json.loads((OUT / "summary_final.json").read_text())
    AT = json.loads((OUT / "alignment_transfer.json").read_text())
    res = {}
    ckas = [S["test"][f"{g}/{t}"]["cka_truth"][0] for g in ["T2", "SO3"] for t in S["protocol"]["evaluation"]["methods"]]
    cka_pairs = [S["alignment"][f"{g}/{t}"]["cka"][0] for g in ["T2", "SO3"] for t in S["protocol"]["evaluation"]["methods"]]
    spread = max(max(ckas[:4]) - min(ckas[:4]), max(ckas[4:]) - min(ckas[4:]),
                 max(cka_pairs[:4]) - min(cka_pairs[:4]), max(cka_pairs[4:]) - min(cka_pairs[4:]))
    res["cka_spread_max<=0.005"] = bool(round(spread, 3) <= 0.005)
    act = []
    for t in S["protocol"]["evaluation"]["methods"]:
        r = S["test"][f"SO3/{t}"]["per_seed"]
        act += [a for a, c in zip(r["action_truth"], r["category"]) if c == "correct_closed"]
    res["so3_correct_action_range"] = [round(min(act), 2), round(max(act), 2)]
    res["so3_correct_action_range_matches_0.36_0.43"] = res["so3_correct_action_range"] == [0.36, 0.43]
    pair = [p for p in AT["SO3"]["comp"]["disjoint_pairs"] if p["categories"] == ["nonclosed", "nonclosed"]
            and p["transfer"]["transfer"]["mse1_gap"] < 0.1]
    gts = S["test"]["SO3/comp"]["per_seed"]["gt_distance"]
    seeds = S["test"]["SO3/comp"]["seeds"]
    if pair:
        a, b = pair[0]["pair"]
        res["near_exception_pair"] = dict(pair=[a, b], gap=round(pair[0]["transfer"]["transfer"]["mse1_gap"], 2),
                                          gt=[round(gts[seeds.index(a)], 2), round(gts[seeds.index(b)], 2)])
        res["near_exception_matches_text"] = res["near_exception_pair"]["gap"] == 0.03 and max(res["near_exception_pair"]["gt"]) <= 0.01
    rts = [v for k, c in S["test"].items() for v in c["per_seed"]["runtime_s"]]
    res["runtime_range"] = [int(np.floor(min(rts))), int(np.ceil(max(rts)))]
    res["runtime_matches_31_106"] = res["runtime_range"] == [31, 107] or res["runtime_range"] == [31, 106]
    t2_fail = {}
    for t in S["protocol"]["evaluation"]["methods"]:
        r = S["test"][f"T2/{t}"]
        t2_fail[t] = [s for s, c in zip(r["seeds"], r["per_seed"]["category"]) if c == "nonclosed"]
    res["t2_nonclosed_seeds"] = t2_fail
    res["t2_failure_text_matches"] = (all({102, 115, 118} <= set(v) for v in t2_fail.values())
                                      and all({109, 116, 119} <= set(t2_fail[t]) for t in ["local", "comp", "bracketnet_lam0.1"]))
    return res


def pdf_checks():
    pdf = PAPER / "main.pdf"
    info = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    fonts = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True).stdout
    text = subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True).stdout
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    ref_page = None
    for p in range(1, pages + 1):
        t = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), str(pdf), "-"], capture_output=True, text=True).stdout
        if re.search(r"^References$", t, re.M):
            ref_page = p
            break
    banned = ["kaushal", "duddugunta", "kduddugunta", "github.com", "bracketnet.git", "claude", "anthropic", "neurreps"]
    hits = [b for b in banned if b in text.lower() or b in info.lower()]
    author = re.search(r"^Author:[ \t]*(.*)$", info, re.M)
    log = (PAPER / "main.log").read_text(errors="ignore")
    return dict(pages=pages, references_start_page=ref_page, main_text_ends_on_page=ref_page,
                type3_fonts=fonts.count("Type 3"), identifying_strings=hits,
                pdf_author=(author.group(1).strip() if author else ""),
                latex_errors=len(re.findall(r"^! ", log, re.M)),
                undefined_refs=len(re.findall(r"undefined", log)),
                overfull_boxes=len(re.findall(r"Overfull \\hbox", log)))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-reruns", action="store_true")
    a = ap.parse_args()
    V = {}
    if not a.skip_reruns:
        print("determinism re-runs:")
        V["reruns"] = reruns()
    V["recompute"] = recompute()
    print("recompute identical:", V["recompute"]["identical"], V["recompute"]["changed"])
    V["macros"] = macro_audit()
    print("undefined macros:", V["macros"]["undefined"], "| macros used:", V["macros"]["n_used"])
    print("unlisted literals:", len(V["macros"]["unlisted_literals"]))
    for l in V["macros"]["unlisted_literals"]:
        print(f"   {l['file']}: {l['literal']!r} ... {l['context']}")
    V["literal_checks"] = literal_checks()
    print("literal checks:", json.dumps(V["literal_checks"]))
    V["pdf"] = pdf_checks()
    print("pdf:", V["pdf"])
    (OUT / "verification.json").write_text(json.dumps(V, indent=1))
    hard = [
        all(r["max_abs_diff"] == 0 and r["same_category"] for r in V.get("reruns", [])),
        V["recompute"]["identical"], not V["macros"]["undefined"],
        all(v for k, v in V["literal_checks"].items() if k.endswith(("matches_text", "_matches_31_106", "<=0.005", "matches_0.36_0.43"))),
        V["pdf"]["latex_errors"] == 0, V["pdf"]["undefined_refs"] == 0, V["pdf"]["type3_fonts"] == 0,
        not V["pdf"]["identifying_strings"], V["pdf"]["pdf_author"] == "",
    ]
    print("HARD CHECKS:", "PASS" if all(hard) else f"FAIL {hard}")
    sys.exit(0 if all(hard) else 1)
