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

for dependency in podman curl openssl; do
    if ! command -v "$dependency" >/dev/null 2>&1; then
        echo "ERROR: '$dependency' is required for the LabHero Podman deployment." >&2
        exit 1
    fi
done

TEACHER_USER="${LABHERO_TEACHER_USER:-teacher}"
TEACHER_PASSWORD="${LABHERO_TEACHER_PASSWORD:-}"
TEACHER_AUTH_DIR="${LABHERO_TEACHER_AUTH_DIR:-${HOME}/.config/labhero}"
TEACHER_HTPASSWD_FILE="${TEACHER_AUTH_DIR}/teacher.htpasswd"

if [ -z "$TEACHER_PASSWORD" ]; then
    echo "ERROR: LABHERO_TEACHER_PASSWORD must be set for the production Teacher route." >&2
    echo "Example: LABHERO_TEACHER_PASSWORD='choose-a-strong-password' ./deploy.sh" >&2
    exit 1
fi

mkdir -p "$TEACHER_AUTH_DIR"
chmod 700 "$TEACHER_AUTH_DIR"
TEACHER_PASSWORD_HASH="$(printf '%s' "$TEACHER_PASSWORD" | openssl passwd -apr1 -stdin)"
printf '%s:%s\n' "$TEACHER_USER" "$TEACHER_PASSWORD_HASH" > "$TEACHER_HTPASSWD_FILE"
chmod 644 "$TEACHER_HTPASSWD_FILE"
LABHERO_TEACHER_PASSWORD_FOR_CHECK="$TEACHER_PASSWORD"
unset TEACHER_PASSWORD TEACHER_PASSWORD_HASH LABHERO_TEACHER_PASSWORD

echo "[LabHero] Teacher route credentials prepared for user '$TEACHER_USER'."
# The parent directory remains mode 0700 on the host, so other host users
# cannot traverse to this file. The file itself is 0644 because nginx handles
# HTTP Basic Auth in an unprivileged worker process inside the rootless Podman
# container and must be able to read the bind-mounted password hash.

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
    -v "${TEACHER_HTPASSWD_FILE}:/etc/nginx/.htpasswd:ro" \
    "$FRONTEND_IMAGE" >/dev/null

echo "[LabHero] Waiting for frontend + backend health..."
HEALTH_URL="http://127.0.0.1:${HOST_PORT}/api/health"
for attempt in $(seq 1 90); do
    if curl -fsS "$HEALTH_URL" >/tmp/labhero-podman-health.json 2>/dev/null; then
        TEACHER_URL="http://127.0.0.1:${HOST_PORT}/teacher/?mission=1"
        UNAUTH_STATUS="$(curl -sS -o /dev/null -w '%{http_code}' "$TEACHER_URL" || true)"
        AUTH_STATUS="$(curl -sS -u "${TEACHER_USER}:${LABHERO_TEACHER_PASSWORD_FOR_CHECK}" -o /dev/null -w '%{http_code}' "$TEACHER_URL" || true)"
        TEACHER_HTML_FILE="/tmp/labhero-teacher-index.html"
        curl -fsS -u "${TEACHER_USER}:${LABHERO_TEACHER_PASSWORD_FOR_CHECK}" \
            "$TEACHER_URL" -o "$TEACHER_HTML_FILE" >/dev/null 2>&1 || true
        TEACHER_ARCHIVE="$(grep -oE 'src\.[0-9a-f]{16}\.tar\.gz' "$TEACHER_HTML_FILE" | head -1 || true)"
        ASSET_STATUS="missing"
        if [ -n "$TEACHER_ARCHIVE" ]; then
            ASSET_STATUS="$(curl -sS -o /dev/null -w '%{http_code}' \
                "http://127.0.0.1:${HOST_PORT}/teacher/${TEACHER_ARCHIVE}" || true)"
        fi

        if [ "$UNAUTH_STATUS" != "401" ] || [ "$AUTH_STATUS" != "200" ] || [ "$ASSET_STATUS" != "200" ]; then
            echo
            echo "ERROR: Teacher route authentication/runtime smoke test failed." >&2
            echo "Expected unauthenticated entry HTTP 401, got ${UNAUTH_STATUS}." >&2
            echo "Expected authenticated entry HTTP 200, got ${AUTH_STATUS}." >&2
            echo "Expected unauthenticated Pygbag teacher asset HTTP 200, got ${ASSET_STATUS}." >&2
            echo "Frontend logs:" >&2
            podman logs "$FRONTEND_CONTAINER" 2>&1 | tail -50 >&2 || true
            exit 1
        fi
        unset LABHERO_TEACHER_PASSWORD_FOR_CHECK
        echo
        echo "[LabHero] Backend health: $(cat /tmp/labhero-podman-health.json)"
        echo "[LabHero] Teacher entry auth: unauthenticated=401 authenticated=200"
        echo "[LabHero] Teacher Pygbag asset: unauthenticated=200 (${TEACHER_ARCHIVE})"
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
