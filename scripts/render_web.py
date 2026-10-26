"""Capture a pinned static build in actual installed Chrome. Optional Playwright dependency."""
from __future__ import annotations
import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import importlib.metadata
import json
import mimetypes
from pathlib import Path
import re
import sys
from threading import Thread
from urllib.parse import unquote,urlsplit,quote
from pipeline import GateError,atomic,digest,file_record,load,now,require,safe,validate_closure,view_query

def content_type(path):
    # Windows registry MIME associations can label .mjs as text/plain. Module
    # execution must not depend on a user's unrelated file associations.
    web_types={'.html':'text/html; charset=utf-8','.htm':'text/html; charset=utf-8',
               '.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8',
               '.css':'text/css; charset=utf-8','.json':'application/json',
               '.svg':'image/svg+xml','.woff':'font/woff','.woff2':'font/woff2'}
    return web_types.get(path.suffix.lower()) or mimetypes.guess_type(str(path))[0] or 'application/octet-stream'

def capture(workspace,manifest,chrome,out,full_page=False,query='',mobile_full_page=False):
    try: from playwright.sync_api import sync_playwright
    except ImportError: raise GateError('Python Playwright unavailable; use an already authorized renderer or explicitly arrange dependency installation')
    root=Path(workspace).resolve(strict=True); require(root.is_dir() and root!=Path(root.anchor),'Explicit non-root workspace directory required')
    query=view_query(query)
    chrome_path=Path(chrome); require(chrome_path.is_absolute() and chrome_path.is_file(),'Explicit existing absolute Chrome executable required')
    require(not chrome_path.is_symlink() and not getattr(chrome_path.lstat(),'st_file_attributes',0)&0x400,'Chrome executable link/reparse rejected')
    manifest_path=safe(root,manifest,True); manifest_hash=digest(manifest_path); closure=validate_closure(root,load(manifest_path)); source_root=safe(root,closure['root'],True)
    output=safe(root,out); require(output.relative_to(root).parts[0] in {'images','transient'},'Capture output must be below images/ or transient/')
    require(not output.is_relative_to(source_root),'Capture output cannot enter pinned source closure')
    require(not output.exists(),'Existing capture preserved');output.mkdir(parents=True)
    listed={item['path']:item['sha256'] for item in closure['files']};server_errors=[]
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            relative=unquote(urlsplit(self.path).path).lstrip('/') or closure['entry']
            if relative=='favicon.ico' and relative not in listed:
                self.send_response(204);self.end_headers();return
            try:
                require(relative in listed,'Request is not a pinned closure member: '+relative)
                path=safe(source_root,relative,True);require(digest(path)==listed[relative],'Served source changed')
                content=path.read_bytes();self.send_response(200);self.send_header('Content-Type',content_type(path));self.send_header('Content-Length',str(len(content)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(content)
            except (GateError,OSError) as error:
                server_errors.append(str(error));self.send_error(404)
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    origin=f'http://127.0.0.1:{server.server_port}';url=origin+'/'+quote(closure['entry'],safe='/')+('?' + query if query else '')
    result={'version':'0.3.0','started_at':now(),'route':'pinned local static closure; actual Python Playwright + explicit Chrome','source_manifest':{'path':manifest_path.relative_to(root).as_posix(),'sha256':manifest_hash,'closure':closure},'chrome_executable':str(chrome_path),'playwright_version':importlib.metadata.version('playwright'),'bind_address':'127.0.0.1','port':server.server_port,'render_url':url,'view_query':query,'full_page':bool(full_page),'mobile_full_page':bool(mobile_full_page),'screenshots':[],'viewports':[],'page_errors':[],'console_errors':[],'external_requests':[],'failed_requests':[],'http_errors':[],'websockets':[],'server_errors':server_errors,'visual':'not-run:must open actual screenshots','human':'not-run','technical_task_behavior':'not-run:render checks only'}
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=str(chrome_path),headless=True);result['browser_version']=browser.version
            try:
                for name,width,height in [('desktop',1440,1000),('mobile',390,844)]:
                    context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1,is_mobile=name=='mobile',has_touch=name=='mobile',reduced_motion='reduce',service_workers='block')
                    page=context.new_page();page.on('pageerror',lambda error:result['page_errors'].append(str(error)));page.on('console',lambda message:result['console_errors'].append(message.text) if message.type=='error' else None)
                    page.on('requestfailed',lambda request:result['failed_requests'].append({'url':request.url,'failure':request.failure}))
                    page.on('response',lambda response:result['http_errors'].append({'url':response.url,'status':response.status}) if response.status>=400 else None)
                    def route(request_route):
                        request_url=urlsplit(request_route.request.url)
                        if request_url.scheme=='http' and request_url.netloc==f'127.0.0.1:{server.server_port}': request_route.continue_()
                        else: result['external_requests'].append(request_route.request.url);request_route.abort()
                    page.route(re.compile(r'^https?://'),route)
                    def websocket(socket):
                        result['websockets'].append(socket.url);socket.close(code=1008,reason='Offline static renderer')
                    page.route_web_socket(re.compile('.*'),websocket)
                    page.goto(url,wait_until='networkidle',timeout=30000);page.evaluate('document.fonts.ready');page.wait_for_timeout(150)
                    geometry=page.evaluate("""()=>{const text=(document.body?.innerText||'').trim();const readable=[...document.querySelectorAll('h1,h2,p,button,label,td,a,input')].filter(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0&&r.height>0&&r.x<innerWidth&&r.right>0&&r.y<innerHeight&&r.bottom>0&&s.visibility!=='hidden'&&s.display!=='none'&&parseFloat(s.fontSize)>=10&&(e.innerText||e.value||e.getAttribute('aria-label')||'').trim().length>0}).length;return{viewport:[innerWidth,innerHeight],document:[document.documentElement.scrollWidth,document.documentElement.scrollHeight],no_horizontal_overflow:document.documentElement.scrollWidth<=innerWidth+1,nonempty_visible_text:text.length>0,visible_readable_elements:readable}}""")
                    geometry['document_title']=page.title()
                    is_full=bool(full_page or (name=='mobile' and mobile_full_page));file=output/(name+'.png');page.screenshot(path=str(file),full_page=is_full)
                    result['screenshots'].append({'state':name,'viewport':[width,height],'full_page':is_full,**file_record(root,file.relative_to(root).as_posix(),True)})
                    result['viewports'].append({'state':name,**geometry});context.close()
            finally: browser.close()
        require(digest(manifest_path)==manifest_hash and validate_closure(root,load(manifest_path))==closure,'Source closure changed during actual render')
        result['source_fresh_after']=True
        result['passed']=all(v['no_horizontal_overflow'] and v['nonempty_visible_text'] and v['visible_readable_elements']>0 for v in result['viewports']) and not any(result[key] for key in ('page_errors','console_errors','external_requests','failed_requests','http_errors','websockets','server_errors'))
        result['capture_limits']='Header/integrity and visible text/geometry heuristics do not prove contrast, pixel quality, task flow, accessibility or human acceptance.'
    except Exception as error:
        result['passed']=False;result['error']=str(error)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2);result['finished_at']=now();atomic(output/'capture.json',result,True)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace',required=True);parser.add_argument('--source-manifest',required=True);parser.add_argument('--chrome',required=True);parser.add_argument('--out',required=True);parser.add_argument('--full-page',action='store_true');parser.add_argument('--mobile-full-page',action='store_true');parser.add_argument('--query',default='');args=parser.parse_args()
    result=capture(args.workspace,args.source_manifest,args.chrome,args.out,args.full_page,args.query,args.mobile_full_page)
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    try:sys.exit(main())
    except (ValueError,OSError,KeyError,TypeError) as error:print(json.dumps({'status':'error','error':str(error)},ensure_ascii=False));sys.exit(2)
