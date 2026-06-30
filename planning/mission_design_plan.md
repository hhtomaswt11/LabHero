# LabHero Mission Design and Progression Plan

## 1. Purpose

This document proposes a structured direction for the next stage of LabHero development. The goal is to extend the current prototype with new content, a clearer narrative progression, and interactive challenges that teach core concepts of constraint-based cellular modelling, including strain design and optimization.

The current version of LabHero already provides a functional gameplay loop:

1. The player talks to a scientist in a laboratory.
2. The scientist presents a mission.
3. The player accepts the mission.
4. The player uses the simulation computer/desk.
5. The player runs a metabolic simulation.
6. The player interprets the results.
7. The player returns to the scientist and delivers the answer.

This structure should be preserved, but expanded into a more coherent learning journey with progressive difficulty.

---

## 2. Internship Objectives and Development Interpretation

### Objective 1  
**Develop new LabHero content organized into narrative, missions and progressive levels.**

Interpretation for implementation:

- Reorganize the current missions into a clearer narrative sequence.
- Group missions by scientific theme.
- Add new missions that increase in difficulty.
- Use unlockable areas or doors to make progression visible inside the game world.
- Keep the current mission-based structure, but make the order and learning path more intentional.

### Objective 2  
**Create interactive challenges to teach fundamental concepts of constraint-based cellular modelling, including strain design and optimization.**

Interpretation for implementation:

- Create missions that require the player to actively change simulation parameters.
- Use the simulation computer as the main interaction point.
- Teach concepts through mission objectives, simulation setup, result interpretation and feedback.
- Progress from simple simulations to more advanced metabolic engineering tasks.
- Introduce strain design gradually, only after the player understands environmental changes and gene knockouts.

### Objective 3  
**Create a web service/interface that allows the game to be played online without local installation.**

Interpretation for implementation:

- Keep validating every new feature in both desktop and web modes.
- Ensure new missions and UI changes work with the current Docker/web deployment.
- Improve documentation for running the web version.
- Treat the final online deployment/documentation as a later stage, after the gameplay content is stable.

---

## 3. Current Game Structure

The current game contains three main missions:

| Current mission | Scientist | Theme | Main concept |
|---|---|---|---|
| Mission 01 — Into the Microbial World | Dr. Martinez | Environmental condition | Anaerobic growth / oxygen availability |
| Mission 02 — Genetic Mystery | Dr. Silva | Gene knockout | Essential gene identification |
| Mission 03 — Sweet as Glucose | Dr. Carter | Carbon source | Alternative substrate / glucose replacement |

Although these missions work, their narrative progression can be improved. The current structure introduces useful concepts, but the missions are not yet strongly organized by theme or difficulty.

---

## 4. Proposed Narrative Direction

The proposed narrative is that the player starts as a new bioinformatician learning how to use metabolic models to help researchers at the laboratory.

At first, the player learns to **observe** how *E. coli* behaves under different environmental conditions. Then, the player learns to **modify** the organism through genetic knockouts. Finally, the player progresses to **designing and optimizing** strains for specific metabolic goals.

This creates a progression from basic to advanced concepts:

```text
Observe the organism
        ↓
Modify environmental conditions
        ↓
Modify genes
        ↓
Compare growth and production
        ↓
Design and optimize a strain
```

This progression connects the gameplay to the scientific learning objectives.

---

## 5. Proposed Mission Organization by Theme

### Phase 1 — Environmental Adaptation

**Scientist:** Dr. Martinez  
**Theme:** How environmental conditions affect *E. coli* growth.  
**Learning goal:** Understand that metabolic models can predict growth under different environmental constraints.

Suggested missions:

| Mission | Status | Concept | Challenge |
|---|---|---|---|
| Mission 01 | Existing | Anaerobic growth | Remove oxygen uptake and observe growth |
| Mission 02 | Existing Mission 03 moved here | Carbon source replacement | Remove glucose and test alternative carbon sources |

Reasoning:

Both missions are about changing environmental conditions. Moving the current glucose mission from Dr. Carter to Dr. Martinez makes the narrative more coherent, because Dr. Martinez becomes responsible for environmental adaptation and nutrient-related challenges.

---

### Phase 2 — Genetic Perturbation

**Scientist:** Dr. Silva  
**Theme:** How genes affect metabolic behaviour.  
**Learning goal:** Understand gene knockouts and their effects on growth and production.

Suggested missions:

| Mission | Status | Concept | Challenge |
|---|---|---|---|
| Mission 03 | Existing Mission 02 moved here | Essential genes | Knock out genes one at a time and identify the essential gene |
| Mission 04 | New | Knockout for production | Remove a gene to increase production of a target metabolite |

Reasoning:

Dr. Silva already introduces gene knockouts. The new mission should build on this by showing that knockouts can be used not only to test survival, but also to redirect metabolism toward production.

Scientific details that need validation:

- Target metabolite to use.
- Candidate genes to test.
- Expected best knockout.
- Minimum acceptable growth threshold, if needed.

---

### Phase 3 — Metabolic Engineering

**Scientist:** Dr. Carter  
**Theme:** Growth vs production and strain design.  
**Learning goal:** Understand that metabolic engineering often requires balancing biomass growth with product formation.

Suggested missions:

| Mission | Status | Concept | Challenge |
|---|---|---|---|
| Mission 05 | New | Metabolic objective | Compare growth-focused simulation with production-focused simulation |
| Mission 06 | New / optional | Strain optimization | Find a setup that improves product formation while preserving growth |

Reasoning:

After the player understands environmental constraints and gene knockouts, Dr. Carter can introduce more advanced metabolic engineering tasks. This makes him responsible for production-oriented challenges rather than the introductory glucose mission.

