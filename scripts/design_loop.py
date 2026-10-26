"""Design-only reference -> analysis/patterns -> prompt -> source -> viewed revision ledger."""
import argparse,json,sys,time
from pathlib import Path
from pipeline import safe,load,atomic,require,digest,ident,now,GateError,png_info,validate_closure
from pattern_loop import validate as validate_patterns
from ux_contract import validate_plan,validate_evidence,validate_interaction_evidence,validate_interaction_checks,CRITERIA
from urllib.parse import parse_qs

def pin(root,relative):
 p=safe(root,relative,True);require(p.is_file(),'Expected a file');return {'path':p.relative_to(root).as_posix(),'sha256':digest(p)}
def fresh(root,record):
 p=safe(root,record['path'],True);require(p.is_file() and digest(p)==record['sha256'],'Stale evidence: '+record['path']);return p

def prepare(root,study,analysis,patterns,prompt,out,budget=2,source_root=None,ux_plan=None):
 ident(study);require(1<=budget<=5,'Budget must be1..5');target=safe(root,out)
 require(not target.exists(),'Existing prompt ledger preserved')
 generated=safe(root,source_root or ('generated/'+study))
 require(not generated.exists() or (generated.is_dir() and not any(p.is_file() for p in generated.rglob('*'))),'Prepare must run before generated source exists')
 a=pin(root,analysis);p=pin(root,patterns);q=pin(root,prompt)
 require(isinstance(load(fresh(root,a)),dict),'Analysis must be an object')
 require(isinstance(load(fresh(root,p)),dict),'Pattern packet must be an object')
 require(len(fresh(root,q).read_text(encoding='utf-8').strip())>=200,'Reconstruction prompt must contain concrete directions')
 record={'version':'1.0','study_id':study,'scope':'design-only; no actor/job/brand/backend prerequisite','prepared_at':now(),'prepared_ns':time.time_ns(),'source_root':generated.relative_to(root).as_posix(),'budget':budget,'analysis':a,'patterns':p,'prompt':q,'iterations':[],'human_acceptance':'pending'}
 if ux_plan:
  ux=pin(root,ux_plan);validate_plan(load(fresh(root,ux)),study);record['ux_plan']=ux
 atomic(target,record,True);return {'status':'prompt-pinned-before-source','ledger':out,'prompt_sha256':q['sha256'],'iterations_remaining':budget}

def bind(root,ledger,source_files):
 target=safe(root,ledger,True);record=load(target)
 for key in ['analysis','patterns','prompt']:fresh(root,record[key])
 if record.get('ux_plan'):validate_plan(load(fresh(root,record['ux_plan'])),record['study_id'])
 if record.get('interaction_checks'):fresh(root,record['interaction_checks'])
 require(record.get('reference_packet'),'Attach validated viewed references before source binding');validate_patterns(root,load(fresh(root,record['reference_packet'])))
 require(len(record['iterations'])<record['budget'],'Visual iteration budget exhausted')
 require(not record['iterations'] or record['iterations'][-1].get('review'),'Review previous actual render before another source binding')
 sources=[pin(root,p) for p in source_files];require(sources,'Actual source required')
 generated=safe(root,record['source_root'])
 for p in sources:
  f=fresh(root,p);require(f.is_relative_to(generated),'Generated source outside declared root');require(f.stat().st_mtime_ns>=record['prepared_ns'],'Source predates pinned reconstruction prompt')
 require(len({p['path'] for p in sources})==len(sources),'Duplicate source files')
 followup=record['iterations'][-1]['review'] if record['iterations'] else None
 if followup: fresh(root,followup)
 record['iterations'].append({'number':len(record['iterations'])+1,'bound_at':now(),'prompt_sha256':record['prompt']['sha256'],'followup_directive':followup,'source_files':sources,'review':None})
 atomic(target,record);return {'status':'source-bound','iteration':len(record['iterations']),'source_files':len(sources),'prompt_sha256':record['prompt']['sha256']}

