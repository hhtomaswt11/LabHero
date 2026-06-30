# LabHero Mission Design and Progression Plan — v2

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

This structure should be preserved, but expanded into a more coherent learning journey with progressive difficulty and clearer narrative transitions between topics.

---

## 2. Internship Objectives and Development Interpretation

### Objective 1  
**Develop new LabHero content organized into narrative, missions and progressive levels.**

Implementation interpretation:

- Reorganize the current missions into a clearer narrative sequence.
- Add new missions that increase in difficulty.
- Use locked areas, locked laboratories or locked mission access to make progression visible inside the game world.
- Introduce narrative transitions between mission groups, so the player understands why a new topic or scientist becomes relevant.
- Keep the current mission-based structure, but make the order and learning path more intentional.

### Objective 2  
**Create interactive challenges to teach fundamental concepts of constraint-based cellular modelling, including strain design and optimization.**

Implementation interpretation:

- Create missions that require the player to actively change simulation parameters.
- Use the simulation computer as the main interaction point.
- Teach concepts through mission objectives, simulation setup, result interpretation and feedback.
- Progress from simple simulations to more advanced metabolic engineering tasks.
- Introduce strain design gradually, only after the player understands environmental changes and gene knockouts.

### Objective 3  
**Create a web service/interface that allows the game to be played online without local installation.**

Implementation interpretation:

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

Although these missions work, their narrative progression can be improved. The current structure introduces useful concepts, but the missions are not yet strongly connected through an explicit story or through visible progression inside the game world.

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

To make this progression more visible and engaging, the game can introduce a **mentor handoff system**: after the player completes a set of missions, the current scientist concludes their teaching segment and introduces the next scientist/topic.

This would turn mission progression into a small narrative sequence instead of isolated tasks.

---

## 5. Mentor Handoff System

### Concept

The laboratory scientists are not only mission providers. They become mentors who guide the player through different scientific topics.

When the player completes a mission group, the current mentor tells the player to speak with them again. This starts a short transition sequence in which the current mentor introduces the next mentor.

Example narrative:

```text
Dr. Martinez:
"My part is complete. You now understand how environmental conditions affect E. coli.
The next step is learning how genes change metabolic behaviour. Dr. Silva can help you with that."

Dr. Silva:
"Great work. Now that you understand environmental constraints, we can start exploring genetic changes.
Let's see what happens when specific genes are removed."
```

This creates a clearer storytelling structure and gives meaning to the scientists who are currently present in the office but have limited gameplay function.

---

## 6. Recommended Implementation Strategy for the Handoff

The final version could include automatic movement/cutscenes, but this should be implemented progressively.

### Version 1 — Simple dialogue handoff

The safest first implementation.

- After completing the required mission(s), the player is asked to return to the current scientist.
- The scientist gives a closing dialogue.
- The next scientist is introduced through dialogue.
- The next mission/lab becomes available.
- No automatic movement is required.

Advantages:

- Simple to implement.
- Low risk.
- Directly improves the narrative.
- Avoids complex pathfinding or cutscene logic.

---

### Version 2 — Static character swap

A slightly more visual version.

- After the handoff dialogue, the next scientist appears in the relevant laboratory.
- The previous scientist may remain in place or return to the office area.
- This can be implemented by changing NPC visibility/position after progression.

Advantages:

- More visual than dialogue-only.
- Still much simpler than animated walking.
- Makes progression clearer.

---

### Version 3 — Scripted movement / cutscene

A future improvement.

- The current scientist automatically walks from the laboratory to another professor/NPC.
- The player can follow or watch the movement.
- The two scientists face each other and exchange dialogue.
- The new scientist then walks to the laboratory.
- The next mission becomes available.

Advantages:

- More engaging and memorable.
- Strong storytelling moment.

Risks:

- Requires scripted NPC movement.
- Requires handling collisions or movement paths.
- Requires controlling player input during the sequence or ensuring the player does not break the cutscene.
- More complex to maintain in both desktop and web modes.

Recommendation:

