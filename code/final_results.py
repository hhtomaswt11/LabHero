"""Campaign-completion summary for Normal and Easy student routes.

The data builder is intentionally independent of pygame so score/completion
semantics can be regression-tested without a graphical runtime.
"""


def build_final_results_snapshot(player):
    """Return the final student-facing campaign summary.

    Scores and hints are filtered to the current campaign sequence.  Skipped
    Easy missions therefore never affect the Easy denominator or statistics.
    Legacy-unscored missions remain explicitly reported rather than receiving
    invented scores.
    """
    context = player.get_campaign_context()
    sequence = tuple(context.mission_sequence or ())
    completed = tuple(context.completed_missions_in_mode(player.missions_completed))

    # Mission completion normally synchronises scores through get_save_data().
    # Synchronise again here so the final screen is correct even when opened
    # from a migrated/historic save.
    player.hint_system.sync_completed_missions(player.missions_completed)
    state = player.hint_system.state

    mission_scores = state.get('mission_scores', {})
    mission_hints = state.get('mission_hints', {})
    legacy = set(state.get('legacy_unscored_missions', ()))

    score = sum(int(mission_scores.get(mid, 0)) for mid in sequence)
    hint_levels_unlocked = sum(int(mission_hints.get(mid, 0)) for mid in sequence)
    missions_with_hints = sum(1 for mid in sequence if int(mission_hints.get(mid, 0)) > 0)
    mission_wrong_answers = state.get('mission_wrong_answers', {})
    wrong_answers = sum(int(mission_wrong_answers.get(mid, 0)) for mid in sequence)
    legacy_unscored = tuple(mid for mid in sequence if mid in legacy)

    return {
        'student': str(player.player_name),
        'mode': context.mode,
        'mode_label': context.mode.title(),
        'score': score,
        'max_score': context.max_score,
        'missions_completed': len(completed),
        'mission_count': context.mission_count,
        'hint_levels_unlocked': hint_levels_unlocked,
        'missions_with_hints': missions_with_hints,
        'wrong_answers': wrong_answers,
        'legacy_unscored_missions': legacy_unscored,
        'campaign_complete': context.is_campaign_complete(player.missions_completed),
        'final_mission': context.final_mission,
    }


class FinalResultsMenu:
    """One-shot pygame-menu presentation opened after the route's final mission."""

    def __init__(self, player, on_close):
        self.player = player
        self.on_close = on_close

    async def update(self):
        import pygame
        import pygame_menu

        from async_menu import run_menu
        from options_values import mytheme
        from settings import SCREEN_HEIGHT, SCREEN_WIDTH
        from utils import get_resource_path

        snapshot = build_final_results_snapshot(self.player)
        menu = pygame_menu.Menu(
            'Campaign Complete',
            SCREEN_WIDTH,
            SCREEN_HEIGHT,
            theme=mytheme,
            onclose=self.on_close,
        )

        unicode_font = get_resource_path('font/LycheeSoda.ttf')

        menu.add.vertical_margin(25)
        menu.add.label(
            'LABHERO — FINAL RESULTS',
            font_size=42,
            align=pygame_menu.locals.ALIGN_CENTER,
        )
        menu.add.vertical_margin(18)
        menu.add.label(
            f"Student: {snapshot['student']}",
            font_name=unicode_font,
            font_size=32,
        )
        menu.add.label(f"Mode: {snapshot['mode_label']}", font_size=30)
        menu.add.vertical_margin(15)
        menu.add.label(
            f"Score: {snapshot['score']} / {snapshot['max_score']}",
            font_size=38,
        )
        menu.add.label(
            f"Missions completed: {snapshot['missions_completed']} / {snapshot['mission_count']}",
            font_size=30,
        )
        menu.add.label(
            f"Hints used: {snapshot['hint_levels_unlocked']}",
            font_size=28,
        )
        menu.add.label(
            f"Missions using hints: {snapshot['missions_with_hints']}",
            font_size=28,
        )
        menu.add.label(
            f"Incorrect final answers: {snapshot['wrong_answers']}",
            font_size=28,
        )

        if snapshot['legacy_unscored_missions']:
            menu.add.vertical_margin(10)
            menu.add.label(
                'Some missions are from an older save and have no reconstructable score: '
                + ', '.join(snapshot['legacy_unscored_missions']),
                wordwrap=True,
                font_size=22,
                font_color=(120, 80, 20),
                padding=(20, 10, 20, 10),
            )

        menu.add.vertical_margin(20)
        menu.add.label(
            'Campaign complete. You may continue exploring the laboratory.',
            wordwrap=True,
            font_size=26,
            align=pygame_menu.locals.ALIGN_CENTER,
        )
        menu.add.vertical_margin(8)
        menu.add.label(
            'After closing, press F while exploring to view these Final Results again.',
            wordwrap=True,
            font_size=23,
            align=pygame_menu.locals.ALIGN_CENTER,
        )

        def close_results():
            self.on_close()
            menu.disable()

        menu.add.button(
            'Continue Exploring',
            close_results,
            background_color=(50, 100, 100),
        )
        await run_menu(menu, pygame.display.get_surface())
