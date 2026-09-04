"""Canonical in-game book content for LabHero.

BOOKS.1 keeps the scientific reference text in one pure-Python module so the
Pygame menu and the repository Markdown mirrors cannot silently diverge.
"""

BOOK_LIBRARY = (
    {
        "id": "how_to_play",
        "title": "How to Play",
        "color": (255, 215, 0),
        "intro": (
            "LabHero is a mission-based metabolic-modelling game. Talk to scientists, "
            "configure controlled simulations, inspect the visible evidence and submit "
            "only conclusions supported by your runs."
        ),
        "sections": (
            (
                "Movement and interaction",
                (
                    "Move with the arrow keys or WASD. Press ENTER when you are close to "
                    "a scientist, computer, bookshelf or other interactive object.",
                    "Press M to open the game menu. Press E to open the key inventory. "
                    "ESC closes the current menu when that screen supports it.",
                ),
            ),
            (
                "Starting a campaign",
                (
                    "A new campaign begins with Dr. Melo. Register your name, choose "
                    "Normal or Easy, review the summary and confirm. The name and mode "
                    "are then fixed for that campaign.",
                    "Normal contains all 40 missions. Easy is the curated 11-mission "
                    "classroom route. Skipped Easy missions are not marked as completed "
                    "and do not count towards the Easy score.",
                ),
            ),
            (
                "Missions and evidence",
                (
                    "Read the mission briefing before changing the simulator. Missions "
                    "often require a baseline and one or more controlled perturbations. "
                    "Change only the variables requested by the mission so that the "
                    "comparison remains interpretable.",
                    "A successful solver run is not automatically valid mission evidence. "
                    "The mission checks method, objective, bounds, genes and required "
                    "reports before recording a trial.",
                ),
            ),
            (
                "Hints, keys and score",
                (
                    "Most missions provide Conceptual, Experimental and Technical hints. "
                    "Hints consume bronze, silver and gold keys respectively.",
                    "A mission is worth 5 points with no hints, 3 after one hint, 2 after "
                    "two hints and 1 after all three. Your inventory and score are saved "
                    "with the campaign.",
                ),
            ),
            (
                "Saving on the Web",
                (
                    "In the browser, LabHero saves campaign state to the browser's local "
                    "storage. Back to Title saves before returning to the title screen. "
                    "New Game intentionally clears the current LabHero campaign.",
                    "Browser storage belongs to the exact site address you are using. A "
                    "save created on one browser/origin is not automatically shared with "
                    "another computer or domain.",
                ),
            ),
        ),
    },
    {
        "id": "how_to_simulate",
        "title": "How to Simulate",
        "color": "royalblue",
        "intro": (
            "Use this book as a reference for the simulator. The most important rule is "
            "to distinguish the model's primary objective from secondary method scores "
            "and from any individual reaction flux."
        ),
        "sections": (
            (
                "FBA: Flux Balance Analysis",
                (
                    "FBA assumes a steady-state intracellular mass balance, commonly "
                    "written S v = 0. Reaction lower and upper bounds define the feasible "
                    "flux space, and a linear objective is optimized inside that space.",
                    "If the biomass reaction is the objective, its optimal flux is a model "
                    "proxy for biomass production under the chosen assumptions. If an "
                    "exchange reaction is the objective, the reported objective flux is "
                    "that exchange flux instead; do not call every objective value a "
                    "growth rate.",
                ),
            ),
            (
                "pFBA: Parsimonious FBA",
                (
                    "pFBA first preserves the optimal primary objective found by FBA and "
                    "then minimizes total flux usage. It therefore selects a parsimonious "
                    "solution among primary-optimal alternatives.",
                    "The pFBA secondary quantity is not a second biological objective and "
                    "a larger value is not automatically better. Compare primary objective "
                    "fluxes first, then use total absolute flux or the displayed pFBA "
                    "diagnostic to discuss parsimony.",
                ),
            ),
            (
                "lMOMA: minimal adjustment",
                (
                    "lMOMA compares a perturbed state with a reference state and finds a "
                    "feasible flux distribution with a small linearized adjustment from "
                    "that reference. It answers a different question from FBA: adaptation "
                    "near a reference rather than complete re-optimization of the primary "
                    "objective.",
                    "A meaningful comparison requires a valid reference generated under "
                    "the intended pre-perturbation conditions.",
                ),
            ),
            (
                "ROOM: regulatory on/off minimization",
                (
                    "ROOM also requires a pre-knockout reference. LabHero records that "
                    "reference before the perturbation and compares the mutant in the same "
                    "environment unless the mission explicitly changes the environment.",
                    "A reaction counts as significantly changed when it leaves the tolerance "
                    "band defined from the reference using delta and epsilon. The ROOM "
                    "method score is an integer ROOM change count, not the predicted growth rate. A "
                    "smaller count means fewer reactions crossed that significant-change "
                    "criterion; it does not by itself mean that the mutant grows better.",
                ),
            ),
            (
                "Objectives",
                (
                    "The Objective menu chooses what the optimization attempts to maximize. "
                    "Biomass is common, but several missions deliberately maximize an "
                    "exchange flux to expose trade-offs between growth and production.",
                    "When comparing runs, keep the objective fixed unless changing it is "
                    "the experimental variable. Record the predicted growth rate separately when "
                    "viability or growth capability is part of the question.",
                ),
            ),
            (
                "Environmental bounds and exchange fluxes",
                (
                    "Exchange reactions connect the model with its environment. In the "
                    "LabHero convention used by the supplied models, a negative exchange "
                    "flux usually represents uptake and a positive exchange flux secretion.",
                    "A lower bound such as -10 permits uptake up to that magnitude; it does "
                    "not force the cell to use exactly 10. Likewise, an upper bound may be "
                    "non-binding if the optimal solution never reaches it. Inspect the "
                    "actual exchange flux before claiming that a bound constrained the "
                    "solution.",
                ),
            ),
            (
                "Genes and GPR rules",
                (
                    "Gene knockouts act through gene-protein-reaction (GPR) rules. AND "
                    "means all listed gene products are required for that reaction; OR "
                    "represents alternative gene products that may preserve activity.",
                    "A zero-growth knockout is therefore context dependent: objective, "
                    "medium, oxygen availability and alternative pathways all matter. "
                    "Do not describe a gene as universally essential from a single model "
                    "condition.",
                ),
            ),
            (
                "Bound Sweeps and controlled comparisons",
                (
                    "A Bound Sweep repeats the same model setup across several values of "
                    "one bound. It is useful for finding thresholds, non-binding regions "
                    "and changes in secretion or predicted growth rate.",
                    "For interpretable evidence, vary one intended factor at a time. Keep "
                    "method, objective, gene state and unrelated bounds unchanged unless "
                    "the mission explicitly defines a factorial experiment.",
                ),
            ),
            (
                "Reading the reports",
                (
                    "Always check solver status. Then distinguish Primary Objective Flux, "
                    "Predicted Growth Rate, exchange/production fluxes and method-specific "
                    "diagnostics. They answer different questions.",
                    "Use Compare Runs, Exchange Flux Report and Bound Sweep Report when a "
                    "mission asks for quantitative evidence. The mission validator uses "
                    "the visible recorded evidence rather than assuming that your latest "
                    "configuration was valid.",
                    "LabHero displays predicted growth rate in h^-1. Reaction and exchange "
                    "fluxes, including configured bounds, use mmol gDW^-1 h^-1. Counts, "
                    "percentages, fold changes and ROOM scores are not given flux units.",
                ),
            ),
        ),
    },
    {
        "id": "brief_history",
        "title": "Microorganisms: From Microscopy to Systems Biology",
        "color": "green",
        "intro": (
            "Microbiology moved from observing tiny organisms to measuring genes, "
            "metabolites and whole biochemical networks. LabHero sits at the systems-"
            "biology end of that history: it asks what a mathematical model predicts "
            "under explicitly defined assumptions."
        ),
        "sections": (
            (
                "What counts as a microorganism?",
                (
                    "Microorganisms include diverse microscopic forms of life such as "
                    "bacteria, archaea and many fungi and protists. Some are unicellular; "
                    "the category is broader than 'single-celled bacteria'. Viruses are "
                    "microscopic infectious agents but are not cellular organisms.",
                    "Microbes inhabit soil, water, hosts and extreme environments. Their "
                    "metabolism helps drive global carbon, nitrogen and sulfur cycles.",
                ),
            ),
            (
                "From observation to experiment",
                (
                    "Microscopy made microbial cells visible. Culture methods, controlled "
                    "media and biochemical assays then allowed researchers to test how "
                    "microbes grow and transform nutrients under defined conditions.",
                    "Modern molecular biology added genes, enzymes and regulatory "
                    "mechanisms to that picture. Genome sequencing later made it possible "
                    "to reconstruct large networks of metabolic reactions.",
                ),
            ),
            (
                "Why models?",
                (
                    "A metabolic reconstruction organizes known reactions, metabolites, "
                    "compartments and gene associations. A constraint-based model adds "
                    "mathematical bounds and an objective so that feasible flux states "
                    "can be analysed computationally.",
                    "A model is not the organism itself. Predictions depend on the network, "
                    "bounds, objective and algorithm. Experimental validation remains "
                    "essential.",
                ),
            ),
            (
                "Two LabHero organisms",
                (
                    "The E. coli core model is deliberately compact and useful for learning "
                    "central metabolism. The yeast iMM904 model is much larger and exposes "
                    "the same modelling ideas in a more complex eukaryotic network.",
                    "Moving from one model to another is a reminder that reaction IDs, "
                    "exchange sets, gene rules and quantitative predictions are model "
                    "specific even when the underlying principles are shared.",
                ),
            ),
        ),
    },
    {
        "id": "intro_modelling",
        "title": "Introduction to Constraint-Based Metabolic Modelling",
        "color": "orange",
        "intro": (
            "Constraint-based modelling asks which reaction-flux patterns are compatible "
            "with a metabolic network and a set of assumptions. It is powerful precisely "
            "because those assumptions are explicit and testable."
        ),
        "sections": (
            (
                "Reactions, metabolites and stoichiometry",
                (
                    "A metabolic model represents reactions that consume and produce "
                    "metabolites. Their stoichiometric coefficients form the matrix S, "
                    "while the vector v contains reaction fluxes.",
                    "Under the steady-state assumption for internal metabolites, S v = 0. "
                    "This is a mass-balance constraint, not a claim that the organism is "
                    "unchanging in every biological sense.",
                ),
            ),
            (
                "Bounds define the environment",
                (
                    "Every reaction has a lower and upper bound. Bounds encode direction, "
                    "capacity and environmental availability. Exchange-reaction bounds are "
                    "therefore one of the main ways LabHero represents different media.",
                    "A configured bound defines what is allowed. The optimized flux tells "
                    "you what the selected solution actually uses.",
                ),
            ),
            (
                "Objectives are hypotheses",
                (
                    "FBA needs an objective. Maximizing biomass is a useful modelling "
                    "hypothesis for many growth experiments, but it is not a universal law "
                    "of cellular behaviour.",
                    "Changing the objective can change the predicted flux distribution "
                    "dramatically. Several LabHero missions exploit this deliberately to "
                    "separate viability, product formation and optimization criteria.",
                ),
            ),
            (
                "Alternative optima and method choice",
                (
                    "Different flux distributions can achieve the same optimal objective. "
                    "pFBA adds a parsimony criterion; lMOMA and ROOM instead compare a "
                    "perturbed state with a reference. These methods therefore answer "
                    "related but different questions.",
                    "Method names should never be treated as interchangeable. Before "
                    "comparing numbers, ask what quantity that method optimized or "
                    "minimized.",
                ),
            ),
            (
                "Genes do not equal reactions",
                (
                    "GPR rules connect genes to reaction capability. A reaction may need "
                    "several genes (AND) or have alternative genes (OR), so a single gene "
                    "knockout does not map mechanically to a single disabled reaction.",
                    "Phenotypes emerge from the remaining network and the environment. "
                    "That is why LabHero tests gene essentiality, redundancy, rescue and "
                    "context dependence rather than memorizing gene labels.",
                ),
            ),
            (
                "What these models do not predict directly",
                (
                    "Standard FBA does not directly predict metabolite concentrations, "
                    "enzyme abundances, regulatory dynamics or time courses. Fluxes are "
                    "steady-state rates consistent with the constraints and objective.",
                    "Treat every result as a conditional model prediction: 'under these "
                    "assumptions, this solution is feasible/optimal', not as automatic "
                    "proof of what a real cell must do.",
                ),
            ),
        ),
    },
    {
        "id": "ecoli",
        "title": "E. coli and the Core Metabolic Model",
        "color": "violet",
        "intro": (
            "Escherichia coli is a major experimental and industrial model organism. "
            "LabHero begins with a compact E. coli core network so that central metabolic "
            "trade-offs remain visible while you learn constraint-based analysis."
        ),
        "sections": (
            (
                "Central carbon metabolism",
                (
                    "Glucose can feed glycolysis, the pentose-phosphate pathway and the "
                    "tricarboxylic-acid network. These pathways exchange carbon, reducing "
                    "power and precursor metabolites needed for biomass formation.",
                    "The core model intentionally omits much of the full organism. Its "
                    "simplicity is useful for reasoning, but predictions should be "
                    "interpreted as properties of this model under the selected conditions.",
                ),
            ),
            (
                "Aerobic and oxygen-limited states",
                (
                    "When oxygen uptake is available, respiratory pathways can support "
                    "efficient reoxidation of reducing equivalents and a high predicted growth rate. "
                    "Closing or limiting oxygen forces the feasible network to redistribute "
                    "flux through alternative pathways.",
                    "Anaerobic does not mean 'no metabolism'. E. coli can maintain redox "
                    "balance through fermentative products and other routes represented in "
                    "the model, depending on available nutrients and bounds.",
                ),
            ),
            (
                "Growth versus production",
                (
                    "Maximizing the biomass reaction and maximizing a secreted product are "
                    "different objectives. A design with high product flux can have poor "
                    "predicted growth rate, and a high-growth solution can secrete little of the "
                    "target product.",
                    "Metabolic engineering therefore involves trade-offs. LabHero missions "
                    "use controlled objectives, knockouts and environmental constraints to "
                    "make those trade-offs measurable.",
                ),
            ),
            (
                "Gene knockouts and redundancy",
                (
                    "Knocking out a gene disables only reactions whose GPR rules require "
                    "that gene. Alternative isoenzymes or pathways can preserve the "
                    "phenotype, while the same knockout may become severe in a different "
                    "environment.",
                    "This is why essentiality is context dependent and why rescue "
                    "experiments must distinguish restored predicted growth rate from restoration "
                    "of the deleted gene or reaction.",
                ),
            ),
            (
                "Reading exchange reactions",
                (
                    "Exchange IDs such as EX_glc__D_e or EX_o2_e describe transfer between "
                    "the model and its environment. In LabHero's convention, negative flux "
                    "typically denotes uptake and positive flux secretion.",
                    "Always inspect the actual optimized exchange flux. A permissive lower "
                    "bound does not prove that the model consumed the full permitted amount.",
                ),
            ),
        ),
    },
    {
        "id": "eat_breathe_love",
        "title": "Eat, Breathe and Ferment",
        "color": "red",
        "intro": (
            "Nutrients, electron acceptors and redox balance shape metabolic behaviour. "
            "This book connects the environmental experiments in LabHero with the "
            "fermentation phenotypes explored in E. coli and yeast."
        ),
        "sections": (
            (
                "Eat: nutrient availability",
                (
                    "Carbon sources provide atoms and reducing power, but uptake is limited "
                    "by exchange bounds and by the reactions available inside the model. "
                    "Supplying a nutrient does not guarantee that the network can use it.",
                    "Nutrient screens and bound sweeps should therefore be read from the "
                    "optimized uptake fluxes, not from the configured bounds alone.",
                ),
            ),
            (
                "Breathe: oxygen as an environmental constraint",
                (
                    "Oxygen uptake can enable respiratory flux patterns with different "
                    "energy and redox consequences from oxygen-limited states. In the "
                    "simulator, changing EX_o2_e changes a constraint; the resulting flux "
                    "distribution is then selected by the chosen method and objective.",
                    "A zero oxygen-uptake bound represents an anaerobic model condition. "
                    "Intermediate caps can reveal transitions rather than a simple binary "
                    "aerobic/anaerobic switch.",
                ),
            ),
            (
                "Ferment: balancing redox without full respiration",
                (
                    "Fermentation routes can reoxidize cofactors and secrete reduced "
                    "products when respiratory capacity is absent or limited. The exact "
                    "products and quantitative fluxes are network- and condition-dependent.",
                    "For E. coli, LabHero tracks products such as ethanol, acetate, formate "
                    "and succinate in several missions. Their fluxes are evidence about how "
                    "the optimized network redistributed carbon and redox demand.",
                ),
            ),
            (
                "Yeast and iMM904",
                (
                    "The Golden Lab introduces Saccharomyces cerevisiae through iMM904, a "
                    "larger genome-scale model. The same principles still apply: choose a "
                    "method and objective, constrain exchanges, inspect fluxes and compare "
                    "controlled conditions.",
                    "Mission 36 uses an oxygen-cap sweep to identify the onset of a "
                    "fermentative phenotype. The lesson is not that one oxygen value is "
                    "universal, but that a model can be interrogated systematically for "
                    "condition-dependent transitions.",
                ),
            ),
            (
                "Interpretation discipline",
                (
                    "Do not infer concentrations or time-dependent growth curves from a "
                    "steady-state flux alone. Do not call a permitted uptake bound an "
                    "observed uptake, and do not equate a method score with predicted growth rate.",
                    "State the model, method, objective and changed constraint when reporting "
                    "a result. That makes the conclusion reproducible and scientifically "
                    "meaningful.",
                ),
            ),
        ),
    },
)


BOOK_BY_ID = {book["id"]: book for book in BOOK_LIBRARY}
