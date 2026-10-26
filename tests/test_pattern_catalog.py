import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from pattern_catalog import ingest,search
from pipeline import GateError
import test_pattern_loop as fixtures
class CatalogTests(unittest.TestCase):
    setUp=fixtures.PatternEvidenceTests.setUp
    tearDown=fixtures.PatternEvidenceTests.tearDown
    def test_accumulates_history_and_reuses_without_duplicate(self):
        (self.root/'packet.json').write_text(json.dumps(self.packet))
        self.assertEqual(ingest(self.root,'packet.json','catalog.json','v6')['changes'],1)
        self.assertEqual(ingest(self.root,'packet.json','catalog.json','v6')['changes'],0)
        changed=json.loads((self.root/'packet.json').read_text());changed['patterns'][0]['directive']='Use44px touch target while preserving compact desktop control.'
        (self.root/'packet.json').write_text(json.dumps(changed))
        ingest(self.root,'packet.json','catalog.json','v6')
        data=json.loads((self.root/'catalog.json').read_text());self.assertEqual(len(data['patterns']),1);self.assertEqual(len(data['history']),2)
        self.assertEqual(data['history'][1]['changes'][0]['previous']['directive'],self.packet['patterns'][0]['directive'])
        self.assertEqual(len(search(data,'touch',role='component',platform='web')),1)
        self.assertEqual(search(data,'touch',platform='ios'),[])
        self.assertNotIn('measurement_evidence',data['patterns'][0])
    def test_stale_packet_cannot_enter_catalog(self):
        (self.root/'packet.json').write_text(json.dumps(self.packet));(self.root/'dom.json').write_text('changed')
        with self.assertRaises(GateError):ingest(self.root,'packet.json','catalog.json','v6')
        self.assertFalse((self.root/'catalog.json').exists())
