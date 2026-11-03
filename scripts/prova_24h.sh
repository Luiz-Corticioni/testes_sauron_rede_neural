#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
if [ -x "$base/.venv/bin/python" ]; then
    exec "$base/.venv/bin/python" "$base/scripts/prova_24h.py" "$@"
fi
exec python3 "$base/scripts/prova_24h.py" "$@"