Implement Version 1 first. Treat animated movement as future work or a later enhancement after the mission system is stable.

---

## 7. Mission Progression Model

There are two possible progression models.

### Option A — Theme-based phases

Each scientist owns one theme and may provide multiple missions.

| Phase | Scientist | Theme | Missions |
|---|---|---|---|
| Phase 1 | Dr. Martinez | Environment and nutrients | Oxygen availability + carbon source |
| Phase 2 | Dr. Silva | Genes and knockouts | Essential gene + knockout for production |
| Phase 3 | Dr. Carter | Metabolic engineering | Growth vs production + strain optimization |

Advantages:

- Scientifically coherent.
- Easy to explain.
- Supports multiple missions per scientist.

---

### Option B — Sequential mission handoff

Only one mission or small mission block is active at a time. Completing one mission unlocks the next scientist/topic.

Example:

```text
Mission 1 available
Mission 2 locked
Mission 3 locked

Mission 1 completed
Mission 2 unlocked

Mission 2 completed
Mission 3 unlocked

Mission 3 completed
Mentor handoff sequence starts
Next scientist/topic unlocked
```

Advantages:

- Very clear progression.
- Stronger storytelling.
- Easier for the player to know what to do next.
- Works well with locked doors and guided learning.

---

### Recommended approach

Use a hybrid model:

- Organize the learning path by scientific themes.
- Unlock missions sequentially to avoid overwhelming the player.
- Use mentor handoff moments between themes.

This avoids the contradiction between "two missions per scientist" and "one mission unlocked at a time". A scientist can still represent a theme, but the missions can be unlocked one by one.

Example:

```text
Dr. Martinez phase:
- Mission 1 unlocked first
- Mission 2 unlocked only after Mission 1 is completed

After Dr. Martinez phase:
- handoff to Dr. Silva

Dr. Silva phase:
- Mission 3 unlocked first
- Mission 4 unlocked only after Mission 3 is completed

After Dr. Silva phase:
- handoff to Dr. Carter
```

---

## 8. Updated Proposed Mission Organization

### Phase 1 — Environmental Adaptation

**Scientist:** Dr. Martinez  
**Theme:** How environmental conditions affect *E. coli* growth.  
**Learning goal:** Understand that metabolic models can predict growth under different environmental constraints.

Suggested missions:

| Mission | Status | Concept | Challenge |
|---|---|---|---|
| Mission 01 | Existing | Anaerobic growth | Remove oxygen uptake and observe growth |
| Mission 02 | Existing Mission 03 moved here | Carbon source replacement | Remove glucose and test alternative carbon sources |

Narrative role:

Dr. Martinez introduces the player to basic simulations. The player learns that environmental conditions and nutrients can change the predicted behaviour of *E. coli*.

Transition after phase:

Dr. Martinez tells the player that they are ready to study genetic changes and introduces Dr. Silva.

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

Narrative role:

Dr. Silva explains that changing environmental conditions is only one part of metabolic modelling. The next step is understanding what happens when genes are removed.

Transition after phase:

Dr. Silva introduces Dr. Carter and explains that genetic changes can be used for metabolic engineering and production goals.

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

Narrative role:

Dr. Carter introduces the player to the idea that the goal of a simulation is not always maximum growth. Sometimes the objective is to produce a compound, which can create a trade-off between cell growth and production.

Scientific details that need validation:

- Which production objective should be used.
- Whether the current simulation menu already supports this objective clearly enough.
- Which result should the player be asked to report.
- Whether this mission should require only objective changes or also gene/environment modifications.

---

## 9. Locked Missions, Doors and Progression

The game can use locked missions and locked areas to guide the player.

### Simple mission lock logic

```text
Mission 1 unlocked by default.
Mission 2 unlocks after Mission 1 is completed.
Mission 3 unlocks after Mission 2 is completed.
Mission 4 unlocks after Mission 3 is completed.
```

If the player tries to access a locked mission:

```text
"This mission is not available yet. Complete the previous mission first."
```

