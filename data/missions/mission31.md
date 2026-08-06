# Mission 31 — Environmental Suppression Matrix

**Scientist:** Dr. Li  
**Laboratory:** Dr. Ribeiro, Dr. Li and Dr. Chen laboratory  
**Prerequisite:** Mission 30 completed

## Learning objective

Mission 29 identified `b0118 / acnB` and `b1276 / acnA` as a synthetic-lethal aconitase pair in the default glucose medium. Mission 30 then showed that the effect of a redundant pair can change across an environmental threshold.

Mission 31 asks the reverse question: can a different carbon-entry route suppress a no-growth phenotype while the deleted isoenzymes remain unavailable?

The player must distinguish three observations:

- a feasible solution with measured growth equal to `0.000`;
- positive uptake of a replacement source;
- a true environmental suppression in which the matched double knockout regains strong growth.

Positive source uptake alone is not a rescue, and a feasible zero-growth solution is not an `INFEASIBLE` result.

## Controlled protocol

Use:

- method `pFBA`;
- objective `BIOMASS_Ecoli_core_w_GAM`;
- no Production Flux selection;
- the lower bound of `EX_glc__D_e` closed;
- exactly one replacement-source lower bound opened at the standard `-10` capacity;
- model-default oxygen and every unrelated environmental bound.

Test these four replacement sources:

- `EX_fru_e` — D-Fructose;
- `EX_pyr_e` — Pyruvate;
- `EX_succ_e` — Succinate;
- `EX_glu__L_e` — L-Glutamate.

For every source, record two matched visible runs in any order:

1. wild type;
2. the exact `b0118 + b1276` double knockout.

The complete matrix therefore contains eight visible runs.

The wild-type runs must keep `ACONTa` and `ACONTb` available. The exact double knockout must disable both reactions through the complete GPR in every environment.

## Expected evidence

Approximate primary growth values are:

| Replacement source | Wild type | `b0118+b1276` | Double retention | Double source uptake |
|---|---:|---:|---:|---:|
| `EX_fru_e` | `0.873922` | `0.000000` | `0.0%` | `0.932` |
| `EX_pyr_e` | `0.291225` | `0.000000` | `0.0%` | `3.729` |
| `EX_succ_e` | `0.397563` | `0.000000` | `0.0%` | `2.098` |
| `EX_glu__L_e` | `0.598732` | `0.576236` | `96.2%` | `10.000` |

All eight expected runs are feasible. In the three zero-growth double knockouts, the source can still show positive uptake. That uptake does not by itself restore biomass production.

Only one tested environment supports strong matched growth retention while `ACONTa` and `ACONTb` remain GPR-disabled.

## Final question

Which tested replacement carbon source suppressed the aconitase no-growth phenotype while `ACONTa` and `ACONTb` remained disabled?

The report must show the complete evidence without writing the answer explicitly.

## Robust state and web compatibility

The mission stores a JSON-serialisable matrix keyed by source and genotype. Runs may arrive in any order, repeated conditions update their existing matrix cell, and an invalid attempt does not erase valid evidence.

Every matrix cell reuses the already visible result returned by the existing `POST /simulate` service. The validator performs no hidden simulation and requires no new backend endpoint or browser-side solver.
