"""
PROMOTE the CoEdit headline from n=3 to n=5 seeds {42,1,7,2,3}.

WHY (reviewer #3, PM directive 2026-06-09): the headline B−C (decoupling) and
B−TGAT (vs best baseline) deltas are currently 3-seed (df=2 ⇒ wide CI, called
"fragile"). Add the 2 NEW seeds {2,3} for config-B, config-C and TGAT, MERGE with
the existing 3-seed per-seed records (same protocol, same train.py), and re-report
the headline with 5-seed mean±std(ddof=1) + a tighter t-based 95% CI (df=4).

REUSE, NO model code change:
  - config-B / config-C SR-GNN seeds via run_one() with the EXACT flags the existing
    3-seed runs used (verified from v3_3_coedit_ARM_{B,C}_*_3seed.json run records).
  - TGAT seeds are run SEPARATELY in the sbatch via run_baselines_benchmark.py; this
    script MERGES that output file (path via env TGAT_NEW_JSON) with the existing
    3-seed TGAT records.

This script only RUNS the seeds NOT already on disk (idempotent): it loads the
existing 3-seed per-seed ind_ap/trans_ap and computes which of {42,1,7,2,3} are
missing for each system, runs only those, then merges. Aggregation PACKED IN.

Env:
  NEW_SEEDS   (default "2,3")   seeds to ADD on top of the existing 3-seed set
  FULL_SEEDS  (default "42,1,7,2,3")  the target 5-seed set for aggregation
  EPOCHS      (default 20)
  TGAT_NEW_JSON (optional) path to a run_baselines_benchmark.py output holding the
                NEW-seed TGAT coedit runs; merged with the existing 3-seed TGAT.

Outputs:
  experiments/results/v3_3_coedit_B_5seed.json
  experiments/results/v3_3_coedit_C_5seed.json
  experiments/results/baselines_coedit_TGAT_5seed.json
  + prints B−C and B−TGAT 5-seed headline (paired per-seed Δ, mean±std, 95% CI).
"""
import os, sys, json, time
import numpy as np

V33_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, V33_DIR)
from run_v3_3_benchmark import run_one  # noqa: E402

RESULTS = os.path.join(os.path.dirname(os.path.dirname(V33_DIR)), "results")
NEW_SEEDS = [int(s) for s in os.environ.get("NEW_SEEDS", "2,3").split(",") if s.strip()]
FULL_SEEDS = [int(s) for s in os.environ.get("FULL_SEEDS", "42,1,7,2,3").split(",") if s.strip()]
EPOCHS = int(os.environ.get("EPOCHS", "20"))
TGAT_NEW_JSON = os.environ.get("TGAT_NEW_JSON", "").strip()
HIDDEN, BATCH, LR = 128, 500, 1e-3

# EXACT flags from the existing 3-seed runs (verified from the ARM_{B,C} JSONs).
COMMON = dict(
    dataset="coedit", epochs=EPOCHS, hidden=HIDDEN, batch_size=BATCH, lr=LR,
    fsm_arch="v3", fsm_decode="hier", decol_hier_v2=True,
    causal_batch=True, hier_causal_policy=True,
    lambda_edge_trans=0.5, p0_fix=False, edge_h_detach_scorepath=True,
)
ARM_KW = {
    "B": dict(COMMON, design="correct_decoupled"),
    "C": dict(COMMON, design="correct"),
}
EXISTING = {
    "B": os.path.join(RESULTS, "v3_3_coedit_ARM_B_publishable_3seed.json"),
    "C": os.path.join(RESULTS, "v3_3_coedit_ARM_C_correct_3seed.json"),
}


def t_ci95_halfwidth(sd, n):
    """t-based 95% CI half-width for the MEAN. Hardcoded t.975 for small df."""
    if n < 2 or np.isnan(sd):
        return float("nan")
    tval = {2: 12.706, 3: 4.303, 4: 3.182, 5: 2.776, 6: 2.571}.get(n, 1.96)
    return float(tval * sd / np.sqrt(n))


def agg(vals):
    a = np.asarray([v for v in vals if v is not None and not np.isnan(v)], float)
    if a.size == 0:
        return float("nan"), float("nan"), 0
    sd = float(a.std(ddof=1)) if a.size > 1 else 0.0
    return float(a.mean()), sd, int(a.size)


def load_existing_srgnn(path):
    """seed -> {ind_ap, trans_ap, ind_auc, trans_auc}"""
    out = {}
    if not os.path.exists(path):
        return out
    with open(path) as f:
        d = json.load(f)
    for r in d.get("runs", []):
        out[int(r["seed"])] = {
            "ind_ap": r["ind_ap"], "trans_ap": r["trans_ap"],
            "ind_auc": r.get("ind_auc"), "trans_auc": r.get("trans_auc"),
            "time_s": r.get("train_time_s"), "source": "existing_3seed",
        }
    return out


def run_srgnn_arm(arm):
    have = load_existing_srgnn(EXISTING[arm])
    per_seed = dict(have)
    for s in FULL_SEEDS:
        if s in per_seed:
            print(f"[{arm}] seed {s} REUSED from {EXISTING[arm]} "
                  f"(ind_ap={per_seed[s]['ind_ap']:.4f})", flush=True)
            continue
        print("=" * 78, flush=True)
        print(f"[{arm}] RUN new seed {s}  design={ARM_KW[arm]['design']}", flush=True)
        ts = time.time()
        r = run_one(seed=s, **ARM_KW[arm])
        dt = time.time() - ts
        per_seed[s] = {"ind_ap": r["ind_ap"], "trans_ap": r["trans_ap"],
                       "ind_auc": r["ind_auc"], "trans_auc": r["trans_auc"],
                       "time_s": dt, "source": "new"}
        print(f"  -> ind_ap={r['ind_ap']:.4f} trans_ap={r['trans_ap']:.4f} ({dt:.0f}s)",
              flush=True)
    return per_seed


