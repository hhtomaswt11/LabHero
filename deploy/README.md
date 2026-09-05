# Deploying LabHero on a server

Entry-point guide for deploying [LabHero](https://github.com/hhtomaswt11/LabHero) as a browser game. It is written for CEB/UMinho IT staff or any sysadmin who has not worked with the project before.

The current release has two deployment paths:

- **Production (CEB/UMinho Darwin):** Podman, using repository-root `deploy.sh` and `deploy/nginx.podman.conf`.
- **Development/local validation:** Docker Compose, using files under `deploy/`.

The browser is the intended classroom client: students open one URL and do not install Python, Pygame, MEWpy or the metabolic models locally.

---

## 1. Production architecture — Darwin / Podman

The production host uses **Podman**, not Docker Compose.

`deploy.sh` builds and starts two containers in one Podman pod:

- **`labhero-frontend`** — nginx serving the fingerprinted Pygbag/WebAssembly bundle and proxying `/api/*`.
- **`labhero-backend`** — FastAPI + metabolic simulation stack for `ecoli_core` and `yeast_iMM904`.

Containers inside the pod share a network namespace, therefore nginx reaches the backend at:

```text
http://127.0.0.1:8000/
```

Only the frontend port is published. The default host mapping is:

```text
127.0.0.1 / host :8080 -> pod :80
```

The host port can be changed with `LABHERO_PORT`.

The expected institutional topology is:

```text
students / teachers
        |
       HTTPS
        |
        v
UMinho institutional reverse proxy
        |
        | internal HTTP
        v
Darwin host :8080
        |
        v
labhero-frontend (nginx)
        |
        +---- static Pygbag bundle
        |
        +---- /api/* ----------> labhero-backend :8000
```

The backend is not published directly to the external network.

### Why HTTPS matters

The public LabHero URL should be served through HTTPS. This is especially important because Teacher access uses HTTP Basic authentication at the web-server boundary. In the CEB/UMinho setup, TLS should normally be terminated by the institutional reverse proxy before traffic reaches the LabHero host port.

Do **not** expose the backend Uvicorn port directly to the internet.

---

## 2. Teacher access

Teacher Preview is isolated from student saves and supports both Normal and Easy campaign contexts.

### In-game access

On the title screen:

```text
SHIFT + T
```

The game asks for Teacher credentials, campaign mode and canonical mission number.

On Web the credentials are validated **server-side** through the protected `/teacher-auth` route. They are not embedded in the Pygbag bundle and are not persisted to `localStorage` or student save data.

After one successful authentication, the Teacher session remains authenticated only in memory for that page/runtime. The professor can switch missions from Settings without entering the password again. Reloading/restarting the page ends that transient authenticated session.

### Direct fallback routes

The protected direct route remains available, for example:

```text
https://<labhero-domain>/teacher/?mission=17&mode=normal
https://<labhero-domain>/teacher/?mission=25&mode=easy
```

The public root must not activate Teacher Preview from query parameters alone:

```text
/?teacher=1&mission=17
```

is not a valid Teacher entry point.

### Credentials

At deploy time, provide a strong password:

```bash
LABHERO_TEACHER_PASSWORD='use-a-strong-password' ./deploy.sh
```

The username defaults to:

```text
teacher
```

and can be changed with:

```bash
LABHERO_TEACHER_USER='another-user' \
LABHERO_TEACHER_PASSWORD='use-a-strong-password' \
./deploy.sh
```

`deploy.sh` hashes the password into:

```text
~/.config/labhero/teacher.htpasswd
```

and mounts the generated file read-only into nginx. Do not commit Teacher credentials, hashes intended as secrets, or plaintext passwords into the repository or browser bundle.

---

## 3. Get the current project

On the target host:

```bash
git clone https://github.com/hhtomaswt11/LabHero.git
cd LabHero
```

For an existing checkout:

```bash
cd ~/LabHero
git pull --ff-only
```

For a classroom/release deployment, prefer deploying a known release tag or exact commit rather than an arbitrary moving `main`.

---

## 4. Production deploy with Podman

### 4.1 Prerequisites

The production host needs:

- Podman
- a shell compatible with `deploy.sh`
- outbound HTTPS during image builds
- access from the institutional reverse proxy to the configured LabHero host port

Verify:

```bash
podman --version
```

### 4.2 Deploy

From the repository root:

```bash
LABHERO_TEACHER_PASSWORD='use-a-strong-password' ./deploy.sh
```

`deploy.sh` builds both images, recreates the LabHero pod, starts frontend/backend and performs deployment smoke checks.

The script currently verifies the important production contracts, including:

- API health;
- protected Teacher entry behaviour;
- Teacher authentication probe;
- Pygbag Teacher asset access;
- a real E. coli FBA simulation;
- a real yeast iMM904 pFBA simulation.

A successful `/api/health` alone is not considered sufficient proof that the scientific backend is usable.

### 4.3 Verify from the host

The default local checks use port `8080`:

```bash
curl http://127.0.0.1:8080/api/health
curl -I http://127.0.0.1:8080/
```

Expected health response:

```json
{"status":"ok"}
```

Then verify the institutional public HTTPS URL from a browser.

---

## 5. HTTPS / public domain

### Recommended CEB/UMinho setup

For the institutional deployment:

1. LabHero listens on an internal host port such as `8080`.
2. The UMinho reverse proxy owns the public hostname and TLS certificate.
3. The proxy forwards requests to the Darwin host.
4. Students and teachers only use the public HTTPS URL.

This keeps certificate management outside the LabHero containers and avoids exposing Uvicorn directly.

### Other environments

If deploying outside the institutional infrastructure, use a normal HTTPS reverse proxy such as Caddy, nginx or an equivalent managed service.

If Cloudflare is used, do **not** document or rely on `Flexible` SSL for a production Teacher deployment. Use end-to-end TLS (`Full (strict)`) when the origin is configured for HTTPS, or use another trusted reverse-proxy design that protects credentials in transit.

---

## 6. Development / local validation with Docker Compose

Docker Compose remains available for local development and smoke testing. It is not the production Darwin path.

### 6.1 Prerequisites

Verify Docker Engine and Compose v2:

```bash
docker --version
docker compose version
```

### 6.2 Build and smoke test

```bash
cd deploy
./local_smoke.sh
```

Or manually:

```bash
docker compose build
docker compose up -d
```

Verify:

```bash
docker compose ps
curl http://localhost/api/health
curl -I http://localhost/
```

Open:

```text
http://localhost/
```

in Firefox or Chrome.

### 6.3 Logs / stop

```bash
docker compose logs -f
docker compose logs -f backend
docker compose restart
docker compose down
```

For a complete image cleanup:

```bash
docker compose down --rmi all
```

There are no application database volumes in the current stack. Student browser progress lives in browser `localStorage`, not in a server-side LabHero account database.

---

## 7. Browser bundle and cache behaviour

The frontend is built with Pygbag.

The build fingerprints the game archive:

```text
src.<sha256>.tar.gz
```

nginx serves:

- `index.html` with revalidation / no-cache semantics;
- fingerprinted archives with a long immutable cache lifetime.

After a deploy, clients revalidate the entry document. If the game bytes changed, the new `index.html` references a different fingerprinted archive URL, avoiding the classic problem where a browser keeps running an obsolete fixed-name game archive.

The first browser visit is the expensive one because the Pygbag CPython/WebAssembly runtime and game archive must be initialized/downloaded. Repeat visits can reuse browser cache.

---

## 8. Browser saves

Student progress is browser-local.

The Web build persists LabHero data under the versioned:

```text
labhero:v1:
```

namespace in `localStorage`, with an in-memory session cache/fallback.

Persisted state includes the normal/easy student campaign data and mission evidence used by the existing save helpers. Autosave also keeps position/profile/reward state reasonably current.

Important operational consequences:

- progress is scoped to the **browser + origin**;
- changing hostname, protocol or port creates a different browser storage origin;
- clearing site data removes that browser's LabHero progress;
- `Back to Title` preserves progress;
- an explicit `New Game` clears LabHero's student namespace rather than unrelated browser storage;
- if `localStorage` is unavailable, the game falls back to session memory and warns in the browser console.

Keep the production hostname stable once students start using the game.

---

## 9. Scientific simulation paths

The browser never needs MEWpy installed on the student's computer. Visible simulations are submitted to FastAPI.

The current backend supports:

```text
model_id:
- ecoli_core
- yeast_iMM904
```

Simulation requests/results are model-aware. The backend validates the objective/model combination and works on an isolated model copy before applying mutation/environmental constraints.

The response separates:

- primary objective flux;
- method-specific diagnostic/score;
- predicted growth;
- requested fluxes;
- exchange/medium information;
- disabled reactions/GPR evidence where applicable.

Bound Sweep is also model-aware. The live browser path submits the tested rows through normal backend simulations and assembles the visible curve client-side. This is used by the E. coli sweep missions and the yeast glucose sweeps in Missions 36 and 40.

The live Pygbag UI uses asynchronous browser requests so the event loop remains responsive. Sweep requests are intentionally awaited sequentially rather than flooding the backend with all rows at once.

---

## 10. Resource sizing and classroom load

Initial sizing still needs to be validated on the final host.

| Resource | Minimum starting point | More comfortable starting point |
|---|---:|---:|
| CPU | 1 vCPU | 2+ vCPU |
| RAM | 1 GB | 2+ GB |
| Disk | 4 GB | 10 GB |
| Network | outbound HTTPS during build | same |

Runtime cost is dominated by Python + the metabolic model/solver stack. E. coli work is lighter than iMM904 and concurrent scientific requests are CPU-bound.

Before claiming a classroom concurrency capacity, perform a representative load test on Darwin. Recommended checkpoints:

```text
5 simultaneous users
10 simultaneous users
20 simultaneous users
30 simultaneous users
```

Record at least:

- error/timeout count;
- p50/p95 response latency;
- CPU;
- RAM.

Do not add Uvicorn workers or nginx rate limits blindly before measuring the real host. Extra workers can improve concurrency but also duplicate model/process memory.

---

## 11. Security notes

### Network boundary

Keep FastAPI internal behind nginx/the institutional reverse proxy. The current dependency stack contains older scientific packages that should not be treated as a reason to expose Uvicorn directly.

### Teacher credentials

Teacher Basic Auth must only travel over the public HTTPS deployment. Credentials must never be embedded in Python files shipped to Pygbag, JavaScript, URLs, screenshots or repository documentation.

### Dependencies

The scientific stack is intentionally pinned for reproducibility. Before a public release, run a dependency audit such as:

```bash
python3 -m pip install pip-audit
pip-audit -r requirements.txt
```

Treat the output as an audit. Do not perform a broad MEWpy/NumPy/pandas/httpx upgrade immediately before release without rerunning the scientific and mission regression suites, because solver/library changes can alter validated behaviour.

---

## 12. Release verification

Before deploying a final classroom release, run from the repository root:

```bash
python3 -m compileall -q code backend/app tests main.py LabHero.py
python3 -m unittest discover -s tests -p "test_*.py"
```

Then validate manually on the public HTTPS deployment:

- New Game / Continue;
- refresh persistence;
- Easy campaign end-to-end;
- Golden Lab / yeast access;
- Golden Egg persistence if part of the QA pass;
- Teacher Access with Normal and Easy;
- Teacher mission switching and exit;
- student save isolation from Teacher Preview;
- E. coli simulation;
- yeast iMM904 simulation;
- representative Bound Sweep;
- Final Results.

For the final handoff, record the exact Git commit/tag deployed on Darwin.

---

## 13. Troubleshooting

| Symptom | Likely cause | First check |
|---|---|---|
| Build fails during Pygbag | Host cannot reach required package/build sources | Check outbound HTTPS and build logs |
| `/api/health` times out | Backend not ready or pod/container networking problem | Backend logs and pod/container status |
| Browser opens but simulation fails | Frontend cannot reach API or scientific backend failed | `/api/health`, backend logs, deploy smoke simulation |
| Teacher credentials always fail | htpasswd not mounted/configured or reverse proxy route mismatch | `~/.config/labhero/teacher.htpasswd`, nginx config, `/teacher-auth` |
| Teacher direct URL is public | `/teacher/` auth boundary misconfigured | nginx auth config before classroom use |
| Browser shows an old game | stale entry point/container deployment | Confirm current `index.html` points to the newest `src.<sha256>.tar.gz` |
| Progress disappears after hostname change | browser storage origin changed | Keep one stable production origin |
| Audio does not start immediately | browser autoplay restrictions | Interact with the page/game first |
| Web "Quit Game" behaviour differs from desktop | browsers cannot close their own tab reliably | Use the Web Back-to-Title flow |

---

## 14. Useful operational commands

### Podman production

Exact container/pod lifecycle is centralized in `deploy.sh`. For troubleshooting:

```bash
podman ps
podman pod ps
podman logs labhero-backend
podman logs labhero-frontend
```

Container names can differ if the deploy script is changed; inspect `podman ps` first.

### Docker development

```bash
cd deploy
docker compose ps
docker compose logs -f
docker compose restart
docker compose down
```

---

## 15. Where to ask for help

- Current project repository / Issues: <https://github.com/hhtomaswt11/LabHero/issues>
- Original LabHero project: <https://github.com/mleiras/LabHero>
- Original archived release / DOI: <https://doi.org/10.5281/zenodo.20292021>

For institutional production changes, coordinate with the CEB/UMinho administrator responsible for the reverse proxy, DNS and TLS.
