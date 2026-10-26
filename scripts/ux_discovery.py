"""MIT. Validate declared UX discovery and live pins, not truth, chronology or usability."""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path
from pipeline import GateError, require, safe, load, digest, ident

MODES = {'new-operational', 'rethought-operational', 'explicit-simulation'}
STATE_KEYS = {'loading', 'empty', 'error', 'cancel', 'success'}
LIMITATION = ('Manual UX-first normalization with current file-pin verification only; '
              'not automatic chronology enforcement, real interviews, truth verification, '
              'user-test results, usability certification or human acceptance.')


def obj(value, required, optional=(), label='Object'):
    require(isinstance(value, dict), label + ' must be an object')
    require(set(required).issubset(value), label + ' missing: ' + ', '.join(sorted(set(required) - set(value))))
    require(set(value).issubset(set(required) | set(optional)), label + ' has unsupported fields')
    return value


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), label + ' must be nonempty text')


def items(value, label, minimum=1):
    require(isinstance(value, list) and len(value) >= minimum, label + ' needs at least ' + str(minimum) + ' item(s)')
    return value


def texts(value, label, minimum=1):
    for item in items(value, label, minimum):
        text(item, label)


def identity(value, seen, label):
    ident(value)
    require(value not in seen, 'Duplicate ' + label + ': ' + value)
    seen.add(value)


def pointer(document, path):
    text(path, 'JSON pointer')
    require(path.startswith('/'), 'Confirmation JSON pointer must start with /')
    current = document
    for raw in path[1:].split('/'):
        require(not re.search(r'~(?![01])', raw), 'Invalid JSON pointer escape')
        key = raw.replace('~1', '/').replace('~0', '~')
        if isinstance(current, dict):
            require(key in current, 'Confirmation JSON pointer missing key')
            current = current[key]
        elif isinstance(current, list):
            require(re.fullmatch(r'0|[1-9][0-9]*', key) and int(key) < len(current), 'Confirmation JSON pointer missing index')
            current = current[int(key)]
        else:
            raise GateError('Confirmation JSON pointer crosses a scalar')
    return current


