# Mission 23 — Nutrient Sensitivity Curve

## Scientist
Dr. Luna — Sensitivity and Response Curves

## Core idea
A two-point comparison shows only endpoints. A bound sweep shows how the predicted phenotype changes across a controlled perturbation range.

This mission varies ammonium uptake capacity while keeping the model, objective, genes and every unrelated environmental bound fixed. The first point is deliberately non-limiting: its lower bound is more permissive than the uptake the optimum actually uses. Tighter points reveal the onset and progression of nutrient limitation.

## Mission goal
Build a four-point pFBA response curve for the lower bound of `EX_nh4_e`, inspect growth, nutrient uptake, respiration and two tracked secretions, and identify the secretion that first appears when ammonium begins to limit growth.

## Controlled setup

- Method: `pFBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Genes: all active
- Base environment: every lower and upper bound at model default
- Bound Sweep variable: `EX_nh4_e` lower bound
- Sweep values: `-5`, `-4`, `-2`, `-1`
- Production Flux: `EX_ac_e`, `EX_co2_e`
- Exchange evidence: `EX_nh4_e`, `EX_glc__D_e`, `EX_o2_e`, `EX_pi_e`

The player configures the shared simulation setup and the Bound Sweep menu, then runs the visible experiment. The report contains four visible solver rows. The mission validator reads only those rows and does not launch hidden simulations.

## Expected model results

| NH4 lower bound | Growth | NH4 uptake | Glucose uptake | Oxygen uptake | Acetate | CO2 | Total absolute flux | Active reactions |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| -5 | 0.873922 | 4.765319 | 10.000000 | 21.799493 | 0.000000 | 22.809833 | 518.422086 | 48 |
| -4 | 0.733568 | 4.000000 | 10.000000 | 15.685282 | 6.124642 | 16.533360 | 438.178773 | 52 |
| -2 | 0.366784 | 2.000000 | 5.623591 | 8.459904 | 4.624462 | 8.883943 | 246.860750 | 47 |
| -1 | 0.183392 | 1.000000 | 3.277906 | 5.162174 | 3.244453 | 5.374194 | 151.863153 | 47 |

Uptake is displayed as a positive magnitude although the signed exchange flux is negative.

## Final question

> Which tracked secretion was absent at the non-limiting point but became active when ammonium first became limiting?

Accepted concise answers include:

- `acetate`
- `acetato`
- `EX_ac_e`
- `acetate exchange`

`CO2`, multiple candidates and unrelated routes are rejected.

## Scientific interpretation

The lower bound sets uptake capacity. At `-5`, the model uses only about `4.765` ammonium units, so the bound is not yet limiting. At `-4`, the constraint becomes active, growth falls and a new tracked secretion appears. Tighter ammonium bounds continue to reduce growth, but the secretion response is not monotonic.

This is a conditional prediction of this model, medium, objective and pFBA protocol. It is not a universal claim that nitrogen limitation always produces the same overflow phenotype.

## Robustness and persistence

- Mission 22 must be complete.
- Activation is idempotent.
- All four rows are required.
- Row order is irrelevant.
- Repeating the sweep replaces the same four points without duplication.
- Missing values are never interpreted as zero.
- Infeasible/error rows retain their status and contain no invented flux values.
- An invalid later sweep does not erase previously valid evidence.
- State is JSON serialisable.
- Desktop uses the local solver; browser mode performs four sequential calls to the existing `/simulate` endpoint and produces the same structured sweep contract.
