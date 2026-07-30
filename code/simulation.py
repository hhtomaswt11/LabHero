import copy
import json
import sys

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

MISSION13_BASELINE_METHOD = 'FBA'
MISSION13_TARGET_METHOD = 'pFBA'
MISSION13_TARGET_PRODUCT = 'succinate'
MISSION13_TARGET_OBJECTIVE = 'EX_succ_e'
MISSION13_OXYGEN_REACTION = 'EX_o2_e'
MISSION13_REQUIRED_TRACKED_FLUXES = ['EX_succ_e']
MISSION13_COMPETING_FLUXES = ['EX_ac_e', 'EX_for_e', 'EX_etoh_e', 'EX_lac__D_e']
MISSION13_MIN_COMPETING_FLUXES = 3
MISSION13_MIN_TARGET_FLUX = 1.0

MISSION14_TARGET_METHOD = 'pFBA'
MISSION14_TARGET_PRODUCT = 'succinate'
MISSION14_TARGET_OBJECTIVE = 'EX_succ_e'
MISSION14_UNWANTED_PRODUCT = 'ethanol'
MISSION14_UNWANTED_FLUX = 'EX_etoh_e'
MISSION14_OXYGEN_REACTION = 'EX_o2_e'
MISSION14_TARGET_GENE = 'b1241'
MISSION14_TARGET_GENE_NAME = 'adhE'
MISSION14_CANDIDATE_GENES = ['b0903', 'b2297', 'b0728', 'b3115', 'b0118', 'b1241']
MISSION14_REQUIRED_TRACKED_FLUXES = ['EX_succ_e', 'EX_etoh_e']
MISSION14_MIN_TARGET_FLUX = 1.0
MISSION14_MAX_UNWANTED_FLUX = 1.0

MISSION15_TARGET_METHOD = 'pFBA'
MISSION15_TARGET_PRODUCT = 'succinate'
MISSION15_TARGET_OBJECTIVE = 'EX_succ_e'
MISSION15_OXYGEN_REACTION = 'EX_o2_e'
MISSION15_TARGET_GENE = 'b1241'
MISSION15_TARGET_GENE_NAME = 'adhE'
MISSION15_CANDIDATE_GENES = ['b0903', 'b2297', 'b0728', 'b3115', 'b0118', 'b1241']
MISSION15_REQUIRED_TRACKED_FLUXES = ['EX_succ_e', 'EX_etoh_e', 'EX_ac_e', 'EX_for_e', 'EX_lac__D_e']
MISSION15_TARGET_FLUX = 'EX_succ_e'
MISSION15_UNWANTED_FLUX = 'EX_etoh_e'
MISSION15_MIN_TARGET_FLUX = 1.0
MISSION15_MAX_UNWANTED_FLUX = 1.0
MISSION15_MIN_GROWTH = 1.0

MISSION16_METHOD = 'FBA'
MISSION16_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION16_BLOCKED_CARBON_SOURCE = 'EX_glc__D_e'
MISSION16_TARGET_CONTEXT = 'alternative carbon rescue'
MISSION16_CANDIDATE_CARBON_SOURCES = ['EX_ac_e', 'EX_pyr_e', 'EX_mal__L_e', 'EX_fum_e', 'EX_akg_e']
MISSION16_REQUIRED_MEDIUM_FLUXES = [
    MISSION16_BLOCKED_CARBON_SOURCE,
    'EX_ac_e',
    'EX_pyr_e',
    'EX_mal__L_e',
    'EX_fum_e',
    'EX_akg_e',
    'EX_nh4_e',
    'EX_pi_e',
    'EX_o2_e',
]
MISSION16_MIN_GROWTH = 5.0
MISSION16_MIN_SOURCE_UPTAKE = 0.001

MISSION17_METHOD = 'FBA'
MISSION17_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION17_TARGET_CONTEXT = 'essential medium component'
MISSION17_TARGET_NUTRIENT = 'EX_pi_e'
MISSION17_TARGET_NUTRIENT_NAME = 'phosphate'
MISSION17_CANDIDATE_NUTRIENTS = ['EX_nh4_e', 'EX_pi_e', 'EX_h2o_e', 'EX_h_e', 'EX_co2_e']
MISSION17_REQUIRED_MEDIUM_FLUXES = [
    'EX_glc__D_e',
    'EX_nh4_e',
    'EX_pi_e',
    'EX_h2o_e',
    'EX_h_e',
    'EX_co2_e',
    'EX_o2_e',
]
MISSION17_MAX_GROWTH = 1.0
MISSION17_MIN_BASELINE_GROWTH = 5.0

MISSION18_METHOD = 'FBA'
MISSION18_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION18_TARGET_CONTEXT = 'export bottleneck'
MISSION18_BLOCKED_CARBON_SOURCE = 'EX_glc__D_e'
MISSION18_ALTERNATIVE_CARBON_SOURCE = 'EX_pyr_e'
MISSION18_EXPORT_BOTTLENECK = 'EX_ac_e'
MISSION18_EXPORT_BOTTLENECK_NAME = 'acetate'
MISSION18_REQUIRED_MEDIUM_FLUXES = [
    MISSION18_BLOCKED_CARBON_SOURCE,
    MISSION18_ALTERNATIVE_CARBON_SOURCE,
    MISSION18_EXPORT_BOTTLENECK,
    'EX_etoh_e',
    'EX_for_e',
    'EX_succ_e',
    'EX_nh4_e',
    'EX_pi_e',
    'EX_o2_e',
]
MISSION18_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_etoh_e', 'EX_for_e', 'EX_succ_e']
MISSION18_MIN_GROWTH = 1.0
MISSION18_MIN_SOURCE_UPTAKE = 0.001
MISSION18_MAX_BLOCKED_EXPORT_FLUX = 0.001

MISSION19_TARGET_METHOD = 'lMOMA'
MISSION19_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION19_TARGET_CONTEXT = 'single-gene perturbation response'
MISSION19_TARGET_GENE = 'b2296'
MISSION19_TARGET_GENE_NAME = 'ackA'
MISSION19_CANDIDATE_GENES = ['b0118', 'b1276', 'b0720', 'b1611', 'b3236', 'b0728', 'b2296']
MISSION19_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_etoh_e', 'EX_for_e', 'EX_lac__D_e', 'EX_succ_e']
MISSION19_MIN_GROWTH = 0.1

MISSION20_TARGET_METHOD = 'pFBA'
MISSION20_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION20_TARGET_CONTEXT = 'final medium robustness report'
MISSION20_BLOCKED_CARBON_SOURCE = 'EX_glc__D_e'
MISSION20_ALTERNATIVE_CARBON_SOURCE = 'EX_pyr_e'
MISSION20_EXPORT_BOTTLENECK = 'EX_ac_e'
MISSION20_EXPORT_BOTTLENECK_NAME = 'acetate'
MISSION20_REQUIRED_ESSENTIAL_UPTAKES = ['EX_nh4_e', 'EX_pi_e']
MISSION20_REQUIRED_MEDIUM_FLUXES = [
    MISSION20_BLOCKED_CARBON_SOURCE,
    MISSION20_ALTERNATIVE_CARBON_SOURCE,
    MISSION20_EXPORT_BOTTLENECK,
    'EX_nh4_e',
    'EX_pi_e',
    'EX_o2_e',
]
MISSION20_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_etoh_e', 'EX_for_e', 'EX_succ_e', 'EX_lac__D_e']
MISSION20_MIN_GROWTH = 1.0
MISSION20_MIN_SOURCE_UPTAKE = 0.001
MISSION20_MIN_ESSENTIAL_UPTAKE = 0.001
MISSION20_MAX_BLOCKED_EXPORT_FLUX = 0.001

MISSION21_METHOD = 'FBA'
MISSION21_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION21_OXYGEN_REACTION = 'EX_o2_e'
MISSION21_TARGET_CONTEXT = 'controlled comparison: aerobic vs anaerobic growth'
MISSION21_MIN_VIABLE_GROWTH = 0.1
MISSION21_MIN_GROWTH_DROP = 1.0

MISSION22_METHOD = 'FBA'
MISSION22_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION22_TARGET_CONTEXT = 'controlled comparison: no knockout vs production knockout'
MISSION22_TARGET_PRODUCT = 'ethanol'
MISSION22_TARGET_FLUX = 'EX_etoh_e'
MISSION22_TARGET_GENE = 'b2297'
MISSION22_TARGET_GENE_NAME = 'pta'
MISSION22_CANDIDATE_GENES = ['b0728', 'b1241', 'b2975', 'b2297', 'b0723']
MISSION22_MIN_GROWTH = 1.0
MISSION22_MIN_PRODUCTION_INCREASE = 20.0

MISSION23_METHOD = 'FBA'
MISSION23_TARGET_CONTEXT = 'controlled comparison: biomass objective vs product objective'
MISSION23_BASELINE_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION23_TARGET_OBJECTIVE = 'EX_etoh_e'
MISSION23_TARGET_PRODUCT = 'ethanol'
MISSION23_TARGET_FLUX = 'EX_etoh_e'
MISSION23_MIN_BASELINE_OBJECTIVE_VALUE = 0.1
MISSION23_MIN_TARGET_OBJECTIVE_VALUE = 1.0
MISSION23_MIN_PRODUCTION_INCREASE = 20.0

MISSION24_BASELINE_METHOD = 'FBA'
MISSION24_TARGET_METHOD = 'pFBA'
MISSION24_TARGET_CONTEXT = 'controlled comparison: FBA vs pFBA method'
MISSION24_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION24_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_etoh_e', 'EX_for_e', 'EX_lac__D_e', 'EX_succ_e']
MISSION24_MIN_OBJECTIVE_VALUE = 0.1

MISSION25_METHOD = 'FBA'
MISSION25_TARGET_CONTEXT = 'final controlled comparison report: aerobic vs oxygen-limited product profile'
MISSION25_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION25_OXYGEN_REACTION = 'EX_o2_e'
MISSION25_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_etoh_e', 'EX_for_e', 'EX_lac__D_e', 'EX_succ_e']
MISSION25_MIN_VIABLE_GROWTH = 0.1
MISSION25_MIN_GROWTH_DROP = 1.0
MISSION25_MIN_CHANGED_FLUXES = 2
MISSION25_MIN_FLUX_CHANGE = 0.001

MISSION26_METHOD = 'FBA'
MISSION26_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION26_TARGET_CONTEXT = 'oxygen sensitivity sweep: aerobic to anaerobic transition'
MISSION26_SWEEP_REACTION = 'EX_o2_e'
MISSION26_SWEEP_REACTION_NAME = 'Oxygen exchange'
MISSION26_SWEEP_BOUND = 'lower'
MISSION26_SWEEP_BOUND_LABEL = 'lower bound'
MISSION26_SWEEP_VALUES = [-20.0, -10.0, -5.0, 0.0]
MISSION26_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_etoh_e', 'EX_for_e', 'EX_lac__D_e', 'EX_succ_e']
MISSION26_MIN_GROWTH_DROP = 0.5
MISSION26_MIN_PROFILE_CHANGE = 1.0
MISSION26_MIN_CHANGED_FLUXES = 2
MISSION26_MIN_VALID_POINTS = 4

MISSION27_METHOD = 'FBA'
MISSION27_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION27_TARGET_CONTEXT = 'glucose sensitivity sweep: carbon limitation threshold'
MISSION27_SWEEP_REACTION = 'EX_glc__D_e'
MISSION27_SWEEP_REACTION_NAME = 'D-Glucose exchange'
MISSION27_SWEEP_BOUND = 'lower'
MISSION27_SWEEP_BOUND_LABEL = 'lower bound'
MISSION27_SWEEP_VALUES = [-1000.0, -500.0, -100.0, -50.0, -10.0, 0.0]
MISSION27_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_etoh_e', 'EX_for_e', 'EX_lac__D_e', 'EX_succ_e']
MISSION27_MIN_GROWTH_DROP = 10.0
MISSION27_MIN_UPTAKE_DROP = 100.0
MISSION27_MAX_FINAL_GROWTH = 1.0
MISSION27_MIN_PROFILE_CHANGE = 10.0
MISSION27_MIN_CHANGED_FLUXES = 3
MISSION27_MIN_RESULT_POINTS = 6
MISSION27_MIN_DECREASING_STEPS = 3

MISSION28_METHOD = 'FBA'
MISSION28_GROWTH_OBJECTIVE = 'BIOMASS_Ecoli_core_w_GAM'
MISSION28_TARGET_CONTEXT = 'alternative carbon source sensitivity sweep under glucose removal'
MISSION28_BLOCKED_CARBON_SOURCE = 'EX_glc__D_e'
MISSION28_CANDIDATE_CARBON_SOURCES = ['EX_ac_e', 'EX_pyr_e', 'EX_mal__L_e', 'EX_fum_e', 'EX_akg_e']
MISSION28_SWEEP_BOUND = 'lower'
MISSION28_SWEEP_BOUND_LABEL = 'lower bound'
MISSION28_SWEEP_VALUES = [-20.0, -10.0, -5.0, -1.0, 0.0]
MISSION28_REQUIRED_TRACKED_FLUXES = ['EX_ac_e', 'EX_etoh_e', 'EX_for_e', 'EX_lac__D_e', 'EX_succ_e']
MISSION28_MIN_FIRST_GROWTH = 5.0
MISSION28_MAX_FINAL_GROWTH = 1.0
MISSION28_MIN_GROWTH_DROP = 5.0
MISSION28_MIN_SOURCE_UPTAKE_DROP = 5.0
MISSION28_MIN_SOURCE_UPTAKE = 1.0
MISSION28_MIN_PROFILE_CHANGE = 1.0
MISSION28_MIN_CHANGED_FLUXES = 2
MISSION28_MIN_RESULT_POINTS = 5
MISSION28_MIN_DECREASING_STEPS = 2


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



def _normalise_result(result):
    results_str = str(result)
    try:
        if str(results_str.splitlines()[1]) == 'Status: INFEASIBLE':
            return 'Status: INFEASIBLE'
        return round(float(str(results_str.splitlines()[0])[11:]), 3)
    except Exception:
        return results_str


def _numeric_result(value):
    try:
        return max(float(value), 0.0)
    except Exception:
        return 0.0


def _read_simulation_file():
    data_simul = load_file(get_save_path('simulation_file'))
    method, objective, genes, reactions = data_simul[:4]

    method_name = method['method'][0][0]
    objective_name = objective['objective'][0][0]

    return method_name, objective_name, genes, reactions



