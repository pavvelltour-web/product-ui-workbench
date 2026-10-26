"""Contextual UX plan/evidence gates; attestations and measurements, never a beauty score."""
import argparse
import json
import sys
from pathlib import Path
from pipeline import GateError, require, safe, load, digest, ident

CRITERIA = (
    'attention-priority', 'semantic-grouping', 'type-roles',
    'chart-semantics', 'control-coherence', 'scope-and-selection',
    'detail-hierarchy', 'touch-first-useful',
)
TYPE_ROLES = {'page', 'section', 'entity', 'body', 'label', 'meta'}
METHODS = {'image-observation', 'measured-dom', 'mixed'}
VIEWPORTS = {'desktop': [1440, 1000], 'mobile': [390, 844]}


def validate_interaction_checks(checks):
    require(isinstance(checks, list) and checks, 'Interaction checks must be a nonempty list')
    ids = []
    for check in checks:
        require(isinstance(check, dict), 'Interaction check must be an object')
        text(check.get('id'), 'Interaction check id')
        ids.append(check['id'])
        require(check.get('kind') in {'open-region', 'selected-value-visible'}, 'Unsupported interaction kind')
        text(check.get('target'), 'Interaction target selector')
        require(isinstance(check.get('viewports'), list)
                and len(check['viewports']) == 2 and set(check['viewports']) == set(VIEWPORTS),
                'Interaction checks require desktop and mobile exactly once')
        if check['kind'] == 'open-region':
            for key in ['trigger', 'identity']:
                text(check.get(key), 'Open region ' + key)
            require(check.get('close') == 'Escape' and check.get('focus_return') is True,
                    'Open region requires Escape and focus return')
    require(len(set(ids)) == len(ids), 'Duplicate interaction check IDs')
    return checks


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + ' required')


def positive(value, label):
    require(isinstance(value, (int, float)) and not isinstance(value, bool)
            and value > 0, label + ' must be positive')


def strings(value, label):
    require(isinstance(value, list) and value, label + ' must be a nonempty list')
    for item in value:
        text(item, label)


def validate_plan(data, study_id=None):
    """Validate an explicit proposal, without inventing an actor or business intake."""
    require(isinstance(data, dict) and data.get('version') == '1.0', 'Unsupported UX plan')
    text(data.get('study_id'), 'UX study_id')
    ident(data['study_id'])
    if study_id is not None:
        require(data['study_id'] == study_id, 'UX plan of wrong study')
    require(data.get('screen_kind') in {'operations', 'catalog', 'other'}, 'UX screen kind required')
    intent = data.get('intent', {})
    text(intent.get('statement'), 'Short screen intent')
    require(intent.get('basis') in {'proposed', 'supplied'}, 'Intent basis must remain explicit')
    attention = data.get('attention', {})
    primary = attention.get('primary', {})
    for key in ['content', 'reason', 'action']:
        text(primary.get(key), 'Primary attention ' + key)
    strings(attention.get('secondary'), 'Secondary attention order')
    groups = data.get('grouping')
    require(isinstance(groups, list) and groups, 'Semantic grouping plan required')
    group_ids = []
    for group in groups:
        text(group.get('id'), 'Group identity')
        group_ids.append(group['id'])
        strings(group.get('contents'), 'Related group contents')
        positive(group.get('inner_gap'), 'Inner group gap')
        positive(group.get('outer_gap'), 'Outer group gap')
        require(group['inner_gap'] < group['outer_gap'], 'Related items need a tighter declared gap than separated groups')
    require(len(set(group_ids)) == len(group_ids), 'Duplicate group identities')
    typography = data.get('typography', {})
    require(TYPE_ROLES.issubset(typography), 'Named page/section/entity/body/label/meta type roles required')
    for role, spec in typography.items():
        text(role, 'Type role')
        text(spec.get('family'), 'Type family')
        positive(spec.get('size_px'), 'Rendered type size')
        positive(spec.get('line_height_px'), 'Type line height')
        require(spec['line_height_px'] >= spec['size_px'], 'Line height smaller than rendered type')
        require(isinstance(spec.get('weight'), int) and not isinstance(spec['weight'], bool)
                and 100 <= spec['weight'] <= 1000, 'Type weight must be100..1000')
    controls = data.get('controls', {})
    for key in ['family', 'search', 'filter_scope', 'result_count', 'selection']:
        text(controls.get(key), 'Control contract ' + key)
    chart = data.get('chart', {})
    require(type(chart.get('present')) is bool, 'Declare chart presence')
    if chart['present']:
        for key in ['measure', 'unit', 'period', 'axis_mapping', 'plot_extent', 'end_padding']:
            text(chart.get(key), 'Chart contract ' + key)
    else:
        text(chart.get('reason'), 'Reason chart is absent')
    mobile = data.get('mobile', {})
    text(mobile.get('first_useful_object'), 'First useful touch object')
    strings(mobile.get('expected_order'), 'Touch attention order')
    positive(mobile.get('text_min_px'), 'Touch text minimum')
    positive(mobile.get('touch_target_px'), 'Touch target')
    if 'interaction_checks' in data:
        validate_interaction_checks(data['interaction_checks'])
    return {'study_id': data['study_id'], 'criteria': list(CRITERIA),
            'scope': 'Declared contextual contract; no automatic usability or preference verdict'}


