"""Check publishable files, local Markdown links and optional exact payload inventory."""
from pathlib import Path
from urllib.parse import unquote
import argparse, hashlib, json, re, struct, sys
from _payload import ROOT, EXCLUDED_DIRS, check_ancestors, excluded, linked, verify_inventory

PRIVATE_PATTERNS = {
    'personal-windows-path': re.compile(r'(?i)[a-z]:[\\/]+Users[\\/]+(?!Public\b|Default\b)[a-z0-9_. -]+[\\/]'),
    'personal-posix-path': re.compile(r'/(?:home|Users)/[a-z][a-z0-9_.-]+/', re.I),
    'private-page': re.compile(r'https?://chatgpt\.com/space/\S+', re.I),
    'conversation-file': re.compile(r'library-file:[a-z0-9_-]+', re.I),
    'internal-agent': re.compile(r'/root/[a-z][a-z0-9_-]+', re.I),
    'credential': re.compile(r'(?:ghp_|github_pat_|sk-proj-)[A-Za-z0-9_]{20,}'),
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
}

ASSET_REGISTRY = 'examples/showcase/assets.json'
ASSET_PATHS = {
    'png': re.compile(r'examples/showcase/images/[A-Za-z0-9][A-Za-z0-9_.-]*\.png'),
    'ttf': re.compile(r'examples/showcase/app/public/fonts/[A-Za-z0-9][A-Za-z0-9_.-]*\.ttf'),
}
BINARY_SUFFIXES = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif', '.ico', '.ttf', '.otf', '.woff', '.woff2',
                   '.pdf', '.zip', '.gz', '.7z', '.exe', '.dll', '.bin', '.mp3', '.mp4', '.mov'}

def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON object key in asset registry: ' + key)
        result[key] = value
    return result

def reviewed_assets(root):
    """Verify an explicit local asset declaration; rights/review claims remain human attestations."""
    registry = root / ASSET_REGISTRY
    if not registry.exists() and not registry.is_symlink():
        return {}
    check_ancestors(registry)
    if not registry.is_file():
        raise ValueError('Asset registry must be a regular file')
    declaration = json.loads(registry.read_text(encoding='utf-8'), object_pairs_hook=unique_json_object)
    if not isinstance(declaration, dict) or set(declaration) != {'version', 'assets'} or type(declaration['version']) is not int or declaration['version'] != 1 or not isinstance(declaration['assets'], list):
        raise ValueError('Asset registry requires version 1 and an assets array')
    approved = {}
    names = set()
    for item in declaration['assets']:
        if not isinstance(item, dict):
            raise ValueError('Asset registry entries must be objects')
        kind = item.get('kind')
        required = {'path', 'sha256', 'bytes', 'kind', 'rights'} | ({'width', 'height'} if kind == 'png' else set())
        if kind not in ASSET_PATHS or set(item) != required:
            raise ValueError('Unsupported asset kind or asset fields')
        name = item['path']
        if not isinstance(name, str) or not ASSET_PATHS[kind].fullmatch(name):
            raise ValueError('Asset path is outside the explicit showcase allowlist')
        if name.casefold() in names:
            raise ValueError('Duplicate asset path: ' + name)
        names.add(name.casefold())
        if not isinstance(item['sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', item['sha256']):
            raise ValueError('Asset requires a lowercase SHA-256: ' + name)
        if type(item['bytes']) is not int or item['bytes'] <= 0:
            raise ValueError('Asset byte size must be a positive integer: ' + name)
        if not isinstance(item['rights'], str) or not item['rights'].strip():
            raise ValueError('Asset requires an explicit rights attestation: ' + name)
        path = root / name
        check_ancestors(path)
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('Asset missing or outside source root: ' + name)
        data = path.read_bytes()
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Asset hash/size mismatch: ' + name)
        if kind == 'png':
            if any(type(item[key]) is not int or not 1 <= item[key] <= 20000 for key in ('width', 'height')):
                raise ValueError('Asset PNG dimensions must be bounded positive integers: ' + name)
            if len(data) < 33 or data[:8] != b'\x89PNG\r\n\x1a\n' or data[8:16] != b'\x00\x00\x00\rIHDR':
                raise ValueError('Asset PNG signature/IHDR invalid: ' + name)
            if struct.unpack('>II', data[16:24]) != (item['width'], item['height']):
                raise ValueError('Asset PNG dimensions differ from registry: ' + name)
        elif len(data) < 12 or data[:4] not in {b'\x00\x01\x00\x00', b'true'}:
            raise ValueError('Asset TTF sfnt signature invalid: ' + name)
        approved[name] = item
    return approved

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
    try:
        assets=reviewed_assets(root)
    except (ValueError, OSError, KeyError, TypeError) as error:
        assets={};errors.append({'file':ASSET_REGISTRY,'kind':'asset-registry','message':str(error)})
    for p in files:
        relative=p.relative_to(root).as_posix()
        if relative in assets:
            continue
        if p.suffix.lower() in BINARY_SUFFIXES:
            errors.append({'file':relative,'kind':'non-text-public-asset-review-required'});continue
        try: text=p.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            errors.append({'file':relative,'kind':'non-text-public-asset-review-required'});continue
        if '\x00' in text:
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
    return {'passed':not errors,'files':len(files),'reviewed_binary_assets':len(assets),'errors':errors,
            'scope':'Pattern/link checks on public text, explicit binary asset paths/hashes/sizes and PNG header dimensions or TTF sfnt signatures, plus optional runtime inventory. Asset rights and review declarations are human attestations, not machine-proven; visual/privacy review is still required.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--no-inventory',action='store_true');a=p.parse_args()
    try:result=check(inventory=not a.no_inventory)
    except (ValueError,OSError) as e: result={'passed':False,'errors':[{'message':str(e)}]}
    print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(0 if result['passed'] else 2)
