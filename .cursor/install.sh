#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for Coinquant.
#
# CI and the production path use Python 3.13 and the standard library only.
# uv supplies that interpreter. Symlinks in /usr/local/bin make it visible to
# non-interactive login shells, which never source the interactive part of bashrc.
set -euo pipefail

export PATH="${HOME}/.local/bin:${PATH}"
if [[ ! -x "${HOME}/.local/bin/uv" ]]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

uv python install 3.13
python_bin="$(uv python find 3.13)"

sudo ln -sfn "${python_bin}" /usr/local/bin/python3.13
sudo ln -sfn "${python_bin}" /usr/local/bin/python3
sudo ln -sfn "${python_bin}" /usr/local/bin/python

# Earlier bootstrap inserted a venv hook that login shells do not reliably load.
bashrc="${HOME}/.bashrc"
marker='# >>> coinquant venv >>>'
end_marker='# <<< coinquant venv <<<'
if [[ -f "${bashrc}" ]] && grep -qF "${marker}" "${bashrc}"; then
  awk -v start="${marker}" -v end="${end_marker}" '
    $0 == start { skip = 1; next }
    $0 == end { skip = 0; next }
    !skip { print }
  ' "${bashrc}" > "${bashrc}.tmp"
  mv "${bashrc}.tmp" "${bashrc}"
fi

python -c 'import sys, zoneinfo; assert sys.version_info[:2] == (3, 13), sys.version; zoneinfo.ZoneInfo("America/New_York")'
