# Mission 30 — Redundancy Breakdown Threshold

**Scientist:** Dr. Li  
**Laboratory:** Dr. Ribeiro, Dr. Li and Dr. Chen laboratory  
**Prerequisite:** Mission 29 completed

## Learning objective

Mission 29 identified isoenzyme redundancy under one default aerobic condition. Mission 30 tests whether that conclusion remains stable when oxygen uptake capacity is progressively restricted.

The player must distinguish two different model outputs:

- a feasible solution with a numerical biomass flux;
- an `INFEASIBLE` solver status, where no flux state satisfies all current constraints.

An `INFEASIBLE` row must never be converted into a measured growth value of `0.000`.

## Controlled protocol

Use:

- method `pFBA`;
- objective `BIOMASS_Ecoli_core_w_GAM`;
- a completely model-default base environment before each curve;
- no Production Flux selection;
- Bound Sweep variable `EX_o2_e` lower bound;
- dedicated preset `PFK redundancy threshold: -30, -10, -5, -2`.

Record four visible curves in any order:

1. wild type;
2. only `b1723 / pfkB` knocked out;
3. only `b3916 / pfkA` knocked out;
4. the exact `b1723 + b3916` double knockout.

The complete GPR must leave `PFK` active in wild type and both single-knockout curves, while the exact double knockout disables `PFK`.

## Expected evidence

Approximate primary growth values are:

| O₂ lower bound | Wild type | `b1723` single | `b3916` single | Double knockout |
|---:|---:|---:|---:|---:|
| `-30` | `0.874` | `0.874` | `0.874` | `0.704` |
| `-10` | `0.559` | `0.559` | `0.559` | `0.248` |
| `-5` | `0.392` | `0.392` | `0.392` | `0.076` |
| `-2` | `0.284` | `0.284` | `0.284` | `INFEASIBLE` |

The first point is non-binding for oxygen in all four curves. The remaining feasible points are binding. The single knockouts track wild type, whereas the double-knockout retention decreases before the final status change.

## Final question

At which tested oxygen lower-bound value does the double knockout first become infeasible while wild type and both single knockouts remain viable?

The report must show the evidence but must not write the answer explicitly.

## Web compatibility

The mission reuses the existing `POST /simulate` service. The browser performs the four visible sweeps and accumulates their JSON rows locally. No hidden solver call or new endpoint is required.
