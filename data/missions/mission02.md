# Mission 02: Sweet as Glucose

After studying how *E. coli* responds to oxygen availability, the next environmental challenge is carbon-source availability.

The culture has lost access to its usual glucose supply. Several alternative carbon sources are available, but they may not support the same predicted growth.

Your task is to design a fair comparison, use the simulation evidence and identify the strongest replacement among:

- malate
- lactate
- glutamate
- glutamine
- fumarate
- fructose
- ethanol
- 2-oxoglutarate
- acetaldehyde
- acetate

The conclusion must come from the model results rather than from guessing.

## Dialogue with the Scientist

**Scientist:** "The culture can no longer use its usual carbon source. I prepared several alternatives, but I need a controlled comparison before choosing one. Which candidate best restores predicted growth?"

*After activating the mission:*

**Scientist:** "Have you built enough evidence to defend one candidate? Show me how the growth results support your conclusion."

*After completing the mission:*

**Scientist:** "Excellent work! You showed that nutrient availability changes predicted growth and that a valid conclusion depends on a controlled experiment."

## Mission Briefing

Carbon sources provide material and energy for cellular metabolism. In a constraint-based model, their availability is represented through exchange-reaction bounds.

Determine which candidate best supports predicted *E. coli* growth when the usual source is unavailable. The trials must be comparable, but deciding how to construct that comparison is part of the challenge.

Think about:

- the difference between replacing a nutrient and supplementing it;
- which experimental factor should change between trials;
- which assumptions should remain comparable;
- which simulation result provides evidence for growth.

## Optional hints

1. A fair experiment changes the factor under study while keeping unrelated assumptions comparable.
2. A true replacement is tested without leaving the usual carbon source available, and alternatives should be examined separately.
3. Use FBA with the biomass objective, keep genes and oxygen unchanged, test one candidate uptake at a time, and give every candidate the same molar uptake allowance (`-10`).
