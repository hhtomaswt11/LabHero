# Mission 25 — Final Controlled Report

## Scientist
Dr. Vega

## Lab
Laboratory 5 — Comparative Experiment Lab

## Main idea
This is the final Dr. Vega mission. The player must make a complete controlled comparison: two simulations, one variable changed, and clear evidence from the results.

A controlled comparison means the player changes only one thing between Run A and Run B. In this mission, the changed variable is oxygen availability.

## Scientific concept
Oxygen availability can strongly affect cell growth and the product/byproduct profile. The player should compare an aerobic baseline with an oxygen-limited setup and use Production Flux evidence to see how exported products change.

## Required comparison
Run A is the baseline aerobic setup.
Run B is the oxygen-limited setup.

The player must keep method, objective, genes and tracked products unchanged between both runs.

## How to pass
Run A — aerobic baseline:
- Method: FBA
- Objective: BIOMASS_Ecoli_core_w_GAM
- Genes: no knockouts
- Environment: unchanged
- Production Flux: track EX_ac_e, EX_etoh_e, EX_for_e, EX_lac__D_e, EX_succ_e
- Run Simulation

Run B — oxygen-limited setup:
- Method: FBA
- Objective: BIOMASS_Ecoli_core_w_GAM
- Genes: no knockouts
- Environment: close only the lower bound of EX_o2_e
- Production Flux: track EX_ac_e, EX_etoh_e, EX_for_e, EX_lac__D_e, EX_succ_e
- Run Simulation

Then:
- Open New Results -> Compare Runs
- Return to Dr. Vega
- Deliver Final Report

## Completion check
The mission is completed when:
- the baseline run is detected
- the oxygen-limited run is detected
- the full production-flux panel is tracked in both runs
- growth decreases after oxygen limitation
- at least two tracked production fluxes change between the runs

## Difficulty progression
Mission 21 introduced simple environment comparison.
Mission 22 compared normal strain vs knockout.
Mission 23 studied a graded ammonium-sensitivity curve and the onset of a new secretion.
Mission 24 compared different simulation methods.
Mission 25 combines controlled comparison with production-flux evidence, closing Dr. Vega's section.
