# Mission 06 — Controlled Multi-Knockout Challenge

## Theme
Metabolic engineering: balancing predicted growth and growth-coupled ethanol secretion under a limited genetic-design budget.

## Learning goal
The player learns that strain quality cannot be judged by production alone, that additional knockouts can help or harm a design, and that competitive scores are meaningful only when the model, medium, objective and design rules remain fixed.

## Scenario
Dr. Carter presents a rival strain. The player must beat the rival balance index without changing or enriching the default aerobic medium.

## Controlled setup
- Method: FBA.
- Objective: `BIOMASS_Ecoli_core_w_GAM`.
- Medium: unchanged default aerobic medium.
- Tracked product: ethanol exchange, `EX_etoh_e`.
- Candidate genes: `b2278 / nuoL`, `b3736 / atpF`, `b1602 / pntB`, `b0728 / sucC`.
- Budget: at most two knockouts per design.
- Operational viability: at least 20% of the all-genes-active reference growth.
- Rival balance index: 2.80.

## Score
The game balance index is:

`predicted growth × ethanol secretion flux`

Both values must come from the same visible biomass-optimal FBA solution. The index is a game rule, not a standard biological unit or universal measure of strain quality.

## Expected design pattern
- No knockout: growth about 0.874, ethanol 0, index 0.
- `b2278`: growth about 0.212, ethanol about 8.279, index about 1.752.
- `b2278 + b1602`: growth about 0.208, ethanol about 9.796, index about 2.033.
- `b2278 + b3736`: growth about 0.203, ethanol about 14.196, index about 2.876.

The winning design is therefore `b2278 + b3736` under the specified controlled conditions. The ethanol flux of this design is fixed at maximum biomass growth, so the outcome does not depend on an arbitrary alternative optimum.

## Evidence and persistence
The mission records:
- the aerobic all-genes-active reference;
- the latest attempt;
- a bounded history of recent valid attempts;
- the best valid result for each tested design;
- the best valid design overall.

A weaker or invalid later attempt does not erase the best valid design. Legacy Mission 06 artifacts based on the old score of 14500 are rejected.
