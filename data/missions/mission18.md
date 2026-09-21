# Mission 18 — Binding Export Constraints

## Theme
Controlled comparison of binding and non-binding exchange upper bounds.

## Learning goal
An upper bound restricts positive export, but the constraint only changes the optimum when the baseline solution uses that export direction. A bound can be present without being binding.

## Phase A — anaerobic baseline
Use FBA with the biomass objective, all genes active, default glucose and only the oxygen lower bound closed. Select the complete panel `EX_ac_e`, `EX_etoh_e`, `EX_for_e`, `EX_succ_e`, `EX_lac__D_e` and record growth, glucose/oxygen uptake and all export values.

## Phase B — two controlled trials
Repeat the same setup twice, closing only one candidate upper bound per run:

- `EX_ac_e`
- `EX_succ_e`

The acetate closure removes an export that is active in the baseline, retains viable growth and redistributes the product profile. The succinate closure is a non-binding control because succinate export is already zero in the baseline.

## Final question
Which upper-bound closure created the binding export constraint in this controlled screen?

The player submits one concise route name or reaction identifier. All evidence comes from the same visible solver results; no hidden simulation is used.