def amend(root,ledger,kind,reason,observer):
 target=safe(root,ledger,True);record=load(target)
 require(kind in {'analysis','patterns'},'Pinned prompt is immutable; evidence-only amendment allowed')
 require(not record['iterations'],'Evidence amendment allowed only before first source binding')
 require(bool(reason.strip()) and bool(observer.strip()),'Named reason required')
 fresh(root,record['prompt']);old=record[kind];new=pin(root,old['path'])
 require(new!=old,'No evidence change to amend')
 record.setdefault('amendments',[]).append({'at':now(),'observer':observer,'kind':kind,'reason':reason,'previous':old,'current':new,'budget_reset':False})
 record[kind]=new;atomic(target,record)
 return {'status':'evidence-amended-with-history','kind':kind,'budget_reset':False,'prompt_sha256':record['prompt']['sha256']}

def attach(root,ledger,packet):
 target=safe(root,ledger,True);record=load(target);ref=pin(root,packet);data=load(fresh(root,ref));summary=validate_patterns(root,data)
 record.setdefault('reference_history',[]).append({'at':now(),'packet':ref,'previous':record.get('reference_packet')})
 record['reference_packet']=ref;atomic(target,record)
 return {'status':'viewed-reference-packet-attached','sources':summary['sources'],'source_observation':'named external attestation; not automatic vision','budget_reset':False}

def attach_interactions(root,ledger,checks,observer,basis):
 target=safe(root,ledger,True);record=load(target)
 require(record.get('ux_plan') and not record['iterations'],'External selector bindings require pinned UX plan and must precede first bind')
 require(not record.get('interaction_checks'),'Existing selector bindings preserved')
 plan=load(fresh(root,record['ux_plan']));validate_plan(plan,record['study_id'])
 require('interaction_checks' not in plan,'External selector bindings cannot override embedded checks')
 require(observer.strip() and basis.strip(),'Named observer and relation to frozen plan required')
 ref=pin(root,checks);data=load(fresh(root,ref))
 require(data.get('version')=='1.0' and data.get('study_id')==record['study_id'],'External checks of wrong study/version')
 require(data.get('plan_sha256',record['ux_plan']['sha256'])==record['ux_plan']['sha256'],'External checks of wrong UX plan')
 validate_interaction_checks(data.get('interaction_checks'))
 generated=safe(root,record['source_root'])
 record['interaction_checks']=ref
 record.setdefault('interaction_binding_history',[]).append({'at':now(),'checks':ref,'ux_plan':record['ux_plan'],'observer':observer,'basis':basis,'phase':'before-first-bind; explicit legacy selector adapter','source_already_present':generated.exists() and any(p.is_file() for p in generated.rglob('*')),'intent_change':False,'intent_relation':'named attestation, not automatic semantic verification','budget_reset':False})
 atomic(target,record);return {'status':'interaction-selector-bindings-attached','plan_changed':False,'budget_reset':False,'source_already_present':record['interaction_binding_history'][-1]['source_already_present']}

def revision(root,ledger,prompt,findings,module,expected):
 target=safe(root,ledger,True);record=load(target)
 require(record['iterations'] and record['iterations'][-1].get('review'),'Review required before revision')
 previous=record['iterations'][-1]['review'];data=load(fresh(root,previous))
 require(data['decision']=='revise' and len(record['iterations'])<record['budget'],'No revision budget or responsible failure')
 allowed=set(data['dimensions'])
 if record.get('ux_plan'):
  ux=load(fresh(root,data['ux_evidence']));allowed.update(ux['criteria'])
 require(findings and set(findings).issubset(allowed) and module.strip() and expected.strip(),'Concrete finding/module/expected delta required')
 current=pin(root,prompt);require(current['path']!=record['prompt']['path'],'Keep prior prompt file intact')
 record.setdefault('prompt_revisions',[]).append({'at':now(),'previous':record['prompt'],'current':current,'findings':findings,'module':module,'expected_visible_difference':expected,'budget_reset':False})
 record['prompt']=current;atomic(target,record)
 return {'status':'prompt-revision-recorded','budget_reset':False,'remaining':record['budget']-len(record['iterations'])}

