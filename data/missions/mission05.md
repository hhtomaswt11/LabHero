# Mission 05 — Knockout for Production under Anaerobic Conditions

## Objective

Discover which gene knockout improves lactate production when *E. coli* is growing without oxygen.

## Concept

In Mission 04, you tested a gene knockout under default aerobic conditions.

In this mission, you must combine two variables:

1. an environmental change: close the lower bound of the O2 exchange reaction (`EX_o2_e`);
2. a genetic change: knock out one candidate gene at a time.

This shows that metabolic engineering often depends on both the cell's environment and its genotype.

## Target product

- Product: lactate
- Production reaction: `EX_lac__D_e`

## Candidate genes

- `b0903` (`pflB`)
- `b1241` (`adhE`)
- `b2297` (`pta`)
- `b0723` (`sdhA`)
- `b3115` (`tdcD`)
- `b0728` (`sucC`)

## Expected answer

The expected answer is:

```text
b0903
```

The common gene name `pflB` is also accepted.

## Tasks

1. Go to the simulation computer.
2. In Environmental Conditions, close the lower bound of `EX_o2_e`.
3. In Genes, switch off one candidate gene at a time.
4. Run the simulation.
5. Check the Mission 05 Production Check in New Results.
6. Return to Dr. Silva and report the correct gene.
