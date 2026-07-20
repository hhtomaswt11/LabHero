# Mission 22 — Knockout Comparison

## Scientist
Dr. Vega — Comparative Experiment Lab

## Core idea
Compare two controlled simulations:

- Run A: normal strain
- Run B: the same setup, but with one gene knockout

The goal is to show that changing one gene can redirect metabolism toward a product, while keeping the cell viable.

## Concept
A knockout disables a gene. In metabolic models, this can block reactions connected to that gene. Sometimes this reduces growth, but sometimes it redirects flux toward a useful product.

## How to pass

### Run A — baseline strain
- Method: FBA
- Objective: BIOMASS_Ecoli_core_w_GAM
- Genes: no knockouts
- Environment: unchanged
- Production Flux: track EX_etoh_e

Run the simulation.

### Run B — knockout strain
- Method: FBA
- Objective: BIOMASS_Ecoli_core_w_GAM
- Genes: turn off b2297 / pta
- Environment: unchanged
- Production Flux: track EX_etoh_e

Run the simulation.

Then open:

- New Results
- Compare Runs

Finally, return to Dr. Vega and deliver the Knockout Comparison.

## Candidate genes
- b0728
- b1241
- b2975
- b2297
- b0723

## Success criteria
- The baseline run is valid.
- The knockout run uses only b2297 / pta.
- Both runs track ethanol production.
- Ethanol production increases in the knockout run.
- Growth remains viable.