def pinned(root, record):
    require(isinstance(record, dict), 'Evidence pin required')
    path = safe(root, record.get('path', ''), True)
    require(path.is_file() and digest(path) == record.get('sha256'), 'Stale UX evidence: ' + str(record.get('path')))
    return path


def identity(record):
    require(isinstance(record, dict), 'Evidence identity must be a pin object')
    return (record.get('path'), record.get('sha256'))


def validate_evidence(root, plan_pin, data, study_id, artifact_pins, decision):
    """Called after design_loop verifies capture mode, source closure and real PNGs."""
    plan = load(pinned(root, plan_pin))
    validate_plan(plan, study_id)
    require(isinstance(data, dict) and data.get('version') == '1.0', 'Unsupported UX evidence')
    require(data.get('study_id') == study_id, 'UX evidence of wrong study')
    require(data.get('plan_sha256') == plan_pin['sha256'], 'UX evidence of wrong plan')
    text(data.get('observer'), 'Named UX observer')
    require(data.get('human_acceptance') == 'pending', 'Only the user supplies UX acceptance')
    evidence_artifacts = data.get('artifacts', {})
    require(set(evidence_artifacts) == set(artifact_pins), 'UX evidence must cover current visual artifacts')
    for kind, reference in artifact_pins.items():
        require(identity(evidence_artifacts[kind]) == identity(reference), 'UX capture record differs from current review')
    expected_manifests = set()
    expected_pngs = set()
    study_pngs = set()
    for kind, reference in artifact_pins.items():
        capture = load(pinned(root, reference))
        expected_manifests.add(identity(capture['source_manifest']))
        for shot in capture['screenshots']:
            expected_pngs.add(identity(shot))
            if kind == 'study':
                study_pngs.add(identity(shot))
    require('study' in artifact_pins and len(study_pngs) >= 1, 'UX requires actual adapted study captures')
    manifest_refs = data.get('source_manifests', [])
    require(isinstance(manifest_refs, list) and {identity(p) for p in manifest_refs} == expected_manifests,
            'UX source manifests differ from current capture closure')
    for reference in manifest_refs:
        pinned(root, reference)
    captures = data.get('captures', [])
    require(isinstance(captures, list) and captures, 'Viewed UX PNG pins required')
    observed = set()
    for shot in captures:
        pinned(root, shot)
        require(shot.get('viewed') is True and identity(shot) in expected_pngs,
                'UX PNG detached from current captures or not viewed')
        observed.add(identity(shot))
    require(study_pngs.issubset(observed), 'UX requires viewed desktop and touch study PNGs')
    criteria = data.get('criteria', {})
    require(set(criteria) == set(CRITERIA), 'Separate UX criteria required')
    observed_hashes = {sha for _, sha in observed}
    unresolved = []
    for name, finding in criteria.items():
        require(finding.get('status') in {'pass', 'revise', 'not-run'}, 'Explicit UX criterion status required')
        require(finding.get('method') in METHODS, 'Explicit UX observation method required')
        text(finding.get('evidence'), 'Concrete UX criterion evidence')
        refs = finding.get('capture_sha256s')
        require(isinstance(refs, list) and refs and set(refs).issubset(observed_hashes),
                'UX criterion must identify viewed current pixels')
        if name == 'attention-priority':
            require(finding['method'] in {'image-observation', 'mixed'},
                    'Attention priority needs named image judgment, not a computed score')
        if finding['method'] in {'measured-dom', 'mixed'}:
            measurements = finding.get('measurements')
            require(isinstance(measurements, list) and measurements, 'Measured UX finding needs actual measurements')
            for measurement in measurements:
                for key in ['name', 'selector', 'viewport', 'unit']:
                    text(measurement.get(key), 'Measurement ' + key)
                require('value' in measurement and measurement['value'] is not None, 'Measurement value required')
        if finding['status'] != 'pass':
            unresolved.append(name)
    if decision == 'candidate':
        require(not unresolved, 'Unresolved UX criteria cannot be candidate: ' + ', '.join(unresolved))
    return {'observer': data['observer'], 'criteria': criteria, 'unresolved': unresolved,
            'plan': plan_pin, 'scope': 'Named observation and declared measurements; not automatic UX validation'}


