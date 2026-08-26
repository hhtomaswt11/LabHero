#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

APP_NAME="labhero"
POD_NAME="${LABHERO_POD_NAME:-labhero-pod}"
HOST_PORT="${LABHERO_PORT:-8080}"
BACKEND_IMAGE="${APP_NAME}-backend"
FRONTEND_IMAGE="${APP_NAME}-frontend"
BACKEND_CONTAINER="${APP_NAME}-backend"
FRONTEND_CONTAINER="${APP_NAME}-frontend"

for dependency in podman curl; do
    if ! command -v "$dependency" >/dev/null 2>&1; then
        echo "ERROR: '$dependency' is required for the LabHero Podman deployment." >&2
        exit 1
    fi
done

echo "[LabHero] Building backend image..."
podman build -t "$BACKEND_IMAGE" ./backend

echo "[LabHero] Building frontend image for a shared Podman pod..."
podman build \
    -t "$FRONTEND_IMAGE" \
    -f deploy/Dockerfile.frontend \
    --build-arg NGINX_CONF=deploy/nginx.podman.conf \
    .

echo "[LabHero] Recreating pod '$POD_NAME' on host port $HOST_PORT..."
podman pod rm -f "$POD_NAME" >/dev/null 2>&1 || true
# Also clean up same-named containers left by an interrupted earlier deployment.
podman rm -f "$BACKEND_CONTAINER" "$FRONTEND_CONTAINER" >/dev/null 2>&1 || true

podman pod create \
    --name "$POD_NAME" \
    -p "${HOST_PORT}:80"

echo "[LabHero] Starting backend..."
podman run -d \
    --name "$BACKEND_CONTAINER" \
    --pod "$POD_NAME" \
    --restart=unless-stopped \
    -e PYTHONUNBUFFERED=1 \
    "$BACKEND_IMAGE" >/dev/null

echo "[LabHero] Starting frontend..."
podman run -d \
    --name "$FRONTEND_CONTAINER" \
    --pod "$POD_NAME" \
    --restart=unless-stopped \
    "$FRONTEND_IMAGE" >/dev/null

echo "[LabHero] Waiting for frontend + backend health..."
HEALTH_URL="http://127.0.0.1:${HOST_PORT}/api/health"
for attempt in $(seq 1 90); do
    if curl -fsS "$HEALTH_URL" >/tmp/labhero-podman-health.json 2>/dev/null; then
        echo
        echo "[LabHero] Backend health: $(cat /tmp/labhero-podman-health.json)"
        echo "[LabHero] Deployment ready at http://127.0.0.1:${HOST_PORT}/"
        exit 0
    fi
    if [ "$attempt" -eq 90 ]; then
        echo
        echo "ERROR: LabHero did not become healthy at $HEALTH_URL." >&2
        echo "Backend logs:" >&2
        podman logs "$BACKEND_CONTAINER" 2>&1 | tail -50 >&2 || true
        echo "Frontend logs:" >&2
        podman logs "$FRONTEND_CONTAINER" 2>&1 | tail -50 >&2 || true
        exit 1
    fi
    printf '.'
    sleep 2
done
