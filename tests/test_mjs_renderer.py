"""Regression for independently observed Windows strict module MIME failure."""
import hashlib,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import render_web
from _browser_support import require_browser

class ModuleMimeTest(unittest.TestCase):
    def test_module_and_import_execute_despite_wrong_os_mime(self):
        chrome=require_browser()
        with tempfile.TemporaryDirectory(prefix='workbench-mjs-') as temp:
            root=Path(temp).resolve();source=root/'generated/module';source.mkdir(parents=True)
            (source/'index.html').write_text('<!doctype html><html><head><title>Not executed</title></head><body><h1>Loading</h1><script type="module" src="main.mjs"></script></body></html>',encoding='utf-8')
            (source/'main.mjs').write_text("import { message } from './part.mjs'; document.title=message; document.querySelector('h1').textContent=message;",encoding='utf-8')
            (source/'part.mjs').write_text("export const message='Module and imported module executed';",encoding='utf-8')
            files=[{'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(source.iterdir())]
            (root/'closure.json').write_text(json.dumps({'root':'generated/module','entry':'index.html','ownership':'run-transient','files':files}),encoding='utf-8')
            original_guess=render_web.mimetypes.guess_type
            def windows_module_association(value,*args,**kwargs):
                return ('text/plain',None) if str(value).lower().endswith(('.js','.mjs')) else original_guess(value,*args,**kwargs)
            with patch.object(render_web.mimetypes,'guess_type',side_effect=windows_module_association):
                result=render_web.capture(root,'closure.json',str(chrome),'images/module')
            self.assertTrue(result['passed'],result)
            self.assertEqual([v['document_title'] for v in result['viewports']],['Module and imported module executed']*2)
            self.assertEqual(result['console_errors'],[])
            self.assertTrue(result['source_fresh_after'])

if __name__=='__main__':unittest.main()
