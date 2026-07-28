# Mission 04 — Growth-Coupled Ethanol Production

## NPC
Dr. Silva

## Theme
Using a controlled gene knockout to redirect flux toward a product while preserving predicted growth.

## Challenge
The culture retains the unchanged default aerobic medium. Determine whether one candidate knockout causes ethanol secretion in a biomass-optimal FBA solution without eliminating predicted growth.

## Target product
- Product: ethanol
- Exchange reaction: `EX_etoh_e`

## Candidate genes
- `b1241 / adhE`
- `b0728 / sucC`
- `b3736 / atpF`
- `b2278 / nuoL`

## Controlled evidence
The mission requires:

1. A no-knockout reference with FBA, the biomass objective, the unchanged default environment and `EX_etoh_e` tracked.
2. One valid trial for each candidate, changing exactly one gene and keeping every other experimental condition equal to the reference.
3. Comparison of predicted growth, growth relative to the reference, ethanol secretion and oxygen uptake.

## Operational mission criteria
- The candidate must retain at least 10% of the reference growth.
- Ethanol secretion must increase by at least 1.0 relative to the reference.
- These thresholds are mission criteria, not universal biological definitions.

## Expected controlled results
| Gene | Approx. growth | Approx. ethanol | Interpretation |
|---|---:|---:|---|
| `b1241 / adhE` | 0.874 | 0.000 | no apparent production effect; alternative genes preserve the relevant GPR functions |
| `b0728 / sucC` | 0.858 | 0.000 | small growth loss without ethanol redirection |
| `b3736 / atpF` | 0.374 | 0.000 | strong growth loss without ethanol redirection |
| `b2278 / nuoL` | 0.212 | 8.279 | growth-coupled ethanol secretion |

## Expected conclusion
`b2278 / nuoL`

The result is conditional on the `e_coli_core` model, the default medium, the biomass objective and the constraints used. It does not claim that this knockout is universally optimal in real organisms or under every growth condition.

## Pedagogical progression
Mission 03 showed that knockouts can have effects ranging from redundancy to loss of predicted growth. Mission 04 adds a second question: does the lost metabolic capacity actually redirect flux toward a useful product? A reduction in growth alone is not sufficient evidence of successful strain design.
