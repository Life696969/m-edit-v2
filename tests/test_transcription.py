import json
import os
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRANSCRIBE = ROOT / 'shared/scripts/transcribe.py'
CONFIG = ROOT / 'shared/templates/config.template.json'


class TranscriptionTests(unittest.TestCase):
    def test_existing_adjacent_caption_is_imported_without_network(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            (project / '.m-edit').mkdir()
            (project / '.m-edit/config.json').write_text(CONFIG.read_text(encoding='utf-8'), encoding='utf-8')
            (project / 'clip.mp4').write_bytes(b'not-decoded-by-existing-provider')
            (project / 'clip.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nHello\n', encoding='utf-8')
            output = project / '.m-edit/transcripts/clip.json'
            subprocess.run([
                sys.executable, str(TRANSCRIBE), 'run', '--project', str(project), '--clip', 'clip.mp4',
                '--output', '.m-edit/transcripts/clip.json', '--provider', 'existing',
            ], check=True, capture_output=True, text=True)
            payload = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(payload['provider'], 'existing')
            self.assertEqual(payload['segments'][0]['text'], 'Hello')

    @unittest.skipIf(os.name == 'nt', 'plants a POSIX shell script as a fake whisper executable')
    def test_openai_whisper_requires_local_model_or_explicit_network_permission(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            (project / '.m-edit').mkdir()
            (project / '.m-edit/config.json').write_text(CONFIG.read_text(encoding='utf-8'), encoding='utf-8')
            (project / 'clip.mp4').write_bytes(b'clip')
            fake_bin = project / 'bin'
            fake_bin.mkdir()
            whisper = fake_bin / 'whisper'
            whisper.write_text('#!/usr/bin/env sh\nexit 99\n', encoding='utf-8')
            whisper.chmod(0o755)
            import os
            env = os.environ.copy()
            env['PATH'] = str(fake_bin) + os.pathsep + env['PATH']
            result = subprocess.run([
                sys.executable, str(TRANSCRIBE), 'run', '--project', str(project), '--clip', 'clip.mp4',
                '--output', '.m-edit/transcripts/clip.json', '--provider', 'openai-whisper',
            ], capture_output=True, text=True, env=env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('no confirmed local', (result.stderr + result.stdout).lower())

    def test_host_provider_exits_with_actionable_limitation(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            (project / '.m-edit').mkdir()
            (project / '.m-edit/config.json').write_text(CONFIG.read_text(encoding='utf-8'), encoding='utf-8')
            (project / 'clip.mp4').write_bytes(b'clip')
            result = subprocess.run([
                sys.executable, str(TRANSCRIBE), 'run', '--project', str(project), '--clip', 'clip.mp4',
                '--output', '.m-edit/transcripts/clip.json', '--provider', 'host',
            ], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('host agent must inspect the audio', result.stderr + result.stdout)


if __name__ == '__main__':
    unittest.main()
