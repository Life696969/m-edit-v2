import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECIPE = ROOT / 'shared/scripts/recipe.py'


class RecipeTests(unittest.TestCase):
    def test_recipe_detects_any_included_input_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            (project / 'clip.mp4').write_bytes(b'clip')
            src = project / 'src'
            src.mkdir()
            (src / 'Root.tsx').write_text('export const Root = 1;\n', encoding='utf-8')
            output = project / 'recipe.json'
            subprocess.run([
                sys.executable, str(RECIPE), 'create', '--project', str(project), '--clip', 'clip.mp4',
                '--composition-id', 'Clip', '--entry-point', 'src/Root.tsx', '--include', 'src',
                '--render-command', 'npx remotion render Clip', '--output', 'recipe.json',
            ], check=True, capture_output=True, text=True)
            subprocess.run([sys.executable, str(RECIPE), 'verify', '--project', str(project), '--recipe', 'recipe.json'], check=True, capture_output=True, text=True)
            (src / 'Root.tsx').write_text('export const Root = 2;\n', encoding='utf-8')
            result = subprocess.run([sys.executable, str(RECIPE), 'verify', '--project', str(project), '--recipe', 'recipe.json'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_recipe_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            project = Path(temporary)
            (project / 'clip.mp4').write_bytes(b'clip')
            external = Path(outside) / 'secret.txt'
            external.write_text('secret', encoding='utf-8')
            result = subprocess.run([
                sys.executable, str(RECIPE), 'create', '--project', str(project), '--clip', 'clip.mp4',
                '--composition-id', 'Clip', '--include', str(external), '--render-command', 'render', '--output', 'recipe.json',
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
