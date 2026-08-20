"""
Aggregate the 3-arm freeze-then-probe control (control protocol) into ONE file with the
verdict. Reads the per-arm runner JSONs produced by run_v3_3_benchmark.py and emits

    experiments/results/v3_3_frozen_probe_control_3seed.json

ARMS
  arm1_decoupling : SR-GNN decoupling-by-construction (config-B; backbone NEVER sees
                    link-pred grad).  --design correct_decoupled --p0_fix off
                    --fsm_arch v3 --fsm_decode hier --decol_hier_v2 --causal_batch
                    --hier_causal_policy --lambda_edge_trans 0.5
  arm2_ftp        : Freeze-then-probe — pretrain e2e (backbone shaped by link-pred),
                    FREEZE backbone, train a fresh link head, measure inductive AP.
                    SAME backbone stack + --frozen_probe.
  arm3_frozen_tgat: (optional) frozen standard TGAT/TGN + probe head — only if its
                    arm JSON is present; otherwise skipped.

Per (arm, dataset): ind/trans AP reported as mean +/- SAMPLE std (ddof=1, n-1).

SUMMARY (control protocol): per dataset compute Δ_ind = arm1.ind_mean - arm2.ind_mean.
  Δ_ind  >  +1.0pp on both datasets  -> "DECOUPLING-DISTINCT": decoupling-by-
      construction beats freeze-then-probe -> measured novelty, mechanism is real.
  |Δ_ind| <= 1.0pp                    -> "DECOUPLING == FtP": the inductive gain is
      the classic linear-probing-transfer effect relocated to temporal graphs ->
      novelty must be rescoped (report honestly, do NOT force #1 to win).
  Δ_ind  <  -1.0pp                    -> "FtP WINS": freeze-then-probe is better;
      decoupling-by-construction is not the source of the inductive edge.
The threshold (1.0pp) is a reporting cutoff; the raw Δ +/- pooled std is always emitted.
"""
import os, sys, json, argparse
import numpy as np

THRESH_PP = 1.0  # reporting cutoff (percentage points) for the verdict label


def _load_runs(path):
    if path is None or not os.path.exists(path):
        return []
    with open(path) as f:
        d = json.load(f)
    return d.get("runs", d if isinstance(d, list) else [])


def _stat(vals):
    vals = [v for v in vals if v is not None and not (isinstance(v, float) and np.isnan(v))]
    if not vals:
        return {"mean": float("nan"), "std": float("nan"), "n": 0, "seeds": []}
    a = np.asarray(vals, dtype=np.float64)
    std = float(a.std(ddof=1)) if len(a) > 1 else 0.0   # SAMPLE std, n-1
    return {"mean": float(a.mean()), "std": std, "n": int(len(a))}


