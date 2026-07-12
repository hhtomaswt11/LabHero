# Mission 07 — Objective Matters

## Theme
Advanced strain design: understanding the role of the FBA objective function.

## Learning goal
The player learns that changing the objective function changes what the metabolic model tries to optimize.

Until now, the default objective was usually biomass because it measures growth. In this mission, the player keeps the model unchanged and discovers which objective makes the model prioritize a target product instead of growth.

## Target product
- Ethanol

## Rules
- Change only the objective.
- Do not change genes.
- Do not change environmental conditions.
- Use the Mission 07 Objective Check in New Results as feedback.

## Task
1. Activate Mission 07 with Dr. Nova.
2. Go to the simulation computer.
3. Open the Objective menu.
4. Test objectives until the model targets ethanol production.
5. Keep genes and environmental conditions unchanged.
6. Run simulations and check the Mission 07 Objective Check in New Results.
7. Return to Dr. Nova only when the objective check says the setup is ready.
8. Deliver the objective results.

## Correct configuration
- Objective: ethanol exchange objective (`EX_etoh_e`)
- Product: ethanol
- Gene knockouts: none
- Environmental changes: none

## Pedagogical rationale
This mission introduces a key idea for later strain design missions: the objective function is not neutral. If the model is asked to optimize biomass, it prioritizes growth. If the model is asked to optimize a product exchange reaction, it prioritizes production of that compound.

The objective name is not given directly in the in-game mission prompt. The player must infer it from the target product and test objectives until the result confirms the correct choice.
