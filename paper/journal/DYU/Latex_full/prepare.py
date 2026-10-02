"""Verify frozen results, regenerate the table, and lock the standalone source."""
from pathlib import Path
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib, json, math, re, statistics, subprocess
HERE = Path(__file__).resolve().parent
import runpy
runpy.run_path(str(HERE / "prepare_historical.py"))
ROOT = next(p for p in HERE.parents if (p / "PROJECT.toml").is_file())
MATRIX = ROOT / "results/frozen/LP-REL-2026-A003-001/payload/results/audit/scientific-matrix.json"
EXPECTED = "09bbd7563be8e95c58e12fce38a45eae1c542cf5cc4179647289f44c611d2cea"
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(MATRIX) == EXPECTED, "Frozen matrix changed"
matrix = json.loads(MATRIX.read_text())
rows, provenance = [], []
def fmt(v):
    return str(Decimal(str(v)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN))
for dataset, title in [("coedit", "CoEdit"), ("mooc", "MOOC"), ("wikipedia", "Wikipedia")]:
    for arm, label in [("coupled-end-to-end", "Coupled"), ("decoupled", "Decoupled"), ("freeze-then-probe", "Freeze then probe")]:
        i, record = next((i, s) for i, s in enumerate(matrix["summary"]) if s["dataset"] == dataset and s["task_profile"] == arm)
        runs = [r for r in matrix["runs"] if r["dataset"] == dataset and r["task_profile"] == arm]
        assert sorted(r["seed"] for r in runs) == record["seeds"] == [1, 7, 42]
        values = [r["ind_ap"] for r in runs]
        assert all(math.isfinite(v) and 0 <= v <= 1 for v in values)
        assert len(values) == record["n_seeds"]
        assert math.isclose(statistics.mean(values), record["ind_ap_mean"], abs_tol=1e-12)
        assert math.isclose(statistics.stdev(values), record["ind_ap_std"], abs_tol=1e-12)
        cell = fmt(record["ind_ap_mean"]) + r"\pm" + fmt(record["ind_ap_std"])
        if arm == "decoupled":
            cell = r"\mathbf{" + cell + "}"
        rows.append(f"{title if arm == 'coupled-end-to-end' else ''} & {label} & " + "$" + cell + "$" + r"\\")
        for field in ["ind_ap_mean", "ind_ap_std", "n_seeds"]:
            provenance.append(dict(claim="LP-C-DECOUPLING-001", evidence="LP-E-SCIENTIFIC-MATRIX-001", job="LP-JOB-SLURM-A003-FINAL-RECONCILE-R2", artifact=MATRIX.relative_to(ROOT).as_posix(), sha256=EXPECTED, selector=f"$.summary[{i}].{field}", value=record[field], rounding="half-even, 4 decimals for AP"))
table = r"""\begin{center}
\captionof{table}{Inductive AP: mean and sample SD.}
\small
\begin{tabular}{@{}llr@{}}
\toprule
Corpus & Profile & AP\\ \midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\end{center}"""
p = HERE / "main.tex"
text = p.read_text()
text, n = re.subn(r"(?<=% BEGIN GENERATED RESULTS\n).*?(?=\n% END GENERATED RESULTS)", lambda _: table + "\n", text, flags=re.S)
assert n == 1
p.write_text(text)
cites = set(k for m in re.findall(r"\\cite\{([^}]+)\}", text) for k in m.split(","))
refs = re.findall(r"\\bibitem\{([^}]+)\}", text)
assert cites == set(refs) and len(refs) == len(set(refs)), "Missing or uncited references"
assert refs, "The manuscript must cite its sources; no fixed reference-count quota applies"
(HERE / "numeric-sources.json").write_text(json.dumps(dict(status="DRAFT_SOURCE_MAP_NOT_SNAPSHOT_REGISTRY", table_values=provenance, other_sources={"training_table":"protocols/link_prediction_v1.toml", "corpus_construction":"resources/source_registry.json", "attempt_counts":"results/frozen/LP-REL-2026-A003-001/payload/results/audit/scientific-matrix-attempts.json", "equations":"symbolic definitions and source implementation; equation labels are structural"}, limitations=["This is not the complete per-occurrence numeric registry required for an admitted snapshot."]), indent=2) + "\n")
inputs = [MATRIX, ROOT/"protocols/link_prediction_v1.toml", ROOT/"resources/source_registry.json",
          ROOT/"src/temporal_link_decoupling/modeling/v33/sr_gnn_v3.py",
          ROOT/"src/temporal_link_decoupling/modeling/v33/sr_gnn_v3_3.py",
          ROOT/"src/temporal_link_decoupling/training.py",
          ROOT/"experiments/dataset_builders/build_coedit.py"]
inputs += [HERE/"historical-numeric-sources.json", HERE/"prepare_historical.py"]
historical = json.loads((HERE/"historical-numeric-sources.json").read_text())
inputs += [ROOT/historical["source_root"]/name for name in historical["source_hashes"]]
lock = {q.relative_to(ROOT).as_posix(): digest(q) for q in inputs}
(HERE/"source-lock.json").write_text(json.dumps(dict(source_commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(), inputs=lock, source_sha256=digest(p), references=len(refs)), indent=2)+"\n")
print(f"PASS: nine result cells reconstructed from 27 runs; {len(refs)} cited references; source lock written.")
