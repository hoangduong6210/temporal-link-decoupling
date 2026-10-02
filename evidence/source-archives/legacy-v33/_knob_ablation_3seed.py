"""
KNOB-ISOLATION ABLATION — config-B (correct_decoupled) base, flip ONE knob toward
config-C (design=correct) at a time, on CoEdit, 3 seeds (42,1,7).

WHY (reviewer #1, PM directive 2026-06-08): the old "+22.1pp inductive" claim
(config-B 0.9885 vs config-C 0.7672) is CONFOUNDED — it flips the WHOLE `design`
preset string `correct_decoupled` -> `correct` at once. The single-variable detach
probe (job 5516013) already showed the detach bit alone is only +0.94pp.

PRESET DIFF (verified from sr_gnn_v3_3.py L632-697 + ctor defaults + the fsm_arch=v3
self-enable block L757-787): WITH the publishable v3 stack held fixed
(fsm_arch=v3, fsm_decode=hier, decol_hier_v2, causal_batch, hier_causal_policy,
lambda_edge_trans=0.5), the ONLY internal knobs that `design=correct` changes
relative to `design=correct_decoupled` are THREE:
   K1 enable_main_predictor : False (detached) -> True  (e2e head trains backbone)
   K2 lfg_mode              : "soft"           -> "hard"
   K3 compliance_floor      : 0.05             -> 0.0   (full hard gate)
(entropy_reg_weight, fix_existence_init, use_trans_loss, and the v3 decol stack are
IDENTICAL in both branches because fsm_arch=v3 forces them, independent of `design`.)

All three are ALREADY CLI/ctor-exposed; NO model code change is needed. Each arm
flips exactly ONE of {K1,K2,K3} from B's value to C's value; every other knob == B.
We also include the FULL C (all three flipped) as the confounded reference and
re-derive that it reproduces the ~0.767 number (sanity, not a new claim).

Arm matrix (base = config-B):
  B           : design=correct_decoupled (baseline)
  K1_e2e      : B + enable_main_predictor=True            (--p0_fix on)
  K2_lfg_hard : B + lfg_mode=hard         (floor stays 0.05)
  K3_floor0   : B + compliance_floor=0.0  (lfg_mode stays soft -> NO-OP: hard gate
                only fires when lfg_mode==hard; included to PROVE floor alone is inert)
  K2K3_gate   : B + lfg_mode=hard + compliance_floor=0.0  (the real hard causal gate)
  C_correct   : design=correct (all of K1+K2+K3) — confounded reference

ind_ap aggregated mean +/- std(ddof=1). Output JSON:
  experiments/results/v3_3_coedit_knob_ablation_3seed.json
"""
import os, sys, json, time
import numpy as np

V33_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, V33_DIR)
from run_v3_3_benchmark import run_one  # noqa: E402

SEEDS = [42, 1, 7]
DATASET = "coedit"
EPOCHS = 20
HIDDEN = 128
BATCH = 500
LR = 1e-3

# Shared config-B publishable stack (held FIXED across every arm).
# NB: run_one defaults p0_fix=True (enable_main_predictor); config-B requires it OFF
# (detached head). We pin p0_fix=False here and let arm K1 / design=correct flip it.
B_FIXED = dict(
    dataset=DATASET, epochs=EPOCHS, hidden=HIDDEN, batch_size=BATCH, lr=LR,
    fsm_arch="v3", fsm_decode="hier", decol_hier_v2=True,
    causal_batch=True, hier_causal_policy=True,
    lambda_edge_trans=0.5, p0_fix=False,
    # detach stays at its canonical default (True) for every arm except K1 (where the
    # e2e main head is what un-detaches the backbone, exactly as design=correct does).
    edge_h_detach_scorepath=True,
)

