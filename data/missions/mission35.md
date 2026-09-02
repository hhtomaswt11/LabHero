# Mission 35 — E. coli Final Systems Certification

## Goal

Complete the final *E. coli* certification dossier by integrating three evidence layers:

1. approve a production design using growth, secretion and GPR impact together;
2. compare two matched oxygen-response curves and identify where their visible phenotypes converge;
3. audit whether direct maximisation of the product remains compatible with predicted growth.

This mission is a synthesis challenge. A larger product flux is not automatically the best biological design, and a matched phenotype does not imply an identical mechanism.

---

## A — Design Approval Screen

Keep the following protocol fixed:

- **Method:** `pFBA`
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- **Environment:** completely model-default and aerobic
- **Production Flux panel:** exactly `EX_for_e`, `EX_ac_e`, `EX_etoh_e`
- **No unrelated gene or bound changes**

Record these four visible runs in any order:

- wild type;
- `b0114 / aceE`;
- `b0726 / sucA`;
- `b0116 / lpd`.

A design qualifies only if all three criteria are satisfied:

- formate secretion **>= 7.5**;
- growth retention **>= 90%** of the wild-type control;
- no more than **one GPR-disabled reaction**.

Use the complete GPR-disabled reaction list reported by the simulator. Do not equate gene count with reaction count.

---

## B — Oxygen Robustness Curves

Compare the two genotypes that disable PDH either alone or together with AKGDH:

- `b0114 / aceE`;
- `b0116 / lpd`.

For each genotype use:

- **Method:** `pFBA`
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- **Base environment:** completely model-default and aerobic
- **Bound Sweep variable:** `EX_o2_e` lower bound
- **Preset:** `Final oxygen convergence: -30, -10, -5, -2`

Read the matched rows using growth, oxygen uptake, formate, acetate, ethanol, pFBA total and active-reaction count. The GPR-disabled reaction sets must remain visible as mechanistic evidence even when the measured phenotypes become indistinguishable.

Identify the **first tested** oxygen lower bound at which the two measured phenotypes converge and remain matched for the tighter tested condition.

---

## C — Objective Viability Audit

Return to the completely model-default aerobic environment and use:

- **Method:** `pFBA`
- **Genotype:** exactly `b0114 / aceE`
- **Objective:** `EX_for_e`

Compare this direct product optimum with the `b0114` biomass-objective result already recorded in Section A.

Inspect both:

- the direct formate objective flux;
- the predicted growth rate in that same visible solution.

A theoretical product maximum is not automatically a growth-compatible design.

---

## Final delivery

The final menu asks for three short conclusions:

- the qualifying **reaction target** from Section A;
- the **first tested O2 lower bound** where the two visible phenotypes converge;
- whether the direct formate optimum is **growth-compatible**.

The answers are accepted only after all three evidence sections are complete. Invalid or repeated experiments do not erase previously valid dossier evidence.

## Scientific scope

Every conclusion is conditional on the current *E. coli* core model, the stated objective functions, the tested genotypes, the specified bounds and pFBA. The pFBA total is a secondary parsimony criterion, not a biological quality ranking. Missing values are not interpreted as zero, and `INFEASIBLE` is never treated as a zero-growth observation.
