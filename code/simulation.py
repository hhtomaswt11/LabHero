import copy
import json
import sys
import re
import unicodedata

from save_load import *
from options_values import *
from gpr import disabled_reaction_ids


# Mission 06 is a controlled multi-knockout strain-design challenge.  The
# player keeps the default aerobic medium fixed, uses biomass-optimal FBA,
# tracks ethanol and may disable at most two highlighted candidate genes.
# The score is a game balance index, not a universal biological quantity.
MISSION06_METHOD = 'FBA'
MISSION06_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION06_PRODUCT_NAME = 'ethanol'
MISSION06_TARGET_FLUX = 'EX_etoh_e'
MISSION06_CANDIDATE_GENES = ['b2278', 'b3736', 'b1602', 'b0728']
MISSION06_GENE_NAMES = {
    'b2278': 'nuoL',
    'b3736': 'atpF',
    'b1602': 'pntB',
    'b0728': 'sucC',
}
MISSION06_MAX_KNOCKOUTS = 2
MISSION06_MIN_BASELINE_GROWTH = 0.05
MISSION06_MAX_BASELINE_PRODUCTION = 0.001
MISSION06_MIN_GROWTH_RATIO = 0.20
MISSION06_FLUX_TOLERANCE = 0.001
MISSION06_VILLAIN_SCORE = 2.80
MISSION06_EXPECTED_WINNING_DESIGN = ('b2278', 'b3736')
MISSION06_HISTORY_LIMIT = 10

# Backwards-compatible names used by the existing UI and older modules.
CHALLENGE_GROWTH_OBJECTIVE = MISSION06_GROWTH_OBJECTIVE
CHALLENGE_PRODUCTION_OBJECTIVE = MISSION06_TARGET_FLUX
VILLAIN_SCORE = MISSION06_VILLAIN_SCORE

# Mission 01 is a controlled aerobic-versus-anaerobic comparison.  The
# thresholds are deliberately relational/tolerant instead of expecting one
# solver-specific rounded value.
MISSION01_METHOD = 'FBA'
MISSION01_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION01_OXYGEN_REACTION = 'EX_o2_e'
MISSION01_MIN_VIABLE_GROWTH = 0.05
MISSION01_MIN_GROWTH_DROP = 0.05
MISSION01_FLUX_TOLERANCE = 0.001

# Mission 02 is a controlled comparison of alternative carbon sources. Each
# candidate is tested as the sole replacement for glucose, with the same molar
# uptake capacity and every other simulation setting kept unchanged.
MISSION02_METHOD = 'FBA'
MISSION02_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION02_BLOCKED_CARBON_SOURCE = 'EX_glc__D_e'
MISSION02_COMMON_UPTAKE_BOUND = -10.0
MISSION02_MIN_GROWTH = 0.001
MISSION02_FLUX_TOLERANCE = 0.001
MISSION02_RANK_TOLERANCE = 0.001
MISSION02_EXPECTED_WINNER = 'EX_fru_e'
MISSION02_CANDIDATE_CARBON_SOURCES = [
    'EX_mal__L_e',
    'EX_lac__D_e',
    'EX_glu__L_e',
    'EX_gln__L_e',
    'EX_fum_e',
    'EX_fru_e',
    'EX_etoh_e',
    'EX_akg_e',
    'EX_acald_e',
    'EX_ac_e',
]
MISSION02_SOURCE_NAMES = {
    'EX_mal__L_e': 'L-Malate',
    'EX_lac__D_e': 'D-Lactate',
    'EX_glu__L_e': 'L-Glutamate',
    'EX_gln__L_e': 'L-Glutamine',
    'EX_fum_e': 'Fumarate',
    'EX_fru_e': 'D-Fructose',
    'EX_etoh_e': 'Ethanol',
    'EX_akg_e': '2-Oxoglutarate',
    'EX_acald_e': 'Acetaldehyde',
    'EX_ac_e': 'Acetate',
}


# Mission 03 introduces conditional gene essentiality through a controlled
# baseline and a compact six-gene knockout screen.  The candidates deliberately
# represent no apparent effect, small/moderate/strong reductions and complete
# loss of predicted biomass formation.
MISSION03_METHOD = 'FBA'
MISSION03_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION03_MIN_BASELINE_GROWTH = 0.05
MISSION03_ESSENTIAL_GROWTH_RATIO = 0.01
MISSION03_EXPECTED_ESSENTIAL_GENE = 'b2926'
MISSION03_CANDIDATE_GENES = [
    'b1241',  # adhE: no apparent effect in this aerobic default medium
    'b0728',  # sucC: small reduction
    'b3919',  # tpiA: moderate reduction
    'b3736',  # atpF: strong reduction
    'b2278',  # nuoL: very strong reduction
    'b2926',  # pgk: no predicted biomass growth
]
MISSION03_GENE_NAMES = {
    'b1241': 'adhE',
    'b0728': 'sucC',
    'b3919': 'tpiA',
    'b3736': 'atpF',
    'b2278': 'nuoL',
    'b2926': 'pgk',
}

DISPLAY_ZERO_TOLERANCE = 0.0005

# The environmental menu currently exposes open/closed toggles rather than
# numeric inputs.  When a bound already exists in the SBML model, opening it
# must restore that original quantitative value (for example glucose -10), not
# replace it with an arbitrary +/-1000.  For a bound that is originally zero,
# opening uptake uses a conservative pedagogical default of -10 and opening
# secretion uses 1000.
DEFAULT_OPEN_UPTAKE_BOUND = -10.0
DEFAULT_OPEN_SECRETION_BOUND = 1000.0

# Mission 04 introduces growth-coupled production.  The player keeps the
# default aerobic medium and biomass objective, then asks whether one genetic
# perturbation forces ethanol secretion while preserving viable predicted
# growth.  The candidate set deliberately includes redundant/no-effect,
# growth-reducing-only and genuine production-redirection outcomes.
MISSION04_METHOD = 'FBA'
MISSION04_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION04_PRODUCT_NAME = 'ethanol'
MISSION04_PRODUCTION_OBJECTIVE = 'EX_etoh_e'
MISSION04_OXYGEN_REACTION = 'EX_o2_e'
MISSION04_TARGET_GENE = 'b2278'
MISSION04_TARGET_GENE_NAME = 'nuoL'
MISSION04_EXPECTED_WINNER = MISSION04_TARGET_GENE
MISSION04_CANDIDATE_GENES = ['b1241', 'b0728', 'b3736', 'b2278']
MISSION04_GENE_NAMES = {
    'b1241': 'adhE',
    'b0728': 'sucC',
    'b3736': 'atpF',
    'b2278': 'nuoL',
}
MISSION04_MIN_BASELINE_GROWTH = 0.05
MISSION04_MAX_BASELINE_PRODUCTION = 0.001
MISSION04_MIN_VIABLE_GROWTH_RATIO = 0.10
MISSION04_MIN_PRODUCTION_INCREASE = 1.0
MISSION04_RANK_TOLERANCE = 0.01
MISSION04_FLUX_TOLERANCE = 0.001

# Mission 05 demonstrates that a useful genetic strategy is context-dependent.
# The player repeats a compact production screen in an anaerobic environment:
# ethanol is already secreted by the no-knockout reference, the Mission 04
# winner becomes neutral, and another viable knockout gives the strongest
# additional growth-coupled secretion.
MISSION05_METHOD = 'FBA'
MISSION05_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION05_PRODUCT_NAME = 'ethanol'
MISSION05_PRODUCTION_OBJECTIVE = 'EX_etoh_e'
MISSION05_TARGET_FLUX = MISSION05_PRODUCTION_OBJECTIVE
MISSION05_OXYGEN_REACTION = 'EX_o2_e'
MISSION05_TARGET_GENE = 'b3736'
MISSION05_TARGET_GENE_NAME = 'atpF'
MISSION05_EXPECTED_WINNER = MISSION05_TARGET_GENE
MISSION05_CANDIDATE_GENES = ['b2278', 'b0728', 'b1602', 'b3736']
MISSION05_GENE_NAMES = {
    'b2278': 'nuoL',
    'b0728': 'sucC',
    'b1602': 'pntB',
    'b3736': 'atpF',
}
MISSION05_MIN_BASELINE_GROWTH = 0.05
MISSION05_MIN_BASELINE_PRODUCTION = 1.0
MISSION05_MIN_VIABLE_GROWTH_RATIO = 0.90
MISSION05_MIN_PRODUCTION_INCREASE = 1.0
MISSION05_RANK_TOLERANCE = 0.01
MISSION05_FLUX_TOLERANCE = 0.001

# Mission 07 compares two FBA questions while keeping genes and medium fixed.
# The visible solution is reused directly: one run maximises biomass and one
# maximises ethanol.  Both runs track ethanol, and biomass is read from the same
# solution so product maximisation is never mistaken for viable growth.
MISSION07_METHOD = 'FBA'
MISSION07_BIOMASS_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION07_DEFAULT_OBJECTIVE = MISSION07_BIOMASS_OBJECTIVE
MISSION07_TARGET_PRODUCT = 'ethanol'
MISSION07_TARGET_OBJECTIVE = 'EX_etoh_e'
MISSION07_TARGET_FLUX = MISSION07_TARGET_OBJECTIVE
MISSION07_OXYGEN_REACTION = 'EX_o2_e'
MISSION07_MIN_REFERENCE_GROWTH = 0.05
MISSION07_MAX_REFERENCE_ETHANOL = 0.001
MISSION07_MIN_TARGET_ETHANOL = 1.0
MISSION07_MAX_TARGET_GROWTH = 0.001
MISSION07_FLUX_TOLERANCE = 0.001

# Mission 08 compares the same direct D-lactate objective before and after
# oxygen uptake is disabled.  The visible solution is reused in both runs.
# Because the unconstrained optimum already uses zero oxygen, the additional
# oxygen restriction does not change this objective optimum because the default optimum already uses zero oxygen.
MISSION08_METHOD = 'FBA'
MISSION08_BIOMASS_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION08_TARGET_PRODUCT = 'D-lactate'
MISSION08_TARGET_OBJECTIVE = 'EX_lac__D_e'
MISSION08_TARGET_FLUX = MISSION08_TARGET_OBJECTIVE
MISSION08_OXYGEN_REACTION = 'EX_o2_e'
MISSION08_MIN_TARGET_FLUX = 1.0
MISSION08_MAX_GROWTH = 0.001
MISSION08_MAX_OXYGEN_UPTAKE = 0.001
MISSION08_OBJECTIVE_MATCH_TOLERANCE = 0.01
MISSION08_EQUIVALENCE_TOLERANCE = 0.001

# Mission 09 integrates environment engineering and a single genetic
# perturbation. The player replaces glucose with L-malate, keeps an aerobic
# biomass-optimal FBA reference, tracks formate, and compares four candidate
# knockouts. The winning design is derived from visible evidence: it must
# retain at least 80% of reference growth and increase formate by at least 1.0.
MISSION09_CHECK_VERSION = 4
MISSION09_METHOD = 'FBA'
MISSION09_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION09_TARGET_PRODUCT = 'formate'
MISSION09_TARGET_FLUX = 'EX_for_e'
MISSION09_BLOCKED_CARBON_SOURCE = 'EX_glc__D_e'
MISSION09_REPLACEMENT_CARBON_SOURCE = 'EX_mal__L_e'
MISSION09_REPLACEMENT_SOURCE_NAME = 'L-malate'
MISSION09_OXYGEN_REACTION = 'EX_o2_e'
MISSION09_CANDIDATE_GENES = ['b1479', 'b0721', 'b0116', 'b0115']
MISSION09_GENE_NAMES = {
    'b1479': 'maeA',
    'b0721': 'sdhC',
    'b0116': 'lpd',
    'b0115': 'aceF',
}
MISSION09_EXPECTED_WINNER = 'b0115'
MISSION09_MIN_BASELINE_GROWTH = 0.05
MISSION09_MAX_BASELINE_PRODUCTION = 0.001
MISSION09_MIN_VIABLE_GROWTH_RATIO = 0.80
MISSION09_MIN_PRODUCTION_INCREASE = 1.0
MISSION09_RANK_TOLERANCE = 0.01
MISSION09_FLUX_TOLERANCE = 0.001

# Mission 10 is Dr. Nova's final controlled design challenge.  The player
# keeps the default glucose supply, closes oxygen uptake, uses biomass-optimal
# FBA, tracks ethanol and acetate, records a no-knockout reference and then
# compares every two-gene pair formed by four genes involved in OR-type GPR
# redundancy.  The winner is derived from the visible evidence rather than
# accepted from the last active pair.
MISSION10_CHECK_VERSION = 3
MISSION10_METHOD = 'FBA'
MISSION10_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION10_TARGET_PRODUCT = 'ethanol'
MISSION10_TARGET_FLUX = 'EX_etoh_e'
MISSION10_COMPETING_PRODUCT = 'acetate'
MISSION10_COMPETING_FLUX = 'EX_ac_e'
MISSION10_OXYGEN_REACTION = 'EX_o2_e'
MISSION10_GLUCOSE_REACTION = 'EX_glc__D_e'
MISSION10_CANDIDATE_GENES = ['b2297', 'b2458', 'b1241', 'b0351']
MISSION10_GENE_NAMES = {
    'b2297': 'pta',
    'b2458': 'eutD',
    'b1241': 'adhE',
    'b0351': 'mhpF',
}
MISSION10_REQUIRED_PAIRS = [
    ('b2297', 'b2458'),
    ('b2297', 'b1241'),
    ('b2297', 'b0351'),
    ('b2458', 'b1241'),
    ('b2458', 'b0351'),
    ('b1241', 'b0351'),
]
MISSION10_EXPECTED_WINNING_PAIR = ('b2297', 'b2458')
MISSION10_REQUIRED_TRACKED_FLUXES = [MISSION10_TARGET_FLUX, MISSION10_COMPETING_FLUX]
MISSION10_MIN_BASELINE_GROWTH = 0.05
MISSION10_MIN_GROWTH_RATIO = 0.80
MISSION10_MIN_ETHANOL_INCREASE = 5.0
MISSION10_RANK_TOLERANCE = 0.01
MISSION10_FLUX_TOLERANCE = 0.001

# Mission 11 starts Dr. Almeida's diagnostics laboratory.  It uses one
# visible anaerobic biomass-optimal solution to build a complete secretion
# fingerprint, then asks the player to identify the dominant tracked product.
# The validation state is JSON-serialisable and independent of pygame widgets,
# which keeps the same mission contract usable by the desktop and web clients.
MISSION11_CHECK_VERSION = 2
MISSION11_METHOD = 'FBA'
MISSION11_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION11_TARGET_CONTEXT = 'anaerobic biomass-optimal growth'
MISSION11_OXYGEN_REACTION = 'EX_o2_e'
MISSION11_GLUCOSE_REACTION = 'EX_glc__D_e'
MISSION11_REQUIRED_TRACKED_FLUXES = ['EX_for_e', 'EX_ac_e', 'EX_etoh_e', 'EX_lac__D_e', 'EX_succ_e']
MISSION11_PRODUCT_NAMES = {
    'EX_for_e': 'formate',
    'EX_ac_e': 'acetate',
    'EX_etoh_e': 'ethanol',
    'EX_lac__D_e': 'D-lactate',
    'EX_succ_e': 'succinate',
}
MISSION11_EXPECTED_POSITIVE_FLUXES = ('EX_for_e', 'EX_ac_e', 'EX_etoh_e')
MISSION11_EXPECTED_ZERO_FLUXES = ('EX_lac__D_e', 'EX_succ_e')
MISSION11_EXPECTED_DOMINANT_FLUX = 'EX_for_e'
MISSION11_MIN_GROWTH = 0.05
MISSION11_FLUX_TOLERANCE = 0.001

# Mission 12 extends Mission 11 from interpreting one fingerprint to
# comparing two complete product-optimal fingerprints.  The state contains
# only JSON-serialisable values and is independent of pygame, so the same
# validation contract can be reused by the desktop and future web clients.
MISSION12_CHECK_VERSION = 2
MISSION12_METHOD = 'FBA'
MISSION12_TARGET_PRODUCT = 'succinate'
MISSION12_TARGET_OBJECTIVE = 'EX_succ_e'
MISSION12_OXYGEN_REACTION = 'EX_o2_e'
MISSION12_GLUCOSE_REACTION = 'EX_glc__D_e'
MISSION12_REQUIRED_TRACKED_FLUXES = ['EX_succ_e', 'EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e']
MISSION12_COMPETING_FLUXES = ['EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e']
MISSION12_PRODUCT_NAMES = {
    'EX_succ_e': 'succinate',
    'EX_ac_e': 'acetate',
    'EX_for_e': 'formate',
    'EX_etoh_e': 'ethanol',
    'EX_lac__D_e': 'D-lactate',
}
MISSION12_EXPECTED_NEW_BYPRODUCT = 'EX_ac_e'
MISSION12_EXPECTED_ZERO_BYPRODUCTS = ('EX_for_e', 'EX_etoh_e', 'EX_lac__D_e')
MISSION12_MIN_TARGET_FLUX = 1.0
MISSION12_MIN_DEFAULT_OXYGEN_UPTAKE = 0.1
MISSION12_MIN_TARGET_DROP = 0.1
MISSION12_MIN_ACETATE_INCREASE = 0.1
MISSION12_MAX_BIOMASS_FLUX = 0.001
MISSION12_FLUX_TOLERANCE = 0.001
MISSION12_TARGET_MATCH_TOLERANCE = 0.01
MISSION12_DEFAULT_GLUCOSE_UPTAKE = 10.0
MISSION12_GLUCOSE_TOLERANCE = 0.01

# Mission 13 compares the oxygen-constrained FBA reference from Mission 12
# with a pFBA run under the exact same biological setup.  The key distinction
# is between the primary metabolic objective and pFBA's secondary parsimony
# criterion.  The report is JSON-serialisable and shared by desktop/web code.
MISSION13_CHECK_VERSION = 2
MISSION13_BASELINE_METHOD = 'FBA'
MISSION13_TARGET_METHOD = 'pFBA'
MISSION13_TARGET_PRODUCT = 'succinate'
MISSION13_TARGET_OBJECTIVE = 'EX_succ_e'
MISSION13_OXYGEN_REACTION = 'EX_o2_e'
MISSION13_GLUCOSE_REACTION = 'EX_glc__D_e'
MISSION13_REQUIRED_TRACKED_FLUXES = ['EX_succ_e', 'EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e']
MISSION13_COMPETING_FLUXES = ['EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e']
MISSION13_PRODUCT_NAMES = dict(MISSION12_PRODUCT_NAMES)
MISSION13_MIN_COMPETING_FLUXES = len(MISSION13_COMPETING_FLUXES)
MISSION13_MIN_TARGET_FLUX = 1.0
MISSION13_MAX_BIOMASS_FLUX = 0.001
MISSION13_DEFAULT_GLUCOSE_UPTAKE = 10.0
MISSION13_FLUX_TOLERANCE = 0.01
MISSION13_PRIMARY_TOLERANCE = 0.01
MISSION13_PARSIMONY_TOLERANCE = 0.05
MISSION13_ACTIVE_FLUX_TOLERANCE = 1e-7
MISSION13_EXPECTED_SECONDARY_CRITERION = 'total_absolute_flux'

# Mission 14 advances from method interpretation to evidence-based screening
# of genetic interventions.  A candidate is not judged from one byproduct in
# isolation: the complete product-optimal fingerprint, target retention and
# newly appearing co-products must all be considered.  The accumulated state
# is JSON-serialisable and is shared by desktop and web clients.
MISSION14_CHECK_VERSION = 2
MISSION14_TARGET_METHOD = 'pFBA'
MISSION14_TARGET_PRODUCT = 'succinate'
MISSION14_TARGET_OBJECTIVE = 'EX_succ_e'
MISSION14_OXYGEN_REACTION = 'EX_o2_e'
MISSION14_GLUCOSE_REACTION = 'EX_glc__D_e'
MISSION14_COPRODUCT_PRODUCT = 'acetate'
MISSION14_COPRODUCT_FLUX = 'EX_ac_e'
# Legacy aliases retained for older modules and save-data readers. Mission 14
# now screens acetate trade-offs, not ethanol.
MISSION14_UNWANTED_PRODUCT = MISSION14_COPRODUCT_PRODUCT
MISSION14_UNWANTED_FLUX = MISSION14_COPRODUCT_FLUX
MISSION14_CANDIDATE_GENES = ['b1241', 'b0115', 'b0474', 'b4151']
MISSION14_GENE_NAMES = {
    'b1241': 'adhE',
    'b0115': 'aceF',
    'b0474': 'adk',
    'b4151': 'frdD',
}
MISSION14_EXPECTED_DISABLED_REACTIONS = {
    'b1241': [],
    'b0115': ['PDH'],
    'b0474': ['ADK1'],
    'b4151': ['FRD7'],
}
MISSION14_REQUIRED_TRACKED_FLUXES = ['EX_succ_e', 'EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e']
MISSION14_PRODUCT_NAMES = dict(MISSION13_PRODUCT_NAMES)
MISSION14_POTENTIAL_NEW_BYPRODUCTS = ('EX_for_e', 'EX_etoh_e', 'EX_lac__D_e')
MISSION14_MIN_TARGET_FLUX = 1.0
MISSION14_MIN_TARGET_RETENTION = 0.90
MISSION14_MIN_ACETATE_REDUCTION = 1.0
MISSION14_NEW_BYPRODUCT_THRESHOLD = 0.10
MISSION14_MAX_BIOMASS_FLUX = 0.001
MISSION14_DEFAULT_GLUCOSE_UPTAKE = 10.0
MISSION14_FLUX_TOLERANCE = 0.01
MISSION14_PRIMARY_TOLERANCE = 0.01
MISSION14_PARSIMONY_TOLERANCE = 0.05
MISSION14_EXPECTED_SECONDARY_CRITERION = 'total_absolute_flux'
MISSION14_EXPECTED_CONCLUSION = 'none'

# Mission 15 closes Dr. Almeida's laboratory with a controlled comparison
# between a product-optimal and a growth-optimal pFBA solution.  The purpose
# is to test whether a high theoretical product maximum is compatible with
# predicted growth under the same strain and medium.  Every value comes from
# the visible solver result, and the accumulated state is JSON-serialisable.
MISSION15_CHECK_VERSION = 2
MISSION15_TARGET_METHOD = 'pFBA'
MISSION15_TARGET_PRODUCT = 'succinate'
MISSION15_PRODUCT_OBJECTIVE = 'EX_succ_e'
MISSION15_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
# Compatibility name retained for older imports and narrative code.
MISSION15_TARGET_OBJECTIVE = MISSION15_PRODUCT_OBJECTIVE
MISSION15_OXYGEN_REACTION = 'EX_o2_e'
MISSION15_GLUCOSE_REACTION = 'EX_glc__D_e'
MISSION15_REQUIRED_TRACKED_FLUXES = ['EX_succ_e', 'EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e']
MISSION15_PRODUCT_NAMES = dict(MISSION14_PRODUCT_NAMES)
MISSION15_EXPECTED_SECONDARY_CRITERION = 'total_absolute_flux'
MISSION15_MIN_PRODUCT_FLUX = 1.0
MISSION15_MAX_PRODUCT_RUN_BIOMASS = 0.001
MISSION15_MIN_GROWTH_FLUX = 0.05
MISSION15_MAX_GROWTH_RUN_PRODUCT = 0.001
MISSION15_DEFAULT_GLUCOSE_UPTAKE = 10.0
MISSION15_FLUX_TOLERANCE = 0.01
MISSION15_PRIMARY_TOLERANCE = 0.01
MISSION15_EXPECTED_RELATIONSHIP = 'objective_conflict'

MISSION16_CHECK_VERSION = 2
MISSION16_METHOD = 'FBA'
MISSION16_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION16_BLOCKED_CARBON_SOURCE = 'EX_glc__D_e'
MISSION16_OXYGEN_REACTION = 'EX_o2_e'
MISSION16_TARGET_CONTEXT = 'context-dependent carbon rescue'
MISSION16_CANDIDATE_CARBON_SOURCES = ['EX_ac_e', 'EX_pyr_e', 'EX_mal__L_e', 'EX_fum_e', 'EX_akg_e']
MISSION16_SOURCE_NAMES = {
    'EX_ac_e': 'Acetate',
    'EX_pyr_e': 'Pyruvate',
    'EX_mal__L_e': 'L-Malate',
    'EX_fum_e': 'Fumarate',
    'EX_akg_e': '2-Oxoglutarate',
}
MISSION16_REQUIRED_MEDIUM_FLUXES = [
    MISSION16_BLOCKED_CARBON_SOURCE,
    *MISSION16_CANDIDATE_CARBON_SOURCES,
    MISSION16_OXYGEN_REACTION,
]
MISSION16_EXPECTED_SOURCE_UPTAKE = 10.0
MISSION16_SOURCE_UPTAKE_TOLERANCE = 0.05
MISSION16_FLUX_TOLERANCE = 0.001
MISSION16_MIN_POSITIVE_GROWTH = 0.01
MISSION16_RANK_TOLERANCE = 0.000001
MISSION16_EXPECTED_STRONGEST_SOURCE = 'EX_akg_e'
MISSION16_EXPECTED_FACTOR = 'oxygen'

MISSION17_CHECK_VERSION = 2
MISSION17_METHOD = 'FBA'
MISSION17_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION17_TARGET_CONTEXT = 'essential uptake routes'
MISSION17_CANDIDATE_NUTRIENTS = ['EX_nh4_e', 'EX_pi_e', 'EX_h2o_e', 'EX_h_e', 'EX_co2_e']
MISSION17_NUTRIENT_NAMES = {
    'EX_nh4_e': 'Ammonium',
    'EX_pi_e': 'Phosphate',
    'EX_h2o_e': 'Water',
    'EX_h_e': 'Proton',
    'EX_co2_e': 'Carbon dioxide',
}
MISSION17_REQUIRED_MEDIUM_FLUXES = [
    'EX_glc__D_e',
    *MISSION17_CANDIDATE_NUTRIENTS,
    'EX_o2_e',
]
MISSION17_MIN_BASELINE_GROWTH = 0.05
MISSION17_COLLAPSE_RATIO = 0.01
MISSION17_PRESERVED_RATIO = 0.99
MISSION17_FLUX_TOLERANCE = 0.001

MISSION18_CHECK_VERSION = 2
MISSION18_METHOD = 'FBA'
MISSION18_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION18_TARGET_CONTEXT = 'binding export constraints'
MISSION18_OXYGEN_REACTION = 'EX_o2_e'
MISSION18_GLUCOSE_REACTION = 'EX_glc__D_e'
MISSION18_CANDIDATE_EXPORTS = ['EX_ac_e', 'EX_succ_e']
MISSION18_EXPORT_NAMES = {
    'EX_ac_e': 'Acetate',
    'EX_succ_e': 'Succinate',
}
MISSION18_FLUX_NAMES = {
    'EX_ac_e': 'Acetate',
    'EX_etoh_e': 'Ethanol',
    'EX_for_e': 'Formate',
    'EX_succ_e': 'Succinate',
    'EX_lac__D_e': 'D-Lactate',
}
MISSION18_REQUIRED_TRACKED_FLUXES = [
    'EX_ac_e',
    'EX_etoh_e',
    'EX_for_e',
    'EX_succ_e',
    'EX_lac__D_e',
]
MISSION18_REQUIRED_MEDIUM_FLUXES = [
    MISSION18_GLUCOSE_REACTION,
    MISSION18_OXYGEN_REACTION,
    *MISSION18_REQUIRED_TRACKED_FLUXES,
]
MISSION18_MIN_BASELINE_GROWTH = 0.05
MISSION18_MIN_BINDING_VIABILITY_RATIO = 0.80
MISSION18_MAX_BINDING_GROWTH_RATIO = 0.98
MISSION18_BASELINE_LIKE_RATIO = 0.99
MISSION18_MIN_ACTIVE_BASELINE_EXPORT = 0.01
MISSION18_MAX_CLOSED_EXPORT_FLUX = 0.001
MISSION18_PROFILE_CHANGE_THRESHOLD = 0.10
MISSION18_PROFILE_SIMILARITY_TOLERANCE = 0.01
MISSION18_EXPECTED_GLUCOSE_UPTAKE = 10.0
MISSION18_GLUCOSE_UPTAKE_TOLERANCE = 0.05
MISSION18_FLUX_TOLERANCE = 0.01
MISSION18_EXPECTED_BINDING_EXPORT = 'EX_ac_e'
MISSION18_EXPECTED_NONBINDING_EXPORT = 'EX_succ_e'

MISSION19_CHECK_VERSION = 3
MISSION19_BASELINE_METHOD = 'FBA'
MISSION19_TARGET_METHOD = 'lMOMA'
MISSION19_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION19_TARGET_CONTEXT = 're-optimisation versus minimal adjustment'
MISSION19_TARGET_GENE = 'b0728'
MISSION19_TARGET_GENE_NAME = 'sucC'
MISSION19_EXPECTED_DISABLED_REACTIONS = ['SUCOAS']
MISSION19_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_etoh_e', 'EX_for_e', 'EX_lac__D_e', 'EX_succ_e']
MISSION19_MIN_BASELINE_GROWTH = 0.05
MISSION19_MIN_MUTANT_VIABILITY_RATIO = 0.80
MISSION19_MIN_BIOMASS_METHOD_GAP = 0.01
MISSION19_MIN_LMOMA_ADJUSTMENT = 0.01
MISSION19_MIN_PROFILE_DIFFERENCE = 0.05
MISSION19_FLUX_TOLERANCE = 0.01
MISSION19_EXPECTED_LOWER_BIOMASS_METHOD = 'lMOMA'
MISSION19_LMOMA_SCORE_NAME = 'total_absolute_flux_adjustment'
LMOMA_DISPLAY_NAME = 'Linear MOMA (lMOMA)'

# Mission 20 closes Dr. Rio's laboratory with a controlled two-factor
# robustness matrix.  The same acetate upper-bound closure is tested with
# oxygen available and with oxygen uptake closed.  Every stored value comes
# from the visible pFBA result and the accumulated state is JSON-safe.
MISSION20_CHECK_VERSION = 2
MISSION20_TARGET_METHOD = 'pFBA'
MISSION20_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION20_TARGET_CONTEXT = 'context-specific export robustness'
MISSION20_OXYGEN_REACTION = 'EX_o2_e'
MISSION20_GLUCOSE_REACTION = 'EX_glc__D_e'
MISSION20_ACETATE_EXPORT = 'EX_ac_e'
# Compatibility aliases retained for narrative/integration code that may still
# use the former bottleneck names.  The obsolete pyruvate protocol is removed.
MISSION20_EXPORT_BOTTLENECK = MISSION20_ACETATE_EXPORT
MISSION20_EXPORT_BOTTLENECK_NAME = 'acetate'
MISSION20_REQUIRED_TRACKED_FLUXES = [
    'EX_ac_e',
    'EX_etoh_e',
    'EX_for_e',
    'EX_succ_e',
    'EX_lac__D_e',
]
MISSION20_REQUIRED_MEDIUM_FLUXES = [
    MISSION20_GLUCOSE_REACTION,
    MISSION20_OXYGEN_REACTION,
    *MISSION20_REQUIRED_TRACKED_FLUXES,
]
MISSION20_EXPECTED_SECONDARY_CRITERION = 'total_absolute_flux'
MISSION20_MIN_BASELINE_GROWTH = 0.05
MISSION20_AEROBIC_BASELINE_LIKE_RATIO = 0.99
MISSION20_ANAEROBIC_MIN_VIABILITY_RATIO = 0.80
MISSION20_ANAEROBIC_MAX_GROWTH_RATIO = 0.98
MISSION20_MIN_ACTIVE_BASELINE_EXPORT = 0.01
MISSION20_MAX_CLOSED_EXPORT_FLUX = 0.001
MISSION20_PROFILE_CHANGE_THRESHOLD = 0.10
MISSION20_PROFILE_SIMILARITY_TOLERANCE = 0.01
MISSION20_PARSIMONY_SIMILARITY_TOLERANCE = 0.05
MISSION20_EXPECTED_GLUCOSE_UPTAKE = 10.0
MISSION20_GLUCOSE_UPTAKE_TOLERANCE = 0.05
MISSION20_MIN_AEROBIC_OXYGEN_UPTAKE = 0.01
MISSION20_FLUX_TOLERANCE = 0.01
MISSION20_PRIMARY_TOLERANCE = 0.01
MISSION20_EXPECTED_RESPONSE_CONTEXT = 'oxygen_closed'

# Mission 21 starts Dr. Vega's compact comparison laboratory.  The player
# records one anaerobic reference and repeats the same visible FBA experiment
# after closing ethanol export.  The conclusion is derived from the largest
# positive change in the complete tracked secretion profile.
MISSION21_CHECK_VERSION = 2
MISSION21_METHOD = 'FBA'
MISSION21_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION21_OXYGEN_REACTION = 'EX_o2_e'
MISSION21_GLUCOSE_REACTION = 'EX_glc__D_e'
MISSION21_ETHANOL_EXPORT = 'EX_etoh_e'
MISSION21_TARGET_CONTEXT = 'compensatory flux comparison after ethanol export closure'
MISSION21_REQUIRED_TRACKED_FLUXES = [
    'EX_ac_e',
    'EX_etoh_e',
    'EX_for_e',
    'EX_succ_e',
    'EX_lac__D_e',
]
MISSION21_REQUIRED_MEDIUM_FLUXES = [
    MISSION21_GLUCOSE_REACTION,
    MISSION21_OXYGEN_REACTION,
    *MISSION21_REQUIRED_TRACKED_FLUXES,
]
MISSION21_FLUX_NAMES = {
    'EX_ac_e': 'Acetate',
    'EX_etoh_e': 'Ethanol',
    'EX_for_e': 'Formate',
    'EX_succ_e': 'Succinate',
    'EX_lac__D_e': 'D-Lactate',
}
MISSION21_EXPECTED_LARGEST_INCREASE = 'EX_lac__D_e'
MISSION21_MIN_BASELINE_GROWTH = 0.05
MISSION21_MIN_MODIFIED_VIABILITY_RATIO = 0.50
MISSION21_MIN_ACTIVE_BASELINE_ETHANOL = 0.01
MISSION21_MAX_CLOSED_ETHANOL_FLUX = 0.001
MISSION21_MIN_COMPENSATORY_INCREASE = 0.10
MISSION21_LARGEST_INCREASE_TOLERANCE = 0.01
MISSION21_EXPECTED_GLUCOSE_UPTAKE = 10.0
MISSION21_GLUCOSE_UPTAKE_TOLERANCE = 0.05
MISSION21_FLUX_TOLERANCE = 0.01
MISSION21_PRIMARY_TOLERANCE = 0.01

# Mission 22 closes Dr. Vega's comparison laboratory with an observational
# equivalence audit.  Two different interventions are compared under the same
# anaerobic FBA protocol: an acetate-export upper-bound closure and the
# b2297+b2458 knockout pair that disables PTAr through its complete OR GPR.
MISSION22_CHECK_VERSION = 2
MISSION22_METHOD = 'FBA'
MISSION22_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION22_TARGET_CONTEXT = 'phenotype equivalence across environmental and genetic interventions'
MISSION22_OXYGEN_REACTION = 'EX_o2_e'
MISSION22_GLUCOSE_REACTION = 'EX_glc__D_e'
MISSION22_ENVIRONMENTAL_EXPORT = 'EX_ac_e'
MISSION22_TARGET_GENES = ['b2297', 'b2458']
MISSION22_TARGET_GENE_NAMES = {'b2297': 'pta', 'b2458': 'eutD'}
MISSION22_EXPECTED_DISABLED_REACTIONS = ['PTAr']
MISSION22_REQUIRED_TRACKED_FLUXES = [
    'EX_ac_e',
    'EX_etoh_e',
    'EX_for_e',
    'EX_succ_e',
    'EX_lac__D_e',
]
MISSION22_REQUIRED_MEDIUM_FLUXES = [
    MISSION22_GLUCOSE_REACTION,
    MISSION22_OXYGEN_REACTION,
    *MISSION22_REQUIRED_TRACKED_FLUXES,
]
MISSION22_FLUX_NAMES = {
    'EX_ac_e': 'Acetate',
    'EX_etoh_e': 'Ethanol',
    'EX_for_e': 'Formate',
    'EX_succ_e': 'Succinate',
    'EX_lac__D_e': 'D-Lactate',
}
MISSION22_PHENOTYPE_OUTPUTS = [
    'growth',
    'glucose_uptake',
    'oxygen_uptake',
    *MISSION22_REQUIRED_TRACKED_FLUXES,
]
MISSION22_OUTPUT_NAMES = {
    'growth': 'Biomass growth',
    'glucose_uptake': 'Glucose uptake',
    'oxygen_uptake': 'Oxygen uptake',
    **MISSION22_FLUX_NAMES,
}
MISSION22_MIN_VIABLE_GROWTH = 0.05
MISSION22_EXPECTED_GLUCOSE_UPTAKE = 10.0
MISSION22_GLUCOSE_UPTAKE_TOLERANCE = 0.05
MISSION22_MAX_ACETATE_EXPORT = 0.001
MISSION22_MIN_ACTIVE_ETHANOL_EXPORT = 0.01
MISSION22_MIN_ACTIVE_FORMATE_EXPORT = 0.01
MISSION22_OUTPUT_DIFFERENCE_TOLERANCE = 0.01
MISSION22_EXPECTED_DIFFERENT_OUTPUT_COUNT = 0
MISSION22_FLUX_TOLERANCE = 0.01
MISSION22_PRIMARY_TOLERANCE = 0.01

# Compatibility aliases retained for external imports from older saves/UI.
MISSION22_TARGET_PRODUCT = 'phenotype outputs'
MISSION22_TARGET_FLUX = MISSION22_ENVIRONMENTAL_EXPORT
MISSION22_TARGET_GENE = MISSION22_TARGET_GENES[0]
MISSION22_TARGET_GENE_NAME = MISSION22_TARGET_GENE_NAMES[MISSION22_TARGET_GENE]
MISSION22_CANDIDATE_GENES = list(MISSION22_TARGET_GENES)

# Mission 23 begins Dr. Luna's sensitivity laboratory.  One structured
# pFBA bound sweep records a non-limiting ammonium point and three progressively
# tighter lower bounds.  The mission validates only the visible sweep table and
# derives the onset of a new secretion from those rows; it never launches a
# hidden validation simulation.
MISSION23_CHECK_VERSION = 2
MISSION23_METHOD = 'pFBA'
MISSION23_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION23_TARGET_CONTEXT = 'ammonium nutrient sensitivity curve and secretion onset'
MISSION23_SWEEP_REACTION = 'EX_nh4_e'
MISSION23_SWEEP_REACTION_NAME = 'Ammonium exchange'
MISSION23_SWEEP_BOUND = 'lower'
MISSION23_SWEEP_BOUND_LABEL = 'lower bound'
MISSION23_SWEEP_VALUES = [-5.0, -4.0, -2.0, -1.0]
MISSION23_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_co2_e']
MISSION23_REQUIRED_MEDIUM_FLUXES = [
    'EX_nh4_e',
    'EX_glc__D_e',
    'EX_o2_e',
    'EX_pi_e',
]
MISSION23_FLUX_NAMES = {
    'EX_ac_e': 'Acetate',
    'EX_co2_e': 'Carbon dioxide',
}
MISSION23_EXPECTED_NEW_SECRETION = 'EX_ac_e'
MISSION23_EXPECTED_SECONDARY_CRITERION = 'total_absolute_flux'
MISSION23_MIN_REFERENCE_GROWTH = 0.05
MISSION23_MAX_REFERENCE_ACETATE = 0.001
MISSION23_MIN_LIMITING_ACETATE = 0.01
MISSION23_MIN_GROWTH_CHANGE = 0.01
MISSION23_MONOTONIC_TOLERANCE = 0.01
MISSION23_FLUX_TOLERANCE = 0.01
MISSION23_PRIMARY_TOLERANCE = 0.01

# Removed Mission 23 objective-comparison aliases are intentionally not kept:
# the redesigned mission must not be confused with the earlier ethanol
# objective exercise or with the generic Compare Runs state.

# Mission 24 closes Dr. Luna's sensitivity laboratory with a graded upper-bound
# restriction.  A pFBA sweep progressively limits CO2 export and records the
# sequential appearance of compensatory secretions.  The mission validator
# consumes only the visible Bound Sweep rows and never launches a hidden solver.
MISSION24_CHECK_VERSION = 2
MISSION24_METHOD = 'pFBA'
MISSION24_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION24_TARGET_CONTEXT = 'CO2 export-capacity threshold curve and sequential compensation'
MISSION24_SWEEP_REACTION = 'EX_co2_e'
MISSION24_SWEEP_REACTION_NAME = 'Carbon dioxide exchange'
MISSION24_SWEEP_BOUND = 'upper'
MISSION24_SWEEP_BOUND_LABEL = 'upper bound'
MISSION24_SWEEP_VALUES = [25.0, 20.0, 10.0, 0.0]
MISSION24_REQUIRED_TRACKED_FLUXES = ['EX_co2_e', 'EX_for_e', 'EX_ac_e']
MISSION24_REQUIRED_MEDIUM_FLUXES = ['EX_glc__D_e', 'EX_o2_e']
MISSION24_FLUX_NAMES = {
    'EX_co2_e': 'Carbon dioxide',
    'EX_for_e': 'Formate',
    'EX_ac_e': 'Acetate',
}
MISSION24_EXPECTED_FIRST_COMPENSATORY_SECRETION = 'EX_for_e'
MISSION24_EXPECTED_SECONDARY_CRITERION = 'total_absolute_flux'
MISSION24_MIN_VIABLE_GROWTH = 0.05
MISSION24_BOUND_TOLERANCE = 0.01
MISSION24_FLUX_TOLERANCE = 0.01
MISSION24_PRIMARY_TOLERANCE = 0.01
MISSION24_MONOTONIC_TOLERANCE = 0.01
MISSION24_MAX_ABSENT_SECRETION = 0.001
MISSION24_MIN_ACTIVE_SECRETION = 0.01
MISSION24_MIN_GROWTH_CHANGE = 0.01

MISSION25_CHECK_VERSION = 2
MISSION25_METHOD = 'FBA'
MISSION25_TARGET_CONTEXT = 'oxygen-context matrix for conditional gene essentiality'
MISSION25_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION25_TARGET_GENE = 'b3956'
MISSION25_TARGET_GENE_NAME = 'ppc'
MISSION25_TARGET_REACTION = 'PPC'
MISSION25_OXYGEN_REACTION = 'EX_o2_e'
MISSION25_GLUCOSE_REACTION = 'EX_glc__D_e'
MISSION25_REQUIRED_MEDIUM_FLUXES = [MISSION25_GLUCOSE_REACTION, MISSION25_OXYGEN_REACTION]
MISSION25_MIN_REFERENCE_GROWTH = 0.05
MISSION25_MIN_AEROBIC_KO_RETENTION = 0.95
MISSION25_MAX_ANAEROBIC_KO_RETENTION = 0.05
MISSION25_MIN_CONTEXT_EFFECT_GAP = 0.80
MISSION25_FLUX_TOLERANCE = 0.001
MISSION25_PRIMARY_TOLERANCE = 0.001
MISSION25_EXPECTED_GLUCOSE_CAPACITY = 10.0
MISSION25_GLUCOSE_CAPACITY_TOLERANCE = 0.01
MISSION25_MIN_AEROBIC_OXYGEN_UPTAKE = 1.0

# Mission 26 completes Dr. Smith's laboratory by extending Mission 25 from
# two endpoint contexts to two matched oxygen-response curves.  The validator
# consumes only the visible Bound Sweep rows and preserves valid WT/KO curves
# independently; it never launches a hidden simulation.
MISSION26_CHECK_VERSION = 2
MISSION26_METHOD = 'FBA'
MISSION26_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION26_TARGET_CONTEXT = 'matched wild-type and b3956 oxygen-response curves'
MISSION26_TARGET_GENE = MISSION25_TARGET_GENE
MISSION26_TARGET_GENE_NAME = MISSION25_TARGET_GENE_NAME
MISSION26_SWEEP_REACTION = 'EX_o2_e'
MISSION26_SWEEP_REACTION_NAME = 'Oxygen exchange'
MISSION26_SWEEP_BOUND = 'lower'
MISSION26_SWEEP_BOUND_LABEL = 'lower bound'
MISSION26_SWEEP_VALUES = [-25.0, -10.0, -1.0, 0.0]
MISSION26_NON_BINDING_BOUND = -25.0
MISSION26_GLUCOSE_REACTION = 'EX_glc__D_e'
MISSION26_OXYGEN_REACTION = 'EX_o2_e'
MISSION26_REQUIRED_MEDIUM_FLUXES = [MISSION26_GLUCOSE_REACTION, MISSION26_OXYGEN_REACTION]
MISSION26_EXPECTED_SCORE_NAME = 'primary_objective_flux'
MISSION26_EXPECTED_GLUCOSE_UPTAKE = 10.0
MISSION26_GLUCOSE_TOLERANCE = 0.05
MISSION26_BOUND_TOLERANCE = 0.05
MISSION26_NON_BINDING_MARGIN = 0.5
MISSION26_MIN_OXYGEN_UPTAKE = 1.0
MISSION26_MIN_VIABLE_GROWTH = 0.05
MISSION26_MIN_POSITIVE_OXYGEN_RETENTION = 0.90
MISSION26_MAX_COLLAPSED_GROWTH = 0.001
MISSION26_MAX_COLLAPSED_RETENTION = 0.01
MISSION26_MONOTONIC_TOLERANCE = 0.001
MISSION26_FLUX_TOLERANCE = 0.01
MISSION26_PRIMARY_TOLERANCE = 0.001

# Mission 27 opens Dr. Ribeiro's laboratory with a metabolic-rescue screen.
# The validator accumulates two controlled references and five single-supplement
# trials from already visible pFBA results.  It never launches a hidden solver.
MISSION27_CHECK_VERSION = 2
MISSION27_METHOD = 'pFBA'
MISSION27_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION27_TARGET_CONTEXT = 'environmental bypass rescue of a gltA knockout'
MISSION27_TARGET_GENE = 'b0720'
MISSION27_TARGET_GENE_NAME = 'gltA'
MISSION27_TARGET_REACTION = 'CS'
MISSION27_GLUCOSE_REACTION = 'EX_glc__D_e'
MISSION27_OXYGEN_REACTION = 'EX_o2_e'
MISSION27_CANDIDATE_SUPPLEMENTS = [
    'EX_akg_e',
    'EX_pyr_e',
    'EX_succ_e',
    'EX_fum_e',
    'EX_mal__L_e',
]
MISSION27_CANDIDATE_NAMES = {
    'EX_akg_e': '2-Oxoglutarate',
    'EX_pyr_e': 'Pyruvate',
    'EX_succ_e': 'Succinate',
    'EX_fum_e': 'Fumarate',
    'EX_mal__L_e': 'L-Malate',
}
MISSION27_EXPECTED_RESCUE = 'EX_akg_e'
MISSION27_REQUIRED_REFERENCE_COUNT = 2
MISSION27_REQUIRED_CANDIDATE_COUNT = len(MISSION27_CANDIDATE_SUPPLEMENTS)
MISSION27_REQUIRED_RUN_COUNT = MISSION27_REQUIRED_REFERENCE_COUNT + MISSION27_REQUIRED_CANDIDATE_COUNT
MISSION27_EXPECTED_SCORE_NAME = 'total_absolute_flux'
MISSION27_EXPECTED_DEFAULT_UPTAKE = 10.0
MISSION27_EXPECTED_SUPPLEMENT_CAPACITY = 10.0
MISSION27_MIN_REFERENCE_GROWTH = 0.5
MISSION27_MAX_KNOCKOUT_GROWTH = 0.001
MISSION27_MIN_RESCUE_GROWTH = 0.05
MISSION27_MAX_NON_RESCUE_GROWTH = 0.001
MISSION27_MIN_RESCUE_UPTAKE = 1.0
MISSION27_MIN_AEROBIC_OXYGEN_UPTAKE = 1.0
MISSION27_FLUX_TOLERANCE = 0.01
MISSION27_PRIMARY_TOLERANCE = 0.001
MISSION27_CAPACITY_TOLERANCE = 0.05

# Mission 28 continues Dr. Ribeiro's rescue programme.  The player keeps the
# gltA lesion and the rescuing 2-oxoglutarate supplement fixed, then screens
# one secondary knockout at a time to identify the network function on which
# the rescue depends.  Every value is taken from the player's visible pFBA
# result; no hidden simulation is launched by the validator.
MISSION28_CHECK_VERSION = 2
MISSION28_METHOD = 'pFBA'
MISSION28_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION28_TARGET_CONTEXT = 'mechanistic dependency mapping of the gltA bypass rescue'
MISSION28_PRIMARY_GENE = MISSION27_TARGET_GENE
MISSION28_PRIMARY_GENE_NAME = MISSION27_TARGET_GENE_NAME
MISSION28_PRIMARY_REACTION = MISSION27_TARGET_REACTION
MISSION28_RESCUE_SUPPLEMENT = MISSION27_EXPECTED_RESCUE
MISSION28_RESCUE_SUPPLEMENT_NAME = MISSION27_CANDIDATE_NAMES[MISSION27_EXPECTED_RESCUE]
MISSION28_SECONDARY_GENES = ['b2587', 'b1761', 'b0728', 'b3236', 'b3403']
MISSION28_SECONDARY_GENE_NAMES = {
    'b2587': 'kgtP',
    'b1761': 'gdhA',
    'b0728': 'sucC',
    'b3236': 'mdh',
    'b3403': 'pckA',
}
MISSION28_SECONDARY_REACTIONS = {
    'b2587': 'AKGt2r',
    'b1761': 'GLUDy',
    'b0728': 'SUCOAS',
    'b3236': 'MDH',
    'b3403': 'PPCK',
}
MISSION28_EXPECTED_DEPENDENCY = 'b2587'
MISSION28_REQUIRED_RUN_COUNT = 1 + len(MISSION28_SECONDARY_GENES)
MISSION28_EXPECTED_SCORE_NAME = MISSION27_EXPECTED_SCORE_NAME
MISSION28_EXPECTED_DEFAULT_UPTAKE = MISSION27_EXPECTED_DEFAULT_UPTAKE
MISSION28_EXPECTED_SUPPLEMENT_CAPACITY = MISSION27_EXPECTED_SUPPLEMENT_CAPACITY
MISSION28_MIN_REFERENCE_GROWTH = 0.05
MISSION28_MIN_REFERENCE_SUPPLEMENT_UPTAKE = 1.0
MISSION28_MAX_DEPENDENCY_GROWTH = 0.001
MISSION28_MAX_DEPENDENCY_UPTAKE = 0.001
MISSION28_MIN_NONDEPENDENCY_RETENTION = 0.90
MISSION28_MIN_NONDEPENDENCY_UPTAKE = 1.0
MISSION28_MIN_AEROBIC_OXYGEN_UPTAKE = 1.0
MISSION28_FLUX_TOLERANCE = 0.01
MISSION28_PRIMARY_TOLERANCE = 0.001
MISSION28_CAPACITY_TOLERANCE = 0.05

# Generic Bound Sweep menu presets retained for Missions 23–26 and future
# experiments. Mission 28 itself no longer consumes these legacy names.
MISSION28_CANDIDATE_CARBON_SOURCES = ['EX_ac_e', 'EX_pyr_e', 'EX_mal__L_e', 'EX_fum_e', 'EX_akg_e']
MISSION28_SWEEP_BOUND = 'lower'
MISSION28_SWEEP_BOUND_LABEL = 'lower bound'
MISSION28_SWEEP_VALUES = [-20.0, -10.0, -5.0, -1.0, 0.0]


EXCHANGE_FLUX_REPORT_REACTION_IDS = [
    'EX_glc__D_e',   # D-Glucose
    'EX_fru_e',      # D-Fructose
    'EX_ac_e',       # Acetate
    'EX_acald_e',    # Acetaldehyde
    'EX_pyr_e',      # Pyruvate
    'EX_mal__L_e',   # L-Malate
    'EX_fum_e',      # Fumarate
    'EX_akg_e',      # 2-Oxoglutarate
    'EX_succ_e',     # Succinate
    'EX_etoh_e',     # Ethanol
    'EX_for_e',      # Formate
    'EX_lac__D_e',   # D-lactate
    'EX_nh4_e',      # Ammonia
    'EX_pi_e',       # Phosphate
    'EX_o2_e',       # Oxygen
    'EX_co2_e',      # CO2
    'EX_h2o_e',      # Water
    'EX_h_e',        # Protons
    'EX_gln__L_e',   # L-Glutamine
    'EX_glu__L_e',   # L-Glutamate
]



def _solver_scalar_value(result):
    """Return the raw scalar printed by the solver, without assigning semantics."""
    results_str = str(result)
    try:
        if len(results_str.splitlines()) > 1 and str(results_str.splitlines()[1]).strip() == 'Status: INFEASIBLE':
            return 'Status: INFEASIBLE'
        return float(str(results_str.splitlines()[0])[11:])
    except Exception:
        return results_str


def _normalise_result(result):
    value = _solver_scalar_value(result)
    if value == 'Status: INFEASIBLE':
        return value
    try:
        numeric = round(float(value), 3)
        if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
            numeric = 0.0
        return numeric
    except Exception:
        return value


def _is_infeasible_solver_exception(error):
    """Recognise solver infeasibility exceptions without desktop-only imports.

    COBRA's FBA path can return a normal result whose status is infeasible, while
    its pFBA path raises ``cobra.exceptions.Infeasible`` before MEWpy can build a
    result object.  Keep this helper import-free so ``simulation.py`` remains
    importable by the browser build, which delegates solving to the backend.
    """
    if error is None:
        return False
    error_name = type(error).__name__.strip().lower()
    error_text = str(error).strip().lower()
    return error_name == 'infeasible' or 'infeasible' in error_text


def _numeric_result(value):
    try:
        return max(float(value), 0.0)
    except Exception:
        return 0.0


def _normalise_method_name(value):
    """Return the canonical solver identifier used by desktop and backend.

    The simulation menu presents a more readable lMOMA label, while existing
    saves and the FastAPI schema continue to use the stable ``lMOMA`` token.
    """
    raw = str(value or '').strip()
    compact = re.sub(r'[^a-z0-9]+', '', raw.lower())
    if (
        'lmoma' in compact
        or compact in {
            'linearmoma',
            'linearminimizationofmetabolicadjustment',
            'linearminimisationofmetabolicadjustment',
        }
    ):
        return 'lMOMA'
    if compact == 'pfba':
        return 'pFBA'
    if compact == 'fba':
        return 'FBA'
    if compact == 'room':
        return 'ROOM'
    return raw


def normalise_method_name(value):
    """Public method-name normaliser for UI and integration modules.

    ``window.py`` imports simulation symbols with ``from simulation import *``.
    Python deliberately excludes names beginning with an underscore from that
    form of import, so UI code must use this public wrapper rather than the
    private implementation above.  Keeping the canonicalisation in one place
    preserves compatibility with old saves, the readable Linear MOMA label and
    the stable FastAPI method tokens.
    """
    return _normalise_method_name(value)


def _read_simulation_file():
    data_simul = load_file(get_save_path('simulation_file'))
    method, objective, genes, reactions = data_simul[:4]

    method_name = _normalise_method_name(method['method'][0][0])
    objective_name = objective['objective'][0][0]

    return method_name, objective_name, genes, reactions



def _build_default_reactions_data():
    """Return JSON-safe toggle states for every model-default exchange bound.

    Pandas scalar comparisons can yield ``numpy.bool_`` values.  They behave
    like booleans in Python conditionals but are rejected by the standard JSON
    encoder, which is used by saves and by the future browser contract.
    Converting at this shared construction boundary keeps every Bound Sweep
    state composed only of native Python values without changing any bound.
    """
    reactions_data = {}
    for i in range(len(REACTIONS.index)):
        reactions_data[f'reaction_{i}_lb'] = bool(REACTIONS.lb.iloc[i] != 0)
        reactions_data[f'reaction_{i}_ub'] = bool(REACTIONS.ub.iloc[i] != 0)
    return reactions_data


def _build_active_genes_data():
    return {gene_id: True for gene_id in GENES}


def _reaction_bound_open_states(reactions, reaction_index):
    """Return the lower/upper toggle states for one exchange reaction.

    New simulation menus save explicit keys (``reaction_<i>_lb`` and
    ``reaction_<i>_ub``).  Older pygame-menu saves used automatically generated
    widget identifiers, but preserved the creation order.  Supporting both
    representations keeps existing saves readable while giving mission
    validators and the simulator one consistent interpretation of the medium.
    """
    if not isinstance(reactions, dict):
        return None, None

    lb_key = f'reaction_{reaction_index}_lb'
    ub_key = f'reaction_{reaction_index}_ub'
    if lb_key in reactions and ub_key in reactions:
        return bool(reactions[lb_key]), bool(reactions[ub_key])

    # If this is an explicit-key payload, missing one member of the requested
    # pair means the data is incomplete.  Do not reinterpret the remaining
    # values positionally, because JSON/dictionary order is not scientific
    # information and could silently map a different reaction to this index.
    if any(
        str(key).startswith('reaction_')
        and (str(key).endswith('_lb') or str(key).endswith('_ub'))
        for key in reactions
    ):
        return None, None

    reaction_values = list(reactions.values())
    lb_index = reaction_index * 2
    ub_index = lb_index + 1
    if ub_index >= len(reaction_values):
        return None, None

    return bool(reaction_values[lb_index]), bool(reaction_values[ub_index])


def _read_selected_production_fluxes():
    """Read the production fluxes selected by the player in the simulation UI.

    Older save files only have method/objective/genes/reactions, so this stays
    backwards compatible and simply returns an empty selection in that case.
    """
    try:
        data_simul = load_file(get_save_path('simulation_file'))
    except Exception:
        return []

    if not isinstance(data_simul, (list, tuple)) or len(data_simul) < 5:
        return []

    raw_flux_data = data_simul[4] or {}
    if not isinstance(raw_flux_data, dict):
        return []

    return [
        reaction_id
        for reaction_id in PRODUCTION_FLUX_REACTION_IDS
        if bool(raw_flux_data.get(reaction_id, False))
    ]

def _build_anaerobic_reactions_data():
    reactions_data = _build_default_reactions_data()

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION05_OXYGEN_REACTION)
        reactions_data[f'reaction_{oxygen_index}_lb'] = False
    except ValueError:
        pass

    return reactions_data


def _oxygen_lower_bound_closed(reactions):
    try:
        oxygen_index = list(REACTIONS.index).index(MISSION05_OXYGEN_REACTION)
    except ValueError:
        return False

    lower_open, _upper_open = _reaction_bound_open_states(reactions, oxygen_index)
    return lower_open is not None and not lower_open


def _mission08_environment_status(reactions):
    """Classify the medium as default or oxygen-constrained.

    Explicit reaction-bound identifiers are read independently of dictionary
    order.  The positional fallback remains available only for legacy
    pygame-menu saves created before explicit identifiers were introduced.
    """
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION08_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lower_bound_open, upper_bound_open = _reaction_bound_open_states(reactions, i)
        reaction_id = REACTIONS.index[i]
        if lower_bound_open is None or upper_bound_open is None:
            unexpected_changes.append(f'{reaction_id} bounds unavailable')
            continue

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        if i == oxygen_index:
            oxygen_lower_bound_closed = not lower_bound_open
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
        else:
            if lower_bound_open != default_lower_bound_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')

    environment_type = (
        'oxygen_constrained' if oxygen_lower_bound_closed else 'default'
    )
    return environment_type, oxygen_lower_bound_closed, unexpected_changes



def _mission09_environment_status(reactions):
    """Validate the controlled aerobic L-malate medium for Mission 09.

    The validator accepts both the explicit reaction-bound identifiers used by
    the corrected menu and the positional pygame-menu format found in older
    saves.  This is the same interpretation used to build the actual simulator
    constraints, preventing a scientifically correct run from being rejected
    solely because of widget-key formatting.
    """
    unexpected_changes = []
    glucose_closed = False
    malate_open = False
    try:
        glucose_index = list(REACTIONS.index).index(MISSION09_BLOCKED_CARBON_SOURCE)
    except ValueError:
        glucose_index = None
    try:
        malate_index = list(REACTIONS.index).index(MISSION09_REPLACEMENT_CARBON_SOURCE)
    except ValueError:
        malate_index = None

    for i in range(len(REACTIONS.index)):
        lower_open, upper_open = _reaction_bound_open_states(reactions, i)
        reaction_id = REACTIONS.index[i]
        if lower_open is None or upper_open is None:
            unexpected_changes.append(f'{reaction_id} bounds unavailable')
            continue

        default_lower_open = REACTIONS.lb.iloc[i] != 0
        default_upper_open = REACTIONS.ub.iloc[i] != 0
        if i == glucose_index:
            glucose_closed = not lower_open
            if upper_open != default_upper_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
        elif i == malate_index:
            malate_open = lower_open
            if upper_open != default_upper_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
        else:
            if lower_open != default_lower_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_open != default_upper_open:
                unexpected_changes.append(f'{reaction_id} upper bound')

    environment_correct = glucose_closed and malate_open and not unexpected_changes
    return environment_correct, glucose_closed, malate_open, unexpected_changes




def _mission10_environment_status(reactions):
    """Validate the default medium with only oxygen uptake disabled.

    Explicit reaction-bound widget identifiers and the legacy positional
    pygame-menu representation are interpreted identically to the simulator.
    """
    oxygen_closed = False
    unexpected_changes = []
    try:
        oxygen_index = list(REACTIONS.index).index(MISSION10_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lower_open, upper_open = _reaction_bound_open_states(reactions, i)
        reaction_id = REACTIONS.index[i]
        if lower_open is None or upper_open is None:
            unexpected_changes.append(f'{reaction_id} bounds unavailable')
            continue

        default_lower_open = REACTIONS.lb.iloc[i] != 0
        default_upper_open = REACTIONS.ub.iloc[i] != 0
        if i == oxygen_index:
            oxygen_closed = not lower_open
            if upper_open != default_upper_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
        else:
            if lower_open != default_lower_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_open != default_upper_open:
                unexpected_changes.append(f'{reaction_id} upper bound')

    environment_correct = oxygen_closed and not unexpected_changes
    return environment_correct, oxygen_closed, unexpected_changes


def _mission11_environment_status(reactions):
    """Validate the default medium with only oxygen uptake disabled.

    The same explicit/legacy bound reader used by the simulator is used here,
    avoiding desktop/web disagreement caused by pygame-menu dictionary order.
    """
    oxygen_closed = False
    unexpected_changes = []
    try:
        oxygen_index = list(REACTIONS.index).index(MISSION11_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lower_open, upper_open = _reaction_bound_open_states(reactions, i)
        reaction_id = REACTIONS.index[i]
        if lower_open is None or upper_open is None:
            unexpected_changes.append(f'{reaction_id} bounds unavailable')
            continue

        default_lower_open = REACTIONS.lb.iloc[i] != 0
        default_upper_open = REACTIONS.ub.iloc[i] != 0
        if i == oxygen_index:
            oxygen_closed = not lower_open
            if upper_open != default_upper_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
        else:
            if lower_open != default_lower_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_open != default_upper_open:
                unexpected_changes.append(f'{reaction_id} upper bound')

    return oxygen_closed and not unexpected_changes, oxygen_closed, unexpected_changes


def _mission12_environment_status(reactions):
    """Classify the controlled Mission 12 environment.

    Valid runs are either the untouched model-default medium or the same
    medium with only the oxygen-exchange lower bound closed.  The explicit
    widget-key reader keeps desktop and web representations equivalent.
    """
    oxygen_closed = False
    unexpected_changes = []
    try:
        oxygen_index = list(REACTIONS.index).index(MISSION12_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lower_open, upper_open = _reaction_bound_open_states(reactions, i)
        reaction_id = REACTIONS.index[i]
        if lower_open is None or upper_open is None:
            unexpected_changes.append(f'{reaction_id} bounds unavailable')
            continue

        default_lower_open = REACTIONS.lb.iloc[i] != 0
        default_upper_open = REACTIONS.ub.iloc[i] != 0
        if i == oxygen_index:
            oxygen_closed = not lower_open
            if upper_open != default_upper_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
            if lower_open not in (default_lower_open, False):
                unexpected_changes.append(f'{reaction_id} lower bound')
        else:
            if lower_open != default_lower_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_open != default_upper_open:
                unexpected_changes.append(f'{reaction_id} upper bound')

    environment_type = None
    if not unexpected_changes:
        environment_type = 'oxygen_constrained' if oxygen_closed else 'default'
    return environment_type, oxygen_closed, unexpected_changes

def _mission13_environment_status(reactions):
    """Validate the exact oxygen-constrained medium using robust bound ids."""
    environment_type, oxygen_closed, unexpected_changes = _mission12_environment_status(reactions)
    return (
        environment_type == 'oxygen_constrained' and oxygen_closed,
        list(unexpected_changes),
    )



def _mission14_environment_status(reactions):
    """Validate the exact oxygen-constrained Mission 14 medium.

    Mission 14 reuses the same anaerobic succinate-optimisation setup as
    Mission 13.  The robust explicit/legacy bound reader avoids depending on
    pygame-menu dictionary order and therefore keeps desktop and web clients
    equivalent.
    """
    oxygen_closed, unexpected_changes = _mission13_environment_status(reactions)
    return oxygen_closed, list(unexpected_changes)



def _mission15_environment_status(reactions):
    """Validate the exact oxygen-constrained medium with robust bound ids."""
    oxygen_closed, unexpected_changes = _mission14_environment_status(reactions)
    return oxygen_closed, list(unexpected_changes)


def _environment_has_changes(reactions):
    """Return whether any exchange-bound toggle differs from the model.

    Explicit keys make the result independent of JSON/dictionary ordering.
    Incomplete bound data is treated conservatively as a changed environment
    rather than silently accepting an uncontrolled run.
    """
    for i in range(len(REACTIONS.index)):
        lower_bound_open, upper_bound_open = _reaction_bound_open_states(reactions, i)
        if lower_bound_open is None or upper_bound_open is None:
            return True

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0
        if (
            lower_bound_open != default_lower_bound_open
            or upper_bound_open != default_upper_bound_open
        ):
            return True

    return False


def _knocked_out_genes(genes):
    return [
        gene_id
        for gene_id, is_active in genes.items()
        if not bool(is_active)
    ]


def resolve_exchange_bound_value(original_bound, is_open, bound_type):
    """Translate an environmental-menu toggle into a quantitative bound.

    Existing non-zero bounds are restored exactly as defined in the model.
    Opening a bound that is zero in the model uses the menu's explicit
    fallback capacity: -10 for uptake (lower bound) and 1000 for secretion
    (upper bound).  Closing either side always sets it to zero.
    """
    if not bool(is_open):
        return 0.0

    try:
        original_value = float(original_bound)
    except (TypeError, ValueError):
        original_value = 0.0

    if original_value != 0.0:
        return original_value

    if bound_type == 'lower':
        return DEFAULT_OPEN_UPTAKE_BOUND
    if bound_type == 'upper':
        return DEFAULT_OPEN_SECRETION_BOUND
    raise ValueError(f'Unknown bound type: {bound_type}')


def _build_envconditions_from_reactions(reactions, reactions_original):
    """Build exchange constraints without inflating the model's medium.

    The old implementation converted every open lower bound to -1000 and every
    open upper bound to 1000.  That changed glucose from -10 to -1000 and made
    Mission 01 report an artificial anaerobic growth value near 15.713.
    """
    envconditions = {}

    for i in range(len(reactions_original.index)):
        lower_bound_open, upper_bound_open = _reaction_bound_open_states(reactions, i)
        if lower_bound_open is None or upper_bound_open is None:
            break

        reaction_id = reactions_original.index[i]

        lower_bound = resolve_exchange_bound_value(
            reactions_original.lb.iloc[i], lower_bound_open, 'lower'
        )
        upper_bound = resolve_exchange_bound_value(
            reactions_original.ub.iloc[i], upper_bound_open, 'upper'
        )
        envconditions[reaction_id] = (lower_bound, upper_bound)

    return envconditions


def _apply_gene_knockouts(envconditions, genes, genes_data=None, metabolic_model=None):
    """Apply gene knockouts only when the complete GPR disables a reaction.

    The previous implementation blocked every reaction associated with a
    knocked-out gene.  That incorrectly disabled reactions with alternative
    genes (OR rules).  The new implementation evaluates each full GPR rule and
    blocks only reactions whose rule becomes false.
    """
    knocked_out = _knocked_out_genes(genes)
    if not knocked_out:
        return envconditions

    active_model = metabolic_model if metabolic_model is not None else model
    if active_model is None:
        raise RuntimeError('A metabolic model is required to evaluate GPR knockouts.')

    for reaction_id in disabled_reaction_ids(active_model, knocked_out):
        envconditions[reaction_id] = (0.0, 0.0)
    return envconditions


def _build_local_constraints(genes, reactions):
    from mewpy.simulation import get_simulator

    simul = get_simulator(model)
    reactions_original = simul.find_reactions('EX')
    envconditions = _build_envconditions_from_reactions(reactions, reactions_original)
    genes_data = simul.find_genes()
    envconditions = _apply_gene_knockouts(envconditions, genes, genes_data, metabolic_model=model)
    return simul, envconditions


def _apply_constraints_to_cobra_model(cobra_model, constraints):
    """Apply reaction-id bounds to an isolated COBRApy model copy."""
    for reaction_id, bounds in (constraints or {}).items():
        try:
            lower_bound, upper_bound = bounds
            reaction = cobra_model.reactions.get_by_id(str(reaction_id))
            reaction.bounds = (float(lower_bound), float(upper_bound))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f'Invalid constraint for reaction {reaction_id}: {bounds}') from exc


def _simulate_local_lmoma_with_reference(objective_name, genes, reactions):
    """Run linear MOMA against an explicit pre-knockout FBA reference.

    MEWpy 0.1.36 delegates lMOMA to COBRApy without exposing a reference
    solution.  When knockout constraints are already present, COBRApy then
    builds its fallback reference on the mutant itself, producing a misleading
    zero adjustment.  The mathematically correct workflow is therefore built
    explicitly here: same selected medium and objective, wild-type FBA
    reference first, then the GPR-derived mutant under linear MOMA.
    """
    if model is None:
        raise RuntimeError('A local COBRApy model is required for lMOMA simulation.')

    from cobra.flux_analysis import moma

    environment_constraints = _build_envconditions_from_reactions(reactions, REACTIONS)
    knocked_out = _knocked_out_genes(genes)
    disabled_reactions = disabled_reaction_ids(model, knocked_out)

    reference_model = model.copy()
    reference_model.objective = objective_name
    _apply_constraints_to_cobra_model(reference_model, environment_constraints)
    reference_solution = reference_model.optimize()
    if str(getattr(reference_solution, 'status', '')).lower() != 'optimal':
        raise RuntimeError(
            f'Could not construct the wild-type FBA reference for lMOMA: '
            f'{getattr(reference_solution, "status", "unknown status")}.'
        )

    mutant_model = model.copy()
    mutant_model.objective = objective_name
    _apply_constraints_to_cobra_model(mutant_model, environment_constraints)
    _apply_constraints_to_cobra_model(
        mutant_model,
        {reaction_id: (0.0, 0.0) for reaction_id in disabled_reactions},
    )

    result = moma(mutant_model, solution=reference_solution, linear=True)
    if str(getattr(result, 'status', '')).lower() != 'optimal':
        raise RuntimeError(
            f'Linear MOMA did not return an optimal solution: '
            f'{getattr(result, "status", "unknown status")}.'
        )

    method_score = _as_float_or_none(getattr(result, 'objective_value', None))
    if method_score is None:
        raise RuntimeError('Linear MOMA did not expose its adjustment objective value.')

    reference_flux = _as_float_or_none(
        _extract_from_mapping(getattr(reference_solution, 'fluxes', None), objective_name)
    )
    metadata = {
        'reference_method': 'FBA',
        'reference_objective_reaction': objective_name,
        'reference_primary_objective_flux': reference_flux,
        'reference_uses_same_environment': True,
        'reference_has_no_gene_knockouts': True,
        'gpr_disabled_reactions': list(disabled_reactions),
    }
    return result, float(method_score), metadata


def _simulate_local_objective(method_name, objective_name, genes, reactions):
    method_name = _normalise_method_name(method_name)
    if method_name == 'lMOMA':
        result, _method_score, _metadata = _simulate_local_lmoma_with_reference(
            objective_name, genes, reactions
        )
        objective_flux = _as_float_or_none(_extract_flux(result, objective_name))
        if objective_flux is None:
            raise RuntimeError(
                f'Linear MOMA did not expose the objective-reaction flux for {objective_name}.'
            )
        return round(float(objective_flux), 3)

    simul, constraints = _build_local_constraints(genes, reactions)
    simul.objective = objective_name
    result = simul.simulate(method=method_name, constraints=constraints)
    return _normalise_result(result)


def _extract_from_mapping(data, key):
    if data is None:
        return None

    if callable(data):
        try:
            data = data()
        except TypeError:
            pass

    if hasattr(data, 'to_dict'):
        try:
            data = data.to_dict()
        except Exception:
            pass

    if isinstance(data, dict):
        if key in data:
            return data[key]
        # Some objects may use reaction objects as keys. Fall back to string ids.
        for candidate_key, value in data.items():
            if str(candidate_key) == key:
                return value
        return None

    if hasattr(data, 'get'):
        try:
            value = data.get(key)
            if value is not None:
                return value
        except Exception:
            pass

    if hasattr(data, 'loc'):
        try:
            return data.loc[key]
        except Exception:
            pass

    try:
        return data[key]
    except Exception:
        return None


def _extract_flux(result, reaction_id):
    """Read one reaction flux from a MEWpy/Cobra-like simulation result."""
    for attr_name in ('fluxes', 'flux_distribution', 'values', 'data'):
        value = _extract_from_mapping(getattr(result, attr_name, None), reaction_id)
        if value is not None:
            return value

    for method_name in ('to_dataframe', 'to_frame'):
        method = getattr(result, method_name, None)
        if not callable(method):
            continue
        try:
            table = method()
        except Exception:
            continue

        if hasattr(table, 'loc'):
            try:
                row = table.loc[reaction_id]
                for column in ('flux', 'Flux', 'value', 'Value'):
                    try:
                        return row[column]
                    except Exception:
                        pass
                try:
                    return float(row)
                except Exception:
                    pass
            except Exception:
                pass

    return _extract_from_mapping(result, reaction_id)


def _as_float_or_none(value):
    try:
        return float(value)
    except Exception:
        return None


def _normalise_flux_mapping(data):
    """Return a clean reaction-id -> float mapping from solver-like data."""
    if data is None:
        return {}
    if callable(data):
        try:
            data = data()
        except TypeError:
            pass
        except Exception:
            return {}
    if hasattr(data, 'to_dict'):
        try:
            data = data.to_dict()
        except Exception:
            pass
    if not isinstance(data, dict):
        try:
            data = dict(data)
        except Exception:
            return {}
    clean = {}
    for reaction_id, value in data.items():
        numeric = _as_float_or_none(value)
        if numeric is not None:
            clean[str(reaction_id)] = float(numeric)
    return clean


def _extract_flux_mapping(result):
    """Extract the full visible flux vector without launching another run."""
    for attr_name in ('fluxes', 'flux_distribution', 'values', 'data'):
        mapping = _normalise_flux_mapping(getattr(result, attr_name, None))
        if mapping:
            return mapping
    return _normalise_flux_mapping(result if isinstance(result, dict) else None)


def _method_score_label(method_name):
    if method_name == 'pFBA':
        return 'total_absolute_flux'
    if method_name == 'FBA':
        return 'primary_objective_flux'
    if method_name == 'lMOMA':
        return 'total_absolute_flux_adjustment'
    if method_name == 'ROOM':
        return 'significant_flux_change_score'
    return 'solver_objective_value'


def _build_method_diagnostics(method_name, objective_name, result, solver_value=None):
    """Build method-aware diagnostics from the same visible solver result.

    ``solver_value`` is the scalar printed by MEWpy.  For pFBA this is the
    secondary parsimony score, not the flux of ``objective_name``.  The primary
    objective flux is therefore always read directly from the returned flux
    vector.
    """
    fluxes = _extract_flux_mapping(result)
    primary = _as_float_or_none(fluxes.get(objective_name))
    if primary is None:
        primary = _as_float_or_none(_extract_flux(result, objective_name))
    method_score = _as_float_or_none(solver_value)
    total_absolute_flux = None
    active_reaction_count = None
    if fluxes:
        total_absolute_flux = sum(abs(float(value)) for value in fluxes.values())
        active_reaction_count = sum(
            1 for value in fluxes.values()
            if abs(float(value)) > MISSION13_ACTIVE_FLUX_TOLERANCE
        )
    return {
        'method': method_name,
        'objective_reaction': objective_name,
        'primary_objective_flux': float(primary) if primary is not None else None,
        'method_score': float(method_score) if method_score is not None else None,
        'method_score_name': _method_score_label(method_name),
        'total_absolute_flux': float(total_absolute_flux) if total_absolute_flux is not None else None,
        'active_reaction_count': int(active_reaction_count) if active_reaction_count is not None else None,
    }


def _method_diagnostics_from_production_data(production_fluxes):
    if not isinstance(production_fluxes, dict):
        return {}
    diagnostics = production_fluxes.get('method_diagnostics')
    return copy.deepcopy(diagnostics) if isinstance(diagnostics, dict) else {}


def _build_production_flux_data(selected_ids, flux_getter=None, error=None):
    """Build display-ready production flux data for selected exchange reactions."""
    selected_ids = [
        reaction_id
        for reaction_id in selected_ids
        if reaction_id in PRODUCTION_FLUX_REACTION_IDS
    ]

    data = {
        'selected_ids': selected_ids,
        'items': [],
    }

    if error:
        data['error'] = error
        return data

    if not selected_ids:
        return data

    for reaction_id in selected_ids:
        raw_flux = None
        if callable(flux_getter):
            try:
                raw_flux = flux_getter(reaction_id)
            except Exception:
                raw_flux = None

        raw_value = _as_float_or_none(raw_flux)
        item = {
            'reaction_id': reaction_id,
            'product_name': PRODUCTION_FLUX_NAMES.get(reaction_id, reaction_id),
            'label': PRODUCTION_FLUX_LABELS.get(reaction_id, reaction_id),
        }

        if raw_value is None:
            item['error'] = 'Flux not available in this simulation result.'
        else:
            # For exchange reactions, positive flux represents secretion/export.
            # A negative value would mean uptake/consumption, not production.
            item['raw_flux'] = round(raw_value, 6)
            item['production_flux'] = round(max(raw_value, 0.0), 3)

        data['items'].append(item)

    return data


def _reaction_display_label(reaction_id):
    try:
        reaction_ids = list(REACTIONS.index)
        reaction_index = reaction_ids.index(reaction_id)
        reaction_name = str(REACTIONS.name.iloc[reaction_index])
        return f'{reaction_name} ({reaction_id})'
    except Exception:
        return reaction_id


def _build_medium_flux_data(reaction_ids=None, flux_getter=None, error=None):
    """Build a compact uptake/exchange report for medium-engineering missions.

    For exchange reactions, negative flux means uptake/consumption and positive
    flux means secretion/export. Production Flux already focuses on exported
    products; this report focuses on what the model is taking from the medium.
    """
    reaction_ids = reaction_ids or EXCHANGE_FLUX_REPORT_REACTION_IDS
    reaction_ids = [reaction_id for reaction_id in reaction_ids if reaction_id in list(REACTIONS.index)]

    data = {
        'reaction_ids': reaction_ids,
        'items': [],
    }

    if error:
        data['error'] = error
        return data

    for reaction_id in reaction_ids:
        raw_flux = None
        if callable(flux_getter):
            try:
                raw_flux = flux_getter(reaction_id)
            except Exception:
                raw_flux = None

        raw_value = _as_float_or_none(raw_flux)
        item = {
            'reaction_id': reaction_id,
            'label': _reaction_display_label(reaction_id),
        }

        if raw_value is None:
            item['error'] = 'Flux not available in this simulation result.'
        else:
            item['raw_flux'] = round(raw_value, 6)
            item['uptake_flux'] = round(max(-raw_value, 0.0), 3)
            item['secretion_flux'] = round(max(raw_value, 0.0), 3)

        data['items'].append(item)

    return data


def _simulate_local_objective_with_production_fluxes(method_name, objective_name, genes, reactions, selected_fluxes):
    method_name = _normalise_method_name(method_name)
    lmoma_metadata = None
    try:
        if method_name == 'lMOMA':
            result, raw_solver_value, lmoma_metadata = _simulate_local_lmoma_with_reference(
                objective_name, genes, reactions
            )
        else:
            simul, constraints = _build_local_constraints(genes, reactions)
            simul.objective = objective_name
            result = simul.simulate(method=method_name, constraints=constraints)
            raw_solver_value = _solver_scalar_value(result)
    except Exception as error:
        # COBRA pFBA raises on an infeasible primary problem instead of returning
        # the status object produced by ordinary FBA.  Convert that expected
        # solver outcome into the same visible structured result used elsewhere.
        if _is_infeasible_solver_exception(error):
            return (
                'Status: INFEASIBLE',
                _build_production_flux_data(
                    selected_fluxes,
                    error='Simulation infeasible. Production fluxes could not be measured.'
                ),
                _build_medium_flux_data(
                    error='Simulation infeasible. Medium fluxes could not be measured.'
                )
            )
        raise

    if method_name == 'lMOMA':
        status = str(getattr(result, 'status', '')).strip().lower()
        solver_value = 'Status: INFEASIBLE' if status == 'infeasible' else raw_solver_value
    else:
        solver_value = _normalise_result(result)

    if solver_value == 'Status: INFEASIBLE':
        return (
            solver_value,
            _build_production_flux_data(
                selected_fluxes,
                error='Simulation infeasible. Production fluxes could not be measured.'
            ),
            _build_medium_flux_data(
                error='Simulation infeasible. Medium fluxes could not be measured.'
            )
        )

    diagnostics = _build_method_diagnostics(
        method_name, objective_name, result, solver_value=raw_solver_value
    )
    if lmoma_metadata:
        diagnostics.update(lmoma_metadata)
    primary_objective_flux = _as_float_or_none(
        diagnostics.get('primary_objective_flux')
    )
    # The visible objective value must always be the selected reaction flux.
    # In pFBA the solver's printed scalar is a secondary parsimony score.
    objective_result = (
        round(float(primary_objective_flux), 3)
        if primary_objective_flux is not None
        else solver_value
    )

    flux_getter = lambda reaction_id: _extract_flux(result, reaction_id)
    production_fluxes = _build_production_flux_data(
        selected_fluxes,
        flux_getter=flux_getter
    )
    if primary_objective_flux is not None:
        production_fluxes['objective_raw'] = float(primary_objective_flux)
    biomass_raw = _as_float_or_none(_extract_flux(result, MISSION07_BIOMASS_OBJECTIVE))
    if biomass_raw is not None:
        production_fluxes['biomass_raw'] = float(biomass_raw)
    production_fluxes['method_diagnostics'] = diagnostics
    medium_fluxes = _build_medium_flux_data(
        flux_getter=flux_getter
    )
    return objective_result, production_fluxes, medium_fluxes




def is_mission06_unlocked(missions_completed):
    """Mission 06 starts only after the guided strain-design sequence."""
    return '05' in (missions_completed or [])


def _mission06_target_flux(production_fluxes):
    """Return the measured non-negative ethanol secretion using raw precision."""
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return None
    for item in production_fluxes.get('items') or []:
        if item.get('reaction_id') != MISSION06_TARGET_FLUX:
            continue
        if item.get('error'):
            return None
        raw = item.get('raw_flux', item.get('production_flux'))
        value = _as_float_or_none(raw)
        return max(value, 0.0) if value is not None else None
    return None


def _mission06_objective_value(objective_result, production_fluxes):
    """Prefer the unrounded objective flux attached to the visible result."""
    if isinstance(production_fluxes, dict):
        raw = _as_float_or_none(production_fluxes.get('objective_raw'))
        if raw is not None:
            return max(raw, 0.0)
    value = _as_float_or_none(objective_result)
    return max(value, 0.0) if value is not None else None


def _mission06_oxygen_uptake(medium_fluxes):
    _raw, uptake, _secretion = _medium_flux_maps(medium_fluxes)
    return _as_float_or_none(uptake.get('EX_o2_e')) if 'EX_o2_e' in uptake else None


def _mission06_design_key(genes):
    return '+'.join(sorted(genes or []))


def _mission06_normalise_attempt(attempt, baseline_growth):
    item = copy.deepcopy(attempt or {})
    growth = _numeric_result(item.get('growth'))
    production = _numeric_result(item.get('production'))
    baseline = _as_float_or_none(baseline_growth)
    ratio = growth / baseline if baseline is not None and baseline > 0 else None
    score = growth * production
    item['growth'] = float(growth)
    item['production'] = float(production)
    item['growth_ratio'] = float(ratio) if ratio is not None else None
    item['growth_percent'] = round(ratio * 100.0, 1) if ratio is not None else None
    item['score'] = float(score)
    item['meets_growth_threshold'] = (
        ratio is not None and ratio >= MISSION06_MIN_GROWTH_RATIO
    )
    item['win'] = (
        item['meets_growth_threshold'] and score > MISSION06_VILLAIN_SCORE
    )
    return item


def _mission06_best_attempt(design_best):
    candidates = list((design_best or {}).values())
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            float(item.get('score', 0.0)),
            float(item.get('growth_ratio', 0.0) or 0.0),
            -len(item.get('knocked_out_genes') or []),
        ),
        reverse=True,
    )
    return copy.deepcopy(candidates[0])


def _build_mission06_challenge_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
):
    """Validate one visible Mission 06 run and preserve the best valid design."""
    if not isinstance(existing_report, dict):
        existing_report = {}
    elif existing_report and (
        existing_report.get('mission_id') != '06'
        or existing_report.get('check_version') != 3
    ):
        # Old 14500-score artifacts came from hidden re-simulations and cannot
        # be trusted under the corrected medium/GPR rules.
        existing_report = {}

    baseline = copy.deepcopy(existing_report.get('baseline'))
    baseline_growth = _as_float_or_none((baseline or {}).get('growth'))
    design_best = copy.deepcopy(existing_report.get('design_best') or {})
    history = copy.deepcopy(existing_report.get('attempt_history') or [])

    knocked_out = sorted(_knocked_out_genes(genes))
    candidate_knockouts = [g for g in knocked_out if g in MISSION06_CANDIDATE_GENES]
    outside_candidates = [g for g in knocked_out if g not in MISSION06_CANDIDATE_GENES]
    is_baseline = len(knocked_out) == 0
    is_design = len(knocked_out) > 0
    within_budget = 1 <= len(knocked_out) <= MISSION06_MAX_KNOCKOUTS

    method_correct = method_name == MISSION06_METHOD
    objective_correct = selected_objective == MISSION06_GROWTH_OBJECTIVE
    environment_default = not _environment_has_changes(reactions)
    selected_fluxes = _read_selected_production_fluxes()
    tracking_ready = MISSION06_TARGET_FLUX in selected_fluxes

    growth_value = _mission06_objective_value(objective_result, production_fluxes)
    production_value = _mission06_target_flux(production_fluxes)
    oxygen_uptake = _mission06_oxygen_uptake(medium_fluxes)
    result_available = growth_value is not None
    production_available = production_value is not None
    oxygen_available = oxygen_uptake is not None

    issues = []
    if objective_error:
        issues.append(objective_error)
    if not method_correct:
        issues.append('Use FBA for every Mission 06 reference and design run.')
    if not objective_correct:
        issues.append('Use the biomass objective so growth and ethanol are measured in the same growth-optimal solution.')
    if not environment_default:
        issues.append('Restore the unchanged default aerobic medium; environmental enrichment is not allowed in this strain-design challenge.')
    if not tracking_ready:
        issues.append(f'Track {MISSION06_TARGET_FLUX} in Production Flux for every Mission 06 run.')
    if not result_available:
        issues.append('The visible simulation did not provide a numeric biomass-growth result.')
    if not production_available:
        issues.append(f'The visible simulation did not provide a numeric {MISSION06_TARGET_FLUX} secretion flux.')
    if not oxygen_available:
        issues.append('The Exchange Flux Report did not provide oxygen-uptake evidence.')
    if outside_candidates:
        issues.append('Use only the highlighted Mission 06 candidate genes: ' + ', '.join(outside_candidates) + '.')
    if is_design and not within_budget:
        issues.append(f'Use one or two knockouts per design; the Mission 06 budget is at most {MISSION06_MAX_KNOCKOUTS}.')

    if is_baseline:
        if result_available and growth_value < MISSION06_MIN_BASELINE_GROWTH:
            issues.append('The all-genes-active aerobic reference must show viable predicted growth.')
        if production_available and production_value > MISSION06_MAX_BASELINE_PRODUCTION:
            issues.append('The default aerobic reference should show negligible ethanol secretion.')
        if oxygen_available and oxygen_uptake <= MISSION06_FLUX_TOLERANCE:
            issues.append('The default aerobic reference should show positive oxygen uptake.')
    else:
        if baseline_growth is None:
            issues.append('Record an all-genes-active default aerobic reference before scoring designs.')
        if len(candidate_knockouts) != len(knocked_out):
            # A more specific outside-candidate issue was already added.
            pass

    growth_ratio = (
        growth_value / baseline_growth
        if growth_value is not None and baseline_growth is not None and baseline_growth > 0
        else None
    )
    if is_design and growth_ratio is not None and growth_ratio < MISSION06_MIN_GROWTH_RATIO:
        issues.append(
            f'The design retains less than {MISSION06_MIN_GROWTH_RATIO * 100:.0f}% of the aerobic reference growth and is not operationally viable for this challenge.'
        )

    current_valid = not issues
    current_recorded = False
    current_type = 'invalid'
    current_attempt = {
        'knocked_out_genes': knocked_out,
        'gene_names': [MISSION06_GENE_NAMES.get(g, GENE_NAMES.get(g, '')) for g in knocked_out],
        'growth': float(growth_value) if growth_value is not None else None,
        'production': float(production_value) if production_value is not None else None,
        'oxygen_uptake': float(oxygen_uptake) if oxygen_uptake is not None else None,
        'issues': list(issues),
        'valid': current_valid,
    }

    if current_valid and is_baseline:
        baseline = {
            'growth': float(growth_value),
            'production': float(production_value),
            'oxygen_uptake': float(oxygen_uptake),
        }
        baseline_growth = float(growth_value)
        current_attempt = _mission06_normalise_attempt(current_attempt, baseline_growth)
        current_recorded = True
        current_type = 'baseline'
        # Re-evaluate saved designs against the freshly recorded reference.
        design_best = {
            key: _mission06_normalise_attempt(attempt, baseline_growth)
            for key, attempt in design_best.items()
        }
        history = [
            _mission06_normalise_attempt(attempt, baseline_growth)
            for attempt in history
        ][-MISSION06_HISTORY_LIMIT:]
    elif current_valid and is_design:
        current_attempt = _mission06_normalise_attempt(current_attempt, baseline_growth)
        design_key = _mission06_design_key(knocked_out)
        current_attempt['design_key'] = design_key
        previous = design_best.get(design_key)
        if previous is None or float(current_attempt['score']) > float(previous.get('score', 0.0)):
            design_best[design_key] = copy.deepcopy(current_attempt)
        history.append(copy.deepcopy(current_attempt))
        history = history[-MISSION06_HISTORY_LIMIT:]
        current_recorded = True
        current_type = 'design'
    else:
        current_attempt = _mission06_normalise_attempt(current_attempt, baseline_growth)

    best_attempt = _mission06_best_attempt(design_best)
    best_score = float((best_attempt or {}).get('score', 0.0))
    best_win = bool((best_attempt or {}).get('win'))

    data = {
        'mission_id': '06',
        'check_version': 3,
        'mission_title': 'Controlled Multi-Knockout Growth-Production Challenge',
        'method': method_name,
        'required_method': MISSION06_METHOD,
        'selected_objective': selected_objective,
        'growth_objective': MISSION06_GROWTH_OBJECTIVE,
        'product_name': MISSION06_PRODUCT_NAME,
        'production_objective': MISSION06_TARGET_FLUX,
        'candidate_genes': list(MISSION06_CANDIDATE_GENES),
        'candidate_gene_names': dict(MISSION06_GENE_NAMES),
        'maximum_knockouts': MISSION06_MAX_KNOCKOUTS,
        'minimum_growth_ratio': MISSION06_MIN_GROWTH_RATIO,
        'villain_score': MISSION06_VILLAIN_SCORE,
        'score_formula': 'growth x ethanol secretion',
        'baseline': baseline,
        'baseline_recorded': baseline is not None,
        'design_best': design_best,
        'attempt_history': history,
        'best_attempt': best_attempt,
        'best_score': best_score,
        'win': best_win,
        'evidence_ready': best_win,
        'current_run_valid': current_valid,
        'current_run_recorded': current_recorded,
        'current_run_type': current_type,
        'current_attempt': current_attempt,
        'current_issues': issues,
        'selected_production_fluxes': selected_fluxes,
        'environment_default': environment_default,
    }
    save_challenge_score(data)
    return data


def build_mission06_challenge_report_text(report_data=None):
    if report_data is None:
        report_data = load_challenge_score() or {}

    lines = ['Mission 06 Controlled Multi-Knockout Challenge', '']
    baseline = report_data.get('baseline') or {}
    best = report_data.get('best_attempt') or {}
    history = report_data.get('attempt_history') or []

    if not baseline:
        lines.extend([
            'Build a fair strain-design competition in the unchanged default aerobic medium.',
            'Record an all-genes-active reference, then explore one- or two-gene designs using only the highlighted candidates.',
            '',
            f'Villain balance index: {MISSION06_VILLAIN_SCORE:.3f}',
            f'Knockout budget: at most {MISSION06_MAX_KNOCKOUTS}',
            f'Operational growth requirement: at least {MISSION06_MIN_GROWTH_RATIO * 100:.0f}% of the reference',
        ])
    else:
        lines.extend([
            'Controlled setup for recorded designs: unchanged default aerobic medium; FBA biomass objective; ethanol exchange tracked; highlighted genes only; at most two knockouts.',
            '',
            (
                f"Reference: growth {float(baseline.get('growth', 0.0)):.3f}; "
                f"ethanol {float(baseline.get('production', 0.0)):.3f}; "
                f"oxygen uptake {_clean_display_number(baseline.get('oxygen_uptake', 0.0)):.3f}"
            ),
            f'Villain balance index: {MISSION06_VILLAIN_SCORE:.3f}',
        ])

    if report_data.get('current_run_recorded'):
        current = report_data.get('current_attempt') or {}
        if report_data.get('current_run_type') == 'baseline':
            lines.extend(['', 'Latest valid run recorded: all-genes-active aerobic reference.'])
        else:
            genes = ' + '.join(current.get('knocked_out_genes') or []) or 'none'
            lines.extend([
                '',
                (
                    f"Latest valid design: {genes}; growth {float(current.get('growth', 0.0)):.3f} "
                    f"({float(current.get('growth_percent', 0.0)):.1f}% of reference); "
                    f"ethanol {float(current.get('production', 0.0)):.3f}; "
                    f"balance index {float(current.get('score', 0.0)):.3f}."
                ),
            ])
    elif report_data.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report_data.get('current_issues') or [])

    if best:
        genes = ' + '.join(best.get('knocked_out_genes') or [])
        lines.extend([
            '',
            'Best valid design retained:',
            (
                f"- Knockouts: {genes}\n"
                f"- Growth: {float(best.get('growth', 0.0)):.3f} "
                f"({float(best.get('growth_percent', 0.0)):.1f}% of reference)\n"
                f"- Ethanol: {float(best.get('production', 0.0)):.3f}\n"
                f"- Balance index: {float(best.get('score', 0.0)):.3f}"
            ),
        ])
        lines.append('Challenge status: rival beaten.' if best.get('win') else 'Challenge status: improve the best valid design to beat the rival.')
    elif baseline:
        lines.extend(['', 'No valid knockout design has been recorded yet.'])

    if history:
        lines.extend(['', 'Recent valid design attempts:'])
        for attempt in history[-5:]:
            genes = ' + '.join(attempt.get('knocked_out_genes') or [])
            lines.append(
                f"- {genes}: growth {float(attempt.get('growth', 0.0)):.3f}; "
                f"ethanol {float(attempt.get('production', 0.0)):.3f}; "
                f"index {float(attempt.get('score', 0.0)):.3f}"
            )

    lines.extend([
        '',
        'Interpretation note: growth x ethanol is a competition balance index used by this game, not a standard biological unit or a universal measure of strain quality.',
        'Scores are comparable only because the model, objective, medium, uptake bounds and design budget are fixed. Growth and ethanol are taken from the same visible biomass-optimal FBA solution.',
        f'Designs below {MISSION06_MIN_GROWTH_RATIO * 100:.0f}% of the reference growth are rejected operationally, even if they produce ethanol.',
    ])
    return '\n'.join(lines)



def _simulate_flux_in_biomass_solution(genes, reactions, production_objective, growth_objective):
    simul, constraints = _build_local_constraints(genes, reactions)
    simul.objective = growth_objective
    result = simul.simulate(method='FBA', constraints=constraints)

    growth = _normalise_result(result)
    if growth == 'Status: INFEASIBLE':
        return 0.0, 0.0, 'Status: INFEASIBLE'

    production_flux = _extract_flux(result, production_objective)
    production_value = _as_float_or_none(production_flux)
    if production_value is None:
        return growth, 0.0, f'Could not read {production_objective} flux from the FBA solution.'

    return growth, production_value, None




def is_mission02_unlocked(missions_completed):
    """Mission 02 starts only after Mission 01 is completed."""
    return '01' in (missions_completed or [])


def is_mission03_unlocked(missions_completed):
    """Mission 03 starts only after the environmental sequence is complete."""
    return '02' in (missions_completed or [])


def _mission03_impact_label(growth_ratio):
    if growth_ratio is None:
        return 'baseline missing'
    if growth_ratio <= MISSION03_ESSENTIAL_GROWTH_RATIO:
        return 'no predicted growth (operationally essential)'
    if growth_ratio <= 0.25:
        return 'very strong growth reduction'
    if growth_ratio <= 0.60:
        return 'strong growth reduction'
    if growth_ratio <= 0.90:
        return 'moderate growth reduction'
    if growth_ratio < 0.99:
        return 'small growth reduction'
    return 'no apparent growth effect'


def _mission03_normalise_trials(trials, baseline_growth):
    normalized = copy.deepcopy(trials or {})
    baseline = _as_float_or_none(baseline_growth)
    for gene_id, trial in normalized.items():
        growth = _numeric_result(trial.get('growth'))
        ratio = None
        if baseline is not None and baseline > 0:
            ratio = growth / baseline
        trial['growth'] = round(growth, 6)
        trial['growth_ratio'] = round(ratio, 6) if ratio is not None else None
        trial['growth_percent'] = round(ratio * 100.0, 1) if ratio is not None else None
        trial['impact'] = _mission03_impact_label(ratio)
        trial['operationally_essential'] = (
            ratio is not None and ratio <= MISSION03_ESSENTIAL_GROWTH_RATIO
        )
    return normalized


def _mission03_rank_trials(trials):
    ranked = sorted(
        (
            (gene_id, float(trial.get('growth_ratio')))
            for gene_id, trial in (trials or {}).items()
            if gene_id in MISSION03_CANDIDATE_GENES
            and trial.get('growth_ratio') is not None
        ),
        key=lambda item: item[1],
    )
    essential = [
        gene_id for gene_id, ratio in ranked
        if ratio <= MISSION03_ESSENTIAL_GROWTH_RATIO
    ]
    unique = len(essential) == 1
    return (essential[0] if unique else None), unique, essential, ranked


def _mission03_answer_alias_map():
    aliases = {}
    for gene_id, gene_name in MISSION03_GENE_NAMES.items():
        variants = {
            gene_id,
            gene_name,
            f'{gene_id} {gene_name}',
            f'{gene_id} ({gene_name})',
            f'{gene_id}/{gene_name}',
        }
        for variant in variants:
            key = ''.join(char.lower() for char in str(variant) if char.isalnum())
            if key:
                aliases[key] = gene_id
    return aliases


def normalise_mission03_answer(answer):
    key = ''.join(char.lower() for char in str(answer or '') if char.isalnum())
    return _mission03_answer_alias_map().get(key)


def mission03_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission03_gene_screen_check() or {}
    if not report_data.get('evidence_ready'):
        return False
    return normalise_mission03_answer(answer) == report_data.get('essential_gene')


def _build_mission03_trial_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    existing_report=None,
    objective_error=None,
):
    """Validate and accumulate one controlled Mission 03 baseline/KO run."""
    existing_report = existing_report or {}
    baseline_growth = _as_float_or_none(existing_report.get('baseline_growth'))
    trials = copy.deepcopy(existing_report.get('trials') or {})

    knocked_out = _knocked_out_genes(genes)
    environment_changed = _environment_has_changes(reactions)
    method_correct = method_name == MISSION03_METHOD
    objective_correct = selected_objective == MISSION03_GROWTH_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_available = objective_value is not None
    growth_value = _numeric_result(objective_value)

    is_baseline = len(knocked_out) == 0
    exactly_one_knockout = len(knocked_out) == 1
    selected_gene = knocked_out[0] if exactly_one_knockout else None
    candidate_selected = selected_gene in MISSION03_CANDIDATE_GENES if selected_gene else False

    issues = []
    if objective_error:
        issues.append(objective_error)
    if not method_correct:
        issues.append('Use the same FBA method for the baseline and every knockout trial.')
    if not objective_correct:
        issues.append('Use the biomass objective so the reported value represents predicted growth.')
    if environment_changed:
        issues.append('Restore the unchanged default environment before evaluating gene effects.')
    if not result_available:
        issues.append('The simulation did not provide a numeric biomass-growth result.')
    if is_baseline and result_available and growth_value < MISSION03_MIN_BASELINE_GROWTH:
        issues.append('The reference run must show viable growth before gene effects can be interpreted.')
    if not is_baseline and not exactly_one_knockout:
        issues.append('Isolate one genetic perturbation: use exactly one gene knockout in each trial.')
    if exactly_one_knockout and not candidate_selected:
        issues.append('The knocked-out gene is not one of the Mission 03 candidates.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run_type = 'invalid'

    if current_run_valid and is_baseline:
        baseline_growth = growth_value
        current_run_recorded = True
        current_run_type = 'baseline'
    elif current_run_valid and selected_gene:
        trials[selected_gene] = {
            'gene_id': selected_gene,
            'gene_name': MISSION03_GENE_NAMES.get(selected_gene, GENE_NAMES.get(selected_gene, '')),
            'growth': round(growth_value, 6),
        }
        current_run_recorded = True
        current_run_type = 'candidate'

    trials = _mission03_normalise_trials(trials, baseline_growth)
    missing_candidates = [gene_id for gene_id in MISSION03_CANDIDATE_GENES if gene_id not in trials]
    comparison_complete = baseline_growth is not None and not missing_candidates
    essential_gene, essential_unique, essential_candidates, ranked = _mission03_rank_trials(trials)
    expected_gene_confirmed = essential_gene == MISSION03_EXPECTED_ESSENTIAL_GENE
    evidence_ready = comparison_complete and essential_unique and expected_gene_confirmed

    data = {
        'mission_id': '03',
        'check_version': 2,
        'method': method_name,
        'required_method': MISSION03_METHOD,
        'selected_objective': selected_objective,
        'growth_objective': MISSION03_GROWTH_OBJECTIVE,
        'baseline_growth': round(baseline_growth, 6) if baseline_growth is not None else None,
        'baseline_recorded': baseline_growth is not None,
        'candidate_genes': list(MISSION03_CANDIDATE_GENES),
        'candidate_gene_names': dict(MISSION03_GENE_NAMES),
        'trials': trials,
        'valid_trial_count': len(trials),
        'required_trial_count': len(MISSION03_CANDIDATE_GENES),
        'missing_candidates': missing_candidates,
        'comparison_complete': comparison_complete,
        'essential_ratio_threshold': MISSION03_ESSENTIAL_GROWTH_RATIO,
        'essential_gene': essential_gene,
        'essential_candidates': essential_candidates,
        'essential_unique': essential_unique,
        'expected_essential_gene': MISSION03_EXPECTED_ESSENTIAL_GENE,
        'expected_gene_confirmed': expected_gene_confirmed,
        'ranked_candidates': ranked,
        'evidence_ready': evidence_ready,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': current_run_type,
        'current_knocked_out_genes': knocked_out,
        'current_selected_gene': selected_gene,
        'current_growth': round(growth_value, 6) if result_available else None,
        'current_issues': issues,
    }
    save_mission03_gene_screen_check(data)
    return data


def run_mission03_gene_trial_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    objective_error = None
    try:
        objective_result = simulation_results[1] if simulation_results is not None else None
    except Exception:
        objective_error = 'Could not read the current simulation result.'

    return _build_mission03_trial_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        existing_report=load_mission03_gene_screen_check(),
        objective_error=objective_error,
    )


def build_mission03_evidence_report_text(report_data=None):
    if report_data is None:
        report_data = load_mission03_gene_screen_check() or {}

    lines = [
        'Mission 03 Gene-Knockout Evidence',
        '',
    ]

    baseline = report_data.get('baseline_growth')
    trials = report_data.get('trials') or {}
    count = report_data.get('valid_trial_count', len(trials))
    required = report_data.get('required_trial_count', len(MISSION03_CANDIDATE_GENES))

    if baseline is None and not trials:
        lines.extend([
            'Build a controlled gene-essentiality comparison.',
            'Establish a viable reference and isolate the effect of each candidate perturbation.',
            '',
            f'Candidate knockout trials recorded: 0/{required}',
        ])
    else:
        lines.append(
            'Controlled setup confirmed for recorded evidence: unchanged default environment; '
            'FBA biomass objective; at most one candidate knockout per trial.'
        )
        lines.append('')
        lines.append(
            f"Baseline growth: {baseline:.3f}" if baseline is not None
            else 'Baseline growth: not recorded yet'
        )
        lines.append(f'Candidate knockout trials recorded: {count}/{required}')
        lines.append('')
        lines.append('Candidate screen:')
        for gene_id in MISSION03_CANDIDATE_GENES:
            gene_name = MISSION03_GENE_NAMES.get(gene_id, '')
            trial = trials.get(gene_id)
            if not trial:
                lines.append(f'- {gene_id} ({gene_name}): pending')
                continue
            percent = trial.get('growth_percent')
            percent_text = f'{percent:.1f}% of baseline' if percent is not None else 'baseline missing'
            lines.append(
                f"- {gene_id} ({gene_name}): growth {float(trial.get('growth', 0.0)):.3f}; "
                f"{percent_text}; {trial.get('impact', '')}"
            )

    if report_data.get('current_run_recorded'):
        lines.append('')
        if report_data.get('current_run_type') == 'baseline':
            lines.append('Latest valid run recorded: reference with all genes active.')
        else:
            gene_id = report_data.get('current_selected_gene')
            gene_name = MISSION03_GENE_NAMES.get(gene_id, '')
            lines.append(
                f"Latest valid trial recorded: {gene_id} ({gene_name}), "
                f"growth {float(report_data.get('current_growth', 0.0)):.3f}."
            )
    elif report_data.get('current_issues'):
        lines.append('')
        lines.append('Latest run was not recorded:')
        lines.extend(f'- {issue}' for issue in report_data.get('current_issues') or [])

    lines.append('')
    if report_data.get('evidence_ready'):
        lines.append(
            'Evidence complete. Identify the candidate whose knockout falls at or below '
            f"{MISSION03_ESSENTIAL_GROWTH_RATIO * 100:.0f}% of baseline growth and submit it to Dr. Silva."
        )
    else:
        missing = report_data.get('missing_candidates') or []
        if baseline is None:
            lines.append('Evidence incomplete: a viable all-genes-active reference is still required.')
        if missing:
            lines.append('Missing candidate trials: ' + ', '.join(missing))

    lines.extend([
        '',
        'Interpretation note: essentiality here is conditional on this model, objective and medium.',
        'No apparent growth effect can reflect GPR redundancy or a pathway that is not growth-limiting in this context; it does not prove that the gene has no biological role.',
        f"The {MISSION03_ESSENTIAL_GROWTH_RATIO * 100:.0f}% threshold is an operational mission criterion, not a universal biological definition.",
    ])
    return '\n'.join(lines)

def is_mission07_unlocked(missions_completed):
    """Mission 07 starts only after Dr. Carter's Mission 06."""
    return '06' in (missions_completed or [])


def _mission07_target_flux(production_fluxes):
    """Return ethanol secretion from the visible solution using raw precision."""
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return None
    for item in production_fluxes.get('items') or []:
        if item.get('reaction_id') != MISSION07_TARGET_FLUX:
            continue
        if item.get('error'):
            return None
        raw = item.get('raw_flux', item.get('production_flux'))
        value = _as_float_or_none(raw)
        return max(value, 0.0) if value is not None else None
    return None


def _mission07_biomass_flux(production_fluxes, selected_objective, objective_result):
    """Read biomass from the same visible solution, never from a hidden run."""
    if isinstance(production_fluxes, dict):
        value = _as_float_or_none(production_fluxes.get('biomass_raw'))
        if value is not None:
            return max(value, 0.0)
    if selected_objective == MISSION07_BIOMASS_OBJECTIVE:
        value = _as_float_or_none(objective_result)
        return max(value, 0.0) if value is not None else None
    return None


def _mission07_oxygen_uptake(medium_fluxes):
    if not isinstance(medium_fluxes, dict) or medium_fluxes.get('error'):
        return None
    for item in medium_fluxes.get('items') or []:
        if item.get('reaction_id') != MISSION07_OXYGEN_REACTION:
            continue
        if item.get('error'):
            return None
        value = _as_float_or_none(item.get('uptake_flux'))
        return max(value, 0.0) if value is not None else None
    return None


def _build_mission07_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
):
    """Validate and accumulate one controlled Mission 07 objective run."""
    if not isinstance(existing_report, dict):
        existing_report = {}
    elif existing_report and (
        existing_report.get('mission_id') != '07'
        or existing_report.get('check_version') != 3
    ):
        # Discard the legacy single-objective format. It could be completed by
        # selecting EX_etoh_e once and did not retain a controlled comparison.
        existing_report = {}
    existing_report = existing_report or {}

    reference_run = copy.deepcopy(existing_report.get('reference_run'))
    target_run = copy.deepcopy(existing_report.get('target_run'))

    knocked_out_genes = _knocked_out_genes(genes)
    environment_changed = _environment_has_changes(reactions)
    selected_fluxes = _read_selected_production_fluxes()
    tracking_ready = MISSION07_TARGET_FLUX in selected_fluxes
    method_correct = method_name == MISSION07_METHOD
    objective_supported = selected_objective in (
        MISSION07_BIOMASS_OBJECTIVE,
        MISSION07_TARGET_OBJECTIVE,
    )

    objective_value = _as_float_or_none(objective_result)
    result_available = objective_value is not None
    ethanol_value = _mission07_target_flux(production_fluxes)
    ethanol_available = ethanol_value is not None
    biomass_value = _mission07_biomass_flux(
        production_fluxes,
        selected_objective,
        objective_result,
    )
    biomass_available = biomass_value is not None
    oxygen_uptake = _mission07_oxygen_uptake(medium_fluxes)
    oxygen_available = oxygen_uptake is not None

    issues = []
    if objective_error:
        issues.append(objective_error)
    if not method_correct:
        issues.append('Use FBA in both objective-comparison runs so the objective is the only modelling variable that changes.')
    if not objective_supported:
        issues.append(
            f'Compare only {MISSION07_BIOMASS_OBJECTIVE} and {MISSION07_TARGET_OBJECTIVE} in Mission 07.'
        )
    if environment_changed:
        issues.append('Restore the unchanged default medium before recording Mission 07 evidence.')
    if knocked_out_genes:
        issues.append('Keep all genes active: changing the objective is not a genetic intervention.')
    if not tracking_ready:
        issues.append(f'Track {MISSION07_TARGET_FLUX} in Production Flux for both Mission 07 runs.')
    if not result_available:
        issues.append('The visible simulation did not provide a numeric objective value.')
    if not ethanol_available:
        issues.append(f'The visible simulation did not provide a numeric {MISSION07_TARGET_FLUX} secretion flux.')
    if not biomass_available:
        issues.append(
            f'The visible simulation did not provide the {MISSION07_BIOMASS_OBJECTIVE} flux needed to interpret predicted growth.'
        )
    if not oxygen_available:
        issues.append(f'The Exchange Flux Report did not provide {MISSION07_OXYGEN_REACTION} uptake evidence.')

    if selected_objective == MISSION07_BIOMASS_OBJECTIVE:
        if biomass_available and biomass_value < MISSION07_MIN_REFERENCE_GROWTH:
            issues.append('The biomass-objective reference must show positive predicted growth.')
        if ethanol_available and ethanol_value > MISSION07_MAX_REFERENCE_ETHANOL:
            issues.append('The biomass-optimal reference should not secrete measurable ethanol in this controlled medium.')
        if oxygen_available and oxygen_uptake <= MISSION07_FLUX_TOLERANCE:
            issues.append('The default biomass-objective reference should show aerobic oxygen uptake.')
    elif selected_objective == MISSION07_TARGET_OBJECTIVE:
        if ethanol_available and ethanol_value < MISSION07_MIN_TARGET_ETHANOL:
            issues.append('The ethanol-objective run must show substantial ethanol secretion.')
        if biomass_available and biomass_value > MISSION07_MAX_TARGET_GROWTH:
            issues.append('The direct ethanol optimum should show no predicted growth under this controlled setup.')
        if oxygen_available and oxygen_uptake > MISSION07_FLUX_TOLERANCE:
            issues.append('The direct ethanol optimum should show zero oxygen uptake in this controlled setup.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run_type = 'invalid'

    run_data = None
    if current_run_valid:
        run_data = {
            'method': method_name,
            'objective': selected_objective,
            'objective_value': round(float(objective_value), 6),
            'biomass_flux': round(float(biomass_value), 6),
            'ethanol_flux': round(float(ethanol_value), 6),
            'oxygen_uptake': round(float(oxygen_uptake), 6),
            'knocked_out_genes': [],
            'environment_changed': False,
            'tracked_fluxes': list(selected_fluxes),
        }
        if selected_objective == MISSION07_BIOMASS_OBJECTIVE:
            reference_run = run_data
            current_run_type = 'reference'
        else:
            target_run = run_data
            current_run_type = 'target'
        current_run_recorded = True

    evidence_ready = bool(reference_run and target_run)

    data = {
        'mission_id': '07',
        'check_version': 3,
        'mission_title': 'Controlled Objective Comparison',
        'required_method': MISSION07_METHOD,
        'default_objective': MISSION07_BIOMASS_OBJECTIVE,
        'biomass_objective': MISSION07_BIOMASS_OBJECTIVE,
        'target_product': MISSION07_TARGET_PRODUCT,
        'target_objective': MISSION07_TARGET_OBJECTIVE,
        'target_flux': MISSION07_TARGET_FLUX,
        'oxygen_reaction': MISSION07_OXYGEN_REACTION,
        'reference_run': reference_run,
        'target_run': target_run,
        'reference_recorded': bool(reference_run),
        'target_recorded': bool(target_run),
        'evidence_ready': evidence_ready,
        'ready_to_deliver': evidence_ready,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': current_run_type,
        'current_method': method_name,
        'current_objective': selected_objective,
        'current_objective_value': round(float(objective_value), 6) if result_available else None,
        'current_biomass_flux': round(float(biomass_value), 6) if biomass_available else None,
        'current_ethanol_flux': round(float(ethanol_value), 6) if ethanol_available else None,
        'current_oxygen_uptake': round(float(oxygen_uptake), 6) if oxygen_available else None,
        'current_knocked_out_genes': knocked_out_genes,
        'current_environment_changed': environment_changed,
        'current_issues': issues,
        'selected_production_fluxes': selected_fluxes,
    }
    save_mission07_objective_check(data)
    return data


def run_mission07_objective_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible simulation before recording Mission 07 evidence.'
    except Exception:
        objective_error = 'Could not read the current visible simulation result.'

    return _build_mission07_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission07_objective_check(),
        objective_error=objective_error,
    )


def build_mission07_objective_comparison_report_text(report_data=None):
    if report_data is None:
        report_data = load_mission07_objective_check() or {}

    lines = ['Mission 07 Controlled Objective Comparison', '']
    reference = report_data.get('reference_run')
    target = report_data.get('target_run')

    if not reference and not target:
        lines.extend([
            'Build a controlled comparison in which the strain, medium and FBA method remain unchanged.',
            'Record one biomass-objective run and one ethanol-objective run while tracking ethanol in both.',
        ])
    else:
        lines.extend([
            'Controlled setup for recorded evidence: FBA in both runs; unchanged default medium; all genes active; ethanol exchange tracked.',
            '',
            'Biomass-objective run:',
        ])
        if reference:
            lines.extend([
                f"- Biomass flux: {float(reference.get('biomass_flux', 0.0)):.3f}",
                f"- Ethanol secretion: {float(reference.get('ethanol_flux', 0.0)):.3f}",
                f"- Oxygen uptake: {_clean_display_number(reference.get('oxygen_uptake', 0.0)):.3f}",
            ])
        else:
            lines.append('- Not recorded yet')

        lines.extend(['', 'Ethanol-objective run:'])
        if target:
            lines.extend([
                f"- Biomass flux: {float(target.get('biomass_flux', 0.0)):.3f}",
                f"- Ethanol secretion: {float(target.get('ethanol_flux', 0.0)):.3f}",
                f"- Oxygen uptake: {_clean_display_number(target.get('oxygen_uptake', 0.0)):.3f}",
            ])
        else:
            lines.append('- Not recorded yet')

    if report_data.get('current_run_recorded'):
        lines.append('')
        if report_data.get('current_run_type') == 'reference':
            lines.append('Latest valid run recorded: biomass-objective reference.')
        else:
            lines.append('Latest valid run recorded: direct ethanol-objective solution.')
    elif report_data.get('current_issues'):
        lines.append('')
        lines.append('Latest run was not recorded:')
        lines.extend(f'- {issue}' for issue in report_data.get('current_issues') or [])

    lines.append('')
    if report_data.get('evidence_ready'):
        lines.append('Evidence complete. Return to Dr. Nova and deliver the controlled objective comparison.')
    else:
        missing = []
        if not reference:
            missing.append('biomass-objective run')
        if not target:
            missing.append('ethanol-objective run')
        if missing:
            lines.append('Evidence incomplete. Missing: ' + ', '.join(missing) + '.')

    lines.extend([
        '',
        'Interpretation note: changing the objective did not alter the strain or the medium; it changed the mathematical question asked of the same feasible space.',
        'The two objective values are fluxes of different reactions and must not be subtracted or ranked as though they were the same quantity.',
        'Direct ethanol maximisation gives the theoretical maximum predicted by this model and these bounds, but the corresponding solution has no predicted growth.',
    ])
    return '\n'.join(lines)


def is_mission08_unlocked(missions_completed):
    """Mission 08 starts only after the controlled Mission 07 comparison."""
    return '07' in (missions_completed or [])


def _mission08_target_flux(production_fluxes):
    """Return D-lactate secretion from the current visible solution."""
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return None
    for item in production_fluxes.get('items') or []:
        if item.get('reaction_id') != MISSION08_TARGET_FLUX:
            continue
        if item.get('error'):
            return None
        raw = item.get('raw_flux', item.get('production_flux'))
        value = _as_float_or_none(raw)
        return max(value, 0.0) if value is not None else None
    return None


def _mission08_biomass_flux(production_fluxes):
    """Read biomass from the same visible solution, never from a hidden run."""
    if not isinstance(production_fluxes, dict):
        return None
    value = _as_float_or_none(production_fluxes.get('biomass_raw'))
    return max(value, 0.0) if value is not None else None


def _mission08_oxygen_uptake(medium_fluxes):
    """Return non-negative oxygen-uptake magnitude from the visible solution."""
    if not isinstance(medium_fluxes, dict) or medium_fluxes.get('error'):
        return None
    for item in medium_fluxes.get('items') or []:
        if item.get('reaction_id') != MISSION08_OXYGEN_REACTION:
            continue
        if item.get('error'):
            return None
        value = _as_float_or_none(item.get('uptake_flux'))
        return max(value, 0.0) if value is not None else None
    return None


def _build_mission08_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
):
    """Validate and accumulate one controlled Mission 08 constraint run."""
    if not isinstance(existing_report, dict):
        existing_report = {}
    elif existing_report and (
        existing_report.get('mission_id') != '08'
        or existing_report.get('check_version') != 4
    ):
        # Discard the legacy single-run format.  It treated closing oxygen as
        # causal even though the direct D-lactate optimum already used none.
        existing_report = {}
    existing_report = existing_report or {}

    default_run = copy.deepcopy(existing_report.get('default_run'))
    constrained_run = copy.deepcopy(existing_report.get('constrained_run'))

    knocked_out_genes = _knocked_out_genes(genes)
    environment_type, oxygen_lower_bound_closed, unexpected_changes = (
        _mission08_environment_status(reactions)
    )
    selected_fluxes = _read_selected_production_fluxes()
    tracking_ready = MISSION08_TARGET_FLUX in selected_fluxes
    method_correct = method_name == MISSION08_METHOD
    objective_correct = selected_objective == MISSION08_TARGET_OBJECTIVE

    objective_value = _as_float_or_none(objective_result)
    result_available = objective_value is not None
    target_value = _mission08_target_flux(production_fluxes)
    target_available = target_value is not None
    biomass_value = _mission08_biomass_flux(production_fluxes)
    biomass_available = biomass_value is not None
    oxygen_uptake = _mission08_oxygen_uptake(medium_fluxes)
    oxygen_available = oxygen_uptake is not None

    issues = []
    if objective_error:
        issues.append(objective_error)
    if not method_correct:
        issues.append('Use FBA in both constraint-comparison runs so oxygen availability is the only modelling variable that changes.')
    if not objective_correct:
        issues.append(f'Use {MISSION08_TARGET_OBJECTIVE} as the objective in both Mission 08 runs.')
    if unexpected_changes:
        issues.append('Keep every environmental bound unchanged except the oxygen-exchange lower bound in the constrained run.')
    if knocked_out_genes:
        issues.append('Keep all genes active: this mission compares an environmental constraint, not a genetic intervention.')
    if not tracking_ready:
        issues.append(f'Track {MISSION08_TARGET_FLUX} in Production Flux for both Mission 08 runs.')
    if not result_available:
        issues.append('The visible simulation did not provide a numeric objective value.')
    if not target_available:
        issues.append(f'The visible simulation did not provide a numeric {MISSION08_TARGET_FLUX} secretion flux.')
    if not biomass_available:
        issues.append(f'The visible simulation did not provide the {MISSION08_BIOMASS_OBJECTIVE} flux needed to interpret predicted growth.')
    if not oxygen_available:
        issues.append(f'The Exchange Flux Report did not provide oxygen-uptake evidence for {MISSION08_OXYGEN_REACTION}.')

    if result_available and target_available and abs(objective_value - target_value) > MISSION08_OBJECTIVE_MATCH_TOLERANCE:
        issues.append('The displayed D-lactate objective value does not match the D-lactate flux from the same visible solution.')
    if target_available and target_value < MISSION08_MIN_TARGET_FLUX:
        issues.append('The direct D-lactate objective must show substantial D-lactate secretion.')
    if biomass_available and biomass_value > MISSION08_MAX_GROWTH:
        issues.append('The direct D-lactate optimum should show no predicted growth in this controlled comparison.')
    if oxygen_available and oxygen_uptake > MISSION08_MAX_OXYGEN_UPTAKE:
        if environment_type == 'default':
            issues.append('The default-medium D-lactate optimum should already show zero oxygen uptake before the constraint is imposed.')
        else:
            issues.append('The oxygen-constrained run must show zero oxygen uptake.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run_type = 'invalid'

    if current_run_valid:
        run_data = {
            'method': method_name,
            'objective': selected_objective,
            'objective_value': round(float(objective_value), 6),
            'd_lactate_flux': round(float(target_value), 6),
            'biomass_flux': round(float(biomass_value), 6),
            'oxygen_uptake': round(float(oxygen_uptake), 6),
            'environment_type': environment_type,
            'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
            'knocked_out_genes': [],
            'tracked_fluxes': list(selected_fluxes),
        }
        if environment_type == 'default':
            default_run = run_data
            current_run_type = 'default'
        else:
            constrained_run = run_data
            current_run_type = 'constrained'
        current_run_recorded = True

    both_runs_recorded = bool(default_run and constrained_run)
    fluxes_equivalent = False
    optimum_unchanged = False
    if both_runs_recorded:
        fluxes_equivalent = all([
            abs(float(default_run.get('d_lactate_flux', 0.0)) - float(constrained_run.get('d_lactate_flux', 0.0))) <= MISSION08_EQUIVALENCE_TOLERANCE,
            abs(float(default_run.get('biomass_flux', 0.0)) - float(constrained_run.get('biomass_flux', 0.0))) <= MISSION08_EQUIVALENCE_TOLERANCE,
            abs(float(default_run.get('oxygen_uptake', 0.0)) - float(constrained_run.get('oxygen_uptake', 0.0))) <= MISSION08_EQUIVALENCE_TOLERANCE,
        ])
        optimum_unchanged = (
            fluxes_equivalent
            and float(default_run.get('oxygen_uptake', 0.0)) <= MISSION08_MAX_OXYGEN_UPTAKE
        )

    evidence_ready = bool(both_runs_recorded and optimum_unchanged)

    data = {
        'mission_id': '08',
        'check_version': 4,
        'mission_title': 'Constraint Impact on the Optimal Solution',
        'required_method': MISSION08_METHOD,
        'biomass_objective': MISSION08_BIOMASS_OBJECTIVE,
        'target_product': MISSION08_TARGET_PRODUCT,
        'target_objective': MISSION08_TARGET_OBJECTIVE,
        'target_flux': MISSION08_TARGET_FLUX,
        'oxygen_reaction': MISSION08_OXYGEN_REACTION,
        'default_run': default_run,
        'constrained_run': constrained_run,
        'default_recorded': bool(default_run),
        'constrained_recorded': bool(constrained_run),
        'both_runs_recorded': both_runs_recorded,
        'fluxes_equivalent': fluxes_equivalent,
        'optimum_unchanged': optimum_unchanged,
        'evidence_ready': evidence_ready,
        'ready_to_deliver': evidence_ready,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': current_run_type,
        'current_method': method_name,
        'current_objective': selected_objective,
        'current_objective_value': round(float(objective_value), 6) if result_available else None,
        'current_d_lactate_flux': round(float(target_value), 6) if target_available else None,
        'current_biomass_flux': round(float(biomass_value), 6) if biomass_available else None,
        'current_oxygen_uptake': round(float(oxygen_uptake), 6) if oxygen_available else None,
        'current_environment_type': environment_type,
        'current_oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'current_unexpected_environment_changes': unexpected_changes,
        'current_knocked_out_genes': knocked_out_genes,
        'current_issues': issues,
        'selected_production_fluxes': selected_fluxes,
    }
    save_mission08_constraint_check(data)
    return data


def run_mission08_constraint_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible simulation before recording Mission 08 evidence.'
    except Exception:
        objective_error = 'Could not read the current visible simulation result.'

    return _build_mission08_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission08_constraint_check(),
        objective_error=objective_error,
    )


def build_mission08_constraint_comparison_report_text(report_data=None):
    if report_data is None:
        report_data = load_mission08_constraint_check() or {}

    lines = ['Mission 08 Constraint Impact on the Optimal Solution', '']
    default_run = report_data.get('default_run')
    constrained_run = report_data.get('constrained_run')

    if not default_run and not constrained_run:
        lines.extend([
            'Test whether removing oxygen availability changes the theoretical maximum predicted for D-lactate.',
            'Keep the strain, objective and method controlled, and compare the visible flux evidence before and after the environmental constraint.',
        ])
    else:
        lines.extend([
            'Controlled setup for recorded evidence: FBA and EX_lac__D_e objective in both runs; all genes active; D-lactate exchange tracked; only oxygen availability differs.',
            '',
            'Default-medium run:',
        ])
        if default_run:
            lines.extend([
                f"- D-lactate secretion: {float(default_run.get('d_lactate_flux', 0.0)):.3f}",
                f"- Biomass flux: {float(default_run.get('biomass_flux', 0.0)):.3f}",
                f"- Oxygen uptake: {_clean_display_number(default_run.get('oxygen_uptake', 0.0)):.3f}",
            ])
        else:
            lines.append('- Not recorded yet')

        lines.extend(['', 'Oxygen-constrained run:'])
        if constrained_run:
            lines.extend([
                f"- D-lactate secretion: {float(constrained_run.get('d_lactate_flux', 0.0)):.3f}",
                f"- Biomass flux: {float(constrained_run.get('biomass_flux', 0.0)):.3f}",
                f"- Oxygen uptake: {_clean_display_number(constrained_run.get('oxygen_uptake', 0.0)):.3f}",
            ])
        else:
            lines.append('- Not recorded yet')

    if report_data.get('current_run_recorded'):
        lines.append('')
        if report_data.get('current_run_type') == 'default':
            lines.append('Latest valid run recorded: direct D-lactate optimum in the default medium.')
        else:
            lines.append('Latest valid run recorded: direct D-lactate optimum with oxygen uptake disabled.')
    elif report_data.get('current_issues'):
        lines.append('')
        lines.append('Latest run was not recorded:')
        lines.extend(f'- {issue}' for issue in report_data.get('current_issues') or [])

    lines.append('')
    if report_data.get('evidence_ready'):
        lines.extend([
            'Evidence complete. Closing oxygen did not change the direct D-lactate optimum.',
            'Return to Dr. Nova and deliver the controlled constraint comparison.',
        ])
    else:
        missing = []
        if not default_run:
            missing.append('default-medium run')
        if not constrained_run:
            missing.append('oxygen-constrained run')
        if missing:
            lines.append('Evidence incomplete. Missing: ' + ', '.join(missing) + '.')
        elif default_run and constrained_run:
            lines.append('Both runs are recorded, but the flux profiles are not equivalent within the mission tolerance. Repeat the controlled comparison.')

    if report_data.get('evidence_ready'):
        lines.extend([
            '',
            'Interpretation note: closing oxygen did not increase the theoretical D-lactate maximum in this comparison.',
            'The default-medium optimum already used zero oxygen. In the constrained run, the oxygen lower bound is satisfied at equality, but adding that bound did not change the optimum.',
            'A constraint changes an optimum only when it excludes or limits solutions that the previous optimum could use; its effect therefore depends on the objective and active flux state.',
            'Both direct D-lactate optima have no predicted growth. They describe a theoretical product maximum under this model and these bounds, not a viable production strain.',
        ])
    else:
        lines.extend([
            '',
            'Interpretation guidance: do not decide whether closing oxygen changes the optimum until both controlled runs have been recorded and their visible flux profiles compared.',
            'Direct D-lactate maximisation describes a theoretical product objective. Inspect the biomass flux in each solution before drawing conclusions about viability.',
        ])
    return '\n'.join(lines)



def is_mission09_unlocked(missions_completed):
    """Mission 09 starts only after the Mission 08 constraint comparison."""
    return '08' in (missions_completed or [])


def _mission09_target_flux(production_fluxes):
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return None
    for item in production_fluxes.get('items') or []:
        if item.get('reaction_id') != MISSION09_TARGET_FLUX or item.get('error'):
            continue
        value = _as_float_or_none(item.get('raw_flux', item.get('production_flux')))
        return max(value, 0.0) if value is not None else None
    return None


def _mission09_growth_value(objective_result, production_fluxes):
    if isinstance(production_fluxes, dict):
        raw = _as_float_or_none(production_fluxes.get('objective_raw'))
        if raw is not None:
            return max(raw, 0.0)
        raw = _as_float_or_none(production_fluxes.get('biomass_raw'))
        if raw is not None:
            return max(raw, 0.0)
    value = _as_float_or_none(objective_result)
    return max(value, 0.0) if value is not None else None


def _mission09_medium_evidence(medium_fluxes):
    _raw, uptake, _secretion = _medium_flux_maps(medium_fluxes)
    values = {}
    for reaction_id in (
        MISSION09_BLOCKED_CARBON_SOURCE,
        MISSION09_REPLACEMENT_CARBON_SOURCE,
        MISSION09_OXYGEN_REACTION,
    ):
        values[reaction_id] = _as_float_or_none(uptake.get(reaction_id)) if reaction_id in uptake else None
    return values


def _mission09_assessment(growth_ratio, production_change):
    if growth_ratio is None or production_change is None:
        return 'awaiting reference comparison'
    if growth_ratio < MISSION09_MIN_VIABLE_GROWTH_RATIO:
        if production_change >= MISSION09_MIN_PRODUCTION_INCREASE:
            return 'formate increases, but growth retention is below the mission criterion'
        return 'growth retention is below the mission criterion'
    if production_change < MISSION09_MIN_PRODUCTION_INCREASE:
        return 'growth retained, but no meaningful formate increase'
    return 'eligible integrated design'


def _mission09_normalise_trials(trials, baseline_growth, baseline_production):
    normalized = copy.deepcopy(trials or {})
    baseline_growth_value = _as_float_or_none(baseline_growth)
    baseline_production_value = _as_float_or_none(baseline_production)
    for trial in normalized.values():
        growth = _numeric_result(trial.get('growth'))
        production = _numeric_result(trial.get('production'))
        growth_ratio = None
        production_change = None
        if baseline_growth_value is not None and baseline_growth_value > 0:
            growth_ratio = growth / baseline_growth_value
        if baseline_production_value is not None:
            production_change = production - baseline_production_value
        viable = growth_ratio is not None and growth_ratio >= MISSION09_MIN_VIABLE_GROWTH_RATIO
        production_improved = production_change is not None and production_change >= MISSION09_MIN_PRODUCTION_INCREASE
        trial.update({
            'growth': round(growth, 6),
            'production': round(production, 6),
            'growth_ratio': round(growth_ratio, 6) if growth_ratio is not None else None,
            'growth_percent': round(growth_ratio * 100.0, 1) if growth_ratio is not None else None,
            'production_change': round(production_change, 6) if production_change is not None else None,
            'viable': viable,
            'production_improved': production_improved,
            'eligible_design': viable and production_improved,
            'assessment': _mission09_assessment(growth_ratio, production_change),
        })
    return normalized


def _mission09_rank_trials(trials):
    eligible = [
        (gene_id, trial)
        for gene_id, trial in (trials or {}).items()
        if gene_id in MISSION09_CANDIDATE_GENES and trial.get('eligible_design')
    ]
    eligible.sort(
        key=lambda item: (
            float(item[1].get('production', 0.0)),
            float(item[1].get('growth_ratio', 0.0) or 0.0),
        ),
        reverse=True,
    )
    if not eligible:
        return None, False, [], []
    best_production = float(eligible[0][1].get('production', 0.0))
    tied = [
        gene_id for gene_id, trial in eligible
        if abs(float(trial.get('production', 0.0)) - best_production) <= MISSION09_RANK_TOLERANCE
    ]
    winner = tied[0] if len(tied) == 1 else None
    ranked = [(gene_id, float(trial.get('production', 0.0))) for gene_id, trial in eligible]
    return winner, len(tied) == 1, tied, ranked


def _prepare_mission09_report(report_data):
    """Return current Mission 09 evidence, migrating compatible version-3 runs.

    Version 3 used the same controlled L-malate experiment but included
    b0720/gltA. Its baseline and the three still-valid candidate trials remain
    scientifically usable; only the removed b0720 trial is discarded.
    """
    if not isinstance(report_data, dict) or report_data.get('mission_id') != '09':
        return {}
    version = report_data.get('check_version')
    if version == MISSION09_CHECK_VERSION:
        return copy.deepcopy(report_data)
    if version != 3:
        return {}

    baseline = copy.deepcopy(report_data.get('baseline'))
    old_trials = report_data.get('trials') or {}
    trials = {
        gene_id: copy.deepcopy(old_trials[gene_id])
        for gene_id in MISSION09_CANDIDATE_GENES
        if gene_id in old_trials and isinstance(old_trials[gene_id], dict)
    }
    missing = [gene_id for gene_id in MISSION09_CANDIDATE_GENES if gene_id not in trials]
    return {
        'mission_id': '09',
        'check_version': MISSION09_CHECK_VERSION,
        'mission_title': 'Integrated Environment-and-Gene Design',
        'baseline': baseline,
        'baseline_recorded': bool(baseline),
        'candidate_genes': list(MISSION09_CANDIDATE_GENES),
        'candidate_gene_names': dict(MISSION09_GENE_NAMES),
        'trials': trials,
        'valid_trial_count': len(trials),
        'required_trial_count': len(MISSION09_CANDIDATE_GENES),
        'missing_candidates': missing,
        'comparison_complete': bool(baseline) and not missing,
        'evidence_ready': False,
        'ready_to_deliver': False,
        'current_run_recorded': False,
        'current_issues': [],
    }


def _build_mission09_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
):
    """Validate and accumulate one visible Mission 09 integrated-design run."""
    existing_report = _prepare_mission09_report(existing_report)

    baseline = copy.deepcopy(existing_report.get('baseline'))
    trials = copy.deepcopy(existing_report.get('trials') or {})
    baseline_growth = _as_float_or_none((baseline or {}).get('growth'))
    baseline_production = _as_float_or_none((baseline or {}).get('production'))

    knocked_out = _knocked_out_genes(genes)
    environment_correct, glucose_closed, malate_open, unexpected_changes = _mission09_environment_status(reactions)
    selected_fluxes = _read_selected_production_fluxes()
    tracking_ready = MISSION09_TARGET_FLUX in selected_fluxes
    method_correct = method_name == MISSION09_METHOD
    objective_correct = selected_objective == MISSION09_GROWTH_OBJECTIVE

    growth_value = _mission09_growth_value(objective_result, production_fluxes)
    production_value = _mission09_target_flux(production_fluxes)
    medium = _mission09_medium_evidence(medium_fluxes)
    glucose_uptake = medium.get(MISSION09_BLOCKED_CARBON_SOURCE)
    malate_uptake = medium.get(MISSION09_REPLACEMENT_CARBON_SOURCE)
    oxygen_uptake = medium.get(MISSION09_OXYGEN_REACTION)

    is_baseline = len(knocked_out) == 0
    exactly_one_knockout = len(knocked_out) == 1
    selected_gene = knocked_out[0] if exactly_one_knockout else None
    candidate_selected = selected_gene in MISSION09_CANDIDATE_GENES if selected_gene else False

    issues = []
    if objective_error:
        issues.append(objective_error)
    if not method_correct:
        issues.append('Use FBA for the L-malate reference and every candidate trial.')
    if not objective_correct:
        issues.append('Use the biomass objective so formate is measured in the same growth-optimal solution.')
    if not environment_correct:
        if not glucose_closed:
            issues.append(f'Make {MISSION09_REPLACEMENT_SOURCE_NAME} replace glucose by closing the lower bound of {MISSION09_BLOCKED_CARBON_SOURCE}.')
        if not malate_open:
            issues.append(f'Provide {MISSION09_REPLACEMENT_SOURCE_NAME} by opening the lower bound of {MISSION09_REPLACEMENT_CARBON_SOURCE}.')
        if unexpected_changes:
            issues.append('Keep every other environmental bound at its model-default state.')
    if not tracking_ready:
        issues.append(f'Track {MISSION09_TARGET_FLUX} in Production Flux for every Mission 09 run.')
    if growth_value is None:
        issues.append('The visible simulation did not provide a numeric biomass-growth flux.')
    if production_value is None:
        issues.append(f'The visible simulation did not provide a numeric {MISSION09_TARGET_FLUX} secretion flux.')
    if glucose_uptake is None:
        issues.append(f'The Exchange Flux Report did not provide {MISSION09_BLOCKED_CARBON_SOURCE} uptake evidence.')
    elif glucose_uptake > MISSION09_FLUX_TOLERANCE:
        issues.append('The controlled L-malate experiment must show zero glucose uptake.')
    if malate_uptake is None:
        issues.append(f'The Exchange Flux Report did not provide {MISSION09_REPLACEMENT_CARBON_SOURCE} uptake evidence.')
    if oxygen_uptake is None:
        issues.append(f'The Exchange Flux Report did not provide oxygen-uptake evidence for {MISSION09_OXYGEN_REACTION}.')

    # Positive malate and oxygen uptake are required in the viable reference.
    # A damaging candidate knockout may legitimately collapse growth and all
    # uptake fluxes; that is an experimental result, not an invalid medium.
    if is_baseline and malate_uptake is not None and malate_uptake <= MISSION09_FLUX_TOLERANCE:
        issues.append('The no-knockout reference must show uptake of the L-malate replacement source.')
    if is_baseline and oxygen_uptake is not None and oxygen_uptake <= MISSION09_FLUX_TOLERANCE:
        issues.append('Keep the L-malate reference aerobic: the visible solution should show oxygen uptake.')
    if is_baseline and growth_value is not None and growth_value < MISSION09_MIN_BASELINE_GROWTH:
        issues.append('The no-knockout L-malate reference must show viable predicted growth.')
    if is_baseline and production_value is not None and production_value > MISSION09_MAX_BASELINE_PRODUCTION:
        issues.append('The no-knockout L-malate reference should show negligible formate secretion.')
    if not is_baseline and not exactly_one_knockout:
        issues.append('Use exactly one candidate knockout in each genetic trial.')
    if exactly_one_knockout and not candidate_selected:
        issues.append('The knocked-out gene is not one of the Mission 09 candidates.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run_type = 'invalid'
    if current_run_valid and is_baseline:
        baseline = {
            'growth': round(float(growth_value), 6),
            'production': round(float(production_value), 6),
            'glucose_uptake': round(float(glucose_uptake), 6),
            'malate_uptake': round(float(malate_uptake), 6),
            'oxygen_uptake': round(float(oxygen_uptake), 6),
        }
        baseline_growth = float(growth_value)
        baseline_production = float(production_value)
        current_run_recorded = True
        current_run_type = 'baseline'
    elif current_run_valid and selected_gene:
        trials[selected_gene] = {
            'gene_id': selected_gene,
            'gene_name': MISSION09_GENE_NAMES.get(selected_gene, GENE_NAMES.get(selected_gene, '')),
            'growth': round(float(growth_value), 6),
            'production': round(float(production_value), 6),
            'glucose_uptake': round(float(glucose_uptake), 6),
            'malate_uptake': round(float(malate_uptake), 6),
            'oxygen_uptake': round(float(oxygen_uptake), 6),
        }
        current_run_recorded = True
        current_run_type = 'candidate'

    trials = _mission09_normalise_trials(trials, baseline_growth, baseline_production)
    missing_candidates = [gene_id for gene_id in MISSION09_CANDIDATE_GENES if gene_id not in trials]
    baseline_recorded = bool(baseline)
    comparison_complete = baseline_recorded and not missing_candidates
    winning_gene, winner_unique, eligible_candidates, ranked_candidates = _mission09_rank_trials(trials)
    evidence_ready = comparison_complete and winner_unique

    data = {
        'mission_id': '09',
        'check_version': MISSION09_CHECK_VERSION,
        'mission_title': 'Integrated Environment-and-Gene Design',
        'required_method': MISSION09_METHOD,
        'growth_objective': MISSION09_GROWTH_OBJECTIVE,
        'target_product': MISSION09_TARGET_PRODUCT,
        'target_flux': MISSION09_TARGET_FLUX,
        'blocked_carbon_source': MISSION09_BLOCKED_CARBON_SOURCE,
        'replacement_carbon_source': MISSION09_REPLACEMENT_CARBON_SOURCE,
        'replacement_source_name': MISSION09_REPLACEMENT_SOURCE_NAME,
        'oxygen_reaction': MISSION09_OXYGEN_REACTION,
        'baseline': baseline,
        'baseline_recorded': baseline_recorded,
        'baseline_growth': round(baseline_growth, 6) if baseline_growth is not None else None,
        'baseline_production': round(baseline_production, 6) if baseline_production is not None else None,
        'candidate_genes': list(MISSION09_CANDIDATE_GENES),
        'candidate_gene_names': dict(MISSION09_GENE_NAMES),
        'trials': trials,
        'valid_trial_count': len(trials),
        'required_trial_count': len(MISSION09_CANDIDATE_GENES),
        'missing_candidates': missing_candidates,
        'comparison_complete': comparison_complete,
        'minimum_viable_growth_ratio': MISSION09_MIN_VIABLE_GROWTH_RATIO,
        'minimum_production_increase': MISSION09_MIN_PRODUCTION_INCREASE,
        'eligible_candidates': eligible_candidates,
        'ranked_candidates': ranked_candidates,
        'winning_gene': winning_gene,
        'winner_unique': winner_unique,
        'expected_winner': MISSION09_EXPECTED_WINNER,
        'expected_winner_confirmed': winning_gene == MISSION09_EXPECTED_WINNER,
        'evidence_ready': evidence_ready,
        'ready_to_deliver': evidence_ready,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': current_run_type,
        'current_method': method_name,
        'current_objective': selected_objective,
        'current_knocked_out_genes': knocked_out,
        'current_selected_gene': selected_gene,
        'current_growth': round(float(growth_value), 6) if growth_value is not None else None,
        'current_production': round(float(production_value), 6) if production_value is not None else None,
        'current_glucose_uptake': round(float(glucose_uptake), 6) if glucose_uptake is not None else None,
        'current_malate_uptake': round(float(malate_uptake), 6) if malate_uptake is not None else None,
        'current_oxygen_uptake': round(float(oxygen_uptake), 6) if oxygen_uptake is not None else None,
        'current_environment_correct': environment_correct,
        'current_unexpected_environment_changes': unexpected_changes,
        'current_issues': issues,
        'selected_production_fluxes': selected_fluxes,
    }
    save_mission09_design_check(data)
    return data


def run_mission09_design_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible simulation before recording Mission 09 evidence.'
    except Exception:
        objective_error = 'Could not read the current visible simulation result.'
    return _build_mission09_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission09_design_check(),
        objective_error=objective_error,
    )


def normalise_mission09_answer(answer):
    value = str(answer or '').strip().lower().replace(' ', '')
    aliases = {}
    for gene_id, gene_name in MISSION09_GENE_NAMES.items():
        aliases[gene_id.lower()] = gene_id
        aliases[gene_name.lower()] = gene_id
        aliases[f'{gene_id.lower()}({gene_name.lower()})'] = gene_id
        aliases[f'{gene_id.lower()}/{gene_name.lower()}'] = gene_id
    return aliases.get(value)


def _mission09_report_is_current(report_data):
    return bool(
        isinstance(report_data, dict)
        and report_data.get('mission_id') == '09'
        and report_data.get('check_version') == MISSION09_CHECK_VERSION
    )


def mission09_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission09_design_check() or {}
    if not _mission09_report_is_current(report_data):
        return False
    return bool(report_data.get('evidence_ready')) and normalise_mission09_answer(answer) == report_data.get('winning_gene')


def build_mission09_evidence_report_text(report_data=None):
    if report_data is None:
        report_data = load_mission09_design_check() or {}
    report_data = _prepare_mission09_report(report_data)
    lines = ['Mission 09 Integrated Environment-and-Gene Evidence', '']
    baseline = report_data.get('baseline')
    trials = report_data.get('trials') or {}
    count = report_data.get('valid_trial_count', len(trials))
    required = report_data.get('required_trial_count', len(MISSION09_CANDIDATE_GENES))
    if not baseline and not trials:
        lines.extend([
            'Build a controlled L-malate strain-design comparison.',
            'First establish a no-knockout reference, then isolate the effect of each highlighted candidate while keeping the objective and medium identical.',
            '',
            f'Candidate knockout trials recorded: 0/{required}',
        ])
    else:
        lines.extend([
            'Controlled setup for recorded evidence: glucose unavailable; L-malate as the replacement carbon source; aerobic medium otherwise unchanged; FBA biomass objective; formate exchange tracked; exactly one candidate knockout per genetic trial.',
            '',
        ])
        if baseline:
            lines.append(
                f"Baseline: growth {float(baseline.get('growth', 0.0)):.3f}; formate {float(baseline.get('production', 0.0)):.3f}; "
                f"L-malate uptake {float(baseline.get('malate_uptake', 0.0)):.3f}; oxygen uptake {float(baseline.get('oxygen_uptake', 0.0)):.3f}."
            )
        else:
            lines.append('Baseline: not recorded yet')
        lines.extend([f'Candidate knockout trials recorded: {count}/{required}', '', 'Candidate screen:'])
        for gene_id in MISSION09_CANDIDATE_GENES:
            name = MISSION09_GENE_NAMES.get(gene_id, '')
            trial = trials.get(gene_id)
            if not trial:
                lines.append(f'- {gene_id} ({name}): pending')
                continue
            percent = trial.get('growth_percent')
            percent_text = f'{float(percent):.1f}% of baseline' if percent is not None else 'baseline missing'
            change = trial.get('production_change')
            change_text = f'{float(change):+.3f}' if change is not None else 'baseline missing'
            lines.append(
                f"- {gene_id} ({name}): growth {float(trial.get('growth', 0.0)):.3f} ({percent_text}); "
                f"formate {float(trial.get('production', 0.0)):.3f} (change {change_text}); {trial.get('assessment', '')}"
            )
    if report_data.get('current_run_recorded'):
        lines.append('')
        if report_data.get('current_run_type') == 'baseline':
            lines.append('Latest valid run recorded: no-knockout aerobic L-malate reference.')
        else:
            gene_id = report_data.get('current_selected_gene')
            lines.append(
                f"Latest valid trial recorded: {gene_id} ({MISSION09_GENE_NAMES.get(gene_id, '')}); "
                f"growth {float(report_data.get('current_growth', 0.0)):.3f}; formate {float(report_data.get('current_production', 0.0)):.3f}."
            )
    elif report_data.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report_data.get('current_issues') or [])
    lines.append('')
    if report_data.get('evidence_ready'):
        lines.append('Evidence complete. Identify the candidate that best balances retained growth with growth-coupled formate secretion and submit its gene id or name to Dr. Nova.')
    else:
        if not baseline:
            lines.append('Evidence incomplete: the no-knockout L-malate reference is still required.')
        missing = report_data.get('missing_candidates') or []
        if missing:
            lines.append('Missing candidate trials: ' + ', '.join(missing))
        elif report_data.get('comparison_complete') and not report_data.get('winner_unique'):
            lines.append('Comparison complete, but the operational criteria do not identify one unique integrated design.')
    lines.extend([
        '',
        'Interpretation note: this mission measures formate secretion in the same biomass-optimal FBA solution used to assess growth. It does not combine values from separate hidden objectives.',
        f'A candidate is operationally viable when it retains at least {MISSION09_MIN_VIABLE_GROWTH_RATIO * 100:.0f}% of the L-malate reference growth and increases formate by at least {MISSION09_MIN_PRODUCTION_INCREASE:.1f}. These are mission criteria, not universal biological definitions.',
        'The result is conditional on this model, L-malate medium, oxygen availability and biomass objective.',
    ])
    return '\n'.join(lines)



def is_mission10_unlocked(missions_completed):
    """Mission 10 starts only after the integrated Mission 09 design."""
    return '09' in (missions_completed or [])


def _mission10_pair_key(pair):
    selected = set(pair or [])
    ordered = [gene_id for gene_id in MISSION10_CANDIDATE_GENES if gene_id in selected]
    if len(ordered) != 2:
        return None
    return '+'.join(ordered)


def _mission10_pair_from_key(pair_key):
    values = str(pair_key or '').split('+')
    return tuple(value for value in values if value)


def _mission10_required_pair_keys():
    return [_mission10_pair_key(pair) for pair in MISSION10_REQUIRED_PAIRS]


def _mission10_growth_value(objective_result, production_fluxes):
    if isinstance(production_fluxes, dict):
        raw = _as_float_or_none(production_fluxes.get('objective_raw'))
        if raw is not None:
            return max(raw, 0.0)
        raw = _as_float_or_none(production_fluxes.get('biomass_raw'))
        if raw is not None:
            return max(raw, 0.0)
    value = _as_float_or_none(objective_result)
    return max(value, 0.0) if value is not None else None


def _mission10_flux_value(production_fluxes, reaction_id):
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return None
    for item in production_fluxes.get('items') or []:
        if item.get('reaction_id') != reaction_id or item.get('error'):
            continue
        value = _as_float_or_none(item.get('raw_flux', item.get('production_flux')))
        return max(value, 0.0) if value is not None else None
    return None


def _mission10_medium_evidence(medium_fluxes):
    _raw, uptake, _secretion = _medium_flux_maps(medium_fluxes)
    return {
        MISSION10_GLUCOSE_REACTION: _as_float_or_none(uptake.get(MISSION10_GLUCOSE_REACTION))
        if MISSION10_GLUCOSE_REACTION in uptake else None,
        MISSION10_OXYGEN_REACTION: _as_float_or_none(uptake.get(MISSION10_OXYGEN_REACTION))
        if MISSION10_OXYGEN_REACTION in uptake else None,
    }


def _mission10_assessment(growth_ratio, ethanol_change, acetate_change):
    if growth_ratio is None or ethanol_change is None:
        return 'awaiting baseline comparison'
    if growth_ratio < MISSION10_MIN_GROWTH_RATIO:
        if ethanol_change >= MISSION10_MIN_ETHANOL_INCREASE:
            return 'ethanol increases, but growth retention is below the mission criterion'
        return 'growth retention is below the mission criterion'
    if ethanol_change < MISSION10_MIN_ETHANOL_INCREASE:
        if abs(ethanol_change) <= MISSION10_FLUX_TOLERANCE:
            return 'no meaningful phenotype improvement from this gene pair'
        return 'growth retained, but ethanol improvement is below the mission criterion'
    if acetate_change is not None and acetate_change < -MISSION10_FLUX_TOLERANCE:
        return 'eligible two-gene redirection design: ethanol increased while acetate decreased'
    return 'eligible two-gene redirection design'


def _mission10_normalise_trials(trials, baseline):
    normalized = copy.deepcopy(trials or {})
    baseline_growth = _as_float_or_none((baseline or {}).get('growth'))
    baseline_ethanol = _as_float_or_none((baseline or {}).get('ethanol'))
    baseline_acetate = _as_float_or_none((baseline or {}).get('acetate'))
    for trial in normalized.values():
        growth = _numeric_result(trial.get('growth'))
        ethanol = _numeric_result(trial.get('ethanol'))
        acetate = _numeric_result(trial.get('acetate'))
        growth_ratio = growth / baseline_growth if baseline_growth is not None and baseline_growth > 0 else None
        ethanol_change = ethanol - baseline_ethanol if baseline_ethanol is not None else None
        acetate_change = acetate - baseline_acetate if baseline_acetate is not None else None
        viable = growth_ratio is not None and growth_ratio >= MISSION10_MIN_GROWTH_RATIO
        ethanol_improved = ethanol_change is not None and ethanol_change >= MISSION10_MIN_ETHANOL_INCREASE
        trial.update({
            'growth': round(growth, 6),
            'ethanol': round(ethanol, 6),
            'acetate': round(acetate, 6),
            'growth_ratio': round(growth_ratio, 6) if growth_ratio is not None else None,
            'growth_percent': round(growth_ratio * 100.0, 1) if growth_ratio is not None else None,
            'ethanol_change': round(ethanol_change, 6) if ethanol_change is not None else None,
            'acetate_change': round(acetate_change, 6) if acetate_change is not None else None,
            'viable': viable,
            'ethanol_improved': ethanol_improved,
            'eligible_design': viable and ethanol_improved,
            'assessment': _mission10_assessment(growth_ratio, ethanol_change, acetate_change),
        })
    return normalized


def _mission10_rank_trials(trials):
    eligible = [
        (pair_key, trial)
        for pair_key, trial in (trials or {}).items()
        if pair_key in _mission10_required_pair_keys() and trial.get('eligible_design')
    ]
    eligible.sort(
        key=lambda item: (
            float(item[1].get('ethanol', 0.0)),
            float(item[1].get('growth_ratio', 0.0) or 0.0),
        ),
        reverse=True,
    )
    if not eligible:
        return None, False, [], []
    best_ethanol = float(eligible[0][1].get('ethanol', 0.0))
    tied = [
        pair_key for pair_key, trial in eligible
        if abs(float(trial.get('ethanol', 0.0)) - best_ethanol) <= MISSION10_RANK_TOLERANCE
    ]
    winner = tied[0] if len(tied) == 1 else None
    ranked = [(pair_key, float(trial.get('ethanol', 0.0))) for pair_key, trial in eligible]
    return winner, len(tied) == 1, tied, ranked


def _prepare_mission10_report(report_data):
    if not isinstance(report_data, dict) or report_data.get('mission_id') != '10':
        return {}
    if report_data.get('check_version') != MISSION10_CHECK_VERSION:
        return {}
    return copy.deepcopy(report_data)


def _build_mission10_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
):
    """Validate and accumulate one visible Mission 10 pair-design run."""
    existing_report = _prepare_mission10_report(existing_report)
    baseline = copy.deepcopy(existing_report.get('baseline'))
    trials = copy.deepcopy(existing_report.get('trials') or {})

    knocked_out = _knocked_out_genes(genes)
    environment_correct, oxygen_closed, unexpected_changes = _mission10_environment_status(reactions)
    selected_fluxes = _read_selected_production_fluxes()
    missing_tracked_fluxes = [
        reaction_id for reaction_id in MISSION10_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    tracking_ready = not missing_tracked_fluxes
    method_correct = method_name == MISSION10_METHOD
    objective_correct = selected_objective == MISSION10_GROWTH_OBJECTIVE

    growth_value = _mission10_growth_value(objective_result, production_fluxes)
    ethanol_value = _mission10_flux_value(production_fluxes, MISSION10_TARGET_FLUX)
    acetate_value = _mission10_flux_value(production_fluxes, MISSION10_COMPETING_FLUX)
    medium = _mission10_medium_evidence(medium_fluxes)
    glucose_uptake = medium.get(MISSION10_GLUCOSE_REACTION)
    oxygen_uptake = medium.get(MISSION10_OXYGEN_REACTION)

    is_baseline = len(knocked_out) == 0
    exactly_two = len(knocked_out) == 2
    only_candidates = exactly_two and all(gene_id in MISSION10_CANDIDATE_GENES for gene_id in knocked_out)
    pair_key = _mission10_pair_key(knocked_out) if only_candidates else None
    pair_required = pair_key in _mission10_required_pair_keys() if pair_key else False

    issues = []
    if objective_error:
        issues.append(objective_error)
    if not method_correct:
        issues.append('Use FBA for the anaerobic reference and every two-gene trial.')
    if not objective_correct:
        issues.append('Use the biomass objective so growth, ethanol and acetate come from the same visible growth-optimal solution.')
    if not environment_correct:
        if not oxygen_closed:
            issues.append(f'Close only the lower bound of {MISSION10_OXYGEN_REACTION} to create the anaerobic comparison medium.')
        if unexpected_changes:
            issues.append('Keep glucose and every other environmental bound at the model-default state.')
    if not tracking_ready:
        issues.append('Track both EX_etoh_e and EX_ac_e in Production Flux for every Mission 10 run.')
    if growth_value is None:
        issues.append('The visible simulation did not provide a numeric biomass-growth flux.')
    if ethanol_value is None:
        issues.append(f'The visible simulation did not provide a numeric {MISSION10_TARGET_FLUX} secretion flux.')
    if acetate_value is None:
        issues.append(f'The visible simulation did not provide a numeric {MISSION10_COMPETING_FLUX} secretion flux.')
    if glucose_uptake is None:
        issues.append(f'The Exchange Flux Report did not provide glucose-uptake evidence for {MISSION10_GLUCOSE_REACTION}.')
    elif glucose_uptake <= MISSION10_FLUX_TOLERANCE:
        issues.append('Keep the default glucose source available: the visible solution must show glucose uptake.')
    if oxygen_uptake is None:
        issues.append(f'The Exchange Flux Report did not provide oxygen-uptake evidence for {MISSION10_OXYGEN_REACTION}.')
    elif oxygen_uptake > MISSION10_FLUX_TOLERANCE:
        issues.append('The anaerobic Mission 10 solution must show zero oxygen uptake.')
    if is_baseline and growth_value is not None and growth_value < MISSION10_MIN_BASELINE_GROWTH:
        issues.append('The no-knockout anaerobic reference must show viable predicted growth.')
    if not is_baseline and not exactly_two:
        issues.append('Use exactly two candidate knockouts in each genetic-pair trial.')
    if exactly_two and not only_candidates:
        issues.append('Both knocked-out genes must belong to the Mission 10 candidate list.')
    if only_candidates and not pair_required:
        issues.append('This gene pair is not one of the controlled Mission 10 comparisons.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run_type = 'invalid'
    if current_run_valid and is_baseline:
        baseline = {
            'growth': round(float(growth_value), 6),
            'ethanol': round(float(ethanol_value), 6),
            'acetate': round(float(acetate_value), 6),
            'glucose_uptake': round(float(glucose_uptake), 6),
            'oxygen_uptake': round(
                0.0 if abs(float(oxygen_uptake)) < DISPLAY_ZERO_TOLERANCE else float(oxygen_uptake),
                6,
            ),
        }
        current_run_recorded = True
        current_run_type = 'baseline'
    elif current_run_valid and pair_key:
        pair = _mission10_pair_from_key(pair_key)
        trials[pair_key] = {
            'pair_key': pair_key,
            'genes': list(pair),
            'gene_names': [MISSION10_GENE_NAMES.get(gene_id, GENE_NAMES.get(gene_id, '')) for gene_id in pair],
            'growth': round(float(growth_value), 6),
            'ethanol': round(float(ethanol_value), 6),
            'acetate': round(float(acetate_value), 6),
            'glucose_uptake': round(float(glucose_uptake), 6),
            'oxygen_uptake': round(float(oxygen_uptake), 6),
        }
        current_run_recorded = True
        current_run_type = 'pair'

    trials = _mission10_normalise_trials(trials, baseline)
    required_pair_keys = _mission10_required_pair_keys()
    missing_pairs = [pair_key for pair_key in required_pair_keys if pair_key not in trials]
    baseline_recorded = bool(baseline)
    comparison_complete = baseline_recorded and not missing_pairs
    winning_pair, winner_unique, eligible_pairs, ranked_pairs = _mission10_rank_trials(trials)
    expected_key = _mission10_pair_key(MISSION10_EXPECTED_WINNING_PAIR)
    evidence_ready = comparison_complete and winner_unique

    data = {
        'mission_id': '10',
        'check_version': MISSION10_CHECK_VERSION,
        'mission_title': 'Two-Gene Redundancy and Flux Redirection',
        'required_method': MISSION10_METHOD,
        'growth_objective': MISSION10_GROWTH_OBJECTIVE,
        'target_product': MISSION10_TARGET_PRODUCT,
        'target_flux': MISSION10_TARGET_FLUX,
        'competing_product': MISSION10_COMPETING_PRODUCT,
        'competing_flux': MISSION10_COMPETING_FLUX,
        'oxygen_reaction': MISSION10_OXYGEN_REACTION,
        'glucose_reaction': MISSION10_GLUCOSE_REACTION,
        'baseline': baseline,
        'baseline_recorded': baseline_recorded,
        'candidate_genes': list(MISSION10_CANDIDATE_GENES),
        'candidate_gene_names': dict(MISSION10_GENE_NAMES),
        'required_pairs': [list(pair) for pair in MISSION10_REQUIRED_PAIRS],
        'required_pair_keys': required_pair_keys,
        'trials': trials,
        'valid_trial_count': len(trials),
        'required_trial_count': len(required_pair_keys),
        'missing_pairs': missing_pairs,
        'comparison_complete': comparison_complete,
        'minimum_growth_ratio': MISSION10_MIN_GROWTH_RATIO,
        'minimum_ethanol_increase': MISSION10_MIN_ETHANOL_INCREASE,
        'eligible_pairs': eligible_pairs,
        'ranked_pairs': ranked_pairs,
        'winning_pair': winning_pair,
        'winner_unique': winner_unique,
        'expected_winning_pair': expected_key,
        'expected_winner_confirmed': winning_pair == expected_key,
        'evidence_ready': evidence_ready,
        'ready_to_deliver': evidence_ready,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': current_run_type,
        'current_method': method_name,
        'current_objective': selected_objective,
        'current_knocked_out_genes': knocked_out,
        'current_pair_key': pair_key,
        'current_growth': round(float(growth_value), 6) if growth_value is not None else None,
        'current_ethanol': round(float(ethanol_value), 6) if ethanol_value is not None else None,
        'current_acetate': round(float(acetate_value), 6) if acetate_value is not None else None,
        'current_glucose_uptake': round(float(glucose_uptake), 6) if glucose_uptake is not None else None,
        'current_oxygen_uptake': (
            round(
                0.0 if abs(float(oxygen_uptake)) < DISPLAY_ZERO_TOLERANCE else float(oxygen_uptake),
                6,
            )
            if oxygen_uptake is not None
            else None
        ),
        'current_environment_correct': environment_correct,
        'current_unexpected_environment_changes': unexpected_changes,
        'current_issues': issues,
        'selected_production_fluxes': selected_fluxes,
        'missing_tracked_fluxes': missing_tracked_fluxes,
    }
    save_mission10_robust_design_check(data)
    return data


def run_mission10_robust_design_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible simulation before recording Mission 10 evidence.'
    except Exception:
        objective_error = 'Could not read the current visible simulation result.'
    return _build_mission10_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission10_robust_design_check(),
        objective_error=objective_error,
    )


def _mission10_report_is_current(report_data):
    return bool(
        isinstance(report_data, dict)
        and report_data.get('mission_id') == '10'
        and report_data.get('check_version') == MISSION10_CHECK_VERSION
    )


def normalise_mission10_answer(answer):
    compact = ''.join(char.lower() for char in str(answer or '') if char.isalnum())
    if not compact:
        return None
    aliases = {}
    for pair in MISSION10_REQUIRED_PAIRS:
        key = _mission10_pair_key(pair)
        first, second = pair
        first_name = MISSION10_GENE_NAMES.get(first, '')
        second_name = MISSION10_GENE_NAMES.get(second, '')
        variants = [
            first + second, second + first,
            first_name + second_name, second_name + first_name,
            first + second_name, second_name + first,
            second + first_name, first_name + second,
        ]
        for variant in variants:
            alias = ''.join(char.lower() for char in variant if char.isalnum())
            if alias:
                aliases[alias] = key
    return aliases.get(compact)


def mission10_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission10_robust_design_check() or {}
    if not _mission10_report_is_current(report_data):
        return False
    return bool(report_data.get('evidence_ready')) and normalise_mission10_answer(answer) == report_data.get('winning_pair')


def _mission10_pair_label(pair_key):
    pair = _mission10_pair_from_key(pair_key)
    return ' + '.join(f"{gene_id} ({MISSION10_GENE_NAMES.get(gene_id, '')})" for gene_id in pair)


def build_mission10_evidence_report_text(report_data=None):
    if report_data is None:
        report_data = load_mission10_robust_design_check() or {}
    report_data = _prepare_mission10_report(report_data)
    lines = ['Mission 10 Two-Gene Redundancy and Flux-Redirection Evidence', '']
    baseline = report_data.get('baseline')
    trials = report_data.get('trials') or {}
    count = report_data.get('valid_trial_count', len(trials))
    required = report_data.get('required_trial_count', len(MISSION10_REQUIRED_PAIRS))

    if not baseline and not trials:
        lines.extend([
            'Build a controlled anaerobic two-gene comparison.',
            'First record the no-knockout reference, then test each candidate pair while keeping FBA, the biomass objective, the medium and the tracked fluxes identical.',
            '',
            f'Candidate pair trials recorded: 0/{required}',
        ])
    else:
        lines.extend([
            'Controlled setup for recorded evidence: FBA biomass objective; default glucose supply; oxygen uptake disabled; all other bounds unchanged; ethanol and acetate exchanges tracked; exactly two candidate knockouts per pair trial.',
            '',
        ])
        if baseline:
            lines.append(
                f"Baseline: growth {float(baseline.get('growth', 0.0)):.3f}; ethanol {float(baseline.get('ethanol', 0.0)):.3f}; "
                f"acetate {float(baseline.get('acetate', 0.0)):.3f}; glucose uptake {float(baseline.get('glucose_uptake', 0.0)):.3f}; oxygen uptake {float(baseline.get('oxygen_uptake', 0.0)):.3f}."
            )
        else:
            lines.append('Baseline: not recorded yet')
        lines.extend([f'Candidate pair trials recorded: {count}/{required}', '', 'Pair screen:'])
        for pair in MISSION10_REQUIRED_PAIRS:
            pair_key = _mission10_pair_key(pair)
            trial = trials.get(pair_key)
            label = _mission10_pair_label(pair_key)
            if not trial:
                lines.append(f'- {label}: pending')
                continue
            percent = trial.get('growth_percent')
            percent_text = f'{float(percent):.1f}% of baseline' if percent is not None else 'baseline missing'
            ethanol_change = trial.get('ethanol_change')
            acetate_change = trial.get('acetate_change')
            ethanol_change_text = f'{float(ethanol_change):+.3f}' if ethanol_change is not None else 'baseline missing'
            acetate_change_text = f'{float(acetate_change):+.3f}' if acetate_change is not None else 'baseline missing'
            lines.append(
                f"- {label}: growth {float(trial.get('growth', 0.0)):.3f} ({percent_text}); "
                f"ethanol {float(trial.get('ethanol', 0.0)):.3f} (change {ethanol_change_text}); "
                f"acetate {float(trial.get('acetate', 0.0)):.3f} (change {acetate_change_text}); {trial.get('assessment', '')}"
            )

    if report_data.get('current_run_recorded'):
        lines.append('')
        if report_data.get('current_run_type') == 'baseline':
            lines.append('Latest valid run recorded: no-knockout anaerobic glucose reference.')
        else:
            pair_key = report_data.get('current_pair_key')
            lines.append(
                f"Latest valid pair recorded: {_mission10_pair_label(pair_key)}; "
                f"growth {float(report_data.get('current_growth', 0.0)):.3f}; "
                f"ethanol {float(report_data.get('current_ethanol', 0.0)):.3f}; "
                f"acetate {float(report_data.get('current_acetate', 0.0)):.3f}."
            )
    elif report_data.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report_data.get('current_issues') or [])

    lines.append('')
    if report_data.get('evidence_ready'):
        lines.append('Evidence complete. Identify the two-gene pair that best increases ethanol while retaining sufficient growth, and submit both gene ids or names to Dr. Nova.')
    else:
        if not baseline:
            lines.append('Evidence incomplete: the no-knockout anaerobic reference is still required.')
        missing = report_data.get('missing_pairs') or []
        if missing:
            lines.append('Missing pair trials: ' + ', '.join(_mission10_pair_label(pair_key) for pair_key in missing))
        elif report_data.get('comparison_complete') and not report_data.get('winner_unique'):
            lines.append('Comparison complete, but the operational criteria do not identify one unique two-gene design.')

    lines.extend([
        '',
        'Interpretation note: all growth, ethanol and acetate values come from the same visible biomass-optimal FBA solution. No hidden product objective is used.',
        'The candidate genes illustrate OR-type GPR redundancy: one knockout can leave a reaction functional through an alternative gene, whereas the appropriate pair can disable the route.',
        f'A pair is operationally eligible when it retains at least {MISSION10_MIN_GROWTH_RATIO * 100:.0f}% of reference growth and increases ethanol by at least {MISSION10_MIN_ETHANOL_INCREASE:.1f}. These are mission criteria, not universal biological definitions.',
        'The result is conditional on this model, default glucose supply, anaerobic environment and biomass objective.',
    ])
    return '\n'.join(lines)



def _production_flux_value_map(production_fluxes):
    values = {}
    if not isinstance(production_fluxes, dict):
        return values

    for item in production_fluxes.get('items') or []:
        reaction_id = item.get('reaction_id')
        if not reaction_id:
            continue
        try:
            values[reaction_id] = float(item.get('production_flux', 0.0))
        except Exception:
            values[reaction_id] = 0.0
    return values


def is_mission11_unlocked(missions_completed):
    """Dr. Almeida's laboratory starts only after Mission 10."""
    return '10' in (missions_completed or [])


def _prepare_mission11_report(report_data):
    if not isinstance(report_data, dict) or report_data.get('mission_id') != '11':
        return {}
    if report_data.get('check_version') != MISSION11_CHECK_VERSION:
        return {}
    return copy.deepcopy(report_data)


def _mission11_growth_value(objective_result, production_fluxes):
    if isinstance(production_fluxes, dict):
        for key in ('objective_raw', 'biomass_raw'):
            value = _as_float_or_none(production_fluxes.get(key))
            if value is not None:
                return max(value, 0.0)
    value = _as_float_or_none(objective_result)
    return max(value, 0.0) if value is not None else None


def _mission11_measured_fluxes(production_fluxes):
    values = {}
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return values
    for item in production_fluxes.get('items') or []:
        reaction_id = item.get('reaction_id')
        if reaction_id not in MISSION11_REQUIRED_TRACKED_FLUXES or item.get('error'):
            continue
        value = _as_float_or_none(item.get('raw_flux', item.get('production_flux')))
        if value is not None:
            values[reaction_id] = max(float(value), 0.0)
    return values


def _mission11_medium_evidence(medium_fluxes):
    _raw, uptake, _secretion = _medium_flux_maps(medium_fluxes)
    glucose = _as_float_or_none(uptake.get(MISSION11_GLUCOSE_REACTION)) if MISSION11_GLUCOSE_REACTION in uptake else None
    oxygen = _as_float_or_none(uptake.get(MISSION11_OXYGEN_REACTION)) if MISSION11_OXYGEN_REACTION in uptake else None
    return glucose, oxygen


def _mission11_product_label(reaction_id):
    return f"{MISSION11_PRODUCT_NAMES.get(reaction_id, reaction_id)} ({reaction_id})"


def _build_mission11_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
    selected_fluxes=None,
):
    previous = _prepare_mission11_report(existing_report)
    fingerprint_run = copy.deepcopy(previous.get('fingerprint_run')) if previous else None

    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = list(selected_fluxes) if selected_fluxes is not None else _read_selected_production_fluxes()
    measured_fluxes = _mission11_measured_fluxes(production_fluxes)
    growth = _mission11_growth_value(objective_result, production_fluxes)
    glucose_uptake, oxygen_uptake = _mission11_medium_evidence(medium_fluxes)
    environment_correct, oxygen_closed, unexpected_changes = _mission11_environment_status(reactions)

    missing_selected = [rid for rid in MISSION11_REQUIRED_TRACKED_FLUXES if rid not in selected_fluxes]
    missing_measured = [rid for rid in MISSION11_REQUIRED_TRACKED_FLUXES if rid not in measured_fluxes]
    positive_products = [rid for rid in MISSION11_REQUIRED_TRACKED_FLUXES if measured_fluxes.get(rid, 0.0) > MISSION11_FLUX_TOLERANCE]
    zero_products = [rid for rid in MISSION11_REQUIRED_TRACKED_FLUXES if rid in measured_fluxes and abs(measured_fluxes[rid]) <= MISSION11_FLUX_TOLERANCE]
    dominant_product = None
    if not missing_measured:
        dominant_product = max(MISSION11_REQUIRED_TRACKED_FLUXES, key=lambda rid: measured_fluxes.get(rid, 0.0))

    issues = []
    if objective_error:
        issues.append(objective_error)
    if method_name != MISSION11_METHOD:
        issues.append(f'Use {MISSION11_METHOD} so the secretion fingerprint is tied to the standard biomass-optimal baseline.')
    if selected_objective != MISSION11_GROWTH_OBJECTIVE:
        issues.append(f'Use {MISSION11_GROWTH_OBJECTIVE} as the objective.')
    if not oxygen_closed:
        issues.append(f'Disable oxygen uptake by closing only the lower bound of {MISSION11_OXYGEN_REACTION}.')
    if unexpected_changes:
        issues.append('Keep every other environmental bound at its model-default state.')
    if knocked_out_genes:
        issues.append('Keep all genes active for this diagnostic reference.')
    if missing_selected:
        issues.append('Select the full fingerprint panel in Production Flux: ' + ', '.join(missing_selected) + '.')
    if missing_measured:
        issues.append('The visible solution did not provide numeric evidence for: ' + ', '.join(missing_measured) + '.')
    if growth is None:
        issues.append('The visible solution did not provide a numeric biomass flux.')
    elif growth < MISSION11_MIN_GROWTH:
        issues.append(f'The model must predict positive growth of at least {MISSION11_MIN_GROWTH:.3f} in this controlled reference.')
    if glucose_uptake is None:
        issues.append(f'The Exchange Flux Report did not provide glucose-uptake evidence for {MISSION11_GLUCOSE_REACTION}.')
    elif glucose_uptake <= MISSION11_FLUX_TOLERANCE:
        issues.append('The default glucose supply is not being used in the visible solution.')
    if oxygen_uptake is None:
        issues.append(f'The Exchange Flux Report did not provide oxygen-uptake evidence for {MISSION11_OXYGEN_REACTION}.')
    elif oxygen_uptake > MISSION11_FLUX_TOLERANCE:
        issues.append('The visible solution still uses oxygen; the intended reference is anaerobic.')

    if not missing_measured:
        for reaction_id in MISSION11_EXPECTED_POSITIVE_FLUXES:
            if measured_fluxes.get(reaction_id, 0.0) <= MISSION11_FLUX_TOLERANCE:
                issues.append(f'{_mission11_product_label(reaction_id)} should show positive secretion in this fingerprint.')
        for reaction_id in MISSION11_EXPECTED_ZERO_FLUXES:
            if abs(measured_fluxes.get(reaction_id, 0.0)) > MISSION11_FLUX_TOLERANCE:
                issues.append(f'{_mission11_product_label(reaction_id)} should be approximately zero in this fingerprint.')
        if dominant_product != MISSION11_EXPECTED_DOMINANT_FLUX:
            issues.append('The measured flux ordering does not match the controlled reference. Verify the complete setup and numeric panel before interpreting the dominant product.')

    current_run_valid = not issues
    if current_run_valid:
        fingerprint_run = {
            'growth': round(float(growth), 6),
            'tracked_flux_values': {rid: round(float(measured_fluxes[rid]), 6) for rid in MISSION11_REQUIRED_TRACKED_FLUXES},
            'positive_products': list(positive_products),
            'zero_products': list(zero_products),
            'dominant_product': dominant_product,
            'glucose_uptake': round(float(glucose_uptake), 6),
            'oxygen_uptake': round(float(oxygen_uptake), 6),
        }

    fingerprint_complete = bool(fingerprint_run)
    data = {
        'mission_id': '11',
        'check_version': MISSION11_CHECK_VERSION,
        'mission_title': 'Anaerobic Secretion Fingerprint',
        'target_context': MISSION11_TARGET_CONTEXT,
        'required_method': MISSION11_METHOD,
        'growth_objective': MISSION11_GROWTH_OBJECTIVE,
        'oxygen_reaction': MISSION11_OXYGEN_REACTION,
        'glucose_reaction': MISSION11_GLUCOSE_REACTION,
        'required_tracked_fluxes': list(MISSION11_REQUIRED_TRACKED_FLUXES),
        'product_names': dict(MISSION11_PRODUCT_NAMES),
        'expected_positive_fluxes': list(MISSION11_EXPECTED_POSITIVE_FLUXES),
        'expected_zero_fluxes': list(MISSION11_EXPECTED_ZERO_FLUXES),
        'expected_dominant_product': MISSION11_EXPECTED_DOMINANT_FLUX,
        'minimum_growth': MISSION11_MIN_GROWTH,
        'fingerprint_run': fingerprint_run,
        'fingerprint_complete': fingerprint_complete,
        'answer_ready': fingerprint_complete,
        'evidence_ready': fingerprint_complete,
        'ready_to_deliver': fingerprint_complete,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_valid,
        'current_method': method_name,
        'current_objective': selected_objective,
        'current_knocked_out_genes': knocked_out_genes,
        'current_environment_correct': environment_correct,
        'current_oxygen_lower_bound_closed': oxygen_closed,
        'current_unexpected_environment_changes': unexpected_changes,
        'current_growth': round(float(growth), 6) if growth is not None else None,
        'current_tracked_flux_values': {rid: round(float(value), 6) for rid, value in measured_fluxes.items()},
        'current_positive_products': positive_products,
        'current_zero_products': zero_products,
        'current_dominant_product': dominant_product,
        'current_glucose_uptake': round(float(glucose_uptake), 6) if glucose_uptake is not None else None,
        'current_oxygen_uptake': round(float(oxygen_uptake), 6) if oxygen_uptake is not None else None,
        'selected_production_fluxes': selected_fluxes,
        'missing_selected_fluxes': missing_selected,
        'missing_measured_fluxes': missing_measured,
        'all_fluxes_measured': not missing_measured,
        'current_issues': issues,
        'latest_attempt': {
            'valid': current_run_valid,
            'method': method_name,
            'objective': selected_objective,
            'issues': list(issues),
        },
    }
    save_mission11_flux_fingerprint_check(data)
    return data


def run_mission11_flux_fingerprint_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible simulation before recording Mission 11 evidence.'
    except Exception:
        objective_error = 'Could not read the current visible simulation result.'

    return _build_mission11_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission11_flux_fingerprint_check(),
        objective_error=objective_error,
    )


def _mission11_report_is_current(report_data):
    return bool(
        isinstance(report_data, dict)
        and report_data.get('mission_id') == '11'
        and report_data.get('check_version') == MISSION11_CHECK_VERSION
    )


def normalise_mission11_answer(answer):
    compact = ''.join(char.lower() for char in str(answer or '') if char.isalnum())
    aliases = {
        'formate': MISSION11_EXPECTED_DOMINANT_FLUX,
        'formicacid': MISSION11_EXPECTED_DOMINANT_FLUX,
        'exfore': MISSION11_EXPECTED_DOMINANT_FLUX,
        'formateexfore': MISSION11_EXPECTED_DOMINANT_FLUX,
        'exforeformate': MISSION11_EXPECTED_DOMINANT_FLUX,
    }
    return aliases.get(compact)


def mission11_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission11_flux_fingerprint_check() or {}
    if not _mission11_report_is_current(report_data) or not report_data.get('evidence_ready'):
        return False
    return normalise_mission11_answer(answer) == (report_data.get('fingerprint_run') or {}).get('dominant_product')


def build_mission11_fingerprint_report_text(report_data=None):
    if report_data is None:
        report_data = load_mission11_flux_fingerprint_check() or {}
    report_data = _prepare_mission11_report(report_data)
    lines = ['Mission 11 Anaerobic Secretion Fingerprint', '']
    fingerprint = report_data.get('fingerprint_run')

    if not fingerprint:
        lines.extend([
            'Build one controlled anaerobic biomass-optimal fingerprint from the visible result.',
            'Keep genes and the default glucose supply unchanged, then measure the complete five-product exchange panel.',
        ])
    else:
        values = fingerprint.get('tracked_flux_values') or {}
        lines.extend([
            'Controlled setup recorded: FBA biomass objective; default glucose supply; oxygen uptake disabled; all genes active; all other bounds unchanged.',
            '',
            f"Predicted biomass flux: {float(fingerprint.get('growth', 0.0)):.3f}",
            f"Glucose uptake: {float(fingerprint.get('glucose_uptake', 0.0)):.3f}",
            f"Oxygen uptake: {_clean_display_number(fingerprint.get('oxygen_uptake', 0.0)):.3f}",
            '',
            'Tracked secretion fingerprint:',
        ])
        for reaction_id in MISSION11_REQUIRED_TRACKED_FLUXES:
            lines.append(f"- {_mission11_product_label(reaction_id)}: {float(values.get(reaction_id, 0.0)):.3f}")
        lines.extend([
            '',
            'Products with positive predicted secretion: ' + ', '.join(MISSION11_PRODUCT_NAMES[rid] for rid in fingerprint.get('positive_products') or []),
            'No predicted secretion in this solution: ' + ', '.join(MISSION11_PRODUCT_NAMES[rid] for rid in fingerprint.get('zero_products') or []),
            'Compare the positive tracked exchange fluxes above. The greatest numeric secretion value determines the requested conclusion.',
        ])

    if report_data.get('current_run_valid'):
        lines.extend(['', 'Latest valid fingerprint recorded from the visible solution.'])
    elif report_data.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report_data.get('current_issues') or [])
        if fingerprint:
            lines.append('The previously valid fingerprint remains available.')

    lines.append('')
    if report_data.get('evidence_ready'):
        lines.append('Evidence complete. Identify the dominant tracked product and submit its name or exchange-reaction id to Dr. Almeida.')
    else:
        lines.append('Evidence incomplete. Record the full controlled fingerprint before submitting an interpretation.')

    lines.extend([
        '',
        'Interpretation note: a positive exchange flux represents secretion predicted in this specific FBA solution.',
        'A zero exchange flux does not mean that E. coli can never produce that compound; it means that this model, objective and set of constraints do not predict secretion in this solution.',
        'The model predicts positive growth under these conditions; this is not a direct experimental claim about viability.',
        'All growth, product and medium values come from the same visible solution. No hidden simulation or product objective is used.',
    ])
    return '\n'.join(lines)


def is_mission12_unlocked(missions_completed):
    """Mission 12 starts only after the Mission 11 fingerprint is complete."""
    return '11' in (missions_completed or [])


def _prepare_mission12_report(report_data):
    if not isinstance(report_data, dict) or report_data.get('mission_id') != '12':
        return {}
    if report_data.get('check_version') != MISSION12_CHECK_VERSION:
        return {}
    return copy.deepcopy(report_data)


def _mission12_report_is_current(report_data):
    return bool(
        isinstance(report_data, dict)
        and report_data.get('mission_id') == '12'
        and report_data.get('check_version') == MISSION12_CHECK_VERSION
    )


def _mission12_measured_fluxes(production_fluxes):
    values = {}
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return values
    for item in production_fluxes.get('items') or []:
        reaction_id = item.get('reaction_id')
        if reaction_id not in MISSION12_REQUIRED_TRACKED_FLUXES or item.get('error'):
            continue
        value = _as_float_or_none(item.get('raw_flux', item.get('production_flux')))
        if value is not None:
            values[reaction_id] = max(float(value), 0.0)
    return values


def _mission12_biomass_value(production_fluxes):
    if not isinstance(production_fluxes, dict):
        return None
    value = _as_float_or_none(production_fluxes.get('biomass_raw'))
    return max(float(value), 0.0) if value is not None else None


def _mission12_medium_evidence(medium_fluxes):
    _raw, uptake, _secretion = _medium_flux_maps(medium_fluxes)
    glucose = _as_float_or_none(uptake.get(MISSION12_GLUCOSE_REACTION)) if MISSION12_GLUCOSE_REACTION in uptake else None
    oxygen = _as_float_or_none(uptake.get(MISSION12_OXYGEN_REACTION)) if MISSION12_OXYGEN_REACTION in uptake else None
    return glucose, oxygen


def _mission12_product_label(reaction_id):
    return f"{MISSION12_PRODUCT_NAMES.get(reaction_id, reaction_id)} ({reaction_id})"


def _mission12_run_label(run_type):
    if run_type == 'default':
        return 'oxygen-available default-medium run'
    if run_type == 'oxygen_constrained':
        return 'oxygen-constrained run'
    return 'unclassified run'


def _build_mission12_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
    selected_fluxes=None,
):
    previous = _prepare_mission12_report(existing_report)
    default_run = copy.deepcopy(previous.get('default_run')) if previous else None
    oxygen_constrained_run = copy.deepcopy(previous.get('oxygen_constrained_run')) if previous else None

    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = list(selected_fluxes) if selected_fluxes is not None else _read_selected_production_fluxes()
    measured_fluxes = _mission12_measured_fluxes(production_fluxes)
    objective_value = _as_float_or_none(objective_result)
    target_flux = measured_fluxes.get(MISSION12_TARGET_OBJECTIVE)
    biomass_flux = _mission12_biomass_value(production_fluxes)
    glucose_uptake, oxygen_uptake = _mission12_medium_evidence(medium_fluxes)
    environment_type, oxygen_closed, unexpected_changes = _mission12_environment_status(reactions)

    missing_selected = [rid for rid in MISSION12_REQUIRED_TRACKED_FLUXES if rid not in selected_fluxes]
    missing_measured = [rid for rid in MISSION12_REQUIRED_TRACKED_FLUXES if rid not in measured_fluxes]

    issues = []
    if objective_error:
        issues.append(objective_error)
    if method_name != MISSION12_METHOD:
        issues.append(f'Use {MISSION12_METHOD} in both runs so oxygen availability is the only modelling variable that changes.')
    if selected_objective != MISSION12_TARGET_OBJECTIVE:
        issues.append(f'Use {MISSION12_TARGET_OBJECTIVE} as the objective in both runs.')
    if unexpected_changes:
        issues.append('Keep the medium at its model-default state, changing only the oxygen lower bound for the constrained run.')
    if environment_type not in ('default', 'oxygen_constrained'):
        issues.append('Record either the completely default medium or the same medium with only oxygen uptake disabled.')
    if knocked_out_genes:
        issues.append('Keep all genes active; this mission isolates an environmental constraint rather than a genetic intervention.')
    if missing_selected:
        issues.append('Select the complete target/byproduct panel in Production Flux: ' + ', '.join(missing_selected) + '.')
    if missing_measured:
        issues.append('The visible solution did not provide numeric evidence for: ' + ', '.join(missing_measured) + '.')

    if objective_value is None:
        issues.append('The visible solution did not provide a numeric succinate-objective value.')
    elif objective_value < MISSION12_MIN_TARGET_FLUX:
        issues.append('The direct succinate objective did not produce a positive theoretical optimum.')

    if target_flux is not None:
        if target_flux < MISSION12_MIN_TARGET_FLUX:
            issues.append('Tracked succinate secretion is not positive enough for this comparison.')
        if objective_value is not None and abs(float(target_flux) - float(objective_value)) > MISSION12_TARGET_MATCH_TOLERANCE:
            issues.append('The tracked succinate flux does not match the visible EX_succ_e objective value from the same solution.')

    if biomass_flux is None:
        issues.append('The visible product-optimal solution did not provide a numeric biomass flux.')
    elif biomass_flux > MISSION12_MAX_BIOMASS_FLUX:
        issues.append('Both direct succinate optima should show approximately zero predicted biomass flux in this controlled comparison.')

    if glucose_uptake is None:
        issues.append(f'The Exchange Flux Report did not provide glucose-uptake evidence for {MISSION12_GLUCOSE_REACTION}.')
    elif abs(float(glucose_uptake) - MISSION12_DEFAULT_GLUCOSE_UPTAKE) > MISSION12_GLUCOSE_TOLERANCE:
        issues.append('The visible solution is not using the expected default glucose supply.')

    if oxygen_uptake is None:
        issues.append(f'The Exchange Flux Report did not provide oxygen-uptake evidence for {MISSION12_OXYGEN_REACTION}.')
    elif environment_type == 'default' and oxygen_uptake < MISSION12_MIN_DEFAULT_OXYGEN_UPTAKE:
        issues.append('The default-medium succinate optimum should visibly use oxygen before the constraint is imposed.')
    elif environment_type == 'oxygen_constrained' and oxygen_uptake > MISSION12_FLUX_TOLERANCE:
        issues.append('The oxygen-constrained solution still uses oxygen; close only the lower bound of EX_o2_e.')

    if not missing_measured:
        acetate = measured_fluxes.get('EX_ac_e', 0.0)
        if environment_type == 'default':
            for reaction_id in MISSION12_COMPETING_FLUXES:
                if abs(measured_fluxes.get(reaction_id, 0.0)) > MISSION12_FLUX_TOLERANCE:
                    issues.append(f'{_mission12_product_label(reaction_id)} should be approximately zero at the oxygen-available succinate optimum.')
        elif environment_type == 'oxygen_constrained':
            if acetate <= MISSION12_FLUX_TOLERANCE:
                issues.append('The oxygen-constrained fingerprint does not show the expected transition from a near-zero byproduct flux to positive secretion. Verify the complete setup and panel.')
            for reaction_id in MISSION12_EXPECTED_ZERO_BYPRODUCTS:
                if abs(measured_fluxes.get(reaction_id, 0.0)) > MISSION12_FLUX_TOLERANCE:
                    issues.append(f'{_mission12_product_label(reaction_id)} should be approximately zero in the oxygen-constrained fingerprint.')

    current_run_valid = not issues
    current_run_type = environment_type if current_run_valid else None
    current_run = None
    if current_run_valid:
        current_run = {
            'run_type': environment_type,
            'method': method_name,
            'objective': selected_objective,
            'objective_value': round(float(objective_value), 6),
            'target_flux': round(float(target_flux), 6),
            'tracked_flux_values': {
                rid: round(float(measured_fluxes[rid]), 6)
                for rid in MISSION12_REQUIRED_TRACKED_FLUXES
            },
            'biomass_flux': round(float(biomass_flux), 6),
            'glucose_uptake': round(float(glucose_uptake), 6),
            'oxygen_uptake': round(float(oxygen_uptake), 6),
            'positive_byproducts': [
                rid for rid in MISSION12_COMPETING_FLUXES
                if measured_fluxes.get(rid, 0.0) > MISSION12_FLUX_TOLERANCE
            ],
        }
        diagnostics = _method_diagnostics_from_production_data(production_fluxes)
        current_run['primary_objective_flux'] = diagnostics.get('primary_objective_flux')
        current_run['method_score'] = diagnostics.get('method_score')
        current_run['method_score_name'] = diagnostics.get('method_score_name')
        current_run['total_absolute_flux'] = diagnostics.get('total_absolute_flux')
        current_run['active_reaction_count'] = diagnostics.get('active_reaction_count')
        if environment_type == 'default':
            default_run = current_run
        elif environment_type == 'oxygen_constrained':
            oxygen_constrained_run = current_run

    comparison_complete = bool(default_run and oxygen_constrained_run)
    target_change = None
    target_change_percent = None
    acetate_change = None
    new_byproduct = None
    constraint_binding = False
    both_no_growth = False
    comparison_issues = []

    if comparison_complete:
        default_target = float(default_run.get('target_flux', 0.0))
        constrained_target = float(oxygen_constrained_run.get('target_flux', 0.0))
        default_values = default_run.get('tracked_flux_values') or {}
        constrained_values = oxygen_constrained_run.get('tracked_flux_values') or {}
        default_acetate = float(default_values.get('EX_ac_e', 0.0))
        constrained_acetate = float(constrained_values.get('EX_ac_e', 0.0))

        target_change = constrained_target - default_target
        target_change_percent = (target_change / default_target * 100.0) if abs(default_target) > MISSION12_FLUX_TOLERANCE else None
        acetate_change = constrained_acetate - default_acetate
        if default_acetate <= MISSION12_FLUX_TOLERANCE and constrained_acetate > MISSION12_FLUX_TOLERANCE:
            new_byproduct = 'EX_ac_e'

        both_no_growth = (
            float(default_run.get('biomass_flux', 0.0)) <= MISSION12_MAX_BIOMASS_FLUX
            and float(oxygen_constrained_run.get('biomass_flux', 0.0)) <= MISSION12_MAX_BIOMASS_FLUX
        )
        constraint_binding = (
            target_change <= -MISSION12_MIN_TARGET_DROP
            and float(default_run.get('oxygen_uptake', 0.0)) >= MISSION12_MIN_DEFAULT_OXYGEN_UPTAKE
            and float(oxygen_constrained_run.get('oxygen_uptake', 0.0)) <= MISSION12_FLUX_TOLERANCE
        )

        if target_change > -MISSION12_MIN_TARGET_DROP:
            comparison_issues.append('The oxygen constraint should reduce the theoretical succinate maximum relative to the default-medium run.')
        if acetate_change < MISSION12_MIN_ACETATE_INCREASE:
            comparison_issues.append('The constrained fingerprint should contain one co-product that changes from approximately zero to positive secretion relative to the default-medium run.')
        if new_byproduct != MISSION12_EXPECTED_NEW_BYPRODUCT:
            comparison_issues.append('The two fingerprints do not yet show the expected single co-product changing from approximately zero to positive secretion.')
        if not both_no_growth:
            comparison_issues.append('Both direct product-optimal solutions should have approximately zero predicted biomass flux.')
        if not constraint_binding:
            comparison_issues.append('The recorded evidence does not yet demonstrate that oxygen availability is binding for this succinate objective.')

    evidence_ready = comparison_complete and not comparison_issues
    fallback_run = oxygen_constrained_run or default_run
    data = {
        'mission_id': '12',
        'check_version': MISSION12_CHECK_VERSION,
        'mission_title': 'Constraint-Driven Succinate Byproducts',
        'required_method': MISSION12_METHOD,
        'target_product': MISSION12_TARGET_PRODUCT,
        'target_objective': MISSION12_TARGET_OBJECTIVE,
        'oxygen_reaction': MISSION12_OXYGEN_REACTION,
        'glucose_reaction': MISSION12_GLUCOSE_REACTION,
        'required_tracked_fluxes': list(MISSION12_REQUIRED_TRACKED_FLUXES),
        'competing_fluxes': list(MISSION12_COMPETING_FLUXES),
        'product_names': dict(MISSION12_PRODUCT_NAMES),
        'expected_new_byproduct': MISSION12_EXPECTED_NEW_BYPRODUCT,
        'default_run': default_run,
        'oxygen_constrained_run': oxygen_constrained_run,
        'comparison_complete': comparison_complete,
        'target_change': round(float(target_change), 6) if target_change is not None else None,
        'target_change_percent': round(float(target_change_percent), 3) if target_change_percent is not None else None,
        'acetate_change': round(float(acetate_change), 6) if acetate_change is not None else None,
        'new_byproduct': new_byproduct,
        'constraint_binding': constraint_binding,
        'both_no_growth': both_no_growth,
        'comparison_issues': comparison_issues,
        'answer_ready': evidence_ready,
        'evidence_ready': evidence_ready,
        'ready_to_deliver': evidence_ready,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_valid,
        'current_run_type': current_run_type,
        'current_method': method_name,
        'current_objective': selected_objective,
        'current_knocked_out_genes': knocked_out_genes,
        'current_environment_type': environment_type,
        'current_oxygen_lower_bound_closed': oxygen_closed,
        'current_unexpected_environment_changes': unexpected_changes,
        'current_objective_value': round(float(objective_value), 6) if objective_value is not None else None,
        'current_target_flux': round(float(target_flux), 6) if target_flux is not None else None,
        'current_biomass_flux': round(float(biomass_flux), 6) if biomass_flux is not None else None,
        'current_glucose_uptake': round(float(glucose_uptake), 6) if glucose_uptake is not None else None,
        'current_oxygen_uptake': round(float(oxygen_uptake), 6) if oxygen_uptake is not None else None,
        'current_tracked_flux_values': {rid: round(float(value), 6) for rid, value in measured_fluxes.items()},
        'selected_production_fluxes': selected_fluxes,
        'missing_selected_fluxes': missing_selected,
        'missing_measured_fluxes': missing_measured,
        'full_panel_measured': not missing_measured,
        'current_issues': issues,
        'latest_attempt': {
            'valid': current_run_valid,
            'run_type': environment_type,
            'method': method_name,
            'objective': selected_objective,
            'issues': list(issues),
        },
        # Compatibility fields for Mission 13, whose pFBA comparison uses the
        # oxygen-constrained FBA run as its baseline.
        'method': MISSION12_METHOD,
        'target_flux': fallback_run.get('target_flux') if fallback_run else None,
        'tracked_flux_values': copy.deepcopy(fallback_run.get('tracked_flux_values')) if fallback_run else {},
    }
    save_mission12_byproduct_check(data)
    return data


def run_mission12_byproduct_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible simulation before recording Mission 12 evidence.'
    except Exception:
        objective_error = 'Could not read the current visible simulation result.'

    return _build_mission12_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission12_byproduct_check(),
        objective_error=objective_error,
    )


def normalise_mission12_answer(answer):
    compact = ''.join(char.lower() for char in str(answer or '') if char.isalnum())
    aliases = {
        'acetate': MISSION12_EXPECTED_NEW_BYPRODUCT,
        'aceticacid': MISSION12_EXPECTED_NEW_BYPRODUCT,
        'exace': MISSION12_EXPECTED_NEW_BYPRODUCT,
        'acetateexace': MISSION12_EXPECTED_NEW_BYPRODUCT,
        'exaceacetate': MISSION12_EXPECTED_NEW_BYPRODUCT,
    }
    return aliases.get(compact)


def mission12_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission12_byproduct_check() or {}
    if not _mission12_report_is_current(report_data) or not report_data.get('evidence_ready'):
        return False
    return normalise_mission12_answer(answer) == report_data.get('new_byproduct')


def build_mission12_comparison_report_text(report_data=None):
    if report_data is None:
        report_data = load_mission12_byproduct_check() or {}
    report_data = _prepare_mission12_report(report_data)
    lines = ['Mission 12 Constraint-Driven Succinate Byproduct Comparison', '']
    default_run = report_data.get('default_run')
    constrained_run = report_data.get('oxygen_constrained_run')

    if not default_run and not constrained_run:
        lines.extend([
            'Build two controlled FBA succinate-optimal fingerprints from visible results.',
            'Keep the objective, genes, glucose supply and full product panel identical; change only oxygen availability.',
        ])
    else:
        lines.extend([
            'Controlled setup for recorded evidence: FBA and EX_succ_e objective in both runs; all genes active; default glucose supply; complete target/byproduct panel; only oxygen availability differs.',
            '',
        ])

        def append_run(title, run):
            lines.append(title + ':')
            if not run:
                lines.append('- Not recorded yet')
                return
            values = run.get('tracked_flux_values') or {}
            for reaction_id in MISSION12_REQUIRED_TRACKED_FLUXES:
                lines.append(f"- {_mission12_product_label(reaction_id)}: {_clean_display_number(values.get(reaction_id, 0.0)):.3f}")
            lines.extend([
                f"- Predicted biomass flux: {_clean_display_number(run.get('biomass_flux', 0.0)):.3f}",
                f"- Glucose uptake: {_clean_display_number(run.get('glucose_uptake', 0.0)):.3f}",
                f"- Oxygen uptake: {_clean_display_number(run.get('oxygen_uptake', 0.0)):.3f}",
            ])

        append_run('Oxygen-available default-medium run', default_run)
        lines.append('')
        append_run('Oxygen-constrained run', constrained_run)

    if report_data.get('current_run_valid'):
        lines.extend(['', 'Latest valid run recorded: ' + _mission12_run_label(report_data.get('current_run_type')) + '.'])
    elif report_data.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report_data.get('current_issues') or [])
        if default_run or constrained_run:
            lines.append('Previously valid Mission 12 evidence remains available.')

    lines.append('')
    if report_data.get('comparison_complete'):
        change = report_data.get('target_change')
        percent = report_data.get('target_change_percent')
        acetate_change = report_data.get('acetate_change')
        percent_text = f' ({float(percent):+.1f}%)' if percent is not None else ''
        lines.extend([
            f"Succinate change after disabling oxygen uptake: {float(change):+.3f}{percent_text}",
            'Compare the complete tracked fingerprints above and identify which co-product changes from approximately zero to positive secretion after oxygen uptake is disabled.',
        ])
        if report_data.get('comparison_issues'):
            lines.append('Comparison issues:')
            lines.extend(f'- {issue}' for issue in report_data.get('comparison_issues') or [])

    lines.append('')
    if report_data.get('evidence_ready'):
        lines.append('Evidence complete. Identify the new positive co-product introduced by the oxygen constraint and submit its name or exchange-reaction id to Dr. Almeida.')
    else:
        missing = []
        if not default_run:
            missing.append('oxygen-available default-medium run')
        if not constrained_run:
            missing.append('oxygen-constrained run')
        if missing:
            lines.append('Evidence incomplete. Missing: ' + ', '.join(missing) + '.')
        elif report_data.get('comparison_issues'):
            lines.append('Both runs are recorded, but the controlled binding-constraint comparison is not yet complete.')
        else:
            lines.append('Evidence incomplete. Record both controlled visible fingerprints before submitting an interpretation.')

    lines.extend([
        '',
        'Interpretation note: changing oxygen availability changes the feasible flux space; it does not genetically modify the strain.',
        'In this model and under these bounds, disabling oxygen uptake reduces the theoretical succinate maximum and changes the predicted co-product profile.',
        'Both direct succinate-optimal solutions have no predicted growth. They are theoretical product optima, not viable production-strain claims.',
        'A zero exchange flux describes only this model, objective and set of constraints; it is not a universal biological incapacity.',
        'All target, byproduct, biomass and medium values come from the same two visible solutions. No hidden simulation is used.',
    ])
    return '\n'.join(lines)


def is_mission13_unlocked(missions_completed):
    """Mission 13 starts only after the controlled Mission 12 comparison."""
    return '12' in (missions_completed or [])


def _prepare_mission13_report(report_data):
    if not isinstance(report_data, dict) or report_data.get('mission_id') != '13':
        return {}
    if report_data.get('check_version') != MISSION13_CHECK_VERSION:
        return {}
    return copy.deepcopy(report_data)


def _mission13_measured_fluxes(production_fluxes):
    values = {}
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return values
    for item in production_fluxes.get('items') or []:
        reaction_id = item.get('reaction_id')
        if reaction_id not in MISSION13_REQUIRED_TRACKED_FLUXES or item.get('error'):
            continue
        value = _as_float_or_none(item.get('raw_flux', item.get('production_flux')))
        if value is not None:
            values[reaction_id] = max(float(value), 0.0)
    return values


def _mission13_biomass_value(production_fluxes):
    if not isinstance(production_fluxes, dict):
        return None
    value = _as_float_or_none(production_fluxes.get('biomass_raw'))
    return max(float(value), 0.0) if value is not None else None


def _mission13_medium_evidence(medium_fluxes):
    _raw, uptake, _secretion = _medium_flux_maps(medium_fluxes)
    glucose = _as_float_or_none(uptake.get(MISSION13_GLUCOSE_REACTION)) if MISSION13_GLUCOSE_REACTION in uptake else None
    oxygen = _as_float_or_none(uptake.get(MISSION13_OXYGEN_REACTION)) if MISSION13_OXYGEN_REACTION in uptake else None
    return glucose, oxygen


def _mission13_import_mission12_baseline():
    """Reuse Mission 12 only when it already contains full visible diagnostics."""
    baseline_data = load_mission12_byproduct_check()
    if not (
        isinstance(baseline_data, dict)
        and baseline_data.get('mission_id') == '12'
        and baseline_data.get('check_version') == MISSION12_CHECK_VERSION
        and baseline_data.get('evidence_ready')
    ):
        return None, False
    source = baseline_data.get('oxygen_constrained_run') or {}
    basic_available = bool(source)
    total_flux = _as_float_or_none(source.get('total_absolute_flux'))
    active_count = source.get('active_reaction_count')
    try:
        active_count = int(active_count) if active_count is not None else None
    except Exception:
        active_count = None
    if total_flux is None or active_count is None:
        return None, basic_available
    tracked = source.get('tracked_flux_values') or {}
    if any(rid not in tracked for rid in MISSION13_REQUIRED_TRACKED_FLUXES):
        return None, basic_available
    imported = {
        'run_type': 'fba',
        'source': 'mission12_visible_run',
        'method': MISSION13_BASELINE_METHOD,
        'objective': MISSION13_TARGET_OBJECTIVE,
        'primary_objective_flux': round(float(source.get('target_flux')), 6),
        'method_score': source.get('method_score'),
        'method_score_name': source.get('method_score_name'),
        'total_absolute_flux': round(float(total_flux), 6),
        'active_reaction_count': active_count,
        'tracked_flux_values': {
            rid: round(float(tracked[rid]), 6)
            for rid in MISSION13_REQUIRED_TRACKED_FLUXES
        },
        'biomass_flux': round(float(source.get('biomass_flux', 0.0)), 6),
        'glucose_uptake': round(float(source.get('glucose_uptake', 0.0)), 6),
        'oxygen_uptake': round(float(source.get('oxygen_uptake', 0.0)), 6),
    }
    return imported, basic_available


def _mission13_product_label(reaction_id):
    return f"{MISSION13_PRODUCT_NAMES.get(reaction_id, reaction_id)} ({reaction_id})"


def _build_mission13_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
    selected_fluxes=None,
):
    previous = _prepare_mission13_report(existing_report)
    fba_run = copy.deepcopy(previous.get('fba_run')) if previous else None
    pfba_run = copy.deepcopy(previous.get('pfba_run')) if previous else None

    imported_baseline, mission12_baseline_available = _mission13_import_mission12_baseline()
    if fba_run is None and imported_baseline is not None:
        fba_run = imported_baseline

    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = list(selected_fluxes) if selected_fluxes is not None else _read_selected_production_fluxes()
    measured_fluxes = _mission13_measured_fluxes(production_fluxes)
    diagnostics = _method_diagnostics_from_production_data(production_fluxes)
    display_objective_value = _as_float_or_none(objective_result)
    primary_objective_flux = _as_float_or_none(diagnostics.get('primary_objective_flux'))
    if primary_objective_flux is None and isinstance(production_fluxes, dict):
        primary_objective_flux = _as_float_or_none(production_fluxes.get('objective_raw'))
    target_flux = measured_fluxes.get(MISSION13_TARGET_OBJECTIVE)
    biomass_flux = _mission13_biomass_value(production_fluxes)
    glucose_uptake, oxygen_uptake = _mission13_medium_evidence(medium_fluxes)
    total_absolute_flux = _as_float_or_none(diagnostics.get('total_absolute_flux'))
    method_score = _as_float_or_none(diagnostics.get('method_score'))
    method_score_name = diagnostics.get('method_score_name')
    active_reaction_count = diagnostics.get('active_reaction_count')
    try:
        active_reaction_count = int(active_reaction_count) if active_reaction_count is not None else None
    except Exception:
        active_reaction_count = None

    oxygen_closed, unexpected_changes = _mission13_environment_status(reactions)
    missing_selected = [rid for rid in MISSION13_REQUIRED_TRACKED_FLUXES if rid not in selected_fluxes]
    missing_measured = [rid for rid in MISSION13_REQUIRED_TRACKED_FLUXES if rid not in measured_fluxes]

    issues = []
    if objective_error:
        issues.append(objective_error)
    if method_name not in (MISSION13_BASELINE_METHOD, MISSION13_TARGET_METHOD):
        issues.append('Use FBA for the reference run or pFBA for the parsimonious run; no other method belongs in this comparison.')
    if selected_objective != MISSION13_TARGET_OBJECTIVE:
        issues.append(f'Use {MISSION13_TARGET_OBJECTIVE} as the primary objective in both method-comparison runs.')
    if not oxygen_closed:
        issues.append(f'Disable oxygen uptake by closing only the lower bound of {MISSION13_OXYGEN_REACTION}.')
    if unexpected_changes:
        issues.append('Keep every environmental bound at its model-default state except the closed oxygen lower bound.')
    if knocked_out_genes:
        issues.append('Keep all genes active; the simulation method must be the only changed modelling choice.')
    if missing_selected:
        issues.append('Select the complete target/byproduct panel in Production Flux: ' + ', '.join(missing_selected) + '.')
    if missing_measured:
        issues.append('The visible solution did not provide numeric evidence for: ' + ', '.join(missing_measured) + '.')

    if primary_objective_flux is None:
        issues.append('The visible result did not provide the primary EX_succ_e objective flux separately from the method score.')
    elif primary_objective_flux < MISSION13_MIN_TARGET_FLUX:
        issues.append('The primary succinate objective did not produce a positive theoretical optimum.')
    if target_flux is None:
        issues.append('Tracked succinate secretion was not measured numerically in the visible solution.')
    elif primary_objective_flux is not None and abs(float(target_flux) - float(primary_objective_flux)) > MISSION13_PRIMARY_TOLERANCE:
        issues.append('The tracked succinate flux does not match the primary EX_succ_e flux from the same visible solution.')
    if display_objective_value is not None and primary_objective_flux is not None and abs(float(display_objective_value) - float(primary_objective_flux)) > MISSION13_PRIMARY_TOLERANCE:
        issues.append('New Results is not displaying the primary objective-reaction flux consistently.')

    if biomass_flux is None:
        issues.append('The visible solution did not provide a numeric biomass flux.')
    elif biomass_flux > MISSION13_MAX_BIOMASS_FLUX:
        issues.append('This direct succinate-optimal comparison should show approximately zero predicted biomass flux.')
    if glucose_uptake is None:
        issues.append('The Exchange Flux Report did not provide numeric glucose-uptake evidence.')
    elif abs(float(glucose_uptake) - MISSION13_DEFAULT_GLUCOSE_UPTAKE) > MISSION13_FLUX_TOLERANCE:
        issues.append('Keep the model-default glucose supply unchanged in both runs.')
    if oxygen_uptake is None:
        issues.append('The Exchange Flux Report did not provide numeric oxygen-uptake evidence.')
    elif oxygen_uptake > MISSION13_FLUX_TOLERANCE:
        issues.append('The visible solution still uses oxygen; the comparison must remain anaerobic.')

    if not missing_measured:
        if measured_fluxes.get('EX_ac_e', 0.0) <= MISSION13_FLUX_TOLERANCE:
            issues.append('Acetate (EX_ac_e) should remain the positive co-product in this anaerobic succinate-optimal fingerprint.')
        for reaction_id in ('EX_for_e', 'EX_etoh_e', 'EX_lac__D_e'):
            if abs(measured_fluxes.get(reaction_id, 0.0)) > MISSION13_FLUX_TOLERANCE:
                issues.append(f'{_mission13_product_label(reaction_id)} should remain approximately zero in this controlled fingerprint.')

    if total_absolute_flux is None:
        issues.append('The visible solver result did not provide the total absolute flux needed for the parsimony comparison.')
    if active_reaction_count is None:
        issues.append('The visible solver result did not provide an active-reaction count.')
    if method_name == MISSION13_TARGET_METHOD:
        if method_score is None:
            issues.append('The pFBA result did not provide its secondary parsimony score.')
        if method_score_name != MISSION13_EXPECTED_SECONDARY_CRITERION:
            issues.append('The pFBA secondary score must be identified as total absolute flux, not as succinate production.')
        if method_score is not None and total_absolute_flux is not None and abs(method_score - total_absolute_flux) > MISSION13_PARSIMONY_TOLERANCE:
            issues.append('The reported pFBA secondary score is inconsistent with the total absolute flux of the visible solution.')

    current_run_valid = not issues
    current_run_type = method_name.lower() if current_run_valid else None
    if current_run_valid:
        current_run = {
            'run_type': current_run_type,
            'source': 'visible_simulation',
            'method': method_name,
            'objective': selected_objective,
            'primary_objective_flux': round(float(primary_objective_flux), 6),
            'method_score': round(float(method_score), 6) if method_score is not None else None,
            'method_score_name': method_score_name,
            'total_absolute_flux': round(float(total_absolute_flux), 6),
            'active_reaction_count': int(active_reaction_count),
            'tracked_flux_values': {
                rid: round(float(measured_fluxes[rid]), 6)
                for rid in MISSION13_REQUIRED_TRACKED_FLUXES
            },
            'biomass_flux': round(float(biomass_flux), 6),
            'glucose_uptake': round(float(glucose_uptake), 6),
            'oxygen_uptake': round(float(oxygen_uptake), 6),
        }
        if method_name == MISSION13_BASELINE_METHOD:
            fba_run = current_run
        elif method_name == MISSION13_TARGET_METHOD:
            pfba_run = current_run

    comparison_complete = bool(fba_run and pfba_run)
    primary_objective_preserved = False
    external_fingerprint_preserved = False
    same_controlled_setup = False
    pfba_not_less_parsimonious = False
    parsimony_classification = None
    total_flux_change = None
    comparison_issues = []

    if comparison_complete:
        primary_difference = float(pfba_run['primary_objective_flux']) - float(fba_run['primary_objective_flux'])
        primary_objective_preserved = abs(primary_difference) <= MISSION13_PRIMARY_TOLERANCE
        if not primary_objective_preserved:
            comparison_issues.append('pFBA must preserve the primary succinate optimum reached by the FBA reference.')

        fingerprint_differences = {
            rid: float(pfba_run['tracked_flux_values'][rid]) - float(fba_run['tracked_flux_values'][rid])
            for rid in MISSION13_REQUIRED_TRACKED_FLUXES
        }
        external_fingerprint_preserved = all(
            abs(value) <= MISSION13_FLUX_TOLERANCE
            for value in fingerprint_differences.values()
        )
        if not external_fingerprint_preserved:
            comparison_issues.append('The complete external target/byproduct fingerprint should be preserved between these FBA and pFBA runs.')

        same_controlled_setup = (
            abs(float(pfba_run['biomass_flux']) - float(fba_run['biomass_flux'])) <= MISSION13_FLUX_TOLERANCE
            and abs(float(pfba_run['glucose_uptake']) - float(fba_run['glucose_uptake'])) <= MISSION13_FLUX_TOLERANCE
            and abs(float(pfba_run['oxygen_uptake']) - float(fba_run['oxygen_uptake'])) <= MISSION13_FLUX_TOLERANCE
        )
        if not same_controlled_setup:
            comparison_issues.append('Biomass and medium evidence must remain identical so the simulation method is the only changed variable.')

        total_flux_change = float(pfba_run['total_absolute_flux']) - float(fba_run['total_absolute_flux'])
        pfba_not_less_parsimonious = total_flux_change <= MISSION13_PARSIMONY_TOLERANCE
        if not pfba_not_less_parsimonious:
            comparison_issues.append('The pFBA solution cannot use more total absolute flux than the compared FBA solution beyond numerical tolerance.')
        elif total_flux_change < -MISSION13_PARSIMONY_TOLERANCE:
            parsimony_classification = 'reduced_total_flux'
        else:
            parsimony_classification = 'equal_fba_already_parsimonious'

    evidence_ready = comparison_complete and not comparison_issues
    data = {
        'mission_id': '13',
        'check_version': MISSION13_CHECK_VERSION,
        'mission_title': 'Primary Objective and Flux Parsimony',
        'baseline_method': MISSION13_BASELINE_METHOD,
        'target_method': MISSION13_TARGET_METHOD,
        'target_product': MISSION13_TARGET_PRODUCT,
        'target_objective': MISSION13_TARGET_OBJECTIVE,
        'required_tracked_fluxes': list(MISSION13_REQUIRED_TRACKED_FLUXES),
        'product_names': dict(MISSION13_PRODUCT_NAMES),
        'fba_run': fba_run,
        'pfba_run': pfba_run,
        'mission12_baseline_available': mission12_baseline_available,
        'mission12_baseline_imported': bool(imported_baseline and fba_run and fba_run.get('source') == 'mission12_visible_run'),
        'comparison_complete': comparison_complete,
        'same_controlled_setup': same_controlled_setup,
        'primary_objective_preserved': primary_objective_preserved,
        'external_fingerprint_preserved': external_fingerprint_preserved,
        'pfba_not_less_parsimonious': pfba_not_less_parsimonious,
        'parsimony_classification': parsimony_classification,
        'total_flux_change': round(float(total_flux_change), 6) if total_flux_change is not None else None,
        'comparison_issues': comparison_issues,
        'evidence_ready': evidence_ready,
        'answer_ready': evidence_ready,
        'ready_to_deliver': evidence_ready,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_valid,
        'current_run_type': current_run_type,
        'current_method': method_name,
        'current_objective': selected_objective,
        'current_primary_objective_flux': round(float(primary_objective_flux), 6) if primary_objective_flux is not None else None,
        'current_method_score': round(float(method_score), 6) if method_score is not None else None,
        'current_method_score_name': method_score_name,
        'current_total_absolute_flux': round(float(total_absolute_flux), 6) if total_absolute_flux is not None else None,
        'current_active_reaction_count': active_reaction_count,
        'current_tracked_flux_values': {rid: round(float(value), 6) for rid, value in measured_fluxes.items()},
        'current_biomass_flux': round(float(biomass_flux), 6) if biomass_flux is not None else None,
        'current_glucose_uptake': round(float(glucose_uptake), 6) if glucose_uptake is not None else None,
        'current_oxygen_uptake': round(float(oxygen_uptake), 6) if oxygen_uptake is not None else None,
        'current_knocked_out_genes': knocked_out_genes,
        'current_oxygen_lower_bound_closed': oxygen_closed,
        'current_unexpected_environment_changes': unexpected_changes,
        'selected_production_fluxes': selected_fluxes,
        'missing_selected_fluxes': missing_selected,
        'missing_measured_fluxes': missing_measured,
        'current_issues': issues,
        'latest_attempt': {
            'valid': current_run_valid,
            'run_type': current_run_type,
            'method': method_name,
            'objective': selected_objective,
            'issues': list(issues),
        },
        # Temporary compatibility fields for the not-yet-reconstructed Mission 14.
        'method': MISSION13_TARGET_METHOD if pfba_run else method_name,
        'target_flux': pfba_run.get('primary_objective_flux') if pfba_run else None,
        'tracked_flux_values': copy.deepcopy(pfba_run.get('tracked_flux_values')) if pfba_run else {},
    }
    save_mission13_method_check(data)
    return data


def run_mission13_method_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible FBA or pFBA simulation before recording Mission 13 evidence.'
    except Exception:
        objective_error = 'Could not read the current visible simulation result.'

    return _build_mission13_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission13_method_check(),
        objective_error=objective_error,
    )


def normalise_mission13_answer(answer):
    compact = ''.join(char.lower() for char in str(answer or '') if char.isalnum())
    aliases = {
        'totalflux': MISSION13_EXPECTED_SECONDARY_CRITERION,
        'totalabsoluteflux': MISSION13_EXPECTED_SECONDARY_CRITERION,
        'sumofabsolutefluxes': MISSION13_EXPECTED_SECONDARY_CRITERION,
        'sumabsolutevaluesoffluxes': MISSION13_EXPECTED_SECONDARY_CRITERION,
        'sumofabsolutevaluesoffluxes': MISSION13_EXPECTED_SECONDARY_CRITERION,
        'fluxsum': MISSION13_EXPECTED_SECONDARY_CRITERION,
        'absolutefluxsum': MISSION13_EXPECTED_SECONDARY_CRITERION,
        'fluxototal': MISSION13_EXPECTED_SECONDARY_CRITERION,
        'somadosfluxosabsolutos': MISSION13_EXPECTED_SECONDARY_CRITERION,
        'somadosvaloresabsolutosdosfluxos': MISSION13_EXPECTED_SECONDARY_CRITERION,
    }
    return aliases.get(compact)


def mission13_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission13_method_check() or {}
    prepared = _prepare_mission13_report(report_data)
    return bool(
        prepared.get('evidence_ready')
        and normalise_mission13_answer(answer) == MISSION13_EXPECTED_SECONDARY_CRITERION
    )


def build_mission13_parsimony_report_text(report_data=None):
    if report_data is None:
        report_data = load_mission13_method_check() or {}
    report = _prepare_mission13_report(report_data)
    fba_run = report.get('fba_run')
    pfba_run = report.get('pfba_run')
    lines = ['Mission 13 Primary Objective and Flux Parsimony', '']

    if not report:
        lines.extend([
            'Build a controlled FBA-versus-pFBA comparison for the oxygen-constrained succinate objective.',
            'Keep objective, genes, medium and the complete exchange panel identical; change only the simulation method.',
        ])
    else:
        lines.extend([
            'Controlled comparison: same model; objective EX_succ_e; all genes active; default glucose supply; oxygen uptake disabled; complete target/byproduct panel.',
            'Only the simulation method may differ.',
        ])

    def append_run(title, run, include_secondary=False):
        lines.extend(['', title + ':'])
        if not run:
            lines.append('- Not recorded yet')
            return
        values = run.get('tracked_flux_values') or {}
        lines.extend([
            f"- Primary succinate flux: {_clean_display_number(run.get('primary_objective_flux', 0.0)):.3f}",
            f"- Acetate: {_clean_display_number(values.get('EX_ac_e', 0.0)):.3f}",
            f"- Formate: {_clean_display_number(values.get('EX_for_e', 0.0)):.3f}",
            f"- Ethanol: {_clean_display_number(values.get('EX_etoh_e', 0.0)):.3f}",
            f"- D-lactate: {_clean_display_number(values.get('EX_lac__D_e', 0.0)):.3f}",
            f"- Predicted biomass flux: {_clean_display_number(run.get('biomass_flux', 0.0)):.3f}",
            f"- Glucose uptake: {_clean_display_number(run.get('glucose_uptake', 0.0)):.3f}",
            f"- Oxygen uptake: {_clean_display_number(run.get('oxygen_uptake', 0.0)):.3f}",
            f"- Total absolute flux of returned solution: {_clean_display_number(run.get('total_absolute_flux', 0.0)):.3f}",
            f"- Active reactions: {int(run.get('active_reaction_count', 0))}",
        ])
        if include_secondary:
            score = run.get('method_score')
            lines.append(f"- pFBA secondary score ({run.get('method_score_name')}): {_clean_display_number(score or 0.0):.3f}")

    append_run('FBA reference', fba_run)
    append_run('pFBA run', pfba_run, include_secondary=True)

    if report.get('current_run_valid'):
        lines.extend(['', 'Latest valid visible run recorded: ' + str(report.get('current_method')) + '.'])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if fba_run or pfba_run:
            lines.append('Previously valid Mission 13 evidence remains available.')

    lines.append('')
    if report.get('comparison_complete'):
        lines.append('Primary objective preserved: ' + ('yes' if report.get('primary_objective_preserved') else 'no'))
        lines.append('External fingerprint preserved: ' + ('yes' if report.get('external_fingerprint_preserved') else 'no'))
        change = report.get('total_flux_change')
        if change is not None:
            lines.append(f"pFBA minus FBA total absolute flux: {float(change):+.3f}")
        if report.get('parsimony_classification') == 'reduced_total_flux':
            lines.append('Parsimony interpretation: pFBA selected a solution with lower total absolute flux.')
        elif report.get('parsimony_classification') == 'equal_fba_already_parsimonious':
            lines.append('Parsimony interpretation: the FBA solver had already returned a solution with the same total flux; pFBA makes that secondary criterion explicit.')
        if report.get('comparison_issues'):
            lines.append('Comparison issues:')
            lines.extend(f'- {issue}' for issue in report.get('comparison_issues') or [])

    lines.append('')
    if report.get('evidence_ready'):
        lines.append('Evidence complete. State what quantity the pFBA secondary criterion minimises and submit it to Dr. Almeida.')
    else:
        missing = []
        if not fba_run:
            missing.append('controlled FBA reference')
        if not pfba_run:
            missing.append('controlled pFBA run')
        if missing:
            lines.append('Evidence incomplete. Missing: ' + ', '.join(missing) + '.')
            if report.get('mission12_baseline_available') and not report.get('mission12_baseline_imported') and not fba_run:
                lines.append('The Mission 12 fingerprint exists, but it predates the method-diagnostic fields; repeat the FBA run once to record total flux and active reactions.')
        else:
            lines.append('Both runs are present, but the controlled method comparison is not yet scientifically consistent.')

    lines.extend([
        '',
        'Interpretation note: pFBA did not maximise hundreds of units of succinate. The primary succinate flux is the EX_succ_e reaction flux shown separately.',
        'pFBA first preserves the primary optimum and then minimises total absolute flux as a secondary criterion.',
        'The external fingerprint can remain unchanged. Equality of FBA and pFBA total flux is valid when the FBA solver already returned a parsimonious optimum.',
        'All objective, product, biomass, medium and parsimony values come from the same visible solver results. No hidden simulation is used.',
    ])
    return '\n'.join(lines)


def is_mission14_unlocked(missions_completed):
    """Mission 14 starts only after the Mission 13 method comparison."""
    return '13' in (missions_completed or [])


def _mission14_report_is_current(report_data):
    return bool(
        isinstance(report_data, dict)
        and report_data.get('mission_id') == '14'
        and report_data.get('check_version') == MISSION14_CHECK_VERSION
    )


def _prepare_mission14_report(report_data):
    if not _mission14_report_is_current(report_data):
        return {}
    return copy.deepcopy(report_data)


def _mission14_measured_fluxes(production_fluxes):
    """Return only numeric values from the required visible exchange panel."""
    return {
        reaction_id: value
        for reaction_id, value in _mission13_measured_fluxes(production_fluxes).items()
        if reaction_id in MISSION14_REQUIRED_TRACKED_FLUXES
    }


def _mission14_biomass_value(production_fluxes):
    return _mission13_biomass_value(production_fluxes)


def _mission14_medium_evidence(medium_fluxes):
    return _mission13_medium_evidence(medium_fluxes)


def _mission14_import_mission13_baseline():
    """Reuse the completed visible pFBA run from Mission 13 as baseline.

    No simulation is launched here.  The imported values were already produced
    by the player's visible Mission 13 pFBA result, keeping the same evidence
    contract valid for desktop and web clients.
    """
    report = load_mission13_method_check()
    if not (
        isinstance(report, dict)
        and report.get('mission_id') == '13'
        and report.get('check_version') == MISSION13_CHECK_VERSION
        and report.get('evidence_ready')
    ):
        return None, False

    source = report.get('pfba_run')
    if not isinstance(source, dict):
        return None, True
    tracked = source.get('tracked_flux_values') or {}
    required_numeric = [
        source.get('primary_objective_flux'),
        source.get('biomass_flux'),
        source.get('glucose_uptake'),
        source.get('oxygen_uptake'),
        source.get('total_absolute_flux'),
        source.get('active_reaction_count'),
    ]
    if any(_as_float_or_none(value) is None for value in required_numeric):
        return None, True
    if any(_as_float_or_none(tracked.get(rid)) is None for rid in MISSION14_REQUIRED_TRACKED_FLUXES):
        return None, True
    if source.get('method') != MISSION14_TARGET_METHOD or source.get('objective') != MISSION14_TARGET_OBJECTIVE:
        return None, True

    baseline = {
        'run_type': 'baseline',
        'source': 'mission13_visible_pfba_run',
        'method': MISSION14_TARGET_METHOD,
        'objective': MISSION14_TARGET_OBJECTIVE,
        'primary_objective_flux': round(float(source['primary_objective_flux']), 6),
        'method_score': round(float(source.get('method_score')), 6) if _as_float_or_none(source.get('method_score')) is not None else None,
        'method_score_name': source.get('method_score_name'),
        'total_absolute_flux': round(float(source['total_absolute_flux']), 6),
        'active_reaction_count': int(source['active_reaction_count']),
        'tracked_flux_values': {
            rid: round(float(tracked[rid]), 6)
            for rid in MISSION14_REQUIRED_TRACKED_FLUXES
        },
        'biomass_flux': round(float(source['biomass_flux']), 6),
        'glucose_uptake': round(float(source['glucose_uptake']), 6),
        'oxygen_uptake': round(float(source['oxygen_uptake']), 6),
        'knocked_out_genes': [],
    }
    return baseline, True


def initialise_mission14_tradeoff_screening():
    """Create the empty current-format state and import Mission 13 evidence.

    This function only copies an already visible, persisted pFBA result.  It
    never launches a solver run and keeps activation deterministic for both
    desktop and web clients.
    """
    baseline, mission13_available = _mission14_import_mission13_baseline()
    data = {
        'mission_id': '14',
        'check_version': MISSION14_CHECK_VERSION,
        'mission_title': 'Byproduct Trade-off Screening',
        'target_method': MISSION14_TARGET_METHOD,
        'target_product': MISSION14_TARGET_PRODUCT,
        'target_objective': MISSION14_TARGET_OBJECTIVE,
        'coproduct_product': MISSION14_COPRODUCT_PRODUCT,
        'coproduct_flux': MISSION14_COPRODUCT_FLUX,
        'required_tracked_fluxes': list(MISSION14_REQUIRED_TRACKED_FLUXES),
        'candidate_genes': list(MISSION14_CANDIDATE_GENES),
        'candidate_gene_names': dict(MISSION14_GENE_NAMES),
        'baseline': baseline,
        'baseline_recorded': bool(baseline),
        'mission13_baseline_available': mission13_available,
        'mission13_baseline_imported': bool(baseline),
        'trials': {},
        'valid_trial_count': 0,
        'required_trial_count': len(MISSION14_CANDIDATE_GENES),
        'missing_candidates': list(MISSION14_CANDIDATE_GENES),
        'comparison_complete': False,
        'clean_candidates': [],
        'clean_candidate_count': 0,
        'no_clean_candidate': False,
        'winning_candidate': None,
        'conclusion': None,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_run_valid': False,
        'current_run_recorded': False,
        'current_run_type': None,
        'current_issues': [],
        'latest_attempt': None,
    }
    save_mission14_reduction_check(data)
    return data


def _mission14_product_label(reaction_id):
    return f"{MISSION14_PRODUCT_NAMES.get(reaction_id, reaction_id)} ({reaction_id})"


def _mission14_gene_label(gene_id):
    return f"{gene_id} ({MISSION14_GENE_NAMES.get(gene_id, GENE_NAMES.get(gene_id, ''))})"


def _mission14_assessment(trial):
    if trial.get('clean_improvement'):
        return 'eligible clean improvement'
    if not trial.get('target_retained'):
        if trial.get('new_positive_byproducts'):
            return 'acetate may decrease, but succinate retention fails and new co-products appear'
        return 'succinate retention is below the mission criterion'
    if trial.get('acetate_reduced') and trial.get('new_positive_byproducts'):
        labels = ', '.join(
            MISSION14_PRODUCT_NAMES.get(rid, rid)
            for rid in trial.get('new_positive_byproducts') or []
        )
        return f'acetate decreases, but new positive co-products appear: {labels}'
    if not trial.get('acetate_reduced'):
        return 'target is retained, but there is no meaningful acetate reduction'
    return 'the complete fingerprint does not satisfy all clean-improvement criteria'


def _mission14_normalise_trials(trials, baseline):
    """Recalculate every candidate assessment from the stored visible values."""
    normalized = {}
    baseline_values = (baseline or {}).get('tracked_flux_values') or {}
    baseline_target = _as_float_or_none(baseline_values.get(MISSION14_TARGET_OBJECTIVE))
    baseline_acetate = _as_float_or_none(baseline_values.get(MISSION14_COPRODUCT_FLUX))

    for gene_id in MISSION14_CANDIDATE_GENES:
        raw = (trials or {}).get(gene_id)
        if not isinstance(raw, dict):
            continue
        trial = copy.deepcopy(raw)
        values = trial.get('tracked_flux_values') or {}
        target = _as_float_or_none(values.get(MISSION14_TARGET_OBJECTIVE))
        acetate = _as_float_or_none(values.get(MISSION14_COPRODUCT_FLUX))
        if target is None or acetate is None:
            continue

        target_ratio = None
        target_retention_percent = None
        acetate_change = None
        acetate_reduction = None
        if baseline_target is not None and baseline_target > MISSION14_FLUX_TOLERANCE:
            target_ratio = target / baseline_target
            target_retention_percent = target_ratio * 100.0
        if baseline_acetate is not None:
            acetate_change = acetate - baseline_acetate
            acetate_reduction = baseline_acetate - acetate

        new_positive_byproducts = []
        for reaction_id in MISSION14_POTENTIAL_NEW_BYPRODUCTS:
            baseline_value = _as_float_or_none(baseline_values.get(reaction_id))
            trial_value = _as_float_or_none(values.get(reaction_id))
            if baseline_value is None or trial_value is None:
                continue
            if (
                baseline_value <= MISSION14_NEW_BYPRODUCT_THRESHOLD
                and trial_value > MISSION14_NEW_BYPRODUCT_THRESHOLD
            ):
                new_positive_byproducts.append(reaction_id)

        target_retained = target_ratio is not None and target_ratio >= MISSION14_MIN_TARGET_RETENTION
        acetate_reduced = (
            acetate_reduction is not None
            and acetate_reduction >= MISSION14_MIN_ACETATE_REDUCTION
        )
        no_new_byproducts = not new_positive_byproducts
        clean_improvement = target_retained and acetate_reduced and no_new_byproducts
        trial.update({
            'target_flux': round(float(target), 6),
            'acetate_flux': round(float(acetate), 6),
            'target_ratio': round(float(target_ratio), 6) if target_ratio is not None else None,
            'target_retention_percent': round(float(target_retention_percent), 1) if target_retention_percent is not None else None,
            'acetate_change': round(float(acetate_change), 6) if acetate_change is not None else None,
            'acetate_reduction': round(float(acetate_reduction), 6) if acetate_reduction is not None else None,
            'target_retained': target_retained,
            'acetate_reduced': acetate_reduced,
            'new_positive_byproducts': new_positive_byproducts,
            'no_new_byproducts': no_new_byproducts,
            'clean_improvement': clean_improvement,
        })
        trial['assessment'] = _mission14_assessment(trial)
        normalized[gene_id] = trial
    return normalized


def _build_mission14_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
    selected_fluxes=None,
):
    """Validate and accumulate one visible Mission 14 screening run."""
    previous = _prepare_mission14_report(existing_report)
    baseline = copy.deepcopy(previous.get('baseline')) if previous else None
    trials = copy.deepcopy(previous.get('trials') or {}) if previous else {}

    imported_baseline, mission13_baseline_available = _mission14_import_mission13_baseline()
    if baseline is None and imported_baseline is not None:
        baseline = imported_baseline

    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = list(selected_fluxes) if selected_fluxes is not None else _read_selected_production_fluxes()
    measured_fluxes = _mission14_measured_fluxes(production_fluxes)
    diagnostics = _method_diagnostics_from_production_data(production_fluxes)
    display_objective_value = _as_float_or_none(objective_result)
    primary_objective_flux = _as_float_or_none(diagnostics.get('primary_objective_flux'))
    if primary_objective_flux is None and isinstance(production_fluxes, dict):
        primary_objective_flux = _as_float_or_none(production_fluxes.get('objective_raw'))
    target_flux = measured_fluxes.get(MISSION14_TARGET_OBJECTIVE)
    biomass_flux = _mission14_biomass_value(production_fluxes)
    glucose_uptake, oxygen_uptake = _mission14_medium_evidence(medium_fluxes)
    total_absolute_flux = _as_float_or_none(diagnostics.get('total_absolute_flux'))
    method_score = _as_float_or_none(diagnostics.get('method_score'))
    method_score_name = diagnostics.get('method_score_name')
    active_reaction_count = diagnostics.get('active_reaction_count')
    try:
        active_reaction_count = int(active_reaction_count) if active_reaction_count is not None else None
    except Exception:
        active_reaction_count = None

    oxygen_closed, unexpected_changes = _mission14_environment_status(reactions)
    missing_selected = [rid for rid in MISSION14_REQUIRED_TRACKED_FLUXES if rid not in selected_fluxes]
    missing_measured = [rid for rid in MISSION14_REQUIRED_TRACKED_FLUXES if rid not in measured_fluxes]
    is_baseline = len(knocked_out_genes) == 0
    exactly_one = len(knocked_out_genes) == 1
    candidate_gene = knocked_out_genes[0] if exactly_one and knocked_out_genes[0] in MISSION14_CANDIDATE_GENES else None

    issues = []
    if objective_error:
        issues.append(objective_error)
    if method_name != MISSION14_TARGET_METHOD:
        issues.append('Use pFBA for the baseline and every candidate trade-off run.')
    if selected_objective != MISSION14_TARGET_OBJECTIVE:
        issues.append(f'Use {MISSION14_TARGET_OBJECTIVE} as the primary objective in every Mission 14 run.')
    if not oxygen_closed:
        issues.append(f'Disable oxygen uptake by closing only the lower bound of {MISSION14_OXYGEN_REACTION}.')
    if unexpected_changes:
        issues.append('Keep glucose and every other environmental bound at the model-default state.')
    if missing_selected:
        issues.append('Select the complete target/co-product panel in Production Flux: ' + ', '.join(missing_selected) + '.')
    if missing_measured:
        issues.append('The visible solution did not provide numeric evidence for: ' + ', '.join(missing_measured) + '.')

    if not is_baseline:
        if not exactly_one:
            issues.append('Use either no knockout for the reference or exactly one candidate knockout per screening run.')
        elif candidate_gene is None:
            issues.append('The single knocked-out gene must belong to the Mission 14 candidate list.')

    if primary_objective_flux is None:
        issues.append('The visible result did not provide the primary EX_succ_e objective flux separately from the pFBA score.')
    elif primary_objective_flux < MISSION14_MIN_TARGET_FLUX:
        issues.append('The visible solution did not retain a positive theoretical succinate optimum.')
    if target_flux is None:
        issues.append('Tracked succinate secretion was not measured numerically in the visible solution.')
    elif primary_objective_flux is not None and abs(float(target_flux) - float(primary_objective_flux)) > MISSION14_PRIMARY_TOLERANCE:
        issues.append('The tracked succinate flux does not match the primary EX_succ_e flux from the same visible solution.')
    if display_objective_value is not None and primary_objective_flux is not None and abs(float(display_objective_value) - float(primary_objective_flux)) > MISSION14_PRIMARY_TOLERANCE:
        issues.append('New Results is not displaying the primary succinate reaction flux consistently.')

    if biomass_flux is None:
        issues.append('The visible solution did not provide a numeric biomass flux.')
    elif biomass_flux > MISSION14_MAX_BIOMASS_FLUX:
        issues.append('These direct succinate-optimal screening runs should show approximately zero predicted biomass flux.')
    if glucose_uptake is None:
        issues.append('The Exchange Flux Report did not provide numeric glucose-uptake evidence.')
    elif abs(float(glucose_uptake) - MISSION14_DEFAULT_GLUCOSE_UPTAKE) > MISSION14_FLUX_TOLERANCE:
        issues.append('Keep the model-default glucose supply unchanged in every screening run.')
    if oxygen_uptake is None:
        issues.append('The Exchange Flux Report did not provide numeric oxygen-uptake evidence.')
    elif oxygen_uptake > MISSION14_FLUX_TOLERANCE:
        issues.append('The visible solution still uses oxygen; Mission 14 must remain anaerobic.')

    if total_absolute_flux is None:
        issues.append('The visible pFBA result did not provide total absolute flux.')
    if active_reaction_count is None:
        issues.append('The visible pFBA result did not provide an active-reaction count.')
    if method_score is None:
        issues.append('The visible pFBA result did not provide its secondary parsimony score.')
    if method_score_name != MISSION14_EXPECTED_SECONDARY_CRITERION:
        issues.append('The pFBA secondary score must be identified as total absolute flux.')
    if method_score is not None and total_absolute_flux is not None and abs(method_score - total_absolute_flux) > MISSION14_PARSIMONY_TOLERANCE:
        issues.append('The pFBA secondary score is inconsistent with the total absolute flux of the visible solution.')

    if is_baseline and not missing_measured:
        if measured_fluxes.get(MISSION14_COPRODUCT_FLUX, 0.0) <= MISSION14_FLUX_TOLERANCE:
            issues.append('The no-knockout reference should show acetate as the positive co-product.')
        for reaction_id in MISSION14_POTENTIAL_NEW_BYPRODUCTS:
            if abs(measured_fluxes.get(reaction_id, 0.0)) > MISSION14_FLUX_TOLERANCE:
                issues.append(f'{_mission14_product_label(reaction_id)} should remain approximately zero in the no-knockout reference.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run_type = 'invalid'
    current_run = None
    if current_run_valid:
        current_run = {
            'run_type': 'baseline' if is_baseline else 'candidate',
            'source': 'visible_simulation',
            'method': method_name,
            'objective': selected_objective,
            'primary_objective_flux': round(float(primary_objective_flux), 6),
            'method_score': round(float(method_score), 6),
            'method_score_name': method_score_name,
            'total_absolute_flux': round(float(total_absolute_flux), 6),
            'active_reaction_count': int(active_reaction_count),
            'tracked_flux_values': {
                rid: round(float(measured_fluxes[rid]), 6)
                for rid in MISSION14_REQUIRED_TRACKED_FLUXES
            },
            'biomass_flux': round(float(biomass_flux), 6),
            'glucose_uptake': round(float(glucose_uptake), 6),
            'oxygen_uptake': round(
                0.0 if abs(float(oxygen_uptake)) < DISPLAY_ZERO_TOLERANCE else float(oxygen_uptake),
                6,
            ),
            'knocked_out_genes': list(knocked_out_genes),
        }
        if is_baseline:
            baseline = current_run
            current_run_type = 'baseline'
        else:
            current_run.update({
                'gene_id': candidate_gene,
                'gene_name': MISSION14_GENE_NAMES.get(candidate_gene, GENE_NAMES.get(candidate_gene, '')),
                'expected_disabled_reactions': list(MISSION14_EXPECTED_DISABLED_REACTIONS.get(candidate_gene, [])),
            })
            trials[candidate_gene] = current_run
            current_run_type = 'candidate'
        current_run_recorded = True

    trials = _mission14_normalise_trials(trials, baseline)
    missing_candidates = [gene_id for gene_id in MISSION14_CANDIDATE_GENES if gene_id not in trials]
    baseline_recorded = bool(baseline)
    comparison_complete = baseline_recorded and not missing_candidates
    clean_candidates = [
        gene_id for gene_id in MISSION14_CANDIDATE_GENES
        if (trials.get(gene_id) or {}).get('clean_improvement')
    ]
    no_clean_candidate = comparison_complete and not clean_candidates
    winning_candidate = clean_candidates[0] if len(clean_candidates) == 1 else None
    conclusion = None
    if comparison_complete:
        if not clean_candidates:
            conclusion = 'none'
        elif len(clean_candidates) == 1:
            conclusion = winning_candidate
        else:
            conclusion = 'ambiguous'
    evidence_ready = comparison_complete and conclusion != 'ambiguous'

    data = {
        'mission_id': '14',
        'check_version': MISSION14_CHECK_VERSION,
        'mission_title': 'Byproduct Trade-off Screening',
        'target_method': MISSION14_TARGET_METHOD,
        'target_product': MISSION14_TARGET_PRODUCT,
        'target_objective': MISSION14_TARGET_OBJECTIVE,
        'coproduct_product': MISSION14_COPRODUCT_PRODUCT,
        'coproduct_flux': MISSION14_COPRODUCT_FLUX,
        'oxygen_reaction': MISSION14_OXYGEN_REACTION,
        'glucose_reaction': MISSION14_GLUCOSE_REACTION,
        'required_tracked_fluxes': list(MISSION14_REQUIRED_TRACKED_FLUXES),
        'product_names': dict(MISSION14_PRODUCT_NAMES),
        'candidate_genes': list(MISSION14_CANDIDATE_GENES),
        'candidate_gene_names': dict(MISSION14_GENE_NAMES),
        'expected_disabled_reactions': copy.deepcopy(MISSION14_EXPECTED_DISABLED_REACTIONS),
        'baseline': baseline,
        'baseline_recorded': baseline_recorded,
        'mission13_baseline_available': mission13_baseline_available,
        'mission13_baseline_imported': bool(baseline and baseline.get('source') == 'mission13_visible_pfba_run'),
        'trials': trials,
        'valid_trial_count': len(trials),
        'required_trial_count': len(MISSION14_CANDIDATE_GENES),
        'missing_candidates': missing_candidates,
        'comparison_complete': comparison_complete,
        'minimum_target_retention': MISSION14_MIN_TARGET_RETENTION,
        'minimum_acetate_reduction': MISSION14_MIN_ACETATE_REDUCTION,
        'new_byproduct_threshold': MISSION14_NEW_BYPRODUCT_THRESHOLD,
        'clean_candidates': clean_candidates,
        'clean_candidate_count': len(clean_candidates),
        'no_clean_candidate': no_clean_candidate,
        'winning_candidate': winning_candidate,
        'conclusion': conclusion,
        'expected_conclusion': MISSION14_EXPECTED_CONCLUSION,
        'expected_conclusion_confirmed': conclusion == MISSION14_EXPECTED_CONCLUSION,
        'evidence_ready': evidence_ready,
        'answer_ready': evidence_ready,
        'ready_to_deliver': evidence_ready,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': current_run_type,
        'current_candidate_gene': candidate_gene,
        'current_method': method_name,
        'current_objective': selected_objective,
        'current_knocked_out_genes': knocked_out_genes,
        'current_primary_objective_flux': round(float(primary_objective_flux), 6) if primary_objective_flux is not None else None,
        'current_method_score': round(float(method_score), 6) if method_score is not None else None,
        'current_method_score_name': method_score_name,
        'current_total_absolute_flux': round(float(total_absolute_flux), 6) if total_absolute_flux is not None else None,
        'current_active_reaction_count': active_reaction_count,
        'current_tracked_flux_values': {rid: round(float(value), 6) for rid, value in measured_fluxes.items()},
        'current_biomass_flux': round(float(biomass_flux), 6) if biomass_flux is not None else None,
        'current_glucose_uptake': round(float(glucose_uptake), 6) if glucose_uptake is not None else None,
        'current_oxygen_uptake': round(float(oxygen_uptake), 6) if oxygen_uptake is not None else None,
        'current_oxygen_lower_bound_closed': oxygen_closed,
        'current_unexpected_environment_changes': unexpected_changes,
        'selected_production_fluxes': selected_fluxes,
        'missing_selected_fluxes': missing_selected,
        'missing_measured_fluxes': missing_measured,
        'full_panel_measured': not missing_measured,
        'current_issues': issues,
        'latest_attempt': {
            'valid': current_run_valid,
            'run_type': current_run_type,
            'candidate_gene': candidate_gene,
            'method': method_name,
            'objective': selected_objective,
            'issues': list(issues),
        },
        # Compatibility summary values for older downstream readers. They
        # come from the visible baseline and preserve the current acetate-screen
        # interpretation.
        'method': MISSION14_TARGET_METHOD,
        'target_flux': (baseline or {}).get('primary_objective_flux'),
        'tracked_flux_values': copy.deepcopy((baseline or {}).get('tracked_flux_values') or {}),
    }
    save_mission14_reduction_check(data)
    return data


def run_mission14_reduction_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible pFBA baseline or candidate simulation before recording Mission 14 evidence.'
    except Exception:
        objective_error = 'Could not read the current visible simulation result.'

    return _build_mission14_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission14_reduction_check(),
        objective_error=objective_error,
    )


def normalise_mission14_answer(answer):
    compact = ''.join(char.lower() for char in str(answer or '') if char.isalnum())
    none_aliases = {
        'none', 'nocandidate', 'nocleancandidate', 'noneofthem', 'neither',
        'nenhum', 'nenhumcandidato', 'nenhumdeles', 'nenhumamelhoria',
        'semcandidato', 'naohacandidato', 'naohamelhoria',
    }
    if compact in none_aliases:
        return 'none'

    aliases = {}
    for gene_id in MISSION14_CANDIDATE_GENES:
        gene_name = MISSION14_GENE_NAMES.get(gene_id, '')
        for value in (gene_id, gene_id[1:] if gene_id.startswith('b') else gene_id, gene_name, gene_id + gene_name, gene_name + gene_id):
            alias = ''.join(char.lower() for char in str(value) if char.isalnum())
            if alias:
                aliases[alias] = gene_id
    return aliases.get(compact)


def mission14_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission14_reduction_check() or {}
    report = _prepare_mission14_report(report_data)
    return bool(
        report.get('evidence_ready')
        and report.get('conclusion') not in (None, 'ambiguous')
        and normalise_mission14_answer(answer) == report.get('conclusion')
    )


def build_mission14_tradeoff_report_text(report_data=None):
    if report_data is None:
        report_data = load_mission14_reduction_check() or {}
    report = _prepare_mission14_report(report_data)
    baseline = report.get('baseline')
    trials = report.get('trials') or {}
    lines = ['Mission 14 Byproduct Trade-off Screening', '']

    if not baseline and not trials:
        lines.extend([
            'Screen the four single-gene interventions under one controlled pFBA succinate-optimal setup.',
            'Use the complete target/co-product panel and decide whether any candidate reduces acetate cleanly without sacrificing too much succinate or creating new positive co-products.',
            '',
            f'Candidate trials recorded: 0/{len(MISSION14_CANDIDATE_GENES)}',
        ])
    else:
        lines.extend([
            'Controlled setup for recorded evidence: pFBA; primary objective EX_succ_e; default glucose supply; oxygen uptake disabled; complete target/co-product panel; no knockout for the reference and exactly one candidate knockout per trial.',
            '',
        ])
        if baseline:
            values = baseline.get('tracked_flux_values') or {}
            lines.extend([
                'Reference:',
                f"- Succinate: {_clean_display_number(values.get('EX_succ_e', 0.0)):.3f}",
                f"- Acetate: {_clean_display_number(values.get('EX_ac_e', 0.0)):.3f}",
                f"- Formate: {_clean_display_number(values.get('EX_for_e', 0.0)):.3f}",
                f"- Ethanol: {_clean_display_number(values.get('EX_etoh_e', 0.0)):.3f}",
                f"- D-lactate: {_clean_display_number(values.get('EX_lac__D_e', 0.0)):.3f}",
                f"- Predicted biomass flux: {_clean_display_number(baseline.get('biomass_flux', 0.0)):.3f}",
                f"- Glucose uptake: {_clean_display_number(baseline.get('glucose_uptake', 0.0)):.3f}",
                f"- Oxygen uptake: {_clean_display_number(baseline.get('oxygen_uptake', 0.0)):.3f}",
                f"- Total absolute flux: {_clean_display_number(baseline.get('total_absolute_flux', 0.0)):.3f}",
                f"- Active reactions: {int(baseline.get('active_reaction_count', 0))}",
            ])
            if baseline.get('source') == 'mission13_visible_pfba_run':
                lines.append('- Source: visible pFBA evidence imported from the completed Mission 13 comparison')
        else:
            lines.append('Reference: not recorded or importable yet')

        lines.extend([
            '',
            f"Candidate trials recorded: {len(trials)}/{len(MISSION14_CANDIDATE_GENES)}",
            '',
            'Candidate screen:',
        ])
        for gene_id in MISSION14_CANDIDATE_GENES:
            trial = trials.get(gene_id)
            label = _mission14_gene_label(gene_id)
            if not trial:
                lines.append(f'- {label}: pending')
                continue
            values = trial.get('tracked_flux_values') or {}
            retention = trial.get('target_retention_percent')
            retention_text = f'{float(retention):.1f}% of reference' if retention is not None else 'reference missing'
            reduction = trial.get('acetate_reduction')
            reduction_text = f'{float(reduction):+.3f}' if reduction is not None else 'reference missing'
            new_products = trial.get('new_positive_byproducts') or []
            new_text = ', '.join(_mission14_product_label(rid) for rid in new_products) if new_products else 'none'
            lines.append(
                f"- {label}: succinate {_clean_display_number(values.get('EX_succ_e', 0.0)):.3f} ({retention_text}); "
                f"acetate {_clean_display_number(values.get('EX_ac_e', 0.0)):.3f} (reduction {reduction_text}); "
                f"formate {_clean_display_number(values.get('EX_for_e', 0.0)):.3f}; "
                f"ethanol {_clean_display_number(values.get('EX_etoh_e', 0.0)):.3f}; "
                f"D-lactate {_clean_display_number(values.get('EX_lac__D_e', 0.0)):.3f}; "
                f"new positive co-products: {new_text}; {trial.get('assessment', '')}"
            )

    if report.get('current_run_recorded'):
        lines.append('')
        if report.get('current_run_type') == 'baseline':
            lines.append('Latest valid visible run recorded: no-knockout pFBA reference.')
        else:
            gene_id = report.get('current_candidate_gene')
            trial = trials.get(gene_id) or {}
            values = trial.get('tracked_flux_values') or {}
            lines.append(
                f"Latest valid candidate recorded: {_mission14_gene_label(gene_id)}; "
                f"succinate {_clean_display_number(values.get('EX_succ_e', 0.0)):.3f}; "
                f"acetate {_clean_display_number(values.get('EX_ac_e', 0.0)):.3f}."
            )
    elif report.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if baseline or trials:
            lines.append('Previously valid Mission 14 evidence remains available.')

    lines.append('')
    if report.get('evidence_ready'):
        lines.extend([
            'Evidence complete.',
            'Evaluate all four candidates against the clean-improvement criteria.',
            'Submit the conclusion supported by the complete target and co-product evidence to Dr. Almeida.',
        ])
    else:
        if not baseline:
            lines.append('Evidence incomplete: a controlled no-knockout pFBA reference is required.')
        missing = report.get('missing_candidates') or []
        if missing:
            lines.append('Missing candidate trials: ' + ', '.join(_mission14_gene_label(gene_id) for gene_id in missing) + '.')
        elif report.get('comparison_complete') and report.get('conclusion') == 'ambiguous':
            lines.append('The screen produced more than one clean candidate; the comparison does not identify a unique conclusion.')

    lines.extend([
        '',
        f"Operational criteria: retain at least {MISSION14_MIN_TARGET_RETENTION * 100:.0f}% of reference succinate, reduce acetate by at least {MISSION14_MIN_ACETATE_REDUCTION:.1f}, and introduce no new co-product above {MISSION14_NEW_BYPRODUCT_THRESHOLD:.1f}. These are mission criteria, not universal biological definitions.",
        'Interpretation note: lowering one byproduct does not by itself prove that a design improved. Carbon can be redirected into other secreted products, and the primary product can fall.',
        'The b1241 trial also revisits GPR redundancy: a selected gene knockout can leave its associated reactions functional through alternative genes.',
        'Every run is a theoretical succinate-optimal pFBA solution with approximately zero predicted biomass flux; it is not a viable production-strain claim.',
        'All objective, product, biomass, medium and parsimony values come from the same visible solver results. No hidden simulation is used.',
    ])
    return '\n'.join(lines)


def is_mission15_unlocked(missions_completed):
    """Mission 15 starts only after the Mission 14 intervention screen."""
    return '14' in (missions_completed or [])


def _mission15_report_is_current(report_data):
    return bool(
        isinstance(report_data, dict)
        and report_data.get('mission_id') == '15'
        and report_data.get('check_version') == MISSION15_CHECK_VERSION
    )


def _prepare_mission15_report(report_data):
    if not _mission15_report_is_current(report_data):
        return {}
    return copy.deepcopy(report_data)


def _mission15_measured_fluxes(production_fluxes):
    return {
        reaction_id: value
        for reaction_id, value in _mission14_measured_fluxes(production_fluxes).items()
        if reaction_id in MISSION15_REQUIRED_TRACKED_FLUXES
    }


def _mission15_biomass_value(production_fluxes):
    return _mission14_biomass_value(production_fluxes)


def _mission15_medium_evidence(medium_fluxes):
    return _mission14_medium_evidence(medium_fluxes)


def _mission15_import_mission14_product_run():
    """Reuse Mission 14's visible no-knockout product optimum.

    The function copies persisted evidence only.  It never launches a solver
    call, which keeps the same scientific contract for desktop and web.
    """
    report = load_mission14_reduction_check()
    if not (
        isinstance(report, dict)
        and report.get('mission_id') == '14'
        and report.get('check_version') == MISSION14_CHECK_VERSION
        and report.get('evidence_ready')
    ):
        return None, False

    source = report.get('baseline')
    if not isinstance(source, dict):
        return None, True
    tracked = source.get('tracked_flux_values') or {}
    numeric_values = [
        source.get('primary_objective_flux'),
        source.get('method_score'),
        source.get('biomass_flux'),
        source.get('glucose_uptake'),
        source.get('oxygen_uptake'),
        source.get('total_absolute_flux'),
        source.get('active_reaction_count'),
    ]
    if any(_as_float_or_none(value) is None for value in numeric_values):
        return None, True
    if any(_as_float_or_none(tracked.get(rid)) is None for rid in MISSION15_REQUIRED_TRACKED_FLUXES):
        return None, True
    if source.get('method') != MISSION15_TARGET_METHOD:
        return None, True
    if source.get('objective') != MISSION15_PRODUCT_OBJECTIVE:
        return None, True
    if source.get('method_score_name') != MISSION15_EXPECTED_SECONDARY_CRITERION:
        return None, True
    if source.get('knocked_out_genes') not in (None, []):
        return None, True
    if abs(float(source['primary_objective_flux']) - float(tracked[MISSION15_PRODUCT_OBJECTIVE])) > MISSION15_PRIMARY_TOLERANCE:
        return None, True
    if abs(float(source['glucose_uptake']) - MISSION15_DEFAULT_GLUCOSE_UPTAKE) > MISSION15_FLUX_TOLERANCE:
        return None, True
    if abs(float(source['oxygen_uptake'])) > MISSION15_FLUX_TOLERANCE:
        return None, True

    product_run = {
        'run_type': 'product_optimal',
        'source': 'mission14_visible_product_run',
        'method': MISSION15_TARGET_METHOD,
        'objective': MISSION15_PRODUCT_OBJECTIVE,
        'primary_objective_flux': round(float(source['primary_objective_flux']), 6),
        'method_score': round(float(source.get('method_score')), 6)
        if _as_float_or_none(source.get('method_score')) is not None else None,
        'method_score_name': source.get('method_score_name'),
        'total_absolute_flux': round(float(source['total_absolute_flux']), 6),
        'active_reaction_count': int(source['active_reaction_count']),
        'tracked_flux_values': {
            rid: round(float(tracked[rid]), 6)
            for rid in MISSION15_REQUIRED_TRACKED_FLUXES
        },
        'biomass_flux': round(float(source['biomass_flux']), 6),
        'glucose_uptake': round(float(source['glucose_uptake']), 6),
        'oxygen_uptake': round(float(source['oxygen_uptake']), 6),
        'knocked_out_genes': [],
    }
    return product_run, True


def initialise_mission15_viability_audit():
    """Create the current state and import visible Mission 14 evidence."""
    product_run, mission14_available = _mission15_import_mission14_product_run()
    data = {
        'mission_id': '15',
        'check_version': MISSION15_CHECK_VERSION,
        'mission_title': 'Product–Growth Viability Audit',
        'target_method': MISSION15_TARGET_METHOD,
        'target_product': MISSION15_TARGET_PRODUCT,
        'product_objective': MISSION15_PRODUCT_OBJECTIVE,
        'growth_objective': MISSION15_GROWTH_OBJECTIVE,
        'required_tracked_fluxes': list(MISSION15_REQUIRED_TRACKED_FLUXES),
        'product_names': dict(MISSION15_PRODUCT_NAMES),
        'product_optimal_run': product_run,
        'growth_optimal_run': None,
        'mission14_product_run_available': mission14_available,
        'mission14_product_run_imported': bool(product_run),
        'comparison_complete': False,
        'same_controlled_setup': False,
        'relationship_classification': None,
        'objective_conflict_supported': False,
        'expected_relationship': MISSION15_EXPECTED_RELATIONSHIP,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_run_valid': False,
        'current_run_recorded': False,
        'current_run_type': None,
        'current_issues': [],
        'latest_attempt': None,
    }
    save_mission15_diagnostic_report_check(data)
    return data


def _mission15_relationship(product_run, growth_run):
    if not product_run or not growth_run:
        return None
    product_biomass = _as_float_or_none(product_run.get('biomass_flux'))
    growth_product = _as_float_or_none(
        (growth_run.get('tracked_flux_values') or {}).get(MISSION15_PRODUCT_OBJECTIVE)
    )
    if product_biomass is None or growth_product is None:
        return None
    if (
        product_biomass <= MISSION15_MAX_PRODUCT_RUN_BIOMASS + MISSION15_FLUX_TOLERANCE
        and growth_product <= MISSION15_MAX_GROWTH_RUN_PRODUCT + MISSION15_FLUX_TOLERANCE
    ):
        return 'objective_conflict'
    if (
        product_biomass > MISSION15_MAX_PRODUCT_RUN_BIOMASS + MISSION15_FLUX_TOLERANCE
        and growth_product > MISSION15_MAX_GROWTH_RUN_PRODUCT + MISSION15_FLUX_TOLERANCE
    ):
        return 'coexistence'
    return 'asymmetric_tradeoff'


def _mission15_same_setup(product_run, growth_run):
    if not product_run or not growth_run:
        return False
    if product_run.get('method') != growth_run.get('method'):
        return False
    if product_run.get('knocked_out_genes') or growth_run.get('knocked_out_genes'):
        return False
    for key in ('glucose_uptake', 'oxygen_uptake'):
        left = _as_float_or_none(product_run.get(key))
        right = _as_float_or_none(growth_run.get(key))
        if left is None or right is None or abs(left - right) > MISSION15_FLUX_TOLERANCE:
            return False
    left_panel = set((product_run.get('tracked_flux_values') or {}).keys())
    right_panel = set((growth_run.get('tracked_flux_values') or {}).keys())
    return left_panel == right_panel == set(MISSION15_REQUIRED_TRACKED_FLUXES)


def _build_mission15_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
    selected_fluxes=None,
):
    existing = _prepare_mission15_report(existing_report)
    product_run = copy.deepcopy(existing.get('product_optimal_run'))
    growth_run = copy.deepcopy(existing.get('growth_optimal_run'))

    imported_product, mission14_available = _mission15_import_mission14_product_run()
    if not product_run and imported_product:
        product_run = imported_product

    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = list(
        selected_fluxes
        if selected_fluxes is not None
        else _read_selected_production_fluxes()
    )
    measured_fluxes = _mission15_measured_fluxes(production_fluxes)
    biomass_flux = _mission15_biomass_value(production_fluxes)
    glucose_uptake, oxygen_uptake = _mission15_medium_evidence(medium_fluxes)
    oxygen_closed, unexpected_changes = _mission15_environment_status(reactions)
    diagnostics = _method_diagnostics_from_production_data(production_fluxes)

    primary_objective_flux = _as_float_or_none(diagnostics.get('primary_objective_flux'))
    method_score = _as_float_or_none(diagnostics.get('method_score'))
    total_absolute_flux = _as_float_or_none(diagnostics.get('total_absolute_flux'))
    method_score_name = diagnostics.get('method_score_name')
    try:
        active_reaction_count = int(diagnostics.get('active_reaction_count'))
    except Exception:
        active_reaction_count = None
    objective_value = _as_float_or_none(objective_result)

    current_run_type = None
    if selected_objective == MISSION15_PRODUCT_OBJECTIVE:
        current_run_type = 'product_optimal'
    elif selected_objective == MISSION15_GROWTH_OBJECTIVE:
        current_run_type = 'growth_optimal'

    missing_selected = [
        rid for rid in MISSION15_REQUIRED_TRACKED_FLUXES
        if rid not in selected_fluxes
    ]
    missing_measured = [
        rid for rid in MISSION15_REQUIRED_TRACKED_FLUXES
        if _as_float_or_none(measured_fluxes.get(rid)) is None
    ]

    issues = []
    if objective_error:
        issues.append(objective_error)
    if method_name != MISSION15_TARGET_METHOD:
        issues.append(f'Use {MISSION15_TARGET_METHOD} for both controlled runs.')
    if current_run_type is None:
        issues.append(
            f'Use either {MISSION15_PRODUCT_OBJECTIVE} or {MISSION15_GROWTH_OBJECTIVE} as the selected objective.'
        )
    if knocked_out_genes:
        issues.append('Keep every gene active; Mission 15 changes only the selected objective.')
    if not oxygen_closed:
        issues.append('Close only the lower bound of oxygen uptake for the controlled anaerobic medium.')
    issues.extend(f'Unexpected environmental change: {item}.' for item in unexpected_changes)
    if missing_selected:
        issues.append('Select the complete target/co-product panel: ' + ', '.join(missing_selected) + '.')
    if missing_measured:
        issues.append('The visible result is missing numeric fluxes for: ' + ', '.join(missing_measured) + '.')
    if objective_value is None:
        issues.append('The visible objective value is not numeric.')
    if biomass_flux is None:
        issues.append('The visible result does not contain a numeric biomass flux.')
    if glucose_uptake is None:
        issues.append('The visible result does not contain glucose uptake.')
    elif abs(float(glucose_uptake) - MISSION15_DEFAULT_GLUCOSE_UPTAKE) > MISSION15_FLUX_TOLERANCE:
        issues.append('Keep the default glucose uptake capacity for both runs.')
    if oxygen_uptake is None:
        issues.append('The visible result does not contain oxygen uptake.')
    elif abs(float(oxygen_uptake)) > MISSION15_FLUX_TOLERANCE:
        issues.append('The visible solution is still using oxygen.')
    if diagnostics.get('method') != MISSION15_TARGET_METHOD:
        issues.append('The visible method diagnostics do not describe pFBA.')
    if diagnostics.get('objective_reaction') != selected_objective:
        issues.append('The visible method diagnostics do not match the selected objective.')
    if primary_objective_flux is None:
        issues.append('The primary objective flux is missing from the visible result.')
    if method_score is None:
        issues.append('The pFBA secondary score is missing from the visible result.')
    if method_score_name != MISSION15_EXPECTED_SECONDARY_CRITERION:
        issues.append('The pFBA secondary criterion is not identified as total absolute flux.')
    if total_absolute_flux is None:
        issues.append('The total absolute flux is missing from the visible result.')
    if active_reaction_count is None:
        issues.append('The active-reaction count is missing from the visible result.')
    if (
        objective_value is not None
        and primary_objective_flux is not None
        and abs(float(objective_value) - float(primary_objective_flux)) > MISSION15_PRIMARY_TOLERANCE
    ):
        issues.append('The displayed objective value does not match the primary objective flux.')

    if current_run_type == 'product_optimal':
        product_flux = _as_float_or_none(measured_fluxes.get(MISSION15_PRODUCT_OBJECTIVE))
        if product_flux is None:
            pass
        elif primary_objective_flux is not None and abs(product_flux - primary_objective_flux) > MISSION15_PRIMARY_TOLERANCE:
            issues.append('The tracked succinate flux does not match the product objective flux.')
        if primary_objective_flux is not None and primary_objective_flux < MISSION15_MIN_PRODUCT_FLUX:
            issues.append('The product-optimal run did not produce a meaningful succinate optimum.')
    elif current_run_type == 'growth_optimal':
        if (
            biomass_flux is not None
            and primary_objective_flux is not None
            and abs(float(biomass_flux) - float(primary_objective_flux)) > MISSION15_PRIMARY_TOLERANCE
        ):
            issues.append('The measured biomass flux does not match the growth objective flux.')
        if biomass_flux is not None and biomass_flux < MISSION15_MIN_GROWTH_FLUX:
            issues.append('The growth-optimal run did not produce viable predicted growth.')

    current_run_valid = not issues
    current_run_recorded = False
    if current_run_valid:
        run = {
            'run_type': current_run_type,
            'source': 'current_visible_run',
            'method': method_name,
            'objective': selected_objective,
            'primary_objective_flux': round(float(primary_objective_flux), 6),
            'method_score': round(float(method_score), 6),
            'method_score_name': method_score_name,
            'total_absolute_flux': round(float(total_absolute_flux), 6),
            'active_reaction_count': int(active_reaction_count),
            'tracked_flux_values': {
                rid: round(float(measured_fluxes[rid]), 6)
                for rid in MISSION15_REQUIRED_TRACKED_FLUXES
            },
            'biomass_flux': round(float(biomass_flux), 6),
            'glucose_uptake': round(float(glucose_uptake), 6),
            'oxygen_uptake': round(
                0.0 if abs(float(oxygen_uptake)) < DISPLAY_ZERO_TOLERANCE else float(oxygen_uptake),
                6,
            ),
            'knocked_out_genes': [],
        }
        if current_run_type == 'product_optimal':
            product_run = run
        else:
            growth_run = run
        current_run_recorded = True

    comparison_complete = bool(product_run and growth_run)
    same_controlled_setup = _mission15_same_setup(product_run, growth_run)
    relationship = _mission15_relationship(product_run, growth_run) if comparison_complete else None
    objective_conflict_supported = relationship == MISSION15_EXPECTED_RELATIONSHIP
    evidence_ready = bool(comparison_complete and same_controlled_setup and relationship)

    data = {
        'mission_id': '15',
        'check_version': MISSION15_CHECK_VERSION,
        'mission_title': 'Product–Growth Viability Audit',
        'target_method': MISSION15_TARGET_METHOD,
        'target_product': MISSION15_TARGET_PRODUCT,
        'product_objective': MISSION15_PRODUCT_OBJECTIVE,
        'growth_objective': MISSION15_GROWTH_OBJECTIVE,
        'oxygen_reaction': MISSION15_OXYGEN_REACTION,
        'glucose_reaction': MISSION15_GLUCOSE_REACTION,
        'required_tracked_fluxes': list(MISSION15_REQUIRED_TRACKED_FLUXES),
        'product_names': dict(MISSION15_PRODUCT_NAMES),
        'product_optimal_run': product_run,
        'growth_optimal_run': growth_run,
        'mission14_product_run_available': mission14_available,
        'mission14_product_run_imported': bool(
            product_run and product_run.get('source') == 'mission14_visible_product_run'
        ),
        'comparison_complete': comparison_complete,
        'same_controlled_setup': same_controlled_setup,
        'relationship_classification': relationship,
        'objective_conflict_supported': objective_conflict_supported,
        'expected_relationship': MISSION15_EXPECTED_RELATIONSHIP,
        'evidence_ready': evidence_ready,
        'answer_ready': evidence_ready,
        'ready_to_deliver': evidence_ready,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': current_run_type,
        'current_method': method_name,
        'current_objective': selected_objective,
        'current_knocked_out_genes': knocked_out_genes,
        'current_primary_objective_flux': round(float(primary_objective_flux), 6)
        if primary_objective_flux is not None else None,
        'current_method_score': round(float(method_score), 6) if method_score is not None else None,
        'current_method_score_name': method_score_name,
        'current_total_absolute_flux': round(float(total_absolute_flux), 6)
        if total_absolute_flux is not None else None,
        'current_active_reaction_count': active_reaction_count,
        'current_tracked_flux_values': {
            rid: round(float(value), 6) for rid, value in measured_fluxes.items()
        },
        'current_biomass_flux': round(float(biomass_flux), 6) if biomass_flux is not None else None,
        'current_glucose_uptake': round(float(glucose_uptake), 6) if glucose_uptake is not None else None,
        'current_oxygen_uptake': round(float(oxygen_uptake), 6) if oxygen_uptake is not None else None,
        'selected_production_fluxes': selected_fluxes,
        'missing_selected_fluxes': missing_selected,
        'missing_measured_fluxes': missing_measured,
        'full_panel_measured': not missing_measured,
        'current_issues': issues,
        'latest_attempt': {
            'valid': current_run_valid,
            'recorded': current_run_recorded,
            'run_type': current_run_type,
            'method': method_name,
            'objective': selected_objective,
            'issues': list(issues),
        },
    }
    if objective_error:
        data['error'] = objective_error
    save_mission15_diagnostic_report_check(data)
    return data


def run_mission15_diagnostic_report_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible product-optimal or growth-optimal pFBA simulation before recording Mission 15 evidence.'
    except Exception:
        objective_error = 'Could not read the current visible simulation result.'

    return _build_mission15_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission15_diagnostic_report_check(),
        objective_error=objective_error,
    )


def _mission15_answer_text(answer):
    """Return accent-insensitive lower-case words for free-text answers."""
    text = unicodedata.normalize('NFKD', str(answer or ''))
    text = ''.join(char for char in text if not unicodedata.combining(char))
    return re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()


def _mission15_priority_clause_supports(clause, priority_terms, zero_terms):
    """Recognise one side of the two-optimum zero-flux observation."""
    priority_pattern = r'(?:maximi[sz](?:e|ed|es|ing)|prioriti[sz](?:e|ed|es|ing)|optimi[sz](?:e|ed|es|ing)|priority|optimum)'
    zero_pattern = r'(?:zero|0(?:\.0+)?|absent|no\s+predicted)'
    priority_subject = r'(?:' + '|'.join(priority_terms) + r')'
    zero_subject = r'(?:' + '|'.join(zero_terms) + r')'
    priority_found = bool(
        re.search(rf'\b{priority_subject}\b(?:\s+\w+){{0,4}}\s+{priority_pattern}\b', clause)
        or re.search(rf'\b{priority_pattern}\b(?:\s+\w+){{0,4}}\s+\b{priority_subject}\b', clause)
    )
    zero_found = bool(
        re.search(rf'\b{zero_subject}\b(?:\s+\w+){{0,4}}\s+{zero_pattern}\b', clause)
        or re.search(rf'\b{zero_pattern}\b(?:\s+\w+){{0,4}}\s+\b{zero_subject}\b', clause)
    )
    return priority_found and zero_found


def normalise_mission15_answer(answer):
    phrase = _mission15_answer_text(answer)
    compact = phrase.replace(' ', '')
    aliases = {
        'objectiveconflict': 'objective_conflict',
        'thereisanobjectiveconflict': 'objective_conflict',
        'theobjectivesconflict': 'objective_conflict',
        'conflictbetweenobjectives': 'objective_conflict',
        'conflictbetweengrowthandproduction': 'objective_conflict',
        'growthproductionconflict': 'objective_conflict',
        'growthproductconflict': 'objective_conflict',
        'notgrowthcoupled': 'objective_conflict',
        'notgrowthcoupledproduction': 'objective_conflict',
        'notgrowthcompatible': 'objective_conflict',
        'productnotgrowthcoupled': 'objective_conflict',
        'productionisnotgrowthcoupled': 'objective_conflict',
        'succinateisnotgrowthcoupled': 'objective_conflict',
        'succinateproductionisnotgrowthcoupled': 'objective_conflict',
        'growthandproductionarenotcoupled': 'objective_conflict',
        'growthisnotcoupledtoproduction': 'objective_conflict',
        'conflitodeobjetivos': 'objective_conflict',
        'conflitoentreobjetivos': 'objective_conflict',
        'conflitocrescimentoproducao': 'objective_conflict',
        'naoestaacopladoaocrescimento': 'objective_conflict',
        'naoacopladoaocrescimento': 'objective_conflict',
        'producaonaoestaacopladaaocrescimento': 'objective_conflict',
        'crescimentoeproducaonaoestaoacoplados': 'objective_conflict',
        'coexistence': 'coexistence',
        'compatible': 'coexistence',
        'bothpositive': 'coexistence',
        'asymmetrictradeoff': 'asymmetric_tradeoff',
        'partialtradeoff': 'asymmetric_tradeoff',
    }
    exact = aliases.get(compact)
    if exact:
        return exact
    if not phrase:
        return None

    # Explicit claims of compatibility or absence of conflict must not be
    # misread as the supported Mission 15 conclusion.
    coexistence_patterns = (
        r'\b(?:growth|biomass)\b.*\b(?:succinate|product|production)\b.*\b(?:are|is|remain|can be)\s+compatible\b',
        r'\b(?:succinate|product|production)\b.*\b(?:growth|biomass)\b.*\b(?:are|is|remain|can be)\s+compatible\b',
        r'\b(?:no|without)\s+(?:objective\s+|growth production\s+)?conflict\b',
        r'\b(?:do|does)\s+not\s+conflict\b',
        r'\bcan\s+coexist\b',
    )
    if any(re.search(pattern, phrase) for pattern in coexistence_patterns):
        return 'coexistence'

    words = set(phrase.split())
    has_growth = bool(words.intersection({'growth', 'biomass'}))
    has_product = bool(words.intersection({'succinate', 'product', 'production'}))
    has_both_subjects = has_growth and has_product

    if has_both_subjects:
        conflict_language = bool(words.intersection({
            'conflict', 'conflicts', 'conflicting', 'incompatible',
            'incompatibility', 'tradeoff', 'uncoupled',
        })) or 'trade off' in phrase or 'mutually exclusive' in phrase
        negative_coupling = bool(re.search(
            r'\b(?:not|no|never)\b(?:\s+\w+){0,3}\s+\b(?:coupled|compatible)\b',
            phrase,
        ))
        if conflict_language or negative_coupling:
            return 'objective_conflict'

    # Accept a complete evidence-based sentence even when the player does not
    # use specialist terms such as "objective conflict" or "growth-coupled".
    clauses = [part.strip() for part in re.split(r'\b(?:and|while|whereas|but)\b', phrase) if part.strip()]
    product_priority_zero_growth = any(
        _mission15_priority_clause_supports(
            clause,
            ('succinate', 'product', 'production'),
            ('growth', 'biomass'),
        )
        for clause in clauses
    )
    growth_priority_zero_product = any(
        _mission15_priority_clause_supports(
            clause,
            ('growth', 'biomass'),
            ('succinate', 'product', 'production'),
        )
        for clause in clauses
    )
    if product_priority_zero_growth and growth_priority_zero_product:
        return 'objective_conflict'

    return None


def mission15_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission15_diagnostic_report_check() or {}
    report = _prepare_mission15_report(report_data)
    return bool(
        report.get('evidence_ready')
        and report.get('relationship_classification')
        and normalise_mission15_answer(answer) == report.get('relationship_classification')
    )


def _mission15_run_lines(title, run):
    if not run:
        return [f'{title}: not recorded.']
    values = run.get('tracked_flux_values') or {}
    lines = [
        f'{title}:',
        f"- Objective: {run.get('objective')}",
        f"- Primary objective flux: {_clean_display_number(run.get('primary_objective_flux')):.3f}",
        f"- Predicted biomass: {_clean_display_number(run.get('biomass_flux')):.3f}",
    ]
    for reaction_id in MISSION15_REQUIRED_TRACKED_FLUXES:
        lines.append(
            f"- {MISSION15_PRODUCT_NAMES.get(reaction_id, reaction_id)} ({reaction_id}): "
            f"{_clean_display_number(values.get(reaction_id)):.3f}"
        )
    lines.extend([
        f"- Glucose uptake: {_clean_display_number(run.get('glucose_uptake')):.3f}",
        f"- Oxygen uptake: {_clean_display_number(run.get('oxygen_uptake')):.3f}",
        f"- Total absolute flux: {_clean_display_number(run.get('total_absolute_flux')):.3f}",
        f"- Active reactions: {int(run.get('active_reaction_count', 0))}",
    ])
    return lines


def build_mission15_viability_report_text(report_data=None):
    if report_data is None:
        report_data = load_mission15_diagnostic_report_check() or {}
    report = _prepare_mission15_report(report_data)
    product_run = report.get('product_optimal_run')
    growth_run = report.get('growth_optimal_run')
    lines = ['Mission 15 Product–Growth Viability Audit', '']

    if not report:
        lines.append('Build two controlled visible pFBA optima under the same anaerobic medium and exchange panel.')
        return '\n'.join(lines)

    lines.extend([
        'Controlled setup:',
        f'- Method in both runs: {MISSION15_TARGET_METHOD}',
        '- Genes: all active',
        '- Medium: default glucose; oxygen uptake closed; all other bounds default',
        '- Complete target/co-product panel: ' + ', '.join(MISSION15_REQUIRED_TRACKED_FLUXES),
        '- Experimental variable: selected objective only',
        '',
    ])
    lines.extend(_mission15_run_lines('Product-priority optimum', product_run))
    lines.append('')
    lines.extend(_mission15_run_lines('Growth-priority optimum', growth_run))

    if product_run and growth_run:
        product_biomass = _clean_display_number(product_run.get('biomass_flux'))
        growth_succinate = _clean_display_number(
            (growth_run.get('tracked_flux_values') or {}).get(MISSION15_PRODUCT_OBJECTIVE)
        )
        lines.extend([
            '',
            'Cross-objective evidence:',
            f'- Biomass in the product-priority optimum: {product_biomass:.3f}',
            f'- Succinate in the growth-priority optimum: {growth_succinate:.3f}',
            '- Controlled setup preserved: ' + ('yes' if report.get('same_controlled_setup') else 'no'),
        ])

    if report.get('current_run_recorded'):
        lines.extend(['', f"Latest valid visible run recorded: {report.get('current_run_type', '').replace('_', ' ')}."])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if product_run or growth_run:
            lines.append('Previously valid Mission 15 evidence remains available.')

    lines.append('')
    if report.get('evidence_ready'):
        lines.extend([
            'Evidence complete.',
            'Compare what happens to biomass when product is prioritised with what happens to succinate when growth is prioritised.',
            'Submit the relationship supported by both controlled optima to Dr. Almeida.',
        ])
    else:
        missing = []
        if not product_run:
            missing.append('product-priority pFBA optimum')
        if not growth_run:
            missing.append('growth-priority pFBA optimum')
        if missing:
            lines.append('Evidence incomplete. Missing: ' + ', '.join(missing) + '.')
            if report.get('mission14_product_run_available') and not report.get('mission14_product_run_imported') and not product_run:
                lines.append('Mission 14 evidence exists but lacks a complete current-format product run; repeat that visible product-optimal run once.')
        elif not report.get('same_controlled_setup'):
            lines.append('Both runs exist, but the controlled setup is not identical apart from the objective.')

    lines.extend([
        '',
        'Interpretation note: an optimum answers the selected objective under the imposed constraints; it does not automatically impose a positive lower bound on another reaction.',
        'Zero flux describes these model solutions and conditions. It is not a universal experimental impossibility claim.',
        'All objective, exchange, biomass, medium and pFBA diagnostic values come from the same visible solver results. No hidden simulation is used.',
    ])
    return '\n'.join(lines)


def _medium_flux_maps(medium_fluxes):
    raw_fluxes = {}
    uptake_fluxes = {}
    secretion_fluxes = {}

    if not medium_fluxes or medium_fluxes.get('error'):
        return raw_fluxes, uptake_fluxes, secretion_fluxes

    for item in medium_fluxes.get('items') or []:
        reaction_id = item.get('reaction_id')
        if not reaction_id or item.get('error'):
            continue
        raw_fluxes[reaction_id] = float(item.get('raw_flux', 0.0))
        uptake_fluxes[reaction_id] = float(item.get('uptake_flux', 0.0))
        secretion_fluxes[reaction_id] = float(item.get('secretion_flux', 0.0))

    return raw_fluxes, uptake_fluxes, secretion_fluxes


def is_mission16_unlocked(missions_completed):
    """Mission 16 starts only after the complete Dr. Almeida path."""
    return '15' in (missions_completed or [])


def _mission16_environment_status(reactions):
    """Return an order-independent description of the Mission 16 medium.

    The valid protocol closes glucose uptake, opens exactly one candidate
    carbon source and either keeps oxygen at its model default (screening) or
    closes only its lower bound (the final robustness challenge).
    """
    bounds_complete = True
    glucose_lower_bound_closed = False
    oxygen_lower_bound_closed = False
    selected_sources = []
    unexpected_changes = []

    for i in range(len(REACTIONS.index)):
        reaction_id = REACTIONS.index[i]
        lower_open, upper_open = _reaction_bound_open_states(reactions, i)
        if lower_open is None or upper_open is None:
            bounds_complete = False
            continue

        default_lower_open = REACTIONS.lb.iloc[i] != 0
        default_upper_open = REACTIONS.ub.iloc[i] != 0
        lower_changed = lower_open != default_lower_open
        upper_changed = upper_open != default_upper_open

        if reaction_id == MISSION16_BLOCKED_CARBON_SOURCE:
            glucose_lower_bound_closed = not lower_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id == MISSION16_OXYGEN_REACTION:
            oxygen_lower_bound_closed = not lower_open
            if lower_changed and lower_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id in MISSION16_CANDIDATE_CARBON_SOURCES:
            if lower_changed and lower_open:
                selected_sources.append(reaction_id)
            elif lower_changed:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    return {
        'bounds_complete': bounds_complete,
        'glucose_lower_bound_closed': glucose_lower_bound_closed,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'selected_sources': selected_sources,
        'unexpected_environment_changes': unexpected_changes,
    }


def _mission16_rank_trials(trials):
    ranked = sorted(
        (
            {
                'source_id': source_id,
                'source_name': MISSION16_SOURCE_NAMES.get(source_id, source_id),
                'growth': float(trial.get('growth')),
            }
            for source_id, trial in (trials or {}).items()
            if source_id in MISSION16_CANDIDATE_CARBON_SOURCES
            and _as_float_or_none(trial.get('growth')) is not None
        ),
        key=lambda row: (-row['growth'], MISSION16_CANDIDATE_CARBON_SOURCES.index(row['source_id'])),
    )
    if not ranked:
        return ranked, [], None

    best_growth = ranked[0]['growth']
    strongest = [
        row['source_id'] for row in ranked
        if abs(row['growth'] - best_growth) <= MISSION16_RANK_TOLERANCE
    ]
    unique = strongest[0] if len(strongest) == 1 else None
    return ranked, strongest, unique


def _normalise_mission16_text(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    text = ''.join(char for char in text if not unicodedata.combining(char))
    return ''.join(char.lower() for char in text if char.isalnum())


def normalise_mission16_answer(answer):
    """Map concise, unambiguous factor names to the expected answer."""
    key = _normalise_mission16_text(answer)
    aliases = {
        'oxygen',
        'o2',
        'molecularoxygen',
        'oxygenavailability',
        'oxygensupply',
        'oxygengas',
        'oxygenuptake',
        'oxygenexchange',
        'oxygeno2',
        'o2availability',
        'o2uptake',
        'exo2e',
        'oxigenio',
        'disponibilidadedeoxigenio',
    }
    return MISSION16_EXPECTED_FACTOR if key in aliases else None


def mission16_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission16_medium_report_check() or {}
    return bool(
        report_data.get('evidence_ready')
        and report_data.get('relationship_supported')
        and normalise_mission16_answer(answer) == report_data.get('expected_factor')
    )


def initialise_mission16_context_rescue():
    data = {
        'mission_id': '16',
        'check_version': MISSION16_CHECK_VERSION,
        'mission_title': 'Context-Dependent Carbon Rescue',
        'target_context': MISSION16_TARGET_CONTEXT,
        'target_method': MISSION16_METHOD,
        'growth_objective': MISSION16_GROWTH_OBJECTIVE,
        'blocked_carbon_source': MISSION16_BLOCKED_CARBON_SOURCE,
        'oxygen_reaction': MISSION16_OXYGEN_REACTION,
        'candidate_carbon_sources': list(MISSION16_CANDIDATE_CARBON_SOURCES),
        'source_names': dict(MISSION16_SOURCE_NAMES),
        'required_medium_fluxes': list(MISSION16_REQUIRED_MEDIUM_FLUXES),
        'candidate_trials': {},
        'valid_trial_count': 0,
        'required_trial_count': len(MISSION16_CANDIDATE_CARBON_SOURCES),
        'missing_candidates': list(MISSION16_CANDIDATE_CARBON_SOURCES),
        'aerobic_screen_complete': False,
        'ranked_candidates': [],
        'strongest_candidates': [],
        'strongest_candidate': None,
        'strongest_growth': None,
        'expected_strongest_candidate': MISSION16_EXPECTED_STRONGEST_SOURCE,
        'expected_strongest_confirmed': False,
        'oxygen_challenge_run': None,
        'oxygen_challenge_recorded': False,
        'oxygen_challenge_infeasible': False,
        'relationship_supported': False,
        'expected_factor': MISSION16_EXPECTED_FACTOR,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_run_valid': False,
        'current_run_recorded': False,
        'current_run_type': None,
        'current_issues': [],
        'latest_attempt': None,
    }
    save_mission16_medium_report_check(data)
    return data


def _build_mission16_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
):
    """Validate and accumulate one visible Mission 16 run."""
    existing_report = existing_report or {}
    if (
        existing_report.get('mission_id') != '16'
        or existing_report.get('check_version') != MISSION16_CHECK_VERSION
    ):
        existing_report = {}

    trials = copy.deepcopy(existing_report.get('candidate_trials') or {})
    oxygen_challenge_run = copy.deepcopy(existing_report.get('oxygen_challenge_run'))

    method_correct = method_name == MISSION16_METHOD
    objective_correct = selected_objective == MISSION16_GROWTH_OBJECTIVE
    knocked_out_genes = _knocked_out_genes(genes)
    environment = _mission16_environment_status(reactions)
    selected_sources = list(environment.get('selected_sources') or [])
    exactly_one_source = len(selected_sources) == 1
    selected_source = selected_sources[0] if exactly_one_source else None
    oxygen_closed = bool(environment.get('oxygen_lower_bound_closed'))
    run_type = 'oxygen_challenge' if oxygen_closed else 'aerobic_screen'

    objective_numeric = _as_float_or_none(objective_result)
    result_infeasible = 'INFEASIBLE' in str(objective_result or '').upper()
    result_available = objective_numeric is not None or result_infeasible

    raw_fluxes, uptake_fluxes, secretion_fluxes = _medium_flux_maps(medium_fluxes)
    missing_medium_fluxes = [
        reaction_id for reaction_id in MISSION16_REQUIRED_MEDIUM_FLUXES
        if reaction_id not in raw_fluxes
    ]
    selected_source_uptake = (
        _as_float_or_none(uptake_fluxes.get(selected_source)) if selected_source else None
    )
    glucose_uptake = _as_float_or_none(uptake_fluxes.get(MISSION16_BLOCKED_CARBON_SOURCE))
    oxygen_uptake = _as_float_or_none(uptake_fluxes.get(MISSION16_OXYGEN_REACTION))

    ranked_before, strongest_before, strongest_source_before = _mission16_rank_trials(trials)
    screen_complete_before = all(
        source_id in trials for source_id in MISSION16_CANDIDATE_CARBON_SOURCES
    )

    issues = []
    if objective_error:
        issues.append(objective_error)
    if not method_correct:
        issues.append('Use FBA for every Mission 16 run.')
    if not objective_correct:
        issues.append('Use the biomass objective for every Mission 16 run.')
    if knocked_out_genes:
        issues.append('Keep every gene active; this is a medium-context experiment.')
    if not environment.get('bounds_complete'):
        issues.append('The environmental-bound payload is incomplete.')
    if not environment.get('glucose_lower_bound_closed'):
        issues.append('Close glucose uptake before testing an alternative carbon source.')
    if not exactly_one_source:
        issues.append('Open exactly one Mission 16 candidate carbon source per run.')
    if environment.get('unexpected_environment_changes'):
        issues.append('Keep every unrelated environmental bound at its model default.')
    if not result_available:
        issues.append('The visible simulation did not return a numeric or infeasible result.')

    if run_type == 'aerobic_screen':
        if result_infeasible:
            issues.append('Aerobic screening runs must return a feasible numeric growth result.')
        if medium_fluxes and medium_fluxes.get('error'):
            issues.append('The Exchange Flux Report did not return measurable screening fluxes.')
        if missing_medium_fluxes:
            issues.append('The Exchange Flux Report is missing required Mission 16 reactions.')
        if glucose_uptake is None:
            issues.append('Numeric glucose-uptake evidence is missing.')
        elif glucose_uptake > MISSION16_FLUX_TOLERANCE:
            issues.append('The visible solution still consumes glucose.')
        if selected_source_uptake is None:
            issues.append('Numeric uptake evidence for the selected source is missing.')
        elif abs(selected_source_uptake - MISSION16_EXPECTED_SOURCE_UPTAKE) > MISSION16_SOURCE_UPTAKE_TOLERANCE:
            issues.append('Use the same model-defined -10 uptake protocol for every candidate source.')
        if oxygen_uptake is None:
            issues.append('Numeric oxygen-uptake evidence is missing.')
        elif oxygen_uptake <= MISSION16_FLUX_TOLERANCE:
            issues.append('Keep oxygen available during the five-run aerobic screen.')
        if objective_numeric is None:
            issues.append('The aerobic screen did not provide numeric predicted growth.')
        elif objective_numeric < MISSION16_MIN_POSITIVE_GROWTH:
            issues.append('The selected source did not provide positive growth rescue.')
    else:
        if not screen_complete_before:
            issues.append('Complete the five-source aerobic screen before the oxygen-removal challenge.')
        if strongest_source_before is None:
            issues.append('The aerobic evidence does not identify one unique strongest-growth source.')
        elif selected_source != strongest_source_before:
            issues.append('Repeat the uniquely strongest aerobic source for the oxygen-removal challenge.')
        if objective_numeric is not None:
            if medium_fluxes and medium_fluxes.get('error'):
                issues.append('The feasible challenge result is missing its Exchange Flux Report.')
            elif missing_medium_fluxes:
                issues.append('The feasible challenge result is missing required medium-flux values.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run = None
    if current_run_valid and run_type == 'aerobic_screen':
        current_run = {
            'run_type': 'aerobic_screen',
            'source': 'visible_simulation',
            'source_id': selected_source,
            'source_name': MISSION16_SOURCE_NAMES.get(selected_source, selected_source),
            'method': method_name,
            'objective': selected_objective,
            'growth': round(float(objective_numeric), 6),
            'source_uptake': round(float(selected_source_uptake), 6),
            'glucose_uptake': round(float(glucose_uptake), 6),
            'oxygen_uptake': round(float(oxygen_uptake), 6),
            'medium_raw_fluxes': {
                reaction_id: round(float(raw_fluxes[reaction_id]), 6)
                for reaction_id in MISSION16_REQUIRED_MEDIUM_FLUXES
            },
        }
        trials[selected_source] = current_run
        current_run_recorded = True
    elif current_run_valid and run_type == 'oxygen_challenge':
        current_run = {
            'run_type': 'oxygen_challenge',
            'source': 'visible_simulation',
            'source_id': selected_source,
            'source_name': MISSION16_SOURCE_NAMES.get(selected_source, selected_source),
            'method': method_name,
            'objective': selected_objective,
            'oxygen_lower_bound_closed': True,
            'status': 'infeasible' if result_infeasible else 'feasible',
            'visible_result': str(objective_result),
            'growth': round(float(objective_numeric), 6) if objective_numeric is not None else None,
        }
        oxygen_challenge_run = current_run
        current_run_recorded = True

    ranked_candidates, strongest_candidates, strongest_candidate = _mission16_rank_trials(trials)
    missing_candidates = [
        source_id for source_id in MISSION16_CANDIDATE_CARBON_SOURCES
        if source_id not in trials
    ]
    aerobic_screen_complete = not missing_candidates
    strongest_growth = ranked_candidates[0]['growth'] if ranked_candidates else None
    expected_strongest_confirmed = (
        aerobic_screen_complete
        and strongest_candidate == MISSION16_EXPECTED_STRONGEST_SOURCE
    )
    oxygen_challenge_recorded = isinstance(oxygen_challenge_run, dict)
    oxygen_challenge_infeasible = bool(
        oxygen_challenge_recorded
        and oxygen_challenge_run.get('status') == 'infeasible'
    )
    relationship_supported = bool(
        expected_strongest_confirmed
        and oxygen_challenge_infeasible
        and oxygen_challenge_run.get('source_id') == strongest_candidate
    )
    evidence_ready = bool(aerobic_screen_complete and oxygen_challenge_recorded)

    data = {
        'mission_id': '16',
        'check_version': MISSION16_CHECK_VERSION,
        'mission_title': 'Context-Dependent Carbon Rescue',
        'target_context': MISSION16_TARGET_CONTEXT,
        'target_method': MISSION16_METHOD,
        'growth_objective': MISSION16_GROWTH_OBJECTIVE,
        'blocked_carbon_source': MISSION16_BLOCKED_CARBON_SOURCE,
        'oxygen_reaction': MISSION16_OXYGEN_REACTION,
        'candidate_carbon_sources': list(MISSION16_CANDIDATE_CARBON_SOURCES),
        'source_names': dict(MISSION16_SOURCE_NAMES),
        'required_medium_fluxes': list(MISSION16_REQUIRED_MEDIUM_FLUXES),
        'candidate_trials': trials,
        'valid_trial_count': len(trials),
        'required_trial_count': len(MISSION16_CANDIDATE_CARBON_SOURCES),
        'missing_candidates': missing_candidates,
        'aerobic_screen_complete': aerobic_screen_complete,
        'ranked_candidates': ranked_candidates,
        'strongest_candidates': strongest_candidates,
        'strongest_candidate': strongest_candidate,
        'strongest_growth': round(float(strongest_growth), 6) if strongest_growth is not None else None,
        'expected_strongest_candidate': MISSION16_EXPECTED_STRONGEST_SOURCE,
        'expected_strongest_confirmed': expected_strongest_confirmed,
        'oxygen_challenge_run': oxygen_challenge_run,
        'oxygen_challenge_recorded': oxygen_challenge_recorded,
        'oxygen_challenge_infeasible': oxygen_challenge_infeasible,
        'relationship_supported': relationship_supported,
        'expected_factor': MISSION16_EXPECTED_FACTOR,
        'evidence_ready': evidence_ready,
        'answer_ready': evidence_ready,
        'ready_to_deliver': evidence_ready and relationship_supported,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': run_type,
        'current_selected_source': selected_source,
        'current_method': method_name,
        'current_objective': selected_objective,
        'current_result': objective_result,
        'current_result_infeasible': result_infeasible,
        'current_knocked_out_genes': knocked_out_genes,
        'current_bounds_complete': environment.get('bounds_complete'),
        'current_glucose_lower_bound_closed': environment.get('glucose_lower_bound_closed'),
        'current_oxygen_lower_bound_closed': oxygen_closed,
        'current_unexpected_environment_changes': list(environment.get('unexpected_environment_changes') or []),
        'current_missing_medium_fluxes': missing_medium_fluxes,
        'current_source_uptake': round(float(selected_source_uptake), 6) if selected_source_uptake is not None else None,
        'current_glucose_uptake': round(float(glucose_uptake), 6) if glucose_uptake is not None else None,
        'current_oxygen_uptake': round(float(oxygen_uptake), 6) if oxygen_uptake is not None else None,
        'current_issues': issues,
        'latest_attempt': {
            'valid': current_run_valid,
            'recorded': current_run_recorded,
            'run_type': run_type,
            'source_id': selected_source,
            'method': method_name,
            'objective': selected_objective,
            'infeasible': result_infeasible,
            'issues': list(issues),
        },
    }
    save_mission16_medium_report_check(data)
    return data


def run_mission16_medium_report_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    medium_fluxes = None
    objective_error = None

    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible Mission 16 simulation before recording evidence.'
    except Exception:
        objective_error = 'Could not read the current visible Mission 16 simulation result.'

    return _build_mission16_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission16_medium_report_check(),
        objective_error=objective_error,
    )


def run_mission16_medium_report_check_remote(backend_url, simulation_results=None):
    """Use the already visible remote result; never issue a hidden request."""
    return run_mission16_medium_report_check(simulation_results)


def build_mission16_context_report_text(report):
    if not report:
        return 'Mission 16 Context-Dependent Carbon Rescue\n\nActivate the mission and run the controlled screen.'

    lines = [
        'Mission 16 Context-Dependent Carbon Rescue',
        '',
        'Aerobic screening protocol:',
        '- FBA biomass objective; all genes active',
        '- Glucose uptake closed; one candidate source opened per run',
        '- Oxygen and every unrelated medium bound kept at model default',
        f'- Common molar uptake protocol: {MISSION16_EXPECTED_SOURCE_UPTAKE:.1f}',
        '',
        f"Candidate trials recorded: {report.get('valid_trial_count', 0)}/{report.get('required_trial_count', len(MISSION16_CANDIDATE_CARBON_SOURCES))}",
    ]

    trials = report.get('candidate_trials') or {}
    for source_id in MISSION16_CANDIDATE_CARBON_SOURCES:
        trial = trials.get(source_id)
        label = f"{MISSION16_SOURCE_NAMES.get(source_id, source_id)} ({source_id})"
        if not trial:
            lines.append(f'- {label}: not recorded')
            continue
        lines.append(
            f"- {label}: growth {float(trial.get('growth', 0.0)):.3f}; "
            f"source uptake {float(trial.get('source_uptake', 0.0)):.3f}; "
            f"oxygen uptake {float(trial.get('oxygen_uptake', 0.0)):.3f}"
        )

    if report.get('aerobic_screen_complete'):
        lines.extend(['', 'Aerobic screen complete.'])
        ranked = report.get('ranked_candidates') or []
        if ranked:
            lines.append('Growth ranking under this common molar protocol:')
            for index, row in enumerate(ranked, start=1):
                lines.append(
                    f"{index}. {MISSION16_SOURCE_NAMES.get(row.get('source_id'), row.get('source_id'))} "
                    f"({row.get('source_id')}): {float(row.get('growth', 0.0)):.3f}"
                )
            if report.get('strongest_candidate'):
                lines.append(
                    'Highest observed growth trial: '
                    f"{MISSION16_SOURCE_NAMES.get(report.get('strongest_candidate'), report.get('strongest_candidate'))} "
                    f"({report.get('strongest_candidate')})."
                )
        lines.append('This is a ranking under equal molar uptake bounds, not a universal carbon-efficiency ranking.')
    else:
        missing = report.get('missing_candidates') or []
        if missing:
            lines.append('Missing aerobic trials: ' + ', '.join(missing) + '.')

    challenge = report.get('oxygen_challenge_run') or {}
    lines.extend(['', 'Robustness challenge:'])
    if challenge:
        lines.extend([
            f"- Repeated source: {challenge.get('source_name')} ({challenge.get('source_id')})",
            f"- Changed factor: {MISSION16_OXYGEN_REACTION} lower bound closed",
            f"- Visible solver status: {str(challenge.get('status', '')).upper()}",
        ])
    elif report.get('aerobic_screen_complete'):
        lines.append('Repeat the uniquely strongest-growth source after closing oxygen uptake.')
    else:
        lines.append('Complete the aerobic screen before running this challenge.')

    if report.get('current_run_recorded'):
        lines.extend(['', f"Latest valid visible run recorded: {str(report.get('current_run_type', '')).replace('_', ' ')}."])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if trials or challenge:
            lines.append('Previously valid Mission 16 evidence remains available.')

    lines.append('')
    if report.get('evidence_ready'):
        lines.extend([
            'Evidence complete.',
            'Use the five-run ranking and the visible robustness-test status to answer Dr. Rio.',
            'Question: Which removed environmental factor did the strongest rescue depend on?',
        ])
    else:
        lines.append('Evidence incomplete.')

    lines.extend([
        '',
        'Interpretation note: the ranking is specific to this model, these bounds and this equal-molar protocol.',
        'An infeasible oxygen-removal result is a condition-specific model prediction, not a universal experimental claim.',
        'All growth and exchange values come from the visible solver results. No hidden simulation is used.',
    ])
    return '\n'.join(lines)

def is_mission17_unlocked(missions_completed):
    """Mission 17 starts only after the context-dependence mission."""
    return '16' in (missions_completed or [])


def _mission17_environment_status(reactions):
    """Describe the Mission 17 setup without relying on dictionary order.

    A baseline keeps every environmental bound at its model default.  A
    candidate trial closes only the lower bound of one candidate exchange,
    leaving its upper bound and every unrelated bound unchanged.
    """
    bounds_complete = True
    closed_candidate_nutrients = []
    unexpected_changes = []

    for i in range(len(REACTIONS.index)):
        reaction_id = REACTIONS.index[i]
        lower_open, upper_open = _reaction_bound_open_states(reactions, i)
        if lower_open is None or upper_open is None:
            bounds_complete = False
            continue

        default_lower_open = REACTIONS.lb.iloc[i] != 0
        default_upper_open = REACTIONS.ub.iloc[i] != 0
        lower_changed = lower_open != default_lower_open
        upper_changed = upper_open != default_upper_open

        if reaction_id in MISSION17_CANDIDATE_NUTRIENTS:
            if lower_changed and not lower_open:
                closed_candidate_nutrients.append(reaction_id)
            elif lower_changed:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    return {
        'bounds_complete': bounds_complete,
        'closed_candidate_nutrients': closed_candidate_nutrients,
        'unexpected_environment_changes': unexpected_changes,
        'all_bounds_default': not closed_candidate_nutrients and not unexpected_changes,
    }


def _mission17_direction(raw_flux):
    value = _as_float_or_none(raw_flux)
    if value is None:
        return 'unavailable'
    if value < -MISSION17_FLUX_TOLERANCE:
        return 'uptake'
    if value > MISSION17_FLUX_TOLERANCE:
        return 'secretion'
    return 'zero'


def _mission17_clean_number(value, decimals=6):
    """Round Mission 17 values and collapse numerical negative zero.

    This is deliberately presentation-safe rather than scientifically
    transformative: values whose magnitude is below the shared display
    tolerance are already indistinguishable from zero at the precision shown
    to the player.  Normalising them prevents ``-0.000`` from leaking into
    desktop reports, persisted JSON state, or the future browser interface.
    """
    numeric = round(float(value), int(decimals))
    if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
        return 0.0
    return numeric


def _mission17_classify_trials(baseline_run, trials):
    baseline_growth = _as_float_or_none((baseline_run or {}).get('growth'))
    rows = []
    collapse_candidates = []
    preserved_growth_candidates = []
    intermediate_candidates = []
    if baseline_growth is None or baseline_growth <= 0:
        return rows, collapse_candidates, preserved_growth_candidates, intermediate_candidates

    for reaction_id in MISSION17_CANDIDATE_NUTRIENTS:
        trial = (trials or {}).get(reaction_id)
        if not isinstance(trial, dict):
            continue
        growth = _as_float_or_none(trial.get('growth'))
        if growth is None:
            continue
        ratio = max(0.0, float(growth) / float(baseline_growth))
        if ratio <= MISSION17_COLLAPSE_RATIO:
            classification = 'collapse'
            collapse_candidates.append(reaction_id)
        elif ratio >= MISSION17_PRESERVED_RATIO:
            classification = 'preserved'
            preserved_growth_candidates.append(reaction_id)
        else:
            classification = 'intermediate'
            intermediate_candidates.append(reaction_id)
        rows.append({
            'reaction_id': reaction_id,
            'name': MISSION17_NUTRIENT_NAMES.get(reaction_id, reaction_id),
            'growth': round(float(growth), 6),
            'baseline_fraction': round(float(ratio), 6),
            'classification': classification,
        })
    return rows, collapse_candidates, preserved_growth_candidates, intermediate_candidates


def _normalise_mission17_text(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(char for char in text if not unicodedata.combining(char)).lower()


def normalise_mission17_answer(answer):
    """Extract candidate route identifiers from a concise player answer."""
    text = _normalise_mission17_text(answer)
    if not text.strip() or re.search(r'\b(?:all|every|todos|todas)\b', text):
        return tuple()

    patterns = {
        'EX_nh4_e': r'\b(?:ex[_\s-]*nh4[_\s-]*e|nh4|ammonia|ammonium|amonia|amonio)\b',
        'EX_pi_e': r'\b(?:ex[_\s-]*pi[_\s-]*e|pi|phosphate|fosfato)\b',
        'EX_h2o_e': r'\b(?:ex[_\s-]*h2o[_\s-]*e|h2o|water|agua)\b',
        # A standalone H/H+ is an unambiguous shorthand for the proton route
        # within this five-candidate answer field.  Recognising it prevents a
        # three-route answer such as 'h pi nh4' from being accepted after the
        # extra proton candidate was silently ignored.
        'EX_h_e': r'\b(?:ex[_\s-]*h[_\s-]*e|proton|protons|hydrogen ion|h)\b',
        'EX_co2_e': r'\b(?:ex[_\s-]*co2[_\s-]*e|co2|carbon dioxide|dioxido de carbono)\b',
    }
    found = {
        reaction_id for reaction_id, pattern in patterns.items()
        if re.search(pattern, text)
    }
    return tuple(
        reaction_id for reaction_id in MISSION17_CANDIDATE_NUTRIENTS
        if reaction_id in found
    )


def mission17_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission17_essential_medium_check() or {}
    expected = tuple(
        reaction_id for reaction_id in MISSION17_CANDIDATE_NUTRIENTS
        if reaction_id in set(report_data.get('collapse_candidates') or [])
    )
    return bool(
        report_data.get('evidence_ready')
        and report_data.get('relationship_supported')
        and expected
        and normalise_mission17_answer(answer) == expected
    )


def initialise_mission17_essential_routes():
    data = {
        'mission_id': '17',
        'check_version': MISSION17_CHECK_VERSION,
        'mission_title': 'Essential Uptake Routes',
        'target_context': MISSION17_TARGET_CONTEXT,
        'target_method': MISSION17_METHOD,
        'growth_objective': MISSION17_GROWTH_OBJECTIVE,
        'candidate_nutrients': list(MISSION17_CANDIDATE_NUTRIENTS),
        'nutrient_names': dict(MISSION17_NUTRIENT_NAMES),
        'required_medium_fluxes': list(MISSION17_REQUIRED_MEDIUM_FLUXES),
        'baseline_run': None,
        'baseline_ready': False,
        'candidate_trials': {},
        'valid_trial_count': 0,
        'required_trial_count': len(MISSION17_CANDIDATE_NUTRIENTS),
        'missing_candidates': list(MISSION17_CANDIDATE_NUTRIENTS),
        'screen_complete': False,
        'classified_trials': [],
        'collapse_candidates': [],
        'preserved_growth_candidates': [],
        'intermediate_candidates': [],
        'relationship_supported': False,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_run_valid': False,
        'current_run_recorded': False,
        'current_run_type': None,
        'current_issues': [],
        'latest_attempt': None,
    }
    save_mission17_essential_medium_check(data)
    return data


def _build_mission17_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
):
    """Validate and accumulate one visible Mission 17 experiment."""
    existing_report = existing_report or {}
    if (
        existing_report.get('mission_id') != '17'
        or existing_report.get('check_version') != MISSION17_CHECK_VERSION
    ):
        existing_report = {}

    baseline_run = copy.deepcopy(existing_report.get('baseline_run'))
    trials = copy.deepcopy(existing_report.get('candidate_trials') or {})

    method_correct = method_name == MISSION17_METHOD
    objective_correct = selected_objective == MISSION17_GROWTH_OBJECTIVE
    knocked_out_genes = _knocked_out_genes(genes)
    environment = _mission17_environment_status(reactions)
    closed = list(environment.get('closed_candidate_nutrients') or [])
    exactly_one_candidate_closed = len(closed) == 1
    selected_nutrient = closed[0] if exactly_one_candidate_closed else None
    run_type = 'baseline' if not closed else 'candidate_trial'

    objective_numeric = _as_float_or_none(objective_result)
    result_infeasible = 'INFEASIBLE' in str(objective_result or '').upper()
    result_available = objective_numeric is not None or result_infeasible
    raw_fluxes, uptake_fluxes, secretion_fluxes = _medium_flux_maps(medium_fluxes)
    missing_medium_fluxes = [
        reaction_id for reaction_id in MISSION17_REQUIRED_MEDIUM_FLUXES
        if reaction_id not in raw_fluxes
    ]
    selected_uptake = (
        _as_float_or_none(uptake_fluxes.get(selected_nutrient))
        if selected_nutrient else None
    )

    issues = []
    if objective_error:
        issues.append(objective_error)
    if not method_correct:
        issues.append('Use FBA for every Mission 17 run.')
    if not objective_correct:
        issues.append('Use the biomass objective for every Mission 17 run.')
    if knocked_out_genes:
        issues.append('Keep every gene active; this is a controlled medium experiment.')
    if not environment.get('bounds_complete'):
        issues.append('The environmental-bound payload is incomplete.')
    if environment.get('unexpected_environment_changes'):
        issues.append('Keep every unrelated environmental bound at its model default.')
    if not result_available:
        issues.append('A visible solver result is required.')
    if result_infeasible or objective_numeric is None:
        issues.append('Mission 17 requires a numeric growth result for each controlled run.')
    if medium_fluxes and medium_fluxes.get('error'):
        issues.append('The Exchange Flux Report is unavailable for this run.')
    elif missing_medium_fluxes:
        issues.append('The Exchange Flux Report is missing required Mission 17 reactions.')

    if run_type == 'baseline':
        if not environment.get('all_bounds_default'):
            issues.append('Record the baseline with every environmental bound at its model default.')
        if objective_numeric is not None and objective_numeric < MISSION17_MIN_BASELINE_GROWTH:
            issues.append('The default-medium baseline does not show viable predicted growth.')
    else:
        if not baseline_run:
            issues.append('Record the default-medium baseline before candidate perturbations.')
        if not exactly_one_candidate_closed:
            issues.append('Close exactly one Mission 17 candidate lower bound per run.')
        if selected_uptake is None:
            issues.append('Numeric uptake evidence for the closed route is missing.')
        elif selected_uptake > MISSION17_FLUX_TOLERANCE:
            issues.append('The selected lower-bound closure did not block uptake through that route.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run = None
    if current_run_valid and run_type == 'baseline':
        current_run = {
            'run_type': 'baseline',
            'source': 'visible_simulation',
            'method': method_name,
            'objective': selected_objective,
            'growth': _mission17_clean_number(objective_numeric),
            'medium_raw_fluxes': {
                reaction_id: _mission17_clean_number(raw_fluxes[reaction_id])
                for reaction_id in MISSION17_REQUIRED_MEDIUM_FLUXES
            },
            'candidate_directions': {
                reaction_id: _mission17_direction(raw_fluxes[reaction_id])
                for reaction_id in MISSION17_CANDIDATE_NUTRIENTS
            },
        }
        baseline_run = current_run
        current_run_recorded = True
    elif current_run_valid and run_type == 'candidate_trial':
        baseline_growth = float(baseline_run.get('growth'))
        growth_ratio = max(0.0, float(objective_numeric) / baseline_growth)
        current_run = {
            'run_type': 'candidate_trial',
            'source': 'visible_simulation',
            'reaction_id': selected_nutrient,
            'name': MISSION17_NUTRIENT_NAMES.get(selected_nutrient, selected_nutrient),
            'method': method_name,
            'objective': selected_objective,
            'growth': _mission17_clean_number(objective_numeric),
            'baseline_fraction': round(float(growth_ratio), 6),
            'closed_route_raw_flux': _mission17_clean_number(raw_fluxes[selected_nutrient]),
            'closed_route_uptake': _mission17_clean_number(selected_uptake),
            'closed_route_secretion': _mission17_clean_number(secretion_fluxes[selected_nutrient]),
            'medium_raw_fluxes': {
                reaction_id: _mission17_clean_number(raw_fluxes[reaction_id])
                for reaction_id in MISSION17_REQUIRED_MEDIUM_FLUXES
            },
        }
        trials[selected_nutrient] = current_run
        current_run_recorded = True

    baseline_ready = isinstance(baseline_run, dict)
    missing_candidates = [
        reaction_id for reaction_id in MISSION17_CANDIDATE_NUTRIENTS
        if reaction_id not in trials
    ]
    screen_complete = baseline_ready and not missing_candidates
    classified, collapsed, preserved, intermediate = _mission17_classify_trials(baseline_run, trials)
    relationship_supported = bool(
        screen_complete
        and len(collapsed) == 2
        and len(preserved) == 3
        and not intermediate
    )
    evidence_ready = bool(screen_complete)

    data = {
        'mission_id': '17',
        'check_version': MISSION17_CHECK_VERSION,
        'mission_title': 'Essential Uptake Routes',
        'target_context': MISSION17_TARGET_CONTEXT,
        'target_method': MISSION17_METHOD,
        'growth_objective': MISSION17_GROWTH_OBJECTIVE,
        'candidate_nutrients': list(MISSION17_CANDIDATE_NUTRIENTS),
        'nutrient_names': dict(MISSION17_NUTRIENT_NAMES),
        'required_medium_fluxes': list(MISSION17_REQUIRED_MEDIUM_FLUXES),
        'baseline_run': baseline_run,
        'baseline_ready': baseline_ready,
        'candidate_trials': trials,
        'valid_trial_count': len(trials),
        'required_trial_count': len(MISSION17_CANDIDATE_NUTRIENTS),
        'missing_candidates': missing_candidates,
        'screen_complete': screen_complete,
        'classified_trials': classified,
        'collapse_candidates': collapsed,
        'preserved_growth_candidates': preserved,
        'intermediate_candidates': intermediate,
        'relationship_supported': relationship_supported,
        'evidence_ready': evidence_ready,
        'answer_ready': evidence_ready and relationship_supported,
        'ready_to_deliver': evidence_ready and relationship_supported,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': run_type,
        'current_selected_nutrient': selected_nutrient,
        'current_method': method_name,
        'current_objective': selected_objective,
        'current_result': objective_result,
        'current_result_infeasible': result_infeasible,
        'current_knocked_out_genes': knocked_out_genes,
        'current_bounds_complete': environment.get('bounds_complete'),
        'current_closed_candidate_nutrients': closed,
        'current_unexpected_environment_changes': list(environment.get('unexpected_environment_changes') or []),
        'current_missing_medium_fluxes': missing_medium_fluxes,
        'current_selected_uptake': round(float(selected_uptake), 6) if selected_uptake is not None else None,
        'current_issues': issues,
        'latest_attempt': {
            'valid': current_run_valid,
            'recorded': current_run_recorded,
            'run_type': run_type,
            'selected_nutrient': selected_nutrient,
            'method': method_name,
            'objective': selected_objective,
            'issues': list(issues),
        },
    }
    save_mission17_essential_medium_check(data)
    return data


def run_mission17_essential_medium_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible Mission 17 simulation before recording evidence.'
    except Exception:
        objective_error = 'Could not read the current visible Mission 17 simulation result.'

    return _build_mission17_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission17_essential_medium_check(),
        objective_error=objective_error,
    )


def run_mission17_essential_medium_check_remote(backend_url, simulation_results=None):
    """Use the already visible backend result; never issue a hidden request."""
    return run_mission17_essential_medium_check(simulation_results)


def build_mission17_essential_routes_report_text(report):
    if not report:
        return 'Mission 17 Essential Uptake Routes\n\nActivate the mission and record the default-medium baseline.'

    lines = [
        'Mission 17 Essential Uptake Routes',
        '',
        'Controlled protocol:',
        '- FBA biomass objective; all genes active',
        '- Baseline: every environmental bound at model default',
        '- Trials: close one candidate lower bound; keep every other bound at default',
        '- Signed exchange flux: negative = uptake; positive = secretion',
        '',
    ]

    baseline = report.get('baseline_run') or {}
    if baseline:
        lines.extend([
            f"Baseline growth: {_mission17_clean_number(baseline.get('growth', 0.0)):.3f}",
            'Baseline signed candidate fluxes:',
        ])
        baseline_fluxes = baseline.get('medium_raw_fluxes') or {}
        for reaction_id in MISSION17_CANDIDATE_NUTRIENTS:
            value = _as_float_or_none(baseline_fluxes.get(reaction_id))
            if value is None:
                lines.append(f'- {MISSION17_NUTRIENT_NAMES.get(reaction_id)} ({reaction_id}): unavailable')
            else:
                lines.append(
                    f'- {MISSION17_NUTRIENT_NAMES.get(reaction_id)} ({reaction_id}): '
                    f'{_mission17_clean_number(value):+.3f} ({_mission17_direction(value)})'
                )
    else:
        lines.append('Baseline: not recorded.')

    lines.extend([
        '',
        f"Candidate trials recorded: {report.get('valid_trial_count', 0)}/{report.get('required_trial_count', len(MISSION17_CANDIDATE_NUTRIENTS))}",
    ])
    trials = report.get('candidate_trials') or {}
    baseline_growth = _as_float_or_none(baseline.get('growth'))
    for reaction_id in MISSION17_CANDIDATE_NUTRIENTS:
        trial = trials.get(reaction_id)
        label = f"{MISSION17_NUTRIENT_NAMES.get(reaction_id, reaction_id)} ({reaction_id})"
        if not trial:
            lines.append(f'- {label}: not recorded')
            continue
        fraction = _as_float_or_none(trial.get('baseline_fraction'))
        percentage = float(fraction) * 100.0 if fraction is not None else 0.0
        growth_value = _mission17_clean_number(trial.get('growth', 0.0))
        closed_route_uptake = _mission17_clean_number(trial.get('closed_route_uptake', 0.0))
        lines.append(
            f"- {label}: growth {growth_value:.3f}; "
            f"{percentage:.1f}% of baseline; closed-route uptake {closed_route_uptake:.3f}"
        )

    if report.get('screen_complete'):
        lines.extend([
            '',
            'Controlled screen complete.',
            f"Trials at or below {MISSION17_COLLAPSE_RATIO * 100:.1f}% of baseline growth: {len(report.get('collapse_candidates') or [])}",
            f"Trials at or above {MISSION17_PRESERVED_RATIO * 100:.1f}% of baseline growth: {len(report.get('preserved_growth_candidates') or [])}",
        ])
    else:
        missing = report.get('missing_candidates') or []
        if missing:
            lines.append('Missing candidate trials: ' + ', '.join(missing) + '.')

    if report.get('current_run_recorded'):
        lines.extend(['', f"Latest valid visible run recorded: {str(report.get('current_run_type', '')).replace('_', ' ')}."])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if baseline or trials:
            lines.append('Previously valid Mission 17 evidence remains available.')

    lines.append('')
    if report.get('evidence_ready') and report.get('relationship_supported'):
        lines.extend([
            'Evidence complete.',
            'Use the five growth responses to identify the two required uptake routes.',
            'Question: Which two candidate uptake routes caused growth to collapse when their lower bounds were closed?',
        ])
    elif report.get('evidence_ready'):
        lines.append('Evidence complete, but the controlled screen does not show the expected two-collapse/three-preserved pattern.')
    else:
        lines.append('Evidence incomplete.')

    lines.extend([
        '',
        'Interpretation note: closing a lower bound blocks uptake but can leave positive secretion available.',
        'These results describe this model, objective and controlled medium; they are not universal experimental claims.',
        'All growth and signed exchange values come from visible solver results. No hidden simulation is used.',
    ])
    return '\n'.join(lines)


def is_mission18_unlocked(missions_completed):
    """Mission 18 starts only after the essential-uptake screen."""
    return '17' in (missions_completed or [])


def _mission18_clean_number(value, decimals=6):
    numeric = round(float(value), int(decimals))
    if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
        return 0.0
    return numeric


def _mission18_environment_status(reactions):
    """Describe the anaerobic baseline and candidate upper-bound closures.

    Every valid run closes only the oxygen lower bound.  A candidate trial
    additionally closes exactly one export upper bound (acetate or succinate),
    leaving candidate lower bounds and every unrelated bound at model default.
    The reader uses explicit reaction-index keys and keeps the legacy positional
    fallback for old desktop saves.
    """
    bounds_complete = True
    oxygen_lower_bound_closed = False
    closed_candidate_upper_bounds = []
    unexpected_changes = []

    for i in range(len(REACTIONS.index)):
        reaction_id = REACTIONS.index[i]
        lower_open, upper_open = _reaction_bound_open_states(reactions, i)
        if lower_open is None or upper_open is None:
            bounds_complete = False
            continue

        default_lower_open = REACTIONS.lb.iloc[i] != 0
        default_upper_open = REACTIONS.ub.iloc[i] != 0
        lower_changed = lower_open != default_lower_open
        upper_changed = upper_open != default_upper_open

        if reaction_id == MISSION18_OXYGEN_REACTION:
            oxygen_lower_bound_closed = not lower_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            if lower_changed and lower_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            continue

        if reaction_id in MISSION18_CANDIDATE_EXPORTS:
            if upper_changed and not upper_open:
                closed_candidate_upper_bounds.append(reaction_id)
            elif upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            if lower_changed:
                unexpected_changes.append(f'{reaction_id} lower bound')
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    return {
        'bounds_complete': bounds_complete,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'closed_candidate_upper_bounds': closed_candidate_upper_bounds,
        'unexpected_environment_changes': unexpected_changes,
        'baseline_environment': (
            bounds_complete
            and oxygen_lower_bound_closed
            and not closed_candidate_upper_bounds
            and not unexpected_changes
        ),
    }


def _mission18_measured_production_values(production_fluxes):
    """Return only numerically measured production/export values."""
    values = {}
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return values
    for item in production_fluxes.get('items') or []:
        if not isinstance(item, dict) or item.get('error'):
            continue
        reaction_id = item.get('reaction_id')
        value = _as_float_or_none(item.get('production_flux'))
        if reaction_id and value is not None:
            values[str(reaction_id)] = _mission18_clean_number(max(float(value), 0.0))
    return values


def _mission18_classify_trials(baseline_run, trials):
    baseline_growth = _as_float_or_none((baseline_run or {}).get('growth'))
    baseline_fluxes = (baseline_run or {}).get('tracked_flux_values') or {}
    rows = []
    binding_candidates = []
    nonbinding_candidates = []
    intermediate_candidates = []
    if baseline_growth is None or baseline_growth <= 0:
        return rows, binding_candidates, nonbinding_candidates, intermediate_candidates

    for reaction_id in MISSION18_CANDIDATE_EXPORTS:
        trial = (trials or {}).get(reaction_id)
        if not isinstance(trial, dict):
            continue
        growth = _as_float_or_none(trial.get('growth'))
        trial_fluxes = trial.get('tracked_flux_values') or {}
        baseline_export = _as_float_or_none(baseline_fluxes.get(reaction_id))
        closed_export = _as_float_or_none(trial_fluxes.get(reaction_id))
        if growth is None or baseline_export is None or closed_export is None:
            continue

        growth_ratio = max(0.0, float(growth) / float(baseline_growth))
        flux_changes = {
            flux_id: _mission18_clean_number(
                float(trial_fluxes.get(flux_id, 0.0)) - float(baseline_fluxes.get(flux_id, 0.0))
            )
            for flux_id in MISSION18_REQUIRED_TRACKED_FLUXES
        }
        maximum_change = max((abs(value) for value in flux_changes.values()), default=0.0)
        export_closed = closed_export <= MISSION18_MAX_CLOSED_EXPORT_FLUX
        baseline_export_active = baseline_export > MISSION18_MIN_ACTIVE_BASELINE_EXPORT
        measurable_response = (
            growth_ratio <= MISSION18_MAX_BINDING_GROWTH_RATIO
            or maximum_change >= MISSION18_PROFILE_CHANGE_THRESHOLD
        )
        baseline_like_response = (
            growth_ratio >= MISSION18_BASELINE_LIKE_RATIO
            and maximum_change <= MISSION18_PROFILE_SIMILARITY_TOLERANCE
        )

        if (
            baseline_export_active
            and export_closed
            and growth_ratio >= MISSION18_MIN_BINDING_VIABILITY_RATIO
            and measurable_response
        ):
            classification = 'binding'
            binding_candidates.append(reaction_id)
        elif (
            not baseline_export_active
            and export_closed
            and baseline_like_response
        ):
            classification = 'nonbinding'
            nonbinding_candidates.append(reaction_id)
        else:
            classification = 'intermediate'
            intermediate_candidates.append(reaction_id)

        rows.append({
            'reaction_id': reaction_id,
            'name': MISSION18_FLUX_NAMES.get(reaction_id, reaction_id),
            'baseline_export': _mission18_clean_number(baseline_export),
            'closed_export': _mission18_clean_number(closed_export),
            'growth': _mission18_clean_number(growth),
            'baseline_fraction': _mission18_clean_number(growth_ratio),
            'maximum_profile_change': _mission18_clean_number(maximum_change),
            'flux_changes': flux_changes,
            'classification': classification,
        })
    return rows, binding_candidates, nonbinding_candidates, intermediate_candidates


def _normalise_mission18_text(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(char for char in text if not unicodedata.combining(char)).lower()


def normalise_mission18_answer(answer):
    """Extract candidate export identifiers from a concise answer."""
    text = _normalise_mission18_text(answer)
    if not text.strip() or re.search(r'\b(?:all|both|every|todos|todas|ambos|ambas)\b', text):
        return tuple()
    # Recognise every tracked export route, not only the two candidates.
    # This prevents an answer such as 'acetate and ethanol' from passing after
    # the additional route was silently ignored.  The UI deliberately asks for
    # one concise route rather than an explanatory sentence.
    patterns = {
        'EX_ac_e': r'\b(?:ex[_\s-]*ac[_\s-]*e|acetate|acetato)\b',
        'EX_etoh_e': r'\b(?:ex[_\s-]*etoh[_\s-]*e|ethanol|etanol)\b',
        'EX_for_e': r'\b(?:ex[_\s-]*for[_\s-]*e|formate|formato)\b',
        'EX_succ_e': r'\b(?:ex[_\s-]*succ[_\s-]*e|succinate|succinato)\b',
        'EX_lac__D_e': r'\b(?:ex[_\s-]*lac[_\s-]*d[_\s-]*e|d[-\s]*lactate|lactate|lactato)\b',
    }
    found = {
        reaction_id for reaction_id, pattern in patterns.items()
        if re.search(pattern, text)
    }
    return tuple(
        reaction_id for reaction_id in MISSION18_REQUIRED_TRACKED_FLUXES
        if reaction_id in found
    )


def mission18_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission18_export_bottleneck_check() or {}
    expected = tuple(
        reaction_id for reaction_id in MISSION18_CANDIDATE_EXPORTS
        if reaction_id in set(report_data.get('binding_candidates') or [])
    )
    return bool(
        report_data.get('evidence_ready')
        and report_data.get('relationship_supported')
        and expected
        and normalise_mission18_answer(answer) == expected
    )


def initialise_mission18_binding_export_screen():
    data = {
        'mission_id': '18',
        'check_version': MISSION18_CHECK_VERSION,
        'mission_title': 'Binding Export Constraints',
        'target_context': MISSION18_TARGET_CONTEXT,
        'target_method': MISSION18_METHOD,
        'growth_objective': MISSION18_GROWTH_OBJECTIVE,
        'oxygen_reaction': MISSION18_OXYGEN_REACTION,
        'candidate_exports': list(MISSION18_CANDIDATE_EXPORTS),
        'export_names': dict(MISSION18_EXPORT_NAMES),
        'required_tracked_fluxes': list(MISSION18_REQUIRED_TRACKED_FLUXES),
        'required_medium_fluxes': list(MISSION18_REQUIRED_MEDIUM_FLUXES),
        'baseline_run': None,
        'baseline_ready': False,
        'candidate_trials': {},
        'valid_trial_count': 0,
        'required_trial_count': len(MISSION18_CANDIDATE_EXPORTS),
        'missing_candidates': list(MISSION18_CANDIDATE_EXPORTS),
        'screen_complete': False,
        'classified_trials': [],
        'binding_candidates': [],
        'nonbinding_candidates': [],
        'intermediate_candidates': [],
        'relationship_supported': False,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_run_valid': False,
        'current_run_recorded': False,
        'current_run_type': None,
        'current_issues': [],
        'latest_attempt': None,
    }
    save_mission18_export_bottleneck_check(data)
    return data


def _build_mission18_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    selected_fluxes=None,
    objective_error=None,
):
    """Validate and accumulate one visible Mission 18 experiment."""
    existing_report = existing_report or {}
    if (
        existing_report.get('mission_id') != '18'
        or existing_report.get('check_version') != MISSION18_CHECK_VERSION
    ):
        existing_report = {}

    baseline_run = copy.deepcopy(existing_report.get('baseline_run'))
    trials = copy.deepcopy(existing_report.get('candidate_trials') or {})
    method_correct = method_name == MISSION18_METHOD
    objective_correct = selected_objective == MISSION18_GROWTH_OBJECTIVE
    knocked_out_genes = _knocked_out_genes(genes)
    environment = _mission18_environment_status(reactions)
    closed = list(environment.get('closed_candidate_upper_bounds') or [])
    exactly_one_candidate_closed = len(closed) == 1
    selected_export = closed[0] if exactly_one_candidate_closed else None
    run_type = 'baseline' if not closed else 'candidate_trial'

    objective_numeric = _as_float_or_none(objective_result)
    result_infeasible = 'INFEASIBLE' in str(objective_result or '').upper()
    result_available = objective_numeric is not None
    raw_fluxes, uptake_fluxes, secretion_fluxes = _medium_flux_maps(medium_fluxes)
    measured_production = _mission18_measured_production_values(production_fluxes)
    if selected_fluxes is None:
        selected_fluxes = _read_selected_production_fluxes()
    selected_fluxes = list(selected_fluxes or [])

    missing_medium_fluxes = [
        reaction_id for reaction_id in MISSION18_REQUIRED_MEDIUM_FLUXES
        if reaction_id not in raw_fluxes
    ]
    missing_selected_fluxes = [
        reaction_id for reaction_id in MISSION18_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    missing_measured_fluxes = [
        reaction_id for reaction_id in MISSION18_REQUIRED_TRACKED_FLUXES
        if reaction_id not in measured_production
    ]

    glucose_uptake = _as_float_or_none(uptake_fluxes.get(MISSION18_GLUCOSE_REACTION))
    oxygen_uptake = _as_float_or_none(uptake_fluxes.get(MISSION18_OXYGEN_REACTION))
    selected_export_value = (
        _as_float_or_none(measured_production.get(selected_export))
        if selected_export else None
    )

    issues = []
    if objective_error:
        issues.append(objective_error)
    if not method_correct:
        issues.append('Use FBA for every Mission 18 run.')
    if not objective_correct:
        issues.append('Use the biomass objective for every Mission 18 run.')
    if knocked_out_genes:
        issues.append('Keep every gene active; this is an exchange-bound experiment.')
    if not environment.get('bounds_complete'):
        issues.append('The environmental-bound payload is incomplete.')
    if not environment.get('oxygen_lower_bound_closed'):
        issues.append('Close only the oxygen lower bound in the shared anaerobic setup.')
    if environment.get('unexpected_environment_changes'):
        issues.append('Keep every unrelated environmental bound at its model default.')
    if result_infeasible or not result_available:
        issues.append('Mission 18 requires a numeric viable growth result for every controlled run.')
    if medium_fluxes and medium_fluxes.get('error'):
        issues.append('The Exchange Flux Report is unavailable for this run.')
    elif missing_medium_fluxes:
        issues.append('The Exchange Flux Report is missing required Mission 18 reactions.')
    if production_fluxes and production_fluxes.get('error'):
        issues.append('The Production Flux report is unavailable for this run.')
    elif missing_measured_fluxes:
        issues.append('The Production Flux report is missing numeric Mission 18 values.')
    if missing_selected_fluxes:
        issues.append('Select the complete Mission 18 product/byproduct panel.')
    if glucose_uptake is None or oxygen_uptake is None:
        issues.append('Numeric glucose and oxygen uptake evidence is required.')
    else:
        if abs(glucose_uptake - MISSION18_EXPECTED_GLUCOSE_UPTAKE) > MISSION18_GLUCOSE_UPTAKE_TOLERANCE:
            issues.append('The anaerobic baseline must retain the model-default glucose uptake protocol.')
        if oxygen_uptake > MISSION18_FLUX_TOLERANCE:
            issues.append('The oxygen lower-bound closure did not eliminate oxygen uptake.')

    for reaction_id in MISSION18_REQUIRED_TRACKED_FLUXES:
        if reaction_id not in raw_fluxes or reaction_id not in measured_production:
            continue
        expected_secretion = max(float(raw_fluxes[reaction_id]), 0.0)
        if abs(float(measured_production[reaction_id]) - expected_secretion) > MISSION18_FLUX_TOLERANCE:
            issues.append('Production Flux and Exchange Flux evidence do not describe the same visible solution.')
            break

    if run_type == 'baseline':
        if not environment.get('baseline_environment'):
            issues.append('Record the baseline with only the oxygen lower bound closed.')
        if objective_numeric is not None and objective_numeric < MISSION18_MIN_BASELINE_GROWTH:
            issues.append('The anaerobic baseline does not show viable predicted growth.')
    else:
        if not baseline_run:
            issues.append('Record the anaerobic baseline before upper-bound trials.')
        if not exactly_one_candidate_closed:
            issues.append('Close exactly one Mission 18 candidate upper bound per run.')
        if selected_export_value is None:
            issues.append('Numeric export evidence for the closed route is missing.')
        elif selected_export_value > MISSION18_MAX_CLOSED_EXPORT_FLUX:
            issues.append('The selected upper-bound closure did not block export through that route.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run = None
    if current_run_valid and run_type == 'baseline':
        current_run = {
            'run_type': 'baseline',
            'source': 'visible_simulation',
            'method': method_name,
            'objective': selected_objective,
            'growth': _mission18_clean_number(objective_numeric),
            'glucose_uptake': _mission18_clean_number(glucose_uptake),
            'oxygen_uptake': _mission18_clean_number(oxygen_uptake),
            'tracked_flux_values': {
                reaction_id: _mission18_clean_number(measured_production[reaction_id])
                for reaction_id in MISSION18_REQUIRED_TRACKED_FLUXES
            },
            'medium_raw_fluxes': {
                reaction_id: _mission18_clean_number(raw_fluxes[reaction_id])
                for reaction_id in MISSION18_REQUIRED_MEDIUM_FLUXES
            },
        }
        baseline_run = current_run
        current_run_recorded = True
    elif current_run_valid and run_type == 'candidate_trial':
        baseline_growth = float(baseline_run.get('growth'))
        growth_ratio = max(0.0, float(objective_numeric) / baseline_growth)
        current_run = {
            'run_type': 'candidate_trial',
            'source': 'visible_simulation',
            'reaction_id': selected_export,
            'name': MISSION18_EXPORT_NAMES.get(selected_export, selected_export),
            'method': method_name,
            'objective': selected_objective,
            'growth': _mission18_clean_number(objective_numeric),
            'baseline_fraction': _mission18_clean_number(growth_ratio),
            'glucose_uptake': _mission18_clean_number(glucose_uptake),
            'oxygen_uptake': _mission18_clean_number(oxygen_uptake),
            'tracked_flux_values': {
                reaction_id: _mission18_clean_number(measured_production[reaction_id])
                for reaction_id in MISSION18_REQUIRED_TRACKED_FLUXES
            },
            'medium_raw_fluxes': {
                reaction_id: _mission18_clean_number(raw_fluxes[reaction_id])
                for reaction_id in MISSION18_REQUIRED_MEDIUM_FLUXES
            },
        }
        trials[selected_export] = current_run
        current_run_recorded = True

    classified, binding, nonbinding, intermediate = _mission18_classify_trials(baseline_run, trials)
    valid_trial_count = len(trials)
    missing_candidates = [
        reaction_id for reaction_id in MISSION18_CANDIDATE_EXPORTS
        if reaction_id not in trials
    ]
    baseline_ready = bool(baseline_run)
    screen_complete = baseline_ready and valid_trial_count == len(MISSION18_CANDIDATE_EXPORTS)
    relationship_supported = bool(
        screen_complete
        and binding == [MISSION18_EXPECTED_BINDING_EXPORT]
        and nonbinding == [MISSION18_EXPECTED_NONBINDING_EXPORT]
        and not intermediate
    )

    latest_attempt = {
        'method': method_name,
        'objective': selected_objective,
        'run_type': run_type,
        'selected_export': selected_export,
        'objective_result': str(objective_result),
        'issues': list(issues),
        'recorded': current_run_recorded,
    }
    report = {
        'mission_id': '18',
        'check_version': MISSION18_CHECK_VERSION,
        'mission_title': 'Binding Export Constraints',
        'target_context': MISSION18_TARGET_CONTEXT,
        'target_method': MISSION18_METHOD,
        'growth_objective': MISSION18_GROWTH_OBJECTIVE,
        'oxygen_reaction': MISSION18_OXYGEN_REACTION,
        'candidate_exports': list(MISSION18_CANDIDATE_EXPORTS),
        'export_names': dict(MISSION18_EXPORT_NAMES),
        'required_tracked_fluxes': list(MISSION18_REQUIRED_TRACKED_FLUXES),
        'required_medium_fluxes': list(MISSION18_REQUIRED_MEDIUM_FLUXES),
        'baseline_run': baseline_run,
        'baseline_ready': baseline_ready,
        'candidate_trials': trials,
        'valid_trial_count': valid_trial_count,
        'required_trial_count': len(MISSION18_CANDIDATE_EXPORTS),
        'missing_candidates': missing_candidates,
        'screen_complete': screen_complete,
        'classified_trials': classified,
        'binding_candidates': binding,
        'nonbinding_candidates': nonbinding,
        'intermediate_candidates': intermediate,
        'relationship_supported': relationship_supported,
        'evidence_ready': screen_complete,
        'answer_ready': relationship_supported,
        'ready_to_deliver': relationship_supported,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': run_type,
        'current_issues': issues,
        'current_run': current_run,
        'latest_attempt': latest_attempt,
        'current_selected_export': selected_export,
        'current_selected_export_value': _mission18_clean_number(selected_export_value) if selected_export_value is not None else None,
        'current_glucose_uptake': _mission18_clean_number(glucose_uptake) if glucose_uptake is not None else None,
        'current_oxygen_uptake': _mission18_clean_number(oxygen_uptake) if oxygen_uptake is not None else None,
        'minimum_baseline_growth': MISSION18_MIN_BASELINE_GROWTH,
        'minimum_binding_viability_ratio': MISSION18_MIN_BINDING_VIABILITY_RATIO,
        'maximum_binding_growth_ratio': MISSION18_MAX_BINDING_GROWTH_RATIO,
        'baseline_like_ratio': MISSION18_BASELINE_LIKE_RATIO,
        'minimum_active_baseline_export': MISSION18_MIN_ACTIVE_BASELINE_EXPORT,
        'maximum_closed_export_flux': MISSION18_MAX_CLOSED_EXPORT_FLUX,
    }
    save_mission18_export_bottleneck_check(report)
    return report


def run_mission18_export_bottleneck_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
    except Exception:
        objective_result = None
    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 18.'

    return _build_mission18_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission18_export_bottleneck_check() or {},
        objective_error=objective_error,
    )


def run_mission18_export_bottleneck_check_remote(backend_url, simulation_results=None):
    """Browser parity wrapper: validate the already visible backend result."""
    del backend_url
    return run_mission18_export_bottleneck_check(simulation_results)


def build_mission18_binding_export_report_text(report):
    if not report:
        return 'Mission 18 Binding Export Constraints\n\nActivate the mission and record the anaerobic baseline.'
    if report.get('mission_id') != '18' or report.get('check_version') != MISSION18_CHECK_VERSION:
        return 'Mission 18 Binding Export Constraints\n\nCurrent-format evidence has not been recorded yet.'

    lines = [
        'Mission 18 Binding Export Constraints',
        '',
        'Controlled protocol:',
        '- FBA biomass objective; all genes active',
        '- Oxygen uptake closed in every run; every unrelated bound at model default',
        '- Baseline: no candidate upper-bound closure',
        '- Trials: close one candidate export upper bound per run',
        '- Complete product/byproduct panel measured from the visible solution',
        '',
    ]

    baseline = report.get('baseline_run') or {}
    if baseline:
        lines.extend([
            f"Baseline growth: {float(baseline.get('growth', 0.0)):.3f}",
            f"Baseline glucose uptake: {float(baseline.get('glucose_uptake', 0.0)):.3f}",
            f"Baseline oxygen uptake: {float(baseline.get('oxygen_uptake', 0.0)):.3f}",
            'Baseline export profile:',
        ])
        baseline_fluxes = baseline.get('tracked_flux_values') or {}
        for reaction_id in MISSION18_REQUIRED_TRACKED_FLUXES:
            lines.append(
                f"- {MISSION18_FLUX_NAMES.get(reaction_id, reaction_id)} ({reaction_id}): "
                f"{float(baseline_fluxes.get(reaction_id, 0.0)):.3f}"
            )
    else:
        lines.append('Baseline: not recorded.')

    trials = report.get('candidate_trials') or {}
    lines.extend(['', f"Candidate trials recorded: {len(trials)}/{len(MISSION18_CANDIDATE_EXPORTS)}"])
    for reaction_id in MISSION18_CANDIDATE_EXPORTS:
        trial = trials.get(reaction_id)
        label = MISSION18_EXPORT_NAMES.get(reaction_id, reaction_id)
        if not trial:
            lines.append(f'- {label} upper-bound closure ({reaction_id}): not recorded')
            continue
        lines.append(
            f"- {label} upper-bound closure ({reaction_id}): growth {float(trial.get('growth', 0.0)):.3f}; "
            f"{float(trial.get('baseline_fraction', 0.0)) * 100:.1f}% of baseline"
        )
        fluxes = trial.get('tracked_flux_values') or {}
        lines.append(
            '  Export profile: ' + '; '.join(
                f"{flux_id} {float(fluxes.get(flux_id, 0.0)):.3f}"
                for flux_id in MISSION18_REQUIRED_TRACKED_FLUXES
            )
        )

    if report.get('screen_complete'):
        lines.extend([
            '',
            'Controlled screen complete.',
            f"Trials with active baseline export and a measurable response: {len(report.get('binding_candidates') or [])}",
            f"Trials with inactive baseline export and a baseline-like response: {len(report.get('nonbinding_candidates') or [])}",
        ])
    else:
        missing = report.get('missing_candidates') or []
        if missing:
            lines.append('Missing upper-bound trials: ' + ', '.join(missing) + '.')

    if report.get('current_run_recorded'):
        lines.extend(['', f"Latest valid visible run recorded: {str(report.get('current_run_type', '')).replace('_', ' ')}."])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if baseline or trials:
            lines.append('Previously valid Mission 18 evidence remains available.')

    lines.append('')
    if report.get('evidence_ready') and report.get('relationship_supported'):
        lines.extend([
            'Evidence complete.',
            'Compare the baseline export state with both upper-bound trials.',
            'Question: Which upper-bound closure created the binding export constraint in this controlled screen?',
        ])
    elif report.get('evidence_ready'):
        lines.append('Evidence complete, but the visible comparison does not identify one binding and one non-binding constraint.')
    else:
        lines.append('Evidence incomplete.')

    lines.extend([
        '',
        'Interpretation note: a bound can be present without being binding; its effect depends on whether the baseline solution uses that flux direction.',
        'The observed redistribution is conditional on this model, anaerobic glucose medium and biomass objective.',
        'All growth, medium and export values come from the same visible solver results. No hidden simulation is used.',
    ])
    return '\n'.join(lines)


def is_mission19_unlocked(missions_completed):
    """Mission 19 starts only after the binding export-constraint screen."""
    return '18' in (missions_completed or [])


def _mission19_clean_number(value, decimals=6):
    numeric = round(float(value), int(decimals))
    if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
        return 0.0
    return numeric


def _mission19_measured_production_values(production_fluxes):
    """Return only numerically measured production values from the visible run."""
    values = {}
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return values
    for item in production_fluxes.get('items') or []:
        if not isinstance(item, dict) or item.get('error'):
            continue
        reaction_id = item.get('reaction_id')
        value = _as_float_or_none(item.get('production_flux'))
        if reaction_id and value is not None:
            values[str(reaction_id)] = _mission19_clean_number(max(float(value), 0.0))
    return values


def _mission19_disabled_reactions(knocked_out_genes):
    """Return the GPR-disabled reactions without launching a simulation.

    Desktop uses the complete SBML GPR evaluator.  The browser delegates the
    solver and GPR application to FastAPI, so it uses the audited static effect
    for the one Mission 19 perturbation.  Both paths describe the same model.
    """
    knocked_out_genes = list(knocked_out_genes or [])
    if model is not None:
        try:
            return sorted(disabled_reaction_ids(model, knocked_out_genes))
        except Exception:
            pass
    if knocked_out_genes == [MISSION19_TARGET_GENE]:
        return list(MISSION19_EXPECTED_DISABLED_REACTIONS)
    if knocked_out_genes == ['b2296']:
        return []
    return []


def _normalise_mission19_text(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(char for char in text if not unicodedata.combining(char)).lower()


def normalise_mission19_answer(answer):
    """Extract explicitly named simulation methods from a concise answer."""
    text = _normalise_mission19_text(answer)
    if not text.strip() or re.search(r'\b(?:all|both|every|todos|todas|ambos|ambas)\b', text):
        return tuple()
    patterns = {
        'FBA': r'(?<![a-z0-9])fba(?![a-z0-9])',
        'pFBA': r'(?<![a-z0-9])pfba(?![a-z0-9])|parsimonious\s+fba',
        'lMOMA': r'(?<![a-z0-9])l\s*[-_]?\s*moma(?![a-z0-9])|linear\s+(?:minimi[sz]ation\s+of\s+metabolic\s+adjustment|moma)',
        'ROOM': r'(?<![a-z0-9])room(?![a-z0-9])|regulatory\s+on\s*/?\s*off\s+minimi[sz]ation',
    }
    found = {method for method, pattern in patterns.items() if re.search(pattern, text)}
    return tuple(method for method in ('FBA', 'pFBA', 'lMOMA', 'ROOM') if method in found)


def mission19_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission19_perturbation_check() or {}
    expected = report_data.get('lower_biomass_method')
    return bool(
        report_data.get('evidence_ready')
        and report_data.get('relationship_supported')
        and expected == MISSION19_EXPECTED_LOWER_BIOMASS_METHOD
        and normalise_mission19_answer(answer) == (expected,)
    )


def initialise_mission19_method_comparison():
    data = {
        'mission_id': '19',
        'check_version': MISSION19_CHECK_VERSION,
        'mission_title': 'Re-optimisation vs Minimal Adjustment',
        'target_context': MISSION19_TARGET_CONTEXT,
        'baseline_method': MISSION19_BASELINE_METHOD,
        'target_method': MISSION19_TARGET_METHOD,
        'growth_objective': MISSION19_GROWTH_OBJECTIVE,
        'target_gene': MISSION19_TARGET_GENE,
        'target_gene_name': MISSION19_TARGET_GENE_NAME,
        'expected_disabled_reactions': list(MISSION19_EXPECTED_DISABLED_REACTIONS),
        'required_tracked_fluxes': list(MISSION19_REQUIRED_TRACKED_FLUXES),
        'baseline_run': None,
        'baseline_ready': False,
        'fba_mutant_run': None,
        'lmoma_mutant_run': None,
        'comparison_ready': False,
        'same_controlled_setup': False,
        'growth_ratios': {},
        'tracked_flux_differences': {},
        'lower_biomass_method': None,
        'relationship_supported': False,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_run_valid': False,
        'current_run_recorded': False,
        'current_run_type': None,
        'current_issues': [],
        'latest_attempt': None,
    }
    save_mission19_perturbation_check(data)
    return data


def _build_mission19_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    existing_report=None,
    selected_fluxes=None,
    objective_error=None,
):
    """Validate and accumulate one visible Mission 19 method-comparison run."""
    existing_report = existing_report or {}
    if (
        existing_report.get('mission_id') != '19'
        or existing_report.get('check_version') != MISSION19_CHECK_VERSION
    ):
        existing_report = {}

    baseline_run = copy.deepcopy(existing_report.get('baseline_run'))
    fba_mutant_run = copy.deepcopy(existing_report.get('fba_mutant_run'))
    lmoma_mutant_run = copy.deepcopy(existing_report.get('lmoma_mutant_run'))

    knocked_out_genes = _knocked_out_genes(genes)
    exact_target_knockout = knocked_out_genes == [MISSION19_TARGET_GENE]
    no_knockout = not knocked_out_genes
    disabled_reactions = _mission19_disabled_reactions(knocked_out_genes)
    target_gpr_effect = (
        exact_target_knockout
        and disabled_reactions == MISSION19_EXPECTED_DISABLED_REACTIONS
    )

    if no_knockout:
        run_type = 'baseline'
    elif exact_target_knockout and method_name == MISSION19_BASELINE_METHOD:
        run_type = 'fba_mutant'
    elif exact_target_knockout and method_name == MISSION19_TARGET_METHOD:
        run_type = 'lmoma_mutant'
    else:
        run_type = 'invalid'

    objective_numeric = _as_float_or_none(objective_result)
    result_infeasible = 'INFEASIBLE' in str(objective_result or '').upper()
    measured_production = _mission19_measured_production_values(production_fluxes)
    diagnostics = _method_diagnostics_from_production_data(production_fluxes)
    biomass_raw = _as_float_or_none(
        production_fluxes.get('biomass_raw') if isinstance(production_fluxes, dict) else None
    )
    primary_flux = _as_float_or_none(diagnostics.get('primary_objective_flux'))
    method_score = _as_float_or_none(diagnostics.get('method_score'))
    method_score_name = str(diagnostics.get('method_score_name') or '')
    if selected_fluxes is None:
        selected_fluxes = _read_selected_production_fluxes()
    selected_fluxes = list(selected_fluxes or [])

    missing_selected_fluxes = [
        reaction_id for reaction_id in MISSION19_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    missing_measured_fluxes = [
        reaction_id for reaction_id in MISSION19_REQUIRED_TRACKED_FLUXES
        if reaction_id not in measured_production
    ]

    issues = []
    if objective_error:
        issues.append(objective_error)
    if selected_objective != MISSION19_GROWTH_OBJECTIVE:
        issues.append('Use the biomass objective for every Mission 19 run.')
    if _environment_has_changes(reactions):
        issues.append('Keep every environmental bound at its model default.')
    if result_infeasible or objective_numeric is None:
        issues.append('Mission 19 requires a numeric viable biomass result.')
    if production_fluxes and production_fluxes.get('error'):
        issues.append('The Production Flux report is unavailable for this run.')
    elif missing_measured_fluxes:
        issues.append('The Production Flux report is missing numeric Mission 19 values.')
    if missing_selected_fluxes:
        issues.append('Select the complete Mission 19 product/byproduct panel.')
    if biomass_raw is None:
        issues.append('The visible result is missing the biomass-reaction flux.')
    if not diagnostics:
        issues.append('Method diagnostics are missing from the visible solver result.')
    else:
        if diagnostics.get('method') != method_name:
            issues.append('Method diagnostics do not match the selected simulation method.')
        if diagnostics.get('objective_reaction') != selected_objective:
            issues.append('Method diagnostics do not match the selected objective reaction.')
        if primary_flux is None:
            issues.append('The visible primary objective flux is missing from method diagnostics.')

    if objective_numeric is not None and biomass_raw is not None:
        if abs(float(objective_numeric) - float(biomass_raw)) > MISSION19_FLUX_TOLERANCE:
            issues.append('The displayed biomass and biomass flux do not describe the same visible solution.')
    if primary_flux is not None and biomass_raw is not None:
        if abs(float(primary_flux) - float(biomass_raw)) > MISSION19_FLUX_TOLERANCE:
            issues.append('Method diagnostics and biomass evidence do not describe the same visible solution.')

    if run_type == 'baseline':
        if method_name != MISSION19_BASELINE_METHOD:
            issues.append('Record the wild-type baseline with FBA.')
        if objective_numeric is not None and objective_numeric < MISSION19_MIN_BASELINE_GROWTH:
            issues.append('The wild-type baseline does not show viable predicted growth.')
    elif run_type in ('fba_mutant', 'lmoma_mutant'):
        if not baseline_run:
            issues.append('Record the wild-type FBA baseline before mutant runs.')
        if not target_gpr_effect:
            issues.append('Use the b0728 knockout that disables SUCOAS under the complete GPR rule.')
        if run_type == 'lmoma_mutant':
            if method_score is None:
                issues.append('The visible lMOMA adjustment score is missing.')
            elif method_score < MISSION19_MIN_LMOMA_ADJUSTMENT:
                issues.append('The lMOMA result does not show a measurable post-perturbation adjustment.')
            if method_score_name != MISSION19_LMOMA_SCORE_NAME:
                issues.append('The lMOMA adjustment score is not labelled with the expected method semantics.')
    else:
        if no_knockout:
            issues.append('Use FBA for the wild-type baseline.')
        elif not exact_target_knockout:
            issues.append('Use exactly the b0728 single-gene knockout for both mutant runs.')
        else:
            issues.append('Compare the b0728 mutant using FBA and lMOMA only.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run = None
    if current_run_valid:
        current_run = {
            'run_type': run_type,
            'source': 'visible_simulation',
            'method': method_name,
            'objective': selected_objective,
            'knocked_out_genes': list(knocked_out_genes),
            'disabled_reactions': list(disabled_reactions),
            'growth': _mission19_clean_number(biomass_raw),
            'tracked_flux_values': {
                reaction_id: _mission19_clean_number(measured_production[reaction_id])
                for reaction_id in MISSION19_REQUIRED_TRACKED_FLUXES
            },
            'method_diagnostics': {
                'primary_objective_flux': _mission19_clean_number(primary_flux),
                'method_score': _mission19_clean_number(method_score) if method_score is not None else None,
                'method_score_name': method_score_name,
            },
        }
        if run_type == 'baseline':
            baseline_run = current_run
        elif run_type == 'fba_mutant':
            fba_mutant_run = current_run
        elif run_type == 'lmoma_mutant':
            lmoma_mutant_run = current_run
        current_run_recorded = True

    baseline_ready = bool(baseline_run)
    comparison_ready = bool(baseline_run and fba_mutant_run and lmoma_mutant_run)
    growth_ratios = {}
    tracked_flux_differences = {}
    lower_biomass_method = None
    same_controlled_setup = False
    relationship_supported = False

    if comparison_ready:
        baseline_growth = float(baseline_run['growth'])
        fba_growth = float(fba_mutant_run['growth'])
        lmoma_growth = float(lmoma_mutant_run['growth'])
        growth_ratios = {
            'fba_mutant_vs_wt': _mission19_clean_number(fba_growth / baseline_growth),
            'lmoma_mutant_vs_wt': _mission19_clean_number(lmoma_growth / baseline_growth),
            'lmoma_vs_fba_mutant': _mission19_clean_number(lmoma_growth / fba_growth),
        }
        fba_fluxes = fba_mutant_run.get('tracked_flux_values') or {}
        lmoma_fluxes = lmoma_mutant_run.get('tracked_flux_values') or {}
        tracked_flux_differences = {
            reaction_id: _mission19_clean_number(
                float(lmoma_fluxes[reaction_id]) - float(fba_fluxes[reaction_id])
            )
            for reaction_id in MISSION19_REQUIRED_TRACKED_FLUXES
        }
        maximum_profile_difference = max(
            (abs(value) for value in tracked_flux_differences.values()), default=0.0
        )
        if lmoma_growth + MISSION19_MIN_BIOMASS_METHOD_GAP <= fba_growth:
            lower_biomass_method = 'lMOMA'
        elif fba_growth + MISSION19_MIN_BIOMASS_METHOD_GAP <= lmoma_growth:
            lower_biomass_method = 'FBA'

        same_controlled_setup = bool(
            baseline_run.get('objective') == fba_mutant_run.get('objective') == lmoma_mutant_run.get('objective') == MISSION19_GROWTH_OBJECTIVE
            and baseline_run.get('method') == MISSION19_BASELINE_METHOD
            and fba_mutant_run.get('method') == MISSION19_BASELINE_METHOD
            and lmoma_mutant_run.get('method') == MISSION19_TARGET_METHOD
            and not baseline_run.get('knocked_out_genes')
            and fba_mutant_run.get('knocked_out_genes') == [MISSION19_TARGET_GENE]
            and lmoma_mutant_run.get('knocked_out_genes') == [MISSION19_TARGET_GENE]
            and fba_mutant_run.get('disabled_reactions') == MISSION19_EXPECTED_DISABLED_REACTIONS
            and lmoma_mutant_run.get('disabled_reactions') == MISSION19_EXPECTED_DISABLED_REACTIONS
        )
        lmoma_score = _as_float_or_none(
            (lmoma_mutant_run.get('method_diagnostics') or {}).get('method_score')
        )
        relationship_supported = bool(
            same_controlled_setup
            and fba_growth / baseline_growth >= MISSION19_MIN_MUTANT_VIABILITY_RATIO
            and lmoma_growth / baseline_growth >= MISSION19_MIN_MUTANT_VIABILITY_RATIO
            and fba_growth <= baseline_growth + MISSION19_FLUX_TOLERANCE
            and lmoma_growth <= baseline_growth + MISSION19_FLUX_TOLERANCE
            and lower_biomass_method == MISSION19_EXPECTED_LOWER_BIOMASS_METHOD
            and lmoma_score is not None
            and lmoma_score >= MISSION19_MIN_LMOMA_ADJUSTMENT
            and maximum_profile_difference >= MISSION19_MIN_PROFILE_DIFFERENCE
        )

    latest_attempt = {
        'method': method_name,
        'objective': selected_objective,
        'run_type': run_type,
        'knocked_out_genes': list(knocked_out_genes),
        'objective_result': str(objective_result),
        'issues': list(issues),
        'recorded': current_run_recorded,
    }
    report = {
        'mission_id': '19',
        'check_version': MISSION19_CHECK_VERSION,
        'mission_title': 'Re-optimisation vs Minimal Adjustment',
        'target_context': MISSION19_TARGET_CONTEXT,
        'baseline_method': MISSION19_BASELINE_METHOD,
        'target_method': MISSION19_TARGET_METHOD,
        'growth_objective': MISSION19_GROWTH_OBJECTIVE,
        'target_gene': MISSION19_TARGET_GENE,
        'target_gene_name': MISSION19_TARGET_GENE_NAME,
        'expected_disabled_reactions': list(MISSION19_EXPECTED_DISABLED_REACTIONS),
        'required_tracked_fluxes': list(MISSION19_REQUIRED_TRACKED_FLUXES),
        'baseline_run': baseline_run,
        'baseline_ready': baseline_ready,
        'fba_mutant_run': fba_mutant_run,
        'lmoma_mutant_run': lmoma_mutant_run,
        'comparison_ready': comparison_ready,
        'same_controlled_setup': same_controlled_setup,
        'growth_ratios': growth_ratios,
        'tracked_flux_differences': tracked_flux_differences,
        'lower_biomass_method': lower_biomass_method,
        'relationship_supported': relationship_supported,
        'evidence_ready': comparison_ready,
        'answer_ready': relationship_supported,
        'ready_to_deliver': relationship_supported,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': run_type,
        'current_issues': issues,
        'current_run': current_run,
        'latest_attempt': latest_attempt,
        'current_biomass_flux': _mission19_clean_number(biomass_raw) if biomass_raw is not None else None,
        'current_method_score': _mission19_clean_number(method_score) if method_score is not None else None,
        'current_method_score_name': method_score_name or None,
        'minimum_baseline_growth': MISSION19_MIN_BASELINE_GROWTH,
        'minimum_mutant_viability_ratio': MISSION19_MIN_MUTANT_VIABILITY_RATIO,
        'minimum_biomass_method_gap': MISSION19_MIN_BIOMASS_METHOD_GAP,
        'minimum_lmoma_adjustment': MISSION19_MIN_LMOMA_ADJUSTMENT,
        'minimum_profile_difference': MISSION19_MIN_PROFILE_DIFFERENCE,
    }
    save_mission19_perturbation_check(report)
    return report


def run_mission19_perturbation_check(simulation_results=None):
    """Validate the already visible Mission 19 result without re-simulating."""
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
    except Exception:
        objective_result = None
    if objective_result is None:
        objective_error = 'Run the simulation before recording Mission 19 evidence.'

    return _build_mission19_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        existing_report=load_mission19_perturbation_check() or {},
        objective_error=objective_error,
    )


def run_mission19_perturbation_check_remote(backend_url, simulation_results=None):
    """Browser parity wrapper: validate the already visible backend result."""
    del backend_url
    return run_mission19_perturbation_check(simulation_results)


def build_mission19_method_comparison_report_text(report):
    if not report:
        return 'Mission 19 Re-optimisation vs Minimal Adjustment\n\nActivate the mission and record the wild-type FBA baseline.'
    if report.get('mission_id') != '19' or report.get('check_version') != MISSION19_CHECK_VERSION:
        return 'Mission 19 Re-optimisation vs Minimal Adjustment\n\nCurrent-format evidence has not been recorded yet.'

    lines = [
        'Mission 19 Re-optimisation vs Minimal Adjustment',
        '',
        'Controlled protocol:',
        '- Biomass objective; default medium; complete product/byproduct panel',
        '- Wild-type reference: FBA with all genes active',
        f'- Mutant comparison: the same {MISSION19_TARGET_GENE} / {MISSION19_TARGET_GENE_NAME} knockout under FBA and lMOMA',
        '- Only the simulation method changes between the two mutant runs',
        '- Biomass and method score are read from the same visible solver result',
        '',
    ]

    def add_run(title, run):
        if not run:
            lines.append(f'{title}: not recorded.')
            return
        lines.append(f'{title}:')
        lines.append(f"- Method: {run.get('method')}")
        lines.append(f"- Biomass flux: {float(run.get('growth', 0.0)):.3f}")
        if run.get('knocked_out_genes'):
            lines.append('- Knockout: ' + ', '.join(run.get('knocked_out_genes') or []))
            lines.append('- GPR-disabled reactions: ' + ', '.join(run.get('disabled_reactions') or []))
        diagnostics = run.get('method_diagnostics') or {}
        if run.get('method') == MISSION19_TARGET_METHOD and diagnostics.get('method_score') is not None:
            lines.append(f"- lMOMA adjustment score: {float(diagnostics.get('method_score')):.3f}")
        lines.append('- Product/byproduct profile:')
        fluxes = run.get('tracked_flux_values') or {}
        for reaction_id in MISSION19_REQUIRED_TRACKED_FLUXES:
            lines.append(f"  {reaction_id}: {float(fluxes.get(reaction_id, 0.0)):.3f}")

    add_run('Wild-type FBA baseline', report.get('baseline_run'))
    lines.append('')
    add_run('b0728 mutant under FBA', report.get('fba_mutant_run'))
    lines.append('')
    add_run('b0728 mutant under lMOMA', report.get('lmoma_mutant_run'))

    if report.get('comparison_ready'):
        ratios = report.get('growth_ratios') or {}
        differences = report.get('tracked_flux_differences') or {}
        lines.extend([
            '',
            'Controlled comparison complete.',
            f"FBA mutant biomass: {float((report.get('fba_mutant_run') or {}).get('growth', 0.0)):.3f} ({float(ratios.get('fba_mutant_vs_wt', 0.0)) * 100:.1f}% of WT)",
            f"lMOMA mutant biomass: {float((report.get('lmoma_mutant_run') or {}).get('growth', 0.0)):.3f} ({float(ratios.get('lmoma_mutant_vs_wt', 0.0)) * 100:.1f}% of WT)",
            'lMOMA minus FBA mutant product-flux differences:',
        ])
        for reaction_id in MISSION19_REQUIRED_TRACKED_FLUXES:
            lines.append(f"- {reaction_id}: {float(differences.get(reaction_id, 0.0)):+.3f}")

    if report.get('current_run_recorded'):
        lines.extend(['', f"Latest valid visible run recorded: {str(report.get('current_run_type', '')).replace('_', ' ')}."])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if report.get('baseline_run') or report.get('fba_mutant_run') or report.get('lmoma_mutant_run'):
            lines.append('Previously valid Mission 19 evidence remains available.')

    lines.append('')
    if report.get('evidence_ready') and report.get('relationship_supported'):
        lines.extend([
            'Evidence complete.',
            'Compare the two biomass values predicted for the same knockout.',
            'Question: Which method predicted the lower viable biomass response for the same b0728 knockout?',
        ])
    elif report.get('evidence_ready'):
        lines.append('Evidence complete, but the visible comparison does not support one lower viable method response.')
    else:
        lines.append('Evidence incomplete.')

    lines.extend([
        '',
        'Interpretation note: FBA re-optimises the selected objective, whereas lMOMA minimises total absolute flux adjustment from a reference state.',
        'The lMOMA adjustment score is not biomass; biomass is read from the biomass reaction in the same visible solution.',
        'All biomass, method-score and product-flux values come from visible solver results. No hidden simulation is used.',
    ])
    return '\n'.join(lines)

def is_mission20_unlocked(missions_completed):
    """Mission 20 starts only after the controlled Mission 19 comparison."""
    return '19' in (missions_completed or [])


def _mission20_clean_number(value, decimals=6):
    numeric = round(float(value), int(decimals))
    if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
        return 0.0
    return numeric


def _mission20_number_or_none(value):
    """Return a finite float or ``None`` for incomplete/invalid evidence."""
    try:
        numeric = float(value)
    except Exception:
        return None
    if numeric != numeric or numeric in (float('inf'), float('-inf')):
        return None
    return numeric


def _mission20_environment_status(reactions):
    """Describe the two-factor oxygen/acetate context for Mission 20.

    Valid runs leave the complete glucose medium at model defaults and vary
    only two toggles: the lower bound of oxygen uptake and the upper bound of
    acetate export.  Explicit reaction-index keys are order-independent; the
    positional fallback is retained only for legacy desktop saves.
    """
    bounds_complete = True
    oxygen_lower_bound_closed = False
    acetate_upper_bound_closed = False
    unexpected_changes = []

    for i in range(len(REACTIONS.index)):
        reaction_id = REACTIONS.index[i]
        lower_open, upper_open = _reaction_bound_open_states(reactions, i)
        if lower_open is None or upper_open is None:
            bounds_complete = False
            continue

        default_lower_open = REACTIONS.lb.iloc[i] != 0
        default_upper_open = REACTIONS.ub.iloc[i] != 0
        lower_changed = lower_open != default_lower_open
        upper_changed = upper_open != default_upper_open

        if reaction_id == MISSION20_OXYGEN_REACTION:
            oxygen_lower_bound_closed = not lower_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            if lower_changed and lower_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            continue

        if reaction_id == MISSION20_ACETATE_EXPORT:
            acetate_upper_bound_closed = not upper_open
            if lower_changed:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_changed and upper_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    context = 'oxygen_closed' if oxygen_lower_bound_closed else 'oxygen_available'
    run_type = f"{context}_{'acetate_closed' if acetate_upper_bound_closed else 'baseline'}"
    return {
        'bounds_complete': bounds_complete,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'acetate_upper_bound_closed': acetate_upper_bound_closed,
        'unexpected_environment_changes': unexpected_changes,
        'context': context,
        'run_type': run_type,
        'controlled_environment': bounds_complete and not unexpected_changes,
    }


def _mission20_measured_medium_values(medium_fluxes):
    """Return only complete numeric exchange measurements from one visible run."""
    raw_fluxes = {}
    uptake_fluxes = {}
    secretion_fluxes = {}
    if not isinstance(medium_fluxes, dict) or medium_fluxes.get('error'):
        return raw_fluxes, uptake_fluxes, secretion_fluxes
    for item in medium_fluxes.get('items') or []:
        if not isinstance(item, dict) or item.get('error'):
            continue
        reaction_id = item.get('reaction_id')
        raw_value = _mission20_number_or_none(item.get('raw_flux'))
        uptake_value = _mission20_number_or_none(item.get('uptake_flux'))
        secretion_value = _mission20_number_or_none(item.get('secretion_flux'))
        if (
            reaction_id
            and raw_value is not None
            and uptake_value is not None
            and secretion_value is not None
        ):
            reaction_id = str(reaction_id)
            raw_fluxes[reaction_id] = _mission20_clean_number(raw_value)
            uptake_fluxes[reaction_id] = _mission20_clean_number(max(float(uptake_value), 0.0))
            secretion_fluxes[reaction_id] = _mission20_clean_number(max(float(secretion_value), 0.0))
    return raw_fluxes, uptake_fluxes, secretion_fluxes


def _mission20_measured_production_values(production_fluxes):
    """Return only numerically measured export values from the visible run."""
    values = {}
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return values
    for item in production_fluxes.get('items') or []:
        if not isinstance(item, dict) or item.get('error'):
            continue
        reaction_id = item.get('reaction_id')
        value = _mission20_number_or_none(item.get('production_flux'))
        if reaction_id and value is not None:
            values[str(reaction_id)] = _mission20_clean_number(max(float(value), 0.0))
    return values


def _mission20_pair_analysis(baseline_run, closed_run):
    """Compare one oxygen context before and after acetate closure."""
    if not isinstance(baseline_run, dict) or not isinstance(closed_run, dict):
        return None

    baseline_growth = _mission20_number_or_none(baseline_run.get('growth'))
    closed_growth = _mission20_number_or_none(closed_run.get('growth'))
    baseline_fluxes = baseline_run.get('tracked_flux_values') or {}
    closed_fluxes = closed_run.get('tracked_flux_values') or {}
    baseline_acetate = _mission20_number_or_none(baseline_fluxes.get(MISSION20_ACETATE_EXPORT))
    closed_acetate = _mission20_number_or_none(closed_fluxes.get(MISSION20_ACETATE_EXPORT))
    if (
        baseline_growth is None
        or closed_growth is None
        or baseline_growth <= 0
        or baseline_acetate is None
        or closed_acetate is None
    ):
        return None

    growth_ratio = max(0.0, float(closed_growth) / float(baseline_growth))
    flux_changes = {}
    for reaction_id in MISSION20_REQUIRED_TRACKED_FLUXES:
        left = _mission20_number_or_none(baseline_fluxes.get(reaction_id))
        right = _mission20_number_or_none(closed_fluxes.get(reaction_id))
        if left is None or right is None:
            return None
        flux_changes[reaction_id] = _mission20_clean_number(float(right) - float(left))
    maximum_profile_change = max((abs(value) for value in flux_changes.values()), default=0.0)

    baseline_diagnostics = baseline_run.get('method_diagnostics') or {}
    closed_diagnostics = closed_run.get('method_diagnostics') or {}
    baseline_total = _mission20_number_or_none(baseline_diagnostics.get('total_absolute_flux'))
    closed_total = _mission20_number_or_none(closed_diagnostics.get('total_absolute_flux'))
    total_flux_change = None
    if baseline_total is not None and closed_total is not None:
        total_flux_change = _mission20_clean_number(float(closed_total) - float(baseline_total))

    try:
        active_reaction_change = int(closed_diagnostics.get('active_reaction_count')) - int(
            baseline_diagnostics.get('active_reaction_count')
        )
    except Exception:
        active_reaction_change = None

    baseline_export_active = baseline_acetate > MISSION20_MIN_ACTIVE_BASELINE_EXPORT
    export_closed = closed_acetate <= MISSION20_MAX_CLOSED_EXPORT_FLUX
    profile_changed = maximum_profile_change >= MISSION20_PROFILE_CHANGE_THRESHOLD
    profile_baseline_like = maximum_profile_change <= MISSION20_PROFILE_SIMILARITY_TOLERANCE
    parsimony_baseline_like = (
        total_flux_change is not None
        and abs(total_flux_change) <= MISSION20_PARSIMONY_SIMILARITY_TOLERANCE
    )

    binding_response = bool(
        baseline_export_active
        and export_closed
        and growth_ratio >= MISSION20_ANAEROBIC_MIN_VIABILITY_RATIO
        and growth_ratio <= MISSION20_ANAEROBIC_MAX_GROWTH_RATIO
        and profile_changed
    )
    nonbinding_response = bool(
        not baseline_export_active
        and export_closed
        and growth_ratio >= MISSION20_AEROBIC_BASELINE_LIKE_RATIO
        and profile_baseline_like
        and parsimony_baseline_like
        and active_reaction_change == 0
    )
    classification = (
        'binding_response'
        if binding_response
        else 'nonbinding_response'
        if nonbinding_response
        else 'intermediate'
    )
    return {
        'baseline_growth': _mission20_clean_number(baseline_growth),
        'closed_growth': _mission20_clean_number(closed_growth),
        'growth_ratio': _mission20_clean_number(growth_ratio),
        'baseline_acetate_export': _mission20_clean_number(baseline_acetate),
        'closed_acetate_export': _mission20_clean_number(closed_acetate),
        'flux_changes': flux_changes,
        'maximum_profile_change': _mission20_clean_number(maximum_profile_change),
        'total_absolute_flux_change': total_flux_change,
        'active_reaction_change': active_reaction_change,
        'baseline_export_active': baseline_export_active,
        'export_closed': export_closed,
        'classification': classification,
    }


def _normalise_mission20_text(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(char for char in text if not unicodedata.combining(char)).lower()


def normalise_mission20_answer(answer):
    """Extract exactly one oxygen context from a concise answer."""
    text = _normalise_mission20_text(answer)
    if not text.strip() or re.search(r'\b(?:both|all|either|neither|ambos|ambas|todos|todas)\b', text):
        return tuple()

    anaerobic_patterns = [
        r'\banaerobic\b',
        r'\banaerobio\b',
        r'\bwithout\s+(?:o2|oxygen)\b',
        r'\bno\s+(?:o2|oxygen)\b',
        r'\b(?:o2|oxygen)\s+(?:closed|unavailable|absent|removed|off)\b',
        r'\bex[_\s-]*o2[_\s-]*e\s+(?:closed|off)\b',
        r'\bsem\s+oxigenio\b',
        r'\boxigenio\s+(?:fechado|indisponivel|ausente|removido)\b',
    ]
    aerobic_patterns = [
        r'\baerobic\b',
        r'\baerobio\b',
        r'\bwith\s+(?:o2|oxygen)\b',
        r'\b(?:o2|oxygen)\s+(?:available|open|present|on)\b',
        r'\bex[_\s-]*o2[_\s-]*e\s+(?:open|on)\b',
        r'\bcom\s+oxigenio\b',
        r'\boxigenio\s+(?:aberto|disponivel|presente)\b',
    ]
    found = []
    if any(re.search(pattern, text) for pattern in anaerobic_patterns):
        found.append('oxygen_closed')
    if any(re.search(pattern, text) for pattern in aerobic_patterns):
        found.append('oxygen_available')
    return tuple(found)


def mission20_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission20_robustness_report_check() or {}
    expected = tuple(report_data.get('responsive_contexts') or [])
    return bool(
        report_data.get('evidence_ready')
        and report_data.get('relationship_supported')
        and expected == (MISSION20_EXPECTED_RESPONSE_CONTEXT,)
        and normalise_mission20_answer(answer) == expected
    )


def initialise_mission20_context_matrix():
    data = {
        'mission_id': '20',
        'check_version': MISSION20_CHECK_VERSION,
        'mission_title': 'Context-Specific Export Robustness',
        'target_context': MISSION20_TARGET_CONTEXT,
        'target_method': MISSION20_TARGET_METHOD,
        'growth_objective': MISSION20_GROWTH_OBJECTIVE,
        'oxygen_reaction': MISSION20_OXYGEN_REACTION,
        'acetate_export': MISSION20_ACETATE_EXPORT,
        'required_tracked_fluxes': list(MISSION20_REQUIRED_TRACKED_FLUXES),
        'required_medium_fluxes': list(MISSION20_REQUIRED_MEDIUM_FLUXES),
        'aerobic_baseline_run': None,
        'aerobic_acetate_closed_run': None,
        'anaerobic_baseline_run': None,
        'anaerobic_acetate_closed_run': None,
        'recorded_run_count': 0,
        'required_run_count': 4,
        'missing_run_types': [
            'oxygen_available_baseline',
            'oxygen_available_acetate_closed',
            'oxygen_closed_baseline',
            'oxygen_closed_acetate_closed',
        ],
        'all_runs_recorded': False,
        'same_controlled_setup': False,
        'aerobic_response': None,
        'anaerobic_response': None,
        'responsive_contexts': [],
        'nonresponsive_contexts': [],
        'relationship_supported': False,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_run_valid': False,
        'current_run_recorded': False,
        'current_run_type': None,
        'current_issues': [],
        'latest_attempt': None,
    }
    save_mission20_robustness_report_check(data)
    return data


def _build_mission20_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    selected_fluxes=None,
    objective_error=None,
):
    """Validate and accumulate one visible Mission 20 matrix run."""
    existing_report = existing_report or {}
    if (
        existing_report.get('mission_id') != '20'
        or existing_report.get('check_version') != MISSION20_CHECK_VERSION
    ):
        existing_report = {}

    slots = {
        'oxygen_available_baseline': copy.deepcopy(existing_report.get('aerobic_baseline_run')),
        'oxygen_available_acetate_closed': copy.deepcopy(existing_report.get('aerobic_acetate_closed_run')),
        'oxygen_closed_baseline': copy.deepcopy(existing_report.get('anaerobic_baseline_run')),
        'oxygen_closed_acetate_closed': copy.deepcopy(existing_report.get('anaerobic_acetate_closed_run')),
    }

    environment = _mission20_environment_status(reactions)
    run_type = environment.get('run_type')
    method_correct = method_name == MISSION20_TARGET_METHOD
    objective_correct = selected_objective == MISSION20_GROWTH_OBJECTIVE
    knocked_out_genes = _knocked_out_genes(genes)
    objective_numeric = _mission20_number_or_none(objective_result)
    result_infeasible = 'INFEASIBLE' in str(objective_result or '').upper()

    measured_production = _mission20_measured_production_values(production_fluxes)
    raw_fluxes, uptake_fluxes, secretion_fluxes = _mission20_measured_medium_values(medium_fluxes)
    diagnostics = _method_diagnostics_from_production_data(production_fluxes)
    biomass_raw = _mission20_number_or_none(_mission13_biomass_value(production_fluxes))
    primary_flux = _mission20_number_or_none(diagnostics.get('primary_objective_flux'))
    method_score = _mission20_number_or_none(diagnostics.get('method_score'))
    total_absolute_flux = _mission20_number_or_none(diagnostics.get('total_absolute_flux'))
    method_score_name = diagnostics.get('method_score_name')
    try:
        active_reaction_count = int(diagnostics.get('active_reaction_count'))
    except Exception:
        active_reaction_count = None

    if selected_fluxes is None:
        selected_fluxes = _read_selected_production_fluxes()
    selected_fluxes = list(selected_fluxes or [])

    missing_medium_fluxes = [
        reaction_id for reaction_id in MISSION20_REQUIRED_MEDIUM_FLUXES
        if reaction_id not in raw_fluxes
    ]
    missing_selected_fluxes = [
        reaction_id for reaction_id in MISSION20_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    missing_measured_fluxes = [
        reaction_id for reaction_id in MISSION20_REQUIRED_TRACKED_FLUXES
        if reaction_id not in measured_production
    ]

    glucose_uptake = _mission20_number_or_none(uptake_fluxes.get(MISSION20_GLUCOSE_REACTION))
    oxygen_uptake = _mission20_number_or_none(uptake_fluxes.get(MISSION20_OXYGEN_REACTION))
    acetate_export = _mission20_number_or_none(measured_production.get(MISSION20_ACETATE_EXPORT))

    issues = []
    if objective_error:
        issues.append(objective_error)
    if not method_correct:
        issues.append('Use pFBA for every Mission 20 matrix run.')
    if not objective_correct:
        issues.append('Use the biomass objective for every Mission 20 matrix run.')
    if knocked_out_genes:
        issues.append('Keep every gene active; Mission 20 varies only oxygen and acetate export.')
    if not environment.get('bounds_complete'):
        issues.append('The environmental-bound payload is incomplete.')
    if environment.get('unexpected_environment_changes'):
        issues.append('Keep glucose and every unrelated environmental bound at the model default.')
    if result_infeasible or objective_numeric is None:
        issues.append('Mission 20 requires a numeric viable biomass result in every matrix cell.')
    elif objective_numeric < MISSION20_MIN_BASELINE_GROWTH:
        issues.append('The current context does not retain enough predicted growth for comparison.')

    if medium_fluxes and medium_fluxes.get('error'):
        issues.append('The Exchange Flux Report is unavailable for this run.')
    elif missing_medium_fluxes:
        issues.append('The Exchange Flux Report is missing required Mission 20 reactions.')
    if production_fluxes and production_fluxes.get('error'):
        issues.append('The Production Flux report is unavailable for this run.')
    elif missing_measured_fluxes:
        issues.append('The Production Flux report is missing numeric Mission 20 values.')
    if missing_selected_fluxes:
        issues.append('Select the complete Mission 20 product/byproduct panel.')

    if glucose_uptake is None or oxygen_uptake is None:
        issues.append('Numeric glucose and oxygen uptake evidence is required.')
    else:
        if abs(float(glucose_uptake) - MISSION20_EXPECTED_GLUCOSE_UPTAKE) > MISSION20_GLUCOSE_UPTAKE_TOLERANCE:
            issues.append('Keep the model-default glucose uptake protocol in all four runs.')
        if environment.get('oxygen_lower_bound_closed'):
            if oxygen_uptake > MISSION20_FLUX_TOLERANCE:
                issues.append('The oxygen-closed context is still consuming oxygen.')
        elif oxygen_uptake < MISSION20_MIN_AEROBIC_OXYGEN_UPTAKE:
            issues.append('The oxygen-available context must show measured oxygen uptake.')

    for reaction_id in MISSION20_REQUIRED_TRACKED_FLUXES:
        if reaction_id not in raw_fluxes or reaction_id not in measured_production:
            continue
        expected_secretion = max(float(raw_fluxes[reaction_id]), 0.0)
        if abs(float(measured_production[reaction_id]) - expected_secretion) > MISSION20_FLUX_TOLERANCE:
            issues.append('Production Flux and Exchange Flux evidence do not describe the same visible solution.')
            break

    if diagnostics.get('method') != MISSION20_TARGET_METHOD:
        issues.append('The visible method diagnostics do not describe pFBA.')
    if diagnostics.get('objective_reaction') != selected_objective:
        issues.append('The visible method diagnostics do not match the biomass objective.')
    if primary_flux is None:
        issues.append('The primary biomass objective flux is missing from the visible result.')
    if biomass_raw is None:
        issues.append('The visible result does not contain a numeric biomass flux.')
    if method_score is None:
        issues.append('The pFBA secondary score is missing from the visible result.')
    if method_score_name != MISSION20_EXPECTED_SECONDARY_CRITERION:
        issues.append('The pFBA secondary criterion is not identified as total absolute flux.')
    if total_absolute_flux is None:
        issues.append('The total absolute flux is missing from the visible result.')
    if active_reaction_count is None:
        issues.append('The active-reaction count is missing from the visible result.')
    if (
        method_score is not None
        and total_absolute_flux is not None
        and abs(float(method_score) - float(total_absolute_flux)) > MISSION20_PARSIMONY_SIMILARITY_TOLERANCE
    ):
        issues.append('The pFBA score and total absolute flux are inconsistent.')
    for left, right, message in (
        (objective_numeric, primary_flux, 'The displayed objective value does not match the primary biomass flux.'),
        (objective_numeric, biomass_raw, 'The displayed objective value does not match the measured biomass flux.'),
        (primary_flux, biomass_raw, 'The primary objective flux does not match the measured biomass flux.'),
    ):
        if left is not None and right is not None and abs(float(left) - float(right)) > MISSION20_PRIMARY_TOLERANCE:
            issues.append(message)

    if environment.get('acetate_upper_bound_closed'):
        if acetate_export is None:
            issues.append('Numeric acetate export evidence is required for the closed-bound run.')
        elif acetate_export > MISSION20_MAX_CLOSED_EXPORT_FLUX:
            issues.append('The acetate upper-bound closure did not eliminate acetate export.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run = None
    if current_run_valid:
        current_run = {
            'run_type': run_type,
            'source': 'visible_simulation',
            'context': environment.get('context'),
            'oxygen_lower_bound_closed': bool(environment.get('oxygen_lower_bound_closed')),
            'acetate_upper_bound_closed': bool(environment.get('acetate_upper_bound_closed')),
            'method': method_name,
            'objective': selected_objective,
            'knocked_out_genes': [],
            'growth': _mission20_clean_number(biomass_raw),
            'glucose_uptake': _mission20_clean_number(glucose_uptake),
            'oxygen_uptake': _mission20_clean_number(oxygen_uptake),
            'tracked_flux_values': {
                reaction_id: _mission20_clean_number(measured_production[reaction_id])
                for reaction_id in MISSION20_REQUIRED_TRACKED_FLUXES
            },
            'medium_raw_fluxes': {
                reaction_id: _mission20_clean_number(raw_fluxes[reaction_id])
                for reaction_id in MISSION20_REQUIRED_MEDIUM_FLUXES
            },
            'selected_fluxes': list(MISSION20_REQUIRED_TRACKED_FLUXES),
            'method_diagnostics': {
                'method': MISSION20_TARGET_METHOD,
                'objective_reaction': selected_objective,
                'primary_objective_flux': _mission20_clean_number(primary_flux),
                'method_score': _mission20_clean_number(method_score),
                'method_score_name': method_score_name,
                'total_absolute_flux': _mission20_clean_number(total_absolute_flux),
                'active_reaction_count': int(active_reaction_count),
            },
        }
        slots[run_type] = current_run
        current_run_recorded = True

    aerobic_response = _mission20_pair_analysis(
        slots.get('oxygen_available_baseline'),
        slots.get('oxygen_available_acetate_closed'),
    )
    anaerobic_response = _mission20_pair_analysis(
        slots.get('oxygen_closed_baseline'),
        slots.get('oxygen_closed_acetate_closed'),
    )
    missing_run_types = [run_id for run_id, run in slots.items() if not isinstance(run, dict)]
    all_runs_recorded = not missing_run_types

    runs = [slots[key] for key in slots if isinstance(slots.get(key), dict)]
    same_controlled_setup = bool(
        all_runs_recorded
        and all(run.get('method') == MISSION20_TARGET_METHOD for run in runs)
        and all(run.get('objective') == MISSION20_GROWTH_OBJECTIVE for run in runs)
        and all(not run.get('knocked_out_genes') for run in runs)
        and all(
            set(run.get('selected_fluxes') or []) == set(MISSION20_REQUIRED_TRACKED_FLUXES)
            for run in runs
        )
        and all(
            abs(float(run.get('glucose_uptake', 0.0)) - MISSION20_EXPECTED_GLUCOSE_UPTAKE)
            <= MISSION20_GLUCOSE_UPTAKE_TOLERANCE
            for run in runs
        )
        and all(
            (run.get('method_diagnostics') or {}).get('method_score_name')
            == MISSION20_EXPECTED_SECONDARY_CRITERION
            for run in runs
        )
    )

    responsive_contexts = []
    nonresponsive_contexts = []
    if isinstance(aerobic_response, dict):
        if aerobic_response.get('classification') == 'binding_response':
            responsive_contexts.append('oxygen_available')
        elif aerobic_response.get('classification') == 'nonbinding_response':
            nonresponsive_contexts.append('oxygen_available')
    if isinstance(anaerobic_response, dict):
        if anaerobic_response.get('classification') == 'binding_response':
            responsive_contexts.append('oxygen_closed')
        elif anaerobic_response.get('classification') == 'nonbinding_response':
            nonresponsive_contexts.append('oxygen_closed')

    relationship_supported = bool(
        same_controlled_setup
        and responsive_contexts == [MISSION20_EXPECTED_RESPONSE_CONTEXT]
        and nonresponsive_contexts == ['oxygen_available']
        and isinstance(aerobic_response, dict)
        and isinstance(anaerobic_response, dict)
    )

    latest_attempt = {
        'method': method_name,
        'objective': selected_objective,
        'run_type': run_type,
        'context': environment.get('context'),
        'oxygen_lower_bound_closed': bool(environment.get('oxygen_lower_bound_closed')),
        'acetate_upper_bound_closed': bool(environment.get('acetate_upper_bound_closed')),
        'objective_result': str(objective_result),
        'issues': list(issues),
        'recorded': current_run_recorded,
    }
    report = {
        'mission_id': '20',
        'check_version': MISSION20_CHECK_VERSION,
        'mission_title': 'Context-Specific Export Robustness',
        'target_context': MISSION20_TARGET_CONTEXT,
        'target_method': MISSION20_TARGET_METHOD,
        'growth_objective': MISSION20_GROWTH_OBJECTIVE,
        'oxygen_reaction': MISSION20_OXYGEN_REACTION,
        'acetate_export': MISSION20_ACETATE_EXPORT,
        'required_tracked_fluxes': list(MISSION20_REQUIRED_TRACKED_FLUXES),
        'required_medium_fluxes': list(MISSION20_REQUIRED_MEDIUM_FLUXES),
        'aerobic_baseline_run': slots.get('oxygen_available_baseline'),
        'aerobic_acetate_closed_run': slots.get('oxygen_available_acetate_closed'),
        'anaerobic_baseline_run': slots.get('oxygen_closed_baseline'),
        'anaerobic_acetate_closed_run': slots.get('oxygen_closed_acetate_closed'),
        'recorded_run_count': len(runs),
        'required_run_count': 4,
        'missing_run_types': missing_run_types,
        'all_runs_recorded': all_runs_recorded,
        'same_controlled_setup': same_controlled_setup,
        'aerobic_response': aerobic_response,
        'anaerobic_response': anaerobic_response,
        'responsive_contexts': responsive_contexts,
        'nonresponsive_contexts': nonresponsive_contexts,
        'relationship_supported': relationship_supported,
        'evidence_ready': all_runs_recorded,
        'answer_ready': relationship_supported,
        'ready_to_deliver': relationship_supported,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': run_type,
        'current_issues': issues,
        'current_run': current_run,
        'latest_attempt': latest_attempt,
        'current_primary_objective_flux': _mission20_clean_number(primary_flux) if primary_flux is not None else None,
        'current_method_score': _mission20_clean_number(method_score) if method_score is not None else None,
        'current_total_absolute_flux': _mission20_clean_number(total_absolute_flux) if total_absolute_flux is not None else None,
        'current_active_reaction_count': active_reaction_count,
        'minimum_baseline_growth': MISSION20_MIN_BASELINE_GROWTH,
        'aerobic_baseline_like_ratio': MISSION20_AEROBIC_BASELINE_LIKE_RATIO,
        'anaerobic_min_viability_ratio': MISSION20_ANAEROBIC_MIN_VIABILITY_RATIO,
        'anaerobic_max_growth_ratio': MISSION20_ANAEROBIC_MAX_GROWTH_RATIO,
        'minimum_active_baseline_export': MISSION20_MIN_ACTIVE_BASELINE_EXPORT,
        'maximum_closed_export_flux': MISSION20_MAX_CLOSED_EXPORT_FLUX,
    }
    save_mission20_robustness_report_check(report)
    return report


def run_mission20_robustness_report_check(simulation_results=None):
    """Validate the already visible Mission 20 result without re-simulating."""
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible Mission 20 simulation before recording evidence.'
    except Exception:
        objective_error = 'Could not read the current visible Mission 20 simulation result.'

    return _build_mission20_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission20_robustness_report_check() or {},
        objective_error=objective_error,
    )


def run_mission20_robustness_report_check_remote(backend_url, simulation_results=None):
    """Browser parity wrapper: validate the already visible backend result."""
    del backend_url
    return run_mission20_robustness_report_check(simulation_results)


def build_mission20_context_report_text(report):
    if not report:
        return 'Mission 20 Context-Specific Export Robustness\n\nActivate the mission and record the four-run matrix.'
    if report.get('mission_id') != '20' or report.get('check_version') != MISSION20_CHECK_VERSION:
        return 'Mission 20 Context-Specific Export Robustness\n\nCurrent-format evidence has not been recorded yet.'

    lines = [
        'Mission 20 Context-Specific Export Robustness',
        '',
        'Controlled two-factor protocol:',
        '- pFBA biomass objective; all genes active; model-default glucose',
        '- Factor 1: oxygen uptake available or lower bound closed',
        '- Factor 2: acetate export upper bound open or closed',
        '- Every unrelated environmental bound remains at model default',
        '- Complete product/byproduct panel and pFBA diagnostics come from each visible solution',
        '',
    ]

    run_specs = [
        ('Oxygen available; acetate export open', 'aerobic_baseline_run'),
        ('Oxygen available; acetate export closed', 'aerobic_acetate_closed_run'),
        ('Oxygen uptake closed; acetate export open', 'anaerobic_baseline_run'),
        ('Oxygen uptake closed; acetate export closed', 'anaerobic_acetate_closed_run'),
    ]
    for title, key in run_specs:
        run = report.get(key) or {}
        if not run:
            lines.append(f'{title}: not recorded.')
            lines.append('')
            continue
        diagnostics = run.get('method_diagnostics') or {}
        lines.extend([
            f'{title}:',
            f"- Biomass flux: {float(run.get('growth', 0.0)):.3f}",
            f"- Glucose uptake: {float(run.get('glucose_uptake', 0.0)):.3f}",
            f"- Oxygen uptake: {float(run.get('oxygen_uptake', 0.0)):.3f}",
            f"- Total absolute flux: {float(diagnostics.get('total_absolute_flux', 0.0)):.3f}",
            f"- Active reactions: {int(diagnostics.get('active_reaction_count', 0))}",
            '- Export profile:',
        ])
        fluxes = run.get('tracked_flux_values') or {}
        for reaction_id in MISSION20_REQUIRED_TRACKED_FLUXES:
            lines.append(f"  {reaction_id}: {float(fluxes.get(reaction_id, 0.0)):.3f}")
        lines.append('')

    def add_pair(title, response):
        if not isinstance(response, dict):
            lines.append(f'{title}: incomplete.')
            return
        lines.extend([
            f'{title}:',
            f"- Growth after/before closure: {float(response.get('growth_ratio', 0.0)) * 100:.1f}%",
            f"- Acetate export before: {float(response.get('baseline_acetate_export', 0.0)):.3f}",
            f"- Acetate export after: {float(response.get('closed_acetate_export', 0.0)):.3f}",
            f"- Largest tracked-profile change: {float(response.get('maximum_profile_change', 0.0)):.3f}",
            f"- Total absolute flux change: {float(response.get('total_absolute_flux_change') or 0.0):+.3f}",
            f"- Active-reaction change: {int(response.get('active_reaction_change') or 0):+d}",
        ])

    add_pair('Oxygen-available pair comparison', report.get('aerobic_response'))
    lines.append('')
    add_pair('Oxygen-closed pair comparison', report.get('anaerobic_response'))

    if report.get('current_run_recorded'):
        lines.extend(['', f"Latest valid visible run recorded: {str(report.get('current_run_type', '')).replace('_', ' ')}."])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if report.get('recorded_run_count', 0):
            lines.append('Previously valid Mission 20 evidence remains available.')

    lines.append('')
    if report.get('evidence_ready') and report.get('relationship_supported'):
        lines.extend([
            'Evidence complete.',
            'Compare the two before/after pairs and identify the oxygen context with a changed predicted phenotype.',
            'Question: In which oxygen context did closing acetate export change the predicted phenotype?',
        ])
    elif report.get('evidence_ready'):
        lines.append('Evidence complete, but the four visible runs do not support one context-specific response.')
    else:
        missing = report.get('missing_run_types') or []
        lines.append('Evidence incomplete.')
        if missing:
            lines.append('Missing matrix runs: ' + ', '.join(item.replace('_', ' ') for item in missing) + '.')

    lines.extend([
        '',
        'Interpretation note: the same upper-bound closure can be non-binding in one environment and alter the optimum in another.',
        'The observed response is conditional on this model, glucose medium, biomass objective and oxygen context.',
        'All biomass, medium, export and pFBA diagnostic values come from the same visible solver results. No hidden simulation is used.',
    ])
    return '\n'.join(lines)

def is_mission04_unlocked(missions_completed):
    """Mission 04 follows the conditional-essentiality investigation."""
    return '03' in (missions_completed or [])


def _mission04_answer_alias_map():
    aliases = {}
    for gene_id, gene_name in MISSION04_GENE_NAMES.items():
        variants = {
            gene_id,
            gene_name,
            f'{gene_id} {gene_name}',
            f'{gene_id} ({gene_name})',
            f'{gene_id}/{gene_name}',
        }
        for variant in variants:
            key = ''.join(char.lower() for char in str(variant) if char.isalnum())
            if key:
                aliases[key] = gene_id
    return aliases


def normalise_mission04_answer(answer):
    key = ''.join(char.lower() for char in str(answer or '') if char.isalnum())
    return _mission04_answer_alias_map().get(key)


def mission04_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission04_production_check() or {}
    if (
        report_data.get('mission_id') != '04'
        or report_data.get('check_version') != 2
        or not report_data.get('evidence_ready')
    ):
        return False
    return normalise_mission04_answer(answer) == report_data.get('winning_gene')


def _mission04_target_flux(production_fluxes):
    """Return a measured, non-negative ethanol secretion flux or ``None``."""
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return None
    for item in production_fluxes.get('items') or []:
        if item.get('reaction_id') != MISSION04_PRODUCTION_OBJECTIVE:
            continue
        if item.get('error') or 'production_flux' not in item:
            return None
        return _as_float_or_none(item.get('production_flux'))
    return None


def _mission04_oxygen_uptake(medium_fluxes):
    _raw_fluxes, uptake_fluxes, _secretion_fluxes = _medium_flux_maps(medium_fluxes)
    if MISSION04_OXYGEN_REACTION not in uptake_fluxes:
        return None
    return _as_float_or_none(uptake_fluxes.get(MISSION04_OXYGEN_REACTION))


def _mission04_assessment(growth_ratio, production_change):
    if growth_ratio is None or production_change is None:
        return 'baseline missing'
    if growth_ratio < MISSION04_MIN_VIABLE_GROWTH_RATIO:
        return 'growth below the operational viability threshold'
    if production_change >= MISSION04_MIN_PRODUCTION_INCREASE:
        return 'growth-coupled ethanol secretion'
    if growth_ratio < 0.99:
        return 'growth reduction without ethanol redirection'
    return 'no apparent production effect'


def _mission04_normalise_trials(trials, baseline_growth, baseline_production):
    normalized = copy.deepcopy(trials or {})
    baseline_growth_value = _as_float_or_none(baseline_growth)
    baseline_production_value = _as_float_or_none(baseline_production)

    for gene_id, trial in normalized.items():
        growth = _numeric_result(trial.get('growth'))
        production = _numeric_result(trial.get('production'))
        growth_ratio = None
        production_change = None
        if baseline_growth_value is not None and baseline_growth_value > 0:
            growth_ratio = growth / baseline_growth_value
        if baseline_production_value is not None:
            production_change = production - baseline_production_value

        viable = (
            growth_ratio is not None
            and growth_ratio >= MISSION04_MIN_VIABLE_GROWTH_RATIO
        )
        production_improved = (
            production_change is not None
            and production_change >= MISSION04_MIN_PRODUCTION_INCREASE
        )

        trial['growth'] = round(growth, 6)
        trial['production'] = round(production, 6)
        trial['growth_ratio'] = round(growth_ratio, 6) if growth_ratio is not None else None
        trial['growth_percent'] = round(growth_ratio * 100.0, 1) if growth_ratio is not None else None
        trial['production_change'] = round(production_change, 6) if production_change is not None else None
        trial['viable'] = viable
        trial['production_improved'] = production_improved
        trial['eligible_design'] = viable and production_improved
        trial['assessment'] = _mission04_assessment(growth_ratio, production_change)
    return normalized


def _mission04_rank_trials(trials):
    eligible = [
        (gene_id, trial)
        for gene_id, trial in (trials or {}).items()
        if gene_id in MISSION04_CANDIDATE_GENES and trial.get('eligible_design')
    ]
    eligible.sort(
        key=lambda item: (
            float(item[1].get('production', 0.0)),
            float(item[1].get('growth_ratio', 0.0)),
        ),
        reverse=True,
    )
    if not eligible:
        return None, False, [], []

    best_production = float(eligible[0][1].get('production', 0.0))
    tied = [
        gene_id for gene_id, trial in eligible
        if abs(float(trial.get('production', 0.0)) - best_production) <= MISSION04_RANK_TOLERANCE
    ]
    unique = len(tied) == 1
    winner = tied[0] if unique else None
    ranked = [
        (gene_id, float(trial.get('production', 0.0)))
        for gene_id, trial in eligible
    ]
    return winner, unique, tied, ranked


def _build_mission04_trial_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
):
    """Validate and accumulate one controlled Mission 04 production run."""
    if not isinstance(existing_report, dict):
        existing_report = {}
    elif existing_report and (
        existing_report.get('mission_id') != '04'
        or existing_report.get('check_version') != 2
    ):
        # Discard legacy Mission 04 artifacts.  The previous format stored only
        # one hidden re-simulation and cannot be mixed with the controlled
        # baseline/candidate evidence introduced by check version 2.
        existing_report = {}
    existing_report = existing_report or {}

    baseline_growth = _as_float_or_none(existing_report.get('baseline_growth'))
    baseline_production = _as_float_or_none(existing_report.get('baseline_production'))
    baseline_oxygen_uptake = _as_float_or_none(existing_report.get('baseline_oxygen_uptake'))
    trials = copy.deepcopy(existing_report.get('trials') or {})

    knocked_out = _knocked_out_genes(genes)
    environment_changed = _environment_has_changes(reactions)
    selected_fluxes = _read_selected_production_fluxes()
    tracking_ready = MISSION04_PRODUCTION_OBJECTIVE in selected_fluxes
    method_correct = method_name == MISSION04_METHOD
    objective_correct = selected_objective == MISSION04_GROWTH_OBJECTIVE

    objective_value = _as_float_or_none(objective_result)
    result_available = objective_value is not None
    growth_value = _numeric_result(objective_value)
    production_value = _mission04_target_flux(production_fluxes)
    production_available = production_value is not None
    oxygen_uptake = _mission04_oxygen_uptake(medium_fluxes)
    oxygen_evidence_available = oxygen_uptake is not None

    is_baseline = len(knocked_out) == 0
    exactly_one_knockout = len(knocked_out) == 1
    selected_gene = knocked_out[0] if exactly_one_knockout else None
    candidate_selected = selected_gene in MISSION04_CANDIDATE_GENES if selected_gene else False

    issues = []
    if objective_error:
        issues.append(objective_error)
    if not method_correct:
        issues.append('Use FBA for the reference and every candidate knockout trial.')
    if not objective_correct:
        issues.append('Use the biomass objective so ethanol is measured in a growth-optimal solution.')
    if environment_changed:
        issues.append('Restore the unchanged default aerobic environment before evaluating production knockouts.')
    if not tracking_ready:
        issues.append(f'Track {MISSION04_PRODUCTION_OBJECTIVE} in Production Flux for every Mission 04 run.')
    if not result_available:
        issues.append('The simulation did not provide a numeric biomass-growth result.')
    if not production_available:
        issues.append(f'The simulation did not provide a numeric {MISSION04_PRODUCTION_OBJECTIVE} secretion flux.')
    if not oxygen_evidence_available:
        issues.append(f'The Exchange Flux Report did not provide {MISSION04_OXYGEN_REACTION} uptake evidence.')

    if is_baseline and result_available and growth_value < MISSION04_MIN_BASELINE_GROWTH:
        issues.append('The no-knockout reference must show viable predicted growth.')
    if is_baseline and production_available and production_value > MISSION04_MAX_BASELINE_PRODUCTION:
        issues.append('The reference should show negligible ethanol secretion in the unchanged default setup.')
    if is_baseline and oxygen_evidence_available and oxygen_uptake <= MISSION04_FLUX_TOLERANCE:
        issues.append('The aerobic reference should show oxygen uptake before genetic respiratory capacity is perturbed.')
    if not is_baseline and not exactly_one_knockout:
        issues.append('Isolate one genetic perturbation: use exactly one gene knockout in each candidate trial.')
    if exactly_one_knockout and not candidate_selected:
        issues.append('The knocked-out gene is not one of the Mission 04 candidates.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run_type = 'invalid'

    if current_run_valid and is_baseline:
        baseline_growth = growth_value
        baseline_production = production_value
        baseline_oxygen_uptake = oxygen_uptake
        current_run_recorded = True
        current_run_type = 'baseline'
    elif current_run_valid and selected_gene:
        trials[selected_gene] = {
            'gene_id': selected_gene,
            'gene_name': MISSION04_GENE_NAMES.get(selected_gene, GENE_NAMES.get(selected_gene, '')),
            'growth': round(growth_value, 6),
            'production': round(production_value, 6),
            'oxygen_uptake': round(float(oxygen_uptake), 6),
        }
        current_run_recorded = True
        current_run_type = 'candidate'

    trials = _mission04_normalise_trials(trials, baseline_growth, baseline_production)
    missing_candidates = [gene_id for gene_id in MISSION04_CANDIDATE_GENES if gene_id not in trials]
    comparison_complete = (
        baseline_growth is not None
        and baseline_production is not None
        and baseline_oxygen_uptake is not None
        and not missing_candidates
    )
    winning_gene, winner_unique, eligible_candidates, ranked_candidates = _mission04_rank_trials(trials)
    expected_winner_confirmed = winning_gene == MISSION04_EXPECTED_WINNER
    # Delivery is derived from the recorded evidence, not from a standalone
    # hard-coded answer.  The expected-winner flag remains available as a
    # regression diagnostic for the model/test suite.
    evidence_ready = comparison_complete and winner_unique

    data = {
        'mission_id': '04',
        'check_version': 2,
        'mission_title': 'Growth-Coupled Ethanol Production',
        'method': method_name,
        'required_method': MISSION04_METHOD,
        'selected_objective': selected_objective,
        'growth_objective': MISSION04_GROWTH_OBJECTIVE,
        'product_name': MISSION04_PRODUCT_NAME,
        'production_objective': MISSION04_PRODUCTION_OBJECTIVE,
        'oxygen_reaction': MISSION04_OXYGEN_REACTION,
        'baseline_growth': round(baseline_growth, 6) if baseline_growth is not None else None,
        'baseline_production': round(baseline_production, 6) if baseline_production is not None else None,
        'baseline_oxygen_uptake': round(baseline_oxygen_uptake, 6) if baseline_oxygen_uptake is not None else None,
        'baseline_recorded': (
            baseline_growth is not None
            and baseline_production is not None
            and baseline_oxygen_uptake is not None
        ),
        'candidate_genes': list(MISSION04_CANDIDATE_GENES),
        'candidate_gene_names': dict(MISSION04_GENE_NAMES),
        'trials': trials,
        'valid_trial_count': len(trials),
        'required_trial_count': len(MISSION04_CANDIDATE_GENES),
        'missing_candidates': missing_candidates,
        'comparison_complete': comparison_complete,
        'minimum_viable_growth_ratio': MISSION04_MIN_VIABLE_GROWTH_RATIO,
        'minimum_production_increase': MISSION04_MIN_PRODUCTION_INCREASE,
        'eligible_candidates': eligible_candidates,
        'ranked_candidates': ranked_candidates,
        'winning_gene': winning_gene,
        'winner_unique': winner_unique,
        'expected_winner': MISSION04_EXPECTED_WINNER,
        'expected_winner_confirmed': expected_winner_confirmed,
        'evidence_ready': evidence_ready,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': current_run_type,
        'current_knocked_out_genes': knocked_out,
        'current_selected_gene': selected_gene,
        'current_growth': round(growth_value, 6) if result_available else None,
        'current_production': round(production_value, 6) if production_available else None,
        'current_oxygen_uptake': round(float(oxygen_uptake), 6) if oxygen_evidence_available else None,
        'current_issues': issues,
        'selected_production_fluxes': selected_fluxes,
    }
    save_mission04_production_check(data)
    return data


def run_mission04_production_trial_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run the simulation before recording Mission 04 evidence.'
    except Exception:
        objective_error = 'Could not read the current simulation result.'

    return _build_mission04_trial_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission04_production_check(),
        objective_error=objective_error,
    )


def build_mission04_evidence_report_text(report_data=None):
    if report_data is None:
        report_data = load_mission04_production_check() or {}

    lines = ['Mission 04 Growth-Coupled Ethanol Evidence', '']
    baseline_growth = report_data.get('baseline_growth')
    baseline_production = report_data.get('baseline_production')
    baseline_oxygen = report_data.get('baseline_oxygen_uptake')
    trials = report_data.get('trials') or {}
    count = report_data.get('valid_trial_count', len(trials))
    required = report_data.get('required_trial_count', len(MISSION04_CANDIDATE_GENES))

    if baseline_growth is None and not trials:
        lines.extend([
            'Build a controlled production-knockout comparison.',
            'Establish a viable no-knockout reference and determine whether any candidate redirects growth-optimal flux toward ethanol.',
            '',
            f'Candidate knockout trials recorded: 0/{required}',
        ])
    else:
        lines.extend([
            'Controlled setup confirmed for recorded evidence: baseline with all genes active; exactly one candidate knockout per candidate trial; unchanged default aerobic environment; FBA biomass objective; ethanol exchange tracked.',
            '',
            (
                f'Baseline: growth {float(baseline_growth):.3f}; ethanol {float(baseline_production):.3f}; '
                f'oxygen uptake {_clean_display_number(baseline_oxygen):.3f}'
                if baseline_growth is not None and baseline_production is not None and baseline_oxygen is not None
                else 'Baseline: not fully recorded yet'
            ),
            f'Candidate knockout trials recorded: {count}/{required}',
            '',
            'Candidate screen:',
        ])
        for gene_id in MISSION04_CANDIDATE_GENES:
            gene_name = MISSION04_GENE_NAMES.get(gene_id, '')
            trial = trials.get(gene_id)
            if not trial:
                lines.append(f'- {gene_id} ({gene_name}): pending')
                continue
            percent = trial.get('growth_percent')
            percent_text = f'{float(percent):.1f}% of baseline' if percent is not None else 'baseline missing'
            change = trial.get('production_change')
            change_text = f'{float(change):+.3f}' if change is not None else 'baseline missing'
            lines.append(
                f"- {gene_id} ({gene_name}): growth {float(trial.get('growth', 0.0)):.3f} "
                f"({percent_text}); ethanol {float(trial.get('production', 0.0)):.3f} "
                f"(change {change_text}); oxygen uptake {_clean_display_number(trial.get('oxygen_uptake', 0.0)):.3f}; "
                f"{trial.get('assessment', '')}"
            )

    if report_data.get('current_run_recorded'):
        lines.append('')
        if report_data.get('current_run_type') == 'baseline':
            lines.append('Latest valid run recorded: aerobic no-knockout reference.')
        else:
            gene_id = report_data.get('current_selected_gene')
            gene_name = MISSION04_GENE_NAMES.get(gene_id, '')
            lines.append(
                f"Latest valid trial recorded: {gene_id} ({gene_name}); "
                f"growth {float(report_data.get('current_growth', 0.0)):.3f}; "
                f"ethanol {float(report_data.get('current_production', 0.0)):.3f}."
            )
    elif report_data.get('current_issues'):
        lines.append('')
        lines.append('Latest run was not recorded:')
        lines.extend(f'- {issue}' for issue in report_data.get('current_issues') or [])

    lines.append('')
    if report_data.get('evidence_ready'):
        lines.append(
            'Evidence complete. Identify the viable candidate that caused a meaningful increase in ethanol secretion and submit it to Dr. Silva.'
        )
    else:
        missing = report_data.get('missing_candidates') or []
        if baseline_growth is None:
            lines.append('Evidence incomplete: a viable no-knockout reference is still required.')
        if missing:
            lines.append('Missing candidate trials: ' + ', '.join(missing))
        elif report_data.get('comparison_complete') and not report_data.get('winner_unique'):
            eligible = report_data.get('eligible_candidates') or []
            if eligible:
                lines.append('Comparison complete, but the mission criteria do not identify one unique production design.')
            else:
                lines.append('Comparison complete, but no candidate satisfies both the viability and ethanol-improvement criteria.')

    lines.extend([
        '',
        'Interpretation note: this mission measures ethanol secretion in a biomass-optimal FBA solution; it does not maximise the theoretical ethanol yield directly.',
        f'A candidate is operationally viable here when predicted growth remains at or above {MISSION04_MIN_VIABLE_GROWTH_RATIO * 100:.0f}% of the reference, and production improvement must be at least {MISSION04_MIN_PRODUCTION_INCREASE:.1f}. These are mission criteria, not universal biological definitions.',
        'A growth reduction alone is not evidence of useful flux redirection. The unchanged medium may still contain oxygen even when a knockout removes respiratory capacity and the model no longer consumes it.',
    ])
    return '\n'.join(lines)


# Backwards-compatible entry point retained for older callers.  Mission 04 now
# validates the actual run selected by the player instead of launching a hidden
# internal simulation with different settings.
def run_mission04_production_check(simulation_results=None):
    return run_mission04_production_trial_check(simulation_results)


def is_mission05_unlocked(missions_completed):
    """Mission 05 follows the aerobic production-knockout investigation."""
    return '04' in (missions_completed or [])


def _mission05_answer_alias_map():
    aliases = {}
    for gene_id, gene_name in MISSION05_GENE_NAMES.items():
        variants = {
            gene_id,
            gene_name,
            f'{gene_id} {gene_name}',
            f'{gene_id} ({gene_name})',
            f'{gene_id}/{gene_name}',
        }
        for variant in variants:
            key = ''.join(char.lower() for char in str(variant) if char.isalnum())
            if key:
                aliases[key] = gene_id
    return aliases


def normalise_mission05_answer(answer):
    key = ''.join(char.lower() for char in str(answer or '') if char.isalnum())
    return _mission05_answer_alias_map().get(key)


def mission05_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission05_production_check() or {}
    if (
        report_data.get('mission_id') != '05'
        or report_data.get('check_version') != 2
        or not report_data.get('evidence_ready')
    ):
        return False
    return normalise_mission05_answer(answer) == report_data.get('winning_gene')


def _mission05_environment_status(reactions):
    """Return whether only the oxygen lower bound was closed.

    Bound identifiers are interpreted independently of dictionary order while
    preserving compatibility with legacy positional pygame-menu saves.
    """
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION05_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lower_bound_open, upper_bound_open = _reaction_bound_open_states(reactions, i)
        reaction_id = REACTIONS.index[i]
        if lower_bound_open is None or upper_bound_open is None:
            unexpected_changes.append(f'{reaction_id} bounds unavailable')
            continue

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        if i == oxygen_index:
            oxygen_lower_bound_closed = not lower_bound_open
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if lower_bound_open != default_lower_bound_open:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_bound_open != default_upper_bound_open:
            unexpected_changes.append(f'{reaction_id} upper bound')

    return oxygen_lower_bound_closed, unexpected_changes


def _mission05_target_flux(production_fluxes):
    """Return a measured, non-negative ethanol secretion flux or ``None``."""
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return None
    for item in production_fluxes.get('items') or []:
        if item.get('reaction_id') != MISSION05_PRODUCTION_OBJECTIVE:
            continue
        if item.get('error') or 'production_flux' not in item:
            return None
        return _as_float_or_none(item.get('production_flux'))
    return None


def _mission05_oxygen_uptake(medium_fluxes):
    _raw_fluxes, uptake_fluxes, _secretion_fluxes = _medium_flux_maps(medium_fluxes)
    if MISSION05_OXYGEN_REACTION not in uptake_fluxes:
        return None
    return _as_float_or_none(uptake_fluxes.get(MISSION05_OXYGEN_REACTION))


def _mission05_assessment(growth_ratio, production_change):
    if growth_ratio is None or production_change is None:
        return 'anaerobic reference missing'
    if growth_ratio < MISSION05_MIN_VIABLE_GROWTH_RATIO:
        return 'growth below the operational retention threshold'
    if production_change >= MISSION05_MIN_PRODUCTION_INCREASE:
        return 'context-dependent anaerobic ethanol improvement'
    if abs(production_change) <= MISSION05_FLUX_TOLERANCE and growth_ratio >= 0.99:
        return 'no additional effect in this anaerobic context'
    if growth_ratio < 0.99:
        return 'growth change without meaningful additional ethanol'
    return 'ethanol change below the mission threshold'


def _mission05_normalise_trials(trials, baseline_growth, baseline_production):
    normalized = copy.deepcopy(trials or {})
    baseline_growth_value = _as_float_or_none(baseline_growth)
    baseline_production_value = _as_float_or_none(baseline_production)

    for gene_id, trial in normalized.items():
        growth = _numeric_result(trial.get('growth'))
        production = _numeric_result(trial.get('production'))
        growth_ratio = None
        production_change = None
        if baseline_growth_value is not None and baseline_growth_value > 0:
            growth_ratio = growth / baseline_growth_value
        if baseline_production_value is not None:
            production_change = production - baseline_production_value

        viable = (
            growth_ratio is not None
            and growth_ratio >= MISSION05_MIN_VIABLE_GROWTH_RATIO
        )
        production_improved = (
            production_change is not None
            and production_change >= MISSION05_MIN_PRODUCTION_INCREASE
        )

        trial['growth'] = round(growth, 6)
        trial['production'] = round(production, 6)
        trial['growth_ratio'] = round(growth_ratio, 6) if growth_ratio is not None else None
        trial['growth_percent'] = round(growth_ratio * 100.0, 1) if growth_ratio is not None else None
        trial['production_change'] = round(production_change, 6) if production_change is not None else None
        trial['viable'] = viable
        trial['production_improved'] = production_improved
        trial['eligible_design'] = viable and production_improved
        trial['assessment'] = _mission05_assessment(growth_ratio, production_change)
    return normalized


def _mission05_rank_trials(trials):
    eligible = [
        (gene_id, trial)
        for gene_id, trial in (trials or {}).items()
        if gene_id in MISSION05_CANDIDATE_GENES and trial.get('eligible_design')
    ]
    eligible.sort(
        key=lambda item: (
            float(item[1].get('production', 0.0)),
            float(item[1].get('growth_ratio', 0.0)),
        ),
        reverse=True,
    )
    if not eligible:
        return None, False, [], []

    best_production = float(eligible[0][1].get('production', 0.0))
    tied = [
        gene_id for gene_id, trial in eligible
        if abs(float(trial.get('production', 0.0)) - best_production) <= MISSION05_RANK_TOLERANCE
    ]
    unique = len(tied) == 1
    winner = tied[0] if unique else None
    ranked = [
        (gene_id, float(trial.get('production', 0.0)))
        for gene_id, trial in eligible
    ]
    return winner, unique, tied, ranked


def _build_mission05_trial_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
):
    """Validate and accumulate one controlled Mission 05 anaerobic run."""
    if not isinstance(existing_report, dict):
        existing_report = {}
    elif existing_report and (
        existing_report.get('mission_id') != '05'
        or existing_report.get('check_version') != 2
    ):
        # Discard the legacy lactate/single-result format.  It was based on
        # hidden re-simulations and an invalid b1241 reaction-level knockout.
        existing_report = {}
    existing_report = existing_report or {}

    baseline_growth = _as_float_or_none(existing_report.get('baseline_growth'))
    baseline_production = _as_float_or_none(existing_report.get('baseline_production'))
    baseline_oxygen_uptake = _as_float_or_none(existing_report.get('baseline_oxygen_uptake'))
    trials = copy.deepcopy(existing_report.get('trials') or {})

    knocked_out = _knocked_out_genes(genes)
    oxygen_closed, unexpected_environment_changes = _mission05_environment_status(reactions)
    selected_fluxes = _read_selected_production_fluxes()
    tracking_ready = MISSION05_PRODUCTION_OBJECTIVE in selected_fluxes
    method_correct = method_name == MISSION05_METHOD
    objective_correct = selected_objective == MISSION05_GROWTH_OBJECTIVE

    objective_value = _as_float_or_none(objective_result)
    result_available = objective_value is not None
    growth_value = _numeric_result(objective_value)
    production_value = _mission05_target_flux(production_fluxes)
    production_available = production_value is not None
    oxygen_uptake = _mission05_oxygen_uptake(medium_fluxes)
    oxygen_evidence_available = oxygen_uptake is not None

    is_baseline = len(knocked_out) == 0
    exactly_one_knockout = len(knocked_out) == 1
    selected_gene = knocked_out[0] if exactly_one_knockout else None
    candidate_selected = selected_gene in MISSION05_CANDIDATE_GENES if selected_gene else False

    issues = []
    if objective_error:
        issues.append(objective_error)
    if not method_correct:
        issues.append('Use FBA for the anaerobic reference and every candidate knockout trial.')
    if not objective_correct:
        issues.append('Use the biomass objective so ethanol is measured in a growth-optimal anaerobic solution.')
    if not oxygen_closed:
        issues.append('Create an anaerobic environment before recording Mission 05 evidence.')
    if unexpected_environment_changes:
        issues.append(
            'Restore the medium so the oxygen lower bound is the only environmental change: '
            + ', '.join(unexpected_environment_changes)
            + '.'
        )
    if not tracking_ready:
        issues.append(f'Track {MISSION05_PRODUCTION_OBJECTIVE} in Production Flux for every Mission 05 run.')
    if not result_available:
        issues.append('The simulation did not provide a numeric biomass-growth result.')
    if not production_available:
        issues.append(f'The simulation did not provide a numeric {MISSION05_PRODUCTION_OBJECTIVE} secretion flux.')
    if not oxygen_evidence_available:
        issues.append(f'The Exchange Flux Report did not provide {MISSION05_OXYGEN_REACTION} uptake evidence.')
    elif oxygen_uptake > MISSION05_FLUX_TOLERANCE:
        issues.append('Anaerobic Mission 05 runs must show zero oxygen uptake.')

    if is_baseline and result_available and growth_value < MISSION05_MIN_BASELINE_GROWTH:
        issues.append('The no-knockout anaerobic reference must show viable predicted growth.')
    if is_baseline and production_available and production_value < MISSION05_MIN_BASELINE_PRODUCTION:
        issues.append('The anaerobic reference should show the expected baseline ethanol secretion before knockouts are compared.')
    if not is_baseline and not exactly_one_knockout:
        issues.append('Isolate one genetic perturbation: use exactly one gene knockout in each candidate trial.')
    if exactly_one_knockout and not candidate_selected:
        issues.append('The knocked-out gene is not one of the Mission 05 candidates.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run_type = 'invalid'

    if current_run_valid and is_baseline:
        baseline_growth = growth_value
        baseline_production = production_value
        baseline_oxygen_uptake = oxygen_uptake
        current_run_recorded = True
        current_run_type = 'baseline'
    elif current_run_valid and selected_gene:
        trials[selected_gene] = {
            'gene_id': selected_gene,
            'gene_name': MISSION05_GENE_NAMES.get(selected_gene, GENE_NAMES.get(selected_gene, '')),
            'growth': round(growth_value, 6),
            'production': round(production_value, 6),
            'oxygen_uptake': round(float(oxygen_uptake), 6),
        }
        current_run_recorded = True
        current_run_type = 'candidate'

    trials = _mission05_normalise_trials(trials, baseline_growth, baseline_production)
    missing_candidates = [gene_id for gene_id in MISSION05_CANDIDATE_GENES if gene_id not in trials]
    comparison_complete = (
        baseline_growth is not None
        and baseline_production is not None
        and baseline_oxygen_uptake is not None
        and not missing_candidates
    )
    winning_gene, winner_unique, eligible_candidates, ranked_candidates = _mission05_rank_trials(trials)
    expected_winner_confirmed = winning_gene == MISSION05_EXPECTED_WINNER
    evidence_ready = comparison_complete and winner_unique

    data = {
        'mission_id': '05',
        'check_version': 2,
        'mission_title': 'Context-Dependent Anaerobic Ethanol Design',
        'method': method_name,
        'required_method': MISSION05_METHOD,
        'selected_objective': selected_objective,
        'growth_objective': MISSION05_GROWTH_OBJECTIVE,
        'product_name': MISSION05_PRODUCT_NAME,
        'production_objective': MISSION05_PRODUCTION_OBJECTIVE,
        'target_flux': MISSION05_TARGET_FLUX,
        'oxygen_reaction': MISSION05_OXYGEN_REACTION,
        'oxygen_lower_bound_closed': oxygen_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'baseline_growth': round(baseline_growth, 6) if baseline_growth is not None else None,
        'baseline_production': round(baseline_production, 6) if baseline_production is not None else None,
        'baseline_oxygen_uptake': round(baseline_oxygen_uptake, 6) if baseline_oxygen_uptake is not None else None,
        'baseline_recorded': (
            baseline_growth is not None
            and baseline_production is not None
            and baseline_oxygen_uptake is not None
        ),
        'candidate_genes': list(MISSION05_CANDIDATE_GENES),
        'candidate_gene_names': dict(MISSION05_GENE_NAMES),
        'trials': trials,
        'valid_trial_count': len(trials),
        'required_trial_count': len(MISSION05_CANDIDATE_GENES),
        'missing_candidates': missing_candidates,
        'comparison_complete': comparison_complete,
        'minimum_viable_growth_ratio': MISSION05_MIN_VIABLE_GROWTH_RATIO,
        'minimum_production_increase': MISSION05_MIN_PRODUCTION_INCREASE,
        'eligible_candidates': eligible_candidates,
        'ranked_candidates': ranked_candidates,
        'winning_gene': winning_gene,
        'winner_unique': winner_unique,
        'expected_winner': MISSION05_EXPECTED_WINNER,
        'expected_winner_confirmed': expected_winner_confirmed,
        'evidence_ready': evidence_ready,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': current_run_type,
        'current_knocked_out_genes': knocked_out,
        'current_selected_gene': selected_gene,
        'current_growth': round(growth_value, 6) if result_available else None,
        'current_production': round(production_value, 6) if production_available else None,
        'current_oxygen_uptake': round(float(oxygen_uptake), 6) if oxygen_evidence_available else None,
        'current_issues': issues,
        'selected_production_fluxes': selected_fluxes,
    }
    save_mission05_production_check(data)
    return data


def run_mission05_production_trial_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run the simulation before recording Mission 05 evidence.'
    except Exception:
        objective_error = 'Could not read the current simulation result.'

    return _build_mission05_trial_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission05_production_check(),
        objective_error=objective_error,
    )


def build_mission05_evidence_report_text(report_data=None):
    if report_data is None:
        report_data = load_mission05_production_check() or {}

    lines = ['Mission 05 Context-Dependent Anaerobic Ethanol Evidence', '']
    baseline_growth = report_data.get('baseline_growth')
    baseline_production = report_data.get('baseline_production')
    baseline_oxygen = report_data.get('baseline_oxygen_uptake')
    trials = report_data.get('trials') or {}
    count = report_data.get('valid_trial_count', len(trials))
    required = report_data.get('required_trial_count', len(MISSION05_CANDIDATE_GENES))

    if baseline_growth is None and not trials:
        lines.extend([
            'Investigate whether a production strategy remains useful after the environmental context changes.',
            'Establish an anaerobic no-knockout reference and compare the highlighted candidates under equivalent conditions.',
            '',
            f'Candidate knockout trials recorded: 0/{required}',
        ])
    else:
        lines.extend([
            'Controlled setup confirmed for recorded evidence: anaerobic reference with all genes active; exactly one candidate knockout per candidate trial; oxygen lower bound as the only environmental change; FBA biomass objective; ethanol exchange tracked.',
            '',
            (
                f'Baseline: growth {float(baseline_growth):.3f}; ethanol {float(baseline_production):.3f}; '
                f'oxygen uptake {_clean_display_number(baseline_oxygen):.3f}'
                if baseline_growth is not None and baseline_production is not None and baseline_oxygen is not None
                else 'Baseline: not fully recorded yet'
            ),
            f'Candidate knockout trials recorded: {count}/{required}',
            '',
            'Candidate screen:',
        ])
        for gene_id in MISSION05_CANDIDATE_GENES:
            gene_name = MISSION05_GENE_NAMES.get(gene_id, '')
            trial = trials.get(gene_id)
            if not trial:
                lines.append(f'- {gene_id} ({gene_name}): pending')
                continue
            percent = trial.get('growth_percent')
            percent_text = f'{float(percent):.1f}% of baseline' if percent is not None else 'baseline missing'
            change = trial.get('production_change')
            change_text = f'{float(change):+.3f}' if change is not None else 'baseline missing'
            lines.append(
                f"- {gene_id} ({gene_name}): growth {float(trial.get('growth', 0.0)):.3f} "
                f"({percent_text}); ethanol {float(trial.get('production', 0.0)):.3f} "
                f"(change {change_text}); oxygen uptake {_clean_display_number(trial.get('oxygen_uptake', 0.0)):.3f}; "
                f"{trial.get('assessment', '')}"
            )

    if report_data.get('current_run_recorded'):
        lines.append('')
        if report_data.get('current_run_type') == 'baseline':
            lines.append('Latest valid run recorded: anaerobic no-knockout reference.')
        else:
            gene_id = report_data.get('current_selected_gene')
            gene_name = MISSION05_GENE_NAMES.get(gene_id, '')
            lines.append(
                f"Latest valid trial recorded: {gene_id} ({gene_name}); "
                f"growth {float(report_data.get('current_growth', 0.0)):.3f}; "
                f"ethanol {float(report_data.get('current_production', 0.0)):.3f}."
            )
    elif report_data.get('current_issues'):
        lines.append('')
        lines.append('Latest run was not recorded:')
        lines.extend(f'- {issue}' for issue in report_data.get('current_issues') or [])

    lines.append('')
    if report_data.get('evidence_ready'):
        lines.append(
            'Evidence complete. Identify the viable candidate that provides the strongest additional ethanol secretion in this anaerobic context and submit it to Dr. Silva.'
        )
    else:
        missing = report_data.get('missing_candidates') or []
        if baseline_growth is None:
            lines.append('Evidence incomplete: a viable anaerobic no-knockout reference is still required.')
        if missing:
            lines.append('Missing candidate trials: ' + ', '.join(missing))
        elif report_data.get('comparison_complete') and not report_data.get('winner_unique'):
            eligible = report_data.get('eligible_candidates') or []
            if eligible:
                lines.append('Comparison complete, but the mission criteria do not identify one unique anaerobic design.')
            else:
                lines.append('Comparison complete, but no candidate satisfies both the growth-retention and ethanol-improvement criteria.')

    lines.extend([
        '',
        'Interpretation note: a knockout strategy is conditional on the model, objective and environment. The candidate that was useful in the aerobic Mission 04 may become neutral when oxygen uptake is already unavailable.',
        'This mission measures ethanol secretion in a biomass-optimal anaerobic FBA solution; it does not maximise theoretical ethanol yield directly.',
        f'A candidate retains sufficient growth here when predicted growth remains at or above {MISSION05_MIN_VIABLE_GROWTH_RATIO * 100:.0f}% of the anaerobic reference, and additional ethanol must be at least {MISSION05_MIN_PRODUCTION_INCREASE:.1f}. These are operational mission criteria, not universal biological definitions.',
    ])
    return '\n'.join(lines)


# Compatibility entry point: Mission 05 now validates the player's visible run
# and never launches hidden baseline/current simulations with different settings.
def run_mission05_production_check(simulation_results=None):
    return run_mission05_production_trial_check(simulation_results)


def _result_value_from_simulation_results(simulation_results):
    try:
        return simulation_results[1]
    except Exception:
        return None


def _bound_state_for_reaction(reactions, reaction_id):
    """Return lower/upper bound UI booleans for one exchange reaction."""
    try:
        reaction_index = list(REACTIONS.index).index(reaction_id)
    except ValueError:
        return None, None
    return _reaction_bound_open_states(reactions, reaction_index)


def _mission21_environment_status(reactions):
    """Describe the two Mission 21 environments without dictionary-order assumptions.

    Both valid runs close oxygen uptake.  The reference keeps ethanol export at
    its model-default upper bound, while the modified run closes only that
    upper bound.  Explicit-key payloads must contain every lower/upper pair;
    legacy positional saves remain readable through ``_reaction_bound_open_states``.
    """
    bounds_complete = True
    unexpected_changes = []
    oxygen_lower_bound_closed = False
    ethanol_upper_bound_closed = False

    for index in range(len(REACTIONS.index)):
        reaction_id = REACTIONS.index[index]
        lower_open, upper_open = _reaction_bound_open_states(reactions, index)
        if lower_open is None or upper_open is None:
            bounds_complete = False
            continue

        default_lower_open = REACTIONS.lb.iloc[index] != 0
        default_upper_open = REACTIONS.ub.iloc[index] != 0
        lower_changed = lower_open != default_lower_open
        upper_changed = upper_open != default_upper_open

        if reaction_id == MISSION21_OXYGEN_REACTION:
            oxygen_lower_bound_closed = not lower_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id == MISSION21_ETHANOL_EXPORT:
            ethanol_upper_bound_closed = not upper_open
            if lower_changed:
                unexpected_changes.append(f'{reaction_id} lower bound')
            # Closing the upper bound is the controlled Mission 21 factor.
            if upper_changed and upper_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    run_type = None
    if bounds_complete and oxygen_lower_bound_closed and not unexpected_changes:
        run_type = 'ethanol_closed' if ethanol_upper_bound_closed else 'baseline'

    return {
        'bounds_complete': bounds_complete,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'ethanol_upper_bound_closed': ethanol_upper_bound_closed,
        'unexpected_environment_changes': unexpected_changes,
        'controlled_environment': bool(
            bounds_complete and oxygen_lower_bound_closed and not unexpected_changes
        ),
        'run_type': run_type,
    }


def _compare_run_name(snapshot):
    if not snapshot:
        return 'empty run'
    return snapshot.get('name') or snapshot.get('slot') or 'simulation run'


def _build_compare_run_snapshot(slot, simulation_results=None):
    method_name, objective_name, genes, reactions = _read_simulation_file()
    objective_result = _result_value_from_simulation_results(simulation_results)
    objective_value = _as_float_or_none(objective_result)
    growth_value = _numeric_result(objective_value)
    knocked_out = _knocked_out_genes(genes)
    environment_changed = _environment_has_changes(reactions)
    oxygen_lower_bound_open, oxygen_upper_bound_open = _bound_state_for_reaction(
        reactions,
        MISSION21_OXYGEN_REACTION,
    )
    mission21_environment = _mission21_environment_status(reactions)
    oxygen_lower_bound_closed = bool(mission21_environment.get('oxygen_lower_bound_closed'))
    oxygen_unexpected_changes = list(mission21_environment.get('unexpected_environment_changes') or [])

    production_fluxes = None
    medium_fluxes = None
    try:
        production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
        medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
    except Exception:
        pass

    production_values = _production_flux_value_map(production_fluxes)
    raw_fluxes, uptake_fluxes, secretion_fluxes = _medium_flux_maps(medium_fluxes)

    if knocked_out and not environment_changed:
        run_kind = 'gene knockout: ' + ', '.join(knocked_out)
    elif knocked_out and environment_changed:
        run_kind = 'gene + environment design'
    elif (not environment_changed) and objective_name != MISSION21_GROWTH_OBJECTIVE:
        run_kind = 'objective test: ' + objective_name
    elif not environment_changed:
        run_kind = 'default growth setup'
    elif (
        oxygen_lower_bound_closed
        and mission21_environment.get('ethanol_upper_bound_closed')
        and not oxygen_unexpected_changes
    ):
        run_kind = 'anaerobic medium + ethanol export blocked'
    elif oxygen_lower_bound_closed and not oxygen_unexpected_changes:
        run_kind = 'anaerobic medium (oxygen uptake blocked)'
    else:
        run_kind = 'modified setup'

    return {
        'slot': slot,
        'name': f'Run {slot}',
        'run_kind': run_kind,
        'method': method_name,
        'objective': objective_name,
        'objective_result': _clean_display_number(growth_value) if objective_value is not None else str(objective_result),
        # Kept for backwards compatibility with missions where the objective is biomass.
        'growth_value': _clean_display_number(growth_value),
        'objective_value': _clean_display_number(growth_value),
        'result_available': objective_value is not None,
        'knocked_out_genes': knocked_out,
        'environment_changed': environment_changed,
        'oxygen_reaction': MISSION21_OXYGEN_REACTION,
        'oxygen_lower_bound_open': oxygen_lower_bound_open,
        'oxygen_upper_bound_open': oxygen_upper_bound_open,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'ethanol_upper_bound_closed': bool(mission21_environment.get('ethanol_upper_bound_closed')),
        'oxygen_unexpected_changes': oxygen_unexpected_changes,
        'production_flux_values': {reaction_id: _clean_display_number(value) for reaction_id, value in production_values.items()},
        'exchange_raw_fluxes': {reaction_id: _clean_display_number(value) for reaction_id, value in raw_fluxes.items()},
        'exchange_uptake_fluxes': {reaction_id: _clean_display_number(value) for reaction_id, value in uptake_fluxes.items()},
        'exchange_secretion_fluxes': {reaction_id: _clean_display_number(value) for reaction_id, value in secretion_fluxes.items()},
        'selected_production_fluxes': _read_selected_production_fluxes(),
    }


def capture_compare_run_snapshot(simulation_results=None):
    """Capture the previous and current simulation for the Compare Runs report.

    The UI always keeps the previous simulation as Run A and the latest
    simulation as Run B. For an anaerobic comparison, run the aerobic baseline
    first, then block oxygen uptake and open Compare Runs.
    """
    existing = load_compare_runs() or {}
    previous_current = existing.get('run_b')
    snapshot = _build_compare_run_snapshot('B', simulation_results)

    if previous_current:
        previous_current = dict(previous_current)
        previous_current['slot'] = 'A'
        previous_current['name'] = 'Run A'

    compare_runs = {
        'run_a': previous_current,
        'run_b': snapshot,
    }
    save_compare_runs(compare_runs)
    return compare_runs


def _clean_display_number(value, tolerance=DISPLAY_ZERO_TOLERANCE):
    """Round values for reports and collapse numerical negative zero to 0.0."""
    numeric = float(value)
    if abs(numeric) < tolerance:
        numeric = 0.0
    return round(numeric, 3)


def _fmt_compare_value(value):
    if value is None:
        return 'not available'
    try:
        return f'{_clean_display_number(value):.3f}'
    except Exception:
        return str(value)


def _fmt_compare_delta(delta):
    if delta is None:
        return 'not available'
    try:
        numeric = _clean_display_number(delta)
        prefix = '+' if numeric > 0 else ''
        return f'{prefix}{numeric:.3f}'
    except Exception:
        return str(delta)


def _safe_delta(value_b, value_a):
    try:
        return _clean_display_number(float(value_b) - float(value_a))
    except Exception:
        return None


def _format_compare_knockouts(snapshot):
    knocked_out = snapshot.get('knocked_out_genes') or []
    return ', '.join(knocked_out) if knocked_out else 'none'


def _format_compare_environment(snapshot):
    if not snapshot.get('environment_changed'):
        return 'unchanged'
    oxygen_closed = bool(snapshot.get('oxygen_lower_bound_closed'))
    ethanol_closed = bool(snapshot.get('ethanol_upper_bound_closed'))
    unexpected = snapshot.get('oxygen_unexpected_changes') or []
    if oxygen_closed and ethanol_closed and not unexpected:
        return (
            f"oxygen lower bound closed ({MISSION21_OXYGEN_REACTION}); "
            f"ethanol upper bound closed ({MISSION21_ETHANOL_EXPORT})"
        )
    if oxygen_closed and not unexpected:
        return f"oxygen lower bound closed ({MISSION21_OXYGEN_REACTION})"
    if ethanol_closed and not unexpected:
        return f"ethanol upper bound closed ({MISSION21_ETHANOL_EXPORT})"
    if unexpected:
        return 'modified: ' + ', '.join(unexpected)
    return 'modified'


def _format_compare_tracked_fluxes(snapshot):
    selected_fluxes = snapshot.get('selected_production_fluxes') or []
    if not selected_fluxes:
        return 'none'
    return ', '.join(
        PRODUCTION_FLUX_LABELS.get(reaction_id, reaction_id)
        for reaction_id in selected_fluxes
    )


def _format_compare_setup(snapshot):
    return (
        f"{snapshot.get('run_kind', 'simulation')}\n"
        f"  Method: {snapshot.get('method')}\n"
        f"  Objective: {snapshot.get('objective')}\n"
        f"  Genes off: {_format_compare_knockouts(snapshot)}\n"
        f"  Environment: {_format_compare_environment(snapshot)}\n"
        f"  Production Flux tracked: {_format_compare_tracked_fluxes(snapshot)}"
    )


def _format_compare_change_list(run_a, run_b):
    changes = []

    if run_a.get('method') != run_b.get('method'):
        changes.append(f"- Method: {run_a.get('method')} -> {run_b.get('method')}")
    if run_a.get('objective') != run_b.get('objective'):
        changes.append(f"- Objective: {run_a.get('objective')} -> {run_b.get('objective')}")

    genes_a = _format_compare_knockouts(run_a)
    genes_b = _format_compare_knockouts(run_b)
    if genes_a != genes_b:
        changes.append(f"- Genes off: {genes_a} -> {genes_b}")

    env_a = _format_compare_environment(run_a)
    env_b = _format_compare_environment(run_b)
    if env_a != env_b:
        changes.append(f"- Environment: {env_a} -> {env_b}")

    tracked_a = _format_compare_tracked_fluxes(run_a)
    tracked_b = _format_compare_tracked_fluxes(run_b)
    if tracked_a != tracked_b:
        changes.append(f"- Production Flux tracked: {tracked_a} -> {tracked_b}")

    if not changes:
        changes.append('- No setup difference detected. Change one variable and run again.')

    return '\n'.join(changes)


def build_compare_runs_report_text(compare_runs=None):
    # None means no explicit state was supplied, so use the persisted comparison.
    # An explicit empty mapping must remain empty (important for clean mission
    # activation, tests, and any caller intentionally requesting a blank report).
    if compare_runs is None:
        compare_runs = load_compare_runs() or {}
    run_a = compare_runs.get('run_a')
    run_b = compare_runs.get('run_b')

    lines = [
        'Compare Runs',
        '',
        'Run A = previous simulation.',
        'Run B = latest simulation.',
        'Recommended flow: run the baseline first, then change ONE variable and run again.',
        'This makes it clear what caused the difference in the results.',
        '',
    ]

    if not run_a or not run_b:
        lines.append('Run two simulations to generate a comparison.')
        if run_b:
            lines.append('')
            lines.append('Current captured run:')
            lines.append('Run B:')
            lines.append(_format_compare_setup(run_b))
            lines.append('')
            lines.append('Now run one more simulation. The current Run B will become Run A.')
        return '\n'.join(lines)

    growth_a = run_a.get('growth_value')
    growth_b = run_b.get('growth_value')
    growth_delta = _safe_delta(growth_b, growth_a)

    oxygen_id = MISSION21_OXYGEN_REACTION
    oxygen_a = (run_a.get('exchange_uptake_fluxes') or {}).get(oxygen_id)
    oxygen_b = (run_b.get('exchange_uptake_fluxes') or {}).get(oxygen_id)
    oxygen_delta = _safe_delta(oxygen_b, oxygen_a)

    lines.extend([
        'What is being compared:',
        '',
        'Run A:',
        _format_compare_setup(run_a),
        '',
        'Run B:',
        _format_compare_setup(run_b),
        '',
        'Setup changes detected:',
        _format_compare_change_list(run_a, run_b),
        '',
        'Main numeric comparison:',
        f"- Objective value: {_fmt_compare_value(growth_a)} -> {_fmt_compare_value(growth_b)} ({_fmt_compare_delta(growth_delta)})",
        f"- Oxygen uptake magnitude ({oxygen_id}): {_fmt_compare_value(oxygen_a)} -> {_fmt_compare_value(oxygen_b)} ({_fmt_compare_delta(oxygen_delta)})",
    ])

    if run_a.get('objective') != run_b.get('objective'):
        lines.extend([
            '',
            'Objective note:',
            '- The objective value belongs to the objective selected in each run.',
            '- When objectives are different, use the tracked production fluxes for the clearest product comparison.',
        ])

    tracked_ids = []
    for reaction_id in (run_a.get('selected_production_fluxes') or []) + (run_b.get('selected_production_fluxes') or []):
        if reaction_id not in tracked_ids:
            tracked_ids.append(reaction_id)

    if tracked_ids:
        lines.append('')
        lines.append('Tracked production fluxes:')
        values_a = run_a.get('production_flux_values') or {}
        values_b = run_b.get('production_flux_values') or {}
        for reaction_id in tracked_ids:
            val_a = values_a.get(reaction_id)
            val_b = values_b.get(reaction_id)
            label = PRODUCTION_FLUX_LABELS.get(reaction_id, reaction_id)
            lines.append(
                f"- {label}: {_fmt_compare_value(val_a)} -> {_fmt_compare_value(val_b)} "
                f"({_fmt_compare_delta(_safe_delta(val_b, val_a))})"
            )

    lines.extend([
        '',
        'Interpretation guide:',
        '- Uptake values are shown as non-negative magnitudes; the raw exchange flux is negative during consumption.',
        '- Negative objective delta = Run B has a lower value for its shown objective.',
        '- Positive production delta = Run B secreted/exported more of that tracked product.',
        '- FBA may have alternative optimal flux distributions, so individual byproduct fluxes are not always unique.',
        '- If many setup changes appear, the comparison is not controlled.',
    ])
    return '\n'.join(lines)

def _mission02_environment_status(reactions):
    """Inspect whether a run follows Mission 02's controlled protocol.

    Explicit bound identifiers are independent of dictionary ordering; legacy
    positional saves remain readable through ``_reaction_bound_open_states``.
    """
    selected_sources = []
    unexpected_changes = []
    glucose_lower_bound_closed = False

    for i in range(len(REACTIONS.index)):
        reaction_id = REACTIONS.index[i]
        lower_bound_open, upper_bound_open = _reaction_bound_open_states(reactions, i)
        if lower_bound_open is None or upper_bound_open is None:
            unexpected_changes.append(f'{reaction_id} bounds unavailable')
            continue

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0
        lower_changed = lower_bound_open != default_lower_bound_open
        upper_changed = upper_bound_open != default_upper_bound_open

        if reaction_id == MISSION02_BLOCKED_CARBON_SOURCE:
            glucose_lower_bound_closed = not lower_bound_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id in MISSION02_CANDIDATE_CARBON_SOURCES:
            if lower_changed and lower_bound_open:
                selected_sources.append(reaction_id)
            elif lower_changed:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    return glucose_lower_bound_closed, selected_sources, unexpected_changes


def _mission02_source_lower_bound(source_id, reactions):
    lower_open, _upper_open = _bound_state_for_reaction(reactions, source_id)
    if lower_open is None:
        return None
    try:
        source_index = list(REACTIONS.index).index(source_id)
    except ValueError:
        return None
    return resolve_exchange_bound_value(
        REACTIONS.lb.iloc[source_index],
        lower_open,
        'lower',
    )


def _mission02_rank_trials(trials):
    ranked = sorted(
        (
            (source_id, float(trial.get('growth', 0.0)))
            for source_id, trial in (trials or {}).items()
            if source_id in MISSION02_CANDIDATE_CARBON_SOURCES
        ),
        key=lambda item: item[1],
        reverse=True,
    )
    if not ranked:
        return None, None, False, []

    top_growth = ranked[0][1]
    top_sources = [
        source_id
        for source_id, growth in ranked
        if abs(growth - top_growth) <= MISSION02_RANK_TOLERANCE
    ]
    winner_unique = len(top_sources) == 1
    winner_reaction = top_sources[0] if winner_unique else None
    return winner_reaction, top_growth, winner_unique, ranked


def _mission02_answer_alias_map():
    aliases = {}
    for source_id, source_name in MISSION02_SOURCE_NAMES.items():
        variants = {
            source_id,
            source_name,
            source_name.replace('D-', ''),
            source_name.replace('L-', ''),
            source_name.replace('-', ' '),
        }
        for variant in variants:
            key = ''.join(char.lower() for char in str(variant) if char.isalnum())
            if key:
                aliases[key] = source_id

    # Common European Portuguese spelling accepted without weakening the
    # requirement for simulation evidence.
    aliases['frutose'] = 'EX_fru_e'
    return aliases


def normalise_mission02_answer(answer):
    key = ''.join(char.lower() for char in str(answer or '') if char.isalnum())
    return _mission02_answer_alias_map().get(key)


def mission02_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission02_source_comparison_check() or {}
    if not report_data.get('evidence_ready'):
        return False
    submitted_source = normalise_mission02_answer(answer)
    return submitted_source == report_data.get('winner_reaction')


def _build_mission02_trial_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
):
    """Validate and accumulate one controlled Mission 02 candidate trial."""
    existing_report = existing_report or {}
    trials = copy.deepcopy(existing_report.get('trials') or {})

    knocked_out_genes = _knocked_out_genes(genes)
    method_correct = method_name == MISSION02_METHOD
    objective_correct = selected_objective == MISSION02_GROWTH_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    growth_value = _numeric_result(objective_value)
    result_valid = objective_value is not None and growth_value >= MISSION02_MIN_GROWTH

    glucose_closed, selected_sources, unexpected_changes = _mission02_environment_status(reactions)
    exactly_one_source = len(selected_sources) == 1
    selected_source = selected_sources[0] if exactly_one_source else None
    source_lower_bound = (
        _mission02_source_lower_bound(selected_source, reactions)
        if selected_source
        else None
    )
    common_bound_used = (
        source_lower_bound is not None
        and abs(float(source_lower_bound) - MISSION02_COMMON_UPTAKE_BOUND)
        <= MISSION02_FLUX_TOLERANCE
    )

    _raw_fluxes, uptake_fluxes, _secretion_fluxes = _medium_flux_maps(medium_fluxes)
    glucose_uptake = uptake_fluxes.get(MISSION02_BLOCKED_CARBON_SOURCE, 0.0)
    source_uptake = uptake_fluxes.get(selected_source, 0.0) if selected_source else 0.0
    glucose_uptake_blocked = glucose_uptake <= MISSION02_FLUX_TOLERANCE
    source_uptake_detected = source_uptake >= MISSION02_FLUX_TOLERANCE

    current_issues = []
    if objective_error:
        current_issues.append(objective_error)
    if not method_correct:
        current_issues.append('Use FBA so every candidate is compared with the same method.')
    if not objective_correct:
        current_issues.append('Use the biomass objective so the measured value represents predicted growth.')
    if knocked_out_genes:
        current_issues.append('Keep all genes active; this mission compares nutrients, not knockouts.')
    if not glucose_closed:
        current_issues.append('Glucose is still available, so the candidate is being added rather than substituted.')
    if not exactly_one_source:
        current_issues.append('Make exactly one candidate carbon source available at a time.')
    if unexpected_changes:
        current_issues.append('Keep every other environmental bound unchanged: ' + ', '.join(unexpected_changes))
    if selected_source and not common_bound_used:
        current_issues.append(
            f'Use the common molar uptake limit ({MISSION02_COMMON_UPTAKE_BOUND:g}) for every candidate.'
        )
    if not result_valid:
        current_issues.append('A positive biomass-growth result was not returned for this trial.')
    if not glucose_uptake_blocked:
        current_issues.append('The exchange report still detects glucose uptake.')
    if selected_source and not source_uptake_detected:
        current_issues.append('The exchange report does not confirm uptake of the selected candidate.')

    current_run_valid = not current_issues
    current_run_recorded = False
    if current_run_valid and selected_source:
        trials[selected_source] = {
            'reaction_id': selected_source,
            'source_name': MISSION02_SOURCE_NAMES.get(selected_source, selected_source),
            'growth': round(float(growth_value), 6),
            'uptake_magnitude': round(float(source_uptake), 6),
            'lower_bound': round(float(source_lower_bound), 6),
            'method': method_name,
            'objective': selected_objective,
        }
        current_run_recorded = True

    missing_candidates = [
        source_id
        for source_id in MISSION02_CANDIDATE_CARBON_SOURCES
        if source_id not in trials
    ]
    comparison_complete = not missing_candidates
    winner_reaction, winner_growth, winner_unique, ranked_trials = _mission02_rank_trials(trials)
    expected_winner_confirmed = (
        comparison_complete
        and winner_unique
        and winner_reaction == MISSION02_EXPECTED_WINNER
    )
    evidence_ready = comparison_complete and winner_unique and expected_winner_confirmed

    mission02_data = {
        'mission_id': '02',
        'check_version': 2,
        'mission_title': 'Alternative Carbon Source',
        'target_method': MISSION02_METHOD,
        'growth_objective': MISSION02_GROWTH_OBJECTIVE,
        'blocked_carbon_source': MISSION02_BLOCKED_CARBON_SOURCE,
        'common_uptake_bound': MISSION02_COMMON_UPTAKE_BOUND,
        'candidate_sources': list(MISSION02_CANDIDATE_CARBON_SOURCES),
        'source_names': dict(MISSION02_SOURCE_NAMES),
        'expected_winner': MISSION02_EXPECTED_WINNER,
        'trials': trials,
        'valid_trial_count': len(trials),
        'required_trial_count': len(MISSION02_CANDIDATE_CARBON_SOURCES),
        'missing_candidates': missing_candidates,
        'comparison_complete': comparison_complete,
        'winner_reaction': winner_reaction,
        'winner_name': MISSION02_SOURCE_NAMES.get(winner_reaction) if winner_reaction else None,
        'winner_growth': _clean_display_number(winner_growth) if winner_growth is not None else None,
        'winner_unique': winner_unique,
        'expected_winner_confirmed': expected_winner_confirmed,
        'evidence_ready': evidence_ready,
        'ranked_trials': [
            {
                'reaction_id': source_id,
                'source_name': MISSION02_SOURCE_NAMES.get(source_id, source_id),
                'growth': _clean_display_number(growth),
            }
            for source_id, growth in ranked_trials
        ],
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_candidate': selected_source,
        'current_candidate_name': MISSION02_SOURCE_NAMES.get(selected_source) if selected_source else None,
        'current_growth': _clean_display_number(growth_value) if objective_value is not None else None,
        'current_source_uptake': _clean_display_number(source_uptake) if selected_source else None,
        'current_source_lower_bound': _clean_display_number(source_lower_bound) if source_lower_bound is not None else None,
        'current_issues': current_issues,
        'unexpected_environment_changes': unexpected_changes,
        'knocked_out_genes': knocked_out_genes,
    }
    save_mission02_source_comparison_check(mission02_data)
    return mission02_data


def run_mission02_source_trial_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = _result_value_from_simulation_results(simulation_results)
    objective_error = None
    if objective_result is None:
        objective_error = 'Run a simulation before recording a Mission 02 trial.'

    medium_fluxes = None
    try:
        medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
    except Exception:
        medium_fluxes = None

    return _build_mission02_trial_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission02_source_comparison_check(),
        objective_error=objective_error,
    )


def build_mission02_evidence_report_text(report_data=None):
    """Build a player-facing evidence table without directly naming the answer."""
    if report_data is None:
        report_data = load_mission02_source_comparison_check() or {}
    trials = report_data.get('trials') or {}
    valid_count = int(report_data.get('valid_trial_count', len(trials)))
    required_count = int(
        report_data.get('required_trial_count', len(MISSION02_CANDIDATE_CARBON_SOURCES))
    )

    lines = [
        'Mission 02 Carbon-Source Evidence',
        '',
        f'Controlled candidate trials recorded: {valid_count}/{required_count}',
    ]

    if valid_count > 0:
        lines.append(
            f'Controlled setup confirmed: glucose unavailable; one candidate per trial; '
            f'common uptake limit {MISSION02_COMMON_UPTAKE_BOUND:g}; FBA biomass objective; genes unchanged.'
        )
    else:
        lines.append(
            'Build a fair carbon-source replacement comparison and use predicted growth as evidence. '
            'Optional hints are available from Dr. Martinez if you need guidance.'
        )

    lines.extend([
        '',
        'Candidate comparison:',
    ])

    for source_id in MISSION02_CANDIDATE_CARBON_SOURCES:
        source_name = MISSION02_SOURCE_NAMES.get(source_id, source_id)
        trial = trials.get(source_id)
        if trial:
            lines.append(
                f"- {source_name}: growth {_fmt_compare_value(trial.get('growth'))}; "
                f"uptake {_fmt_compare_value(trial.get('uptake_magnitude'))}; "
                f"lower bound {_fmt_compare_value(trial.get('lower_bound'))}"
            )
        else:
            lines.append(f'- {source_name}: not yet recorded')

    current_issues = report_data.get('current_issues') or []
    if report_data.get('current_run_recorded'):
        lines.extend([
            '',
            f"Latest valid trial recorded: {report_data.get('current_candidate_name')} "
            f"(growth {_fmt_compare_value(report_data.get('current_growth'))}).",
        ])
    elif current_issues:
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in current_issues)

    lines.append('')
    if report_data.get('evidence_ready'):
        lines.append('Evidence complete. Identify the candidate with the highest growth value and submit its name to Dr. Martinez.')
    elif report_data.get('comparison_complete'):
        lines.append('All candidates were tested, but the ranking is not yet a unique, stable result. Review the controlled setups and repeat any doubtful trial.')
    else:
        missing = report_data.get('missing_candidates') or []
        missing_names = [MISSION02_SOURCE_NAMES.get(source_id, source_id) for source_id in missing]
        lines.append('Continue the controlled comparison. Missing: ' + ', '.join(missing_names))

    lines.extend([
        '',
        'Interpretation note: this comparison uses the same molar uptake limit for every source. It does not claim that one source is universally best under every model, medium or normalization.',
    ])
    return '\n'.join(lines)


def _mission01_is_baseline_run(snapshot):
    if not snapshot:
        return False
    return (
        snapshot.get('result_available')
        and snapshot.get('method') == MISSION01_METHOD
        and snapshot.get('objective') == MISSION01_GROWTH_OBJECTIVE
        and not snapshot.get('knocked_out_genes')
        and not snapshot.get('environment_changed')
    )


def _mission01_is_anaerobic_run(snapshot):
    if not snapshot:
        return False
    return (
        snapshot.get('result_available')
        and snapshot.get('method') == MISSION01_METHOD
        and snapshot.get('objective') == MISSION01_GROWTH_OBJECTIVE
        and not snapshot.get('knocked_out_genes')
        and snapshot.get('oxygen_lower_bound_closed')
        and not snapshot.get('oxygen_unexpected_changes')
    )


def _build_mission01_data(compare_runs=None, error=None):
    # Keep an explicitly supplied empty comparison isolated from persisted runs.
    if compare_runs is None:
        compare_runs = {}
    run_a = compare_runs.get('run_a')
    run_b = compare_runs.get('run_b')

    baseline_run = None
    anaerobic_run = None
    for snapshot in (run_a, run_b):
        if baseline_run is None and _mission01_is_baseline_run(snapshot):
            baseline_run = snapshot
        if anaerobic_run is None and _mission01_is_anaerobic_run(snapshot):
            anaerobic_run = snapshot

    baseline_growth = baseline_run.get('growth_value') if baseline_run else None
    anaerobic_growth = anaerobic_run.get('growth_value') if anaerobic_run else None

    growth_drop = None
    anaerobic_growth_viable = False
    growth_decreased = False
    if baseline_growth is not None and anaerobic_growth is not None:
        baseline_growth = float(baseline_growth)
        anaerobic_growth = float(anaerobic_growth)
        growth_drop = round(baseline_growth - anaerobic_growth, 3)
        anaerobic_growth_viable = anaerobic_growth >= MISSION01_MIN_VIABLE_GROWTH
        growth_decreased = growth_drop >= MISSION01_MIN_GROWTH_DROP

    baseline_o2 = None
    anaerobic_o2 = None
    if baseline_run:
        baseline_o2 = (baseline_run.get('exchange_uptake_fluxes') or {}).get(
            MISSION01_OXYGEN_REACTION
        )
    if anaerobic_run:
        anaerobic_o2 = (anaerobic_run.get('exchange_uptake_fluxes') or {}).get(
            MISSION01_OXYGEN_REACTION
        )

    baseline_uses_oxygen = False
    anaerobic_oxygen_blocked = False
    if baseline_o2 is not None:
        try:
            baseline_uses_oxygen = float(baseline_o2) > MISSION01_FLUX_TOLERANCE
        except (TypeError, ValueError):
            pass
    if anaerobic_o2 is not None:
        try:
            anaerobic_oxygen_blocked = abs(float(anaerobic_o2)) <= MISSION01_FLUX_TOLERANCE
        except (TypeError, ValueError):
            pass

    mission01_data = {
        'mission_id': '01',
        'check_version': 2,
        'mission_title': 'Anaerobic Growth',
        'target_method': MISSION01_METHOD,
        'growth_objective': MISSION01_GROWTH_OBJECTIVE,
        'oxygen_reaction': MISSION01_OXYGEN_REACTION,
        'run_a': run_a,
        'run_b': run_b,
        'baseline_run_found': baseline_run is not None,
        'anaerobic_run_found': anaerobic_run is not None,
        'baseline_growth': _clean_display_number(baseline_growth) if baseline_growth is not None else None,
        'anaerobic_growth': _clean_display_number(anaerobic_growth) if anaerobic_growth is not None else None,
        'growth_drop': _clean_display_number(growth_drop) if growth_drop is not None else None,
        'anaerobic_growth_viable': anaerobic_growth_viable,
        'growth_decreased': growth_decreased,
        'baseline_oxygen_uptake': _clean_display_number(baseline_o2) if baseline_o2 is not None else None,
        'anaerobic_oxygen_uptake': _clean_display_number(anaerobic_o2) if anaerobic_o2 is not None else None,
        'baseline_uses_oxygen': baseline_uses_oxygen,
        'anaerobic_oxygen_blocked': anaerobic_oxygen_blocked,
        'ready_to_deliver': (
            baseline_run is not None
            and anaerobic_run is not None
            and anaerobic_growth_viable
            and growth_decreased
            and baseline_uses_oxygen
            and anaerobic_oxygen_blocked
        ),
    }
    if error:
        mission01_data['error'] = error
    save_mission01_comparison_check(mission01_data)
    return mission01_data


def run_mission01_comparison_check(compare_runs=None):
    # Only an omitted argument loads persisted runs. Passing {} explicitly means
    # that no runs are available and must never be replaced by stale save data.
    if compare_runs is None:
        compare_runs = load_compare_runs()
    if not compare_runs or not compare_runs.get('run_a') or not compare_runs.get('run_b'):
        return _build_mission01_data(
            compare_runs,
            error='Run the aerobic baseline and the anaerobic setup before delivering Mission 01.',
        )
    return _build_mission01_data(compare_runs)


def is_mission21_unlocked(missions_completed):
    """Mission 21 starts only after Dr. Rio's final mission."""
    return '20' in (missions_completed or [])


def _mission21_number_or_none(value):
    numeric = _as_float_or_none(value)
    return float(numeric) if numeric is not None else None


def _mission21_clean_number(value, decimals=6):
    numeric = float(value)
    if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
        numeric = 0.0
    return round(numeric, decimals)


def _mission21_measured_medium_values(medium_fluxes):
    """Read only complete numeric exchange rows from the visible solution."""
    raw_fluxes = {}
    uptake_fluxes = {}
    secretion_fluxes = {}
    if not isinstance(medium_fluxes, dict) or medium_fluxes.get('error'):
        return raw_fluxes, uptake_fluxes, secretion_fluxes
    for item in medium_fluxes.get('items') or []:
        if not isinstance(item, dict) or item.get('error'):
            continue
        reaction_id = item.get('reaction_id')
        raw_value = _mission21_number_or_none(item.get('raw_flux'))
        uptake_value = _mission21_number_or_none(item.get('uptake_flux'))
        secretion_value = _mission21_number_or_none(item.get('secretion_flux'))
        if (
            reaction_id
            and raw_value is not None
            and uptake_value is not None
            and secretion_value is not None
        ):
            reaction_id = str(reaction_id)
            raw_fluxes[reaction_id] = _mission21_clean_number(raw_value)
            uptake_fluxes[reaction_id] = _mission21_clean_number(max(uptake_value, 0.0))
            secretion_fluxes[reaction_id] = _mission21_clean_number(max(secretion_value, 0.0))
    return raw_fluxes, uptake_fluxes, secretion_fluxes


def _mission21_measured_production_values(production_fluxes):
    """Read numeric secretion values from the visible Production Flux report."""
    values = {}
    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        return values
    for item in production_fluxes.get('items') or []:
        if not isinstance(item, dict) or item.get('error'):
            continue
        reaction_id = item.get('reaction_id')
        value = _mission21_number_or_none(item.get('production_flux'))
        if reaction_id and value is not None:
            values[str(reaction_id)] = _mission21_clean_number(max(value, 0.0))
    return values


def _normalise_mission21_text(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(char for char in text if not unicodedata.combining(char)).lower()


def normalise_mission21_answer(answer):
    """Extract tracked secretion identifiers from a concise player answer."""
    text = _normalise_mission21_text(answer)
    if not text.strip() or re.search(r'\b(?:all|every|todos|todas|both|ambos|ambas)\b', text):
        return tuple()
    patterns = {
        'EX_ac_e': r'\b(?:ex[_\s-]*ac[_\s-]*e|acetate|acetato)\b',
        'EX_etoh_e': r'\b(?:ex[_\s-]*etoh[_\s-]*e|ethanol|etanol)\b',
        'EX_for_e': r'\b(?:ex[_\s-]*for[_\s-]*e|formate|formato)\b',
        'EX_succ_e': r'\b(?:ex[_\s-]*succ[_\s-]*e|succinate|succinato)\b',
        'EX_lac__D_e': r'\b(?:ex[_\s-]*lac[_\s-]*d[_\s-]*e|d[-\s]*lactate|lactate|lactato)\b',
    }
    found = {
        reaction_id for reaction_id, pattern in patterns.items()
        if re.search(pattern, text)
    }
    return tuple(
        reaction_id for reaction_id in MISSION21_REQUIRED_TRACKED_FLUXES
        if reaction_id in found
    )


def mission21_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission21_comparison_check() or {}
    expected = tuple(
        reaction_id for reaction_id in MISSION21_REQUIRED_TRACKED_FLUXES
        if reaction_id in set(report_data.get('largest_increase_candidates') or [])
    )
    return bool(
        report_data.get('evidence_ready')
        and report_data.get('relationship_supported')
        and expected
        and normalise_mission21_answer(answer) == expected
    )


def initialise_mission21_compensatory_comparison():
    data = {
        'mission_id': '21',
        'check_version': MISSION21_CHECK_VERSION,
        'mission_title': 'Compensatory Flux Comparison',
        'target_context': MISSION21_TARGET_CONTEXT,
        'target_method': MISSION21_METHOD,
        'growth_objective': MISSION21_GROWTH_OBJECTIVE,
        'oxygen_reaction': MISSION21_OXYGEN_REACTION,
        'ethanol_export': MISSION21_ETHANOL_EXPORT,
        'required_tracked_fluxes': list(MISSION21_REQUIRED_TRACKED_FLUXES),
        'required_medium_fluxes': list(MISSION21_REQUIRED_MEDIUM_FLUXES),
        'baseline_run': None,
        'ethanol_closed_run': None,
        'recorded_run_count': 0,
        'required_run_count': 2,
        'missing_run_types': ['baseline', 'ethanol_closed'],
        'all_runs_recorded': False,
        'same_controlled_setup': False,
        'growth_ratio': None,
        'flux_differences': {},
        'largest_increase': None,
        'largest_increase_candidates': [],
        'relationship_supported': False,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_run_valid': False,
        'current_run_recorded': False,
        'current_run_type': None,
        'current_issues': [],
        'latest_attempt': None,
    }
    save_mission21_comparison_check(data)
    return data


def _build_mission21_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    selected_fluxes=None,
    objective_error=None,
):
    """Validate and accumulate one visible Mission 21 comparison run."""
    existing_report = existing_report or {}
    if (
        existing_report.get('mission_id') != '21'
        or existing_report.get('check_version') != MISSION21_CHECK_VERSION
    ):
        existing_report = {}

    baseline_run = copy.deepcopy(existing_report.get('baseline_run'))
    ethanol_closed_run = copy.deepcopy(existing_report.get('ethanol_closed_run'))

    environment = _mission21_environment_status(reactions)
    run_type = environment.get('run_type')
    knocked_out_genes = _knocked_out_genes(genes)
    objective_numeric = _mission21_number_or_none(objective_result)
    result_infeasible = 'INFEASIBLE' in str(objective_result or '').upper()

    measured_production = _mission21_measured_production_values(production_fluxes)
    raw_fluxes, uptake_fluxes, secretion_fluxes = _mission21_measured_medium_values(medium_fluxes)
    diagnostics = _method_diagnostics_from_production_data(production_fluxes)
    biomass_raw = _mission21_number_or_none(_mission13_biomass_value(production_fluxes))
    primary_flux = _mission21_number_or_none(diagnostics.get('primary_objective_flux'))
    method_score = _mission21_number_or_none(diagnostics.get('method_score'))
    method_score_name = diagnostics.get('method_score_name')
    total_absolute_flux = _mission21_number_or_none(diagnostics.get('total_absolute_flux'))
    try:
        active_reaction_count = int(diagnostics.get('active_reaction_count'))
    except Exception:
        active_reaction_count = None

    if selected_fluxes is None:
        selected_fluxes = _read_selected_production_fluxes()
    selected_fluxes = list(selected_fluxes or [])

    missing_medium_fluxes = [
        reaction_id for reaction_id in MISSION21_REQUIRED_MEDIUM_FLUXES
        if reaction_id not in raw_fluxes
    ]
    missing_selected_fluxes = [
        reaction_id for reaction_id in MISSION21_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    extra_selected_fluxes = [
        reaction_id for reaction_id in selected_fluxes
        if reaction_id not in MISSION21_REQUIRED_TRACKED_FLUXES
    ]
    missing_measured_fluxes = [
        reaction_id for reaction_id in MISSION21_REQUIRED_TRACKED_FLUXES
        if reaction_id not in measured_production
    ]

    glucose_uptake = _mission21_number_or_none(uptake_fluxes.get(MISSION21_GLUCOSE_REACTION))
    oxygen_uptake = _mission21_number_or_none(uptake_fluxes.get(MISSION21_OXYGEN_REACTION))
    ethanol_export = _mission21_number_or_none(measured_production.get(MISSION21_ETHANOL_EXPORT))

    issues = []
    if objective_error:
        issues.append(objective_error)
    if method_name != MISSION21_METHOD:
        issues.append('Use FBA for both Mission 21 runs.')
    if selected_objective != MISSION21_GROWTH_OBJECTIVE:
        issues.append('Use the biomass objective for both Mission 21 runs.')
    if knocked_out_genes:
        issues.append('Keep every gene active; only ethanol export may change between the two runs.')
    if not environment.get('bounds_complete'):
        issues.append('The environmental-bound payload is incomplete.')
    if not environment.get('oxygen_lower_bound_closed'):
        issues.append('Close the oxygen lower bound in both Mission 21 runs.')
    if environment.get('unexpected_environment_changes'):
        issues.append('Keep glucose and every unrelated environmental bound at the model default.')
    if run_type not in {'baseline', 'ethanol_closed'}:
        issues.append('Use either the anaerobic reference or the same setup with only ethanol export closed.')

    if result_infeasible or objective_numeric is None:
        issues.append('Mission 21 requires a numeric viable biomass result in both runs.')
    elif objective_numeric < MISSION21_MIN_BASELINE_GROWTH:
        issues.append('The current run does not retain enough predicted growth for comparison.')

    if medium_fluxes and medium_fluxes.get('error'):
        issues.append('The Exchange Flux Report is unavailable for this run.')
    elif missing_medium_fluxes:
        issues.append('The Exchange Flux Report is missing required Mission 21 reactions.')
    if production_fluxes and production_fluxes.get('error'):
        issues.append('The Production Flux report is unavailable for this run.')
    elif missing_measured_fluxes:
        issues.append('The Production Flux report is missing numeric Mission 21 values.')
    if missing_selected_fluxes or extra_selected_fluxes:
        issues.append('Select exactly the complete Mission 21 product/byproduct panel.')

    if glucose_uptake is None or oxygen_uptake is None:
        issues.append('Numeric glucose and oxygen uptake evidence is required.')
    else:
        if abs(glucose_uptake - MISSION21_EXPECTED_GLUCOSE_UPTAKE) > MISSION21_GLUCOSE_UPTAKE_TOLERANCE:
            issues.append('Keep the model-default glucose uptake protocol in both runs.')
        if oxygen_uptake > MISSION21_FLUX_TOLERANCE:
            issues.append('The Mission 21 comparison must remain in the oxygen-closed context.')

    for reaction_id in MISSION21_REQUIRED_TRACKED_FLUXES:
        if reaction_id not in raw_fluxes or reaction_id not in measured_production:
            continue
        expected_secretion = max(float(raw_fluxes[reaction_id]), 0.0)
        if abs(float(measured_production[reaction_id]) - expected_secretion) > MISSION21_FLUX_TOLERANCE:
            issues.append('Production Flux and Exchange Flux evidence do not describe the same visible solution.')
            break

    if diagnostics.get('method') != MISSION21_METHOD:
        issues.append('The visible method diagnostics do not describe FBA.')
    if diagnostics.get('objective_reaction') != selected_objective:
        issues.append('The visible method diagnostics do not match the biomass objective.')
    if method_score_name != 'primary_objective_flux':
        issues.append('The FBA method score is not identified as the primary objective flux.')
    if primary_flux is None or biomass_raw is None or method_score is None:
        issues.append('The visible result is missing biomass or FBA objective diagnostics.')
    else:
        if abs(primary_flux - objective_numeric) > MISSION21_PRIMARY_TOLERANCE:
            issues.append('The displayed objective value does not match the visible primary biomass flux.')
        if abs(biomass_raw - primary_flux) > MISSION21_PRIMARY_TOLERANCE:
            issues.append('The biomass value and primary objective flux describe different results.')
        if abs(method_score - primary_flux) > MISSION21_PRIMARY_TOLERANCE:
            issues.append('The FBA method score does not match the primary objective flux.')
    if total_absolute_flux is None or active_reaction_count is None:
        issues.append('The visible FBA result is missing flux-distribution diagnostics.')

    if run_type == 'baseline' and ethanol_export is not None:
        if ethanol_export <= MISSION21_MIN_ACTIVE_BASELINE_ETHANOL:
            issues.append('The anaerobic reference must show active ethanol export before it is closed.')
    if run_type == 'ethanol_closed' and ethanol_export is not None:
        if ethanol_export > MISSION21_MAX_CLOSED_ETHANOL_FLUX:
            issues.append('The ethanol-closed run still exports ethanol.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run = None
    if current_run_valid:
        current_run = {
            'run_type': run_type,
            'method': method_name,
            'objective': selected_objective,
            'growth': _mission21_clean_number(objective_numeric),
            'knocked_out_genes': list(knocked_out_genes),
            'oxygen_lower_bound_closed': bool(environment.get('oxygen_lower_bound_closed')),
            'ethanol_upper_bound_closed': bool(environment.get('ethanol_upper_bound_closed')),
            'glucose_uptake': _mission21_clean_number(glucose_uptake),
            'oxygen_uptake': _mission21_clean_number(oxygen_uptake),
            'tracked_flux_values': {
                reaction_id: _mission21_clean_number(measured_production[reaction_id])
                for reaction_id in MISSION21_REQUIRED_TRACKED_FLUXES
            },
            'selected_fluxes': list(selected_fluxes),
            'method_diagnostics': {
                'method': diagnostics.get('method'),
                'objective_reaction': diagnostics.get('objective_reaction'),
                'primary_objective_flux': _mission21_clean_number(primary_flux),
                'method_score': _mission21_clean_number(method_score),
                'method_score_name': method_score_name,
                'total_absolute_flux': _mission21_clean_number(total_absolute_flux),
                'active_reaction_count': active_reaction_count,
            },
        }
        if run_type == 'baseline':
            baseline_run = current_run
        else:
            ethanol_closed_run = current_run
        current_run_recorded = True

    all_runs_recorded = isinstance(baseline_run, dict) and isinstance(ethanol_closed_run, dict)
    missing_run_types = []
    if not isinstance(baseline_run, dict):
        missing_run_types.append('baseline')
    if not isinstance(ethanol_closed_run, dict):
        missing_run_types.append('ethanol_closed')

    same_controlled_setup = bool(
        all_runs_recorded
        and baseline_run.get('method') == MISSION21_METHOD
        and ethanol_closed_run.get('method') == MISSION21_METHOD
        and baseline_run.get('objective') == MISSION21_GROWTH_OBJECTIVE
        and ethanol_closed_run.get('objective') == MISSION21_GROWTH_OBJECTIVE
        and not baseline_run.get('knocked_out_genes')
        and not ethanol_closed_run.get('knocked_out_genes')
        and baseline_run.get('oxygen_lower_bound_closed')
        and ethanol_closed_run.get('oxygen_lower_bound_closed')
        and not baseline_run.get('ethanol_upper_bound_closed')
        and ethanol_closed_run.get('ethanol_upper_bound_closed')
        and set(baseline_run.get('selected_fluxes') or []) == set(MISSION21_REQUIRED_TRACKED_FLUXES)
        and set(ethanol_closed_run.get('selected_fluxes') or []) == set(MISSION21_REQUIRED_TRACKED_FLUXES)
        and abs(float(baseline_run.get('glucose_uptake')) - MISSION21_EXPECTED_GLUCOSE_UPTAKE)
        <= MISSION21_GLUCOSE_UPTAKE_TOLERANCE
        and abs(float(ethanol_closed_run.get('glucose_uptake')) - MISSION21_EXPECTED_GLUCOSE_UPTAKE)
        <= MISSION21_GLUCOSE_UPTAKE_TOLERANCE
        and float(baseline_run.get('oxygen_uptake')) <= MISSION21_FLUX_TOLERANCE
        and float(ethanol_closed_run.get('oxygen_uptake')) <= MISSION21_FLUX_TOLERANCE
    )

    growth_ratio = None
    flux_differences = {}
    largest_increase = None
    largest_increase_candidates = []
    relationship_supported = False
    if all_runs_recorded:
        baseline_growth = _mission21_number_or_none(baseline_run.get('growth'))
        modified_growth = _mission21_number_or_none(ethanol_closed_run.get('growth'))
        if baseline_growth is not None and modified_growth is not None and baseline_growth > 0:
            growth_ratio = _mission21_clean_number(modified_growth / baseline_growth)
        for reaction_id in MISSION21_REQUIRED_TRACKED_FLUXES:
            baseline_value = _mission21_number_or_none(
                (baseline_run.get('tracked_flux_values') or {}).get(reaction_id)
            )
            modified_value = _mission21_number_or_none(
                (ethanol_closed_run.get('tracked_flux_values') or {}).get(reaction_id)
            )
            if baseline_value is None or modified_value is None:
                flux_differences = {}
                break
            flux_differences[reaction_id] = _mission21_clean_number(modified_value - baseline_value)

        if flux_differences:
            largest_increase = max(flux_differences.values())
            if largest_increase >= MISSION21_MIN_COMPENSATORY_INCREASE:
                largest_increase_candidates = [
                    reaction_id for reaction_id in MISSION21_REQUIRED_TRACKED_FLUXES
                    if abs(flux_differences[reaction_id] - largest_increase)
                    <= MISSION21_LARGEST_INCREASE_TOLERANCE
                ]

        baseline_ethanol = _mission21_number_or_none(
            (baseline_run.get('tracked_flux_values') or {}).get(MISSION21_ETHANOL_EXPORT)
        )
        closed_ethanol = _mission21_number_or_none(
            (ethanol_closed_run.get('tracked_flux_values') or {}).get(MISSION21_ETHANOL_EXPORT)
        )
        relationship_supported = bool(
            same_controlled_setup
            and growth_ratio is not None
            and growth_ratio >= MISSION21_MIN_MODIFIED_VIABILITY_RATIO
            and baseline_ethanol is not None
            and baseline_ethanol > MISSION21_MIN_ACTIVE_BASELINE_ETHANOL
            and closed_ethanol is not None
            and closed_ethanol <= MISSION21_MAX_CLOSED_ETHANOL_FLUX
            and largest_increase_candidates == [MISSION21_EXPECTED_LARGEST_INCREASE]
        )

    latest_attempt = {
        'method': method_name,
        'objective': selected_objective,
        'run_type': run_type,
        'objective_result': str(objective_result),
        'issues': list(issues),
        'recorded': current_run_recorded,
    }
    report = {
        'mission_id': '21',
        'check_version': MISSION21_CHECK_VERSION,
        'mission_title': 'Compensatory Flux Comparison',
        'target_context': MISSION21_TARGET_CONTEXT,
        'target_method': MISSION21_METHOD,
        'growth_objective': MISSION21_GROWTH_OBJECTIVE,
        'oxygen_reaction': MISSION21_OXYGEN_REACTION,
        'ethanol_export': MISSION21_ETHANOL_EXPORT,
        'required_tracked_fluxes': list(MISSION21_REQUIRED_TRACKED_FLUXES),
        'required_medium_fluxes': list(MISSION21_REQUIRED_MEDIUM_FLUXES),
        'baseline_run': baseline_run,
        'ethanol_closed_run': ethanol_closed_run,
        'recorded_run_count': int(isinstance(baseline_run, dict)) + int(isinstance(ethanol_closed_run, dict)),
        'required_run_count': 2,
        'missing_run_types': missing_run_types,
        'all_runs_recorded': all_runs_recorded,
        'same_controlled_setup': same_controlled_setup,
        'growth_ratio': growth_ratio,
        'flux_differences': flux_differences,
        'largest_increase': _mission21_clean_number(largest_increase) if largest_increase is not None else None,
        'largest_increase_candidates': largest_increase_candidates,
        'expected_largest_increase': MISSION21_EXPECTED_LARGEST_INCREASE,
        'relationship_supported': relationship_supported,
        'evidence_ready': all_runs_recorded,
        'answer_ready': relationship_supported,
        'ready_to_deliver': relationship_supported,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': run_type,
        'current_issues': issues,
        'current_run': current_run,
        'latest_attempt': latest_attempt,
    }
    save_mission21_comparison_check(report)
    return report


def run_mission21_comparison_check(simulation_results=None):
    """Validate the already visible Mission 21 result without re-simulating."""
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible Mission 21 simulation before recording evidence.'
    except Exception:
        objective_error = 'Could not read the current visible Mission 21 simulation result.'

    return _build_mission21_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission21_comparison_check() or {},
        objective_error=objective_error,
    )


def run_mission21_comparison_check_remote(backend_url, simulation_results=None):
    """Browser parity wrapper: validate the already visible backend result."""
    del backend_url
    return run_mission21_comparison_check(simulation_results)


def build_mission21_compensatory_report_text(report):
    if not report:
        return 'Mission 21 Compensatory Flux Comparison\n\nActivate the mission and record the two controlled runs.'
    if report.get('mission_id') != '21' or report.get('check_version') != MISSION21_CHECK_VERSION:
        return 'Mission 21 Compensatory Flux Comparison\n\nCurrent-format evidence has not been recorded yet.'

    lines = [
        'Mission 21 Compensatory Flux Comparison',
        '',
        'Controlled protocol:',
        '- FBA biomass objective; all genes active',
        '- Model-default glucose; oxygen uptake lower bound closed in both runs',
        '- Reference: ethanol export upper bound open',
        '- Modified run: close only the ethanol export upper bound',
        '- Complete product/byproduct panel measured from each visible solution',
        '',
        f"Controlled runs recorded: {report.get('recorded_run_count', 0)}/{report.get('required_run_count', 2)}",
    ]

    for title, key in (
        ('Anaerobic reference', 'baseline_run'),
        ('Ethanol-export closure', 'ethanol_closed_run'),
    ):
        run = report.get(key) or {}
        if not run:
            lines.append(f'- {title}: not recorded')
            continue
        lines.extend([
            f'{title}:',
            f"- Growth: {float(run.get('growth')):.3f}",
            f"- Glucose uptake: {float(run.get('glucose_uptake')):.3f}",
            f"- Oxygen uptake: {float(run.get('oxygen_uptake')):.3f}",
            '- Export profile:',
        ])
        fluxes = run.get('tracked_flux_values') or {}
        for reaction_id in MISSION21_REQUIRED_TRACKED_FLUXES:
            lines.append(
                f"  {MISSION21_FLUX_NAMES.get(reaction_id, reaction_id)} ({reaction_id}): "
                f"{float(fluxes.get(reaction_id)):.3f}"
            )
        lines.append('')

    if report.get('all_runs_recorded'):
        lines.append('Before/after comparison:')
        if report.get('growth_ratio') is not None:
            lines.append(f"- Modified growth as fraction of reference: {float(report.get('growth_ratio')) * 100:.1f}%")
        differences = report.get('flux_differences') or {}
        for reaction_id in MISSION21_REQUIRED_TRACKED_FLUXES:
            if reaction_id in differences:
                value = float(differences[reaction_id])
                prefix = '+' if value > 0 else ''
                lines.append(
                    f"- {MISSION21_FLUX_NAMES.get(reaction_id, reaction_id)} ({reaction_id}): {prefix}{value:.3f}"
                )
    else:
        missing = report.get('missing_run_types') or []
        if missing:
            lines.append('Missing controlled runs: ' + ', '.join(missing) + '.')

    if report.get('current_run_recorded'):
        lines.extend(['', f"Latest valid visible run recorded: {str(report.get('current_run_type') or '').replace('_', ' ')}."])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if report.get('baseline_run') or report.get('ethanol_closed_run'):
            lines.append('Previously valid Mission 21 evidence remains available.')

    lines.append('')
    if report.get('evidence_ready'):
        lines.extend([
            'Evidence complete.',
            'Compare the signed before/after changes and identify the tracked secretion with the largest increase.',
            'Question: Which tracked secretion showed the largest increase after ethanol export was closed?',
        ])
    else:
        lines.append('Evidence incomplete.')

    lines.extend([
        '',
        'Interpretation note: a large final flux and a large increase are not the same quantity; use the recorded differences.',
        'The observed compensation is conditional on this model, anaerobic glucose medium and biomass objective.',
        'All growth and exchange values come from the same visible solver results. No hidden simulation is used.',
    ])
    return '\n'.join(lines)

def is_mission22_unlocked(missions_completed):
    """Mission 22 is Dr. Vega's final task and follows Mission 21."""
    return '21' in (missions_completed or [])


def _mission22_number_or_none(value):
    numeric = _as_float_or_none(value)
    return float(numeric) if numeric is not None else None


def _mission22_clean_number(value, decimals=6):
    numeric = float(value)
    if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
        numeric = 0.0
    return round(numeric, decimals)


def _mission22_environment_status(reactions):
    """Classify Mission 22 environments by reaction id, never dict order.

    Both controlled runs close oxygen uptake.  The environmental intervention
    additionally closes acetate export; the genetic intervention keeps the
    acetate exchange at its model-default bounds.  Every unrelated bound must
    remain at the SBML default.
    """
    bounds_complete = True
    oxygen_lower_bound_closed = False
    acetate_upper_bound_closed = False
    unexpected_changes = []

    for index in range(len(REACTIONS.index)):
        reaction_id = REACTIONS.index[index]
        lower_open, upper_open = _reaction_bound_open_states(reactions, index)
        if lower_open is None or upper_open is None:
            bounds_complete = False
            continue

        default_lower_open = REACTIONS.lb.iloc[index] != 0
        default_upper_open = REACTIONS.ub.iloc[index] != 0
        lower_changed = lower_open != default_lower_open
        upper_changed = upper_open != default_upper_open

        if reaction_id == MISSION22_OXYGEN_REACTION:
            oxygen_lower_bound_closed = not lower_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id == MISSION22_ENVIRONMENTAL_EXPORT:
            acetate_upper_bound_closed = not upper_open
            if lower_changed:
                unexpected_changes.append(f'{reaction_id} lower bound')
            # The upper-bound closure is the controlled environmental factor.
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    controlled_environment = bool(
        bounds_complete
        and oxygen_lower_bound_closed
        and not unexpected_changes
    )
    return {
        'bounds_complete': bounds_complete,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'acetate_upper_bound_closed': acetate_upper_bound_closed,
        'unexpected_environment_changes': unexpected_changes,
        'controlled_environment': controlled_environment,
    }


def _mission22_disabled_reactions(knocked_out_genes):
    """Evaluate the complete GPR without running a metabolic simulation."""
    knocked_out_genes = list(knocked_out_genes or [])
    if model is not None:
        try:
            return sorted(disabled_reaction_ids(model, knocked_out_genes))
        except Exception:
            pass

    # Browser-safe fallback for the exact Mission 22 GPR demonstrated earlier:
    # PTAr = b2297 OR b2458.  One gene alone leaves the reaction functional.
    if set(knocked_out_genes) == set(MISSION22_TARGET_GENES) and len(knocked_out_genes) == 2:
        return list(MISSION22_EXPECTED_DISABLED_REACTIONS)
    return []


def _mission22_measured_medium_values(medium_fluxes):
    raw, uptake, secretion = _mission21_measured_medium_values(medium_fluxes)
    return raw, uptake, secretion


def _mission22_measured_production_values(production_fluxes):
    return _mission21_measured_production_values(production_fluxes)


def _normalise_mission22_text(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    text = ''.join(character for character in text if not unicodedata.combining(character))
    return text.lower().strip()


def normalise_mission22_answer(answer):
    """Return the submitted output count only for an unambiguous zero answer."""
    text = _normalise_mission22_text(answer)
    if not text:
        return None
    if re.search(r'\b[1-9]\d*\b', text):
        return None
    if re.search(
        r'\b(?:acetate|acetato|ethanol|etanol|formate|formato|succinate|succinato|'
        r'lactate|lactato|ptar|b2297|b2458|all|todos|todas|both|ambos|ambas)\b',
        text,
    ):
        return None

    compact = ''.join(character for character in text if character.isalnum())
    accepted = {
        '0', 'zero', 'none', 'nothing', 'nenhum', 'nenhuma',
        'nodifference', 'nodifferences', 'nooutput', 'nooutputs',
        'zerodifference', 'zerodifferences', 'zerooutput', 'zerooutputs',
        'nenhumadiferenca', 'nenhumasdiferencas', 'nenhumoutput', 'nenhumoutputs',
    }
    return 0 if compact in accepted else None


def mission22_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission22_comparison_check() or {}
    submitted = normalise_mission22_answer(answer)
    expected = report_data.get('different_output_count')
    return bool(
        report_data.get('evidence_ready')
        and report_data.get('relationship_supported')
        and submitted is not None
        and expected is not None
        and submitted == int(expected)
    )


def initialise_mission22_phenotype_equivalence_audit():
    data = {
        'mission_id': '22',
        'check_version': MISSION22_CHECK_VERSION,
        'mission_title': 'Phenotype Equivalence Audit',
        'target_context': MISSION22_TARGET_CONTEXT,
        'target_method': MISSION22_METHOD,
        'growth_objective': MISSION22_GROWTH_OBJECTIVE,
        'oxygen_reaction': MISSION22_OXYGEN_REACTION,
        'environmental_export': MISSION22_ENVIRONMENTAL_EXPORT,
        'target_genes': list(MISSION22_TARGET_GENES),
        'expected_disabled_reactions': list(MISSION22_EXPECTED_DISABLED_REACTIONS),
        'required_tracked_fluxes': list(MISSION22_REQUIRED_TRACKED_FLUXES),
        'required_medium_fluxes': list(MISSION22_REQUIRED_MEDIUM_FLUXES),
        'environmental_intervention_run': None,
        'genetic_intervention_run': None,
        'recorded_run_count': 0,
        'required_run_count': 2,
        'missing_run_types': ['environmental_intervention', 'genetic_intervention'],
        'all_runs_recorded': False,
        'same_base_protocol': False,
        'phenotype_differences': {},
        'different_output_ids': [],
        'different_output_count': None,
        'maximum_absolute_difference': None,
        'relationship_supported': False,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_run_valid': False,
        'current_run_recorded': False,
        'current_run_type': None,
        'current_issues': [],
        'latest_attempt': None,
    }
    save_mission22_comparison_check(data)
    return data


def _build_mission22_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    selected_fluxes=None,
    objective_error=None,
):
    """Validate and accumulate one visible Mission 22 intervention run."""
    existing_report = existing_report or {}
    if (
        existing_report.get('mission_id') != '22'
        or existing_report.get('check_version') != MISSION22_CHECK_VERSION
    ):
        existing_report = {}

    environmental_run = copy.deepcopy(existing_report.get('environmental_intervention_run'))
    genetic_run = copy.deepcopy(existing_report.get('genetic_intervention_run'))

    environment = _mission22_environment_status(reactions)
    knocked_out_genes = _knocked_out_genes(genes)
    exact_target_pair = (
        len(knocked_out_genes) == len(MISSION22_TARGET_GENES)
        and set(knocked_out_genes) == set(MISSION22_TARGET_GENES)
    )
    disabled_reactions = _mission22_disabled_reactions(knocked_out_genes)

    run_type = None
    if environment.get('controlled_environment'):
        if not knocked_out_genes and environment.get('acetate_upper_bound_closed'):
            run_type = 'environmental_intervention'
        elif exact_target_pair and not environment.get('acetate_upper_bound_closed'):
            run_type = 'genetic_intervention'

    objective_numeric = _mission22_number_or_none(objective_result)
    result_infeasible = 'INFEASIBLE' in str(objective_result or '').upper()
    measured_production = _mission22_measured_production_values(production_fluxes)
    raw_fluxes, uptake_fluxes, secretion_fluxes = _mission22_measured_medium_values(medium_fluxes)
    diagnostics = _method_diagnostics_from_production_data(production_fluxes)
    biomass_raw = _mission22_number_or_none(_mission13_biomass_value(production_fluxes))
    primary_flux = _mission22_number_or_none(diagnostics.get('primary_objective_flux'))
    method_score = _mission22_number_or_none(diagnostics.get('method_score'))
    method_score_name = diagnostics.get('method_score_name')
    diagnostics_method = normalise_method_name(diagnostics.get('method'))
    diagnostics_objective = diagnostics.get('objective_reaction')

    if selected_fluxes is None:
        selected_fluxes = _read_selected_production_fluxes()
    selected_fluxes = list(selected_fluxes or [])

    missing_medium_fluxes = [
        reaction_id for reaction_id in MISSION22_REQUIRED_MEDIUM_FLUXES
        if reaction_id not in raw_fluxes
    ]
    missing_selected_fluxes = [
        reaction_id for reaction_id in MISSION22_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    extra_selected_fluxes = [
        reaction_id for reaction_id in selected_fluxes
        if reaction_id not in MISSION22_REQUIRED_TRACKED_FLUXES
    ]
    missing_measured_fluxes = [
        reaction_id for reaction_id in MISSION22_REQUIRED_TRACKED_FLUXES
        if reaction_id not in measured_production
    ]

    glucose_uptake = _mission22_number_or_none(uptake_fluxes.get(MISSION22_GLUCOSE_REACTION))
    oxygen_uptake = _mission22_number_or_none(uptake_fluxes.get(MISSION22_OXYGEN_REACTION))
    acetate_export = _mission22_number_or_none(measured_production.get(MISSION22_ENVIRONMENTAL_EXPORT))
    ethanol_export = _mission22_number_or_none(measured_production.get('EX_etoh_e'))
    formate_export = _mission22_number_or_none(measured_production.get('EX_for_e'))

    issues = []
    if objective_error:
        issues.append(objective_error)
    if normalise_method_name(method_name) != MISSION22_METHOD:
        issues.append('Use FBA for both Mission 22 runs.')
    if selected_objective != MISSION22_GROWTH_OBJECTIVE:
        issues.append('Use the biomass objective for both Mission 22 runs.')
    if not environment.get('bounds_complete'):
        issues.append('The environmental-bound payload is incomplete.')
    if not environment.get('oxygen_lower_bound_closed'):
        issues.append('Close the oxygen lower bound in both Mission 22 runs.')
    if environment.get('unexpected_environment_changes'):
        issues.append('Keep glucose and every unrelated environmental bound at the model default.')

    if not knocked_out_genes:
        if not environment.get('acetate_upper_bound_closed'):
            issues.append('The environmental intervention must close acetate export with every gene active.')
    elif exact_target_pair:
        if environment.get('acetate_upper_bound_closed'):
            issues.append('The genetic intervention must keep the acetate upper bound at its model default.')
        if disabled_reactions != MISSION22_EXPECTED_DISABLED_REACTIONS:
            issues.append('The b2297 + b2458 pair must disable PTAr under the complete GPR rule.')
    else:
        issues.append('Use either all genes active for the environmental run or exactly b2297 + b2458 for the genetic run.')

    if run_type not in {'environmental_intervention', 'genetic_intervention'}:
        issues.append('Use one of the two controlled Mission 22 interventions without combining them.')

    if result_infeasible or objective_numeric is None:
        issues.append('Mission 22 requires a numeric viable biomass result in both runs.')
    elif objective_numeric < MISSION22_MIN_VIABLE_GROWTH:
        issues.append('The current intervention does not retain enough predicted growth for comparison.')

    if medium_fluxes and medium_fluxes.get('error'):
        issues.append('The Exchange Flux Report is unavailable for this run.')
    elif missing_medium_fluxes:
        issues.append('The Exchange Flux Report is missing required Mission 22 reactions.')
    if production_fluxes and production_fluxes.get('error'):
        issues.append('The Production Flux report is unavailable for this run.')
    elif missing_measured_fluxes:
        issues.append('The Production Flux report is missing numeric Mission 22 values.')
    if missing_selected_fluxes or extra_selected_fluxes:
        issues.append('Select exactly the complete Mission 22 product/byproduct panel.')

    if glucose_uptake is None or oxygen_uptake is None:
        issues.append('Numeric glucose and oxygen uptake evidence is required.')
    else:
        if abs(glucose_uptake - MISSION22_EXPECTED_GLUCOSE_UPTAKE) > MISSION22_GLUCOSE_UPTAKE_TOLERANCE:
            issues.append('Keep model-default glucose uptake in both Mission 22 runs.')
        if oxygen_uptake > MISSION22_FLUX_TOLERANCE:
            issues.append('The Exchange Flux Report still detects oxygen uptake.')

    for reaction_id in MISSION22_REQUIRED_TRACKED_FLUXES:
        production_value = _mission22_number_or_none(measured_production.get(reaction_id))
        exchange_value = _mission22_number_or_none(secretion_fluxes.get(reaction_id))
        if production_value is not None and exchange_value is not None:
            if abs(production_value - exchange_value) > MISSION22_FLUX_TOLERANCE:
                issues.append('Production Flux and Exchange Flux must describe the same visible solution.')
                break

    if diagnostics_method != MISSION22_METHOD or diagnostics_objective != MISSION22_GROWTH_OBJECTIVE:
        issues.append('The visible method diagnostics do not describe the required FBA biomass result.')
    if primary_flux is None or method_score is None or biomass_raw is None:
        issues.append('The visible result is missing biomass or FBA objective diagnostics.')
    else:
        if abs(primary_flux - objective_numeric) > MISSION22_PRIMARY_TOLERANCE:
            issues.append('The displayed objective result does not match the primary biomass flux.')
        if abs(biomass_raw - objective_numeric) > MISSION22_PRIMARY_TOLERANCE:
            issues.append('The visible biomass evidence does not match the displayed result.')
        if method_score_name != 'primary_objective_flux':
            issues.append('The FBA method score is not identified as the primary objective flux.')
        if abs(method_score - primary_flux) > MISSION22_PRIMARY_TOLERANCE:
            issues.append('The FBA method score does not match the primary objective flux.')

    if acetate_export is None or ethanol_export is None or formate_export is None:
        issues.append('The visible phenotype panel is incomplete.')
    else:
        if acetate_export > MISSION22_MAX_ACETATE_EXPORT:
            issues.append('The intended intervention should suppress acetate export in this controlled phenotype.')
        if ethanol_export < MISSION22_MIN_ACTIVE_ETHANOL_EXPORT:
            issues.append('The current run does not show the expected positive ethanol secretion phenotype.')
        if formate_export < MISSION22_MIN_ACTIVE_FORMATE_EXPORT:
            issues.append('The current run does not show the expected positive formate secretion phenotype.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run = None
    if current_run_valid:
        current_run = {
            'run_type': run_type,
            'method': MISSION22_METHOD,
            'objective': selected_objective,
            'growth': _mission22_clean_number(objective_numeric),
            'glucose_uptake': _mission22_clean_number(glucose_uptake),
            'oxygen_uptake': _mission22_clean_number(oxygen_uptake),
            'tracked_flux_values': {
                reaction_id: _mission22_clean_number(measured_production[reaction_id])
                for reaction_id in MISSION22_REQUIRED_TRACKED_FLUXES
            },
            'selected_fluxes': list(selected_fluxes),
            'knocked_out_genes': list(knocked_out_genes),
            'disabled_reactions': list(disabled_reactions),
            'oxygen_lower_bound_closed': bool(environment.get('oxygen_lower_bound_closed')),
            'acetate_upper_bound_closed': bool(environment.get('acetate_upper_bound_closed')),
            'method_diagnostics': {
                'method': diagnostics_method,
                'objective_reaction': diagnostics_objective,
                'primary_objective_flux': _mission22_clean_number(primary_flux),
                'method_score': _mission22_clean_number(method_score),
                'method_score_name': method_score_name,
            },
        }
        if run_type == 'environmental_intervention':
            environmental_run = current_run
        elif run_type == 'genetic_intervention':
            genetic_run = current_run
        current_run_recorded = True

    all_runs_recorded = bool(environmental_run and genetic_run)
    missing_run_types = []
    if not environmental_run:
        missing_run_types.append('environmental_intervention')
    if not genetic_run:
        missing_run_types.append('genetic_intervention')

    same_base_protocol = bool(
        all_runs_recorded
        and environmental_run.get('method') == genetic_run.get('method') == MISSION22_METHOD
        and environmental_run.get('objective') == genetic_run.get('objective') == MISSION22_GROWTH_OBJECTIVE
        and not environmental_run.get('knocked_out_genes')
        and set(genetic_run.get('knocked_out_genes') or []) == set(MISSION22_TARGET_GENES)
        and genetic_run.get('disabled_reactions') == MISSION22_EXPECTED_DISABLED_REACTIONS
        and environmental_run.get('oxygen_lower_bound_closed')
        and genetic_run.get('oxygen_lower_bound_closed')
        and environmental_run.get('acetate_upper_bound_closed')
        and not genetic_run.get('acetate_upper_bound_closed')
        and set(environmental_run.get('selected_fluxes') or []) == set(MISSION22_REQUIRED_TRACKED_FLUXES)
        and set(genetic_run.get('selected_fluxes') or []) == set(MISSION22_REQUIRED_TRACKED_FLUXES)
    )

    phenotype_differences = {}
    different_output_ids = []
    different_output_count = None
    maximum_absolute_difference = None
    relationship_supported = False
    if all_runs_recorded:
        phenotype_differences = {
            'growth': _mission22_clean_number(
                float(genetic_run['growth']) - float(environmental_run['growth'])
            ),
            'glucose_uptake': _mission22_clean_number(
                float(genetic_run['glucose_uptake']) - float(environmental_run['glucose_uptake'])
            ),
            'oxygen_uptake': _mission22_clean_number(
                float(genetic_run['oxygen_uptake']) - float(environmental_run['oxygen_uptake'])
            ),
        }
        for reaction_id in MISSION22_REQUIRED_TRACKED_FLUXES:
            phenotype_differences[reaction_id] = _mission22_clean_number(
                float((genetic_run.get('tracked_flux_values') or {})[reaction_id])
                - float((environmental_run.get('tracked_flux_values') or {})[reaction_id])
            )
        different_output_ids = [
            output_id for output_id in MISSION22_PHENOTYPE_OUTPUTS
            if abs(float(phenotype_differences[output_id])) > MISSION22_OUTPUT_DIFFERENCE_TOLERANCE
        ]
        different_output_count = len(different_output_ids)
        maximum_absolute_difference = max(
            (abs(float(value)) for value in phenotype_differences.values()),
            default=0.0,
        )
        relationship_supported = bool(
            same_base_protocol
            and different_output_count == MISSION22_EXPECTED_DIFFERENT_OUTPUT_COUNT
            and float(environmental_run['growth']) >= MISSION22_MIN_VIABLE_GROWTH
            and float(genetic_run['growth']) >= MISSION22_MIN_VIABLE_GROWTH
            and float((environmental_run.get('tracked_flux_values') or {})['EX_etoh_e'])
            >= MISSION22_MIN_ACTIVE_ETHANOL_EXPORT
            and float((genetic_run.get('tracked_flux_values') or {})['EX_etoh_e'])
            >= MISSION22_MIN_ACTIVE_ETHANOL_EXPORT
        )

    latest_attempt = {
        'method': method_name,
        'objective': selected_objective,
        'run_type': run_type,
        'knocked_out_genes': list(knocked_out_genes),
        'objective_result': str(objective_result),
        'issues': list(issues),
        'recorded': current_run_recorded,
    }
    report = {
        'mission_id': '22',
        'check_version': MISSION22_CHECK_VERSION,
        'mission_title': 'Phenotype Equivalence Audit',
        'target_context': MISSION22_TARGET_CONTEXT,
        'target_method': MISSION22_METHOD,
        'growth_objective': MISSION22_GROWTH_OBJECTIVE,
        'oxygen_reaction': MISSION22_OXYGEN_REACTION,
        'environmental_export': MISSION22_ENVIRONMENTAL_EXPORT,
        'target_genes': list(MISSION22_TARGET_GENES),
        'expected_disabled_reactions': list(MISSION22_EXPECTED_DISABLED_REACTIONS),
        'required_tracked_fluxes': list(MISSION22_REQUIRED_TRACKED_FLUXES),
        'required_medium_fluxes': list(MISSION22_REQUIRED_MEDIUM_FLUXES),
        'environmental_intervention_run': environmental_run,
        'genetic_intervention_run': genetic_run,
        'recorded_run_count': int(isinstance(environmental_run, dict)) + int(isinstance(genetic_run, dict)),
        'required_run_count': 2,
        'missing_run_types': missing_run_types,
        'all_runs_recorded': all_runs_recorded,
        'same_base_protocol': same_base_protocol,
        'phenotype_differences': phenotype_differences,
        'different_output_ids': different_output_ids,
        'different_output_count': different_output_count,
        'maximum_absolute_difference': (
            _mission22_clean_number(maximum_absolute_difference)
            if maximum_absolute_difference is not None else None
        ),
        'relationship_supported': relationship_supported,
        'evidence_ready': all_runs_recorded,
        'answer_ready': relationship_supported,
        'ready_to_deliver': relationship_supported,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': run_type,
        'current_issues': issues,
        'current_run': current_run,
        'latest_attempt': latest_attempt,
        'output_difference_tolerance': MISSION22_OUTPUT_DIFFERENCE_TOLERANCE,
        'expected_different_output_count': MISSION22_EXPECTED_DIFFERENT_OUTPUT_COUNT,
    }
    save_mission22_comparison_check(report)
    return report


def run_mission22_comparison_check(simulation_results=None):
    """Validate the already visible Mission 22 result without re-simulating."""
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible Mission 22 simulation before recording evidence.'
    except Exception:
        objective_error = 'Could not read the current visible Mission 22 simulation result.'

    return _build_mission22_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission22_comparison_check() or {},
        objective_error=objective_error,
    )


def run_mission22_comparison_check_remote(backend_url, simulation_results=None):
    """Browser parity wrapper: validate the already visible backend result."""
    del backend_url
    return run_mission22_comparison_check(simulation_results)


def build_mission22_phenotype_equivalence_report_text(report):
    if not report:
        return 'Mission 22 Phenotype Equivalence Audit\n\nActivate the mission and record the two controlled intervention runs.'
    if report.get('mission_id') != '22' or report.get('check_version') != MISSION22_CHECK_VERSION:
        return 'Mission 22 Phenotype Equivalence Audit\n\nCurrent-format evidence has not been recorded yet.'

    lines = [
        'Mission 22 Phenotype Equivalence Audit',
        '',
        'Shared protocol:',
        '- FBA biomass objective; model-default glucose; oxygen uptake closed',
        '- Complete product/byproduct panel measured from each visible solution',
        f'- Output-difference tolerance: {MISSION22_OUTPUT_DIFFERENCE_TOLERANCE:.3f}',
        '- Counted phenotype outputs: biomass, glucose uptake, oxygen uptake and the five tracked secretions',
        '- Intervention settings and GPR labels describe mechanisms; they are not counted phenotype outputs',
        '- Environmental intervention: all genes active; acetate export upper bound closed',
        '- Genetic intervention: acetate export bound default; b2297 + b2458 disabled',
        '- Complete GPR check required: PTAr disabled only in the genetic intervention',
        '',
        f"Controlled runs recorded: {report.get('recorded_run_count', 0)}/{report.get('required_run_count', 2)}",
    ]

    for title, key in (
        ('Environmental intervention', 'environmental_intervention_run'),
        ('Genetic intervention', 'genetic_intervention_run'),
    ):
        run = report.get(key) or {}
        if not run:
            lines.append(f'- {title}: not recorded')
            continue
        lines.extend([
            f'{title}:',
            f"- Growth: {float(run.get('growth')):.3f}",
            f"- Glucose uptake: {float(run.get('glucose_uptake')):.3f}",
            f"- Oxygen uptake: {float(run.get('oxygen_uptake')):.3f}",
            f"- Knockouts: {', '.join(run.get('knocked_out_genes') or []) or 'none'}",
            f"- GPR-disabled reactions: {', '.join(run.get('disabled_reactions') or []) or 'none'}",
            '- Export profile:',
        ])
        fluxes = run.get('tracked_flux_values') or {}
        for reaction_id in MISSION22_REQUIRED_TRACKED_FLUXES:
            lines.append(
                f"  {MISSION22_FLUX_NAMES.get(reaction_id, reaction_id)} ({reaction_id}): "
                f"{float(fluxes.get(reaction_id)):.3f}"
            )
        lines.append('')

    if report.get('all_runs_recorded'):
        lines.append('Genetic minus environmental phenotype differences:')
        differences = report.get('phenotype_differences') or {}
        for output_id in MISSION22_PHENOTYPE_OUTPUTS:
            if output_id not in differences:
                continue
            value = float(differences[output_id])
            prefix = '+' if value > 0 else ''
            lines.append(f"- {MISSION22_OUTPUT_NAMES.get(output_id, output_id)}: {prefix}{value:.3f}")
    else:
        missing = report.get('missing_run_types') or []
        if missing:
            lines.append('Missing controlled runs: ' + ', '.join(missing) + '.')

    if report.get('current_run_recorded'):
        lines.extend(['', f"Latest valid visible run recorded: {str(report.get('current_run_type') or '').replace('_', ' ')}."])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if report.get('environmental_intervention_run') or report.get('genetic_intervention_run'):
            lines.append('Previously valid Mission 22 evidence remains available.')

    lines.append('')
    if report.get('evidence_ready'):
        lines.extend([
            'Evidence complete.',
            'Inspect every recorded output difference and report how many exceed the stated numerical tolerance.',
            'Question: How many recorded phenotype outputs differed beyond tolerance between the two interventions?',
        ])
    else:
        lines.append('Evidence incomplete.')

    lines.extend([
        '',
        'Interpretation note: equal observed outputs do not prove equal intervention mechanisms.',
        'This comparison is conditional on this model, anaerobic glucose medium, biomass objective and recorded phenotype panel.',
        'All growth and exchange values come from the same visible solver results. No hidden simulation is used.',
    ])
    return '\n'.join(lines)


def is_mission23_unlocked(missions_completed):
    """Mission 23 begins only after Dr. Vega's final mission."""
    return '22' in (missions_completed or [])


def _mission23_clean_number(value):
    numeric = float(value)
    if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
        numeric = 0.0
    return round(numeric, 6)


def _mission23_number_or_none(value):
    numeric = _as_float_or_none(value)
    return _mission23_clean_number(numeric) if numeric is not None else None


def _mission23_base_environment_status(reactions):
    """Require a complete model-default environment without relying on key order."""
    reactions = reactions or {}
    bounds_complete = True
    unexpected_changes = []
    for index in range(len(REACTIONS.index)):
        reaction_id = REACTIONS.index[index]
        lower_open, upper_open = _reaction_bound_open_states(reactions, index)
        if lower_open is None or upper_open is None:
            bounds_complete = False
            continue
        default_lower_open = REACTIONS.lb.iloc[index] != 0
        default_upper_open = REACTIONS.ub.iloc[index] != 0
        if lower_open != default_lower_open:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_open != default_upper_open:
            unexpected_changes.append(f'{reaction_id} upper bound')
    return {
        'bounds_complete': bounds_complete,
        'unexpected_environment_changes': unexpected_changes,
        'environment_default': bool(bounds_complete and not unexpected_changes),
    }


def _mission23_empty_report():
    return {
        'mission_id': '23',
        'check_version': MISSION23_CHECK_VERSION,
        'mission_title': 'Nutrient Sensitivity Curve',
        'target_context': MISSION23_TARGET_CONTEXT,
        'target_method': MISSION23_METHOD,
        'growth_objective': MISSION23_GROWTH_OBJECTIVE,
        'sweep_reaction': MISSION23_SWEEP_REACTION,
        'sweep_bound': MISSION23_SWEEP_BOUND,
        'required_bound_values': list(MISSION23_SWEEP_VALUES),
        'required_tracked_fluxes': list(MISSION23_REQUIRED_TRACKED_FLUXES),
        'required_medium_fluxes': list(MISSION23_REQUIRED_MEDIUM_FLUXES),
        'sweep_data': None,
        'sweep_rows': [],
        'recorded_bound_values': [],
        'recorded_point_count': 0,
        'required_point_count': len(MISSION23_SWEEP_VALUES),
        'missing_bound_values': list(MISSION23_SWEEP_VALUES),
        'all_points_recorded': False,
        'nonlimiting_reference': None,
        'first_limiting_point': None,
        'growth_trend': False,
        'ammonium_uptake_trend': False,
        'tracked_flux_trends': {},
        'new_secretion_candidates': [],
        'relationship_supported': False,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_sweep_valid': False,
        'current_sweep_recorded': False,
        'current_issues': [],
        'latest_attempt': None,
    }


def initialise_mission23_nutrient_sensitivity_curve():
    report = _mission23_empty_report()
    save_mission23_comparison_check(report)
    return report


def _mission23_value_key(value):
    numeric = _as_float_or_none(value)
    return round(float(numeric), 6) if numeric is not None else None


def _mission23_row_map(rows):
    mapped = {}
    for row in rows or []:
        key = _mission23_value_key(row.get('bound_value'))
        if key is not None:
            mapped[key] = row
    return mapped


def _mission23_complete_numeric_mapping(mapping, required_ids):
    if not isinstance(mapping, dict):
        return False
    return all(_as_float_or_none(mapping.get(reaction_id)) is not None for reaction_id in required_ids)


def _mission23_validate_sweep(sweep_data):
    """Validate one visible bound-sweep result and return normalised rows/issues."""
    issues = []
    if not isinstance(sweep_data, dict) or not sweep_data:
        return False, [], ['Run the Mission 23 Bound Sweep before recording evidence.']
    if sweep_data.get('error'):
        issues.append(str(sweep_data.get('error')))

    if sweep_data.get('method') != MISSION23_METHOD:
        issues.append('Use pFBA for the Mission 23 sensitivity sweep.')
    if sweep_data.get('objective') != MISSION23_GROWTH_OBJECTIVE:
        issues.append('Use the biomass objective for the Mission 23 sensitivity sweep.')
    if sweep_data.get('knocked_out_genes'):
        issues.append('Keep every gene active during the Mission 23 sensitivity sweep.')

    environment = _mission23_base_environment_status(sweep_data.get('base_reactions') or {})
    if not environment['bounds_complete']:
        issues.append('The explicit environmental-bound payload is incomplete.')
    elif not environment['environment_default']:
        issues.append('Keep every base environmental bound at the model default before the sweep.')

    if sweep_data.get('reaction_id') != MISSION23_SWEEP_REACTION or sweep_data.get('bound') != MISSION23_SWEEP_BOUND:
        issues.append('Sweep only the lower bound of EX_nh4_e.')

    got_values = [_mission23_value_key(value) for value in (sweep_data.get('values') or [])]
    expected_values = [_mission23_value_key(value) for value in MISSION23_SWEEP_VALUES]
    if sorted(value for value in got_values if value is not None) != sorted(expected_values):
        issues.append('Use the four required ammonium lower-bound values: -5, -4, -2 and -1.')

    selected_fluxes = set(sweep_data.get('selected_production_fluxes') or [])
    missing_selected = [
        reaction_id for reaction_id in MISSION23_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    if missing_selected:
        issues.append('Select EX_ac_e and EX_co2_e in Production Flux before running the sweep.')

    rows_by_value = _mission23_row_map(sweep_data.get('rows') or [])
    normalised_rows = []
    for bound_value in MISSION23_SWEEP_VALUES:
        key = _mission23_value_key(bound_value)
        row = rows_by_value.get(key)
        if not isinstance(row, dict):
            issues.append(f'Missing the visible sweep row for ammonium lower bound {bound_value:g}.')
            continue
        if row.get('status') != 'ok':
            issues.append(f'The sweep row at ammonium lower bound {bound_value:g} did not return an optimal measurable result.')
            continue

        growth = _mission23_number_or_none(row.get('growth_value'))
        raw_fluxes = row.get('exchange_raw_fluxes') or {}
        tracked = row.get('tracked_flux_values') or {}
        diagnostics = row.get('method_diagnostics') or {}
        if growth is None:
            issues.append(f'Biomass is missing from the row at ammonium lower bound {bound_value:g}.')
        if not _mission23_complete_numeric_mapping(raw_fluxes, MISSION23_REQUIRED_MEDIUM_FLUXES):
            issues.append(f'The Exchange Flux evidence is incomplete at ammonium lower bound {bound_value:g}.')
        if not _mission23_complete_numeric_mapping(tracked, MISSION23_REQUIRED_TRACKED_FLUXES):
            issues.append(f'The Production Flux evidence is incomplete at ammonium lower bound {bound_value:g}.')

        primary = _mission23_number_or_none(diagnostics.get('primary_objective_flux'))
        method_score = _mission23_number_or_none(diagnostics.get('method_score'))
        total_absolute_flux = _mission23_number_or_none(diagnostics.get('total_absolute_flux'))
        active_reactions = diagnostics.get('active_reaction_count')
        if diagnostics.get('method') != MISSION23_METHOD:
            issues.append(f'The visible method diagnostics do not describe pFBA at ammonium lower bound {bound_value:g}.')
        if diagnostics.get('objective_reaction') != MISSION23_GROWTH_OBJECTIVE:
            issues.append(f'The visible method diagnostics use the wrong objective at ammonium lower bound {bound_value:g}.')
        if diagnostics.get('method_score_name') != MISSION23_EXPECTED_SECONDARY_CRITERION:
            issues.append(f'The pFBA secondary criterion is missing at ammonium lower bound {bound_value:g}.')
        if primary is None or growth is None or abs(float(primary) - float(growth)) > MISSION23_PRIMARY_TOLERANCE:
            issues.append(f'The pFBA primary objective flux does not match biomass at ammonium lower bound {bound_value:g}.')
        if method_score is None or total_absolute_flux is None:
            issues.append(f'The pFBA total-flux diagnostic is missing at ammonium lower bound {bound_value:g}.')
        elif abs(float(method_score) - float(total_absolute_flux)) > MISSION23_FLUX_TOLERANCE:
            issues.append(f'The pFBA method score does not match total absolute flux at ammonium lower bound {bound_value:g}.')
        try:
            active_reactions = int(active_reactions)
        except Exception:
            active_reactions = None
            issues.append(f'The active-reaction count is missing at ammonium lower bound {bound_value:g}.')

        if growth is not None and _mission23_complete_numeric_mapping(raw_fluxes, MISSION23_REQUIRED_MEDIUM_FLUXES) and _mission23_complete_numeric_mapping(tracked, MISSION23_REQUIRED_TRACKED_FLUXES):
            clean_raw = {
                reaction_id: _mission23_clean_number(raw_fluxes[reaction_id])
                for reaction_id in MISSION23_REQUIRED_MEDIUM_FLUXES
            }
            clean_tracked = {
                reaction_id: _mission23_clean_number(tracked[reaction_id])
                for reaction_id in MISSION23_REQUIRED_TRACKED_FLUXES
            }
            normalised_rows.append({
                'bound_value': float(bound_value),
                'status': 'ok',
                'growth_value': _mission23_clean_number(growth),
                'ammonium_raw_flux': clean_raw[MISSION23_SWEEP_REACTION],
                'ammonium_uptake': _mission23_clean_number(max(-clean_raw[MISSION23_SWEEP_REACTION], 0.0)),
                'glucose_uptake': _mission23_clean_number(max(-clean_raw['EX_glc__D_e'], 0.0)),
                'oxygen_uptake': _mission23_clean_number(max(-clean_raw['EX_o2_e'], 0.0)),
                'phosphate_uptake': _mission23_clean_number(max(-clean_raw['EX_pi_e'], 0.0)),
                'exchange_raw_fluxes': clean_raw,
                'tracked_flux_values': clean_tracked,
                'method_diagnostics': {
                    'method': diagnostics.get('method'),
                    'objective_reaction': diagnostics.get('objective_reaction'),
                    'primary_objective_flux': primary,
                    'method_score': method_score,
                    'method_score_name': diagnostics.get('method_score_name'),
                    'total_absolute_flux': total_absolute_flux,
                    'active_reaction_count': active_reactions,
                },
            })

    valid = not issues and len(normalised_rows) == len(MISSION23_SWEEP_VALUES)
    return valid, normalised_rows, issues


def _mission23_derive_relationship(rows):
    rows_by_value = _mission23_row_map(rows)
    reference = rows_by_value.get(_mission23_value_key(MISSION23_SWEEP_VALUES[0]))
    first_limiting = rows_by_value.get(_mission23_value_key(MISSION23_SWEEP_VALUES[1]))
    ordered = [rows_by_value.get(_mission23_value_key(value)) for value in MISSION23_SWEEP_VALUES]
    ordered = [row for row in ordered if row]

    growth_values = [float(row['growth_value']) for row in ordered]
    ammonium_values = [float(row['ammonium_uptake']) for row in ordered]
    growth_trend = bool(
        len(growth_values) == len(MISSION23_SWEEP_VALUES)
        and all(after < before - MISSION23_MONOTONIC_TOLERANCE for before, after in zip(growth_values, growth_values[1:]))
    )
    ammonium_uptake_trend = bool(
        len(ammonium_values) == len(MISSION23_SWEEP_VALUES)
        and all(after < before - MISSION23_MONOTONIC_TOLERANCE for before, after in zip(ammonium_values, ammonium_values[1:]))
    )

    tracked_flux_trends = {
        reaction_id: [
            _mission23_clean_number((row.get('tracked_flux_values') or {}).get(reaction_id, 0.0))
            for row in ordered
        ]
        for reaction_id in MISSION23_REQUIRED_TRACKED_FLUXES
    }
    new_candidates = []
    if reference and first_limiting:
        for reaction_id in MISSION23_REQUIRED_TRACKED_FLUXES:
            reference_value = float((reference.get('tracked_flux_values') or {}).get(reaction_id, 0.0))
            limiting_value = float((first_limiting.get('tracked_flux_values') or {}).get(reaction_id, 0.0))
            if reference_value <= MISSION23_MAX_REFERENCE_ACETATE and limiting_value >= MISSION23_MIN_LIMITING_ACETATE:
                new_candidates.append(reaction_id)

    relationship_supported = bool(
        reference
        and first_limiting
        and float(reference['growth_value']) >= MISSION23_MIN_REFERENCE_GROWTH
        and float(first_limiting['growth_value']) <= float(reference['growth_value']) - MISSION23_MIN_GROWTH_CHANGE
        and growth_trend
        and ammonium_uptake_trend
        and new_candidates == [MISSION23_EXPECTED_NEW_SECRETION]
    )
    return {
        'nonlimiting_reference': reference,
        'first_limiting_point': first_limiting,
        'growth_trend': growth_trend,
        'ammonium_uptake_trend': ammonium_uptake_trend,
        'tracked_flux_trends': tracked_flux_trends,
        'new_secretion_candidates': new_candidates,
        'relationship_supported': relationship_supported,
    }


def _build_mission23_data(sweep_data=None, existing_report=None):
    existing_report = existing_report if isinstance(existing_report, dict) else {}
    if existing_report.get('mission_id') != '23' or existing_report.get('check_version') != MISSION23_CHECK_VERSION:
        existing_report = _mission23_empty_report()

    current_valid, current_rows, issues = _mission23_validate_sweep(sweep_data)
    retained_sweep = copy.deepcopy(existing_report.get('sweep_data')) if existing_report.get('evidence_ready') else None
    retained_rows = copy.deepcopy(existing_report.get('sweep_rows') or []) if retained_sweep else []
    current_recorded = False
    if current_valid:
        retained_sweep = copy.deepcopy(sweep_data)
        retained_rows = current_rows
        current_recorded = True

    relation = _mission23_derive_relationship(retained_rows) if retained_rows else {
        'nonlimiting_reference': None,
        'first_limiting_point': None,
        'growth_trend': False,
        'ammonium_uptake_trend': False,
        'tracked_flux_trends': {},
        'new_secretion_candidates': [],
        'relationship_supported': False,
    }
    recorded_values = [float(row['bound_value']) for row in retained_rows]
    expected_keys = {_mission23_value_key(value) for value in MISSION23_SWEEP_VALUES}
    recorded_keys = {_mission23_value_key(value) for value in recorded_values}
    missing_values = [value for value in MISSION23_SWEEP_VALUES if _mission23_value_key(value) not in recorded_keys]
    all_points = bool(recorded_keys == expected_keys and len(retained_rows) == len(MISSION23_SWEEP_VALUES))
    evidence_ready = bool(all_points and retained_sweep)
    relationship_supported = bool(evidence_ready and relation['relationship_supported'])

    latest_attempt = {
        'method': (sweep_data or {}).get('method') if isinstance(sweep_data, dict) else None,
        'objective': (sweep_data or {}).get('objective') if isinstance(sweep_data, dict) else None,
        'reaction_id': (sweep_data or {}).get('reaction_id') if isinstance(sweep_data, dict) else None,
        'bound': (sweep_data or {}).get('bound') if isinstance(sweep_data, dict) else None,
        'values': list((sweep_data or {}).get('values') or []) if isinstance(sweep_data, dict) else [],
        'issues': list(issues),
        'recorded': current_recorded,
    }
    report = _mission23_empty_report()
    report.update({
        'sweep_data': retained_sweep,
        'sweep_rows': retained_rows,
        'recorded_bound_values': recorded_values,
        'recorded_point_count': len(retained_rows),
        'missing_bound_values': missing_values,
        'all_points_recorded': all_points,
        **relation,
        'relationship_supported': relationship_supported,
        'evidence_ready': evidence_ready,
        'answer_ready': relationship_supported,
        'ready_to_deliver': relationship_supported,
        'current_sweep_valid': current_valid,
        'current_sweep_recorded': current_recorded,
        'current_issues': list(issues),
        'latest_attempt': latest_attempt,
    })
    save_mission23_comparison_check(report)
    return report


def run_mission23_sensitivity_check(sweep_data=None):
    """Validate the visible sweep table; never invoke the solver from the validator."""
    if sweep_data is None:
        sweep_data = load_bound_sweep()
    return _build_mission23_data(
        sweep_data=sweep_data,
        existing_report=load_mission23_comparison_check() or {},
    )


def run_mission23_sensitivity_check_remote(backend_url, sweep_data=None):
    """Browser parity wrapper for the already visible remote sweep result."""
    del backend_url
    return run_mission23_sensitivity_check(sweep_data)


def _mission23_answer_mentions(answer):
    text = unicodedata.normalize('NFKD', str(answer or '')).encode('ascii', 'ignore').decode('ascii').lower()
    mentions = set()
    patterns = {
        'EX_ac_e': [r'\bex[_\s-]*ac[_\s-]*e\b', r'\bacetate\b', r'\bacetato\b', r'\bacetic acid\b'],
        'EX_co2_e': [r'\bex[_\s-]*co2[_\s-]*e\b', r'\bco2\b', r'\bcarbon dioxide\b', r'\bdioxido(?: de)? carbono\b'],
    }
    for reaction_id, aliases in patterns.items():
        if any(re.search(pattern, text) for pattern in aliases):
            mentions.add(reaction_id)
    return mentions


def normalise_mission23_answer(answer):
    mentions = _mission23_answer_mentions(answer)
    return next(iter(mentions)) if len(mentions) == 1 else None


def mission23_answer_matches(answer, report_data=None):
    report_data = report_data if report_data is not None else (load_mission23_comparison_check() or {})
    return bool(
        report_data.get('mission_id') == '23'
        and report_data.get('check_version') == MISSION23_CHECK_VERSION
        and report_data.get('answer_ready')
        and normalise_mission23_answer(answer) == MISSION23_EXPECTED_NEW_SECRETION
    )


def build_mission23_nutrient_sensitivity_report_text(report):
    if not report:
        return (
            'Prepare a controlled four-point sensitivity experiment before activation. '
            'Keep the model, biomass objective, genes and every unrelated environmental bound unchanged while varying only ammonium uptake capacity.\n\n'
            'The visible sweep must combine growth, exchange evidence, the selected secretion panel and pFBA diagnostics so that the onset of nutrient limitation can be identified from the recorded curve.\n\n'
            'Activate the mission when you are ready to configure the Bound Sweep. Use the briefing for the exact controlled protocol and the optional hints for interpreting a lower-bound response curve.'
        )
    if report.get('mission_id') != '23' or report.get('check_version') != MISSION23_CHECK_VERSION:
        return 'Mission 23 Nutrient Sensitivity Curve\n\nCurrent-format sensitivity evidence has not been recorded yet.'

    lines = [
        'Mission 23 Nutrient Sensitivity Curve',
        '',
        'Controlled sweep protocol:',
        '- pFBA biomass objective; all genes active',
        '- Model-default environment before the sweep',
        '- Only the EX_nh4_e lower bound changes: -5, -4, -2, -1',
        '- Production Flux panel: EX_ac_e and EX_co2_e',
        '- Exchange evidence: EX_nh4_e, EX_glc__D_e, EX_o2_e and EX_pi_e',
        '- Every row includes the pFBA primary flux and total-absolute-flux diagnostic',
        '',
        f"Sweep points recorded: {report.get('recorded_point_count', 0)}/{report.get('required_point_count', len(MISSION23_SWEEP_VALUES))}",
    ]
    rows = report.get('sweep_rows') or []
    if rows:
        lines.extend([
            'LB | growth | NH4 uptake | glucose uptake | oxygen uptake | acetate | CO2 | total abs flux | active reactions',
        ])
        for row in rows:
            tracked = row.get('tracked_flux_values') or {}
            diagnostics = row.get('method_diagnostics') or {}
            lines.append(
                f"{float(row.get('bound_value')):.0f} | "
                f"{float(row.get('growth_value')):.3f} | "
                f"{float(row.get('ammonium_uptake')):.3f} | "
                f"{float(row.get('glucose_uptake')):.3f} | "
                f"{float(row.get('oxygen_uptake')):.3f} | "
                f"{float(tracked.get('EX_ac_e')):.3f} | "
                f"{float(tracked.get('EX_co2_e')):.3f} | "
                f"{float(diagnostics.get('total_absolute_flux')):.3f} | "
                f"{int(diagnostics.get('active_reaction_count'))}"
            )
    else:
        lines.append('No current-format sweep rows recorded.')

    if report.get('missing_bound_values'):
        lines.append('Missing bound values: ' + ', '.join(f'{float(value):g}' for value in report.get('missing_bound_values') or []))

    if report.get('current_sweep_recorded'):
        lines.extend(['', 'Latest valid visible Bound Sweep recorded.'])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest sweep was not recorded:'])
        lines.extend(f"- {issue}" for issue in report.get('current_issues') or [])
        if report.get('evidence_ready'):
            lines.append('Previously valid Mission 23 evidence remains available.')

    lines.append('')
    if report.get('evidence_ready'):
        lines.extend([
            'Evidence complete.',
            'Compare the non-limiting row with the first row where ammonium limits growth.',
            'Question: Which tracked secretion was absent at the non-limiting point but became active when ammonium first became limiting?',
        ])
    else:
        lines.append('Evidence incomplete.')

    lines.extend([
        '',
        'Interpretation note: a lower bound sets uptake capacity; the realised uptake may be smaller when the bound is not limiting.',
        'A secretion that appears during this sweep is a conditional prediction of this model, medium, objective and ammonium protocol, not a universal experimental rule.',
        'All growth, exchange, production and pFBA diagnostic values come from the visible Bound Sweep results. No hidden validation simulation is used.',
    ])
    return '\n'.join(lines)


# Backwards-compatible name retained for older window imports.  It now validates
# the redesigned sensitivity sweep rather than the removed objective comparison.
def run_mission23_comparison_check(sweep_data=None):
    return run_mission23_sensitivity_check(sweep_data)


def is_mission24_unlocked(missions_completed):
    """Mission 24 is Dr. Luna's final task and follows Mission 23."""
    return '23' in (missions_completed or [])


def _mission24_clean_number(value):
    numeric = float(value)
    if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
        numeric = 0.0
    return round(numeric, 6)


def _mission24_number_or_none(value):
    numeric = _as_float_or_none(value)
    return _mission24_clean_number(numeric) if numeric is not None else None


def _mission24_value_key(value):
    numeric = _as_float_or_none(value)
    return round(float(numeric), 6) if numeric is not None else None


def _mission24_row_map(rows):
    mapped = {}
    for row in rows or []:
        key = _mission24_value_key(row.get('bound_value'))
        if key is not None:
            mapped[key] = row
    return mapped


def _mission24_complete_numeric_mapping(mapping, required_ids):
    if not isinstance(mapping, dict):
        return False
    return all(_as_float_or_none(mapping.get(reaction_id)) is not None for reaction_id in required_ids)


def _mission24_base_environment_status(reactions):
    """Require every base bound to match the model default, independent of key order."""
    reactions = reactions or {}
    bounds_complete = True
    unexpected_changes = []
    for index in range(len(REACTIONS.index)):
        reaction_id = REACTIONS.index[index]
        lower_open, upper_open = _reaction_bound_open_states(reactions, index)
        if lower_open is None or upper_open is None:
            bounds_complete = False
            continue
        default_lower_open = REACTIONS.lb.iloc[index] != 0
        default_upper_open = REACTIONS.ub.iloc[index] != 0
        if lower_open != default_lower_open:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_open != default_upper_open:
            unexpected_changes.append(f'{reaction_id} upper bound')
    return {
        'bounds_complete': bounds_complete,
        'unexpected_environment_changes': unexpected_changes,
        'environment_default': bool(bounds_complete and not unexpected_changes),
    }


def _mission24_empty_report():
    return {
        'mission_id': '24',
        'check_version': MISSION24_CHECK_VERSION,
        'mission_title': 'Export Capacity Thresholds',
        'target_context': MISSION24_TARGET_CONTEXT,
        'target_method': MISSION24_METHOD,
        'growth_objective': MISSION24_GROWTH_OBJECTIVE,
        'sweep_reaction': MISSION24_SWEEP_REACTION,
        'sweep_bound': MISSION24_SWEEP_BOUND,
        'required_bound_values': list(MISSION24_SWEEP_VALUES),
        'required_tracked_fluxes': list(MISSION24_REQUIRED_TRACKED_FLUXES),
        'required_medium_fluxes': list(MISSION24_REQUIRED_MEDIUM_FLUXES),
        'sweep_data': None,
        'sweep_rows': [],
        'recorded_bound_values': [],
        'recorded_point_count': 0,
        'required_point_count': len(MISSION24_SWEEP_VALUES),
        'missing_bound_values': list(MISSION24_SWEEP_VALUES),
        'all_points_recorded': False,
        'nonbinding_reference': None,
        'first_binding_point': None,
        'later_compensation_point': None,
        'tightest_point': None,
        'growth_trend': False,
        'co2_export_trend': False,
        'oxygen_uptake_trend': False,
        'tracked_flux_trends': {},
        'first_compensatory_candidates': [],
        'formate_onset': False,
        'acetate_onset': False,
        'relationship_supported': False,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_sweep_valid': False,
        'current_sweep_recorded': False,
        'current_issues': [],
        'latest_attempt': None,
    }


def initialise_mission24_export_capacity_thresholds():
    report = _mission24_empty_report()
    save_mission24_comparison_check(report)
    return report


def _mission24_validate_sweep(sweep_data):
    """Validate one visible CO2 upper-bound sweep and normalise its four rows."""
    issues = []
    if not isinstance(sweep_data, dict) or not sweep_data:
        return False, [], ['Run the Mission 24 Bound Sweep before recording evidence.']
    if sweep_data.get('error'):
        issues.append(str(sweep_data.get('error')))

    if sweep_data.get('method') != MISSION24_METHOD:
        issues.append('Use pFBA for the Mission 24 export-capacity sweep.')
    if sweep_data.get('objective') != MISSION24_GROWTH_OBJECTIVE:
        issues.append('Use the biomass objective for the Mission 24 export-capacity sweep.')
    if sweep_data.get('knocked_out_genes'):
        issues.append('Keep every gene active during the Mission 24 export-capacity sweep.')

    environment = _mission24_base_environment_status(sweep_data.get('base_reactions') or {})
    if not environment['bounds_complete']:
        issues.append('The explicit environmental-bound payload is incomplete.')
    elif not environment['environment_default']:
        issues.append('Keep every base environmental bound at the model default before the sweep.')

    if sweep_data.get('reaction_id') != MISSION24_SWEEP_REACTION or sweep_data.get('bound') != MISSION24_SWEEP_BOUND:
        issues.append('Sweep only the upper bound of EX_co2_e.')

    got_values = [_mission24_value_key(value) for value in (sweep_data.get('values') or [])]
    expected_values = [_mission24_value_key(value) for value in MISSION24_SWEEP_VALUES]
    if sorted(value for value in got_values if value is not None) != sorted(expected_values):
        issues.append('Use the four required CO2 upper-bound values: 25, 20, 10 and 0.')

    selected_fluxes = set(sweep_data.get('selected_production_fluxes') or [])
    missing_selected = [
        reaction_id for reaction_id in MISSION24_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    if missing_selected:
        issues.append('Select EX_co2_e, EX_for_e and EX_ac_e in Production Flux before running the sweep.')

    rows_by_value = _mission24_row_map(sweep_data.get('rows') or [])
    normalised_rows = []
    for bound_value in MISSION24_SWEEP_VALUES:
        key = _mission24_value_key(bound_value)
        row = rows_by_value.get(key)
        if not isinstance(row, dict):
            issues.append(f'Missing the visible sweep row for CO2 upper bound {bound_value:g}.')
            continue
        if row.get('status') != 'ok':
            issues.append(f'The sweep row at CO2 upper bound {bound_value:g} did not return an optimal measurable result.')
            continue

        growth = _mission24_number_or_none(row.get('growth_value'))
        raw_fluxes = row.get('exchange_raw_fluxes') or {}
        tracked = row.get('tracked_flux_values') or {}
        diagnostics = row.get('method_diagnostics') or {}
        if growth is None:
            issues.append(f'Biomass is missing from the row at CO2 upper bound {bound_value:g}.')
        if not _mission24_complete_numeric_mapping(raw_fluxes, MISSION24_REQUIRED_MEDIUM_FLUXES):
            issues.append(f'The Exchange Flux evidence is incomplete at CO2 upper bound {bound_value:g}.')
        if not _mission24_complete_numeric_mapping(tracked, MISSION24_REQUIRED_TRACKED_FLUXES):
            issues.append(f'The Production Flux evidence is incomplete at CO2 upper bound {bound_value:g}.')

        primary = _mission24_number_or_none(diagnostics.get('primary_objective_flux'))
        method_score = _mission24_number_or_none(diagnostics.get('method_score'))
        total_absolute_flux = _mission24_number_or_none(diagnostics.get('total_absolute_flux'))
        active_reactions = diagnostics.get('active_reaction_count')
        if diagnostics.get('method') != MISSION24_METHOD:
            issues.append(f'The visible method diagnostics do not describe pFBA at CO2 upper bound {bound_value:g}.')
        if diagnostics.get('objective_reaction') != MISSION24_GROWTH_OBJECTIVE:
            issues.append(f'The visible method diagnostics use the wrong objective at CO2 upper bound {bound_value:g}.')
        if diagnostics.get('method_score_name') != MISSION24_EXPECTED_SECONDARY_CRITERION:
            issues.append(f'The pFBA secondary criterion is missing at CO2 upper bound {bound_value:g}.')
        if primary is None or growth is None or abs(float(primary) - float(growth)) > MISSION24_PRIMARY_TOLERANCE:
            issues.append(f'The pFBA primary objective flux does not match biomass at CO2 upper bound {bound_value:g}.')
        if method_score is None or total_absolute_flux is None:
            issues.append(f'The pFBA total-flux diagnostic is missing at CO2 upper bound {bound_value:g}.')
        elif abs(float(method_score) - float(total_absolute_flux)) > MISSION24_FLUX_TOLERANCE:
            issues.append(f'The pFBA method score does not match total absolute flux at CO2 upper bound {bound_value:g}.')
        try:
            active_reactions = int(active_reactions)
        except Exception:
            active_reactions = None
            issues.append(f'The active-reaction count is missing at CO2 upper bound {bound_value:g}.')

        if (
            growth is not None
            and _mission24_complete_numeric_mapping(raw_fluxes, MISSION24_REQUIRED_MEDIUM_FLUXES)
            and _mission24_complete_numeric_mapping(tracked, MISSION24_REQUIRED_TRACKED_FLUXES)
        ):
            clean_raw = {
                reaction_id: _mission24_clean_number(raw_fluxes[reaction_id])
                for reaction_id in MISSION24_REQUIRED_MEDIUM_FLUXES
            }
            clean_tracked = {
                reaction_id: _mission24_clean_number(tracked[reaction_id])
                for reaction_id in MISSION24_REQUIRED_TRACKED_FLUXES
            }
            co2_export = clean_tracked[MISSION24_SWEEP_REACTION]
            raw_co2 = _mission24_number_or_none((row.get('exchange_raw_fluxes') or {}).get(MISSION24_SWEEP_REACTION))
            if raw_co2 is None:
                issues.append(f'The signed CO2 exchange flux is missing at CO2 upper bound {bound_value:g}.')
            elif abs(float(raw_co2) - float(co2_export)) > MISSION24_FLUX_TOLERANCE:
                issues.append(f'The tracked CO2 export does not match the signed exchange flux at CO2 upper bound {bound_value:g}.')
            if co2_export > float(bound_value) + MISSION24_BOUND_TOLERANCE:
                issues.append(f'The CO2 export exceeds its configured upper bound at {bound_value:g}.')

            normalised_rows.append({
                'bound_value': float(bound_value),
                'status': 'ok',
                'growth_value': _mission24_clean_number(growth),
                'glucose_uptake': _mission24_clean_number(max(-clean_raw['EX_glc__D_e'], 0.0)),
                'oxygen_uptake': _mission24_clean_number(max(-clean_raw['EX_o2_e'], 0.0)),
                'exchange_raw_fluxes': clean_raw,
                'tracked_flux_values': clean_tracked,
                'method_diagnostics': {
                    'method': diagnostics.get('method'),
                    'objective_reaction': diagnostics.get('objective_reaction'),
                    'primary_objective_flux': primary,
                    'method_score': method_score,
                    'method_score_name': diagnostics.get('method_score_name'),
                    'total_absolute_flux': total_absolute_flux,
                    'active_reaction_count': active_reactions,
                },
            })

    valid = not issues and len(normalised_rows) == len(MISSION24_SWEEP_VALUES)
    return valid, normalised_rows, issues


def _mission24_derive_relationship(rows):
    rows_by_value = _mission24_row_map(rows)
    reference = rows_by_value.get(_mission24_value_key(25.0))
    first_binding = rows_by_value.get(_mission24_value_key(20.0))
    later = rows_by_value.get(_mission24_value_key(10.0))
    tightest = rows_by_value.get(_mission24_value_key(0.0))
    ordered = [rows_by_value.get(_mission24_value_key(value)) for value in MISSION24_SWEEP_VALUES]
    ordered = [row for row in ordered if row]

    growth_values = [float(row['growth_value']) for row in ordered]
    oxygen_values = [float(row['oxygen_uptake']) for row in ordered]
    co2_values = [float((row.get('tracked_flux_values') or {}).get('EX_co2_e', 0.0)) for row in ordered]
    growth_trend = bool(
        len(growth_values) == len(MISSION24_SWEEP_VALUES)
        and all(after < before - MISSION24_MONOTONIC_TOLERANCE for before, after in zip(growth_values, growth_values[1:]))
    )
    oxygen_uptake_trend = bool(
        len(oxygen_values) == len(MISSION24_SWEEP_VALUES)
        and all(after < before - MISSION24_MONOTONIC_TOLERANCE for before, after in zip(oxygen_values, oxygen_values[1:]))
    )
    co2_export_trend = bool(
        len(co2_values) == len(MISSION24_SWEEP_VALUES)
        and all(after < before - MISSION24_MONOTONIC_TOLERANCE for before, after in zip(co2_values, co2_values[1:]))
    )
    tracked_flux_trends = {
        reaction_id: [
            _mission24_clean_number((row.get('tracked_flux_values') or {}).get(reaction_id, 0.0))
            for row in ordered
        ]
        for reaction_id in MISSION24_REQUIRED_TRACKED_FLUXES
    }

    first_candidates = []
    if reference and first_binding:
        for reaction_id in ('EX_for_e', 'EX_ac_e'):
            reference_value = float((reference.get('tracked_flux_values') or {}).get(reaction_id, 0.0))
            first_value = float((first_binding.get('tracked_flux_values') or {}).get(reaction_id, 0.0))
            if reference_value <= MISSION24_MAX_ABSENT_SECRETION and first_value >= MISSION24_MIN_ACTIVE_SECRETION:
                first_candidates.append(reaction_id)

    reference_co2 = float((reference.get('tracked_flux_values') or {}).get('EX_co2_e', 0.0)) if reference else 0.0
    first_co2 = float((first_binding.get('tracked_flux_values') or {}).get('EX_co2_e', 0.0)) if first_binding else 0.0
    first_formate = float((first_binding.get('tracked_flux_values') or {}).get('EX_for_e', 0.0)) if first_binding else 0.0
    first_acetate = float((first_binding.get('tracked_flux_values') or {}).get('EX_ac_e', 0.0)) if first_binding else 0.0
    later_formate = float((later.get('tracked_flux_values') or {}).get('EX_for_e', 0.0)) if later else 0.0
    later_acetate = float((later.get('tracked_flux_values') or {}).get('EX_ac_e', 0.0)) if later else 0.0

    nonbinding_reference = bool(reference and reference_co2 < 25.0 - MISSION24_BOUND_TOLERANCE)
    first_binding_point = bool(
        first_binding
        and abs(first_co2 - 20.0) <= MISSION24_BOUND_TOLERANCE
        and first_formate >= MISSION24_MIN_ACTIVE_SECRETION
        and first_acetate <= MISSION24_MAX_ABSENT_SECRETION
    )
    formate_onset = bool(first_candidates == ['EX_for_e'])
    acetate_onset = bool(
        later
        and later_formate >= MISSION24_MIN_ACTIVE_SECRETION
        and later_acetate >= MISSION24_MIN_ACTIVE_SECRETION
    )
    all_viable = bool(
        len(growth_values) == len(MISSION24_SWEEP_VALUES)
        and all(value >= MISSION24_MIN_VIABLE_GROWTH for value in growth_values)
    )
    relationship_supported = bool(
        reference
        and first_binding
        and later
        and tightest
        and nonbinding_reference
        and first_binding_point
        and formate_onset
        and acetate_onset
        and all_viable
        and float(first_binding['growth_value']) <= float(reference['growth_value']) - MISSION24_MIN_GROWTH_CHANGE
        and growth_trend
        and oxygen_uptake_trend
        and co2_export_trend
    )
    return {
        'nonbinding_reference': reference,
        'first_binding_point': first_binding,
        'later_compensation_point': later,
        'tightest_point': tightest,
        'growth_trend': growth_trend,
        'oxygen_uptake_trend': oxygen_uptake_trend,
        'co2_export_trend': co2_export_trend,
        'tracked_flux_trends': tracked_flux_trends,
        'first_compensatory_candidates': first_candidates,
        'formate_onset': formate_onset,
        'acetate_onset': acetate_onset,
        'relationship_supported': relationship_supported,
    }


def _build_mission24_data(sweep_data=None, existing_report=None):
    existing_report = existing_report if isinstance(existing_report, dict) else {}
    if existing_report.get('mission_id') != '24' or existing_report.get('check_version') != MISSION24_CHECK_VERSION:
        existing_report = _mission24_empty_report()

    current_valid, current_rows, issues = _mission24_validate_sweep(sweep_data)
    retained_sweep = copy.deepcopy(existing_report.get('sweep_data')) if existing_report.get('evidence_ready') else None
    retained_rows = copy.deepcopy(existing_report.get('sweep_rows') or []) if retained_sweep else []
    current_recorded = False
    if current_valid:
        retained_sweep = copy.deepcopy(sweep_data)
        retained_rows = current_rows
        current_recorded = True

    relation = _mission24_derive_relationship(retained_rows) if retained_rows else {
        'nonbinding_reference': None,
        'first_binding_point': None,
        'later_compensation_point': None,
        'tightest_point': None,
        'growth_trend': False,
        'oxygen_uptake_trend': False,
        'co2_export_trend': False,
        'tracked_flux_trends': {},
        'first_compensatory_candidates': [],
        'formate_onset': False,
        'acetate_onset': False,
        'relationship_supported': False,
    }
    recorded_values = [float(row['bound_value']) for row in retained_rows]
    expected_keys = {_mission24_value_key(value) for value in MISSION24_SWEEP_VALUES}
    recorded_keys = {_mission24_value_key(value) for value in recorded_values}
    missing_values = [value for value in MISSION24_SWEEP_VALUES if _mission24_value_key(value) not in recorded_keys]
    all_points = bool(recorded_keys == expected_keys and len(retained_rows) == len(MISSION24_SWEEP_VALUES))
    evidence_ready = bool(all_points and retained_sweep)
    relationship_supported = bool(evidence_ready and relation['relationship_supported'])

    latest_attempt = {
        'method': (sweep_data or {}).get('method') if isinstance(sweep_data, dict) else None,
        'objective': (sweep_data or {}).get('objective') if isinstance(sweep_data, dict) else None,
        'reaction_id': (sweep_data or {}).get('reaction_id') if isinstance(sweep_data, dict) else None,
        'bound': (sweep_data or {}).get('bound') if isinstance(sweep_data, dict) else None,
        'values': list((sweep_data or {}).get('values') or []) if isinstance(sweep_data, dict) else [],
        'issues': list(issues),
        'recorded': current_recorded,
    }
    report = _mission24_empty_report()
    report.update({
        'sweep_data': retained_sweep,
        'sweep_rows': retained_rows,
        'recorded_bound_values': recorded_values,
        'recorded_point_count': len(retained_rows),
        'missing_bound_values': missing_values,
        'all_points_recorded': all_points,
        **relation,
        'relationship_supported': relationship_supported,
        'evidence_ready': evidence_ready,
        'answer_ready': relationship_supported,
        'ready_to_deliver': relationship_supported,
        'current_sweep_valid': current_valid,
        'current_sweep_recorded': current_recorded,
        'current_issues': list(issues),
        'latest_attempt': latest_attempt,
    })
    save_mission24_comparison_check(report)
    return report


def run_mission24_export_capacity_check(sweep_data=None):
    """Validate the visible sweep table without invoking a solver."""
    if sweep_data is None:
        sweep_data = load_bound_sweep()
    return _build_mission24_data(
        sweep_data=sweep_data,
        existing_report=load_mission24_comparison_check() or {},
    )


def run_mission24_export_capacity_check_remote(backend_url, sweep_data=None):
    """Browser parity wrapper for an already visible remote Bound Sweep result."""
    del backend_url
    return run_mission24_export_capacity_check(sweep_data)


def _mission24_answer_mentions(answer):
    text = unicodedata.normalize('NFKD', str(answer or '')).encode('ascii', 'ignore').decode('ascii').lower()
    mentions = set()
    patterns = {
        'EX_for_e': [r'\bex[_\s-]*for[_\s-]*e\b', r'\bformate\b', r'\bformato\b', r'\bformic acid\b'],
        'EX_ac_e': [r'\bex[_\s-]*ac[_\s-]*e\b', r'\bacetate\b', r'\bacetato\b', r'\bacetic acid\b'],
        'EX_co2_e': [r'\bex[_\s-]*co2[_\s-]*e\b', r'\bco2\b', r'\bcarbon dioxide\b', r'\bdioxido(?: de)? carbono\b'],
    }
    for reaction_id, aliases in patterns.items():
        if any(re.search(pattern, text) for pattern in aliases):
            mentions.add(reaction_id)
    return mentions


def normalise_mission24_answer(answer):
    mentions = _mission24_answer_mentions(answer)
    return next(iter(mentions)) if len(mentions) == 1 else None


def mission24_answer_matches(answer, report_data=None):
    report_data = report_data if report_data is not None else (load_mission24_comparison_check() or {})
    candidates = report_data.get('first_compensatory_candidates') or []
    return bool(
        report_data.get('mission_id') == '24'
        and report_data.get('check_version') == MISSION24_CHECK_VERSION
        and report_data.get('answer_ready')
        and candidates == [MISSION24_EXPECTED_FIRST_COMPENSATORY_SECRETION]
        and normalise_mission24_answer(answer) == candidates[0]
    )


def build_mission24_export_capacity_report_text(report):
    if not report:
        return (
            'Prepare a controlled four-point export-capacity experiment before activation. '
            'Keep the model, biomass objective, genes and every unrelated environmental bound unchanged while progressively restricting only CO2 export.\n\n'
            'The visible sweep must show when the export cap becomes binding and how the tracked secretion profile responds as the restriction tightens, using the pFBA diagnostics from every recorded row.\n\n'
            'Activate the mission when you are ready to configure the Bound Sweep. Use the briefing for the exact controlled protocol and the optional hints for interpreting upper-bound constraints; infer the final route from the evidence.'
        )
    if report.get('mission_id') != '24' or report.get('check_version') != MISSION24_CHECK_VERSION:
        return 'Mission 24 Export Capacity Thresholds\n\nCurrent-format export-capacity evidence has not been recorded yet.'

    lines = [
        'Mission 24 Export Capacity Thresholds',
        '',
        'Controlled sweep protocol:',
        '- pFBA biomass objective; all genes active',
        '- Model-default environment before the sweep',
        '- Only the EX_co2_e upper bound changes: 25, 20, 10, 0',
        '- Production Flux panel: EX_co2_e, EX_for_e and EX_ac_e',
        '- Exchange evidence: EX_glc__D_e and EX_o2_e',
        '- Every row includes the pFBA primary flux and total-absolute-flux diagnostic',
        '',
        f"Sweep points recorded: {report.get('recorded_point_count', 0)}/{report.get('required_point_count', len(MISSION24_SWEEP_VALUES))}",
    ]
    rows = report.get('sweep_rows') or []
    if rows:
        lines.append('UB | growth | glucose uptake | oxygen uptake | CO2 | formate | acetate | total abs flux | active reactions')
        for row in rows:
            tracked = row.get('tracked_flux_values') or {}
            diagnostics = row.get('method_diagnostics') or {}
            lines.append(
                f"{float(row.get('bound_value')):.0f} | "
                f"{float(row.get('growth_value')):.3f} | "
                f"{float(row.get('glucose_uptake')):.3f} | "
                f"{float(row.get('oxygen_uptake')):.3f} | "
                f"{float(tracked.get('EX_co2_e')):.3f} | "
                f"{float(tracked.get('EX_for_e')):.3f} | "
                f"{float(tracked.get('EX_ac_e')):.3f} | "
                f"{float(diagnostics.get('total_absolute_flux')):.3f} | "
                f"{int(diagnostics.get('active_reaction_count'))}"
            )
    else:
        lines.append('No current-format sweep rows recorded.')

    if report.get('missing_bound_values'):
        lines.append('Missing bound values: ' + ', '.join(f'{float(value):g}' for value in report.get('missing_bound_values') or []))

    if report.get('current_sweep_recorded'):
        lines.extend(['', 'Latest valid visible Bound Sweep recorded.'])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest sweep was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if report.get('evidence_ready'):
            lines.append('Previously valid Mission 24 evidence remains available.')

    lines.append('')
    if report.get('evidence_ready'):
        lines.extend([
            'Evidence complete.',
            'Compare the non-binding reference with the first binding cap, then inspect the tighter cap where a second route appears.',
            'Question: Which tracked secretion became active at the first binding CO2-export cap, before acetate appeared at a tighter cap?',
        ])
    else:
        lines.append('Evidence incomplete.')

    lines.extend([
        '',
        'Interpretation note: an upper bound can be present without being binding when the optimum exports less than the cap.',
        'The sequential secretion response is conditional on this model, default medium, biomass objective and pFBA protocol.',
        'All growth, exchange, production and pFBA diagnostic values come from the visible Bound Sweep results. No hidden validation simulation is used.',
    ])
    return '\n'.join(lines)


# Backwards-compatible entry point retained for older imports.  It now validates
# the redesigned Bound Sweep rather than the removed FBA-versus-pFBA comparison.
def run_mission24_comparison_check(sweep_data=None):
    return run_mission24_export_capacity_check(sweep_data)


def is_mission25_unlocked(missions_completed):
    """Mission 25 starts only after Dr. Luna's final sensitivity mission."""
    return '24' in (missions_completed or [])


def _mission25_number_or_none(value):
    numeric = _as_float_or_none(value)
    return float(numeric) if numeric is not None else None


def _mission25_clean_number(value, decimals=6):
    numeric = float(value)
    if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
        numeric = 0.0
    return round(numeric, decimals)


def _mission25_environment_status(reactions):
    """Classify the exact aerobic/default or oxygen-blocked Mission 25 medium."""
    bounds_complete = True
    unexpected_changes = []
    oxygen_lower_bound_closed = False

    for index in range(len(REACTIONS.index)):
        reaction_id = REACTIONS.index[index]
        lower_open, upper_open = _reaction_bound_open_states(reactions, index)
        if lower_open is None or upper_open is None:
            bounds_complete = False
            continue

        default_lower_open = bool(REACTIONS.lb.iloc[index] != 0)
        default_upper_open = bool(REACTIONS.ub.iloc[index] != 0)
        lower_changed = bool(lower_open) != default_lower_open
        upper_changed = bool(upper_open) != default_upper_open

        if reaction_id == MISSION25_OXYGEN_REACTION:
            oxygen_lower_bound_closed = not bool(lower_open)
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            # The lower-bound change is the controlled oxygen-context factor.
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    context = None
    if bounds_complete and not unexpected_changes:
        context = 'anaerobic' if oxygen_lower_bound_closed else 'aerobic'

    return {
        'bounds_complete': bounds_complete,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'unexpected_environment_changes': unexpected_changes,
        'controlled_environment': bool(bounds_complete and not unexpected_changes),
        'context': context,
    }


def _mission25_genotype(knocked_out_genes):
    genes = list(knocked_out_genes or [])
    if not genes:
        return 'wild_type'
    if genes == [MISSION25_TARGET_GENE]:
        return 'knockout'
    return None


def _normalise_mission25_text(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(char for char in text if not unicodedata.combining(char)).lower()


def normalise_mission25_answer(answer):
    """Return one oxygen context from a concise English or Portuguese answer."""
    text = _normalise_mission25_text(answer)
    if not text.strip():
        return None
    if re.search(r'\b(?:both|ambos|ambas|all|todos|todas)\b', text):
        return None
    aerobic = bool(re.search(
        r'\b(?:aerobic|aerobiosis|with\s+oxygen|oxygen\s+available|aerobio|aerobiose|com\s+oxigenio)\b',
        text,
    ))
    anaerobic = bool(re.search(
        r'\b(?:anaerobic|anaerobiosis|without\s+oxygen|oxygen\s+blocked|oxygen[-\s]*free|anaerobio|anaerobiose|sem\s+oxigenio|oxigenio\s+bloqueado)\b',
        text,
    ))
    if aerobic == anaerobic:
        return None
    return 'anaerobic' if anaerobic else 'aerobic'


def mission25_answer_matches(answer, report_data=None):
    if report_data is None:
        report_data = load_mission25_comparison_check() or {}
    return bool(
        report_data.get('evidence_ready')
        and report_data.get('relationship_supported')
        and normalise_mission25_answer(answer) == 'anaerobic'
    )


def initialise_mission25_context_matrix():
    data = {
        'mission_id': '25',
        'check_version': MISSION25_CHECK_VERSION,
        'mission_title': 'Context-Dependent Gene Essentiality',
        'target_context': MISSION25_TARGET_CONTEXT,
        'target_method': MISSION25_METHOD,
        'growth_objective': MISSION25_GROWTH_OBJECTIVE,
        'target_gene': MISSION25_TARGET_GENE,
        'target_gene_name': MISSION25_TARGET_GENE_NAME,
        'target_reaction': MISSION25_TARGET_REACTION,
        'oxygen_reaction': MISSION25_OXYGEN_REACTION,
        'glucose_reaction': MISSION25_GLUCOSE_REACTION,
        'required_medium_fluxes': list(MISSION25_REQUIRED_MEDIUM_FLUXES),
        'aerobic_wild_type': None,
        'aerobic_knockout': None,
        'anaerobic_wild_type': None,
        'anaerobic_knockout': None,
        'recorded_run_count': 0,
        'required_run_count': 4,
        'missing_conditions': [
            'aerobic_wild_type',
            'aerobic_knockout',
            'anaerobic_wild_type',
            'anaerobic_knockout',
        ],
        'matrix_complete': False,
        'aerobic_growth_retention': None,
        'anaerobic_growth_retention': None,
        'context_effect_difference': None,
        'relationship_supported': False,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_run_valid': False,
        'current_run_recorded': False,
        'current_run_type': None,
        'current_issues': [],
        'current_run': None,
        'latest_attempt': None,
    }
    save_mission25_comparison_check(data)
    return data


def _build_mission25_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
):
    """Validate and accumulate one visible cell of the Mission 25 matrix."""
    existing_report = existing_report or {}
    if (
        existing_report.get('mission_id') != '25'
        or existing_report.get('check_version') != MISSION25_CHECK_VERSION
    ):
        existing_report = {}

    matrix_keys = (
        'aerobic_wild_type',
        'aerobic_knockout',
        'anaerobic_wild_type',
        'anaerobic_knockout',
    )
    matrix = {key: copy.deepcopy(existing_report.get(key)) for key in matrix_keys}

    environment = _mission25_environment_status(reactions)
    context = environment.get('context')
    knocked_out_genes = _knocked_out_genes(genes)
    genotype = _mission25_genotype(knocked_out_genes)
    run_type = f'{context}_{genotype}' if context and genotype else None

    objective_numeric = _mission25_number_or_none(objective_result)
    result_infeasible = 'INFEASIBLE' in str(objective_result or '').upper()
    raw_fluxes, uptake_fluxes, _secretion_fluxes = _mission21_measured_medium_values(medium_fluxes)
    diagnostics = _method_diagnostics_from_production_data(production_fluxes)
    biomass_raw = _mission25_number_or_none(_mission13_biomass_value(production_fluxes))
    primary_flux = _mission25_number_or_none(diagnostics.get('primary_objective_flux'))
    method_score = _mission25_number_or_none(diagnostics.get('method_score'))
    total_absolute_flux = _mission25_number_or_none(diagnostics.get('total_absolute_flux'))
    method_score_name = diagnostics.get('method_score_name')
    try:
        active_reaction_count = int(diagnostics.get('active_reaction_count'))
    except Exception:
        active_reaction_count = None

    glucose_raw = _mission25_number_or_none(raw_fluxes.get(MISSION25_GLUCOSE_REACTION))
    oxygen_raw = _mission25_number_or_none(raw_fluxes.get(MISSION25_OXYGEN_REACTION))
    glucose_uptake = _mission25_number_or_none(uptake_fluxes.get(MISSION25_GLUCOSE_REACTION))
    oxygen_uptake = _mission25_number_or_none(uptake_fluxes.get(MISSION25_OXYGEN_REACTION))

    issues = []
    if objective_error:
        issues.append(objective_error)
    if method_name != MISSION25_METHOD:
        issues.append('Use FBA for every Mission 25 matrix cell.')
    if selected_objective != MISSION25_GROWTH_OBJECTIVE:
        issues.append('Use the biomass objective for every Mission 25 matrix cell.')
    if not environment.get('bounds_complete'):
        issues.append('The environmental-bound payload is incomplete.')
    if environment.get('unexpected_environment_changes'):
        issues.append('Keep every unrelated environmental bound at the model default.')
    if context not in {'aerobic', 'anaerobic'}:
        issues.append('Use either the completely default aerobic medium or close only the oxygen lower bound.')
    if genotype is None:
        issues.append(f'Use either every gene active or only {MISSION25_TARGET_GENE} / {MISSION25_TARGET_GENE_NAME} knocked out.')

    if result_infeasible or objective_numeric is None:
        issues.append('Mission 25 requires a numeric visible biomass result, including a measured zero when growth is lost.')
    elif objective_numeric < -MISSION25_PRIMARY_TOLERANCE:
        issues.append('The biomass result is outside the valid non-negative range.')

    missing_medium = [reaction_id for reaction_id in MISSION25_REQUIRED_MEDIUM_FLUXES if reaction_id not in raw_fluxes]
    if medium_fluxes and medium_fluxes.get('error'):
        issues.append('The Exchange Flux Report is unavailable for this run.')
    elif missing_medium:
        issues.append('Numeric glucose and oxygen exchange evidence is required.')

    if glucose_raw is not None and glucose_uptake is not None:
        if glucose_raw > MISSION25_FLUX_TOLERANCE:
            issues.append('Glucose must not be secreted in the controlled matrix.')
        if glucose_uptake > MISSION25_EXPECTED_GLUCOSE_CAPACITY + MISSION25_GLUCOSE_CAPACITY_TOLERANCE:
            issues.append('Glucose uptake exceeds the model-default capacity.')
    if context == 'aerobic' and oxygen_uptake is not None:
        if oxygen_uptake < MISSION25_MIN_AEROBIC_OXYGEN_UPTAKE:
            issues.append('The aerobic cell must show measurable oxygen uptake.')
    if context == 'anaerobic' and oxygen_uptake is not None:
        if oxygen_uptake > MISSION25_FLUX_TOLERANCE:
            issues.append('The anaerobic cell must show zero oxygen uptake.')
    if oxygen_raw is not None and context == 'anaerobic' and abs(oxygen_raw) > MISSION25_FLUX_TOLERANCE:
        issues.append('The signed oxygen exchange flux is inconsistent with the blocked lower bound.')

    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        issues.append('The visible result is missing biomass and method-aware diagnostics.')
    if biomass_raw is None:
        issues.append('The visible result is missing the biomass-reaction flux.')
    if primary_flux is None:
        issues.append('The visible FBA result is missing the primary objective flux.')
    if objective_numeric is not None and biomass_raw is not None:
        if abs(objective_numeric - biomass_raw) > MISSION25_PRIMARY_TOLERANCE:
            issues.append('The displayed objective value does not match the biomass-reaction flux.')
    if biomass_raw is not None and primary_flux is not None:
        if abs(biomass_raw - primary_flux) > MISSION25_PRIMARY_TOLERANCE:
            issues.append('The primary objective diagnostic does not match biomass.')
    if diagnostics.get('method') != MISSION25_METHOD:
        issues.append('The method diagnostic does not identify FBA.')
    if diagnostics.get('objective_reaction') != MISSION25_GROWTH_OBJECTIVE:
        issues.append('The method diagnostic does not identify the biomass objective.')
    if method_score_name != 'primary_objective_flux':
        issues.append('The FBA method-score meaning is missing or incorrect.')
    if primary_flux is not None and method_score is not None:
        if abs(primary_flux - method_score) > MISSION25_PRIMARY_TOLERANCE:
            issues.append('The FBA method score does not match the primary objective flux.')
    else:
        issues.append('The visible FBA method score is missing.')
    if total_absolute_flux is None or active_reaction_count is None:
        issues.append('The visible FBA result is missing flux-distribution diagnostics.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run = None
    if current_run_valid:
        current_run = {
            'run_type': run_type,
            'context': context,
            'genotype': genotype,
            'method': method_name,
            'objective': selected_objective,
            'growth': _mission25_clean_number(objective_numeric),
            'knocked_out_genes': list(knocked_out_genes),
            'oxygen_lower_bound_closed': bool(environment.get('oxygen_lower_bound_closed')),
            'glucose_raw_flux': _mission25_clean_number(glucose_raw),
            'glucose_uptake': _mission25_clean_number(glucose_uptake),
            'oxygen_raw_flux': _mission25_clean_number(oxygen_raw),
            'oxygen_uptake': _mission25_clean_number(oxygen_uptake),
            'method_diagnostics': {
                'method': diagnostics.get('method'),
                'objective_reaction': diagnostics.get('objective_reaction'),
                'primary_objective_flux': _mission25_clean_number(primary_flux),
                'method_score': _mission25_clean_number(method_score),
                'method_score_name': method_score_name,
                'total_absolute_flux': _mission25_clean_number(total_absolute_flux),
                'active_reaction_count': active_reaction_count,
            },
        }
        matrix[run_type] = current_run
        current_run_recorded = True

    missing_conditions = [key for key in matrix_keys if not isinstance(matrix.get(key), dict)]
    matrix_complete = not missing_conditions
    recorded_run_count = len(matrix_keys) - len(missing_conditions)

    aerobic_growth_retention = None
    anaerobic_growth_retention = None
    context_effect_difference = None
    relationship_supported = False
    if matrix_complete:
        aerobic_reference = _mission25_number_or_none(matrix['aerobic_wild_type'].get('growth'))
        aerobic_knockout = _mission25_number_or_none(matrix['aerobic_knockout'].get('growth'))
        anaerobic_reference = _mission25_number_or_none(matrix['anaerobic_wild_type'].get('growth'))
        anaerobic_knockout = _mission25_number_or_none(matrix['anaerobic_knockout'].get('growth'))
        if (
            aerobic_reference is not None
            and aerobic_knockout is not None
            and anaerobic_reference is not None
            and anaerobic_knockout is not None
            and aerobic_reference >= MISSION25_MIN_REFERENCE_GROWTH
            and anaerobic_reference >= MISSION25_MIN_REFERENCE_GROWTH
        ):
            aerobic_growth_retention = _mission25_clean_number(aerobic_knockout / aerobic_reference)
            anaerobic_growth_retention = _mission25_clean_number(anaerobic_knockout / anaerobic_reference)
            context_effect_difference = _mission25_clean_number(
                aerobic_growth_retention - anaerobic_growth_retention
            )
            relationship_supported = bool(
                aerobic_growth_retention >= MISSION25_MIN_AEROBIC_KO_RETENTION
                and anaerobic_growth_retention <= MISSION25_MAX_ANAEROBIC_KO_RETENTION
                and context_effect_difference >= MISSION25_MIN_CONTEXT_EFFECT_GAP
            )

    latest_attempt = {
        'method': method_name,
        'objective': selected_objective,
        'context': context,
        'genotype': genotype,
        'run_type': run_type,
        'objective_result': str(objective_result),
        'issues': list(issues),
        'recorded': current_run_recorded,
    }
    report = {
        'mission_id': '25',
        'check_version': MISSION25_CHECK_VERSION,
        'mission_title': 'Context-Dependent Gene Essentiality',
        'target_context': MISSION25_TARGET_CONTEXT,
        'target_method': MISSION25_METHOD,
        'growth_objective': MISSION25_GROWTH_OBJECTIVE,
        'target_gene': MISSION25_TARGET_GENE,
        'target_gene_name': MISSION25_TARGET_GENE_NAME,
        'target_reaction': MISSION25_TARGET_REACTION,
        'oxygen_reaction': MISSION25_OXYGEN_REACTION,
        'glucose_reaction': MISSION25_GLUCOSE_REACTION,
        'required_medium_fluxes': list(MISSION25_REQUIRED_MEDIUM_FLUXES),
        **matrix,
        'recorded_run_count': recorded_run_count,
        'required_run_count': 4,
        'missing_conditions': missing_conditions,
        'matrix_complete': matrix_complete,
        'aerobic_growth_retention': aerobic_growth_retention,
        'anaerobic_growth_retention': anaerobic_growth_retention,
        'context_effect_difference': context_effect_difference,
        'relationship_supported': relationship_supported,
        'evidence_ready': matrix_complete,
        'answer_ready': relationship_supported,
        'ready_to_deliver': relationship_supported,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_run_type': run_type,
        'current_issues': issues,
        'current_run': current_run,
        'latest_attempt': latest_attempt,
    }
    save_mission25_comparison_check(report)
    return report


def run_mission25_context_check(simulation_results=None):
    """Validate the already visible Mission 25 result without re-simulating."""
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible Mission 25 simulation before recording evidence.'
    except Exception:
        objective_error = 'Could not read the current visible Mission 25 simulation result.'

    return _build_mission25_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission25_comparison_check() or {},
        objective_error=objective_error,
    )


def run_mission25_context_check_remote(backend_url, simulation_results=None):
    """The browser uses the same already returned structured simulation result."""
    _ = backend_url
    return run_mission25_context_check(simulation_results)


def build_mission25_context_report_text(report_data=None):
    report = report_data or {}
    if report.get('mission_id') != '25' or report.get('check_version') != MISSION25_CHECK_VERSION:
        return (
            'Build a four-cell oxygen-by-genotype matrix for the highlighted ppc gene.\n\n'
            'Record wild type and knockout growth with oxygen available, then repeat both genotypes with only oxygen uptake blocked. '
            'The report requires numeric glucose and oxygen exchange evidence plus method-aware FBA diagnostics from each visible run.'
        )

    def fmt(value):
        return 'pending' if value is None else f'{float(value):.3f}'

    def pct(value):
        return 'pending' if value is None else f'{float(value) * 100:.1f}%'

    labels = {
        'aerobic_wild_type': 'Aerobic wild type',
        'aerobic_knockout': f'Aerobic {MISSION25_TARGET_GENE} knockout',
        'anaerobic_wild_type': 'Anaerobic wild type',
        'anaerobic_knockout': f'Anaerobic {MISSION25_TARGET_GENE} knockout',
    }
    lines = [
        'Controlled matrix:',
        f'- Method: {MISSION25_METHOD}',
        f'- Objective: {MISSION25_GROWTH_OBJECTIVE}',
        f'- Tested gene: {MISSION25_TARGET_GENE} / {MISSION25_TARGET_GENE_NAME}',
        '- Factors: oxygen available/blocked and wild type/single-gene knockout',
        '',
        f"Matrix cells recorded: {report.get('recorded_run_count', 0)}/4",
        '',
    ]
    for key in ('aerobic_wild_type', 'aerobic_knockout', 'anaerobic_wild_type', 'anaerobic_knockout'):
        run = report.get(key)
        if not isinstance(run, dict):
            lines.append(f'{labels[key]}: pending')
            continue
        lines.extend([
            labels[key] + ':',
            f"- Growth: {fmt(run.get('growth'))}",
            f"- Glucose uptake: {fmt(run.get('glucose_uptake'))}",
            f"- Oxygen uptake: {fmt(run.get('oxygen_uptake'))}",
            f"- Total absolute flux: {fmt((run.get('method_diagnostics') or {}).get('total_absolute_flux'))}",
            f"- Active reactions: {(run.get('method_diagnostics') or {}).get('active_reaction_count', 'pending')}",
        ])

    lines.extend([
        '',
        'Within-context growth retention:',
        f"- Aerobic knockout / aerobic wild type: {pct(report.get('aerobic_growth_retention'))}",
        f"- Anaerobic knockout / anaerobic wild type: {pct(report.get('anaerobic_growth_retention'))}",
    ])

    if report.get('current_run_recorded'):
        lines.extend(['', f"Latest valid matrix cell recorded: {report.get('current_run_type') }."])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if report.get('evidence_ready'):
            lines.append('Previously valid Mission 25 matrix evidence remains available.')

    lines.append('')
    if report.get('evidence_ready'):
        lines.extend([
            'Evidence complete.',
            'Compare knockout-to-reference growth retention separately inside the two oxygen contexts.',
            'Question: In which oxygen context did the same knockout produce the strongest predicted growth defect?',
        ])
        if not report.get('relationship_supported'):
            lines.append('The current four-cell evidence does not support the expected contrasting context relationship; verify every controlled cell.')
    else:
        missing = report.get('missing_conditions') or []
        lines.append('Evidence incomplete.')
        if missing:
            lines.append('Missing matrix cells: ' + ', '.join(missing))

    lines.extend([
        '',
        'Interpretation note: gene essentiality here is operational and conditional on this model, objective, medium and oxygen context.',
        'All growth, exchange and FBA diagnostic values come from visible simulation results. No hidden validation simulation is used.',
    ])
    return '\n'.join(lines)


# Backwards-compatible names retained for older imports.  They now validate the
# redesigned four-cell context matrix rather than the removed two-run report.
def run_mission25_comparison_check(simulation_results=None):
    return run_mission25_context_check(simulation_results)


def _build_mission25_text(report_data=None):
    return build_mission25_context_report_text(report_data)

def _selected_sweep_value(menu_data, key, default_value):
    """Return a recognised internal dropselect value from pygame-menu data.

    pygame-menu has used more than one nesting shape across versions.  Walk the
    value recursively and prefer recognised internal identifiers instead of
    relying on a fixed tuple/list position.
    """
    value = (menu_data or {}).get(key)

    def strings(item):
        if isinstance(item, str):
            yield item
        elif isinstance(item, (list, tuple)):
            for child in item:
                yield from strings(child)

    preferred_values = {
        'sweep_variable': {
            f'{MISSION23_SWEEP_REACTION}:lower',
            f'{MISSION24_SWEEP_REACTION}:upper',
            f'{MISSION26_SWEEP_REACTION}:lower',
            f'{MISSION27_GLUCOSE_REACTION}:lower',
            *[f'{reaction_id}:lower' for reaction_id in MISSION28_CANDIDATE_CARBON_SOURCES],
        },
        'sweep_values': {
            'ammonium_sensitivity',
            'co2_export_capacity',
            'oxygen_transition',
            'glucose_limitation',
            'alternative_carbon_limitation',
        },
    }
    candidates = list(strings(value))
    for candidate in candidates:
        if candidate in preferred_values.get(key, set()):
            return candidate
    return default_value


def _normalise_sweep_config(sweep_menu_data=None):
    sweep_menu_data = sweep_menu_data or {}
    variable = _selected_sweep_value(
        sweep_menu_data,
        'sweep_variable',
        f'{MISSION23_SWEEP_REACTION}:lower',
    )
    preset = _selected_sweep_value(
        sweep_menu_data,
        'sweep_values',
        'ammonium_sensitivity',
    )

    sweep_options = {
        f'{MISSION23_SWEEP_REACTION}:lower': {
            'reaction_id': MISSION23_SWEEP_REACTION,
            'reaction_name': MISSION23_SWEEP_REACTION_NAME,
            'bound': MISSION23_SWEEP_BOUND,
            'bound_label': MISSION23_SWEEP_BOUND_LABEL,
            'default_preset': 'ammonium_sensitivity',
        },
        f'{MISSION24_SWEEP_REACTION}:upper': {
            'reaction_id': MISSION24_SWEEP_REACTION,
            'reaction_name': MISSION24_SWEEP_REACTION_NAME,
            'bound': MISSION24_SWEEP_BOUND,
            'bound_label': MISSION24_SWEEP_BOUND_LABEL,
            'default_preset': 'co2_export_capacity',
        },
        f'{MISSION26_SWEEP_REACTION}:lower': {
            'reaction_id': MISSION26_SWEEP_REACTION,
            'reaction_name': MISSION26_SWEEP_REACTION_NAME,
            'bound': MISSION26_SWEEP_BOUND,
            'bound_label': MISSION26_SWEEP_BOUND_LABEL,
            'default_preset': 'oxygen_transition',
        },
        f'{MISSION27_GLUCOSE_REACTION}:lower': {
            'reaction_id': MISSION27_GLUCOSE_REACTION,
            'reaction_name': 'D-Glucose exchange',
            'bound': 'lower',
            'bound_label': 'lower bound',
            'default_preset': 'glucose_limitation',
        },
    }
    for reaction_id in MISSION28_CANDIDATE_CARBON_SOURCES:
        sweep_options[f'{reaction_id}:lower'] = {
            'reaction_id': reaction_id,
            'reaction_name': _reaction_display_label(reaction_id).split(' (')[0],
            'bound': MISSION28_SWEEP_BOUND,
            'bound_label': MISSION28_SWEEP_BOUND_LABEL,
            'default_preset': 'alternative_carbon_limitation',
        }

    preset_values = {
        'ammonium_sensitivity': list(MISSION23_SWEEP_VALUES),
        'co2_export_capacity': list(MISSION24_SWEEP_VALUES),
        'oxygen_transition': list(MISSION26_SWEEP_VALUES),
        'glucose_limitation': [-1000.0, -500.0, -100.0, -50.0, -10.0, 0.0],
        'alternative_carbon_limitation': list(MISSION28_SWEEP_VALUES),
    }
    resolved_variable = (
        variable if variable in sweep_options
        else f'{MISSION23_SWEEP_REACTION}:lower'
    )
    config = sweep_options[resolved_variable].copy()
    expected_preset = config['default_preset']

    # Preserve every recognised preset selected by the player.  A preset can be
    # scientifically incompatible with the selected reaction, but silently
    # replacing it with the reaction default would make an invalid visible setup
    # execute as a valid experiment.  Mission validators must receive the exact
    # values that were shown and selected in the Bound Sweep menu.
    if preset not in preset_values:
        preset = expected_preset

    return {
        'variable': resolved_variable,
        'preset': preset,
        'expected_preset': expected_preset,
        'preset_matches_variable': preset == expected_preset,
        'reaction_id': config.get('reaction_id'),
        'reaction_name': config.get('reaction_name'),
        'bound': config.get('bound'),
        'bound_label': config.get('bound_label'),
        'values': list(preset_values[preset]),
    }


def _apply_numeric_bound_to_constraints(constraints, reaction_id, bound, value):
    current_lb, current_ub = constraints.get(reaction_id, (-1000, 1000))
    if bound == 'upper':
        constraints[reaction_id] = (current_lb, float(value))
    else:
        constraints[reaction_id] = (float(value), current_ub)
    return constraints


def _row_value(row, key, default=0.0):
    try:
        return float(row.get(key, default))
    except Exception:
        return float(default)


def _bound_sweep_flux_values(production_fluxes):
    values = {}
    if not isinstance(production_fluxes, dict):
        return values
    for item in production_fluxes.get('items') or []:
        reaction_id = item.get('reaction_id')
        numeric = _as_float_or_none(item.get('production_flux'))
        if reaction_id and numeric is not None and not item.get('error'):
            values[str(reaction_id)] = float(numeric)
    return values


def _bound_sweep_default_tracked_fluxes():
    """Compatibility helper; sweeps now expose only explicitly selected fluxes."""
    return []


def _bound_sweep_exchange_maps(flux_getter):
    raw, uptake, secretion = {}, {}, {}
    for reaction_id in list(REACTIONS.index):
        numeric = _as_float_or_none(flux_getter(reaction_id))
        if numeric is None:
            continue
        numeric = float(numeric)
        raw[reaction_id] = round(numeric, 6)
        uptake[reaction_id] = round(max(-numeric, 0.0), 6)
        secretion[reaction_id] = round(max(numeric, 0.0), 6)
    return raw, uptake, secretion


def _build_bound_sweep_row(bound_value, config, method_name, objective_name, tracked_fluxes, flux_getter, diagnostics):
    raw_fluxes, uptake_fluxes, secretion_fluxes = _bound_sweep_exchange_maps(flux_getter)
    primary = _as_float_or_none((diagnostics or {}).get('primary_objective_flux'))
    biomass = _as_float_or_none(raw_fluxes.get(MISSION07_BIOMASS_OBJECTIVE))
    if biomass is None:
        biomass = _as_float_or_none(flux_getter(MISSION07_BIOMASS_OBJECTIVE))
    production_fluxes = _build_production_flux_data(tracked_fluxes, flux_getter=flux_getter)
    tested_raw = _as_float_or_none(raw_fluxes.get(config.get('reaction_id')))
    oxygen_raw = _as_float_or_none(raw_fluxes.get('EX_o2_e'))
    return {
        'bound_value': float(bound_value),
        'status': 'ok',
        'objective_result': round(float(primary), 6) if primary is not None else None,
        'growth_value': round(float(biomass), 6) if biomass is not None else None,
        'tested_reaction_raw_flux': round(float(tested_raw), 6) if tested_raw is not None else None,
        'tested_reaction_uptake': round(max(-float(tested_raw), 0.0), 6) if tested_raw is not None else None,
        'oxygen_raw_flux': round(float(oxygen_raw), 6) if oxygen_raw is not None else None,
        'oxygen_uptake': round(max(-float(oxygen_raw), 0.0), 6) if oxygen_raw is not None else None,
        'tracked_flux_values': {
            reaction_id: round(float(value), 6)
            for reaction_id, value in _bound_sweep_flux_values(production_fluxes).items()
        },
        'exchange_raw_fluxes': raw_fluxes,
        'exchange_uptake_fluxes': uptake_fluxes,
        'exchange_secretion_fluxes': secretion_fluxes,
        'method_diagnostics': copy.deepcopy(diagnostics or {}),
    }


def _bound_sweep_infeasible_row(bound_value, message=None):
    row = {
        'bound_value': float(bound_value),
        'status': 'infeasible',
        'objective_result': None,
        'growth_value': None,
        'tested_reaction_raw_flux': None,
        'tested_reaction_uptake': None,
        'oxygen_raw_flux': None,
        'oxygen_uptake': None,
        'tracked_flux_values': {},
        'exchange_raw_fluxes': {},
        'exchange_uptake_fluxes': {},
        'exchange_secretion_fluxes': {},
        'method_diagnostics': {},
    }
    if message:
        row['message'] = str(message)
    return row


def _bound_sweep_error_row(bound_value, message):
    row = _bound_sweep_infeasible_row(bound_value, message=message)
    row['status'] = 'error'
    return row


def _new_bound_sweep_data(method_name, objective_name, genes, reactions, config, selected_fluxes):
    return {
        'sweep_id': 'bound_sweep',
        'check_version': 3,
        'method': method_name,
        'objective': objective_name,
        'knocked_out_genes': _knocked_out_genes(genes),
        'environment_changed': _environment_has_changes(reactions),
        'base_genes': copy.deepcopy(genes),
        'base_reactions': copy.deepcopy(reactions),
        'variable': config.get('variable'),
        'preset': config.get('preset'),
        'expected_preset': config.get('expected_preset'),
        'preset_matches_variable': bool(config.get('preset_matches_variable')),
        'reaction_id': config.get('reaction_id'),
        'reaction_name': config.get('reaction_name'),
        'bound': config.get('bound'),
        'bound_label': config.get('bound_label'),
        'values': list(config.get('values') or []),
        'tracked_fluxes': list(selected_fluxes),
        'selected_production_fluxes': list(selected_fluxes),
        'rows': [],
    }


def run_bound_sweep(sweep_menu_data=None):
    """Run one visible one-variable sweep with local solver parity."""
    method_name, objective_name, genes, reactions = _read_simulation_file()
    config = _normalise_sweep_config(sweep_menu_data)
    selected_fluxes = [
        reaction_id for reaction_id in _read_selected_production_fluxes()
        if reaction_id in PRODUCTION_FLUX_REACTION_IDS
    ]
    data = _new_bound_sweep_data(method_name, objective_name, genes, reactions, config, selected_fluxes)

    for bound_value in config.get('values') or []:
        try:
            simul, constraints = _build_local_constraints(genes, reactions)
            simul.objective = objective_name
            constraints = _apply_numeric_bound_to_constraints(
                constraints, config.get('reaction_id'), config.get('bound'), bound_value
            )
            result = simul.simulate(method=method_name, constraints=constraints)
            normalised = _normalise_result(result)
            if normalised == 'Status: INFEASIBLE':
                data['rows'].append(_bound_sweep_infeasible_row(bound_value))
                continue
            solver_value = _solver_scalar_value(result)
            diagnostics = _build_method_diagnostics(
                method_name, objective_name, result, solver_value=solver_value
            )
            flux_getter = lambda reaction_id: _extract_flux(result, reaction_id)
            data['rows'].append(_build_bound_sweep_row(
                bound_value, config, method_name, objective_name,
                selected_fluxes, flux_getter, diagnostics,
            ))
        except Exception as exc:
            if _is_infeasible_solver_exception(exc):
                data['rows'].append(_bound_sweep_infeasible_row(bound_value, message=exc))
            else:
                data['rows'].append(_bound_sweep_error_row(bound_value, exc))

    if any(row.get('status') == 'error' for row in data['rows']):
        data['error'] = 'One or more Bound Sweep rows failed. Inspect the row status instead of treating missing values as zero.'
    save_bound_sweep(data)
    return data


def run_bound_sweep_remote(backend_url, sweep_menu_data=None):
    """Browser sweep: sequentially reuse the existing /simulate contract."""
    method_name, objective_name, genes, reactions = _read_simulation_file()
    config = _normalise_sweep_config(sweep_menu_data)
    selected_fluxes = [
        reaction_id for reaction_id in _read_selected_production_fluxes()
        if reaction_id in PRODUCTION_FLUX_REACTION_IDS
    ]
    data = _new_bound_sweep_data(method_name, objective_name, genes, reactions, config, selected_fluxes)
    base_payload = _build_request_payload()

    for bound_value in config.get('values') or []:
        payload = copy.deepcopy(base_payload)
        env = payload.setdefault('env_conditions', {})
        current = list(env.get(config.get('reaction_id'), [-1000.0, 1000.0]))
        if config.get('bound') == 'upper':
            current[1] = float(bound_value)
        else:
            current[0] = float(bound_value)
        env[config.get('reaction_id')] = current
        try:
            response = _http_post_json(backend_url.rstrip('/') + '/simulate', payload)
        except Exception as exc:
            data['rows'].append(_bound_sweep_error_row(bound_value, f'Backend error: {exc}'))
            continue
        status = response.get('status')
        if status == 'infeasible':
            data['rows'].append(_bound_sweep_infeasible_row(bound_value, response.get('message')))
            continue
        if status != 'ok':
            data['rows'].append(_bound_sweep_error_row(bound_value, response.get('message', 'unknown backend error')))
            continue

        fluxes = response.get('fluxes') or {}
        flux_getter = lambda reaction_id, mapping=fluxes: mapping.get(reaction_id)
        primary = _as_float_or_none(response.get('primary_objective_flux', fluxes.get(objective_name)))
        total_abs = _as_float_or_none(response.get('total_absolute_flux'))
        if total_abs is None and fluxes:
            total_abs = sum(abs(float(value)) for value in fluxes.values())
        active_count = response.get('active_reaction_count')
        if active_count is None and fluxes:
            active_count = sum(1 for value in fluxes.values() if abs(float(value)) > MISSION13_ACTIVE_FLUX_TOLERANCE)
        method_score = _as_float_or_none(response.get('method_score'))
        diagnostics = {
            'method': response.get('method', method_name),
            'objective_reaction': response.get('objective_reaction', objective_name),
            'primary_objective_flux': float(primary) if primary is not None else None,
            'method_score': float(method_score) if method_score is not None else None,
            'method_score_name': response.get('method_score_name', _method_score_label(method_name)),
            'total_absolute_flux': float(total_abs) if total_abs is not None else None,
            'active_reaction_count': int(active_count) if active_count is not None else None,
        }
        data['rows'].append(_build_bound_sweep_row(
            bound_value, config, method_name, objective_name,
            selected_fluxes, flux_getter, diagnostics,
        ))

    if any(row.get('status') == 'error' for row in data['rows']):
        data['error'] = 'One or more remote Bound Sweep rows failed. Inspect the row status instead of treating missing values as zero.'
    save_bound_sweep(data)
    return data


def _growth_values_from_rows(rows):
    return [_row_value(row, 'growth_value') for row in rows]


def _count_decreasing_steps(values, tolerance=0.001):
    count = 0
    for before, after in zip(values, values[1:]):
        if after < before - tolerance:
            count += 1
    return count


def _selected_fluxes_include(required_fluxes, selected_fluxes):
    selected_fluxes = selected_fluxes or []
    return all(reaction_id in selected_fluxes for reaction_id in required_fluxes)

def is_mission26_unlocked(missions_completed):
    """Mission 26 is Dr. Smith's second task and follows Mission 25."""
    return '25' in (missions_completed or [])


def _mission26_clean_number(value):
    numeric = float(value)
    if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
        numeric = 0.0
    return round(numeric, 6)


def _mission26_number_or_none(value):
    numeric = _as_float_or_none(value)
    return _mission26_clean_number(numeric) if numeric is not None else None


def _mission26_value_key(value):
    numeric = _as_float_or_none(value)
    return round(float(numeric), 6) if numeric is not None else None


def _mission26_base_environment_status(reactions):
    """Require a complete model-default base environment, independent of key order."""
    return _mission23_base_environment_status(reactions)


def _mission26_empty_report():
    return {
        'mission_id': '26',
        'check_version': MISSION26_CHECK_VERSION,
        'mission_title': 'Genotype-Environment Interaction Curve',
        'target_context': MISSION26_TARGET_CONTEXT,
        'target_method': MISSION26_METHOD,
        'growth_objective': MISSION26_GROWTH_OBJECTIVE,
        'target_gene': MISSION26_TARGET_GENE,
        'target_gene_name': MISSION26_TARGET_GENE_NAME,
        'sweep_reaction': MISSION26_SWEEP_REACTION,
        'sweep_bound': MISSION26_SWEEP_BOUND,
        'required_bound_values': list(MISSION26_SWEEP_VALUES),
        'required_medium_fluxes': list(MISSION26_REQUIRED_MEDIUM_FLUXES),
        'wild_type_sweep': None,
        'knockout_sweep': None,
        'wild_type_sweep_rows': [],
        'knockout_sweep_rows': [],
        'recorded_sweep_count': 0,
        'required_sweep_count': 2,
        'missing_sweeps': ['wild_type', 'knockout'],
        'curves_complete': False,
        'matched_points_complete': False,
        'growth_retention_by_bound': {},
        'oxygen_binding_by_bound': {},
        'wild_type_growth_monotonic': False,
        'knockout_growth_monotonic': False,
        'positive_oxygen_growth_retained': False,
        'zero_bound_wild_type_viable': False,
        'zero_bound_knockout_collapsed': False,
        'interaction_threshold_supported': False,
        'threshold_bound': None,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_sweep_type': None,
        'current_sweep_valid': False,
        'current_sweep_recorded': False,
        'current_issues': [],
        'latest_attempt': None,
    }


def initialise_mission26_interaction_curves():
    report = _mission26_empty_report()
    save_mission26_bound_sweep_check(report)
    return report


def _mission26_row_groups(rows):
    grouped = {}
    for row in rows or []:
        key = _mission26_value_key(row.get('bound_value'))
        if key is not None:
            grouped.setdefault(key, []).append(row)
    return grouped


def _mission26_complete_numeric_mapping(mapping, required_ids):
    if not isinstance(mapping, dict):
        return False
    return all(_as_float_or_none(mapping.get(reaction_id)) is not None for reaction_id in required_ids)


def _mission26_validate_sweep(sweep_data):
    """Validate one visible WT or b3956 oxygen sweep without invoking a solver."""
    issues = []
    if not isinstance(sweep_data, dict) or not sweep_data:
        return None, [], ['Run one Mission 26 oxygen Bound Sweep before recording evidence.']
    if sweep_data.get('error'):
        issues.append(str(sweep_data.get('error')))

    if sweep_data.get('method') != MISSION26_METHOD:
        issues.append('Use FBA for both Mission 26 curves.')
    if sweep_data.get('objective') != MISSION26_GROWTH_OBJECTIVE:
        issues.append('Use the biomass objective for both Mission 26 curves.')

    knocked_out_genes = sorted(set(sweep_data.get('knocked_out_genes') or []))
    if not knocked_out_genes:
        sweep_type = 'wild_type'
    elif knocked_out_genes == [MISSION26_TARGET_GENE]:
        sweep_type = 'knockout'
    else:
        sweep_type = None
        issues.append(
            f'Use either every gene active or only {MISSION26_TARGET_GENE} / '
            f'{MISSION26_TARGET_GENE_NAME} knocked out.'
        )

    base_genes = sweep_data.get('base_genes') or {}
    if not isinstance(base_genes, dict) or any(gene_id not in base_genes for gene_id in GENES):
        issues.append('The explicit base-gene payload is incomplete.')
    elif sorted(_knocked_out_genes(base_genes)) != knocked_out_genes:
        issues.append('The reported knockout list does not match the visible base-gene configuration.')

    environment = _mission26_base_environment_status(sweep_data.get('base_reactions') or {})
    if not environment.get('bounds_complete'):
        issues.append('The explicit base environmental-bound payload is incomplete.')
    elif not environment.get('environment_default'):
        issues.append('Keep every base environmental bound at the model default before both sweeps.')

    if sweep_data.get('reaction_id') != MISSION26_SWEEP_REACTION or sweep_data.get('bound') != MISSION26_SWEEP_BOUND:
        issues.append('Sweep only the lower bound of EX_o2_e.')

    expected_keys = [_mission26_value_key(value) for value in MISSION26_SWEEP_VALUES]
    got_keys = [_mission26_value_key(value) for value in (sweep_data.get('values') or [])]
    if len(got_keys) != len(expected_keys) or sorted(value for value in got_keys if value is not None) != sorted(expected_keys):
        issues.append('Use exactly the four oxygen lower-bound values: -25, -10, -1 and 0.')

    row_groups = _mission26_row_groups(sweep_data.get('rows') or [])
    normalised_rows = []
    for bound_value in MISSION26_SWEEP_VALUES:
        key = _mission26_value_key(bound_value)
        candidates = row_groups.get(key) or []
        if len(candidates) != 1:
            if not candidates:
                issues.append(f'Missing the visible sweep row for oxygen lower bound {bound_value:g}.')
            else:
                issues.append(f'Duplicate visible sweep rows were returned for oxygen lower bound {bound_value:g}.')
            continue
        row = candidates[0]
        if row.get('status') != 'ok':
            issues.append(f'The sweep row at oxygen lower bound {bound_value:g} did not return an optimal measurable result.')
            continue

        growth = _mission26_number_or_none(row.get('growth_value'))
        objective_result = _mission26_number_or_none(row.get('objective_result'))
        row_oxygen_uptake = _mission26_number_or_none(row.get('oxygen_uptake'))
        raw_fluxes = row.get('exchange_raw_fluxes') or {}
        diagnostics = row.get('method_diagnostics') or {}
        if growth is None:
            issues.append(f'Biomass is missing from the row at oxygen lower bound {bound_value:g}.')
        if objective_result is None or growth is None or abs(float(objective_result) - float(growth)) > MISSION26_PRIMARY_TOLERANCE:
            issues.append(f'The visible objective result does not match biomass at oxygen lower bound {bound_value:g}.')
        if not _mission26_complete_numeric_mapping(raw_fluxes, MISSION26_REQUIRED_MEDIUM_FLUXES):
            issues.append(f'Numeric glucose and oxygen exchange evidence is incomplete at oxygen lower bound {bound_value:g}.')

        glucose_raw = _mission26_number_or_none(raw_fluxes.get(MISSION26_GLUCOSE_REACTION))
        oxygen_raw = _mission26_number_or_none(raw_fluxes.get(MISSION26_OXYGEN_REACTION))
        glucose_uptake = max(-float(glucose_raw), 0.0) if glucose_raw is not None else None
        oxygen_uptake = max(-float(oxygen_raw), 0.0) if oxygen_raw is not None else None
        tested_uptake = _mission26_number_or_none(row.get('tested_reaction_uptake'))

        primary = _mission26_number_or_none(diagnostics.get('primary_objective_flux'))
        method_score = _mission26_number_or_none(diagnostics.get('method_score'))
        total_absolute_flux = _mission26_number_or_none(diagnostics.get('total_absolute_flux'))
        active_reactions = diagnostics.get('active_reaction_count')
        try:
            active_reactions = int(active_reactions)
        except Exception:
            active_reactions = None

        if diagnostics.get('method') != MISSION26_METHOD:
            issues.append(f'The visible method diagnostics do not describe FBA at oxygen lower bound {bound_value:g}.')
        if diagnostics.get('objective_reaction') != MISSION26_GROWTH_OBJECTIVE:
            issues.append(f'The visible diagnostics use the wrong objective at oxygen lower bound {bound_value:g}.')
        if diagnostics.get('method_score_name') != MISSION26_EXPECTED_SCORE_NAME:
            issues.append(f'The FBA score label is missing at oxygen lower bound {bound_value:g}.')
        if primary is None or growth is None or abs(float(primary) - float(growth)) > MISSION26_PRIMARY_TOLERANCE:
            issues.append(f'The primary biomass flux does not match growth at oxygen lower bound {bound_value:g}.')
        if method_score is None or primary is None or abs(float(method_score) - float(primary)) > MISSION26_PRIMARY_TOLERANCE:
            issues.append(f'The FBA method score does not match the primary biomass flux at oxygen lower bound {bound_value:g}.')
        if total_absolute_flux is None or active_reactions is None:
            issues.append(f'Total flux or active-reaction diagnostics are missing at oxygen lower bound {bound_value:g}.')

        if oxygen_uptake is not None and row_oxygen_uptake is not None:
            if abs(float(oxygen_uptake) - float(row_oxygen_uptake)) > MISSION26_FLUX_TOLERANCE:
                issues.append(f'The visible oxygen-uptake field does not match oxygen exchange at lower bound {bound_value:g}.')
        elif oxygen_uptake is not None:
            issues.append(f'The visible oxygen-uptake field is missing at lower bound {bound_value:g}.')
        if oxygen_uptake is not None and tested_uptake is not None:
            if abs(float(oxygen_uptake) - float(tested_uptake)) > MISSION26_FLUX_TOLERANCE:
                issues.append(f'The tested-reaction uptake does not match oxygen exchange at lower bound {bound_value:g}.')
        elif oxygen_uptake is not None:
            issues.append(f'The tested oxygen-uptake value is missing at lower bound {bound_value:g}.')

        if glucose_raw is not None:
            if float(glucose_raw) > MISSION26_FLUX_TOLERANCE:
                issues.append(f'The model is secreting rather than consuming glucose at oxygen lower bound {bound_value:g}.')
            if growth is not None and float(growth) > MISSION26_MAX_COLLAPSED_GROWTH:
                if abs(float(glucose_uptake) - MISSION26_EXPECTED_GLUCOSE_UPTAKE) > MISSION26_GLUCOSE_TOLERANCE:
                    issues.append(f'Keep model-default glucose uptake at oxygen lower bound {bound_value:g}.')
            elif float(glucose_uptake) > MISSION26_EXPECTED_GLUCOSE_UPTAKE + MISSION26_GLUCOSE_TOLERANCE:
                issues.append(f'Glucose uptake exceeds the model-default capacity at oxygen lower bound {bound_value:g}.')

        capacity = abs(float(bound_value))
        if oxygen_uptake is not None:
            if bound_value == MISSION26_NON_BINDING_BOUND:
                if oxygen_uptake <= MISSION26_MIN_OXYGEN_UPTAKE:
                    issues.append('The -25 reference row must retain measurable aerobic oxygen uptake.')
                if oxygen_uptake >= capacity - MISSION26_NON_BINDING_MARGIN:
                    issues.append('The -25 oxygen capacity should be non-binding in both curves.')
            elif abs(float(oxygen_uptake) - capacity) > MISSION26_BOUND_TOLERANCE:
                issues.append(f'Oxygen uptake should reach the tested capacity at lower bound {bound_value:g}.')

        normalised_rows.append({
            'bound_value': float(bound_value),
            'growth_value': _mission26_clean_number(growth) if growth is not None else None,
            'glucose_uptake': _mission26_clean_number(glucose_uptake) if glucose_uptake is not None else None,
            'oxygen_uptake': _mission26_clean_number(oxygen_uptake) if oxygen_uptake is not None else None,
            'method_diagnostics': {
                'method': diagnostics.get('method'),
                'objective_reaction': diagnostics.get('objective_reaction'),
                'primary_objective_flux': _mission26_clean_number(primary) if primary is not None else None,
                'method_score': _mission26_clean_number(method_score) if method_score is not None else None,
                'method_score_name': diagnostics.get('method_score_name'),
                'total_absolute_flux': _mission26_clean_number(total_absolute_flux) if total_absolute_flux is not None else None,
                'active_reaction_count': active_reactions,
            },
        })

    unexpected_keys = sorted(set(row_groups) - set(expected_keys))
    if unexpected_keys:
        issues.append('The visible sweep includes unexpected oxygen lower-bound rows.')

    current_valid = bool(sweep_type and len(normalised_rows) == len(MISSION26_SWEEP_VALUES) and not issues)
    normalised_sweep = None
    if current_valid:
        normalised_sweep = {
            'sweep_type': sweep_type,
            'method': MISSION26_METHOD,
            'objective': MISSION26_GROWTH_OBJECTIVE,
            'knocked_out_genes': [] if sweep_type == 'wild_type' else [MISSION26_TARGET_GENE],
            'reaction_id': MISSION26_SWEEP_REACTION,
            'bound': MISSION26_SWEEP_BOUND,
            'values': list(MISSION26_SWEEP_VALUES),
            'rows': normalised_rows,
        }
    return sweep_type, normalised_sweep, issues


def _mission26_rows_by_bound(rows):
    return {
        _mission26_value_key(row.get('bound_value')): row
        for row in rows or []
        if _mission26_value_key(row.get('bound_value')) is not None
    }


def _mission26_curve_is_monotonic(rows):
    values = [float(row.get('growth_value')) for row in rows or []]
    return bool(values) and all(
        after <= before + MISSION26_MONOTONIC_TOLERANCE
        for before, after in zip(values, values[1:])
    )


def _mission26_relationship(wild_type_sweep, knockout_sweep):
    empty = {
        'matched_points_complete': False,
        'growth_retention_by_bound': {},
        'oxygen_binding_by_bound': {},
        'wild_type_growth_monotonic': False,
        'knockout_growth_monotonic': False,
        'positive_oxygen_growth_retained': False,
        'zero_bound_wild_type_viable': False,
        'zero_bound_knockout_collapsed': False,
        'interaction_threshold_supported': False,
        'threshold_bound': None,
    }
    if not wild_type_sweep or not knockout_sweep:
        return empty

    wt_rows = _mission26_rows_by_bound(wild_type_sweep.get('rows') or [])
    ko_rows = _mission26_rows_by_bound(knockout_sweep.get('rows') or [])
    expected_keys = [_mission26_value_key(value) for value in MISSION26_SWEEP_VALUES]
    matched = all(key in wt_rows and key in ko_rows for key in expected_keys)
    if not matched:
        return empty

    retention = {}
    binding = {}
    for bound_value in MISSION26_SWEEP_VALUES:
        key = _mission26_value_key(bound_value)
        wt = wt_rows[key]
        ko = ko_rows[key]
        wt_growth = float(wt.get('growth_value'))
        ko_growth = float(ko.get('growth_value'))
        retention[str(float(bound_value))] = round(ko_growth / wt_growth, 6) if wt_growth > MISSION26_FLUX_TOLERANCE else None
        capacity = abs(float(bound_value))
        binding[str(float(bound_value))] = {
            'wild_type': bool(bound_value != MISSION26_NON_BINDING_BOUND and abs(float(wt.get('oxygen_uptake')) - capacity) <= MISSION26_BOUND_TOLERANCE),
            'knockout': bool(bound_value != MISSION26_NON_BINDING_BOUND and abs(float(ko.get('oxygen_uptake')) - capacity) <= MISSION26_BOUND_TOLERANCE),
        }

    positive_bounds = [value for value in MISSION26_SWEEP_VALUES if value < 0]
    positive_retained = all(
        float(wt_rows[_mission26_value_key(value)].get('growth_value')) >= MISSION26_MIN_VIABLE_GROWTH
        and float(ko_rows[_mission26_value_key(value)].get('growth_value')) >= MISSION26_MIN_VIABLE_GROWTH
        and float(retention[str(float(value))]) >= MISSION26_MIN_POSITIVE_OXYGEN_RETENTION
        for value in positive_bounds
    )
    zero_key = _mission26_value_key(0.0)
    zero_wt_viable = float(wt_rows[zero_key].get('growth_value')) >= MISSION26_MIN_VIABLE_GROWTH
    zero_ko_collapsed = (
        float(ko_rows[zero_key].get('growth_value')) <= MISSION26_MAX_COLLAPSED_GROWTH
        and float(retention[str(0.0)]) <= MISSION26_MAX_COLLAPSED_RETENTION
    )
    wt_monotonic = _mission26_curve_is_monotonic([wt_rows[key] for key in expected_keys])
    ko_monotonic = _mission26_curve_is_monotonic([ko_rows[key] for key in expected_keys])
    nonbinding = all(
        float(rows[_mission26_value_key(MISSION26_NON_BINDING_BOUND)].get('oxygen_uptake'))
        < abs(MISSION26_NON_BINDING_BOUND) - MISSION26_NON_BINDING_MARGIN
        for rows in (wt_rows, ko_rows)
    )
    threshold_supported = bool(
        matched and positive_retained and zero_wt_viable and zero_ko_collapsed
        and wt_monotonic and ko_monotonic and nonbinding
    )
    return {
        'matched_points_complete': matched,
        'growth_retention_by_bound': retention,
        'oxygen_binding_by_bound': binding,
        'wild_type_growth_monotonic': wt_monotonic,
        'knockout_growth_monotonic': ko_monotonic,
        'positive_oxygen_growth_retained': positive_retained,
        'zero_bound_wild_type_viable': zero_wt_viable,
        'zero_bound_knockout_collapsed': zero_ko_collapsed,
        'interaction_threshold_supported': threshold_supported,
        'threshold_bound': 0.0 if threshold_supported else None,
    }


def _build_mission26_data(sweep_data=None, existing_report=None):
    existing_report = existing_report or {}
    if existing_report.get('mission_id') != '26' or existing_report.get('check_version') != MISSION26_CHECK_VERSION:
        existing_report = _mission26_empty_report()

    sweep_type, normalised_sweep, issues = _mission26_validate_sweep(sweep_data)
    current_valid = normalised_sweep is not None and not issues
    current_recorded = False

    wild_type_sweep = copy.deepcopy(existing_report.get('wild_type_sweep'))
    knockout_sweep = copy.deepcopy(existing_report.get('knockout_sweep'))
    if current_valid and sweep_type == 'wild_type':
        wild_type_sweep = normalised_sweep
        current_recorded = True
    elif current_valid and sweep_type == 'knockout':
        knockout_sweep = normalised_sweep
        current_recorded = True

    curves_complete = bool(wild_type_sweep and knockout_sweep)
    relation = _mission26_relationship(wild_type_sweep, knockout_sweep)
    evidence_ready = bool(curves_complete and relation.get('interaction_threshold_supported'))
    missing_sweeps = []
    if not wild_type_sweep:
        missing_sweeps.append('wild_type')
    if not knockout_sweep:
        missing_sweeps.append('knockout')

    report = _mission26_empty_report()
    report.update({
        'wild_type_sweep': wild_type_sweep,
        'knockout_sweep': knockout_sweep,
        'wild_type_sweep_rows': copy.deepcopy((wild_type_sweep or {}).get('rows') or []),
        'knockout_sweep_rows': copy.deepcopy((knockout_sweep or {}).get('rows') or []),
        'recorded_sweep_count': int(bool(wild_type_sweep)) + int(bool(knockout_sweep)),
        'missing_sweeps': missing_sweeps,
        'curves_complete': curves_complete,
        **relation,
        'evidence_ready': evidence_ready,
        'answer_ready': evidence_ready,
        'ready_to_deliver': evidence_ready,
        'current_sweep_type': sweep_type,
        'current_sweep_valid': current_valid,
        'current_sweep_recorded': current_recorded,
        'current_issues': list(issues),
        'latest_attempt': {
            'sweep_type': sweep_type,
            'values': list((sweep_data or {}).get('values') or []),
            'valid': current_valid,
            'recorded': current_recorded,
            'issues': list(issues),
        },
    })
    save_mission26_bound_sweep_check(report)
    return report


def run_mission26_interaction_curve_check(sweep_data=None):
    """Validate one visible sweep and preserve any previously valid companion curve."""
    if sweep_data is None:
        sweep_data = load_bound_sweep()
    return _build_mission26_data(
        sweep_data=sweep_data,
        existing_report=load_mission26_bound_sweep_check() or {},
    )


def run_mission26_interaction_curve_check_remote(backend_url, sweep_data=None):
    """Browser parity wrapper: the remote solver has already produced the visible rows."""
    del backend_url
    return run_mission26_interaction_curve_check(sweep_data)


# Backwards-compatible alias retained for older window imports and saves.
def run_mission26_bound_sweep_check(sweep_data=None):
    return run_mission26_interaction_curve_check(sweep_data)


def normalise_mission26_answer(answer):
    text = unicodedata.normalize('NFKD', str(answer or '')).encode('ascii', 'ignore').decode('ascii').lower().strip()
    if re.search(r'(?<![\d.])0(?:\.0+)?(?![\d.])', text):
        return 0.0
    accepted_phrases = (
        'zero',
        'lower bound zero',
        'lower bound at zero',
        'lb zero',
        'complete oxygen block',
        'oxygen blocked',
        'full oxygen block',
        'full block',
        'bloqueio completo',
        'oxigenio bloqueado',
        'bloqueio de oxigenio',
    )
    if any(phrase in text for phrase in accepted_phrases):
        return 0.0
    return None


def mission26_answer_matches(answer, report_data=None):
    report_data = report_data if report_data is not None else (load_mission26_bound_sweep_check() or {})
    return bool(
        report_data.get('mission_id') == '26'
        and report_data.get('check_version') == MISSION26_CHECK_VERSION
        and report_data.get('answer_ready')
        and report_data.get('interaction_threshold_supported')
        and normalise_mission26_answer(answer) == 0.0
    )


def build_mission26_interaction_report_text(report):
    if not report:
        return (
            'Prepare two matched oxygen-response curves for wild type and the highlighted b3956 / ppc knockout. '
            'Keep the FBA biomass setup and base environment unchanged while sweeping only oxygen uptake capacity.\n\n'
            'The visible rows must record growth, glucose uptake, oxygen uptake and FBA diagnostics at lower bounds -25, -10, -1 and 0. '
            'Activate the mission when you are ready to construct both curves.'
        )
    if report.get('mission_id') != '26' or report.get('check_version') != MISSION26_CHECK_VERSION:
        return 'Mission 26 Genotype-Environment Interaction Curve\n\nCurrent-format curve evidence has not been recorded yet.'

    lines = [
        'Mission 26 Genotype-Environment Interaction Curve',
        '',
        'Controlled matched protocol:',
        '- FBA biomass objective; model-default base environment',
        f'- Curves: wild type and single {MISSION26_TARGET_GENE} / {MISSION26_TARGET_GENE_NAME} knockout',
        '- Sweep only the EX_o2_e lower bound: -25, -10, -1, 0',
        '- Every row includes numeric glucose/oxygen exchange and FBA diagnostics',
        '',
        f"Curves recorded: {report.get('recorded_sweep_count', 0)}/{report.get('required_sweep_count', 2)}",
    ]

    def append_curve(title, rows):
        lines.extend(['', title])
        if not rows:
            lines.append('- pending')
            return
        lines.append('LB | growth | glucose uptake | O2 uptake | total abs flux | active reactions')
        for row in rows:
            diagnostics = row.get('method_diagnostics') or {}
            lines.append(
                f"{float(row.get('bound_value')):.0f} | "
                f"{float(row.get('growth_value')):.3f} | "
                f"{float(row.get('glucose_uptake')):.3f} | "
                f"{float(row.get('oxygen_uptake')):.3f} | "
                f"{float(diagnostics.get('total_absolute_flux')):.3f} | "
                f"{int(diagnostics.get('active_reaction_count'))}"
            )

    append_curve('Wild-type oxygen sweep:', report.get('wild_type_sweep_rows') or [])
    append_curve(f'{MISSION26_TARGET_GENE} knockout oxygen sweep:', report.get('knockout_sweep_rows') or [])

    retention = report.get('growth_retention_by_bound') or {}
    if retention:
        lines.extend(['', 'Knockout-to-wild-type growth retention:'])
        for bound_value in MISSION26_SWEEP_VALUES:
            value = retention.get(str(float(bound_value)))
            lines.append(
                f"- LB {bound_value:g}: {float(value) * 100.0:.1f}%"
                if value is not None else f"- LB {bound_value:g}: unavailable"
            )

    if report.get('missing_sweeps'):
        lines.append('Missing curves: ' + ', '.join(report.get('missing_sweeps') or []))

    if report.get('current_sweep_recorded'):
        lines.extend(['', f"Latest valid visible curve recorded: {report.get('current_sweep_type')}."])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest sweep was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if report.get('wild_type_sweep') or report.get('knockout_sweep'):
            lines.append('Previously valid Mission 26 curve evidence remains available.')

    lines.append('')
    if report.get('evidence_ready'):
        lines.extend([
            'Evidence complete.',
            'Compare matched wild-type and knockout growth at every tested oxygen capacity.',
            'Question: At which tested oxygen lower-bound value does knockout growth collapse while wild-type growth remains viable?',
        ])
    else:
        lines.append('Evidence incomplete.')

    lines.extend([
        '',
        'Interpretation note: the first point tests a non-binding oxygen capacity; the remaining points test progressively tighter capacities.',
        'The threshold is conditional on this model, biomass objective, medium, genotype and tested bound values.',
        'All growth, exchange and FBA diagnostic values come from the visible Bound Sweep results. No hidden validation simulation is used.',
    ])
    return '\n'.join(lines)

def is_mission27_unlocked(missions_completed):
    """Mission 27 starts only after Dr. Smith's final interaction-curve mission."""
    return '26' in (missions_completed or [])


def _mission27_number_or_none(value):
    numeric = _as_float_or_none(value)
    return float(numeric) if numeric is not None else None


def _mission27_clean_number(value, decimals=6):
    numeric = float(value)
    if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
        numeric = 0.0
    return round(numeric, decimals)


def _mission27_disabled_reactions(knocked_out_genes):
    """Return deterministic GPR-disabled reactions without launching a simulation."""
    knocked_out_genes = sorted(knocked_out_genes or [])
    if not knocked_out_genes:
        return []
    try:
        if model is not None:
            return sorted(disabled_reaction_ids(model, knocked_out_genes))
    except Exception:
        pass
    if knocked_out_genes == [MISSION27_TARGET_GENE]:
        return [MISSION27_TARGET_REACTION]
    return []


def _mission27_environment_status(reactions):
    """Classify the exact default medium or one-candidate supplementation setup."""
    bounds_complete = True
    changes = []
    candidate = None

    for index in range(len(REACTIONS.index)):
        reaction_id = REACTIONS.index[index]
        lower_open, upper_open = _reaction_bound_open_states(reactions, index)
        if lower_open is None or upper_open is None:
            bounds_complete = False
            continue

        default_lower_open = bool(REACTIONS.lb.iloc[index] != 0)
        default_upper_open = bool(REACTIONS.ub.iloc[index] != 0)
        lower_changed = bool(lower_open) != default_lower_open
        upper_changed = bool(upper_open) != default_upper_open
        if lower_changed:
            changes.append((reaction_id, 'lower', bool(lower_open)))
        if upper_changed:
            changes.append((reaction_id, 'upper', bool(upper_open)))

    if bounds_complete and len(changes) == 1:
        reaction_id, bound, is_open = changes[0]
        if reaction_id in MISSION27_CANDIDATE_SUPPLEMENTS and bound == 'lower' and is_open:
            candidate = reaction_id

    setup_type = None
    if bounds_complete and not changes:
        setup_type = 'default'
    elif bounds_complete and candidate is not None:
        setup_type = 'candidate'

    return {
        'bounds_complete': bounds_complete,
        'changes': [f'{reaction_id} {bound}' for reaction_id, bound, _is_open in changes],
        'candidate': candidate,
        'setup_type': setup_type,
        'controlled_environment': bool(setup_type),
    }


def _mission27_empty_report():
    return {
        'mission_id': '27',
        'check_version': MISSION27_CHECK_VERSION,
        'mission_title': 'Metabolic Bypass Rescue',
        'target_context': MISSION27_TARGET_CONTEXT,
        'target_method': MISSION27_METHOD,
        'growth_objective': MISSION27_GROWTH_OBJECTIVE,
        'target_gene': MISSION27_TARGET_GENE,
        'target_gene_name': MISSION27_TARGET_GENE_NAME,
        'target_reaction': MISSION27_TARGET_REACTION,
        'candidate_supplements': list(MISSION27_CANDIDATE_SUPPLEMENTS),
        'candidate_names': copy.deepcopy(MISSION27_CANDIDATE_NAMES),
        'wild_type_reference': None,
        'knockout_reference': None,
        'candidate_trials': {},
        'recorded_run_count': 0,
        'required_run_count': MISSION27_REQUIRED_RUN_COUNT,
        'missing_conditions': ['wild_type_reference', 'knockout_reference'] + list(MISSION27_CANDIDATE_SUPPLEMENTS),
        'rescue_candidates': [],
        'unique_rescue_supported': False,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_run_type': None,
        'current_candidate': None,
        'current_run_valid': False,
        'current_run_recorded': False,
        'current_issues': [],
        'current_run': None,
        'latest_attempt': None,
    }


def initialise_mission27_rescue_screen():
    report = _mission27_empty_report()
    save_mission27_rescue_check(report)
    return report


def _build_mission27_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
):
    """Validate and accumulate one visible Mission 27 reference or candidate run."""
    existing_report = existing_report or {}
    if (
        existing_report.get('mission_id') != '27'
        or existing_report.get('check_version') != MISSION27_CHECK_VERSION
    ):
        existing_report = _mission27_empty_report()

    wild_type_reference = copy.deepcopy(existing_report.get('wild_type_reference'))
    knockout_reference = copy.deepcopy(existing_report.get('knockout_reference'))
    candidate_trials = copy.deepcopy(existing_report.get('candidate_trials') or {})

    environment = _mission27_environment_status(reactions)
    knocked_out_genes = sorted(_knocked_out_genes(genes))
    disabled_reactions = _mission27_disabled_reactions(knocked_out_genes)
    target_reaction_disabled = MISSION27_TARGET_REACTION in disabled_reactions

    run_type = None
    candidate = environment.get('candidate')
    if environment.get('setup_type') == 'default' and not knocked_out_genes:
        run_type = 'wild_type_reference'
    elif environment.get('setup_type') == 'default' and knocked_out_genes == [MISSION27_TARGET_GENE]:
        run_type = 'knockout_reference'
    elif environment.get('setup_type') == 'candidate' and knocked_out_genes == [MISSION27_TARGET_GENE]:
        run_type = 'candidate_trial'

    objective_numeric = _mission27_number_or_none(objective_result)
    result_infeasible = 'INFEASIBLE' in str(objective_result or '').upper()
    raw_fluxes, uptake_fluxes, _secretion_fluxes = _mission21_measured_medium_values(medium_fluxes)
    diagnostics = _method_diagnostics_from_production_data(production_fluxes)
    biomass_raw = _mission27_number_or_none(_mission13_biomass_value(production_fluxes))
    primary_flux = _mission27_number_or_none(diagnostics.get('primary_objective_flux'))
    method_score = _mission27_number_or_none(diagnostics.get('method_score'))
    total_absolute_flux = _mission27_number_or_none(diagnostics.get('total_absolute_flux'))
    method_score_name = diagnostics.get('method_score_name')
    try:
        active_reaction_count = int(diagnostics.get('active_reaction_count'))
    except Exception:
        active_reaction_count = None

    glucose_raw = _mission27_number_or_none(raw_fluxes.get(MISSION27_GLUCOSE_REACTION))
    oxygen_raw = _mission27_number_or_none(raw_fluxes.get(MISSION27_OXYGEN_REACTION))
    glucose_uptake = _mission27_number_or_none(uptake_fluxes.get(MISSION27_GLUCOSE_REACTION))
    oxygen_uptake = _mission27_number_or_none(uptake_fluxes.get(MISSION27_OXYGEN_REACTION))
    candidate_raw = _mission27_number_or_none(raw_fluxes.get(candidate)) if candidate else None
    candidate_uptake = _mission27_number_or_none(uptake_fluxes.get(candidate)) if candidate else None

    issues = []
    if objective_error:
        issues.append(objective_error)
    if method_name != MISSION27_METHOD:
        issues.append('Use pFBA for every Mission 27 reference and candidate trial.')
    if selected_objective != MISSION27_GROWTH_OBJECTIVE:
        issues.append('Use the biomass objective for every Mission 27 run.')
    if not environment.get('bounds_complete'):
        issues.append('The environmental-bound payload is incomplete.')
    if environment.get('setup_type') is None:
        issues.append('Use either the completely default medium or open exactly one Mission 27 candidate lower bound.')
    if run_type is None:
        issues.append(
            f'Use wild type only for the default reference, or keep exactly {MISSION27_TARGET_GENE} / '
            f'{MISSION27_TARGET_GENE_NAME} knocked out for the knockout reference and every candidate trial.'
        )
    if run_type in {'knockout_reference', 'candidate_trial'} and not target_reaction_disabled:
        issues.append(f'The {MISSION27_TARGET_GENE} knockout must keep {MISSION27_TARGET_REACTION} disabled by the GPR.')
    if run_type == 'wild_type_reference' and disabled_reactions:
        issues.append('The wild-type reference must not contain GPR-disabled reactions.')

    if result_infeasible or objective_numeric is None:
        issues.append('Mission 27 requires a numeric visible biomass result; an infeasible result is not a measured zero-growth solution.')
    elif objective_numeric < -MISSION27_PRIMARY_TOLERANCE:
        issues.append('The biomass result is outside the valid non-negative range.')

    required_medium = [MISSION27_GLUCOSE_REACTION, MISSION27_OXYGEN_REACTION]
    if candidate:
        required_medium.append(candidate)
    missing_medium = [reaction_id for reaction_id in required_medium if reaction_id not in raw_fluxes]
    if medium_fluxes and medium_fluxes.get('error'):
        issues.append('The Exchange Flux Report is unavailable for this run.')
    elif missing_medium:
        issues.append('Numeric glucose, oxygen and selected-candidate exchange evidence is required.')

    if glucose_raw is not None and glucose_uptake is not None:
        if glucose_raw > MISSION27_FLUX_TOLERANCE:
            issues.append('Glucose must not be secreted in the controlled rescue screen.')
        if glucose_uptake > MISSION27_EXPECTED_DEFAULT_UPTAKE + MISSION27_CAPACITY_TOLERANCE:
            issues.append('Glucose uptake exceeds the model-default capacity.')
    if oxygen_raw is not None and oxygen_uptake is not None:
        if oxygen_raw > MISSION27_FLUX_TOLERANCE:
            issues.append('Oxygen must not be secreted in the controlled rescue screen.')
    if candidate_raw is not None and candidate_uptake is not None:
        if candidate_raw > MISSION27_FLUX_TOLERANCE:
            issues.append('The selected candidate must be consumed rather than secreted.')
        if candidate_uptake > MISSION27_EXPECTED_SUPPLEMENT_CAPACITY + MISSION27_CAPACITY_TOLERANCE:
            issues.append('Candidate uptake exceeds the controlled supplementation capacity.')

    if not isinstance(production_fluxes, dict) or production_fluxes.get('error'):
        issues.append('The visible result is missing biomass and method-aware diagnostics.')
    if biomass_raw is None:
        issues.append('The visible result is missing the biomass-reaction flux.')
    if primary_flux is None:
        issues.append('The visible pFBA result is missing the primary objective flux.')
    if objective_numeric is not None and biomass_raw is not None:
        if abs(objective_numeric - biomass_raw) > MISSION27_PRIMARY_TOLERANCE:
            issues.append('The displayed objective value does not match the biomass-reaction flux.')
    if biomass_raw is not None and primary_flux is not None:
        if abs(biomass_raw - primary_flux) > MISSION27_PRIMARY_TOLERANCE:
            issues.append('The primary objective diagnostic does not match biomass.')
    if diagnostics.get('method') != MISSION27_METHOD:
        issues.append('The method diagnostic does not identify pFBA.')
    if diagnostics.get('objective_reaction') != MISSION27_GROWTH_OBJECTIVE:
        issues.append('The method diagnostic does not identify the biomass objective.')
    if method_score_name != MISSION27_EXPECTED_SCORE_NAME:
        issues.append('The pFBA secondary-score meaning is missing or incorrect.')
    if method_score is None or total_absolute_flux is None:
        issues.append('The visible pFBA secondary score or total absolute flux is missing.')
    elif abs(method_score - total_absolute_flux) > MISSION27_PRIMARY_TOLERANCE:
        issues.append('The pFBA method score does not match total absolute flux.')
    if active_reaction_count is None:
        issues.append('The visible pFBA result is missing the active-reaction diagnostic.')

    if objective_numeric is not None:
        if run_type == 'wild_type_reference':
            if objective_numeric < MISSION27_MIN_REFERENCE_GROWTH:
                issues.append('The wild-type default reference must retain clear positive growth.')
            if glucose_uptake is not None and abs(glucose_uptake - MISSION27_EXPECTED_DEFAULT_UPTAKE) > MISSION27_CAPACITY_TOLERANCE:
                issues.append('The wild-type reference must use the model-default glucose uptake capacity.')
            if oxygen_uptake is not None and oxygen_uptake < MISSION27_MIN_AEROBIC_OXYGEN_UPTAKE:
                issues.append('The wild-type reference must show measurable oxygen uptake.')
        elif run_type == 'knockout_reference':
            if objective_numeric > MISSION27_MAX_KNOCKOUT_GROWTH:
                issues.append('The default gltA knockout reference should show no predicted growth.')
        elif run_type == 'candidate_trial':
            if candidate == MISSION27_EXPECTED_RESCUE:
                if objective_numeric < MISSION27_MIN_RESCUE_GROWTH:
                    issues.append('The expected rescue trial does not restore clear positive growth.')
                if candidate_uptake is not None and candidate_uptake < MISSION27_MIN_RESCUE_UPTAKE:
                    issues.append('The rescue candidate is not measurably consumed.')
                if glucose_uptake is not None and abs(glucose_uptake - MISSION27_EXPECTED_DEFAULT_UPTAKE) > MISSION27_CAPACITY_TOLERANCE:
                    issues.append('Keep model-default glucose availability in the rescue trial.')
                if oxygen_uptake is not None and oxygen_uptake < MISSION27_MIN_AEROBIC_OXYGEN_UPTAKE:
                    issues.append('The rescue trial must retain measurable oxygen uptake.')
            elif objective_numeric > MISSION27_MAX_NON_RESCUE_GROWTH:
                issues.append('This candidate unexpectedly restores growth above the non-rescue tolerance.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run = None
    if current_run_valid:
        current_run = {
            'run_type': run_type,
            'candidate': candidate,
            'candidate_name': MISSION27_CANDIDATE_NAMES.get(candidate) if candidate else None,
            'method': method_name,
            'objective': selected_objective,
            'growth': _mission27_clean_number(objective_numeric),
            'knocked_out_genes': list(knocked_out_genes),
            'disabled_reactions': list(disabled_reactions),
            'target_reaction_disabled': bool(target_reaction_disabled),
            'environment_changes': list(environment.get('changes') or []),
            'glucose_raw_flux': _mission27_clean_number(glucose_raw),
            'glucose_uptake': _mission27_clean_number(glucose_uptake),
            'oxygen_raw_flux': _mission27_clean_number(oxygen_raw),
            'oxygen_uptake': _mission27_clean_number(oxygen_uptake),
            'candidate_raw_flux': _mission27_clean_number(candidate_raw) if candidate_raw is not None else None,
            'candidate_uptake': _mission27_clean_number(candidate_uptake) if candidate_uptake is not None else None,
            'method_diagnostics': {
                'method': diagnostics.get('method'),
                'objective_reaction': diagnostics.get('objective_reaction'),
                'primary_objective_flux': _mission27_clean_number(primary_flux),
                'method_score': _mission27_clean_number(method_score),
                'method_score_name': method_score_name,
                'total_absolute_flux': _mission27_clean_number(total_absolute_flux),
                'active_reaction_count': active_reaction_count,
            },
        }
        if run_type == 'wild_type_reference':
            wild_type_reference = current_run
        elif run_type == 'knockout_reference':
            knockout_reference = current_run
        elif run_type == 'candidate_trial':
            candidate_trials[candidate] = current_run
        current_run_recorded = True

    missing_conditions = []
    if not isinstance(wild_type_reference, dict):
        missing_conditions.append('wild_type_reference')
    if not isinstance(knockout_reference, dict):
        missing_conditions.append('knockout_reference')
    missing_conditions.extend(
        candidate for candidate in MISSION27_CANDIDATE_SUPPLEMENTS
        if not isinstance(candidate_trials.get(candidate), dict)
    )
    recorded_run_count = MISSION27_REQUIRED_RUN_COUNT - len(missing_conditions)
    evidence_ready = not missing_conditions

    rescue_candidates = []
    if evidence_ready:
        for candidate_id in MISSION27_CANDIDATE_SUPPLEMENTS:
            growth = _mission27_number_or_none((candidate_trials.get(candidate_id) or {}).get('growth'))
            if growth is not None and growth >= MISSION27_MIN_RESCUE_GROWTH:
                rescue_candidates.append(candidate_id)
    unique_rescue_supported = bool(
        evidence_ready
        and rescue_candidates == [MISSION27_EXPECTED_RESCUE]
        and _mission27_number_or_none((wild_type_reference or {}).get('growth')) >= MISSION27_MIN_REFERENCE_GROWTH
        and _mission27_number_or_none((knockout_reference or {}).get('growth')) <= MISSION27_MAX_KNOCKOUT_GROWTH
        and all(
            bool((candidate_trials.get(candidate_id) or {}).get('target_reaction_disabled'))
            for candidate_id in MISSION27_CANDIDATE_SUPPLEMENTS
        )
    )

    latest_attempt = {
        'method': method_name,
        'objective': selected_objective,
        'run_type': run_type,
        'candidate': candidate,
        'knocked_out_genes': list(knocked_out_genes),
        'valid': current_run_valid,
        'recorded': current_run_recorded,
        'issues': list(issues),
    }

    report = _mission27_empty_report()
    report.update({
        'wild_type_reference': wild_type_reference,
        'knockout_reference': knockout_reference,
        'candidate_trials': candidate_trials,
        'recorded_run_count': recorded_run_count,
        'missing_conditions': missing_conditions,
        'rescue_candidates': rescue_candidates,
        'unique_rescue_supported': unique_rescue_supported,
        'evidence_ready': evidence_ready,
        'answer_ready': unique_rescue_supported,
        'ready_to_deliver': unique_rescue_supported,
        'current_run_type': run_type,
        'current_candidate': candidate,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_issues': list(issues),
        'current_run': current_run,
        'latest_attempt': latest_attempt,
    })
    save_mission27_rescue_check(report)
    return report


def run_mission27_rescue_check(simulation_results=None):
    """Validate the already visible Mission 27 result without re-simulating."""
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible Mission 27 simulation before recording evidence.'
    except Exception:
        objective_error = 'Could not read the current visible Mission 27 simulation result.'

    return _build_mission27_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission27_rescue_check() or {},
        objective_error=objective_error,
    )


def run_mission27_rescue_check_remote(backend_url, simulation_results=None):
    """Browser parity wrapper using the same already returned visible result."""
    del backend_url
    return run_mission27_rescue_check(simulation_results)


def _normalise_mission27_text(value):
    text = str(value or '').replace('α', 'alpha').replace('Α', 'alpha')
    text = unicodedata.normalize('NFKD', text)
    return ''.join(char for char in text if not unicodedata.combining(char)).lower().strip()


def normalise_mission27_answer(answer):
    text = _normalise_mission27_text(answer)
    if not text:
        return None
    patterns = (
        r'\bex[_\s-]*akg[_\s-]*e\b',
        r'\b(?:2|two)[-\s]*(?:oxo|keto)glutarate\b',
        r'\balpha[-\s]*ketoglutarate\b',
        r'\bakg\b',
        r'\b2og\b',
    )
    return MISSION27_EXPECTED_RESCUE if any(re.search(pattern, text) for pattern in patterns) else None


def mission27_answer_matches(answer, report_data=None):
    report = report_data if report_data is not None else (load_mission27_rescue_check() or {})
    return bool(
        report.get('mission_id') == '27'
        and report.get('check_version') == MISSION27_CHECK_VERSION
        and report.get('answer_ready')
        and report.get('unique_rescue_supported')
        and normalise_mission27_answer(answer) == MISSION27_EXPECTED_RESCUE
    )


def build_mission27_rescue_report_text(report_data=None):
    report = report_data or {}
    if report.get('mission_id') != '27' or report.get('check_version') != MISSION27_CHECK_VERSION:
        return (
            'Mission 27 Metabolic Bypass Rescue\n\n'
            'Record a default wild-type reference, a default b0720 / gltA knockout reference, and five single-supplement knockout trials. '
            'Use pFBA with the biomass objective and keep every unrelated environmental bound at model default.'
        )

    def fmt(value):
        return 'pending' if value is None else f'{float(value):.3f}'

    lines = [
        'Mission 27 Metabolic Bypass Rescue',
        '',
        'Controlled protocol:',
        f'- Method: {MISSION27_METHOD}',
        f'- Objective: {MISSION27_GROWTH_OBJECTIVE}',
        f'- Genetic lesion: {MISSION27_TARGET_GENE} / {MISSION27_TARGET_GENE_NAME}',
        f'- GPR-disabled reaction in knockout runs: {MISSION27_TARGET_REACTION}',
        '- Candidate trials: open exactly one candidate lower bound while keeping glucose, oxygen and every unrelated bound at model default',
        '',
        f"Runs recorded: {report.get('recorded_run_count', 0)}/{report.get('required_run_count', MISSION27_REQUIRED_RUN_COUNT)}",
        '',
    ]

    for key, title in (
        ('wild_type_reference', 'Wild-type default reference'),
        ('knockout_reference', f'{MISSION27_TARGET_GENE} knockout default reference'),
    ):
        run = report.get(key)
        if not isinstance(run, dict):
            lines.append(f'{title}: pending')
            continue
        lines.extend([
            title + ':',
            f"- Growth: {fmt(run.get('growth'))}",
            f"- Glucose uptake: {fmt(run.get('glucose_uptake'))}",
            f"- Oxygen uptake: {fmt(run.get('oxygen_uptake'))}",
            f"- {MISSION27_TARGET_REACTION} disabled: {'yes' if run.get('target_reaction_disabled') else 'no'}",
        ])

    lines.extend(['', 'Candidate supplementation trials:', 'Candidate | growth | candidate uptake | CS disabled'])
    trials = report.get('candidate_trials') or {}
    for candidate_id in MISSION27_CANDIDATE_SUPPLEMENTS:
        trial = trials.get(candidate_id)
        if not isinstance(trial, dict):
            lines.append(f'{candidate_id} | pending | pending | pending')
            continue
        lines.append(
            f"{candidate_id} | {fmt(trial.get('growth'))} | {fmt(trial.get('candidate_uptake'))} | "
            f"{'yes' if trial.get('target_reaction_disabled') else 'no'}"
        )

    if report.get('current_run_recorded'):
        label = report.get('current_run_type')
        if report.get('current_candidate'):
            label += f" ({report.get('current_candidate')})"
        lines.extend(['', f'Latest valid visible run recorded: {label}.'])
    elif report.get('current_issues'):
        lines.extend(['', 'Latest run was not recorded:'])
        lines.extend(f'- {issue}' for issue in report.get('current_issues') or [])
        if report.get('recorded_run_count'):
            lines.append('Previously valid Mission 27 rescue evidence remains available.')

    lines.append('')
    if report.get('evidence_ready'):
        lines.extend([
            'Evidence complete.',
            'Compare all candidate growth values while confirming that the knockout-defined reaction remains disabled.',
            'Question: Which candidate exchange restored predicted growth while citrate synthase remained disabled?',
        ])
        if not report.get('unique_rescue_supported'):
            lines.append('The current complete evidence does not support one unique rescue under the controlled criteria; verify the visible runs.')
    else:
        lines.append('Evidence incomplete.')
        if report.get('missing_conditions'):
            lines.append('Missing conditions: ' + ', '.join(report.get('missing_conditions') or []))

    lines.extend([
        '',
        'Interpretation note: environmental rescue bypasses the predicted consequence of the knockout; it does not restore the deleted gene or citrate synthase reaction.',
        'The conclusion is conditional on this model, pFBA biomass objective, medium, bounds and tested candidate set.',
        'All growth, exchange and pFBA diagnostic values come from visible simulation results. No hidden validation simulation is used.',
    ])
    return '\n'.join(lines)


# Backwards-compatible names retained for stale imports. Mission 27 no longer
# uses Bound Sweep; these aliases now expose the redesigned rescue report.
def run_mission27_bound_sweep_check(sweep_data=None):
    del sweep_data
    return load_mission27_rescue_check() or _mission27_empty_report()


def _build_mission27_text(report_data=None):
    return build_mission27_rescue_report_text(report_data)


def is_mission28_unlocked(missions_completed):
    """Mission 28 is Dr. Ribeiro's second mission and requires Mission 27."""
    return '27' in (missions_completed or [])


def _mission28_number_or_none(value):
    numeric = _as_float_or_none(value)
    return float(numeric) if numeric is not None else None


def _mission28_clean_number(value, decimals=6):
    numeric = float(value)
    if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
        numeric = 0.0
    return round(numeric, decimals)


def _mission28_disabled_reactions(knocked_out_genes):
    """Evaluate GPR consequences without running a metabolic optimisation."""
    knocked_out_genes = sorted(knocked_out_genes or [])
    if not knocked_out_genes:
        return []
    try:
        if model is not None:
            return sorted(disabled_reaction_ids(model, knocked_out_genes))
    except Exception:
        pass

    disabled = []
    if MISSION28_PRIMARY_GENE in knocked_out_genes:
        disabled.append(MISSION28_PRIMARY_REACTION)
    for gene_id, reaction_id in MISSION28_SECONDARY_REACTIONS.items():
        if gene_id in knocked_out_genes:
            disabled.append(reaction_id)
    return sorted(set(disabled))


def _mission28_environment_status(reactions):
    """Require exactly the Mission 27 rescue medium: only EX_akg_e uptake open."""
    status = _mission27_environment_status(reactions)
    rescue_medium_ready = bool(
        status.get('bounds_complete')
        and status.get('setup_type') == 'candidate'
        and status.get('candidate') == MISSION28_RESCUE_SUPPLEMENT
    )
    return {
        'bounds_complete': bool(status.get('bounds_complete')),
        'changes': list(status.get('changes') or []),
        'candidate': status.get('candidate'),
        'setup_type': status.get('setup_type'),
        'rescue_medium_ready': rescue_medium_ready,
    }


def _mission28_reference_from_mission27(mission27_report=None):
    """Reuse the player's persisted visible rescue run; never re-simulate it."""
    report = mission27_report or {}
    if (
        report.get('mission_id') != '27'
        or report.get('check_version') != MISSION27_CHECK_VERSION
        or not report.get('unique_rescue_supported')
        or not report.get('evidence_ready')
    ):
        return None

    trial = copy.deepcopy((report.get('candidate_trials') or {}).get(MISSION28_RESCUE_SUPPLEMENT))
    if not isinstance(trial, dict):
        return None
    growth = _mission28_number_or_none(trial.get('growth'))
    uptake = _mission28_number_or_none(trial.get('candidate_uptake'))
    knocked_out = sorted(trial.get('knocked_out_genes') or [])
    disabled = sorted(trial.get('disabled_reactions') or [])
    if (
        growth is None
        or uptake is None
        or growth < MISSION28_MIN_REFERENCE_GROWTH
        or uptake < MISSION28_MIN_REFERENCE_SUPPLEMENT_UPTAKE
        or knocked_out != [MISSION28_PRIMARY_GENE]
        or MISSION28_PRIMARY_REACTION not in disabled
        or trial.get('method') != MISSION28_METHOD
        or trial.get('objective') != MISSION28_GROWTH_OBJECTIVE
    ):
        return None

    return {
        'run_type': 'rescue_reference',
        'source': 'mission27_visible_evidence',
        'method': trial.get('method'),
        'objective': trial.get('objective'),
        'growth': _mission28_clean_number(growth),
        'knocked_out_genes': list(knocked_out),
        'disabled_reactions': list(disabled),
        'primary_reaction_disabled': True,
        'environment_changes': list(trial.get('environment_changes') or []),
        'glucose_raw_flux': trial.get('glucose_raw_flux'),
        'glucose_uptake': trial.get('glucose_uptake'),
        'oxygen_raw_flux': trial.get('oxygen_raw_flux'),
        'oxygen_uptake': trial.get('oxygen_uptake'),
        'supplement_raw_flux': trial.get('candidate_raw_flux'),
        'supplement_uptake': _mission28_clean_number(uptake),
        'method_diagnostics': copy.deepcopy(trial.get('method_diagnostics') or {}),
    }


def _mission28_empty_report(mission27_report=None):
    imported_reference = _mission28_reference_from_mission27(mission27_report)
    missing = list(MISSION28_SECONDARY_GENES)
    if imported_reference is None:
        missing.insert(0, 'rescue_reference')
    return {
        'mission_id': '28',
        'check_version': MISSION28_CHECK_VERSION,
        'mission_title': 'Bypass Dependency Mapping',
        'target_context': MISSION28_TARGET_CONTEXT,
        'target_method': MISSION28_METHOD,
        'growth_objective': MISSION28_GROWTH_OBJECTIVE,
        'primary_gene': MISSION28_PRIMARY_GENE,
        'primary_gene_name': MISSION28_PRIMARY_GENE_NAME,
        'primary_reaction': MISSION28_PRIMARY_REACTION,
        'rescue_supplement': MISSION28_RESCUE_SUPPLEMENT,
        'rescue_supplement_name': MISSION28_RESCUE_SUPPLEMENT_NAME,
        'secondary_genes': list(MISSION28_SECONDARY_GENES),
        'secondary_gene_names': copy.deepcopy(MISSION28_SECONDARY_GENE_NAMES),
        'secondary_reactions': copy.deepcopy(MISSION28_SECONDARY_REACTIONS),
        'rescue_reference': imported_reference,
        'reference_imported_from_mission27': imported_reference is not None,
        'secondary_trials': {},
        'recorded_run_count': 1 if imported_reference is not None else 0,
        'required_run_count': MISSION28_REQUIRED_RUN_COUNT,
        'missing_conditions': missing,
        'growth_retention_by_candidate': {},
        'supplement_uptake_by_candidate': {},
        'dependency_candidates': [],
        'unique_dependency_candidate': None,
        'unique_transport_dependency_supported': False,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_run_type': None,
        'current_candidate': None,
        'current_run_valid': False,
        'current_run_recorded': False,
        'current_issues': [],
        'current_run': None,
        'latest_attempt': None,
    }


def initialise_mission28_dependency_screen(mission27_report=None):
    report = _mission28_empty_report(mission27_report)
    save_mission28_dependency_check(report)
    return report


def _build_mission28_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    mission27_report=None,
    objective_error=None,
):
    """Validate and accumulate one visible rescue-reference or double-KO run."""
    existing_report = existing_report or {}
    if (
        existing_report.get('mission_id') != '28'
        or existing_report.get('check_version') != MISSION28_CHECK_VERSION
    ):
        existing_report = _mission28_empty_report(mission27_report)

    rescue_reference = copy.deepcopy(existing_report.get('rescue_reference'))
    secondary_trials = copy.deepcopy(existing_report.get('secondary_trials') or {})
    reference_imported = bool(existing_report.get('reference_imported_from_mission27'))

    environment = _mission28_environment_status(reactions)
    knocked_out_genes = sorted(_knocked_out_genes(genes))
    disabled_reactions = _mission28_disabled_reactions(knocked_out_genes)
    primary_reaction_disabled = MISSION28_PRIMARY_REACTION in disabled_reactions

    run_type = None
    candidate = None
    if environment.get('rescue_medium_ready') and knocked_out_genes == [MISSION28_PRIMARY_GENE]:
        run_type = 'rescue_reference'
    elif environment.get('rescue_medium_ready') and len(knocked_out_genes) == 2 and MISSION28_PRIMARY_GENE in knocked_out_genes:
        secondary = [gene for gene in knocked_out_genes if gene != MISSION28_PRIMARY_GENE]
        if len(secondary) == 1 and secondary[0] in MISSION28_SECONDARY_GENES:
            run_type = 'secondary_trial'
            candidate = secondary[0]

    objective_numeric = _mission28_number_or_none(objective_result)
    result_infeasible = 'INFEASIBLE' in str(objective_result or '').upper()
    raw_fluxes, uptake_fluxes, _secretion_fluxes = _mission21_measured_medium_values(medium_fluxes)
    diagnostics = _method_diagnostics_from_production_data(production_fluxes)
    biomass_raw = _mission28_number_or_none(_mission13_biomass_value(production_fluxes))
    primary_flux = _mission28_number_or_none(diagnostics.get('primary_objective_flux'))
    method_score = _mission28_number_or_none(diagnostics.get('method_score'))
    total_absolute_flux = _mission28_number_or_none(diagnostics.get('total_absolute_flux'))
    method_score_name = diagnostics.get('method_score_name')
    try:
        active_reaction_count = int(diagnostics.get('active_reaction_count'))
    except Exception:
        active_reaction_count = None

    glucose_raw = _mission28_number_or_none(raw_fluxes.get(MISSION27_GLUCOSE_REACTION))
    oxygen_raw = _mission28_number_or_none(raw_fluxes.get(MISSION27_OXYGEN_REACTION))
    supplement_raw = _mission28_number_or_none(raw_fluxes.get(MISSION28_RESCUE_SUPPLEMENT))
    glucose_uptake = _mission28_number_or_none(uptake_fluxes.get(MISSION27_GLUCOSE_REACTION))
    oxygen_uptake = _mission28_number_or_none(uptake_fluxes.get(MISSION27_OXYGEN_REACTION))
    supplement_uptake = _mission28_number_or_none(uptake_fluxes.get(MISSION28_RESCUE_SUPPLEMENT))

    expected_candidate_reaction = MISSION28_SECONDARY_REACTIONS.get(candidate)
    candidate_reaction_disabled = bool(
        expected_candidate_reaction and expected_candidate_reaction in disabled_reactions
    )

    issues = []
    if objective_error:
        issues.append(objective_error)
    if method_name != MISSION28_METHOD:
        issues.append('Use pFBA for the Mission 28 rescue reference and every secondary-knockout trial.')
    if selected_objective != MISSION28_GROWTH_OBJECTIVE:
        issues.append('Use the biomass objective for every Mission 28 run.')
    if not environment.get('bounds_complete'):
        issues.append('The environmental-bound payload is incomplete.')
    if not environment.get('rescue_medium_ready'):
        issues.append('Keep exactly the 2-oxoglutarate rescue supplement open and every unrelated environmental bound at model default.')
    if run_type is None:
        issues.append(
            f'Use exactly {MISSION28_PRIMARY_GENE} / {MISSION28_PRIMARY_GENE_NAME} for the rescue reference, or that gene plus exactly one highlighted secondary candidate.'
        )
    if run_type in {'rescue_reference', 'secondary_trial'} and not primary_reaction_disabled:
        issues.append(f'The primary knockout must keep {MISSION28_PRIMARY_REACTION} disabled by the GPR.')
    if run_type == 'secondary_trial' and not candidate_reaction_disabled:
        issues.append('The secondary knockout must disable its expected candidate reaction through the GPR.')

    if result_infeasible or objective_numeric is None:
        issues.append('Mission 28 requires a numeric visible biomass result; an infeasible result is not a measured zero-growth solution.')
    elif objective_numeric < -MISSION28_PRIMARY_TOLERANCE:
        issues.append('The biomass result is outside the valid non-negative range.')

    required_medium = [MISSION27_GLUCOSE_REACTION, MISSION27_OXYGEN_REACTION, MISSION28_RESCUE_SUPPLEMENT]
    missing_medium = [reaction_id for reaction_id in required_medium if reaction_id not in raw_fluxes]
    if medium_fluxes and medium_fluxes.get('error'):
        issues.append('The Exchange Flux Report is unavailable for this run.')
    elif missing_medium:
        issues.append('Numeric glucose, oxygen and 2-oxoglutarate exchange evidence is required.')
    else:
        if (
            glucose_raw is None or oxygen_raw is None or supplement_raw is None
            or glucose_uptake is None or oxygen_uptake is None or supplement_uptake is None
        ):
            issues.append('The required exchange evidence contains non-numeric values.')
        else:
            if glucose_raw > MISSION28_FLUX_TOLERANCE:
                issues.append('Glucose must not be secreted in the controlled rescue medium.')
            if oxygen_raw > MISSION28_FLUX_TOLERANCE:
                issues.append('Oxygen must not be secreted in the controlled rescue medium.')
            if supplement_raw > MISSION28_FLUX_TOLERANCE:
                issues.append('2-Oxoglutarate must not be secreted in the rescue trial.')
            if glucose_uptake is not None and glucose_uptake > MISSION28_EXPECTED_DEFAULT_UPTAKE + MISSION28_CAPACITY_TOLERANCE:
                issues.append('Glucose uptake exceeds the model-default capacity.')
            if supplement_uptake is not None and supplement_uptake > MISSION28_EXPECTED_SUPPLEMENT_CAPACITY + MISSION28_CAPACITY_TOLERANCE:
                issues.append('2-Oxoglutarate uptake exceeds the controlled supplement capacity.')

    if production_fluxes and production_fluxes.get('error'):
        issues.append('The visible simulation diagnostics are unavailable.')
    if biomass_raw is None or primary_flux is None:
        issues.append('The visible biomass and primary-objective diagnostics are required.')
    else:
        if objective_numeric is not None and abs(objective_numeric - biomass_raw) > MISSION28_PRIMARY_TOLERANCE:
            issues.append('The displayed objective value does not match the biomass-reaction flux.')
        if abs(biomass_raw - primary_flux) > MISSION28_PRIMARY_TOLERANCE:
            issues.append('The primary objective diagnostic does not match biomass.')
    if diagnostics.get('method') != MISSION28_METHOD:
        issues.append('The method diagnostic does not identify pFBA.')
    if diagnostics.get('objective_reaction') != MISSION28_GROWTH_OBJECTIVE:
        issues.append('The method diagnostic does not identify the biomass objective.')
    if method_score_name != MISSION28_EXPECTED_SCORE_NAME:
        issues.append('The pFBA secondary-score meaning is missing or incorrect.')
    if method_score is None or total_absolute_flux is None:
        issues.append('The visible pFBA secondary score or total absolute flux is missing.')
    elif abs(method_score - total_absolute_flux) > MISSION28_PRIMARY_TOLERANCE:
        issues.append('The pFBA method score does not match total absolute flux.')
    if active_reaction_count is None:
        issues.append('The visible pFBA result is missing the active-reaction diagnostic.')

    if objective_numeric is not None and supplement_uptake is not None:
        if run_type == 'rescue_reference':
            if objective_numeric < MISSION28_MIN_REFERENCE_GROWTH:
                issues.append('The rescue reference must retain clear positive growth.')
            if supplement_uptake < MISSION28_MIN_REFERENCE_SUPPLEMENT_UPTAKE:
                issues.append('The rescue reference must show measurable 2-oxoglutarate uptake.')
            if glucose_uptake is not None and abs(glucose_uptake - MISSION28_EXPECTED_DEFAULT_UPTAKE) > MISSION28_CAPACITY_TOLERANCE:
                issues.append('Keep model-default glucose availability in the rescue reference.')
            if oxygen_uptake is not None and oxygen_uptake < MISSION28_MIN_AEROBIC_OXYGEN_UPTAKE:
                issues.append('The rescue reference must retain measurable oxygen uptake.')
        elif run_type == 'secondary_trial' and candidate == MISSION28_EXPECTED_DEPENDENCY:
            if objective_numeric > MISSION28_MAX_DEPENDENCY_GROWTH:
                issues.append('The transporter knockout should abolish the model-predicted rescue growth.')
            if supplement_uptake > MISSION28_MAX_DEPENDENCY_UPTAKE:
                issues.append('The transporter knockout should abolish measurable 2-oxoglutarate uptake.')
        elif run_type == 'secondary_trial':
            reference_growth = _mission28_number_or_none((rescue_reference or {}).get('growth'))
            if reference_growth is not None and reference_growth > MISSION28_PRIMARY_TOLERANCE:
                retention = objective_numeric / reference_growth
                if retention < MISSION28_MIN_NONDEPENDENCY_RETENTION:
                    issues.append('This control knockout retains too little of the established rescue growth.')
            if supplement_uptake < MISSION28_MIN_NONDEPENDENCY_UPTAKE:
                issues.append('This control knockout should retain measurable 2-oxoglutarate uptake.')

    current_run_valid = not issues
    current_run_recorded = False
    current_run = None
    if current_run_valid:
        current_run = {
            'run_type': run_type,
            'candidate': candidate,
            'candidate_name': MISSION28_SECONDARY_GENE_NAMES.get(candidate) if candidate else None,
            'expected_disabled_reaction': expected_candidate_reaction,
            'candidate_reaction_disabled': bool(candidate_reaction_disabled),
            'method': method_name,
            'objective': selected_objective,
            'growth': _mission28_clean_number(objective_numeric),
            'knocked_out_genes': list(knocked_out_genes),
            'disabled_reactions': list(disabled_reactions),
            'primary_reaction_disabled': bool(primary_reaction_disabled),
            'environment_changes': list(environment.get('changes') or []),
            'glucose_raw_flux': _mission28_clean_number(glucose_raw),
            'glucose_uptake': _mission28_clean_number(glucose_uptake),
            'oxygen_raw_flux': _mission28_clean_number(oxygen_raw),
            'oxygen_uptake': _mission28_clean_number(oxygen_uptake),
            'supplement_raw_flux': _mission28_clean_number(supplement_raw),
            'supplement_uptake': _mission28_clean_number(supplement_uptake),
            'method_diagnostics': {
                'method': diagnostics.get('method'),
                'objective_reaction': diagnostics.get('objective_reaction'),
                'primary_objective_flux': _mission28_clean_number(primary_flux),
                'method_score': _mission28_clean_number(method_score),
                'method_score_name': method_score_name,
                'total_absolute_flux': _mission28_clean_number(total_absolute_flux),
                'active_reaction_count': active_reaction_count,
            },
        }
        if run_type == 'rescue_reference':
            current_run['source'] = 'current_visible_run'
            rescue_reference = current_run
            reference_imported = False
        elif run_type == 'secondary_trial':
            secondary_trials[candidate] = current_run
        current_run_recorded = True

    missing_conditions = []
    if not isinstance(rescue_reference, dict):
        missing_conditions.append('rescue_reference')
    missing_conditions.extend(
        candidate for candidate in MISSION28_SECONDARY_GENES
        if not isinstance(secondary_trials.get(candidate), dict)
    )
    recorded_run_count = MISSION28_REQUIRED_RUN_COUNT - len(missing_conditions)
    evidence_ready = not missing_conditions

    reference_growth = _mission28_number_or_none((rescue_reference or {}).get('growth'))
    growth_retention_by_candidate = {}
    supplement_uptake_by_candidate = {}
    dependency_candidates = []
    controls_supported = True
    if evidence_ready and reference_growth is not None and reference_growth > MISSION28_PRIMARY_TOLERANCE:
        for candidate_id in MISSION28_SECONDARY_GENES:
            trial = secondary_trials.get(candidate_id) or {}
            growth = _mission28_number_or_none(trial.get('growth'))
            uptake = _mission28_number_or_none(trial.get('supplement_uptake'))
            retention = None if growth is None else growth / reference_growth
            growth_retention_by_candidate[candidate_id] = (
                _mission28_clean_number(retention) if retention is not None else None
            )
            supplement_uptake_by_candidate[candidate_id] = (
                _mission28_clean_number(uptake) if uptake is not None else None
            )
            if (
                growth is not None and growth <= MISSION28_MAX_DEPENDENCY_GROWTH
                and uptake is not None and uptake <= MISSION28_MAX_DEPENDENCY_UPTAKE
                and trial.get('primary_reaction_disabled')
                and trial.get('candidate_reaction_disabled')
            ):
                dependency_candidates.append(candidate_id)
            elif (
                retention is None or retention < MISSION28_MIN_NONDEPENDENCY_RETENTION
                or uptake is None or uptake < MISSION28_MIN_NONDEPENDENCY_UPTAKE
                or not trial.get('primary_reaction_disabled')
                or not trial.get('candidate_reaction_disabled')
            ):
                controls_supported = False

    unique_dependency_candidate = dependency_candidates[0] if len(dependency_candidates) == 1 else None
    unique_transport_dependency_supported = bool(
        evidence_ready
        and reference_growth is not None
        and reference_growth >= MISSION28_MIN_REFERENCE_GROWTH
        and _mission28_number_or_none((rescue_reference or {}).get('supplement_uptake')) >= MISSION28_MIN_REFERENCE_SUPPLEMENT_UPTAKE
        and unique_dependency_candidate == MISSION28_EXPECTED_DEPENDENCY
        and controls_supported
    )

    latest_attempt = {
        'method': method_name,
        'objective': selected_objective,
        'run_type': run_type,
        'candidate': candidate,
        'knocked_out_genes': list(knocked_out_genes),
        'valid': current_run_valid,
        'recorded': current_run_recorded,
        'issues': list(issues),
    }

    report = _mission28_empty_report()
    report.update({
        'rescue_reference': rescue_reference,
        'reference_imported_from_mission27': reference_imported,
        'secondary_trials': secondary_trials,
        'recorded_run_count': recorded_run_count,
        'missing_conditions': missing_conditions,
        'growth_retention_by_candidate': growth_retention_by_candidate,
        'supplement_uptake_by_candidate': supplement_uptake_by_candidate,
        'dependency_candidates': dependency_candidates,
        'unique_dependency_candidate': unique_dependency_candidate,
        'unique_transport_dependency_supported': unique_transport_dependency_supported,
        'evidence_ready': evidence_ready,
        'answer_ready': unique_transport_dependency_supported,
        'ready_to_deliver': unique_transport_dependency_supported,
        'current_run_type': run_type,
        'current_candidate': candidate,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_issues': list(issues),
        'current_run': current_run,
        'latest_attempt': latest_attempt,
    })
    save_mission28_dependency_check(report)
    return report


def run_mission28_dependency_check(simulation_results=None):
    """Validate the already displayed Mission 28 result without re-simulating."""
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible Mission 28 simulation before recording evidence.'
    except Exception:
        objective_error = 'Could not read the current visible Mission 28 simulation result.'

    return _build_mission28_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission28_dependency_check() or {},
        mission27_report=load_mission27_rescue_check() or {},
        objective_error=objective_error,
    )


def run_mission28_dependency_check_remote(backend_url, simulation_results=None):
    """Browser parity wrapper using the same visible backend response."""
    del backend_url
    return run_mission28_dependency_check(simulation_results)


def _normalise_mission28_text(value):
    text = str(value or '').replace('α', 'alpha').replace('Α', 'alpha')
    text = unicodedata.normalize('NFKD', text)
    return ''.join(char for char in text if not unicodedata.combining(char)).lower().strip()


def normalise_mission28_answer(answer):
    text = _normalise_mission28_text(answer)
    if not text:
        return None
    patterns = (
        r'\bb2587\b',
        r'\bkgtp\b',
        r'\bakgt2r\b',
        r'\b(?:2|two)[-\s]*(?:oxo|keto)glutarate\s+transporter\b',
        r'\balpha[-\s]*ketoglutarate\s+transporter\b',
    )
    return MISSION28_EXPECTED_DEPENDENCY if any(re.search(pattern, text) for pattern in patterns) else None


def mission28_answer_matches(answer, report_data=None):
    report = report_data if report_data is not None else (load_mission28_dependency_check() or {})
    return bool(
        report.get('mission_id') == '28'
        and report.get('check_version') == MISSION28_CHECK_VERSION
        and report.get('answer_ready')
        and report.get('unique_transport_dependency_supported')
        and normalise_mission28_answer(answer) == report.get('unique_dependency_candidate')
    )


def build_mission28_dependency_report_text(report_data=None):
    report = report_data or {}
    if report.get('mission_id') != '28' or report.get('check_version') != MISSION28_CHECK_VERSION:
        return (
            'No dependency evidence has been recorded yet.\n\n'
            'Experimental objective:\n'
            'Use the validated 2-oxoglutarate rescue from Mission 27 as a controlled reference. Keep b0720 / gltA knocked out, keep EX_akg_e as the only opened supplement, and use pFBA with the biomass objective.\n\n'
            'Dependency screen:\n'
            'Test each highlighted secondary gene in a separate visible run. Change only one secondary knockout at a time while keeping the rescue medium unchanged. For every trial, compare predicted growth, measured 2-oxoglutarate uptake, and the reactions disabled through the GPR.\n\n'
            'What to determine:\n'
            'Identify the secondary knockout that removes both supplement uptake and the rescued-growth phenotype while citrate synthase remains disabled. Activate the mission to begin recording the reference and five controlled secondary-knockout trials.'
        )

    def fmt(value):
        return 'pending' if value is None else f'{float(value):.3f}'

    lines = [
        'Mission 28 Bypass Dependency Mapping',
        '',
        'Controlled protocol:',
        f'- Method: {MISSION28_METHOD}',
        f'- Objective: {MISSION28_GROWTH_OBJECTIVE}',
        f'- Fixed lesion: {MISSION28_PRIMARY_GENE} / {MISSION28_PRIMARY_GENE_NAME}',
        f'- Fixed rescue supplement: {MISSION28_RESCUE_SUPPLEMENT} / {MISSION28_RESCUE_SUPPLEMENT_NAME}',
        '- Secondary trials: add exactly one highlighted candidate knockout while keeping the rescue medium unchanged',
        '',
        f"Runs recorded: {report.get('recorded_run_count', 0)}/{report.get('required_run_count', MISSION28_REQUIRED_RUN_COUNT)}",
        '',
        'Rescue reference:',
    ]

    reference = report.get('rescue_reference')
    if isinstance(reference, dict):
        lines.extend([
            f"- Growth: {fmt(reference.get('growth'))}",
            f"- 2-Oxoglutarate uptake: {fmt(reference.get('supplement_uptake'))}",
            f"- {MISSION28_PRIMARY_REACTION} disabled: {'yes' if reference.get('primary_reaction_disabled') else 'no'}",
            f"- Source: {'Mission 27 visible evidence' if report.get('reference_imported_from_mission27') else 'current visible run'}",
        ])
    else:
        lines.append('- Pending')

    lines.extend([
        '',
        'Secondary-knockout trials:',
        'Candidate | growth | retention | 2OG uptake | GPR-disabled reactions',
    ])
    trials = report.get('secondary_trials') or {}
    retention = report.get('growth_retention_by_candidate') or {}
    for candidate_id in MISSION28_SECONDARY_GENES:
        trial = trials.get(candidate_id)
        label = f'{candidate_id}/{MISSION28_SECONDARY_GENE_NAMES[candidate_id]}'
        if not isinstance(trial, dict):
            lines.append(f'{label} | pending | pending | pending | pending')
            continue
        retention_value = retention.get(candidate_id)
        retention_text = 'pending' if retention_value is None else f'{100.0 * float(retention_value):.1f}%'
        disabled_text = ', '.join(trial.get('disabled_reactions') or []) or 'none'
        lines.append(
            f"{label} | {fmt(trial.get('growth'))} | {retention_text} | {fmt(trial.get('supplement_uptake'))} | {disabled_text}"
        )

    latest = report.get('latest_attempt') or {}
    if latest and not latest.get('recorded'):
        lines.extend(['', 'Latest run was not recorded:'])
        for issue in latest.get('issues') or ['The visible run did not match the controlled Mission 28 protocol.']:
            lines.append(f'- {issue}')
        if report.get('recorded_run_count', 0):
            lines.append('Previously valid Mission 28 dependency evidence remains available.')
    elif report.get('current_run_recorded'):
        current = report.get('current_run') or {}
        if current.get('run_type') == 'rescue_reference':
            recorded = 'rescue_reference'
        else:
            recorded = f"secondary_trial[{current.get('candidate')}]"
        lines.extend(['', f'Latest valid visible run recorded: {recorded}.'])

    lines.append('')
    if report.get('evidence_ready'):
        lines.extend([
            'Evidence complete.',
            'Compare rescue retention, measured 2-oxoglutarate uptake and the GPR-disabled reactions.',
            'Question: Which secondary gene knockout abolished the rescue by preventing 2-oxoglutarate uptake while citrate synthase remained disabled?',
        ])
    else:
        lines.append('Evidence incomplete.')
        missing = report.get('missing_conditions') or []
        if missing:
            lines.append('Missing conditions: ' + ', '.join(missing))

    lines.extend([
        '',
        'Interpretation note: external supplement availability is not the same as metabolic uptake; the rescue depends on functions that make the supplement accessible to the network.',
        'The conclusion is conditional on this model, pFBA biomass objective, medium, bounds and tested secondary-gene set.',
        'All growth, exchange and GPR evidence comes from visible simulation results. No hidden validation simulation is used.',
    ])
    return '\n'.join(lines)


# Backwards-compatible name retained for stale imports from the old sweep-based
# Mission 28.  It now exposes the redesigned dependency report and never runs a
# Bound Sweep.
def run_mission28_bound_sweep_check(sweep_data=None):
    del sweep_data
    return load_mission28_dependency_check() or _mission28_empty_report(load_mission27_rescue_check() or {})

def run_simul():
    method_name, objective_name, genes, reactions = _read_simulation_file()
    selected_fluxes = _read_selected_production_fluxes()
    results, production_fluxes, medium_fluxes = _simulate_local_objective_with_production_fluxes(
        method_name,
        objective_name,
        genes,
        reactions,
        selected_fluxes,
    )
    return objective_name, results, production_fluxes, medium_fluxes


def run_challenge_score(simulation_results=None):
    """Validate the visible Mission 06 simulation without re-simulating it."""
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run the simulation before recording a Mission 06 challenge attempt.'
    except Exception:
        objective_error = 'Could not read the current visible simulation result.'

    return _build_mission06_challenge_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_challenge_score(),
        objective_error=objective_error,
    )



def _build_request_payload():
    method_name, objective_name, genes, reactions = _read_simulation_file()

    constraints = _build_envconditions_from_reactions(reactions, REACTIONS)
    env_conditions = {
        reaction_id: [float(bounds[0]), float(bounds[1])]
        for reaction_id, bounds in constraints.items()
    }
    gene_knockouts = [k for k, x in genes.items() if not x]

    return {
        'method': method_name,
        'objective': objective_name,
        'gene_knockouts': gene_knockouts,
        'env_conditions': env_conditions,
    }


def _http_post_json(url, payload):
    body = json.dumps(payload)
    if sys.platform == 'emscripten':
        # pygbag's pyodide does not expose `from js import XMLHttpRequest`
        # as a constructable JsProxy (XMLHttpRequest.new is None and the
        # plain JsProxy is not callable), so we instantiate via js.eval.
        # Synchronous XHR lets us stay inside the sync pygame_menu callback
        # at window.py:data_fun — no async bridge needed for the simulate call.
        import js
        xhr = js.eval("new XMLHttpRequest()")
        xhr.open('POST', url, False)
        xhr.setRequestHeader('Content-Type', 'application/json')
        xhr.send(body)
        return json.loads(xhr.responseText)
    import urllib.request
    req = urllib.request.Request(
        url,
        data=body.encode('utf-8'),
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def run_simul_remote(backend_url):
    payload = _build_request_payload()
    selected_fluxes = _read_selected_production_fluxes()
    try:
        response = _http_post_json(backend_url.rstrip('/') + '/simulate', payload)
    except Exception as e:
        return payload['objective'], f'Error: {e}', _build_production_flux_data(
            selected_fluxes,
            error=f'Backend error: {e}'
        ), _build_medium_flux_data(
            error=f'Backend error: {e}'
        )

    if response.get('status') == 'ok':
        fluxes = response.get('fluxes') or {}
        flux_getter = lambda reaction_id: fluxes.get(reaction_id)
        production_fluxes = _build_production_flux_data(
            selected_fluxes,
            flux_getter=flux_getter
        )
        objective_raw = _as_float_or_none(
            response.get('primary_objective_flux', fluxes.get(payload['objective']))
        )
        if objective_raw is None:
            objective_raw = _as_float_or_none(fluxes.get(payload['objective'], response.get('result')))
        if objective_raw is not None:
            production_fluxes['objective_raw'] = float(objective_raw)
        biomass_raw = _as_float_or_none(fluxes.get(MISSION07_BIOMASS_OBJECTIVE))
        if biomass_raw is not None:
            production_fluxes['biomass_raw'] = float(biomass_raw)

        total_absolute_flux = _as_float_or_none(response.get('total_absolute_flux'))
        if total_absolute_flux is None and fluxes:
            total_absolute_flux = sum(abs(float(value)) for value in fluxes.values())
        active_reaction_count = response.get('active_reaction_count')
        if active_reaction_count is None and fluxes:
            active_reaction_count = sum(
                1 for value in fluxes.values()
                if abs(float(value)) > MISSION13_ACTIVE_FLUX_TOLERANCE
            )
        method_score = _as_float_or_none(response.get('method_score'))
        if method_score is None:
            # Backward compatibility with an older backend where `result` held
            # the pFBA secondary score while the objective flux was in `fluxes`.
            method_score = _as_float_or_none(response.get('result'))
        production_fluxes['method_diagnostics'] = {
            'method': response.get('method', payload['method']),
            'objective_reaction': response.get('objective_reaction', payload['objective']),
            'primary_objective_flux': float(objective_raw) if objective_raw is not None else None,
            'method_score': float(method_score) if method_score is not None else None,
            'method_score_name': response.get('method_score_name', _method_score_label(payload['method'])),
            'total_absolute_flux': float(total_absolute_flux) if total_absolute_flux is not None else None,
            'active_reaction_count': int(active_reaction_count) if active_reaction_count is not None else None,
        }
        visible_result = round(float(objective_raw), 3) if objective_raw is not None else response.get('result')
        return response['objective'], visible_result, production_fluxes, _build_medium_flux_data(
            flux_getter=flux_getter
        )
    if response.get('status') == 'infeasible':
        return response['objective'], 'Status: INFEASIBLE', _build_production_flux_data(
            selected_fluxes,
            error='Simulation infeasible. Production fluxes could not be measured.'
        ), _build_medium_flux_data(
            error='Simulation infeasible. Medium fluxes could not be measured.'
        )
    return (
        response.get('objective', payload['objective']),
        f'Error: {response.get("message", "unknown")}',
        _build_production_flux_data(
            selected_fluxes,
            error=response.get('message', 'unknown backend error')
        ),
        _build_medium_flux_data(
            error=response.get('message', 'unknown backend error')
        )
    )



def _build_default_env_conditions_payload():
    """Return the exact exchange bounds defined by the model."""
    env_conditions = {}
    for i in range(len(REACTIONS.index)):
        reaction_id = REACTIONS.index[i]
        env_conditions[reaction_id] = [
            float(REACTIONS.lb.iloc[i]),
            float(REACTIONS.ub.iloc[i]),
        ]
    return env_conditions


def _simulate_remote_flux_solution(backend_url, payload, objective):
    request_payload = copy.deepcopy(payload)
    request_payload['method'] = 'FBA'
    request_payload['objective'] = objective
    return _http_post_json(backend_url.rstrip('/') + '/simulate', request_payload)


def _extract_remote_growth_and_flux(response, production_objective):
    if response.get('status') == 'infeasible':
        return 0.0, 0.0, 'Status: INFEASIBLE'

    if response.get('status') != 'ok':
        return 0.0, 0.0, response.get('message', 'unknown backend error')

    growth = response.get('result', 0.0)
    fluxes = response.get('fluxes') or {}
    production_flux = fluxes.get(production_objective)

    production_value = _as_float_or_none(production_flux)
    if production_value is None:
        return growth, 0.0, f'Backend did not return {production_objective} flux.'

    return growth, production_value, None


def run_mission04_production_check_remote(backend_url, simulation_results=None):
    """Compatibility wrapper for the browser build.

    The current browser simulation result already contains the objective,
    production-flux and exchange-flux evidence returned by the backend.  Reuse
    that same result so Mission 04 never launches a hidden second simulation
    with settings that differ from the player's visible run.
    """
    return run_mission04_production_trial_check(simulation_results)



def _build_anaerobic_env_conditions_payload():
    """Compatibility helper retained for callers outside Mission 05."""
    env_conditions = _build_default_env_conditions_payload()
    if MISSION05_OXYGEN_REACTION in env_conditions:
        env_conditions[MISSION05_OXYGEN_REACTION][0] = 0
    return env_conditions


def run_mission05_production_check_remote(backend_url, simulation_results=None):
    """Reuse the visible browser result instead of launching hidden requests."""
    return run_mission05_production_trial_check(simulation_results)


def run_mission09_design_check_remote(backend_url, simulation_results=None):
    """Reuse the visible browser result; Mission 09 launches no hidden requests."""
    return run_mission09_design_check(simulation_results)


def run_challenge_score_remote(backend_url, simulation_results=None):
    """Web wrapper: reuse the already displayed backend result; no hidden request."""
    return run_challenge_score(simulation_results)


def run_mission10_robust_design_check_remote(backend_url, simulation_results=None):
    """Reuse the visible browser result; Mission 10 launches no hidden requests."""
    return run_mission10_robust_design_check(simulation_results)

def run_mission11_flux_fingerprint_check_remote(backend_url, simulation_results=None):
    """Reuse the visible browser result; Mission 11 launches no hidden requests."""
    return run_mission11_flux_fingerprint_check(simulation_results)


def run_mission12_byproduct_check_remote(backend_url, simulation_results=None):
    """Reuse the visible browser result; Mission 12 launches no hidden requests."""
    return run_mission12_byproduct_check(simulation_results)


def run_mission13_method_check_remote(backend_url, simulation_results=None):
    """Reuse the visible browser result; Mission 13 launches no hidden requests."""
    return run_mission13_method_check(simulation_results)


def run_mission14_reduction_check_remote(backend_url, simulation_results=None):
    """Reuse the visible browser result; Mission 14 launches no hidden requests."""
    return run_mission14_reduction_check(simulation_results)


def run_mission15_diagnostic_report_check_remote(backend_url, simulation_results=None):
    """Reuse the visible browser result; Mission 15 launches no hidden requests."""
    return run_mission15_diagnostic_report_check(simulation_results)
# Mission 29 — Isoenzyme Redundancy and Synthetic Lethality
# Dr. Li begins a network-robustness programme by comparing three matched
# isoenzyme pairs. The player records a wild-type reference, all six single
# knockouts and the three corresponding double knockouts under one unchanged
# aerobic medium. The conclusion is inferred from visible pFBA evidence only.
MISSION29_CHECK_VERSION = 2
MISSION29_METHOD = 'pFBA'
MISSION29_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION29_TARGET_CONTEXT = 'isoenzyme redundancy and synthetic-lethal interaction screen'
MISSION29_PAIR_ORDER = ['aconitase', 'phosphofructokinase', 'pyruvate_kinase']
MISSION29_PAIRS = {
    'aconitase': ('b0118', 'b1276'),
    'phosphofructokinase': ('b1723', 'b3916'),
    'pyruvate_kinase': ('b1676', 'b1854'),
}
MISSION29_PAIR_LABELS = {
    'aconitase': 'Aconitase isoenzymes',
    'phosphofructokinase': 'Phosphofructokinase isoenzymes',
    'pyruvate_kinase': 'Pyruvate-kinase isoenzymes',
}
MISSION29_GENE_NAMES = {
    'b0118': 'acnB',
    'b1276': 'acnA',
    'b1723': 'pfkB',
    'b3916': 'pfkA',
    'b1676': 'pykF',
    'b1854': 'pykA',
}
MISSION29_PAIR_REACTIONS = {
    'aconitase': ['ACONTa', 'ACONTb'],
    'phosphofructokinase': ['PFK'],
    'pyruvate_kinase': ['PYK'],
}
MISSION29_SINGLE_GENES = [
    gene_id
    for pair_id in MISSION29_PAIR_ORDER
    for gene_id in MISSION29_PAIRS[pair_id]
]
MISSION29_EXPECTED_SYNTHETIC_PAIR = 'aconitase'
MISSION29_REQUIRED_RUN_COUNT = 1 + len(MISSION29_SINGLE_GENES) + len(MISSION29_PAIR_ORDER)
MISSION29_EXPECTED_SCORE_NAME = 'total_absolute_flux'
MISSION29_EXPECTED_DEFAULT_UPTAKE = 10.0
MISSION29_MIN_REFERENCE_GROWTH = 0.5
MISSION29_MIN_SINGLE_RETENTION = 0.95
MISSION29_MAX_SYNTHETIC_PAIR_RETENTION = 0.01
MISSION29_MIN_CONTROL_PAIR_RETENTION = 0.10
MISSION29_MIN_AEROBIC_OXYGEN_UPTAKE = 0.1
MISSION29_FLUX_TOLERANCE = 0.01
MISSION29_PRIMARY_TOLERANCE = 0.001
MISSION29_CAPACITY_TOLERANCE = 0.05


def is_mission29_unlocked(missions_completed):
    """Mission 29 is Dr. Li's first mission and requires Mission 28."""
    return '28' in (missions_completed or [])


def _mission29_number_or_none(value):
    numeric = _as_float_or_none(value)
    return float(numeric) if numeric is not None else None


def _mission29_clean_number(value, decimals=6):
    numeric = float(value)
    if abs(numeric) < DISPLAY_ZERO_TOLERANCE:
        numeric = 0.0
    return round(numeric, decimals)


def _mission29_pair_for_gene(gene_id):
    for pair_id in MISSION29_PAIR_ORDER:
        if gene_id in MISSION29_PAIRS[pair_id]:
            return pair_id
    return None


def _mission29_pair_for_knockouts(knocked_out_genes):
    knocked = tuple(sorted(knocked_out_genes or []))
    for pair_id in MISSION29_PAIR_ORDER:
        if knocked == tuple(sorted(MISSION29_PAIRS[pair_id])):
            return pair_id
    return None


def _mission29_disabled_reactions(knocked_out_genes):
    """Evaluate GPR consequences without launching a metabolic simulation."""
    knocked_out_genes = sorted(knocked_out_genes or [])
    if not knocked_out_genes:
        return []
    try:
        if model is not None:
            return sorted(disabled_reaction_ids(model, knocked_out_genes))
    except Exception:
        pass

    disabled = []
    knocked = set(knocked_out_genes)
    for pair_id in MISSION29_PAIR_ORDER:
        if set(MISSION29_PAIRS[pair_id]).issubset(knocked):
            disabled.extend(MISSION29_PAIR_REACTIONS[pair_id])
    return sorted(set(disabled))


def _mission29_environment_status(reactions):
    status = _mission27_environment_status(reactions)
    return {
        'bounds_complete': bool(status.get('bounds_complete')),
        'changes': list(status.get('changes') or []),
        'setup_type': status.get('setup_type'),
        'default_environment_ready': bool(
            status.get('bounds_complete') and status.get('setup_type') == 'default'
        ),
    }


def _mission29_empty_report():
    missing = ['wild_type_reference']
    missing.extend(f'single:{gene_id}' for gene_id in MISSION29_SINGLE_GENES)
    missing.extend(f'pair:{pair_id}' for pair_id in MISSION29_PAIR_ORDER)
    return {
        'mission_id': '29',
        'check_version': MISSION29_CHECK_VERSION,
        'mission_title': 'Isoenzyme Redundancy Screen',
        'target_context': MISSION29_TARGET_CONTEXT,
        'target_method': MISSION29_METHOD,
        'growth_objective': MISSION29_GROWTH_OBJECTIVE,
        'pair_order': list(MISSION29_PAIR_ORDER),
        'pairs': copy.deepcopy(MISSION29_PAIRS),
        'pair_labels': copy.deepcopy(MISSION29_PAIR_LABELS),
        'gene_names': copy.deepcopy(MISSION29_GENE_NAMES),
        'pair_reactions': copy.deepcopy(MISSION29_PAIR_REACTIONS),
        'wild_type_reference': None,
        'single_trials': {},
        'pair_trials': {},
        'recorded_run_count': 0,
        'required_run_count': MISSION29_REQUIRED_RUN_COUNT,
        'missing_conditions': missing,
        'single_growth_retention': {},
        'pair_growth_retention': {},
        'pair_interaction_summary': {},
        'synthetic_lethal_candidates': [],
        'unique_synthetic_pair': None,
        'unique_synthetic_lethality_supported': False,
        'evidence_ready': False,
        'answer_ready': False,
        'ready_to_deliver': False,
        'current_run_type': None,
        'current_gene': None,
        'current_pair': None,
        'current_run_valid': False,
        'current_run_recorded': False,
        'current_issues': [],
        'current_run': None,
        'latest_attempt': None,
    }


def initialise_mission29_redundancy_screen():
    report = _mission29_empty_report()
    save_mission29_redundancy_check(report)
    return report


def _build_mission29_data(
    method_name,
    selected_objective,
    objective_result,
    genes,
    reactions,
    production_fluxes=None,
    medium_fluxes=None,
    existing_report=None,
    objective_error=None,
):
    """Validate and accumulate one visible Mission 29 reference/single/pair run."""
    existing_report = existing_report or {}
    if (
        existing_report.get('mission_id') != '29'
        or existing_report.get('check_version') != MISSION29_CHECK_VERSION
    ):
        existing_report = _mission29_empty_report()

    wild_type_reference = copy.deepcopy(existing_report.get('wild_type_reference'))
    single_trials = copy.deepcopy(existing_report.get('single_trials') or {})
    pair_trials = copy.deepcopy(existing_report.get('pair_trials') or {})

    environment = _mission29_environment_status(reactions)
    knocked_out_genes = sorted(_knocked_out_genes(genes))
    disabled_reactions = _mission29_disabled_reactions(knocked_out_genes)

    run_type = None
    current_gene = None
    current_pair = None
    if not knocked_out_genes:
        run_type = 'wild_type_reference'
    elif len(knocked_out_genes) == 1 and knocked_out_genes[0] in MISSION29_SINGLE_GENES:
        run_type = 'single_trial'
        current_gene = knocked_out_genes[0]
        current_pair = _mission29_pair_for_gene(current_gene)
    elif len(knocked_out_genes) == 2:
        pair_id = _mission29_pair_for_knockouts(knocked_out_genes)
        if pair_id:
            run_type = 'pair_trial'
            current_pair = pair_id

    objective_numeric = _mission29_number_or_none(objective_result)
    result_infeasible = 'INFEASIBLE' in str(objective_result or '').upper()
    raw_fluxes, uptake_fluxes, _secretion_fluxes = _mission21_measured_medium_values(medium_fluxes)
    diagnostics = _method_diagnostics_from_production_data(production_fluxes)
    biomass_raw = _mission29_number_or_none(_mission13_biomass_value(production_fluxes))
    primary_flux = _mission29_number_or_none(diagnostics.get('primary_objective_flux'))
    method_score = _mission29_number_or_none(diagnostics.get('method_score'))
    total_absolute_flux = _mission29_number_or_none(diagnostics.get('total_absolute_flux'))
    method_score_name = diagnostics.get('method_score_name')
    try:
        active_reaction_count = int(diagnostics.get('active_reaction_count'))
    except Exception:
        active_reaction_count = None

    glucose_raw = _mission29_number_or_none(raw_fluxes.get(MISSION27_GLUCOSE_REACTION))
    oxygen_raw = _mission29_number_or_none(raw_fluxes.get(MISSION27_OXYGEN_REACTION))
    glucose_uptake = _mission29_number_or_none(uptake_fluxes.get(MISSION27_GLUCOSE_REACTION))
    oxygen_uptake = _mission29_number_or_none(uptake_fluxes.get(MISSION27_OXYGEN_REACTION))

    issues = []
    if objective_error:
        issues.append(objective_error)
    if method_name != MISSION29_METHOD:
        issues.append('Use pFBA for every Mission 29 reference, single knockout and double knockout.')
    if selected_objective != MISSION29_GROWTH_OBJECTIVE:
        issues.append(f'Use {MISSION29_GROWTH_OBJECTIVE} as the primary objective.')
    if not environment.get('bounds_complete'):
        issues.append('The visible environmental-bounds payload is incomplete.')
    elif not environment.get('default_environment_ready'):
        issues.append('Keep the complete environmental medium at model default for every Mission 29 run.')
    if run_type is None:
        issues.append(
            'Use wild type, exactly one highlighted candidate gene, or exactly one of the three defined highlighted gene pairs.'
        )
    if result_infeasible:
        issues.append('An INFEASIBLE result is not valid Mission 29 growth evidence.')
    if objective_numeric is None:
        issues.append('The visible growth value is missing or non-numeric.')
    elif objective_numeric < -MISSION29_PRIMARY_TOLERANCE:
        issues.append('The visible growth value is outside the accepted non-negative range.')

    if glucose_raw is None or glucose_uptake is None:
        issues.append('Numeric glucose exchange evidence is required.')
    else:
        if glucose_raw > MISSION29_FLUX_TOLERANCE:
            issues.append('Glucose must not be secreted in this controlled aerobic screen.')
        if glucose_uptake > MISSION29_EXPECTED_DEFAULT_UPTAKE + MISSION29_CAPACITY_TOLERANCE:
            issues.append('Measured glucose uptake exceeds the model-default capacity.')
    if oxygen_raw is None or oxygen_uptake is None:
        issues.append('Numeric oxygen exchange evidence is required.')
    else:
        if oxygen_raw > MISSION29_FLUX_TOLERANCE:
            issues.append('Oxygen must not be secreted in this controlled aerobic screen.')
        if oxygen_uptake < MISSION29_MIN_AEROBIC_OXYGEN_UPTAKE:
            issues.append('The run must remain aerobic with positive measured oxygen uptake.')

    if biomass_raw is None:
        issues.append('The visible biomass flux is missing from the structured result.')
    if primary_flux is None:
        issues.append('The visible primary-objective diagnostic is missing.')
    if objective_numeric is not None and biomass_raw is not None:
        if abs(objective_numeric - biomass_raw) > MISSION29_PRIMARY_TOLERANCE:
            issues.append('The visible growth value does not match the biomass reaction flux.')
    if biomass_raw is not None and primary_flux is not None:
        if abs(biomass_raw - primary_flux) > MISSION29_PRIMARY_TOLERANCE:
            issues.append('The primary-objective diagnostic does not match the biomass flux.')
    if diagnostics.get('method') != MISSION29_METHOD:
        issues.append('The visible method diagnostics do not describe pFBA.')
    if diagnostics.get('objective_reaction') != MISSION29_GROWTH_OBJECTIVE:
        issues.append('The visible method diagnostics do not describe the biomass objective.')
    if method_score_name != MISSION29_EXPECTED_SCORE_NAME:
        issues.append('The pFBA score label is missing or incorrect.')
    if method_score is None or total_absolute_flux is None:
        issues.append('The pFBA secondary score is missing or non-numeric.')
    elif abs(method_score - total_absolute_flux) > MISSION29_PRIMARY_TOLERANCE:
        issues.append('The pFBA method score does not match total absolute flux.')
    if active_reaction_count is None:
        issues.append('The visible active-reaction count is missing.')

    if run_type == 'wild_type_reference':
        if objective_numeric is not None and objective_numeric < MISSION29_MIN_REFERENCE_GROWTH:
            issues.append('The wild-type reference must show positive default-medium growth.')
        if any(
            reaction_id in disabled_reactions
            for reactions_list in MISSION29_PAIR_REACTIONS.values()
            for reaction_id in reactions_list
        ):
            issues.append('The wild-type reference must not disable a screened isoenzyme reaction through the GPR.')
    elif run_type == 'single_trial' and current_pair:
        expected_reactions = MISSION29_PAIR_REACTIONS[current_pair]
        if any(reaction_id in disabled_reactions for reaction_id in expected_reactions):
            issues.append('A single isoenzyme knockout must leave the matched reaction available through its partner gene.')
    elif run_type == 'pair_trial' and current_pair:
        expected_reactions = MISSION29_PAIR_REACTIONS[current_pair]
        missing_disabled = [reaction_id for reaction_id in expected_reactions if reaction_id not in disabled_reactions]
        if missing_disabled:
            issues.append(
                'The complete pair knockout must disable its matched GPR reaction(s): ' + ', '.join(missing_disabled) + '.'
            )

    current_run_valid = not issues
    current_run_recorded = False
    current_run = None
    if current_run_valid:
        current_run = {
            'run_type': run_type,
            'gene': current_gene,
            'gene_name': MISSION29_GENE_NAMES.get(current_gene) if current_gene else None,
            'pair': current_pair,
            'pair_label': MISSION29_PAIR_LABELS.get(current_pair) if current_pair else None,
            'method': method_name,
            'objective': selected_objective,
            'growth': _mission29_clean_number(objective_numeric),
            'knocked_out_genes': list(knocked_out_genes),
            'disabled_reactions': list(disabled_reactions),
            'environment_changes': list(environment.get('changes') or []),
            'glucose_raw_flux': _mission29_clean_number(glucose_raw),
            'glucose_uptake': _mission29_clean_number(glucose_uptake),
            'oxygen_raw_flux': _mission29_clean_number(oxygen_raw),
            'oxygen_uptake': _mission29_clean_number(oxygen_uptake),
            'method_diagnostics': {
                'method': diagnostics.get('method'),
                'objective_reaction': diagnostics.get('objective_reaction'),
                'primary_objective_flux': _mission29_clean_number(primary_flux),
                'method_score': _mission29_clean_number(method_score),
                'method_score_name': method_score_name,
                'total_absolute_flux': _mission29_clean_number(total_absolute_flux),
                'active_reaction_count': active_reaction_count,
            },
        }
        if run_type == 'wild_type_reference':
            wild_type_reference = current_run
        elif run_type == 'single_trial':
            single_trials[current_gene] = current_run
        elif run_type == 'pair_trial':
            pair_trials[current_pair] = current_run
        current_run_recorded = True

    recorded_run_count = (
        (1 if wild_type_reference else 0)
        + len(single_trials)
        + len(pair_trials)
    )
    missing_conditions = []
    if not wild_type_reference:
        missing_conditions.append('wild_type_reference')
    missing_conditions.extend(
        f'single:{gene_id}' for gene_id in MISSION29_SINGLE_GENES if gene_id not in single_trials
    )
    missing_conditions.extend(
        f'pair:{pair_id}' for pair_id in MISSION29_PAIR_ORDER if pair_id not in pair_trials
    )

    single_growth_retention = {}
    pair_growth_retention = {}
    pair_interaction_summary = {}
    synthetic_candidates = []
    reference_growth = _mission29_number_or_none((wild_type_reference or {}).get('growth'))
    if reference_growth is not None and reference_growth > MISSION29_PRIMARY_TOLERANCE:
        for gene_id, trial in single_trials.items():
            growth = _mission29_number_or_none(trial.get('growth'))
            if growth is not None:
                single_growth_retention[gene_id] = _mission29_clean_number(growth / reference_growth)
        for pair_id, trial in pair_trials.items():
            growth = _mission29_number_or_none(trial.get('growth'))
            if growth is not None:
                pair_growth_retention[pair_id] = _mission29_clean_number(growth / reference_growth)

        for pair_id in MISSION29_PAIR_ORDER:
            gene_a, gene_b = MISSION29_PAIRS[pair_id]
            ret_a = single_growth_retention.get(gene_a)
            ret_b = single_growth_retention.get(gene_b)
            pair_ret = pair_growth_retention.get(pair_id)
            pair_trial = pair_trials.get(pair_id) or {}
            expected_reactions = MISSION29_PAIR_REACTIONS[pair_id]
            disabled_ok = bool(pair_trial) and all(
                reaction_id in (pair_trial.get('disabled_reactions') or [])
                for reaction_id in expected_reactions
            )
            if ret_a is not None and ret_b is not None and pair_ret is not None:
                min_single = min(ret_a, ret_b)
                pair_interaction_summary[pair_id] = {
                    'single_a_retention': ret_a,
                    'single_b_retention': ret_b,
                    'minimum_single_retention': _mission29_clean_number(min_single),
                    'pair_retention': pair_ret,
                    'interaction_drop': _mission29_clean_number(min_single - pair_ret),
                    'matched_reactions_disabled': disabled_ok,
                }
                if (
                    ret_a >= MISSION29_MIN_SINGLE_RETENTION
                    and ret_b >= MISSION29_MIN_SINGLE_RETENTION
                    and pair_ret <= MISSION29_MAX_SYNTHETIC_PAIR_RETENTION
                    and disabled_ok
                ):
                    synthetic_candidates.append(pair_id)

    evidence_ready = recorded_run_count == MISSION29_REQUIRED_RUN_COUNT and not missing_conditions
    unique_synthetic_pair = synthetic_candidates[0] if len(synthetic_candidates) == 1 else None
    controls_remain_viable = bool(
        evidence_ready
        and unique_synthetic_pair
        and all(
            pair_growth_retention.get(pair_id, 0.0) >= MISSION29_MIN_CONTROL_PAIR_RETENTION
            for pair_id in MISSION29_PAIR_ORDER
            if pair_id != unique_synthetic_pair
        )
    )
    unique_synthetic_supported = bool(
        evidence_ready
        and controls_remain_viable
        and unique_synthetic_pair is not None
    )

    latest_attempt = {
        'method': method_name,
        'objective': selected_objective,
        'run_type': run_type,
        'gene': current_gene,
        'pair': current_pair,
        'knocked_out_genes': list(knocked_out_genes),
        'valid': current_run_valid,
        'recorded': current_run_recorded,
        'issues': list(issues),
    }

    report = _mission29_empty_report()
    report.update({
        'wild_type_reference': wild_type_reference,
        'single_trials': single_trials,
        'pair_trials': pair_trials,
        'recorded_run_count': recorded_run_count,
        'missing_conditions': missing_conditions,
        'single_growth_retention': single_growth_retention,
        'pair_growth_retention': pair_growth_retention,
        'pair_interaction_summary': pair_interaction_summary,
        'synthetic_lethal_candidates': synthetic_candidates,
        'unique_synthetic_pair': unique_synthetic_pair,
        'unique_synthetic_lethality_supported': unique_synthetic_supported,
        'evidence_ready': evidence_ready,
        'answer_ready': unique_synthetic_supported,
        'ready_to_deliver': unique_synthetic_supported,
        'current_run_type': run_type,
        'current_gene': current_gene,
        'current_pair': current_pair,
        'current_run_valid': current_run_valid,
        'current_run_recorded': current_run_recorded,
        'current_issues': list(issues),
        'current_run': current_run,
        'latest_attempt': latest_attempt,
    })
    save_mission29_redundancy_check(report)
    return report


def run_mission29_redundancy_check(simulation_results=None):
    """Validate the already displayed Mission 29 result without re-simulating."""
    method_name, selected_objective, genes, reactions = _read_simulation_file()
    objective_result = None
    production_fluxes = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results is not None:
            result_objective = simulation_results[0]
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
            if result_objective != selected_objective:
                objective_error = 'The displayed simulation result does not match the currently selected objective.'
        else:
            objective_error = 'Run a visible Mission 29 simulation before recording evidence.'
    except Exception:
        objective_error = 'Could not read the current visible Mission 29 simulation result.'

    return _build_mission29_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        existing_report=load_mission29_redundancy_check() or {},
        objective_error=objective_error,
    )


def run_mission29_redundancy_check_remote(backend_url, simulation_results=None):
    """Browser parity wrapper using the same visible backend response."""
    del backend_url
    return run_mission29_redundancy_check(simulation_results)


def _normalise_mission29_text(value):
    text = unicodedata.normalize('NFKD', str(value or ''))
    return ''.join(char for char in text if not unicodedata.combining(char)).lower().strip()


def normalise_mission29_answer(answer):
    text = _normalise_mission29_text(answer)
    compact = re.sub(r'[^a-z0-9]+', ' ', text).strip()
    tokens = set(compact.split())
    pair_aliases = {
        'aconitase': [
            ({'b0118', 'b1276'}, None),
            ({'acnb', 'acna'}, None),
            ({'aconta', 'acontb'}, None),
            (set(), r'\baconitase(?:\s+isoenzyme|\s+isoenzymes|\s+pair)?\b'),
        ],
        'phosphofructokinase': [
            ({'b1723', 'b3916'}, None),
            ({'pfkb', 'pfka'}, None),
            (set(), r'\bphosphofructokinase(?:\s+isoenzyme|\s+isoenzymes|\s+pair)?\b'),
        ],
        'pyruvate_kinase': [
            ({'b1676', 'b1854'}, None),
            ({'pykf', 'pyka'}, None),
            (set(), r'\bpyruvate\s+kinase(?:\s+isoenzyme|\s+isoenzymes|\s+pair)?\b'),
        ],
    }
    matches = []
    for pair_id, aliases in pair_aliases.items():
        if any((required and required.issubset(tokens)) or (pattern and re.search(pattern, compact)) for required, pattern in aliases):
            matches.append(pair_id)
    return matches[0] if len(matches) == 1 else None


def mission29_answer_matches(answer, report_data=None):
    report = report_data if report_data is not None else (load_mission29_redundancy_check() or {})
    return bool(
        report.get('mission_id') == '29'
        and report.get('check_version') == MISSION29_CHECK_VERSION
        and report.get('answer_ready')
        and report.get('unique_synthetic_lethality_supported')
        and normalise_mission29_answer(answer) == report.get('unique_synthetic_pair')
    )


def _mission29_run_growth_text(run):
    if not isinstance(run, dict):
        return 'pending'
    growth = _mission29_number_or_none(run.get('growth'))
    return 'pending' if growth is None else f'{growth:.3f}'


def build_mission29_redundancy_report_text(report_data=None):
    report = report_data or {}
    if not report:
        return (
            'No redundancy evidence has been recorded yet.\n\n'
            'Experimental objective:\n'
            'Keep the aerobic default medium fixed and use pFBA with the biomass objective. '
            'Record wild type, both single knockouts and the matched double knockout for each highlighted isoenzyme pair.\n\n'
            'What to determine:\n'
            'Compare single-gene retention with double-knockout retention and the GPR-disabled reactions. '
            'Identify a non-additive interaction in which either single perturbation is tolerated but the matched pair abolishes predicted growth.'
        )

    lines = [
        'Mission 29 Isoenzyme Redundancy Screen',
        '',
        'Controlled protocol:',
        f'- Method: {MISSION29_METHOD}',
        f'- Objective: {MISSION29_GROWTH_OBJECTIVE}',
        '- Environment: completely model-default and aerobic',
        '- For each highlighted pair: wild type reference, both single knockouts and the exact matched double knockout',
        '',
        f"Runs recorded: {report.get('recorded_run_count', 0)}/{report.get('required_run_count', MISSION29_REQUIRED_RUN_COUNT)}",
        '',
        'Wild-type reference:',
    ]
    wt = report.get('wild_type_reference')
    if wt:
        lines.extend([
            f"- Growth: {float(wt.get('growth', 0.0)):.3f}",
            f"- Glucose uptake: {float(wt.get('glucose_uptake', 0.0)):.3f}",
            f"- Oxygen uptake: {float(wt.get('oxygen_uptake', 0.0)):.3f}",
        ])
    else:
        lines.append('- Pending')

    lines.extend([
        '',
        'Matched isoenzyme screen:',
        'Pair | single A growth | single B growth | double growth | double retention | GPR-disabled reactions',
    ])
    singles = report.get('single_trials') or {}
    pairs = report.get('pair_trials') or {}
    pair_retention = report.get('pair_growth_retention') or {}
    for pair_id in MISSION29_PAIR_ORDER:
        gene_a, gene_b = MISSION29_PAIRS[pair_id]
        pair_run = pairs.get(pair_id)
        retention = pair_retention.get(pair_id)
        retention_text = 'pending' if retention is None else f'{100.0 * float(retention):.1f}%'
        disabled_text = 'pending'
        if pair_run:
            disabled_text = ', '.join(pair_run.get('disabled_reactions') or []) or 'none'
        lines.append(
            f"{gene_a}/{MISSION29_GENE_NAMES[gene_a]} + {gene_b}/{MISSION29_GENE_NAMES[gene_b]} | "
            f"{_mission29_run_growth_text(singles.get(gene_a))} | "
            f"{_mission29_run_growth_text(singles.get(gene_b))} | "
            f"{_mission29_run_growth_text(pair_run)} | {retention_text} | {disabled_text}"
        )

    latest = report.get('latest_attempt') or {}
    if latest:
        lines.append('')
        if latest.get('recorded'):
            if latest.get('run_type') == 'wild_type_reference':
                label = 'wild_type_reference'
            elif latest.get('run_type') == 'single_trial':
                label = f"single_trial[{latest.get('gene')}]"
            elif latest.get('run_type') == 'pair_trial':
                label = f"pair_trial[{latest.get('pair')}]"
            else:
                label = 'unknown'
            lines.append(f'Latest valid visible run recorded: {label}.')
        else:
            lines.append('Latest run was not recorded:')
            for issue in latest.get('issues') or ['The visible run did not match the controlled Mission 29 protocol.']:
                lines.append(f'- {issue}')
            if report.get('recorded_run_count', 0):
                lines.append('Previously valid Mission 29 redundancy evidence remains available.')

    lines.append('')
    if report.get('evidence_ready'):
        lines.extend([
            'Evidence complete.',
            'Compare each single knockout with its matched double knockout and inspect the GPR-disabled reactions.',
            'Question: Which tested gene pair shows a synthetic-lethal interaction under this default aerobic model context?',
        ])
    else:
        lines.append('Evidence incomplete.')
        missing = report.get('missing_conditions') or []
        if missing:
            lines.append('Missing conditions: ' + ', '.join(missing))

    lines.extend([
        '',
        'Interpretation note: redundancy can mask the effect of a single knockout. Synthetic lethality here means that both single knockouts retain predicted growth while their matched double knockout abolishes it in this model context.',
        'The conclusion is conditional on this model, pFBA biomass objective, default aerobic medium and tested pair set.',
        'All growth, exchange and GPR evidence comes from visible simulation results. No hidden validation simulation is used.',
    ])
    return '\n'.join(lines)


def _build_mission29_text(report_data=None):
    return build_mission29_redundancy_report_text(report_data)
