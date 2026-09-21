# Mission 25 — Context-Dependent Gene Essentiality

## Scientist
Dr. Smith

## Lab
Laboratory 9 — Context and Dependency Lab

## Main idea
The same gene knockout can have a very different predicted growth effect in two environmental contexts. The player must construct a complete two-by-two matrix rather than interpreting one isolated mutant result.

## Scientific concept
Gene essentiality is conditional on the model, objective and environment. A gene that is nearly dispensable with oxygen available may become operationally essential when oxygen uptake is blocked because the available metabolic alternatives have changed.

The mission tests `b3956 / ppc`, whose GPR controls the `PPC` reaction in the E. coli core model.

## Controlled matrix
Record four visible FBA simulations with objective `BIOMASS_Ecoli_core_w_GAM`:

1. Aerobic wild type — every gene active and every environmental bound at model default.
2. Aerobic knockout — same environment with only `b3956 / ppc` disabled.
3. Anaerobic wild type — every gene active, with only the lower bound of `EX_o2_e` closed.
4. Anaerobic knockout — the same oxygen-blocked medium with only `b3956 / ppc` disabled.

The order is unrestricted. Repeating a valid condition replaces that matrix cell without duplicating evidence. An invalid later run does not erase previously recorded cells.

## Required visible evidence
Every matrix cell must include:

- numeric biomass-objective flux;
- numeric biomass-reaction flux;
- numeric glucose and oxygen exchange values;
- FBA primary-objective diagnostics;
- total absolute flux and active-reaction count;
- complete environmental-bound data;
- either no knockout or exactly the target single-gene knockout.

No Production Flux selection is required because the experimental question concerns within-context growth retention.

## Expected model results
Approximate values are:

| Context | Genotype | Growth | Oxygen uptake |
|---|---|---:|---:|
| Aerobic | wild type | 0.874 | 21.799 |
| Aerobic | `b3956` knockout | 0.871 | 21.938 |
| Anaerobic | wild type | 0.212 | 0.000 |
| Anaerobic | `b3956` knockout | 0.000 | 0.000 |

The aerobic knockout retains approximately 99.6% of its matching wild-type growth. The anaerobic knockout retains approximately 0% of its matching wild-type growth.

## Player conclusion
After all four cells are recorded, the player answers:

> In which oxygen context did the same knockout produce the strongest predicted growth defect?

The report presents both within-context retention values but does not state the answer. English and European Portuguese descriptions of the oxygen context are accepted.

## Scientific limitation
The conclusion is operational and conditional. It does not establish that `ppc` is universally essential in real E. coli across all media, objectives or experimental conditions.

## Web-service readiness
The mission validates the structured result already returned by the normal simulation endpoint. It launches no hidden solver or HTTP request, accumulates only JSON-serialisable state and uses identical validation logic for desktop and browser execution.
