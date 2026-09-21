# Mission 20 — Context-Specific Export Robustness

## Scientist
Dr. Rio

## Theme
Medium Engineering, Binding Constraints & Context Robustness

## Learning goal
Show that the same exchange upper-bound closure can be non-binding in one environmental context and alter the predicted phenotype in another.

## Concept
A constraint should not be interpreted from its presence alone. Its effect depends on whether the unconstrained solution uses the restricted flux direction and on the rest of the environmental context. Robustness therefore requires controlled comparisons across more than one condition.

## Challenge
Build a four-run pFBA matrix in which only oxygen availability and the acetate export upper bound vary. Compare acetate-open and acetate-closed runs with oxygen available, then repeat the same pair after closing oxygen uptake.

## Controlled protocol
- Use pFBA with the biomass objective.
- Keep every gene active.
- Keep glucose and every unrelated environmental bound at model default.
- Track `EX_ac_e`, `EX_etoh_e`, `EX_for_e`, `EX_succ_e` and `EX_lac__D_e` in every run.
- Record all four combinations of:
  - `EX_o2_e` lower bound open or closed;
  - `EX_ac_e` upper bound open or closed.
- Use the same visible solver result for biomass, Exchange Flux, Production Flux and pFBA diagnostics.

## Final interpretation
Identify the oxygen context in which closing acetate export changes the predicted growth and export profile. The answer field expects one concise context rather than a free-form essay.

## Pedagogical role
This closes Dr. Rio's laboratory by combining environmental context, lower- and upper-bound reasoning, pFBA diagnostics, controlled before/after comparisons and a short evidence-based conclusion. It prepares the transition to Dr. Vega's formal comparison laboratory.
