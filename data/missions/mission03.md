# Mission 03: The Conditional Essentiality Screen

Dr. Silva asks the player to identify which candidate gene is operationally
essential for predicted biomass formation in the standard aerobic
`e_coli_core` experiment.

## Scientific protocol

The evidence consists of:

1. one viable reference run with all genes active;
2. six single-gene knockout runs;
3. FBA with the biomass objective in every run;
4. the unchanged default medium in every run;
5. comparison through growth relative to the reference.

Candidates:

- `b1241 / adhE` — no apparent growth effect in this context;
- `b0728 / sucC` — small growth reduction;
- `b3919 / tpiA` — moderate growth reduction;
- `b3736 / atpF` — strong growth reduction;
- `b2278 / nuoL` — very strong growth reduction;
- `b2926 / pgk` — no predicted biomass growth.

The mission treats growth at or below 1% of the reference as operationally
essential. This threshold is explicitly presented as a mission criterion, not
a universal biological definition.

## Expected conclusion

`b2926 / pgk` is the unique candidate that meets the operational essentiality
criterion under the model, objective and medium used by the mission.

## Pedagogical approach

The initial task describes the biological problem without listing every UI
step. Three optional hints progressively reveal the conceptual, experimental
and technical setup. Invalid runs with environmental changes, multiple
knockouts, non-candidate genes, the wrong method or the wrong objective are not
recorded as evidence.