def _per_ds(runs):
    out = {}
    for r in runs:
        ds = r["dataset"]
        out.setdefault(ds, {"ind": [], "trans": [], "seeds": []})
        out[ds]["ind"].append(r.get("ind_ap"))
        out[ds]["trans"].append(r.get("trans_ap"))
        out[ds]["seeds"].append(r.get("seed"))
    agg = {}
    for ds, v in out.items():
        agg[ds] = {
            "ind_ap": {**_stat(v["ind"]), "seeds": v["seeds"],
                       "per_seed": v["ind"]},
            "trans_ap": {**_stat(v["trans"]), "per_seed": v["trans"]},
        }
    return agg


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--arm1", required=True, help="decoupling (config-B) runner JSON")
    p.add_argument("--arm2", required=True, help="freeze-then-probe runner JSON")
    p.add_argument("--arm3", default=None, help="(optional) frozen TGAT/TGN runner JSON")
    p.add_argument("--out", required=True)
    a = p.parse_args()

    arms = {
        "arm1_decoupling": _per_ds(_load_runs(a.arm1)),
        "arm2_ftp":        _per_ds(_load_runs(a.arm2)),
    }
    if a.arm3:
        arm3 = _per_ds(_load_runs(a.arm3))
        if arm3:
            arms["arm3_frozen_tgat"] = arm3

    datasets = sorted(set(arms["arm1_decoupling"]) | set(arms["arm2_ftp"]))

    verdict = {}
    for ds in datasets:
        d1 = arms["arm1_decoupling"].get(ds, {}).get("ind_ap")
        d2 = arms["arm2_ftp"].get(ds, {}).get("ind_ap")
        if not d1 or not d2 or np.isnan(d1["mean"]) or np.isnan(d2["mean"]):
            verdict[ds] = {"delta_ind_pp": None, "label": "INCOMPLETE"}
            continue
        delta = d1["mean"] - d2["mean"]
        delta_pp = 100.0 * delta
        # pooled std of the difference of means (independent arms, n-1 each)
        pooled = float(np.sqrt((d1["std"] ** 2) / max(d1["n"], 1)
                               + (d2["std"] ** 2) / max(d2["n"], 1)))
        if delta_pp > THRESH_PP:
            lab = "DECOUPLING-DISTINCT"
        elif delta_pp < -THRESH_PP:
            lab = "FtP WINS"
        else:
            lab = "DECOUPLING == FtP"
        verdict[ds] = {
            "delta_ind_pp": round(delta_pp, 3),
            "se_of_mean_diff_pp": round(100.0 * pooled, 3),
            "arm1_ind_mean": d1["mean"], "arm1_ind_std": d1["std"],
            "arm2_ind_mean": d2["mean"], "arm2_ind_std": d2["std"],
            "label": lab,
        }

    labs = [v["label"] for v in verdict.values() if v["label"] not in ("INCOMPLETE",)]
    if labs and all(l == "DECOUPLING-DISTINCT" for l in labs):
        overall = "DECOUPLING-DISTINCT (novelty measured: decoupling-by-construction > freeze-then-probe on all datasets)"
    elif labs and all(l == "DECOUPLING == FtP" for l in labs):
        overall = "DECOUPLING == FtP (rescope novelty: decoupling = freeze-then-probe relocated to temporal graphs)"
    elif labs and any(l == "FtP WINS" for l in labs):
        overall = "MIXED/FtP-FAVORED (freeze-then-probe matches or beats decoupling on >=1 dataset)"
    else:
        overall = "MIXED (per-dataset verdicts disagree; see table)"

    result = {
        "experiment": "freeze-then-probe control vs decoupling-by-construction (control protocol)",
        "threshold_pp": THRESH_PP,
        "arms": arms,
        "verdict_per_dataset": verdict,
        "overall_verdict": overall,
        "sources": {"arm1": a.arm1, "arm2": a.arm2, "arm3": a.arm3},
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(result, f, indent=2)

    # ── inline table ──
    print("\n" + "=" * 78)
    print("FREEZE-THEN-PROBE CONTROL — 3 seeds (ddof=1, n-1 std)")
    print("=" * 78)
    print(f"{'arm':<18}{'dataset':<12}{'ind_AP (mean+/-std)':<24}{'trans_AP':<22}")
    print("-" * 78)
    for arm_name, arm in arms.items():
        for ds in sorted(arm):
            i = arm[ds]["ind_ap"]; t = arm[ds]["trans_ap"]
            print(f"{arm_name:<18}{ds:<12}"
                  f"{i['mean']:.4f}+/-{i['std']:.4f} (n={i['n']})   "
                  f"{t['mean']:.4f}+/-{t['std']:.4f}")
    print("-" * 78)
    print("SUMMARY (Δ_ind = arm1_decoupling - arm2_ftp):")
    for ds, v in verdict.items():
        if v["delta_ind_pp"] is None:
            print(f"  {ds:<12} INCOMPLETE")
        else:
            print(f"  {ds:<12} Δ_ind = {v['delta_ind_pp']:+.3f}pp "
                  f"(SE {v['se_of_mean_diff_pp']:.3f}pp) -> {v['label']}")
    print(f"\nOVERALL: {overall}")
    print(f"\nSaved -> {a.out}")


if __name__ == "__main__":
    main()
