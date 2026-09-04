# LabHero — Cheat Sheet das Missões 01–40

> **Uso interno do professor — contém todas as soluções.**
>
> Para evitar penalizações, usa de preferência **a resposta exatamente como está indicada** e não acrescentes texto extra.

## Notas rápidas

- **M01–M35:** modelo `E. coli core`.
- **M36–M40:** modelo `Yeast iMM904`.
- **Default** = não alterar quaisquer bounds que não sejam explicitamente referidos.
- **LB closed** = fechar o *lower bound* da exchange indicada.
- **UB closed** = fechar o *upper bound* da exchange indicada.
- **Easy Mode:** `01 → 03 → 06 → 07 → 13 → 18 → 21 → 23 → 25 → 27 → 36`.
- No Teacher Mode, os números das missões são os mesmos do Normal/Easy.
- M01, M06, M07 e M08 **não têm resposta escrita**: basta completar a evidência e carregar em *Deliver*.

---

## M01 — Into the Microbial World

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Fazer 2 runs:
  1. WT, ambiente completamente default.
  2. Igual ao anterior, mas fechar apenas o LB de `EX_o2_e`.
- **Resposta:** nenhuma. Carregar em **Deliver Results** quando os dois runs estiverem registados.

## M02 — Sweet as Glucose

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Fechar uptake de glucose: `EX_glc__D_e` LB closed.
- Testar **um de cada vez**, com uptake `-10`:
  - `EX_mal__L_e`
  - `EX_lac__D_e`
  - `EX_glu__L_e`
  - `EX_gln__L_e`
  - `EX_fum_e`
  - `EX_fru_e`
  - `EX_etoh_e`
  - `EX_akg_e`
  - `EX_acald_e`
  - `EX_ac_e`
- **Resposta:** `fructose`

## M03 — The Conditional Essentiality Screen

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Ambiente default.
- Fazer WT + 6 single knockouts:
  - `b1241`
  - `b0728`
  - `b3919`
  - `b3736`
  - `b2278`
  - `b2926`
- **Resposta:** `b2926`

## M04 — Growth-Coupled Ethanol Production

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Ambiente default aeróbio.
- **Production Flux:** `EX_etoh_e`
- Fazer WT + single knockouts:
  - `b1241`
  - `b0728`
  - `b3736`
  - `b2278`
- **Resposta:** `b2278`

## M05 — Context-Dependent Anaerobic Ethanol Design

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Fechar apenas LB de `EX_o2_e`.
- **Production Flux:** `EX_etoh_e`
- Fazer WT + single knockouts:
  - `b2278`
  - `b0728`
  - `b1602`
  - `b3736`
- **Resposta:** `b3736`

## M06 — Controlled Multi-Knockout Challenge

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Ambiente completamente default.
- **Production Flux:** `EX_etoh_e`
- Primeiro fazer WT.
- Depois fazer o design vencedor: `b2278 + b3736`.
- **Resposta:** nenhuma. Carregar em **Deliver Best Valid Design**.

## M07 — Objective Matters

- **Método:** FBA
- WT, ambiente completamente default.
- **Production Flux:** `EX_etoh_e`
- Fazer 2 runs:
  1. Objective `BIOMASS_Ecoli_core_w_GAM`.
  2. Objective `EX_etoh_e`.
- **Resposta:** nenhuma. Carregar em **Deliver Objective Comparison**.

## M08 — Constraint Impact on the Optimal Solution

- **Método:** FBA
- **Objective:** `EX_lac__D_e`
- WT.
- **Production Flux:** `EX_lac__D_e`
- Fazer 2 runs:
  1. Ambiente default.
  2. Igual, mas fechar apenas LB de `EX_o2_e`.
- **Resposta:** nenhuma. Carregar em **Deliver Constraint Comparison**.

## M09 — Integrated Environment-and-Gene Design

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Fechar `EX_glc__D_e` LB.
- Abrir `EX_mal__L_e` como fonte de carbono.
- **Production Flux:** `EX_for_e`
- Fazer referência WT + single knockouts:
  - `b1479`
  - `b0721`
  - `b0116`
  - `b0115`