def _build_default_reactions_data():
    reactions_data = {}
    for i in range(len(REACTIONS.index)):
        reactions_data[f'reaction_{i}_lb'] = REACTIONS.lb.iloc[i] != 0
        reactions_data[f'reaction_{i}_ub'] = REACTIONS.ub.iloc[i] != 0
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

    reaction_values = list(reactions.values())
    lb_index = oxygen_index * 2
    if lb_index >= len(reaction_values):
        return False

    return not bool(reaction_values[lb_index])


def _mission08_environment_status(reactions):
    """Classify the medium as default or oxygen-constrained.

    Mission 08 accepts exactly two environmental states: the unchanged model
    medium, or that same medium with only the oxygen-exchange lower bound
    closed.  Any other changed bound is returned as an unexpected change.
    """
    reaction_values = list(reactions.values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION08_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1
        if ub_index >= len(reaction_values):
            break

        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])
        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0
        reaction_id = REACTIONS.index[i]

        if i == oxygen_index:
            oxygen_lower_bound_closed = not lower_bound_open
            # The lower bound may either remain at its default state or be
            # closed.  The upper bound must remain unchanged.
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
    """Return whether Mission 13 changed only the oxygen lower bound."""
    reaction_values = list(reactions.values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION13_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        reaction_id = REACTIONS.index[i]

        if i == oxygen_index:
            oxygen_lower_bound_closed = not lower_bound_open
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
        else:
            if lower_bound_open != default_lower_bound_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')

    return oxygen_lower_bound_closed, unexpected_changes



def _mission14_environment_status(reactions):
    """Return whether Mission 14 changed only the oxygen lower bound."""
    reaction_values = list(reactions.values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION14_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        reaction_id = REACTIONS.index[i]

        if i == oxygen_index:
            oxygen_lower_bound_closed = not lower_bound_open
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
        else:
            if lower_bound_open != default_lower_bound_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')

    return oxygen_lower_bound_closed, unexpected_changes



def _mission15_environment_status(reactions):
    """Return whether Mission 15 changed only the oxygen lower bound."""
    reaction_values = list(reactions.values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION15_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        reaction_id = REACTIONS.index[i]

        if i == oxygen_index:
            oxygen_lower_bound_closed = not lower_bound_open
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')
        else:
            if lower_bound_open != default_lower_bound_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_bound_open != default_upper_bound_open:
                unexpected_changes.append(f'{reaction_id} upper bound')

    return oxygen_lower_bound_closed, unexpected_changes


def _environment_has_changes(reactions):
    reaction_values = list(reactions.values())
    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        lower_bound_open = reaction_values[lb_index]
        upper_bound_open = reaction_values[ub_index]

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


def _simulate_local_objective(method_name, objective_name, genes, reactions):
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
    simul, constraints = _build_local_constraints(genes, reactions)
    simul.objective = objective_name
    result = simul.simulate(method=method_name, constraints=constraints)
    objective_result = _normalise_result(result)

    if objective_result == 'Status: INFEASIBLE':
        return (
            objective_result,
            _build_production_flux_data(
                selected_fluxes,
                error='Simulation infeasible. Production fluxes could not be measured.'
            ),
            _build_medium_flux_data(
                error='Simulation infeasible. Medium fluxes could not be measured.'
            )
        )

    flux_getter = lambda reaction_id: _extract_flux(result, reaction_id)
    production_fluxes = _build_production_flux_data(
        selected_fluxes,
        flux_getter=flux_getter
    )
    # Preserve the unrounded objective-reaction flux for score-based missions.
    # Display text may still use the traditional three-decimal objective value.
    objective_raw = _as_float_or_none(_extract_flux(result, objective_name))
    if objective_raw is not None:
        production_fluxes['objective_raw'] = float(objective_raw)
    biomass_raw = _as_float_or_none(_extract_flux(result, MISSION07_BIOMASS_OBJECTIVE))
    if biomass_raw is not None:
        production_fluxes['biomass_raw'] = float(biomass_raw)
    medium_fluxes = _build_medium_flux_data(
        flux_getter=flux_getter
    )
    return objective_result, production_fluxes, medium_fluxes




def _simulate_local_reaction_flux(method_name, objective_name, genes, reactions, reaction_id):
    """Run a local simulation and read one reaction flux from its solution.

    For lMOMA/ROOM, the printed objective value may represent the method
    objective instead of the biomass reaction flux. Mission 19 therefore reads
    the biomass reaction flux directly from the solution.
    """
    simul, constraints = _build_local_constraints(genes, reactions)
    simul.objective = objective_name
    result = simul.simulate(method=method_name, constraints=constraints)
    raw_flux = _extract_flux(result, reaction_id)
    return _as_float_or_none(raw_flux)

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
            issues.append(f'The dominant product within the required panel should be {_mission11_product_label(MISSION11_EXPECTED_DOMINANT_FLUX)}.')

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
            'Dominant tracked product: ' + _mission11_product_label(fingerprint.get('dominant_product')),
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
                issues.append('Acetate (EX_ac_e) should appear as a positive co-product at the oxygen-constrained succinate optimum.')
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
            comparison_issues.append('Acetate should increase from approximately zero to a positive co-product after oxygen uptake is disabled.')
        if new_byproduct != MISSION12_EXPECTED_NEW_BYPRODUCT:
            comparison_issues.append('The new positive anaerobic co-product should be acetate (EX_ac_e).')
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
            f"Acetate change after disabling oxygen uptake: {float(acetate_change):+.3f}",
            'New positive co-product: ' + _mission12_product_label(report_data.get('new_byproduct')),
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
        'In this model and under these bounds, disabling oxygen uptake reduces the theoretical succinate maximum and introduces acetate as a predicted co-product.',
        'Both direct succinate-optimal solutions have no predicted growth. They are theoretical product optima, not viable production-strain claims.',
        'A zero exchange flux describes only this model, objective and set of constraints; it is not a universal biological incapacity.',
        'All target, byproduct, biomass and medium values come from the same two visible solutions. No hidden simulation is used.',
    ])
    return '\n'.join(lines)


def _build_mission13_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    flux_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == MISSION13_TARGET_METHOD
    baseline_method_selected = method_name == MISSION13_BASELINE_METHOD
    objective_correct = selected_objective == MISSION13_TARGET_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_valid = objective_value is not None and objective_value > 0
    oxygen_lower_bound_closed, unexpected_environment_changes = _mission13_environment_status(reactions)

    target_flux_tracked = MISSION13_TARGET_OBJECTIVE in selected_fluxes
    target_flux = flux_values.get(MISSION13_TARGET_OBJECTIVE, 0.0)
    target_flux_positive = target_flux >= MISSION13_MIN_TARGET_FLUX

    selected_competing_fluxes = [
        reaction_id
        for reaction_id in MISSION13_COMPETING_FLUXES
        if reaction_id in selected_fluxes
    ]
    competing_fluxes_ready = len(selected_competing_fluxes) >= MISSION13_MIN_COMPETING_FLUXES

    missing_required_fluxes = [
        reaction_id
        for reaction_id in MISSION13_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]

    baseline_data = load_mission12_byproduct_check()
    baseline_available = (
        isinstance(baseline_data, dict)
        and baseline_data.get('mission_id') == '12'
        and baseline_data.get('check_version') == MISSION12_CHECK_VERSION
        and baseline_data.get('evidence_ready')
    )
    baseline_run = (baseline_data.get('oxygen_constrained_run') or {}) if baseline_available else {}
    baseline_target_flux = baseline_run.get('target_flux') if baseline_available else None
    baseline_method = baseline_run.get('method') if baseline_available else None

    flux_difference = None
    try:
        if baseline_target_flux is not None:
            flux_difference = round(float(target_flux) - float(baseline_target_flux), 3)
    except Exception:
        flux_difference = None

    mission13_data = {
        'mission_id': '13',
        'check_version': 1,
        'target_product': MISSION13_TARGET_PRODUCT,
        'target_objective': MISSION13_TARGET_OBJECTIVE,
        'baseline_method': MISSION13_BASELINE_METHOD,
        'target_method': MISSION13_TARGET_METHOD,
        'method': method_name,
        'method_correct': method_correct,
        'baseline_method_selected': baseline_method_selected,
        'selected_objective': selected_objective,
        'objective_correct': objective_correct,
        'objective_result': round(objective_value, 3) if objective_value is not None else str(objective_result),
        'oxygen_reaction': MISSION13_OXYGEN_REACTION,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'selected_fluxes': selected_fluxes,
        'tracked_flux_values': {reaction_id: round(value, 3) for reaction_id, value in flux_values.items()},
        'required_tracked_fluxes': MISSION13_REQUIRED_TRACKED_FLUXES,
        'missing_required_fluxes': missing_required_fluxes,
        'competing_flux_options': MISSION13_COMPETING_FLUXES,
        'selected_competing_fluxes': selected_competing_fluxes,
        'minimum_competing_fluxes': MISSION13_MIN_COMPETING_FLUXES,
        'target_flux_tracked': target_flux_tracked,
        'target_flux': round(target_flux, 3),
        'minimum_target_flux': MISSION13_MIN_TARGET_FLUX,
        'target_flux_positive': target_flux_positive,
        'competing_fluxes_ready': competing_fluxes_ready,
        'baseline_available': baseline_available,
        'previous_baseline_method': baseline_method,
        'previous_fba_target_flux': baseline_target_flux,
        'target_flux_difference_from_fba': flux_difference,
        'result_valid': result_valid,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and oxygen_lower_bound_closed
            and not unexpected_environment_changes
            and not knocked_out_genes
            and target_flux_tracked
            and target_flux_positive
            and competing_fluxes_ready
            and result_valid
        ),
    }
    if objective_error:
        mission13_data['error'] = objective_error
    save_mission13_method_check(mission13_data)
    return mission13_data


def run_mission13_method_check(simulation_results=None):
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
        objective_error = 'Run the simulation before delivering Mission 13.'

    return _build_mission13_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        objective_error=objective_error,
    )



def _build_mission14_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    flux_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == MISSION14_TARGET_METHOD
    objective_correct = selected_objective == MISSION14_TARGET_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_valid = objective_value is not None and objective_value > 0
    oxygen_lower_bound_closed, unexpected_environment_changes = _mission14_environment_status(reactions)

    exact_one_knockout = len(knocked_out_genes) == 1
    target_gene_found = knocked_out_genes == [MISSION14_TARGET_GENE]

    target_flux_tracked = MISSION14_TARGET_OBJECTIVE in selected_fluxes
    unwanted_flux_tracked = MISSION14_UNWANTED_FLUX in selected_fluxes
    required_fluxes_ready = all(
        reaction_id in selected_fluxes
        for reaction_id in MISSION14_REQUIRED_TRACKED_FLUXES
    )

    target_flux = flux_values.get(MISSION14_TARGET_OBJECTIVE, 0.0)
    unwanted_flux = flux_values.get(MISSION14_UNWANTED_FLUX, 0.0)
    target_flux_positive = target_flux >= MISSION14_MIN_TARGET_FLUX
    unwanted_flux_reduced = unwanted_flux <= MISSION14_MAX_UNWANTED_FLUX

    baseline_data = load_mission13_method_check()
    baseline_available = (
        isinstance(baseline_data, dict)
        and baseline_data.get('mission_id') == '13'
        and baseline_data.get('check_version') == 1
        and baseline_data.get('ready_to_deliver')
    )
    baseline_unwanted_flux = None
    if baseline_available:
        baseline_values = baseline_data.get('tracked_flux_values') or {}
        baseline_unwanted_flux = baseline_values.get(MISSION14_UNWANTED_FLUX)

    unwanted_flux_change = None
    try:
        if baseline_unwanted_flux is not None:
            unwanted_flux_change = round(float(unwanted_flux) - float(baseline_unwanted_flux), 3)
    except Exception:
        unwanted_flux_change = None

    mission14_data = {
        'mission_id': '14',
        'check_version': 1,
        'target_product': MISSION14_TARGET_PRODUCT,
        'target_objective': MISSION14_TARGET_OBJECTIVE,
        'unwanted_product': MISSION14_UNWANTED_PRODUCT,
        'unwanted_flux': MISSION14_UNWANTED_FLUX,
        'target_method': MISSION14_TARGET_METHOD,
        'method': method_name,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'objective_correct': objective_correct,
        'objective_result': round(objective_value, 3) if objective_value is not None else str(objective_result),
        'oxygen_reaction': MISSION14_OXYGEN_REACTION,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'candidate_genes': MISSION14_CANDIDATE_GENES,
        'target_gene': MISSION14_TARGET_GENE,
        'target_gene_name': MISSION14_TARGET_GENE_NAME,
        'knocked_out_genes': knocked_out_genes,
        'exact_one_knockout': exact_one_knockout,
        'target_gene_found': target_gene_found,
        'selected_fluxes': selected_fluxes,
        'tracked_flux_values': {reaction_id: round(value, 3) for reaction_id, value in flux_values.items()},
        'required_tracked_fluxes': MISSION14_REQUIRED_TRACKED_FLUXES,
        'target_flux_tracked': target_flux_tracked,
        'unwanted_flux_tracked': unwanted_flux_tracked,
        'required_fluxes_ready': required_fluxes_ready,
        'target_flux': round(target_flux, 3),
        'minimum_target_flux': MISSION14_MIN_TARGET_FLUX,
        'target_flux_positive': target_flux_positive,
        'current_unwanted_flux': round(unwanted_flux, 3),
        'maximum_unwanted_flux': MISSION14_MAX_UNWANTED_FLUX,
        'unwanted_flux_reduced': unwanted_flux_reduced,
        'baseline_available': baseline_available,
        'previous_unwanted_flux': baseline_unwanted_flux,
        'unwanted_flux_change_from_previous': unwanted_flux_change,
        'result_valid': result_valid,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and oxygen_lower_bound_closed
            and not unexpected_environment_changes
            and exact_one_knockout
            and target_gene_found
            and target_flux_tracked
            and unwanted_flux_tracked
            and required_fluxes_ready
            and target_flux_positive
            and unwanted_flux_reduced
            and result_valid
        ),
    }
    if objective_error:
        mission14_data['error'] = objective_error
    save_mission14_reduction_check(mission14_data)
    return mission14_data


def run_mission14_reduction_check(simulation_results=None):
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
        objective_error = 'Run the simulation before delivering Mission 14.'

    return _build_mission14_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        objective_error=objective_error,
    )



