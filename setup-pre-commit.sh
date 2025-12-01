#!/usr/bin/env zsh
# Setup pre-commit hooks for q-task
# Usage:
#   ./setup-pre-commit.sh          # install hooks
#   ./setup-pre-commit.sh --all    # install hooks and run `pre-commit run --all-files`

set -eu

echodo() {
    echo "+ $*"
    "$@"
}

echo "Setting up pre-commit hooks for q-task..."

# Helper: try to run a command if available
command_exists() {
    command -v "$1" &> /dev/null
}

# Install pre-commit if it's missing. Prefer user-level `pipx`, then `pip`.
if ! command_exists pre-commit; then
    if command_exists pipx; then
        echo "Installing pre-commit with pipx (recommended)..."
        echodo pipx install pre-commit
    else
        echo "pipx not available, falling back to python -m pip --user install pre-commit"
        echodo python3 -m pip install --user pre-commit
        # Add user base bin to PATH hint (doesn't modify current PATH)
        user_bin=$(python3 -m site --user-base)/bin
        echo "If 'pre-commit' is still not found, add this to your PATH: $user_bin"
    fi
fi

# Use uv if it's available in this environment (some devcontainers use it),
# otherwise run pre-commit directly.
if command_exists uv; then
    echo "Installing git hook scripts via 'uv run pre-commit install'"
    echodo uv run pre-commit install
else
    echo "Installing git hook scripts via 'pre-commit install'"
    echodo pre-commit install
fi

if [ "${1:-}" = "--all" ] || [ "${1:-}" = "-a" ]; then
    echo "Running pre-commit checks against all files (this may take a while)..."
    echodo pre-commit run --all-files
fi

echo ""
echo "Pre-commit hooks installed successfully."
echo "To run pre-commit against all files later, run:"
echo "  pre-commit run --all-files"