- **Resposta:** `b0115`

## M10 — Two-Gene Redundancy and Flux Redirection

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Fechar apenas LB de `EX_o2_e`.
- **Production Flux:** `EX_etoh_e`, `EX_ac_e`
- Fazer WT + os 6 pares:
  - `b2297 + b2458`
  - `b2297 + b1241`
  - `b2297 + b0351`
  - `b2458 + b1241`
  - `b2458 + b0351`
  - `b1241 + b0351`
- **Resposta:** `b2297 + b2458`

## M11 — Anaerobic Secretion Fingerprint

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- WT.
- Fechar apenas LB de `EX_o2_e`.
- **Production Flux:** `EX_for_e`, `EX_ac_e`, `EX_etoh_e`, `EX_lac__D_e`, `EX_succ_e`
- Fazer 1 run.
- **Resposta:** `formate`

## M12 — Constraint-Driven Succinate Byproducts

- **Método:** FBA
- **Objective:** `EX_succ_e`
- WT.
- **Production Flux:** `EX_succ_e`, `EX_ac_e`, `EX_for_e`, `EX_etoh_e`, `EX_lac__D_e`
- Fazer 2 runs:
  1. Ambiente default.
  2. Igual, mas LB de `EX_o2_e` fechado.
- **Resposta:** `acetate`

## M13 — Primary Objective and Flux Parsimony

- **Objective:** `EX_succ_e`
- WT.
- Fechar apenas LB de `EX_o2_e`.
- **Production Flux:** `EX_succ_e`, `EX_ac_e`, `EX_for_e`, `EX_etoh_e`, `EX_lac__D_e`
- Fazer 2 runs com tudo igual excepto o método:
  1. FBA
  2. pFBA
- **Resposta:** `total absolute flux`

## M14 — Byproduct Trade-off Screening

- **Método:** pFBA
- **Objective:** `EX_succ_e`
- Fechar apenas LB de `EX_o2_e`.
- **Production Flux:** `EX_succ_e`, `EX_ac_e`, `EX_for_e`, `EX_etoh_e`, `EX_lac__D_e`
- Usar a referência sem knockout da M13 se já estiver disponível; caso contrário, correr WT.
- Testar os 4 single knockouts:
  - `b1241`
  - `b0115`
  - `b0474`
  - `b4151`
- **Resposta:** `none`

## M15 — Product–Growth Viability Audit

- **Método:** pFBA
- WT.
- Fechar apenas LB de `EX_o2_e`.
- **Production Flux:** `EX_succ_e`, `EX_ac_e`, `EX_for_e`, `EX_etoh_e`, `EX_lac__D_e`
- Fazer/completar 2 optima:
  1. Objective `EX_succ_e`.
  2. Objective `BIOMASS_Ecoli_core_w_GAM`.
- **Resposta:** `objective conflict`

## M16 — Context-Dependent Carbon Rescue

### Phase A
- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Fechar LB de `EX_glc__D_e`.
- Oxigénio default.
- Abrir um candidato de cada vez com capacidade `-10`:
  - `EX_ac_e`
  - `EX_pyr_e`
  - `EX_mal__L_e`
  - `EX_fum_e`
  - `EX_akg_e`

### Phase B
- Repetir o vencedor `EX_akg_e`, mas fechar também LB de `EX_o2_e`.
- **Resposta:** `oxygen`

## M17 — Essential Uptake Routes

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- WT.
- Fazer baseline completamente default.
- Depois repetir fechando **apenas um LB de cada vez**:
  - `EX_nh4_e`
  - `EX_pi_e`
  - `EX_h2o_e`
  - `EX_h_e`
  - `EX_co2_e`
- **Resposta:** `ammonium and phosphate`

## M18 — Binding Export Constraints

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- WT.
- Fechar LB de `EX_o2_e`.
- **Production Flux:** `EX_ac_e`, `EX_etoh_e`, `EX_for_e`, `EX_succ_e`, `EX_lac__D_e`
- Fazer:
  1. baseline anaeróbia;
  2. mesmo setup + UB de `EX_ac_e` fechado;
  3. mesmo setup + UB de `EX_succ_e` fechado.
