"""Validate paired light/dark design coverage; identity and evidence bookkeeping, not aesthetic approval."""
from pathlib import Path
import argparse,json,sys
from urllib.parse import parse_qs
from pipeline import GateError,require,safe,load,digest,png_info,validate_closure,atomic,now

def validate(data):
 require(data.get('version')=='1.0','Unsupported theme matrix version')
 concepts=data.get('concepts');require(isinstance(concepts,list) and 1<=len(concepts)<=32,'Explicit nonempty bounded concept list required')
 ids=set()
 for c in concepts:
  sid=c.get('id');require(isinstance(sid,str) and sid and sid not in ids,'Unique concept identity required');ids.add(sid)
  require(c.get('themes')==['light','dark'],'Declare one light/dark pair in stable order')
  require(all(isinstance(c.get(k),str) and c[k].strip() for k in ['product','family','first','layout']),'Meaningful product/family/first task/layout required')
  views=c.get('viewports');require(isinstance(views,dict) and set(views)=={'desktop','mobile'},'Explicit desktop and mobile required')
  for wh in views.values():require(isinstance(wh,list) and len(wh)==2 and all(type(n)is int and 1<=n<=8192 for n in wh),'Explicit safe viewport dimensions required')
 roles=data.get('type_contract',{}).get('roles',{});require(set(roles)=={'page','section','entity','body','label','meta'},'Six declared type roles required')
 for r,v in roles.items():require(isinstance(v,list) and len(v)==3 and all(type(n) in [int,float] for n in v) and 8<=v[0]<=120 and v[1]>=v[0] and 100<=v[2]<=900,'Explicit readable type recipe required: '+r)
 require(isinstance(data.get('theme_contract'),str) and data['theme_contract'].strip(),'Theme/content consistency contract required')
 return {'concepts':len(concepts),'theme_variants':len(concepts)*2,'viewport_cases':len(concepts)*4}

def pinned(root,ref):
 require(isinstance(ref,dict),'Pinned file required');p=safe(root,ref.get('path',''),True);require(p.is_file() and ref.get('sha256')==digest(p),'Missing/stale evidence: '+str(p));return p

def verify(root,plan,index,qa):
 plan_path=safe(root,plan,True);contract=load(plan_path);summary=validate(contract)
 index_path=safe(root,index,True);records=load(index_path);require(records.get('version')=='1.0' and records.get('matrix_sha256')==digest(plan_path),'Capture index of wrong matrix')
 concepts={c['id']:c for c in contract['concepts']};expected={(sid,t) for sid in concepts for t in ['light','dark']};seen=set();manifest_ids=set();images=[]
 for item in records.get('captures',[]):
  key=(item.get('study_id'),item.get('theme'));require(key in expected and key not in seen,'Duplicate/unknown theme capture');seen.add(key)
  cap=load(pinned(root,item.get('capture')));require(cap.get('passed')is True,'Actual render checks did not pass')
  q=parse_qs(cap.get('view_query',''));require(q.get('variant')==[key[0]] and q.get('theme')==[key[1]] and not q.get('mode'),'Capture route/theme differs from matrix study')
  ref=cap.get('source_manifest');mp=pinned(root,ref);closure=validate_closure(root,load(mp));require(ref.get('closure')==closure,'Capture closure differs from actual pinned closure');manifest_ids.add((ref['path'],ref['sha256']))
  shots=cap.get('screenshots',[]);require(len(shots)==2 and {s.get('state') for s in shots}=={'desktop','mobile'},'Missing desktop/mobile image')
  for s in shots:
   info=png_info(pinned(root,s));wh=concepts[key[0]]['viewports'][s['state']];require([info['width'],info['height']]==wh,'Screenshot size differs from matrix viewport');images.append(s)
 require(seen==expected,'Missing light/dark concept coverage');require(len(manifest_ids)==1,'Mixed source builds in theme comparison')
 qa_path=safe(root,qa,True);checks=load(qa_path);require(checks.get('passed')is True and checks.get('closure_unchanged')is True,'Actual browser matrix checks failed or stale')
 require(checks.get('matrix_sha256')==digest(plan_path),'QA of wrong matrix');mref=checks.get('source_manifest',{});pinned(root,mref);require((mref.get('path'),mref.get('sha256')) in manifest_ids,'QA source differs from capture source')
 declared=contract.get('qa_contract',[]);require(isinstance(declared,list) and declared and len(set(declared))==len(declared),'Declare actual QA slices before execution')
 expected_cases={(sid,t,v) for sid,t in expected for v in ['desktop','mobile']};cases={}
 for c in checks.get('cases',[]):
  key=(c.get('variant'),c.get('theme'),c.get('viewport'));require(key in expected_cases and key not in cases,'Duplicate/unknown QA case');cases[key]=c
  require(c.get('passed')is True and set(c.get('checks',{}))==set(declared) and all(type(b)is bool and b for b in c['checks'].values()),'Missing/failing declared QA slice')
  require(isinstance(c.get('semantic'),dict) and c['semantic'],'Concrete semantic content identity required')
  require(isinstance(c.get('geometry'),dict) and c['geometry'],'Concrete paired geometry required')
 require(set(cases)==expected_cases,'Missing paired QA viewport')
 for sid in concepts:
  for v in ['desktop','mobile']:
   a,b=cases[(sid,'light',v)],cases[(sid,'dark',v)];require(a['semantic']==b['semantic'],'Theme pair changed semantic fixture/task: '+sid)
   require(set(a['geometry'])==set(b['geometry']),'Theme pair geometry fields differ')
   for name,val in a['geometry'].items():
    other=b['geometry'][name];require(type(val) in [int,float] and type(other) in [int,float] and abs(val-other)<=1,'Theme pair changed geometry: '+sid+'/'+name)
 return {'version':'1.0','at':now(),'passed':True,**summary,'matrix':{'path':plan,'sha256':digest(plan_path)},'capture_index':{'path':index,'sha256':digest(index_path)},'qa':{'path':qa,'sha256':digest(qa_path)},'pngs':len(images),'source_manifest':mref,'human_acceptance':'pending','scope':'Pinned coverage, declared actual browser results and paired semantic/geometry comparison. Observer truth, beauty, full accessibility and physical device behavior are not proved by this helper.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--workspace',required=True);p.add_argument('--plan',required=True);s=p.add_subparsers(dest='command',required=True);s.add_parser('validate');v=s.add_parser('verify');v.add_argument('--index',required=True);v.add_argument('--qa',required=True);v.add_argument('--out',required=True);a=p.parse_args();root=Path(a.workspace).resolve(strict=True);require(root.is_dir() and root!=Path(root.anchor),'Explicit non-root workspace required')
 result=validate(load(safe(root,a.plan,True))) if a.command=='validate' else verify(root,a.plan,a.index,a.qa)
 if a.command=='verify':atomic(safe(root,a.out),result,True)
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
 sys.stdout.reconfigure(encoding='utf-8')
 try:main()
 except (GateError,ValueError,KeyError,TypeError,OSError) as e:print(json.dumps({'error':str(e)},ensure_ascii=False));sys.exit(2)
