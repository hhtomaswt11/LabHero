# Mission 16 — Context-Dependent Carbon Rescue

## Professor
Dr. Rio — Medium Engineering & Stress Robustness

## Learning goal
Evaluate a carbon-source rescue as a controlled medium experiment and test whether the strongest result remains valid after a second environmental factor is removed.

The mission teaches that:

- a source ranking is meaningful only under a declared comparison protocol;
- equal molar uptake bounds are not the same as equal carbon supply;
- a strong result in one medium may depend on another medium component;
- an infeasible solver result is evidence about this model and these constraints, not a universal biological impossibility.

## Phase A — aerobic screening

Use:

- `FBA`;
- objective `BIOMASS_Ecoli_core_w_GAM`;
- all genes active;
- glucose uptake closed;
- model-default oxygen availability;
- exactly one candidate source opened per run;
- every unrelated environmental bound unchanged;
- the Exchange Flux Report from the visible result.

Candidates:

- `EX_ac_e` — acetate;
- `EX_pyr_e` — pyruvate;
- `EX_mal__L_e` — L-malate;
- `EX_fum_e` — fumarate;
- `EX_akg_e` — 2-oxoglutarate.

All five runs use the same open lower-bound protocol, corresponding to a maximum uptake of `10` model flux units for these sources.

Expected growth ranking under this equal-molar protocol:

1. `EX_akg_e` — approximately `0.529`;
2. `EX_mal__L_e` and `EX_fum_e` — approximately `0.371`;
3. `EX_pyr_e` — approximately `0.291`;
4. `EX_ac_e` — approximately `0.173`.

This is a protocol-specific growth ranking, not a universal carbon-efficiency ranking.

## Phase B — robustness challenge

Repeat the uniquely strongest source, `EX_akg_e`, while keeping the screening setup unchanged except for closing the lower bound of `EX_o2_e`.

Expected visible result:

```text
Status: INFEASIBLE
```

The final question is intentionally concise:

> Which removed environmental factor did the strongest rescue depend on?

Accepted answers include `oxygen`, `O2`, and `EX_o2_e`.
