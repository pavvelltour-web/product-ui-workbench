"""Shared runtime payload and exact integrity checks; never inventory the whole clone."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ('agents', 'docs', 'examples', 'library', 'licenses', 'references', 'schemas', 'scripts', 'tests')
FILES = ('SKILL.md', 'README.md', 'README.en.md', 'LICENSE', 'NOTICE', 'NOTICE.md', 'workbench.json', '.gitignore', '.gitattributes', 'requirements-render.txt')
INVENTORY = 'portable-manifest.json'
EXCLUDED_DIRS = {'.git', '.github', '.venv', 'venv', 'env', 'node_modules', '__pycache__', '.pytest_cache', '.mypy_cache', 'output', 'outputs', 'runs', 'private', 'secrets'}
EXCLUDED_SUFFIXES = {'.pyc', '.pyo', '.pem', '.key', '.p12', '.pfx'}

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def linked(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path.lstat(), 'st_file_attributes', 0) & 0x400)

def check_ancestors(path: Path) -> None:
    """Check lexical ancestors before resolving: resolution would hide a symlink."""
    current = Path(os.path.abspath(path))
    for candidate in (current, *current.parents):
        if candidate.exists() or candidate.is_symlink():
            if linked(candidate):
                raise ValueError('Symlink/reparse ancestor rejected: ' + str(candidate))
            if candidate != current and not candidate.is_dir():
                raise ValueError('Ancestor is not a directory: ' + str(candidate))

def excluded(path: Path) -> bool:
    name = path.name.lower()
    return name == '.env' or name.startswith('.env.') or path.suffix.lower() in EXCLUDED_SUFFIXES or name == '.workbench-install.json'

def payload_paths(root: Path, include_inventory: bool = False) -> list[Path]:
    root = Path(root)
    check_ancestors(root)
    if not root.is_dir():
        raise ValueError('Payload root is not a directory')
    paths = []
    for name in FILES + ((INVENTORY,) if include_inventory else ()):
        path = root / name
        if path.exists() or path.is_symlink():
            if linked(path) or not path.is_file():
                raise ValueError('Payload file link or non-file rejected: ' + name)
            paths.append(path)
    for folder in FOLDERS:
        start = root / folder
        if not start.exists() and not start.is_symlink():
            continue
        if linked(start) or not start.is_dir():
            raise ValueError('Payload directory link or non-directory rejected: ' + folder)
        for current, directories, files in os.walk(start, followlinks=False):
            current = Path(current)
            for name in directories:
                if linked(current / name):
                    raise ValueError('Payload symlink/reparse directory rejected: ' + str(current / name))
            directories[:] = sorted(name for name in directories if name.lower() not in EXCLUDED_DIRS)
            for name in sorted(files):
                path = current / name
                if linked(path):
                    raise ValueError('Payload symlink/reparse file rejected: ' + str(path))
                if excluded(path):
                    continue
                if not path.is_file():
                    raise ValueError('Non-regular payload file rejected: ' + str(path))
                paths.append(path)
    return sorted(paths, key=lambda path: path.relative_to(root).as_posix())

def records(root: Path) -> list[dict]:
    return [{'path': path.relative_to(root).as_posix(), 'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
            for path in payload_paths(root)]

def verify_inventory(root: Path) -> dict:
    root = Path(root)
    manifest_path = root / INVENTORY
    check_ancestors(manifest_path)
    if not manifest_path.is_file():
        raise ValueError('Portable inventory missing; maintainer must run scripts/inventory.py')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    declared = manifest.get('files')
    if not isinstance(declared, list) or not declared:
        raise ValueError('Portable inventory has no files')
    names = []
    for item in declared:
        name = item.get('path')
        if not isinstance(name, str) or not name or '\\' in name or ':' in name:
            raise ValueError('Unsafe inventory path')
        posix, windows = PurePosixPath(name), PureWindowsPath(name)
        if posix.is_absolute() or windows.is_absolute() or '..' in posix.parts or name != posix.as_posix():
            raise ValueError('Unsafe inventory path: ' + name)
        names.append(name)
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError('Duplicate inventory path')
    actual = records(root)
    actual_names = {item['path'] for item in actual}
    if set(names) != actual_names:
        raise ValueError('Stale portable inventory: payload file set changed')
    expected = {item['path']: item for item in declared}
    for item in actual:
        pin = expected[item['path']]
        if pin.get('sha256') != item['sha256'] or pin.get('bytes') != item['bytes']:
            raise ValueError('Stale portable inventory: ' + item['path'])
    identity = json.loads((root / 'workbench.json').read_text(encoding='utf-8'))
    if manifest.get('name') != identity.get('name') or manifest.get('version') != identity.get('version') or manifest.get('entry') != 'SKILL.md':
        raise ValueError('Inventory identity differs from workbench.json')
    return manifest
