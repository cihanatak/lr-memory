#!/bin/sh
# Runs the mind panel with the first Python 3.9 or newer on PATH: python3, python, then the Windows launcher py.
here=$(dirname "$0")
for p in python3 python py; do
  if "$p" -c 'import sys; sys.exit(sys.version_info < (3, 9))' </dev/null >/dev/null 2>&1; then
    exec "$p" "$here/panel.py" "$@"
  fi
done
echo "mind: no Python 3.9 or newer found on PATH (tried python3, python, py)" >&2
exit 1
