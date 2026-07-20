# Mission 24 — Method Comparison

## Lab
Laboratory 5 — Comparative Experiment Lab

## Scientist
Dr. Vega

## Concept
This mission compares two simulation methods while keeping the biological setup unchanged.

- **FBA** optimizes the chosen objective and returns one valid flux distribution.
- **pFBA** keeps the same objective goal but prefers a simpler/parsimony flux distribution.

The key idea is controlled comparison: change only the method and observe what changes in the flux profile.

## How to pass

### Run A — FBA baseline
- Method: `FBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Genes: no knockouts
- Environment: unchanged
- Production Flux: track:
  - `EX_ac_e`
  - `EX_etoh_e`
  - `EX_for_e`
  - `EX_lac__D_e`
  - `EX_succ_e`

Run the simulation.

### Run B — pFBA method test
- Method: `pFBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Genes: no knockouts
- Environment: unchanged
- Production Flux: track the same fluxes as Run A:
  - `EX_ac_e`
  - `EX_etoh_e`
  - `EX_for_e`
  - `EX_lac__D_e`
  - `EX_succ_e`

Run the simulation.

Then open **New Results → Compare Runs** and return to Dr. Vega to deliver the Method Comparison.

## Success condition
The mission is completed when the game detects:

- one valid FBA run;
- one valid pFBA run;
- the same biomass objective in both runs;
- no gene knockouts;
- unchanged environment;
- the required production-flux panel tracked in both simulations.
