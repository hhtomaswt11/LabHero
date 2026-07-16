# Mission 19 — Perturbation Method Challenge

## Theme
Perturbation-response simulation and method choice.

## Learning goal
This mission introduces lMOMA as a way to study how a metabolic model responds after a genetic perturbation. The player must keep the medium unchanged, use one candidate knockout, and justify the mutant response with pathway flux evidence.

## Main concepts
- FBA asks for an optimal solution under constraints.
- lMOMA is useful after perturbations because it represents a more conservative metabolic adjustment.
- A single knockout can change central carbon metabolism without changing the medium.
- Flux evidence helps interpret the response beyond the objective value.

## Mission setup
- Method: lMOMA
- Objective: biomass
- Environment: unchanged
- Genetic change: exactly one candidate knockout
- Evidence: track central carbon pathway products

## Candidate genes
- b0118
- b1276
- b0720
- b1611
- b3236
- b0728
- b2296

## Required flux evidence
- EX_ac_e
- EX_etoh_e
- EX_for_e
- EX_lac__D_e
- EX_succ_e

## Intended educational role
Mission 19 prepares the player for final robustness challenges by showing that the simulation method itself is part of the modelling decision.
