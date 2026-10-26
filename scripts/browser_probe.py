"""Run declared interaction slices in actual Chrome against an exact local static closure."""
from __future__ import annotations
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.metadata
import json
from pathlib import Path
import re
import sys
from threading import Thread
from urllib.parse import quote, unquote, urlsplit
from pipeline import GateError, atomic, digest, file_record, load, now, require, safe, validate_closure
from render_web import content_type
from ux_contract import VIEWPORTS, validate_plan, validate_interaction_checks


MEASURE = """element => {
 const rect=element.getBoundingClientRect(), style=getComputedStyle(element);
 let cssVisible=true, opacity=1, cursor=element;
 while(cursor){const s=getComputedStyle(cursor);cssVisible=cssVisible&&s.display!=='none'&&s.visibility!=='hidden'&&s.visibility!=='collapse';opacity*=Number(s.opacity);cursor=cursor.parentElement;}
 if(element.tagName==='SELECT'){
   const selected=element.selectedOptions[0];
   const text=selected?(selected.label||selected.textContent||'').trim():'';
   const px=value=>parseFloat(value)||0, fontSize=parseFloat(style.fontSize);
   const content={x:rect.x+px(style.borderLeftWidth)+px(style.paddingLeft),
     y:rect.y+px(style.borderTopWidth)+px(style.paddingTop),
     width:Math.max(0,rect.width-px(style.borderLeftWidth)-px(style.borderRightWidth)-px(style.paddingLeft)-px(style.paddingRight)),
     height:Math.max(0,rect.height-px(style.borderTopWidth)-px(style.borderBottomWidth)-px(style.paddingTop)-px(style.paddingBottom))};
   const inViewport=rect.right>0&&rect.bottom>0&&rect.x<innerWidth&&rect.y<innerHeight;
   const contentInViewport=content.x+content.width>0&&content.y+content.height>0&&content.x<innerWidth&&content.y<innerHeight;
   const colorAlpha=style.color.includes('/')?Number(style.color.slice(style.color.lastIndexOf('/')+1,-1)):(style.color.startsWith('rgba(')?Number(style.color.slice(5,-1).split(',')[3]):1);
   const transparent=style.color==='transparent'||colorAlpha===0;
   const closedSingle=!element.multiple&&element.size<=1;
   return {method:'native-selected-option-control-geometry',text,
     rect:{x:rect.x,y:rect.y,width:rect.width,height:rect.height},content_box:content,
     content_box_basis:'Computed control bounds minus CSS borders and padding; native arrow/internal label area unknown',
     text_rects:[],native_text_bounds:'unknown; no DOM Range or actual glyph-pixel measurement for native control internals',
     selected_label_source:'selectedOptions[0].label || selectedOptions[0].textContent',
     closed_single_select:closedSingle,multiple:element.multiple,size:element.size,
     unsupported_reason:closedSingle?null:'Multiple/listbox select is outside this closed-value check',
     font_size:fontSize,font_family:style.fontFamily,font_weight:style.fontWeight,line_height:style.lineHeight,
     color:style.color,opacity,css_visible:cssVisible,in_viewport:inViewport,
     scope:'CSS, selected-label and control-geometry heuristic only; inspect saved PNG for glyph visibility, clipping, occlusion and contrast',
     readable:closedSingle&&cssVisible&&opacity>0&&rect.width>0&&rect.height>0&&inViewport&&contentInViewport&&
       content.width>=fontSize*.5&&content.height>=fontSize*.5&&text.length>0&&fontSize>=10&&!transparent};
 }
 const range=document.createRange();range.selectNodeContents(element);
 const textRects=[...range.getClientRects()].map(r=>({x:r.x,y:r.y,width:r.width,height:r.height}));
 const text=(element.innerText||element.textContent||element.value||'').trim();
 const inViewport=rect.right>0&&rect.bottom>0&&rect.x<innerWidth&&rect.y<innerHeight;
 const textPixels=textRects.some(r=>r.width>0&&r.height>0&&r.x+r.width>0&&r.y+r.height>0&&r.x<innerWidth&&r.y<innerHeight);
 const transparent=/rgba\\([^)]*,\\s*0(?:\\.0+)?\\)$/.test(style.color)||style.color==='transparent';
 return {method:'dom-range-text-geometry',text,rect:{x:rect.x,y:rect.y,width:rect.width,height:rect.height},text_rects:textRects,
   font_size:parseFloat(style.fontSize),color:style.color,opacity,css_visible:cssVisible,in_viewport:inViewport,
   readable:cssVisible&&opacity>0&&rect.width>0&&rect.height>0&&inViewport&&textPixels&&text.length>0&&parseFloat(style.fontSize)>=10&&!transparent};
}"""