Scientific details that need validation:

- Which production objective should be used.
- Whether the current simulation menu already supports this objective clearly enough.
- Which result should the player be asked to report.
- Whether this mission should require only objective changes or also gene/environment modifications.

---

## 6. Proposed Level Progression and Locked Areas

To make the progression visible in the game world, locked doors or blocked areas can be added.

Suggested unlock logic:

```text
Initial access:
- Dr. Martinez area / environmental missions

After completing Phase 1:
- Unlock Dr. Silva area / genetic perturbation missions

After completing Phase 2:
- Unlock Dr. Carter area / metabolic engineering missions
```

A simple first implementation could be:

- A closed door sprite or collision area.
- When the player interacts with it before completing the required missions, a message appears:
  - "This area is locked. Complete the previous missions first."
- After completing the required missions, the door allows access or changes its message:
  - "New research area unlocked: Genetic Perturbation Lab."

This does not need to be visually complex at first. The priority is to make progression clear.

---

## 7. Recent Usability Improvements Already Implemented

Two small usability improvements have already been implemented or planned:

### Gene labels in the simulation computer

The simulation menu now displays gene IDs together with readable gene names when available, for example:

```text
b2926 (pgk)
```

The internal simulation still uses the gene ID, while the UI becomes easier to understand.

### Simulation summary after running a simulation

After running a simulation, the player should be able to open a static summary showing:

- Simulation method.
- Objective function.
- Knocked-out genes, if any.
- Changed environmental conditions, if any.

This improves result interpretation because the player can connect the final result with the simulation setup that produced it.

---

## 8. Proposed Implementation Roadmap

### Step 1 — Planning and validation

Create and validate this mission progression plan with the supervisor/Mónica.

Deliverables:

- Mission progression document.
- List of proposed mission changes.
- List of scientific questions requiring validation.

Important questions:

1. Is the proposed reorganization of scientists by theme acceptable?
2. Should the current Mission 03 be moved from Dr. Carter to Dr. Martinez?
3. Which metabolite/product should be used for the new production-oriented missions?
4. Which genes should be used in the knockout-for-production mission?
5. Should the next implementation focus first on mission reorganization or on adding the first new mission?

---

### Step 2 — Reorganize current missions conceptually

Before creating new missions, update the current mission order and narrative.

Possible changes:

- Move the glucose/carbon-source mission to Dr. Martinez.
- Keep the essential-gene mission with Dr. Silva.
- Free Dr. Carter for advanced metabolic engineering content.

This may require changes in:

- Mission dialogue files.
- Mission markdown descriptions.
- Mission IDs/order.
- NPC assignment.
- Menu labels.
- Save/progress logic, if mission IDs are changed.

Recommendation:

Avoid renaming mission IDs immediately unless necessary. It may be safer to first change narrative/dialogue while preserving IDs internally, then refactor IDs later if needed.

---

### Step 3 — Implement one new mission as a vertical slice

Do not implement all new missions at once. First create one complete mission from start to finish.

Recommended first new mission:

**Knockout for production** with Dr. Silva.

Why:

- It extends the existing gene knockout concept.
- It is easier to connect with the current simulation menu.
- It prepares the player for strain design.

Vertical slice requirements:

- New mission dialogue.
- New mission briefing.
- New mission activation.
- Simulation setup required.
- Correct answer validation.
- Completion state.
- Save/load support.
- Works in desktop and web.

---

### Step 4 — Add locked doors / progression

After the first new mission works, implement a simple unlock system.

Initial version:

- Door blocks access to advanced area.
- Door opens only after required missions are completed.
- If locked, display explanatory message.

This supports the "progressive levels" requirement.

---

### Step 5 — Add advanced metabolic engineering mission

After the player has environmental and genetic knowledge, implement a Dr. Carter mission about objective functions and growth vs production.

Recommended concept:

- Compare a biomass objective with a production objective.
- Ask the player to interpret how the result changes.
- Introduce the idea that maximizing growth is not always the same as maximizing production.

---

### Step 6 — Web/deployment refinement

Once the gameplay content is stable:

- Confirm all missions work in web mode.
- Confirm simulation requests work through the backend.
- Update web deployment documentation.
- Prepare a final demonstration workflow.

---

## 9. Suggested Short-Term Task List

Immediate next tasks:

1. Ask for the scientifically correct target metabolite and candidate genes for the new production missions.
2. Test desktop and web versions.
3. Start implementing one new mission as a vertical slice.

---

## 10. Scientific Validation Checklist

Before implementing the new scientific missions, confirm:

- Target metabolite/product.
- Correct objective function ID.
- Candidate genes.
- Expected simulation results.
- Whether the mission should accept a gene ID, a metabolite name, or a numeric result.
- Whether the success condition should be exact or tolerance-based.
- Whether growth must remain above a minimum threshold.
- Whether the mission should use FBA only or compare FBA/pFBA/lMOMA/ROOM.

---

## 11. Technical Notes

Current code considerations:

- The existing mission logic is implemented in separate files such as `mission01.py`, `mission02.py`, and `mission03.py`.
- Mission state is stored through activated/completed mission lists.
- The simulation computer already provides method, objective, gene and environmental condition settings.
- The game currently uses *E. coli* as the main model.
- Desktop and web versions should both be tested after every meaningful change.

Recommended implementation strategy:

- Keep changes small and incremental.
- Avoid changing internal mission IDs unless needed.
- Preserve the existing gameplay loop.
- Prefer one complete new mission over several incomplete ones.
- Keep scientific mission definitions validated by the supervisor/Mónica.
