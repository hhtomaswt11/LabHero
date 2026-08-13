# Mission 37 — Fermentation Redundancy Cut Set

**NPC:** Voss  
**Model:** Yeast iMM904  
**Method:** pFBA  
**Objective:** `BIOMASS_SC5_notrace`

Mission 36 established a visible environmental transition: with oxygen uptake capped, increasing glucose availability eventually produced a fermentative solution. Voss now asks whether that phenotype is protected by genetic redundancy in the pyruvate-decarboxylase step.

Keep the yeast medium completely at model defaults and track exactly `EX_etoh_e` and `EX_succ_e`. This mission uses normal simulations only; the Bound Sweep is not part of the protocol. Record the following runs in any order:

- wild type;
- `PDC1`;
- `PDC1 + PDC5`;
- `PDC1 + PDC6`;
- `PDC5 + PDC6`;
- `PDC1 + PDC5 + PDC6`.

For each visible run, compare predicted growth, ethanol secretion, succinate secretion and the reactions disabled by the complete GPR evaluation. Use the wild-type run to calculate relative growth and ethanol retention.

Your interpretation must identify the **smallest tested knockout set** that satisfies all of the following visible criteria:

1. both `PYRDC` and `PYRDC2` are disabled by the GPR;
2. at least 50% of wild-type predicted growth is retained;
3. ethanol secretion is no more than 1% of the wild-type level.

Succinate is displayed as an additional carbon-rerouting signal and is not itself the answer criterion.

The conclusion is limited to iMM904, pFBA, the biomass objective, the model-default medium and the tested genotype series. The mission validator reads only visible simulation evidence; it does not launch a hidden optimisation.
