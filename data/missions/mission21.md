# Mission 21 — Compensatory Flux Comparison

## Scientist
Dr. Vega — Controlled Comparison Lab

## Theme
Before-and-after comparison of a binding export constraint and the compensatory secretion profile.

## Concept
A final flux value does not show how much a route changed. Mission 21 uses two controlled anaerobic FBA runs and asks the player to compare `modified - reference` for every tracked secretion.

The reference actively exports ethanol. Closing only the ethanol exchange upper bound keeps the model viable but redirects the predicted flux distribution. The player must identify the tracked secretion with the largest positive change without the report stating the answer directly.

## Controlled protocol
Both runs use:

- Method: `FBA`
- Objective: `BIOMASS_Ecoli_core_w_GAM`
- Genes: all active
- Glucose: model default
- Oxygen: lower bound of `EX_o2_e` closed
- Every unrelated environmental bound: model default
- Production Flux panel:
  - `EX_ac_e`
  - `EX_etoh_e`
  - `EX_for_e`
  - `EX_succ_e`
  - `EX_lac__D_e`

## Run A — anaerobic reference
Keep the upper bound of `EX_etoh_e` open.

Expected visible values:

- Growth: approximately `0.211663`
- Acetate: approximately `8.503585`
- Ethanol: approximately `8.279455`
- Formate: approximately `17.804674`
- Succinate: approximately `0`
- D-lactate: approximately `0`
- Glucose uptake: approximately `10`
- Oxygen uptake: approximately `0`

## Run B — ethanol export closed
Keep the same setup and close only the upper bound of `EX_etoh_e`.

Expected visible values:

- Growth: approximately `0.137905`
- Acetate: approximately `0.146027`
- Ethanol: approximately `0`
- Formate: approximately `0.811652`
- Succinate: approximately `0`
- D-lactate: approximately `17.758027`

## Comparison
Expected `Run B - Run A` differences:

- Acetate: approximately `-8.357558`
- Ethanol: approximately `-8.279455`
- Formate: approximately `-16.993022`
- Succinate: approximately `0`
- D-lactate: approximately `+17.758027`

The modified run retains approximately `65.15%` of reference growth.

## Final question
**Which tracked secretion showed the largest increase after ethanol export was closed?**

Accepted concise answers include:

- `D-lactate`
- `lactate`
- `EX_lac__D_e`

The report shows the complete numeric differences but does not write the final route as the answer.

## State and web contract
Mission 21 stores the two valid runs independently of the generic two-slot Compare Runs view. Repeated valid runs update their corresponding slot; invalid later attempts do not erase valid evidence. The state is JSON-serialisable, the validator reads the already visible solver result, and the browser wrapper does not launch a hidden simulation or require a new endpoint.