- **Resposta:** `acetate`

## M19 — Re-optimisation vs Minimal Adjustment

- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Ambiente default.
- **Production Flux:** `EX_ac_e`, `EX_etoh_e`, `EX_for_e`, `EX_lac__D_e`, `EX_succ_e`
- Fazer:
  1. WT com FBA;
  2. `b0728` com FBA;
  3. `b0728` com lMOMA.
- **Resposta:** `lMOMA`

## M20 — Context-Specific Export Robustness

- **Método:** pFBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- WT.
- **Production Flux:** `EX_ac_e`, `EX_etoh_e`, `EX_for_e`, `EX_succ_e`, `EX_lac__D_e`
- Fazer as 4 combinações:
  1. O2 aberto + acetate UB aberto.
  2. O2 aberto + acetate UB fechado.
  3. O2 LB fechado + acetate UB aberto.
  4. O2 LB fechado + acetate UB fechado.
- **Resposta:** `anaerobic`

## M21 — Compensatory Flux Comparison

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- WT.
- Fechar LB de `EX_o2_e`.
- **Production Flux:** `EX_ac_e`, `EX_etoh_e`, `EX_for_e`, `EX_succ_e`, `EX_lac__D_e`
- Fazer 2 runs:
  1. ethanol UB aberto;
  2. fechar apenas UB de `EX_etoh_e`.
- **Resposta:** `D-lactate`

## M22 — Phenotype Equivalence Audit

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Fechar LB de `EX_o2_e`.
- **Production Flux:** `EX_ac_e`, `EX_etoh_e`, `EX_for_e`, `EX_succ_e`, `EX_lac__D_e`
- Run A: WT + fechar UB de `EX_ac_e`.
- Run B: restaurar acetate UB ao default + knockout `b2297 + b2458`.
- **Resposta:** `0`

## M23 — Nutrient Sensitivity Curve

- **Método:** pFBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- WT, ambiente base default.
- **Bound Sweep:** `EX_nh4_e`, **lower bound**, valores `-5, -4, -2, -1`.
- **Production Flux:** `EX_ac_e`, `EX_co2_e`
- **Resposta:** `acetate`

## M24 — Export Capacity Thresholds

- **Método:** pFBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- WT, ambiente base default.
- **Bound Sweep:** `EX_co2_e`, **upper bound**, valores `25, 20, 10, 0`.
- **Production Flux:** `EX_co2_e`, `EX_for_e`, `EX_ac_e`
- **Resposta:** `formate`

## M25 — Context-Dependent Gene Essentiality

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Fazer matriz 2×2:
  1. WT, O2 default.
  2. `b3956`, O2 default.
  3. WT, LB de `EX_o2_e` fechado.
  4. `b3956`, LB de `EX_o2_e` fechado.
- **Resposta:** `anaerobic`

## M26 — Genotype–Environment Interaction Curve

- **Método:** FBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Ambiente base completamente default.
- Fazer 2 Bound Sweeps de `EX_o2_e` **lower bound** com valores `-25, -10, -1, 0`:
  1. WT.
  2. `b3956` knockout.
- **Resposta:** `0`

## M27 — Metabolic Bypass Rescue

- **Método:** pFBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Fazer 2 referências default:
  1. WT.
  2. `b0720 / gltA` knockout.
- Depois manter `b0720` e abrir **um suplemento de cada vez**:
  - `EX_akg_e`
  - `EX_pyr_e`
  - `EX_succ_e`
  - `EX_fum_e`
  - `EX_mal__L_e`
- **Resposta:** `EX_akg_e`

## M28 — Bypass Dependency Mapping

- **Método:** pFBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Manter sempre:
  - `b0720 / gltA` knockout;
  - `EX_akg_e` LB aberto;
  - restantes condições default.
- Referência: apenas `b0720`.
- Depois acrescentar um secondary KO de cada vez:
  - `b2587`
  - `b1761`
  - `b0728`
  - `b3236`
  - `b3403`
