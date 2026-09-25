#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for Coinquant.
#
# The production observation path is Python 3.13 stdlib-only; offline research
# and the test suite additionally need numpy (pinned in requirements-research.txt)
# and pytest (imported by tests/test_active_core.py). CI uses Python 3.13, so we
# pin the same interpreter here via uv and expose it through a project venv.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

# 1) Deterministic Python 3.13 toolchain via uv (installs to ~/.local/bin).
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"

uv python install 3.13

# 2) Project virtualenv with the pinned research dependency plus the pytest
#    dev dependency the test suite requires. Re-running only reconciles state.
uv venv --python 3.13 --allow-existing .venv
uv pip install --python "$REPO_DIR/.venv/bin/python" -r requirements-research.txt pytest

# 3) Make `python`/`python3` resolve to the 3.13 venv in future agent shells.
#    Inserted before Ubuntu's non-interactive early-return so it also applies to
#    non-interactive command shells. Guarded so re-runs do not duplicate it.
BASHRC="$HOME/.bashrc"
MARKER='# >>> coinquant venv >>>'
if [ ! -f "$BASHRC" ] || ! grep -qF "$MARKER" "$BASHRC"; then
  BLOCK="$(cat <<EOF
$MARKER
if [ -f "$REPO_DIR/.venv/bin/activate" ]; then
  . "$REPO_DIR/.venv/bin/activate"
fi
# <<< coinquant venv <<<
EOF
)"
  if [ -f "$BASHRC" ]; then
    printf '%s\n%s\n' "$BLOCK" "$(cat "$BASHRC")" > "$BASHRC"
  else
    printf '%s\n' "$BLOCK" > "$BASHRC"
  fi
fi
