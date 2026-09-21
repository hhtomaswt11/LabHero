# Mission 22 — Phenotype Equivalence Audit

## Scientist
Dr. Vega — Comparative Experiment Lab

## Core idea
Different interventions can act through different mechanisms and still produce the same recorded phenotype under one controlled model protocol.

Mission 22 compares:

- an environmental intervention that closes acetate export;
- a genetic intervention that disables `PTAr` through the complete `b2297 OR b2458` GPR rule.

The mission asks whether the recorded growth, uptake and secretion outputs distinguish the two interventions beyond numerical tolerance.

## Shared protocol

- Method: `FBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Glucose: model default
- Oxygen: close only the lower bound of `EX_o2_e`
- Production Flux panel:
  - `EX_ac_e`
  - `EX_etoh_e`
  - `EX_for_e`
  - `EX_succ_e`
  - `EX_lac__D_e`
- Every unrelated environmental bound remains at the model default.

## Run A — environmental intervention

- Keep every gene active.
- Close the upper bound of `EX_ac_e`.
- Run the simulation and inspect the visible growth, Exchange Flux and Production Flux evidence.

## Run B — genetic intervention

- Restore the upper bound of `EX_ac_e` to its model default.
- Disable exactly:
  - `b2297 / pta`
  - `b2458 / eutD`
- Keep oxygen uptake closed and every unrelated bound at the model default.
- Confirm that the complete GPR disables `PTAr`.
- Run the simulation with the same complete panel.

The two runs may be recorded in either order. Repeating a valid run updates its slot without duplicating evidence. A later invalid attempt does not erase valid evidence.

## Expected model outputs

Both interventions should remain viable and produce approximately:

- Growth: `0.189173`
- Glucose uptake: `10.000000`
- Oxygen uptake: `0.000000`
- Acetate: `0.000000`
- Ethanol: `16.584256`
- Formate: `3.956347`
- Succinate: `0.000000`
- D-lactate: `0.000000`

The report calculates genetic minus environmental differences for every counted phenotype output: biomass, glucose uptake, oxygen uptake and the five tracked secretions. Intervention settings and GPR-disabled reaction labels document the mechanisms but are not included in the phenotype-output count. The numerical difference tolerance is shown in the report.

## Final question

`How many recorded phenotype outputs differed beyond tolerance between the environmental and genetic interventions?`

Accepted concise forms include:

- `0`
- `zero`
- `none`
- `nenhum`

The mission report displays the values and differences but does not state the answer directly.

## Scientific interpretation

Observational equivalence under this limited phenotype panel does not prove mechanistic equivalence. One intervention closes an exchange bound; the other disables an internal reaction through a two-gene GPR.

All validated evidence comes from the same visible solver results. The mission does not launch a hidden simulation.

## Progression

This is Dr. Vega's final mission. Mission 21 asked for the largest change between two runs; Mission 22 asks whether any recorded output distinguishes two different mechanisms. After completion, Dr. Luna begins Mission 23.
