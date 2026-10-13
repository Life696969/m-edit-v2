"""Clean final delivery (`m-edit deliver-clean`): no metadata or encoder traces, single-encode audio, two check rounds."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'shared' / 'scripts'
sys.path.insert(0, str(SCRIPTS))

try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False

HAVE_FFMPEG = bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))


def ff(*args):
    subprocess.run(['ffmpeg', '-y', '-v', 'error', *map(str, args)], check=True)


SPEECHLIKE = "aevalsrc='{amp}*sin(2*PI*220*t)*(0.55+0.45*sin(2*PI*3*t))+{amp}*0.25*(random(0)-0.5)':s=48000:d={d}"


def make_dirty_render(path: Path, seconds=2.0, audio="anoisesrc=color=pink:amplitude=0.2:sample_rate=48000", rate='30'):
    """What a Remotion/FFmpeg render looks like: x264 + FFmpeg AAC, encoder tags, a text comment, default handlers."""
    ff('-f', 'lavfi', '-i', f'testsrc2=size=320x568:rate={rate}:duration={seconds}', '-f', 'lavfi', '-i', f'{audio}:duration={seconds}',
       '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-metadata', 'comment=Made with Remotion',
       '-shortest', path)


def make_project(folder: Path, seconds=2.0, voice_amp=0.5):
    """A one-clip m-edit project: a recording with a speech-like voice, a music bed and one effect cue."""
    public = folder / 'public'
    (folder / '.m-edit').mkdir(parents=True)
    public.mkdir()
    voice = SPEECHLIKE.format(amp=voice_amp, d=seconds)
    ff('-f', 'lavfi', '-i', f'testsrc2=size=320x568:rate=30:duration={seconds}', '-f', 'lavfi', '-i', voice,
       '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '256k', '-shortest', public / 'take1.mp4')
    ff('-f', 'lavfi', '-i', f'anoisesrc=color=pink:amplitude=0.3:sample_rate=48000:duration={seconds + 4}', '-ac', '2',
       '-c:a', 'pcm_s16le', public / 'bed.wav')
    ff('-f', 'lavfi', '-i', 'sine=frequency=1200:sample_rate=48000:duration=0.25', '-af', 'afade=t=out:st=0.05:d=0.2',
       '-c:a', 'pcm_s16le', public / 'pop.wav')
    edit = {
        'schema_version': 1,
        'canvas': {'width': 320, 'height': 568, 'fps': 30},
        'assets': [
            {'id': 'bed', 'path': 'public/bed.wav', 'public_path': 'bed.wav', 'kind': 'music', 'source': 'test tone', 'license': 'CC0'},
            {'id': 'pop', 'path': 'public/pop.wav', 'public_path': 'pop.wav', 'kind': 'sfx', 'source': 'test tone', 'license': 'CC0'},
        ],
        'music': {'asset': 'bed', 'volume': 0.08},
        'clips': [{'id': 'clip1.mp4', 'duration': seconds, 'src': {'preview': 'take1.mp4', 'final': 'take1.mp4'},
                   'cues': [{'at': 0.5, 'asset': 'pop', 'volume': 0.2}]}],
    }
    (folder / '.m-edit' / 'edit.json').write_text(json.dumps(edit), encoding='utf-8')
    render = folder / 'render.mp4'
    make_dirty_render(render, seconds)
    return public, render


@unittest.skipUnless(HAVE_FFMPEG and HAVE_NUMPY, 'FFmpeg and numpy required')
class CleanDeliveryTests(unittest.TestCase):
    def setUp(self):
        import deliver_clean
        self.dc = deliver_clean
        self.tmp = Path(tempfile.mkdtemp(prefix='m-edit-test-'))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dirty_render_fails_metadata_and_scrub_passes_with_identical_samples(self):
        dirty = self.tmp / 'dirty.mp4'
        make_dirty_render(dirty)
        fails, _ = self.dc.check_metadata(dirty)
        joined = ' '.join(fails)
        for expected in ('container tags', 'forbidden boxes', 'ftyp brand', 'trace strings', 'SEI user data'):
            self.assertIn(expected, joined)
        muxed, clean = self.tmp / 'muxed.mp4', self.tmp / 'clean.mp4'
        self.dc.run(['ffmpeg', '-y', '-v', 'error', '-i', str(dirty), '-map', '0', '-c:v', 'copy',
                     '-bsf:v', 'filter_units=remove_types=6', *self.dc.AAC, *self.dc.MUX_COMMON, str(muxed)])
        self.dc.mp4_scrub.scrub(muxed, clean, *self.dc.vui_codes(muxed))
        fails, _ = self.dc.check_metadata(clean)
        self.assertEqual(fails, [])
        self.assertEqual(self.dc.video_md5(clean), self.dc.video_md5(muxed))       # decode hashes unchanged by the scrub
        audio = lambda p: subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-map', '0:a', '-f', 'md5', '-'],
                                         capture_output=True, text=True, check=True).stdout
        self.assertEqual(audio(clean), audio(muxed))

    def test_deliver_passes_both_rounds_with_zero_lag_and_a_voice_safe_level(self):
        public, render = make_project(self.tmp)
        out = self.tmp / 'finals' / 'clip1_final.mp4'
        proc = subprocess.run([sys.executable, str(SCRIPTS / 'deliver_clean.py'), 'deliver', '--project', str(self.tmp),
                               '--clip', 'clip1.mp4', '--render', str(render), '--public', str(public), '--output', str(out)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.loads((self.tmp / '.m-edit' / 'deliveries' / 'clip1.mp4' / 'delivery_check.json').read_text(encoding='utf-8'))
        self.assertTrue(report['passed'])
        self.assertTrue(report['round1']['passed'] and report['round2']['passed'])
        self.assertEqual(report['final_sha256'], self.dc.sha256(out))
        info = report['round2']['info']
        self.assertEqual(info['lag_vs_intended'], 0)
        self.assertLessEqual(info['limiter_gr_db'], self.dc.MAX_LIMITER_GR_DB)
        self.assertLessEqual(info['voice_peak_dbfs'], self.dc.db(self.dc.LIMIT) - self.dc.VOICE_MARGIN_DB + 0.01)
        self.assertEqual(info['voice_processing'], 'gain only')
        self.assertEqual(info.get('video'), 'bit-exact copy of the render')
        self.assertIn(report['round1']['info']['aac_target'], ('320k', *self.dc.AAC_RETRY_TARGETS))
        self.assertGreaterEqual(info['snr_vs_intended_db'], self.dc.MIN_SNR_DB)
        self.assertFalse((self.tmp / '.m-edit' / 'deliveries' / 'clip1.mp4' / 'staging').exists())

    def test_standard_loudness_is_quieter_than_voice_safe_and_never_hotter(self):
        public, _ = make_project(self.tmp)
        edit = self.tmp / '.m-edit' / 'edit.json'
        safe = self.dc.Reel(edit, public, 'voice-safe').gain()
        standard = self.dc.Reel(edit, public, 'standard').gain()
        self.assertLess(standard['gain_db'], safe['gain_db'])
        ceiling = self.dc.db(self.dc.LIMIT) - self.dc.VOICE_MARGIN_DB
        for gain in (safe, standard):
            self.assertLessEqual(max(t['peak_dbfs'] for t in gain['takes']) + gain['gain_db'], ceiling + 1e-6)

    def test_an_undershooting_aac_encode_is_redone_from_the_lossless_mix(self):
        rates = iter([298_000, 321_000])
        calls = []
        with mock.patch.object(self.dc, 'run', side_effect=lambda args, **kw: calls.append(args)), \
             mock.patch.object(self.dc, 'probe', side_effect=lambda *a, **k: {'streams': [{'bit_rate': next(rates)}]}):
            kept = self.dc.mux_aac(Path('v.mp4'), Path('mix.wav'), Path('out.mp4'))
        self.assertEqual(kept, '352k')
        self.assertEqual(len(calls), 2)
        self.assertTrue(all('mix.wav' in call for call in calls))                  # both encodes start from the lossless mix

    def test_dual_mono_voice_only_mix_is_warned_not_refused(self):
        composed, mix, out = self.tmp / 'composed.mp4', self.tmp / 'mono.wav', self.tmp / 'mono_final.mp4'
        make_dirty_render(composed)
        ff('-f', 'lavfi', '-i', SPEECHLIKE.format(amp=0.4, d=2), '-ac', '2', '-c:a', 'pcm_f32le', mix)   # identical channels
        proc = subprocess.run([sys.executable, str(SCRIPTS / 'deliver_clean.py'), 'clean', '--input', str(composed),
                               '--audio', str(mix), '--output', str(out)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.loads((self.tmp / 'mono_final.delivery_check.json').read_text(encoding='utf-8'))
        self.assertEqual(report['round1']['info']['aac_target'], self.dc.AAC_RETRY_TARGETS[-1])   # retried to the top
        self.assertTrue(report['round2']['info'].get('warnings'))

    def test_a_phone_frame_rate_keeps_every_frame(self):
        composed, mix, out = self.tmp / 'phone.mp4', self.tmp / 'phone.wav', self.tmp / 'phone_final.mp4'
        make_dirty_render(composed, seconds=3.0, rate='359/12')                   # a phone's ~29.92 fps
        ff('-f', 'lavfi', '-i', SPEECHLIKE.format(amp=0.4, d=3), '-af', 'aformat=channel_layouts=stereo', '-c:a', 'pcm_f32le', mix)
        proc = subprocess.run([sys.executable, str(SCRIPTS / 'deliver_clean.py'), 'clean', '--input', str(composed),
                               '--audio', str(mix), '--output', str(out)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.dc.frames_fps(out)[0], self.dc.frames_fps(composed)[0])

    def test_clean_refuses_to_reencode_lossy_audio(self):
        dirty = self.tmp / 'composed.mp4'
        make_dirty_render(dirty)
        proc = subprocess.run([sys.executable, str(SCRIPTS / 'deliver_clean.py'), 'clean', '--input', str(dirty),
                               '--output', str(self.tmp / 'final.mp4')], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('lossless mix', proc.stderr)
        self.assertFalse((self.tmp / 'final.mp4').exists())

    def test_clean_with_a_lossless_mix_passes(self):
        composed, mix = self.tmp / 'composed.mp4', self.tmp / 'mix.wav'
        make_dirty_render(composed)
        ff('-f', 'lavfi', '-i', SPEECHLIKE.format(amp=0.4, d=2), '-ac', '2', '-c:a', 'pcm_f32le', mix)
        out = self.tmp / 'final.mp4'
        proc = subprocess.run([sys.executable, str(SCRIPTS / 'deliver_clean.py'), 'clean', '--input', str(composed),
                               '--audio', str(mix), '--output', str(out)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.loads((self.tmp / 'final.delivery_check.json').read_text(encoding='utf-8'))
        self.assertTrue(report['round1']['passed'] and report['round2']['passed'])
        self.assertEqual(report['round2']['info']['lag_vs_intended'], 0)


class DeliveryRecordTests(unittest.TestCase):
    """mark-reel-final accepts only a passing two-round report for exactly this final, unless the user opted out."""

    def setUp(self):
        import director
        self.director = director
        self.tmp = Path(tempfile.mkdtemp(prefix='m-edit-test-'))
        self.final = self.tmp / 'clip1_final.mp4'
        self.final.write_bytes(b'final bytes')

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def report(self, **overrides):
        from common import sha256
        data = {'passed': True, 'clip': 'clip1.mp4', 'final_sha256': sha256(self.final),
                'round1': {'passed': True}, 'round2': {'passed': True}}
        data.update(overrides)
        path = self.tmp / 'delivery_check.json'
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def test_valid_report_is_accepted(self):
        self.director.validate_delivery(self.final, self.report(), 'clip1.mp4')

    def test_bad_reports_are_refused(self):
        for overrides in ({'passed': False}, {'round2': {'passed': False}}, {'round1': None},
                          {'clip': 'clip2.mp4'}, {'final_sha256': '0' * 64}):
            with self.subTest(overrides=overrides), self.assertRaises(SystemExit):
                self.director.validate_delivery(self.final, self.report(**overrides), 'clip1.mp4')

    def test_clean_delivery_is_on_unless_the_user_opted_out(self):
        self.assertTrue(self.director.delivery_policy({}))
        self.assertTrue(self.director.delivery_policy({'delivery': {'loudness': 'standard'}}))
        self.assertFalse(self.director.delivery_policy({'delivery': {'clean': False}}))


if __name__ == '__main__':
    unittest.main()