- **Resposta:** `b2587`

## M29 — Isoenzyme Redundancy Screen

- **Método:** pFBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Ambiente completamente default.
- Fazer WT.
- Fazer os 6 singles:
  - `b0118`
  - `b1276`
  - `b1723`
  - `b3916`
  - `b1676`
  - `b1854`
- Fazer os 3 doubles:
  - `b0118 + b1276`
  - `b1723 + b3916`
  - `b1676 + b1854`
- **Resposta:** `b0118 + b1276`

## M30 — Redundancy Breakdown Threshold

- **Método:** pFBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Ambiente base completamente default.
- **Bound Sweep:** `EX_o2_e`, lower bound, preset/valores `-30, -10, -5, -2`.
- Fazer 4 curvas:
  1. WT.
  2. `b1723`.
  3. `b3916`.
  4. `b1723 + b3916`.
- **Resposta:** `-2`

## M31 — Environmental Suppression Matrix

- **Método:** pFBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Fechar LB de `EX_glc__D_e`.
- Oxigénio default.
- Testar cada fonte a `-10`:
  - `EX_fru_e`
  - `EX_pyr_e`
  - `EX_succ_e`
  - `EX_glu__L_e`
- Para cada fonte fazer:
  1. WT;
  2. `b0118 + b1276`.
- Total: 8 runs.
- **Resposta:** `EX_glu__L_e`

## M32 — Respiratory Complex Cut-Set

- **Método:** pFBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Ambiente default aeróbio.
- Fazer 6 genótipos:
  1. WT
  2. `b0978`
  3. `b0733`
  4. `b0978 + b0979`
  5. `b0733 + b0734`
  6. `b0978 + b0733`
- **Resposta:** `b0978 + b0733`

## M33 — Reference-State Adjustment Footprint

Fazer 4 condições:

1. **Aeróbio reference:** pFBA, biomass objective, WT, ambiente default.
2. **Aeróbio mutant:** ROOM, biomass objective, `b0978 + b0733`, ambiente default.
3. **O2-closed reference:** pFBA, biomass objective, WT, apenas LB `EX_o2_e` fechado.
4. **O2-closed mutant:** ROOM, biomass objective, `b0978 + b0733`, mesmo ambiente O2-closed.

- **Resposta:** `unused`
- **Nota:** não usar `inactive`; o validator distingue “reaction unused” de “gene/reaction unavailable”.

## M34 — Shared-Subunit Equivalence Audit

- **Método:** pFBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Ambiente completamente default.
- Fazer 6 genótipos:
  1. WT
  2. `b0114`
  3. `b0726`
  4. `b0726 + b0727`
  5. `b0116`
  6. `b0114 + b0726`
- **Resposta:** `equivalent`
- **Nota:** usar `equivalent`, não `equal`.

## M35 — E. coli Final Systems Certification

### A — Design Approval
- **Método:** pFBA
- **Objective:** `BIOMASS_Ecoli_core_w_GAM`
- Ambiente default.
- **Production Flux:** `EX_for_e`, `EX_ac_e`, `EX_etoh_e`
- Fazer:
  - WT
  - `b0114`
  - `b0726`
  - `b0116`

### B — Oxygen Robustness
- **Bound Sweep:** `EX_o2_e` lower bound, valores `-30, -10, -5, -2`.
- Fazer uma curva para `b0114` e outra para `b0116`.

### C — Objective Viability
- pFBA, ambiente default, genotype `b0114`.
- Objective `EX_for_e`.

### Respostas finais
1. **Reaction target:** `PDH`
2. **First convergence O2 LB:** `-5`
3. **Growth-compatible?:** `no`

---

# Golden Lab — Yeast iMM904

## M36 — Oxygen-Capped Fermentation Onset

- **Modelo:** Yeast iMM904
- **Método:** pFBA
- **Objective:** `BIOMASS_SC5_notrace`
- WT, ambiente default.
- **Production Flux:** `EX_etoh_e`, `EX_co2_e`
- Fazer referência default.
- Depois **Bound Sweep** de `EX_glc__D_e` lower bound com `-0.5, -1, -2, -10`.
- **Resposta:** `-1`

