"""Synthetic bookkeeping probes, not human UX approval or real design observations."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from pipeline import GateError
from design_loop import prepare, bind, attach, review, revision
from ux_contract import validate_plan, CRITERIA
import test_design_loop as design_fixtures


def example():
    path = Path(__file__).resolve().parents[1] / 'docs/ux-plan.example.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    data['study_id'] = 'abstract'
    # Retain this suite's legacy no-probe contract as the public example gains optional checks.
    # New actual-browser/probe gates are exercised separately in test_browser_probe.py.
    data.pop('interaction_checks', None)
    return data


class UxPlanTests(unittest.TestCase):
    def test_aggregate_can_lead_when_explicitly_justified(self):
        plan = example()
        plan['intent']['statement'] = 'Proposed executive overview: compare the current open commitment.'
        plan['attention']['primary'] = {'content': 'Open amount', 'reason': 'This supplied overview centers the current aggregate, not daily action work.', 'action': 'Compare the amount and inspect its constituent deals'}
        self.assertEqual(validate_plan(plan)['study_id'], 'abstract')

    def test_incomplete_or_ambiguous_plan_rejected(self):
        for mutation in [lambda p: p['attention']['primary'].pop('reason'),
                         lambda p: p['typography'].pop('label'),
                         lambda p: p['grouping'][0].update(outer_gap=8),
                         lambda p: p.update(chart={'present': True, 'measure': 'amount'}),
                         lambda p: p['mobile'].update(expected_order=[])]:
            plan = example(); mutation(plan)
            with self.assertRaises(GateError):
                validate_plan(plan)


class UxEvidenceTests(unittest.TestCase):
    def setUp(self):
        design_fixtures.DesignLoopTests.setUp(self)
        # Replace only the synthetic pre-source ledger, retaining its empty generated root.
        (self.r / 'ledger.json').unlink()
        self.write('ux-plan.json', example())
        prepare(self.r, 'abstract', 'analysis.json', 'patterns.json', 'prompt.md',
                'ledger.json', 2, source_root='generated', ux_plan='ux-plan.json')
        attach(self.r, 'ledger.json', 'references.json')
        (self.r / 'generated/source.jsx').write_text('Synthetic original interface')
        bind(self.r, 'ledger.json', ['generated/source.jsx'])
        (self.r / 'capture-mobile.png').write_bytes((self.r / 'capture.png').read_bytes())
        for kind in self.artifacts:
            name = kind + '-capture.json'
            capture = json.loads((self.r / name).read_text())
            capture['screenshots'][1] = {**self.pin('capture-mobile.png'), 'state': 'mobile'}
            self.write(name, capture)
            self.artifacts[kind] = self.pin(name)
        self.ux = {'version': '1.0', 'study_id': 'abstract', 'plan_sha256': self.pin('ux-plan.json')['sha256'],
                   'observer': 'Synthetic test observer', 'human_acceptance': 'pending',
                   'artifacts': self.artifacts, 'source_manifests': [self.pin('manifest.json')],
                   'captures': [{**self.pin('capture.png'), 'viewed': True},
                                {**self.pin('capture-mobile.png'), 'viewed': True}],
                   'criteria': {name: {'status': 'pass', 'method': 'image-observation',
                                      'evidence': 'Synthetic fixture attestation, not a real UX inspection.',
                                      'capture_sha256s': [self.pin('capture.png')['sha256']]}
                                for name in CRITERIA}}
        self.data = {'observer': 'Synthetic test reviewer', 'captures': self.ux['captures'],
                     'dimensions': {name: {'status': 'pass', 'evidence': 'Synthetic fixture visual attestation'}
                                    for name in ['reference-fidelity', 'composition', 'color-hierarchy',
                                                 'component-coherence', 'material', 'responsive-states']},
                     'decision': 'candidate', 'human_acceptance': 'pending', 'artifacts': self.artifacts,
                     'calibration_comparison': {'reference_ids': ['source'], 'region': 'Synthetic fixture',
                                                'status': 'pass', 'evidence': 'Invented test comparison'}}

    tearDown = design_fixtures.DesignLoopTests.tearDown
    evidence = design_fixtures.DesignLoopTests.evidence

    def write(self, name, data):
        (self.r / name).write_text(json.dumps(data), encoding='utf-8')

    def pin(self, name):
        return {'path': name, 'sha256': hashlib.sha256((self.r / name).read_bytes()).hexdigest()}

    def save(self):
        self.write('ux-evidence.json', self.ux)
        self.data['ux_evidence'] = self.pin('ux-evidence.json')
        self.write('review.json', self.data)

    def reject(self):
        self.save()
        with self.assertRaises(GateError):
            review(self.r, 'ledger.json', 'review.json')
        ledger = json.loads((self.r / 'ledger.json').read_text())
        self.assertIsNone(ledger['iterations'][0]['review'])

    def test_full_pinned_ux_candidate_retains_six_visual_dimensions(self):
        self.save()
        result = review(self.r, 'ledger.json', 'review.json')
        self.assertEqual(result['decision'], 'candidate')
        ledger = json.loads((self.r / 'ledger.json').read_text())
        self.assertEqual(len(ledger['iterations'][0]['review']['dimensions']), 6)
        self.assertEqual(len(ledger['iterations'][0]['review']['ux']['criteria']), 8)
        self.assertEqual(ledger['human_acceptance'], 'pending')

    def test_plan_is_fresh_at_bind_and_review(self):
        self.write('ux-plan.json', {**example(), 'changed': True})
        self.reject()
        with self.assertRaises(GateError):
            bind(self.r, 'ledger.json', ['generated/source.jsx'])

    def test_missing_ux_evidence_cannot_approve(self):
        self.write('review.json', self.data)
        with self.assertRaisesRegex(GateError, 'UX evidence'):
            review(self.r, 'ledger.json', 'review.json')

    def test_wrong_manifest_or_capture_pin_cannot_approve(self):
        original = copy.deepcopy(self.ux)
        self.ux['source_manifests'] = []
        self.reject()
        self.ux = original
        self.ux['artifacts'] = copy.deepcopy(self.artifacts)
        self.ux['artifacts']['study'] = self.pin('manifest.json')
        self.reject()

    def test_missing_viewed_study_or_wrong_plan_cannot_approve(self):
        original = copy.deepcopy(self.ux)
        self.ux['captures'][0]['viewed'] = False
        self.reject()
        self.ux = original
        self.ux['plan_sha256'] = '0' * 64
        self.reject()

    def test_desktop_only_or_stale_ux_file_cannot_approve(self):
        original = copy.deepcopy(self.ux)
        self.ux['captures'] = self.ux['captures'][:1]
        self.reject()
        self.ux = original
        self.save()
        self.write('ux-evidence.json', {**self.ux, 'changed': True})
        with self.assertRaisesRegex(GateError, 'Stale evidence'):
            review(self.r, 'ledger.json', 'review.json')

    def test_revise_or_not_run_ux_blocks_candidate(self):
        for status in ['revise', 'not-run']:
            self.ux['criteria']['attention-priority']['status'] = status
            self.reject()

    def test_automatic_attention_score_and_unmeasured_dom_cannot_approve(self):
        self.ux['criteria']['attention-priority']['method'] = 'measured-dom'
        self.reject()
        self.ux['criteria']['attention-priority']['method'] = 'image-observation'
        self.ux['criteria']['type-roles']['method'] = 'measured-dom'
        self.reject()

    def test_ux_revision_chains_same_budget_and_named_finding(self):
        self.ux['criteria']['attention-priority']['status'] = 'revise'
        self.data.update(decision='revise', changed_module='attention', next_change='Make the next due action first')
        self.save(); review(self.r, 'ledger.json', 'review.json')
        (self.r / 'prompt-v2.md').write_text('Correct the next useful action priority while retaining source calibration. ' * 5)
        result = revision(self.r, 'ledger.json', 'prompt-v2.md', ['attention-priority'], 'attention', 'Due action precedes amount')
        self.assertFalse(result['budget_reset'])
        self.assertEqual(result['remaining'], 1)


if __name__ == '__main__':
    unittest.main()
