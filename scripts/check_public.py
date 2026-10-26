"""Check publishable files, local Markdown links and optional exact payload inventory."""
from pathlib import Path
from urllib.parse import unquote
import argparse, json, re, sys
from _payload import ROOT, EXCLUDED_DIRS, excluded, linked, verify_inventory

PRIVATE_PATTERNS = {
    'personal-windows-path': re.compile(r'(?i)[a-z]:[\\/]+Users[\\/]+(?!Public\b|Default\b)[a-z0-9_. -]+[\\/]'),
    'personal-posix-path': re.compile(r'/(?:home|Users)/[a-z][a-z0-9_.-]+/', re.I),
    'private-page': re.compile(r'https?://chatgpt\.com/space/\S+', re.I),
    'conversation-file': re.compile(r'library-file:[a-z0-9_-]+', re.I),
    'internal-agent': re.compile(r'/root/[a-z][a-z0-9_-]+', re.I),
    'credential': re.compile(r'(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_]{20,}'),
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
}

def public_files(root):
    files = []
    for p in sorted(root.rglob('*')):
        rel = p.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if p.is_file() and '__pycache__' not in rel.parts and p.suffix not in {'.pyc', '.pyo'}:
            if linked(p) or excluded(p):
                raise ValueError('Excluded or linked public file: ' + rel.as_posix())
            files.append(p)
    # .github is intentionally absent from the installed payload, but still public source.
    for p in sorted((root / '.github').rglob('*')):
        if p.is_file(): files.append(p)
    return files

def check(root=ROOT, inventory=True):
    errors=[]; files=public_files(root)
    for p in files:
        relative=p.relative_to(root).as_posix()
        try: text=p.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            errors.append({'file':relative,'kind':'non-text-public-asset-review-required'});continue
        for kind, pattern in PRIVATE_PATTERNS.items():
            if pattern.search(text): errors.append({'file':relative,'kind':kind})
        if p.suffix.lower()=='.md':
            for target in re.findall(r'\]\(([^\s)]+)(?:\s+"[^"]*")?\)',text):
                if target.startswith(('#','http:','https:','mailto:')):continue
                target=unquote(target.split('#',1)[0]);local=(p.parent/target).resolve()
                if not local.is_relative_to(root.resolve()) or not local.exists():
                    errors.append({'file':relative,'kind':'broken-local-link','target':target})
    if inventory:
        try: verify_inventory(root)
        except (ValueError, OSError, KeyError) as e:errors.append({'kind':'inventory','message':str(e)})
    return {'passed':not errors,'files':len(files),'errors':errors,
            'scope':'Pattern and link checks on public text plus exact runtime payload hashes; human review is still required.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--no-inventory',action='store_true');a=p.parse_args()
    try:result=check(inventory=not a.no_inventory)
    except (ValueError,OSError) as e: result={'passed':False,'errors':[{'message':str(e)}]}
    print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['passed'] else 2)
