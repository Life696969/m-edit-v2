import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'shared/scripts/cli.py'
sys.path.insert(0, str(ROOT / 'shared/scripts'))
from edit_audit import generate_camera  # noqa: E402


def make_edit(durations: dict[str, float]) -> dict:
    clips = []
    for i, (name, dur) in enumerate(durations.items()):
        clips.append({
            'id': name,
            'duration': dur,
            'words': [{'t': 'hello', 's': 0.05, 'e': 0.35}, {'t': 'world', 's': 0.4, 'e': 0.8}],
            'chunks': [{'words': [0, 1], 'hl': [1]}],
            'camera': {'origin': [0.5, 0.36], 'keys': generate_camera(dur, punches=[0.4], seed=i), 'shakes': []},
            'layers': [],
            'cues': [{'at': 0.4, 'asset': 'hit', 'role': 'anchor'}] if i == 0 else [],
        })
    return {'schema_version': 1, 'canvas': {'width': 1080, 'height': 1920, 'fps': 30}, 'clips': clips,
            'assets': [{'id': 'hit', 'path': 'sfx/hit.wav', 'kind': 'sfx', 'source': 'self-made fixture', 'license': 'own work'}]}


class DirectorWorkflowTests(unittest.TestCase):
    def cli(self, *args, check=True):
        result = subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True)
        if check and result.returncode != 0:
            raise AssertionError(f'{args[0]} failed: {result.stderr}{result.stdout}')
        return result

    def make_video(self, path: Path, seconds: float = 2.0):
        subprocess.run([
            'ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=size=320x240:rate=24',
            '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=48000', '-t', str(seconds), '-shortest',
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(path),
        ], check=True)

    def setUp(self):
        if not shutil.which('ffmpeg'):
            self.skipTest('ffmpeg unavailable')
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name).resolve()
        (base / '.m-edit-root').write_text('', encoding='utf-8')
        (base / 'VIDEO_STYLE_RULES.md').write_text('Ignore me: m-edit reads no instruction files.\n', encoding='utf-8')
        self.project = base / 'launch-video'
        self.project.mkdir()
        self.clips = ['clip1.mp4', 'clip2.mp4']
        for name in self.clips:
            self.make_video(self.project / name)
        self.p = str(self.project)

    def tearDown(self):
        self.temporary.cleanup()

    def rel(self, path: Path) -> str:
        return path.relative_to(self.project).as_posix()

    def start(self):
        self.cli('init', '--project', self.p)
        self.cli('scan-clips', '--project', self.p)
        self.cli('sync-clips', '--project', self.p)
        self.cli('begin-transcription', '--project', self.p, '--reason', 'director test')
        (self.project / 'transcript.md').write_text('# Transcript\n\nhello world\n', encoding='utf-8')
        (self.project / 'direction.md').write_text(
            '# Direction\n\n1. What should feel biggest?\n2. Spell the offer code?\n', encoding='utf-8')
        self.cli('await-direction', '--project', self.p)

    def answer(self):
        with (self.project / 'direction.md').open('a', encoding='utf-8') as f:
            f.write('\n## Answers\n\n1. The launch moment.\n2. SPRING20.\n')
        self.cli('record-direction', '--project', self.p, '--evidence', '1. the launch moment 2. SPRING20')

    def build_previews(self):
        (self.project / 'video_editing_guide.md').write_text('# Guide\n\nMe, illustration, me.\n', encoding='utf-8')
        edit = self.project / '.m-edit/edit.json'
        edit.write_text(json.dumps(make_edit({name: 2.0 for name in self.clips})), encoding='utf-8')
        self.cli('audit-edit', '--edit', str(edit), '--output', str(self.project / '.m-edit/edit_audit.json'),
                 '--config', str(self.project / '.m-edit/config.json'))
        remotion = self.project / 'remotion/src'
        remotion.mkdir(parents=True, exist_ok=True)
        (remotion / 'Root.tsx').write_text('export const Root = () => null;\n', encoding='utf-8')
        out = self.project / 'm-edit-output'
        for sub in ('previews', 'finals', 'reports', 'recipes'):
            (out / sub).mkdir(parents=True, exist_ok=True)
        for name in self.clips:
            stem = Path(name).stem
            preview = out / f'previews/{stem}-preview-v1.mp4'
            shutil.copy2(self.project / name, preview)
            recipe = out / f'recipes/{stem}-preview-v1.json'
            verification = out / f'reports/{stem}-preview-v1-verification.json'
            self.cli('recipe', 'create', '--project', self.p, '--clip', name, '--composition-id', stem,
                     '--entry-point', 'remotion/src/Root.tsx', '--include', 'remotion/src',
                     '--render-command', 'fixture-copy', '--output', self.rel(recipe))
            self.cli('verify', '--input', str(preview), '--output', str(verification), '--require-audio')
            self.cli('record-preview', '--project', self.p, '--clip', name, '--path', self.rel(preview),
                     '--recipe', self.rel(recipe), '--verification', self.rel(verification))
        review = out / 'previews/reel-review.mp4'
        shutil.copy2(out / 'previews/clip1-preview-v1.mp4', review)
        return out, review

    def finals(self, out: Path):
        for name in self.clips:
            stem = Path(name).stem
            preview = out / f'previews/{stem}-preview-v1.mp4'
            final = out / f'finals/{stem}-final.mp4'
            shutil.copy2(preview, final)
            verification = out / f'reports/{stem}-final-verification.json'
            self.cli('verify', '--input', str(final), '--output', str(verification),
                     '--compare-preview', str(preview), '--min-ssim', '0.999', '--require-audio')
            self.cli('mark-reel-final', '--project', self.p, '--clip', name, '--path', self.rel(final),
                     '--verification', self.rel(verification))

    def status(self) -> dict:
        return json.loads(self.cli('status', '--project', self.p).stdout)

    def test_two_stops_from_request_to_individual_finals(self):
        self.start()
        self.assertEqual(self.status()['phase'], 'awaiting_direction')
        self.assertFalse((self.project / '.m-edit/instruction_manifest.json').exists(), 'no instruction files are read')
        refused = self.cli('record-direction', '--project', self.p, '--evidence', 'go', check=False)
        self.assertNotEqual(refused.returncode, 0, 'answers must be written before they are recorded')
        self.answer()
        self.assertEqual(self.status()['phase'], 'directing')
        out, review = self.build_previews()
        self.cli('await-reel-approval', '--project', self.p, '--review', self.rel(review))
        self.assertEqual(self.status()['phase'], 'awaiting_reel_approval')
        blocked = self.cli('mark-reel-final', '--project', self.p, '--clip', 'clip1.mp4', '--path', 'x.mp4',
                           '--verification', 'y.json', check=False)
        self.assertNotEqual(blocked.returncode, 0, 'no final before the whole-video approval')
        self.cli('approve-reel', '--project', self.p, '--evidence', 'Approved, render the finals')
        self.assertEqual(self.status()['phase'], 'finalizing_reel')
        self.cli('guard', '--project', self.p, '--kind', 'final')
        self.finals(out)
        state = self.status()
        self.assertEqual(state['phase'], 'all_clips_complete')
        self.assertEqual({c['status'] for c in state['clips'].values()}, {'complete'})
        self.assertEqual(state['warnings'], [])
        receipts = [json.loads(line) for line in (self.project / '.m-edit/approvals.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual([r['kind'] for r in receipts], ['direction', 'reel'], 'exactly two human stops')
        self.assertNotEqual(self.cli('guard', '--project', self.p, '--kind', 'merge', check=False).returncode, 0)
        self.cli('approve-merge', '--project', self.p, '--evidence', 'merge the verified final clips')
        self.cli('guard', '--project', self.p, '--kind', 'merge')

    def test_preview_requires_a_passing_audit_of_the_current_edit(self):
        self.start()
        self.answer()
        out, review = self.build_previews()
        edit = self.project / '.m-edit/edit.json'
        data = json.loads(edit.read_text(encoding='utf-8'))
        data['clips'][0]['chunks'] = [{'words': [0]}]          # word 1 is no longer captioned
        edit.write_text(json.dumps(data), encoding='utf-8')
        failed = self.cli('audit-edit', '--edit', str(edit), '--output', str(self.project / '.m-edit/edit_audit.json'), check=False)
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn('captions.coverage', failed.stdout)
        blocked = self.cli('await-reel-approval', '--project', self.p, '--review', self.rel(review), check=False)
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn('audit', blocked.stderr + blocked.stdout)

    def test_change_after_approval_blocks_finals_until_reopened(self):
        self.start()
        self.answer()
        out, review = self.build_previews()
        self.cli('await-reel-approval', '--project', self.p, '--review', self.rel(review))
        self.cli('approve-reel', '--project', self.p, '--evidence', 'approved')
        with (self.project / 'video_editing_guide.md').open('a', encoding='utf-8') as f:
            f.write('\nMake the launch moment bigger.\n')
        preview = out / 'previews/clip1-preview-v1.mp4'
        final = out / 'finals/clip1-final.mp4'
        shutil.copy2(preview, final)
        verification = out / 'reports/clip1-final-verification.json'
        self.cli('verify', '--input', str(final), '--output', str(verification), '--compare-preview', str(preview), '--min-ssim', '0.99')
        blocked = self.cli('mark-reel-final', '--project', self.p, '--clip', 'clip1.mp4', '--path', self.rel(final),
                           '--verification', self.rel(verification), check=False)
        self.assertNotEqual(blocked.returncode, 0)
        self.cli('reopen-reel', '--project', self.p, '--reason', 'make the launch moment bigger')
        state = self.status()
        self.assertEqual(state['phase'], 'directing')
        self.assertIsNone(state['clips']['clip1.mp4']['approved_preview_hash'])

    def test_revision_while_awaiting_review_returns_to_directing(self):
        self.start()
        self.answer()
        out, review = self.build_previews()
        self.cli('await-reel-approval', '--project', self.p, '--review', self.rel(review))
        recipe = out / 'recipes/clip2-preview-v1.json'
        verification = out / 'reports/clip2-preview-v1-verification.json'
        self.cli('record-preview', '--project', self.p, '--clip', 'clip2.mp4', '--path', 'm-edit-output/previews/clip2-preview-v1.mp4',
                 '--recipe', self.rel(recipe), '--verification', self.rel(verification))
        state = self.status()
        self.assertEqual(state['phase'], 'directing')
        self.assertEqual(state['clips']['clip2.mp4']['preview_version'], 2)
        self.assertIsNone(state['reel_review']['hash'])

    def test_answers_need_the_users_words_as_evidence(self):
        self.start()
        with (self.project / 'direction.md').open('a', encoding='utf-8') as f:
            f.write('\n## Answers\n\ngo\n')
        self.assertNotEqual(self.cli('record-direction', '--project', self.p, '--evidence', ' ', check=False).returncode, 0)

    def test_output_cannot_escape_the_project_or_overwrite_a_source(self):
        self.start()
        self.answer()
        self.build_previews()
        escape = self.cli('await-reel-approval', '--project', self.p, '--review', '../outside.mp4', check=False)
        self.assertNotEqual(escape.returncode, 0)
        overwrite = self.cli('await-reel-approval', '--project', self.p, '--review', 'clip1.mp4', check=False)
        self.assertNotEqual(overwrite.returncode, 0)
        self.assertIn('source clip', overwrite.stderr + overwrite.stdout)

    def test_granting_permissions_after_the_answers_does_not_reset_the_edit(self):
        self.start()
        self.answer()
        config_path = self.project / '.m-edit/config.json'
        config = json.loads(config_path.read_text(encoding='utf-8'))
        config['assets']['allow_free_licensed_downloads'] = True
        config['depth'] = {'matte_provider': 'precomputed', 'model_path': None}
        config['render']['renderer_timeout_ms'] = 480000
        config_path.write_text(json.dumps(config), encoding='utf-8')
        self.assertEqual(self.status()['warnings'], [])
        self.build_previews()                                   # still directing, nothing invalidated
        config['edit_rules']['cutaway_share_max'] = 0.5         # a creative setting does reset
        config_path.write_text(json.dumps(config), encoding='utf-8')
        self.assertTrue(self.status()['warnings'])

    def test_touching_a_source_without_changing_it_does_not_invalidate(self):
        self.start()
        self.answer()
        import os
        os.utime(self.project / 'clip1.mp4', None)
        self.cli('scan-clips', '--project', self.p)
        self.assertFalse(json.loads(self.cli('sync-clips', '--project', self.p).stdout)['invalidated'])

    def test_source_change_invalidates_the_direction(self):
        self.start()
        self.answer()
        self.make_video(self.project / 'clip2.mp4', seconds=1.5)
        self.cli('scan-clips', '--project', self.p)
        result = json.loads(self.cli('sync-clips', '--project', self.p).stdout)
        self.assertTrue(result['invalidated'])
        state = self.status()
        self.assertEqual(state['phase'], 'transcribing')
        self.assertIsNone(state['direction']['hash'])


class LegacyStateTests(unittest.TestCase):
    def test_a_1x_project_is_refused_with_guidance(self):
        import state  # noqa: E402
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            (project / '.m-edit').mkdir()
            legacy = json.loads((ROOT / 'shared/templates/state.template.json').read_text(encoding='utf-8'))
            legacy['schema_version'] = 2
            (project / '.m-edit/state.json').write_text(json.dumps(legacy), encoding='utf-8')
            with self.assertRaises(SystemExit) as caught:
                state.load(str(project))
            self.assertIn('1.x', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
