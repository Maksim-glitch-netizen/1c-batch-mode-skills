#!/usr/bin/env python3
"""Build Windows/macOS/Linux artifacts. Actual tests were performed only on Windows."""
from __future__ import annotations
import argparse
import copy
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(output):
    spec = importlib.util.spec_from_file_location('release_validator', ROOT / 'scripts' / 'validate-package.py')
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.validate(ROOT)
    output = output.resolve()
    try:
        output.relative_to(ROOT)
    except ValueError:
        pass
    else:
        raise ValueError('Release output must be outside the source repository')
    manifest = json.loads((ROOT / 'release-manifest.json').read_text(encoding='utf-8'))
    version = manifest['bundleVersion']
    files = sorted(set(manifest['files']) | {'release-manifest.json'})
    prefix = f'1c-agent-skills-{version}/'
    names = {os_name: f'1c-agent-skills-{version}-{os_name}' + ('.zip' if os_name == 'windows' else '.tar.gz')
             for os_name in ('windows', 'macos', 'linux')}
    planned = [output / name for name in names.values()] + [output / 'release-artifacts.json', output / 'SHA256SUMS']
    if any(path.exists() for path in planned):
        raise ValueError('Release artifacts already exist; choose another output directory')
    output.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for os_name, name in names.items():
        payload = {relative: (ROOT / relative).read_bytes() for relative in files}
        profile = {'target_os': os_name, 'test_evidence': 'windows_only'}
        payload['distribution-profile.json'] = (json.dumps(profile, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
        variant_manifest = copy.deepcopy(manifest)
        profile_bytes = payload['distribution-profile.json']
        variant_manifest['files']['distribution-profile.json'] = {'bytes': len(profile_bytes), 'sha256': hashlib.sha256(profile_bytes).hexdigest()}
        payload['release-manifest.json'] = (json.dumps(variant_manifest, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
        target = output / name
        if os_name == 'windows':
            with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
                for relative in files:
                    info = zipfile.ZipInfo(prefix + relative)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    mode = 0o755 if relative in {'install-macos.sh', 'install-linux.sh'} else 0o644
                    info.external_attr = (0o100000 | mode) << 16
                    archive.writestr(info, payload[relative])
            with zipfile.ZipFile(target) as archive:
                if archive.testzip() is not None:
                    raise ValueError(f'Invalid ZIP CRC: {target}')
                assert len(archive.namelist()) == len(files)
                for relative in files:
                    assert archive.read(prefix + relative) == payload[relative]
        else:
            with target.open('xb') as stream, gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode='w') as archive:
                    for relative in files:
                        data = payload[relative]
                        info = tarfile.TarInfo(prefix + relative)
                        info.size = len(data)
                        info.mode = 0o755 if relative in {'install-macos.sh', 'install-linux.sh'} else 0o644
                        info.mtime = 0
                        archive.addfile(info, io.BytesIO(data))
            with tarfile.open(target, 'r:gz') as archive:
                assert len(archive.getmembers()) == len(files)
                for relative in files:
                    member = archive.getmember(prefix + relative)
                    assert member.isfile()
                    assert archive.extractfile(member).read() == payload[relative]
        artifacts.append({'file': name, 'target_os': os_name,
                          'testing_status': 'tested_on_windows' if os_name == 'windows' else 'prepared_not_tested',
                          'native_target_os_tested': os_name == 'windows',
                          'sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
    metadata = {'bundleVersion': version, 'tested_operating_systems': ['windows'],
                'notice': 'All actual tests were performed only on Windows. macOS and Linux have not been tested on their target OS.',
                'files_per_archive': len(files), 'artifacts': artifacts}
    (output / 'release-artifacts.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (output / 'SHA256SUMS').write_text(''.join(item['sha256']+'  '+item['file']+'\n' for item in artifacts), encoding='ascii')
    print(json.dumps(metadata, ensure_ascii=False))
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        build(args.output_dir)
    except (OSError, ValueError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')


if __name__ == '__main__':
    main()
