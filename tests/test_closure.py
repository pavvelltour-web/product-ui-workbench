import json
from pathlib import Path
import struct,subprocess,sys,unittest
import test_pipeline as fixtures
from _browser_support import require_browser

class ClosureTests(unittest.TestCase):
    setUp=fixtures.LoopTests.setUp;tearDown=fixtures.LoopTests.tearDown
    write=fixtures.LoopTests.write;hash=fixtures.LoopTests.hash;call=fixtures.LoopTests.call;prepare=fixtures.LoopTests.prepare;review=fixtures.LoopTests.review
    def make_closure(self,ownership='run-transient',folder='generated/dist'):
        self.write(folder+'/index.html','<!doctype html><link rel="stylesheet" href="/assets/main.css"><h1>Actual static fixture</h1><button>Open record</button><script src="/assets/main.js"></script>')
        self.write(folder+'/assets/main.css','body{font:16px Arial;margin:24px;color:#222;background:#fff}button{min-height:44px}')
        self.write(folder+'/assets/main.js','document.querySelector("button").onclick=()=>document.querySelector("h1").textContent="Opened record"')
        self.call('source-manifest','--source-root',folder,'--entry','index.html','--ownership',ownership,'--out','inputs/closure.json')
        return folder
    def register(self,folder):
        return self.call('render','--campaign','crm','--variant','one','--iteration','1','--source',folder+'/index.html','--source-manifest','inputs/closure.json','--png','render.png','--generator','synthetic fixture')
    def review_closure(self,folder,number=1):
        data={'observer':'fixture','inspected_at':'2026-01-01T00:00:00Z','source_sha256':self.hash(folder+'/index.html'),'png_sha256s':[self.hash('render.png')],'pixel_observations':[{'png_sha256':self.hash('render.png'),'observation':'Synthetic test attestation'}],'technical':{'status':'pass','evidence':'fixture'},'visual':{'status':'candidate','evidence':'fixture'},'human':{'status':'not-run','evidence':'fixture'},'independent':{'technical':'not-run','visual':'not-run','evidence':'fixture'},'findings':[],'best_so_far':True,'replace_reference':False}
        self.write('review.json',data);self.call('review','--campaign','crm','--variant','one','--iteration',str(number),'--record','review.json')
    def test_full_build_export_and_run_owned_cleanup(self):
        folder=self.make_closure();self.analysis['asset_path']='references/source.png';self.write('references/source.png',fixtures.png());self.prepare();self.register(folder);self.review_closure(folder)
        exported=self.call('export','--campaign','crm','--variant','one','--iteration','1')
        self.assertEqual(exported['entry'],'exports/crm/one/1/app/index.html')
        self.assertEqual(self.hash('exports/crm/one/1/app/assets/main.js'),self.hash(folder+'/assets/main.js'))
        self.call('cleanup','--campaign','crm');self.assertFalse((self.root/folder/'index.html').exists());self.assertFalse((self.root/'references/source.png').exists())
        self.assertTrue((self.root/'exports/crm/one/1/app/assets/main.css').exists());self.assertTrue((self.root/'render.png').exists())
    def test_active_source_and_unregistered_files_preserved(self):
        folder=self.make_closure('active','active-app/dist');self.prepare();self.register(folder);self.review_closure(folder)
        self.call('export','--campaign','crm','--variant','one','--iteration','1');self.write('active-app/source.tsx','Original development source');self.call('cleanup','--campaign','crm')
        self.assertTrue((self.root/folder/'assets/main.js').exists());self.assertTrue((self.root/'active-app/source.tsx').exists())
    def test_active_declaration_protects_shared_run_prefix(self):
        folder=self.make_closure();self.prepare();self.register(folder);self.review_closure(folder)
        self.write('spec.json',self.spec);self.call('compile','--campaign','crm','--variant','one','--reference','ref-one','--spec','spec.json')
        data=json.loads((self.root/'inputs/closure.json').read_text());data['ownership']='active';self.write('inputs/active.json',data)
        self.call('render','--campaign','crm','--variant','one','--iteration','2','--source',folder+'/index.html','--source-manifest','inputs/active.json','--png','render.png','--generator','fixture')
        self.review_closure(folder,2);self.call('export','--campaign','crm','--variant','one','--iteration','2');self.call('cleanup','--campaign','crm')
        self.assertTrue((self.root/folder/'index.html').exists());self.assertTrue((self.root/folder/'assets/main.js').exists())
    def test_dependency_change_and_added_file_invalidate_reviews(self):
        folder=self.make_closure();self.prepare();self.register(folder);self.review_closure(folder)
        self.write(folder+'/assets/extra.js','Untracked file');self.call('decide','--campaign','crm','--variant','one','--iteration','1',ok=False)
        (self.root/folder/'assets/extra.js').unlink();self.write(folder+'/assets/main.js','Changed dependency')
        self.call('export','--campaign','crm','--variant','one','--iteration','1',ok=False)
        self.assertFalse((self.root/'exports/crm/one/1').exists())
    def test_manifest_paths_ownership_duplicates_and_missing_files(self):
        folder=self.make_closure();original=json.loads((self.root/'inputs/closure.json').read_text())
        self.prepare()
        for mode in ('traversal','missing','duplicate','root-ownership'):
            data=json.loads(json.dumps(original))
            if mode=='traversal':data['files'][0]['path']='../outside.js'
            if mode=='missing':data['files'][0]['path']='assets/missing.js'
            if mode=='duplicate':data['files'].append(data['files'][0])
            if mode=='root-ownership':data['root']='active-app/dist';self.write('active-app/dist/index.html','Active app')
            self.write('inputs/closure.json',data)
            self.call('render','--campaign','crm','--variant','one','--iteration','1','--source',folder+'/index.html','--source-manifest','inputs/closure.json','--png','render.png','--generator','fixture',ok=False)
    def test_nested_build_symlink_rejected(self):
        folder=self.make_closure();self.write('outside.js','fixture')
        link=self.root/folder/'assets/redirect.js'
        try:link.symlink_to(self.root/'outside.js')
        except OSError:self.skipTest('Host does not permit symlink fixtures')
        self.call('source-manifest','--source-root',folder,'--ownership','run-transient','--out','inputs/other.json',ok=False)
    def test_jpeg_reference_headers_and_corrupt_end(self):
        # Structural marker fixture only; deliberately does not claim full JPEG pixel decode.
        def segment(marker,body):return bytes([255,marker])+struct.pack('>H',len(body)+2)+body
        data=b'\xff\xd8'+segment(0xc0,b'\x08\x00\x01\x00\x01\x01\x01\x11\x00')+segment(0xda,b'\x01\x01\x00\x00\x3f\x00')+b'\x12\xff\x00\x34\xff\xd9'
        self.write('reference.jpg',data);self.analysis['asset_path']='reference.jpg';self.analysis['asset_sha256']=self.hash('reference.jpg');self.write('analysis.json',self.analysis)
        recorded=self.call('reference','--campaign','crm','--analysis','analysis.json');self.assertEqual(recorded['asset']['format'],'jpeg');self.assertIn('not full pixel decode',recorded['asset']['validation'])
        self.write('broken.jpg',data[:-2]);bad=dict(self.analysis,id='broken',asset_path='broken.jpg',asset_sha256=self.hash('broken.jpg'));self.write('bad.json',bad);self.call('reference','--campaign','crm','--analysis','bad.json',ok=False)

