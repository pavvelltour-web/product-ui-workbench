"""Build a verified standalone skill ZIP; no installation, activation or publication."""
import argparse
import json
from pathlib import Path
import sys
import zipfile
from _payload import ROOT, check_ancestors, payload_paths, sha, verify_inventory

def build(output):
    target = Path(output).absolute()
    check_ancestors(target)
    if target.exists():
        raise ValueError('Existing archive preserved')
    if target.suffix.lower() != '.zip':
        raise ValueError('Archive output requires .zip suffix')
    if target.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Archive output must be outside skill source')
    manifest = verify_inventory(ROOT)
    payloads = {path.relative_to(ROOT).as_posix(): path.read_bytes() for path in payload_paths(ROOT, include_inventory=True)}
    if json.loads(payloads['portable-manifest.json']) != manifest:
        raise ValueError('Inventory changed while reading payload')
    for item in manifest['files']:
        data = payloads.get(item['path'])
        if data is None or sha(data) != item['sha256'] or len(data) != item['bytes']:
            raise ValueError('Source changed while reading payload: ' + item['path'])
    pins = {name: {'sha256': sha(data), 'bytes': len(data)} for name, data in payloads.items()}
    target.parent.mkdir(parents=True, exist_ok=True)
    check_ancestors(target.parent)
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as archive:
        for name, data in payloads.items():
            archive.writestr(name, data)
        archive.writestr('PACKAGE-MANIFEST.json', json.dumps({'version': manifest['version'], 'installed': False, 'files': pins}, indent=2) + '\n')
    with zipfile.ZipFile(target) as archive:
        if set(archive.namelist()) != set(pins) | {'PACKAGE-MANIFEST.json'}:
            raise ValueError('Archive file set readback mismatch')
        for name, pin in pins.items():
            data = archive.read(name)
            if sha(data) != pin['sha256'] or len(data) != pin['bytes']:
                raise ValueError('Archive readback mismatch')
    return {'status': 'package-ready', 'path': str(target), 'sha256': sha(target.read_bytes()), 'files': len(pins), 'installed': False, 'activated': False, 'readback': 'pass'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.out), indent=2))
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({'status': 'error', 'error': str(error)}))
        sys.exit(2)
