from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('1c-add-new-object', '1c-configurator-batch-8-3-27')


def run_python(script, *args, io_encoding=None):
    env = dict(os.environ)
    if io_encoding:
        env["PYTHONIOENCODING"] = io_encoding
    return subprocess.run([sys.executable, '-B', str(script), *map(str, args)],
                          capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90, env=env)


def snapshot(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


class PortableTests(unittest.TestCase):
    def test_install_repeat_and_installed_python_validators(self):
        with tempfile.TemporaryDirectory(prefix='skills python ') as temp:
            project = Path(temp) / 'Проект с пробелами'
            project.mkdir()
            args = ('--client', 'both', '--scope', 'project', '--project-path', project)
            result = run_python(ROOT / 'install.py', *args, io_encoding='cp1252')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('only on Windows', result.stdout)
            self.assertIn(project.name, result.stdout)
            for client_root in ('.agents', '.claude'):
                for name in NAMES:
                    installed = project / client_root / 'skills' / name
                    self.assertEqual(snapshot(installed), snapshot(ROOT / 'skills' / name))
            installed = project / '.claude' / 'skills'
            for name in NAMES:
                checked = run_python(installed / name / 'scripts' / 'validate-skill.py')
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            before = snapshot(project)
            repeated = run_python(ROOT / 'install.py', *args, io_encoding='cp1252')
            self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
            self.assertEqual(snapshot(project), before)

    def test_conflict_preflight_checks_all_destinations(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            conflicting = project / '.claude' / 'skills' / NAMES[-1]
            conflicting.mkdir(parents=True)
            (conflicting / 'keep.txt').write_text('user changes', encoding='utf-8')
            before = snapshot(project)
            result = run_python(ROOT / 'install.py', '--client', 'both', '--scope', 'project', '--project-path', project)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(snapshot(project), before)
            self.assertFalse((project / '.agents').exists())

    def test_dry_run_does_not_write(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run_python(ROOT / 'install.py', '--client', 'both', '--scope', 'project', '--project-path', temp, '--dry-run')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_missing_project_is_rejected(self):
        result = run_python(ROOT / 'install.py', '--client', 'codex', '--scope', 'project')
        self.assertNotEqual(result.returncode, 0)

    def test_codex_only_does_not_install_claude(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            result = run_python(ROOT / 'install.py', '--client', 'codex', '--scope', 'project', '--project-path', project)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((project / '.agents' / 'skills' / NAMES[0]).is_dir())
            self.assertFalse((project / '.claude').exists())

    def test_foreign_os_launcher_guard(self):
        other_os = 'linux' if sys.platform != 'linux' else 'macos'
        result = run_python(ROOT / 'install.py', '--client', 'both', '--require-os', other_os, '--dry-run')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('actual host is', result.stderr)

    def test_python_search_covers_merge_and_invalid_regex(self):
        script = ROOT / 'skills' / NAMES[-1] / 'scripts' / 'search-docs.py'
        result = run_python(script, 'ConfigurationsNotRelated', io_encoding='cp1252')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('11-merge-cfg.md', result.stdout)
        invalid = run_python(script, '[', '--regex')
        self.assertEqual(invalid.returncode, 2)

    def test_release_archives_keep_untested_status_and_shell_permissions(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run_python(ROOT / 'scripts' / 'build-releases.py', '--output-dir', temp)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            metadata = json.loads((Path(temp) / 'release-artifacts.json').read_text(encoding='utf-8'))
            self.assertEqual(metadata['tested_operating_systems'], ['windows'])
            for item in metadata['artifacts']:
                if item['target_os'] in ('macos', 'linux'):
                    self.assertFalse(item['native_target_os_tested'])
                    self.assertEqual(item['testing_status'], 'prepared_not_tested')
                    with tarfile.open(Path(temp) / item['file'], 'r:gz') as archive:
                        shell = next(m for m in archive.getmembers() if m.name.endswith('/install-'+item['target_os']+'.sh'))
                        self.assertEqual(shell.mode, 0o755)
                        profile_member = next(m for m in archive.getmembers() if m.name.endswith('/distribution-profile.json'))
                        profile = json.loads(archive.extractfile(profile_member).read())
                        self.assertEqual(profile['target_os'], item['target_os'])
                        self.assertEqual(profile['test_evidence'], 'windows_only')
                        unpacked = Path(temp) / ('unpacked-' + item['target_os'])
                        unpacked.mkdir()
                        # Read known regular archive members without trusting extraction paths.
                        for member in archive.getmembers():
                            relative = Path(*Path(member.name).parts[1:])
                            destination = unpacked / relative
                            destination.resolve().relative_to(unpacked.resolve())
                            destination.parent.mkdir(parents=True, exist_ok=True)
                            destination.write_bytes(archive.extractfile(member).read())
                        checked = run_python(unpacked / 'scripts' / 'validate-package.py')
                        self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
                        host_os = 'windows' if os.name == 'nt' else ('macos' if sys.platform == 'darwin' else 'linux')
                        if item['target_os'] != host_os:
                            guarded = run_python(unpacked / 'install.py', '--client', 'both', '--dry-run')
                            self.assertNotEqual(guarded.returncode, 0)
                            self.assertIn('This archive targets', guarded.stderr)
            repeated = run_python(ROOT / 'scripts' / 'build-releases.py', '--output-dir', temp)
            self.assertNotEqual(repeated.returncode, 0)

    @unittest.skipUnless(os.environ.get('SKILLS_TEST_BASH'), 'Bash syntax check not configured on this host')
    def test_shell_launcher_syntax_on_current_host(self):
        for name in ('install-macos.sh', 'install-linux.sh'):
            result = subprocess.run([os.environ['SKILLS_TEST_BASH'], '-n', str(ROOT / name)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
