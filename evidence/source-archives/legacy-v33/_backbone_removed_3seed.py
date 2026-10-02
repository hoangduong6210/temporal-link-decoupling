"""
DETERMINISTIC-ONLY BACKBONE — reviewer Q4 / caveat-(2) rebuttal (PM 2026-06-11).

WHY (reviewer): characterize what the KL-trained LEARNABLE backbone actually
contributes. The reviewer's alternative reading is that the hand-crafted point-process
features carry most of the inductive AP and the learnable CSN/DRGC adds little. We test
this directly: remove the learnable backbone ENTIRELY and let the SAME detached config-B
scoring head consume ONLY the deterministic point-process channels.

DESIGN (single axis vs config B — determ_only_backbone — everything else held):
  FULL-B (reference): the normal config-B model. Learnable ResidualCSN event encoder +
    DRGC_v2 coupled-GRU node-memory + deterministic point-process stats; detached
    existence_decoder is the AP-scored head (enable_main_predictor=False).
  DETERM-ONLY: the learnable backbone is REMOVED from the score path and frozen at init:
    (1) CSN bypassed  → feat_g = raw feat, salience sal = 0 (no learned event encoder).
    (2) DRGC bypassed → node memory passes through unchanged (no coupled-GRU update);
        the backbone-derived edge_h fed to the FSM scoring head (state_observer /
        transition_predictor, BOTH pos and neg) is ZEROED → the scored next-state
        distribution depends on NO learnable-backbone content, only on the deterministic
        pair_phi (Hawkes λ, Welford μ/var/n, recurrence/rate EWMA, staleness, ever_alive)
        + the lifecycle mask/gate.
    (3) csn/ectg/drgc parameters frozen at init (requires_grad=False) ⇒ ZERO trainable
        backbone params; lambda_echo*kl trains nothing (kl=0 in this arm).
  The detached FSM head (state_observer/transition_predictor/lifecycle_mask/
  existence_decoder/hier gate heads) is UNCHANGED across arms — it is the config-B
  scoring head, NOT the "learnable backbone" being ablated. So the SOLE axis toggled is
  learnable-CSN+DRGC vs deterministic-only.

HONEST CAVEAT (flagged to PM): "deterministic-only" is clean for the parts the reviewer
named (CSN event encoder + DRGC node-memory: zero trainable params, zero score-path
signal). It is NOT perfectly parameter-free overall, because the SAME detached FSM head
that config B uses still has trainable params and must by signature receive a 2H edge_h
tensor — we feed it a constant ZERO (no backbone info, no gradient) rather than deleting
it, so the head reads the deterministic pair_phi exactly as in config B. This is the
faithful "remove the learnable backbone, keep config-B's detached head" cut.

Everything else fixed at the config-B publishable stack (held IDENTICAL across arms):
  design=correct_decoupled, fsm_arch=v3, fsm_decode=hier, decol_hier_v2, causal_batch,
  hier_causal_policy, lambda_edge_trans=0.5, p0_fix=False (detached existence_decoder
  is the AP-scored head).

DATASET: parameterized via argv[1] in {coedit, wikipedia}; seeds {42,1,7}; B-protocol
(chrono 70/15/15, fair inductive neg, PRE-update leak-free, sklearn AP). Reports
inductive + transductive AP per seed + mean±std(ddof=1) and Δ(FULL-B − DETERM-ONLY).

DECISIVE READ (honest either way):
  DETERM-ONLY ≈ FULL-B inductively ⇒ the hand-crafted point-process features carry most
    of it; the KL-trained learnable backbone adds little (partially supports the
    reviewer's alternative reading — report plainly).
  DETERM-ONLY ≪ FULL-B inductively ⇒ the KL-trained learnable backbone is doing real
    work. Both outcomes are a publishable characterization.

Output JSON:
  experiments/results/backbone_removed/backbone_removed_{coedit,wikipedia}_3seed.json
"""
import os, sys, json, time
import numpy as np

