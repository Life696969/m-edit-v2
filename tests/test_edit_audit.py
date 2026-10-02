import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'shared/scripts'))
from edit_audit import DEFAULT_RULES, audit, generate_camera  # noqa: E402


def clip(dur=6.0, words=None, seed=0):
    words = words or [{'t': w, 's': 0.3 * i, 'e': 0.3 * i + 0.25} for i, w in enumerate(['today', 'we', 'hit', 'one', 'million', 'users'])]
    return {'id': 'clip1.mp4', 'duration': dur, 'words': words,
            'chunks': [{'words': [0, 1, 2], 'hl': [2]}, {'words': [3, 4, 5]}],
            'camera': {'origin': [0.5, 0.36], 'keys': generate_camera(dur, punches=[0.9], seed=seed), 'shakes': []},
            'layers': [], 'cues': []}


def edit(*clips, assets=None):
    return {'schema_version': 1, 'canvas': {'width': 1080, 'height': 1920, 'fps': 30}, 'clips': list(clips),
            'assets': assets or [{'id': 'boom', 'path': 'sfx/boom.wav', 'kind': 'sfx', 'source': 'library', 'license': 'own pack'}]}


def rules_hit(e, **overrides):
    findings, metrics = audit(e, {**DEFAULT_RULES, **overrides})
    return {f['rule'] for f in findings}, metrics