def probe(workspace, manifest, plan, chrome, out, checks_file=None):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise GateError('Existing Python Playwright required; dependency installation is not implicit')
    root = Path(workspace).resolve(strict=True)
    require(root.is_dir() and root != Path(root.anchor), 'Explicit non-root workspace required')
    plan_path = safe(root, plan, True); plan_hash = digest(plan_path); proposal = load(plan_path)
    validate_plan(proposal)
    checks_path = safe(root, checks_file, True) if checks_file else plan_path
    checks_hash = digest(checks_path)
    if checks_file:
        require('interaction_checks' not in proposal, 'External checks cannot override embedded checks')
        external = load(checks_path)
        require(external.get('version') == '1.0' and external.get('study_id') == proposal['study_id'], 'External checks of wrong study/version')
        require(external.get('plan_sha256', plan_hash) == plan_hash, 'External checks of wrong UX plan')
        checks = validate_interaction_checks(external.get('interaction_checks'))
    else:
        checks = validate_interaction_checks(proposal.get('interaction_checks'))
    manifest_path = safe(root, manifest, True); manifest_hash = digest(manifest_path)
    closure = validate_closure(root, load(manifest_path)); source_root = safe(root, closure['root'], True)
    chrome_path = Path(chrome)
    require(chrome_path.is_absolute() and chrome_path.is_file(), 'Explicit existing absolute Chrome required')
    require(not chrome_path.is_symlink() and not getattr(chrome_path.lstat(), 'st_file_attributes', 0) & 0x400, 'Chrome reparse/link rejected')
    output = safe(root, out)
    require(output.relative_to(root).parts[0] in {'images', 'transient'}, 'Probe output must be below images/ or transient/')
    require(not output.is_relative_to(source_root) and not output.exists(), 'Existing output/source closure preserved')
    output.mkdir(parents=True)
    result = {'version': '1.0', 'runner': 'browser-probe:playwright-chrome', 'started_at': now(),
              'study_id': proposal['study_id'], 'plan_sha256': plan_hash,
              'plan': {'path': plan_path.relative_to(root).as_posix(), 'sha256': plan_hash},
              'checks_contract': {'path': checks_path.relative_to(root).as_posix(), 'sha256': checks_hash},
              'planned_checks': checks, 'source_manifest': {'path': manifest_path.relative_to(root).as_posix(), 'sha256': manifest_hash, 'closure': closure},
              'view_query': 'variant=' + proposal['study_id'], 'chrome_executable': str(chrome_path),
              'playwright_version': importlib.metadata.version('playwright'), 'cases': [],
              **{key: [] for key in ['page_errors', 'console_errors', 'external_requests', 'failed_requests', 'http_errors', 'websockets', 'server_errors']},
              'scope': 'Declared interaction slices and readable text/geometry heuristics; no beauty, full usability, accessibility or human acceptance verdict'}
    listed = {item['path']: item['sha256'] for item in closure['files']}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            relative = unquote(urlsplit(self.path).path).lstrip('/') or closure['entry']
            if relative == 'favicon.ico' and relative not in listed:
                self.send_response(204); self.end_headers(); return
            try:
                require(relative in listed, 'Request not in pinned closure: ' + relative)
                path = safe(source_root, relative, True)
                require(digest(path) == listed[relative], 'Served source changed')
                content = path.read_bytes(); self.send_response(200)
                self.send_header('Content-Type', content_type(path)); self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(content)
            except (GateError, OSError) as error:
                result['server_errors'].append(str(error)); self.send_error(404)
        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    url = origin + '/' + quote(closure['entry'], safe='/') + '?' + result['view_query']
    result.update(bind_address='127.0.0.1', port=server.server_port)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=str(chrome_path), headless=True)
            result['browser_version'] = browser.version
            try:
                for check_index, check in enumerate(checks):
                    for viewport in check['viewports']:
                        width, height = VIEWPORTS[viewport]
                        context = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=1,
                                                      is_mobile=viewport == 'mobile', has_touch=viewport == 'mobile',
                                                      reduced_motion='reduce', service_workers='block')
                        page = context.new_page()
                        case = {'id': check['id'], 'viewport': viewport, 'viewport_size': [width, height], 'check': check,
                                'passed': False, 'assertions': {}, 'measurements': {'target': {'text': '', 'rect': {}, 'readable': False}}, 'screenshots': []}
                        result['cases'].append(case)
                        page.on('pageerror', lambda error: result['page_errors'].append(str(error)))
                        page.on('console', lambda message: result['console_errors'].append(message.text) if message.type == 'error' else None)
                        page.on('requestfailed', lambda request: result['failed_requests'].append({'url': request.url, 'failure': request.failure}))
                        page.on('response', lambda response: result['http_errors'].append({'url': response.url, 'status': response.status}) if response.status >= 400 else None)
                        def route(request_route):
                            parsed = urlsplit(request_route.request.url)
                            if parsed.scheme == 'http' and parsed.netloc == f'127.0.0.1:{server.server_port}':
                                request_route.continue_()
                            else:
                                result['external_requests'].append(request_route.request.url); request_route.abort()
                        page.route(re.compile(r'^https?://'), route)
                        def websocket(socket):
                            result['websockets'].append(socket.url); socket.close(code=1008, reason='Offline interaction probe')
                        page.route_web_socket(re.compile('.*'), websocket)
                        def shot(state):
                            file = output / f'{check_index + 1:02d}-{viewport}-{state}.png'
                            page.screenshot(path=str(file), full_page=False)
                            case['screenshots'].append({'state': state, **file_record(root, file.relative_to(root).as_posix(), True)})
                        try:
                            page.goto(url, wait_until='networkidle', timeout=30000)
                            page.evaluate('document.fonts.ready'); page.wait_for_timeout(100); shot('before')
                            target = page.locator(check['target'])
                            if check['kind'] == 'selected-value-visible':
                                require(target.count() == 1, 'Interaction target must match one element')
                                case['measurements']['initial_target'] = target.evaluate(MEASURE)
                                target.scroll_into_view_if_needed(timeout=5000)
                                shot('revealed')
                                measurement = target.evaluate(MEASURE); case['measurements']['target'] = measurement
                                case['assertions'] = {'target_visible': target.is_visible(), 'text_readable': measurement['readable']}
                                shot('value')
                                require(all(case['assertions'].values()), 'Closed selected value failed CSS/text/geometry readability heuristic; inspect saved PNG')
                            else:
                                trigger = page.locator(check['trigger'])
                                require(trigger.count() == 1, 'Interaction trigger must match one element')
                                trigger.click(timeout=5000)
                                require(target.count() == 1, 'Opened target must match one element')
                                target.wait_for(state='visible', timeout=5000)
                                measurement = target.evaluate(MEASURE); case['measurements']['target'] = measurement
                                case['assertions'] = {'region_visible': target.is_visible() and measurement['readable'],
                                                      'identity_matches': check['identity'] in measurement['text'], 'closed': False, 'focus_returned': False}
                                shot('opened'); require(case['assertions']['identity_matches'], 'Opened wrong region identity')
                                page.keyboard.press(check['close']); target.wait_for(state='hidden', timeout=5000)
                                page.wait_for_timeout(100)
                                case['assertions']['closed'] = not target.is_visible()
                                case['assertions']['focus_returned'] = trigger.evaluate('(element)=>document.activeElement===element')
                                shot('closed'); require(all(case['assertions'].values()), 'Region close/focus return failed')
                            case['passed'] = True
                        except Exception as error:
                            case['error'] = str(error)
                            expected = ['target_visible', 'text_readable'] if check['kind'] == 'selected-value-visible' else ['region_visible', 'identity_matches', 'closed', 'focus_returned']
                            for name in expected:
                                case['assertions'].setdefault(name, False)
                            try:
                                shot('failure')
                            except Exception as capture_error:
                                case['screenshot_error'] = str(capture_error)
                        finally:
                            context.close()
            finally:
                browser.close()
        require(digest(plan_path) == plan_hash, 'UX plan changed during interaction probe')
        require(digest(checks_path) == checks_hash, 'Interaction selector bindings changed during probe')
        require(digest(manifest_path) == manifest_hash and validate_closure(root, load(manifest_path)) == closure,
                'Source closure changed during actual interaction probe')
        result['source_fresh_after'] = True
        errors = ['page_errors', 'console_errors', 'external_requests', 'failed_requests', 'http_errors', 'websockets', 'server_errors']
        result['passed'] = all(case['passed'] for case in result['cases']) and not any(result[key] for key in errors)
    except Exception as error:
        result.update(passed=False, error=str(error))
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
        result['finished_at'] = now(); atomic(output / 'interaction.json', result, True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['workspace', 'source-manifest', 'plan', 'out', 'chrome']:
        parser.add_argument('--' + flag, required=True)
    parser.add_argument('--checks', help='Explicit additive selector bindings for a frozen legacy plan without embedded checks')
    args = parser.parse_args()
    result = probe(args.workspace, args.source_manifest, args.plan, args.chrome, args.out, args.checks)
    print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')
    try:
        sys.exit(main())
    except (GateError, ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False)); sys.exit(2)