def _build_mission15_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    flux_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == MISSION15_TARGET_METHOD
    objective_correct = selected_objective == MISSION15_TARGET_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_valid = objective_value is not None and objective_value > 0
    oxygen_lower_bound_closed, unexpected_environment_changes = _mission15_environment_status(reactions)

    exact_one_knockout = len(knocked_out_genes) == 1
    target_gene_found = knocked_out_genes == [MISSION15_TARGET_GENE]

    required_fluxes_ready = all(
        reaction_id in selected_fluxes
        for reaction_id in MISSION15_REQUIRED_TRACKED_FLUXES
    )
    target_flux_tracked = MISSION15_TARGET_FLUX in selected_fluxes
    unwanted_flux_tracked = MISSION15_UNWANTED_FLUX in selected_fluxes

    target_flux = flux_values.get(MISSION15_TARGET_FLUX, 0.0)
    unwanted_flux = flux_values.get(MISSION15_UNWANTED_FLUX, 0.0)
    target_flux_positive = target_flux >= MISSION15_MIN_TARGET_FLUX
    unwanted_flux_reduced = unwanted_flux <= MISSION15_MAX_UNWANTED_FLUX

    byproduct_fluxes = {
        reaction_id: flux_values.get(reaction_id, 0.0)
        for reaction_id in MISSION15_REQUIRED_TRACKED_FLUXES
        if reaction_id != MISSION15_TARGET_FLUX
    }
    highest_byproduct_flux = max(byproduct_fluxes.values()) if byproduct_fluxes else 0.0
    target_dominates_byproducts = target_flux > highest_byproduct_flux

    baseline_data = load_mission14_reduction_check()
    baseline_available = (
        isinstance(baseline_data, dict)
        and baseline_data.get('mission_id') == '14'
        and baseline_data.get('check_version') == 1
        and baseline_data.get('ready_to_deliver')
    )
    baseline_target_flux = None
    baseline_unwanted_flux = None
    if baseline_available:
        baseline_target_flux = baseline_data.get('target_flux')
        baseline_unwanted_flux = baseline_data.get('current_unwanted_flux')

    target_flux_change = None
    unwanted_flux_change = None
    try:
        if baseline_target_flux is not None:
            target_flux_change = round(float(target_flux) - float(baseline_target_flux), 3)
    except Exception:
        target_flux_change = None
    try:
        if baseline_unwanted_flux is not None:
            unwanted_flux_change = round(float(unwanted_flux) - float(baseline_unwanted_flux), 3)
    except Exception:
        unwanted_flux_change = None

    mission15_data = {
        'mission_id': '15',
        'check_version': 1,
        'target_product': MISSION15_TARGET_PRODUCT,
        'target_objective': MISSION15_TARGET_OBJECTIVE,
        'target_method': MISSION15_TARGET_METHOD,
        'method': method_name,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'objective_correct': objective_correct,
        'objective_result': round(objective_value, 3) if objective_value is not None else str(objective_result),
        'oxygen_reaction': MISSION15_OXYGEN_REACTION,
        'oxygen_lower_bound_closed': oxygen_lower_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'candidate_genes': MISSION15_CANDIDATE_GENES,
        'target_gene': MISSION15_TARGET_GENE,
        'target_gene_name': MISSION15_TARGET_GENE_NAME,
        'knocked_out_genes': knocked_out_genes,
        'exact_one_knockout': exact_one_knockout,
        'target_gene_found': target_gene_found,
        'selected_fluxes': selected_fluxes,
        'tracked_flux_values': {reaction_id: round(value, 3) for reaction_id, value in flux_values.items()},
        'required_tracked_fluxes': MISSION15_REQUIRED_TRACKED_FLUXES,
        'required_fluxes_ready': required_fluxes_ready,
        'target_flux_tracked': target_flux_tracked,
        'unwanted_flux_tracked': unwanted_flux_tracked,
        'target_flux': round(target_flux, 3),
        'minimum_target_flux': MISSION15_MIN_TARGET_FLUX,
        'target_flux_positive': target_flux_positive,
        'current_unwanted_flux': round(unwanted_flux, 3),
        'maximum_unwanted_flux': MISSION15_MAX_UNWANTED_FLUX,
        'unwanted_flux_reduced': unwanted_flux_reduced,
        'byproduct_fluxes': {reaction_id: round(value, 3) for reaction_id, value in byproduct_fluxes.items()},
        'highest_byproduct_flux': round(highest_byproduct_flux, 3),
        'target_dominates_byproducts': target_dominates_byproducts,
        'baseline_available': baseline_available,
        'previous_target_flux': baseline_target_flux,
        'previous_unwanted_flux': baseline_unwanted_flux,
        'target_flux_change_from_previous': target_flux_change,
        'unwanted_flux_change_from_previous': unwanted_flux_change,
        'result_valid': result_valid,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and oxygen_lower_bound_closed
            and not unexpected_environment_changes
            and exact_one_knockout
            and target_gene_found
            and required_fluxes_ready
            and target_flux_tracked
            and unwanted_flux_tracked
            and target_flux_positive
            and unwanted_flux_reduced
            and target_dominates_byproducts
            and result_valid
        ),
    }
    if objective_error:
        mission15_data['error'] = objective_error
    save_mission15_diagnostic_report_check(mission15_data)
    return mission15_data


def run_mission15_diagnostic_report_check(simulation_results=None):
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
        objective_error = 'Run the simulation before delivering Mission 15.'

    return _build_mission15_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        objective_error=objective_error,
    )


def _mission16_environment_status(reactions):
    """Evaluate the medium changes required for Mission 16.

    The player must close glucose uptake and open exactly one candidate
    alternative carbon source, without adding unrelated medium changes.
    """
    reaction_values = list(reactions.values())
    glucose_lower_bound_closed = False
    selected_sources = []
    unexpected_changes = []

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        reaction_id = REACTIONS.index[i]
        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        lower_changed = lower_bound_open != default_lower_bound_open
        upper_changed = upper_bound_open != default_upper_bound_open

        if reaction_id == MISSION16_BLOCKED_CARBON_SOURCE:
            glucose_lower_bound_closed = not lower_bound_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id in MISSION16_CANDIDATE_CARBON_SOURCES:
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


def _build_mission16_data(method_name, selected_objective, objective_result, genes, reactions, medium_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    method_correct = method_name == MISSION16_METHOD
    objective_correct = selected_objective == MISSION16_GROWTH_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    growth_value = _numeric_result(objective_value)
    growth_ok = growth_value >= MISSION16_MIN_GROWTH

    glucose_lower_bound_closed, selected_sources, unexpected_environment_changes = _mission16_environment_status(reactions)
    exactly_one_alternative_source = len(selected_sources) == 1
    selected_source = selected_sources[0] if exactly_one_alternative_source else None

    raw_fluxes, uptake_fluxes, secretion_fluxes = _medium_flux_maps(medium_fluxes)
    selected_source_uptake = uptake_fluxes.get(selected_source, 0.0) if selected_source else 0.0
    glucose_uptake = uptake_fluxes.get(MISSION16_BLOCKED_CARBON_SOURCE, 0.0)
    source_uptake_detected = selected_source_uptake >= MISSION16_MIN_SOURCE_UPTAKE
    glucose_uptake_blocked = glucose_uptake <= MISSION16_MIN_SOURCE_UPTAKE

    result_valid = objective_value is not None and objective_value > 0

    mission16_data = {
        'mission_id': '16',
        'check_version': 1,
        'mission_title': 'Alternative Carbon Rescue',
        'target_context': MISSION16_TARGET_CONTEXT,
        'method': method_name,
        'target_method': MISSION16_METHOD,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'growth_objective': MISSION16_GROWTH_OBJECTIVE,
        'objective_correct': objective_correct,
        'objective_result': round(growth_value, 3) if objective_value is not None else str(objective_result),
        'blocked_carbon_source': MISSION16_BLOCKED_CARBON_SOURCE,
        'candidate_carbon_sources': MISSION16_CANDIDATE_CARBON_SOURCES,
        'glucose_lower_bound_closed': glucose_lower_bound_closed,
        'selected_alternative_sources': selected_sources,
        'selected_source': selected_source,
        'exactly_one_alternative_source': exactly_one_alternative_source,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'medium_fluxes': medium_fluxes or {},
        'medium_raw_fluxes': {reaction_id: round(value, 3) for reaction_id, value in raw_fluxes.items()},
        'medium_uptake_fluxes': {reaction_id: round(value, 3) for reaction_id, value in uptake_fluxes.items()},
        'medium_secretion_fluxes': {reaction_id: round(value, 3) for reaction_id, value in secretion_fluxes.items()},
        'selected_source_uptake': round(selected_source_uptake, 3),
        'glucose_uptake': round(glucose_uptake, 3),
        'minimum_source_uptake': MISSION16_MIN_SOURCE_UPTAKE,
        'source_uptake_detected': source_uptake_detected,
        'glucose_uptake_blocked': glucose_uptake_blocked,
        'minimum_growth': MISSION16_MIN_GROWTH,
        'growth_ok': growth_ok,
        'result_valid': result_valid,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and glucose_lower_bound_closed
            and glucose_uptake_blocked
            and exactly_one_alternative_source
            and not unexpected_environment_changes
            and not knocked_out_genes
            and source_uptake_detected
            and growth_ok
            and result_valid
        ),
    }
    if objective_error:
        mission16_data['error'] = objective_error
    save_mission16_medium_report_check(mission16_data)
    return mission16_data


def run_mission16_medium_report_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
    except Exception:
        objective_result = None

    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 16.'

    return _build_mission16_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        medium_fluxes=medium_fluxes,
        objective_error=objective_error,
    )



def _mission17_environment_status(reactions):
    """Evaluate the medium perturbation required for Mission 17.

    The player must close exactly one candidate medium component, and the
    intended component is phosphate. This teaches that growth depends on
    essential nutrients, not only on carbon sources or oxygen.
    """
    reaction_values = list(reactions.values())
    closed_candidate_nutrients = []
    unexpected_changes = []

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        reaction_id = REACTIONS.index[i]
        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        lower_changed = lower_bound_open != default_lower_bound_open
        upper_changed = upper_bound_open != default_upper_bound_open

        if reaction_id in MISSION17_CANDIDATE_NUTRIENTS:
            if lower_changed and not lower_bound_open:
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

    return closed_candidate_nutrients, unexpected_changes


def _build_mission17_data(method_name, selected_objective, objective_result, genes, reactions, medium_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    method_correct = method_name == MISSION17_METHOD
    objective_correct = selected_objective == MISSION17_GROWTH_OBJECTIVE

    objective_value = _as_float_or_none(objective_result)
    if objective_value is None and str(objective_result) == 'Status: INFEASIBLE':
        growth_value = 0.0
        result_available = True
        infeasible = True
    else:
        growth_value = _numeric_result(objective_value)
        result_available = objective_value is not None
        infeasible = False

    growth_collapsed = result_available and growth_value <= MISSION17_MAX_GROWTH

    closed_candidate_nutrients, unexpected_environment_changes = _mission17_environment_status(reactions)
    exactly_one_candidate_closed = len(closed_candidate_nutrients) == 1
    selected_nutrient = closed_candidate_nutrients[0] if exactly_one_candidate_closed else None
    target_nutrient_closed = selected_nutrient == MISSION17_TARGET_NUTRIENT

    raw_fluxes, uptake_fluxes, secretion_fluxes = _medium_flux_maps(medium_fluxes)
    target_uptake = uptake_fluxes.get(MISSION17_TARGET_NUTRIENT, 0.0)
    target_uptake_blocked = target_nutrient_closed and target_uptake <= 0.001

    mission17_data = {
        'mission_id': '17',
        'check_version': 1,
        'mission_title': 'Essential Medium Component',
        'target_context': MISSION17_TARGET_CONTEXT,
        'method': method_name,
        'target_method': MISSION17_METHOD,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'growth_objective': MISSION17_GROWTH_OBJECTIVE,
        'objective_correct': objective_correct,
        'objective_result': round(growth_value, 3) if result_available else str(objective_result),
        'simulation_infeasible': infeasible,
        'target_nutrient': MISSION17_TARGET_NUTRIENT,
        'target_nutrient_name': MISSION17_TARGET_NUTRIENT_NAME,
        'candidate_nutrients': MISSION17_CANDIDATE_NUTRIENTS,
        'closed_candidate_nutrients': closed_candidate_nutrients,
        'selected_nutrient': selected_nutrient,
        'exactly_one_candidate_closed': exactly_one_candidate_closed,
        'target_nutrient_closed': target_nutrient_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'medium_fluxes': medium_fluxes or {},
        'medium_raw_fluxes': {reaction_id: round(value, 3) for reaction_id, value in raw_fluxes.items()},
        'medium_uptake_fluxes': {reaction_id: round(value, 3) for reaction_id, value in uptake_fluxes.items()},
        'medium_secretion_fluxes': {reaction_id: round(value, 3) for reaction_id, value in secretion_fluxes.items()},
        'target_nutrient_uptake': round(target_uptake, 3),
        'target_uptake_blocked': target_uptake_blocked,
        'maximum_growth_after_removal': MISSION17_MAX_GROWTH,
        'growth_collapsed': growth_collapsed,
        'result_available': result_available,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and exactly_one_candidate_closed
            and target_nutrient_closed
            and not unexpected_environment_changes
            and not knocked_out_genes
            and growth_collapsed
            and result_available
        ),
    }
    if objective_error:
        mission17_data['error'] = objective_error
    save_mission17_essential_medium_check(mission17_data)
    return mission17_data


def run_mission17_essential_medium_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    medium_fluxes = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
            medium_fluxes = simulation_results[3] if len(simulation_results) > 3 else None
    except Exception:
        objective_result = None

    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 17.'

    return _build_mission17_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        medium_fluxes=medium_fluxes,
        objective_error=objective_error,
    )


def _mission18_environment_status(reactions):
    """Evaluate the export-bottleneck setup required for Mission 18.

    The player must remove glucose uptake, open pyruvate uptake and close
    acetate export. This teaches that exchange bounds affect both import and
    export, and that upper bounds can create secretion bottlenecks.
    """
    reaction_values = list(reactions.values())
    glucose_lower_bound_closed = False
    pyruvate_lower_bound_open = False
    acetate_upper_bound_closed = False
    unexpected_changes = []

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        reaction_id = REACTIONS.index[i]
        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        lower_changed = lower_bound_open != default_lower_bound_open
        upper_changed = upper_bound_open != default_upper_bound_open

        if reaction_id == MISSION18_BLOCKED_CARBON_SOURCE:
            glucose_lower_bound_closed = not lower_bound_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id == MISSION18_ALTERNATIVE_CARBON_SOURCE:
            pyruvate_lower_bound_open = lower_bound_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id == MISSION18_EXPORT_BOTTLENECK:
            acetate_upper_bound_closed = not upper_bound_open
            if lower_changed:
                unexpected_changes.append(f'{reaction_id} lower bound')
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    return (
        glucose_lower_bound_closed,
        pyruvate_lower_bound_open,
        acetate_upper_bound_closed,
        unexpected_changes,
    )


