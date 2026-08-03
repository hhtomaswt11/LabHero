# Mission 17 — Essential Uptake Routes

## Theme
Controlled nutrient-uptake screening and interpretation of signed exchange fluxes.

## Learning goal
Show that closing an exchange lower bound blocks uptake capacity, but does not necessarily block positive secretion. Under the controlled default medium, the player identifies which candidate lower-bound closures collapse biomass growth.

## Phase A — baseline
Use FBA with `BIOMASS_Ecoli_core_w_GAM`, all genes active and every environmental bound at model default. Record predicted growth and the signed exchange fluxes for:

- `EX_nh4_e`
- `EX_pi_e`
- `EX_h2o_e`
- `EX_h_e`
- `EX_co2_e`

Negative exchange flux represents uptake in the displayed solution; positive exchange flux represents secretion.

## Phase B — five controlled trials
Repeat the baseline setup five times. In each run, close only the lower bound of one candidate exchange and keep every other lower and upper bound at model default.

The mission compares every growth result with the visible baseline. A value at or below 1% of baseline is classified as collapse; a value at or above 99% is classified as baseline-like preservation.

## Final question
`Which two candidate uptake routes caused growth to collapse when their lower bounds were closed?`

The answer field accepts the two reaction identifiers or common names in either order, for example `nh4 and pi` or `ammonium and phosphate`. The report presents the numerical evidence but does not print the final pair as an answer.

## Scientific scope
The conclusion is specific to this model, biomass objective and controlled medium. It is not a universal experimental claim. All values come from visible solver results; no hidden simulation is used.
