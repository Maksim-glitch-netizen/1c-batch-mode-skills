#!/usr/bin/env python3
"""Portable offline validation entrypoint; release tests were performed only on Windows."""
from __future__ import annotations
import ast
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    subprocess.run([sys.executable, '-B', *map(str, args)], check=True, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})


def main():
    print('Release test evidence: Windows only. macOS and Linux have not been tested on their target OS.', flush=True)
    try:
        run(ROOT / 'scripts' / 'validate-package.py')
        run(ROOT / 'scripts' / 'update-manifests.py', '--check')
        for name in ('1c-add-new-object', '1c-configurator-batch-8-3-27'):
            run(ROOT / 'skills' / name / 'scripts' / 'validate-skill.py')
        for path in ROOT.rglob('*.py'):
            if not any(part in {'.git', '.agents', '.claude', '__pycache__'} for part in path.relative_to(ROOT).parts):
                ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
        run('-m', 'unittest', 'discover', '-s', ROOT / 'tests', '-p', 'test_*.py', '-v')
    except (OSError, SyntaxError, subprocess.CalledProcessError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 1
    print('OK: portable offline checks passed on the current host; this does not certify other OSes.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
