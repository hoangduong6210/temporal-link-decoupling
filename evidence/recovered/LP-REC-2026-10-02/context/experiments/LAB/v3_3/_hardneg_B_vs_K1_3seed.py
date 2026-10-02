"""
HARD-NEGATIVE ROBUSTNESS of the decoupling effect — reviewer P1 ask (b).

QUESTION (paper-decisive): does B > K1 (decoupling wins; the SAME single-flag contrast
as Table 3) STILL HOLD under HARD negatives, or does the ordering shrink/invert?

CONTRAST (identical to Table 3 / _knob_ablation_3seed.py):
  B    : config-B publishable v3 stack, design=correct_decoupled, p0_fix=False
         (enable_main_predictor=False -> detached scoring head)
  K1   : EXACT same stack, p0_fix=True  (enable_main_predictor=True -> e2e head
         trains the backbone). This is the ONE knob isolated from design=correct.
Every other knob is held fixed and equal across the two arms.

NEGATIVES (Poursafaei et al. 2022, "Towards Better Evaluation for Dynamic Link
Prediction", NeurIPS). Each trained model is evaluated inductively under THREE
negative-sampling strategies on the SAME model + SAME warmup state:
  random      : the existing fair pool-matched random NS (Table-3 reference).
  historical  : neg dst drawn from the pool of destinations SEEN in TRAIN but absent
                at the current eval step (a plausible past partner).
  inductive   : neg dst drawn from the destinations of TEST-PHASE-ONLY edges — (src,dst)
                pairs observed during test but NEVER present in train (Poursafaei
                CORRECT def; about test-phase edges, NOT unseen nodes). The prior buggy
                def restricted the TRAIN-dst pool to unseen nodes, which is empty by
                construction and degenerated (gave a trivial 1.000); this is the v2 fix.

PAIRING: run_one resets np.random to a fixed hardneg_eval_seed immediately before each
strategy's eval, so for a given (dataset, data-seed, strategy) BOTH B and K1 are scored
on bit-identical negative sets. This makes the B-vs-K1 delta a paired comparison.

INTEGRITY: every number written here comes from an actual run_one() call. No fabricated
values. Output JSON (mean +/- std, ddof=1):
  experiments/results/hardneg/hardneg_B_vs_K1_<dataset>_3seed_v2.json
(v2 = corrected inductive-NS pool; historical+random must reproduce the prior run since
the eval RNG is fixed — that doubles as a validation.)
"""
import os, sys, json, time, argparse
import numpy as np

V33_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, V33_DIR)
from run_v3_3_benchmark import run_one  # noqa: E402

SEEDS = [42, 1, 7]
HIDDEN = 128
BATCH = 500
LR = 1e-3

# config-B publishable stack, held FIXED across B and K1 (mirrors _knob_ablation).
B_FIXED = dict(
    epochs=20, hidden=HIDDEN, batch_size=BATCH, lr=LR,
    fsm_arch="v3", fsm_decode="hier", decol_hier_v2=True,
    causal_batch=True, hier_causal_policy=True,
    lambda_edge_trans=0.5,
    edge_h_detach_scorepath=True,
    hardneg_eval=True,            # <- turns on the three-strategy inductive eval
)

ARMS = [
    ("B",       dict(design="correct_decoupled", p0_fix=False)),
    ("K1_e2e",  dict(design="correct_decoupled", p0_fix=True)),
]

STRATS = [
    ("random",     "ind_ap",         "ind_auc"),
    ("historical", "ind_ap_histneg", "ind_auc_histneg"),
    ("inductive",  "ind_ap_indneg",  "ind_auc_indneg"),
]


