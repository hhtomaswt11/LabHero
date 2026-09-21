# Mission 28 — Bypass Dependency Mapping

**Scientist:** Dr. Ribeiro  
**Laboratory:** Diagnosis, Rescue and Metabolic Robustness  
**Prerequisite:** Mission 27 completed

## Learning objective

Mission 27 established that opening `EX_akg_e` can restore predicted growth to a `b0720 / gltA` knockout while `CS` remains disabled. Mission 28 asks a harder mechanistic question: which network function is required for that rescue?

The mission distinguishes external supplement availability from actual metabolic uptake. A compound can be present in the medium but fail to rescue growth if the network can no longer transport it into the modelled metabolic system.

## Controlled protocol

Use:

- Method: `pFBA`
- Primary objective: `BIOMASS_Ecoli_core_w_GAM`
- Fixed primary knockout: `b0720 / gltA`
- Fixed rescue supplement: open only the lower bound of `EX_akg_e`
- Glucose and oxygen: model-default bounds
- Every unrelated environmental bound: model default
- Production Flux panel: not required

The valid rescue reference contains only the primary knockout. Mission 28 can import the already recorded visible `EX_akg_e` rescue trial from Mission 27; alternatively, the player may record the same reference again.

For each dependency trial, retain `b0720` and add exactly one secondary knockout:

| Gene | Name | GPR-disabled candidate reaction |
|---|---|---|
| `b2587` | `kgtP` | `AKGt2r` |
| `b1761` | `gdhA` | `GLUDy` |
| `b0728` | `sucC` | `SUCOAS` |
| `b3236` | `mdh` | `MDH` |
| `b3403` | `pckA` | `PPCK` |

The reference and five double-knockout trials may be recorded in any order. Repeating a valid condition updates that condition without duplicating evidence.

## Expected model results

| Condition | Predicted growth | 2-Oxoglutarate uptake | GPR-disabled reactions |
|---|---:|---:|---|
| `b0720 + EX_akg_e` reference | about `1.395438` | about `10.000` | `CS` |
| + `b2587 / kgtP` | about `0.000000` | about `0.000` | `CS`, `AKGt2r` |
| + `b1761 / gdhA` | about `1.348118` | about `10.000` | `CS`, `GLUDy` |
| + `b0728 / sucC` | about `1.345444` | about `10.000` | `CS`, `SUCOAS` |
| + `b3236 / mdh` | about `1.321581` | about `10.000` | `CS`, `MDH` |
| + `b3403 / pckA` | about `1.354106` | about `10.000` | `CS`, `PPCK` |

The four control knockouts retain more than 90% of the reference rescue growth. The `b2587 / kgtP` knockout removes measurable 2-oxoglutarate uptake and abolishes the rescue while `CS` remains disabled.

## Final question

> Which secondary gene knockout abolished the rescue by preventing 2-oxoglutarate uptake while citrate synthase remained disabled?

Accepted answer forms include `b2587`, `kgtP`, `AKGt2r`, `2-oxoglutarate transporter`, and `alpha-ketoglutarate transporter`.

The report displays growth, rescue retention, measured supplement uptake and GPR-disabled reactions, but does not state the answer explicitly.

## Scientific interpretation

The supported conclusion is conditional on this model, the pFBA biomass objective, the selected medium and bounds, and the tested candidate set. The result does not establish a universal experimental dependency in every *E. coli* condition.

## Robustness and web compatibility

- Numeric zero is accepted only when returned by a feasible visible simulation.
- `INFEASIBLE` is never converted to zero growth.
- Exactly one secondary candidate is allowed in each double-knockout trial.
- The primary lesion, rescue supplement and all unrelated environmental bounds are validated.
- pFBA primary and secondary diagnostics must be coherent.
- Invalid attempts do not erase previously valid evidence.
- State is JSON serializable.
- The validator uses the visible `/simulate` response and launches no hidden simulation or additional HTTP request.
