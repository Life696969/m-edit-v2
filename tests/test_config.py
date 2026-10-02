import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'shared/scripts/validate_config.py'
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location('validate_config_tests', SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'shared/templates/config.template.json').read_text(encoding='utf-8'))

    def test_default_config_is_valid(self):
        self.assertEqual(module.validate(self.config), [])

    def test_review_and_explicit_merge_cannot_be_disabled(self):
        for field in module.REQUIRED_TRUE:
            with self.subTest(field=field):
                config = copy.deepcopy(self.config)
                config['workflow'][field] = False
                self.assertTrue(any(field in error for error in module.validate(config)))

    def test_four_to_five_questions_by_default(self):
        self.assertEqual((self.config['direction']['min_questions'], self.config['direction']['max_questions']), (4, 5))
        config = copy.deepcopy(self.config)
        config['direction']['max_questions'] = 9
        self.assertTrue(any('max_questions' in e for e in module.validate(config)))

    def test_rule_ranges_are_enforced(self):
        for field, value in (('camera_pulse_seconds', 0), ('cutaway_share_max', 0.95), ('max_caption_words', 40)):
            with self.subTest(field=field):
                config = copy.deepcopy(self.config)
                config['edit_rules'][field] = value
                self.assertTrue(any(field in error for error in module.validate(config)))
        config = copy.deepcopy(self.config)
        config['edit_rules']['background'] = 'replace-always'
        self.assertTrue(any('background' in error for error in module.validate(config)))

    def test_no_instruction_or_profile_settings_exist(self):
        for key in ('instruction_policy', 'profile', 'custom_profile_path', 'project_boundary'):
            self.assertNotIn(key, self.config)

    def test_output_path_must_stay_relative(self):
        config = copy.deepcopy(self.config)
        config['output_root'] = '../outside'
        self.assertTrue(module.validate(config))


if __name__ == '__main__':
    unittest.main()
