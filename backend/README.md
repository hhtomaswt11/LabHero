# LabHero backend

FastAPI service that wraps MEWpy simulations for the LabHero web version.

## Quick start

```
docker compose up --build
```

Then:

- Health check: http://localhost:8002/health
- Interactive API docs: http://localhost:8002/docs
- Simulate endpoint: `POST http://localhost:8002/simulate`

Source code is bind-mounted into the container and uvicorn runs with `--reload`,
so edits under `app/` reload automatically.

## Status

The `/simulate` endpoint is implemented and uses MEWpy/Cobra to run simulations
with the bundled `e_coli_core.xml.gz` model. It accepts the simulation method,
objective reaction, gene knockouts and environmental conditions, then returns the
simulation result with an `ok`, `infeasible` or `error` status.