def agg(vals):
    a = np.asarray([v for v in vals if v is not None and not np.isnan(v)], float)
    if a.size == 0:
        return float("nan"), float("nan"), 0
    sd = float(a.std(ddof=1)) if a.size > 1 else 0.0
    return float(a.mean()), sd, int(a.size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)   # wikipedia | coedit
    ap.add_argument("--epochs", type=int, default=20)
    args = ap.parse_args()
    dataset = args.dataset

    fixed = dict(B_FIXED); fixed["epochs"] = args.epochs

    out_dir = os.path.join(
        os.path.dirname(os.path.dirname(V33_DIR)), "results", "hardneg")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"hardneg_B_vs_K1_{dataset}_3seed_v2.json")

    results = {"meta": {
        "task": "P1(b): decoupling robustness under hard negatives (B vs K1, "
                "the single enable_main_predictor flag, same contrast as Table 3)",
        "ref": "Poursafaei et al. 2022 NeurIPS — historical + inductive NS",
        "dataset": dataset, "seeds": SEEDS, "epochs": args.epochs,
        "hidden": HIDDEN, "batch": BATCH, "lr": LR,
        "protocol": "B-protocol chrono 70/15/15, PRE-update leak-free, sklearn AP; "
                    "inductive eval re-run per strategy on the SAME trained model; "
                    "fixed hardneg_eval_seed -> B and K1 share identical neg sets (paired)",
        "B_fixed_stack": fixed,
        "strategies": [s[0] for s in STRATS],
    }, "arms": []}

    t0 = time.time()
    per_arm = {}
    for arm, overrides in ARMS:
        kwargs = dict(fixed); kwargs.update(overrides)
        per_seed = []
        strat_vals = {s[0]: {"ap": [], "auc": []} for s in STRATS}
        indpool_from_train = None
        n_indneg_pool_by_seed = {}
        for s in SEEDS:
            print("=" * 78, flush=True)
            print(f"ARM {arm}  dataset={dataset}  seed={s}  overrides={overrides}",
                  flush=True)
            ts = time.time()
            r = run_one(dataset=dataset, seed=s, **kwargs)
            dt = time.time() - ts
            indpool_from_train = r.get("hardneg_indpool_from_train")
            n_indneg_pool_by_seed[s] = r.get("hardneg_n_indneg_pool")
            row = {"seed": s, "time_s": dt,
                   "n_indneg_pool": r.get("hardneg_n_indneg_pool"),
                   "trans_ap": r["trans_ap"], "trans_auc": r["trans_auc"]}
            for strat, apk, auck in STRATS:
                row[apk] = r[apk]; row[auck] = r[auck]
                strat_vals[strat]["ap"].append(r[apk])
                strat_vals[strat]["auc"].append(r[auck])
            per_seed.append(row)
            print(f"  -> random ind_ap={r['ind_ap']:.4f}  "
                  f"hist ind_ap={r['ind_ap_histneg']:.4f}  "
                  f"indneg ind_ap={r['ind_ap_indneg']:.4f}  ({dt:.0f}s)", flush=True)
        # honest degeneracy flag: pool is small if any seed's test-only pool < 50.
        _pool_sizes = [v for v in n_indneg_pool_by_seed.values() if v is not None]
        _min_pool = min(_pool_sizes) if _pool_sizes else None
        arm_rec = {"arm": arm, "overrides": overrides,
                   "indpool_from_train": indpool_from_train,
                   "n_indneg_pool_by_seed": n_indneg_pool_by_seed,
                   "n_indneg_pool_min": _min_pool,
                   "indneg_pool_small_flag": (_min_pool is not None and _min_pool < 50),
                   "per_seed": per_seed, "by_strategy": {}}
        for strat, _, _ in STRATS:
            apm, aps, n = agg(strat_vals[strat]["ap"])
            aum, aus, _ = agg(strat_vals[strat]["auc"])
            arm_rec["by_strategy"][strat] = {
                "ind_ap_mean": apm, "ind_ap_std": aps, "n_seeds": n,
                "ind_auc_mean": aum, "ind_auc_std": aus}
        results["arms"].append(arm_rec)
        per_arm[arm] = arm_rec
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)

    # delta table B - K1 per strategy
    deltas = {}
    if "B" in per_arm and "K1_e2e" in per_arm:
        for strat, _, _ in STRATS:
            b = per_arm["B"]["by_strategy"][strat]["ind_ap_mean"]
            k = per_arm["K1_e2e"]["by_strategy"][strat]["ind_ap_mean"]
            deltas[strat] = {"B": b, "K1": k, "delta_B_minus_K1": b - k}
    results["meta"]["delta_B_minus_K1_by_strategy"] = deltas
    results["meta"]["total_time_s"] = time.time() - t0
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 84, flush=True)
    print(f"P1(b) HARD-NEG  {dataset}  B vs K1  ind_ap  3 seeds {SEEDS} mean+/-std",
          flush=True)
    print("-" * 84, flush=True)
    print(f"{'strategy':<12} {'B':>16} {'K1':>16} {'Δ(B-K1)':>12}  holds?", flush=True)
    for strat, _, _ in STRATS:
        b = per_arm["B"]["by_strategy"][strat]
        k = per_arm["K1_e2e"]["by_strategy"][strat]
        d = b["ind_ap_mean"] - k["ind_ap_mean"]
        holds = "YES" if d > 0 else "NO/INVERT"
        print(f"{strat:<12} {b['ind_ap_mean']:>8.4f}±{b['ind_ap_std']:<6.4f} "
              f"{k['ind_ap_mean']:>8.4f}±{k['ind_ap_std']:<6.4f} {d:>+12.4f}  {holds}",
              flush=True)
    print("=" * 84, flush=True)
    print(f"\nwrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
