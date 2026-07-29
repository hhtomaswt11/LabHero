# Mission 08 — Constraint Impact on the Optimal Solution

## Concept
Constraint-based optimisation: determining whether an added environmental bound changes an optimum.

## Learning objective
The player learns that adding a constraint does not necessarily change the optimal solution. A new bound may reduce the feasible space while leaving the previous optimum and its flux profile unchanged when that optimum already satisfies the new condition.

## Challenge
Dr. Nova asks whether removing oxygen availability necessarily increases the direct theoretical maximum of D-lactate represented by `EX_lac__D_e`.

The player must record two visible FBA runs with the same objective, genes and medium bounds except for oxygen availability:

1. default medium;
2. the same medium with only the lower bound of `EX_o2_e` closed.

Both runs must keep all genes active and track `EX_lac__D_e` in Production Flux. Biomass, D-lactate and oxygen uptake must be read from the same visible solution; no hidden simulation is allowed.

## Expected evidence
Both controlled runs produce approximately:

- D-lactate secretion: `20.000`;
- biomass flux: `0.000`;
- oxygen uptake: `0.000`.

Closing oxygen therefore does not change the optimum for this objective. The default-medium direct D-lactate optimum already uses zero oxygen. In the constrained run, the oxygen lower bound is satisfied at equality, but the added bound does not alter the optimal product, biomass or oxygen fluxes.

## Interpretation
The mission must not claim that anaerobiosis caused or increased D-lactate production. It demonstrates that the effect of a constraint depends on the objective and on which capabilities the previous optimum actually used.

The direct product maximum also has no predicted growth, so it represents a theoretical optimum under this model and these bounds, not a viable production strain.

Use **D-lactate**, not generic “lactate”, because `EX_lac__D_e` represents the D stereoisomer in this model.

## Progression
Mission 08 is unlocked only after Mission 07. The initial challenge remains conceptual; progressively more explicit optional hints describe the controlled protocol.
