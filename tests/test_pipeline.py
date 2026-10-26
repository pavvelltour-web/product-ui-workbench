"""CLI integration tests use invented fixture evidence, never claim real visual approval."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

CLI = Path(__file__).resolve().parents[1]/'scripts'/'pipeline.py'
ASPECTS = ['composition','typography','spacing','material','color','responsive']
def png():
    def chunk(kind,body): return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\xff\xff\xff'))+chunk(b'IEND',b'')

class LoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name).resolve()
        self.write('task.json',{'job':'Review synthetic pipeline','scope':'CRM fixture','factual_data':['Invented test values'],'interactions':['Open detail'],'constraints':['No network']})
        self.write('reference.png',png()); self.write('generated.html','<!doctype html><title>Synthetic fixture</title>'); self.write('render.png',png())
        self.analysis = {'id':'ref-one','canonical_url':'https://example.org/fixture','asset_path':'reference.png','asset_sha256':self.hash('reference.png'),'observed':{'observer':'fixture-observer','at':'2026-01-01T00:00:00Z','method':'actual-image-view'},'rights':{'purpose':'visual-analysis','status':'permitted','evidence':'Synthetic original test fixture'},'traits':[{'id':aspect,'aspect':aspect,'basis':'observed' if aspect!='responsive' else 'proposed','description':'Invented test trait '+aspect} for aspect in ASPECTS]}
        self.spec = {'intent':'Synthetic test composition','directives':[{'trait_id':aspect,'basis':'proposed','decision':'Concrete fixture decision for '+aspect} for aspect in ASPECTS],'delta_findings':[]}
        self.call('create','--task','task.json','--campaign','crm','--iterations','2','--variants','1')
    def tearDown(self): self.temp.cleanup()
    def write(self,path,value):
        p=self.root/path; p.parent.mkdir(parents=True,exist_ok=True)
        if isinstance(value,bytes): p.write_bytes(value)
        elif isinstance(value,str): p.write_text(value,encoding='utf-8')
        else: p.write_text(json.dumps(value),encoding='utf-8')
    def hash(self,path): return hashlib.sha256((self.root/path).read_bytes()).hexdigest()
    def call(self,*args,ok=True):
        result = subprocess.run([sys.executable,str(CLI),'--workspace',str(self.root),*args],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0 if ok else 2,result.stdout+result.stderr)
        return json.loads(result.stdout)
    def prepare(self):
        self.write('analysis.json',self.analysis); self.call('reference','--campaign','crm','--analysis','analysis.json')
        self.write('spec.json',self.spec); self.call('compile','--campaign','crm','--variant','one','--reference','ref-one','--spec','spec.json')
    def render(self,number=1): return self.call('render','--campaign','crm','--variant','one','--iteration',str(number),'--source','generated.html','--png','render.png','--generator','Synthetic test fixture generator')
    def review(self,number=1,visual='revise',technical='pass',best=True,findings=True):
        data={'observer':'fixture-reviewer','inspected_at':'2026-01-01T00:00:00Z','source_sha256':self.hash('generated.html'),'png_sha256s':[self.hash('render.png')],'pixel_observations':[{'png_sha256':self.hash('render.png'),'observation':'Synthetic fixture observation, not real review'}],'technical':{'status':technical,'evidence':'Synthetic check'},'visual':{'status':visual,'evidence':'Synthetic observation'},'human':{'status':'not-run','evidence':'No human input'},'independent':{'technical':'not-run','visual':'not-run','evidence':'No independent review'},'findings':[{'id':'hierarchy','category':'visual','severity':'major','evidence':'Synthetic fixture title hierarchy','action':'Increase fixture title'}] if findings else [],'best_so_far':best,'replace_reference':False}
        self.write('review.json',data); self.call('review','--campaign','crm','--variant','one','--iteration',str(number),'--record','review.json'); return data
    def test_full_bounded_loop_winner_only_cleanup(self):
        self.prepare(); self.render(); self.review()
        self.assertEqual(self.call('decide','--campaign','crm','--variant','one','--iteration','1')['action'],'revise')
        self.spec['delta_findings']=['hierarchy']; self.write('spec.json',self.spec)
        self.call('compile','--campaign','crm','--variant','one','--reference','ref-one','--spec','spec.json'); self.render(2); self.review(2,visual='candidate',findings=False)
        decision=self.call('decide','--campaign','crm','--variant','one','--iteration','2'); self.assertEqual(decision['action'],'keep-candidate'); self.assertEqual(decision['human_acceptance'],'not-run')
        self.call('compile','--campaign','crm','--variant','one','--reference','ref-one','--spec','spec.json',ok=False)
        self.call('export','--campaign','crm','--variant','one','--iteration','2')
        self.call('cleanup','--campaign','crm')
        self.assertTrue((self.root/'reference.png').exists()); self.assertTrue((self.root/'render.png').exists())
        self.assertTrue((self.root/'exports/crm/one/2/view-1.png').exists()); self.assertFalse((self.root/'exports/crm/one/1').exists())
        self.assertTrue((self.root/'campaigns/crm/one/1/review.json').exists())
        self.assertEqual(len(json.loads((self.root/'campaigns/crm/cleanup.json').read_text())['files']),0)
        self.assertTrue((self.root/'generated.html').exists()) # Legacy paths remain accepted and conservatively preserved.
    def test_unobserved_rights_hash_and_missing_reference(self):
        for key in ('unobserved','rights','hash','missing'):
            value=json.loads(json.dumps(self.analysis))
            if key=='unobserved': value['observed']['method']='metadata-only'
            if key=='rights': value['rights']['status']='unknown'
            if key=='hash': value['asset_sha256']='0'*64
            if key=='missing': value['asset_path']='missing.png'
            self.write('bad.json',value); self.call('reference','--campaign','crm','--analysis','bad.json',ok=False)
    def test_no_actual_png_and_stale_reviews(self):
        self.prepare(); self.write('render.png',b'not png'); self.render_fail()
        self.write('render.png',png()); self.render()
        self.write('generated.html','Changed source')
        self.write('review.json',{}); self.call('review','--campaign','crm','--variant','one','--iteration','1','--record','review.json',ok=False)
    def render_fail(self): self.call('render','--campaign','crm','--variant','one','--iteration','1','--source','generated.html','--png','render.png','--generator','fixture',ok=False)
    def test_technical_pass_never_visual_acceptance(self):
        self.prepare(); self.render(); self.review(visual='not-run',findings=False)
        result=self.call('decide','--campaign','crm','--variant','one','--iteration','1')
        self.assertEqual(result['action'],'await-user'); self.assertEqual(result['human_acceptance'],'not-run')
    def test_reference_change_invalidates_review_and_compile(self):
        self.prepare(); self.render(); self.review(); self.write('reference.png',png()+b'changed')
        self.call('decide','--campaign','crm','--variant','one','--iteration','1',ok=False)
        self.spec['delta_findings']=['hierarchy']; self.write('spec.json',self.spec)
        self.call('compile','--campaign','crm','--variant','one','--reference','ref-one','--spec','spec.json',ok=False)
    def test_paths_lock_variant_budget_and_unknown_directives(self):
        for path in ('../task.json','C:/outside.json','CON','bad.json:stream'):
            self.call('create','--task',path,'--campaign','bad',ok=False)
        self.write('.pipeline-lock','unrelated-pid'); self.call('create','--task','task.json','--campaign','bad',ok=False)
        self.assertEqual((self.root/'.pipeline-lock').read_text(),'unrelated-pid'); (self.root/'.pipeline-lock').unlink()
        self.prepare(); self.render(); self.review()
        self.call('compile','--campaign','crm','--variant','two','--reference','ref-one','--spec','spec.json',ok=False)
        self.spec['directives'][0]['trait_id']='unknown'; self.write('spec.json',self.spec)
        self.call('compile','--campaign','crm','--variant','one','--reference','ref-one','--spec','spec.json',ok=False)
    def test_cleanup_requires_verified_winner_export(self):
        self.prepare(); self.render(); self.review(); self.call('cleanup','--campaign','crm',ok=False)
        self.assertTrue((self.root/'reference.png').exists()); self.call('export','--campaign','crm','--variant','one','--iteration','1')
        self.write('exports/crm/one/1/view-1.png',b'changed'); self.call('cleanup','--campaign','crm',ok=False)
        self.assertTrue((self.root/'reference.png').exists())
    def test_export_rejects_superseded_iteration(self):
        self.prepare(); self.render(); self.review()
        self.spec['delta_findings']=['hierarchy']; self.write('spec.json',self.spec)
        self.call('compile','--campaign','crm','--variant','one','--reference','ref-one','--spec','spec.json')
        self.render(2); self.review(2,visual='candidate',findings=False)
        self.call('export','--campaign','crm','--variant','one','--iteration','1',ok=False)
        self.assertFalse((self.root/'exports/crm/one/1').exists())
        self.call('export','--campaign','crm','--variant','one','--iteration','2')
    def test_png_scanline_length_and_task_freshness(self):
        self.prepare()
        def chunk(kind,body): return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body)&0xffffffff)
        malformed=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00'))+chunk(b'IEND',b'')
        self.write('render.png',malformed); self.render_fail()
        self.write('render.png',png()); self.render(); self.review()
        campaign=json.loads((self.root/'campaigns/crm/campaign.json').read_text())
        campaign['task']['job']='Changed contract'
        self.write('campaigns/crm/campaign.json',campaign)
        self.call('decide','--campaign','crm','--variant','one','--iteration','1',ok=False)
    def test_cleanup_rejects_shared_unicode_alias_paths(self):
        self.write('references/референс.png',png()); self.analysis['asset_path']='references/референс.png'
        self.analysis['asset_sha256']=self.hash('references/референс.png')
        self.prepare(); self.render(); self.review()
        self.call('export','--campaign','crm','--variant','one','--iteration','1')
        self.call('create','--task','task.json','--campaign','other')
        shared=dict(self.analysis); shared['asset_path']='./references/референс.png'
        self.write('shared.json',shared)
        self.call('reference','--campaign','other','--analysis','shared.json')
        self.call('cleanup','--campaign','crm',ok=False)
        self.assertTrue((self.root/'references/референс.png').exists())
        self.assertTrue((self.root/'generated.html').exists())
    def test_reference_generated_alias_rejected(self):
        self.prepare()
        self.call('render','--campaign','crm','--variant','one','--iteration','1','--source','generated.html','--png','./reference.png','--generator','fixture',ok=False)
        self.assertFalse((self.root/'campaigns/crm/one/1/render.json').exists())
    def test_hash_pinned_review_and_independent_identity(self):
        self.prepare(); self.render()
        data={'observer':'same','inspected_at':'2026-01-01T00:00:00Z','source_sha256':self.hash('generated.html'),'png_sha256s':[self.hash('render.png')],'pixel_observations':[{'png_sha256':self.hash('render.png'),'observation':'Synthetic pixel'}],'technical':{'status':'pass','evidence':'fixture'},'visual':{'status':'candidate','evidence':'fixture'},'human':{'status':'not-run','evidence':'fixture'},'independent':{'technical':'pass','visual':'pass','reviewer':'same','evidence':'fixture'},'findings':[],'best_so_far':True,'replace_reference':False}
        self.write('review.json',data); self.call('review','--campaign','crm','--variant','one','--iteration','1','--record','review.json',ok=False)
        data['independent']['reviewer']='other'; data['png_sha256s']=['0'*64]
        self.write('review.json',data); self.call('review','--campaign','crm','--variant','one','--iteration','1','--record','review.json',ok=False)
        data['png_sha256s']=[self.hash('render.png')]; data['pixel_observations']=[]
        self.write('review.json',data); self.call('review','--campaign','crm','--variant','one','--iteration','1','--record','review.json',ok=False)
    def test_managed_record_link_rejected(self):
        self.prepare(); target=self.root/'outside'; target.mkdir()
        link=self.root/'campaigns/crm/redirect'
        try: link.symlink_to(target,target_is_directory=True)
        except OSError: self.skipTest('Host does not permit creating symlink fixtures')
        self.call('compile','--campaign','crm','--variant','one','--reference','ref-one','--spec','spec.json',ok=False)

if __name__=='__main__': unittest.main(verbosity=2)
