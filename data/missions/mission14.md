# Mission 14 — Byproduct Trade-off Screening

## Theme
Evidence-based screening of genetic interventions and interpretation of product trade-offs.

## Learning goal
Understand that lowering one byproduct is not enough to prove that a metabolic intervention improved a design. A candidate must be judged using the primary target, the complete co-product fingerprint and the modelling context that produced those values.

## Progression
Mission 11 introduced one complete exchange fingerprint. Mission 12 compared two fingerprints under a changed environmental constraint. Mission 13 separated the primary metabolic objective from pFBA's secondary parsimony criterion. Mission 14 now asks the player to apply all three skills to a controlled single-gene screen.

## Controlled setup
Every valid run uses:

- method `pFBA`;
- primary objective `EX_succ_e`;
- default glucose supply;
- only the lower bound of `EX_o2_e` closed;
- all remaining environmental bounds at their model-default state;
- the complete panel `EX_succ_e`, `EX_ac_e`, `EX_for_e`, `EX_etoh_e`, `EX_lac__D_e`;
- no knockout for the reference or exactly one candidate knockout for a trial.

The completed visible pFBA run from Mission 13 may be reused as the no-knockout reference. No hidden simulation is launched.

## Candidate genes

- `b1241 / adhE`
- `b0115 / aceF`
- `b0474 / adk`
- `b4151 / frdD`

## Expected evidence

| Run | Succinate | Target retained | Acetate | Formate | Ethanol | Interpretation |
|---|---:|---:|---:|---:|---:|---|
| Reference | 13.906 | 100% | 5.665 | 0.000 | 0.000 | no-knockout reference |
| `b1241 / adhE` | 13.906 | 100.0% | 5.665 | 0.000 | 0.000 | no meaningful effect because alternative genes preserve the relevant GPR functions |
| `b0115 / aceF` | 13.313 | 95.7% | 4.479 | 8.896 | 0.000 | acetate decreases, but formate appears |
| `b0474 / adk` | 12.915 | 92.9% | 2.712 | 10.000 | 1.458 | acetate decreases further, but formate and ethanol appear |
| `b4151 / frdD` | 4.000 | 28.8% | 0.000 | 20.000 | 12.000 | acetate disappears, but the succinate optimum collapses and major co-products appear |

All direct succinate-optimal solutions have approximately zero predicted biomass flux. They are theoretical product optima, not viable production-strain claims.

## Operational criteria
A candidate is a clean improvement only when it simultaneously:

- retains at least 90% of reference succinate;
- reduces acetate by at least 1.0;
- introduces no new co-product above 0.1.

These are mission criteria, not universal biological definitions.

## Correct conclusion
No candidate satisfies all three criteria.

Accepted answers include:

- `none`
- `no candidate`
- `nenhum`
- `nenhum candidato`

## Persistence and web compatibility
The state stores the reference, candidate trials, latest attempt, current issues, trade-off calculations and final conclusion as JSON-serialisable data. Trial order is irrelevant, repeated runs update rather than duplicate evidence, and invalid attempts do not erase valid evidence. Desktop and browser clients reuse the same visible solver result and the same validation logic.
