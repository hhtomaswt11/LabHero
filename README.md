![LabHero](LabHero.png)

# LabHero

LabHero is an educational serious game for learning **constraint-based metabolic modelling** through guided, evidence-driven missions. The player enters a systems-biology laboratory as a student, registers with **Dr. Melo**, chooses a campaign route, talks to researchers, designs simulations and interprets the visible evidence before submitting conclusions.

The current game supports two metabolic models:

- **E. coli core** (`ecoli_core`) for the main modelling curriculum.
- **Yeast iMM904** (`yeast_iMM904`) for the Golden Lab and the final yeast missions.

LabHero was originally developed as part of Mónica Leiras' MSc thesis, *Development of a serious game to stimulate the learning of genome-scale metabolic modeling concepts* (MSc in Bioinformatics, University of Minho / Centre of Biological Engineering), and has since been extended with additional missions, browser deployment, campaign modes, scoring, teacher-preview tooling and multi-model support.

## Play online

The browser version is the main classroom deployment and requires **no local installation**:

```text
https://labhero.bio.di.uminho.pt/
```

The first load may take longer while the browser initializes the Pygbag/WebAssembly runtime and downloads the current game archive. Student progress is stored in browser `localStorage` for the LabHero origin.

## Campaign modes

A new student registers a name with Dr. Melo and then chooses one campaign mode. The choice is locked for that save.

### Normal

The full campaign contains **40 missions**:

```text
M01 -> M02 -> ... -> M40
```

Maximum score: **200 points**.

M01-M35 form the E. coli curriculum. Completing M35 unlocks the **Golden LabHero** skin, the Golden Lab and the yeast programme. M36-M40 use the iMM904 model.

### Easy

The curated classroom route contains **11 missions** and is designed for a substantially shorter playthrough:

```text
M01 -> M03 -> M06 -> M07 -> M13 -> M18 -> M21 -> M23 -> M25 -> M27 -> M36
```

Maximum score: **55 points**.

Easy mode intentionally keeps the **canonical mission numbers from Normal mode**. The skipped numbers are not renumbered and are not marked as completed. For example, an Easy-mode student really plays Mission 25 as **M25**, not as an Easy-specific "Mission 9".

After M27, Easy mode unlocks the Golden Lab and yeast simulator so the route can finish with M36. The **Golden LabHero skin remains an exclusive reward for completing Normal Mission 35**.

## Scoring, hints and answers

Starting hint-key budgets are campaign-specific:

| Campaign | Bronze | Silver | Gold |
|---|---:|---:|---:|
| Normal | 15 | 10 | 5 |
| Easy | 8 | 5 | 2 |

Keys are limited and are spent when optional hints are unlocked. A mission starts at 5 possible points and hint use changes its score ceiling as follows:

| Hints unlocked | Mission score before answer penalties |
|---:|---:|
| 0 | 5 |
| 1 | 3 |
| 2 | 2 |
| 3 | 1 |

Once the required mission evidence is complete, **every rejected final-answer submission costs 1 additional point**, including spelling/typing mistakes. Mission scores never fall below 0. This discourages brute-force guessing and rewards careful interpretation of the report.

Dr. Melo explains the key inventory and scoring rules during registration. Current keys, score, hints and skins can be reviewed in the Inventory.

### Golden Egg

LabHero contains an optional exploration reward. If the Golden Egg is found **before the selected campaign is complete**, it awards:

- **Normal:** +3 Gold Keys
- **Easy:** +1 Gold Key

The reward is one-time and persisted with the student save. If the egg was never collected and is only found after campaign completion, it is intentionally too late to claim the reward.

## Controls

### Title screen

- **ENTER** — continue the existing save.
- **SPACE** — request a New Game.
- **SPACE again** — confirm the New Game and erase the current student save.
- **ESC** — cancel the New Game confirmation.
- **SHIFT + T** — open the protected Teacher Access flow.

### Exploration

- **Arrow keys / WASD** — move.
- **ENTER** — interact with nearby scientists, Dr. Melo, simulators, books and other interactive objects.
- **E** — open the Inventory / skin selector.
- **M** — open LabHero Settings.
- **F** — after campaign completion, reopen Final Results.
- **ESC** — close/back out of most dialogues and menus.

ENTER interactions are release-gated: an ENTER used to close/confirm a menu is not reused automatically as a world interaction on the following frame.

### Settings

The `M` menu provides music/volume controls, **Back to Spawnpoint**, How to Play and the platform-appropriate save/exit options. Back to Spawnpoint returns the player to the map's canonical Tiled `Start` position **without resetting campaign progress**.

During Teacher Preview, Settings also provides the Teacher-specific mission-switch and exit controls.

## Simulator workflow

The simulator supports controlled environmental and genetic experiments, objective selection, production/exchange reporting, and mission-specific comparison/sweep workflows.

Current UI/runtime features include:

- reaction objectives displayed as **Name (ID)** while the solver receives the canonical reaction ID;
- model-aware requests that keep `ecoli_core` and `yeast_iMM904` explicit end-to-end;
- structured results that separate the **primary objective** from method-specific secondary diagnostics;
- gene search, clear-search and reset tools in the E. coli simulator;
- compact validated gene/objective inputs with canonical preview in the yeast simulator;
- Environmental Conditions search/validation by exchange **name or ID**;
- **Clear Search** without changing edited bounds;
- **Reset Environment** to restore every exchange to the model's real default lower/upper-bound state;
- model-aware Bound Sweeps, including the yeast glucose sweeps used by Missions 36 and 40;
- safe validation of unknown objectives, genes, exchanges and contradictory environmental edits before the solver runs.

