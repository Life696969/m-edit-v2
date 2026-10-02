import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def run_install(self, *args, env=None):
        return subprocess.run(['bash', str(ROOT / 'install.sh'), *args], check=True, capture_output=True, text=True, env=env)

    def test_global_all_hosts_and_uninstall(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = os.environ.copy()
            env['HOME'] = temporary
            self.run_install('--host', 'all', '--local-home', temporary, env=env)
            base = Path(temporary)
            for target in (
                '.claude/skills/m-edit/SKILL.md',
                '.codex/skills/m-edit/SKILL.md',
                '.agents/skills/m-edit/SKILL.md',
                '.claude/commands/m_edit.md',
                '.m-edit/current/shared/scripts/state.py',
            ):
                self.assertTrue((base / target).exists(), target)
            version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
            self.assertTrue((base / '.m-edit' / 'releases' / version / 'VERSION').exists())

            subprocess.run(['bash', str(ROOT / 'uninstall.sh'), '--host', 'all'], check=True, env=env, capture_output=True, text=True)
            self.assertFalse((base / '.claude/skills/m-edit').exists())
            self.assertFalse((base / '.codex/skills/m-edit').exists())
            self.assertTrue((base / '.m-edit/current').exists(), 'uninstall should preserve release data without --purge')

    def test_project_install_uses_agents_surface_for_codex(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary) / 'repo'
            project.mkdir()
            self.run_install('--host', 'codex', '--scope', 'project', '--project-dir', str(project))
            self.assertTrue((project / '.agents/skills/m-edit/SKILL.md').exists())
            self.assertTrue((project / '.m-edit-suite/current/shared/scripts/state.py').exists())

    def test_same_version_requires_force_and_force_creates_backup(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.run_install('--host', 'codex', '--local-home', temporary)
            second = subprocess.run([
                'bash', str(ROOT / 'install.sh'), '--host', 'codex', '--local-home', temporary,
            ], capture_output=True, text=True)
            self.assertNotEqual(second.returncode, 0)
            self.run_install('--host', 'codex', '--local-home', temporary, '--force')
            backups = list((Path(temporary) / '.m-edit/backups').glob('*/codex/m-edit'))
            self.assertTrue(backups)

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.run_install('--host', 'claude', '--local-home', temporary, '--dry-run')
            self.assertEqual(list(Path(temporary).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
