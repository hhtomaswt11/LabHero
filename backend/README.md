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
objective reaction, gene knockouts and environmental conditions, then returns a
method-aware structured result with an `ok`, `infeasible` or `error` status.

For successful simulations, the contract separates:

- `primary_objective_flux`: flux of the selected objective reaction;
- `method_score`: scalar criterion reported by the selected algorithm;
- `method_score_name`: semantic name of that criterion;
- `total_absolute_flux`: sum of the absolute values of the returned flux vector;
- `active_reaction_count`: number of non-negligible reaction fluxes;
- `fluxes`: complete reaction-flux mapping.

This distinction is essential for pFBA: its secondary score is not the amount of
product secreted. The browser and desktop clients consume the same fields rather
than parsing solver strings differently.
