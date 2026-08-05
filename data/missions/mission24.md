# Mission 24 — Export Capacity Thresholds

## Scientist
Dr. Luna — Sensitivity and Response Curves

## Core idea
Mission 23 varied an uptake lower bound. Mission 24 advances to a graded export upper bound and asks when the restriction becomes binding and which compensatory routes appear in sequence.

An upper bound can be present without affecting the optimum. It becomes binding only when the solution reaches the cap. A tighter cap can then redirect flux through other exchanges.

## Mission goal
Build a four-point pFBA curve for the upper bound of `EX_co2_e`, inspect growth, respiration and three tracked secretions, and identify the first compensatory secretion that appears at the first binding cap before acetate appears at a tighter cap.

## Controlled setup

- Method: `pFBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Genes: all active
- Base environment: every lower and upper bound at model default
- Bound Sweep variable: `EX_co2_e` upper bound
- Sweep values: `25`, `20`, `10`, `0`
- Production Flux: `EX_co2_e`, `EX_for_e`, `EX_ac_e`
- Exchange evidence: `EX_glc__D_e`, `EX_o2_e`

The player configures the shared simulation setup and the Bound Sweep menu, then runs one visible four-point experiment. The validator reads only the displayed sweep rows and never launches a hidden simulation.

## Expected model results

| CO2 upper bound | Growth | Glucose uptake | Oxygen uptake | CO2 | Formate | Acetate | Total absolute flux | Active reactions |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 25 | 0.873922 | 10.000000 | 21.799493 | 22.809833 | 0.000000 | 0.000000 | 518.422086 | 48 |
| 20 | 0.842120 | 10.000000 | 21.107998 | 20.000000 | 4.163147 | 0.000000 | 516.338131 | 51 |
| 10 | 0.681852 | 10.000000 | 15.868330 | 10.000000 | 13.313238 | 3.835115 | 463.432427 | 55 |
| 0 | 0.461670 | 10.000000 | 7.484524 | 0.000000 | 16.036520 | 12.158449 | 370.683878 | 50 |

Uptake is displayed as a positive magnitude although the signed glucose and oxygen exchange fluxes are negative.

## Final question

> Which tracked secretion became active at the first binding CO2-export cap, before acetate appeared at a tighter cap?

Accepted concise answers include:

- `formate`
- `formato`
- `EX_for_e`
- `formate exchange`

`acetate`, `CO2`, multiple candidates and unrelated routes are rejected.

## Scientific interpretation

At the upper bound `25`, predicted CO2 export is only about `22.810`, so the cap is non-binding. At `20`, the solution reaches the cap, growth decreases and one previously absent tracked secretion becomes active while acetate remains zero. At `10`, acetate also becomes active. This establishes a sequential compensatory response within this model and protocol.

This is a conditional prediction of the model-default medium, biomass objective and pFBA formulation. It is not a universal claim that restricting CO2 export produces the same sequence experimentally.

## Robustness and persistence

- Mission 23 must be complete.
- Activation is idempotent.
- All four rows are required.
- Row order is irrelevant.
- Repeating the sweep replaces the same four points without duplication.
- Missing values are never interpreted as zero.
- Infeasible/error rows retain their status and contain no invented flux values.
- pFBA primary and secondary diagnostics are required in every row.
- An invalid later sweep does not erase previously valid evidence.
- State is JSON serialisable.
- Desktop uses the local solver; browser mode performs four sequential calls to the existing `/simulate` endpoint and produces the same structured sweep contract.
- Completing Mission 24 ends Dr. Luna's block and directs the player to Dr. Smith at Mission 25.
