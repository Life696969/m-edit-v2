import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPTIONS = ROOT / 'shared/scripts/captions.py'


class CaptionTests(unittest.TestCase):
    def test_srt_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'captions.srt'
            source.write_text('1\n00:00:00,000 --> 00:00:01,000\nHello world\n\n2\n00:00:01,100 --> 00:00:02,500\nSecond line\n', encoding='utf-8')
            canonical = root / 'captions.json'
            exported = root / 'roundtrip.srt'
            subprocess.run([sys.executable, str(CAPTIONS), 'import', '--input', str(source), '--output', str(canonical)], check=True, capture_output=True, text=True)
            payload = json.loads(canonical.read_text(encoding='utf-8'))
            self.assertEqual(len(payload['segments']), 2)
            subprocess.run([sys.executable, str(CAPTIONS), 'validate', '--input', str(canonical)], check=True, capture_output=True, text=True)
            subprocess.run([sys.executable, str(CAPTIONS), 'export-srt', '--input', str(canonical), '--output', str(exported)], check=True, capture_output=True, text=True)
            self.assertIn('Hello world', exported.read_text(encoding='utf-8'))

    def test_webvtt_timestamp_without_hours_is_supported(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'captions.vtt'
            source.write_text('WEBVTT\n\n00:01.000 --> 00:02.250 align:center\nHello VTT\n', encoding='utf-8')
            output = root / 'captions.json'
            subprocess.run([sys.executable, str(CAPTIONS), 'import', '--input', str(source), '--output', str(output)], check=True, capture_output=True, text=True)
            segment = json.loads(output.read_text(encoding='utf-8'))['segments'][0]
            self.assertEqual(segment['start_ms'], 1000)
            self.assertEqual(segment['end_ms'], 2250)

    def test_invalid_timestamps_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'bad.json'
            path.write_text(json.dumps({'segments': [{'start_ms': 1000, 'end_ms': 500, 'text': 'bad'}]}), encoding='utf-8')
            result = subprocess.run([sys.executable, str(CAPTIONS), 'validate', '--input', str(path)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)


    def test_chunking_preserves_words_and_full_time_range(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'canonical.json'
            source.write_text(json.dumps({
                'schema_version': 1,
                'segments': [{'start_ms': 0, 'end_ms': 4000, 'text': 'one two three four five six seven'}]
            }), encoding='utf-8')
            output = root / 'chunked.json'
            subprocess.run([
                sys.executable, str(CAPTIONS), 'chunk', '--input', str(source), '--output', str(output),
                '--max-words', '3', '--max-chars', '20',
            ], check=True, capture_output=True, text=True)
            payload = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(' '.join(item['text'] for item in payload['segments']), 'one two three four five six seven')
            self.assertEqual(payload['segments'][0]['start_ms'], 0)
            self.assertEqual(payload['segments'][-1]['end_ms'], 4000)
            self.assertTrue(all(len(item['text'].split()) <= 3 for item in payload['segments']))

    def test_word_timestamp_chunking_uses_real_boundaries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'canonical.json'
            words = [
                {'start_ms': 0, 'end_ms': 400, 'text': 'one'},
                {'start_ms': 500, 'end_ms': 900, 'text': 'two'},
                {'start_ms': 1000, 'end_ms': 1400, 'text': 'three'},
            ]
            source.write_text(json.dumps({
                'schema_version': 1,
                'segments': [{'start_ms': 0, 'end_ms': 1400, 'text': 'one two three', 'words': words}]
            }), encoding='utf-8')
            output = root / 'chunked.json'
            subprocess.run([
                sys.executable, str(CAPTIONS), 'chunk', '--input', str(source), '--output', str(output), '--max-words', '2'
            ], check=True, capture_output=True, text=True)
            segments = json.loads(output.read_text(encoding='utf-8'))['segments']
            self.assertEqual(segments[0], {'start_ms': 0, 'end_ms': 900, 'text': 'one two'})
            self.assertEqual(segments[1], {'start_ms': 1000, 'end_ms': 1400, 'text': 'three'})


if __name__ == '__main__':
    unittest.main()