def artifacts(root,record,data):
 evidence=data.get('artifacts',{});require(evidence,'Actual capture records required, not detached PNGs')
 if data['decision']=='candidate':require(set(evidence)=={'calibration','study','components'},'Candidate needs calibration, adapted study and component board')
 registered=set()
 for kind,ref in evidence.items():
  require(kind in {'calibration','study','components'},'Unknown visual artifact kind')
  cap=load(fresh(root,ref));require(cap.get('passed') is True,'Capture checks failed')
  source=cap['source_manifest'];manifest=load(fresh(root,source));validate_closure(root,manifest)
  require(source.get('closure')==manifest,'Capture closure differs from pinned manifest')
  query=parse_qs(cap.get('view_query',''));require(query.get('variant')==[record['study_id']],'Capture of wrong study')
  expected={'calibration':'calibration','study':None,'components':'components'}[kind]
  require(query.get('mode')==([expected] if expected else None),'Capture of wrong artifact mode')
  require({s['state'] for s in cap['screenshots']}=={'desktop','mobile'},'Desktop and touch captures required')
  for shot in cap['screenshots']:png_info(fresh(root,shot));registered.add((shot['path'],shot['sha256']))
 require(all((c['path'],c['sha256']) in registered for c in data['captures']),'PNG detached from declared capture records')
 packet=record.get('reference_packet');require(packet,'Viewed reference/pattern packet required')
 refs=load(fresh(root,packet));validate_patterns(root,refs)
 comparison=data.get('calibration_comparison',{})
 require(comparison.get('reference_ids') and set(comparison['reference_ids']).issubset({s['id'] for s in refs['sources']}),'Declared source identities required for comparison')
 require(comparison.get('region') and comparison.get('evidence') and comparison.get('status') in {'pass','revise'},'Concrete reference-region comparison required')
 if data['decision']=='candidate':require(comparison['status']=='pass','Unresolved calibration cannot yield final candidate')
 return {'artifacts':evidence,'calibration_comparison':comparison,'reference_packet':packet}