V33_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, V33_DIR)
from run_v3_3_benchmark import run_one  # noqa: E402

SEEDS = [42, 1, 7]
EPOCHS = 20
HIDDEN = 128
BATCH = 500
LR = 1e-3

# Config-B publishable stack, held FIXED across BOTH arms. p0_fix=False ⇒ the detached
# existence_decoder is the AP-scored head (config B). The determ_only_backbone toggle is
# the SOLE difference between the two arms.
def b_fixed(dataset):
    return dict(
        dataset=dataset, epochs=EPOCHS, hidden=HIDDEN, batch_size=BATCH, lr=LR,
        design="correct_decoupled",
        fsm_arch="v3", fsm_decode="hier", decol_hier_v2=True,
        causal_batch=True, hier_causal_policy=True,
        lambda_edge_trans=0.5,
        p0_fix=False,                      # detached existence_decoder IS the scored head
        edge_h_detach_scorepath=True,      # canonical config-B detach (interp-only path)
    )

# Arm label + the ONE kwarg that differs (determ_only_backbone).
ARMS = [
    ("FULL-B", "learnable CSN+DRGC + deterministic stats + detached head (config B)",
        dict(determ_only_backbone=False)),
    ("DETERM-ONLY", "learnable CSN+DRGC removed/frozen; detached head reads only "
                    "deterministic point-process channels (pair_phi)",
        dict(determ_only_backbone=True)),
]


