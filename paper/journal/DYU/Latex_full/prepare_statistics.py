"""Recompute manuscript corpus counts only after verifying corpus identities."""
from pathlib import Path
import hashlib,json,re
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'PROJECT.toml').exists())
expected={'coedit':'cbdb09bfbd83456be01a039fa3a0b4c2e37415af43a3406fc8d3f55be4a5c736','wikipedia':'f035f7dd2e97dbb931d48a4b3c099d43b2fdc25d0e15828de6fa2c604b8017c7','mooc':'e422cf5e1e6a95763b24a6a5dc53fec993c9ae80948b3fd7ef4f82816b26a278'}
records={}
for name,sha in expected.items():
 p=ROOT/'resources/corpora'/f'{name}.npz'
 assert hashlib.sha256(p.read_bytes()).hexdigest()==sha,f'Corpus identity differs: {name}'
 with np.load(p,allow_pickle=False) as d:
  s,t=d['sources'],d['destinations'];n=len(s);a=int(n*.7);b=int(n*(.7+.15))
  unseen=np.setdiff1d(np.union1d(s[b:],t[b:]),np.union1d(s[:b],t[:b]))
  records[name]=dict(sha256=sha,nodes=len(np.union1d(s,t)),events=n,features=d['features'].shape[1],train=a,validation=b-a,test=n-b,inductive_nodes=len(unseen),inductive_events=int((np.isin(s[b:],unseen)|np.isin(t[b:],unseen)).sum()))
tex=(HERE/'main.tex').read_text()
for label,key in [('Nodes','nodes'),('Events','events'),('Feature dimension','features'),('Training events','train'),('Validation events','validation'),('Test events','test'),('Inductive nodes','inductive_nodes'),('Inductive test events','inductive_events')]:
 row=label+' & '+' & '.join(f'{records[n][key]:,}' for n in expected)+r'\\'
 assert row in tex,f'Manuscript count mismatch: {label}'
(HERE/'dataset-statistics.json').write_text(json.dumps(dict(method='Chronological 70/15/15; unseen after training and validation; observed unique node identities.',corpora=records),indent=2)+'\n')
print('PASS: dataset statistics verified against three SHA-256-identified corpora')