# Each arm: knob_flipped label + the kwargs that DIFFER from B (merged onto B_FIXED).
ARMS = [
    ("B",           "(baseline, none)",
        dict(design="correct_decoupled")),
    ("K1_e2e",      "enable_main_predictor: False->True",
        dict(design="correct_decoupled", p0_fix=True)),
    ("K2_lfg_hard", "lfg_mode: soft->hard (floor=0.05)",
        dict(design="correct_decoupled", lfg_mode="hard")),
    ("K3_floor0",   "compliance_floor: 0.05->0.0 (lfg soft; inert control)",
        dict(design="correct_decoupled", compliance_floor=0.0)),
    ("K2K3_gate",   "lfg_mode=hard + compliance_floor=0.0 (hard causal gate)",
        dict(design="correct_decoupled", lfg_mode="hard", compliance_floor=0.0)),
    ("C_correct",   "design=correct (K1+K2+K3 confounded ref)",
        dict(design="correct")),
]


def agg(vals):
    a = np.asarray([v for v in vals if v is not None and not np.isnan(v)], float)
    if a.size == 0:
        return float("nan"), float("nan"), 0
    sd = float(a.std(ddof=1)) if a.size > 1 else 0.0
    return float(a.mean()), sd, int(a.size)


def main():
    out_path = os.path.join(
        os.path.dirname(os.path.dirname(V33_DIR)),
        "results", "v3_3_coedit_knob_ablation_3seed.json")
    results = {"meta": {
        "task": "config-B knob-isolation ablation (reviewer #1 confound decomposition)",
        "dataset": DATASET, "seeds": SEEDS, "epochs": EPOCHS,
        "hidden": HIDDEN, "batch": BATCH, "lr": LR,
        "protocol": "B-protocol: chrono 70/15/15, fair inductive neg, PRE-update "
                    "leak-free, sklearn AP",
        "B_fixed_stack": B_FIXED,
        "preset_diff_note": "with fsm_arch=v3 stack fixed, design=correct vs "
                            "correct_decoupled differ ONLY in K1 enable_main_predictor, "
                            "K2 lfg_mode, K3 compliance_floor",
    }, "arms": []}

    t0 = time.time()
    for arm, knob_label, overrides in ARMS:
        kwargs = dict(B_FIXED)
        kwargs.update(overrides)
        ind_aps, trans_aps, ind_aucs = [], [], []
        per_seed = []
        for s in SEEDS:
            print("=" * 78, flush=True)
            print(f"ARM {arm}  ({knob_label})  seed={s}  overrides={overrides}",
                  flush=True)
            ts = time.time()
            r = run_one(seed=s, **kwargs)
            dt = time.time() - ts
            ind_aps.append(r["ind_ap"]); trans_aps.append(r["trans_ap"])
            ind_aucs.append(r["ind_auc"])
            per_seed.append({"seed": s, "ind_ap": r["ind_ap"],
                             "trans_ap": r["trans_ap"], "ind_auc": r["ind_auc"],
                             "trans_auc": r["trans_auc"], "time_s": dt,
                             "edge_state_dist": r["final_info"].get("edge_state_dist")})
            print(f"  -> ind_ap={r['ind_ap']:.4f}  trans_ap={r['trans_ap']:.4f}  "
                  f"({dt:.0f}s)", flush=True)
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

    # inline table, sorted by Delta(ind_ap) vs B
    base = next(a for a in results["arms"] if a["arm"] == "B")
    base_ind = base["ind_ap_mean"]
    rows = []
    for a in results["arms"]:
        rows.append((a["arm"], a["knob_flipped"], a["ind_ap_mean"], a["ind_ap_std"],
                     a["trans_ap_mean"], a["ind_ap_mean"] - base_ind))
    rows_sorted = sorted(rows, key=lambda x: x[5])  # most-negative Delta first
    print("\n" + "=" * 90, flush=True)
    print(f"KNOB ABLATION — CoEdit ind_ap, base=B ({base_ind:.4f}), "
          f"3 seeds {SEEDS} mean+/-std(ddof=1)", flush=True)
    print("-" * 90, flush=True)
    print(f"{'arm':<12} {'ind_ap':>16} {'trans_ap':>10} {'Δind vs B':>12}  knob", flush=True)
    for arm, knob, im, isd, tm, d in rows_sorted:
        print(f"{arm:<12} {im:>8.4f}±{isd:<6.4f} {tm:>10.4f} {d:>+12.4f}  {knob}",
              flush=True)
    print("=" * 90, flush=True)
    results["meta"]["total_time_s"] = time.time() - t0
    results["meta"]["base_ind_ap_mean"] = base_ind
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
