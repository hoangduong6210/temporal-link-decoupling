"""
KNOB-ISOLATION ABLATION on STANDARD benchmark data (wikipedia / mooc).

WHY (reviewer #2, PM directive 2026-06-09): the inductive-gain mechanism
(`enable_main_predictor=False` → large inductive AP gain) has so far only been
shown on CoEdit (self-built). Reviewer wants it on standard data. This reuses the
EXACT same config-B publishable stack + run_one() as the coedit knob ablation
(_knob_ablation_3seed.py) but on wikipedia and mooc, restricted to the LOAD-BEARING
arms so wall-clock stays sane on the heavier datasets:

  B       : design=correct_decoupled, enable_main_predictor=False  (detached head)
  K1_e2e  : B + enable_main_predictor=True   (--p0_fix on; end-to-end main head)
  K2K3_gate (optional, set ARM_K2K3=1): B + lfg_mode=hard + compliance_floor=0.0
            (the real hard causal gate; included to confirm it is NOT what drives
            the inductive gain on standard data either)

MECHANISM CLAIM under test: B should have a LARGE inductive AP gain over K1
(Δind = ind_ap(B) − ind_ap(K1_e2e) >> 0), mirroring CoEdit (B 0.9899 vs K1 0.7788,
Δind ≈ +0.211, 3-seed). If Δind is SMALL/zero on wiki/mooc → mechanism IS a CoEdit
artifact → reported HONESTLY (that is the finding the reviewer is probing for).

NO model code changed — run_one + existing CLI/ctor flags only. Same B-protocol as
every other v3.3 run (train.py:run_epoch, chrono 70/15/15, fair inductive neg pool,
PRE-update leak-free scoring, sklearn AP). ind_ap aggregated mean ± std(ddof=1).

Dataset chosen via env DATASET (wikipedia|mooc); seeds via env SEEDS (default 42,1,7).
Output JSON (aggregation PACKED IN — one invocation = predictions + summary):
  experiments/results/v3_3_knob_ablation_{DATASET}_3seed.json
"""
import os, sys, json, time
import numpy as np

V33_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, V33_DIR)
from run_v3_3_benchmark import run_one  # noqa: E402

DATASET = os.environ.get("DATASET", "wikipedia").strip()
SEEDS = [int(s) for s in os.environ.get("SEEDS", "42,1,7").split(",") if s.strip()]
INCLUDE_K2K3 = os.environ.get("ARM_K2K3", "0").strip() in ("1", "true", "True")
EPOCHS = int(os.environ.get("EPOCHS", "20"))
HIDDEN = 128
BATCH = 500
LR = 1e-3

# Shared config-B publishable stack — IDENTICAL to _knob_ablation_3seed.py B_FIXED.
B_FIXED = dict(
    dataset=DATASET, epochs=EPOCHS, hidden=HIDDEN, batch_size=BATCH, lr=LR,
    fsm_arch="v3", fsm_decode="hier", decol_hier_v2=True,
    causal_batch=True, hier_causal_policy=True,
    lambda_edge_trans=0.5, p0_fix=False,
    edge_h_detach_scorepath=True,
)

ARMS = [
    ("B",      "(baseline detached, enable_main_predictor=False)",
        dict(design="correct_decoupled")),
    ("K1_e2e", "enable_main_predictor: False->True",
        dict(design="correct_decoupled", p0_fix=True)),
]
if INCLUDE_K2K3:
    ARMS.append(
        ("K2K3_gate", "lfg_mode=hard + compliance_floor=0.0 (hard causal gate)",
            dict(design="correct_decoupled", lfg_mode="hard", compliance_floor=0.0)))


def agg(vals):
    a = np.asarray([v for v in vals if v is not None and not np.isnan(v)], float)
    if a.size == 0:
        return float("nan"), float("nan"), 0
    sd = float(a.std(ddof=1)) if a.size > 1 else 0.0
    return float(a.mean()), sd, int(a.size)