def agg(vals):
    a = np.asarray([v for v in vals if v is not None and not np.isnan(v)], float)
    if a.size == 0:
        return float("nan"), float("nan"), 0
    sd = float(a.std(ddof=1)) if a.size > 1 else 0.0
    return float(a.mean()), sd, int(a.size)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("coedit", "wikipedia"):
        print("usage: python _backbone_removed_3seed.py {coedit|wikipedia}", flush=True)
        sys.exit(2)
    dataset = sys.argv[1]

    out_dir = os.path.join(os.path.dirname(os.path.dirname(V33_DIR)),
                           "results", "backbone_removed")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"backbone_removed_{dataset}_3seed.json")

    B = b_fixed(dataset)
    results = {"meta": {
        "task": "DETERMINISTIC-ONLY BACKBONE (reviewer Q4/caveat-2): remove the "
                "learnable CSN event encoder + DRGC coupled-GRU node-memory, keep "
                "config-B's detached scoring head reading only deterministic "
                "point-process channels. Toggle ONLY determ_only_backbone.",
        "dataset": dataset, "seeds": SEEDS, "epochs": EPOCHS,
        "hidden": HIDDEN, "batch": BATCH, "lr": LR,
        "protocol": "B-protocol: chrono 70/15/15, fair inductive neg, PRE-update "
                    "leak-free, sklearn AP",
        "B_fixed_stack": {k: v for k, v in B.items()},
        "determ_only_mechanism": "CSN bypassed (feat_g=feat, sal=0); DRGC bypassed "
                                 "(node mem unchanged, edge_h to FSM head zeroed for "
                                 "pos+neg); csn/ectg/drgc frozen at init "
                                 "(requires_grad=False) ⇒ zero trainable backbone "
                                 "params, kl=0. Scored head reads only pair_phi "
                                 "(Hawkes/Welford/recurrence/staleness/ever_alive).",
        "honest_caveat": "the detached FSM head (config B's head) keeps trainable "
                         "params and is fed a constant zero edge_h (no backbone info/"
                         "grad) rather than deleted; so DETERM-ONLY is parameter-free "
                         "in the CSN/DRGC backbone only, not globally. n_backbone_"
                         "params_frozen is recorded per run.",
    }, "arms": []}

    t0 = time.time()
    arm_means = {}
    for arm, desc, overrides in ARMS:
        kwargs = dict(B)
        kwargs.update(overrides)
        ind_aps, trans_aps, ind_aucs, trans_aucs = [], [], [], []
        per_seed = []
        for s in SEEDS:
            print("=" * 78, flush=True)
            print(f"ARM {arm}  ({desc})  dataset={dataset}  seed={s}  "
                  f"overrides={overrides}", flush=True)
            ts = time.time()
            r = run_one(seed=s, **kwargs)
            dt = time.time() - ts
            ind_aps.append(r["ind_ap"]); trans_aps.append(r["trans_ap"])
            ind_aucs.append(r["ind_auc"]); trans_aucs.append(r["trans_auc"])
            per_seed.append({"seed": s, "ind_ap": r["ind_ap"],
                             "trans_ap": r["trans_ap"], "ind_auc": r["ind_auc"],
                             "trans_auc": r["trans_auc"], "time_s": dt,
                             "determ_only_backbone": r.get("determ_only_backbone"),
                             "n_backbone_params_frozen": r.get("n_backbone_params_frozen"),
                             "edge_state_dist": r["final_info"].get("edge_state_dist")})
            print(f"  -> ind_ap={r['ind_ap']:.4f}  trans_ap={r['trans_ap']:.4f}  "
                  f"frozen_bb={r.get('n_backbone_params_frozen')}  ({dt:.0f}s)",
                  flush=True)
        ind_m, ind_s, n = agg(ind_aps)
        tr_m, tr_s, _ = agg(trans_aps)
        ia_m, ia_s, _ = agg(ind_aucs)
        ta_m, ta_s, _ = agg(trans_aucs)
        arm_means[arm] = {"ind_ap": ind_m, "trans_ap": tr_m}
        results["arms"].append({
            "arm": arm, "desc": desc, "overrides": overrides,
            "ind_ap_mean": ind_m, "ind_ap_std": ind_s, "n_seeds": n,
            "trans_ap_mean": tr_m, "trans_ap_std": tr_s,
            "ind_auc_mean": ia_m, "ind_auc_std": ia_s,
            "trans_auc_mean": ta_m, "trans_auc_std": ta_s,
            "per_seed": per_seed,
        })
        with open(out_path, "w") as f:
            json.dump(results, f, indent=2)

    # Decisive delta: FULL-B − DETERM-ONLY (inductive + transductive).
    if "FULL-B" in arm_means and "DETERM-ONLY" in arm_means:
        d_ind = arm_means["FULL-B"]["ind_ap"] - arm_means["DETERM-ONLY"]["ind_ap"]
        d_tr = arm_means["FULL-B"]["trans_ap"] - arm_means["DETERM-ONLY"]["trans_ap"]
        results["delta_fullB_minus_determonly"] = {
            "ind_ap": d_ind, "trans_ap": d_tr,
            "interpretation": "ind_ap ≈ 0 ⇒ hand-crafted point-process features carry "
                              "most of it, learnable backbone adds little (supports "
                              "reviewer's alternative reading). ind_ap ≫ 0 ⇒ the "
                              "KL-trained learnable backbone is doing real work.",
        }
        print("\n" + "=" * 90, flush=True)
        print(f"DETERM-ONLY BACKBONE — {dataset}, 3 seeds {SEEDS} mean±std(ddof=1)",
              flush=True)
        print("-" * 90, flush=True)
        for a in results["arms"]:
            print(f"{a['arm']:<14} ind_ap={a['ind_ap_mean']:.4f}±{a['ind_ap_std']:.4f}"
                  f"  trans_ap={a['trans_ap_mean']:.4f}±{a['trans_ap_std']:.4f}",
                  flush=True)
        print(f"Δ(FULL-B−DETERM-ONLY)  ind_ap={d_ind:+.4f}  trans_ap={d_tr:+.4f}",
              flush=True)
        print("=" * 90, flush=True)

    results["meta"]["total_time_s"] = time.time() - t0
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
