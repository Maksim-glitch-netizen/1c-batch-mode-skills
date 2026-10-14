"""Offline structure, portability, and integrity checks for the publication bundle."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ('1c-add-new-object', '1c-configurator-batch-8-3-27')


def public_files(root):
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in {'.git', '.agents', '.claude', '__pycache__'} for part in relative.parts):
            continue
        if path.is_file() and path.suffix not in {'.pyc', '.pyo'}:
            yield path


def check_manifest(base, manifest_path, expected_name=None):
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if expected_name and manifest.get('name') != expected_name:
        raise ValueError(f'Wrong manifest name: {manifest_path}')
    files = manifest.get('files')
    if not isinstance(files, dict) or not files:
        raise ValueError(f'Empty file inventory: {manifest_path}')
    actual = {p.relative_to(base).as_posix() for p in public_files(base)}
    actual.discard(manifest_path.relative_to(base).as_posix())
    if set(files) != actual:
        raise ValueError(f'Inventory file set differs: {manifest_path}')
    for relative, expected in files.items():
        path = base / relative
        try:
            path.resolve().relative_to(base.resolve())
        except ValueError as exc:
            raise ValueError(f'Inventory escapes root: {relative}') from exc
        data = path.read_bytes()
        if len(data) != expected['bytes'] or hashlib.sha256(data).hexdigest() != expected['sha256']:
            raise ValueError(f'Integrity mismatch: {path}')


def validate(root):
    required = ('distribution-profile.json', 'install.py', 'install-macos.sh', 'install-linux.sh', 'platforms.json',
                'scripts/validate.py', 'README.md', 'LICENSE', 'THIRD_PARTY.md', 'install.ps1', 'dependencies.json',
                'docs/dependencies.md', 'docs/validation.md', 'docs/publishing.md',
                'scripts/validate.ps1', 'scripts/update-manifests.py', 'release-manifest.json')
    for relative in required:
        if not (root / relative).is_file():
            raise ValueError(f'Missing file: {relative}')
    for name in SKILLS:
        skill = root / 'skills' / name
        text = (skill / 'SKILL.md').read_text(encoding='utf-8-sig')
        match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', text, re.S)
        if not match:
            raise ValueError(f'Invalid frontmatter: {name}')
        fields = dict(line.split(':', 1) for line in match[1].splitlines())
        if set(fields) != {'name', 'description'} or fields['name'].strip() != name:
            raise ValueError(f'Unexpected frontmatter: {name}')
        if not 1 <= len(fields['description'].strip()) <= 1024:
            raise ValueError(f'Invalid description: {name}')
        check_manifest(skill, skill / 'manifest.json', name)
    profile = json.loads((root / 'distribution-profile.json').read_text(encoding='utf-8'))
    if profile.get('target_os') not in {'universal', 'windows', 'macos', 'linux'} or profile.get('test_evidence') != 'windows_only':
        raise ValueError('Invalid distribution profile or unsupported native-test claim')
    status = json.loads((root / 'platforms.json').read_text(encoding='utf-8'))
    if status.get('tested_operating_systems') != ['windows']:
        raise ValueError('This release has test evidence only for Windows')
    for os_name in ('macos', 'linux'):
        if status['variants'][os_name]['status'] != 'prepared_not_tested':
            raise ValueError('macOS/Linux native test evidence has not been supplied')
    private_profile = re.compile(r'[A-Za-z]:\\Users\\[A-Za-z0-9_.-]+\\', re.I)
    for path in public_files(root):
        if path.is_symlink():
            raise ValueError(f'Unexpected symlink in distribution: {path}')
        if path.suffix.lower() in {'.cf', '.cfe', '.dt', '.epf', '.erf', '.1cd', '.zip', '.log', '.result'}:
            raise ValueError(f'Runtime artifact in distribution: {path}')
        data = path.read_bytes()
        text = data.decode('utf-8-sig')
        if b'\r\n' in data:
            raise ValueError(f'Publication text must use LF to preserve Git hashes: {path}')
        if path.suffix == '.sh' and (b'\r' in data or not data.startswith(b'#!/usr/bin/env bash\n')):
            raise ValueError(f'Shell launcher must have a shebang and LF: {path}')
        if path.suffix == '.ps1' and not data.startswith(b'\xef\xbb\xbf'):
            raise ValueError(f'PowerShell requires UTF-8 BOM for 5.1: {path}')
        if private_profile.search(text):
            raise ValueError(f'Private environment reference: {path}')
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----', text):
            raise ValueError(f'Private key marker: {path}')
        if path.suffix == '.md':
            outside_code = re.sub(r'```.*?```', '', text, flags=re.S)
            for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', outside_code):
                if re.match(r'^(?:https?://|mailto:|#)', link):
                    continue
                target = unquote(link.split('#')[0]).strip('<>')
                if target and not (path.parent / target).exists():
                    raise ValueError(f'Broken relative link in {path}: {link}')
    check_manifest(root, root / 'release-manifest.json')
    print('OK: two portable skills, links, UTF-8, and all file hashes')


def main():
    try:
        validate(ROOT)
    except (OSError, ValueError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
