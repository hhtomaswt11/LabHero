# Mission 13 — Primary Objective and Flux Parsimony

## Theme
Controlled FBA-versus-pFBA comparison and method-aware interpretation.

## Learning goal
Understand that pFBA preserves the primary metabolic optimum and introduces a secondary criterion that minimises total absolute flux. The pFBA score must not be interpreted as extra product formation.

## Scenario
Dr. Almeida asks the player to keep the oxygen-constrained succinate problem from Mission 12 unchanged and compare two visible solver results:

- one FBA reference;
- one pFBA run.

The player must determine what remains unchanged and what the pFBA secondary criterion means.

## Controlled setup
Both runs use:

- objective `EX_succ_e`;
- all genes active;
- default glucose supply;
- only the lower bound of `EX_o2_e` closed;
- complete panel `EX_succ_e`, `EX_ac_e`, `EX_for_e`, `EX_etoh_e`, `EX_lac__D_e`.

Only the simulation method changes.

## Expected evidence
The two methods preserve approximately:

- succinate `13.906`;
- acetate `5.665`;
- formate `0`;
- ethanol `0`;
- D-lactate `0`;
- biomass `0`;
- glucose uptake `10`;
- oxygen uptake `0`.

The pFBA result also reports the secondary parsimony criterion, approximately the total absolute flux of the returned solution. Equality between the FBA and pFBA total fluxes is valid if the FBA solver already returned a parsimonious optimum.

## Required interpretation
The player must answer that pFBA minimises:

- total flux;
- total absolute flux;
- the sum of absolute fluxes.

`Succinate` is not accepted because it is the primary objective, not the secondary criterion.

## Scientific note
The value near `343.047` is not succinate secretion. The primary `EX_succ_e` flux remains near `13.906`. All values must come from the two visible solver results; no hidden simulations are used.

## Web compatibility
The mission consumes a structured result contract containing separate fields for the primary objective flux, method score, total absolute flux, active-reaction count, biomass, exchange fluxes and medium fluxes. The mission state is JSON-serialisable and independent of Pygame.
