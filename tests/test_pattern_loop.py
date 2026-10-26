import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pattern_loop import validate, compile_patterns, review
from pipeline import GateError

class PatternEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        (self.root/'dom.json').write_text('{"selector":"button","height":"36px"}')
        self.pin = {'path':'dom.json', 'sha256':hashlib.sha256((self.root/'dom.json').read_bytes()).hexdigest()}
        self.packet = {'version':'1.0','sources':[{'id':'geist','canonical_url':'https://vercel.com/geist/button','rights':'unknown-private','kind':'component-ui','app':'Geist','platform':'web','visible_state':'default','viewed':True,'observer':'researcher','evidence':self.pin}], 'patterns':[{'id':'button-rhythm','source_id':'geist','role':'component','kind':'measured-code','observation':'Medium button is 36 px tall.','directive':'Use 36 px controls for dense desktop toolbar, 44 px touch targets.','suitable_for':'dense desktop navigation','unsuitable_for':'unmodified phone touch target','selector':'button[data-size=medium]','property':'height','value':'36px','measurement_evidence':self.pin}],'selected_pattern_ids':['button-rhythm']}
    def tearDown(self): self.temp.cleanup()
    def test_traceable_compile_preserves_existing(self):
        result=compile_patterns(self.root,self.packet,'directives.md')
        self.assertEqual(result['selected'],1)
        self.assertIn('[button-rhythm; measured-code; source geist]',(self.root/'directives.md').read_text())
        with self.assertRaises(GateError): compile_patterns(self.root,self.packet,'directives.md')
    def test_private_rights_and_actual_observer_required(self):
        for key,value in [('rights',None),('viewed',False),('observer','')]:
            with self.subTest(key=key):
                data=copy.deepcopy(self.packet);data['sources'][0][key]=value
                with self.assertRaises(GateError): validate(self.root,data)
    def test_no_unobserved_hover(self):
        data=copy.deepcopy(self.packet);data['patterns'][0]['claimed_states']=['hover'];data['patterns'][0]['observed_states']=['default']
        with self.assertRaises(GateError): validate(self.root,data)
    def test_changed_dom_invalidates_measurement(self):
        (self.root/'dom.json').write_text('{"height":"99px"}')
        with self.assertRaises(GateError): validate(self.root,self.packet)
    def test_image_estimate_cannot_claim_css_pixels(self):
        data=copy.deepcopy(self.packet);item=data['patterns'][0];item.update(kind='measured-image',image_size=[1000,800],region=[0,0,36,36],unit='css-px',uncertainty='±2 px')
        with self.assertRaises(GateError): validate(self.root,data)
    def test_unknown_pattern_and_duplicate_ids(self):
        data=copy.deepcopy(self.packet);data['selected_pattern_ids']=['invented']
        with self.assertRaises(GateError): validate(self.root,data)
        data=copy.deepcopy(self.packet);data['patterns'].append(data['patterns'][0])
        with self.assertRaises(GateError): validate(self.root,data)
    def test_recovery_review_cannot_be_self_certified(self):
        data={'version':'1.0','author':'same','reviewer':'same','independent':True,'captures':[{**self.pin,'viewed':True}],'dimensions':{x:{'status':'pass','evidence':'observed working state'} for x in ['composition','type-spacing','color-material','responsive','task-recovery','reference-transfer']},'decision':'candidate','human_acceptance':'pending'}
        with self.assertRaises(GateError): review(self.root,data)
        data['reviewer']='other';data['dimensions']['task-recovery']['status']='fail'
        with self.assertRaises(GateError): review(self.root,data)
        data.update(decision='research-again',next_question='Why does failed save erase the draft?',changed_module='state-recovery')
        self.assertEqual(review(self.root,data)['failed_dimensions'],['task-recovery'])
    def test_workspace_escape(self):
        data=copy.deepcopy(self.packet);data['sources'][0]['evidence']={'path':'../dom.json','sha256':self.pin['sha256']}
        with self.assertRaises(GateError): validate(self.root,data)

if __name__=='__main__': unittest.main()
