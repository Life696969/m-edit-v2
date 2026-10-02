import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class EvalDefinitionTests(unittest.TestCase):
    def test_eval_cases_cover_routing_and_pressure(self):
        payload = json.loads((ROOT / 'evals/cases.json').read_text(encoding='utf-8'))
        cases = payload['cases']
        self.assertGreaterEqual(len(cases), 6)
        skills = {case['expected_skill'] for case in cases}
        self.assertIn('m-edit', skills)
        self.assertIn('m-edit-transcribe', skills)
        self.assertIn('m-edit-final', skills)
        self.assertTrue(any('skip' in case['prompt'].lower() for case in cases))
        for case in cases:
            self.assertTrue(case['must_include'])


if __name__ == '__main__':
    unittest.main()
