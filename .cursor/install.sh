#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for Coinquant.
#
# The package, offline research tools, and tests use the Python 3.13 standard
# library only. CI pins CPython 3.13 (.github/workflows/check.yml). The default
# Cloud Agent image provides Python 3.12, so this script installs 3.13 and
# exposes it on the default PATH ahead of /usr/bin.
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/0.12.20/install.sh | env UV_UNMANAGED_INSTALL="${HOME}/.local/bin" sh
fi

uv python install 3.13
python_bin="$(uv python find 3.13)"

# A direct symlink keeps the interpreter's prefix. Non-interactive agent
# shells do not source ~/.profile, and /usr/local/bin is already on PATH.
sudo ln -sfn "${python_bin}" /usr/local/bin/python3.13
sudo ln -sfn python3.13 /usr/local/bin/python3
sudo ln -sfn python3.13 /usr/local/bin/python

/usr/local/bin/python - <<'PY'
import sys
from zoneinfo import ZoneInfo

if sys.version_info[:2] != (3, 13):
    raise SystemExit(f"expected Python 3.13, found {sys.version}")
ZoneInfo("America/New_York")
PY
