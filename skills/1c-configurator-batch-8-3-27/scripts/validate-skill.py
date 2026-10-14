#!/usr/bin/env python3
"""Validate the installed skill with Python only. Tests were performed only on Windows."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def validate(root):
    name = root.name
    allowed = {'1c-add-new-object', '1c-configurator-batch-8-3-27'}
    if name not in allowed:
        raise ValueError(f'Unexpected skill directory: {name}')
    text = (root / 'SKILL.md').read_text(encoding='utf-8-sig')
    header = re.match(r'\A---\n(.*?)\n---(?:\n|$)', text, re.S)
    if not header:
        raise ValueError('Invalid SKILL.md frontmatter')
    fields = dict(line.split(':', 1) for line in header[1].splitlines())
    if set(fields) != {'name', 'description'} or fields['name'].strip() != name:
        raise ValueError('Frontmatter name/fields do not match the skill')
    if not 1 <= len(fields['description'].strip()) <= 1024:
        raise ValueError('Invalid description length')
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    actual = {}
    for path in sorted(root.rglob('*')):
        if '__pycache__' in path.parts or path.suffix in {'.pyc', '.pyo'}:
            continue
        if path.is_symlink():
            raise ValueError(f'Unexpected symlink: {path}')
        if not path.is_file() or path.name == 'manifest.json' and path.parent == root:
            continue
        data = path.read_bytes()
        relative = path.relative_to(root).as_posix()
        actual[relative] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        body = data.decode('utf-8-sig')
        if path.suffix == '.py':
            ast.parse(body, filename=str(path))
        if path.suffix == '.md':
            body = re.sub(r'```.*?```', '', body, flags=re.S)
            for link in re.findall(r'\[[^\]]+\]\(([^)]+)\)', body):
                target = link.split('#')[0]
                if target and not re.match(r'^(https?://|mailto:)', target) and not (path.parent / target).exists():
                    raise ValueError(f'Broken link: {path}: {target}')
    if manifest.get('name') != name or manifest.get('files') != actual:
        raise ValueError('Skill manifest integrity or file set differs')
    if name == '1c-configurator-batch-8-3-27':
        rules = {
            '02-xml-dump.md': '`-listFile` нельзя использовать с другими параметрами этой команды',
            '03-xml-load.md': 'Если расширение подключено к хранилищу, полностью загрузить его нельзя',
            '04-repository-read-bind.md': 'нет документированного ключа `-update`',
            '05-repository-write.md': 'не должен генерировать содержимое такого файла по догадке',
            '06-update-db-cfg.md': '-SessionTerminate force',
            '08-results-errors.md': 'Не переносить код `101`',
            '11-merge-cfg.md': 'При неопределенном ответе изменяющий `MergeCfg` автоматически не повторять',
        }
        for reference, phrase in rules.items():
            if phrase not in (root / 'references' / reference).read_text(encoding='utf-8-sig'):
                raise ValueError(f'Missing critical rule: {reference}')
    print(f'OK: {name}, structure, links, Python syntax and manifest')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skill-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--no-tests', action='store_true')
    args = parser.parse_args()
    try:
        validate(args.skill_root)
        if args.skill_root.name == '1c-add-new-object' and not args.no_tests:
            subprocess.run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s',
                            str(args.skill_root / 'tests'), '-p', 'test_*.py', '-v'], check=True)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
