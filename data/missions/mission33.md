# Mission 33 — Reference-State Adjustment Footprint

## Scientist

Dr. Chen

## Learning objective

Use ROOM with an explicit pre-knockout reference and distinguish three different ideas:

- a reaction being available through its GPR;
- a reaction carrying flux in the reference state;
- the number of significant flux changes required after a perturbation.

ROOM compares a mutant with a matched reference. Its significant-change score is not biomass, total absolute flux or the number of active reactions.

## Controlled matched protocol

Build four visible runs in any order.

### Default aerobic context

```text
Reference
Method: pFBA
Objective: BIOMASS_Ecoli_core_w_GAM
Genes: wild type
Environment: completely model-default and aerobic

Perturbation
Method: ROOM
Objective: BIOMASS_Ecoli_core_w_GAM
Knockouts: b0978 + b0733
Environment: the same completely default aerobic medium
```

### Oxygen-lower-bound-closed context

```text
Reference
Method: pFBA
Objective: BIOMASS_Ecoli_core_w_GAM
Genes: wild type
Environment: close only the EX_o2_e lower bound

Perturbation
Method: ROOM
Objective: BIOMASS_Ecoli_core_w_GAM
Knockouts: b0978 + b0733
Environment: the same oxygen-lower-bound-closed medium
```

No other gene or environmental change is accepted. Production Flux does not need to be selected.

## ROOM reference contract

For every ROOM result, LabHero constructs an explicit wild-type pFBA reference before applying the knockouts. The reference must use:

```text
the same objective
the same environment
no gene knockouts
ROOM delta = 0.03
ROOM epsilon = 0.001
integer ROOM, not the linear relaxation
SciPy/HiGHS MILP with a 12-second safety limit
```

The result exposes the reference method, reference growth, reference `CYTBD` flux and the matching-environment flag. This makes the reference part of the visible evidence rather than a hidden validation run.

## Expected evidence pattern

The default aerobic wild-type reference should show approximately:

```text
Growth: 0.873922
Oxygen uptake: 21.799
CYTBD flux: 43.599
```

The matched ROOM mutant should disable `CYTBD`, reduce measured oxygen uptake to zero and produce a positive integer significant-change score. The exact mutant biomass is not a rigid mission threshold because alternative ROOM-optimal flux distributions may exist.

The oxygen-lower-bound-closed wild-type reference should show approximately:

```text
Growth: 0.211663
Oxygen uptake: 0.000
CYTBD flux: 0.000
```

The matched ROOM mutant should still disable `CYTBD`, keep oxygen uptake at zero and produce a significant-change score equal or very close to zero.

All four results must remain feasible. Missing data or an `INFEASIBLE` status must never be rewritten as a numerical zero.

## Interpretation

The same genetic cut set can have a different adjustment footprint in two reference states. A false GPR does not prove that a flux changed: the target may already have carried no flux before the perturbation. Conversely, disabling a reaction that carried substantial reference flux can require broad network reorganisation.

A zero ROOM score does not mean that no genes were deleted. It means that the mutant remains within the configured significant-change tolerances relative to its matched reference.

## Delivery question

Complete with one word: in the zero-score reference, `CYTBD` was already ______.

Answer with the functional-state word inferred from the completed comparison table. The canonical answer is a short description of a reaction that carried no reference flux before the knockout; compact English and Portuguese equivalents are accepted. Numeric values, context names, method names, knockout identifiers and the word `inactive` are not accepted because genetic availability and flux use are distinct concepts. The accumulated report presents the evidence without adding a separate answer statement.

## Web-service compatibility

Both pFBA and ROOM remain normal visible requests to the existing `/simulate` endpoint. For ROOM, the backend creates independent wild-type-reference and mutant model copies, applies the same environment to both, computes the wild-type pFBA reference before the knockouts and returns JSON-serialisable reference metadata with the mutant result.

The browser does not run MEWpy, COBRApy or a MILP solver, and Mission 33 introduces no new endpoint or hidden validation simulation. The backend performs the same bounded-time HiGHS MILP used by the desktop implementation, keeping the response contract identical while avoiding an unbounded GLPK solve.
