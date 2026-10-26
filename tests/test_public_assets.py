"""A narrow original-showcase registry cannot authorize arbitrary binary publication."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from check_public import ASSET_REGISTRY, check


def fixture_png(width=2, height=1):
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress((b'\x00' + bytes(width * 3)) * height)) + chunk(b'IEND', b''))


class PublicAssetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='workbench-public-assets-')
        self.root = Path(self.temp.name).resolve()
        (self.root / 'README.md').write_text('Original synthetic asset fixture', encoding='utf-8')
        self.png = 'examples/showcase/images/example-desktop.png'
        self.font = 'examples/showcase/app/public/fonts/Example.ttf'
        self.write(self.png, fixture_png())
        # Header-only sfnt fixture: the gate intentionally does not prove usable glyphs or font licensing.
        self.write(self.font, b'\x00\x01\x00\x00' + bytes(8))
        self.registry = {'version': 1, 'assets': [self.entry(self.png, 'png'), self.entry(self.font, 'ttf')]}
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def entry(self, name, kind):
        data = (self.root / name).read_bytes()
        result = {'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'kind': kind,
                  'rights': 'Original authored interface; synthetic fixture' if kind == 'png' else 'OFL-1.1; retain the accompanying license'}
        if kind == 'png':
            result.update(width=2, height=1)
        return result

    def save(self, data=None):
        self.write(ASSET_REGISTRY, json.dumps(self.registry if data is None else data).encode('utf-8'))

    def result(self):
        return check(self.root, inventory=False)

    def assert_rejected(self):
        result = self.result()
        self.assertFalse(result['passed'], result)
        return result

    def test_explicit_original_png_and_font_pins_are_accepted_without_visual_claim(self):
        result = self.result()
        self.assertTrue(result['passed'], result)
        self.assertEqual(result['reviewed_binary_assets'], 2)
        self.assertIn('human attestations', result['scope'])
        self.assertIn('visual/privacy review', result['scope'])

    def test_legacy_missing_registry_allows_text_but_no_binary(self):
        (self.root / ASSET_REGISTRY).unlink()
        self.assert_rejected()
        (self.root / self.png).unlink()
        (self.root / self.font).unlink()
        self.assertTrue(self.result()['passed'])

    def test_unlisted_non_utf8_and_utf8_with_nul_binaries_rejected(self):
        for name, data in [('examples/showcase/images/unlisted.png', fixture_png()), ('docs/hidden.data', b'utf8\x00binary'),
                           ('docs/ascii.bin', b'ASCII-only binary payload'), ('docs/ascii.pdf', b'%PDF-1.4 ASCII-only fixture')]:
            with self.subTest(name=name):
                self.write(name, data)
                result = self.assert_rejected()
                self.assertTrue(any(item.get('file') == name and item['kind'] == 'non-text-public-asset-review-required' for item in result['errors']))
                (self.root / name).unlink()

    def test_modified_bytes_size_missing_asset_and_png_dimensions_rejected(self):
        original = (self.root / self.png).read_bytes()
        self.write(self.png, original + b'changed')
        self.assert_rejected()
        self.write(self.png, original)
        for field, value in [('bytes', len(original) + 1), ('width', 1), ('height', 0), ('rights', ''), ('sha256', 'not-a-hash')]:
            with self.subTest(field=field):
                data = copy.deepcopy(self.registry)
                data['assets'][0][field] = value
                self.save(data)
                self.assert_rejected()
        self.save()
        (self.root / self.font).unlink()
        self.assert_rejected()

    def test_arbitrary_paths_traversal_duplicate_and_wrong_kind_cannot_be_approved(self):
        for value in ['../outside.png', '/outside.png', 'C:/outside.png', 'examples/showcase/images/subdir/extra.png',
                      'docs/reference.png', 'examples/showcase/images/../extra.png', 'examples\\showcase\\images\\extra.png']:
            with self.subTest(path=value):
                data = copy.deepcopy(self.registry)
                data['assets'][0]['path'] = value
                self.save(data)
                self.assert_rejected()
        data = copy.deepcopy(self.registry)
        data['assets'].append(copy.deepcopy(data['assets'][0]))
        self.save(data)
        self.assert_rejected()
        data = copy.deepcopy(self.registry)
        data['assets'][0]['kind'] = 'ttf'
        self.save(data)
        self.assert_rejected()

    def test_signature_checks_do_not_accept_only_matching_hashes(self):
        for name, kind in [(self.png, 'png'), (self.font, 'ttf')]:
            original = (self.root / name).read_bytes()
            self.write(name, b'wrong-format\x00' + original)
            data = copy.deepcopy(self.registry)
            data['assets'][0 if kind == 'png' else 1] = self.entry(name, kind)
            self.save(data)
            self.assert_rejected()
            self.write(name, original)
            self.save()

    def test_malformed_registry_extra_fields_and_duplicate_json_keys_rejected(self):
        for data in [{'version': True, 'assets': []}, {'version': 2, 'assets': []}, {'version': 1, 'assets': {}},
                     {'version': 1, 'assets': [], 'unreviewed': True}, {'version': 1, 'assets': ['bad-entry']}]:
            self.save(data)
            self.assert_rejected()
        self.write(ASSET_REGISTRY, b'{"version":1,"version":1,"assets":[]}')
        self.assert_rejected()
        self.write(ASSET_REGISTRY, b'{')
        self.assert_rejected()

    def test_asset_symlink_to_other_file_is_rejected(self):
        original = (self.root / self.png).read_bytes()
        target = self.root / 'other.png'
        target.write_bytes(original)
        path = self.root / self.png
        path.unlink()
        try:
            path.symlink_to(target)
        except OSError:
            self.skipTest('Host does not permit symlink fixtures')
        with self.assertRaises(ValueError):
            self.result()


if __name__ == '__main__':
    unittest.main(verbosity=2)
