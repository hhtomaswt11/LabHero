# Mission 26 — Oxygen Sensitivity Sweep

## Scientist
Dr. Luna

## Lab Theme
Comparative Experiment Lab — sensitivity to medium conditions.

## Concept
This mission introduces **Bound Sweep**. Instead of testing only two states, the simulator tests several values for one environmental bound and shows the trend.

For exchange reactions, changing the lower bound changes how much the model can consume from the medium. Oxygen is a good first example because the cell can behave differently when oxygen is abundant, limited, or blocked.

## Mission Goal
Test how growth and product/byproduct secretion change when oxygen availability is progressively restricted.

## Required Setup
- Simulation Method: `FBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Genes: no knockouts
- Environment: unchanged before running the sweep
- Bound Sweep variable: oxygen lower bound (`EX_o2_e`)
- Sweep values: `-20`, `-10`, `-5`, `0`

## What the Bound Sweep Report Shows
For each oxygen level, the report shows:
- growth/objective value
- oxygen uptake
- selected product/byproduct fluxes
- whether the profile changes as oxygen becomes more limited

## Success Criteria
The mission is ready to deliver when:
- the correct oxygen lower-bound sweep was run
- all sweep points produced valid results
- growth shows a clear measurable decrease across the oxygen series
- oxygen uptake decreases
- at least two tracked products/byproducts change enough to show a metabolic shift

## Optional Hint
Do not search for one isolated “correct” value. Read the trend from left to right: as oxygen becomes more restricted, growth and secretion patterns should change.
