import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = ROOT / 'shared/scripts/scaffold_remotion.py'


class ScaffoldTests(unittest.TestCase):
    def test_scaffold_creates_neutral_project_without_installing_dependencies(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            subprocess.run([sys.executable, str(SCAFFOLD), '--project', str(project)], check=True, capture_output=True, text=True)
            target = project / 'm-edit-remotion'
            self.assertTrue((target / 'src/CaptionTrack.tsx').exists())
            self.assertTrue((target / 'package.json').exists())
            self.assertFalse((target / 'node_modules').exists())
            result = subprocess.run([sys.executable, str(SCAFFOLD), '--project', str(project)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_target_path_cannot_escape_project(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            result = subprocess.run([
                sys.executable, str(SCAFFOLD), '--project', str(project), '--target', '../outside'
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