def _build_mission18_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, medium_fluxes=None, objective_error=None):
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    production_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == MISSION18_METHOD
    objective_correct = selected_objective == MISSION18_GROWTH_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_available = objective_value is not None
    growth_value = _numeric_result(objective_value)
    growth_ok = result_available and growth_value >= MISSION18_MIN_GROWTH

    (
        glucose_lower_bound_closed,
        pyruvate_lower_bound_open,
        acetate_upper_bound_closed,
        unexpected_environment_changes,
    ) = _mission18_environment_status(reactions)

    raw_fluxes, uptake_fluxes, secretion_fluxes = _medium_flux_maps(medium_fluxes)
    glucose_uptake = uptake_fluxes.get(MISSION18_BLOCKED_CARBON_SOURCE, 0.0)
    pyruvate_uptake = uptake_fluxes.get(MISSION18_ALTERNATIVE_CARBON_SOURCE, 0.0)
    acetate_medium_secretion = secretion_fluxes.get(MISSION18_EXPORT_BOTTLENECK, 0.0)
    acetate_production_flux = production_values.get(MISSION18_EXPORT_BOTTLENECK, 0.0)

    glucose_uptake_blocked = glucose_uptake <= MISSION18_MIN_SOURCE_UPTAKE
    pyruvate_uptake_detected = pyruvate_uptake >= MISSION18_MIN_SOURCE_UPTAKE
    acetate_export_blocked = acetate_upper_bound_closed and acetate_production_flux <= MISSION18_MAX_BLOCKED_EXPORT_FLUX

    missing_required_fluxes = [
        reaction_id
        for reaction_id in MISSION18_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    tracking_ready = not missing_required_fluxes

    mission18_data = {
        'mission_id': '18',
        'check_version': 1,
        'mission_title': 'Export Bottleneck',
        'target_context': MISSION18_TARGET_CONTEXT,
        'method': method_name,
        'target_method': MISSION18_METHOD,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'growth_objective': MISSION18_GROWTH_OBJECTIVE,
        'objective_correct': objective_correct,
        'objective_result': round(growth_value, 3) if result_available else str(objective_result),
        'blocked_carbon_source': MISSION18_BLOCKED_CARBON_SOURCE,
        'alternative_carbon_source': MISSION18_ALTERNATIVE_CARBON_SOURCE,
        'export_bottleneck': MISSION18_EXPORT_BOTTLENECK,
        'export_bottleneck_name': MISSION18_EXPORT_BOTTLENECK_NAME,
        'glucose_lower_bound_closed': glucose_lower_bound_closed,
        'pyruvate_lower_bound_open': pyruvate_lower_bound_open,
        'acetate_upper_bound_closed': acetate_upper_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'medium_fluxes': medium_fluxes or {},
        'medium_uptake_fluxes': {reaction_id: round(value, 3) for reaction_id, value in uptake_fluxes.items()},
        'medium_secretion_fluxes': {reaction_id: round(value, 3) for reaction_id, value in secretion_fluxes.items()},
        'glucose_uptake': round(glucose_uptake, 3),
        'pyruvate_uptake': round(pyruvate_uptake, 3),
        'acetate_medium_secretion': round(acetate_medium_secretion, 3),
        'minimum_source_uptake': MISSION18_MIN_SOURCE_UPTAKE,
        'glucose_uptake_blocked': glucose_uptake_blocked,
        'pyruvate_uptake_detected': pyruvate_uptake_detected,
        'selected_fluxes': selected_fluxes,
        'tracked_flux_values': {reaction_id: round(value, 3) for reaction_id, value in production_values.items()},
        'required_tracked_fluxes': MISSION18_REQUIRED_TRACKED_FLUXES,
        'missing_required_fluxes': missing_required_fluxes,
        'tracking_ready': tracking_ready,
        'acetate_production_flux': round(acetate_production_flux, 3),
        'maximum_blocked_export_flux': MISSION18_MAX_BLOCKED_EXPORT_FLUX,
        'acetate_export_blocked': acetate_export_blocked,
        'minimum_growth': MISSION18_MIN_GROWTH,
        'growth_ok': growth_ok,
        'result_available': result_available,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and glucose_lower_bound_closed
            and glucose_uptake_blocked
            and pyruvate_lower_bound_open
            and pyruvate_uptake_detected
            and acetate_upper_bound_closed
            and acetate_export_blocked
            and not unexpected_environment_changes
            and not knocked_out_genes
            and tracking_ready
            and growth_ok
            and result_available
        ),
    }
    if objective_error:
        mission18_data['error'] = objective_error
    save_mission18_export_bottleneck_check(mission18_data)
    return mission18_data


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
        objective_error=objective_error,
    )



def _build_mission19_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, biomass_flux=None, objective_error=None):
    """Evaluate Mission 19: lMOMA response to a single gene perturbation."""
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    flux_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == MISSION19_TARGET_METHOD
    objective_correct = selected_objective == MISSION19_GROWTH_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    biomass_flux_value = _as_float_or_none(biomass_flux)
    result_available = objective_value is not None

    # lMOMA minimises a perturbation-distance objective. The printed objective
    # result can therefore be 0 even when the biomass reaction still carries
    # flux. For viability, use the actual biomass flux from the solution when
    # it is available.
    if biomass_flux_value is not None:
        growth_value = _numeric_result(biomass_flux_value)
        growth_measure = 'biomass flux from lMOMA solution'
    else:
        growth_value = _numeric_result(objective_value)
        growth_measure = 'objective result'

    growth_ok = result_available and growth_value >= MISSION19_MIN_GROWTH

    environment_changed = _environment_has_changes(reactions)
    exact_one_knockout = len(knocked_out_genes) == 1
    target_gene_found = knocked_out_genes == [MISSION19_TARGET_GENE]

    missing_required_fluxes = [
        reaction_id
        for reaction_id in MISSION19_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    tracking_ready = not missing_required_fluxes

    mission19_data = {
        'mission_id': '19',
        'check_version': 2,
        'mission_title': 'Perturbation Method Challenge',
        'target_context': MISSION19_TARGET_CONTEXT,
        'method': method_name,
        'target_method': MISSION19_TARGET_METHOD,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'growth_objective': MISSION19_GROWTH_OBJECTIVE,
        'objective_correct': objective_correct,
        'objective_result': round(_numeric_result(objective_value), 3) if objective_value is not None else str(objective_result),
        'biomass_flux': round(growth_value, 3) if result_available else None,
        'growth_measure': growth_measure,
        'candidate_genes': MISSION19_CANDIDATE_GENES,
        'target_gene': MISSION19_TARGET_GENE,
        'target_gene_name': MISSION19_TARGET_GENE_NAME,
        'knocked_out_genes': knocked_out_genes,
        'exact_one_knockout': exact_one_knockout,
        'target_gene_found': target_gene_found,
        'environment_changed': environment_changed,
        'selected_fluxes': selected_fluxes,
        'tracked_flux_values': {reaction_id: round(value, 3) for reaction_id, value in flux_values.items()},
        'required_tracked_fluxes': MISSION19_REQUIRED_TRACKED_FLUXES,
        'missing_required_fluxes': missing_required_fluxes,
        'tracking_ready': tracking_ready,
        'minimum_growth': MISSION19_MIN_GROWTH,
        'growth_ok': growth_ok,
        'result_available': result_available,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and exact_one_knockout
            and target_gene_found
            and not environment_changed
            and tracking_ready
            and growth_ok
            and result_available
        ),
    }
    if objective_error:
        mission19_data['error'] = objective_error
    save_mission19_perturbation_check(mission19_data)
    return mission19_data


def run_mission19_perturbation_check(simulation_results=None):
    method_name, selected_objective, genes, reactions = _read_simulation_file()

    objective_result = None
    production_fluxes = None
    biomass_flux = None
    objective_error = None
    try:
        if simulation_results and simulation_results[0] == selected_objective:
            objective_result = simulation_results[1]
            production_fluxes = simulation_results[2] if len(simulation_results) > 2 else None
    except Exception:
        objective_result = None

    try:
        biomass_flux = _simulate_local_reaction_flux(
            method_name,
            selected_objective,
            genes,
            reactions,
            MISSION19_GROWTH_OBJECTIVE,
        )
    except Exception:
        biomass_flux = None

    if objective_result is None:
        objective_error = 'Run the simulation before delivering Mission 19.'

    return _build_mission19_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        biomass_flux=biomass_flux,
        objective_error=objective_error,
    )


def _mission20_environment_status(reactions):
    """Evaluate the medium/stress setup required for Mission 20."""
    reaction_values = list(reactions.values())
    glucose_lower_bound_closed = False
    pyruvate_lower_bound_open = False
    acetate_upper_bound_closed = False
    unexpected_changes = []

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        reaction_id = REACTIONS.index[i]
        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        lower_changed = lower_bound_open != default_lower_bound_open
        upper_changed = upper_bound_open != default_upper_bound_open

        if reaction_id == MISSION20_BLOCKED_CARBON_SOURCE:
            glucose_lower_bound_closed = not lower_bound_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id == MISSION20_ALTERNATIVE_CARBON_SOURCE:
            pyruvate_lower_bound_open = lower_bound_open
            if not lower_changed or not lower_bound_open:
                unexpected_changes.append(f'{reaction_id} lower bound')
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if reaction_id == MISSION20_EXPORT_BOTTLENECK:
            acetate_upper_bound_closed = not upper_bound_open
            if lower_changed:
                unexpected_changes.append(f'{reaction_id} lower bound')
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    return (
        glucose_lower_bound_closed,
        pyruvate_lower_bound_open,
        acetate_upper_bound_closed,
        unexpected_changes,
    )


def _build_mission20_data(method_name, selected_objective, objective_result, genes, reactions, production_fluxes=None, medium_fluxes=None, objective_error=None):
    """Evaluate Mission 20: final medium robustness report."""
    knocked_out_genes = _knocked_out_genes(genes)
    selected_fluxes = _read_selected_production_fluxes()
    production_values = _production_flux_value_map(production_fluxes)

    method_correct = method_name == MISSION20_TARGET_METHOD
    objective_correct = selected_objective == MISSION20_GROWTH_OBJECTIVE
    objective_value = _as_float_or_none(objective_result)
    result_available = objective_value is not None
    growth_value = _numeric_result(objective_value)
    growth_ok = result_available and growth_value >= MISSION20_MIN_GROWTH

    (
        glucose_lower_bound_closed,
        pyruvate_lower_bound_open,
        acetate_upper_bound_closed,
        unexpected_environment_changes,
    ) = _mission20_environment_status(reactions)

    raw_fluxes, uptake_fluxes, secretion_fluxes = _medium_flux_maps(medium_fluxes)
    glucose_uptake = uptake_fluxes.get(MISSION20_BLOCKED_CARBON_SOURCE, 0.0)
    pyruvate_uptake = uptake_fluxes.get(MISSION20_ALTERNATIVE_CARBON_SOURCE, 0.0)
    acetate_medium_secretion = secretion_fluxes.get(MISSION20_EXPORT_BOTTLENECK, 0.0)
    acetate_production_flux = production_values.get(MISSION20_EXPORT_BOTTLENECK, 0.0)

    glucose_uptake_blocked = glucose_uptake <= MISSION20_MIN_SOURCE_UPTAKE
    pyruvate_uptake_detected = pyruvate_uptake >= MISSION20_MIN_SOURCE_UPTAKE
    acetate_export_blocked = acetate_upper_bound_closed and acetate_production_flux <= MISSION20_MAX_BLOCKED_EXPORT_FLUX

    essential_uptake_values = {
        reaction_id: uptake_fluxes.get(reaction_id, 0.0)
        for reaction_id in MISSION20_REQUIRED_ESSENTIAL_UPTAKES
    }
    missing_essential_uptakes = [
        reaction_id
        for reaction_id, value in essential_uptake_values.items()
        if value < MISSION20_MIN_ESSENTIAL_UPTAKE
    ]
    essential_uptake_ready = not missing_essential_uptakes

    missing_required_fluxes = [
        reaction_id
        for reaction_id in MISSION20_REQUIRED_TRACKED_FLUXES
        if reaction_id not in selected_fluxes
    ]
    tracking_ready = not missing_required_fluxes

    tracked_byproduct_values = {
        reaction_id: round(production_values.get(reaction_id, 0.0), 3)
        for reaction_id in MISSION20_REQUIRED_TRACKED_FLUXES
    }
    positive_tracked_products = [
        reaction_id
        for reaction_id, value in tracked_byproduct_values.items()
        if value > 0.001
    ]

    mission20_data = {
        'mission_id': '20',
        'check_version': 1,
        'mission_title': 'Final Medium Robustness Report',
        'target_context': MISSION20_TARGET_CONTEXT,
        'method': method_name,
        'target_method': MISSION20_TARGET_METHOD,
        'method_correct': method_correct,
        'selected_objective': selected_objective,
        'growth_objective': MISSION20_GROWTH_OBJECTIVE,
        'objective_correct': objective_correct,
        'objective_result': round(growth_value, 3) if result_available else str(objective_result),
        'blocked_carbon_source': MISSION20_BLOCKED_CARBON_SOURCE,
        'alternative_carbon_source': MISSION20_ALTERNATIVE_CARBON_SOURCE,
        'export_bottleneck': MISSION20_EXPORT_BOTTLENECK,
        'export_bottleneck_name': MISSION20_EXPORT_BOTTLENECK_NAME,
        'glucose_lower_bound_closed': glucose_lower_bound_closed,
        'pyruvate_lower_bound_open': pyruvate_lower_bound_open,
        'acetate_upper_bound_closed': acetate_upper_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'knocked_out_genes': knocked_out_genes,
        'medium_fluxes': medium_fluxes or {},
        'medium_uptake_fluxes': {reaction_id: round(value, 3) for reaction_id, value in uptake_fluxes.items()},
        'medium_secretion_fluxes': {reaction_id: round(value, 3) for reaction_id, value in secretion_fluxes.items()},
        'glucose_uptake': round(glucose_uptake, 3),
        'pyruvate_uptake': round(pyruvate_uptake, 3),
        'acetate_medium_secretion': round(acetate_medium_secretion, 3),
        'essential_uptake_values': {reaction_id: round(value, 3) for reaction_id, value in essential_uptake_values.items()},
        'required_essential_uptakes': MISSION20_REQUIRED_ESSENTIAL_UPTAKES,
        'missing_essential_uptakes': missing_essential_uptakes,
        'essential_uptake_ready': essential_uptake_ready,
        'minimum_source_uptake': MISSION20_MIN_SOURCE_UPTAKE,
        'minimum_essential_uptake': MISSION20_MIN_ESSENTIAL_UPTAKE,
        'glucose_uptake_blocked': glucose_uptake_blocked,
        'pyruvate_uptake_detected': pyruvate_uptake_detected,
        'selected_fluxes': selected_fluxes,
        'tracked_flux_values': tracked_byproduct_values,
        'positive_tracked_products': positive_tracked_products,
        'required_tracked_fluxes': MISSION20_REQUIRED_TRACKED_FLUXES,
        'missing_required_fluxes': missing_required_fluxes,
        'tracking_ready': tracking_ready,
        'acetate_production_flux': round(acetate_production_flux, 3),
        'maximum_blocked_export_flux': MISSION20_MAX_BLOCKED_EXPORT_FLUX,
        'acetate_export_blocked': acetate_export_blocked,
        'minimum_growth': MISSION20_MIN_GROWTH,
        'growth_ok': growth_ok,
        'result_available': result_available,
        'ready_to_deliver': (
            method_correct
            and objective_correct
            and glucose_lower_bound_closed
            and glucose_uptake_blocked
            and pyruvate_lower_bound_open
            and pyruvate_uptake_detected
            and acetate_upper_bound_closed
            and acetate_export_blocked
            and essential_uptake_ready
            and not unexpected_environment_changes
            and not knocked_out_genes
            and tracking_ready
            and growth_ok
            and result_available
        ),
    }
    if objective_error:
        mission20_data['error'] = objective_error
    save_mission20_robustness_report_check(mission20_data)
    return mission20_data


