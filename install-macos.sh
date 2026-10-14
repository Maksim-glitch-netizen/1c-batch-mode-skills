#!/usr/bin/env bash
# Prepared for macos; tests were performed only on Windows.
set -euo pipefail
script_dir="$(CDPATH= cd -P -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python_command="${PYTHON:-python3}"
exec "$python_command" -B "$script_dir/install.py" --require-os macos "$@"
