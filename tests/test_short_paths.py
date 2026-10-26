"""Canonical workspace boundaries, including real Windows 8.3 aliases when available."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from pipeline import GateError, canonical_workspace, closure_files, file_record, safe, validate_closure
from _payload import check_ancestors, payload_paths
from demo import create as create_demo


def windows_short_path(path):
    if os.name != 'nt':
        raise unittest.SkipTest('Windows 8.3 alias regression requires Windows')
    get_short = ctypes.WinDLL('kernel32', use_last_error=True).GetShortPathNameW
    get_short.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint]
    get_short.restype = ctypes.c_uint
    buffer = ctypes.create_unicode_buffer(32768)
    count = get_short(str(path), buffer, len(buffer))
    if not count or count >= len(buffer):
        raise unittest.SkipTest('No usable Windows short-path alias on this volume')
    short = Path(buffer.value)
    if short == path.resolve():
        raise unittest.SkipTest('This volume does not provide a distinct Windows 8.3 alias')
    return short


class CanonicalWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workbench-boundary-')
        self.root = Path(self.temp.name).resolve()
        (self.root / 'inside.txt').write_text('Synthetic canonical boundary fixture')

    def tearDown(self):
        self.temp.cleanup()

    def test_canonical_file_record_and_closure_keep_workspace_relative_paths(self):
        root = canonical_workspace(self.root)
        self.assertEqual(root, self.root)
        self.assertEqual(file_record(root, 'inside.txt')['path'], 'inside.txt')
        (root / 'generated').mkdir()
        (root / 'generated/index.html').write_text('<title>Canonical fixture</title>')
        manifest = validate_closure(root, {'root': 'generated', 'entry': 'index.html', 'ownership': 'active',
                                          'files': closure_files(root, 'generated')})
        self.assertEqual(manifest['root'], 'generated')
        self.assertEqual(manifest['files'][0]['path'], 'index.html')

    def test_new_workspace_normalization_keeps_strict_root_and_child_boundaries(self):
        target = canonical_workspace(self.root / 'new/workspace', exists=False)
        self.assertEqual(target, self.root / 'new/workspace')
        self.assertFalse(target.exists())
        for unsafe in ('../outside.txt', str(self.root / 'inside.txt'), 'NUL', 'file.txt:stream'):
            with self.assertRaises(GateError):
                safe(self.root, unsafe)
        with self.assertRaises(GateError):
            canonical_workspace(self.root.anchor)
        with self.assertRaises(GateError):
            canonical_workspace(self.root / 'inside.txt')

    def test_lexical_symlink_ancestor_and_child_escape_are_rejected_before_resolution(self):
        real = self.root / 'real'
        real.mkdir()
        alias = self.root / 'alias'
        try:
            alias.symlink_to(real, target_is_directory=True)
        except OSError:
            self.skipTest('Host does not permit symlink fixtures')
        with self.assertRaisesRegex(GateError, 'Symlink/reparse'):
            canonical_workspace(alias)
        with self.assertRaisesRegex(GateError, 'Symlink/reparse'):
            canonical_workspace(alias / 'new', exists=False)
        with self.assertRaisesRegex(GateError, 'Symlink/reparse'):
            safe(self.root, 'alias/new')
        self.assertEqual(list(real.iterdir()), [])


class WindowsShortPathTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workbench-long-workspace-alias-')
        self.root = Path(self.temp.name).resolve()
        self.addCleanup(self.temp.cleanup)
        self.short = windows_short_path(self.root)

    def test_actual_short_alias_canonical_api_does_not_widen_containment(self):
        self.assertNotEqual(self.short, self.root)
        self.assertEqual(self.short.resolve(), self.root)
        (self.root / 'inside.txt').write_text('Synthetic short-alias fixture')
        canonical = canonical_workspace(self.short)
        self.assertEqual(canonical, self.root)
        self.assertEqual(safe(canonical, 'inside.txt', True), self.root / 'inside.txt')
        self.assertEqual(file_record(canonical, 'inside.txt')['path'], 'inside.txt')
        with self.assertRaises(GateError):
            safe(canonical, '../outside.txt')

    def test_demo_cli_accepts_actual_short_parent_and_returns_canonical_workspace(self):
        target = self.short / 'new-demo'
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/demo.py'), '--workspace', str(target)],
                                capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(Path(report['workspace']), self.root / 'new-demo')
        manifest = json.loads((self.root / 'new-demo/inputs/build.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['root'], 'generated/demo')
        self.assertEqual({item['path'] for item in manifest['files']}, {'index.html', 'native-workbench.mjs'})
        original = (self.root / 'new-demo/generated/demo/index.html').read_bytes()
        retry = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/demo.py'), '--workspace', str(target)], capture_output=True)
        self.assertEqual(retry.returncode, 2)
        self.assertEqual((self.root / 'new-demo/generated/demo/index.html').read_bytes(), original)

    def test_pipeline_cli_accepts_actual_short_workspace(self):
        (self.root / 'task.json').write_text(json.dumps({'job': 'Synthetic alias test', 'scope': 'One fixture screen',
                                                       'factual_data': ['Synthetic'], 'interactions': ['Open'], 'constraints': ['Offline']}))
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/pipeline.py'), '--workspace', str(self.short),
                                 'create', '--task', 'task.json', '--campaign', 'alias'], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.root / 'campaigns/alias/campaign.json').is_file())
        self.assertFalse((self.root / '.pipeline-lock').exists())


@unittest.skipUnless(os.name == 'nt', 'Windows junction regression requires Windows')
class WindowsJunctionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workbench-junction-')
        self.root = Path(self.temp.name).resolve()
        self.addCleanup(self.temp.cleanup)
        self.real = self.root / 'real'
        self.real.mkdir()
        self.alias = self.root / 'library'
        self.make_junction(self.alias)

    def make_junction(self, path):
        result = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(path), str(self.real)],
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(path.lstat().st_file_attributes & 0x400)
        # Remove only this fixture's junction entry before TemporaryDirectory cleanup.
        self.addCleanup(path.rmdir)

    def test_dangling_workspace_ancestor_rejected_before_demo_creates_target(self):
        self.real.rmdir()
        self.assertFalse(self.alias.exists())
        self.assertFalse(self.alias.is_symlink())
        for workspace in (self.alias, self.alias / 'new-demo'):
            with self.assertRaisesRegex(GateError, 'Symlink/reparse'):
                canonical_workspace(workspace, exists=False)
        with self.assertRaisesRegex(GateError, 'Symlink/reparse'):
            create_demo(self.alias / 'new-demo')
        self.assertFalse(self.real.exists())

    def test_dangling_child_junction_is_rejected_without_creating_target(self):
        self.real.rmdir()
        for relative in ('library', 'library/new'):
            with self.assertRaisesRegex(GateError, 'Symlink/reparse'):
                safe(self.root, relative)
        self.assertFalse(self.real.exists())

    def test_payload_dangling_ancestors_root_files_and_folders_are_rejected(self):
        self.real.rmdir()
        with self.assertRaisesRegex(ValueError, 'Symlink/reparse ancestor'):
            check_ancestors(self.alias / 'new')
        with self.assertRaisesRegex(ValueError, 'Payload directory link'):
            payload_paths(self.root)
        root_file = self.root / 'README.md'
        self.make_junction(root_file)
        with self.assertRaisesRegex(ValueError, 'Payload file link'):
            payload_paths(self.root)
        self.assertFalse(self.real.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
