from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
CODE=ROOT/"code"
class QAScientificHintConsistencyTests(unittest.TestCase):
    def test_missions_with_briefing_hints_also_offer_hints_on_main_menu(self):
        failures=[]
        for mission_id in range(3,36):
            source=(CODE/f"mission{mission_id:02d}.py").read_text(encoding="utf-8")
            if "briefing.add.button('Optional Hints" in source and "menu.add.button('Optional Hints" not in source:
                failures.append(f"Mission {mission_id:02d}")
        self.assertEqual([],failures,"Missing main-menu hint access: "+", ".join(failures))
    def test_mission15_biomass_objective_is_presented_as_growth_rate(self):
        source=(CODE/"simulation.py").read_text(encoding="utf-8")
        self.assertIn("Predicted growth rate (primary objective)",source)
        self.assertIn("run.get('objective') == MISSION15_GROWTH_OBJECTIVE",source)
    def test_aggregate_flux_criteria_use_model_flux_units(self):
        source=(CODE/"scientific_display.py").read_text(encoding="utf-8")
        self.assertIn('AGGREGATE_FLUX_UNIT = "model flux units"',source)
    def test_mission35_uses_inventory_key_e(self):
        source=(CODE/"mission35.py").read_text(encoding="utf-8")
        self.assertNotIn("Press C",source); self.assertNotIn("press C",source); self.assertIn("Inventory with E",source)
    def test_mission_markdown_has_no_biomass_flux_label(self):
        offenders=[p.name for p in (ROOT/"data/missions").glob("mission*.md") if "biomass flux" in p.read_text(encoding="utf-8").lower()]
        self.assertEqual([],offenders)
if __name__=="__main__": unittest.main()
