# Mission 32 — Respiratory Complex Cut-Set

## Scientist

Dr. Chen

## Learning objective

Interpret a nested gene–protein–reaction rule containing mandatory subunits within alternative protein branches:

```text
(b0978 AND b0979) OR (b0733 AND b0734)
```

The mission distinguishes:

- a broken protein branch from a disabled metabolic reaction;
- oxygen availability in the medium from measured oxygen uptake;
- reduced but feasible growth from an `INFEASIBLE` solver result;
- a cut set identified within the tested candidates from a universal biological claim.

## Controlled protocol

Use the same setup for every visible run:

```text
Method: pFBA
Objective: BIOMASS_Ecoli_core_w_GAM
Environment: completely model-default and aerobic
Production Flux: no selection required
```

The target reaction is `CYTBD`. Its two model branches are:

```text
cbdAB: b0978 / cbdA AND b0979 / cbdB
cydAB: b0733 / cydA AND b0734 / cydB
```

Record these six genotypes in any order:

1. wild type;
2. `b0978`;
3. `b0733`;
4. `b0978+b0979`;
5. `b0733+b0734`;
6. `b0978+b0733`.

No additional knockout or environmental change is accepted.

## Expected visible evidence

The first five conditions retain approximately:

```text
Growth: 0.873922
Glucose uptake: 10.000
Oxygen uptake: 21.799
CYTBD disabled by the GPR: no
```

The tested cross-branch pair produces approximately:

```text
Growth: 0.211663
Glucose uptake: 10.000
Oxygen uptake: 0.000
CYTBD disabled by the GPR: yes
Acetate secretion: 8.504
Ethanol secretion: 8.279
Formate secretion: 17.805
```

This final condition is feasible. It must not be reported as `INFEASIBLE` or as complete loss of growth.

## Interpretation

Removing both genes from one branch breaks that branch, but the alternative complete branch keeps the overall `OR` expression true. The tested cross-branch pair removes one required subunit from each branch, so neither `AND` branch remains complete and the full `CYTBD` GPR becomes false.

Oxygen remains available in the unchanged medium, but its measured uptake falls to zero after `CYTBD` is disabled. The model remains viable through a lower-growth fermentative phenotype.

The conclusion applies only to this model, objective, default aerobic environment and tested genotype set. Other cross-branch pairs implied by the same GPR were not part of this mission.

## Delivery question

Which tested knockout pair broke one required subunit in each alternative `CYTBD` branch and disabled the reaction?

The report must provide the accumulated evidence without explicitly writing the answer for the player.

## Web-service compatibility

Every condition is a normal visible request to the existing `/simulate` endpoint. The mission accumulates JSON-serialisable snapshots containing the selected method, objective, complete gene and bound state, growth, exchange evidence, GPR-disabled reactions and pFBA diagnostics. It does not add a backend endpoint, run a solver in the browser or perform a hidden validation simulation.
