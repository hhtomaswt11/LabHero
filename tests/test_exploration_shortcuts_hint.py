import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.join(ROOT, 'code')
if CODE not in sys.path:
    sys.path.insert(0, CODE)


class ExplorationShortcutHintSourceTests(unittest.TestCase):
    def test_hint_lists_q_and_e_and_conditional_f(self):
        with open(os.path.join(CODE, 'quest_tracker.py'), encoding='utf-8') as handle:
            source = handle.read()
        self.assertIn('Q  Quest Tracker', source)
        self.assertIn('E  Inventory', source)
        self.assertIn('F  Final Results', source)
        self.assertIn('if show_final_results', source)

    def test_level_passes_campaign_completion_flag_to_hint(self):
        with open(os.path.join(CODE, 'level.py'), encoding='utf-8') as handle:
            source = handle.read()
        self.assertIn('show_final_results=self.can_reopen_final_results()', source)


if __name__ == '__main__':
    unittest.main()