The browser frontend sends simulations to the FastAPI backend. The backend keeps model templates cached but uses an isolated model copy for each request before applying objectives, bounds or knockouts.

## Golden Lab and yeast programme

Normal M35 unlocks the Golden Lab, Golden LabHero skin and yeast model. Easy reaches the Golden Lab after M27 but does not unlock the Golden LabHero skin.

The final Normal arc uses the Golden Lab scientists:

```text
Vale   -> M36
Voss   -> M37
Umbra  -> M38
Morbus -> M39
Mortis -> M40
```

The Golden Lab also contains optional historical/scientific tribute characters and exploration content that do not change mission progression.

## Saves and Final Results

The browser version persists the selected student campaign in namespaced `localStorage` and autosaves during play. Desktop saves use the platform-specific LabHero save directory.

The save includes campaign identity/progression, score state, hint usage, keys, skin, position and one-time exploration state. Starting an explicit New Game clears the LabHero student namespace without affecting unrelated browser storage.

At the end of a student campaign, Final Results report the student name, campaign mode, score, completed missions, hints and incorrect final-answer submissions. After closing the screen, press **F** while exploring to reopen it.

## Teacher Preview

Teacher Preview is intentionally isolated from the student's normal save.

### In-game access

From the title screen:

```text
SHIFT + T
```

Teacher Access authenticates server-side on Web, then lets the professor select **Normal** or **Easy** and a canonical mission number. Authentication is session-only and is not written to the student save or browser `localStorage`.

During an authenticated Teacher session, the professor can switch missions from Settings without re-entering credentials. Each mission switch creates a fresh isolated preview state.

### Web fallback route

The protected direct route remains available:

```text
/teacher/?mission=17&mode=normal
/teacher/?mission=25&mode=easy
```

The `/teacher/` route is protected server-side with HTTP Basic Auth. Credentials are configured at deployment time and are **not stored in the Pygbag/browser bundle**. A public query such as `/?teacher=1&mission=17` does not activate Teacher Preview.

### Desktop

```bash
python3 LabHero.py --teacher --mission 17 --mode normal
python3 LabHero.py --teacher --mission 25 --mode easy
```

Normal previews reproduce the full Normal predecessor chain. Easy previews reproduce only the curated Easy predecessors, so skipped Normal missions are not falsely marked as completed.

Teacher Preview uses a separate disposable save namespace and suppresses student Final Results. Leaving Teacher Preview restores the normal student namespace.

## Running from source

LabHero is currently developed/tested with Python 3.10 and the versions pinned in `requirements.txt`.

```bash
git clone https://github.com/hhtomaswt11/LabHero.git
cd LabHero
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 LabHero.py
```

## Web deployment

Two deployment paths are retained:

- **Podman / CEB-UMinho production path** — repository-root `deploy.sh`.
- **Docker Compose development path** — files under `deploy/`.

For the current Podman path, provide the Teacher password at deployment time:

```bash
LABHERO_TEACHER_PASSWORD='use-a-strong-password' ./deploy.sh
```

The username defaults to `teacher` and can be changed with `LABHERO_TEACHER_USER`.

For Docker-based local validation:

```bash
cd deploy
./local_smoke.sh
```

See [`deploy/README.md`](deploy/README.md) for Podman/Darwin, Docker development, nginx, HTTPS, Teacher authentication and verification details.

## Tests

Compile the project and run the complete regression suite from the repository root:

```bash
python3 -m compileall -q code backend/app tests main.py LabHero.py
python3 -m unittest discover -s tests -p "test_*.py"
```

Mission-specific tests can also be run directly, for example:

```bash
python3 tests/test_mission36.py
python3 tests/test_multimodel_yeast.py
python3 tests/test_easy2a_curated_progression.py
python3 tests/test_teacher1a_protected_access.py
python3 tests/test_golden_egg_easter_egg.py
```

Automated tests complement, rather than replace, manual playthrough QA. In particular, the curated Easy route and Teacher Preview should be validated end-to-end on the production Web deployment before a classroom release.

## Repository layout

```text
code/          game, campaign, mission and simulator UI logic
backend/app/   FastAPI simulation backend
data/          maps, mission material, books and model metadata
data/models/   metabolic model files and metadata
deploy/        browser/container/nginx deployment files
graphics/      sprites, portraits and map assets
audio/         game audio
font/          game font assets
installer/     desktop packaging/build support
tests/         regression and scientific-consistency tests
planning/      development/design history; not part of the runtime bundle
```

Historical patch manifests, old test plans and roadmaps are kept out of the repository root and, when retained, live under `planning/archive/` so they cannot be mistaken for current release instructions.

## Citation

If you use LabHero in research or teaching, see [`CITATION.cff`](CITATION.cff). The software citation currently identifies the original LabHero project/research metadata. Citation/authorship and licensing metadata for this extended release should be coordinated with the project supervisors before being changed.
