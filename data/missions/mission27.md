# Mission 27 — Metabolic Bypass Rescue

**Scientist:** Dr. Ribeiro  
**Laboratory theme:** Diagnosis, rescue and metabolic robustness  
**Prerequisite:** Mission 26

## Learning objective

Demonstrate that an environmental supplementation can bypass the predicted consequence of a genetic knockout without restoring the blocked gene-associated reaction.

This is a model-conditional rescue claim. It applies only to the current metabolic model, pFBA biomass objective, medium, bounds and tested candidate set.

## Controlled protocol

Use:

- Method: `pFBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Target gene: `b0720 / gltA`
- GPR-disabled reaction in knockout runs: `CS` (citrate synthase)

Record two references with the completely default environment:

1. Wild type, all genes active
2. Single `b0720 / gltA` knockout

Then keep only `b0720` knocked out and test each candidate separately by opening exactly one candidate lower bound. Glucose, oxygen and every unrelated environmental bound must remain at model default.

Candidate exchanges:

- `EX_akg_e` — 2-Oxoglutarate
- `EX_pyr_e` — Pyruvate
- `EX_succ_e` — Succinate
- `EX_fum_e` — Fumarate
- `EX_mal__L_e` — L-Malate

No Production Flux selection is required. The mission uses growth, medium exchange values, GPR-disabled reactions and method-aware pFBA diagnostics from the visible simulation result.

## Expected scientific pattern

Approximate primary biomass fluxes:

| Condition | Growth |
|---|---:|
| Wild type, default medium | 0.873922 |
| `b0720` knockout, default medium | 0.000000 |
| Knockout + `EX_akg_e` | 1.395438 |
| Knockout + `EX_pyr_e` | 0.000000 |
| Knockout + `EX_succ_e` | 0.000000 |
| Knockout + `EX_fum_e` | 0.000000 |
| Knockout + `EX_mal__L_e` | 0.000000 |

The report must show that `CS` remains disabled in every knockout trial. A positive growth result therefore represents an operational bypass in this model, not repair of `gltA` or restoration of citrate synthase.

## Final question

> Which candidate exchange restored predicted growth while citrate synthase remained disabled?

The report presents the seven visible runs but does not state the final answer for the player.

## Robustness requirements

- Runs may be completed in any order.
- Repeating a valid condition updates that condition without duplicating evidence.
- An invalid later attempt does not erase valid references or candidate trials.
- Exactly one candidate lower bound may be opened per candidate trial.
- Wild type is allowed only for the default reference.
- Knockout references and candidate trials require exactly `b0720` knocked out.
- `INFEASIBLE` is not treated as numeric zero growth.
- Numeric glucose, oxygen and candidate exchange evidence is required.
- pFBA primary and secondary diagnostics must be internally consistent.
- State must remain JSON serializable and usable in desktop and browser modes.
- No hidden validation simulation or extra HTTP request is used.
