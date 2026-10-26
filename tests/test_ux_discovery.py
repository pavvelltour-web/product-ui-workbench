"""Synthetic adversarial bookkeeping tests; no claim about real interviews or UX quality."""
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pipeline import GateError
from ux_discovery import validate, run


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.data = json.loads((Path(__file__).resolve().parents[1] / 'docs/ux-discovery.example.json').read_text(encoding='utf-8'))
        (self.root / 'notes.md').write_text('Simulated operator answers; not a real participant.', encoding='utf-8')
        self.data['provenance']['files'] = [self.pin('notes', 'notes.md', 'simulated-notes')]

    def tearDown(self):
        self.tmp.cleanup()

    def pin(self, id, path, kind):
        return {'id': id, 'path': path, 'sha256': hashlib.sha256((self.root / path).read_bytes()).hexdigest(), 'kind': kind}

    def save(self):
        (self.root / 'packet.json').write_text(json.dumps(self.data), encoding='utf-8')

    def test_valid_receipt_is_limited_and_nonaccepting(self):
        result = validate(self.root, self.data)
        self.assertEqual(result['simulated_questions'], 1)
        self.assertEqual(result['human_acceptance'], 'pending')
        self.assertIn('not automatic chronology', result['limitation'])
        self.assertEqual(result['status'], 'declared-and-pins-verified')

    def test_simulated_interview_cannot_be_real_or_unlabelled(self):
        for key, value in [('origin', 'real'), ('evidence_level', 'validated'), ('origin', '')]:
            data = copy.deepcopy(self.data); data['interviews'][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(GateError):
                validate(self.root, data)
        del self.data['interviews'][0]['origin']
        with self.assertRaises(GateError): validate(self.root, self.data)

    def test_answer_must_be_labelled_simulated(self):
        self.data['interviews'][0]['questions'][0]['answer_kind'] = 'reported'
        with self.assertRaises(GateError): validate(self.root, self.data)

    def test_simulation_needs_simulated_source_kind(self):
        self.data['provenance']['files'][0]['kind'] = 'source-notes'
        with self.assertRaises(GateError): validate(self.root, self.data)

    def test_stale_source_pin_is_rejected(self):
        (self.root / 'notes.md').write_text('Changed notes after normalization', encoding='utf-8')
        with self.assertRaisesRegex(GateError, 'Stale pinned file'):
            validate(self.root, self.data)

    def test_missing_tradeoff_or_single_option_is_rejected(self):
        for operation in ('tradeoff', 'single'):
            data = copy.deepcopy(self.data)
            if operation == 'tradeoff': data['products'][0]['alternatives'][0].pop('tradeoff')
            else: data['products'][0]['alternatives'] = data['products'][0]['alternatives'][:1]
            with self.subTest(operation=operation), self.assertRaises(GateError):
                validate(self.root, data)

    def test_unknown_choice_rejected(self):
        self.data['products'][0]['chosen']['id'] = 'nonexistent'
        with self.assertRaisesRegex(GateError, 'Unknown chosen'):
            validate(self.root, self.data)

    def test_scope_ids_and_collection_contract_must_match(self):
        mutations = [lambda d: d['scope'].update(product_ids=['crm']),
                     lambda d: d['products'][0]['scenario']['scopes'][0].pop('selection'),
                     lambda d: d['products'][0]['falsification_cases'][0].update(scope_ids=['global-unknown'])]
        for mutate in mutations:
            data = copy.deepcopy(self.data); mutate(data)
            with self.subTest(mutation=mutate), self.assertRaises(GateError):
                validate(self.root, data)

    def test_state_and_mobile_contracts_required(self):
        for field in ('error', 'cancel'):
            data = copy.deepcopy(self.data); data['products'][0]['scenario']['states'].pop(field)
            with self.subTest(field=field), self.assertRaises(GateError): validate(self.root, data)
        self.data['products'][0]['scenario']['mobile']['touch_target_px'] = 24
        with self.assertRaises(GateError): validate(self.root, self.data)

    def test_fake_score_method_cannot_replace_observable_probe(self):
        self.data['products'][0]['falsification_cases'][0]['method'] = 'simulated-user-score'
        with self.assertRaises(GateError): validate(self.root, self.data)

    def test_validation_and_chronology_claims_rejected(self):
        for mutate in [lambda d: d['provenance'].update(evidence_status='validated-research'),
                       lambda d: d['provenance']['chronology'].update(automatic_enforcement=True),
                       lambda d: d['scope'].update(backend=True)]:
            data = copy.deepcopy(self.data); mutate(data)
            with self.subTest(mutation=mutate), self.assertRaises(GateError): validate(self.root, data)

    def add_confirmation(self):
        (self.root / 'brief.json').write_text(json.dumps({'user_confirmed': 'Manage AI-agent runs'}), encoding='utf-8')
        self.data['provenance']['files'].append(self.pin('brief', 'brief.json', 'user-brief'))
        self.data['assumptions'][0].update(status='user-confirmed', confirmation={
            'file_id': 'brief', 'json_pointer': '/user_confirmed', 'expected_value': 'Manage AI-agent runs'})

    def test_actual_recorded_confirmation_pointer_matches(self):
        self.add_confirmation()
        self.assertEqual(validate(self.root, self.data)['product_ids'], ['ai'])
        self.data['assumptions'][0]['confirmation']['expected_value'] = 'Invented domain'
        with self.assertRaisesRegex(GateError, 'pointer/value mismatch'):
            validate(self.root, self.data)

    def test_unknown_confirmation_pointer_rejected(self):
        self.add_confirmation()
        self.data['assumptions'][0]['confirmation']['json_pointer'] = '/missing'
        with self.assertRaises(GateError): validate(self.root, self.data)

    def test_unresolved_cannot_look_confirmed(self):
        self.add_confirmation(); self.data['assumptions'][0]['status'] = 'unresolved'
        with self.assertRaises(GateError): validate(self.root, self.data)

    def test_no_interviews_optional_for_new_ux_but_not_explicit_simulation(self):
        self.data['interviews'] = []
        with self.assertRaises(GateError): validate(self.root, self.data)
        self.data['applicability']['mode'] = 'new-operational'
        self.assertEqual(validate(self.root, self.data)['simulated_interviews'], 0)

    def test_safe_workspace_relative_pins_and_io(self):
        self.save()
        for bad in ('../packet.json', 'C:/outside.json', '/outside.json', 'NUL', 'notes.md:stream'):
            with self.subTest(path=bad), self.assertRaises((GateError, FileNotFoundError)):
                run(self.root, bad)
        data = copy.deepcopy(self.data); data['provenance']['files'][0]['path'] = '../notes.md'
        with self.assertRaises(GateError): validate(self.root, data)
        with self.assertRaises(GateError): run(self.root, 'packet.json', '../receipt.json')

    def test_receipt_never_overwrites_input_or_existing_output(self):
        self.save(); before = (self.root / 'packet.json').read_bytes()
        with self.assertRaises(GateError): run(self.root, 'packet.json', 'packet.json')
        self.assertEqual((self.root / 'packet.json').read_bytes(), before)
        result = run(self.root, 'packet.json', 'out/receipt.json')
        self.assertEqual(json.loads((self.root / 'out/receipt.json').read_text())['input'], result['input'])
        with self.assertRaises(GateError): run(self.root, 'packet.json', 'out/receipt.json')

    def test_symlink_pin_is_rejected_when_supported(self):
        try: (self.root / 'link.md').symlink_to(self.root / 'notes.md')
        except OSError: self.skipTest('Host does not permit symlink creation')
        self.data['provenance']['files'][0]['path'] = 'link.md'
        with self.assertRaises(GateError): validate(self.root, self.data)


if __name__ == '__main__':
    unittest.main()
