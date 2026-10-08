"""Verification of the final submission package (paper/submission, paper/final_submission.pdf).

    python scripts/verify_submission.py [--skip-reruns]

Checks: determinism re-runs (main and review experiments); recomputation of all tables/macros from raw files;
every manuscript macro defined; every literal number listed with its justification or recomputed; PDF build log,
fonts, metadata and anonymity; supplementary archive scan. Writes results/review/verification_submission.json.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SUB = ROOT / "paper/submission"
PDF = ROOT / "paper/final_submission.pdf"
ARCHIVE = ROOT / "supplement/bracketnet_supplement_anonymous.zip"
BANNED = ["kaushal", "duddugunta", "kduddugunta", "kaushald10", "@gmail", "github.com/kaushal", "anthropic.com",
          "claude.ai/code", "session_01", "neurreps"]

# literal numbers in the prose that are protocol constants, definitions or mathematical facts
ALLOWED = {
    "0": "", "1": "", "2": "", "3": "", "4": "", "5": "", "6": "", "9": "", "10": "", "16": "anti-collapse weight",
    "20": "seeds / image size", "35": "schedule %", "64": "width", "70": "schedule %", "100": "", "119": "", "160": "batch",
    "190": "all pairs", "400": "obs dim / seeds", "420": "dev budget", "1000": "dev budget", "2000": "dev budget",
    "280": "dev runs", "0.24": "coef std", "0.18": "obs map", "0.65": "coef bound", "0.1": "threshold / lambda ref",
    "0.5": "transfer failure threshold", "0.3": "ablation / renderer", "0.45": "renderer", "0.7": "renderer",
    "3.2": "renderer field of view / tabcolsep", "1{,}400": "train triples", "4{,}000": "max dev budget",
    "100--119": "seeds", "200--209": "seeds", "300--319": "seeds", "400--419": "seeds", "5--9": "seeds", "5--6": "seeds",
    "0.60": "random-span closure (MC 0.598)", "0.66": "random-span closure (MC 0.661)", "0.80": "chance distance",
    "0.50": "chance distance", "0.12": "radius ln2/4/sqrt2", "45": "principal angle", "1.20": "amendment tolerance",
    "1.2": "comp weight", "2.4": "tabcolsep", "2.6": "tabcolsep", "3.5": "tabcolsep", "2.9": "column width",
    "2.3": "column width", "1.9": "column width", "2.0": "column width",
    "10^{-3}": "lr exponent", "10^{-5}": "wd", "10^{-6}": "eps", "2\\times10^{-3}": "lr",
    "3.2\\times10^{-3}": "theory check (recomputed below)", "10^{-31}": "theory check (recomputed below)",
    "0.002": "min exact p with n=10", "2014": "citation year",
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
    cases = [ROOT / "results/final/runs/test/SO3_bracketnet_s112.json", ROOT / "results/final/runs/test/T2_comp_s105.json",
             ROOT / "results/review/runs/oracle/SO3_oracle_bn_s400.json", ROOT / "results/review/runs/render/SO3img_bracketnet_s300.json"]
    out = []
    for p in cases:
        rec = json.loads(p.read_text())
        sp = rec["spec"]
        cfg = dict(sp["cfg"])
        ds = make_dataset(sp["group"], sp["seed"])
        model, _ = train(ds, Config(method=sp["method"], **cfg), sp["seed"])
        m, s = evaluate(model, ds), structural_report(model, ds)
        diff = max(abs(m[k] - rec["metrics"][k]) for k in ["mse_1step", "mse_10step", "closure_residual"])
        out.append(dict(run=p.name, max_abs_diff=diff, same_category=s["category"] == rec["metrics"]["structure"]["category"]))
        print(f"  rerun {p.name:36s} max|diff|={diff:.3e} same_category={out[-1]['same_category']}", flush=True)
    return out


def recompute():
    files = list((ROOT / "results/final/tables").glob("*.tex")) + list((ROOT / "results/review").glob("*.tex")) + \
        list((ROOT / "results/review/tables").glob("*.tex"))
    before = {str(p): sha(p) for p in files}
    for s in ["analyze_final.py", "analyze_review.py"]:
        subprocess.run([sys.executable, str(ROOT / "scripts" / s)], check=True, capture_output=True)
    after = {str(p): sha(p) for p in files}
    return dict(identical=before == after, changed=[k for k in after if before.get(k) != after[k]])


def macro_audit():
    defined = set()
    for f in [ROOT / "results/final/tables/numbers.tex", ROOT / "results/review/numbers_review.tex"]:
        defined |= set(re.findall(r"\\newcommand\{(\\[NR][A-Za-z]+)\}", f.read_text()))
    used, lits = set(), []
    for f in sorted((SUB / "sections").glob("*.tex")):
        txt = f.read_text()
        used |= set(re.findall(r"\\[NR][A-Z][A-Za-z]+", txt))
        body = re.sub(r"%.*", "", txt)
        body = re.sub(r"\\(label|ref|eqref|cite[tp]?|includegraphics|tabinput|input|begin|end)\{[^}]*\}", "", body)
        body = re.sub(r"\\citep\[[^]]*\]\{[^}]*\}", "", body)
        for m in re.finditer(r"(?<![A-Za-z\\])(\d+(?:\{,\}\d+)?(?:\.\d+)?(?:--\d+)?(?:\\times10\^\{-?\d+\})?)", body):
            if m.group(1) not in ALLOWED:
                lits.append(dict(file=f.name, literal=m.group(1), context=body[max(0, m.start() - 50): m.end() + 15].replace("\n", " ")))
    # \N... and \R... used but undefined (excluding LaTeX built-ins starting with \R / \N that are not ours)
    ours = {u for u in used if re.match(r"\\(N[A-Z]|R[A-Z])", u)}
    return dict(undefined=sorted(ours - defined), n_used=len(ours), unlisted_literals=lits)


def theory_literals():
    import numpy as np
    from bracketnet.data import make_dataset
    from bracketnet.groups import true_generators
    from bracketnet.theory_checks import chiral_basis, chiral_infer, diagonal_infer_minimal, evaluate_solution
    ds = make_dataset("SO3", 100, n_train=600, n_test=10)
    z0, z1, z2 = ds.z_train[:, 0], ds.z_train[:, 1], ds.z_train[:, 2]
    d = evaluate_solution(z0, z1, z2, true_generators("SO3"), diagonal_infer_minimal)
    c = evaluate_solution(z0, z1, z2, chiral_basis(+1), lambda u, v: chiral_infer(u, v, +1))
    return dict(diag_composition=d["composition"], chiral_composition=c["composition"],
                diag_matches_3p2e3=bool(round(d["composition"], 4) == 0.0032),
                chiral_is_1e31_order=bool(c["composition"] < 1e-29), radius_rad=float(np.log(2) / 4 / np.sqrt(2)))


def pdf_checks():
    info = subprocess.run(["pdfinfo", str(PDF)], capture_output=True, text=True).stdout
    fonts = subprocess.run(["pdffonts", str(PDF)], capture_output=True, text=True).stdout
    text = subprocess.run(["pdftotext", str(PDF), "-"], capture_output=True, text=True).stdout.lower()
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    ref = next((p for p in range(1, pages + 1) if re.search(r"^References$", subprocess.run(
        ["pdftotext", "-f", str(p), "-l", str(p), str(PDF), "-"], capture_output=True, text=True).stdout, re.M)), None)
    log = (SUB / ".build_proxy/main.log").read_text(errors="ignore") if (SUB / ".build_proxy/main.log").exists() else ""
    author = re.search(r"^Author:[ \t]*(.*)$", info, re.M)
    return dict(pages=pages, references_page=ref, type3=fonts.count("Type 3"), latex_errors=len(re.findall(r"^! ", log, re.M)),
                warnings=len(re.findall(r"Warning", log)), undefined=len(re.findall(r"undefined", log)),
                overfull=len(re.findall(r"Overfull", log)), pdf_author=(author.group(1).strip() if author else ""),
                identifying=[b for b in BANNED if b in text or b in info.lower()],
                anonymous_header="anonymous author" in text)


def archive_scan():
    if not ARCHIVE.exists():
        return dict(exists=False)
    hits, names = [], []
    with zipfile.ZipFile(ARCHIVE) as z:
        for n in z.namelist():
            names.append(n)
            if n.endswith((".pt", ".png", ".pdf", ".zip")):
                continue
            t = z.read(n).decode("utf-8", errors="ignore").lower()
            for b in BANNED + ["/home/user"]:
                if b in t:
                    hits.append((n, b))
    return dict(exists=True, n_files=len(names), has_git=any("/.git/" in n or n.startswith(".git") for n in names),
                identifier_hits=hits[:50], n_hits=len(hits))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-reruns", action="store_true")
    a = ap.parse_args()
    V = {}
    if not a.skip_reruns:
        V["reruns"] = reruns()
    V["recompute"] = recompute()
    print("recompute identical:", V["recompute"]["identical"], V["recompute"]["changed"])
    V["macros"] = macro_audit()
    print("undefined macros:", V["macros"]["undefined"], "used:", V["macros"]["n_used"])
    for l in V["macros"]["unlisted_literals"]:
        print("   literal", l["file"], repr(l["literal"]), "...", l["context"])
    V["theory_literals"] = theory_literals()
    print("theory literals:", V["theory_literals"])
    V["pdf"] = pdf_checks()
    print("pdf:", V["pdf"])
    V["archive"] = archive_scan()
    print("archive:", {k: v for k, v in V["archive"].items() if k != "identifier_hits"})
    (ROOT / "results/review/verification_submission.json").write_text(json.dumps(V, indent=1))
    hard = dict(
        reruns=all(r["max_abs_diff"] == 0 and r["same_category"] for r in V.get("reruns", [])),
        recompute=V["recompute"]["identical"], macros=not V["macros"]["undefined"],
        literals=not V["macros"]["unlisted_literals"],
        theory=V["theory_literals"]["diag_matches_3p2e3"] and V["theory_literals"]["chiral_is_1e31_order"],
        latex=V["pdf"]["latex_errors"] == 0 and V["pdf"]["undefined"] == 0, fonts=V["pdf"]["type3"] == 0,
        anonymity=not V["pdf"]["identifying"] and V["pdf"]["pdf_author"] == "",
        archive=V["archive"].get("exists", False) and V["archive"].get("n_hits", 1) == 0 and not V["archive"].get("has_git", True))
    print("HARD CHECKS:", hard, "->", "PASS" if all(hard.values()) else "FAIL")
    sys.exit(0 if all(hard.values()) else 1)
