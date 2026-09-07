"""Validate requests and run real solver checks at the backend boundary."""
import sys
import unittest
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.schemas import SimulateRequest
from app.simulator import simulate


class BackendInputValidationTests(unittest.TestCase):
    def request(self, **overrides):
        return SimulateRequest(**{'objective': 'BIOMASS_Ecoli_core_w_GAM', **overrides})

    def test_nonfinite_bounds_are_rejected_before_solving(self):
        for number in ('NaN', 'Infinity', '-Infinity'):
            for bounds in ((number, 1000), (-10, number)):
                with self.subTest(bounds=bounds), self.assertRaises(ValidationError):
                    self.request(env_conditions={'EX_o2_e': bounds})

    def test_reversed_bounds_are_rejected_before_solving(self):
        with self.assertRaises(ValidationError):
            self.request(env_conditions={'EX_o2_e': (1, 0)})

    def test_internal_reaction_cannot_be_changed_as_environment(self):
        result = simulate(self.request(env_conditions={'ATPM': (0, 0)}))
        self.assertEqual(result.status, 'error')
        self.assertIn('not an exchange', result.message)

    def test_unknown_gene_and_objective_are_rejected(self):
        for changes in ({'objective': 'missing'}, {'gene_knockouts': ['missing']}):
            with self.subTest(changes=changes):
                self.assertEqual(simulate(self.request(**changes)).status, 'error')

    def test_environment_change_does_not_leak_into_next_request(self):
        baseline = simulate(self.request())
        anaerobic = simulate(self.request(env_conditions={'EX_o2_e': (0, 1000)}))
        restored = simulate(self.request())
        self.assertEqual([r.status for r in (baseline, anaerobic, restored)], ['ok'] * 3)
        self.assertGreater(baseline.primary_objective_flux, anaerobic.primary_objective_flux)
        self.assertAlmostEqual(baseline.primary_objective_flux, restored.primary_objective_flux)

    def test_yeast_pfba_returns_primary_biomass_flux(self):
        result = simulate(self.request(model_id='yeast_iMM904', method='pFBA',
                                       objective='BIOMASS_SC5_notrace'))
        self.assertEqual(result.status, 'ok')
        self.assertGreater(result.primary_objective_flux, 0)
        self.assertEqual(result.primary_objective_flux, result.fluxes['BIOMASS_SC5_notrace'])


if __name__ == '__main__':
    unittest.main()
