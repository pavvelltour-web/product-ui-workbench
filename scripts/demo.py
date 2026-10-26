"""Create a new original offline example; optionally capture actual browser PNGs."""
from pathlib import Path
import argparse, json, shutil, sys
from pipeline import GateError, closure_files, validate_closure, atomic, canonical_workspace

ROOT = Path(__file__).resolve().parents[1]

def create(workspace, chrome=None):
    target = canonical_workspace(workspace, exists=False)
    if target.exists():
        raise ValueError('Use a new demo directory; existing work is preserved')
    if target == Path(target.anchor) or target.is_relative_to(ROOT) or ROOT.is_relative_to(target):
        raise ValueError('Demo must be a separate non-root workspace outside the skill')
    target.mkdir(parents=True, exist_ok=False)
    app = target / 'generated/demo'
    app.mkdir(parents=True)
    shutil.copyfile(ROOT / 'examples/offline-demo/index.html', app / 'index.html')
    shutil.copyfile(ROOT / 'library/components/native-workbench.mjs', app / 'native-workbench.mjs')
    (target / 'research').mkdir()
    shutil.copyfile(ROOT / 'examples/offline-demo/ux-plan.json', target / 'research/ux-plan.json')
    manifest = validate_closure(target, {'root': 'generated/demo', 'entry': 'index.html',
                                       'ownership': 'active', 'files': closure_files(target, 'generated/demo')})
    atomic(target / 'inputs/build.json', manifest)
    result = {'status': 'demo-created', 'workspace': str(target), 'entry': 'generated/demo/index.html',
              'source_manifest': 'inputs/build.json', 'interaction_plan': 'research/ux-plan.json',
              'data': 'Original synthetic in-memory tasks',
              'reference_review': 'not-run; this example is not a reconstruction of an external UI',
              'visual_review': 'not-run; open real PNGs before judging', 'browser': 'not-run',
              'manual_preview': 'Serve generated/demo over localhost HTTP (ES modules do not work reliably via file://).'}
    if chrome:
        from render_web import capture
        result['capture'] = capture(target, 'inputs/build.json', chrome, 'images/demo', mobile_full_page=True)
        result['browser'] = 'capture-executed; see capture.json for exact assertions and limits'
    atomic(target / 'demo.json', result)
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--chrome')
    args = parser.parse_args()
    try:
        print(json.dumps(create(args.workspace, args.chrome), ensure_ascii=False, indent=2))
    except (ValueError, OSError, GateError) as error:
        print(json.dumps({'error': str(error)}, ensure_ascii=False)); sys.exit(2)
