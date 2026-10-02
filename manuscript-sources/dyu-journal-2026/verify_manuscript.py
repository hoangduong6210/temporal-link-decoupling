"""Verify this author draft against frozen evidence, not formal snapshot admission."""
from collections import Counter
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import tomllib
from zipfile import ZipFile
from lxml import etree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT))
from scripts.numeric_evidence import NUMBER_TOKEN
RELEASE=ROOT/"results/frozen/LP-REL-2026-A003-001"
MATRIX=RELEASE/"payload/results/audit/scientific-matrix.json"
PROTOCOL=RELEASE/"payload/protocols/link_prediction_v1.toml"
CLAIM="LP-C-DECOUPLING-001"
EVIDENCE="LP-E-SCIENTIFIC-MATRIX-001"
JOB="LP-JOB-SLURM-A003-FINAL-RECONCILE-R2"

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    checked=0
    for line in (RELEASE/"checksums.sha256").read_text().splitlines():
        digest,rel=line.split(maxsplit=1);rel=rel.lstrip("* ")
        assert sha(RELEASE/rel)==digest, rel
        checked+=1
    matrix=json.loads(MATRIX.read_text())
    protocol=tomllib.loads(PROTOCOL.read_text())
    summary=matrix["summary"]
    for row in summary:
        vals=[r["ind_ap"] for r in matrix["runs"] if r["dataset"]==row["dataset"] and r["task_profile"]==row["task_profile"]]
        assert len(vals)==row["n_seeds"]==3
        assert math.isclose(statistics.mean(vals),row["ind_ap_mean"],rel_tol=0,abs_tol=1e-12)
        assert math.isclose(statistics.stdev(vals),row["ind_ap_std"],rel_tol=0,abs_tol=1e-12)
    assert len(matrix["runs"])==27
    look={(r["dataset"],r["task_profile"]):i for i,r in enumerate(summary)}
    profile={"Coupled":"coupled-end-to-end","Decoupled":"decoupled","Freeze then probe":"freeze-then-probe"}
    protocol_map={
      "Backbone hidden width":("training.hidden",protocol["training"]["hidden"]),
      "Batch size":("training.batch_size",protocol["training"]["batch_size"]),
      "Training epochs":("training.epochs",protocol["training"]["epochs"]),
      "Probe phase epochs":("task_profiles.freeze-then-probe.parameters.probe_epochs",protocol["task_profiles"]["freeze-then-probe"]["parameters"]["probe_epochs"]),
      "Learning rate":("training.learning_rate",protocol["training"]["learning_rate"]),
      "Weight decay":("optimizer.weight_decay",protocol["optimizer"]["weight_decay"]),
    }
    registry=[]
    empirical=0
    for ln,line in enumerate((HERE/"manuscript.txt").read_text().splitlines(),1):
        if not line.strip():continue
        role,text=line.split("\t",1)
        matches=list(NUMBER_TOKEN.finditer(line));seen=Counter()
        result_idx=None
        if role=="RESULT_ROW" and not text.startswith("Corpus|"):
            dataset,arm,vals=text.split("|")
            result_idx=look[(dataset.lower(),profile[arm])]
        for mi,m in enumerate(matches):
            literal=m.group();seen[literal]+=1
            record={"file":"manuscript.txt","line":ln,"literal":literal,"occurrence":seen[literal]}
            if result_idx is not None:
                field=["ind_ap_mean","ind_ap_std"][mi]
                raw=summary[result_idx][field]
                rounded=Decimal(str(raw)).quantize(Decimal("0.0001"),rounding=ROUND_HALF_EVEN)
                assert Decimal(literal)==rounded,(ln,literal,raw)
                record.update(kind="empirical",claim_id=CLAIM,evidence_id=EVIDENCE,job_id=JOB,
                    artifact_path=str(MATRIX.relative_to(ROOT)),artifact_sha256=sha(MATRIX),
                    artifact_selector=f"$.summary[{result_idx}].{field}",precision=4,rounding="ROUND_HALF_EVEN")
                empirical+=1
            elif role=="TRAIN_ROW":
                name,value=text.split("|")
                if name=="Train / validation / test":
                    selector="study.split"
                    vals=re.findall(r"\d+",protocol["study"]["split"])
                    expected=vals[mi]
                elif name=="Selected random seeds":
                    selector=f"study.seeds[{mi}]";expected=protocol["study"]["seeds"][mi]
                else:selector,expected=protocol_map[name]
                assert Decimal(literal)==Decimal(str(expected)),(ln,literal,expected)
                record.update(kind="protocol",claim_id=CLAIM,evidence_id=EVIDENCE,job_id=JOB,
                    artifact_path=str(PROTOCOL.relative_to(ROOT)),artifact_sha256=sha(PROTOCOL),
                    artifact_selector=selector,selector_format="TOML key; split components by occurrence",expected=str(expected))
            elif role=="P" and "n = 3 selected seeds" in text and literal=="3":
                assert all(r["n_seeds"]==3 for r in summary)
                record.update(kind="empirical",claim_id=CLAIM,evidence_id=EVIDENCE,job_id=JOB,
                    artifact_path=str(MATRIX.relative_to(ROOT)),artifact_sha256=sha(MATRIX),artifact_selector="$.summary[0].n_seeds",assertion="exact; also checked all cells")
                empirical+=1
            else:
                if role=="REF": exemption="bibliographic-locator"
                elif role=="EQ":exemption="equation-label"
                elif role in ["H1","H2"]:exemption="section-label"
                elif role=="TABLE_CAP":exemption="table-label"
                elif role=="P":
                    start=m.start()-len(role)-1
                    is_citation=any(c.start()<=start<c.end() for c in re.finditer(r"\[[\d, ]+\]",text))
                    is_table=text[max(0,start-6):start]=="Table "
                    assert is_citation or is_table,(ln,literal,text)
                    exemption="bibliographic-locator" if is_citation else "table-label"
                else: raise AssertionError(("Unclassified occurrence",ln,literal))
                record.update(kind="structural",exemption=exemption)
            registry.append(record)
    assert empirical==19
    (HERE/"numeric-provenance.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n" for r in registry))
    # Confirm that the rendered manuscript contains every source paragraph/cell,
    # and has exactly the intended page geometry and section columns.
    ns={"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    def norm(t):
        t=re.sub(r"(F|G|φ|H|p)_(θ|ψ|uv|t|dec)",r"\1\2",t)
        return re.sub(r"\s+"," ",t).strip()
    with ZipFile(HERE/"DYU_Journal_Manuscript.docx") as z:
        doc=ET.fromstring(z.read("word/document.xml"))
        paras=["".join(p.itertext()) for p in []] # use text elements only below
        paras=[norm("".join(p.xpath(".//w:t/text()",namespaces=ns))) for p in doc.findall(".//w:p",ns)]
        actual=Counter(paras)
        for line in (HERE/"manuscript.txt").read_text().splitlines():
            if not line.strip():continue
            role,t=line.split("\t",1)
            values=t.split("|") if role.endswith("_ROW") else [t]
            for value in values:
                key=norm(value)
                if role=="EQ":key=re.sub(r"\s+(\(\d+\))$",r"\1",key)
                assert actual[key]>0,("Missing source text",role,value)
                actual[key]-=1
        sects=doc.findall(".//w:sectPr",ns)
        assert len(sects)==3
        for s in sects:
            assert s.find("w:pgSz",ns).get("{%s}w"%ns["w"])=="11906"
            assert s.find("w:pgMar",ns).get("{%s}top"%ns["w"])=="1985"
        assert [s.find("w:cols",ns).get("{%s}num"%ns["w"]) for s in sects]==["1","2","1"]
    report={"status":"PASS","scope":"Author-draft validation only; not canonical paper snapshot admission",
      "frozen_release_files_verified":checked,"selected_runs":len(matrix["runs"]),"aggregate_rows_recomputed":len(summary),
      "registered_numeric_occurrences":len(registry),"empirical_occurrences":empirical,
      "source_sha256":sha(HERE/"manuscript.txt"),"docx_sha256":sha(HERE/"DYU_Journal_Manuscript.docx"),
      "limitations":["Protocol selectors include TOML and must be reconciled with the canonical JSON-only snapshot gate before admission.",
      "No independent training rerun or external-baseline parity evaluation is claimed."]}
    (HERE/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()

