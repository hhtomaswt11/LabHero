# Mission 10 — Two-Gene Redundancy and Flux Redirection

## Theme
Advanced strain design with OR-type GPR redundancy, controlled two-gene knockouts, and visible growth/product evidence.

## Learning goal
The player learns that a single knockout may have no effect when another gene can satisfy the same OR-type GPR. An appropriate pair can disable a reaction, redirect flux and improve a target product, but the design must still retain sufficient predicted growth.

## Scenario
Dr. Nova asks the player to compare a no-knockout anaerobic reference with every pair formed by four candidate genes. The objective, medium and tracked exchanges remain identical so differences can be attributed to the pair.

## Controlled setup
- Method: `FBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Carbon source: default glucose uptake (`EX_glc__D_e` lower bound remains `-10`)
- Oxygen: uptake disabled by closing only the lower bound of `EX_o2_e`
- Remaining environmental bounds: model default
- Production Flux: track `EX_etoh_e` and `EX_ac_e`
- Baseline: all genes active
- Pair trials: exactly two candidate genes disabled

## Candidate genes
- `b2297 / pta`
- `b2458 / eutD`
- `b1241 / adhE`
- `b0351 / mhpF`

## Required pair screen
- `b2297 + b2458`
- `b2297 + b1241`
- `b2297 + b0351`
- `b2458 + b1241`
- `b2458 + b0351`
- `b1241 + b0351`

## Operational criteria
A pair is eligible when it:
- retains at least 80% of the no-knockout reference growth;
- increases ethanol secretion by at least 5.0 in the same biomass-optimal solution.

These are mission-specific operational criteria, not universal biological definitions.

## Expected evidence
The no-knockout anaerobic reference is approximately:
- growth `0.211663`;
- ethanol `8.279455`;
- acetate `8.503585`.

The pair `b2297 + b2458` makes the `PTAr` rule `b2297 OR b2458` false and gives approximately:
- growth `0.189173` (`89.4%` of baseline);
- ethanol `16.584256`;
- acetate `0.000000`.

The pair `b1241 + b0351` blocks `ACALD` and strongly changes fermentation, but retains only about `65.2%` of baseline growth, so it is not eligible. Cross-pairs leave the relevant OR rules satisfied and reproduce the baseline phenotype.

## Evidence and delivery
The player must record the baseline and all six pairs. Runs may be completed in any order. Repeated pairs update the same record; invalid runs do not erase valid evidence. Once the comparison is complete, the player submits the winning pair as gene ids or names, for example `b2297 + b2458` or `pta + eutD`.
