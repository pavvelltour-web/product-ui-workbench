"""Maintainer command: refresh generated library pins and allowlisted runtime inventory."""
import json
import os
from _payload import ROOT, INVENTORY, records

def main():
    from library_seed import build
    library = build()
    (ROOT / 'library/manifest.json').write_bytes((json.dumps(library, indent=2) + '\n').encode('utf-8'))
    identity = json.loads((ROOT / 'workbench.json').read_text(encoding='utf-8'))
    manifest = {'name': identity['name'], 'version': identity['version'], 'entry': 'SKILL.md',
                'installed': False, 'activated': False, 'cli': 'scripts/pipeline.py',
                'runtime': 'Python >=3.10 standard library; optional browser checks need Python Playwright and an explicit existing Chrome/Chromium executable',
                'rights': 'Original code MIT; upstream notices retained; no external reference pixels bundled',
                'files': records(ROOT)}
    temporary = ROOT / (INVENTORY + '.tmp')
    temporary.write_bytes((json.dumps(manifest, indent=2) + '\n').encode('utf-8'))
    os.replace(temporary, ROOT / INVENTORY)
    print(json.dumps({'status': 'inventory-written', 'files': len(manifest['files'])}))

if __name__ == '__main__':
    main()
