#!/usr/bin/env python3
"""Frozen final comparison for PRV-103 QA09; no recapture and no tuning."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from mininode_api.domain_packs.privacy.evidence_adapter import _form_purpose_signal
from mininode_api.web_inspector.models import FormEvidence
ROOT=Path(__file__).resolve().parents[2]
A=ROOT/'docs/evidence/prv103-holdout-0.9-artifact-a.json'; G=ROOT/'docs/evidence/prv103-holdout-0.9-gold.json'
A_HASH='45a16c3bea81a62a9504d6616ac67221ee1240efe340703a8ad9f3fe7682afd2'; G_HASH='5a7ba4009436023d6c74ba5842462aa138206b1dcbcae760831e7b494eea145e'
def h(p): return hashlib.sha256(json.dumps(json.loads(p.read_text()),ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def form(r): return FormEvidence('https://blind.invalid/','','post',[],[],'',[],r.get('heading'),r.get('legend'),r.get('introductory_text'),r.get('submit_text'))
def pct(n,d): return round(100*n/d,2) if d else 0.0
def main():
 assert h(A)==A_HASH and h(G)==G_HASH
 a=json.loads(A.read_text()); gr=json.loads(G.read_text()); assert len(a)==len(gr)==56
 gold={r['blind_id']:r['gold'] for r in gr}; assert len(gold)==56 and {r['blind_id'] for r in a}==set(gold)
 rows=[{'blind_id':r['blind_id'],'gold':gold[r['blind_id']],'prediction':_form_purpose_signal(form(r))} for r in a]
 adj=[r for r in rows if r['gold']!='unknown']; emit=[r for r in adj if r['prediction']!='unknown']; gc=[r for r in adj if r['gold']=='concrete']; pc=[r for r in adj if r['prediction']=='concrete']
 tp=sum(r['gold']=='concrete' and r['prediction']=='concrete' for r in adj); fc=sum(r['prediction']=='concrete' and r['gold']!='concrete' for r in adj); fnone=sum(r['prediction']=='none' and r['gold'] not in {'none','unknown'} for r in rows)
 m={'eligible':56,'adjudicable':len(adj),'exact_accuracy':pct(sum(r['prediction']==r['gold'] for r in adj),len(adj)),'coverage':pct(len(emit),len(adj)),'emitted_precision':pct(sum(r['prediction']==r['gold'] for r in emit),len(emit)),'concrete_precision':pct(tp,len(pc)),'concrete_recall':pct(tp,len(gc)),'false_concrete':fc,'false_adverse_none':fnone}
 p=(m['exact_accuracy']>=90 and m['coverage']>=90 and m['emitted_precision']>=95 and m['concrete_precision']>=90 and m['concrete_recall']>=85 and fc<=1 and fnone==0)
 o=(m['exact_accuracy']>=85 and m['coverage']>=80 and m['emitted_precision']>=90 and m['concrete_precision']>=85 and m['concrete_recall']>=80 and fnone<=1)
 v='PASS' if p else 'PASS WITH OBSERVATIONS' if o else 'NEEDS FIX'; errors=[r for r in rows if r['gold']!='unknown' and r['prediction']!=r['gold']]
 result={'product_sha':'6fbe6f94887114f4a5459af861f1fcaa0c4b7bd7','framework_version':'0.9','scoring_version':'0.1','artifact_a_canonical_sha256':A_HASH,'gold_canonical_sha256':G_HASH,'metrics':m,'provisional_verdict':v,'errors':errors,'predictions':rows,'note':'Final verdict requires manual systematic-pattern review.'}
 out=ROOT/'artifacts/privacy-prv103-qa09-final'; out.mkdir(parents=True,exist_ok=True); (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'metrics':m,'provisional_verdict':v,'errors':errors},ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
