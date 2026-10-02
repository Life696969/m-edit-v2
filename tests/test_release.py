import hashlib
import sys
import importlib.util
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / 'shared/scripts/release_audit.py'
PACKAGE = ROOT / 'scripts/package_release.py'


class ReleaseTests(unittest.TestCase):
    def test_release_audit_passes_source_tree(self):
        subprocess.run([sys.executable, str(AUDIT), '--root', str(ROOT)], check=True, capture_output=True, text=True)

    def test_release_audit_catches_private_denylist_material_and_secret(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / 'source'
            root.mkdir()
            (root / 'skills/example').mkdir(parents=True)
            (root / '.claude-plugin').mkdir()
            (root / 'VERSION').write_text('1.0.0\n', encoding='utf-8')
            private_phrase = 'creator-private-sentinel'
            token = 'sk-' + 'abcdefghijklmnopqrstuvwxyz'
            (root / 'skills/example/SKILL.md').write_text(f'---\nname: example\ndescription: Use when testing\nversion: 1.0.0\n---\n{private_phrase} {token}\n', encoding='utf-8')
            (root / '.claude-plugin/plugin.json').write_text('{"version":"1.0.0"}', encoding='utf-8')
            (root / '.claude-plugin/marketplace.json').write_text('{"version":"1.0.0","plugins":[]}', encoding='utf-8')
            denylist = Path(temporary) / 'private-denylist.txt'
            denylist.write_text(private_phrase + '\n', encoding='utf-8')
            result = subprocess.run([
                sys.executable, str(AUDIT), '--root', str(root), '--private-denylist', str(denylist)
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('private denylist phrase', result.stdout + result.stderr)
            self.assertIn('OpenAI token', result.stdout + result.stderr)

    def test_packaging_is_deterministic_and_excludes_generated_files(self):
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            subprocess.run([sys.executable, str(PACKAGE), '--root', str(ROOT), '--dist', one], check=True, capture_output=True, text=True)
            subprocess.run([sys.executable, str(PACKAGE), '--root', str(ROOT), '--dist', two], check=True, capture_output=True, text=True)
            version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
            first = Path(one) / f'm-edit-{version}.zip'
            second = Path(two) / f'm-edit-{version}.zip'
            self.assertEqual(hashlib.sha256(first.read_bytes()).hexdigest(), hashlib.sha256(second.read_bytes()).hexdigest())
            with zipfile.ZipFile(first) as archive:
                names = archive.namelist()
            self.assertFalse(any('__pycache__' in name or name.endswith('.pyc') or '/dist/' in name for name in names))
            self.assertTrue(any(name.endswith('/skills/m-edit/SKILL.md') for name in names))


if __name__ == '__main__':
    unittest.main()
