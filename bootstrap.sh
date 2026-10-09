#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

command -v node >/dev/null || {
  echo "Node.js 24.18.0 is required."
  exit 1
}
command -v pnpm >/dev/null || {
  echo "pnpm 10.34.0 is required."
  exit 1
}

[[ "$(node --version)" == "v24.18.0" ]] || {
  echo "Expected Node.js v24.18.0, found $(node --version)."
  exit 1
}
[[ "$(pnpm --version)" == "10.34.0" ]] || {
  echo "Expected pnpm 10.34.0, found $(pnpm --version)."
  exit 1
}

echo "Installing workspace dependencies..."
pnpm install --frozen-lockfile

echo "Installing Electron..."
pnpm --filter @catan/desktop exec install-electron --no

electron_version="$(pnpm --filter @catan/desktop exec electron --version)"
echo "Bootstrap complete (${electron_version}). Run: pnpm dev"
