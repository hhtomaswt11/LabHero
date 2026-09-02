# Introduction to Constraint-Based Metabolic Modelling

Constraint-based modelling asks which reaction-flux patterns are compatible with a metabolic network and a set of assumptions. It is powerful precisely because those assumptions are explicit and testable.

## Reactions, metabolites and stoichiometry

A metabolic model represents reactions that consume and produce metabolites. Their stoichiometric coefficients form the matrix S, while the vector v contains reaction fluxes.

Under the steady-state assumption for internal metabolites, S v = 0. This is a mass-balance constraint, not a claim that the organism is unchanging in every biological sense.

## Bounds define the environment

Every reaction has a lower and upper bound. Bounds encode direction, capacity and environmental availability. Exchange-reaction bounds are therefore one of the main ways LabHero represents different media.

A configured bound defines what is allowed. The optimized flux tells you what the selected solution actually uses.

## Objectives are hypotheses

FBA needs an objective. Maximizing biomass is a useful modelling hypothesis for many growth experiments, but it is not a universal law of cellular behaviour.

Changing the objective can change the predicted flux distribution dramatically. Several LabHero missions exploit this deliberately to separate viability, product formation and optimization criteria.

## Alternative optima and method choice

Different flux distributions can achieve the same optimal objective. pFBA adds a parsimony criterion; lMOMA and ROOM instead compare a perturbed state with a reference. These methods therefore answer related but different questions.

Method names should never be treated as interchangeable. Before comparing numbers, ask what quantity that method optimized or minimized.

## Genes do not equal reactions

GPR rules connect genes to reaction capability. A reaction may need several genes (AND) or have alternative genes (OR), so a single gene knockout does not map mechanically to a single disabled reaction.

Phenotypes emerge from the remaining network and the environment. That is why LabHero tests gene essentiality, redundancy, rescue and context dependence rather than memorizing gene labels.

## What these models do not predict directly

Standard FBA does not directly predict metabolite concentrations, enzyme abundances, regulatory dynamics or time courses. Fluxes are steady-state rates consistent with the constraints and objective.

Treat every result as a conditional model prediction: 'under these assumptions, this solution is feasible/optimal', not as automatic proof of what a real cell must do.
