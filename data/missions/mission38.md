# Mission 38 — Background-Dependent Compensation Audit

**NPC:** Umbra  
**Model:** Yeast iMM904  
**Method:** pFBA  
**Objective:** `BIOMASS_SC5_notrace`

Mission 37 showed that removing `PDC1`, `PDC5` and `PDC6` strongly suppresses ethanol while the model still predicts substantial growth and a new succinate-secreting state. Umbra now asks whether genes that appear harmless in wild type remain harmless after that compensatory state has been created.

Keep the medium completely model-default, leave Bound Sweep off, and track exactly `EX_etoh_e`, `EX_succ_e` and `EX_pyr_e`. Record the following six normal simulations in any order:

- wild type;
- `FRD1`;
- `MAE1`;
- `PDC1 + PDC5 + PDC6`;
- `PDC1 + PDC5 + PDC6 + FRD1`;
- `PDC1 + PDC5 + PDC6 + MAE1`.

Use wild type to determine whether each candidate is generally growth-limiting. Use the complete PDC cut-set run as the matched background reference for the combined genotypes.

Your interpretation must identify the candidate that satisfies all visible criteria:

1. the candidate alone retains at least 95% of wild-type predicted growth;
2. in the PDC-cut-set background, the combined genotype retains no more than 60% of the PDC-background growth;
3. its succinate secretion is no more than 10% of the PDC-background level;
4. pyruvate secretion is at least 1.0 in the same combined run.

The GPR-disabled reaction lists are part of the evidence and must match the tested genotype. The conclusion is conditional on iMM904, pFBA, the biomass objective, the model-default medium and this controlled genotype matrix. The validator reads only the visible simulation outputs and does not launch a hidden optimisation.
