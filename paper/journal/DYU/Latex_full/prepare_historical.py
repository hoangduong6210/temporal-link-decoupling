"""Reconstruct retrospective tables; preserve recovered source bytes."""
from pathlib import Path
import hashlib, json, math, re, statistics
HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "PROJECT.toml").is_file())
BASE = ROOT / "results/recovered/legacy_import"
sources, cells = {}, []
def read(name):
    p = BASE / name
    sources[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return json.loads(p.read_text())
def cell(name, records, selector, field="ind_ap", digits=4, expected=None):
    values = [r[field] for r in records]
    seeds = [int(r["seed"]) for r in records]
    assert len(set(seeds)) == len(seeds) and sorted(seeds) in ([1,7,42],[1,2,3,7,42])
    assert all(math.isfinite(v) and 0 <= v <= 1 for v in values)
    mean, sd = statistics.mean(values), statistics.stdev(values)
    if expected is not None:
        assert math.isclose(mean, expected[field+"_mean"], abs_tol=1e-12)
        assert math.isclose(sd, expected[field+"_std"], abs_tol=1e-12)
    cells.append(dict(artifact="results/recovered/legacy_import/"+name,
        sha256=sources[name], selector=selector, field=field, seeds=seeds,
        values=values, mean=mean, sample_sd=sd, decimals=digits))
    return "$"+f"{mean:.{digits}f}\\pm{sd:.{digits}f}"+"$"
def table(label, caption, header, rows):
    return (r"\begin{center}"+"\n"+r"\begin{minipage}{\linewidth}\centering"+"\n"+r"\captionof{table}{"+caption+"}"+r"\label{tab:"+label+"}\n"+
        r"\small\setlength{\tabcolsep}{3pt}"+"\n"+r"\begin{tabular}{@{}"+("l"*len(header))+r"@{}}"+"\n"+
        r"\toprule"+"\n"+" & ".join(header)+r"\\ \midrule"+"\n"+
        "\n".join(" & ".join(row)+r"\\" for row in rows)+"\n"+
        r"\bottomrule"+"\n"+r"\end{tabular}"+"\n"+r"\end{minipage}"+"\n"+r"\end{center}")
blocks = {}
rows=[]
for name,label in [("v3_3_coedit_B_5seed.json","B preset"),("v3_3_coedit_C_5seed.json","C preset"),("baselines_coedit_TGAT_5seed.json","TGAT proxy")]:
    d=read(name)["summary"]; records=[dict(seed=int(k),**v) for k,v in d["per_seed"].items()]
    rows.append([label,cell(name,records,"$.summary.per_seed",expected=d),
        cell(name,records,"$.summary.per_seed","trans_ap",expected=d)])
blocks["PRESETS"]=table("presets","CoEdit preset comparison.",["Configuration","Inductive AP","Transductive AP"],rows)
rows=[]
labels={"B":"B","K1_e2e":"K1: predictor","K2_lfg_hard":"K2: hard gate","K3_floor0":"K3: zero floor","K2K3_gate":"K2 + K3","C_correct":"C: K1 + K2 + K3"}
for dataset in ["coedit","wikipedia","mooc"]:
    name="v3_3_coedit_knob_ablation_3seed.json" if dataset=="coedit" else f"v3_3_knob_ablation_{dataset}_3seed.json"
    for i,a in enumerate(read(name)["arms"]):
        rows.append([{"coedit":"CoEdit","wikipedia":"Wikipedia","mooc":"MOOC"}[dataset] if i==0 else "",labels[a["arm"]],cell(name,a["per_seed"],f"$.arms[{i}].per_seed",expected=a)])
blocks["KNOBS"]=table("knobs","Predictor and gate ablations.",["Corpus","Configuration","AP"],rows)
rows=[]
for dataset,title in [("coedit","CoEdit"),("wikipedia","Wikipedia")]:
    name=f"hardneg/hardneg_B_vs_K1_{dataset}_3seed_v2.json"
    d=read(name)
    for j,(strategy,field) in enumerate([("random","ind_ap"),("historical","ind_ap_histneg"),("inductive","ind_ap_indneg")]):
        row=[title if j==0 else "",strategy.capitalize()]
        for i,a in enumerate(d["arms"]):
            row.append(cell(name,a["per_seed"],f"$.arms[{i}].per_seed",field))
        rows.append(row)
blocks["NEGATIVES"]=table("negatives","Candidate-pool sensitivity.",["Corpus","Pool","B","K1"],rows)
rows=[]
for dataset,title in [("coedit","CoEdit"),("wikipedia","Wikipedia")]:
    name=f"backbone_removed/backbone_removed_{dataset}_3seed.json"
    for i,a in enumerate(read(name)["arms"]):
        rows.append([title if i==0 else "", "Full B" if i==0 else "Pair statistics",cell(name,a["per_seed"],f"$.arms[{i}].per_seed",digits=6,expected=a)])
blocks["BACKBONE"]=table("backbone","Learned-backbone contribution.",["Corpus","Representation","Inductive AP"],rows)
rows=[]
for dataset,title in [("coedit","CoEdit"),("wikipedia","Wikipedia")]:
    for arm,label in [("ARM1_decoupling","Decoupled"),("ARM2_ftp","Freeze then probe")]:
        name=f"v3_3_frozen_probe_{arm}.json"; d=read(name)
        records=[r for r in d["runs"] if r["dataset"]==dataset]
        rows.append([title if arm.startswith("ARM1") else "",label,cell(name,records,f'$.runs[dataset={dataset}]')])
name="v3_3_frozen_probe_ARM2_ftp_wikipedia_idfix.json"
rows.append(["Wikipedia","Probe, ID-corrected",cell(name,read(name)["runs"],"$.runs")])
blocks["PROBES"]=table("probes","Freeze-then-probe comparison.",["Corpus","Procedure","Inductive AP"],rows)
p=HERE/"main.tex"; text=p.read_text()
for key,block in blocks.items():
    text,n=re.subn(r"(?<=% BEGIN HISTORICAL "+key+r"\n).*?(?=\n% END HISTORICAL "+key+r")",lambda _:block,text,flags=re.S)
    assert n==1,key
p.write_text(text)
(HERE/"historical-numeric-sources.json").write_text(json.dumps(dict(
    status="RETROSPECTIVE_DRAFT_NOT_ADMITTED_RELEASE",
    method="Means and sample SD reconstructed from recovered per-seed observations; no training rerun.",
    source_root="results/recovered/legacy_import",source_hashes=sources,cells=cells),indent=2,allow_nan=False)+"\n")
print(f"PASS: {len(blocks)} historical tables, {len(cells)} AP cells, {len(sources)} source files; per-seed reconstruction.")
