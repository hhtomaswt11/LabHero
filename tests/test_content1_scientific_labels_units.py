import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / "code"


class Content1ScientificDisplayTests(unittest.TestCase):
    def test_canonical_units_are_explicit(self):
        source = (CODE / "scientific_display.py").read_text(encoding="utf-8")
        self.assertIn('GROWTH_RATE_UNIT = "h^-1"', source)
        self.assertIn('FLUX_UNIT = "mmol gDW^-1 h^-1"', source)
        self.assertIn('AGGREGATE_FLUX_UNIT = "model flux units"', source)

    def test_simulator_uses_growth_rate_for_biomass_display(self):
        source = (CODE / "window.py").read_text(encoding="utf-8")
        self.assertIn("Predicted growth rate:", source)
        self.assertNotIn("Predicted biomass flux:", source)
        self.assertNotIn("Reference biomass flux:", source)

    def test_objective_flux_is_not_globally_called_growth(self):
        source = (CODE / "window.py").read_text(encoding="utf-8")
        self.assertIn("Objective flux", source)
        self.assertIn("Primary objective flux", source)
        self.assertIn("objective_name == biomass_reaction", source)

    def test_exchange_and_production_fluxes_use_flux_units(self):
        source = (CODE / "window.py").read_text(encoding="utf-8")
        self.assertIn("format_flux(item.get('production_flux'", source)
        self.assertIn("raw flux {format_flux(raw_flux)}", source)
        self.assertIn("FLUX_UNIT", source)

    def test_bound_sweep_headers_declare_units(self):
        source = (CODE / "window.py").read_text(encoding="utf-8")
        self.assertIn("growth rate ({GROWTH_RATE_UNIT})", source)
        self.assertIn("({FLUX_UNIT})", source)

    def test_room_score_is_not_given_flux_units(self):
        source = (CODE / "window.py").read_text(encoding="utf-8")
        line = next(
            line for line in source.splitlines()
            if "Significant flux changes:" in line and "score" in line
        )
        self.assertNotIn("FLUX_UNIT", line)
        self.assertNotIn("GROWTH_RATE_UNIT", line)

    def test_mission_reports_share_canonical_units(self):
        source = (CODE / "simulation.py").read_text(encoding="utf-8")
        self.assertIn("from scientific_display import GROWTH_RATE_UNIT, FLUX_UNIT, AGGREGATE_FLUX_UNIT", source)
        self.assertIn("growth rate ({GROWTH_RATE_UNIT})", source)
        self.assertIn("AGGREGATE_FLUX_UNIT", source)
        self.assertIn("Glucose LB ({FLUX_UNIT})", source)

    def test_mission09_baseline_uptakes_include_flux_units(self):
        source = (CODE / "simulation.py").read_text(encoding="utf-8")
        self.assertIn("L-malate uptake {float(baseline.get('malate_uptake', 0.0)):.3f} {FLUX_UNIT}", source)
        self.assertIn("oxygen uptake {float(baseline.get('oxygen_uptake', 0.0)):.3f} {FLUX_UNIT}", source)

    def test_mission15_and_18_tracked_flux_profiles_include_units(self):
        source = (CODE / "simulation.py").read_text(encoding="utf-8")
        self.assertIn("{_clean_display_number(values.get(reaction_id)):.3f} {FLUX_UNIT}", source)
        self.assertIn("{float(baseline_fluxes.get(reaction_id, 0.0)):.3f} {FLUX_UNIT}", source)
        self.assertIn("{flux_id} {float(fluxes.get(flux_id, 0.0)):.3f} {FLUX_UNIT}", source)

    def test_mission19_player_text_uses_growth_rate(self):
        source = (CODE / "mission19.py").read_text(encoding="utf-8")
        self.assertIn("predicted growth rate", source)
        self.assertNotIn("both biomass flux and the lMOMA adjustment score", source)

    def test_books_document_units(self):
        text = (ROOT / "data/books/How to Simulate.md").read_text(encoding="utf-8")
        self.assertIn("h^-1", text)
        self.assertIn("mmol gDW^-1 h^-1", text)
        self.assertIn("Predicted Growth Rate", text)
        self.assertIn("model flux units", text)


if __name__ == "__main__":
    unittest.main()
