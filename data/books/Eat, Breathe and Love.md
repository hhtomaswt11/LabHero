# Eat, Breathe and Ferment

Nutrients, electron acceptors and redox balance shape metabolic behaviour. This book connects the environmental experiments in LabHero with the fermentation phenotypes explored in E. coli and yeast.

## Eat: nutrient availability

Carbon sources provide atoms and reducing power, but uptake is limited by exchange bounds and by the reactions available inside the model. Supplying a nutrient does not guarantee that the network can use it.

Nutrient screens and bound sweeps should therefore be read from the optimized uptake fluxes, not from the configured bounds alone.

## Breathe: oxygen as an environmental constraint

Oxygen uptake can enable respiratory flux patterns with different energy and redox consequences from oxygen-limited states. In the simulator, changing EX_o2_e changes a constraint; the resulting flux distribution is then selected by the chosen method and objective.

A zero oxygen-uptake bound represents an anaerobic model condition. Intermediate caps can reveal transitions rather than a simple binary aerobic/anaerobic switch.

## Ferment: balancing redox without full respiration

Fermentation routes can reoxidize cofactors and secrete reduced products when respiratory capacity is absent or limited. The exact products and quantitative fluxes are network- and condition-dependent.

For E. coli, LabHero tracks products such as ethanol, acetate, formate and succinate in several missions. Their fluxes are evidence about how the optimized network redistributed carbon and redox demand.

## Yeast and iMM904

The Golden Lab introduces Saccharomyces cerevisiae through iMM904, a larger genome-scale model. The same principles still apply: choose a method and objective, constrain exchanges, inspect fluxes and compare controlled conditions.

Mission 36 uses an oxygen-cap sweep to identify the onset of a fermentative phenotype. The lesson is not that one oxygen value is universal, but that a model can be interrogated systematically for condition-dependent transitions.

## Interpretation discipline

Do not infer concentrations or time-dependent growth curves from a steady-state flux alone. Do not call a permitted uptake bound an observed uptake, and do not equate a method score with predicted growth rate.

State the model, method, objective and changed constraint when reporting a result. That makes the conclusion reproducible and scientifically meaningful.
