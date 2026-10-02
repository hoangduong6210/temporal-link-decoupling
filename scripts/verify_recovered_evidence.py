"""Verify recovered bytes and recompute supported legacy aggregates; does not admit claims."""
from pathlib import Path
import hashlib,json,statistics,math
ROOT=Path(__file__).resolve().parents[1]
bundle=ROOT/'evidence/recovered/LP-REC-2026-10-02'
report=json.loads((bundle/'recovery-audit.json').read_text())
for line in (bundle/'checksums.sha256').read_text().splitlines():
 digest,name=line.split(maxsplit=1)
 assert hashlib.sha256((bundle/name).read_bytes()).hexdigest()==digest,name
checks=[]
def check(path,sel,vals,mean,sd=None,n=None):
 if not vals or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in vals):return
 m=statistics.mean(vals);s=statistics.stdev(vals) if len(vals)>1 else None
 checks.append(dict(path=path,selector=sel,count=len(vals),recorded_n=n,mean=m,recorded_mean=mean,sample_std=s,recorded_std=sd,pass_mean=math.isclose(m,mean,abs_tol=1e-10),pass_std=sd is None or (s is not None and math.isclose(s,sd,abs_tol=1e-10)),pass_count=n is None or n==len(vals)))
def walk(obj,path,sel='$'):
 if isinstance(obj,dict):
  ps=obj.get('per_seed')
  if isinstance(ps,list) and ps and all(isinstance(v,(int,float)) for v in ps) and isinstance(obj.get('mean'),(int,float)):
   check(path,sel,ps,obj['mean'],obj.get('std'),obj.get('n'))
  rows=list(ps.values()) if isinstance(ps,dict) else ps
  if isinstance(rows,list) and rows and all(isinstance(r,dict) for r in rows):
   for k,v in obj.items():
    if k.endswith('_mean') and isinstance(v,(int,float)):
     metric=k[:-5];vals=[r[metric] for r in rows if isinstance(r.get(metric),(int,float))]
     if len(vals)==len(rows):check(path,sel+'.'+metric,vals,v,obj.get(metric+'_std'),obj.get('n_seeds'))
   for strat,agg in obj.get('by_strategy',{}).items():
    key={'random':'ind_ap','historical':'ind_ap_histneg','inductive':'ind_ap_indneg'}.get(strat)
    if key and all(key in r for r in rows):check(path,sel+'.by_strategy.'+strat,[r[key] for r in rows],agg['ind_ap_mean'],agg.get('ind_ap_std'),agg.get('n_seeds'))
  for k,v in obj.items():walk(v,path,sel+'.'+k)
 elif isinstance(obj,list):
  for i,v in enumerate(obj):walk(v,path,sel+f'[{i}]')

for row in report['artifacts']:
 walk(json.loads((bundle/row['path']).read_text()),row['path'])
assert checks==report['aggregate_checks'], 'Aggregate reconstruction changed'
for row in report['frozen_comparison']:
 assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256']
assert all(r['matches'] for r in report['original_manifest_checks'])
failures=[r for r in checks if not all(r[k] for k in ('pass_mean','pass_std','pass_count'))]
print(f"PASS: recovered byte integrity; {len(checks)} aggregates reconstructed; {len(failures)} recorded discrepancies retained. No evidence admission.")
