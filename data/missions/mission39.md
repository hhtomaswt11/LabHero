# Mission 39 — Pathway Bypass Rescue

**NPC:** Morbus  
**Model:** Yeast iMM904  
**Method:** pFBA  
**Objective:** `BIOMASS_SC5_notrace`

Mission 38 showed that the `PDC1 + PDC5 + PDC6 + FRD1` background is much more fragile than the corresponding single knockouts: growth falls strongly, succinate almost disappears and pyruvate is secreted. Morbus now asks whether a controlled extracellular supplement can bypass part of that blocked state.

Keep the genotype fixed at `PDC1 + PDC5 + PDC6 + FRD1`, leave Bound Sweep off, and track exactly `EX_etoh_e`, `EX_succ_e` and `EX_pyr_e`. Record these four normal simulations in any order:

- completely model-default environment;
- open only the lower bound of `EX_pyr_e`;
- open only the lower bound of `EX_etoh_e`;
- open only the lower bound of `EX_acald_e`.

Do not change any upper bound and do not combine supplements. The exchange report is part of the visible evidence: opening a lower bound makes uptake possible, but does not force the optimal solution to consume that metabolite.

Use the default-medium run as the reference. Your interpretation must identify the tested lower-bound opening that simultaneously:

1. is actually used at substantial uptake (at least 1.0 in the visible exchange report);
2. produces at least a two-fold increase in predicted growth relative to the default-medium reference;
3. restores ethanol secretion to at least 5.0.

The three tested metabolites deliberately bracket the blocked pyruvate-decarboxylase step: pyruvate is upstream, acetaldehyde is the immediate product, and ethanol lies further downstream. The conclusion is conditional on iMM904, pFBA, this fixed genotype and the tested exchange bounds. A model rescue demonstrates a feasible constraint-based bypass; it is not a claim that the same supplementation is physiologically practical or safe. The validator reads only visible simulation evidence and does not launch hidden optimisation.

This is the last new mechanistic concept before the final certification. The rescue identified here is a condition-specific feasibility result; Mission 40 will ask whether that rescue remains robust when the environmental context changes.
