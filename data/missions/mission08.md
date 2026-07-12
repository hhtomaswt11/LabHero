# Mission 08 — Objective Under Constraints

## Theme
Advanced strain design: objective functions and environmental constraints.

## Learning goal
The player learns that choosing an objective is only part of a constraint-based simulation. The model is also limited by the environmental conditions. The player must discover a coherent setup through testing instead of being given the exact answer immediately.

## Scenario
Dr. Nova asks the player to configure *E. coli* to produce lactate in a fermentation-like context.

## Rules shown to the player
- Target product: lactate.
- Use the Objective menu to target the product.
- Use Environmental Conditions to create the right biological context.
- Do not use gene knockouts in this mission.
- Run simulations and use the Mission 08 Constraint Check to reason about the setup.

## Intended solution for validation
- Objective: `EX_lac__D_e`
- Environmental condition: close the lower bound of oxygen uptake (`EX_o2_e`)
- Gene knockouts: none

## Pedagogical explanation
Mission 07 introduced the idea that the objective determines what FBA optimizes. Mission 08 adds a second layer: constraints matter too. The player must connect lactate production with fermentation and infer that oxygen availability is the key environmental variable to test.
