# Mission 05 — Context-Dependent Anaerobic Ethanol Design

## Objective

Determine which viable candidate knockout produces the strongest additional ethanol secretion when the model is evaluated in an anaerobic environment.

## Concept

A genetic strategy is conditional on its environment. Mission 04 identified a knockout that forced ethanol secretion while oxygen remained available. In anaerobiosis, the no-knockout model already ferments, so the previous winner may become neutral and a different perturbation may perform better.

This mission compares ethanol secretion in biomass-optimal FBA solutions. It does not directly maximise theoretical ethanol yield.

## Target flux

- Product: ethanol
- Exchange flux: `EX_etoh_e`
- Mathematical objective: `BIOMASS_Ecoli_core_w_GAM`

## Candidate genes

- `b2278` (`nuoL`)
- `b0728` (`sucC`)
- `b1602` (`pntB`)
- `b3736` (`atpF`)

## Controlled experiment

1. Establish a viable anaerobic reference with all genes active.
2. Keep FBA, the biomass objective and the anaerobic medium unchanged.
3. Track `EX_etoh_e` in Production Flux.
4. Test exactly one candidate knockout per run.
5. Compare retained growth and additional ethanol relative to the anaerobic reference.

## Operational mission criteria

- Growth retention: at least 90% of the anaerobic reference.
- Additional ethanol: at least `1.0` above the anaerobic reference.
- Winner: the eligible candidate with the highest ethanol secretion.

These thresholds are mission criteria, not universal biological definitions.

## Expected evidence with the included `e_coli_core` model

| Condition | Growth | Ethanol |
|---|---:|---:|
| Anaerobic baseline | ~0.212 | ~8.279 |
| `b2278` / `nuoL` | ~0.212 | ~8.279 |
| `b0728` / `sucC` | ~0.212 | ~8.279 |
| `b1602` / `pntB` | ~0.208 | ~9.796 |
| `b3736` / `atpF` | ~0.196 | ~13.893 |

The evidence identifies `b3736` / `atpF` as the strongest eligible design in this model, medium and objective.