## M37 — Fermentation Redundancy Cut Set

- **Método:** pFBA
- **Objective:** `BIOMASS_SC5_notrace`
- Ambiente completamente default.
- **Production Flux:** `EX_etoh_e`, `EX_succ_e`
- Bound Sweep OFF.
- Fazer:
  1. WT
  2. `PDC1`
  3. `PDC1 + PDC5`
  4. `PDC1 + PDC6`
  5. `PDC5 + PDC6`
  6. `PDC1 + PDC5 + PDC6`
- **Resposta:** `PDC1 + PDC5 + PDC6`

## M38 — Background-Dependent Compensation Audit

- **Método:** pFBA
- **Objective:** `BIOMASS_SC5_notrace`
- Ambiente default.
- **Production Flux:** `EX_etoh_e`, `EX_succ_e`, `EX_pyr_e`
- Bound Sweep OFF.
- Fazer:
  1. WT
  2. `FRD1`
  3. `MAE1`
  4. `PDC1 + PDC5 + PDC6`
  5. `PDC1 + PDC5 + PDC6 + FRD1`
  6. `PDC1 + PDC5 + PDC6 + MAE1`
- **Resposta:** `FRD1`

## M39 — Pathway Bypass Rescue

- **Método:** pFBA
- **Objective:** `BIOMASS_SC5_notrace`
- Genotype fixo: `PDC1 + PDC5 + PDC6 + FRD1`.
- **Production Flux:** `EX_etoh_e`, `EX_succ_e`, `EX_pyr_e`
- Bound Sweep OFF.
- Fazer 4 ambientes:
  1. completamente default;
  2. abrir apenas LB de `EX_pyr_e`;
  3. abrir apenas LB de `EX_etoh_e`;
  4. abrir apenas LB de `EX_acald_e`.
- **Resposta:** `acetaldehyde`

## M40 — Final Rescue Robustness Certification

- **Método:** pFBA
- **Objective:** `BIOMASS_SC5_notrace`
- Genotype fixo: `PDC1 + PDC5 + PDC6 + FRD1`.
- **Production Flux:** `EX_etoh_e`, `EX_succ_e`, `EX_pyr_e`
- **Bound Sweep ON:** `EX_glc__D_e` lower bound, valores `-0.5, -1, -2, -10`.
- Fazer 2 curvas:
  1. ambiente base completamente default;
  2. mesmo setup, mas abrir apenas LB de `EX_acald_e`.
- **Resposta:** `-2 and -10`

---

## Respostas rápidas — só para consulta

| Missão | Resposta |
|---|---|
| 01 | sem resposta escrita |
| 02 | `fructose` |
| 03 | `b2926` |
| 04 | `b2278` |
| 05 | `b3736` |
| 06 | sem resposta escrita; design `b2278+b3736` |
| 07 | sem resposta escrita |
| 08 | sem resposta escrita |
| 09 | `b0115` |
| 10 | `b2297 + b2458` |
| 11 | `formate` |
| 12 | `acetate` |
| 13 | `total absolute flux` |
| 14 | `none` |
| 15 | `objective conflict` |
| 16 | `oxygen` |
| 17 | `ammonium and phosphate` |
| 18 | `acetate` |
| 19 | `lMOMA` |
| 20 | `anaerobic` |
| 21 | `D-lactate` |
| 22 | `0` |
| 23 | `acetate` |
| 24 | `formate` |
| 25 | `anaerobic` |
| 26 | `0` |
| 27 | `EX_akg_e` |
| 28 | `b2587` |
| 29 | `b0118 + b1276` |
| 30 | `-2` |
| 31 | `EX_glu__L_e` |
| 32 | `b0978 + b0733` |
| 33 | `unused` |
| 34 | `equivalent` |
| 35 | `PDH` / `-5` / `no` |
| 36 | `-1` |
| 37 | `PDC1 + PDC5 + PDC6` |
| 38 | `FRD1` |
| 39 | `acetaldehyde` |
| 40 | `-2 and -10` |

