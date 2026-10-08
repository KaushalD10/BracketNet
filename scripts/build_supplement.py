"""Build the anonymous supplementary archive supplement/bracketnet_supplement_anonymous.zip.

Contents: code (bracketnet/), experiment and analysis scripts, tests, configs, requirements, the result files and
fresh-seed checkpoints behind every number in the paper, and the figures. Excluded: git metadata, the round-1
history (which references an earlier manuscript), logs, LaTeX build products, and the verification scripts (they
contain the authors' identifiers as search strings). File timestamps are normalized.
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "supplement"
OUT.mkdir(exist_ok=True)
ZIP = OUT / "bracketnet_supplement_anonymous.zip"

INCLUDE = ["bracketnet", "tests", "configs", "figures/final", "figures/review",
           "results/final/runs", "results/final/checkpoints/test", "results/final/tables",
           "results/final/summary_final.json", "results/final/alignment_transfer.json",
           "results/review/runs", "results/review/summary_review.json", "results/review/statistical_audit.json",
           "results/review/transfer_prediction.json", "results/review/transfer_allpairs.json",
           "results/review/closure_flow.json", "results/review/numbers_review.tex", "results/review/tables",
           "requirements.txt"]
SCRIPTS = ["run_final.py", "freeze_protocol.py", "run_alignment_final.py", "analyze_final.py", "make_figures_final.py",
           "run_review.py", "review_stats.py", "review_transfer.py", "analyze_review.py", "make_figures_review.py"]
README = """# Supplementary code and results (anonymous)

Reproduces every number, table and figure of the submission.

    pip install -r requirements.txt
    python -m pytest -q tests                        # mathematical and pipeline checks
    python scripts/run_final.py --phase dev          # development grid (selection only)
    python scripts/freeze_protocol.py                # applies configs/dev_selection.yaml -> configs/final_protocol.yaml
    python scripts/run_final.py --phase dev_mode && python scripts/freeze_protocol.py
    python scripts/run_final.py --phase test         # fresh seeds 100-119
    python scripts/run_final.py --phase ablation     # seeds 200-209
    python scripts/run_alignment_final.py            # disjoint-pair alignment and transfer
    python scripts/run_review.py --phase trace|oracle|render
    python scripts/review_stats.py && python scripts/review_transfer.py
    python scripts/analyze_final.py && python scripts/analyze_review.py   # tables + LaTeX number macros
    python scripts/make_figures_final.py && python scripts/make_figures_review.py

Runs are CPU-only and bit-identical on repeat on the same machine. `configs/dev_selection.yaml` and
`configs/review_preregistration.yaml` contain the rules and predictions fixed before the corresponding runs.
Result files: one JSON per run (configuration, metrics, structural report, loss history).
"""


def files():
    for inc in INCLUDE:
        p = ROOT / inc
        if p.is_file():
            yield p
        elif p.is_dir():
            yield from (q for q in sorted(p.rglob("*")) if q.is_file() and "__pycache__" not in q.parts and q.suffix != ".tmp")
    for s in SCRIPTS:
        yield ROOT / "scripts" / s


with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
    for f in files():
        info = zipfile.ZipInfo(str(f.relative_to(ROOT)), date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, f.read_bytes())
    z.writestr(zipfile.ZipInfo("README.md", date_time=(2026, 1, 1, 0, 0, 0)), README)
print(ZIP, ZIP.stat().st_size // 1024, "KiB")
