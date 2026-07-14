# Mission 09 — Integrated Strain Design

## Theme
Advanced strain design: combining objective functions, environmental constraints, and gene knockouts.

## Learning goal
The player learns that a real strain-design problem usually requires more than one modelling decision. A good design must target a product, use biologically coherent constraints, and redirect metabolism genetically without destroying growth.

## Scenario
Dr. Nova gives the player an integrated design challenge: configure *E. coli* to improve lactate production while keeping the strain viable.

## Rules shown to the player
- Target product: lactate.
- Choose the objective that targets the product.
- Create a fermentation-like environmental context.
- Use exactly one knockout from the candidate list.
- Do not change random extra environmental conditions.
- Keep growth above a minimum viability threshold.
- Use Mission 09 Design Check in New Results as feedback.

## Candidate genes
- `b0903`
- `b2297`
- `b0723`
- `b3115`
- `b0728`
- `b1241`

## Intended solution for validation
- Objective: lactate exchange objective (`EX_lac__D_e`)
- Environmental condition: close the lower bound of oxygen uptake (`EX_o2_e`)
- Gene knockout: `b1241` / `adhE`
- Extra environmental changes: none
- Number of knockouts: exactly one
- Growth threshold: at least 8.0
- Production improvement threshold: at least 100.0 flux units over the anaerobic no-knockout baseline

## Pedagogical explanation
Mission 07 introduced objective selection. Mission 08 added environmental constraints. Mission 09 combines objective, environment, and one genetic intervention in an integrated challenge before the final double-knockout task. The exact setup is not revealed in the in-game prompt: the player must iterate through simulations, interpret the feedback, and identify the configuration that improves production without killing growth.