def load_tgat_existing():
    path = os.path.join(RESULTS, "baselines", "baselines_coedit_Bprotocol.json")
    out = {}
    if not os.path.exists(path):
        return out
    with open(path) as f:
        d = json.load(f)
    for r in d.get("runs", []):
        if r.get("model") == "tgat" and r.get("dataset") == "coedit":
            out[int(r["seed"])] = {"ind_ap": r["ind_ap"], "trans_ap": r["trans_ap"],
                                   "ind_auc": r.get("ind_auc"),
                                   "trans_auc": r.get("trans_auc"),
                                   "source": "existing_3seed"}
    return out


def load_tgat_new():
    out = {}
    if not (TGAT_NEW_JSON and os.path.exists(TGAT_NEW_JSON)):
        return out
    with open(TGAT_NEW_JSON) as f:
        d = json.load(f)
    for r in d.get("runs", []):
        if r.get("model") == "tgat" and r.get("dataset") == "coedit":
            out[int(r["seed"])] = {"ind_ap": r["ind_ap"], "trans_ap": r["trans_ap"],
                                   "ind_auc": r.get("ind_auc"),
                                   "trans_auc": r.get("trans_auc"), "source": "new"}
    return out


def summarize(per_seed):
    seeds = [s for s in FULL_SEEDS if s in per_seed]
    ind = [per_seed[s]["ind_ap"] for s in seeds]
    tr = [per_seed[s]["trans_ap"] for s in seeds]
    im, isd, n = agg(ind)
    tm, tsd, _ = agg(tr)
    return {
        "seeds": seeds, "n_seeds": n,
        "ind_ap_mean": im, "ind_ap_std": isd,
        "ind_ap_ci95_halfwidth": t_ci95_halfwidth(isd, n),
        "trans_ap_mean": tm, "trans_ap_std": tsd,
        "trans_ap_ci95_halfwidth": t_ci95_halfwidth(tsd, n),
        "per_seed": {str(s): per_seed[s] for s in seeds},
    }


def write(path, payload):
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"wrote {path}", flush=True)


def main():
    t0 = time.time()
    B = run_srgnn_arm("B")
    C = run_srgnn_arm("C")
    TGAT = dict(load_tgat_existing()); TGAT.update(load_tgat_new())

    sB, sC, sT = summarize(B), summarize(C), summarize(TGAT)

    meta = {"protocol": "B-protocol chrono 70/15/15, fair ind neg, leak-free, "
                        "sklearn AP; std=ddof=1; CI=t.975 half-width",
            "full_seeds": FULL_SEEDS, "epochs": EPOCHS}
    write(os.path.join(RESULTS, "v3_3_coedit_B_5seed.json"),
          {"meta": dict(meta, arm="B (correct_decoupled, detached head)",
                        config=ARM_KW["B"]), "summary": sB})
    write(os.path.join(RESULTS, "v3_3_coedit_C_5seed.json"),
          {"meta": dict(meta, arm="C (correct, end-to-end)",
                        config=ARM_KW["C"]), "summary": sC})
    write(os.path.join(RESULTS, "baselines_coedit_TGAT_5seed.json"),
          {"meta": dict(meta, model="tgat (best baseline)"), "summary": sT})

    # ---- paired headline deltas on the COMMON seed set ----
    def paired_delta(P, Q, key="ind_ap"):
        common = sorted(set(P) & set(Q) & set(FULL_SEEDS))
        d = np.array([P[s][key] - Q[s][key] for s in common], float)
        d = d[~np.isnan(d)]
        m = float(d.mean()) if d.size else float("nan")
        sd = float(d.std(ddof=1)) if d.size > 1 else 0.0
        return common, [round(P[s][key] - Q[s][key], 4) for s in common], m, sd

    print("\n" + "=" * 92, flush=True)
    print(f"COEDIT 5-SEED HEADLINE  seeds={FULL_SEEDS}  ind_ap mean±std(ddof=1) [95% CI half-width]",
          flush=True)
    print("-" * 92, flush=True)
    for name, s in (("config-B (SR-GNN)", sB), ("config-C (SR-GNN)", sC),
                    ("TGAT (best baseline)", sT)):
        print(f"  {name:<22} ind_ap = {s['ind_ap_mean']:.4f} ± {s['ind_ap_std']:.4f}  "
              f"[±{s['ind_ap_ci95_halfwidth']:.4f}]  n={s['n_seeds']}", flush=True)
    print("-" * 92, flush=True)
    for tag, P, Q in (("B − C   (decoupling)", B, C),
                      ("B − TGAT (vs best baseline)", B, TGAT)):
        common, ps, m, sd = paired_delta(P, Q)
        ci = t_ci95_halfwidth(sd, len(common))
        print(f"  Δind {tag:<28} = {m:+.4f} ± {sd:.4f}  [±{ci:.4f}]  "
              f"n={len(common)}  per-seed={ps}", flush=True)
    print("=" * 92, flush=True)
    print(f"total {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
