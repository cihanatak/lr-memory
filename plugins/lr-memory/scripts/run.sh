#!/bin/sh
# Runs lr-memory with the first Python 3.9 or newer on PATH: python3, python, then the Windows launcher py.
# Claude Code runs hook commands with sh on macOS and Linux, and with Git Bash on Windows.
here=$(dirname "$0")
for p in python3 python py; do
  if "$p" -c 'import sys; sys.exit(sys.version_info < (3, 9))' </dev/null >/dev/null 2>&1; then
    exec "$p" "$here/lrm.py" "$@"
  fi
done
echo "lr-memory: no Python 3.9 or newer found on PATH (tried python3, python, py)" >&2
exit 1
