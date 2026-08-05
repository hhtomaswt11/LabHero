# Mission 29 — Isoenzyme Redundancy Screen

**Scientist:** Dr. Li  
**Prerequisite:** Mission 28

## Learning objective

Distinguish ordinary functional redundancy from a synthetic-lethal interaction in a constraint-based metabolic model. A single knockout may have little or no effect when another isoenzyme still supports the same reaction. A matched double knockout can expose a hidden dependency.

## Controlled protocol

Use:

- `pFBA`;
- objective `BIOMASS_Ecoli_core_w_GAM`;
- the completely model-default aerobic environment;
- no supplementary carbon source;
- no unrelated environmental changes;
- no `Production Flux` selection.

Record one wild-type reference. Then record both individual knockouts and the exact double knockout for each pair:

- `b0118 / acnB` + `b1276 / acnA`;
- `b1723 / pfkB` + `b3916 / pfkA`;
- `b1676 / pykF` + `b1854 / pykA`.

The ten visible runs may be completed in any order. Repeating a valid condition updates that cell without duplicating evidence. An invalid attempt must not erase previously valid evidence.

## Evidence to interpret

Compare:

- growth of each single knockout relative to wild type;
- growth of the matched double knockout;
- reactions disabled through the complete GPR;
- numeric glucose and oxygen exchange evidence;
- pFBA primary and secondary diagnostics.

A synthetic-lethal relationship in this mission is operational and conditional: both single knockouts retain predicted growth, while their matched double knockout abolishes it in this model, objective and default aerobic medium.

## Final question

Identify the tested gene pair that supports that relationship. The report presents the full evidence but must not state the answer directly.
