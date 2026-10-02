import json
import sys
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN = ROOT / 'shared' / 'scripts' / 'scan_clips.py'
VERIFY = ROOT / 'shared' / 'scripts' / 'verify_media.py'


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
class MediaToolTests(unittest.TestCase):
    def make_video(self, path: Path, color='black'):
        subprocess.run([
            'ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'color=size=320x240:rate=24:color={color}',
            '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', '0.8', '-shortest',
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(path),
        ], check=True)

    def test_scan_excludes_output_full_hashes_and_verify_compares(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            (project / '.m-edit').mkdir()
            (project / '.m-edit' / 'config.json').write_text(json.dumps({
                'output_root': 'm-edit-output', 'source_hash_mode': 'full'
            }), encoding='utf-8')
            source = project / 'source.mp4'
            self.make_video(source)
            output_dir = project / 'm-edit-output'
            output_dir.mkdir()
            self.make_video(output_dir / 'render.mp4')

            subprocess.run([sys.executable, str(SCAN), '--project', str(project)], check=True, capture_output=True, text=True)
            inventory = json.loads((project / '.m-edit' / 'clip_inventory.json').read_text(encoding='utf-8'))
            self.assertEqual([clip['path'] for clip in inventory['clips']], ['source.mp4'])
            self.assertEqual(inventory['clips'][0]['fingerprint']['hash_mode'], 'full')
            self.assertEqual(len(inventory['clips'][0]['fingerprint']['sha256']), 64)

            verification = project / 'verification.json'
            sheet = project / 'sheet.jpg'
            subprocess.run([
                sys.executable, str(VERIFY), '--input', str(source), '--output', str(verification),
                '--width', '320', '--height', '240', '--require-audio', '--compare-preview', str(source),
                '--min-ssim', '0.999', '--contact-sheet', str(sheet),
            ], check=True, capture_output=True, text=True)
            payload = json.loads(verification.read_text(encoding='utf-8'))
            self.assertTrue(payload['passed'])
            self.assertTrue(payload['checks']['all_streams_decode'])
            self.assertGreaterEqual(payload['comparison']['ssim'], 0.999)
            self.assertTrue(sheet.exists())

    def test_visual_drift_fails_ssim(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            preview = project / 'preview.mp4'
            final = project / 'final.mp4'
            self.make_video(preview, 'black')
            self.make_video(final, 'white')
            completed = subprocess.run([
                sys.executable, str(VERIFY), '--input', str(final), '--output', str(project / 'verification.json'),
                '--compare-preview', str(preview), '--min-ssim', '0.99',
            ], capture_output=True, text=True)
            self.assertNotEqual(completed.returncode, 0)


if __name__ == '__main__':
    unittest.main()