def run_mission20_robustness_report_check(simulation_results=None):
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
        objective_error = 'Run the simulation before delivering Mission 20.'

    return _build_mission20_data(
        method_name,
        selected_objective,
        objective_result,
        genes,
        reactions,
        production_fluxes=production_fluxes,
        medium_fluxes=medium_fluxes,
        objective_error=objective_error,
    )





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

    Mission 05 requires the model's default medium with one environmental
    change: oxygen uptake is unavailable.  Every other lower/upper-bound
    toggle must match the SBML model so candidate effects remain comparable.
    """
    reaction_values = list((reactions or {}).values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION05_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1
        if ub_index >= len(reaction_values):
            unexpected_changes.append('incomplete environmental-bound data')
            break

        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])
        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0
        reaction_id = REACTIONS.index[i]

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
    """Return lower/upper bound UI booleans for a reaction.

    The environmental menu stores two booleans per exchange reaction:
    lower-bound open/closed and upper-bound open/closed.
    """
    try:
        reaction_index = list(REACTIONS.index).index(reaction_id)
    except ValueError:
        return None, None

    reaction_values = list(reactions.values())
    lb_index = reaction_index * 2
    ub_index = lb_index + 1
    if ub_index >= len(reaction_values):
        return None, None

    return bool(reaction_values[lb_index]), bool(reaction_values[ub_index])


def _mission21_environment_status(reactions):
    """Evaluate whether the setup is default or only oxygen-limited."""
    reaction_values = list(reactions.values())
    oxygen_lower_bound_closed = False
    unexpected_changes = []

    try:
        oxygen_index = list(REACTIONS.index).index(MISSION21_OXYGEN_REACTION)
    except ValueError:
        oxygen_index = None

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1
        if ub_index >= len(reaction_values):
            break

        reaction_id = REACTIONS.index[i]
        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])
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

    return oxygen_lower_bound_closed, unexpected_changes


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
    oxygen_lower_bound_closed, oxygen_unexpected_changes = _mission21_environment_status(reactions)

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
    if snapshot.get('oxygen_lower_bound_closed') and not snapshot.get('oxygen_unexpected_changes'):
        return f"oxygen lower bound closed ({MISSION21_OXYGEN_REACTION})"
    unexpected = snapshot.get('oxygen_unexpected_changes') or []
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
    oxygen_a = (run_a.get('exchange_uptake_fluxes') or {}).get(oxygen_id, 0.0)
    oxygen_b = (run_b.get('exchange_uptake_fluxes') or {}).get(oxygen_id, 0.0)
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
            val_a = values_a.get(reaction_id, 0.0)
            val_b = values_b.get(reaction_id, 0.0)
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

    A valid trial removes glucose, opens exactly one candidate carbon-source
    lower bound, and leaves every other environmental toggle unchanged.
    """
    reaction_values = list(reactions.values())
    selected_sources = []
    unexpected_changes = []
    glucose_lower_bound_closed = False

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1
        if ub_index >= len(reaction_values):
            break

        reaction_id = REACTIONS.index[i]
        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])
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


def _mission21_is_baseline_run(snapshot):
    if not snapshot:
        return False
    return (
        snapshot.get('method') == MISSION21_METHOD
        and snapshot.get('objective') == MISSION21_GROWTH_OBJECTIVE
        and not snapshot.get('knocked_out_genes')
        and not snapshot.get('environment_changed')
        and snapshot.get('growth_value', 0.0) >= MISSION21_MIN_VIABLE_GROWTH
    )


def _mission21_is_oxygen_limited_run(snapshot):
    if not snapshot:
        return False
    return (
        snapshot.get('method') == MISSION21_METHOD
        and snapshot.get('objective') == MISSION21_GROWTH_OBJECTIVE
        and not snapshot.get('knocked_out_genes')
        and snapshot.get('oxygen_lower_bound_closed')
        and not snapshot.get('oxygen_unexpected_changes')
        and snapshot.get('growth_value', 0.0) >= MISSION21_MIN_VIABLE_GROWTH
    )


def _build_mission21_data(compare_runs=None, error=None):
    compare_runs = compare_runs or load_compare_runs() or {}
    run_a = compare_runs.get('run_a')
    run_b = compare_runs.get('run_b')
    available_runs = [run for run in (run_a, run_b) if run]

    baseline_run = next((run for run in available_runs if _mission21_is_baseline_run(run)), None)
    oxygen_limited_run = next((run for run in available_runs if _mission21_is_oxygen_limited_run(run)), None)

    baseline_growth = baseline_run.get('growth_value') if baseline_run else None
    oxygen_growth = oxygen_limited_run.get('growth_value') if oxygen_limited_run else None
    growth_drop = None
    growth_decreased = False
    if baseline_growth is not None and oxygen_growth is not None:
        growth_drop = round(float(baseline_growth) - float(oxygen_growth), 3)
        growth_decreased = growth_drop >= MISSION21_MIN_GROWTH_DROP

    oxygen_id = MISSION21_OXYGEN_REACTION
    baseline_o2 = None
    oxygen_limited_o2 = None
    oxygen_uptake_decreased = False
    if baseline_run:
        baseline_o2 = (baseline_run.get('exchange_uptake_fluxes') or {}).get(oxygen_id)
    if oxygen_limited_run:
        oxygen_limited_o2 = (oxygen_limited_run.get('exchange_uptake_fluxes') or {}).get(oxygen_id)
    if baseline_o2 is not None and oxygen_limited_o2 is not None:
        try:
            oxygen_uptake_decreased = float(baseline_o2) > float(oxygen_limited_o2) + 0.001
        except Exception:
            oxygen_uptake_decreased = False

    mission21_data = {
        'mission_id': '21',
        'check_version': 1,
        'mission_title': 'Controlled Comparison',
        'target_context': MISSION21_TARGET_CONTEXT,
        'target_method': MISSION21_METHOD,
        'growth_objective': MISSION21_GROWTH_OBJECTIVE,
        'oxygen_reaction': MISSION21_OXYGEN_REACTION,
        'run_a': run_a,
        'run_b': run_b,
        'baseline_run_found': baseline_run is not None,
        'oxygen_limited_run_found': oxygen_limited_run is not None,
        'baseline_growth': round(float(baseline_growth), 3) if baseline_growth is not None else None,
        'oxygen_limited_growth': round(float(oxygen_growth), 3) if oxygen_growth is not None else None,
        'growth_drop': growth_drop,
        'growth_decreased': growth_decreased,
        'baseline_oxygen_uptake': round(float(baseline_o2), 3) if baseline_o2 is not None else None,
        'oxygen_limited_oxygen_uptake': round(float(oxygen_limited_o2), 3) if oxygen_limited_o2 is not None else None,
        'oxygen_uptake_decreased': oxygen_uptake_decreased,
        'ready_to_deliver': (
            baseline_run is not None
            and oxygen_limited_run is not None
            and growth_decreased
        ),
    }
    if error:
        mission21_data['error'] = error
    save_mission21_comparison_check(mission21_data)
    return mission21_data


def run_mission21_comparison_check(compare_runs=None):
    compare_runs = compare_runs or load_compare_runs()
    if not compare_runs or not compare_runs.get('run_a') or not compare_runs.get('run_b'):
        return _build_mission21_data(compare_runs, error='Run two simulations before delivering Mission 21.')
    return _build_mission21_data(compare_runs)


def _mission22_is_baseline_run(snapshot):
    if not snapshot:
        return False
    selected_fluxes = snapshot.get('selected_production_fluxes') or []
    return (
        snapshot.get('method') == MISSION22_METHOD
        and snapshot.get('objective') == MISSION22_GROWTH_OBJECTIVE
        and not snapshot.get('knocked_out_genes')
        and not snapshot.get('environment_changed')
        and MISSION22_TARGET_FLUX in selected_fluxes
        and snapshot.get('growth_value', 0.0) >= MISSION22_MIN_GROWTH
    )


def _mission22_is_knockout_run(snapshot):
    if not snapshot:
        return False
    selected_fluxes = snapshot.get('selected_production_fluxes') or []
    return (
        snapshot.get('method') == MISSION22_METHOD
        and snapshot.get('objective') == MISSION22_GROWTH_OBJECTIVE
        and snapshot.get('knocked_out_genes') == [MISSION22_TARGET_GENE]
        and not snapshot.get('environment_changed')
        and MISSION22_TARGET_FLUX in selected_fluxes
        and snapshot.get('growth_value', 0.0) >= MISSION22_MIN_GROWTH
    )


def _build_mission22_data(compare_runs=None, error=None):
    compare_runs = compare_runs or load_compare_runs() or {}
    run_a = compare_runs.get('run_a')
    run_b = compare_runs.get('run_b')
    available_runs = [run for run in (run_a, run_b) if run]

    baseline_run = next((run for run in available_runs if _mission22_is_baseline_run(run)), None)
    knockout_run = next((run for run in available_runs if _mission22_is_knockout_run(run)), None)

    baseline_growth = baseline_run.get('growth_value') if baseline_run else None
    knockout_growth = knockout_run.get('growth_value') if knockout_run else None

    baseline_flux = None
    knockout_flux = None
    if baseline_run:
        baseline_flux = (baseline_run.get('production_flux_values') or {}).get(MISSION22_TARGET_FLUX)
    if knockout_run:
        knockout_flux = (knockout_run.get('production_flux_values') or {}).get(MISSION22_TARGET_FLUX)

    production_increase = None
    production_increased = False
    if baseline_flux is not None and knockout_flux is not None:
        production_increase = round(float(knockout_flux) - float(baseline_flux), 3)
        production_increased = production_increase >= MISSION22_MIN_PRODUCTION_INCREASE

    target_flux_tracked = False
    if baseline_run and knockout_run:
        target_flux_tracked = (
            MISSION22_TARGET_FLUX in (baseline_run.get('selected_production_fluxes') or [])
            and MISSION22_TARGET_FLUX in (knockout_run.get('selected_production_fluxes') or [])
        )

    growth_ok = (
        baseline_growth is not None
        and knockout_growth is not None
        and float(baseline_growth) >= MISSION22_MIN_GROWTH
        and float(knockout_growth) >= MISSION22_MIN_GROWTH
    )

    mission22_data = {
        'mission_id': '22',
        'check_version': 1,
        'mission_title': 'Knockout Comparison',
        'target_context': MISSION22_TARGET_CONTEXT,
        'target_method': MISSION22_METHOD,
        'growth_objective': MISSION22_GROWTH_OBJECTIVE,
        'target_product': MISSION22_TARGET_PRODUCT,
        'target_flux': MISSION22_TARGET_FLUX,
        'target_gene': MISSION22_TARGET_GENE,
        'target_gene_name': MISSION22_TARGET_GENE_NAME,
        'candidate_genes': MISSION22_CANDIDATE_GENES,
        'minimum_growth': MISSION22_MIN_GROWTH,
        'minimum_production_increase': MISSION22_MIN_PRODUCTION_INCREASE,
        'run_a': run_a,
        'run_b': run_b,
        'baseline_run_found': baseline_run is not None,
        'knockout_run_found': knockout_run is not None,
        'baseline_growth': round(float(baseline_growth), 3) if baseline_growth is not None else None,
        'knockout_growth': round(float(knockout_growth), 3) if knockout_growth is not None else None,
        'baseline_product_flux': round(float(baseline_flux), 3) if baseline_flux is not None else None,
        'knockout_product_flux': round(float(knockout_flux), 3) if knockout_flux is not None else None,
        'production_increase': production_increase,
        'production_increased': production_increased,
        'target_flux_tracked': target_flux_tracked,
        'growth_ok': growth_ok,
        'ready_to_deliver': (
            baseline_run is not None
            and knockout_run is not None
            and target_flux_tracked
            and production_increased
            and growth_ok
        ),
    }
    if error:
        mission22_data['error'] = error
    save_mission22_comparison_check(mission22_data)
    return mission22_data


def run_mission22_comparison_check(compare_runs=None):
    compare_runs = compare_runs or load_compare_runs()
    if not compare_runs or not compare_runs.get('run_a') or not compare_runs.get('run_b'):
        return _build_mission22_data(compare_runs, error='Run two simulations before delivering Mission 22.')
    return _build_mission22_data(compare_runs)


def _mission23_is_growth_objective_run(snapshot):
    if not snapshot:
        return False
    selected_fluxes = snapshot.get('selected_production_fluxes') or []
    return (
        snapshot.get('method') == MISSION23_METHOD
        and snapshot.get('objective') == MISSION23_BASELINE_OBJECTIVE
        and not snapshot.get('knocked_out_genes')
        and not snapshot.get('environment_changed')
        and MISSION23_TARGET_FLUX in selected_fluxes
        and snapshot.get('objective_value', snapshot.get('growth_value', 0.0)) >= MISSION23_MIN_BASELINE_OBJECTIVE_VALUE
    )


def _mission23_is_product_objective_run(snapshot):
    if not snapshot:
        return False
    selected_fluxes = snapshot.get('selected_production_fluxes') or []
    return (
        snapshot.get('method') == MISSION23_METHOD
        and snapshot.get('objective') == MISSION23_TARGET_OBJECTIVE
        and not snapshot.get('knocked_out_genes')
        and not snapshot.get('environment_changed')
        and MISSION23_TARGET_FLUX in selected_fluxes
        and snapshot.get('objective_value', snapshot.get('growth_value', 0.0)) >= MISSION23_MIN_TARGET_OBJECTIVE_VALUE
    )


