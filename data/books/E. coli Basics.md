# E. coli and the Core Metabolic Model

Escherichia coli is a major experimental and industrial model organism. LabHero begins with a compact E. coli core network so that central metabolic trade-offs remain visible while you learn constraint-based analysis.

## Central carbon metabolism

Glucose can feed glycolysis, the pentose-phosphate pathway and the tricarboxylic-acid network. These pathways exchange carbon, reducing power and precursor metabolites needed for biomass formation.

The core model intentionally omits much of the full organism. Its simplicity is useful for reasoning, but predictions should be interpreted as properties of this model under the selected conditions.

## Aerobic and oxygen-limited states

When oxygen uptake is available, respiratory pathways can support efficient reoxidation of reducing equivalents and high predicted growth rate. Closing or limiting oxygen forces the feasible network to redistribute flux through alternative pathways.

Anaerobic does not mean 'no metabolism'. E. coli can maintain redox balance through fermentative products and other routes represented in the model, depending on available nutrients and bounds.

## Growth versus production

Maximizing the biomass reaction and maximizing a secreted product are different objectives. A design with high product flux can have poor predicted growth rate, and a high-growth solution can secrete little of the target product.

Metabolic engineering therefore involves trade-offs. LabHero missions use controlled objectives, knockouts and environmental constraints to make those trade-offs measurable.

## Gene knockouts and redundancy

Knocking out a gene disables only reactions whose GPR rules require that gene. Alternative isoenzymes or pathways can preserve the phenotype, while the same knockout may become severe in a different environment.

This is why essentiality is context dependent and why rescue experiments must distinguish restored predicted growth rate from restoration of the deleted gene or reaction.

## Reading exchange reactions

Exchange IDs such as EX_glc__D_e or EX_o2_e describe transfer between the model and its environment. In LabHero's convention, negative flux typically denotes uptake and positive flux secretion.

Always inspect the actual optimized exchange flux. A permissive lower bound does not prove that the model consumed the full permitted amount.
