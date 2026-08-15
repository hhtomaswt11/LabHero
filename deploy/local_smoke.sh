#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

for dependency in docker curl; do
    if ! command -v "$dependency" >/dev/null 2>&1; then
        echo "ERROR: '$dependency' is required for the local LabHero web smoke test." >&2
        exit 1
    fi
done

if ! docker compose version >/dev/null 2>&1; then
    echo "ERROR: Docker Compose v2 ('docker compose') is required." >&2
    exit 1
fi

echo "[LabHero] Building and starting frontend + backend..."
docker compose up -d --build

echo "[LabHero] Waiting for /api/health..."
for attempt in $(seq 1 90); do
    if curl -fsS http://localhost/api/health >/tmp/labhero-health.json 2>/dev/null; then
        echo
        echo "[LabHero] Backend health: $(cat /tmp/labhero-health.json)"
        break
    fi
    if [ "$attempt" -eq 90 ]; then
        echo
        echo "ERROR: backend did not become healthy in time." >&2
        echo "Run: cd deploy && docker compose logs backend" >&2
        exit 1
    fi
    printf '.'
    sleep 2
done

if ! curl -fsSI http://localhost/ >/tmp/labhero-front-headers.txt; then
    echo "ERROR: frontend did not answer on http://localhost/." >&2
    echo "Run: cd deploy && docker compose logs frontend" >&2
    exit 1
fi

echo "[LabHero] Frontend answered successfully."
echo "[LabHero] Open http://localhost/ in Firefox or Chrome."
echo "[LabHero] Keep this terminal available for: docker compose logs -f"