class BrowserTests(unittest.TestCase):
    setUp=fixtures.LoopTests.setUp;tearDown=fixtures.LoopTests.tearDown
    write=fixtures.LoopTests.write;hash=fixtures.LoopTests.hash;call=fixtures.LoopTests.call;prepare=fixtures.LoopTests.prepare
    make_closure=ClosureTests.make_closure;register=ClosureTests.register;review_closure=ClosureTests.review_closure
    def test_actual_renderer_offline_and_export_is_runnable(self):
        folder=self.make_closure();chrome=require_browser()
        renderer=fixtures.CLI.parent/'render_web.py'
        result=subprocess.run([sys.executable,str(renderer),'--workspace',str(self.root),'--source-manifest','inputs/closure.json','--chrome',str(chrome),'--out','images/actual'],capture_output=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);report=json.loads(result.stdout)
        self.assertTrue(report['passed']);self.assertEqual([p['viewport'] for p in report['screenshots']],[[1440,1000],[390,844]]);self.assertEqual(report['external_requests'],[])
        self.assertTrue(all(v['visible_readable_elements']>=2 for v in report['viewports']))
        self.prepare();self.register(folder);self.review_closure(folder);self.call('export','--campaign','crm','--variant','one','--iteration','1')
        # Revalidate and serve only the exported app files, independently of the original build.
        exported_root='exports/crm/one/1/app';files=[]
        for path in (self.root/exported_root).rglob('*'):
            if path.is_file():files.append({'path':path.relative_to(self.root/exported_root).as_posix(),'sha256':self.hash(path.relative_to(self.root).as_posix())})
        # Exports are intentionally not admissible active source roots; run the pinned artifact through a new explicit workspace.
        app_workspace=self.root/exported_root
        import shutil
        isolated=self.root/'export-inspection';isolated.mkdir();shutil.copytree(app_workspace,isolated/'app')
        self.write('export-inspection/closure.json',{'root':'app','entry':'index.html','ownership':'active','files':[item for item in files]})
        rerun=subprocess.run([sys.executable,str(renderer),'--workspace',str(isolated),'--source-manifest','closure.json','--chrome',str(chrome),'--out','images/export'],capture_output=True,encoding='utf-8')
        self.assertEqual(rerun.returncode,0,rerun.stdout+rerun.stderr)
    def test_actual_renderer_blocks_external_and_overflow(self):
        folder=self.make_closure();chrome=require_browser()
        self.write(folder+'/index.html','<!doctype html><h1 style="width:2000px">Overflow fixture</h1><img src="https://example.invalid/forbidden.png">')
        self.call('source-manifest','--source-root',folder,'--ownership','run-transient','--out','inputs/bad-closure.json')
        result=subprocess.run([sys.executable,str(fixtures.CLI.parent/'render_web.py'),'--workspace',str(self.root),'--source-manifest','inputs/bad-closure.json','--chrome',str(chrome),'--out','images/blocked'],capture_output=True,encoding='utf-8')
        self.assertEqual(result.returncode,1,result.stdout+result.stderr);report=json.loads(result.stdout);self.assertFalse(report['passed']);self.assertTrue(report['external_requests']);self.assertTrue(any(not v['no_horizontal_overflow'] for v in report['viewports']))
    def test_query_variant_fullpage_and_capture_receipt_pinned(self):
        folder=self.make_closure();chrome=require_browser()
        self.write(folder+'/assets/main.js','const v=new URLSearchParams(location.search).get("variant");document.querySelector("h1").textContent=v;document.title=v;document.body.style.minHeight="1300px";')
        self.call('source-manifest','--source-root',folder,'--ownership','run-transient','--out','inputs/query-closure.json')
        result=subprocess.run([sys.executable,str(fixtures.CLI.parent/'render_web.py'),'--workspace',str(self.root),'--source-manifest','inputs/query-closure.json','--chrome',str(chrome),'--query','variant=aura','--mobile-full-page','--out','images/query'],capture_output=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr);report=json.loads(result.stdout)
        self.assertEqual(report['view_query'],'variant=aura');self.assertTrue(report['render_url'].endswith('?variant=aura'));self.assertTrue(all(v['document_title']=='aura' for v in report['viewports']));self.assertGreater(report['screenshots'][1]['height'],844)
        self.assertEqual(report['screenshots'][0]['height'],1000);self.assertEqual([p['full_page'] for p in report['screenshots']],[False,True])
        self.prepare()
        self.call('render','--campaign','crm','--variant','one','--iteration','1','--source',folder+'/index.html','--source-manifest','inputs/query-closure.json','--capture-record','images/query/capture.json','--view-query','variant=aura','--png','images/query/desktop.png','images/query/mobile.png','--generator','fixture')
        data={'observer':'synthetic test','inspected_at':'2026-01-01T00:00:00Z','source_sha256':self.hash(folder+'/index.html'),'png_sha256s':[p['sha256'] for p in report['screenshots']],'pixel_observations':[{'png_sha256':p['sha256'],'observation':'Synthetic receipt test, not a visual quality claim'} for p in report['screenshots']],'technical':{'status':'pass','evidence':'Actual fixture browser capture'},'visual':{'status':'candidate','evidence':'Synthetic test attestation'},'human':{'status':'not-run','evidence':'No human'},'independent':{'technical':'not-run','visual':'not-run','evidence':'No independent'},'findings':[],'best_so_far':True,'replace_reference':False}
        self.write('review.json',data);self.call('review','--campaign','crm','--variant','one','--iteration','1','--record','review.json');exported=self.call('export','--campaign','crm','--variant','one','--iteration','1')
        self.assertEqual(exported['view_query'],'variant=aura');self.assertTrue(exported['entry_url'].endswith('?variant=aura'))
        report['view_query']='variant=changed';self.write('images/query/capture.json',report);self.call('decide','--campaign','crm','--variant','one','--iteration','1',ok=False)

if __name__=='__main__':unittest.main(verbosity=2)
