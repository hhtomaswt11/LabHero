import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODE = ROOT / 'code'
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import simulation


class AnswerValidationStrictnessTests(unittest.TestCase):
    """Regression guard against accepting ``correct answer + extra junk``.

    Mission answers are intentionally direct.  A validator may support known
    aliases/synonyms, but it must validate the complete submission rather than
    searching for one correct token inside an otherwise incorrect string.
    """

    def test_every_written_answer_parser_rejects_appended_unknown_content(self):
        cases = (
            ('M02', simulation.normalise_mission02_answer, 'fructose'),
            ('M03', simulation.normalise_mission03_answer, 'b2926'),
            ('M04', simulation.normalise_mission04_answer, 'b2278'),
            ('M05', simulation.normalise_mission05_answer, 'b3736'),
            ('M09', simulation.normalise_mission09_answer, 'b0115'),
            ('M10', simulation.normalise_mission10_answer, 'b2297 + b2458'),
            ('M11', simulation.normalise_mission11_answer, 'formate'),
            ('M12', simulation.normalise_mission12_answer, 'acetate'),
            ('M13', simulation.normalise_mission13_answer, 'total flux'),
            ('M14', simulation.normalise_mission14_answer, 'none'),
            ('M15', simulation.normalise_mission15_answer, 'objective conflict'),
            ('M16', simulation.normalise_mission16_answer, 'oxygen'),
            ('M17', simulation.normalise_mission17_answer, 'nh4 and pi'),
            ('M18', simulation.normalise_mission18_answer, 'acetate'),
            ('M19', simulation.normalise_mission19_answer, 'lMOMA'),
            ('M20', simulation.normalise_mission20_answer, 'anaerobic'),
            ('M21', simulation.normalise_mission21_answer, 'D-lactate'),
            ('M22', simulation.normalise_mission22_answer, 'zero'),
            ('M23', simulation.normalise_mission23_answer, 'acetate'),
            ('M24', simulation.normalise_mission24_answer, 'formate'),
            ('M25', simulation.normalise_mission25_answer, 'anaerobic'),
            ('M26', simulation.normalise_mission26_answer, '0'),
            ('M27', simulation.normalise_mission27_answer, 'akg'),
            ('M28', simulation.normalise_mission28_answer, 'b2587'),
            ('M29', simulation.normalise_mission29_answer, 'b0118 + b1276'),
            ('M30', simulation.normalise_mission30_answer, '-2'),
            ('M31', simulation.normalise_mission31_answer, 'glu'),
            ('M32', simulation.normalise_mission32_answer, 'b0978 + b0733'),
            ('M33', simulation.normalise_mission33_answer, 'unused'),
            ('M34', simulation.normalise_mission34_answer, 'equivalent'),
        )
        for mission, parser, valid in cases:
            with self.subTest(mission=mission):
                expected = parser(valid)
                self.assertNotEqual(expected, parser(f'{valid} randomtext'))

    def test_mission35_three_fields_are_individually_strict(self):
        self.assertEqual(simulation.normalise_mission35_target_answer('PDH'), 'PDH')
        self.assertIsNone(simulation.normalise_mission35_target_answer('PDH randomtext'))

        self.assertEqual(simulation.normalise_mission35_bound_answer('-5'), -5.0)
        self.assertIsNone(simulation.normalise_mission35_bound_answer('-5 -2'))

        self.assertFalse(simulation.normalise_mission35_viability_answer('no'))
        self.assertIsNone(simulation.normalise_mission35_viability_answer('no randomtext'))

    def test_yeast_answer_parsers_reject_appended_unknown_content(self):
        self.assertEqual(simulation._mission36_parse_answer('-1'), -1.0)
        self.assertIsNone(simulation._mission36_parse_answer('-1 randomtext'))

        valid37 = simulation._mission37_normalise_answer('PDC1 + PDC5 + PDC6')
        self.assertNotEqual(valid37, simulation._mission37_normalise_answer('PDC1 + PDC5 + PDC6 FRD1'))

        self.assertEqual(simulation._mission38_normalise_answer('FRD1'), 'FRD1')
        self.assertIsNone(simulation._mission38_normalise_answer('FRD1 PDC1'))

        self.assertEqual(simulation._mission39_normalise_answer('acetaldehyde'), 'acetaldehyde_open')
        self.assertIsNone(simulation._mission39_normalise_answer('acetaldehyde ethanol'))

        self.assertEqual(simulation._mission40_parse_answer_bounds('-2 -10'), {-2.0, -10.0})
        self.assertIsNone(simulation._mission40_parse_answer_bounds('-2 -10 randomtext'))

    def test_screenshot_regressions_are_closed(self):
        # M29: the correct aconitase pair plus an unrelated candidate gene.
        self.assertIsNone(simulation.normalise_mission29_answer('b0118 b1276 b1723'))
        # M30: the correct threshold plus another numeric answer.
        self.assertIsNone(simulation.normalise_mission30_answer('-2 -1'))
        # M31: correct source plus arbitrary extra text.
        self.assertIsNone(simulation.normalise_mission31_answer('glu randomtext'))
        # M38: correct candidate plus another gene from the experiment.
        self.assertIsNone(simulation._mission38_normalise_answer('FRD1 PDC1'))

    def test_legitimate_multi_token_aliases_remain_supported(self):
        self.assertEqual(
            set(simulation.normalise_mission17_answer(
                'I think ammonium and phosphate are the required uptake routes'
            )),
            {'EX_nh4_e', 'EX_pi_e'},
        )
        self.assertEqual(simulation.normalise_mission18_answer('acetate exchange'), ('EX_ac_e',))
        self.assertEqual(simulation.normalise_mission29_answer('ACONTa and ACONTb'), 'aconitase')
        self.assertEqual(
            simulation.normalise_mission32_answer(
                'cbdA + cydA',
                {'unique_tested_cut_set_genes': ['b0978', 'b0733']},
            ),
            ['b0733', 'b0978'],
        )
        self.assertEqual(
            simulation._mission40_parse_answer_bounds('LB -10, -2'),
            {-10.0, -2.0},
        )


if __name__ == '__main__':
    unittest.main()
