import ast
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))

from campaign import CampaignContext
from final_results import build_final_results_snapshot


class FakeHintSystem:
    def __init__(self, scores=None, hints=None, wrong_answers=None, legacy=None):
        self.state = {
            'mission_scores': dict(scores or {}),
            'mission_hints': dict(hints or {}),
            'mission_wrong_answers': dict(wrong_answers or {}),
            'legacy_unscored_missions': list(legacy or []),
        }

    def sync_completed_missions(self, _completed):
        return {}


class FakePlayer:
    def __init__(self, mode, completed, scores=None, hints=None, wrong_answers=None, legacy=None):
        self.player_name = 'Tomás'
        self.campaign_mode = mode
        self.missions_completed = list(completed)
        self.hint_system = FakeHintSystem(scores=scores, hints=hints, wrong_answers=wrong_answers, legacy=legacy)

    def get_campaign_context(self):
        return CampaignContext(self.campaign_mode)


class Student2FinalResultsTests(unittest.TestCase):
    def test_easy_summary_uses_11_mission_denominator(self):
        ctx = CampaignContext('easy')
        scores = {mid: 5 for mid in ctx.mission_sequence}
        player = FakePlayer('easy', ctx.mission_sequence, scores=scores)
        data = build_final_results_snapshot(player)
        self.assertTrue(data['campaign_complete'])
        self.assertEqual(data['missions_completed'], 11)
        self.assertEqual(data['mission_count'], 11)
        self.assertEqual(data['score'], 55)
        self.assertEqual(data['max_score'], 55)
        self.assertEqual(data['final_mission'], '36')

    def test_normal_summary_uses_40_mission_denominator(self):
        ctx = CampaignContext('normal')
        scores = {mid: 5 for mid in ctx.mission_sequence}
        player = FakePlayer('normal', ctx.mission_sequence, scores=scores)
        data = build_final_results_snapshot(player)
        self.assertEqual(data['missions_completed'], 40)
        self.assertEqual(data['score'], 200)
        self.assertEqual(data['max_score'], 200)
        self.assertEqual(data['final_mission'], '40')

    def test_easy_summary_ignores_scores_and_hints_outside_easy_route(self):
        ctx = CampaignContext('easy')
        scores = {mid: 3 for mid in ctx.mission_sequence}
        scores['40'] = 5
        hints = {'01': 1, '03': 2, '40': 3}
        player = FakePlayer('easy', ctx.mission_sequence, scores=scores, hints=hints)
        data = build_final_results_snapshot(player)
        self.assertEqual(data['score'], 33)
        self.assertEqual(data['hint_levels_unlocked'], 3)
        self.assertEqual(data['missions_with_hints'], 2)

    def test_summary_reports_wrong_answers_only_from_current_route(self):
        ctx = CampaignContext('easy')
        scores = {mid: 4 for mid in ctx.mission_sequence}
        wrong_answers = {'02': 3, '03': 1, '40': 7}
        player = FakePlayer(
            'easy',
            ctx.mission_sequence,
            scores=scores,
            wrong_answers=wrong_answers,
        )
        data = build_final_results_snapshot(player)
        # Mission 40 is not part of the Easy route and must not pollute the
        # student's Easy final-results statistics.
        expected = sum(
            wrong_answers.get(mid, 0)
            for mid in ctx.mission_sequence
        )
        self.assertEqual(data['wrong_answers'], expected)

    def test_legacy_unscored_is_reported_not_invented(self):
        ctx = CampaignContext('easy')
        scores = {mid: 5 for mid in ctx.mission_sequence if mid != '36'}
        player = FakePlayer(
            'easy',
            ctx.mission_sequence,
            scores=scores,
            legacy=['36', '40'],
        )
        data = build_final_results_snapshot(player)
        self.assertEqual(data['score'], 50)
        self.assertEqual(data['legacy_unscored_missions'], ('36',))

    def test_not_complete_until_mode_final_mission_is_done(self):
        ctx = CampaignContext('easy')
        completed = ctx.mission_sequence[:-1]
        player = FakePlayer('easy', completed)
        self.assertFalse(build_final_results_snapshot(player)['campaign_complete'])

    def test_player_state_persists_seen_flag_without_save_schema_change(self):
        source = (ROOT / 'code' / 'player.py').read_text(encoding='utf-8')
        self.assertIn("self.final_results_seen = bool(", source)
        self.assertIn("'final_results_seen': bool(self.final_results_seen)", source)
        self.assertIn("return [", source)
        self.assertIn("self.hint_system.to_dict()", source)

    def test_default_state_migrates_old_saves_to_unseen(self):
        source = (ROOT / 'code' / 'settings.py').read_text(encoding='utf-8')
        self.assertIn("'final_results_seen': False", source)

    def test_level_opens_results_from_campaign_context_and_marks_seen_on_close(self):
        source = (ROOT / 'code' / 'level.py').read_text(encoding='utf-8')
        self.assertIn('self.campaign_context.is_campaign_complete(self.player.missions_completed)', source)
        self.assertIn('not self.player.final_results_seen', source)
        self.assertIn('self.player.final_results_seen = True', source)
        self.assertIn('save_file(self.player.get_save_data())', source)
        self.assertIn('elif self.menu_active:', source)

    def test_completed_campaign_can_reopen_final_results_with_f_only(self):
        source = (ROOT / 'code' / 'level.py').read_text(encoding='utf-8')
        self.assertIn('def can_reopen_final_results(self):', source)
        self.assertIn('not self.teacher_preview', source)
        self.assertIn('self.player.name_confirmed', source)
        self.assertIn('self.campaign_context.is_campaign_complete(self.player.missions_completed)', source)
        self.assertIn('def handle_final_results_shortcut(self):', source)
        self.assertIn('pygame.K_f', source)
        self.assertIn('self.final_results_active = True', source)
        self.assertIn('self.handle_final_results_shortcut()', source)

    def test_final_results_screen_explains_f_reopen_shortcut(self):
        source = (ROOT / 'code' / 'final_results.py').read_text(encoding='utf-8')
        self.assertIn(
            'After closing, press F while exploring to view these Final Results again.',
            source,
        )

    def test_final_results_ui_uses_unicode_font_for_student_name(self):
        source = (ROOT / 'code' / 'final_results.py').read_text(encoding='utf-8')
        self.assertIn("font_name=unicode_font", source)
        self.assertIn("Student: {snapshot['student']}", source)

    def test_final_results_module_has_no_top_level_pygame_dependency(self):
        tree = ast.parse((ROOT / 'code' / 'final_results.py').read_text(encoding='utf-8'))
        top_imports = [
            node for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        imported = []
        for node in top_imports:
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            else:
                imported.append(node.module or '')
        self.assertNotIn('pygame', imported)
        self.assertNotIn('pygame_menu', imported)


if __name__ == '__main__':
    unittest.main()
