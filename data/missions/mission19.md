# Mission 19 — Re-optimisation vs Minimal Adjustment

## Theme
Controlled comparison of FBA and lMOMA after the same genetic perturbation.

## Learning goal
The mission separates two modelling questions. FBA re-optimises the selected objective after a perturbation, whereas lMOMA predicts a post-perturbation state by minimising total absolute flux adjustment from a reference solution. Biomass must be read from the biomass reaction; the lMOMA adjustment score is a different quantity.

## Controlled protocol
1. Record a wild-type FBA baseline with the biomass objective, every gene active, the default medium and the complete product/byproduct panel.
2. Disable only `b0728 / sucC` and repeat the setup with FBA.
3. Keep the same knockout, objective, medium and panel, changing only the method to Linear MOMA (`lMOMA`). The solver first computes an explicit wild-type FBA reference in that same medium, then applies the GPR-derived knockout to the mutant model.

The complete GPR rule makes the `b0728` knockout disable `SUCOAS`. The previous target `b2296 / ackA` is not used because its isolated knockout leaves `ACKr` functional through alternative genes.

## Required Production Flux panel
- `EX_ac_e`
- `EX_etoh_e`
- `EX_for_e`
- `EX_lac__D_e`
- `EX_succ_e`

## Expected visible evidence
- Wild-type FBA biomass: approximately `0.874`.
- `b0728` FBA biomass: approximately `0.858`.
- `b0728` lMOMA biomass: approximately `0.803`.
- lMOMA adjustment score: approximately `39.785`; this is not biomass.
- lMOMA introduces visible acetate and D-lactate secretion that are absent from the FBA mutant profile.

## Final interpretation
The final field asks which method predicts the lower viable biomass response for the same knockout. The answer is derived from the two visible mutant biomass values and is deliberately short.

## Architecture
The mission validates the same structured result shown to the player. The wild-type reference is an internal, required step of the lMOMA method rather than a hidden mission-validation run. No hidden simulation is used by the mission validator, which never launches a second solver call. Desktop and FastAPI use the same explicit-reference workflow, JSON-serialisable result contract and scientific rules.
