# How to Simulate

Use this book as a reference for the simulator. The most important rule is to distinguish the model's primary objective from secondary method scores and from any individual reaction flux.

## FBA: Flux Balance Analysis

FBA assumes a steady-state intracellular mass balance, commonly written S v = 0. Reaction lower and upper bounds define the feasible flux space, and a linear objective is optimized inside that space.

If the biomass reaction is the objective, its optimal flux is a model proxy for biomass production under the chosen assumptions. If an exchange reaction is the objective, the reported objective flux is that exchange flux instead; do not call every objective value a growth rate.

## pFBA: Parsimonious FBA

pFBA first preserves the optimal primary objective found by FBA and then minimizes total flux usage. It therefore selects a parsimonious solution among primary-optimal alternatives.

The pFBA secondary quantity is not a second biological objective and a larger value is not automatically better. Compare primary objective fluxes first, then use total absolute flux or the displayed pFBA diagnostic to discuss parsimony.

## lMOMA: minimal adjustment

lMOMA compares a perturbed state with a reference state and finds a feasible flux distribution with a small linearized adjustment from that reference. It answers a different question from FBA: adaptation near a reference rather than complete re-optimization of the primary objective.

A meaningful comparison requires a valid reference generated under the intended pre-perturbation conditions.

## ROOM: regulatory on/off minimization

ROOM also requires a pre-knockout reference. LabHero records that reference before the perturbation and compares the mutant in the same environment unless the mission explicitly changes the environment.

A reaction counts as significantly changed when it leaves the tolerance band defined from the reference using delta and epsilon. The ROOM method score is an integer ROOM change count, not predicted growth rate. A smaller count means fewer reactions crossed that significant-change criterion; it does not by itself mean that the mutant grows better.

## Objectives

The Objective menu chooses what the optimization attempts to maximize. Biomass is common, but several missions deliberately maximize an exchange flux to expose trade-offs between growth and production.

When comparing runs, keep the objective fixed unless changing it is the experimental variable. Record predicted growth rate separately when viability or growth capability is part of the question.

## Environmental bounds and exchange fluxes

Exchange reactions connect the model with its environment. In the LabHero convention used by the supplied models, a negative exchange flux usually represents uptake and a positive exchange flux secretion.

A lower bound such as -10 permits uptake up to that magnitude; it does not force the cell to use exactly 10. Likewise, an upper bound may be non-binding if the optimal solution never reaches it. Inspect the actual exchange flux before claiming that a bound constrained the solution.

## Genes and GPR rules

Gene knockouts act through gene-protein-reaction (GPR) rules. AND means all listed gene products are required for that reaction; OR represents alternative gene products that may preserve activity.

A zero-growth knockout is therefore context dependent: objective, medium, oxygen availability and alternative pathways all matter. Do not describe a gene as universally essential from a single model condition.

## Bound Sweeps and controlled comparisons

A Bound Sweep repeats the same model setup across several values of one bound. It is useful for finding thresholds, non-binding regions and changes in secretion or predicted growth rate.

For interpretable evidence, vary one intended factor at a time. Keep method, objective, gene state and unrelated bounds unchanged unless the mission explicitly defines a factorial experiment.

## Reading the reports

Always check solver status. Then distinguish Primary Objective Flux, Predicted Growth Rate, exchange/production fluxes and method-specific diagnostics. They answer different questions.

Use Compare Runs, Exchange Flux Report and Bound Sweep Report when a mission asks for quantitative evidence. The mission validator uses the visible recorded evidence rather than assuming that your latest configuration was valid.


## Units used in LabHero
Predicted growth rate is displayed in `h^-1`. Reaction and exchange fluxes, including configured bounds, are displayed in `mmol gDW^-1 h^-1`. Aggregate optimisation diagnostics such as pFBA total absolute flux and the lMOMA adjustment score are displayed in `model flux units`. Counts, percentages, fold changes and ROOM scores are dimensionless or count-valued and are not given flux units.
