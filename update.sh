#!/usr/bin/env bash
# One-command update on the server: pull the latest code and rebuild.
# Data (Postgres + ./data) is never touched. Run from the repo dir on the VM:  ./update.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "==> pulling latest"
git pull --ff-only

echo "==> rebuilding & restarting"
docker compose up -d --build

echo "==> status"
docker compose ps
echo "Done. Tail logs with: docker compose logs -f"