def review(root,ledger,review_file):
 target=safe(root,ledger,True);record=load(target);require(record['iterations'],'No source iteration bound')
 current=record['iterations'][-1];require(current['review'] is None,'Existing review preserved')
 for p in current['source_files']:fresh(root,p)
 ref=pin(root,review_file);data=load(fresh(root,ref))
 require(data.get('observer') and data.get('captures'),'Actual named observer and captures required')
 for p in data['captures']:
  png_info(fresh(root,p));require(p.get('viewed') is True,'Actual image inspection required')
 dims={'reference-fidelity','composition','color-hierarchy','component-coherence','material','responsive-states'}
 require(set(data.get('dimensions',{}))==dims,'Separate design dimensions required')
 for d in data['dimensions'].values():require(d.get('status') in {'pass','revise','not-run'} and bool(d.get('evidence')),'Concrete dimension evidence required')
 require(data.get('decision') in {'revise','candidate','stop-budget'},'Explicit decision required')
 failures=[k for k,v in data['dimensions'].items() if v['status']!='pass']
 if data['decision']=='candidate':require(not failures,'Unresolved design dimensions cannot be candidate')
 if data['decision']=='revise':require(data.get('changed_module') and data.get('next_change'),'Revision requires responsible module and concrete change')
 require(data.get('human_acceptance')=='pending','Only human supplies final preference')
 closure=artifacts(root,record,data)
 if record.get('ux_plan'):
  require(data.get('ux_evidence'),'Pinned UX plan requires actual UX evidence')
  ux_pin=data['ux_evidence'];ux_data=load(fresh(root,ux_pin))
  ux_result=validate_evidence(root,record['ux_plan'],ux_data,record['study_id'],data['artifacts'],data['decision'])
  closure.update({'ux_evidence':ux_pin,'ux':ux_result});failures.extend(ux_result['unresolved'])
  plan=load(fresh(root,record['ux_plan']))
  if plan.get('interaction_checks') or record.get('interaction_checks'):
   require(data.get('interaction_evidence'),'Planned interaction checks require actual browser interaction evidence')
   interaction_pin=data['interaction_evidence'];interaction_data=load(fresh(root,interaction_pin))
   interaction_result=validate_interaction_evidence(root,record['ux_plan'],interaction_data,record['study_id'],data['artifacts'],data['decision'],record.get('interaction_checks'))
   closure.update({'interaction_evidence':interaction_pin,'interaction':interaction_result});failures.extend(interaction_result['unresolved'])
 current['review']={**ref,'observer':data['observer'],'decision':data['decision'],'dimensions':data['dimensions'],**closure}
 atomic(target,record);return {'status':'review-recorded','decision':data['decision'],'unresolved':failures,'iterations_remaining':record['budget']-len(record['iterations']),'human_acceptance':'pending'}

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--workspace',required=True);s=a.add_subparsers(dest='mode',required=True)
 p=s.add_parser('prepare');p.add_argument('--id',required=True);p.add_argument('--analysis',required=True);p.add_argument('--patterns',required=True);p.add_argument('--prompt',required=True);p.add_argument('--out',required=True);p.add_argument('--budget',type=int,default=2);p.add_argument('--source-root',required=True);p.add_argument('--ux-plan')
 p=s.add_parser('bind-source');p.add_argument('--ledger',required=True);p.add_argument('--source',nargs='+',required=True)
 p=s.add_parser('review');p.add_argument('--ledger',required=True);p.add_argument('--input',required=True)
 p=s.add_parser('amend-evidence');p.add_argument('--ledger',required=True);p.add_argument('--kind',choices=['analysis','patterns'],required=True);p.add_argument('--reason',required=True);p.add_argument('--observer',required=True)
 p=s.add_parser('attach-references');p.add_argument('--ledger',required=True);p.add_argument('--packet',required=True)
 p=s.add_parser('attach-interactions');p.add_argument('--ledger',required=True);p.add_argument('--checks',required=True);p.add_argument('--observer',required=True);p.add_argument('--basis',required=True)
 p=s.add_parser('revise-prompt');p.add_argument('--ledger',required=True);p.add_argument('--prompt',required=True);p.add_argument('--findings',nargs='+',required=True);p.add_argument('--module',required=True);p.add_argument('--expected',required=True)
 x=a.parse_args();root=Path(x.workspace).resolve(strict=True);require(root.is_dir() and root!=Path(root.anchor),'Explicit workspace directory required')
 result=prepare(root,x.id,x.analysis,x.patterns,x.prompt,x.out,x.budget,x.source_root,x.ux_plan) if x.mode=='prepare' else bind(root,x.ledger,x.source) if x.mode=='bind-source' else amend(root,x.ledger,x.kind,x.reason,x.observer) if x.mode=='amend-evidence' else attach(root,x.ledger,x.packet) if x.mode=='attach-references' else attach_interactions(root,x.ledger,x.checks,x.observer,x.basis) if x.mode=='attach-interactions' else revision(root,x.ledger,x.prompt,x.findings,x.module,x.expected) if x.mode=='revise-prompt' else review(root,x.ledger,x.input)
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
 sys.stdout.reconfigure(encoding='utf-8')
 try:main()
 except (GateError,ValueError,KeyError,TypeError,OSError) as e:print(json.dumps({'error':str(e)},ensure_ascii=False));sys.exit(2)
