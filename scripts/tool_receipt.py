"""Normalize supplied actual tool receipts. Does not invoke MCP or invent observation."""
import argparse,json,sys
from pathlib import Path
from pipeline import atomic,digest,file_record,image_info,load,nonempty,read_input,require,safe,timestamp

def normalize(root,receipt_path,out):
    receipt=read_input(root,receipt_path);timestamp(receipt.get('retrieved_at'))
    provider=receipt.get('provider');require(provider in {'mobbin','shadcn'},'Supported receipt provider is mobbin or shadcn')
    require(nonempty(receipt.get('tool')) and isinstance(receipt.get('request'),dict) and isinstance(receipt.get('result'),dict),'Actual tool name/request/result required')
    request=receipt['request'];result=receipt['result'];source={'path':receipt_path,'sha256':digest(safe(root,receipt_path,True)),'provider':provider,'tool':receipt['tool'],'request':request,'authenticity':'supplied external receipt; not independently authenticated by CLI'}
    if provider=='mobbin':
        require(receipt['tool'].split('__')[-1] in {'search_screens','search_flows'},'Use actual screen/flow tool receipt')
        require(request.get('output_destination')=='code' and nonempty(request.get('task_intent')) and nonempty(request.get('query')) and request.get('platform') in {'web','ios'},'Mobbin coding receipt needs code destination, consistent English task_intent, query and platform')
        require('output_mode' not in request,'Invented Mobbin output_mode is unsupported')
        collection=result.get('screens') if receipt['tool'].endswith('search_screens') else result.get('flows')
        require(isinstance(collection,list),'Mobbin result screens/flows array required')
        selected=[item for item in collection if item.get('id')==receipt.get('selected_id')];require(len(selected)==1,'Selected actual Mobbin id absent/duplicated')
        item=selected[0];require(item.get('platform')==request['platform'],'Selected Mobbin platform mismatch')
        if receipt.get('expected_app'):require(item.get('app_name')==receipt['expected_app'],'Selected Mobbin app identity mismatch')
        observed=receipt.get('observed',{});require(observed.get('method')=='actual-image-view' and nonempty(observed.get('observer')),'Actual full-resolution visual observer required');timestamp(observed.get('at'))
        asset=file_record(root,receipt.get('asset_path',''));asset.update(image_info(safe(root,asset['path'],True)));require(asset['sha256']==receipt.get('asset_sha256'),'Viewed full-resolution asset hash mismatch')
        if receipt['tool'].endswith('search_flows'):
            frames=[frame for frame in item.get('screens',[]) if frame.get('screen_id')==receipt.get('selected_screen_id')];require(len(frames)==1,'Observed flow frame id required')
            source['flow_frame_id']=frames[0]['screen_id'];source['flow_observation_limit']='One actual viewed frame does not prove the entire flow'
        notice=result.get('ai_usage_notice')
        if notice is not None:
            require(nonempty(notice.get('text')),'Malformed provider usage notice')
            require(receipt.get('notice_presented_verbatim') is True and receipt.get('presented_notice_text')==notice['text'],'Provider ai_usage_notice must be presented verbatim, separately after results')
            source['ai_usage_notice_text']=notice['text']
        value={'id':receipt.get('id'),'canonical_url':item.get('mobbin_url'),'asset_path':asset['path'],'asset_sha256':asset['sha256'],'observed':observed,'rights':receipt.get('rights'),'traits':receipt.get('traits'),'adapter_receipt':source,'source_identity':{'app':item.get('app_name'),'platform':item.get('platform'),'selected_id':item['id']}}
    else:
        require(receipt['tool'].split('__')[-1] in {'view_items_in_registries','get_item_examples_from_registries'},'Component receipt must include actual source/example retrieval')
        require(nonempty(receipt.get('registry')) and nonempty(receipt.get('registry_style')) and nonempty(receipt.get('framework_version')),'Registry/style/framework version evidence required')
        require(isinstance(receipt.get('files'),list) and receipt['files'],'Real retrieved component source files required')
        files=[file_record(root,item['path']) for item in receipt['files']]
        require(all(actual['sha256']==claimed.get('sha256') for actual,claimed in zip(files,receipt['files'])),'Component source hash mismatch')
        require(nonempty(receipt.get('license_evidence')) and isinstance(receipt.get('api'),dict) and receipt['api'],'Component license and actual API evidence required')
        require(receipt.get('local_library_gate') in {'not-run','pass','fail'},'Library gate status required')
        if receipt['local_library_gate']=='pass':require(nonempty(receipt.get('build_and_task_evidence')),'Library pass needs actual imports/build/task state evidence')
        value={'provider':provider,'adapter_receipt':source,'registry':receipt['registry'],'registry_style':receipt['registry_style'],'framework_version':receipt['framework_version'],'source_files':files,'license_evidence':receipt['license_evidence'],'api':receipt['api'],'local_library_gate':receipt['local_library_gate'],'build_and_task_evidence':receipt.get('build_and_task_evidence'),'visual':'not-inferred','human':'not-inferred'}
    require(safe(root,out)!=safe(root,receipt_path,True),'Receipt input must be preserved')
    atomic(safe(root,out),value,True)
    return {'status':'receipt-normalized','provider':provider,'out':out,'receipt_sha256':source['sha256'],'required_usage_notice':source.get('ai_usage_notice_text'),'limits':'Input attestation validation; no MCP invocation, pixel judgment or automatic library certification'}
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',required=True);parser.add_argument('--receipt',required=True);parser.add_argument('--out',required=True);args=parser.parse_args();sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    try:
        root=Path(args.workspace).resolve(strict=True);require(root.is_dir() and root!=Path(root.anchor),'Explicit non-root workspace required');print(json.dumps(normalize(root,args.receipt,args.out),ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError,TypeError,AttributeError) as error:print(json.dumps({'status':'error','error':str(error)},ensure_ascii=False));sys.exit(2)
