"""Validate observed patterns and compile traceable directives; never score beauty."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from pipeline import GateError, atomic, digest, load, require, safe

KINDS = {'observed', 'measured-code', 'measured-image', 'inferred', 'proposed'}
ROLES = {'composition', 'spacing', 'type', 'color', 'material', 'component', 'state', 'responsive'}

def pinned(root, record):
    require(isinstance(record, dict), 'Expected a pinned file record')
    path = safe(root, record.get('path', ''), True)
    require(path.is_file(), 'Pinned evidence must be a file')
    require(record.get('sha256') == digest(path), 'Missing or stale evidence hash: ' + str(path))
    return path

def validate(root, data):
    require(data.get('version') == '1.0', 'Unsupported pattern packet version')
    sources = data.get('sources', [])
    require(isinstance(sources, list) and sources, 'Viewed sources are required')
    ids = set()
    for source in sources:
        sid = source.get('id')
        require(isinstance(sid, str) and sid and sid not in ids, 'Missing or duplicate source ID')
        ids.add(sid)
        url = urlsplit(source.get('canonical_url', ''))
        require(url.scheme == 'https' and bool(url.netloc), 'Canonical source URL required')
        require(source.get('rights') in {'unknown-private', 'licensed', 'original'}, 'Explicit rights required')
        require(source.get('kind') in {'actual-ui', 'component-ui', 'material-study'}, 'Honest source kind required')
        require(bool(source.get('app')) and bool(source.get('platform')) and bool(source.get('visible_state')), 'Source identity/state required')
        require(source.get('viewed') is True and bool(source.get('observer')), 'Actual named image/DOM observer required')
        pinned(root, source.get('evidence'))
    patterns = data.get('patterns', [])
    require(isinstance(patterns, list) and patterns, 'No patterns supplied')
    pattern_ids = set()
    for item in patterns:
        pid = item.get('id')
        require(isinstance(pid, str) and pid and pid not in pattern_ids, 'Missing or duplicate pattern ID')
        pattern_ids.add(pid)
        require(item.get('source_id') in ids, 'Unknown pattern source')
        require(item.get('role') in ROLES and item.get('kind') in KINDS, 'Unknown observation role or kind')
        require(all(isinstance(item.get(k), str) and item[k].strip() for k in ('observation', 'directive', 'suitable_for', 'unsuitable_for')), 'Observation, directive and fit boundaries required')
        if item['kind'] == 'measured-code':
            require(bool(item.get('selector')) and bool(item.get('property')) and 'value' in item, 'CSS measurements require selector/property/value')
            pinned(root, item.get('measurement_evidence'))
        if item['kind'] == 'measured-image':
            require(isinstance(item.get('image_size'), list) and len(item['image_size']) == 2, 'Image coordinate system required')
            require(isinstance(item.get('region'), list) and len(item['region']) == 4, 'Declared measured region required')
            require(item.get('unit') == 'comparison-px' and bool(item.get('uncertainty')), 'Image estimates must not be called upstream CSS tokens')
        if item.get('claimed_states'):
            require(set(item['claimed_states']).issubset(set(item.get('observed_states', []))), 'Unobserved interaction/state claim')
    require(all(pid in pattern_ids for pid in data.get('selected_pattern_ids', [])), 'Selected pattern does not exist')
    return {'sources': len(sources), 'patterns': len(patterns), 'selected': len(data.get('selected_pattern_ids', []))}

def compile_patterns(root, data, out):
    summary = validate(root, data)
    selected = set(data.get('selected_pattern_ids', []))
    require(selected, 'Select concrete patterns before compiling')
    lines = ['# Reference-derived directives', '', 'Keep product facts, entities and task behavior from the task contract.', '']
    for item in data['patterns']:
        if item['id'] in selected:
            lines += [f"- [{item['id']}; {item['kind']}; source {item['source_id']}] {item['directive']}", f"  Fit: {item['suitable_for']}. Avoid: {item['unsuitable_for']}."]
    lines += ['', 'After actual desktop and touch rendering, inspect composition, spacing, type, color/material and task states separately.', 'A failed transfer requires a concrete next research question or structural change. Build success is not visual acceptance.', '']
    target = safe(root, out)
    require(not target.exists(), 'Existing compiled directives preserved')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('\n'.join(lines), encoding='utf-8')
    return {**summary, 'path': out, 'sha256': digest(target), 'human_acceptance': 'not-run'}

def review(root, data):
    require(data.get('version') == '1.0', 'Unsupported review version')
    require(bool(data.get('author')) and bool(data.get('reviewer')), 'Named author and reviewer required')
    if data.get('independent'):
        require(data['author'] != data['reviewer'], 'Author cannot certify an independent review')
    require(data.get('captures'), 'Actual captures required')
    for capture in data['captures']:
        pinned(root, capture)
        require(capture.get('viewed') is True, 'Capture was not visually inspected')
    dimensions = data.get('dimensions', {})
    expected = {'composition', 'type-spacing', 'color-material', 'responsive', 'task-recovery', 'reference-transfer'}
    require(set(dimensions) == expected, 'Separate visual/task review dimensions required')
    for name, item in dimensions.items():
        require(item.get('status') in {'pass', 'fail', 'not-run'}, 'Unsupported review status')
        require(bool(item.get('evidence')), 'Concrete evidence required: ' + name)
    failures = [name for name, item in dimensions.items() if item['status'] == 'fail']
    require(data.get('decision') in {'revise-structure', 'research-again', 'candidate', 'stop-budget'}, 'Explicit bounded-loop decision required')
    if failures:
        require(data['decision'] != 'candidate', 'Known hard failure cannot be selected as a candidate')
        require(bool(data.get('next_question')) and bool(data.get('changed_module')), 'Failure needs a research question and responsible module')
    if data['decision'] == 'candidate':
        require(all(x['status'] == 'pass' for x in dimensions.values()), 'Not-run is not pass')
    require(data.get('human_acceptance') == 'pending', 'Only the human can supply human acceptance outside this validator')
    return {'decision': data['decision'], 'failed_dimensions': failures, 'independent': bool(data.get('independent')), 'human_acceptance': 'pending'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('mode', choices=['validate', 'compile', 'review'])
    parser.add_argument('--input', required=True)
    parser.add_argument('--out')
    args = parser.parse_args()
    root = Path(args.workspace).resolve(strict=True)
    require(root.is_dir() and root != Path(root.anchor), 'Explicit workspace directory required')
    data = load(safe(root, args.input, True))
    if args.mode == 'compile':
        require(bool(args.out), '--out is required')
        result = compile_patterns(root, data, args.out)
    else:
        result = validate(root, data) if args.mode == 'validate' else review(root, data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        sys.exit(main())
    except (GateError, ValueError, KeyError, TypeError, OSError) as error:
        print(json.dumps({'status': 'error', 'error': str(error)}, ensure_ascii=False))
        sys.exit(2)
