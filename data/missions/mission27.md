# Mission 27 — Glucose Limitation Sweep

**Scientist:** Dr. Luna  
**Lab:** Laboratory 5 — Comparative Experiment Lab  
**Theme:** Medium sensitivity / carbon limitation

## Mission idea

The player uses **Bound Sweep** to test how the model responds when glucose uptake becomes progressively restricted.

This mission is harder than Mission 26 because the player must not only run the sweep, but also provide a full product/byproduct evidence panel and interpret the collapse trend.

## Required simulator setup

Base setup before the sweep:

- Method: `FBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Genes: no knockouts
- Environment: unchanged

Bound Sweep Setup:

- Variable: `EX_glc__D_e` lower bound
- Preset values: `-1000, -500, -100, -50, -10, 0`

Production Flux evidence required:

- `EX_ac_e`
- `EX_etoh_e`
- `EX_for_e`
- `EX_lac__D_e`
- `EX_succ_e`

## What the player should observe

As the glucose lower bound moves closer to `0`, less glucose can be consumed.

The expected trend is:

- glucose uptake decreases;
- growth drops strongly;
- the final point shows severe or no growth;
- several product/byproduct fluxes decrease because the cell has less carbon available.

## Success criteria

The mission is ready to deliver when:

- the base setup is clean;
- the glucose lower-bound sweep is selected;
- all required sweep values are returned;
- the full Production Flux panel was selected;
- growth drops strongly across the sweep;
- final growth is very low;
- several tracked product/byproduct fluxes decrease.

## Optional hint

Do not look only at the final row. The important part is the trend: when carbon input goes down, growth and secretion should fall together.
