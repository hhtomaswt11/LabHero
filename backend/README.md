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

## ROOM reference contract

ROOM runs use an explicit wild-type pFBA reference built before gene knockouts.
The reference and mutant use independent model copies with the same objective
and environmental constraints; only the mutant receives the GPR-derived
reaction closures. Mission 33 uses integer ROOM with `delta=0.03` and
`epsilon=0.001`. The binary problem is solved with SciPy/HiGHS and a 12-second
safety limit rather than the default GLPK MILP path, which can stall on the
aerobic cut-set case.

A successful ROOM response also exposes:

- `reference_method` and `reference_objective_reaction`;
- `reference_primary_objective_flux` and `reference_cytbd_flux`;
- `reference_uses_same_environment`;
- `reference_has_no_gene_knockouts`;
- `room_delta`, `room_epsilon` and `room_linear`;
- `room_solver` and `room_time_limit_seconds`.

The ROOM `method_score` is the significant-flux-change criterion and is kept
separate from the selected objective-reaction flux.

### GPR-disabled reactions

Successful `/simulate` responses include the additive field:

```json
{
  "gpr_disabled_reactions": ["AKGDH", "PDH"]
}
```

The field is evaluated by the backend from the complete model GPR after applying the requested gene knockouts. Browser clients should use this visible server result instead of reimplementing GPR parsing. Existing clients remain compatible because the field is optional and no endpoint changed.
