# Mission 34 — Shared-Subunit Equivalence Audit

## Purpose

Mission 34 closes Dr. Chen's gene-protein-reaction programme by separating the number of deleted genes from the number of reactions disabled by the complete GPR logic.

The experiment asks whether one knockout in a shared subunit can create the same reaction-level lesion as two reaction-specific knockouts.

## Controlled protocol

Use the same settings in all six runs:

- Method: `pFBA`
- Primary objective: `BIOMASS_Ecoli_core_w_GAM`
- Environment: completely model-default and aerobic
- Production Flux: no selection is required
- No unrelated gene or bound changes

The visible result must provide:

- biomass/primary-objective flux;
- model-default glucose uptake;
- positive oxygen uptake;
- formate secretion;
- pFBA total absolute flux;
- active-reaction count;
- the complete GPR-disabled reaction set.

## GPR map

```text
PDH   = b0114 AND b0115 AND b0116
AKGDH = b0726 AND b0116 AND b0727
```

Gene names:

```text
b0114 / aceE
b0116 / lpd
b0726 / sucA
b0727 / sucB
```

`b0116 / lpd` is shared by both reactions in this model.

## Required visible runs

Record the following six genotypes in any order:

```text
1. Wild type
2. b0114
3. b0726
4. b0726+b0727
5. b0116
6. b0114+b0726
```

No other knockout combination is accepted.

## Expected reaction-level patterns

```text
Wild type      -> no GPR-disabled reactions
b0114          -> PDH
b0726          -> AKGDH
b0726+b0727    -> AKGDH
b0116          -> AKGDH and PDH
b0114+b0726    -> AKGDH and PDH
```

The first comparison shows that deleting a second required subunit from an already broken AKGDH complex does not add another disabled reaction.

The second comparison shows that a shared-subunit single knockout and a split double knockout can impose the same reaction closures.

## Expected numerical profile

Approximate pFBA values in the included E. coli core model:

| Condition | Growth | O2 uptake | Formate | Total absolute flux | Active reactions |
|---|---:|---:|---:|---:|---:|
| Wild type | 0.874 | 21.799 | 0.000 | 518.422 | 48 |
| `b0114` | 0.797 | 21.304 | 7.743 | 532.797 | 50 |
| `b0726` | 0.858 | 22.482 | 0.000 | 531.461 | 48 |
| `b0726+b0727` | 0.858 | 22.482 | 0.000 | 531.461 | 48 |
| `b0116` | 0.782 | 21.910 | 7.784 | 556.281 | 50 |
| `b0114+b0726` | 0.782 | 21.910 | 7.784 | 556.281 | 50 |

All six rows must remain feasible. A missing value or an `INFEASIBLE` result is never converted into zero.

## Interpretation

The mission demonstrates that:

```text
one gene knockout can disable two reactions
```

while:

```text
two gene knockouts can still disable only one reaction
```

Different genotypes are not identical. They are reaction-level equivalent only when the complete GPR evaluation produces the same reaction closures and the measured pFBA outputs match under the same model, objective and environment.

The pFBA total absolute flux is a secondary parsimony criterion. It is not a universal measure of biological quality.

## Final delivery

The final question asks for the reaction-level relationship between:

```text
b0116
```

and:

```text
b0114+b0726
```

The report displays the evidence but does not print the answer directly.

## Desktop/web contract

Every row comes from one visible simulation result. The desktop result and the existing `POST /simulate` response expose the same additive field:

```text
gpr_disabled_reactions
```

This prevents a future browser interface from duplicating GPR evaluation. Mission 34 requires no new endpoint, no solver in the browser and no hidden validation simulation. The accumulated mission state is JSON-serialisable.
