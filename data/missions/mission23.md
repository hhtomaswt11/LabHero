# Mission 23 — Objective Comparison

## Scientist
Dr. Vega — Comparative Experiment Lab

## Core idea
This mission compares the same model setup under two different objectives.

The objective is what the simulation tries to maximize. If the objective is biomass, the model prioritizes growth. If the objective is a product exchange reaction, the model prioritizes secretion/export of that product.

## Mission goal
Compare a normal growth objective with an ethanol-production objective while keeping everything else unchanged.

## How to pass

### Run A — growth objective
- Simulation Method: `FBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Genes: no knockouts
- Environmental Conditions: unchanged
- Production Flux: select `EX_etoh_e`
- Run Simulation

### Run B — product objective
- Simulation Method: `FBA`
- Objective: `EX_etoh_e`
- Genes: no knockouts
- Environmental Conditions: unchanged
- Production Flux: select `EX_etoh_e`
- Run Simulation

Then open:

`New Results -> Compare Runs`

Return to Dr. Vega and choose:

`Deliver Objective Comparison`

## Success condition
The mission is completed when the game detects:
- one run using the biomass objective;
- one run using the ethanol objective;
- no gene knockouts;
- no environmental changes;
- ethanol tracked in Production Flux in both runs;
- ethanol production increases when the ethanol objective is used.

## Difficulty progression
Mission 21 compared two environments. Mission 22 compared two strains. Mission 23 compares two objectives, teaching the player that changing the optimization target changes the interpretation of the simulation result.
