# Mission 15 — Product–Growth Viability Audit

## Scientist
Dr. Almeida

## Theme
Objective choice, product optima and predicted viability.

## Learning goal
Determine whether a high theoretical product optimum is compatible with predicted growth under the same strain and medium.

## Scenario
The player closes Dr. Almeida's laboratory by comparing two controlled pFBA solutions. One prioritises succinate and the other prioritises biomass. Method, strain, medium and exchange evidence remain identical; only the selected objective changes.

## Main concepts
- objective-dependent optimal solutions
- product-priority versus growth-priority pFBA
- biomass as a viability indicator in the model
- cross-objective flux interpretation
- controlled comparisons
- limits of interpreting a product maximum as a viable strain design

## Required experiment
Use pFBA with all genes active, default glucose, only the lower bound of oxygen uptake closed, and the complete panel `EX_succ_e`, `EX_ac_e`, `EX_for_e`, `EX_etoh_e`, `EX_lac__D_e`.

Record:

1. a product-priority run with objective `EX_succ_e`;
2. a growth-priority run with objective `BIOMASS_Ecoli_core_w_GAM`.

The Mission 14 no-knockout product optimum may be reused when its persisted visible diagnostics are complete. No hidden simulation is allowed.

## Expected evidence

Product-priority optimum:
- succinate approximately `13.906`;
- biomass approximately `0`;
- acetate approximately `5.665`;
- formate, ethanol and D-lactate approximately `0`;
- glucose uptake approximately `10`;
- oxygen uptake approximately `0`.

Growth-priority optimum:
- biomass approximately `0.212`;
- succinate approximately `0`;
- formate approximately `17.805`;
- acetate approximately `8.504`;
- ethanol approximately `8.279`;
- D-lactate approximately `0`;
- glucose uptake approximately `10`;
- oxygen uptake approximately `0`.

## Final interpretation
The report must present the two optima without stating the answer directly. The player submits an evidence-based description of the relationship between growth and succinate production supported by the cross-objective fluxes.
