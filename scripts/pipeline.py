"""Bounded, evidence-recorded design loop. Generation and pixel inspection are external."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import struct
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse,parse_qsl,urlencode
import zlib

VERSION = '0.3.0'
PACKAGE_ROOT=Path(__file__).resolve().parents[1]
ASPECTS = {'composition', 'typography', 'spacing', 'material', 'color', 'responsive'}
BASIS = {'observed', 'inferred', 'proposed'}
class GateError(ValueError): pass
def require(ok, message):
    if not ok: raise GateError(message)
def now(): return datetime.now(timezone.utc).isoformat()
def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path): return json.loads(path.read_text(encoding='utf-8-sig'))
def task_hash(task):return hashlib.sha256(json.dumps(task,sort_keys=True).encode()).hexdigest()
def nonempty(value): return isinstance(value, str) and bool(value.strip())
def view_query(value):
    if not value:return ''
    require(isinstance(value,str) and len(value)<=2048 and not value.startswith('?'),'View query must be a query string without leading ?, bounded to2048 characters')
    try:pairs=parse_qsl(value,keep_blank_values=True,strict_parsing=True)
    except ValueError:raise GateError('Invalid view query; expected key=value pairs')
    require(pairs and len({key for key,_ in pairs})==len(pairs) and all(re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*',key) for key,_ in pairs),'View query keys must be unique safe names')
    return urlencode(pairs)
def ident(value):
    require(isinstance(value, str) and re.fullmatch(r'[a-z][a-z0-9-]{0,63}', value), 'Invalid id: use lowercase letters, numbers and hyphens')
    return value
def timestamp(value):
    require(nonempty(value), 'Timestamp required')
    try: dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError: raise GateError('Invalid ISO timestamp')
    require(dt.tzinfo is not None and dt <= datetime.now(timezone.utc), 'Timestamp must have timezone and cannot be in the future')
def canonical_workspace(value, exists=True):
    """Normalize a workspace once, before helpers compare canonical child paths.

    Windows 8.3 names can resolve to a different spelling without being links.
    Inspect the supplied lexical ancestors before resolving so real links and
    reparse points remain rejected rather than disappearing during normalization.
    """
    raw = Path(value).expanduser().absolute()
    for node in (raw, *raw.parents):
        try:
            metadata = node.lstat()
        except (FileNotFoundError, NotADirectoryError):
            continue
        require(not stat.S_ISLNK(metadata.st_mode) and not getattr(metadata, 'st_file_attributes', 0) & 0x400,
                'Symlink/reparse workspace ancestor rejected')
    root = raw.resolve(strict=exists)
    require(root != Path(root.anchor) and (not exists or root.is_dir()),
            'Workspace must be an explicit non-root directory' + (' that exists' if exists else ''))
    return root
def safe(root, relative, exists=False):
    """Resolve a child under a canonical root; callers normalize their root once."""
    value = str(relative)
    win, pos = PureWindowsPath(value), PurePosixPath(value.replace('\\', '/'))
    require(value and value not in ('.', './') and not win.drive and not win.is_absolute() and not pos.is_absolute() and '..' not in pos.parts, 'Unsafe path: expected workspace-relative file')
    reserved = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1,10)), *(f'LPT{i}' for i in range(1,10))}
    require(all(':' not in part and not part.endswith(('.', ' ')) and part.split('.')[0].upper() not in reserved for part in pos.parts), 'Unsafe Windows path')
    raw = root.joinpath(*pos.parts)
    for node in (raw, *raw.parents):
        try:
            metadata = node.lstat()
        except (FileNotFoundError, NotADirectoryError):
            metadata = None
        if metadata is not None:
            require(not stat.S_ISLNK(metadata.st_mode) and not getattr(metadata, 'st_file_attributes', 0) & 0x400, 'Symlink/reparse path rejected')
        if node == root: break
    target = raw.resolve(strict=exists)
    require(target.is_relative_to(root), 'Path escapes workspace')
    return target
def read_input(root, relative):
    require(not PurePosixPath(relative.replace('\\','/')).parts[0] in ('campaigns','exports'), 'Input must be outside managed campaigns/exports')
    value = load(safe(root, relative, True)); require(isinstance(value,dict),'Input must be a JSON object'); return value
def atomic(path, value, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not exclusive or not path.exists(), 'Existing record preserved: '+str(path))
    content = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2)+'\n'
    fd, name = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)
def png_info(path):
    data = path.read_bytes()
    require(data[:8] == b'\x89PNG\r\n\x1a\n', 'Actual PNG required: '+str(path))
    offset, dimensions, end, compressed, header = 8, None, False, bytearray(), None
    while offset < len(data):
        require(offset+12 <= len(data), 'Truncated PNG chunk')
        size = struct.unpack('>I', data[offset:offset+4])[0]
        kind, body = data[offset+4:offset+8], data[offset+8:offset+8+size]
        require(offset+size+12 <= len(data), 'Truncated PNG data')
        crc = struct.unpack('>I', data[offset+8+size:offset+12+size])[0]
        require(zlib.crc32(kind+body) & 0xffffffff == crc, 'PNG checksum mismatch')
        if dimensions is None:
            require(kind == b'IHDR' and size == 13, 'PNG missing initial IHDR')
            dimensions = struct.unpack('>II', body[:8]); require(all(0 < v <= 20000 for v in dimensions), 'Invalid PNG dimensions')
            depth,color,compression,filtering,interlace = body[8:]
            depths = {0:{1,2,4,8,16},2:{8,16},4:{8,16},6:{8,16}}
            require(color in depths and depth in depths[color] and compression == filtering == interlace == 0, 'Unsupported PNG header; use a non-interlaced standard PNG')
            channels = {0:1,2:3,3:1,4:2,6:4}[color]
            rowbytes = (dimensions[0]*channels*depth+7)//8
            header = (rowbytes,dimensions[1])
            require((rowbytes+1)*dimensions[1] <= 128*1024*1024,'PNG decoded size exceeds supported limit')
        else: require(kind != b'IHDR','Duplicate PNG header')
        if kind == b'IDAT': compressed.extend(body)
        offset += size+12
        if kind == b'IEND': require(size == 0,'Invalid PNG end'); end = True; break
    require(end and compressed and offset == len(data), 'PNG missing image data/end or has trailing data')
    expected = (header[0]+1)*header[1]
    try:
        decoder = zlib.decompressobj()
        decoded = decoder.decompress(compressed,expected+1)
    except zlib.error: raise GateError('Invalid compressed PNG pixels')
    require(len(decoded) == expected and decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail, 'PNG scanline data length mismatch')
    require(all(decoded[offset] <= 4 for offset in range(0,expected,header[0]+1)), 'Invalid PNG scanline filter')
    return {'width': dimensions[0], 'height': dimensions[1]}
def jpeg_info(path):
    """Marker/header integrity only; actual visual decode/view is external."""
    data = path.read_bytes(); require(data[:2] == b'\xff\xd8', 'JPEG SOI header required')
    offset, dimensions, scans, entropy = 2, None, 0, 0
    while offset < len(data):
        require(data[offset] == 255, 'Invalid JPEG marker boundary')
        while offset < len(data) and data[offset] == 255: offset += 1
        require(offset < len(data), 'Truncated JPEG marker')
        marker = data[offset]; offset += 1
        if marker == 0xd9:
            require(offset == len(data) and dimensions and scans and entropy, 'JPEG missing frame/scan/end or has trailing data')
            return {'width':dimensions[0], 'height':dimensions[1], 'format':'jpeg', 'validation':'marker/header integrity; not full pixel decode'}
        require(marker not in (0x00,0xd8) and not 0xd0 <= marker <= 0xd7, 'Invalid standalone JPEG marker')
        if marker == 0x01: continue
        require(offset+2 <= len(data), 'Truncated JPEG segment length')
        length = struct.unpack('>H',data[offset:offset+2])[0]
        require(length >= 2 and offset+length <= len(data), 'Truncated JPEG segment')
        body = data[offset+2:offset+length]; offset += length
        if marker in {0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf}:
            require(len(body)>=6 and len(body)==6+3*body[5], 'Invalid JPEG frame header')
            height,width = struct.unpack('>HH',body[1:5]); require(all(0<v<=20000 for v in (width,height)), 'Invalid JPEG dimensions')
            require(dimensions is None or dimensions==(width,height),'Conflicting JPEG frame dimensions'); dimensions=(width,height)
        if marker == 0xda:
            require(dimensions and len(body)>=4 and len(body)==4+2*body[0], 'JPEG scan missing/invalid frame or scan header')
            scans += 1; start = offset
            while offset < len(data):
                if data[offset] != 255: offset += 1; continue
                require(offset+1<len(data),'Truncated JPEG entropy marker')
                if data[offset+1] == 0 or 0xd0 <= data[offset+1] <= 0xd7: offset += 2; continue
                break
            entropy += offset-start
    raise GateError('JPEG missing EOI end marker')
def image_info(path):
    signature = path.read_bytes()[:8]
    if signature.startswith(b'\xff\xd8'): return jpeg_info(path)
    if signature == b'\x89PNG\r\n\x1a\n': return {**png_info(path),'format':'png','validation':'header/chunk/scanline integrity; not visual observation'}
    raise GateError('Reference requires actual PNG or JPEG bytes')
def file_record(root, relative, png=False):
    path = safe(root, relative, True); require(path.is_file() and path.stat().st_size > 0, 'Expected nonempty file: '+relative)
    return {'path': path.relative_to(root).as_posix(), 'sha256': digest(path), 'bytes': path.stat().st_size, **(png_info(path) if png else {})}
def current(root, record):
    try: return digest(safe(root, record['path'], True)) == record['sha256']
    except OSError: return False
def closure_files(root, relative):
    folder = safe(root,relative,True); require(folder.is_dir(),'Source closure root must be a directory')
    require(PurePosixPath(folder.relative_to(root).as_posix()).parts[0] not in ('campaigns','exports'),'Closure root cannot contain managed evidence/exports')
    files = []
    for current_dir,dirs,names in os.walk(folder,followlinks=False):
        for name in [*dirs,*names]: safe(root,(Path(current_dir)/name).relative_to(root).as_posix(),True)
        for name in names:
            path=Path(current_dir)/name; require(path.is_file() and path.stat().st_size>0,'Empty/non-file closure member rejected')
            files.append({'path':path.relative_to(folder).as_posix(),'sha256':digest(path)})
    require(files,'Source closure has no files'); return sorted(files,key=lambda item:item['path'])
def validate_closure(root, data):
    require(isinstance(data,dict) and data.get('ownership') in {'active','run-transient'},'Closure ownership must be active or run-transient')
    folder = safe(root,data.get('root',''),True)
    if data['ownership']=='run-transient': require(folder.relative_to(root).parts[0] in {'generated','transient'},'Run-transient closure must be below generated/ or transient/; active app protected')
    entry = safe(folder,data.get('entry',''),True); require(entry.is_file() and entry.suffix.lower()=='.html','Closure entry must be an existing HTML file')
    require(isinstance(data.get('files'),list) and data['files'],'Closure files list required')
    normalized = []
    for item in data['files']:
        file = safe(folder,item.get('path',''),True); require(file.is_file(),'Closure member is not a file')
        require(isinstance(item.get('sha256'),str) and re.fullmatch('[a-f0-9]{64}',item['sha256']),'Closure member SHA-256 required')
        normalized.append({'path':file.relative_to(folder).as_posix(),'sha256':item['sha256']})
    require(len({item['path'] for item in normalized})==len(normalized),'Duplicate/aliased closure member')
    require(sorted(normalized,key=lambda item:item['path']) == closure_files(root,data['root']),'Source closure stale/incomplete: exact file set and hashes must match')
    require(entry.relative_to(folder).as_posix() in {item['path'] for item in normalized},'Closure entry is not tracked')
    return {'root':folder.relative_to(root).as_posix(),'entry':entry.relative_to(folder).as_posix(),'ownership':data['ownership'],'files':sorted(normalized,key=lambda item:item['path'])}
def source_manifest(root,args):
    data={'root':args.source_root,'entry':args.entry,'ownership':args.ownership,'files':closure_files(root,args.source_root)}
    data=validate_closure(root,data)
    require(PurePosixPath(args.out.replace('\\','/')).parts[0] not in {'campaigns','exports','generated'},'Manifest output must be separate input/evidence, not inside built closure')
    require(not safe(root,args.out).is_relative_to(safe(root,data['root'],True)),'Source manifest output cannot enter its own pinned closure')
    atomic(safe(root,args.out),data,True)
    return {'status':'source-manifest-written','path':args.out,'files':len(data['files']),'entry':data['entry']}
def pinned_closure(root,record):
    if not record.get('source_manifest'): return None
    pinned=record['source_manifest']; require(current(root,pinned),'Source manifest changed/missing; review invalidated')
    closure=validate_closure(root,load(safe(root,pinned['path'],True)))
    require(closure == pinned['closure'],'Pinned source closure differs; review invalidated')
    return closure
def library_search(root,args):
    manifest_path=PACKAGE_ROOT/'library/manifest.json';data=load(manifest_path);items=data['items'];ids={item['id'] for item in items}
    require(1<=args.limit<=50,'Library result limit must be1..50')
    require(len(ids)==len(items),'Duplicate library id')
    for item in items:
        require(item.get('type') in {'component','pattern','example'},'Unknown library type')
        license=item.get('license',{});require(license.get('spdx') in {'MIT','Apache-2.0','BSD-2-Clause','BSD-3-Clause','ISC'} and current(PACKAGE_ROOT,{'path':license.get('notice',''),'sha256':license.get('sha256')}),'Library license/notice unsupported, missing or stale')
        for file in item.get('source_files',[]):require(current(PACKAGE_ROOT,file),'Library source stale/missing: '+file['path'])
        for field in ('api','dependencies','provenance'):
            if item.get(field):require(safe(PACKAGE_ROOT,item[field],True).is_file(),'Library '+field+' pointer missing')
        require(all(value in ids for value in item.get('composition',[])),'Library pattern contains unknown component id')
        if item.get('example'):require(item['example'] in ids,'Library pattern example missing')
    query=set(re.findall(r'[\w-]+',args.query.lower()));results=[]
    for item in items:
        facets={'job':'job','platform':'platform','state':'states','stack':'stack','entity':'entities','action':'actions','density':'density','accessibility':'accessibility'}
        if any(getattr(args,key,None) and getattr(args,key) not in item.get(field,[]) for key,field in facets.items()):continue
        if args.type and item['type']!=args.type:continue
        words=set(re.findall(r'[\w-]+',json.dumps(item,ensure_ascii=False).lower()));overlap=query&words
        if query and not overlap:continue
        score=sum(3 if word in item['title'].lower() else 1 for word in overlap)
        results.append({'id':item['id'],'type':item['type'],'title':item['title'],'score':score,'job':item.get('job',[]),'states':item.get('states',[]),'stack':item.get('stack',[]),'source_files':item.get('source_files',[]),'composition':item.get('composition',[]),'example':item.get('example'),'license':item['license'],'verification':item['verification'],'limitations':item.get('limitations',[]),'api':item.get('api')})
    return {'status':'pass','version':data['version'],'manifest_sha256':digest(manifest_path),'method':'Deterministic token overlap plus exact facets; id tie-break; inspected source/notice hashes','results':sorted(results,key=lambda item:(-item['score'],item['id']))[:args.limit]}
def campaign(root, name):
    folder = safe(root, 'campaigns/'+ident(name), True)
    # Managed record directories must not redirect reads/writes via a nested link.
    for current_dir, dirs, files in os.walk(folder, followlinks=False):
        for name in [*dirs,*files]:
            node = Path(current_dir)/name
            require(not node.is_symlink() and not getattr(node.lstat(),'st_file_attributes',0)&0x400, 'Managed record symlink/reparse path rejected')
    return folder, load(folder/'campaign.json')
def task_history(folder,state):
    current_hash=task_hash(state['task']);revision=state.get('task_revision',0)
    if not revision:
        require(not state.get('task_sha256') or state['task_sha256']==current_hash,'Task changed without audited amendment')
        return {current_hash}
    origin_path=folder/'task-origin.json';origin=load(origin_path);previous=origin['task'];previous_hash=task_hash(previous)
    require(previous_hash==origin['task_sha256'],'Task origin snapshot hash mismatch')
    known={previous_hash};previous_record=digest(origin_path)
    for number in range(1,revision+1):
        path=folder/'task-amendments'/f'{number}.json';entry=load(path)
        require(entry['revision']==number and entry['previous_record_sha256']==previous_record and entry['old_task']==previous and entry['old_task_sha256']==previous_hash,'Task amendment chain mismatch')
        require(task_hash(entry['new_task'])==entry['new_task_sha256'] and nonempty(entry['reason']) and nonempty(entry['author']),'Task amendment snapshot/reason/author invalid')
        previous=entry['new_task'];previous_hash=entry['new_task_sha256'];previous_record=digest(path);known.add(previous_hash)
    require(previous_record==state.get('task_ledger_sha256') and previous_hash==current_hash and state['task']==previous,'Current task differs from audited amendment ledger')
    return known
def validate_task(task):
    require(nonempty(task.get('job')) and nonempty(task.get('scope')), 'Task job and scope required')
    for key in ('factual_data','interactions','constraints'):require(isinstance(task.get(key),list) and task[key] and all(nonempty(v) for v in task[key]),'Task '+key+' must contain concrete preserved contracts')
def task_amend(root,args):
    folder,state=campaign(root,args.campaign);task_history(folder,state);new=read_input(root,args.task);validate_task(new)
    require(nonempty(args.reason) and nonempty(args.author),'Audited correction needs concrete reason and named author')
    old=state['task'];old_hash=task_hash(old);new_hash=task_hash(new);require(new_hash!=old_hash,'No task change to amend')
    revision=state.get('task_revision',0)+1
    if revision==1:
        for prompt in folder.glob('*/*/prompt.json'):require(load(prompt)['task_sha256']==old_hash,'Prior prompt task hash differs from unamended current task; refuse to legitimize unlogged mutation')
        atomic(folder/'task-origin.json',{'task':old,'task_sha256':old_hash,'recorded_at':now()},True);previous_record=digest(folder/'task-origin.json')
    else:previous_record=state['task_ledger_sha256']
    entry={'revision':revision,'created_at':now(),'reason':args.reason,'author':args.author,'old_task':old,'old_task_sha256':old_hash,'new_task':new,'new_task_sha256':new_hash,'previous_record_sha256':previous_record,'effect':'Prior task-dependent approval/actions stale; historical critique may inform next compile; budgets unchanged'}
    path=folder/'task-amendments'/f'{revision}.json';atomic(path,entry,True)
    state.update({'task':new,'task_sha256':new_hash,'task_revision':revision,'task_ledger_sha256':digest(path)});atomic(folder/'campaign.json',state)
    return {'status':'task-amended','revision':revision,'old_task_sha256':old_hash,'new_task_sha256':new_hash,'record':path.relative_to(root).as_posix(),'prior_reviews':'historical only; no retroactive fresh approval','budgets_changed':False}
def iteration(root, args):
    folder, state = campaign(root, args.campaign); ident(args.variant)
    require(args.variant in state['variants'], 'Unknown variant')
    require(args.iteration in state['variants'][args.variant]['iterations'], 'Unknown iteration')
    return folder, state, folder/args.variant/str(args.iteration)
def ref_current(root, folder, prompt):
    reference = load(folder/'references'/f"{prompt['reference_id']}.json")
    require(digest(folder/'references'/f"{prompt['reference_id']}.json") == prompt['reference_sha256'], 'Reference analysis changed; recompile required')
    require(current(root, {'path': reference['asset_path'], 'sha256': reference['asset_sha256']}), 'Reference asset changed/missing/evicted; fresh inspection and new reference required')
    if reference.get('adapter_receipt'): require(current(root,reference['adapter_receipt']),'Reference tool receipt changed/missing; provenance review invalidated')
    return reference
def render_current(root, folder, out,allow_amended_task=False):
    prompt = load(out/'prompt.json'); ref_current(root, folder, prompt)
    state=load(folder/'campaign.json');known=task_history(folder,state)
    require(prompt['task_sha256']==task_hash(state['task']) or (allow_amended_task and prompt['task_sha256'] in known),'Task changed; prior prompt and review invalidated for current approval')
    if state.get('task_revision') and not allow_amended_task:require(prompt.get('task_revision',0)==state['task_revision'] and prompt.get('task_ledger_sha256')==state['task_ledger_sha256'],'Historical task revision cannot be reused for current approval')
    require(digest(out/'prompt.md') == prompt['prompt_sha256'], 'Prompt changed; recompile required')
    render = load(out/'render.json')
    require(render['prompt_sha256'] == prompt['prompt_sha256'], 'Render has stale prompt')
    require(all(current(root, item) for item in [render['source'], *render['pngs']]), 'Rendered source/PNG changed or missing; review invalidated')
    pinned_closure(root,render)
    if render.get('capture_record'):require(current(root,render['capture_record']),'Actual capture record changed/missing; review invalidated')
    return prompt, render
def review_current(root, folder, out,allow_amended_task=False):
    prompt, render = render_current(root, folder, out,allow_amended_task); record = load(out/'review.json')
    require(record['source_sha256'] == render['source']['sha256'] and record['png_sha256s'] == [p['sha256'] for p in render['pngs']], 'Review hash mismatch')
    require(record['render_sha256'] == digest(out/'render.json'), 'Review is stale')
    return prompt, render, record
def create(root, args):
    ident(args.campaign); require(1 <= args.iterations <= 12 and 1 <= args.variants <= 6, 'Budget out of bounds: iterations 1..12, variants 1..6')
    task = read_input(root, args.task)
    validate_task(task)
    out = safe(root, 'campaigns/'+args.campaign); require(not out.exists(), 'Campaign already exists')
    state = {'version': VERSION, 'id': args.campaign, 'created_at': now(), 'max_iterations':args.iterations, 'max_variants':args.variants, 'variants':{}, 'task':task,'task_sha256':task_hash(task),'task_revision':0, 'references':[], 'tombstones':[]}
    atomic(out/'campaign.json', state, True)
    return {'status':'created','campaign':args.campaign,'budget':{'iterations_per_variant':args.iterations,'variants':args.variants}}
def reference(root, args):
    folder, state = campaign(root, args.campaign); data = read_input(root, args.analysis); rid = ident(data.get('id'))
    url = urlparse(data.get('canonical_url',''))
    require(url.scheme == 'https' and url.netloc and not url.username and not url.password, 'Canonical HTTPS URL required')
    asset = file_record(root, data.get('asset_path',''))
    asset.update(image_info(safe(root,asset['path'],True)))
    require(not asset['path'].startswith(('campaigns/','exports/')), 'Reference pixels must be outside managed records/exports')
    require(asset['sha256'] == data.get('asset_sha256'), 'Observed reference asset hash mismatch')
    observed, rights = data.get('observed',{}), data.get('rights',{})
    require(nonempty(observed.get('observer')) and observed.get('method') == 'actual-image-view', 'Unobserved asset rejected: actual-image-view observer required')
    timestamp(observed.get('at'))
    require(rights.get('status') == 'permitted' and rights.get('purpose') == 'visual-analysis' and nonempty(rights.get('evidence')), 'Unknown/unsupported rights for visual-analysis purpose')
    traits = data.get('traits',[]); require(isinstance(traits,list) and traits, 'Observed traits required')
    ids = set()
    for trait in traits:
        tid = ident(trait.get('id')); require(tid not in ids, 'Duplicate trait id'); ids.add(tid)
        require(trait.get('aspect') in ASPECTS and trait.get('basis') in BASIS and nonempty(trait.get('description')), 'Invalid reference trait')
    require(any(t['basis'] == 'observed' for t in traits), 'Reference must contain observed visual traits')
    receipt=data.get('adapter_receipt')
    if receipt:
        require(current(root,receipt),'Actual reference receipt hash/path mismatch')
        if receipt.get('provider')=='mobbin':
            request=receipt.get('request',{});require(request.get('output_destination')=='code' and nonempty(request.get('task_intent')),'Mobbin coding reference needs code destination and task_intent')
            for prior in state['references']:
                prior_receipt=load(folder/'references'/f'{prior}.json').get('adapter_receipt',{})
                if prior_receipt.get('provider')=='mobbin':
                    prior_request=prior_receipt['request'];require(all(request.get(k)==prior_request.get(k) for k in ('output_destination','task_intent','output_tool')),'Mobbin same-task destination/intent/output_tool mismatch')
    out = folder/'references'/f'{rid}.json'; atomic(out, data, True)
    state['references'].append(rid); atomic(folder/'campaign.json',state)
    return {'status':'reference-recorded','id':rid,'analysis_sha256':digest(out),'asset':asset,'rights_scope':'visual-analysis only; source pixels are not redistributable by this record'}
def compile_prompt(root, args):
    folder, state = campaign(root, args.campaign); variant = ident(args.variant); rid = ident(args.reference)
    task_history(folder,state)
    require(rid in state['references'], 'Unknown reference')
    reference_path = folder/'references'/f'{rid}.json'; ref = load(reference_path)
    require(current(root, {'path':ref['asset_path'],'sha256':ref['asset_sha256']}), 'Reference asset changed/missing/evicted; reinspection required')
    if ref.get('adapter_receipt'):require(current(root,ref['adapter_receipt']),'Reference tool receipt changed/missing; reinspection required')
    variants = state['variants']; require(variant in variants or len(variants) < state['max_variants'], 'Variant budget exhausted')
    info = variants.get(variant, {'iterations':[], 'best_so_far':None})
    number = len(info['iterations'])+1; require(number <= state['max_iterations'], 'Iteration budget exhausted; await user or keep reviewed candidate')
    spec = read_input(root,args.spec); require(nonempty(spec.get('intent')), 'Concrete prompt intent required')
    directives = spec.get('directives',[]); require(isinstance(directives,list) and directives, 'Prompt directives required')
    traits = {t['id']:t for t in ref['traits']}; covered = set()
    for directive in directives:
        require(directive.get('trait_id') in traits and directive.get('basis') in BASIS and nonempty(directive.get('decision')), 'Each concrete directive must trace to a known reference trait and basis')
        covered.add(traits[directive['trait_id']]['aspect'])
    require(ASPECTS <= covered, 'Prompt lacks concrete aspects: '+', '.join(sorted(ASPECTS-covered)))
    delta = spec.get('delta_findings',[]); require(isinstance(delta,list), 'delta_findings must be a list')
    previous = None
    if number > 1:
        previous_out = folder/variant/str(number-1)
        previous_prompt, _, previous = review_current(root,folder,previous_out,allow_amended_task=True)
        findings = {f['id'] for f in previous['findings']}
        require(set(delta) <= findings and (not findings or delta), 'Revision must cite previous concrete finding ids')
    else: require(not delta, 'First prompt cannot cite nonexistent prior findings')
    lines = [f'# Generation handoff: {args.campaign}/{variant}/{number}', '', spec['intent'], '', '## Preserve task contract', json.dumps(state['task'],ensure_ascii=False,indent=2), '', '## Reference provenance', f"Canonical URL: {ref['canonical_url']}", f"Viewed asset SHA-256: {ref['asset_sha256']}", f"Analysis SHA-256: {digest(reference_path)}", '', '## Concrete visual instructions']
    if state.get('task_revision'):lines += ['',f"Audited task revision {state['task_revision']}; ledger SHA-256 {state['task_ledger_sha256']}. Previous critique may be historical; prior approval is not renewed by this correction."]
    for item in directives:
        trait = traits[item['trait_id']]
        lines.append(f"- [{item['basis']}; trait {trait['id']} / {trait['aspect']}; source basis {trait['basis']}] {item['decision']}\n  Reference observation: {trait['description']}")
    lines += ['', '## Prior critique deltas', json.dumps([f for f in previous['findings'] if f['id'] in delta],ensure_ascii=False,indent=2) if previous else 'Initial generation.', '', '## Required external execution', 'Generate real source using this prompt. Render desktop and mobile; capture actual PNGs. Inspect pixels against the reference and record concrete findings. Preserve factual values, labels and interaction contracts. Do not treat technical success as visual or human approval.']
    out = folder/variant/str(number); atomic(out/'prompt.md','\n'.join(lines)+'\n', True)
    prompt = {'version':VERSION,'iteration':number,'reference_id':rid,'reference_sha256':digest(reference_path),'spec':spec,'task_sha256':task_hash(state['task']),'task_revision':state.get('task_revision',0),'task_ledger_sha256':state.get('task_ledger_sha256'),'prompt_sha256':digest(out/'prompt.md'),'created_at':now()}
    atomic(out/'prompt.json',prompt,True); info['iterations'].append(number); variants[variant] = info; atomic(folder/'campaign.json',state)
    return {'status':'external-generation-required','iteration':number,'prompt':str((out/'prompt.md').relative_to(root)).replace('\\','/'),'prompt_sha256':prompt['prompt_sha256']}
def render(root, args):
    folder, state, out = iteration(root,args); prompt = load(out/'prompt.json'); ref_current(root,folder,prompt)
    task_history(folder,state);require(prompt['task_sha256']==task_hash(state['task']),'Prompt task superseded by audited correction; compile the next prompt')
    if state.get('task_revision'):require(prompt.get('task_revision',0)==state['task_revision'] and prompt.get('task_ledger_sha256')==state['task_ledger_sha256'],'Prompt revision superseded; compile the next prompt')
    require(digest(out/'prompt.md') == prompt['prompt_sha256'], 'Prompt changed; recompile required')
    source = file_record(root,args.source); require(Path(args.source).suffix.lower() in ('.html','.js','.mjs','.jsx','.tsx','.vue','.svelte'), 'Generated source file type unsupported')
    require(nonempty(args.generator), 'Actual external generator/run identity required')
    pngs = [file_record(root,p,True) for p in args.png]; require(len({p['path'] for p in pngs}) == len(pngs), 'Duplicate PNG path')
    for item in [source,*pngs]: require(not item['path'].startswith(('campaigns/','exports/')), 'Generated artifacts must be outside managed records/exports')
    reference_paths = {safe(root,load(folder/'references'/f'{r}.json')['asset_path'],True) for r in state['references']}
    require(not any(safe(root,item['path'],True) in reference_paths for item in [source,*pngs]), 'Generated output cannot overwrite reference assets')
    record = {'created_at':now(),'prompt_sha256':prompt['prompt_sha256'],'generator':args.generator,'source':source,'pngs':pngs,'review_status':'not-run'}
    record['view_query']=view_query(getattr(args,'view_query',''))
    if getattr(args,'source_manifest',None):
        manifest=file_record(root,args.source_manifest); closure=validate_closure(root,read_input(root,args.source_manifest))
        require(safe(root,source['path'],True)==safe(root,closure['root'],True)/closure['entry'],'Rendered source must equal closure HTML entry')
        closure_paths={safe(root,closure['root'],True)/item['path'] for item in closure['files']}
        require(not closure_paths.intersection(reference_paths),'Source closure contains private reference pixels')
        require(not any(safe(root,p['path'],True) in closure_paths for p in pngs),'PNG capture cannot be inside source closure')
        record['source_manifest']={**manifest,'closure':closure}
    if getattr(args,'capture_record',None):
        capture=file_record(root,args.capture_record);data=load(safe(root,capture['path'],True))
        require(data.get('passed') is True,'Actual capture record reports failure/not-run')
        require(record.get('source_manifest') and data.get('source_manifest',{}).get('sha256')==record['source_manifest']['sha256'] and data['source_manifest'].get('closure')==record['source_manifest']['closure'],'Actual capture source closure mismatch')
        require([(p['path'],p['sha256']) for p in data.get('screenshots',[])]==[(p['path'],p['sha256']) for p in pngs],'Actual capture PNG list/hash mismatch')
        captured_query=view_query(data.get('view_query',''))
        require(not getattr(args,'view_query','') or record['view_query']==captured_query,'Capture/query variant mismatch')
        record['view_query']=captured_query;record['capture_record']=capture
    atomic(out/'render.json',record,True)
    return {'status':'render-recorded','source':source,'pngs':pngs,'source_manifest':record.get('source_manifest'),'next':'Inspect these actual PNGs; record independent statuses honestly'}
def review(root, args):
    folder,state,out = iteration(root,args);historical=bool(getattr(args,'historical_task',False));prompt,rendered = render_current(root,folder,out,allow_amended_task=historical); data = read_input(root,args.record)
    if historical:require(state.get('task_revision',0)>0 and prompt.get('task_revision',0)<state['task_revision'],'Historical review requires an older prompt under a valid audited amendment ledger')
    require(nonempty(data.get('observer')), 'Named pixel reviewer required'); timestamp(data.get('inspected_at'))
    require(data.get('source_sha256') == rendered['source']['sha256'] and data.get('png_sha256s') == [p['sha256'] for p in rendered['pngs']], 'Stale artifact review: source and ordered PNG hashes must match')
    pixels = data.get('pixel_observations',[])
    require(isinstance(pixels,list) and {p.get('png_sha256') for p in pixels} == set(data['png_sha256s']) and all(nonempty(p.get('observation')) for p in pixels), 'Actual pixel observation for every PNG required')
    for key, statuses in [('technical',{'pass','fail','not-run'}),('visual',{'candidate','revise','not-run'}),('human',{'accepted','rejected','not-run'})]:
        require(data.get(key,{}).get('status') in statuses and nonempty(data[key].get('evidence')), 'Invalid '+key+' status/evidence')
    independent = data.get('independent',{})
    require(all(independent.get(k) in {'pass','fail','not-run'} for k in ('technical','visual')) and nonempty(independent.get('evidence')), 'Independent review statuses/evidence required')
    if any(independent.get(k) != 'not-run' for k in ('technical','visual')):
        require(nonempty(independent.get('reviewer')) and independent['reviewer'] != data['observer'], 'Independent pass/fail requires a different named reviewer')
    findings = data.get('findings'); require(isinstance(findings,list), 'Concrete findings array required'); ids = set()
    for finding in findings:
        fid = ident(finding.get('id')); require(fid not in ids,'Duplicate finding id'); ids.add(fid)
        require(finding.get('category') in {'technical','visual','reference'} and finding.get('severity') in {'minor','major','blocking'} and all(nonempty(finding.get(k)) for k in ('evidence','action')), 'Finding needs category, severity, concrete evidence and action')
    require(data['visual']['status'] != 'revise' or findings, 'Visual revise requires concrete findings')
    require(type(data.get('best_so_far')) is bool and type(data.get('replace_reference')) is bool, 'Explicit best_so_far and replace_reference booleans required')
    if historical:require(data['best_so_far'] is False and data['human']['status']!='accepted','Historical-task review cannot select best-so-far or record human acceptance')
    require(not data['best_so_far'] or (data['technical']['status'] != 'fail' and not any(f['severity']=='blocking' for f in findings)), 'Failed/blocking candidate cannot be best-so-far')
    data['render_sha256'] = digest(out/'render.json'); data['recorded_at'] = now()
    if historical:data['historical_task_context']={'status':'historical-only; no current approval','prompt_task_sha256':prompt['task_sha256'],'prompt_task_revision':prompt.get('task_revision',0),'current_task_revision':state['task_revision'],'ledger_sha256':state['task_ledger_sha256']}
    atomic(out/'review.json',data,True)
    if data['best_so_far']: state['variants'][args.variant]['best_so_far'] = args.iteration; atomic(folder/'campaign.json',state)
    return {'status':'review-recorded','historical_only':historical,'technical':data['technical']['status'],'visual':data['visual']['status'],'human':data['human']['status'],'independent':independent,'best_so_far':state['variants'][args.variant]['best_so_far']}
def decide(root,args):
    folder,state,out = iteration(root,args); prompt,rendered,record = review_current(root,folder,out)
    remaining = state['max_iterations']-len(state['variants'][args.variant]['iterations'])
    failed = record['technical']['status'] == 'fail' or any(record['independent'][key] == 'fail' for key in ('technical','visual')) or any(f['severity'] == 'blocking' for f in record['findings'])
    if failed: action = 'revise' if remaining else 'await-user'
    elif record['human']['status'] == 'accepted': action = 'keep-candidate'
    elif record['human']['status'] == 'rejected': action = 'revise' if remaining else 'await-user'
    elif record['replace_reference']: action = 'replace-reference' if remaining else 'await-user'
    elif record['technical']['status'] == 'fail' or record['visual']['status'] == 'revise': action = 'revise' if remaining else 'await-user'
    elif record['visual']['status'] == 'candidate' and record['technical']['status'] == 'pass': action = 'keep-candidate'
    else: action = 'await-user'
    result = {'status':'decision','action':action,'remaining_iterations':remaining,'best_so_far':state['variants'][args.variant]['best_so_far'],'human_acceptance':record['human']['status'],'independent':record['independent'],'findings':[f['id'] for f in record['findings']],'stop_bound':remaining == 0,'review_sha256':digest(out/'review.json')}
    atomic(out/'decision.json',result); return result
def export(root,args):
    folder,state,out = iteration(root,args); prompt,rendered,record = review_current(root,folder,out)
    require(state['variants'][args.variant]['best_so_far'] == args.iteration, 'Only the selected best-so-far iteration may be exported')
    require(not any(p.parent != out for p in (folder/args.variant).glob('*/export.json')), 'An earlier export exists; preserve it and explicitly reconcile the final selection before exporting again')
    target = safe(root, f'exports/{args.campaign}/{args.variant}/{args.iteration}'); require(not target.exists(),'Existing export preserved')
    target.mkdir(parents=True)
    records = []
    closure=pinned_closure(root,rendered); entry=None
    if closure:
        source_root=safe(root,closure['root'],True)
        for item in closure['files']:
            destination=safe(root,(target/'app'/item['path']).relative_to(root).as_posix()); destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(safe(source_root,item['path'],True),destination);require(digest(destination)==item['sha256'],'Export closure copy hash mismatch')
            records.append({'path':destination.relative_to(root).as_posix(),'sha256':item['sha256']})
        entry=(target/'app'/closure['entry']).relative_to(root).as_posix()
    for index,item in enumerate([rendered['source'],*rendered['pngs']]):
        if index==0 and closure: continue
        name = ('source'+Path(item['path']).suffix) if index == 0 else f'view-{index}.png'
        shutil.copyfile(safe(root,item['path'],True), target/name)
        require(digest(target/name) == item['sha256'],'Export copy hash mismatch'); records.append({'path':str((target/name).relative_to(root)).replace('\\','/'),'sha256':item['sha256']})
    query=rendered.get('view_query','');entry_url=entry+('?' + query if query else '') if entry else None
    evidence = {'version':VERSION,'exported_at':now(),'files':records,'entry':entry,'view_query':query,'entry_url':entry_url,'source_closure':closure,'source_render_sha256':digest(out/'render.json'),'review_sha256':digest(out/'review.json'),'reference_analysis':load(folder/'references'/f"{prompt['reference_id']}.json"),'prompt':prompt,'review':record,'private_reference_pixels_included':False}
    if rendered.get('capture_record'):evidence['capture_record']=rendered['capture_record'];evidence['actual_capture']=load(safe(root,rendered['capture_record']['path'],True))
    if state.get('task_revision'):evidence['task_revision']=state['task_revision'];evidence['task_amendments']=[load(folder/'task-amendments'/f'{number}.json') for number in range(1,state['task_revision']+1)]
    atomic(target/'evidence.json',evidence,True); atomic(out/'export.json',{'path':str((target/'evidence.json').relative_to(root)).replace('\\','/'),'sha256':digest(target/'evidence.json')},True)
    return {'status':'exported','path':str(target),'entry':entry,'view_query':query,'entry_url':entry_url,'human_acceptance':record['human']['status'],'files':records}
def cleanup(root,args):
    folder,state = campaign(root,args.campaign); targets = {};protected_active=set()
    for variant,info in state['variants'].items():
        winner = info['best_so_far']; require(winner is not None, 'Best-so-far choice required before cleanup')
        winner_out = folder/variant/str(winner)
        exported = load(winner_out/'export.json'); require(current(root,exported),'Best-so-far reviewed export required before cleanup')
        evidence = load(safe(root,exported['path'],True))
        require(evidence['review_sha256'] == digest(winner_out/'review.json') and all(current(root,f) for f in evidence['files']),'Best-so-far export evidence/artifacts stale')
        for number in info['iterations']:
            out = folder/variant/str(number); require((out/'render.json').is_file(),'Unrendered prompt prevents campaign cleanup')
            prompt,rendered,record = review_current(root,folder,out,allow_amended_task=True)
            closure=pinned_closure(root,rendered)
            if closure and closure['ownership']=='active':
                protected_active.update(safe(root,closure['root']+'/'+item['path'],True) for item in closure['files'])
            if closure and closure['ownership']=='run-transient':
                for item in closure['files']: targets[closure['root']+'/'+item['path']]=item['sha256']
            elif not closure and PurePosixPath(rendered['source']['path']).parts[0] in {'generated','transient'}: targets[rendered['source']['path']]=rendered['source']['sha256']
            for item in rendered['pngs']:
                if PurePosixPath(item['path']).parts[0] in {'images','transient'}: targets[item['path']]=item['sha256']
    require(state['variants'],'No reviewed variants to clean')
    for rid in state['references']:
        ref = load(folder/'references'/f'{rid}.json')
        if PurePosixPath(ref['asset_path'].replace('\\','/')).parts[0] in {'references','transient'}: targets[ref['asset_path']]=ref['asset_sha256']
    # Deduplicate aliases before mutation; never unlink one file twice.
    normalized_targets = {}
    for path,expected in targets.items():
        canonical = safe(root,path,True)
        require(canonical not in normalized_targets or normalized_targets[canonical] == expected,'Conflicting hashes for aliased cleanup targets')
        normalized_targets[canonical] = expected
    targets = {path.relative_to(root).as_posix():expected for path,expected in normalized_targets.items()}
    targets = {path:expected for path,expected in targets.items() if safe(root,path,True) not in protected_active}
    normalized_targets = {path:expected for path,expected in normalized_targets.items() if path not in protected_active}
    # Compare parsed, normalized paths; JSON spelling/Unicode/./ aliases cannot hide sharing.
    canonical_targets = set(normalized_targets)
    def referenced_paths(value):
        if isinstance(value,dict):
            if {'root','entry','files'} <= value.keys():
                for item in value['files']: yield safe(root,value['root']+'/'+item['path'])
                return
            for key,item in value.items():
                if key in {'path','asset_path'} and isinstance(item,str):
                    yield safe(root,item)
                else:
                    yield from referenced_paths(item)
        elif isinstance(value,list):
            for item in value: yield from referenced_paths(item)
    for other in (root/'campaigns').glob('*/campaign.json'):
        if other.parent == folder: continue
        campaign(root,other.parent.name)
        for recpath in other.parent.rglob('*.json'):
            require(not canonical_targets.intersection(referenced_paths(load(recpath))), 'Shared artifact referenced by another campaign; cleanup blocked')
    for path,expected in targets.items():
        require(current(root,{'path':path,'sha256':expected}),'Cleanup target changed/missing; preserve it and inspect')
    tombstones = [{'path':p,'sha256':h,'evicted_at':now(),'reason':'reviewed and exported; no fresh reinspection claim'} for p,h in targets.items()]
    atomic(folder/'cleanup-pending.json',tombstones,True)
    for item in tombstones: safe(root,item['path'],True).unlink()
    state['tombstones'].extend(tombstones); atomic(folder/'campaign.json',state); atomic(folder/'cleanup.json',{'status':'evicted','files':tombstones,'records_retained':True},True)
    return {'status':'cleaned','evicted_files':len(tombstones),'source_policy':'active/unregistered files preserved; only registered run-owned transients removed','reference_freshness':'evicted references cannot be freshly reinspected; retained files remain subject to hash/view evidence'}
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--workspace',required=True)
    commands = parser.add_subparsers(dest='command',required=True)
    p = commands.add_parser('create'); p.add_argument('--task',required=True); p.add_argument('--campaign',required=True); p.add_argument('--iterations',type=int,default=3); p.add_argument('--variants',type=int,default=2)
    p = commands.add_parser('reference'); p.add_argument('--campaign',required=True); p.add_argument('--analysis',required=True)
    p = commands.add_parser('task-amend');p.add_argument('--campaign',required=True);p.add_argument('--task',required=True);p.add_argument('--reason',required=True);p.add_argument('--author',required=True)
    p = commands.add_parser('compile'); p.add_argument('--campaign',required=True); p.add_argument('--variant',required=True); p.add_argument('--reference',required=True); p.add_argument('--spec',required=True)
    p = commands.add_parser('source-manifest'); p.add_argument('--source-root',required=True); p.add_argument('--entry',default='index.html'); p.add_argument('--ownership',required=True,choices=('active','run-transient')); p.add_argument('--out',required=True)
    p = commands.add_parser('library-search');p.add_argument('query',nargs='?',default='')
    for facet in ('job','platform','state','stack','entity','action','density','accessibility'):p.add_argument('--'+facet)
    p.add_argument('--type',choices=('component','pattern','example'));p.add_argument('--limit',type=int,default=8)
    for command in ('render','review','decide','export'):
        p = commands.add_parser(command); p.add_argument('--campaign',required=True); p.add_argument('--variant',required=True); p.add_argument('--iteration',required=True,type=int)
        if command == 'render': p.add_argument('--source',required=True); p.add_argument('--source-manifest'); p.add_argument('--view-query',default=''); p.add_argument('--capture-record'); p.add_argument('--png',required=True,nargs='+'); p.add_argument('--generator',required=True)
        if command == 'review': p.add_argument('--record',required=True);p.add_argument('--historical-task',action='store_true')
    p = commands.add_parser('cleanup'); p.add_argument('--campaign',required=True)
    args = parser.parse_args(argv); root = canonical_workspace(args.workspace)
    # Exclusive workspace lock prevents concurrent check-then-write budget consumption.
    lock = safe(root,'.pipeline-lock'); fd = None; owned = False
    try:
        try: fd = os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
        except FileExistsError: raise GateError('Workspace locked; another operation or stale lock requires inspection')
        owned = True
        os.write(fd,str(os.getpid()).encode()); os.close(fd); fd = None
        result = {'create':create,'reference':reference,'task-amend':task_amend,'compile':compile_prompt,'source-manifest':source_manifest,'library-search':library_search,'render':render,'review':review,'decide':decide,'export':export,'cleanup':cleanup}[args.command](root,args)
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
    finally:
        if fd is not None: os.close(fd)
        if owned and lock.exists(): lock.unlink()
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')
    try: sys.exit(main())
    except (ValueError,OSError,KeyError,TypeError,AttributeError,IndexError,struct.error) as error:
        print(json.dumps({'status':'error','error':str(error)},ensure_ascii=False)); sys.exit(2)
