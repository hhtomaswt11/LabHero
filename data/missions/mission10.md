# Mission 10 — Multi-Knockout Robust Design

## Theme
Advanced strain design: robust production design using objective choice, environmental constraints, production-flux evidence, and a two-gene knockout pair.

## Learning goal
The player learns that a stronger strain-design problem may require several modelling decisions at once. A useful solution must target the correct product, use a biologically coherent environment, compare production fluxes, apply more than one genetic intervention, and preserve growth.

## Scenario
Dr. Nova gives the player the final challenge of the Advanced Strain Design Lab: build a robust *E. coli* design for lactate production. The player is not given the exact objective, environmental reaction, tracked fluxes, or knockout pair.

## Rules shown to the player
- Target product: lactate.
- Choose the objective that targets the product.
- Create a fermentation-like environmental context.
- Use exactly two knockouts from the candidate list.
- Track enough production fluxes to compare the target with a competing fermentation product.
- Do not change random extra environmental conditions.
- Keep growth viable.
- Use Mission 10 Robust Design Check in New Results as feedback.

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
- Gene knockouts: `b1241` / `adhE` and `b2297` / `pta`
- Production fluxes to track: lactate (`EX_lac__D_e`) and ethanol (`EX_etoh_e`)
- Extra environmental changes: none
- Number of knockouts: exactly two
- Growth threshold: at least 5.0
- Production improvement threshold: at least 50.0 flux units over the anaerobic no-knockout baseline

## Pedagogical explanation
Mission 07 introduced objective selection. Mission 08 added environmental constraints. Mission 09 combined objective, environment and one knockout. Mission 10 increases the difficulty by requiring a two-knockout design and explicit production-flux evidence, forcing the player to iterate through multiple candidate pairs and interpret feedback rather than following a direct recipe.