def _build_mission23_data(compare_runs=None, error=None):
    compare_runs = compare_runs or load_compare_runs() or {}
    run_a = compare_runs.get('run_a')
    run_b = compare_runs.get('run_b')
    available_runs = [run for run in (run_a, run_b) if run]

    growth_objective_run = next((run for run in available_runs if _mission23_is_growth_objective_run(run)), None)
    product_objective_run = next((run for run in available_runs if _mission23_is_product_objective_run(run)), None)

    growth_objective_value = None
    product_objective_value = None
    if growth_objective_run:
        growth_objective_value = growth_objective_run.get('objective_value', growth_objective_run.get('growth_value'))
    if product_objective_run:
        product_objective_value = product_objective_run.get('objective_value', product_objective_run.get('growth_value'))

    baseline_flux = None
    product_flux = None
    if growth_objective_run:
        baseline_flux = (growth_objective_run.get('production_flux_values') or {}).get(MISSION23_TARGET_FLUX)
    if product_objective_run:
        product_flux = (product_objective_run.get('production_flux_values') or {}).get(MISSION23_TARGET_FLUX)

    production_increase = None
    production_increased = False
    if baseline_flux is not None and product_flux is not None:
        production_increase = round(float(product_flux) - float(baseline_flux), 3)
        production_increased = production_increase >= MISSION23_MIN_PRODUCTION_INCREASE

    target_flux_tracked = False
    if growth_objective_run and product_objective_run:
        target_flux_tracked = (
            MISSION23_TARGET_FLUX in (growth_objective_run.get('selected_production_fluxes') or [])
            and MISSION23_TARGET_FLUX in (product_objective_run.get('selected_production_fluxes') or [])
        )

    objective_changed = (
        growth_objective_run is not None
        and product_objective_run is not None
        and growth_objective_run.get('objective') != product_objective_run.get('objective')
    )

    mission23_data = {
        'mission_id': '23',
        'check_version': 1,
        'mission_title': 'Objective Comparison',
        'target_context': MISSION23_TARGET_CONTEXT,
        'target_method': MISSION23_METHOD,
        'baseline_objective': MISSION23_BASELINE_OBJECTIVE,
        'target_objective': MISSION23_TARGET_OBJECTIVE,
        'target_product': MISSION23_TARGET_PRODUCT,
        'target_flux': MISSION23_TARGET_FLUX,
        'minimum_production_increase': MISSION23_MIN_PRODUCTION_INCREASE,
        'run_a': run_a,
        'run_b': run_b,
        'growth_objective_run_found': growth_objective_run is not None,
        'product_objective_run_found': product_objective_run is not None,
        'growth_objective_value': round(float(growth_objective_value), 3) if growth_objective_value is not None else None,
        'product_objective_value': round(float(product_objective_value), 3) if product_objective_value is not None else None,
        'baseline_product_flux': round(float(baseline_flux), 3) if baseline_flux is not None else None,
        'product_objective_flux': round(float(product_flux), 3) if product_flux is not None else None,
        'production_increase': production_increase,
        'production_increased': production_increased,
        'target_flux_tracked': target_flux_tracked,
        'objective_changed': objective_changed,
        'ready_to_deliver': (
            growth_objective_run is not None
            and product_objective_run is not None
            and objective_changed
            and target_flux_tracked
            and production_increased
        ),
    }
    if error:
        mission23_data['error'] = error
    save_mission23_comparison_check(mission23_data)
    return mission23_data


def run_mission23_comparison_check(compare_runs=None):
    compare_runs = compare_runs or load_compare_runs()
    if not compare_runs or not compare_runs.get('run_a') or not compare_runs.get('run_b'):
        return _build_mission23_data(compare_runs, error='Run two simulations before delivering Mission 23.')
    return _build_mission23_data(compare_runs)


def _mission24_same_base_setup(snapshot):
    if not snapshot:
        return False
    return (
        snapshot.get('objective') == MISSION24_GROWTH_OBJECTIVE
        and not snapshot.get('knocked_out_genes')
        and not snapshot.get('environment_changed')
        and snapshot.get('objective_value', snapshot.get('growth_value', 0.0)) >= MISSION24_MIN_OBJECTIVE_VALUE
    )


def _mission24_is_fba_run(snapshot):
    return (
        _mission24_same_base_setup(snapshot)
        and snapshot.get('method') == MISSION24_BASELINE_METHOD
    )


def _mission24_is_pfba_run(snapshot):
    return (
        _mission24_same_base_setup(snapshot)
        and snapshot.get('method') == MISSION24_TARGET_METHOD
    )


def _mission24_tracking_ready(snapshot):
    if not snapshot:
        return False
    selected_fluxes = snapshot.get('selected_production_fluxes') or []
    return all(
        reaction_id in selected_fluxes
        for reaction_id in MISSION24_REQUIRED_TRACKED_FLUXES
    )


def _build_mission24_data(compare_runs=None, error=None):
    compare_runs = compare_runs or load_compare_runs() or {}
    run_a = compare_runs.get('run_a')
    run_b = compare_runs.get('run_b')
    available_runs = [run for run in (run_a, run_b) if run]

    fba_run = next((run for run in available_runs if _mission24_is_fba_run(run)), None)
    pfba_run = next((run for run in available_runs if _mission24_is_pfba_run(run)), None)

    fba_value = fba_run.get('objective_value', fba_run.get('growth_value')) if fba_run else None
    pfba_value = pfba_run.get('objective_value', pfba_run.get('growth_value')) if pfba_run else None

    fba_tracking_ready = _mission24_tracking_ready(fba_run)
    pfba_tracking_ready = _mission24_tracking_ready(pfba_run)
    tracking_ready = fba_tracking_ready and pfba_tracking_ready

    method_changed = (
        fba_run is not None
        and pfba_run is not None
        and fba_run.get('method') != pfba_run.get('method')
    )

    same_objective = (
        fba_run is not None
        and pfba_run is not None
        and fba_run.get('objective') == pfba_run.get('objective') == MISSION24_GROWTH_OBJECTIVE
    )

    same_clean_setup = (
        fba_run is not None
        and pfba_run is not None
        and not fba_run.get('knocked_out_genes')
        and not pfba_run.get('knocked_out_genes')
        and not fba_run.get('environment_changed')
        and not pfba_run.get('environment_changed')
    )

    fba_flux_values = fba_run.get('production_flux_values') if fba_run else {}
    pfba_flux_values = pfba_run.get('production_flux_values') if pfba_run else {}
    flux_differences = {}
    for reaction_id in MISSION24_REQUIRED_TRACKED_FLUXES:
        if reaction_id in fba_flux_values and reaction_id in pfba_flux_values:
            flux_differences[reaction_id] = round(float(pfba_flux_values.get(reaction_id, 0.0)) - float(fba_flux_values.get(reaction_id, 0.0)), 3)

    mission24_data = {
        'mission_id': '24',
        'check_version': 1,
        'mission_title': 'Method Comparison',
        'target_context': MISSION24_TARGET_CONTEXT,
        'baseline_method': MISSION24_BASELINE_METHOD,
        'target_method': MISSION24_TARGET_METHOD,
        'growth_objective': MISSION24_GROWTH_OBJECTIVE,
        'required_tracked_fluxes': MISSION24_REQUIRED_TRACKED_FLUXES,
        'run_a': run_a,
        'run_b': run_b,
        'fba_run_found': fba_run is not None,
        'pfba_run_found': pfba_run is not None,
        'fba_objective_value': round(float(fba_value), 3) if fba_value is not None else None,
        'pfba_objective_value': round(float(pfba_value), 3) if pfba_value is not None else None,
        'method_changed': method_changed,
        'same_objective': same_objective,
        'same_clean_setup': same_clean_setup,
        'fba_tracking_ready': fba_tracking_ready,
        'pfba_tracking_ready': pfba_tracking_ready,
        'tracking_ready': tracking_ready,
        'fba_tracked_flux_values': {reaction_id: round(float(fba_flux_values.get(reaction_id, 0.0)), 3) for reaction_id in MISSION24_REQUIRED_TRACKED_FLUXES},
        'pfba_tracked_flux_values': {reaction_id: round(float(pfba_flux_values.get(reaction_id, 0.0)), 3) for reaction_id in MISSION24_REQUIRED_TRACKED_FLUXES},
        'tracked_flux_differences': flux_differences,
        'ready_to_deliver': (
            fba_run is not None
            and pfba_run is not None
            and method_changed
            and same_objective
            and same_clean_setup
            and tracking_ready
        ),
    }
    if error:
        mission24_data['error'] = error
    save_mission24_comparison_check(mission24_data)
    return mission24_data


def run_mission24_comparison_check(compare_runs=None):
    compare_runs = compare_runs or load_compare_runs()
    if not compare_runs or not compare_runs.get('run_a') or not compare_runs.get('run_b'):
        return _build_mission24_data(compare_runs, error='Run two simulations before delivering Mission 24.')
    return _build_mission24_data(compare_runs)



def _mission25_tracking_ready(snapshot):
    if not snapshot:
        return False
    selected_fluxes = snapshot.get('selected_production_fluxes') or []
    return all(
        reaction_id in selected_fluxes
        for reaction_id in MISSION25_REQUIRED_TRACKED_FLUXES
    )


def _mission25_is_baseline_run(snapshot):
    if not snapshot:
        return False
    return (
        snapshot.get('method') == MISSION25_METHOD
        and snapshot.get('objective') == MISSION25_GROWTH_OBJECTIVE
        and not snapshot.get('knocked_out_genes')
        and not snapshot.get('environment_changed')
        and snapshot.get('growth_value', 0.0) >= MISSION25_MIN_VIABLE_GROWTH
    )


def _mission25_is_oxygen_limited_run(snapshot):
    if not snapshot:
        return False
    return (
        snapshot.get('method') == MISSION25_METHOD
        and snapshot.get('objective') == MISSION25_GROWTH_OBJECTIVE
        and not snapshot.get('knocked_out_genes')
        and snapshot.get('oxygen_lower_bound_closed')
        and not snapshot.get('oxygen_unexpected_changes')
        and snapshot.get('growth_value', 0.0) >= MISSION25_MIN_VIABLE_GROWTH
    )


def _build_mission25_data(compare_runs=None, error=None):
    compare_runs = compare_runs or load_compare_runs() or {}
    run_a = compare_runs.get('run_a')
    run_b = compare_runs.get('run_b')
    available_runs = [run for run in (run_a, run_b) if run]

    baseline_run = next((run for run in available_runs if _mission25_is_baseline_run(run)), None)
    oxygen_limited_run = next((run for run in available_runs if _mission25_is_oxygen_limited_run(run)), None)

    baseline_growth = baseline_run.get('growth_value') if baseline_run else None
    oxygen_growth = oxygen_limited_run.get('growth_value') if oxygen_limited_run else None
    growth_drop = None
    growth_decreased = False
    if baseline_growth is not None and oxygen_growth is not None:
        growth_drop = round(float(baseline_growth) - float(oxygen_growth), 3)
        growth_decreased = growth_drop >= MISSION25_MIN_GROWTH_DROP

    baseline_flux_values = baseline_run.get('production_flux_values') if baseline_run else {}
    oxygen_flux_values = oxygen_limited_run.get('production_flux_values') if oxygen_limited_run else {}
    flux_differences = {}
    changed_fluxes = []
    for reaction_id in MISSION25_REQUIRED_TRACKED_FLUXES:
        if reaction_id in baseline_flux_values and reaction_id in oxygen_flux_values:
            difference = round(float(oxygen_flux_values.get(reaction_id, 0.0)) - float(baseline_flux_values.get(reaction_id, 0.0)), 3)
            flux_differences[reaction_id] = difference
            if abs(difference) >= MISSION25_MIN_FLUX_CHANGE:
                changed_fluxes.append(reaction_id)

    baseline_tracking_ready = _mission25_tracking_ready(baseline_run)
    oxygen_tracking_ready = _mission25_tracking_ready(oxygen_limited_run)
    tracking_ready = baseline_tracking_ready and oxygen_tracking_ready
    production_profile_changed = len(changed_fluxes) >= MISSION25_MIN_CHANGED_FLUXES

    oxygen_id = MISSION25_OXYGEN_REACTION
    baseline_o2 = None
    oxygen_limited_o2 = None
    oxygen_uptake_decreased = False
    if baseline_run:
        baseline_o2 = (baseline_run.get('exchange_uptake_fluxes') or {}).get(oxygen_id)
    if oxygen_limited_run:
        oxygen_limited_o2 = (oxygen_limited_run.get('exchange_uptake_fluxes') or {}).get(oxygen_id)
    if baseline_o2 is not None and oxygen_limited_o2 is not None:
        try:
            oxygen_uptake_decreased = float(baseline_o2) > float(oxygen_limited_o2) + 0.001
        except Exception:
            oxygen_uptake_decreased = False

    mission25_data = {
        'mission_id': '25',
        'check_version': 1,
        'mission_title': 'Final Controlled Report',
        'target_context': MISSION25_TARGET_CONTEXT,
        'target_method': MISSION25_METHOD,
        'growth_objective': MISSION25_GROWTH_OBJECTIVE,
        'oxygen_reaction': MISSION25_OXYGEN_REACTION,
        'required_tracked_fluxes': MISSION25_REQUIRED_TRACKED_FLUXES,
        'minimum_growth_drop': MISSION25_MIN_GROWTH_DROP,
        'minimum_changed_fluxes': MISSION25_MIN_CHANGED_FLUXES,
        'minimum_flux_change': MISSION25_MIN_FLUX_CHANGE,
        'run_a': run_a,
        'run_b': run_b,
        'baseline_run_found': baseline_run is not None,
        'oxygen_limited_run_found': oxygen_limited_run is not None,
        'baseline_tracking_ready': baseline_tracking_ready,
        'oxygen_tracking_ready': oxygen_tracking_ready,
        'tracking_ready': tracking_ready,
        'baseline_growth': round(float(baseline_growth), 3) if baseline_growth is not None else None,
        'oxygen_limited_growth': round(float(oxygen_growth), 3) if oxygen_growth is not None else None,
        'growth_drop': growth_drop,
        'growth_decreased': growth_decreased,
        'baseline_oxygen_uptake': round(float(baseline_o2), 3) if baseline_o2 is not None else None,
        'oxygen_limited_oxygen_uptake': round(float(oxygen_limited_o2), 3) if oxygen_limited_o2 is not None else None,
        'oxygen_uptake_decreased': oxygen_uptake_decreased,
        'baseline_tracked_flux_values': {reaction_id: round(float(baseline_flux_values.get(reaction_id, 0.0)), 3) for reaction_id in MISSION25_REQUIRED_TRACKED_FLUXES},
        'oxygen_limited_tracked_flux_values': {reaction_id: round(float(oxygen_flux_values.get(reaction_id, 0.0)), 3) for reaction_id in MISSION25_REQUIRED_TRACKED_FLUXES},
        'tracked_flux_differences': flux_differences,
        'changed_fluxes': changed_fluxes,
        'changed_flux_count': len(changed_fluxes),
        'production_profile_changed': production_profile_changed,
        'ready_to_deliver': (
            baseline_run is not None
            and oxygen_limited_run is not None
            and tracking_ready
            and growth_decreased
            and production_profile_changed
        ),
    }
    if error:
        mission25_data['error'] = error
    save_mission25_comparison_check(mission25_data)
    return mission25_data


