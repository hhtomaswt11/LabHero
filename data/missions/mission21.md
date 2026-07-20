# Mission 21 — Controlled Comparison

## Scientist
Dr. Vega — Comparative Experiment Lab

## Theme
Controlled comparisons between two simulations.

## Concept
A single simulation tells the player what happens in one setup. A comparison shows what changes when one variable is altered.

Mission 21 compares normal aerobic growth with oxygen-limited growth. The biological idea is simple: if oxygen uptake is removed, the model has less respiratory capacity, so growth should drop.

## New functionality introduced
**Compare Runs**

The simulator now captures the previous simulation as **Run A** and the latest simulation as **Run B**. The report compares:

- growth/objective value;
- oxygen uptake;
- tracked production fluxes, when selected.

## How to complete

### Run A — baseline
- Simulation Method: `FBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Genes: no knockouts
- Environmental Conditions: unchanged
- Run Simulation

### Run B — oxygen-limited setup
- Simulation Method: `FBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Genes: no knockouts
- Environmental Conditions: close only the lower bound of `EX_o2_e`
- Run Simulation

Then open:

`New Results -> Compare Runs`

The mission passes when the comparison contains the baseline run, the oxygen-limited run, and a clear growth decrease.