def validate_interaction_evidence(root, plan_pin, data, study_id, artifact_pins, decision, checks_pin=None):
    """Pin actual probe cases to the current plan/build. This is not tamper-proof evidence."""
    from pipeline import png_info, validate_closure
    plan = load(pinned(root, plan_pin))
    validate_plan(plan, study_id)
    if checks_pin:
        require('interaction_checks' not in plan, 'External bindings cannot override embedded checks')
        external = load(pinned(root, checks_pin))
        require(external.get('version') == '1.0' and external.get('study_id') == study_id, 'External checks of wrong study/version')
        require(external.get('plan_sha256', plan_pin['sha256']) == plan_pin['sha256'], 'External checks of wrong UX plan')
        checks = validate_interaction_checks(external.get('interaction_checks'))
    else:
        checks = validate_interaction_checks(plan.get('interaction_checks'))
    require(isinstance(data, dict) and data.get('version') == '1.0', 'Unsupported interaction evidence')
    require(data.get('runner') == 'browser-probe:playwright-chrome', 'Actual browser probe record required')
    require(data.get('study_id') == study_id and data.get('plan_sha256') == plan_pin['sha256'],
            'Interaction evidence of wrong plan/study')
    require(data.get('planned_checks') == checks, 'Interaction checks differ from pinned plan')
    require(identity(data.get('checks_contract')) == identity(checks_pin or plan_pin), 'Interaction selector contract pin differs')
    study = load(pinned(root, artifact_pins['study']))
    manifest = data.get('source_manifest')
    require(identity(manifest) == identity(study['source_manifest']), 'Interaction source manifest differs from current capture')
    closure = load(pinned(root, manifest))
    validate_closure(root, closure)
    require(manifest.get('closure') == closure and data.get('source_fresh_after') is True,
            'Interaction closure not verified fresh')
    require(data.get('view_query') == 'variant=' + study_id, 'Interaction probe of wrong view')
    errors = ['page_errors', 'console_errors', 'external_requests', 'failed_requests', 'http_errors', 'websockets', 'server_errors']
    for name in errors:
        require(isinstance(data.get(name), list), 'Interaction error inventory missing: ' + name)
    expected = {(check['id'], viewport): check for check in checks for viewport in check['viewports']}
    cases = data.get('cases')
    require(isinstance(cases, list) and len(cases) == len(expected), 'Missing interaction cases')
    observed = set()
    unresolved = []
    for case in cases:
        key = (case.get('id'), case.get('viewport'))
        require(key in expected and key not in observed, 'Unknown or duplicate interaction case')
        observed.add(key)
        check = expected[key]
        require(case.get('check') == check and case.get('viewport_size') == VIEWPORTS[key[1]],
                'Interaction case contract/viewport mismatch')
        require(type(case.get('passed')) is bool and isinstance(case.get('assertions'), dict), 'Explicit interaction outcome required')
        required = {'target_visible', 'text_readable'} if check['kind'] == 'selected-value-visible' else {'region_visible', 'identity_matches', 'closed', 'focus_returned'}
        require(required.issubset(case['assertions']) and all(type(case['assertions'][name]) is bool for name in required),
                'Concrete interaction assertions required')
        measurements = case.get('measurements', {})
        require(isinstance(measurements, dict) and 'target' in measurements, 'Actual target measurement required')
        target = measurements['target']
        require(isinstance(target, dict) and isinstance(target.get('rect'), dict)
                and isinstance(target.get('text'), str) and type(target.get('readable')) is bool,
                'Target text/geometry measurement required')
        states = ({'before', 'value'} if check['kind'] == 'selected-value-visible' else {'before', 'opened', 'closed'}) if case['passed'] else {'before', 'failure'}
        screenshots = case.get('screenshots', [])
        require(isinstance(screenshots, list) and states.issubset({shot.get('state') for shot in screenshots}),
                'Interaction state PNGs missing')
        for shot in screenshots:
            info = png_info(pinned(root, shot))
            require([info['width'], info['height']] == VIEWPORTS[key[1]], 'Interaction PNG of wrong viewport size')
        consistent = all(case['assertions'][name] for name in required) and target['readable'] and bool(target['text'].strip())
        if case['passed']:
            require(consistent, 'Interaction pass contradicts measured assertions')
            require(target['rect'].get('width', 0) > 0 and target['rect'].get('height', 0) > 0
                    and target.get('font_size', 0) >= 10 and target.get('opacity', 0) > 0
                    and target.get('css_visible') is True and target.get('in_viewport') is True
                    and isinstance(target.get('text_rects'), list) and bool(target['text_rects']),
                    'Interaction pass requires rendered text geometry/styles')
        if not case['passed']:
            unresolved.append(key[0] + ':' + key[1])
    require(observed == set(expected), 'Missing interaction viewport coverage')
    computed_pass = not unresolved and not any(data[name] for name in errors)
    require(type(data.get('passed')) is bool and data['passed'] == computed_pass, 'Interaction summary contradicts cases/errors')
    if decision == 'candidate':
        require(computed_pass, 'Unresolved actual interaction probe cannot be candidate')
    return {'passed': computed_pass, 'cases': len(cases), 'unresolved': unresolved,
            'scope': 'Pinned actual browser actions/text measurements; not full usability, accessibility or beauty approval'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--study-id')
    args = parser.parse_args()
    root = Path(args.workspace).resolve(strict=True)
    require(root.is_dir() and root != Path(root.anchor), 'Explicit workspace directory required')
    result = validate_plan(load(safe(root, args.plan, True)), args.study_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        main()
    except (GateError, ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False))
        sys.exit(2)