class EditAuditTests(unittest.TestCase):
    def test_a_clean_edit_passes(self):
        hit, metrics = rules_hit(edit(clip()))
        self.assertEqual(hit, set())
        self.assertEqual(metrics['speaker_share'], 1.0)

    def test_camera_needs_a_key_every_pulse(self):
        c = clip()
        c['camera']['keys'] = [k for k in c['camera']['keys'] if not 1.5 < k['t'] < 3.5]
        self.assertIn('camera.pulse', rules_hit(edit(c))[0])

    def test_camera_must_never_expose_a_frame_edge(self):
        c = clip()
        c['camera']['keys'][2] = {**c['camera']['keys'][2], 's': 1.03, 'x': 0.006}
        c['camera']['shakes'] = [{'t': 2.0, 'dur': 0.3, 'amp': 12.0}]     # a shake eats the crop margin
        self.assertIn('camera.edge', rules_hit(edit(c))[0])

    def test_camera_moves_must_not_tick_like_a_metronome(self):
        c = clip()
        c['camera']['keys'] = [{'t': float(t), 's': 1.03 if t % 2 == 0 else 1.05, 'x': 0.0, 'y': 0.0} for t in range(7)]
        c['duration'] = 6.0
        self.assertIn('camera.metronome', rules_hit(edit(c))[0])

    def test_pulse_is_configurable(self):
        c = clip()
        c['camera']['keys'] = generate_camera(6.0, seed=1, rules={**DEFAULT_RULES, 'camera_pulse_seconds': 2.0})
        self.assertIn('camera.pulse', rules_hit(edit(c))[0])
        self.assertNotIn('camera.pulse', rules_hit(edit(c), camera_pulse_seconds=2.0)[0])

    def test_every_word_is_captioned_once_and_chunks_stay_short(self):
        c = clip()
        c['chunks'] = [{'words': [0, 1, 2, 3, 4]}, {'words': [5]}]
        self.assertIn('captions.length', rules_hit(edit(c))[0])
        c['chunks'] = [{'words': [0, 1, 2]}, {'words': [4, 5]}]
        self.assertIn('captions.coverage', rules_hit(edit(c))[0])

    def test_cutaways_cannot_take_over_the_video(self):
        c = clip()
        c['layers'] = [{'id': 'a', 'type': 'cutaway', 's': 0.0, 'e': 2.6}]
        hit, metrics = rules_hit(edit(c))
        self.assertIn('cutaway.share', hit)
        self.assertAlmostEqual(metrics['cutaway_share'], 2.6 / 6.0, places=3)
        c['layers'] = [{'id': 'a', 'type': 'cutaway', 's': 0.0, 'e': 5.0}]
        self.assertIn('cutaway.length', rules_hit(edit(c), cutaway_share_max=0.9)[0])

    def test_one_card_or_cutaway_at_a_time(self):
        c = clip()
        c['layers'] = [{'id': 'card', 'type': 'card', 's': 0.5, 'e': 2.0}, {'id': 'cut', 'type': 'cutaway', 's': 1.5, 'e': 2.5}]
        self.assertIn('layers.overlap', rules_hit(edit(c))[0])

    def test_layers_never_cross_a_clip_boundary(self):
        c = clip()
        c['layers'] = [{'id': 'card', 'type': 'card', 's': 5.0, 'e': 6.4}]
        self.assertIn('layers.bounds', rules_hit(edit(c))[0])

    def test_background_is_preserved_unless_allowed(self):
        c = clip()
        c['layers'] = [{'id': 'bg', 'type': 'background-replace', 's': 0.0, 'e': 1.0}]
        self.assertIn('background.preserve', rules_hit(edit(c))[0])
        self.assertNotIn('background.preserve', rules_hit(edit(c), background='allow-replace')[0])

    def test_depth_beat_needs_a_matte(self):
        c = clip()
        c['layers'] = [{'id': 'hundred', 'type': 'depth', 's': 1.0, 'e': 3.0}]
        self.assertIn('depth.matte', rules_hit(edit(c))[0])
        c['layers'][0]['matte'] = 'p1_proxy.webm'
        self.assertNotIn('depth.matte', rules_hit(edit(c))[0])

    def test_real_people_appear_only_when_named(self):
        assets = [{'id': 'jane', 'path': 'img/jane.jpg', 'kind': 'photo', 'person': 'Jane Doe', 'source': 'press kit', 'license': 'press use'}]
        c = clip()
        c['layers'] = [{'id': 'jane-photo', 'type': 'photo', 'asset': 'jane', 's': 0.5, 'e': 1.5}]
        self.assertIn('people.named', rules_hit(edit(c, assets=assets))[0])
        c['words'][1]['t'] = 'Doe'
        self.assertNotIn('people.named', rules_hit(edit(c, assets=assets))[0])

    def test_one_anchor_hit_and_a_licensed_ledger(self):
        c = clip()
        c['cues'] = [{'at': 1.0, 'asset': 'boom', 'role': 'anchor'}, {'at': 3.0, 'asset': 'boom', 'role': 'anchor'}]
        self.assertIn('cues.anchor', rules_hit(edit(c))[0])
        c['cues'] = [{'at': 1.0, 'asset': 'mystery', 'role': 'ui'}]
        self.assertIn('assets.ledger', rules_hit(edit(c))[0])
        unlicensed = [{'id': 'boom', 'path': 'x.wav', 'source': 'somewhere', 'license': ''}]
        self.assertIn('assets.ledger', rules_hit(edit(clip(), assets=unlicensed))[0])

    def test_captions_and_cards_clear_the_face_when_face_data_exists(self):
        c = clip()
        c['face'] = [{'t': t / 10, 'eye': 0.36, 'mouth': 0.55, 'chin': 0.62} for t in range(60)]
        c['chunks'][0]['y'] = 0.56                                  # on the mouth
        c['layers'] = [{'id': 'card', 'type': 'card', 's': 2.0, 'e': 4.0, 'box': [64, 200, 1016, 640]}]
        hit = rules_hit(edit(c))[0]
        self.assertIn('captions.mouth', hit)
        self.assertIn('cards.eyes', hit)

    def test_generated_camera_always_passes(self):
        for seed in range(150):
            for dur, punches, jumps in ((6.5, [0.0, 2.2, 4.2], []), (16.0, [0.5, 4.6, 9.6, 14.7], [3.1, 8.0]), (2.0, [1.0], [])):
                c = clip(dur=dur)
                c['camera'] = {'origin': [0.5, 0.36], 'keys': generate_camera(dur, punches=punches, jumps=jumps, seed=seed, shake_px=4.5),
                               'shakes': [{'t': 0.2, 'dur': 0.3, 'amp': 4.5}]}
                camera_rules = {r for r in rules_hit(edit(c))[0] if r.startswith('camera')}
                self.assertEqual(camera_rules, set(), f'seed {seed}, {dur}s')

    def test_cli_writes_a_report_bound_to_the_edit_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'edit.json'
            path.write_text(json.dumps(edit(clip())), encoding='utf-8')
            report = Path(temporary) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'shared/scripts/cli.py'), 'audit-edit', '--edit', str(path), '--output', str(report)],
                           check=True, capture_output=True)
            data = json.loads(report.read_text(encoding='utf-8'))
            self.assertTrue(data['passed'])
            import hashlib
            self.assertEqual(data['edit_sha256'], hashlib.sha256(path.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
