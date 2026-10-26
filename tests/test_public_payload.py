"""Public payload rejects stale additions and never inventories clone metadata/secrets."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from _payload import payload_paths, records, verify_inventory

class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workbench-payload-')
        self.root = Path(self.temp.name).resolve()
        self.write('workbench.json', json.dumps({'name': 'product-ui-workbench', 'version': '0.11.0'}))
        self.write('SKILL.md', '---\nname: product-ui-workbench\ndescription: Fixture\n---\nFixture')
        self.write('README.md', 'Fixture')
        self.write('references/guide.md', 'Portable guide')
        self.write('scripts/tool.py', 'print("fixture")')
    def tearDown(self):
        self.temp.cleanup()
    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding='utf-8')
    def seal(self):
        self.write('portable-manifest.json', json.dumps({'name': 'product-ui-workbench', 'version': '0.11.0', 'entry': 'SKILL.md', 'files': records(self.root)}))
    def test_clone_metadata_private_and_environments_not_in_runtime(self):
        forbidden = ['.git/config', '.github/workflows/ci.yml', '.env', 'output/result.txt', '.venv/secret.txt',
                     'scripts/__pycache__/tool.pyc', 'docs/.env.local', 'library/node_modules/package/file.js',
                     'references/private/reference.png', 'library/secrets/client.txt', 'docs/cert.pem']
        for name in forbidden:
            self.write(name, 'not distributed')
        self.seal()
        names = {path.relative_to(self.root).as_posix() for path in payload_paths(self.root)}
        self.assertFalse(names.intersection(forbidden))
        self.assertEqual(len(names), 5)
        verify_inventory(self.root)
    def test_unlisted_new_file_missing_file_and_changed_bytes_fail(self):
        self.seal()
        self.write('docs/new.md', 'Added after inventory')
        with self.assertRaisesRegex(ValueError, 'file set changed'):
            verify_inventory(self.root)
        (self.root / 'docs/new.md').unlink()
        self.write('scripts/tool.py', 'print("changed")')
        with self.assertRaisesRegex(ValueError, 'Stale portable inventory'):
            verify_inventory(self.root)
        self.seal()
        (self.root / 'references/guide.md').unlink()
        with self.assertRaisesRegex(ValueError, 'file set changed'):
            verify_inventory(self.root)
    def test_duplicate_traversal_and_identity_inventory_rejected(self):
        self.seal()
        original = json.loads((self.root / 'portable-manifest.json').read_text())
        for change in ('duplicate', 'traversal', 'identity'):
            data = json.loads(json.dumps(original))
            if change == 'duplicate':
                data['files'].append(data['files'][0])
            elif change == 'traversal':
                data['files'][0]['path'] = '../outside.txt'
            else:
                data['version'] = 'different'
            self.write('portable-manifest.json', json.dumps(data))
            with self.assertRaises(ValueError):
                verify_inventory(self.root)
    def test_symlink_payload_and_ancestor_refused(self):
        outside = self.root / 'outside.txt'
        outside.write_text('Outside scope')
        link = self.root / 'references/linked.md'
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest('Host does not permit symlink fixtures')
        with self.assertRaisesRegex(ValueError, 'symlink/reparse'):
            payload_paths(self.root)
        link.unlink()
        alias = self.root / 'alias'
        alias.symlink_to(self.root / 'references', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'ancestor'):
            payload_paths(alias)

if __name__ == '__main__':
    unittest.main(verbosity=2)
