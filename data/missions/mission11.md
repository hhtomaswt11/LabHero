# Mission 11 — Anaerobic Secretion Fingerprint

## Theme
Flux Diagnostics & Pathway Evidence

## Learning goal
Interpret a metabolic simulation through both the biomass objective and a complete panel of exchange fluxes. The player must distinguish positive predicted secretion from zero flux and identify the dominant tracked product.

## Scenario
After completing Dr. Nova's strain-design laboratory, the player starts Dr. Almeida's Flux Diagnostics Lab. The first task is not to redesign the strain, but to diagnose one controlled anaerobic biomass-optimal solution.

## Controlled experiment

- Method: `FBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Genes: all active
- Glucose: model-default supply (`EX_glc__D_e` lower bound `-10`)
- Oxygen: uptake disabled by closing only the lower bound of `EX_o2_e`
- All remaining environmental bounds: model default

## Required Production Flux panel

- `EX_for_e` — formate
- `EX_ac_e` — acetate
- `EX_etoh_e` — ethanol
- `EX_lac__D_e` — D-lactate
- `EX_succ_e` — succinate

All five values must be selected and numerically present in the same visible solution.

## Expected fingerprint

| Evidence | Expected result |
|---|---:|
| Predicted biomass flux | approximately `0.211663` |
| Formate secretion | approximately `17.804674` |
| Acetate secretion | approximately `8.503585` |
| Ethanol secretion | approximately `8.279455` |
| D-lactate secretion | approximately `0` |
| Succinate secretion | approximately `0` |
| Glucose uptake | approximately `10` |
| Oxygen uptake | approximately `0` |

The three positive products are formate, acetate and ethanol. D-lactate and succinate are zero in this solution. Formate is the dominant tracked product.

## Player interpretation
After recording the complete fingerprint, the player must submit:

- `formate`, or
- `EX_for_e`.

The answer is accepted only after valid visible evidence has been recorded.

## Scientific interpretation
A positive exchange flux represents secretion predicted in this specific model solution. A zero exchange flux does not mean that *E. coli* can never produce the compound; it means that this model, objective and set of constraints do not predict secretion in this solution.

The model predicts positive growth under these conditions. This is a model result, not a direct experimental claim about viability.

## Engineering and web-readiness
Mission validation consumes the same serialisable visible-result structure on desktop and browser: objective value, tracked production fluxes and medium fluxes. It launches no hidden local or backend simulations. This keeps the mission compatible with the future online LabHero interface and web-service deployment.
