# Mission 03: Genetic Mystery - The Essential Gene

Dr. Silva has selected a small set of candidate genes from *E. coli*.
One of them appears to be critical for survival.

Your goal is to use knockout simulations to identify which candidate gene has the strongest impact on growth.

## Dialogue with Dr. Silva

**Dr. Silva:** "Greetings! I have a small set of candidate genes from *E. coli*. One of them seems critical for survival. Can you identify which one?"

*After activating the mission:*

**Dr. Silva:** "Have you tested the candidate knockouts? Show me what the growth results revealed."

*After completing the mission:*

**Dr. Silva:** "Very good! You learned how a knockout can reveal an essential gene. But knockouts are not only used to test survival. They can also redirect metabolism toward useful products."

## Mission Description

Candidate genes:
- b1241
- b3115
- b3736
- b2975
- b1524
- b2278
- b2926
- b2297
- b0728
- b3919

Run simulations, compare growth behaviour, and deliver the gene that best explains the loss of viability.

## Mission Briefing

An essential gene is a gene that the organism needs to maintain a viable metabolic state. If that gene is removed, the model may lose the ability to support normal growth.

Gene knockout simulations are used to test this idea computationally: instead of changing the environment, the model is perturbed genetically and the growth response is observed.

Use the candidate list as the search space and compare the growth behaviour after each genetic perturbation. The strongest loss of viability is the key evidence.
