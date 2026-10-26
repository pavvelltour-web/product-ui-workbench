from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Thread
import unittest
from _browser_support import require_browser

ROOT=Path(__file__).resolve().parents[1]

class DemoTests(unittest.TestCase):
    def generate(self, destination):
        result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/demo.py'),'--workspace',str(destination)],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return json.loads(result.stdout)

    def test_original_demo_is_complete_and_existing_workspace_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'demo';report=self.generate(target)
            self.assertEqual(report['browser'],'not-run')
            self.assertIn('not-run',report['reference_review'])
            manifest=json.loads((target/'inputs/build.json').read_text(encoding='utf-8'))
            self.assertEqual({f['path'] for f in manifest['files']},{'index.html','native-workbench.mjs'})
            original=(target/'generated/demo/index.html').read_bytes()
            retry=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/demo.py'),'--workspace',str(target)],capture_output=True,text=True)
            self.assertEqual(retry.returncode,2)
            self.assertEqual((target/'generated/demo/index.html').read_bytes(),original)

    def test_actual_offline_demo_identity_error_retry_and_focus_at_two_widths(self):
        executable=require_browser()
        from playwright.sync_api import sync_playwright
        class Quiet(SimpleHTTPRequestHandler):
            extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.mjs':'text/javascript'}
            def log_message(self,*args):pass
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'demo';self.generate(target)
            server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(target/'generated/demo')))
            thread=Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                with sync_playwright() as p:
                    browser=p.chromium.launch(executable_path=str(executable),headless=True)
                    for width,height in [(1440,1000),(390,844)]:
                        context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                        page=context.new_page();errors=[];external=[];base=f'http://127.0.0.1:{server.server_port}/'
                        page.on('pageerror',lambda e:errors.append(str(e)))
                        def route(r):
                            if r.request.url.startswith(base):r.continue_()
                            else:external.append(r.request.url);r.abort()
                        page.route('**/*',route);page.goto(base,wait_until='networkidle')
                        opener=page.get_by_test_id('primary-open');opener.click()
                        self.assertIn('task-a',page.get_by_test_id('record-identity').inner_text())
                        page.get_by_test_id('note').fill('Synthetic review note')
                        page.get_by_test_id('simulate-error').click()
                        self.assertIn('Synthetic save error',page.locator('#error').inner_text())
                        self.assertEqual(page.get_by_test_id('note').input_value(),'Synthetic review note')
                        page.get_by_test_id('save').click();page.locator('dialog').wait_for(state='hidden')
                        page.wait_for_function('el=>document.activeElement===el',arg=opener.element_handle())
                        self.assertIn('Task A: note saved',page.locator('#feedback').inner_text())
                        opener.click();self.assertEqual(page.get_by_test_id('note').input_value(),'Synthetic review note')
                        page.keyboard.press('Escape');page.locator('dialog').wait_for(state='hidden')
                        page.wait_for_function('el=>document.activeElement===el',arg=opener.element_handle())
                        page.get_by_test_id('status-filter').select_option(label='Complete')
                        self.assertEqual(page.locator('#count').inner_text(),'1 visible tasks')
                        page.get_by_test_id('row-task-c').click();self.assertIn('task-c',page.get_by_test_id('record-identity').inner_text())
                        self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth+1'))
                        self.assertEqual(errors,[]);self.assertEqual(external,[]);context.close()
                    browser.close()
            finally:server.shutdown();server.server_close();thread.join(2)

if __name__=='__main__':unittest.main(verbosity=2)
