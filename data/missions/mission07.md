# Mission 07 — Objective Matters

## Theme
Controlled comparison of FBA objective functions.

## Learning goal
The player learns that changing the objective function changes the mathematical question asked of the same constrained metabolic model. It does not alter the strain or the medium.

The mission also distinguishes a positive product objective from predicted viability: direct ethanol maximisation can produce a high theoretical secretion flux while the biomass flux is zero.

## Target product
- Ethanol (`EX_etoh_e`)

## Mission rules
- Complete Mission 06 first.
- Use FBA in both runs.
- Keep all genes active.
- Keep the default environment unchanged.
- Track `EX_etoh_e` in both runs.
- Record one run with `BIOMASS_Ecoli_core_w_GAM` as objective.
- Record one run with `EX_etoh_e` as objective.
- Use only the visible solution; no hidden or auxiliary simulation is used.

## Expected controlled evidence

### Biomass-objective run
- Biomass flux: approximately `0.874`
- Ethanol secretion: approximately `0.000`
- Oxygen uptake: approximately `21.799`

### Ethanol-objective run
- Biomass flux: approximately `0.000`
- Ethanol secretion: approximately `20.000`
- Oxygen uptake: approximately `0.000`

## Interpretation
The objective values belong to different reactions and must not be directly subtracted or ranked as though they represented the same quantity.

The ethanol result is a theoretical maximum predicted by this model, medium and uptake bounds. It is not a universal biological constant and it does not describe a growing production strain because the corresponding biomass flux is zero.
