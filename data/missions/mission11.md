# Mission 11 — Flux Fingerprint

## Theme
Flux Diagnostics & Pathway Evidence

## Learning goal
Understand that a simulation result should not be interpreted only through the objective value. A strain may remain viable, but its exchange fluxes reveal which products are actually being secreted.

## Scenario
Dr. Almeida studies how metabolic fluxes can be used as evidence. After the Advanced Strain Design missions, the player must learn to diagnose the phenotype produced by a simulation.

## Challenge
Build a secretion fingerprint for *E. coli* under respiration-limited growth.

The player should keep the experiment controlled:

- use the standard biomass objective;
- keep the strain unchanged;
- apply one biologically meaningful environmental constraint;
- track a production-flux panel.

## Production flux panel

- `EX_ac_e` — acetate
- `EX_for_e` — formate
- `EX_etoh_e` — ethanol
- `EX_lac__D_e` — D-lactate
- `EX_succ_e` — succinate

## Briefing focus
A growth value answers whether the model remains viable. Production fluxes answer a different question: what the model is secreting. By tracking several exchange reactions, the player can build a metabolic fingerprint instead of relying on a single value.

The goal is not to redesign the strain yet. The goal is to collect evidence and interpret the phenotype.
