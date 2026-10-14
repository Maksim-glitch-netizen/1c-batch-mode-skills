#!/usr/bin/env python3
"""Search skill references with Python only. Tests were performed only on Windows."""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query')
    parser.add_argument('--regex', action='store_true')
    parser.add_argument('--include-source-register', action='store_true')
    parser.add_argument('--skill-root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        pattern = re.compile(args.query if args.regex else re.escape(args.query), re.I)
    except re.error as exc:
        print(f'Invalid regex: {exc}', file=sys.stderr)
        return 2
    found = False
    for path in sorted((args.skill_root / 'references').glob('*.md')):
        if not re.match(r'^(?:0[0-9]|11)-', path.name) and not (args.include_source_register and path.name == '10-source-register.md'):
            continue
        for line_number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
            if pattern.search(line):
                print(f'{path.relative_to(args.skill_root).as_posix()}:{line_number}: {line.strip()}')
                found = True
    return 0 if found else 1


if __name__ == '__main__':
    # CLI output stays UTF-8 when Windows redirects streams through a legacy code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='backslashreplace')
    raise SystemExit(main())