def run_mission25_comparison_check(compare_runs=None):
    compare_runs = compare_runs or load_compare_runs()
    if not compare_runs or not compare_runs.get('run_a') or not compare_runs.get('run_b'):
        return _build_mission25_data(compare_runs, error='Run two simulations before delivering Mission 25.')
    return _build_mission25_data(compare_runs)



def _selected_sweep_value(menu_data, key, default_value):
    """Return the internal value selected in a pygame_menu dropselect.

    pygame_menu can return dropselect data as [(label, internal_value)].
    Earlier code was reading index [0][0], which gives the visible label.
    That broke Mission 27 because the visible label
    "D-Glucose lower bound (EX_glc__D_e)" is not the internal id
    "EX_glc__D_e:lower" used by the Bound Sweep validator.
    """
    try:
        value = menu_data.get(key)
        selected = value[0]
    except Exception:
        return default_value

    candidates = list(selected) if isinstance(selected, (list, tuple)) else [selected]
    preferred_values = {
        'sweep_variable': {
            f'{MISSION26_SWEEP_REACTION}:lower',
            f'{MISSION27_SWEEP_REACTION}:lower',
            *[f'{reaction_id}:lower' for reaction_id in MISSION28_CANDIDATE_CARBON_SOURCES],
        },
        'sweep_values': {
            'oxygen_transition',
            'glucose_limitation',
            'alternative_carbon_limitation',
        },
    }

    for candidate in candidates:
        if candidate in preferred_values.get(key, set()):
            return candidate

    for candidate in reversed(candidates):
        if isinstance(candidate, str):
            return candidate

    return default_value


