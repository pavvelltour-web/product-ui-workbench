"""Copy this complete skill into a NEW destination; never overwrite or install dependencies."""
from __future__ import annotations
import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from _payload import ROOT, check_ancestors, payload_paths, sha, verify_inventory

def rename_new_directory(source, target):
    """Atomic publication with no replacement, including an empty destination race."""
    if os.name == 'nt':
        # Windows rename refuses existing files and directories.
        os.rename(source, target)
        return
    runtime = ctypes.CDLL(None, use_errno=True)
    if sys.platform.startswith('linux') and hasattr(runtime, 'renameat2'):
        rename = runtime.renameat2
        rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        status = rename(-100, os.fsencode(source), -100, os.fsencode(target), 1)  # RENAME_NOREPLACE
    elif sys.platform == 'darwin' and hasattr(runtime, 'renamex_np'):
        rename = runtime.renamex_np
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        status = rename(os.fsencode(source), os.fsencode(target), 4)  # RENAME_EXCL
    else:
        raise ValueError('Atomic no-overwrite directory install unavailable on this OS; clone into a new skill folder manually')
    if status:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(target))

def destination(host, project=None, explicit=None):
    if host not in ('codex', 'claude'):
        raise ValueError('Host must be codex or claude')
    if project is not None and explicit is not None:
        raise ValueError('Choose --project or --destination, not both')
    if explicit is not None:
        target = Path(os.path.abspath(Path(explicit).expanduser()))
    else:
        base = Path(os.path.abspath(Path(project).expanduser())) if project is not None else Path.home()
        check_ancestors(base)
        if not base.is_dir():
            raise ValueError('--project must be an existing directory')
        target = base / ('.agents' if host == 'codex' else '.claude') / 'skills' / 'product-ui-workbench'
    check_ancestors(target)
    if target == Path(target.anchor) or target.parent == target:
        raise ValueError('Drive/filesystem root destination rejected')
    if target.exists() or target.is_symlink():
        raise ValueError('Destination already exists; existing data preserved')
    source = ROOT.resolve()
    resolved = target.resolve()
    if resolved.is_relative_to(source) or source.is_relative_to(resolved):
        raise ValueError('Source and destination overlap')
    return target

def install(host, project=None, explicit=None, dry_run=False):
    manifest = verify_inventory(ROOT)
    target = destination(host, project, explicit)
    paths = payload_paths(ROOT, include_inventory=True)
    result = {'status': 'dry-run' if dry_run else 'installed', 'host': host, 'destination': str(target),
              'version': manifest['version'], 'files': len(paths), 'dependencies_installed': False,
              'host_settings_changed': False, 'restart_performed': False}
    if dry_run:
        return result
    target.parent.mkdir(parents=True, exist_ok=True)
    check_ancestors(target.parent)
    staging = Path(tempfile.mkdtemp(prefix='.product-ui-workbench-install-', dir=target.parent))
    try:
        for path in paths:
            relative = path.relative_to(ROOT)
            output = staging / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            data = path.read_bytes()
            output.write_bytes(data)
            if sha(output.read_bytes()) != sha(data):
                raise ValueError('Installed copy hash mismatch: ' + relative.as_posix())
        verify_inventory(staging)
        receipt = {**result, 'installed_at': datetime.now(timezone.utc).isoformat(), 'verification': 'exact allowlisted payload and hashes'}
        (staging / '.workbench-install.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        check_ancestors(target)
        if target.exists():
            raise ValueError('Destination appeared during installation; existing data preserved')
        rename_new_directory(staging, target)
        verify_inventory(target)
    finally:
        # Only the unique directory created by this invocation is disposable.
        if staging.exists():
            if staging.parent != target.parent or not staging.name.startswith('.product-ui-workbench-install-'):
                raise ValueError('Unexpected staging path; cleanup refused')
            shutil.rmtree(staging)
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', required=True, choices=('codex', 'claude'))
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument('--project', help='Existing project directory for project-scoped installation')
    choice.add_argument('--destination', help='Explicit new directory instead of the default host path')
    parser.add_argument('--dry-run', action='store_true', help='Verify source and show target without writing')
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.host, args.project, args.destination, args.dry_run), indent=2))
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({'status': 'error', 'error': str(error)}))
        sys.exit(2)
