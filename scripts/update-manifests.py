"""Build or check reproducible file inventories; never run 1C."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ('1c-add-new-object', '1c-configurator-batch-8-3-27')


def payload_files(base: Path):
    for path in sorted(base.rglob('*')):
        relative = path.relative_to(base)
        if any(part in {'.git', '.agents', '.claude', '__pycache__'} for part in relative.parts):
            continue
        if path.is_file() and path.suffix not in {'.pyc', '.pyo'}:
            yield path


def inventory(base: Path, excluded: set[str]):
    return {
        path.relative_to(base).as_posix(): {
            'bytes': len(path.read_bytes()),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        }
        for path in payload_files(base)
        if path.relative_to(base).as_posix() not in excluded
    }


def serialized(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def expected_manifests():
    result = []
    for name in SKILLS:
        skill = ROOT / 'skills' / name
        manifest = {
            'name': name,
            'version': '1.1.1' if name == SKILLS[0] else '2.3.1',
            'bundle_version': '0.2.1',
            'platform_scope': '1C:Enterprise 8.3.27; Windows tested; macOS/Linux prepared, not tested',
            'files': inventory(skill, {'manifest.json'}),
        }
        result.append((skill / 'manifest.json', manifest))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write', action='store_true')
    group.add_argument('--check', action='store_true')
    args = parser.parse_args()
    pending = expected_manifests()
    if args.write:
        for path, manifest in pending:
            path.write_text(serialized(manifest), encoding='utf-8', newline='\n')
        release = {'bundleVersion': '0.2.1', 'files': inventory(ROOT, {'release-manifest.json'})}
        (ROOT / 'release-manifest.json').write_text(serialized(release), encoding='utf-8', newline='\n')
        print('Updated skill manifests and release-manifest.json')
        return 0
    errors = []
    for path, expected in pending:
        if not path.is_file() or path.read_text(encoding='utf-8') != serialized(expected):
            errors.append(str(path.relative_to(ROOT)))
    release = {'bundleVersion': '0.2.1', 'files': inventory(ROOT, {'release-manifest.json'})}
    path = ROOT / 'release-manifest.json'
    if not path.is_file() or path.read_text(encoding='utf-8') != serialized(release):
        errors.append('release-manifest.json')
    if errors:
        print('Stale inventories: ' + ', '.join(errors))
        return 1
    print('OK: all inventories match the current files')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
