"""Regression tests for Mission 01 and exchange-bound handling.

Run from the project root with:
    python -m unittest tests.test_mission01

The test intentionally checks relationships instead of one exact rounded
objective value, so it remains robust across compatible solver versions.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_DIR = PROJECT_ROOT / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import simulation  # noqa: E402


class Mission01RegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.genes = simulation._build_active_genes_data()
        self.default_reactions = simulation._build_default_reactions_data()

    def _simulate_growth(self, reactions):
        simul, constraints = simulation._build_local_constraints(self.genes, reactions)
        simul.objective = simulation.MISSION01_GROWTH_OBJECTIVE
        result = simul.simulate(method=simulation.MISSION01_METHOD, constraints=constraints)
        growth = simulation._as_float_or_none(simulation._normalise_result(result))
        oxygen_flux = simulation._as_float_or_none(
            simulation._extract_flux(result, simulation.MISSION01_OXYGEN_REACTION)
        )
        self.assertIsNotNone(growth)
        self.assertIsNotNone(oxygen_flux)
        return float(growth), float(oxygen_flux), constraints

    def _valid_compare_runs(self):
        baseline = {
            "result_available": True,
            "run_kind": "default growth setup",
            "method": simulation.MISSION01_METHOD,
            "objective": simulation.MISSION01_GROWTH_OBJECTIVE,
            "knocked_out_genes": [],
            "environment_changed": False,
            "oxygen_lower_bound_closed": False,
            "oxygen_unexpected_changes": [],
            "growth_value": 0.874,
            "exchange_uptake_fluxes": {
                simulation.MISSION01_OXYGEN_REACTION: 21.799
            },
            "selected_production_fluxes": [],
        }
        anaerobic = {
            "result_available": True,
            "run_kind": "anaerobic medium (oxygen uptake blocked)",
            "method": simulation.MISSION01_METHOD,
            "objective": simulation.MISSION01_GROWTH_OBJECTIVE,
            "knocked_out_genes": [],
            "environment_changed": True,
            "oxygen_lower_bound_closed": True,
            "oxygen_unexpected_changes": [],
            "growth_value": 0.212,
            "exchange_uptake_fluxes": {
                simulation.MISSION01_OXYGEN_REACTION: 0.0
            },
            "selected_production_fluxes": [],
        }
        return {"run_a": baseline, "run_b": anaerobic}

    def test_explicit_empty_comparison_does_not_load_saved_runs(self):
        stored_runs = self._valid_compare_runs()
        with patch.object(simulation, "load_compare_runs", return_value=stored_runs) as loader:
            with patch.object(simulation, "save_mission01_comparison_check"):
                check = simulation.run_mission01_comparison_check({})

        loader.assert_not_called()
        self.assertFalse(check["baseline_run_found"])
        self.assertFalse(check["anaerobic_run_found"])
        self.assertFalse(check["ready_to_deliver"])
        self.assertIn("Run the aerobic baseline", check.get("error", ""))

    def test_omitted_comparison_loads_saved_runs(self):
        stored_runs = self._valid_compare_runs()
        with patch.object(simulation, "load_compare_runs", return_value=stored_runs) as loader:
            with patch.object(simulation, "save_mission01_comparison_check"):
                check = simulation.run_mission01_comparison_check()

        loader.assert_called_once_with()
        self.assertTrue(check["baseline_run_found"])
        self.assertTrue(check["anaerobic_run_found"])
        self.assertTrue(check["ready_to_deliver"])

    def test_explicit_empty_compare_report_does_not_load_saved_runs(self):
        stored_runs = self._valid_compare_runs()
        with patch.object(simulation, "load_compare_runs", return_value=stored_runs) as loader:
            report = simulation.build_compare_runs_report_text({})

        loader.assert_not_called()
        self.assertIn("Run two simulations to generate a comparison.", report)
        self.assertNotIn("Main numeric comparison:", report)

    def test_default_medium_preserves_model_bounds(self):
        _, _, constraints = self._simulate_growth(self.default_reactions)
        self.assertEqual(constraints["EX_glc__D_e"], (-10.0, 1000.0))
        self.assertEqual(constraints["EX_o2_e"], (-1000.0, 1000.0))

    def test_opening_closed_uptake_uses_minus_ten_fallback(self):
        reactions = dict(self.default_reactions)
        fructose_index = list(simulation.REACTIONS.index).index("EX_fru_e")
        reactions[f"reaction_{fructose_index}_lb"] = True
        _, _, constraints = self._simulate_growth(reactions)
        self.assertEqual(constraints["EX_fru_e"], (-10.0, 1000.0))

    def test_report_formatting_uses_anaerobic_terms_and_cleans_negative_zero(self):
        self.assertEqual(simulation._fmt_compare_value(-0.0), "0.000")
        self.assertEqual(simulation._fmt_compare_delta(-0.0), "0.000")

        baseline = {
            "run_kind": "default growth setup",
            "method": simulation.MISSION01_METHOD,
            "objective": simulation.MISSION01_GROWTH_OBJECTIVE,
            "growth_value": 0.874,
            "knocked_out_genes": [],
            "environment_changed": False,
            "oxygen_lower_bound_closed": False,
            "oxygen_unexpected_changes": [],
            "exchange_uptake_fluxes": {simulation.MISSION01_OXYGEN_REACTION: 21.799},
            "selected_production_fluxes": [],
        }
        anaerobic = {
            "run_kind": "anaerobic medium (oxygen uptake blocked)",
            "method": simulation.MISSION01_METHOD,
            "objective": simulation.MISSION01_GROWTH_OBJECTIVE,
            "growth_value": 0.212,
            "knocked_out_genes": [],
            "environment_changed": True,
            "oxygen_lower_bound_closed": True,
            "oxygen_unexpected_changes": [],
            "exchange_uptake_fluxes": {simulation.MISSION01_OXYGEN_REACTION: -0.0},
            "selected_production_fluxes": [],
        }
        report = simulation.build_compare_runs_report_text(
            {"run_a": baseline, "run_b": anaerobic}
        )
        self.assertIn("anaerobic medium (oxygen uptake blocked)", report)
        self.assertIn("Oxygen uptake magnitude", report)
        self.assertNotIn("-0.000", report)
        self.assertIn("alternative optimal flux distributions", report)

    def test_controlled_anaerobic_comparison_is_valid(self):
        baseline_growth, baseline_o2_flux, _ = self._simulate_growth(self.default_reactions)

        anaerobic_reactions = dict(self.default_reactions)
        oxygen_index = list(simulation.REACTIONS.index).index(
            simulation.MISSION01_OXYGEN_REACTION
        )
        anaerobic_reactions[f"reaction_{oxygen_index}_lb"] = False
        anaerobic_growth, anaerobic_o2_flux, constraints = self._simulate_growth(
            anaerobic_reactions
        )

        self.assertEqual(constraints[simulation.MISSION01_OXYGEN_REACTION], (0.0, 1000.0))
        self.assertGreater(baseline_growth, anaerobic_growth)
        self.assertGreaterEqual(anaerobic_growth, simulation.MISSION01_MIN_VIABLE_GROWTH)
        self.assertLessEqual(abs(anaerobic_o2_flux), simulation.MISSION01_FLUX_TOLERANCE)

        baseline_snapshot = {
            "result_available": True,
            "method": simulation.MISSION01_METHOD,
            "objective": simulation.MISSION01_GROWTH_OBJECTIVE,
            "knocked_out_genes": [],
            "environment_changed": False,
            "oxygen_lower_bound_closed": False,
            "oxygen_unexpected_changes": [],
            "growth_value": baseline_growth,
            "exchange_uptake_fluxes": {
                simulation.MISSION01_OXYGEN_REACTION: max(-baseline_o2_flux, 0.0)
            },
        }
        anaerobic_snapshot = {
            "result_available": True,
            "method": simulation.MISSION01_METHOD,
            "objective": simulation.MISSION01_GROWTH_OBJECTIVE,
            "knocked_out_genes": [],
            "environment_changed": True,
            "oxygen_lower_bound_closed": True,
            "oxygen_unexpected_changes": [],
            "growth_value": anaerobic_growth,
            "exchange_uptake_fluxes": {
                simulation.MISSION01_OXYGEN_REACTION: max(-anaerobic_o2_flux, 0.0)
            },
        }

        with patch.object(simulation, "save_mission01_comparison_check"):
            check = simulation._build_mission01_data(
                {"run_a": baseline_snapshot, "run_b": anaerobic_snapshot}
            )

        self.assertTrue(check["ready_to_deliver"])
        self.assertTrue(check["anaerobic_growth_viable"])
        self.assertTrue(check["growth_decreased"])
        self.assertTrue(check["baseline_uses_oxygen"])
        self.assertTrue(check["anaerobic_oxygen_blocked"])

    def test_mission01_delivery_requires_activation(self):
        source = (CODE_DIR / 'mission01.py').read_text(encoding='utf-8')
        self.assertIn("if '01' not in self.missions_activated:", source)
        self.assertIn('Activate Mission 01 before delivering results.', source)

    def test_mission01_reactivation_does_not_clear_valid_evidence(self):
        source = (CODE_DIR / 'mission01.py').read_text(encoding='utf-8')
        active_guard = source.index("if '01' in self.missions_activated:")
        clear_runs = source.index('clear_compare_runs()', active_guard)
        clear_check = source.index('clear_mission01_comparison_check()', active_guard)
        self.assertLess(active_guard, clear_runs)
        self.assertLess(active_guard, clear_check)
        self.assertIn('Mission 01 is already active.', source[active_guard:clear_runs])



if __name__ == "__main__":
    unittest.main()
