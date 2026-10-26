import json
from pathlib import Path
import shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve();self.package=self.root/'plugin'
        shutil.copytree(ROOT,self.package,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        self.run=self.root/'run';self.run.mkdir()
    def tearDown(self):self.temp.cleanup()
    def call(self,*args,ok=True):
        result=subprocess.run([sys.executable,str(self.package/'scripts/pipeline.py'),'--workspace',str(self.run),'library-search',*args],capture_output=True,encoding='utf-8')
        self.assertEqual(result.returncode,0 if ok else 2,result.stdout+result.stderr);return json.loads(result.stdout)
    def test_job_state_stack_lookup_and_portable_actual_sources(self):
        result=self.call('--job','select-records','--type','pattern');self.assertEqual([r['id'] for r in result['results']],['pattern.selection-actions'])
        result=self.call('--state','save-error','--stack','react-shadcn','--type','pattern');self.assertEqual({r['id'] for r in result['results']},{'pattern.queue-detail','pattern.recovery-form','pattern.own-account-transfer','pattern.selected-object-workspace'})
        result=self.call('--job','track-finances','--state','save-error','--type','example');self.assertEqual([r['id'] for r in result['results']],['example.local-ledger']);self.assertTrue(all((self.package/f['path']).is_file() for f in result['results'][0]['source_files']))
        result=self.call('dialog','--type','component','--stack','react-shadcn');self.assertEqual(result['results'][0]['id'],'component.shadcn-dialog');self.assertTrue(result['results'][0]['source_files'][0]['sha256']);self.assertEqual(result['results'][0]['verification']['browser'],'not-run in reusable package')
        self.assertTrue((self.package/'library/components/react-shadcn/LICENSE.md').is_file())
    def test_changed_source_and_missing_license_fail_closed(self):
        source=self.package/'library/components/react-shadcn/ui/dialog.tsx';original=source.read_bytes();source.write_bytes(original+b'\n// changed\n');self.call('dialog',ok=False);source.write_bytes(original)
        manifest=json.loads((self.package/'library/manifest.json').read_text());manifest['items'][0]['license']['spdx']='unknown';(self.package/'library/manifest.json').write_text(json.dumps(manifest));self.call('',ok=False)
    def test_broken_pattern_component_and_output_bounds(self):
        manifest=json.loads((self.package/'library/manifest.json').read_text());next(item for item in manifest['items'] if item['id']=='pattern.queue-detail')['composition'].append('component.absent');(self.package/'library/manifest.json').write_text(json.dumps(manifest));self.call('queue',ok=False)
        self.call('--limit','-1',ok=False)
if __name__=='__main__':unittest.main(verbosity=2)
