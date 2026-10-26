"""Accumulate and retrieve sourced visual patterns across actual iterations."""
import argparse,json,sys,re
from pathlib import Path
from pipeline import safe,load,atomic,require,GateError,digest
from pattern_loop import validate

def ingest(root,packet_path,catalog_path,campaign):
    require(bool(re.fullmatch(r'[a-z0-9-]{1,64}',campaign)), 'Explicit campaign ID required')
    source=safe(root,packet_path,True);packet=load(source);validate(root,packet)
    target=safe(root,catalog_path)
    catalog=load(target) if target.exists() else {'version':'1.0','patterns':[],'history':[]}
    require(catalog.get('version')=='1.0' and isinstance(catalog.get('patterns'),list), 'Unsupported catalog')
    sources={s['id']:s for s in packet['sources']};by_id={p['id']:p for p in catalog['patterns']}
    require(len(by_id)==len(catalog['patterns']), 'Duplicate catalog IDs')
    event={'campaign':campaign,'packet_sha256':digest(source),'changes':[]}
    for item in packet['patterns']:
        basis=sources[item['source_id']]
        # Retain descriptions, provenance and hashes; never private pixels or temporary download URLs.
        stored={**item,'source':{k:basis[k] for k in ['id','canonical_url','app','platform','visible_state','kind','rights','observer']},'source_evidence_sha256':basis['evidence']['sha256'],'campaign':campaign,'human_acceptance':'pending'}
        stored.pop('measurement_evidence',None)
        old=by_id.get(item['id'])
        if old==stored:continue
        if old:event['changes'].append({'id':item['id'],'previous':old})
        else:event['changes'].append({'id':item['id'],'previous':None})
        by_id[item['id']]=stored
    if event['changes']:
        catalog['patterns']=sorted(by_id.values(),key=lambda x:x['id']);catalog['history'].append(event);atomic(target,catalog)
    return {'patterns':len(by_id),'changes':len(event['changes']),'catalog':catalog_path,'source_pixels_copied':False}

def search(data,query='',role=None,platform=None,limit=8):
    require(data.get('version')=='1.0' and isinstance(data.get('patterns'),list), 'Unsupported catalog')
    require(1<=limit<=50,'Limit must be1..50')
    terms=set(re.findall(r'[\w-]+',query.lower()));matches=[]
    for p in data['patterns']:
        if role and p['role']!=role:continue
        if platform and p['source']['platform']!=platform:continue
        words=set(re.findall(r'[\w-]+',json.dumps(p,ensure_ascii=False).lower()));score=len(terms&words)
        if terms and not score:continue
        matches.append({'id':p['id'],'score':score,'role':p['role'],'origin':p['kind'],'observation':p['observation'],'directive':p['directive'],'suitable_for':p['suitable_for'],'unsuitable_for':p['unsuitable_for'],'source':p['source'],'human_acceptance':p['human_acceptance']})
    return sorted(matches,key=lambda x:(-x['score'],x['id']))[:limit]

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--workspace',required=True);a.add_argument('--catalog',required=True)
    sub=a.add_subparsers(dest='mode',required=True)
    s=sub.add_parser('ingest');s.add_argument('--packet',required=True);s.add_argument('--campaign',required=True)
    s=sub.add_parser('search');s.add_argument('query',nargs='?',default='');s.add_argument('--role');s.add_argument('--platform');s.add_argument('--limit',type=int,default=8)
    x=a.parse_args();root=Path(x.workspace).resolve(strict=True);require(root.is_dir() and root!=Path(root.anchor),'Explicit workspace directory required')
    result=ingest(root,x.packet,x.catalog,x.campaign) if x.mode=='ingest' else {'method':'deterministic terms and exact role/platform filters','results':search(load(safe(root,x.catalog,True)),x.query,x.role,x.platform,x.limit)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:main()
    except (GateError,ValueError,TypeError,KeyError,OSError) as e:print(json.dumps({'error':str(e)},ensure_ascii=False));sys.exit(2)
