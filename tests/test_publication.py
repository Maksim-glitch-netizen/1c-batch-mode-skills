from __future__ import annotations
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SHELL = os.environ.get('SKILLS_TEST_POWERSHELL') or shutil.which('pwsh') or shutil.which('powershell')
NAMES = ('1c-add-new-object', '1c-configurator-batch-8-3-27')


def run_ps(script, *args):
    if not SHELL:
        raise RuntimeError('PowerShell is required for installation tests')
    return subprocess.run([SHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script), *map(str, args)],
                          capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=90)


def snapshot(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob('*') if p.is_file()}


@unittest.skipUnless(os.name == 'nt' and SHELL, 'Windows PowerShell installation tests')
class InstallationTests(unittest.TestCase):
    def test_both_clients_unicode_space_path_and_repeat(self):
        with tempfile.TemporaryDirectory(prefix='1c skills ') as temp:
            project = Path(temp) / 'Проект с пробелами'
            project.mkdir()
            result = run_ps(ROOT / 'install.ps1', '-Client', 'Both', '-Scope', 'Project', '-ProjectPath', project)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for directory in ('.agents', '.claude'):
                for name in NAMES:
                    self.assertEqual(snapshot(ROOT / 'skills' / name), snapshot(project / directory / 'skills' / name))
            before = snapshot(project)
            repeated = run_ps(ROOT / 'install.ps1', '-Client', 'Both', '-Scope', 'Project', '-ProjectPath', project)
            self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
            self.assertEqual(snapshot(project), before)
            # Both installed skill validators must run without the distribution root.
            for name in NAMES:
                skill = project / '.claude' / 'skills' / name
                checked = run_ps(skill / 'scripts' / 'validate-skill.ps1', '-SkillRoot', skill)
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_conflict_in_last_target_prevents_all_copying(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            conflict = project / '.claude' / 'skills' / NAMES[-1]
            conflict.mkdir(parents=True)
            (conflict / 'keep.txt').write_text('user changes', encoding='utf-8')
            before = snapshot(project)
            result = run_ps(ROOT / 'install.ps1', '-Client', 'Both', '-Scope', 'Project', '-ProjectPath', project)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(snapshot(project), before)
            self.assertFalse((project / '.agents').exists())

    def test_whatif_does_not_create_client_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            result = run_ps(ROOT / 'install.ps1', '-Client', 'Both', '-Scope', 'Project', '-ProjectPath', project, '-WhatIf')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(list(project.iterdir()), [])

    def test_project_scope_requires_explicit_existing_path(self):
        result = run_ps(ROOT / 'install.ps1', '-Client', 'Codex', '-Scope', 'Project')
        self.assertNotEqual(result.returncode, 0)


class PublicationChecks(unittest.TestCase):

    def test_git_checkout_preserves_manifest_hashes_with_autocrlf(self):
        git = shutil.which('git')
        self.assertIsNotNone(git, 'Git is required for checkout portability tests')
        with tempfile.TemporaryDirectory(prefix='1c git ') as temp:
            source = Path(temp) / 'source'
            checkout = Path(temp) / 'checkout'
            shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('.git', '.agents', '.claude', '__pycache__'))
            checkout.mkdir()
            for args in (['init', '-q'], ['add', '--', '.'],
                         ['checkout-index', '--all', '--prefix=' + checkout.as_posix() + '/']):
                result = subprocess.run([git, '-C', str(source), '-c', 'core.autocrlf=true', *args],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            checked = subprocess.run([sys.executable, '-B', str(checkout / 'scripts' / 'validate-package.py')],
                                     capture_output=True, text=True, timeout=30)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    @unittest.skipUnless(os.name == 'nt' and SHELL, 'Windows PowerShell search test')
    def test_search_includes_merge_reference(self):
        search = ROOT / 'skills' / NAMES[1] / 'scripts' / 'search-docs.ps1'
        result = run_ps(search, '-Query', 'ConfigurationsNotRelated')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('11-merge-cfg.md', result.stdout)

    def test_inventory_rejects_changed_payload(self):
        script = ROOT / 'scripts' / 'validate-package.py'
        spec = importlib.util.spec_from_file_location('package_validator', script)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            skill = Path(temp) / NAMES[0]
            shutil.copytree(ROOT / 'skills' / NAMES[0], skill)
            (skill / 'SKILL.md').write_text('tampered', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Integrity mismatch'):
                module.check_manifest(skill, skill / 'manifest.json', NAMES[0])


if __name__ == '__main__':
    unittest.main()
