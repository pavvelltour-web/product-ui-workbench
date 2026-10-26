"""Actual minimal Chrome fixture plus negative evidence gates; not design/user approval."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from _browser_support import require_browser
from pipeline import GateError
from browser_probe import probe
from ux_contract import validate_plan, validate_interaction_evidence
import test_ux_contract as ux_fixtures


def planned_checks():
    return [{'id': 'stage-value', 'kind': 'selected-value-visible', 'target': '[data-slot=select-value]', 'viewports': ['desktop', 'mobile']},
            {'id': 'deal-open', 'kind': 'open-region', 'trigger': '[data-testid=deal-d1]', 'target': 'dialog',
             'identity': 'Sample Company', 'viewports': ['desktop', 'mobile'], 'close': 'Escape', 'focus_return': True}]


class InteractionPlanTests(unittest.TestCase):
    def test_old_plan_and_explicit_interaction_plan_supported(self):
        plan = ux_fixtures.example(); validate_plan(plan)
        plan['interaction_checks'] = planned_checks(); validate_plan(plan)

    def test_empty_duplicate_incomplete_or_mobile_omission_rejected(self):
        for mutate in [lambda c: c.clear(), lambda c: c[1].update(id=c[0]['id']),
                       lambda c: c[1].pop('identity'), lambda c: c[0].update(viewports=['desktop']),
                       lambda c: c[1].update(focus_return=False)]:
            plan = ux_fixtures.example(); plan['interaction_checks'] = planned_checks(); mutate(plan['interaction_checks'])
            with self.assertRaises(GateError): validate_plan(plan)


class BrowserInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chrome = require_browser()
        cls.temp = tempfile.TemporaryDirectory(prefix='workbench-interaction-')
        cls.root = Path(cls.temp.name); source = cls.root / 'build'; source.mkdir()
        html = '''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Actual interaction fixture</title>
<style>body{font:16px Arial;padding:20px}button{font:14px Arial;min-height:44px}dialog{font:16px Arial;width:260px}.hidden{display:none}</style></head><body>
<h1>Fixture</h1><button aria-label="All stages"><span data-slot="select-value">Все этапы</span><span id="hidden-value" class="hidden">Hidden text</span></button>
<button data-testid="deal-d1" onclick="document.querySelector('dialog').showModal()">Sample Company — открыть</button>
<dialog><h2>Sample Company</h2><p>Согласовать финальную версию договора</p><button onclick="this.closest('dialog').close()">Закрыть</button></dialog></body></html>'''
        (source / 'index.html').write_text(html, encoding='utf-8')
        cls.write('manifest.json', {'root': 'build', 'entry': 'index.html', 'ownership': 'active',
                                   'files': [{'path': 'index.html', 'sha256': cls.pin('build/index.html')['sha256']}]})
        plan = ux_fixtures.example(); plan['interaction_checks'] = planned_checks()
        cls.write('plan.json', plan)
        cls.result = probe(cls.root, 'manifest.json', 'plan.json', str(cls.chrome), 'images/probe')
        cls.artifacts = {'study': cls.pin('capture.json')}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def pin(cls, name):
        # Synthetic capture wrapper only links the actual manifest; actual state PNGs come from Chrome.
        if name == 'capture.json' and not (cls.root / name).exists():
            cls.write(name, {'source_manifest': cls.result['source_manifest']})
        return {'path': name, 'sha256': hashlib.sha256((cls.root / name).read_bytes()).hexdigest()}

    @classmethod
    def write(cls, name, data):
        (cls.root / name).write_text(json.dumps(data), encoding='utf-8')

    def validate(self, data, decision='candidate'):
        return validate_interaction_evidence(self.root, self.pin('plan.json'), data, 'abstract', self.artifacts, decision)

    def test_actual_both_widths_open_close_focus_and_visible_selected_text(self):
        self.assertTrue(self.result['passed'], self.result)
        self.assertEqual(len(self.result['cases']), 4)
        self.assertTrue(self.validate(self.result)['passed'])

    def test_actual_hidden_selected_text_fails_even_with_aria_frame(self):
        plan = ux_fixtures.example(); plan['interaction_checks'] = [planned_checks()[0]]
        plan['interaction_checks'][0]['target'] = '#hidden-value'
        self.write('hidden-plan.json', plan)
        result = probe(self.root, 'manifest.json', 'hidden-plan.json', str(self.chrome), 'images/hidden')
        self.assertFalse(result['passed'])
        self.assertTrue(all(not case['assertions']['text_readable'] for case in result['cases']))
        self.assertTrue(all(any(s['state'] == 'failure' for s in case['screenshots']) for case in result['cases']))

    def test_secondary_selected_value_is_revealed_without_claiming_initial_fold(self):
        # Own closure: never mutate the class fixture or its pinned manifest.
        with tempfile.TemporaryDirectory(prefix='workbench-offscreen-') as name:
            root = Path(name); source = root / 'build'; source.mkdir()
            html = (self.root / 'build/index.html').read_text(encoding='utf-8')
            html = html.replace('<h1>Fixture</h1>', '<h1>Fixture</h1><div style="height:1200px" aria-hidden="true"></div>')
            (source / 'index.html').write_text(html, encoding='utf-8')
            manifest = {'root': 'build', 'entry': 'index.html', 'ownership': 'active',
                        'files': [{'path': 'index.html', 'sha256': hashlib.sha256((source / 'index.html').read_bytes()).hexdigest()}]}
            (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
            plan = ux_fixtures.example(); plan['interaction_checks'] = [planned_checks()[0]]
            (root / 'plan.json').write_text(json.dumps(plan), encoding='utf-8')
            result = probe(root, 'manifest.json', 'plan.json', str(self.chrome), 'images/revealed')
            self.assertTrue(result['passed'], result)
            for case in result['cases']:
                self.assertFalse(case['measurements']['initial_target']['in_viewport'])
                self.assertTrue(case['measurements']['target']['in_viewport'])
                self.assertTrue(case['measurements']['target']['readable'])
                self.assertTrue(any(s['state'] == 'revealed' and (root / s['path']).is_file() for s in case['screenshots']))

    def test_actual_external_bindings_preserve_frozen_plan(self):
        plan = ux_fixtures.example(); self.write('legacy-plan.json', plan)
        before = self.pin('legacy-plan.json')
        self.write('selector-bindings.json', {'version': '1.0', 'study_id': 'abstract',
                                             'interaction_checks': planned_checks()})
        result = probe(self.root, 'manifest.json', 'legacy-plan.json', str(self.chrome), 'images/external', 'selector-bindings.json')
        self.assertTrue(result['passed'], result)
        validated = validate_interaction_evidence(self.root, before, result, 'abstract', self.artifacts,
                                                 'candidate', self.pin('selector-bindings.json'))
        self.assertTrue(validated['passed'])
        self.assertEqual(before, self.pin('legacy-plan.json'))
        result['checks_contract']['sha256'] = '0' * 64
        with self.assertRaises(GateError):
            validate_interaction_evidence(self.root, before, result, 'abstract', self.artifacts,
                                          'candidate', self.pin('selector-bindings.json'))

    def test_claim_only_missing_case_wrong_manifest_and_not_run_cannot_approve(self):
        for mutate in [lambda d: d.update(cases=[]),
                       lambda d: d.update(plan_sha256='0' * 64),
                       lambda d: d['source_manifest'].update(sha256='0' * 64),
                       lambda d: d['cases'][0]['assertions'].update(text_readable=False),
                       lambda d: d['cases'][0].update(measurements={}),
                       lambda d: d['cases'][0].update(passed='not-run'),
                       lambda d: d['cases'][0].update(screenshots=[]),
                       lambda d: d.update(console_errors=['Actual error'])]:
            data = copy.deepcopy(self.result); mutate(data)
            with self.assertRaises(GateError): self.validate(data)

    def test_stale_plan_and_png_fail_closed(self):
        data = copy.deepcopy(self.result)
        data['cases'][0]['screenshots'][0]['sha256'] = '0' * 64
        with self.assertRaises(GateError): self.validate(data)
        wrong = self.pin('plan.json'); wrong['sha256'] = '0' * 64
        with self.assertRaises(GateError):
            validate_interaction_evidence(self.root, wrong, self.result, 'abstract', self.artifacts, 'candidate')


class NativeSelectBrowserTests(unittest.TestCase):
    """Actual Chrome native-control geometry, explicitly not native glyph pixel decoding."""
    @classmethod
    def setUpClass(cls):
        cls.chrome = require_browser()
        cls.temp = tempfile.TemporaryDirectory(prefix='workbench-native-select-')
        cls.root = Path(cls.temp.name)
        source = cls.root / 'build'
        source.mkdir()
        html = '''<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><title>Native select fixture</title>
<style>body{font:16px Arial;padding:20px}select{font:16px Arial;width:180px;height:44px;padding:4px 12px;color:#151515;background:white;display:block;margin:8px}</style></head><body>
<h1>Native select fixture</h1>
<select id="scope" aria-label="Scope"><option value="all">All records</option><option value="mine" selected label="My records">OPTION_INTERNAL_TEXT</option></select>
<select id="blank" aria-label="Empty selection"><option value="" selected> </option><option value="later">Unselected visible text</option></select>
<select id="transparent" aria-label="Transparent selection" style="color:transparent"><option selected>My records</option></select>
<select id="hidden" aria-label="Hidden selection" style="display:none"><option selected>My records</option></select>
<div style="opacity:0"><select id="opacity" aria-label="Transparent ancestor"><option selected>My records</option></select></div>
<select id="zero" aria-label="Zero dimensions" style="width:0;height:0;padding:0;border:0"><option selected>My records</option></select>
<select id="multiple" aria-label="Multiple selection" multiple><option selected>My records</option><option selected>Others</option></select>
<select id="listbox" aria-label="Listbox" size="2"><option selected>My records</option><option>Others</option></select>
</body></html>'''
        (source / 'index.html').write_text(html, encoding='utf-8')
        manifest = {'root': 'build', 'entry': 'index.html', 'ownership': 'active',
                    'files': [{'path': 'index.html', 'sha256': hashlib.sha256((source / 'index.html').read_bytes()).hexdigest()}]}
        (cls.root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
        plan = ux_fixtures.example()
        plan['interaction_checks'] = [{'id': 'native-value', 'kind': 'selected-value-visible', 'target': '#scope', 'viewports': ['desktop', 'mobile']}]
        (cls.root / 'plan.json').write_text(json.dumps(plan), encoding='utf-8')
        cls.visible = probe(cls.root, 'manifest.json', 'plan.json', str(cls.chrome), 'images/visible')
        plan['interaction_checks'] = [{'id': name, 'kind': 'selected-value-visible', 'target': '#' + name, 'viewports': ['desktop', 'mobile']}
                                      for name in ['blank', 'transparent', 'hidden', 'opacity', 'zero', 'multiple', 'listbox']]
        (cls.root / 'negative-plan.json').write_text(json.dumps(plan), encoding='utf-8')
        cls.negative = probe(cls.root, 'manifest.json', 'negative-plan.json', str(cls.chrome), 'images/negative')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_native_single_selected_label_both_widths_and_pngs(self):
        self.assertTrue(self.visible['passed'], self.visible)
        self.assertEqual({case['viewport'] for case in self.visible['cases']}, {'desktop', 'mobile'})
        for case in self.visible['cases']:
            value = case['measurements']['target']
            self.assertEqual(value['text'], 'My records')
            self.assertNotIn('OPTION_INTERNAL_TEXT', value['text'])
            self.assertNotIn('All records', value['text'])
            self.assertEqual(value['method'], 'native-selected-option-control-geometry')
            self.assertEqual(value['text_rects'], [])
            self.assertIn('unknown', value['native_text_bounds'])
            self.assertGreater(value['content_box']['width'], 0)
            self.assertGreater(value['content_box']['height'], 0)
            self.assertTrue(value['readable'])
            self.assertTrue(all((self.root / shot['path']).is_file() for shot in case['screenshots']))

    def test_native_blank_transparent_hidden_opacity_and_zero_rejected(self):
        self.assertFalse(self.negative['passed'])
        for name in ['blank', 'transparent', 'hidden', 'opacity', 'zero']:
            cases = [case for case in self.negative['cases'] if case['id'] == name]
            self.assertEqual(len(cases), 2)
            for case in cases:
                self.assertFalse(case['passed'], name)
                self.assertFalse(case['assertions']['text_readable'], name)
                initial = case['measurements']['initial_target']
                self.assertEqual(initial['method'], 'native-selected-option-control-geometry')
                self.assertFalse(initial['readable'], name)
                self.assertTrue(any(shot['state'] == 'failure' and (self.root / shot['path']).is_file() for shot in case['screenshots']))

    def test_native_multiple_and_listbox_are_outside_closed_check(self):
        for name in ['multiple', 'listbox']:
            cases = [case for case in self.negative['cases'] if case['id'] == name]
            self.assertEqual(len(cases), 2)
            for case in cases:
                value = case['measurements']['target']
                self.assertFalse(case['passed'])
                self.assertFalse(value['closed_single_select'])
                self.assertFalse(value['readable'])
                self.assertIn('outside', value['unsupported_reason'])


class InteractionReviewGateTests(unittest.TestCase):
    """Reuse schema-only fixtures; this class does not claim they are browser evidence."""
    setUp = ux_fixtures.UxEvidenceTests.setUp
    tearDown = ux_fixtures.UxEvidenceTests.tearDown
    write = ux_fixtures.UxEvidenceTests.write
    pin = ux_fixtures.UxEvidenceTests.pin
    save = ux_fixtures.UxEvidenceTests.save
    evidence = ux_fixtures.UxEvidenceTests.evidence
    def test_planned_checks_require_additional_probe_pin(self):
        plan = ux_fixtures.example(); plan['interaction_checks'] = planned_checks()
        self.write('ux-plan.json', plan)
        # This fixture rewrites only its synthetic ledger pin to isolate the new review gate.
        ledger = json.loads((self.r / 'ledger.json').read_text()); ledger['ux_plan'] = self.pin('ux-plan.json')
        self.write('ledger.json', ledger); self.ux['plan_sha256'] = ledger['ux_plan']['sha256']; self.save()
        from design_loop import review
        with self.assertRaisesRegex(GateError, 'interaction evidence'):
            review(self.r, 'ledger.json', 'review.json')


class ExternalBindingLedgerTests(unittest.TestCase):
    def test_additive_binding_retains_plan_history_and_refuses_after_bind(self):
        from design_loop import prepare, attach, attach_interactions, bind
        import test_design_loop as fixtures
        fixtures.DesignLoopTests.setUp(self)
        try:
            (self.r / 'ledger.json').unlink()
            plan = ux_fixtures.example()
            (self.r / 'ux-plan.json').write_text(json.dumps(plan), encoding='utf-8')
            prepare(self.r, 'abstract', 'analysis.json', 'patterns.json', 'prompt.md',
                    'ledger.json', 2, source_root='generated', ux_plan='ux-plan.json')
            attach(self.r, 'ledger.json', 'references.json')
            before = hashlib.sha256((self.r / 'ux-plan.json').read_bytes()).hexdigest()
            (self.r / 'generated/source.jsx').write_text('Synthetic source already exists before legacy binding')
            (self.r / 'checks.json').write_text(json.dumps({'version': '1.0', 'study_id': 'abstract', 'interaction_checks': planned_checks()}))
            result = attach_interactions(self.r, 'ledger.json', 'checks.json', 'Synthetic author',
                                         'Selectors bind already declared controls/mobile interaction; no intent change')
            self.assertTrue(result['source_already_present']); self.assertFalse(result['budget_reset'])
            self.assertEqual(before, hashlib.sha256((self.r / 'ux-plan.json').read_bytes()).hexdigest())
            ledger = json.loads((self.r / 'ledger.json').read_text())
            self.assertEqual(ledger['interaction_binding_history'][0]['ux_plan']['sha256'], before)
            bind(self.r, 'ledger.json', ['generated/source.jsx'])
            with self.assertRaises(GateError):
                attach_interactions(self.r, 'ledger.json', 'checks.json', 'Synthetic author', 'Cannot replace after bind')
            (self.r / 'checks.json').write_text('{}')
            with self.assertRaises(GateError): bind(self.r, 'ledger.json', ['generated/source.jsx'])
        finally:
            fixtures.DesignLoopTests.tearDown(self)

    evidence = ux_fixtures.UxEvidenceTests.evidence
