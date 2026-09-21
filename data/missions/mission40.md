# Mission 40 — Final Rescue Robustness Certification

**Scientist:** Dr. Mortis  
**Model:** Yeast iMM904  
**Method:** pFBA  
**Objective:** `BIOMASS_SC5_notrace`

## Purpose

Mission 39 showed that opening acetaldehyde uptake can rescue the vulnerable `PDC1 + PDC5 + PDC6 + FRD1` background under the default medium. The final mission asks whether that rescue is robust when glucose availability changes.

This is a matched-curve experiment. The genotype, objective, method, tracked products and glucose sweep must be identical between the two curves. The only permitted base-environment difference is acetaldehyde availability.

## Fixed setup

For **both** curves:

- Genes knocked out: `PDC1 + PDC5 + PDC6 + FRD1`
- Production Flux: exactly `EX_etoh_e`, `EX_succ_e`, `EX_pyr_e`
- Bound Sweep: **ON**
- Sweep variable: `EX_glc__D_e` lower bound
- Yeast glucose preset: `-0.5, -1, -2, -10`

Record the curves in any order.

### Curve A — no rescue

Keep the base environment completely model-default.

### Curve B — acetaldehyde rescue

In **Lower bounds to open**, enter only:

`EX_acald_e`

Do not change any other environmental bound.

## Final interpretation

Compare the two curves at the same glucose lower bound. Identify every tested bound where the rescue curve simultaneously has:

- acetaldehyde uptake at least `1.0`;
- growth at least `1.20x` the matched no-rescue growth;
- ethanol secretion at least `5.0`.

Enter all qualifying tested glucose lower bounds together.

The conclusion is specific to iMM904, pFBA, this genotype and the tested bounds. It is a constraint-based robustness audit, not a physiological supplementation recommendation.
