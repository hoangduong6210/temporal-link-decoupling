"""
IDENTICAL-HEAD K1 DETACH PROBE — reviewer §8.2.i rebuttal (PM 2026-06-10).

WHY (reviewer): the existing B-vs-K1 contrast confounds TWO changes at once — K1
both (a) swaps the FSM existence decoder for a 2-layer MLP scoring head AND (b)
enables the link gradient to the backbone (enable_main_predictor=True). The reviewer
asks: hold the HEAD FIXED (same 2-layer MLP, same init per seed) and toggle ONLY the
stop-gradient, to isolate gradient-flow from head-architecture and rule out the
alternative "a coupled MLP merely destroys hand-crafted features".

DESIGN (single-bit contrast, head held IDENTICAL):
  Both arms set enable_main_predictor=True ⇒ the SAME self.main_predictor (a
  2-layer MLP: Linear(2H,H)->ReLU->Linear(H,1)) is the AP-scored head in BOTH arms.
  Because run_one reseeds (random/np/torch) per (seed) BEFORE building the model and
  the new flag adds NO module, the head's parameter init is BIT-IDENTICAL per seed
  across the two arms (CPU-verified: torch.equal over all head params == True).
  The ONLY difference is the single ``.detach()`` on the backbone→head input,
  controlled by main_predictor_detach (sr_gnn_v3_3.py forward, the main_pos/neg
  logit block):
    DETACHED-MLP : main_predictor_detach=True  → main_predictor(edge_h.detach())
                   ⇒ backbone (CSN/ECTG/DRGC) gets ZERO link-pred gradient. Should
                   behave like config-B if the inductive damage is the detach.
    COUPLED-MLP  : main_predictor_detach=False → main_predictor(edge_h)
                   ⇒ link-pred BCE flows into the backbone. == the prior K1 arm,
                   byte-identical, but with the head architecture now held identical
                   to DETACHED-MLP.
  CPU gradient probe (aux losses zeroed to isolate the link BCE): COUPLED feeds 20
  DRGC params nonzero link gradient; DETACHED feeds exactly 0. Single bit confirmed.

Everything else fixed at the config-B publishable stack (held IDENTICAL across arms):
  fsm_arch=v3, fsm_decode=hier, decol_hier_v2, causal_batch, hier_causal_policy,
  lambda_edge_trans=0.5, design=correct_decoupled. (design=correct_decoupled does NOT
  touch enable_main_predictor — verified sr_gnn_v3_3.py: the only reassignment of
  enable_main_predictor is inside the design=="correct" branch, NOT this one — so
  passing p0_fix=True keeps the MLP head as the scored head in both arms.)

DATASET: parameterized via argv[1] in {coedit, wikipedia}; seeds {42,1,7}; B-protocol
(chrono 70/15/15, fair inductive neg, PRE-update leak-free, sklearn AP). Reports
inductive + transductive AP per seed + mean±std(ddof=1) and Δ(DETACHED − COUPLED).

DECISIVE READ: if DETACHED-MLP ≫ COUPLED-MLP inductively (same direction + similar
magnitude as the existing B−K1 gap), the inductive damage is attributable to the
GRADIENT FLOW (the detach), NOT the head architecture.

Output JSON:
  experiments/results/identhead/identhead_K1_{coedit,wikipedia}_3seed.json
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

# Config-B publishable stack, held FIXED across BOTH arms. enable_main_predictor is
# forced ON in BOTH arms (p0_fix=True) so the SAME 2-layer MLP head scores both; the
# detach toggle (main_predictor_detach) is the SOLE difference.
def b_fixed(dataset):
    return dict(
        dataset=dataset, epochs=EPOCHS, hidden=HIDDEN, batch_size=BATCH, lr=LR,
        design="correct_decoupled",
        fsm_arch="v3", fsm_decode="hier", decol_hier_v2=True,
        causal_batch=True, hier_causal_policy=True,
        lambda_edge_trans=0.5,
        p0_fix=True,                       # MLP main_predictor IS the scored head (both arms)
        edge_h_detach_scorepath=True,      # FSM-score path detach untouched (interp-only)
    )

# Arm label + the ONE kwarg that differs (main_predictor_detach).
ARMS = [
    ("DETACHED-MLP", "main_predictor(edge_h.detach()) — zero backbone link grad",
        dict(main_predictor_detach=True)),
    ("COUPLED-MLP",  "main_predictor(edge_h) — link grad flows to backbone (== K1)",
        dict(main_predictor_detach=False)),
]


def agg(vals):
    a = np.asarray([v for v in vals if v is not None and not np.isnan(v)], float)
    if a.size == 0:
        return float("nan"), float("nan"), 0
    sd = float(a.std(ddof=1)) if a.size > 1 else 0.0
    return float(a.mean()), sd, int(a.size)


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("coedit", "wikipedia"):
        print("usage: python _identhead_K1_3seed.py {coedit|wikipedia}", flush=True)
        sys.exit(2)
    dataset = sys.argv[1]

    out_dir = os.path.join(os.path.dirname(os.path.dirname(V33_DIR)),
                           "results", "identhead")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"identhead_K1_{dataset}_3seed.json")

    B = b_fixed(dataset)
    results = {"meta": {
        "task": "IDENTICAL-HEAD K1 detach probe (reviewer §8.2.i): same 2-layer MLP "
                "scoring head, identical init per seed; toggle ONLY the backbone→head "
                ".detach() (main_predictor_detach).",
        "dataset": dataset, "seeds": SEEDS, "epochs": EPOCHS,
        "hidden": HIDDEN, "batch": BATCH, "lr": LR,
        "protocol": "B-protocol: chrono 70/15/15, fair inductive neg, PRE-update "
                    "leak-free, sklearn AP",
        "B_fixed_stack": {k: v for k, v in B.items()},
        "head_held_identical": "both arms enable_main_predictor=True ⇒ same "
                               "self.main_predictor (Linear(2H,H)->ReLU->Linear(H,1)); "
                               "run_one reseeds per seed before build and the toggle "
                               "adds no module ⇒ bit-identical head init per seed "
                               "(CPU-verified torch.equal over head params).",
        "single_bit": "main_predictor_detach: True=DETACHED-MLP (zero backbone link "
                      "grad), False=COUPLED-MLP (link grad flows). CPU grad probe "
                      "(aux losses zeroed): COUPLED 20 DRGC params w/ link grad, "
                      "DETACHED 0.",
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
                             "edge_state_dist": r["final_info"].get("edge_state_dist")})
            print(f"  -> ind_ap={r['ind_ap']:.4f}  trans_ap={r['trans_ap']:.4f}  "
                  f"({dt:.0f}s)", flush=True)
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

    # Decisive delta: DETACHED − COUPLED (inductive + transductive).
    if "DETACHED-MLP" in arm_means and "COUPLED-MLP" in arm_means:
        d_ind = arm_means["DETACHED-MLP"]["ind_ap"] - arm_means["COUPLED-MLP"]["ind_ap"]
        d_tr = arm_means["DETACHED-MLP"]["trans_ap"] - arm_means["COUPLED-MLP"]["trans_ap"]
        results["delta_detached_minus_coupled"] = {
            "ind_ap": d_ind, "trans_ap": d_tr,
            "interpretation": "ind_ap > 0 (same direction + similar magnitude as the "
                              "existing B-K1 gap) ⇒ inductive damage is the GRADIENT "
                              "FLOW (detach), NOT the head architecture.",
        }
        print("\n" + "=" * 90, flush=True)
        print(f"IDENTICAL-HEAD K1 — {dataset}, 3 seeds {SEEDS} mean±std(ddof=1)",
              flush=True)
        print("-" * 90, flush=True)
        for a in results["arms"]:
            print(f"{a['arm']:<14} ind_ap={a['ind_ap_mean']:.4f}±{a['ind_ap_std']:.4f}"
                  f"  trans_ap={a['trans_ap_mean']:.4f}±{a['trans_ap_std']:.4f}",
                  flush=True)
        print(f"Δ(DETACHED−COUPLED)  ind_ap={d_ind:+.4f}  trans_ap={d_tr:+.4f}",
              flush=True)
        print("=" * 90, flush=True)

    results["meta"]["total_time_s"] = time.time() - t0
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote {out_path}", flush=True)


if __name__ == "__main__":
    main()
