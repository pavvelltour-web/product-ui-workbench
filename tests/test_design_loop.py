import unittest,tempfile,json,sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from design_loop import prepare,bind,review,attach,amend
from pipeline import GateError
import test_pipeline as fixtures
class DesignLoopTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.r=Path(self.tmp.name).resolve()
  for n in ['analysis','patterns']:(self.r/f'{n}.json').write_text('{}')
  (self.r/'prompt.md').write_text('Proposed layer, type, component and primary accent color adaptation. '*8)
  prepare(self.r,'abstract','analysis.json','patterns.json','prompt.md','ledger.json',1,source_root='generated')
  (self.r/'generated').mkdir()
  (self.r/'capture.png').write_bytes(fixtures.png());self.evidence()
 def tearDown(self):self.tmp.cleanup()
 def test_design_without_product_or_backend_and_stale_prompt_rejected(self):
  (self.r/'generated/source.jsx').write_text('original interface')
  (self.r/'prompt.md').write_text('changed')
  with self.assertRaises(GateError):bind(self.r,'ledger.json',['generated/source.jsx'])
  self.assertEqual(json.loads((self.r/'ledger.json').read_text())['iterations'],[])
 def test_actual_review_required_and_budget_not_reset(self):
  (self.r/'generated/source.jsx').write_text('original interface');bind(self.r,'ledger.json',['generated/source.jsx'])
  with self.assertRaises(GateError):bind(self.r,'ledger.json',['generated/source.jsx'])
  (self.r/'capture.png').write_bytes(fixtures.png())
  q={'observer':'independent','captures':[{'path':'capture.png','sha256':hashlib.sha256((self.r/'capture.png').read_bytes()).hexdigest(),'viewed':True}],'dimensions':{k:{'status':'pass','evidence':'external observer attestation'} for k in ['reference-fidelity','composition','color-hierarchy','component-coherence','material','responsive-states']},'decision':'candidate','human_acceptance':'pending','artifacts':self.artifacts,'calibration_comparison':{'reference_ids':['source'],'region':'fixture fragment','status':'pass','evidence':'synthetic test observer attestation, not real browser evidence'}}
  (self.r/'review.json').write_text(json.dumps(q));review(self.r,'ledger.json','review.json')
  with self.assertRaises(GateError):bind(self.r,'ledger.json',['generated/source.jsx'])
  with self.assertRaises(GateError):prepare(self.r,'abstract','analysis.json','patterns.json','prompt.md','ledger.json',2)
 def evidence(self):
  def pin(name):return {'path':name,'sha256':hashlib.sha256((self.r/name).read_bytes()).hexdigest()}
  packet={'version':'1.0','sources':[{'id':'source','canonical_url':'https://example.org/synthetic-source','app':'Synthetic fixture','platform':'web','visible_state':'default','viewed':True,'observer':'synthetic test observer','rights':'original','kind':'actual-ui','evidence':pin('capture.png')}],'patterns':[{'id':'one','source_id':'source','role':'composition','kind':'proposed','observation':'Synthetic shape','directive':'Synthetic direction','suitable_for':'fixture','unsuitable_for':'real visual quality claim'}],'selected_pattern_ids':['one']}
  (self.r/'references.json').write_text(json.dumps(packet));attach(self.r,'ledger.json','references.json')
  (self.r/'build').mkdir();(self.r/'build/index.html').write_text('<title>synthetic fixture</title>')
  manifest={'root':'build','entry':'index.html','ownership':'active','files':[{'path':'index.html','sha256':hashlib.sha256((self.r/'build/index.html').read_bytes()).hexdigest()}]}
  (self.r/'manifest.json').write_text(json.dumps(manifest));self.artifacts={}
  for kind in ['calibration','study','components']:
   mode='' if kind=='study' else '&mode='+kind
   cap={'passed':True,'view_query':'variant=abstract'+mode,'source_manifest':{**pin('manifest.json'),'closure':manifest},'screenshots':[{**pin('capture.png'),'state':v} for v in ['desktop','mobile']]}
   name=kind+'-capture.json';(self.r/name).write_text(json.dumps(cap));self.artifacts[kind]=pin(name)
 def test_existing_source_cannot_be_prepared_and_prompt_cannot_be_amended(self):
  (self.r/'generated/source.jsx').write_text('existing')
  with self.assertRaises(GateError):prepare(self.r,'other','analysis.json','patterns.json','prompt.md','other.json',source_root='generated')
  with self.assertRaises(GateError):amend(self.r,'ledger.json','prompt','silent rewrite','author')
 def test_detached_png_cannot_approve_a_design(self):
  (self.r/'generated/source.jsx').write_text('source');bind(self.r,'ledger.json',['generated/source.jsx']);(self.r/'capture.png').write_bytes(fixtures.png())
  q={'observer':'fixture','captures':[{'path':'capture.png','sha256':hashlib.sha256((self.r/'capture.png').read_bytes()).hexdigest(),'viewed':True}],'dimensions':{k:{'status':'pass','evidence':'test'} for k in ['reference-fidelity','composition','color-hierarchy','component-coherence','material','responsive-states']},'decision':'candidate','human_acceptance':'pending'}
  (self.r/'review.json').write_text(json.dumps(q))
  with self.assertRaises(GateError):review(self.r,'ledger.json','review.json')
  self.assertIsNone(json.loads((self.r/'ledger.json').read_text())['iterations'][0]['review'])

if __name__=='__main__':unittest.main()
