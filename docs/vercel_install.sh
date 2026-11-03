#!/usr/bin/env bash
# Install the documentation dependencies into .venv-docs at the repository root.
# Used as the Vercel install command (see vercel.json) and works locally too.
#
# conf.py needs Python >= 3.11 (tomllib), and the default python3 of the Vercel
# build image (Amazon Linux 2023) may be older, so an explicit version is used.
set -euo pipefail
cd "$(dirname "$0")/.."
VENV=.venv-docs
rm -rf "$VENV"

if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 "$VENV"
    uv pip install --python "$VENV/bin/python" -r docs/requirements.txt
    exit 0
fi

for py in python3.14 python3.13 python3.12 python3.11; do
    if command -v "$py" >/dev/null 2>&1; then
        "$py" -m venv "$VENV"
        "$VENV/bin/pip" install --quiet -r docs/requirements.txt
        exit 0
    fi
done

echo 'Python >= 3.11 is required to build the documentation' >&2
exit 1