### Door/area lock logic

Doors can be used to separate phases:

```text
Phase 1 available at start.
Phase 2 unlocks after completing Phase 1.
Phase 3 unlocks after completing Phase 2.
```

If the player interacts with a locked door:

```text
"This area is locked. Complete the current research topic first."
```

When unlocked:

```text
"New research area unlocked: Genetic Perturbation Lab."
```

This supports the "progressive levels" requirement and makes progression visible.

---

## 10. Recent Usability Improvements Already Implemented or Planned

### Gene labels in the simulation computer

The simulation menu displays gene IDs together with readable gene names when available, for example:

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

## 11. Proposed Implementation Roadmap

### Step 1 — Planning and validation

Validate this updated progression plan with the supervisor/Mónica.

Important questions:

1. Is the mentor handoff idea appropriate for LabHero?
2. Should the handoff initially be implemented only with dialogue, leaving animation for future work?
3. Is the proposed reorganization of scientists by theme acceptable?
4. Should the current carbon-source mission be moved from Dr. Carter to Dr. Martinez?
5. Which metabolite/product should be used for the new production-oriented missions?
6. Which genes should be used in the knockout-for-production mission?
7. Should the next implementation focus first on sequential mission locking or on adding the first new mission?

---

### Step 2 — Stabilize UI improvements

Finish and test smaller UI improvements:

- Gene names in the simulation menu.
- Simulation summary in the results menu.

Testing:

```text
Desktop: python LabHero.py
Web: cd deploy && docker compose build && docker compose up -d
```

---

### Step 3 — Implement sequential mission locking

Before adding animated handoffs, implement a simple mission lock system.

First version:

- Mission 1 available.
- Mission 2 locked until Mission 1 is complete.
- Mission 3 locked until Mission 2 is complete.

This creates progression without requiring map or animation changes.

---

### Step 4 — Add dialogue-based mentor handoff

After the current mission chain is complete:

- The player is told to speak again with the current scientist.
- The scientist introduces the next topic/scientist.
- The next mission/phase becomes available.

This can be implemented before automatic movement.

---

### Step 5 — Reorganize current missions conceptually

Update the current mission order and narrative.

Possible changes:

- Move the glucose/carbon-source mission to Dr. Martinez.
- Keep the essential-gene mission with Dr. Silva.
- Free Dr. Carter for advanced metabolic engineering content.

Recommendation:

Avoid renaming mission IDs immediately unless necessary. It may be safer to first change narrative/dialogue while preserving IDs internally, then refactor IDs later if needed.

---

### Step 6 — Implement one new mission as a vertical slice

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

### Step 7 — Add locked doors / visual progression

After the mission locking and first new mission work, implement simple locked doors or blocked areas.

Initial version:

- Door blocks access to advanced area.
- Door opens only after required missions are completed.
- If locked, display explanatory message.

Animated mentor movement can be considered after this.

---

### Step 8 — Add advanced metabolic engineering mission

After the player has environmental and genetic knowledge, implement a Dr. Carter mission about objective functions and growth vs production.

Recommended concept:

- Compare a biomass objective with a production objective.
- Ask the player to interpret how the result changes.
- Introduce the idea that maximizing growth is not always the same as maximizing production.

---

### Step 9 — Web/deployment refinement

Once gameplay content is stable:

- Confirm all missions work in web mode.
- Confirm simulation requests work through the backend.
- Update web deployment documentation.
- Prepare a final demonstration workflow.

---

## 12. Suggested Short-Term Task List

Immediate next tasks:

1. Validate the updated narrative/mentor handoff idea.
2. Finish the Simulation Summary feature.
3. Implement simple sequential mission locking.
4. Ask for the scientifically correct target metabolite and candidate genes for the new production missions.
5. Start implementing one new mission as a vertical slice.

---

## 13. Scientific Validation Checklist

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

## 14. Technical Notes

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
- Implement dialogue-based handoffs before attempting animated NPC movement.
- Treat scripted cutscenes as a future enhancement unless there is enough time.