def _normalise_sweep_config(sweep_menu_data=None):
    sweep_menu_data = sweep_menu_data or {}
    variable = _selected_sweep_value(
        sweep_menu_data,
        'sweep_variable',
        f'{MISSION26_SWEEP_REACTION}:lower'
    )
    preset = _selected_sweep_value(
        sweep_menu_data,
        'sweep_values',
        'oxygen_transition'
    )

    # Keep this data-driven: each new Dr. Luna sweep adds one entry here and
    # the generic sweep runner/report can stay unchanged.
    sweep_options = {
        f'{MISSION26_SWEEP_REACTION}:lower': {
            'reaction_id': MISSION26_SWEEP_REACTION,
            'reaction_name': MISSION26_SWEEP_REACTION_NAME,
            'bound': MISSION26_SWEEP_BOUND,
            'bound_label': MISSION26_SWEEP_BOUND_LABEL,
            'default_preset': 'oxygen_transition',
        },
        f'{MISSION27_SWEEP_REACTION}:lower': {
            'reaction_id': MISSION27_SWEEP_REACTION,
            'reaction_name': MISSION27_SWEEP_REACTION_NAME,
            'bound': MISSION27_SWEEP_BOUND,
            'bound_label': MISSION27_SWEEP_BOUND_LABEL,
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
        'oxygen_transition': list(MISSION26_SWEEP_VALUES),
        'glucose_limitation': list(MISSION27_SWEEP_VALUES),
        'alternative_carbon_limitation': list(MISSION28_SWEEP_VALUES),
    }

    config = sweep_options.get(variable, sweep_options[f'{MISSION26_SWEEP_REACTION}:lower']).copy()

    # If the preset and variable do not match, keep the variable selected by the
    # player but use its matching default values. This avoids confusing results.
    if preset not in preset_values:
        preset = config['default_preset']
    if variable == f'{MISSION26_SWEEP_REACTION}:lower' and preset != 'oxygen_transition':
        preset = 'oxygen_transition'
    if variable == f'{MISSION27_SWEEP_REACTION}:lower' and preset != 'glucose_limitation':
        preset = 'glucose_limitation'
    if variable in [f'{reaction_id}:lower' for reaction_id in MISSION28_CANDIDATE_CARBON_SOURCES] and preset != 'alternative_carbon_limitation':
        preset = 'alternative_carbon_limitation'

    return {
        'variable': variable,
        'preset': preset,
        'reaction_id': config.get('reaction_id'),
        'reaction_name': config.get('reaction_name'),
        'bound': config.get('bound'),
        'bound_label': config.get('bound_label'),
        'values': preset_values[preset],
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
        if reaction_id:
            try:
                values[reaction_id] = float(item.get('production_flux', 0.0))
            except Exception:
                values[reaction_id] = 0.0
    return values


def _bound_sweep_default_tracked_fluxes():
    tracked = []
    for reaction_id in list(MISSION26_REQUIRED_TRACKED_FLUXES) + list(MISSION27_REQUIRED_TRACKED_FLUXES) + list(MISSION28_REQUIRED_TRACKED_FLUXES):
        if reaction_id in PRODUCTION_FLUX_REACTION_IDS and reaction_id not in tracked:
            tracked.append(reaction_id)
    return tracked


def run_bound_sweep(sweep_menu_data=None):
    """Run a one-variable bound sweep using the current simulator setup.

    Dr. Luna missions use this to test sensitivity to medium bounds. The runner
    is generic: the menu chooses the reaction/bound/preset, while each mission
    validates whether the selected sweep is the correct experiment.
    """
    method_name, objective_name, genes, reactions = _read_simulation_file()
    config = _normalise_sweep_config(sweep_menu_data)

    selected_fluxes = _read_selected_production_fluxes()
    tracked_fluxes = []
    for reaction_id in list(selected_fluxes) + _bound_sweep_default_tracked_fluxes():
        if reaction_id in PRODUCTION_FLUX_REACTION_IDS and reaction_id not in tracked_fluxes:
            tracked_fluxes.append(reaction_id)

    knocked_out_genes = _knocked_out_genes(genes)
    environment_changed = _environment_has_changes(reactions)

    data = {
        'sweep_id': 'bound_sweep',
        'check_version': 2,
        'method': method_name,
        'objective': objective_name,
        'knocked_out_genes': knocked_out_genes,
        'environment_changed': environment_changed,
        'base_genes': genes,
        'base_reactions': reactions,
        'variable': config.get('variable'),
        'preset': config.get('preset'),
        'reaction_id': config.get('reaction_id'),
        'reaction_name': config.get('reaction_name'),
        'bound': config.get('bound'),
        'bound_label': config.get('bound_label'),
        'values': config.get('values'),
        'tracked_fluxes': tracked_fluxes,
        'selected_production_fluxes': selected_fluxes,
        'rows': [],
    }

    try:
        for bound_value in config.get('values') or []:
            simul, constraints = _build_local_constraints(genes, reactions)
            simul.objective = objective_name
            constraints = _apply_numeric_bound_to_constraints(
                constraints,
                config.get('reaction_id'),
                config.get('bound'),
                bound_value,
            )
            result = simul.simulate(method=method_name, constraints=constraints)
            objective_result = _normalise_result(result)

            row = {
                'bound_value': float(bound_value),
                'objective_result': objective_result,
                'growth_value': _numeric_result(objective_result),
            }

            if objective_result == 'Status: INFEASIBLE':
                row['status'] = 'infeasible'
                row['tested_reaction_raw_flux'] = 0.0
                row['tested_reaction_uptake'] = 0.0
                row['oxygen_uptake'] = 0.0
                row['tracked_flux_values'] = {reaction_id: 0.0 for reaction_id in tracked_fluxes}
            else:
                row['status'] = 'ok'
                flux_getter = lambda reaction_id: _extract_flux(result, reaction_id)

                tested_flux = _as_float_or_none(flux_getter(config.get('reaction_id')))
                row['tested_reaction_raw_flux'] = round(float(tested_flux), 6) if tested_flux is not None else None
                row['tested_reaction_uptake'] = round(max(-float(tested_flux), 0.0), 3) if tested_flux is not None else 0.0

                oxygen_flux = _as_float_or_none(flux_getter(MISSION26_SWEEP_REACTION))
                row['oxygen_raw_flux'] = round(float(oxygen_flux), 6) if oxygen_flux is not None else None
                row['oxygen_uptake'] = round(max(-float(oxygen_flux), 0.0), 3) if oxygen_flux is not None else 0.0

                production_fluxes = _build_production_flux_data(tracked_fluxes, flux_getter=flux_getter)
                row['tracked_flux_values'] = {
                    reaction_id: round(float(value), 3)
                    for reaction_id, value in _bound_sweep_flux_values(production_fluxes).items()
                }

            data['rows'].append(row)
    except Exception as exc:
        data['error'] = f'Bound Sweep failed: {exc}'

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

def _build_mission26_data(sweep_data=None, error=None):
    sweep_data = sweep_data or load_bound_sweep() or {}
    rows = sweep_data.get('rows') or []
    valid_rows = [row for row in rows if row.get('status') == 'ok']

    clean_base_setup = (
        sweep_data.get('method') == MISSION26_METHOD
        and sweep_data.get('objective') == MISSION26_GROWTH_OBJECTIVE
        and not sweep_data.get('knocked_out_genes')
        and not sweep_data.get('environment_changed')
    )

    expected_values = [float(value) for value in MISSION26_SWEEP_VALUES]
    got_values = [float(value) for value in (sweep_data.get('values') or [])]
    oxygen_sweep_selected = (
        sweep_data.get('reaction_id') == MISSION26_SWEEP_REACTION
        and sweep_data.get('bound') == MISSION26_SWEEP_BOUND
        and got_values == expected_values
    )

    all_points_valid = len(valid_rows) >= MISSION26_MIN_VALID_POINTS

    first_row = valid_rows[0] if valid_rows else None
    last_row = valid_rows[-1] if valid_rows else None
    first_growth = _row_value(first_row, 'growth_value') if first_row else 0.0
    last_growth = _row_value(last_row, 'growth_value') if last_row else 0.0
    growth_drop = round(first_growth - last_growth, 3) if valid_rows else 0.0
    growth_decreased = growth_drop >= MISSION26_MIN_GROWTH_DROP

    first_oxygen = _row_value(first_row, 'oxygen_uptake') if first_row else 0.0
    last_oxygen = _row_value(last_row, 'oxygen_uptake') if last_row else 0.0
    oxygen_uptake_drop = round(first_oxygen - last_oxygen, 3) if valid_rows else 0.0
    oxygen_uptake_decreased = oxygen_uptake_drop > 0.001

    profile_differences = {}
    changed_fluxes = []
    if first_row and last_row:
        first_fluxes = first_row.get('tracked_flux_values') or {}
        last_fluxes = last_row.get('tracked_flux_values') or {}
        for reaction_id in MISSION26_REQUIRED_TRACKED_FLUXES:
            difference = round(float(last_fluxes.get(reaction_id, 0.0)) - float(first_fluxes.get(reaction_id, 0.0)), 3)
            profile_differences[reaction_id] = difference
            if abs(difference) >= MISSION26_MIN_PROFILE_CHANGE:
                changed_fluxes.append(reaction_id)

    profile_changed = len(changed_fluxes) >= MISSION26_MIN_CHANGED_FLUXES

    mission26_data = {
        'mission_id': '26',
        'check_version': 1,
        'mission_title': 'Oxygen Sensitivity Sweep',
        'target_context': MISSION26_TARGET_CONTEXT,
        'target_method': MISSION26_METHOD,
        'growth_objective': MISSION26_GROWTH_OBJECTIVE,
        'sweep_reaction': MISSION26_SWEEP_REACTION,
        'sweep_bound': MISSION26_SWEEP_BOUND,
        'sweep_values': expected_values,
        'required_tracked_fluxes': MISSION26_REQUIRED_TRACKED_FLUXES,
        'minimum_growth_drop': MISSION26_MIN_GROWTH_DROP,
        'minimum_profile_change': MISSION26_MIN_PROFILE_CHANGE,
        'minimum_changed_fluxes': MISSION26_MIN_CHANGED_FLUXES,
        'sweep_data': sweep_data,
        'clean_base_setup': clean_base_setup,
        'oxygen_sweep_selected': oxygen_sweep_selected,
        'valid_point_count': len(valid_rows),
        'all_points_valid': all_points_valid,
        'first_growth': round(first_growth, 3),
        'last_growth': round(last_growth, 3),
        'growth_drop': growth_drop,
        'growth_decreased': growth_decreased,
        'first_oxygen_uptake': round(first_oxygen, 3),
        'last_oxygen_uptake': round(last_oxygen, 3),
        'oxygen_uptake_drop': oxygen_uptake_drop,
        'oxygen_uptake_decreased': oxygen_uptake_decreased,
        'profile_differences': profile_differences,
        'changed_fluxes': changed_fluxes,
        'changed_flux_count': len(changed_fluxes),
        'profile_changed': profile_changed,
        'ready_to_deliver': (
            clean_base_setup
            and oxygen_sweep_selected
            and all_points_valid
            and growth_decreased
            and oxygen_uptake_decreased
            and profile_changed
        ),
    }
    if error or sweep_data.get('error'):
        mission26_data['error'] = error or sweep_data.get('error')
    save_mission26_bound_sweep_check(mission26_data)
    return mission26_data


def run_mission26_bound_sweep_check(sweep_data=None):
    sweep_data = sweep_data or load_bound_sweep()
    if not sweep_data or not sweep_data.get('rows'):
        return _build_mission26_data(sweep_data, error='Run a Bound Sweep before delivering Mission 26.')
    return _build_mission26_data(sweep_data)



def _build_mission27_data(sweep_data=None, error=None):
    sweep_data = sweep_data or load_bound_sweep() or {}
    rows = sweep_data.get('rows') or []
    result_rows = [row for row in rows if row.get('status') in ('ok', 'infeasible')]
    ok_rows = [row for row in rows if row.get('status') == 'ok']

    clean_base_setup = (
        sweep_data.get('method') == MISSION27_METHOD
        and sweep_data.get('objective') == MISSION27_GROWTH_OBJECTIVE
        and not sweep_data.get('knocked_out_genes')
        and not sweep_data.get('environment_changed')
    )

    expected_values = [float(value) for value in MISSION27_SWEEP_VALUES]
    got_values = [float(value) for value in (sweep_data.get('values') or [])]
    glucose_sweep_selected = (
        sweep_data.get('reaction_id') == MISSION27_SWEEP_REACTION
        and sweep_data.get('bound') == MISSION27_SWEEP_BOUND
        and got_values == expected_values
    )

    tracking_ready = _selected_fluxes_include(
        MISSION27_REQUIRED_TRACKED_FLUXES,
        sweep_data.get('selected_production_fluxes') or []
    )
    all_points_returned = len(result_rows) >= MISSION27_MIN_RESULT_POINTS

    first_row = result_rows[0] if result_rows else None
    last_row = result_rows[-1] if result_rows else None
    first_growth = _row_value(first_row, 'growth_value') if first_row else 0.0
    last_growth = _row_value(last_row, 'growth_value') if last_row else 0.0
    growth_drop = round(first_growth - last_growth, 3) if result_rows else 0.0
    growth_decreased = growth_drop >= MISSION27_MIN_GROWTH_DROP
    final_growth_low = last_growth <= MISSION27_MAX_FINAL_GROWTH if last_row else False

    growth_values = _growth_values_from_rows(result_rows)
    decreasing_steps = _count_decreasing_steps(growth_values)
    trend_is_gradual = decreasing_steps >= MISSION27_MIN_DECREASING_STEPS

    first_uptake = _row_value(first_row, 'tested_reaction_uptake') if first_row else 0.0
    last_uptake = _row_value(last_row, 'tested_reaction_uptake') if last_row else 0.0
    glucose_uptake_drop = round(first_uptake - last_uptake, 3) if result_rows else 0.0
    glucose_uptake_decreased = glucose_uptake_drop >= MISSION27_MIN_UPTAKE_DROP

    profile_differences = {}
    decreased_fluxes = []
    if first_row and last_row:
        first_fluxes = first_row.get('tracked_flux_values') or {}
        last_fluxes = last_row.get('tracked_flux_values') or {}
        for reaction_id in MISSION27_REQUIRED_TRACKED_FLUXES:
            difference = round(float(last_fluxes.get(reaction_id, 0.0)) - float(first_fluxes.get(reaction_id, 0.0)), 3)
            profile_differences[reaction_id] = difference
            if difference <= -MISSION27_MIN_PROFILE_CHANGE:
                decreased_fluxes.append(reaction_id)

    profile_decreased = len(decreased_fluxes) >= MISSION27_MIN_CHANGED_FLUXES

    mission27_data = {
        'mission_id': '27',
        'check_version': 1,
        'mission_title': 'Glucose Limitation Sweep',
        'target_context': MISSION27_TARGET_CONTEXT,
        'target_method': MISSION27_METHOD,
        'growth_objective': MISSION27_GROWTH_OBJECTIVE,
        'sweep_reaction': MISSION27_SWEEP_REACTION,
        'sweep_bound': MISSION27_SWEEP_BOUND,
        'sweep_values': expected_values,
        'required_tracked_fluxes': MISSION27_REQUIRED_TRACKED_FLUXES,
        'minimum_growth_drop': MISSION27_MIN_GROWTH_DROP,
        'minimum_uptake_drop': MISSION27_MIN_UPTAKE_DROP,
        'maximum_final_growth': MISSION27_MAX_FINAL_GROWTH,
        'minimum_profile_change': MISSION27_MIN_PROFILE_CHANGE,
        'minimum_changed_fluxes': MISSION27_MIN_CHANGED_FLUXES,
        'minimum_result_points': MISSION27_MIN_RESULT_POINTS,
        'minimum_decreasing_steps': MISSION27_MIN_DECREASING_STEPS,
        'sweep_data': sweep_data,
        'clean_base_setup': clean_base_setup,
        'glucose_sweep_selected': glucose_sweep_selected,
        'tracking_ready': tracking_ready,
        'result_point_count': len(result_rows),
        'valid_ok_point_count': len(ok_rows),
        'all_points_returned': all_points_returned,
        'first_growth': round(first_growth, 3),
        'last_growth': round(last_growth, 3),
        'growth_drop': growth_drop,
        'growth_decreased': growth_decreased,
        'final_growth_low': final_growth_low,
        'decreasing_steps': decreasing_steps,
        'trend_is_gradual': trend_is_gradual,
        'first_glucose_uptake': round(first_uptake, 3),
        'last_glucose_uptake': round(last_uptake, 3),
        'glucose_uptake_drop': glucose_uptake_drop,
        'glucose_uptake_decreased': glucose_uptake_decreased,
        'profile_differences': profile_differences,
        'decreased_fluxes': decreased_fluxes,
        'decreased_flux_count': len(decreased_fluxes),
        'profile_decreased': profile_decreased,
        'ready_to_deliver': (
            clean_base_setup
            and glucose_sweep_selected
            and tracking_ready
            and all_points_returned
            and growth_decreased
            and final_growth_low
            and trend_is_gradual
            and glucose_uptake_decreased
            and profile_decreased
        ),
    }
    if error or sweep_data.get('error'):
        mission27_data['error'] = error or sweep_data.get('error')
    save_mission27_bound_sweep_check(mission27_data)
    return mission27_data


def run_mission27_bound_sweep_check(sweep_data=None):
    sweep_data = sweep_data or load_bound_sweep()
    if not sweep_data or not sweep_data.get('rows'):
        return _build_mission27_data(sweep_data, error='Run a Bound Sweep before delivering Mission 27.')
    return _build_mission27_data(sweep_data)



def _mission28_environment_status(reactions):
    """Mission 28 base medium: close only glucose lower bound.

    The sweep itself supplies the alternative source numerically. Before the
    sweep, the only manual medium change should be glucose removal.
    """
    reaction_values = list((reactions or {}).values())
    glucose_lower_bound_closed = False
    unexpected_changes = []

    for i in range(len(REACTIONS.index)):
        lb_index = i * 2
        ub_index = lb_index + 1

        if ub_index >= len(reaction_values):
            break

        reaction_id = REACTIONS.index[i]
        lower_bound_open = bool(reaction_values[lb_index])
        upper_bound_open = bool(reaction_values[ub_index])

        default_lower_bound_open = REACTIONS.lb.iloc[i] != 0
        default_upper_bound_open = REACTIONS.ub.iloc[i] != 0

        lower_changed = lower_bound_open != default_lower_bound_open
        upper_changed = upper_bound_open != default_upper_bound_open

        if reaction_id == MISSION28_BLOCKED_CARBON_SOURCE:
            glucose_lower_bound_closed = not lower_bound_open
            if upper_changed:
                unexpected_changes.append(f'{reaction_id} upper bound')
            continue

        if lower_changed:
            unexpected_changes.append(f'{reaction_id} lower bound')
        if upper_changed:
            unexpected_changes.append(f'{reaction_id} upper bound')

    return glucose_lower_bound_closed, unexpected_changes


def _build_mission28_data(sweep_data=None, error=None):
    sweep_data = sweep_data or load_bound_sweep() or {}
    rows = sweep_data.get('rows') or []
    result_rows = [row for row in rows if row.get('status') in ('ok', 'infeasible')]
    ok_rows = [row for row in rows if row.get('status') == 'ok']

    base_reactions = sweep_data.get('base_reactions') or {}
    glucose_lower_bound_closed, unexpected_environment_changes = _mission28_environment_status(base_reactions)

    base_medium_ready = (
        sweep_data.get('method') == MISSION28_METHOD
        and sweep_data.get('objective') == MISSION28_GROWTH_OBJECTIVE
        and not sweep_data.get('knocked_out_genes')
        and glucose_lower_bound_closed
        and not unexpected_environment_changes
    )

    expected_values = [float(value) for value in MISSION28_SWEEP_VALUES]
    got_values = [float(value) for value in (sweep_data.get('values') or [])]
    selected_source = sweep_data.get('reaction_id')
    candidate_sweep_selected = (
        selected_source in MISSION28_CANDIDATE_CARBON_SOURCES
        and sweep_data.get('bound') == MISSION28_SWEEP_BOUND
        and got_values == expected_values
    )

    tracking_ready = _selected_fluxes_include(
        MISSION28_REQUIRED_TRACKED_FLUXES,
        sweep_data.get('selected_production_fluxes') or []
    )
    all_points_returned = len(result_rows) >= MISSION28_MIN_RESULT_POINTS

    first_row = result_rows[0] if result_rows else None
    last_row = result_rows[-1] if result_rows else None
    first_growth = _row_value(first_row, 'growth_value') if first_row else 0.0
    last_growth = _row_value(last_row, 'growth_value') if last_row else 0.0
    growth_drop = round(first_growth - last_growth, 3) if result_rows else 0.0
    first_growth_viable = first_growth >= MISSION28_MIN_FIRST_GROWTH
    growth_decreased = growth_drop >= MISSION28_MIN_GROWTH_DROP
    final_growth_low = last_growth <= MISSION28_MAX_FINAL_GROWTH if last_row else False

    growth_values = _growth_values_from_rows(result_rows)
    decreasing_steps = _count_decreasing_steps(growth_values)
    trend_is_gradual = decreasing_steps >= MISSION28_MIN_DECREASING_STEPS

    first_uptake = _row_value(first_row, 'tested_reaction_uptake') if first_row else 0.0
    last_uptake = _row_value(last_row, 'tested_reaction_uptake') if last_row else 0.0
    source_uptake_drop = round(first_uptake - last_uptake, 3) if result_rows else 0.0
    source_consumed = first_uptake >= MISSION28_MIN_SOURCE_UPTAKE
    source_uptake_decreased = source_uptake_drop >= MISSION28_MIN_SOURCE_UPTAKE_DROP

    profile_differences = {}
    changed_fluxes = []
    if first_row and last_row:
        first_fluxes = first_row.get('tracked_flux_values') or {}
        last_fluxes = last_row.get('tracked_flux_values') or {}
        for reaction_id in MISSION28_REQUIRED_TRACKED_FLUXES:
            difference = round(float(last_fluxes.get(reaction_id, 0.0)) - float(first_fluxes.get(reaction_id, 0.0)), 3)
            profile_differences[reaction_id] = difference
            if abs(difference) >= MISSION28_MIN_PROFILE_CHANGE:
                changed_fluxes.append(reaction_id)

    profile_changed = len(changed_fluxes) >= MISSION28_MIN_CHANGED_FLUXES

    mission28_data = {
        'mission_id': '28',
        'check_version': 1,
        'mission_title': 'Alternative Carbon Source Sweep',
        'target_context': MISSION28_TARGET_CONTEXT,
        'target_method': MISSION28_METHOD,
        'growth_objective': MISSION28_GROWTH_OBJECTIVE,
        'blocked_carbon_source': MISSION28_BLOCKED_CARBON_SOURCE,
        'candidate_carbon_sources': MISSION28_CANDIDATE_CARBON_SOURCES,
        'selected_source': selected_source,
        'sweep_bound': MISSION28_SWEEP_BOUND,
        'sweep_values': expected_values,
        'required_tracked_fluxes': MISSION28_REQUIRED_TRACKED_FLUXES,
        'minimum_first_growth': MISSION28_MIN_FIRST_GROWTH,
        'maximum_final_growth': MISSION28_MAX_FINAL_GROWTH,
        'minimum_growth_drop': MISSION28_MIN_GROWTH_DROP,
        'minimum_source_uptake': MISSION28_MIN_SOURCE_UPTAKE,
        'minimum_source_uptake_drop': MISSION28_MIN_SOURCE_UPTAKE_DROP,
        'minimum_profile_change': MISSION28_MIN_PROFILE_CHANGE,
        'minimum_changed_fluxes': MISSION28_MIN_CHANGED_FLUXES,
        'minimum_result_points': MISSION28_MIN_RESULT_POINTS,
        'minimum_decreasing_steps': MISSION28_MIN_DECREASING_STEPS,
        'sweep_data': sweep_data,
        'glucose_lower_bound_closed': glucose_lower_bound_closed,
        'unexpected_environment_changes': unexpected_environment_changes,
        'base_medium_ready': base_medium_ready,
        'candidate_sweep_selected': candidate_sweep_selected,
        'tracking_ready': tracking_ready,
        'result_point_count': len(result_rows),
        'valid_ok_point_count': len(ok_rows),
        'all_points_returned': all_points_returned,
        'first_growth': round(first_growth, 3),
        'last_growth': round(last_growth, 3),
        'first_growth_viable': first_growth_viable,
        'growth_drop': growth_drop,
        'growth_decreased': growth_decreased,
        'final_growth_low': final_growth_low,
        'decreasing_steps': decreasing_steps,
        'trend_is_gradual': trend_is_gradual,
        'first_source_uptake': round(first_uptake, 3),
        'last_source_uptake': round(last_uptake, 3),
        'source_uptake_drop': source_uptake_drop,
        'source_consumed': source_consumed,
        'source_uptake_decreased': source_uptake_decreased,
        'profile_differences': profile_differences,
        'changed_fluxes': changed_fluxes,
        'changed_flux_count': len(changed_fluxes),
        'profile_changed': profile_changed,
        'ready_to_deliver': (
            base_medium_ready
            and candidate_sweep_selected
            and tracking_ready
            and all_points_returned
            and source_consumed
            and source_uptake_decreased
            and first_growth_viable
            and growth_decreased
            and final_growth_low
            and trend_is_gradual
            and profile_changed
        ),
    }
    if error or sweep_data.get('error'):
        mission28_data['error'] = error or sweep_data.get('error')
    save_mission28_bound_sweep_check(mission28_data)
    return mission28_data


def run_mission28_bound_sweep_check(sweep_data=None):
    sweep_data = sweep_data or load_bound_sweep()
    if not sweep_data or not sweep_data.get('rows'):
        return _build_mission28_data(sweep_data, error='Run a Bound Sweep before delivering Mission 28.')
    return _build_mission28_data(sweep_data)

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
        objective_raw = _as_float_or_none(fluxes.get(payload['objective'], response.get('result')))
        if objective_raw is not None:
            production_fluxes['objective_raw'] = float(objective_raw)
        biomass_raw = _as_float_or_none(fluxes.get(MISSION07_BIOMASS_OBJECTIVE))
        if biomass_raw is not None:
            production_fluxes['biomass_raw'] = float(biomass_raw)
        return response['objective'], response['result'], production_fluxes, _build_medium_flux_data(
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
