# Mission 09 — Integrated Environment-and-Gene Design

## Theme
Controlled strain design that combines carbon-source replacement with one gene knockout.

## Learning goal
The player learns to evaluate an integrated design using one visible biomass-optimal solution: environmental context, genetic perturbation, predicted growth and product secretion must all be controlled and interpreted together.

## Scenario
Dr. Nova asks the player to replace glucose with L-malate and identify which single candidate knockout creates useful growth-coupled formate secretion while preserving most of the reference growth.

## Controlled experiment
- FBA;
- biomass objective;
- glucose unavailable;
- L-malate available as the replacement carbon source;
- oxygen and all remaining environmental bounds unchanged;
- formate exchange (`EX_for_e`) tracked;
- all genes active in the reference;
- exactly one highlighted candidate knockout in each genetic trial.

## Candidate genes
- `b1479 / maeA`;
- `b0721 / sdhC`;
- `b0116 / lpd`;
- `b0115 / aceF`.

## Operational criteria
A candidate must retain at least 80% of the no-knockout L-malate reference growth and increase formate secretion by at least 1.0 in the same biomass-optimal solution. These are mission criteria, not universal biological definitions.

## Expected evidence
The candidate screen should identify `b0115 / aceF` as the unique best eligible design. The result is conditional on this model, medium, objective and bounds.
