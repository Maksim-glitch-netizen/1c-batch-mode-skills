#!/usr/bin/env python3
"""Portable skill installer. Actual release tests were performed only on Windows."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
NAMES = ('1c-add-new-object', '1c-configurator-batch-8-3-27')
TEST_NOTICE = 'Tests were performed only on Windows. macOS and Linux variants have NOT been tested on their target OS.'


def current_os():
    if sys.platform == 'win32':
        return 'windows'
    if sys.platform == 'darwin':
        return 'macos'
    if sys.platform.startswith('linux'):
        return 'linux'
    return sys.platform


def is_link(path):
    return path.is_symlink() or getattr(path, 'is_junction', lambda: False)()


def payload(directory):
    if is_link(directory):
        raise ValueError(f'Skill directory is a link: {directory}')
    result = {}
    for path in sorted(directory.rglob('*')):
        if '__pycache__' in path.parts or path.suffix in {'.pyc', '.pyo'}:
            continue
        if is_link(path):
            raise ValueError(f'Link in skill contents: {path}')
        if path.is_file():
            result[path.relative_to(directory)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def validate_distribution():
    spec = importlib.util.spec_from_file_location('publication_validator', ROOT / 'scripts' / 'validate-package.py')
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.validate(ROOT)


def install(args):
    host = current_os()
    print(TEST_NOTICE)
    if args.require_os and args.require_os != host:
        raise ValueError(f'This launcher requires {args.require_os}; actual host is {host}. Use the matching launcher or install.py.')
    if host not in {'windows', 'macos', 'linux'}:
        raise ValueError(f'Unsupported installation host: {host}')
    profile = json.loads((ROOT / 'distribution-profile.json').read_text(encoding='utf-8'))
    target_os = profile['target_os']
    if target_os != 'universal' and target_os != host:
        raise ValueError(f'This archive targets {target_os}; actual host is {host}. Use the matching archive.')
    validate_distribution()
    if args.scope == 'project':
        if not args.project_path:
            raise ValueError('--project-path is required for project scope')
        base = Path(args.project_path).expanduser().absolute()
        if not base.is_dir():
            raise ValueError(f'Project directory does not exist: {base}')
    else:
        if args.project_path:
            raise ValueError('--project-path is valid only for project scope')
        base = Path.home()
    clients = ('codex', 'claude') if args.client == 'both' else (args.client,)
    plan = []
    for client in clients:
        skill_root = base / ('.agents' if client == 'codex' else '.claude') / 'skills'
        for ancestor in (skill_root.parent, skill_root):
            if is_link(ancestor):
                raise ValueError(f'Installation parent is a link; inspect it manually: {ancestor}')
        for name in NAMES:
            source = ROOT / 'skills' / name
            destination = skill_root / name
            if is_link(destination):
                raise ValueError(f'Destination is a link; inspect it manually: {destination}')
            same = False
            if destination.exists():
                same = destination.is_dir() and payload(source) == payload(destination)
                if not same:
                    raise ValueError(f'Existing skill differs; nothing copied: {destination}')
            plan.append((source, destination, same))
    # All destinations have been checked. Copy only into new directories, with exclusive files.
    for source, destination, same in plan:
        if same:
            print(f'Already installed: {destination}')
        elif args.dry_run:
            print(f'Would install: {destination}')
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.mkdir(exist_ok=False)
            for relative in payload(source):
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with (source / relative).open('rb') as source_file, target.open('xb') as target_file:
                    shutil.copyfileobj(source_file, target_file)
            if payload(source) != payload(destination):
                raise ValueError(f'Installed copy failed verification; inspect the new directory: {destination}')
            print(f'Installed: {destination}')
    print('1C and the five external scaffolding skills must be installed separately. See docs/dependencies.md.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', choices=('codex', 'claude', 'both'), required=True)
    parser.add_argument('--scope', choices=('user', 'project'), default='user')
    parser.add_argument('--project-path')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--require-os', choices=('windows', 'macos', 'linux'), help='Guard used by OS-specific launchers')
    args = parser.parse_args()
    try:
        install(args)
    except (OSError, ValueError, KeyError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