def main():
    out_path = os.path.join(
        os.path.dirname(os.path.dirname(V33_DIR)),
        "results", f"v3_3_knob_ablation_{DATASET}_3seed.json")
    results = {"meta": {
        "task": "config-B knob-isolation ablation on STANDARD data (reviewer #2: "
                "mechanism not a CoEdit artifact)",
        "dataset": DATASET, "seeds": SEEDS, "epochs": EPOCHS,
        "hidden": HIDDEN, "batch": BATCH, "lr": LR,
        "include_K2K3": INCLUDE_K2K3,
        "protocol": "B-protocol: chrono 70/15/15, fair inductive neg, PRE-update "
                    "leak-free, sklearn AP",
        "B_fixed_stack": B_FIXED,
        "mechanism_claim": "Delta_ind = ind_ap(B) - ind_ap(K1_e2e) should be >>0 if "
                           "the enable_main_predictor=False inductive gain holds on "
                           "standard data (CoEdit 3-seed Delta_ind ~ +0.211).",
    }, "arms": []}

    t0 = time.time()
    for arm, knob_label, overrides in ARMS:
        kwargs = dict(B_FIXED); kwargs.update(overrides)
        ind_aps, trans_aps, ind_aucs, trans_aucs = [], [], [], []
        per_seed = []
        for s in SEEDS:
            print("=" * 78, flush=True)
            print(f"[{DATASET}] ARM {arm}  ({knob_label})  seed={s}  overrides={overrides}",
                  flush=True)
            ts = time.time()
            r = run_one(seed=s, **kwargs)
            dt = time.time() - ts
            ind_aps.append(r["ind_ap"]); trans_aps.append(r["trans_ap"])
            ind_aucs.append(r["ind_auc"]); trans_aucs.append(r["trans_auc"])
            per_seed.append({"seed": s, "ind_ap": r["ind_ap"],
                             "trans_ap": r["trans_ap"], "ind_auc": r["ind_auc"],
                             "trans_auc": r["trans_auc"], "time_s": dt,
                             "edge_state_dist": r["final_info"].get("edge_state_dist")})
            print(f"  -> ind_ap={r['ind_ap']:.4f}  trans_ap={r['trans_ap']:.4f}  "
                  f"ind_auc={r['ind_auc']:.4f}  ({dt:.0f}s)", flush=True)
        ind_m, ind_s, n = agg(ind_aps)
        tr_m, tr_s, _ = agg(trans_aps)
        ia_m, ia_s, _ = agg(ind_aucs)
        results["arms"].append({
            "arm": arm, "knob_flipped": knob_label, "overrides": overrides,
            "ind_ap_mean": ind_m, "ind_ap_std": ind_s, "n_seeds": n,
            "trans_ap_mean": tr_m, "trans_ap_std": tr_s,
            "ind_auc_mean": ia_m, "ind_auc_std": ia_s,
            "per_seed": per_seed,
        })
        # checkpoint after each arm so a timeout still leaves partial results
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)

    # ---- paired Delta_ind (B - K1) packed in ----
    by_arm = {a["arm"]: a for a in results["arms"]}
    B = by_arm.get("B"); K1 = by_arm.get("K1_e2e")
    if B and K1:
        # paired per-seed delta on the common seed set
        bseed = {p["seed"]: p["ind_ap"] for p in B["per_seed"]}
        kseed = {p["seed"]: p["ind_ap"] for p in K1["per_seed"]}
        common = sorted(set(bseed) & set(kseed))
        d = np.array([bseed[s] - kseed[s] for s in common], float)
        d = d[~np.isnan(d)]
        delta_mean = float(d.mean()) if d.size else float("nan")
        delta_std = float(d.std(ddof=1)) if d.size > 1 else 0.0
        results["meta"]["delta_ind_B_minus_K1"] = {
            "seeds": common,
            "per_seed": [round(float(bseed[s] - kseed[s]), 4) for s in common],
            "mean": delta_mean, "std": delta_std,
            "B_ind_ap_mean": B["ind_ap_mean"], "K1_ind_ap_mean": K1["ind_ap_mean"],
        }
        print("\n" + "=" * 90, flush=True)
        print(f"KNOB ABLATION — {DATASET}  ind_ap  seeds {SEEDS}  mean±std(ddof=1)",
              flush=True)
        print("-" * 90, flush=True)
        print(f"{'arm':<12} {'ind_ap':>16} {'trans_ap':>12}  knob", flush=True)
        for a in results["arms"]:
            print(f"{a['arm']:<12} {a['ind_ap_mean']:>8.4f}±{a['ind_ap_std']:<6.4f} "
                  f"{a['trans_ap_mean']:>12.4f}  {a['knob_flipped']}", flush=True)
        print("-" * 90, flush=True)
        print(f"Δind (B − K1_e2e) = {delta_mean:+.4f} ± {delta_std:.4f}  "
              f"per-seed={results['meta']['delta_ind_B_minus_K1']['per_seed']}", flush=True)
        verdict = ("MECHANISM HOLDS on " + DATASET) if delta_mean > 0.05 else \
                  ("MECHANISM WEAK/ABSENT on " + DATASET + " (honest finding)")
        print(f"VERDICT: {verdict}", flush=True)
        print("=" * 90, flush=True)

    results["meta"]["total_time_s"] = time.time() - t0
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
