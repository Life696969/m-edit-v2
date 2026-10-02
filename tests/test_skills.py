import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/validate_skills.py'
spec = importlib.util.spec_from_file_location('validate_skills_tests', SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)


class SkillMetadataTests(unittest.TestCase):
    def test_all_skill_metadata_and_gate_markers_are_valid(self):
        self.assertEqual(module.validate(ROOT), [])

    def test_every_specialist_can_resolve_suite_root_independently(self):
        for path in (ROOT / 'skills').glob('m-edit-*/SKILL.md'):
            text = path.read_text(encoding='utf-8')
            self.assertIn('CLAUDE_PLUGIN_ROOT', text, path.parent.name)
            self.assertIn('~/.m-edit/current', text, path.parent.name)

    def test_router_is_shorter_than_specialist_suite(self):
        router = (ROOT / 'skills/m-edit/SKILL.md').read_text(encoding='utf-8').split()
        specialists = sum(len(path.read_text(encoding='utf-8').split()) for path in (ROOT / 'skills').glob('m-edit-*/SKILL.md'))
        self.assertLess(len(router), specialists)


if __name__ == '__main__':
    unittest.main()
