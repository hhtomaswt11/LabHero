# Deploying LabHero on a server

Entry-point guide for getting [LabHero](https://github.com/mleiras/LabHero) live on a server with a public domain. Written for UMinho IT staff (or any sysadmin) who has not seen this project before.

If you already have Docker installed on a server reachable on the internet, jump to [§3 Deploy](#3-deploy) — the actual game-specific steps are just three commands. Everything before that is generic VM + DNS + TLS setup that may or may not apply.

---

## What you're deploying

LabHero is a serious game (RPG simulation) that teaches non-bioinformaticians about genome-scale metabolic models. Players control a bioinformatician at a university and complete missions involving FBA simulations on E. coli.

It started life as a Python/Pygame desktop game and has been ported to the browser via pygbag. The stack you'll run consists of two Docker containers:

- **`labhero-backend`** — FastAPI + MEWpy. Receives simulation requests, runs the selected method on the `e_coli_core` model, and returns a structured method-aware result separating the primary objective flux from secondary solver scores. CPU-bound, small RAM footprint.
- **`labhero-frontend`** — nginx. Serves the pygbag-compiled game bundle as static files and reverse-proxies `/api/*` to the backend over the internal Docker network.

Only the frontend is exposed to the host network. End users only ever see one URL.

```
        public internet
              │
              ▼
   ┌──────────────────────┐
   │  TLS terminator      │  ←  Cloudflare / Caddy / nginx
   │  (your choice)       │     (HTTPS, certs, the public domain)
   └─────────┬────────────┘
             │ plain HTTP
             ▼
   ┌──────────────────────┐
   │  labhero-frontend    │  ←  port 80 on the host
   │  (nginx)             │
   └─────────┬────────────┘
             │ docker network
             ▼
   ┌──────────────────────┐
   │  labhero-backend     │  ←  not exposed to host
   │  (FastAPI + MEWpy)   │
   └──────────────────────┘
```

### Resource sizing

| Resource | Minimum | Comfortable |
|---|---|---|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Disk | 4 GB | 10 GB |
| Network | outbound HTTPS during build only | same |

Runtime cost is dominated by uvicorn + cobra/MEWpy holding the `e_coli_core` model in memory. Concurrent FBA requests are CPU-bound but fast (<1 s each for the included model); a single vCPU handles a small classroom of simultaneous players comfortably.

---

## 1. Prepare the server

Skip this section if you already have a Linux VM with Docker installed and outbound internet access.

### 1.1 OS

Any recent Linux. Ubuntu 22.04 / 24.04 LTS, Debian 12, Rocky / Alma 9, or equivalent. Instructions below assume Ubuntu/Debian; substitute the package manager for RPM-based distros.

### 1.2 Install Docker

Use Docker's official `get.docker.com` script (works on Ubuntu, Debian, Fedora, CentOS, Rocky, Alma):

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
# log out and back in for the group change to apply
```

Verify:

```bash
docker --version
docker compose version
```

You need Docker Engine 20.10+ and the Compose v2 plugin (the command is `docker compose`, two words — not the older `docker-compose`).

### 1.3 Firewall

The frontend listens on port 80 of the host. If you'll put a TLS terminator on the same host, that terminator also needs 443. UMinho's network team likely manages this at the VLAN level — check before opening anything host-side.

If using `ufw`:

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp   # if TLS lives on this host
```

---

## 2. Domain and HTTPS

Skip this section if you'll be reached via an existing UMinho subdomain that already has TLS handled upstream.

Browsers refuse to run modern game features (audio, fast wasm) over plain HTTP on a public domain. You **must** terminate TLS somewhere before traffic hits the LabHero containers. There are three good ways to do it.

### Option A: Cloudflare (zero config on the server)

Sign up at cloudflare.com, add your domain, point the nameservers as instructed by Cloudflare, then create an A record pointing `labhero.yourdomain.tld` → your server's public IP. Make sure the orange-cloud proxy icon is on. Set SSL/TLS mode to "Flexible" (Cloudflare → user is HTTPS; Cloudflare → your server is plain HTTP). Done.

This is the lowest-friction option. The downside is your traffic passes through a third party.

### Option B: Caddy on the same host (1 file)

Caddy gets a Let's Encrypt cert automatically. Install:

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

`/etc/caddy/Caddyfile`:

```
labhero.yourdomain.tld {
    reverse_proxy localhost:80
}
```

Then:

```bash
sudo systemctl restart caddy
```

Caddy will provision the cert on first request and renew it automatically. Make sure the `A` record for `labhero.yourdomain.tld` already points at this server before Caddy starts, otherwise the ACME challenge fails.

### Option C: nginx + certbot on the same host

Most flexible but most moving parts. UMinho IT may already have a preferred pattern — defer to that. The principle is the same: nginx (or any TLS terminator) listens on 443, proxies to `127.0.0.1:80` where labhero-frontend is bound.

---

## 3. Deploy

This is the part that's specific to LabHero. All commands run on the server.

### 3.1 Get the code

```bash
sudo apt install -y git
git clone https://github.com/mleiras/LabHero.git
cd LabHero/deploy
```

### 3.2 Build and start

For the first local browser smoke test, the repository includes a helper that builds the two containers, waits for the API health check and verifies that nginx serves the frontend:

```bash
cd deploy
./local_smoke.sh
```

The equivalent manual commands are:

```bash
docker compose build
docker compose up -d
```

First build takes 3-6 minutes (downloads ~600 MB of pip wheels for the backend image, plus pygbag and the game bundle for the frontend image). Subsequent builds reuse Docker layers and take under a minute.

### 3.3 Verify

```bash
docker compose ps                    # both services should be Up
curl http://localhost/api/health     # {"status":"ok"}
curl -I http://localhost/            # Content-Type: text/html
```

For local validation, open `http://localhost/` in Firefox or Chrome. On the final server, open the configured public URL instead. The first page load is the expensive one because the browser must bootstrap Pygbag's CPython/WebAssembly runtime and download the game archive. Repeat visits reuse the content-addressed game archive from the browser cache.

---

## 4. Operate

### Day-to-day

```bash
docker compose ps                # who's up
docker compose logs -f           # tail logs from both containers
docker compose logs -f backend   # just one
docker compose restart           # restart in place (e.g. after host reboot)
```

### Update to a new game version

When the upstream repo gets a new release:

```bash
cd ~/LabHero
git pull
cd deploy
docker compose build --no-cache    # force rebuild so latest game code is bundled
docker compose up -d
```

The frontend build fingerprints the Pygbag archive as `src.<sha256>.tar.gz`. nginx keeps `index.html` on `Cache-Control: no-cache`, so clients revalidate the entry point after a deploy; if the game bytes changed, that fresh index references a new archive URL. The fingerprinted archive itself is served with a long `immutable` cache lifetime, so repeat visits avoid re-downloading the ~12 MB bundle without risking an old fixed-name archive after an update.

### Stop / uninstall

```bash
docker compose down              # stop and remove containers (images stay)
docker compose down --rmi all    # also remove images, for a full uninstall
```

There are no Docker volumes — the stack is stateless. Nothing to back up.

### Configuration knobs

This stack runs with sensible defaults out of the box. You probably do not need to edit anything. If you do, the surfaces are:

- **`docker-compose.yml`** — service definitions, port mapping. Change `"80:80"` if you need to bind to a different host port.
- **`nginx.conf`** — proxy timeouts, MIME types, cache headers.
- **`Dockerfile.frontend`** — pinned pygbag version (0.9.3).
- **`../backend/Dockerfile`** — pinned Python (3.10-slim) and the `libexpat1` system dependency MEWpy/libsbml needs.

If you change `nginx.conf` you can hot-reload without rebuilding the image:

```bash
docker compose exec frontend nginx -s reload
```

---

## 5. Troubleshooting

| Symptom | Likely cause | First thing to check |
|---|---|---|
| Build fails on the pygbag step | Server has no outbound HTTPS to `pygame-web.github.io` | Build the image on a workstation, push to a registry, `docker pull` on the server |
| `curl http://localhost/` downloads a file instead of returning HTML | `nginx.conf` was edited and now overrides `types {}` | Revert to the shipped `nginx.conf` or read the comment block in it |
| `curl http://localhost/api/health` times out | Backend not ready or docker network broken | `docker compose logs backend` for the startup line; `docker compose down && up -d` |
| Browser shows the title screen but the simulation menu hangs | Frontend reached but backend unreachable from frontend | `docker compose exec frontend wget -qO- http://backend:8000/health` should return `{"status":"ok"}` |
| Audio doesn't play | Browser audio is gated behind user interaction | Click anywhere on the page first |
| Audio works but stutters when opening menus | Single-threaded wasm running heavy menu construction (137 gene toggles, 40 reaction toggles) | Expected. The build is broken into chunks that yield to the audio mixer between batches, but on low-end CPUs the gaps can still be audible |
| Browser appears to run an older build after a deploy | Confirm the served `index.html` references the newest `src.<sha256>.tar.gz`; a hard refresh should revalidate the no-cache entry point | Rebuild/restart the frontend and verify the fingerprinted archive name changed when game bytes changed |
| "Quit Game" does nothing on web | Expected | The game replaces "Quit Game" with "Back to Title" on the web because browsers don't let JavaScript close their own tab |

---

## 6. Known issues to revisit before going public

### Browser save persistence

The current pygbag build keeps player and mission state in an in-memory web store. It survives navigation inside the running game, but a full page refresh or closed tab can discard progress. Before a public classroom release, replace this with either browser `localStorage`/IndexedDB or a backend save API with user/session identifiers. Mission evidence is already JSON-serialisable, so this is a storage-layer task rather than a mission-logic rewrite.

### Browser-only simulation paths

Normal visible simulations, including Mission 19's FBA/lMOMA comparison, use the FastAPI service and validate the already visible structured result. For lMOMA, the backend computes an explicit wild-type FBA reference in the selected medium before applying the GPR-derived mutant constraints; the browser never runs MEWpy locally. Bound Sweeps are now model-aware and reuse the same `POST /simulate` contract: the browser submits each tested bound as a normal backend simulation and assembles the visible rows client-side for the E. coli sweep missions and Mission 36. The live browser simulation path now uses Pygbag asynchronous Fetch (`aio.fetch`), and Bound Sweep requests are awaited sequentially so the Pygame/pygbag event loop stays responsive without multiplying backend load. A legacy synchronous helper remains only for backwards-compatible direct callers/tests; it is not used by the live simulator UI.

### Dependency security

Three Dependabot CVEs were dismissed for the desktop game because they are not reachable in a Pygame desktop binary. They **become reachable** the moment the backend starts parsing real HTTP behind a public TLS terminator.

- **h11 < 0.13** is forced by MEWpy 0.1.36's transitive pin on `httpx==0.23.0` (Chunked-Encoding CVE). The included nginx in this stack handles HTTP parsing itself before traffic reaches uvicorn, which is sufficient mitigation. **If you bypass nginx and expose uvicorn directly to the public internet, the CVE is in play.**
- **idna** is in the same dependency tree and has a low-severity CVE.
- **Pillow** is not currently in the runtime dependency closure but a future game update that adds image processing would introduce it.

If your security team needs a clean scan, the path is to upgrade MEWpy to a version that does not pin httpx 0.23.0, or to vendor the FBA call directly against cobrapy (the backend's `app/simulator.py` already does most of this — only the `mewpy.simulation.get_simulator` indirection would need replacing).

---

## 7. Where to ask for help

- The repo's GitHub Issues: <https://github.com/mleiras/LabHero/issues>
- The game's archived release on Zenodo (DOI [10.5281/zenodo.20292021](https://doi.org/10.5281/zenodo.20292021))
