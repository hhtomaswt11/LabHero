# Mission 12 — Constraint-Driven Succinate Byproducts

## Theme
Controlled comparison of two product-optimal secretion fingerprints.

## Learning goal
Understand that an environmental constraint can be binding for one objective even when a similar constraint was non-binding in a previous mission. The player must attribute changes in both the target flux and co-product profile to oxygen availability while keeping every other modelling variable fixed.

## Scenario
Dr. Almeida asks whether oxygen availability changes the theoretical succinate optimum. The player must record two complete visible fingerprints: one in the untouched default medium and one with only oxygen uptake disabled.

## Controlled configuration
Both runs use:

- FBA;
- objective `EX_succ_e`;
- all genes active;
- default glucose supply;
- the complete Production Flux panel:
  - `EX_succ_e`;
  - `EX_ac_e`;
  - `EX_for_e`;
  - `EX_etoh_e`;
  - `EX_lac__D_e`.

The only changed configuration is the lower bound of `EX_o2_e`.

## Expected evidence

### Oxygen-available default medium

- succinate approximately `16.384`;
- acetate, formate, ethanol and D-lactate approximately `0`;
- biomass approximately `0`;
- oxygen uptake approximately `2.655`.

### Oxygen-constrained medium

- succinate approximately `13.906`;
- acetate approximately `5.665`;
- formate, ethanol and D-lactate approximately `0`;
- biomass approximately `0`;
- oxygen uptake approximately `0`.

## Interpretation
Disabling oxygen uptake reduces the theoretical succinate maximum and introduces acetate as a predicted co-product. The oxygen constraint is therefore binding for this objective under these model conditions.

Both direct product-optimal solutions predict zero predicted growth rate. They are theoretical optima, not claims about a viable production strain.

## Required conclusion
After both runs have been recorded, submit:

- `acetate`; or
- `EX_ac_e`.

## Implementation principles

- all target, byproduct, biomass and medium evidence comes from the two visible solutions;
- no hidden simulation is executed;
- run order is irrelevant;
- repeated runs update evidence without duplication;
- invalid attempts do not erase valid evidence;
- state is JSON-serialisable and shared by desktop and future web clients.
