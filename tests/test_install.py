"""Real isolated installs, no-overwrite and source/destination safety checks."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import install as installer
from _payload import records, verify_inventory

class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workbench-install-test-')
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'source'
        self.source.mkdir()
        self.write('workbench.json', json.dumps({'name': 'product-ui-workbench', 'version': '0.11.0'}))
        self.write('SKILL.md', '---\nname: product-ui-workbench\ndescription: Test fixture\n---\nFixture')
        self.write('README.md', 'Install fixture')
        self.write('references/guide.md', 'Self-contained reference')
        self.write('scripts/tool.py', 'print("fixture")')
        self.write('portable-manifest.json', json.dumps({'name': 'product-ui-workbench', 'version': '0.11.0', 'entry': 'SKILL.md', 'files': records(self.source)}))
        self.target = self.root / 'installed/product-ui-workbench'
        self.root_patch = patch.object(installer, 'ROOT', self.source)
        self.root_patch.start()
    def tearDown(self):
        self.root_patch.stop()
        self.temp.cleanup()
    def write(self, name, data):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding='utf-8')
    def test_complete_new_target_verified_and_repeat_preserves_data(self):
        result = installer.install('codex', explicit=str(self.target))
        self.assertEqual(result['status'], 'installed')
        verify_inventory(self.target)
        self.assertEqual((self.target / 'references/guide.md').read_text(), 'Self-contained reference')
        self.assertFalse(result['dependencies_installed'])
        sentinel = self.target / 'my-work.txt'
        sentinel.write_text('Keep me')
        with self.assertRaisesRegex(ValueError, 'already exists'):
            installer.install('codex', explicit=str(self.target))
        self.assertEqual(sentinel.read_text(), 'Keep me')
        self.assertFalse(list(self.target.parent.glob('.product-ui-workbench-install-*')))
    def test_dry_run_does_not_create_parent_or_modify_source(self):
        before = records(self.source)
        result = installer.install('claude', explicit=str(self.target), dry_run=True)
        self.assertEqual(result['status'], 'dry-run')
        self.assertFalse(self.target.parent.exists())
        self.assertEqual(records(self.source), before)
    def test_project_and_default_host_targets(self):
        project = self.root / 'project'
        project.mkdir()
        self.assertEqual(installer.destination('codex', project=str(project)), project / '.agents/skills/product-ui-workbench')
        self.assertEqual(installer.destination('claude', project=str(project)), project / '.claude/skills/product-ui-workbench')
        with patch.object(Path, 'home', return_value=project):
            self.assertEqual(installer.destination('codex'), project / '.agents/skills/product-ui-workbench')
            self.assertEqual(installer.destination('claude'), project / '.claude/skills/product-ui-workbench')
        with self.assertRaisesRegex(ValueError, 'existing directory'):
            installer.destination('codex', project=str(project / 'missing'))
    def test_source_overlap_root_and_stale_source_rejected(self):
        with self.assertRaisesRegex(ValueError, 'overlap'):
            installer.install('codex', explicit=str(self.source / 'nested'))
        with self.assertRaises(ValueError):
            installer.install('codex', explicit=self.source.anchor)
        self.write('docs/unlisted.md', 'New file')
        with self.assertRaisesRegex(ValueError, 'Stale portable inventory'):
            installer.install('codex', explicit=str(self.target))
        self.assertFalse(self.target.exists())
    def test_destination_symlink_and_linked_ancestor_refused(self):
        real = self.root / 'real'
        real.mkdir()
        link = self.root / 'alias'
        try:
            link.symlink_to(real, target_is_directory=True)
        except OSError:
            self.skipTest('Host does not permit symlink fixtures')
        with self.assertRaisesRegex(ValueError, 'ancestor'):
            installer.install('codex', explicit=str(link / 'new-target'))
        self.assertEqual(list(real.iterdir()), [])
    def test_atomic_publish_never_replaces_existing_empty_directory(self):
        source = self.root / 'stage'
        source.mkdir()
        (source / 'new.txt').write_text('New source')
        existing = self.root / 'appeared'
        existing.mkdir()
        with self.assertRaises(OSError):
            installer.rename_new_directory(source, existing)
        self.assertTrue((source / 'new.txt').is_file())
        self.assertEqual(list(existing.iterdir()), [])

if __name__ == '__main__':
    unittest.main(verbosity=2)
