# Mission 26 — Genotype–Environment Interaction Curve

## Scientist
Dr. Smith

## Lab Theme
Conditional essentiality, matched response curves and genotype–environment interaction.

## Concept
Mission 25 compared two oxygen contexts for `b3956 / ppc`. Mission 26 extends those endpoints into two matched four-point curves.

A lower bound on `EX_o2_e` defines the maximum oxygen uptake capacity. The realised uptake may be smaller when the capacity is non-binding. Comparing wild type and knockout at the same lower-bound values distinguishes a gradual environmental response from a genotype-specific threshold.

The conclusion is conditional on this model, biomass objective, glucose medium, genotype and tested oxygen capacities. It is not a universal statement about gene essentiality.

## Mission Goal
Determine at which tested oxygen lower-bound value the `b3956 / ppc` knockout loses predicted growth while the matched wild type remains viable.

## Required Setup
Run two Bound Sweeps in any order.

### Wild-type curve
- Method: `FBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Genes: all active
- Base environment: completely default
- Sweep reaction: `EX_o2_e`
- Bound: lower
- Values: `-25`, `-10`, `-1`, `0`

### Knockout curve
Use the same setup and values, changing only:
- Knockout: `b3956 / ppc`

No Production Flux panel is required. Every visible row must include numeric growth, glucose uptake, oxygen uptake, total absolute flux, active-reaction count and FBA objective diagnostics.

## Expected Model Behaviour
Approximate growth values are:

| Oxygen lower bound | Wild type | `b3956` knockout | KO/WT retention |
|---:|---:|---:|---:|
| `-25` | `0.874` | `0.871` | `99.6%` |
| `-10` | `0.559` | `0.530` | `94.8%` |
| `-1` | `0.248` | `0.232` | `93.7%` |
| `0` | `0.212` | `0.000` | `0.0%` |

At `-25`, both curves use less oxygen than the available capacity, so the bound is non-binding. At `-10`, `-1` and `0`, oxygen uptake reaches the tested capacity.

## Evidence Rules
- both curves are mandatory;
- either curve may be recorded first;
- repeating a valid curve replaces that curve without duplicating evidence;
- an invalid later sweep does not erase a previously valid curve;
- rows are matched by bound value, not by list position;
- missing, duplicate or non-numeric rows are rejected;
- the wild type must remain viable at lower bound `0`;
- the knockout must retain most growth at every tested negative lower bound and collapse at `0`;
- validation uses only the visible Bound Sweep output and performs no hidden simulation.

## Final Question
At which tested oxygen lower-bound value does knockout growth collapse while wild-type growth remains viable?

The report shows both curves and the retention values but does not state the final answer.