def validate(root, data):
    root = Path(root).resolve(strict=True)
    require(root.is_dir(), 'Workspace must be a directory')
    obj(data, {'version', 'study_id', 'applicability', 'scope', 'provenance', 'interviews', 'products', 'assumptions'})
    require(data['version'] == '1.0', 'Unsupported discovery version')
    ident(data['study_id'])
    application = obj(data['applicability'], {'mode', 'reason'})
    require(application['mode'] in MODES, 'Discovery applies only to new/rethought operational UX or explicit simulation')
    text(application['reason'], 'Applicability reason')
    scope = obj(data['scope'], {'kind', 'backend', 'product_ids'})
    require(scope['kind'] == 'design-only' and scope['backend'] is False, 'Scope must remain design-only with backend=false')
    texts(scope['product_ids'], 'Scope product IDs')
    require(len(set(scope['product_ids'])) == len(scope['product_ids']), 'Duplicate scope products')
    provenance = obj(data['provenance'], {'observer', 'method', 'evidence_status', 'chronology', 'files'})
    text(provenance['observer'], 'Named manual observer')
    require(provenance['method'] == 'manual-normalization', 'Manual normalization must remain explicit')
    require(provenance['evidence_status'] == 'proposed-not-validated', 'Discovery cannot claim validated research')
    chronology = obj(provenance['chronology'], {'kind', 'statement', 'automatic_enforcement'})
    require(chronology['kind'] == 'manual-attestation' and chronology['automatic_enforcement'] is False,
            'Chronology is a manual attestation, not automatic enforcement')
    text(chronology['statement'], 'Chronology attestation')
    pin_ids, documents, verified, paths = set(), {}, [], set()
    for pin in items(provenance['files'], 'Pinned files'):
        obj(pin, {'id', 'path', 'sha256', 'kind'})
        identity(pin['id'], pin_ids, 'pin ID')
        require(pin['kind'] in {'simulated-notes', 'design-decisions', 'user-brief', 'source-notes'}, 'Unsupported provenance kind')
        text(pin['path'], 'Pin path')
        require(re.fullmatch(r'[a-f0-9]{64}', pin['sha256']) is not None, 'Pin SHA256 must be lowercase hex')
        path = safe(root, pin['path'], True)
        require(path.is_file(), 'Pinned path must be a file')
        require(path not in paths, 'Duplicate pinned file path')
        paths.add(path)
        require(digest(path) == pin['sha256'], 'Stale pinned file: ' + pin['path'])
        documents[pin['id']] = path
        verified.append(dict(pin))
    product_ids = set()
    for product in items(data['products'], 'Products'):
        obj(product, {'id', 'name', 'source_file_ids', 'alternatives', 'chosen', 'scenario', 'falsification_cases'})
        identity(product['id'], product_ids, 'product ID')
        text(product['name'], 'Product name')
        texts(product['source_file_ids'], 'Product source-file IDs')
        require(set(product['source_file_ids']).issubset(pin_ids), 'Unknown product source-file ID')
        alternatives = set()
        for alternative in items(product['alternatives'], 'Alternatives', 2):
            obj(alternative, {'id', 'approach', 'benefit', 'tradeoff'})
            identity(alternative['id'], alternatives, 'alternative ID')
            for key in ('approach', 'benefit', 'tradeoff'):
                text(alternative[key], 'Alternative ' + key)
        chosen = obj(product['chosen'], {'id', 'reason'})
        require(chosen['id'] in alternatives, 'Unknown chosen alternative')
        text(chosen['reason'], 'Chosen reason')
        scenario = obj(product['scenario'], {'job', 'first_useful_entity', 'actions', 'scopes', 'states', 'mobile'})
        for key in ('job', 'first_useful_entity'):
            text(scenario[key], 'Scenario ' + key)
        action_ids = set()
        for action in items(scenario['actions'], 'Scenario actions'):
            obj(action, {'id', 'label', 'entity', 'effect'})
            identity(action['id'], action_ids, 'action ID')
            for key in ('label', 'entity', 'effect'):
                text(action[key], 'Action ' + key)
        scope_ids = set()
        for collection in items(scenario['scopes'], 'Collection scopes'):
            obj(collection, {'id', 'label', 'collection', 'controls', 'result_count', 'selection'})
            identity(collection['id'], scope_ids, 'collection scope ID')
            for key in ('label', 'collection', 'result_count', 'selection'):
                text(collection[key], 'Collection scope ' + key)
            texts(collection['controls'], 'Scoped controls')
        states = obj(scenario['states'], STATE_KEYS)
        for name in STATE_KEYS:
            text(states[name], 'State ' + name)
        mobile = obj(scenario['mobile'], {'first_useful_object', 'order', 'touch_target_px'})
        text(mobile['first_useful_object'], 'First useful mobile object')
        texts(mobile['order'], 'Mobile attention order')
        require(type(mobile['touch_target_px']) is int and mobile['touch_target_px'] >= 44,
                'Mobile touch target must be an integer of at least44px')
        case_ids = set()
        for case in items(product['falsification_cases'], 'Falsification cases'):
            obj(case, {'id', 'probe', 'expected', 'method', 'scope_ids'})
            identity(case['id'], case_ids, 'falsification case ID')
            text(case['probe'], 'Observable falsification probe')
            text(case['expected'], 'Observable expected result')
            require(case['method'] == 'prototype-observation', 'Falsification is a proposed prototype observation, not a user score')
            texts(case['scope_ids'], 'Falsification scope IDs')
            require(set(case['scope_ids']).issubset(scope_ids), 'Unknown falsification scope ID')
    require(set(scope['product_ids']) == product_ids, 'Scope products must match declared product IDs')
    interview_ids, question_count = set(), 0
    for interview in items(data['interviews'], 'Simulated interviews', 0):
        obj(interview, {'id', 'product_id', 'source_file_id', 'persona', 'origin', 'evidence_level', 'conflicting_need', 'questions'})
        identity(interview['id'], interview_ids, 'interview ID')
        require(interview['product_id'] in product_ids, 'Interview of unknown product')
        require(interview['source_file_id'] in pin_ids, 'Unknown interview source-file ID')
        pin = next(p for p in verified if p['id'] == interview['source_file_id'])
        require(pin['kind'] == 'simulated-notes', 'Simulated interview needs a simulated-notes source pin')
        require(interview['origin'] == 'simulated' and interview['evidence_level'] == 'hypothesis',
                'Simulated interviews must stay explicitly simulated/hypothesis, never real research')
        text(interview['persona'], 'Simulated persona')
        text(interview['conflicting_need'], 'Conflicting need/tradeoff')
        for question in items(interview['questions'], 'Interview questions'):
            obj(question, {'question', 'followup', 'answer', 'answer_kind', 'hypothesis'})
            require(question['answer_kind'] == 'simulated', 'Answer must be explicitly simulated')
            for key in ('question', 'followup', 'answer', 'hypothesis'):
                text(question[key], 'Interview ' + key)
            question_count += 1
    if application['mode'] == 'explicit-simulation':
        require(data['interviews'], 'Explicit simulation requires labelled interviews')
    assumption_ids = set()
    for assumption in items(data['assumptions'], 'Assumptions'):
        obj(assumption, {'id', 'statement', 'status'}, {'confirmation'})
        identity(assumption['id'], assumption_ids, 'assumption ID')
        text(assumption['statement'], 'Assumption statement')
        require(assumption['status'] in {'unresolved', 'proposed', 'user-confirmed'}, 'Unknown assumption status')
        if assumption['status'] == 'user-confirmed':
            confirmation = obj(assumption.get('confirmation'), {'file_id', 'json_pointer', 'expected_value'})
            require(confirmation['file_id'] in pin_ids, 'Unknown confirmation file ID')
            pin = next(p for p in verified if p['id'] == confirmation['file_id'])
            require(pin['kind'] == 'user-brief', 'User confirmation needs pinned user-brief')
            actual = pointer(load(documents[confirmation['file_id']]), confirmation['json_pointer'])
            require(type(actual) == type(confirmation['expected_value']) and actual == confirmation['expected_value'],
                    'User confirmation pointer/value mismatch')
            require(isinstance(actual, str) and bool(actual.strip()), 'Confirmation must quote nonempty recorded text')
        else:
            require('confirmation' not in assumption, 'Unresolved/proposed assumption cannot carry confirmed evidence')
    return {'version': '1.0', 'study_id': data['study_id'], 'status': 'declared-and-pins-verified',
            'scope': scope, 'verified_files': verified, 'product_ids': sorted(product_ids),
            'simulated_interviews': len(data['interviews']), 'simulated_questions': question_count,
            'human_acceptance': 'pending', 'limitation': LIMITATION}


def run(workspace, input_file, out=None):
    supplied_root = Path(workspace).absolute()
    require(supplied_root.is_dir() and not supplied_root.is_symlink(), 'Workspace must be a real directory')
    root = supplied_root.resolve(strict=True)
    source = safe(root, input_file, True)
    require(source.is_file() and source.stat().st_size <= 2 * 1024 * 1024, 'Input must be a JSON file no larger than2MiB')
    result = validate(root, load(source))
    result['input'] = {'path': str(source.relative_to(root)).replace('\\', '/'), 'sha256': digest(source)}
    if out is not None:
        target = safe(root, out)
        require(not target.exists(), 'Existing receipt preserved')
        target.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents overwriting a concurrent or earlier receipt.
        with target.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--out')
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.workspace, args.input, args.out), ensure_ascii=False, indent=2))
    except (GateError, OSError, ValueError, TypeError) as error:
        print(json.dumps({'status': 'rejected', 'error': str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
